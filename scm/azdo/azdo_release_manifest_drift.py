#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
azdo_release_manifest_drift.py

Auditoría de consistencia de un stage CD (default: Production):

  1. Recorre todas las release definitions, una específica o un grupo
     separado por comas (IDs o substrings de nombre).
  2. Por cada una, localiza el ÚLTIMO release con deploy EFECTIVO en el
     stage (Deployments API: deploymentStatus != notDeployed) y descarga
     su snapshot.
  3. Descarga los logs de las tasks de manifiesto/apply del último
     attempt efectivo del stage.
  4. Compara definición actual vs snapshot del release (stages, variables,
     approvals, tasks + inputs de tasks).
  5. Analiza los logs de "get file k8-manifest", "show manifest" y
     "kubectl apply" para detectar DELTA entre el manifiesto aplicado y
     el estado del cluster — evidencia de manipulación directa fuera del
     pipeline:

       HIGH    objeto sin anotación last-applied-configuration
               (creado por fuera de kubectl apply)
       HIGH    objeto 'configured' con manifiesto IDÉNTICO al del release
               efectivo anterior (--prev-release): alguien lo editó a mano
       MEDIUM  objeto del manifiesto sin verdict en el apply
       LOW     objeto en el apply ausente del 'show manifest'
       INFO    'created' en objeto nuevo / 'configured' explicado por
               cambio de manifiesto

Uso:
    python azdo_release_manifest_drift.py
    python azdo_release_manifest_drift.py --definition-ids 3670
    python azdo_release_manifest_drift.py --definition-ids 3670,3701 --prev-release
    python azdo_release_manifest_drift.py --definition-ids "wms" \
        --task-patterns "k8.?manifest|kubectl.*apply" --output json

Autor: Harold Adrian
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

BASE_DIR = Path(__file__).resolve().parent          # scm/azdo
SCM_ROOT = BASE_DIR.parent                          # scm/

__version__ = "1.0.1"

# Reuso del cliente/config del remediator (mismo directorio)
try:
    from scm.azdo.scm_inspection_remediator import (
        AzdoClient, get_azdo_params, resolve_outcome_dir, _env_token, _LOG_TS,
    )
except ImportError:
    sys.path.insert(0, str(BASE_DIR))
    from scm_inspection_remediator import (
        AzdoClient, get_azdo_params, resolve_outcome_dir, _env_token, _LOG_TS,
    )

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH = True
except ImportError:
    RICH = False

console = Console() if RICH else None

SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4,
             "NONE": 5}
SEV_STYLE = {"CRITICAL": "bold white on red", "HIGH": "bold red",
             "MEDIUM": "yellow", "LOW": "cyan", "INFO": "dim", "NONE": "green"}

DEFAULT_STAGE = "production"
DEFAULT_TASK_PATTERNS = (
    r"get.?file.?k8.?manifest|show.?manifest|kubectl.*apply"
)
_APPLY_VERDICTS = ("created", "configured", "unchanged", "deleted", "pruned")


# ═══════════════════════════════════════════════════════════════════════════════
# ARGUMENTOS
# ═══════════════════════════════════════════════════════════════════════════════

def get_args() -> argparse.Namespace:
    cfg_defaults = {}
    p = argparse.ArgumentParser(
        description="Auditoría de drift de manifiestos K8s aplicados por CD "
                    "(definición vs release vs logs de kubectl apply).")
    p.add_argument("--pat", default="", help="Azure DevOps PAT (o azdo.pat en config.json)")
    p.add_argument("--org", default="", help="Organización AzDO")
    p.add_argument("--project", default="", help="Proyecto AzDO")
    p.add_argument(
        "--definition-ids", default="all",
        help="'all' | un ID | lista 'id1,id2' | substring de nombre "
             "(coma-separados, mezclables)")
    p.add_argument("--stage-name", default=DEFAULT_STAGE,
                   help=f"Stage a auditar (default: {DEFAULT_STAGE})")
    p.add_argument("--task-patterns", default=DEFAULT_TASK_PATTERNS,
                   help="Regex (|) para matchear tasks cuyos logs se analizan. "
                        f"Default: {DEFAULT_TASK_PATTERNS}")
    p.add_argument("--prev-release", action="store_true",
                   help="Comparar manifiesto del último release efectivo vs el "
                        "anterior: 'configured' con YAML idéntico = edición "
                        "manual en el cluster")
    p.add_argument("--top-deployments", type=int, default=10,
                   help="Deployments a revisar buscando efectivos (default: 10)")
    p.add_argument("--output", choices=["json", "csv", "both"], default="",
                   help="Exportar resultados a outcome/")
    p.add_argument("--threads", type=int, default=4,
                   help="Pipelines en paralelo (default: 4)")
    p.add_argument("--severity", choices=list(SEV_ORDER), default="NONE",
                   help="Solo mostrar pipelines con severidad >= N en el resumen")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# API — definiciones, deployments efectivos, release, logs
# ═══════════════════════════════════════════════════════════════════════════════

def list_release_definitions(client: AzdoClient, debug: bool = False) -> List[Dict]:
    """Todas las release definitions (paginación continuationToken)."""
    all_values: List[Dict] = []
    token = None
    while True:
        params: Dict = {"api-version": "7.1", "$top": 200}
        if token:
            params["continuationToken"] = token
        data = client.get(f"{client.base}/definitions", params=params)
        all_values.extend(data.get("value", []))
        token = data.get("continuationToken")
        if not token:
            break
    if debug and console:
        console.print(f"  [dim]{len(all_values)} release definitions[/]")
    return all_values


def select_definitions(defs: List[Dict], selector: str) -> List[Dict]:
    """Filtra definitions por 'all', IDs o substrings de nombre (coma-sep)."""
    sel = (selector or "all").strip()
    if sel.lower() in ("all", "*", ""):
        return defs
    tokens = [t.strip() for t in sel.split(",") if t.strip()]
    out = []
    for d in defs:
        did = str(d.get("id", ""))
        name = (d.get("name") or "").lower()
        for t in tokens:
            if t == did or (not t.isdigit() and t.lower() in name):
                out.append(d)
                break
    return out


def get_definition(client: AzdoClient, def_id) -> Dict:
    return client.get(f"{client.base}/definitions/{def_id}",
                      params={"api-version": "7.1", "$expand": "environments"})


def find_stage_env(definition: Dict, stage_name: str) -> Optional[Dict]:
    """Environment de la definición que corresponde al stage (default prod).

    Match en orden: nombre exacto → sufijo 'duction' (Production/Producción)
    → token de ambiente (_env_token: prod/stg/qa/dev) → substring.
    """
    target = (stage_name or "").lower()
    envs = definition.get("environments", [])
    for e in envs:
        if (e.get("name") or "").lower() == target:
            return e
    if target.endswith("duction"):
        for e in envs:
            if (e.get("name") or "").lower().endswith("duction"):
                return e
    for e in envs:
        if _env_token(e.get("name", "")) == "prod" and _env_token(stage_name) == "prod":
            return e
    for e in envs:
        if target and target in (e.get("name") or "").lower():
            return e
    return None


def find_effective_deployments(client: AzdoClient, def_id, env_id,
                               top: int = 10, limit: int = 2) -> List[Dict]:
    """Últimos deployments EFECTIVOS del stage (deploymentStatus != notDeployed),
    ordenados desc. Retorna hasta `limit` para soportar --prev-release."""
    data = client.get(
        f"{client.base}/deployments",
        params={"api-version": "7.1", "definitionId": def_id,
                "definitionEnvironmentId": env_id,
                "queryOrder": "descending", "$top": top})
    effective = []
    for d in data.get("value", []):
        if d.get("deploymentStatus") == "notDeployed":
            continue
        effective.append(d)
        if len(effective) >= limit:
            break
    return effective


def get_release(client: AzdoClient, release_id) -> Dict:
    return client.get(f"{client.base}/releases/{release_id}",
                      params={"api-version": "7.1"})


def find_release_env(release: Dict, def_env: Dict) -> Optional[Dict]:
    """Environment del release que corresponde al stage de la definición."""
    name = (def_env.get("name") or "").lower()
    def_env_id = def_env.get("id")
    for e in release.get("environments", []):
        if (e.get("name") or "").lower() == name:
            return e
        if def_env_id is not None and e.get("definitionEnvironmentId") == def_env_id:
            return e
    return None


def extract_stage_tasks(release_env: Dict) -> List[Dict]:
    """Tasks ejecutadas del ÚLTIMO attempt del stage.

    Retorna [{phase_id, task_id, name, log_url}] — mismo recorrido que
    scm_inspection_remediator.discover.
    """
    steps = release_env.get("deploySteps") or []
    step = max(steps, key=lambda s: s.get("attempt", 0)) if steps else {}
    tasks = []
    for ph in step.get("releaseDeployPhases", []):
        for job in ph.get("deploymentJobs", []):
            for t in job.get("tasks", []):
                if t.get("status") in ("skipped", "pending"):
                    continue
                tasks.append({
                    "phase_id": ph.get("id"),
                    "task_id": t.get("id"),
                    "name": t.get("name", "task"),
                    "log_url": t.get("logUrl"),
                })
    return tasks


def download_task_logs(client: AzdoClient, release_id, env_id,
                       tasks: List[Dict], pattern: str) -> Dict[str, str]:
    """Descarga logs de las tasks que matchean el regex (name, case-insens)."""
    rx = re.compile(pattern, re.IGNORECASE)
    logs: Dict[str, str] = {}
    for t in tasks:
        if not rx.search(t["name"]):
            continue
        url = t.get("log_url") or (
            f"{client.base}/releases/{release_id}/environments/{env_id}"
            f"/deployPhases/{t['phase_id']}/tasks/{t['task_id']}/logs")
        try:
            logs[t["name"]] = client.get(url, raw=True,
                                         params={"api-version": "7.1"})
        except SystemExit:
            raise
        except Exception as e:
            logs[t["name"]] = ""
            if console:
                console.print(f"  [yellow]⚠ log '{t['name']}': {e}[/]")
    return logs


# ═══════════════════════════════════════════════════════════════════════════════
# PARSERS — logs y manifiesto (puros → unit-testables)
# ═══════════════════════════════════════════════════════════════════════════════

_RE_APPLY_VERDICT = re.compile(
    r"^(\S+)\s+(created|configured|unchanged|deleted|pruned)\b")
_RE_MISSING_ANNOTATION = re.compile(
    r"resource (\S+) is missing the "
    r"kubectl\.kubernetes\.io/last-applied-configuration")


def parse_apply_log(text: str) -> Dict:
    """Parsea salida de `kubectl apply`.

    Retorna {
      verdicts: {resource_str: created|configured|unchanged|deleted|pruned},
      missing_annotation: {resources sin last-applied-configuration},
      errors: [líneas de error],
    }
    """
    verdicts: Dict[str, str] = {}
    missing: set = set()
    errors: List[str] = []
    for raw in text.splitlines():
        line = _LOG_TS.sub("", raw.rstrip("\r"))
        m = _RE_MISSING_ANNOTATION.search(line)
        if m:
            missing.add(m.group(1))
            continue
        m = _RE_APPLY_VERDICT.search(line)
        if m:
            verdicts[m.group(1)] = m.group(2)
            continue
        low = line.lower()
        if ("error" in low or "forbidden" in low or "refused" in low) \
                and not line.startswith((" ", "#")):
            errors.append(line.strip())
    return {"verdicts": verdicts, "missing_annotation": missing,
            "errors": errors}


_YAMLISH = re.compile(
    r"^\s*([A-Za-z_][\w.\-/]*\s*:\s*.*|-\s+.+|#.*|\s*)$")


def _try_doc(block: str) -> Optional[str]:
    """Devuelve el bloque si parsea como doc K8s (kind + metadata)."""
    try:
        obj = yaml.safe_load(block)
    except Exception:
        return None
    if isinstance(obj, dict) and obj.get("kind") \
            and isinstance(obj.get("metadata"), dict):
        return block
    return None


def extract_manifest_docs(text: str) -> List[str]:
    """Extrae documentos YAML de un log (p.ej. salida de `cat manifest.yaml`).

    Tolerante: quita prefijos de timestamp y líneas de control ##, separa por
    '---', y solo conserva bloques que parseen como dict K8s (kind +
    metadata). Si un bloque no parsea por líneas de ruido del log, reintenta
    conservando solo líneas con forma YAML (`key:`, `- item`, comentarios).
    """
    lines = [_LOG_TS.sub("", l.rstrip("\r")) for l in text.splitlines()]
    docs, cur = [], []

    def flush():
        block = "\n".join(cur).strip()
        cur.clear()
        if not block:
            return
        doc = _try_doc(block)
        if doc is None:
            clean = "\n".join(l for l in block.split("\n")
                              if _YAMLISH.match(l))
            doc = _try_doc(clean)
        if doc is not None:
            docs.append(doc)

    for line in lines:
        if line.strip() == "---":
            flush()
            continue
        if line.startswith(("##[", "##vso")):
            continue
        cur.append(line)
    flush()
    return docs


def manifest_key(kind: str, namespace: str, name: str) -> str:
    ns = namespace or ""
    return f"{(kind or '').lower()}/{ns}/{name or ''}"


def parse_manifest_objects(docs: List[str]) -> Dict[str, Dict]:
    """Parsea docs YAML → {key: {kind, namespace, name, canonical}}."""
    out: Dict[str, Dict] = {}
    for i, block in enumerate(docs):
        try:
            obj = yaml.safe_load(block)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        meta = obj.get("metadata") or {}
        kind = obj.get("kind", "")
        name = meta.get("name", "")
        ns = meta.get("namespace", "")
        if not kind or not name:
            continue
        key = manifest_key(kind, ns, name)
        try:
            canonical = yaml.dump(obj, sort_keys=True)
        except Exception:
            canonical = block
        out[key] = {"kind": kind, "namespace": ns, "name": name,
                    "doc_index": i, "canonical": canonical}
    return out


def apply_resource_key(resource: str) -> str:
    """'deployment.apps/foo' → 'deployment//foo' (kind//name, sin ns)."""
    res = resource.strip()
    kind, _, name = res.rpartition("/")
    short_kind = (kind.split(".")[0] if kind else "").lower()
    return f"{short_kind}//{name}"


def analyze_manifest(objects: Dict[str, Dict], apply: Dict,
                     prev_objects: Optional[Dict[str, Dict]] = None) -> List[Dict]:
    """Genera findings de drift a partir de manifiesto + salida apply.

    prev_objects (opcional): objetos del release efectivo anterior — habilita
    la señal 'configured con YAML idéntico = edición manual'.
    """
    findings: List[Dict] = []

    # Mapear verdicts apply → key manifiesto (apply no lleva namespace)
    verdict_by_key: Dict[str, Tuple[str, str]] = {}
    for res, verdict in apply.get("verdicts", {}).items():
        akey = apply_resource_key(res)
        match = next((k for k, o in objects.items()
                      if f"{o['kind'].lower()}//{o['name']}" == akey), None)
        verdict_by_key[match or f"?//{res}"] = (res, verdict)

    # Señal 1 (HIGH): recurso sin anotación last-applied-configuration
    for res in sorted(apply.get("missing_annotation", [])):
        findings.append({
            "severity": "HIGH", "rule": "NOT_MANAGED_BY_APPLY",
            "object": res,
            "detail": "Existe en el cluster sin anotación "
                      "last-applied-configuration — creado fuera de "
                      "kubectl apply (manipulación directa u otra vía).",
        })

    # Señal 3 (MEDIUM): objetos del manifiesto sin verdict en apply
    for key, obj in objects.items():
        if key not in verdict_by_key:
            findings.append({
                "severity": "MEDIUM", "rule": "NOT_APPLIED",
                "object": f"{obj['kind']}/{obj['name']}",
                "detail": "Presente en 'show manifest' pero sin línea de "
                          "salida en 'kubectl apply'.",
            })

    # Verdicts recorridos
    for key, (res, verdict) in verdict_by_key.items():
        if key not in objects:
            findings.append({
                "severity": "LOW", "rule": "APPLIED_NOT_IN_MANIFEST",
                "object": res,
                "detail": "El apply procesó un recurso que no se vio en "
                          "'show manifest' (¿otro doc del archivo?).",
            })
            continue
        obj = objects[key]
        if verdict == "created":
            findings.append({
                "severity": "INFO", "rule": "CREATED",
                "object": res,
                "detail": "Recurso creado por este apply (nuevo o recreado).",
            })
        elif verdict == "configured":
            if prev_objects is not None and key in prev_objects:
                if prev_objects[key]["canonical"] == obj["canonical"]:
                    findings.append({
                        "severity": "HIGH", "rule": "EXTERNAL_MODIFICATION",
                        "object": res,
                        "detail": "Manifiesto idéntico al release efectivo "
                                  "anterior pero el apply tuvo que "
                                  "RECONFIGURAR el objeto — el estado vivo "
                                  "difería del YAML (edición manual "
                                  "probable).",
                    })
                else:
                    findings.append({
                        "severity": "INFO", "rule": "EXPECTED_CONFIG",
                        "object": res,
                        "detail": "Reconfigurado — el manifiesto cambió "
                                  "respecto al release anterior (cambio "
                                  "vía pipeline).",
                    })
            else:
                findings.append({
                    "severity": "INFO", "rule": "CONFIGURED",
                    "object": res,
                    "detail": "Reconfigurado por el apply (sin release "
                              "previo para distinguir causa — use "
                              "--prev-release).",
                })

    for err in apply.get("errors", [])[:10]:
        findings.append({
            "severity": "MEDIUM", "rule": "APPLY_ERROR",
            "object": "",
            "detail": err[:200],
        })
    return findings


# ═══════════════════════════════════════════════════════════════════════════════
# DIFF — definición actual vs snapshot del release
# ═══════════════════════════════════════════════════════════════════════════════

def _env_workflow_tasks(env: Dict) -> List[Dict]:
    """workflowTasks del env — def actual (deployPhases) o snapshot del
    release (releaseDefinitionEnvironment.deployPhases /
    deployPhasesSnapshot)."""
    tasks: List[Dict] = []
    for phase in env.get("deployPhases", []):
        tasks.extend(phase.get("workflowTasks", []))
    if not tasks:
        inner = env.get("releaseDefinitionEnvironment", {})
        for phase in inner.get("deployPhases", []):
            tasks.extend(phase.get("workflowTasks", []))
    if not tasks:
        for phase in env.get("deployPhasesSnapshot", []):
            tasks.extend(phase.get("workflowTasks", []))
    return tasks


def diff_env_def_vs_release(def_env: Dict, release_env: Dict) -> Dict:
    """Diff definición-actual vs snapshot-del-release para el stage:
    tasks añadidas/eliminadas, versión, inputs y variables."""
    cur_tasks = _env_workflow_tasks(def_env)
    snap_tasks = _env_workflow_tasks(release_env)

    def _idx(tasks: List[Dict]) -> Dict:
        return {t.get("taskId") or t.get("name", ""): t for t in tasks}

    cur_idx, snap_idx = _idx(cur_tasks), _idx(snap_tasks)
    cur_ids, snap_ids = set(cur_idx), set(snap_idx)

    added = [cur_idx[k].get("name", "?") for k in sorted(cur_ids - snap_ids)]
    removed = [snap_idx[k].get("name", "?") for k in sorted(snap_ids - cur_ids)]
    version_changed, inputs_changed = [], []
    for k in sorted(cur_ids & snap_ids):
        ct, st = cur_idx[k], snap_idx[k]
        name = ct.get("name", "?")
        if ct.get("version", "") != st.get("version", ""):
            version_changed.append(
                f"{name}: {st.get('version','')} → {ct.get('version','')}")
        cin = ct.get("inputs") or {}
        sin = st.get("inputs") or {}
        diff_keys = [kk for kk in set(cin) | set(sin)
                     if cin.get(kk) != sin.get(kk)]
        for kk in sorted(diff_keys):
            inputs_changed.append({
                "task": name, "input": kk,
                "snapshot": str(sin.get(kk))[:120],
                "current": str(cin.get(kk))[:120],
            })

    cur_vars = set((def_env.get("variables") or {}).keys())
    snap_env_src = (release_env.get("releaseDefinitionEnvironment")
                    or release_env)
    snap_vars = set((snap_env_src.get("variables") or {}).keys())

    return {
        "tasks_added": added,
        "tasks_removed": removed,
        "tasks_version_changed": version_changed,
        "task_inputs_changed": inputs_changed,
        "vars_added": sorted(cur_vars - snap_vars),
        "vars_removed": sorted(snap_vars - cur_vars),
        "tasks_available": bool(cur_tasks or snap_tasks),
    }


def diff_has_changes(d: Dict) -> bool:
    return any(d[k] for k in ("tasks_added", "tasks_removed",
                              "tasks_version_changed", "task_inputs_changed",
                              "vars_added", "vars_removed"))


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS POR PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_definition(client: AzdoClient, summary: Dict, args,
                       pattern: str) -> Dict:
    """Pipeline completo para una release definition."""
    result: Dict = {
        "definition_id": summary.get("id"),
        "definition_name": summary.get("name", "?"),
        "stage": args.stage_name,
        "release_id": None, "release_name": "", "release_created": "",
        "deployment_status": "",
        "task_logs": [], "manifest_objects": 0,
        "apply_counts": {v: 0 for v in _APPLY_VERDICTS},
        "def_release_diff": None,
        "findings": [],
        "error": "",
    }
    try:
        definition = get_definition(client, summary["id"])
    except SystemExit:
        raise
    except Exception as e:
        result["error"] = f"definition: {e}"
        return result

    def_env = find_stage_env(definition, args.stage_name)
    if not def_env:
        result["error"] = f"stage '{args.stage_name}' no existe en la definición"
        return result

    limit = 2 if args.prev_release else 1
    try:
        effective = find_effective_deployments(
            client, summary["id"], def_env["id"],
            top=args.top_deployments, limit=limit)
    except Exception as e:
        result["error"] = f"deployments: {e}"
        return result
    if not effective:
        result["error"] = "sin deploy efectivo en el stage"
        return result

    def _analyze_release(dep: Dict, want_logs: bool) -> Dict:
        rid = dep.get("release", {}).get("id")
        rel = get_release(client, rid)
        env = find_release_env(rel, def_env)
        tasks = extract_stage_tasks(env) if env else []
        logs = download_task_logs(client, rid, env.get("id"), tasks, pattern) \
            if want_logs and env else {}
        return {"release": rel, "env": env, "tasks": tasks, "logs": logs}

    try:
        latest = _analyze_release(effective[0], want_logs=True)
    except SystemExit:
        raise
    except Exception as e:
        result["error"] = f"release: {e}"
        return result

    rel, rel_env, logs = latest["release"], latest["env"], latest["logs"]
    result["release_id"] = rel.get("id")
    result["release_name"] = rel.get("name", "")
    result["release_created"] = rel.get("createdOn", "")
    result["deployment_status"] = effective[0].get("deploymentStatus", "")
    result["task_logs"] = sorted(logs.keys())

    # diff definición vs snapshot del release
    if rel_env:
        result["def_release_diff"] = diff_env_def_vs_release(def_env, rel_env)
        if diff_has_changes(result["def_release_diff"]):
            result["findings"].append({
                "severity": "MEDIUM", "rule": "DEF_RELEASE_DRIFT",
                "object": "",
                "detail": "La definición difiere del snapshot del último "
                          "release efectivo (tasks/inputs/variables).",
            })

    # manifiesto + apply
    manifest_docs: List[str] = []
    apply = {"verdicts": {}, "missing_annotation": set(), "errors": []}
    for name, text in logs.items():
        low = name.lower()
        if "manifest" in low and "apply" not in low:
            manifest_docs.extend(extract_manifest_docs(text))
        elif "apply" in low:
            parsed = parse_apply_log(text)
            apply["verdicts"].update(parsed["verdicts"])
            apply["missing_annotation"] |= parsed["missing_annotation"]
            apply["errors"].extend(parsed["errors"])

    objects = parse_manifest_objects(manifest_docs)
    result["manifest_objects"] = len(objects)
    for v in apply["verdicts"].values():
        if v in result["apply_counts"]:
            result["apply_counts"][v] += 1

    prev_objects = None
    if args.prev_release and len(effective) >= 2:
        try:
            prev = _analyze_release(effective[1], want_logs=True)
            prev_docs: List[str] = []
            for name, text in prev["logs"].items():
                if "manifest" in name.lower() and "apply" not in name.lower():
                    prev_docs.extend(extract_manifest_docs(text))
            prev_objects = parse_manifest_objects(prev_docs)
            result["prev_release_id"] = prev["release"].get("id")
            result["prev_release_name"] = prev["release"].get("name", "")
        except Exception as e:
            result["prev_release_error"] = str(e)

    result["findings"].extend(
        analyze_manifest(objects, apply, prev_objects))
    result["severity"] = min(
        (f["severity"] for f in result["findings"]),
        key=lambda s: SEV_ORDER.get(s, 9), default="NONE")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE + EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def _print_finding(f: Dict):
    sev = f["severity"]
    if console:
        console.print(f"    [{SEV_STYLE[sev]}]{sev:<8}[/] "
                      f"[bold]{f['rule']}[/] {f['object']}")
        console.print(f"      [dim]{f['detail']}[/]")
    else:
        print(f"    {sev:<8} {f['rule']} {f['object']} — {f['detail']}")


def print_result(r: Dict):
    head = (f"[bold]{r['definition_name']}[/]  (def {r['definition_id']})"
            if console else f"{r['definition_name']} (def {r['definition_id']})")
    if console:
        console.print(Panel(head, expand=False))
    else:
        print(f"\n=== {head} ===")

    if r["error"]:
        msg = f"  [yellow]⚠ {r['error']}[/]" if console else f"  ! {r['error']}"
        (console.print if console else print)(msg)
        return

    info = (f"  Release {r['release_name']} (id {r['release_id']}) "
            f"— {r['deployment_status']} — {r['release_created'][:16]}")
    (console.print if console else print)(info)
    if r.get("prev_release_id"):
        (console.print if console else print)(
            f"  Prev release {r.get('prev_release_name','')} "
            f"(id {r['prev_release_id']})")
    (console.print if console else print)(
        f"  Logs analizados: {', '.join(r['task_logs']) or '(ninguna task '
        'matcheó el patrón)'}")

    d = r.get("def_release_diff")
    if d and diff_has_changes(d):
        (console.print if console else print)("  Def actual vs snapshot:")
        for label, key in (("tasks añadidas", "tasks_added"),
                           ("tasks eliminadas", "tasks_removed"),
                           ("versión task", "tasks_version_changed"),
                           ("vars añadidas", "vars_added"),
                           ("vars eliminadas", "vars_removed")):
            if d[key]:
                (console.print if console else print)(
                    f"    {label}: {', '.join(map(str, d[key]))}")
        for ic in d["task_inputs_changed"]:
            (console.print if console else print)(
                f"    input '{ic['task']}.{ic['input']}': "
                f"{ic['snapshot']!r} → {ic['current']!r}")

    if r["manifest_objects"] or r["task_logs"]:
        counts = r["apply_counts"]
        (console.print if console else print)(
            f"  Manifiesto: {r['manifest_objects']} objeto(s) — apply: "
            f"{counts['created']} created, {counts['configured']} configured, "
            f"{counts['unchanged']} unchanged")

    if r["findings"]:
        for f in sorted(r["findings"],
                        key=lambda x: SEV_ORDER.get(x["severity"], 9)):
            _print_finding(f)
    else:
        (console.print if console else print)(
            "  [green]✓ Sin findings[/]" if console else "  ✓ Sin findings")


def print_summary(results: List[Dict], min_sev: str):
    rows = [r for r in results
            if SEV_ORDER.get(r.get("severity", "NONE"), 9) <= SEV_ORDER[min_sev]]
    if console:
        t = Table(title="Resumen — Manifest Drift Audit")
        for col in ("Pipeline", "Release", "Objetos", "Configured",
                    "Missing-Ann", "Def-Diff", "Severidad"):
            t.add_column(col)
        for r in rows:
            d = r.get("def_release_diff") or {}
            t.add_row(
                str(r["definition_name"]),
                str(r.get("release_name", "")),
                str(r["manifest_objects"]),
                str(r["apply_counts"]["configured"]),
                str(_missing_ann_count(r)),
                "Sí" if diff_has_changes(d) else "—",
                f"[{SEV_STYLE.get(r.get('severity','NONE'),'')}]"
                f"{r.get('severity','NONE')}[/]",
            )
        console.print(t)
    else:
        for r in rows:
            print(f"{r['definition_name']} | {r.get('release_name','')} | "
                  f"sev={r.get('severity','NONE')}")


def _missing_ann_count(r: Dict) -> int:
    return sum(1 for f in r.get("findings", [])
               if f["rule"] == "NOT_MANAGED_BY_APPLY")


def export_results(results: List[Dict], fmt: str) -> List[Path]:
    out_dir = resolve_outcome_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths: List[Path] = []

    def _clean(r: Dict) -> Dict:
        rr = dict(r)
        return rr

    if fmt in ("json", "both"):
        p = out_dir / f"manifest_drift_{ts}.json"
        p.write_text(json.dumps([_clean(r) for r in results],
                                indent=2, ensure_ascii=False, default=str),
                     encoding="utf-8")
        paths.append(p)
    if fmt in ("csv", "both"):
        import csv as _csv
        p = out_dir / f"manifest_drift_{ts}.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = _csv.writer(f, delimiter=";")
            w.writerow(["DEFINITION_ID", "PIPELINE", "RELEASE_ID", "RELEASE",
                        "DEPLOY_STATUS", "SEVERITY", "RULE", "OBJECT",
                        "DETAIL", "ERROR"])
            for r in results:
                if not r["findings"]:
                    w.writerow([r["definition_id"], r["definition_name"],
                                r.get("release_id"), r.get("release_name"),
                                r.get("deployment_status"),
                                r.get("severity", "NONE"), "", "", "",
                                r.get("error", "")])
                for f_ in r["findings"]:
                    w.writerow([r["definition_id"], r["definition_name"],
                                r.get("release_id"), r.get("release_name"),
                                r.get("deployment_status"),
                                f_["severity"], f_["rule"], f_["object"],
                                f_["detail"], ""])
        paths.append(p)
    return paths


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    args = get_args()
    org, project, pat = get_azdo_params(args)
    client = AzdoClient(org, project, pat)

    try:
        pattern = re.compile(args.task_patterns, re.IGNORECASE)
    except re.error as e:
        print(f"ERROR: --task-patterns inválido: {e}")
        return 1

    if console:
        console.print(f"[bold cyan]Auditoría Manifest Drift[/] — {org}/{project} "
                      f"— stage '{args.stage_name}'"
                      + (" — prev-release ON" if args.prev_release else ""))

    defs = list_release_definitions(client, args.debug)
    selected = select_definitions(defs, args.definition_ids)
    if not selected:
        (console.print if console else print)(
            f"Sin definitions que matcheen '{args.definition_ids}'.")
        return 1
    if console:
        console.print(f"[dim]{len(selected)} pipeline(s) a analizar[/]")

    results: List[Dict] = []
    max_w = max(1, args.threads)
    with ThreadPoolExecutor(max_workers=max_w) as ex:
        futs = {ex.submit(analyze_definition, client, d, args,
                          args.task_patterns): d for d in selected}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            print_result(r)

    results.sort(key=lambda r: SEV_ORDER.get(r.get("severity", "NONE"), 9))
    print_summary(results, args.severity)

    if args.output:
        paths = export_results(results, args.output)
        for p in paths:
            (console.print if console else print)(f"Exportado: {p}")

    worst = min((SEV_ORDER.get(r.get("severity", "NONE"), 9) for r in results),
                default=9)
    return 2 if worst <= SEV_ORDER["HIGH"] else 0


if __name__ == "__main__":
    sys.exit(main())
