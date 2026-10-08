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
import html as _html
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

__version__ = "1.0.5"

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
    from rich import box
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
_APPLY_VERDICTS = ("created", "configured", "unchanged", "deleted", "pruned",
                   "replaced")


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
    p.add_argument("--output",
                   choices=["json", "csv", "html", "both", "all"], default="",
                   help="Exportar resultados a outcome/ (both=json+csv, "
                        "all=json+csv+html)")
    p.add_argument("--threads", type=int, default=4,
                   help="Pipelines en paralelo (default: 4)")
    p.add_argument("--severity", choices=list(SEV_ORDER), default="NONE",
                   help="Solo mostrar pipelines con severidad >= N en el resumen")
    p.add_argument("--show-skipped", action="store_true",
                   help="Muestra panel por pipeline omitido (sin stage o sin "
                        "deploy efectivo); por defecto se resumen en conteos")
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
    ordenados desc. Deduplica por release.id (la API devuelve una entrada por
    attempt — el mismo release puede aparecer N veces).
    Retorna hasta `limit` releases distintos (soporta --prev-release)."""
    data = client.get(
        f"{client.base}/deployments",
        params={"api-version": "7.1", "definitionId": def_id,
                "definitionEnvironmentId": env_id,
                "queryOrder": "descending", "$top": top})
    effective, seen = [], set()
    for d in data.get("value", []):
        if d.get("deploymentStatus") == "notDeployed":
            continue
        rid = d.get("release", {}).get("id")
        if rid in seen:
            continue
        seen.add(rid)
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


_K8S_APPLY_CMDS = {"apply", "create", "replace", "patch"}
_K8S_SCRIPT_RX = re.compile(
    r"\bkubectl\s+(apply|create|replace|patch)\b", re.IGNORECASE)


def applyish_task_names(workflow_tasks: List[Dict]) -> set:
    """Nombres de workflowTasks que ejecutan kubectl apply/create/replace/patch
    aunque su displayName no lo indique: tasks Kubernetes@1/Kubectl@1 con
    inputs.command=apply|create|…, o scripts inline que corren kubectl."""
    names = set()
    for t in workflow_tasks:
        inputs = t.get("inputs") or {}
        cmd = (inputs.get("command") or "").strip().lower()
        if cmd in _K8S_APPLY_CMDS:
            if t.get("name"):
                names.add(t["name"])
            continue
        for k in ("inlineScript", "script", "targetScript", "scriptContents"):
            v = inputs.get(k)
            if isinstance(v, str) and _K8S_SCRIPT_RX.search(v):
                if t.get("name"):
                    names.add(t["name"])
                break
    return names


def download_task_logs(client: AzdoClient, release_id, env_id,
                       tasks: List[Dict], pattern: str,
                       apply_names_extra: Optional[set] = None
                       ) -> Tuple[Dict[str, str], set]:
    """Descarga logs de las tasks que matchean el regex (name, case-insens)
    o que están en apply_names_extra (tasks apply-typed detectados por sus
    inputs). Retorna ({nombre: log}, {nombres de tasks de apply})."""
    rx = re.compile(pattern, re.IGNORECASE)
    extra = {n.lower() for n in (apply_names_extra or set())}
    logs: Dict[str, str] = {}
    apply_names: set = set()
    for t in tasks:
        name = t["name"]
        if not rx.search(name) and name.lower() not in extra \
                and "manifest" not in name.lower():
            continue
        if "apply" in name.lower() or name.lower() in extra:
            apply_names.add(name)
        url = t.get("log_url") or (
            f"{client.base}/releases/{release_id}/environments/{env_id}"
            f"/deployPhases/{t['phase_id']}/tasks/{t['task_id']}/logs")
        try:
            logs[name] = client.get(url, raw=True,
                                    params={"api-version": "7.1"})
        except SystemExit:
            raise
        except Exception as e:
            logs[name] = ""
            if console:
                console.print(f"  [yellow]⚠ log '{name}': {e}[/]")
    return logs, apply_names


# ═══════════════════════════════════════════════════════════════════════════════
# PARSERS — logs y manifiesto (puros → unit-testables)
# ═══════════════════════════════════════════════════════════════════════════════

_RE_APPLY_VERDICT = re.compile(
    r"^(\S+)\s+(created|configured|unchanged|deleted|pruned|replaced)\b"
    r"(?:\s*\((?:server )?dry run\))?", re.IGNORECASE)
# kubectl < 1.18 imprime: deployment.apps "web" configured
_RE_APPLY_VERDICT_OLD = re.compile(
    r'^([A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)\s+"([^"]+)"\s+'
    r"(created|configured|unchanged|deleted|pruned|replaced)\b"
    r"(?:\s*\((?:server )?dry run\))?", re.IGNORECASE)
_RE_MISSING_ANNOTATION = re.compile(
    r"resource (\S+) is missing the "
    r"kubectl\.kubernetes\.io/last-applied-configuration")
# kubectl < 1.13: warning genérico sin nombre de recurso
_RE_OLD_APPLY_WARN = re.compile(
    r"apply should be used on resource created by", re.IGNORECASE)


def parse_apply_log(text: str) -> Dict:
    """Parsea salida de `kubectl apply`.

    Soporta formato moderno (`kind/name verdict`) y antiguo
    (`kind "name" verdict`, kubectl < 1.18), más sufijos `(dry run)`.

    Retorna {
      verdicts: {resource_str: created|configured|unchanged|deleted|pruned|
                 replaced},
      missing_annotation: {resources sin last-applied-configuration},
      old_warn: warning genérico de kubectl antiguo (sin recurso),
      errors: [líneas de error],
    }
    """
    verdicts: Dict[str, str] = {}
    missing: set = set()
    errors: List[str] = []
    old_warn = False
    for raw in text.splitlines():
        line = _LOG_TS.sub("", raw.rstrip("\r"))
        m = _RE_MISSING_ANNOTATION.search(line)
        if m:
            missing.add(m.group(1))
            continue
        m = _RE_APPLY_VERDICT_OLD.match(line.strip())
        if m:
            verdicts[f"{m.group(1)}/{m.group(2)}"] = m.group(3).lower()
            continue
        m = _RE_APPLY_VERDICT.search(line)
        if m:
            verdicts[m.group(1)] = m.group(2).lower()
            continue
        if _RE_OLD_APPLY_WARN.search(line):
            old_warn = True
            continue
        low = line.lower()
        if ("error" in low or "forbidden" in low or "refused" in low) \
                and not line.startswith((" ", "#")):
            errors.append(line.strip())
    return {"verdicts": verdicts, "missing_annotation": missing,
            "old_warn": old_warn, "errors": errors}


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


# Tokens sin renderizar en el archivo mostrado por 'show manifest'
# (#{var}# de Replace Tokens, $(var) de AzDO, {{var}} de Helm/Jinja)
_PLACEHOLDER = re.compile(r"#\{[^}]*\}|\$\([^)]*\)|\{\{[^}]+\}\}")


def map_verdicts(objects: Dict[str, Dict],
                 verdicts: Dict[str, str]) -> Dict[str, Tuple[str, str]]:
    """Mapea verdicts apply → key manifiesto (apply no lleva namespace).
    Recursos sin objeto manifiesto quedan bajo la clave '?//<res>'."""
    out: Dict[str, Tuple[str, str]] = {}
    for res, verdict in verdicts.items():
        akey = apply_resource_key(res)
        match = next((k for k, o in objects.items()
                      if f"{o['kind'].lower()}//{o['name']}" == akey), None)
        out[match or f"?//{res}"] = (res, verdict)
    return out


def analyze_manifest(objects: Dict[str, Dict], apply: Dict,
                     prev_objects: Optional[Dict[str, Dict]] = None) -> List[Dict]:
    """Genera findings de drift a partir de manifiesto + salida apply.

    apply acepta además: 'log_names' (logs apply descargados), 'empty_logs'
    (logs apply vacíos/no descargables) y 'old_warn' (warning genérico de
    kubectl < 1.13) para diagnosticar logs sin verdicts.

    prev_objects (opcional): objetos del release efectivo anterior — habilita
    la señal 'configured con YAML idéntico = edición manual'.

    Los findings ligados a un objeto llevan 'key' = clave del objeto en el
    manifiesto, o '?//<res>' para recursos solo vistos en el apply.
    """
    findings: List[Dict] = []

    # Mapear verdicts apply → key manifiesto (apply no lleva namespace)
    verdict_by_key = map_verdicts(objects, apply.get("verdicts", {}))

    # Diagnóstico de logs apply sin verdicts ni vacíos
    apply_logs = apply.get("log_names", [])
    empty_apply = set(apply.get("empty_logs", [])) & set(apply_logs)
    if apply_logs and not apply.get("verdicts") \
            and len(empty_apply) < len(apply_logs):
        findings.append({
            "severity": "MEDIUM", "rule": "APPLY_NO_VERDICTS",
            "object": "",
            "detail": "El log de apply no contiene líneas de verdict "
                      "reconocibles (created/configured/unchanged) — formato "
                      "no soportado o apply en modo silencioso.",
        })
    for name in apply.get("empty_logs", []):
        findings.append({
            "severity": "INFO", "rule": "EMPTY_LOG",
            "object": "",
            "detail": f"Log de '{name}' vacío o no descargable.",
        })
    if apply.get("old_warn"):
        findings.append({
            "severity": "LOW", "rule": "OLD_APPLY_WARNING",
            "object": "",
            "detail": "kubectl antiguo emitió el warning genérico 'apply "
                      "should be used on resource created by either create "
                      "--save-config or apply' — hay recursos no gestionados "
                      "por apply, pero la versión no indica cuáles.",
        })

    # Señal 1 (HIGH): recurso sin anotación last-applied-configuration
    for res in sorted(apply.get("missing_annotation", [])):
        vk = next((k for k, (rr, _) in verdict_by_key.items() if rr == res),
                  None)
        f = {
            "severity": "HIGH", "rule": "NOT_MANAGED_BY_APPLY",
            "object": res,
            "detail": "Existe en el cluster sin anotación "
                      "last-applied-configuration — creado fuera de "
                      "kubectl apply (manipulación directa u otra vía).",
        }
        if vk:
            f["key"] = vk
        findings.append(f)

    # Señal 3 (MEDIUM): objetos del manifiesto sin verdict en apply
    for key, obj in objects.items():
        if _PLACEHOLDER.search(obj["name"]):
            findings.append({
                "severity": "INFO", "rule": "UNRENDERED_NAME",
                "object": f"{obj['kind']}/{obj['name']}", "key": key,
                "detail": "El nombre contiene placeholders sin renderizar — "
                          "'show manifest' mostró el template antes de la "
                          "sustitución de tokens.",
            })
            continue
        if key not in verdict_by_key:
            findings.append({
                "severity": "MEDIUM", "rule": "NOT_APPLIED",
                "object": f"{obj['kind']}/{obj['name']}", "key": key,
                "detail": "Presente en 'show manifest' pero sin línea de "
                          "salida en 'kubectl apply'.",
            })

    # Verdicts recorridos
    for key, (res, verdict) in verdict_by_key.items():
        if key not in objects:
            findings.append({
                "severity": "LOW", "rule": "APPLIED_NOT_IN_MANIFEST",
                "object": res, "key": key,
                "detail": "El apply procesó un recurso que no se vio en "
                          "'show manifest' (¿otro doc del archivo?).",
            })
            continue
        obj = objects[key]
        if verdict == "created":
            findings.append({
                "severity": "INFO", "rule": "CREATED",
                "object": res, "key": key,
                "detail": "Recurso creado por este apply (nuevo o recreado).",
            })
        elif verdict == "configured":
            if prev_objects is not None and key in prev_objects:
                if prev_objects[key]["canonical"] == obj["canonical"]:
                    findings.append({
                        "severity": "HIGH", "rule": "EXTERNAL_MODIFICATION",
                        "object": res, "key": key,
                        "detail": "Manifiesto idéntico al release efectivo "
                                  "anterior pero el apply tuvo que "
                                  "RECONFIGURAR el objeto — el estado vivo "
                                  "difería del YAML (edición manual "
                                  "probable).",
                    })
                else:
                    findings.append({
                        "severity": "INFO", "rule": "EXPECTED_CONFIG",
                        "object": res, "key": key,
                        "detail": "Reconfigurado — el manifiesto cambió "
                                  "respecto al release anterior (cambio "
                                  "vía pipeline).",
                    })
            else:
                findings.append({
                    "severity": "INFO", "rule": "CONFIGURED",
                    "object": res, "key": key,
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


_FALSY_INPUT = {"", "false", "0", "no", "none"}


def _inputs_equiv(a, b) -> bool:
    """True si los inputs son equivalentes. Un input ausente (None) equivale
    a un valor falsy explícito ('false', '', '0') — AzDO materializa defaults
    falsy al re-guardar la definición, generando diffs espurios."""
    if a == b:
        return True
    if (a is None and str(b).strip().lower() in _FALSY_INPUT) or \
            (b is None and str(a).strip().lower() in _FALSY_INPUT):
        return True
    return False


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
                     if not _inputs_equiv(cin.get(kk), sin.get(kk))]
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
    return any(d.get(k) for k in ("tasks_added", "tasks_removed",
                                  "tasks_version_changed",
                                  "task_inputs_changed",
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
        "objects": {}, "apply_verdicts": {},
        "manifest_log_names": [], "apply_log_names": [],
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
        extra = applyish_task_names(_env_workflow_tasks(env)) if env else set()
        logs, apply_names = (
            download_task_logs(client, rid, env.get("id"), tasks, pattern,
                               apply_names_extra=extra)
            if want_logs and env else ({}, set()))
        return {"release": rel, "env": env, "tasks": tasks,
                "logs": logs, "apply_names": apply_names}

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
    if not logs:
        result["findings"].append({
            "severity": "INFO", "rule": "NO_MANIFEST_TASKS", "object": "",
            "detail": "Ninguna task del stage produjo log de manifiesto/apply "
                      "(¿el pipeline no usa las 3 tasks de manifiesto?).",
        })

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
    manifest_log_names: List[str] = []
    apply = {"verdicts": {}, "missing_annotation": set(), "errors": [],
             "old_warn": False, "log_names": [], "empty_logs": []}
    apply_names = latest.get("apply_names", set())
    for name, text in logs.items():
        if name in apply_names:
            apply["log_names"].append(name)
            if not (text or "").strip():
                apply["empty_logs"].append(name)
                continue
            parsed = parse_apply_log(text)
            apply["verdicts"].update(parsed["verdicts"])
            apply["missing_annotation"] |= parsed["missing_annotation"]
            apply["errors"].extend(parsed["errors"])
            apply["old_warn"] = apply["old_warn"] or parsed["old_warn"]
        elif "manifest" in name.lower():
            manifest_log_names.append(name)
            if not (text or "").strip():
                apply["empty_logs"].append(name)
                continue
            manifest_docs.extend(extract_manifest_docs(text))

    result["manifest_log_names"] = manifest_log_names
    result["apply_log_names"] = list(apply["log_names"])
    objects = parse_manifest_objects(manifest_docs)
    if manifest_log_names and not objects:
        result["findings"].append({
            "severity": "INFO", "rule": "MANIFEST_NO_DOCS", "object": "",
            "detail": "Los logs de manifiesto no contenían documentos YAML "
                      "K8s reconocibles (kind + metadata).",
        })
    result["manifest_objects"] = len(objects)
    result["objects"] = {k: {"kind": o["kind"], "namespace": o["namespace"],
                             "name": o["name"]} for k, o in objects.items()}
    result["apply_verdicts"] = dict(apply["verdicts"])
    for v in apply["verdicts"].values():
        if v in result["apply_counts"]:
            result["apply_counts"][v] += 1

    prev_objects = None
    if args.prev_release and len(effective) >= 2:
        try:
            prev = _analyze_release(effective[1], want_logs=True)
            prev_docs: List[str] = []
            prev_apply_names = prev.get("apply_names", set())
            for name, text in prev["logs"].items():
                if name not in prev_apply_names \
                        and "manifest" in name.lower():
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


def build_object_rows(r: Dict) -> Tuple[List[Dict], List[Dict]]:
    """Filas para la tabla objeto×apply del pipeline + findings sin objeto.

    Cada fila: objeto, ns, en_manifiesto (✓/✗), verdict apply, severidad
    (la peor de sus findings) y reglas. Findings sin 'key' (DEF_RELEASE_DRIFT,
    APPLY_ERROR, EMPTY_LOG, …) van en la segunda lista.
    """
    objects = r.get("objects") or {}
    vmap = map_verdicts(objects, r.get("apply_verdicts") or {})
    fby_key: Dict[str, List[Dict]] = {}
    other: List[Dict] = []
    for f in r.get("findings", []):
        if f.get("key"):
            fby_key.setdefault(f["key"], []).append(f)
        else:
            other.append(f)

    def _row(key, obj_name, ns, in_manifest, verdict):
        fs = fby_key.get(key, [])
        sev = min((f["severity"] for f in fs),
                  key=lambda s: SEV_ORDER.get(s, 9), default="")
        return {"object": obj_name, "ns": ns, "in_manifest": in_manifest,
                "verdict": verdict or "—", "severity": sev,
                "rules": ", ".join(sorted({f["rule"] for f in fs}))}

    rows = []
    for key, obj in objects.items():
        _res, verdict = vmap.get(key, ("", ""))
        rows.append(_row(key, f"{obj['kind']}/{obj['name']}",
                         obj.get("namespace") or "—", "✓", verdict))
    for key, (res, verdict) in vmap.items():
        if key.startswith("?//"):
            rows.append(_row(key, res, "—", "✗", verdict))
    rows.sort(key=lambda x: (SEV_ORDER.get(x["severity"], 99)
                             if x["severity"] else 99, x["object"]))
    return rows, other


def consistency_summary(r: Dict) -> Dict:
    """Verificación explícita de consistencia entre las tasks de manifiesto
    y las de apply del último release efectivo.

    Retorna {manifest_logs, apply_logs, objects, verdicts,
             missing_in_apply, applied_not_in_manifest}.
    """
    rows, _ = build_object_rows(r)
    return {
        "manifest_logs": r.get("manifest_log_names") or [],
        "apply_logs": r.get("apply_log_names") or [],
        "objects": r.get("manifest_objects", 0),
        "verdicts": len(r.get("apply_verdicts") or {}),
        "missing_in_apply": [
            x["object"] for x in rows
            if x["in_manifest"] == "✓" and x["verdict"] == "—"
            and "UNRENDERED_NAME" not in x["rules"]],
        "applied_not_in_manifest": [
            x["object"] for x in rows if x["in_manifest"] == "✗"],
    }


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

    # ── Consistencia explícita de las 3 tasks (análisis principal) ────
    cs = consistency_summary(r)
    manif_txt = (f"{', '.join(cs['manifest_logs'])} → "
                 f"{cs['objects']} objeto(s)"
                 if cs["manifest_logs"] else "✗ sin task de manifiesto")
    apply_txt = (f"{', '.join(cs['apply_logs'])} → "
                 f"{cs['verdicts']} verdict(s)"
                 if cs["apply_logs"] else "✗ sin task de apply")
    if console:
        console.print("  [bold]Consistencia manifiesto ↔ apply:[/]")
        console.print(f"    manifiesto: {manif_txt}")
        console.print(f"    apply:      {apply_txt}")
        for label, items, style in (
                ("En manifiesto SIN línea en apply",
                 cs["missing_in_apply"], "yellow"),
                ("Aplicado sin aparecer en manifiesto",
                 cs["applied_not_in_manifest"], "cyan")):
            if items:
                console.print(f"    [{style}]► {label}: "
                              f"{', '.join(items)}[/]")
            else:
                console.print(f"    [green]✓ {label}: ninguno[/]")
    else:
        print("  Consistencia manifiesto <-> apply:")
        print(f"    manifiesto: {manif_txt}")
        print(f"    apply:      {apply_txt}")
        print(f"    En manifiesto SIN linea en apply: "
              f"{', '.join(cs['missing_in_apply']) or 'ninguno'}")
        print(f"    Aplicado sin aparecer en manifiesto: "
              f"{', '.join(cs['applied_not_in_manifest']) or 'ninguno'}")

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
        verdict_line = ", ".join(
            f"{counts.get(v, 0)} {v}" for v in _APPLY_VERDICTS
            if counts.get(v) or v in ("created", "configured", "unchanged"))
        (console.print if console else print)(
            f"  Manifiesto: {r['manifest_objects']} objeto(s) — apply: "
            f"{verdict_line}")

    rows, other_findings = build_object_rows(r)
    if rows:
        if console:
            t = Table(box=box.SIMPLE, expand=False)
            for col in ("Objeto", "NS", "Manif.", "Apply",
                        "Severidad", "Regla"):
                t.add_column(col)
            for row in rows:
                sev = row["severity"]
                sev_cell = (f"[{SEV_STYLE[sev]}]{sev}[/]"
                            if sev else "[green]OK[/]")
                t.add_row(row["object"], row["ns"], row["in_manifest"],
                          row["verdict"], sev_cell, row["rules"] or "—")
            console.print(t)
        else:
            print(f"    {'OBJETO':<44} {'NS':<18} {'MANIF':<5} "
                  f"{'APPLY':<11} {'SEV':<8} REGLA")
            for row in rows:
                print(f"    {row['object']:<44.44} {row['ns']:<18.18} "
                      f"{row['in_manifest']:<5} {row['verdict']:<11} "
                      f"{row['severity'] or 'OK':<8} {row['rules'] or '-'}")

    if other_findings:
        for f in sorted(other_findings,
                        key=lambda x: SEV_ORDER.get(x["severity"], 9)):
            _print_finding(f)
    elif not r["findings"]:
        (console.print if console else print)(
            "  [green]✓ Sin findings[/]" if console else "  ✓ Sin findings")


_SKIP_MARKERS = ("no existe en la definición", "sin deploy efectivo")


def _is_skip(r: Dict) -> bool:
    """Pipeline omitido por causa benigna (sin stage o sin deploy efectivo)."""
    return bool(r.get("error")) and any(m in r["error"] for m in _SKIP_MARKERS)


def print_summary(results: List[Dict], min_sev: str):
    """Tabla resumen con TODOS los pipelines: los analizados primero (por
    severidad) y los omitidos al final marcados con su causa."""
    min_rank = SEV_ORDER[min_sev]
    analyzed = [r for r in results
                if not _is_skip(r)
                and (SEV_ORDER.get(r.get("severity", "NONE"), 9) <= min_rank
                     or r.get("error"))]
    skipped = [r for r in results if _is_skip(r)]
    rows = analyzed + sorted(skipped,
                             key=lambda r: str(r["definition_name"]).lower())
    if console:
        t = Table(title="Resumen — Manifest Drift Audit")
        for col in ("Pipeline", "Release", "Estado", "Objetos", "Configured",
                    "Missing-Ann", "Def-Diff", "Severidad"):
            t.add_column(col)
        for r in rows:
            d = r.get("def_release_diff") or {}
            estado = (r.get("deployment_status") or
                      (f"[dim]{r['error']}[/]" if r.get("error") else ""))
            sev = r.get("severity", "NONE")
            sev_cell = (f"[{SEV_STYLE.get(sev, '')}]{sev}[/]"
                        if not r.get("error") else "[dim]—[/]")
            t.add_row(
                str(r["definition_name"]),
                str(r.get("release_name", "")) or "—",
                estado,
                str(r["manifest_objects"]),
                str(r["apply_counts"]["configured"]),
                str(_missing_ann_count(r)),
                "Sí" if diff_has_changes(d) else "—",
                sev_cell,
            )
        console.print(t)
    else:
        for r in rows:
            estado = r.get("deployment_status") or r.get("error", "")
            print(f"{r['definition_name']} | {r.get('release_name','')} | "
                  f"{estado} | sev={r.get('severity','NONE')}")


def _missing_ann_count(r: Dict) -> int:
    return sum(1 for f in r.get("findings", [])
               if f["rule"] == "NOT_MANAGED_BY_APPLY")


def export_results(results: List[Dict], fmt: str,
                   org: str = "", project: str = "") -> List[Path]:
    out_dir = resolve_outcome_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths: List[Path] = []

    def _clean(r: Dict) -> Dict:
        rr = dict(r)
        rr.pop("objects", None)          # canonical YAML ya aplicado a findings
        return rr

    if fmt in ("json", "both", "all"):
        p = out_dir / f"manifest_drift_{ts}.json"
        p.write_text(json.dumps([_clean(r) for r in results],
                                indent=2, ensure_ascii=False, default=str),
                     encoding="utf-8")
        paths.append(p)
    if fmt in ("csv", "both", "all"):
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
    if fmt in ("html", "all"):
        p = out_dir / f"manifest_drift_{ts}.html"
        p.write_text(build_html_report(results, org=org, project=project),
                     encoding="utf-8")
        paths.append(p)
    return paths


# ═══════════════════════════════════════════════════════════════════════════════
# HTML REPORT
# ═══════════════════════════════════════════════════════════════════════════════

_SEV_CSS = {"CRITICAL": "#7f1d1d", "HIGH": "#b91c1c", "MEDIUM": "#b45309",
            "LOW": "#1d4ed8", "INFO": "#6b7280", "NONE": "#15803d"}


def _esc(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def _azdo_urls(org: str, project: str, r: Dict) -> Dict[str, str]:
    """URLs web de Azure DevOps para la definición y el release."""
    if not org or not project:
        return {}
    base = f"https://dev.azure.com/{org}/{project}"
    out = {"definition":
           f"{base}/_release?view=mine&definitionId={r['definition_id']}"}
    if r.get("release_id"):
        out["release"] = (f"{base}/_releaseProgress?"
                          f"_a=release-pipeline-progress"
                          f"&releaseId={r['release_id']}")
    return out


def build_html_report(results: List[Dict],
                      org: str = "", project: str = "") -> str:
    """Reporte HTML autocontenido: resumen + detalle por pipeline con la
    tabla objeto×verdict×severidad (análisis principal de las 3 tasks)."""
    e = _esc
    analyzed = [r for r in results if not _is_skip(r)]
    skipped = [r for r in results if _is_skip(r)]

    sev_counts: Dict[str, int] = {}
    for r in analyzed:
        sev = r.get("severity", "NONE")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

    parts = ["""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>Release Manifest Drift — Auditoría</title>
<style>
body{font-family:'Segoe UI',system-ui,sans-serif;margin:24px;background:#f8fafc;color:#1f2937}
h1{font-size:22px} h2{font-size:16px;margin:28px 0 6px}
table{border-collapse:collapse;width:100%;background:#fff;margin:8px 0}
th,td{border:1px solid #e5e7eb;padding:6px 10px;text-align:left;
     font-size:12.5px;vertical-align:top}
th{background:#1e3a5f;color:#fff;white-space:nowrap}
tr:nth-child(even){background:#f9fafb}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;color:#fff;
       font-size:11px;font-weight:600;white-space:nowrap}
.pipe{border:1px solid #d1d5db;border-radius:8px;padding:14px 18px;
      margin:14px 0;background:#fff}
.meta{color:#4b5563;font-size:12.5px;line-height:1.7}
.small{font-size:11.5px;color:#6b7280}
.ok{color:#15803d;font-weight:600}
.warn{color:#b45309}
.kpi{display:inline-block;margin-right:18px}
code{background:#f3f4f6;padding:1px 4px;border-radius:3px;font-size:11.5px}
</style></head><body>"""]

    worst_order = {s: SEV_ORDER.get(s, 9) for s in sev_counts}
    sev_line = " · ".join(
        f'<span class="badge" style="background:{_SEV_CSS[s]}">{s}: '
        f'{sev_counts[s]}</span>'
        for s in sorted(sev_counts, key=lambda s: worst_order[s]))
    parts.append(
        f"<h1>🌪️ Release Manifest Drift — Auditoría</h1>"
        f"<div class='meta'>Generado: {e(datetime.now().strftime('%Y-%m-%d %H:%M'))} · "
        f"Pipelines analizados: <b>{len(analyzed)}</b> · Omitidos (sin stage/deploy): "
        f"<b>{len(skipped)}</b></div>"
        f"<div style='margin:10px 0'>{sev_line or '<span class=ok>Sin severidades</span>'}</div>")

    # ── Tabla resumen ────────────────────────────────────────────────
    parts.append("<h2>Resumen por pipeline</h2><table><tr>"
                 "<th>Pipeline</th><th>Release</th><th>Estado</th>"
                 "<th>Objetos</th><th>Apply</th><th>Def-Diff</th>"
                 "<th>Severidad</th><th>Findings</th></tr>")
    for r in sorted(analyzed, key=lambda x: SEV_ORDER.get(
            x.get("severity", "NONE"), 9)):
        counts = r.get("apply_counts", {})
        apply_txt = ", ".join(f"{counts.get(v, 0)} {v}" for v in _APPLY_VERDICTS
                              if counts.get(v)) or "—"
        d = r.get("def_release_diff") or {}
        sev = r.get("severity", "NONE")
        badge = (f'<span class="badge" style="background:{_SEV_CSS[sev]}">{sev}</span>'
                 if sev != "NONE" else '<span class="ok">OK</span>')
        findings_n = len(r.get("findings", []))
        err = e(r.get("error", ""))
        urls = _azdo_urls(org, project, r)
        azdo_link = (f' <a href="{e(urls["definition"])}" target="_blank" '
                     f'title="Abrir definición en Azure DevOps">↗</a>'
                     if urls.get("definition") else "")
        rel_html = e(r.get("release_name", ""))
        if urls.get("release"):
            rel_html = (f'<a href="{e(urls["release"])}" target="_blank" '
                        f'title="Abrir release en Azure DevOps">'
                        f'{rel_html}</a>')
        parts.append(
            f"<tr><td><b><a href='#def-{e(r['definition_id'])}'>"
            f"{e(r['definition_name'])}</a></b>{azdo_link}<br>"
            f"<span class='small'>def {e(r['definition_id'])}</span></td>"
            f"<td>{rel_html}<br><span class='small'>"
            f"id {e(r.get('release_id', ''))} · "
            f"{e(str(r.get('release_created', ''))[:16])}</span></td>"
            f"<td>{e(r.get('deployment_status', ''))}{' — ' + err if err else ''}</td>"
            f"<td>{e(r.get('manifest_objects', 0))}</td>"
            f"<td>{e(apply_txt)}</td>"
            f"<td>{'Sí' if diff_has_changes(d) else '—'}</td>"
            f"<td>{badge}</td><td>{findings_n}</td></tr>")
    parts.append("</table>")

    # ── Detalle por pipeline ─────────────────────────────────────────
    parts.append("<h2>Detalle por pipeline</h2>")
    for r in sorted(analyzed, key=lambda x: SEV_ORDER.get(
            x.get("severity", "NONE"), 9)):
        sev = r.get("severity", "NONE")
        badge = (f'<span class="badge" style="background:{_SEV_CSS[sev]}">{sev}</span>'
                 if sev != "NONE" else '<span class="ok">OK</span>')
        urls = _azdo_urls(org, project, r)
        name_html = e(r["definition_name"])
        if urls.get("definition"):
            name_html = (f'<a href="{e(urls["definition"])}" '
                         f'target="_blank">{name_html}</a>')
        rel_txt = e(r.get("release_name", ""))
        if urls.get("release"):
            rel_txt = (f'<a href="{e(urls["release"])}" target="_blank">'
                       f'{rel_txt}</a>')
        parts.append(
            f"<div class='pipe' id='def-{e(r['definition_id'])}'>"
            f"<b>{name_html}</b> {badge} "
            f"<div class='meta'>Release <code>{rel_txt}</code> "
            f"(id {e(r.get('release_id',''))}) — {e(r.get('deployment_status',''))} — "
            f"{e(str(r.get('release_created',''))[:16])}"
            + (f" · Prev <code>{e(r.get('prev_release_name',''))}</code> "
               f"(id {e(r.get('prev_release_id',''))})"
               if r.get("prev_release_id") else "")
            + (f"<br><span class='warn'>⚠ {e(r['error'])}</span>"
               if r.get("error") else "")
            + f"<br>Logs: <span class='small'>{e(', '.join(r.get('task_logs') or []) or '(ninguno)')}</span>"
              "</div>")

        # ── Consistencia explícita manifiesto ↔ apply ────────────────
        cs = consistency_summary(r)
        manif_txt = (f"{e(', '.join(cs['manifest_logs']))} → "
                     f"{e(cs['objects'])} objeto(s)"
                     if cs["manifest_logs"]
                     else "✗ sin task de manifiesto")
        apply_txt = (f"{e(', '.join(cs['apply_logs']))} → "
                     f"{e(cs['verdicts'])} verdict(s)"
                     if cs["apply_logs"] else "✗ sin task de apply")
        miss = (f"<span class='warn'>{e(', '.join(cs['missing_in_apply']))}</span>"
                if cs["missing_in_apply"] else '<span class="ok">ninguno</span>')
        extra = (f"<span class='warn'>{e(', '.join(cs['applied_not_in_manifest']))}</span>"
                 if cs["applied_not_in_manifest"]
                 else '<span class="ok">ninguno</span>')
        parts.append(
            "<div class='meta'><b>Consistencia manifiesto ↔ apply:</b><br>"
            f"&nbsp;&nbsp;manifiesto: {manif_txt}<br>"
            f"&nbsp;&nbsp;apply: {apply_txt}<br>"
            f"&nbsp;&nbsp;► En manifiesto SIN línea en apply: {miss}<br>"
            f"&nbsp;&nbsp;► Aplicado sin aparecer en manifiesto: {extra}"
            "</div>")

        d = r.get("def_release_diff")
        if d and diff_has_changes(d):
            parts.append("<div class='meta'><b>Def actual vs snapshot:</b> ")
            for label, key in (("tasks añadidas", "tasks_added"),
                               ("tasks eliminadas", "tasks_removed"),
                               ("versión task", "tasks_version_changed"),
                               ("vars añadidas", "vars_added"),
                               ("vars eliminadas", "vars_removed")):
                if d.get(key):
                    parts.append(
                        f"<br>&nbsp;&nbsp;{e(label)}: "
                        f"{e(', '.join(map(str, d[key])))}")
            for ic in d.get("task_inputs_changed", []):
                parts.append(
                    f"<br>&nbsp;&nbsp;input <code>{e(ic['task'])}.{e(ic['input'])}"
                    f"</code>: <code>{e(ic['snapshot'])}</code> → "
                    f"<code>{e(ic['current'])}</code>")
            parts.append("</div>")

        rows, other = build_object_rows(r)
        if rows:
            parts.append("<table><tr><th>Objeto</th><th>Namespace</th>"
                         "<th>Manifiesto</th><th>Apply</th><th>Severidad</th>"
                         "<th>Regla</th></tr>")
            for row in rows:
                sev_r = row["severity"]
                cell = (f'<span class="badge" style="background:{_SEV_CSS[sev_r]}">'
                        f"{sev_r}</span>" if sev_r
                        else '<span class="ok">OK</span>')
                parts.append(
                    f"<tr><td>{e(row['object'])}</td><td>{e(row['ns'])}</td>"
                    f"<td>{e(row['in_manifest'])}</td><td>{e(row['verdict'])}</td>"
                    f"<td>{cell}</td><td>{e(row['rules'] or '—')}</td></tr>")
            parts.append("</table>")

        if other:
            parts.append("<table><tr><th>Severidad</th><th>Regla</th>"
                         "<th>Objeto</th><th>Detalle</th></tr>")
            for f in sorted(other,
                            key=lambda x: SEV_ORDER.get(x["severity"], 9)):
                parts.append(
                    f"<tr><td><span class='badge' style='background:"
                    f"{_SEV_CSS.get(f['severity'],'#6b7280')}'>"
                    f"{e(f['severity'])}</span></td><td>{e(f['rule'])}</td>"
                    f"<td>{e(f['object'])}</td><td>{e(f['detail'])}</td></tr>")
            parts.append("</table>")
        elif not rows and not r["findings"]:
            parts.append("<div class='ok'>✓ Sin findings</div>")
        parts.append("</div>")

    if skipped:
        parts.append(
            f"<h2>Omitidos ({len(skipped)})</h2><div class='small'>"
            + ", ".join(e(r["definition_name"]) for r in skipped)
            + "</div>")

    parts.append("</body></html>")
    return "".join(parts)


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
    skipped: List[Dict] = []
    max_w = max(1, args.threads)
    with ThreadPoolExecutor(max_workers=max_w) as ex:
        futs = {ex.submit(analyze_definition, client, d, args,
                          args.task_patterns): d for d in selected}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            if not args.show_skipped and _is_skip(r):
                skipped.append(r)
            else:
                print_result(r)

    if skipped:
        no_stage = sum(1 for r in skipped
                       if "no existe" in r["error"])
        no_deploy = len(skipped) - no_stage
        (console.print if console else print)(
            f"Omitidos: {len(skipped)} pipeline(s) — {no_stage} sin stage "
            f"'{args.stage_name}' · {no_deploy} sin deploy efectivo "
            f"(--show-skipped para detalle)")

    results.sort(key=lambda r: SEV_ORDER.get(r.get("severity", "NONE"), 9))
    print_summary(results, args.severity)

    if args.output:
        paths = export_results(results, args.output, org, project)
        for p in paths:
            (console.print if console else print)(f"Exportado: {p}")

    worst = min((SEV_ORDER.get(r.get("severity", "NONE"), 9) for r in results),
                default=9)
    return 2 if worst <= SEV_ORDER["HIGH"] else 0


if __name__ == "__main__":
    sys.exit(main())
