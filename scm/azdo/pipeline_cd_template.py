#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline CD Template — extrae la definición completa de un pipeline CD como
template YAML reutilizable y (opcionalmente) la aplica sobre otro
definitionId.

Modos:

  Extract (default):  --source-id N
      GET /release/definitions/{id} → limpia campos del servidor, redacta
      secretos y resuelve IDs a nombres (queues, variable groups, task
      groups). Genera en outcome/templates/:

      * pipe_cd_full_<id>_<nombre>.yaml      — definición completa
        normalizada (metadata + definition + resolved_names + secrets):
        editable y aplicable via PUT sobre otro pipeline.
      * pipe_cd_updater_<id>_<nombre>.yaml   — template DSL del
        pipeline_updater (opción 41): search + update con un
        `action: add` por stage (definición embebida) y variables de
        nivel release.

  Apply:              --template FILE --target-id M
      Lee una template full exportada, hace backup del destino en
      outcome/backups/template/, muestra diff (stages añadidos/eliminados,
      variables) y hace PUT del definition transformado (id/revision del
      destino; nombre/path propios salvo --new-name/--new-path).
      Secretos con value:null conservan el valor existente del destino
      si la variable ya existe.

  Combinado:          --source-id N --target-id M [--dry-run]
      Extrae de N y aplica sobre M en una sola corrida.

Uso:
    python pipeline_cd_template.py --source-id 905
    python pipeline_cd_template.py --source-id 905 --target-id 910 --dry-run
    python pipeline_cd_template.py --template outcome/templates/pipe_cd_full_905_x.yaml --target-id 910
    python pipeline_cd_template.py --interactive

Autor: Harold Adrian
"""

import argparse
import copy
import json
import re
import sys
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
        AzdoClient, get_azdo_params, resolve_outcome_dir,
    )
except ImportError:
    sys.path.insert(0, str(BASE_DIR))
    from scm_inspection_remediator import (
        AzdoClient, get_azdo_params, resolve_outcome_dir,
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

# Campos gestionados por el servidor — no forman parte del "template"
SYSTEM_FIELDS = [
    "id", "revision", "createdOn", "modifiedOn", "createdBy", "modifiedBy",
    "_links", "url", "projectReference", "isDeleted", "currentRelease",
    "badgeUrl", "lastRelease",
]
ENV_FIELDS = ["id", "releaseId", "badgeUrl"]
PHASE_FIELDS = ["id"]


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACT — limpieza, secretos, resolución de nombres
# ═══════════════════════════════════════════════════════════════════════════════

def clean_definition_for_template(defn: Dict) -> Dict:
    """Deep-copy de la definición sin campos del servidor.

    Quita ids de definition/environment/deployPhase para que el template
    pueda hacer PUT sobre otra definición (los envs se recrean por nombre).
    """
    d = copy.deepcopy(defn)
    for f in SYSTEM_FIELDS:
        d.pop(f, None)
    for env in d.get("environments", []):
        for f in ENV_FIELDS:
            env.pop(f, None)
        env.pop("queue", None)          # display-only (nombre cacheado)
        for phase in env.get("deployPhases", []):
            for f in PHASE_FIELDS:
                phase.pop(f, None)
        for ap in (env.get("preDeployApprovals") or {}).get("approvals", []):
            ap.pop("id", None)
        for ap in (env.get("postDeployApprovals") or {}).get("approvals", []):
            ap.pop("id", None)
    return d


def redact_secret_values(defn: Dict) -> List[Dict]:
    """Pone value:null a variables isSecret (in-place) y devuelve la lista.

    En un PUT posterior, una variable secreta con value null conserva el
    valor que ya tenga el destino si la variable existe.
    """
    secrets: List[Dict] = []
    for scope_vars, env in ((defn.get("variables") or {}, None),):
        for name, val in scope_vars.items():
            if isinstance(val, dict) and val.get("isSecret"):
                val["value"] = None
                secrets.append({"scope": "definition", "name": name,
                                "env": None})
    for env in defn.get("environments", []):
        for name, val in (env.get("variables") or {}).items():
            if isinstance(val, dict) and val.get("isSecret"):
                val["value"] = None
                secrets.append({"scope": "environment", "name": name,
                                "env": env.get("name")})
    return secrets


def _core_get(client: AzdoClient, org: str, project: str, path: str):
    """GET contra dev.azure.com core API (AzdoClient.base es vsrm)."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/{path}"
    try:
        resp = client.session.get(url, params={"api-version": "7.1"},
                                  timeout=20)
        return resp.json() if resp.status_code == 200 else {}
    except Exception:
        return {}


def resolve_reference_names(client: AzdoClient, org: str, project: str,
                            defn: Dict) -> Dict:
    """Resuelve IDs → nombres para queues, variable groups y task groups."""
    resolved = {"agent_queues": {}, "variable_groups": {}, "task_groups": {}}
    queue_ids, vg_ids, tg_ids = set(), set(), set()

    for vg in defn.get("variableGroups", []) or []:
        if isinstance(vg, int):
            vg_ids.add(vg)
        elif isinstance(vg, dict) and vg.get("id"):
            vg_ids.add(vg["id"])

    for env in defn.get("environments", []):
        if env.get("queueId"):
            queue_ids.add(env["queueId"])
        for vg in env.get("variableGroups", []) or []:
            if isinstance(vg, int):
                vg_ids.add(vg)
            elif isinstance(vg, dict) and vg.get("id"):
                vg_ids.add(vg["id"])
        for phase in env.get("deployPhases", []):
            for inp_key in ("deploymentInput", "phaseInput"):
                qid = (phase.get(inp_key) or {}).get("queueId")
                if qid:
                    queue_ids.add(qid)
            for task in phase.get("workflowTasks", []):
                t = task.get("task", {})
                if t.get("taskGroup") and t.get("id"):
                    tg_ids.add(str(t["id"]))

    for qid in sorted(queue_ids):
        name = _core_get(client, org, project,
                         f"distributedtask/queues/{qid}").get("name")
        resolved["agent_queues"][str(qid)] = name or str(qid)
    for vgid in sorted(vg_ids, key=str):
        name = _core_get(client, org, project,
                         f"distributedtask/variablegroups/{vgid}").get("name")
        resolved["variable_groups"][str(vgid)] = name or str(vgid)
    for tgid in sorted(tg_ids):
        name = _core_get(client, org, project,
                         f"distributedtask/taskgroups/{tgid}").get("name")
        resolved["task_groups"][tgid] = name or tgid
    return resolved


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_"
                   for c in (name or "pipeline"))[:60]


def build_full_template(defn_clean: Dict, source_def: Dict, org: str,
                        project: str, resolved: Dict,
                        secrets: List[Dict]) -> Dict:
    """Template completa: metadata + definition normalizada."""
    envs = defn_clean.get("environments", [])
    return {
        "metadata": {
            "name": f"Template de {source_def.get('name', '?')}",
            "version": "1.0",
            "description": "Definición completa de pipeline CD extraída "
                           "de Azure DevOps — editable y aplicable sobre "
                           "otro definitionId via PUT",
            "comment": (
                "Template generada por pipeline_cd_template.py (opción 46).\n\n"
                "Uso:\n"
                "  python pipeline_cd_template.py --template <este archivo> "
                "--target-id <definitionId>\n\n"
                "Notas:\n"
                "  - Los ids de stages se omiten: al aplicar se recrean.\n"
                "  - Las variables secretas vienen con value null — al "
                "aplicar conservan el valor del destino si la variable ya "
                "existe; si no, quedan vacías (rellenar antes de usar).\n"
                "  - Los artifacts de esta template apuntan a los orígenes "
                "(build/repo) del pipeline ORIGEN. Al aplicar, el destino "
                "guarda primero un backup YAML y por defecto PRESERVA sus "
                "propios artifacts y triggers (--preserve). Para sobrescribir "
                "artifacts del origen use --preserve none.\n"
                "  - Estrategia por defecto: MERGE — solo agrega stages/"
                "variables que el destino no tiene; los compartidos se "
                "conservan (o se preguntan con --overwrite-stages ask). "
                "--strategy replace = reemplazo total.\n"
                "  - resolved_names documenta a qué corresponde cada ID de "
                "queue/variable-group/task-group.\n\n"
                "Placeholders [[target.*]] (resueltos contra el DESTINO al "
                "aplicar con --target-id):\n"
                "  [[target.name]]            nombre del pipeline destino\n"
                "  [[target.id]]              definitionId destino\n"
                "  [[target.path]]            carpeta del destino\n"
                "  [[target.artifact.alias]]  alias del 1er artifact destino\n"
                "  [[target.artifact.name]]   nombre def/repo del artifact\n"
                "  [[target.artifact.N.alias|name]]  artifact N-ésimo\n"
                "  [[target.var.NOMBRE]]      variable release del destino\n"
                "  [[target.env.STAGE.var.NOMBRE]]  variable de un stage "
                "del destino\n"
                "Ej: value: \"[[target.artifact.alias]]\" toma el alias del "
                "artifact del pipeline destino."
            ),
            "author": "SCM Team",
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "source": {
                "definition_id": source_def.get("id"),
                "name": source_def.get("name"),
                "path": source_def.get("path", "\\"),
                "revision": source_def.get("revision"),
                "org": org, "project": project,
                "stages": [e.get("name") for e in envs],
            },
        },
        "definition": defn_clean,
        "resolved_names": resolved,
        "secrets": secrets,
    }


def build_updater_template(defn_clean: Dict, source_def: Dict) -> Dict:
    """Template DSL del pipeline_updater (opción 41): un `action: add` por
    stage con la definición embebida + variables de nivel release."""
    envs = defn_clean.get("environments", [])
    stage_rules = [{
        "action": "add",
        "name": e.get("name", "stage"),
        "position": "end",
        "definition": e,
    } for e in envs]
    var_rules = [{
        "name": name,
        "action": "add",
        "scope": "release",
        "value": "" if (isinstance(v, dict) and v.get("isSecret"))
                 else (v.get("value") if isinstance(v, dict) else v),
        "allowOverride": bool((v or {}).get("allowOverride"))
                         if isinstance(v, dict) else False,
        "isSecret": bool((v or {}).get("isSecret"))
                    if isinstance(v, dict) else False,
    } for name, v in (defn_clean.get("variables") or {}).items()]

    return {
        "metadata": {
            "name": f"Replicar stages de {source_def.get('name', '?')}",
            "version": "1.0",
            "description": "Template DSL (opción 41) que inserta los stages "
                           f"del pipeline {source_def.get('id')} en el "
                           "pipeline destino",
            "comment": (
                "Generada por pipeline_cd_template.py (opción 46).\n"
                "ATENCIÓN: `action: add` AGREGA los stages — no reemplaza "
                "los existentes con el mismo nombre. Para reemplazo total "
                "del pipeline use la template full (pipe_cd_full_*.yaml) "
                "con --target-id."
            ),
            "author": "SCM Team",
            "created_at": datetime.now().strftime("%Y-%m-%d"),
        },
        "search": {"stages": [{"name": "*"}]},
        "update": {
            "variables": var_rules,
            "stages": stage_rules,
        },
        "options": {"dry_run": True, "rollback_on_error": True},
    }


def export_templates(source_def: Dict, org: str, project: str, fmt: str,
                     out_dir: Path, resolve_names: bool = True,
                     client: Optional[AzdoClient] = None) -> List[Path]:
    """Genera los archivos de template; devuelve paths escritos."""
    clean = clean_definition_for_template(source_def)
    secrets = redact_secret_values(clean)
    resolved = (resolve_reference_names(client, org, project, clean)
                if resolve_names and client else
                {"agent_queues": {}, "variable_groups": {},
                 "task_groups": {}})

    sid = source_def.get("id")
    safe = _safe_name(source_def.get("name"))
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    if fmt in ("full", "both"):
        tpl = build_full_template(clean, source_def, org, project,
                                  resolved, secrets)
        p = out_dir / f"pipe_cd_full_{sid}_{safe}.yaml"
        p.write_text(yaml.safe_dump(tpl, sort_keys=False,
                                    allow_unicode=True), encoding="utf-8")
        written.append(p)
    if fmt in ("updater", "both"):
        tpl = build_updater_template(clean, source_def)
        p = out_dir / f"pipe_cd_updater_{sid}_{safe}.yaml"
        p.write_text(yaml.safe_dump(tpl, sort_keys=False,
                                    allow_unicode=True), encoding="utf-8")
        written.append(p)
    return written


# ═══════════════════════════════════════════════════════════════════════════════
# APPLY — PUT del template sobre otra definition
# ═══════════════════════════════════════════════════════════════════════════════

# Placeholders resueltos contra la definición DESTINO al aplicar:
#   [[target.name]]                  nombre del pipeline destino
#   [[target.id]]                    definitionId destino
#   [[target.path]]                  carpeta del destino
#   [[target.artifact.alias]]        alias del 1er artifact del destino
#   [[target.artifact.name]]         nombre de la def/repo del 1er artifact
#   [[target.artifact.N.alias|name]] artifact N-ésimo del destino
#   [[target.var.<NAME>]]            variable release del destino
#   [[target.env.<STAGE>.var.<NAME>]] variable del stage <STAGE> del destino
_TARGET_PH = re.compile(r"\[\[target\.([^\]]+)\]\]")


def _target_lookup(target: Dict, path: str):
    """Resuelve la ruta de un placeholder [[target.<path>]] contra la
    definición destino. None si no se puede resolver."""
    arts = target.get("artifacts") or []

    if path == "name":
        return target.get("name")
    if path == "id":
        return target.get("id")
    if path == "path":
        return target.get("path")

    m = re.fullmatch(r"artifact(?:\.(\d+))?\.(alias|name)", path)
    if m:
        idx = int(m.group(1) or 0)
        if idx >= len(arts):
            return None
        art = arts[idx]
        if m.group(2) == "alias":
            return art.get("alias")
        return ((art.get("definitionReference") or {})
                .get("definition") or {}).get("name")

    m = re.fullmatch(r"var\.(.+)", path)
    if m:
        v = (target.get("variables") or {}).get(m.group(1))
        return v.get("value") if isinstance(v, dict) else v

    m = re.fullmatch(r"env\.(.+)\.var\.(.+)", path)
    if m:
        stage, var = m.group(1), m.group(2)
        for env in target.get("environments", []):
            if (env.get("name") or "").lower() == stage.lower():
                v = (env.get("variables") or {}).get(var)
                return v.get("value") if isinstance(v, dict) else v
    return None


def resolve_target_placeholders(node, target: Dict,
                                unresolved: Optional[List[str]] = None):
    """Sustituye recursivamente [[target.<path>]] en strings con valores
    de la definición destino. Los no resolubles quedan literales y se
    acumulan en `unresolved`."""
    if isinstance(node, str):
        def _rep(m):
            val = _target_lookup(target, m.group(1))
            if val is None:
                if unresolved is not None:
                    unresolved.append(m.group(0))
                return m.group(0)
            return str(val)
        return _TARGET_PH.sub(_rep, node)
    if isinstance(node, dict):
        return {k: resolve_target_placeholders(v, target, unresolved)
                for k, v in node.items()}
    if isinstance(node, list):
        return [resolve_target_placeholders(v, target, unresolved)
                for v in node]
    return node


def load_template_definition(path: Path) -> Dict:
    """Carga la definición de una template exportada (acepta la envoltura
    {metadata, definition} o un dict de definición directo)."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: no es un mapping YAML")
    defn = data.get("definition")
    if isinstance(defn, dict) and "environments" in defn:
        return defn
    if "environments" in data:
        return data
    raise ValueError(f"{path}: no contiene una 'definition' con "
                     "environments")


# ═══════════════════════════════════════════════════════════════════════════════
# PRESERVE FROM TARGET — valores del destino que no se deben sobrescribir
# ═══════════════════════════════════════════════════════════════════════════════
#
# Rutas soportadas en --preserve:
#   artifacts            lista de artifacts del destino (source/build artifact)
#   triggers             triggers del destino (referencian los artifacts)
#   releaseNameFormat    formato de nombre de release del destino
#   variableGroups       grupos de variables del destino
#   variables            todas las variables de release del destino
#   var.<NOMBRE>         una variable de release concreta del destino
#   env.<STAGE>          stage completo del destino (reemplaza el mismo nombre
#                        en la template o lo agrega si no existe)
#   env.*                todos los stages del destino
#   env.<STAGE>.variables   variables de un stage del destino (si existe en payload)
#   retentionPolicy / processParameters / description / badgeOptions  (top-level)
DEFAULT_PRESERVE_PATHS = ["artifacts", "triggers"]

# Campos read-only de un environment preservado del destino
_ENV_PRESERVE_STRIP = ("releaseId", "badgeUrl", "queue")


def _env_by_name(defn: Dict, stage: str) -> Optional[Dict]:
    for env in defn.get("environments", []):
        if (env.get("name") or "").lower() == stage.lower():
            return env
    return None


def _preserve_get(target: Dict, path: str):
    """Obtiene el valor de una ruta preserve desde la definición destino."""
    m = re.fullmatch(r"var\.(.+)", path)
    if m:
        return (target.get("variables") or {}).get(m.group(1))
    m = re.fullmatch(r"env\.(.+?)\.(.+)", path)
    if m:
        env = _env_by_name(target, m.group(1))
        return env.get(m.group(2)) if env else None
    m = re.fullmatch(r"env\.(.+)", path)
    if m:
        return _env_by_name(target, m.group(1))
    return target.get(path)


def _preserve_set(payload: Dict, path: str, value) -> bool:
    """Escribe el valor preserve en el payload. False si la ruta no aplica
    (p.ej. el stage no existe en la template)."""
    m = re.fullmatch(r"var\.(.+)", path)
    if m:
        payload.setdefault("variables", {})[m.group(1)] = value
        return True
    m = re.fullmatch(r"env\.(.+?)\.(.+)", path)
    if m:
        env = _env_by_name(payload, m.group(1))
        if env is None:
            return False
        env[m.group(2)] = value
        return True
    m = re.fullmatch(r"env\.(.+)", path)
    if m:
        # Stage completo: reemplaza el mismo nombre o se agrega al final.
        if isinstance(value, dict):
            for f in _ENV_PRESERVE_STRIP:
                value.pop(f, None)
        envs = payload.setdefault("environments", [])
        existing = _env_by_name(payload, m.group(1))
        if existing is not None:
            envs[envs.index(existing)] = value
        else:
            envs.append(value)
        return True
    payload[path] = value
    return True


def preserve_from_target(payload: Dict, target: Dict,
                         paths: List[str]) -> Tuple[List[str], List[str]]:
    """Copia valores del destino al payload para que el PUT no los planche.

    Devuelve (paths_aplicados, paths_no_aplicados). Un path no aplica cuando
    el destino no tiene el valor o el stage no existe en la template
    (para env.<STAGE>.<campo>; env.<STAGE> siempre aplica).
    """
    expanded: List[str] = []
    for p in paths:
        if p == "env.*":
            expanded += [f"env.{e.get('name')}"
                         for e in target.get("environments", [])
                         if e.get("name")]
        else:
            expanded.append(p)

    applied: List[str] = []
    skipped: List[str] = []
    for path in expanded:
        value = _preserve_get(target, path)
        if value is None:
            skipped.append(path)
            continue
        if _preserve_set(payload, path, copy.deepcopy(value)):
            applied.append(path)
        else:
            skipped.append(path)
    return applied, skipped


# ═══════════════════════════════════════════════════════════════════════════════
# MERGE — aplicar template sin planchar el destino
# ═══════════════════════════════════════════════════════════════════════════════
#
# Estrategia merge (default del apply):
#   - Stage solo en template        → se AGREGA
#   - Stage en ambos                → por defecto se conserva el del destino;
#     si se decide sobrescribir (ask/all/lista), se usa el de la template pero
#     conservando el `id` del env destino (linkage) y, salvo --update-vars,
#     sus variables (merge de variables: nuevas de la template se agregan,
#     las del destino no se tocan)
#   - Stage solo en destino         → se conserva intacto (merge nunca borra)
#   - Variables de release          → nuevas de la template se agregan; las
#     existentes conservan el valor del destino salvo --update-vars
def _merge_vars(target_vars: Dict, tpl_vars: Dict,
                update_vars: bool) -> Dict:
    """Overlay: base = destino; template agrega nuevas y (con update_vars)
    actualiza las existentes."""
    merged = copy.deepcopy(target_vars or {})
    for name, val in (tpl_vars or {}).items():
        if name not in merged or update_vars:
            merged[name] = copy.deepcopy(val)
    return merged


def merge_definitions(tpl_def: Dict, target: Dict,
                      overwrite: str = "ask",
                      update_vars: bool = False,
                      ask_fn=None,
                      decisions: Optional[Dict[str, bool]] = None
                      ) -> Tuple[Dict, List[str]]:
    """Mergea la template sobre el destino. Devuelve (definición, reporte).

    overwrite: "ask" (pregunta por stage vía ask_fn; sin ask_fn → conserva),
               "all", "none" o lista CSV de nombres de stages.
    decisions: dict compartido para reutilizar respuestas entre dry-run y PUT.
    """
    merged = copy.deepcopy(tpl_def)
    report: List[str] = []
    decisions = decisions if decisions is not None else {}

    if isinstance(overwrite, str) and overwrite not in ("ask", "all", "none"):
        overwrite_set = {s.strip().lower() for s in overwrite.split(",")
                         if s.strip()}
    elif isinstance(overwrite, (list, tuple, set)):
        overwrite_set = {str(s).lower() for s in overwrite}
    else:
        overwrite_set = None

    tgt_envs = {e.get("name", "").lower(): e
                for e in target.get("environments", [])}
    tpl_names = set()
    new_envs: List[Dict] = []

    for env in merged.get("environments", []):
        name = env.get("name", "")
        tpl_names.add(name.lower())
        te = tgt_envs.get(name.lower())
        if te is None:
            new_envs.append(env)
            report.append(f"+ stage nuevo (template): {name}")
            continue

        do_overwrite = False
        if overwrite == "all":
            do_overwrite = True
        elif overwrite == "none":
            do_overwrite = False
        elif overwrite_set is not None:
            do_overwrite = name.lower() in overwrite_set
        else:  # ask
            if name.lower() in decisions:
                do_overwrite = decisions[name.lower()]
            elif ask_fn is not None:
                do_overwrite = bool(ask_fn(name))
                decisions[name.lower()] = do_overwrite
            else:
                do_overwrite = False

        if not do_overwrite:
            new_envs.append(copy.deepcopy(te))
            report.append(f"= stage conservado del destino: {name}")
            continue

        new_env = env
        if te.get("id"):
            new_env["id"] = te["id"]       # linkage del stage destino
        if update_vars:
            new_env["variables"] = _merge_vars(te.get("variables"),
                                               env.get("variables"), True)
        else:
            new_env["variables"] = copy.deepcopy(te.get("variables") or {})
        new_envs.append(new_env)
        vnote = "variables mergeadas" if update_vars \
            else "variables del destino preservadas"
        report.append(f"~ stage sobrescrito por template ({vnote}): {name}")

    kept = 0
    for env in target.get("environments", []):
        if env.get("name", "").lower() not in tpl_names:
            new_envs.append(copy.deepcopy(env))
            kept += 1
    if kept:
        report.append(f"= stages solo en destino conservados: {kept}")
    merged["environments"] = new_envs

    before = len(target.get("variables") or {})
    merged["variables"] = _merge_vars(target.get("variables"),
                                      merged.get("variables"), update_vars)
    added = [k for k in merged["variables"]
             if k not in (target.get("variables") or {})]
    if added:
        report.append(f"+ variables nuevas: {', '.join(added)}")
    if update_vars:
        report.append("~ variables existentes actualizadas por template")
    else:
        report.append(f"= variables del destino preservadas ({before})")

    return merged, report


def backup_definition(defn: Dict, backup_dir: Path) -> Dict:
    """Backup del destino en JSON + YAML; devuelve {"json": p, "yaml": p}."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = _safe_name(defn.get("name"))
    data = {
        "metadata": {"tool": "pipeline_cd_template",
                     "version": __version__,
                     "backupDate": datetime.now().isoformat(),
                     "pipelineId": defn.get("id"),
                     "pipelineName": defn.get("name"),
                     "revision": defn.get("revision")},
        "definition": defn,
    }
    pj = backup_dir / f"backup_def_{defn.get('id')}_{safe}_{ts}.json"
    pj.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                  encoding="utf-8")
    py = backup_dir / f"backup_def_{defn.get('id')}_{safe}_{ts}.yaml"
    py.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False,
                                 default_flow_style=False),
                  encoding="utf-8")
    return {"json": pj, "yaml": py}


def load_target_backup(path: Path) -> Dict:
    """Relee el backup del destino (JSON o YAML) y devuelve la definición."""
    text = path.read_text(encoding="utf-8")
    data = (yaml.safe_load(text) if path.suffix.lower() in (".yaml", ".yml")
            else json.loads(text))
    return data.get("definition", data) if isinstance(data, dict) else {}


def apply_diff_summary(target: Dict, tpl_def: Dict) -> List[str]:
    """Resumen legible de lo que cambiaría el PUT (stages y variables)."""
    lines: List[str] = []
    tgt_envs = {e.get("name"): e for e in target.get("environments", [])}
    tpl_envs = {e.get("name"): e for e in tpl_def.get("environments", [])}
    added = [n for n in tpl_envs if n not in tgt_envs]
    removed = [n for n in tgt_envs if n not in tpl_envs]
    kept = [n for n in tpl_envs if n in tgt_envs]
    lines.append(f"stages template: {len(tpl_envs)} | destino actual: "
                 f"{len(tgt_envs)}")
    if added:
        lines.append(f"+ stages nuevos: {', '.join(added)}")
    if removed:
        lines.append(f"- stages solo en destino: {', '.join(removed)}")
    lines.append(f"= stages en ambos: {', '.join(kept) or 'ninguno'}")
    tgt_vars = set(target.get("variables") or {})
    tpl_vars = set(tpl_def.get("variables") or {})
    if set(tpl_vars) - tgt_vars:
        lines.append(f"+ variables: {', '.join(sorted(set(tpl_vars) - tgt_vars))}")
    if tgt_vars - tpl_vars:
        lines.append(f"- variables: {', '.join(sorted(tgt_vars - tpl_vars))}")
    return lines


def apply_template(client: AzdoClient, target_id: int, tpl_def: Dict,
                   new_name: str = "", new_path: str = "",
                   dry_run: bool = False,
                   backup_dir: Optional[Path] = None,
                   preserve: Optional[List[str]] = None,
                   strategy: str = "merge",
                   overwrite: str = "ask",
                   update_vars: bool = False,
                   ask_fn=None,
                   decisions: Optional[Dict[str, bool]] = None) -> Dict:
    """PUT del template sobre la definición destino (con backup previo).

    strategy="merge" (default): solo agrega lo que el destino no tiene —
    stages nuevos de la template se insertan, los existentes se conservan
    salvo decisión de overwrite (ask/all/none/lista), variables del destino
    preservadas salvo update_vars. strategy="replace": reemplazo total.

    Flujo: descarga el destino → backup JSON+YAML del destino original →
    relee el YAML como fuente de merge/preserve/placeholders → renumera
    ranks → guarda el payload resultante como YAML (updater aplicado) →
    PUT (solo si no es dry-run). Los YAML del destino y del updater se
    escriben siempre que backup_dir esté definido — incluso en dry-run,
    pues son archivos locales y no tocan AzDO.

    Devuelve {"backup": {json,yaml}|None, "updater_yaml": Path|None,
              "result": respuesta|None, "summary": [líneas],
              "preserve_applied": [...], "payload": payload}.
    """
    if preserve is None:
        preserve = list(DEFAULT_PRESERVE_PATHS)

    target = client.get(f"{client.base}/definitions/{target_id}",
                        params={"api-version": "7.1"})
    summary = apply_diff_summary(target, tpl_def)
    summary.append(f"target: id {target_id} '{target.get('name')}' "
                   f"rev {target.get('revision')}")
    summary.append(f"strategy: {strategy}")

    # Backup del destino siempre que haya backup_dir (archivo local, no
    # toca AzDO) — y se relee el YAML como fuente de merge/preserve.
    backup_paths: Optional[Dict] = None
    preserve_src = target
    if backup_dir is not None:
        backup_paths = backup_definition(target, backup_dir)
        try:
            preserve_src = load_target_backup(backup_paths["yaml"]) or target
        except Exception:
            preserve_src = target
        summary.append(f"backup destino: {backup_paths['yaml']}")

    if strategy == "merge":
        payload, merge_report = merge_definitions(
            tpl_def, preserve_src, overwrite=overwrite,
            update_vars=update_vars, ask_fn=ask_fn, decisions=decisions)
        summary += merge_report
    else:
        payload = copy.deepcopy(tpl_def)

    payload["id"] = target_id
    payload["revision"] = preserve_src.get("revision")
    payload["name"] = new_name or preserve_src.get("name")
    payload["path"] = new_path or preserve_src.get("path", "\\")

    if preserve:
        applied, skipped = preserve_from_target(payload, preserve_src,
                                                preserve)
        if applied:
            summary.append("preservado del destino: " + ", ".join(applied))
        if skipped:
            summary.append("preserve sin valor en destino: "
                           + ", ".join(skipped))

    unresolved: List[str] = []
    payload = resolve_target_placeholders(payload, preserve_src, unresolved)
    if unresolved:
        summary.append("⚠ placeholders sin resolver: "
                       + ", ".join(sorted(set(unresolved))))

    # VS402874: los ranks de los stages deben ser naturales consecutivos
    # desde 1 — tras merge/preserve hay que renumerarlos.
    for i, env in enumerate(payload.get("environments", []), 1):
        env["rank"] = i

    # Siempre guardar el YAML del updater resultante (payload final).
    updater_yaml: Optional[Path] = None
    if backup_dir is not None:
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        updater_yaml = backup_dir / (
            f"updater_result_{target_id}_"
            f"{_safe_name(payload.get('name'))}_{ts}.yaml")
        updater_yaml.write_text(yaml.safe_dump(
            {"metadata": {"tool": "pipeline_cd_template",
                          "version": __version__,
                          "generated": datetime.now().isoformat(),
                          "targetId": target_id,
                          "strategy": strategy,
                          "dryRun": dry_run},
             "definition": payload},
            allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8")
        summary.append(f"updater yaml: {updater_yaml}")

    if dry_run:
        return {"backup": backup_paths, "updater_yaml": updater_yaml,
                "result": None, "summary": summary, "payload": payload,
                "preserve_applied": applied if preserve else []}

    result = client.put(f"{client.base}/definitions/{target_id}",
                        payload, params={"api-version": "7.1"})
    return {"backup": backup_paths, "updater_yaml": updater_yaml,
            "result": result, "summary": summary, "payload": payload,
            "preserve_applied": applied if preserve else []}


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE + CLI
# ═══════════════════════════════════════════════════════════════════════════════

def _print(msg: str = "", style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/]" if style else msg)
    else:
        print(msg)


def _show_definition_summary(defn: Dict):
    envs = defn.get("environments", [])
    n_tasks = sum(len(p.get("workflowTasks", []))
                  for e in envs for p in e.get("deployPhases", []))
    lines = [
        f"ID:        {defn.get('id')}",
        f"Nombre:    {defn.get('name')}",
        f"Path:      {defn.get('path', chr(92))}",
        f"Revisión:  {defn.get('revision')}",
        f"Stages:    {len(envs)} ({', '.join(e.get('name','?') for e in envs)})",
        f"Tasks:     {n_tasks}",
        f"Variables: {len(defn.get('variables') or {})}",
        f"Artifacts: {len(defn.get('artifacts') or [])}",
    ]
    if console:
        console.print(Panel("\n".join(lines), title="Definición",
                            expand=False))
    else:
        print("\n".join("  " + l for l in lines))


def get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Extrae un pipeline CD como template YAML reutilizable "
                    "y/o la aplica sobre otro definitionId.")
    p.add_argument("--pat", default="")
    p.add_argument("--org", default="")
    p.add_argument("--project", default="")
    p.add_argument("--source-id", type=int, default=0,
                   help="definitionId origen a extraer")
    p.add_argument("--template", default="",
                   help="template YAML exportada previamente (modo apply)")
    p.add_argument("--target-id", type=int, default=0,
                   help="definitionId destino para aplicar (PUT)")
    p.add_argument("--new-name", default="",
                   help="nombre para el destino al aplicar (default: mantiene)")
    p.add_argument("--new-path", default="",
                   help="path para el destino al aplicar (default: mantiene)")
    p.add_argument("--format", choices=["full", "updater", "both"],
                   default="both", help="formato(s) de template a exportar")
    p.add_argument("--output-dir", default="",
                   help="carpeta de templates (default: outcome/templates)")
    p.add_argument("--backup-dir", default="",
                   help="carpeta de backups (default: outcome/backups/template)")
    p.add_argument("--no-resolve-names", action="store_true",
                   help="no resolver IDs de queue/variable-group/task-group "
                        "a nombres")
    p.add_argument("--strategy", choices=["merge", "replace"],
                   default="merge",
                   help="apply: merge (default) agrega lo que falta y "
                        "conserva el destino; replace = reemplazo total")
    p.add_argument("--overwrite-stages", default="ask",
                   help="merge: stages compartidos a sobrescribir — ask "
                        "(default), all, none o lista CSV de nombres")
    p.add_argument("--update-vars", action="store_true",
                   help="merge: actualizar variables existentes con los "
                        "valores de la template (default: preservar destino)")
    p.add_argument("--preserve", default="",
                   help="apply: rutas del destino que NO se sobrescriben, "
                        "separadas por coma (default: artifacts,triggers; "
                        "'none' desactiva). Soporta var.<NOMBRE> y "
                        "env.<STAGE>.<campo>")
    p.add_argument("--dry-run", action="store_true",
                   help="apply: muestra el diff sin hacer PUT")
    p.add_argument("--yes", action="store_true",
                   help="apply: no pedir confirmación")
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def _ask(prompt: str, default: str = "") -> str:
    if console:
        from rich.prompt import Prompt
        return Prompt.ask(prompt, default=default) if default \
            else Prompt.ask(prompt)
    sfx = f" [{default}]" if default else ""
    v = input(f"{prompt}{sfx}: ").strip()
    return v or default


def interactive(args) -> argparse.Namespace:
    cfg_org, cfg_proj = "", ""
    try:
        cfg_org, cfg_proj, _ = get_azdo_params(args)
    except SystemExit:
        pass
    _print("\nPipeline CD Template — interactivo", "bold cyan")
    args.source_id = int(_ask("  definitionId ORIGEN a extraer",
                              str(args.source_id) if args.source_id else ""))
    fmt = _ask("  Formato (full/updater/both)", args.format)
    args.format = fmt if fmt in ("full", "updater", "both") else "both"
    ans = _ask("  ¿Aplicar sobre otro definitionId? (id destino o vacío)")
    if ans.strip():
        args.target_id = int(ans)
        args.new_name = _ask("  Nombre destino (vacío = mantiene)",
                             args.new_name)
        args.new_path = _ask("  Path destino (vacío = mantiene)",
                             args.new_path)
        args.preserve = _ask(
            "  Preservar del destino (coma, 'none' = nada)",
            args.preserve or ",".join(DEFAULT_PRESERVE_PATHS))
        st = _ask("  Estrategia (merge/replace)", args.strategy)
        args.strategy = st if st in ("merge", "replace") else "merge"
        if args.strategy == "merge":
            args.overwrite_stages = _ask(
                "  Stages a sobrescribir (ask/all/none/o nombres CSV)",
                args.overwrite_stages)
            uv = _ask("  ¿Actualizar variables existentes del destino? (s/n)",
                      "s" if args.update_vars else "n")
            args.update_vars = uv.lower().startswith("s")
        dr = _ask("  ¿Dry-run? (s/n)", "s" if args.dry_run else "n")
        args.dry_run = dr.lower().startswith("s")
    return args


def _parse_preserve(raw: str) -> Optional[List[str]]:
    """'none'/'no' → [] ; vacío → None (default); resto → lista de rutas."""
    raw = (raw or "").strip()
    if raw.lower() in ("none", "no", "nada"):
        return []
    if not raw:
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


def main() -> int:
    args = get_args()
    if args.interactive or (not args.source_id and not args.template):
        args = interactive(args)
    org, project, pat = get_azdo_params(args)
    client = AzdoClient(org, project, pat)

    out_dir = (Path(args.output_dir) if args.output_dir
               else resolve_outcome_dir() / "templates")
    backup_dir = (Path(args.backup_dir) if args.backup_dir
                  else resolve_outcome_dir() / "backups" / "template")

    _print(f"Pipeline CD Template v{__version__} — {org}/{project}",
           "bold cyan")

    tpl_def: Optional[Dict] = None

    # ── Extract ──────────────────────────────────────────────────────────
    if args.source_id:
        source = client.get(
            f"{client.base}/definitions/{args.source_id}",
            params={"api-version": "7.1"})
        _show_definition_summary(source)
        written = export_templates(
            source, org, project, args.format, out_dir,
            resolve_names=not args.no_resolve_names, client=client)
        for p in written:
            _print(f"  Template: {p}", "green")
        if not args.target_id:
            _print("\nÚsala con opción 41 (updater) o con esta misma "
                   "opción: --template <archivo> --target-id <id>", "dim")
        tpl_def = clean_definition_for_template(source)

    # ── Apply ────────────────────────────────────────────────────────────
    if args.target_id:
        if tpl_def is None:
            if not args.template:
                _print("ERROR: --target-id requiere --source-id o "
                       "--template", "bold red")
                return 1
            try:
                tpl_def = load_template_definition(Path(args.template))
            except Exception as e:
                _print(f"ERROR leyendo template: {e}", "bold red")
                return 1
        # limpieza por si la template trae campos del servidor
        tpl_def = clean_definition_for_template(tpl_def)

        preserve = _parse_preserve(args.preserve)
        ow = args.overwrite_stages
        overwrite: object = (ow if ow in ("ask", "all", "none")
                             else [s.strip() for s in ow.split(",")
                                   if s.strip()])
        decisions: Dict[str, bool] = {}

        def _ask_stage(name: str) -> bool:
            if console:
                from rich.prompt import Confirm
                return Confirm.ask(
                    f"  Stage '{name}' existe en el destino — "
                    f"¿sobrescribir con la template?", default=False)
            ans = _ask(f"  ¿Sobrescribir stage '{name}'? (s/n)", "n")
            return ans.lower().startswith("s")

        res = apply_template(client, args.target_id, tpl_def,
                             new_name=args.new_name, new_path=args.new_path,
                             dry_run=True, preserve=preserve,
                             backup_dir=backup_dir,
                             strategy=args.strategy, overwrite=overwrite,
                             update_vars=args.update_vars,
                             ask_fn=_ask_stage, decisions=decisions)
        _print("\nDiff destino ← template:", "bold")
        for l in res["summary"]:
            _print(f"  {l}")
        if args.dry_run:
            _print("\nDry-run — no se aplicó nada.", "yellow")
            return 0
        if not args.yes:
            ans = _ask("\n¿Confirmar PUT sobre el destino? (s/n)", "n")
            if not ans.lower().startswith("s"):
                _print("Cancelado.", "yellow")
                return 0
        res = apply_template(client, args.target_id, tpl_def,
                             new_name=args.new_name, new_path=args.new_path,
                             dry_run=False, backup_dir=backup_dir,
                             preserve=preserve, strategy=args.strategy,
                             overwrite=overwrite, update_vars=args.update_vars,
                             ask_fn=_ask_stage, decisions=decisions)
        if res["backup"]:
            _print(f"  Backup destino (yaml): {res['backup']['yaml']}", "dim")
            _print(f"  Backup destino (json): {res['backup']['json']}", "dim")
        if res.get("updater_yaml"):
            _print(f"  Updater aplicado (yaml): {res['updater_yaml']}", "dim")
        new_def = res["result"]
        _print(f"\n✓ Aplicado — definition {new_def.get('id')} "
               f"'{new_def.get('name')}' rev {new_def.get('revision')}",
               "bold green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
