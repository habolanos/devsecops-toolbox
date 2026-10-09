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
import html as _html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

BASE_DIR = Path(__file__).resolve().parent          # scm/azdo
SCM_ROOT = BASE_DIR.parent                          # scm/

__version__ = "1.0.17"

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

console = Console(record=True) if RICH else None

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Transcript de consola → reporte de evidencia HTML ─────────────────────
# Todo lo que _print/_ask/_show_definition_summary emite queda registrado
# aquí (incluye las respuestas del usuario en modo interactivo) y se vuelca
# a outcome/reports/EVIDENCIA_pipe_cd_template_<ts>.html al final del run.
_TRANSCRIPT: List[Tuple[str, str]] = []   # (texto, estilo rich)
_REPORT_META: Dict[str, object] = {}


def _record(line: str = "", style: str = "") -> None:
    _TRANSCRIPT.append((line, style))


def _record_files(files) -> None:
    _REPORT_META.setdefault("files", [])
    _REPORT_META["files"].extend((label, str(p)) for label, p in files)


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


def _ids_tag(source_id, target_id) -> str:
    """Segmento '<srcId>-to-<dstId>' para los archivos del apply
    (ej. '3687-to-1899'; 'src-to-1899' si el origen se desconoce)."""
    s = str(source_id) if source_id else "src"
    t = str(target_id) if target_id else "dst"
    return f"{s}-to-{t}"


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


def _updater_artifact_filters(env: Dict, artifacts: List[Dict]
                              ) -> Tuple[Optional[List[Dict]], List[str]]:
    """Traduce las conditions de artifact de un stage a reglas
    `artifact_filters` del DSL de la opción 41 (que resuelve el alias
    contra los artifacts del pipeline DESTINO al aplicar).

    Devuelve (filters, warnings):
      - filters == []   → el stage no tiene condiciones artifact.
      - filters == lista → todas reconstruibles; la opción 41 las
        reescribirá con el alias del destino al aplicar.
      - filters == None → alguna condición no es reconstruible (sin name o
        sin sourceBranch parseable): NO emitir artifact_filters — las
        conditions quedan tal cual en la definición embebida (política
        all-or-nothing para no borrar filtros en silencio).

    Token `artifact`: `$auto:<Tipo>` cuando el artifact del origen es el
    único de su tipo (resolución inequívoca en el destino); si el tipo se
    repite o el alias no figura en los artifacts del origen, se emite el
    alias literal (mejor esfuerzo) y se reporta un warning.
    """
    conds = [c for c in env.get("conditions", [])
             if c.get("conditionType") == "artifact"]
    if not conds:
        return [], []

    alias_to_art = {a.get("alias"): a for a in artifacts if a.get("alias")}
    type_count: Dict[str, int] = {}
    for a in artifacts:
        t = a.get("type") or "Build"
        type_count[t] = type_count.get(t, 0) + 1

    warnings: List[str] = []
    grouped: Dict[str, Dict] = {}
    order: List[str] = []
    for c in conds:
        alias = c.get("name")
        try:
            val = json.loads(c.get("value") or "{}")
        except (ValueError, TypeError):
            val = {}
        branch = val.get("sourceBranch")
        if not alias or not isinstance(branch, str) or not branch:
            warnings.append(
                f"stage '{env.get('name')}': condition artifact sin "
                f"alias/sourceBranch reconstruible — artifact_filters no "
                f"emitido para este stage")
            return None, warnings
        if alias not in grouped:
            art = alias_to_art.get(alias)
            if art is not None and type_count.get(
                    art.get("type") or "Build", 0) == 1:
                token = f"$auto:{art.get('type') or 'Build'}"
            else:
                token = alias
                warnings.append(
                    f"stage '{env.get('name')}': artifact '{alias}' "
                    f"sin token $auto inequívoco (tipo repetido o alias "
                    f"no encontrado en origen) — se emite el alias "
                    f"literal; verifique que el destino lo reutilice")
            grouped[alias] = {"artifact": token, "type": "include",
                              "branches": []}
            order.append(alias)
        if branch not in grouped[alias]["branches"]:
            grouped[alias]["branches"].append(branch)
    return [grouped[a] for a in order], warnings


def _updater_artifact_alias_map(env: Dict, artifacts: List[Dict]
                                ) -> Tuple[Dict[str, str], List[str]]:
    """Detecta alias de artifact del ORIGEN referenciados dentro de
    deployPhases del stage (downloadInputs, etc.) y los mapea a tokens
    `artifact_alias_map` de la opción 41 (`$auto:<Tipo>` cuando el tipo
    es único en el origen; alias literal + warning si es ambiguo)."""
    alias_to_art = {a.get("alias"): a for a in artifacts if a.get("alias")}
    type_count: Dict[str, int] = {}
    for a in artifacts:
        t = a.get("type") or "Build"
        type_count[t] = type_count.get(t, 0) + 1

    found: List[str] = []

    def _walk(node):
        if isinstance(node, dict):
            for key in ("alias", "artifactAlias"):
                v = node.get(key)
                if (isinstance(v, str) and v in alias_to_art
                        and v not in found):
                    found.append(v)
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    for phase in env.get("deployPhases", []):
        _walk(phase)

    mapping: Dict[str, str] = {}
    warnings: List[str] = []
    for alias in found:
        art = alias_to_art[alias]
        atype = art.get("type") or "Build"
        if type_count.get(atype, 0) == 1:
            mapping[alias] = f"$auto:{atype}"
        else:
            mapping[alias] = alias
            warnings.append(
                f"stage '{env.get('name')}': deployPhases usa '{alias}' "
                f"con tipo '{atype}' repetido en el origen — "
                f"artifact_alias_map emitido con alias literal; "
                f"verifique el alias en el destino")
    return mapping, warnings


def build_updater_template(defn_clean: Dict, source_def: Dict) -> Dict:
    """Template DSL del pipeline_updater (opción 41): un `action: add` por
    stage con la definición embebida + variables de nivel release.

    Si el stage tiene artifact filters (conditions tipo 'artifact'), se
    emiten también como reglas `artifact_filters` para que la opción 41
    los reescriba con el alias del artifact del pipeline DESTINO (la
    definición embebida conserva las conditions originales como
    referencia, pero son las reglas las que mandan al aplicar)."""
    envs = defn_clean.get("environments", [])
    artifacts = defn_clean.get("artifacts") or []
    stage_rules: List[Dict] = []
    warnings_all: List[str] = []
    for e in envs:
        rule: Dict = {
            "action": "add",
            "name": e.get("name", "stage"),
            "position": "end",
            "definition": e,
        }
        filters, warns = _updater_artifact_filters(e, artifacts)
        if filters:
            rule["artifact_filters"] = filters
        warnings_all += warns
        alias_map, am_warns = _updater_artifact_alias_map(e, artifacts)
        if alias_map:
            rule["artifact_alias_map"] = alias_map
        warnings_all += am_warns
        stage_rules.append(rule)
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
                "con --target-id.\n"
                "Las reglas `artifact_filters` reemplazan las conditions "
                "de artifact del stage al aplicar (el alias se resuelve "
                "contra los artifacts del pipeline destino vía "
                "$auto:<Tipo>); `artifact_alias_map` remapea los alias "
                "referenciados en deployPhases (downloadInputs)."
                + ("\nADVERTENCIAS:\n- " + "\n- ".join(warnings_all)
                   if warnings_all else "")
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


def load_template(path: Path) -> Tuple[Dict, Dict]:
    """Carga una template exportada y devuelve (definition, metadata).

    Acepta la envoltura {metadata, definition} o un dict de definición
    directo (metadata vacía en ese caso).
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: no es un mapping YAML")
    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) \
        else {}
    defn = data.get("definition")
    if isinstance(defn, dict) and "environments" in defn:
        return defn, meta
    if "environments" in data:
        return data, meta
    raise ValueError(f"{path}: no contiene una 'definition' con "
                     "environments")


def load_template_definition(path: Path) -> Dict:
    """Carga solo la definición de una template exportada."""
    defn, _ = load_template(path)
    return defn


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


def backup_definition(defn: Dict, backup_dir: Path,
                      ids_tag: str = "") -> Dict:
    """Backup del destino en JSON + YAML; devuelve {"json": p, "yaml": p}.

    `ids_tag` opcional ('<srcId>-to-<dstId>') va en el nombre del archivo
    para trazabilidad origen→destino.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = _safe_name(defn.get("name"))
    tag = ids_tag or str(defn.get("id"))
    data = {
        "metadata": {"tool": "pipeline_cd_template",
                     "version": __version__,
                     "backupDate": datetime.now().isoformat(),
                     "pipelineId": defn.get("id"),
                     "pipelineName": defn.get("name"),
                     "revision": defn.get("revision")},
        "definition": defn,
    }
    pj = backup_dir / f"BACKUP_DESTINO_{tag}_{safe}_{ts}.json"
    pj.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                  encoding="utf-8")
    py = backup_dir / f"BACKUP_DESTINO_{tag}_{safe}_{ts}.yaml"
    py.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False,
                                 default_flow_style=False),
                  encoding="utf-8")
    return {"json": pj, "yaml": py}


def save_apply_yaml(backup_dir: Path, prefix: str, def_id,
                    name: str, data: Dict, extra_meta: Optional[Dict] = None
                    ) -> Path:
    """Guarda un YAML con prefijo ORIGEN_/UPDATER_ + metadata del apply."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    meta = {"tool": "pipeline_cd_template", "version": __version__,
            "generated": datetime.now().isoformat()}
    if extra_meta:
        meta.update(extra_meta)
    p = backup_dir / f"{prefix}_{def_id}_{_safe_name(name)}_{ts}.yaml"
    p.write_text(yaml.safe_dump({"metadata": meta, "definition": data},
                                allow_unicode=True, sort_keys=False,
                                default_flow_style=False),
                 encoding="utf-8")
    return p


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


def _artifact_alias_map(tpl_def: Dict, target: Dict) -> Dict[str, str]:
    """Mapea alias de artifacts de la template → alias del destino.

    Match por nombre de la definición del artifact (definitionReference.
    definition.name); si no hay match por nombre, por posición. Solo se
    incluyen pares donde el alias difiere.
    """
    tpl_arts = tpl_def.get("artifacts") or []
    tgt_arts = target.get("artifacts") or []
    mapping: Dict[str, str] = {}
    for i, ta in enumerate(tpl_arts):
        alias = ta.get("alias")
        if not alias:
            continue
        tname = ((ta.get("definitionReference") or {})
                 .get("definition") or {}).get("name")
        match = None
        if tname:
            for xa in tgt_arts:
                xname = ((xa.get("definitionReference") or {})
                         .get("definition") or {}).get("name")
                if xname == tname:
                    match = xa
                    break
        if match is None and i < len(tgt_arts):
            match = tgt_arts[i]
        if match and match.get("alias") and match["alias"] != alias:
            mapping[alias] = match["alias"]
    return mapping


def remap_artifact_aliases(payload: Dict, alias_map: Dict[str, str]
                           ) -> List[str]:
    """Reemplaza alias de artifact del origen por los del destino en las
    condiciones de los environments (artifact filters por stage,
    conditionType 'artifact', campo name/artifactAlias) y en cualquier
    campo 'artifactAlias' del payload.

    Devuelve la lista de envs donde se remapeó algo."""
    if not alias_map:
        return []
    touched: List[str] = []

    def _walk(node, env_name):
        if isinstance(node, dict):
            changed = False
            for key in ("name", "artifactAlias", "alias"):
                v = node.get(key)
                if isinstance(v, str) and v in alias_map:
                    node[key] = alias_map[v]
                    changed = True
            if changed and env_name and env_name not in touched:
                touched.append(env_name)
            for v in node.values():
                _walk(v, env_name)
        elif isinstance(node, list):
            for v in node:
                _walk(v, env_name)

    for env in payload.get("environments", []):
        # Solo condiciones/triggers del env — no tocar su 'name'
        for field in ("conditions", "triggers", "preDeploymentGates",
                      "postDeploymentGates", "deployPhases"):
            if field in env:
                _walk(env[field], env.get("name"))
    return touched


def apply_template(client: AzdoClient, target_id: int, tpl_def: Dict,
                   new_name: str = "", new_path: str = "",
                   dry_run: bool = False,
                   backup_dir: Optional[Path] = None,
                   preserve: Optional[List[str]] = None,
                   strategy: str = "merge",
                   overwrite: str = "ask",
                   update_vars: bool = False,
                   ask_fn=None,
                   decisions: Optional[Dict[str, bool]] = None,
                   comment: str = "",
                   template_comment: str = "",
                   description: Optional[str] = None,
                   source_id=None) -> Dict:
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

    # Tag '<srcId>-to-<dstId>' para los archivos del apply (trazabilidad
    # origen→destino en BACKUP_DESTINO / ORIGEN / UPDATER).
    ids = _ids_tag(source_id, target_id)

    # Backup del destino siempre que haya backup_dir (archivo local, no
    # toca AzDO) — y se relee el YAML como fuente de merge/preserve.
    backup_paths: Optional[Dict] = None
    preserve_src = target
    if backup_dir is not None:
        backup_paths = backup_definition(target, backup_dir, ids)
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

    # Descripción: la 'description' de la template es la del pipeline
    # ORIGEN — no aplica al destino. Por defecto se conserva la del
    # destino; --description la sobreescribe explícitamente.
    if description is not None:
        payload["description"] = description
    elif preserve_src.get("description"):
        payload["description"] = preserve_src["description"]

    if preserve:
        applied, skipped = preserve_from_target(payload, preserve_src,
                                                preserve)
        if applied:
            summary.append("preservado del destino: " + ", ".join(applied))
        if skipped:
            summary.append("preserve sin valor en destino: "
                           + ", ".join(skipped))

    # Si se preservaron los artifacts del destino, las condiciones de los
    # stages traídos de la template referencian alias del ORIGEN que no
    # existen en el destino → remapear al alias destino (artifact filters).
    if preserve and "artifacts" in preserve:
        alias_map = _artifact_alias_map(tpl_def, preserve_src)
        if alias_map:
            touched = remap_artifact_aliases(payload, alias_map)
            summary.append(
                "alias de artifact remapeados: "
                + ", ".join(f"{k}→{v}" for k, v in sorted(alias_map.items())))
            if touched:
                summary.append("  en stages: " + ", ".join(touched))

    unresolved: List[str] = []
    payload = resolve_target_placeholders(payload, preserve_src, unresolved)
    if unresolved:
        summary.append("⚠ placeholders sin resolver: "
                       + ", ".join(sorted(set(unresolved))))

    # VS402874: los ranks de los stages deben ser naturales consecutivos
    # desde 1 — tras merge/preserve hay que renumerarlos.
    for i, env in enumerate(payload.get("environments", []), 1):
        env["rank"] = i

    # Comentario del PUT (historial AzDO) = resumen de todo lo actualizado:
    # el diff de stages/variables, target, estrategia, preserve aplicado,
    # alias remapeados y placeholders. Se construye al final, cuando el
    # summary ya recoge todos los cambios. El encabezado es --comment,
    # o el tag comment/description de la template, o uno generado.
    head = (comment or template_comment
            or f"pipeline_cd_template v{__version__} — apply a "
               f"definition {target_id}")
    change_lines = [
        l for l in summary
        if not l.startswith(("backup ", "origen yaml:", "updater yaml:",
                             "comentario PUT:", "descripción:"))]
    payload["comment"] = "\n".join([head] + change_lines)
    summary.append(f"comentario PUT: {payload['comment'][:160]}")
    summary.append(
        f"descripción: {(payload.get('description') or '')[:120]}")

    # Siempre guardar los YAML del origen (template) y del updater
    # resultante (payload final) junto al BACKUP_DESTINO.
    origen_yaml: Optional[Path] = None
    updater_yaml: Optional[Path] = None
    if backup_dir is not None:
        extra = {"targetId": target_id, "strategy": strategy,
                 "dryRun": dry_run}
        origen_yaml = save_apply_yaml(
            backup_dir, "ORIGEN", ids,
            tpl_def.get("name", "template"), tpl_def, extra)
        # El UPDATER documenta en su metadata el resumen de lo aplicado
        # (mismo reporte que se muestra en consola).
        updater_yaml = save_apply_yaml(
            backup_dir, "UPDATER", ids,
            payload.get("name", "target"), payload,
            {**extra, "comment": list(summary)})
        summary.append(f"origen yaml: {origen_yaml}")
        summary.append(f"updater yaml: {updater_yaml}")

    if dry_run:
        return {"backup": backup_paths, "origen_yaml": origen_yaml,
                "updater_yaml": updater_yaml, "result": None,
                "summary": summary, "payload": payload,
                "preserve_applied": applied if preserve else []}

    result = client.put(f"{client.base}/definitions/{target_id}",
                        payload, params={"api-version": "7.1"})
    return {"backup": backup_paths, "origen_yaml": origen_yaml,
            "updater_yaml": updater_yaml, "result": result,
            "summary": summary, "payload": payload,
            "preserve_applied": applied if preserve else []}


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE + CLI
# ═══════════════════════════════════════════════════════════════════════════════

def _print(msg: str = "", style: str = ""):
    _record(msg, style)
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
    _record("[Definición]", "bold cyan")
    for l in lines:
        _record(l, "cyan")
    if console:
        console.print(Panel("\n".join(lines), title="Definición",
                            expand=False))
    else:
        print("\n".join("  " + l for l in lines))


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTE DE EVIDENCIA HTML
# ═══════════════════════════════════════════════════════════════════════════════

_EVIDENCE_CSS = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f2f5;
           padding: 24px; }
    .wrap { max-width: 1100px; margin: 0 auto; }
    .card { background: #fff; border-radius: 10px; padding: 24px;
            margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
    h1 { color: #2b579a; font-size: 22px; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 12px;
             font-size: 12px; font-weight: bold; margin-left: 10px;
             vertical-align: middle; }
    .badge-interactive { background: #d1ecf1; color: #0c5460; }
    .badge-cli { background: #e2e3e5; color: #383d41; }
    .badge-dryrun { background: #fff3cd; color: #856404; }
    .badge-applied { background: #d4edda; color: #155724; }
    .badge-cancelled { background: #f8d7da; color: #721c24; }
    .muted { color: #777; font-size: 13px; }
    table.meta { width: 100%; border-collapse: collapse; margin-top: 14px; }
    table.meta th, table.meta td { text-align: left; padding: 8px 10px;
        border-bottom: 1px solid #eee; font-size: 13px; }
    table.meta th { width: 190px; color: #555; background: #f8f9fa;
        font-weight: 600; }
    h2 { color: #2b579a; font-size: 16px; margin-bottom: 12px; }
    pre.console { background: #1e1e2e; color: #d4d4d4; padding: 18px;
        border-radius: 8px; font-family: 'Cascadia Code', Consolas, monospace;
        font-size: 12.5px; line-height: 1.5; overflow-x: auto;
        white-space: pre-wrap; word-break: break-word; }
    ul.files { list-style: none; }
    ul.files li { padding: 6px 0; border-bottom: 1px solid #f0f0f0;
        font-family: Consolas, monospace; font-size: 12.5px; }
    ul.files .flabel { color: #2b579a; font-weight: 600; }
    .footer { text-align: center; color: #999; font-size: 12px;
              margin-top: 10px; }
"""


# Mapa de estilos Rich usados por el script → CSS (fallback cuando Rich no
# está instalado; con Rich se usa console.export_html, que reproduce los
# colores exactos del terminal).
_STYLE_COLORS = {
    "black": "#495057", "red": "#ff6b6b", "green": "#51cf66",
    "yellow": "#ffd43b", "blue": "#74c0fc", "magenta": "#e599f7",
    "cyan": "#66d9e8", "white": "#f1f3f5", "orange": "#ffa94d",
    "purple": "#b197fc", "grey": "#adb5bd", "gray": "#adb5bd",
}


def _style_to_css(style: str) -> str:
    """Traduce un estilo Rich ('bold cyan', 'dim', ...) a declaraciones CSS."""
    decls = []
    for tok in (style or "").split():
        if tok == "bold":
            decls.append("font-weight:700")
        elif tok in ("dim", "faint"):
            decls.append("opacity:.6")
        elif tok == "italic":
            decls.append("font-style:italic")
        elif tok == "underline":
            decls.append("text-decoration:underline")
        elif tok in _STYLE_COLORS:
            decls.append(f"color:{_STYLE_COLORS[tok]}")
    return ";".join(decls)


def _console_section_html() -> str:
    """HTML de la salida de consola con los colores del terminal.

    Con Rich disponible usa console.export_html (fidelidad total: colores,
    negritas, paneles, tablas). Sin Rich renderiza el transcript (texto,
    estilo) como spans con el mapa _STYLE_COLORS sobre fondo oscuro.
    """
    if console is not None:
        try:
            from rich.terminal_theme import MONOKAI
            # code_format="{code}": solo los spans estilizados (sin <html>
            # embebido); el <pre class="console"> aporta el fondo oscuro.
            frag = console.export_html(theme=MONOKAI, inline_styles=True,
                                       clear=False, code_format="{code}")
            if frag:
                return f'<pre class="console">{frag}</pre>'
        except Exception:
            pass
    lines = []
    for text, style in _TRANSCRIPT:
        css = _style_to_css(style)
        esc = _html.escape(text)
        lines.append(f'<span style="{css}">{esc}</span>' if css else esc)
    return f'<pre class="console">{"\n".join(lines)}</pre>'


def write_evidence_report(report_dir: Path) -> Optional[Path]:
    """Vuelca la salida de consola a un reporte HTML de evidencia.

    Incluye metadatos del run (org/proyecto/modo/parámetros), los archivos
    generados y la salida de consola **con los mismos colores del
    terminal** (export_html de Rich cuando está instalado). Devuelve el
    path escrito o None si no hubo salida.
    """
    if not _TRANSCRIPT:
        return None
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ids = ""
    if _REPORT_META.get("source_id") or _REPORT_META.get("target_id"):
        ids = "_" + _ids_tag(_REPORT_META.get("source_id"),
                             _REPORT_META.get("target_id"))
    path = report_dir / f"EVIDENCIA_pipe_cd_template{ids}_{ts}.html"

    meta = dict(_REPORT_META)
    mode = str(meta.get("mode") or "cli")
    status = str(meta.get("result") or "")
    badge_cls = ("badge-interactive" if mode == "interactivo"
                 else "badge-cli")
    status_html = ""
    if status:
        scls = ("badge-applied" if "aplicado" in status.lower()
                else "badge-dryrun" if "dry" in status.lower()
                else "badge-cancelled")
        status_html = f'<span class="badge {scls}">{_html.escape(status)}</span>'

    meta_rows = [
        ("Herramienta", "Pipeline CD Template (opción 46)"),
        ("Versión", __version__),
        ("Fecha/Hora", str(meta.get("timestamp")
                           or datetime.now().isoformat(timespec="seconds"))),
        ("Organización", str(meta.get("org") or "-")),
        ("Proyecto", str(meta.get("project") or "-")),
        ("Modo", mode),
    ]
    for k in ("source_id", "target_id", "template", "strategy",
              "preserve", "overwrite_stages", "update_vars", "dry_run",
              "comment"):
        v = meta.get(k)
        if v not in (None, "", []):
            meta_rows.append((k.replace("_", " ").title(), str(v)))

    files = meta.get("files") or []
    files_html = ""
    if files:
        items = "".join(
            f'<li><span class="flabel">{_html.escape(str(lbl))}:</span> '
            f'{_html.escape(str(p))}</li>'
            for lbl, p in files)
        files_html = (f'<div class="card"><h2>📁 Archivos generados</h2>'
                      f'<ul class="files">{items}</ul></div>')

    console_block = _console_section_html()
    html_doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Evidencia — Pipeline CD Template {ts}</title>
<style>{_EVIDENCE_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>📋 Reporte de Evidencia <span class="badge {badge_cls}">{_html.escape(mode.upper())}</span>{status_html}</h1>
    <p class="muted">Salida completa de la ejecución de Pipeline CD Template</p>
    <table class="meta">
      {''.join(f'<tr><th>{_html.escape(k)}</th><td>{_html.escape(v)}</td></tr>' for k, v in meta_rows)}
    </table>
  </div>
  {files_html}
  <div class="card">
    <h2>🖥️ Salida de consola</h2>
    {console_block}
  </div>
  <div class="footer">DevSecOps Toolbox — pipeline_cd_template v{__version__} — generado {ts}</div>
</div>
</body>
</html>"""
    path.write_text(html_doc, encoding="utf-8")
    return path


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
    p.add_argument("--comment", default="",
                   help="apply: encabezado del comentario de revisión del "
                        "PUT (historial AzDO) — se le agrega el resumen de "
                        "los cambios aplicados. Default: tag 'comment'/"
                        "'description' de la template")
    p.add_argument("--description", default=None,
                   help="apply: descripción de la definición en el PUT "
                        "(default: conserva la del destino, no la del "
                        "pipeline origen)")
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
        v = Prompt.ask(prompt, default=default) if default \
            else Prompt.ask(prompt)
    else:
        sfx = f" [{default}]" if default else ""
        v = input(f"{prompt}{sfx}: ").strip()
        v = v or default
    # Evidencia: la respuesta del usuario no queda en el buffer de Rich —
    # la ecoamos en dim para que el export HTML la incluya, y registramos
    # pregunta→respuesta en el transcript de respaldo.
    if console:
        console.print(f"  → {v}", style="dim")
    _record(f"{prompt} -> {v}", "dim")
    return v


def interactive(args) -> argparse.Namespace:
    cfg_org, cfg_proj = "", ""
    try:
        cfg_org, cfg_proj, _ = get_azdo_params(args)
    except SystemExit:
        pass
    _REPORT_META["mode"] = "interactivo"
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
        args.comment = _ask(
            "  Comentario del PUT (encabezado; se agrega el resumen "
            "de cambios)", args.comment)
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

    _REPORT_META.update({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": _REPORT_META.get("mode") or "cli",
        "org": org, "project": project,
        "source_id": args.source_id or None,
        "target_id": args.target_id or None,
        "template": args.template or None,
        "strategy": args.strategy,
        "preserve": args.preserve or ",".join(DEFAULT_PRESERVE_PATHS),
        "overwrite_stages": args.overwrite_stages,
        "update_vars": args.update_vars,
        "dry_run": args.dry_run,
    })

    out_dir = (Path(args.output_dir) if args.output_dir
               else resolve_outcome_dir() / "templates")
    backup_dir = (Path(args.backup_dir) if args.backup_dir
                  else resolve_outcome_dir() / "backups" / "template")

    _print(f"Pipeline CD Template v{__version__} — {org}/{project}",
           "bold cyan")

    tpl_def: Optional[Dict] = None
    tpl_meta: Dict = {}

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
        _record_files(("Template", p) for p in written)
        if not args.target_id:
            _print("\nÚsala con opción 41 (updater) o con esta misma "
                   "opción: --template <archivo> --target-id <id>", "dim")
        tpl_def = clean_definition_for_template(source)
        tpl_meta = {
            "name": f"Template de {source.get('name', '?')}",
            "description": (f"Template extraída del pipeline "
                            f"{source.get('id')} "
                            f"'{source.get('name', '?')}'"),
        }

    # ── Apply ────────────────────────────────────────────────────────────
    if args.target_id:
        if tpl_def is None:
            if not args.template:
                _print("ERROR: --target-id requiere --source-id o "
                       "--template", "bold red")
                return 1
            try:
                tpl_def, tpl_meta = load_template(Path(args.template))
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

        # Encabezado del comentario del PUT: --comment explícito, o el tag
        # 'comment'/'description' de la template. apply_template le agrega
        # el resumen completo de los cambios aplicados.
        template_comment = (tpl_meta.get("comment")
                            or tpl_meta.get("description") or "")
        _REPORT_META["comment"] = (args.comment or template_comment
                                   or "(auto-resumen)")

        # definitionId del origen para los nombres de archivo: el arg, o
        # metadata.source.definition_id de la template, o el dígito del
        # propio nombre pipe_cd_(full|updater)_<id>_*.yaml.
        apply_src_id = args.source_id or (
            (tpl_meta.get("source") or {}).get("definition_id"))
        if not apply_src_id and args.template:
            mfile = re.search(r"pipe_cd_(?:full|updater)_(\d+)",
                              Path(args.template).name)
            if mfile:
                apply_src_id = int(mfile.group(1))
        if apply_src_id:
            _REPORT_META["source_id"] = apply_src_id

        def _ask_stage(name: str) -> bool:
            if console:
                from rich.prompt import Confirm
                ans = Confirm.ask(
                    f"  Stage '{name}' existe en el destino — "
                    f"¿sobrescribir con la template?", default=False)
                console.print(f"  → {'s' if ans else 'n'}", style="dim")
                _record(f"  ¿Sobrescribir stage '{name}'? -> "
                        f"{'s' if ans else 'n'}", "dim")
                return ans
            ans = _ask(f"  ¿Sobrescribir stage '{name}'? (s/n)", "n")
            return ans.lower().startswith("s")

        res = apply_template(client, args.target_id, tpl_def,
                             new_name=args.new_name, new_path=args.new_path,
                             dry_run=True, preserve=preserve,
                             backup_dir=backup_dir,
                             strategy=args.strategy, overwrite=overwrite,
                             update_vars=args.update_vars,
                             ask_fn=_ask_stage, decisions=decisions,
                             comment=args.comment,
                             template_comment=template_comment,
                             description=args.description,
                             source_id=apply_src_id)
        _print("\nDiff destino ← template:", "bold")
        for l in res["summary"]:
            _print(f"  {l}")

        def _print_files(r):
            files = []
            if r.get("backup"):
                files += [("BACKUP_DESTINO (yaml)", r["backup"]["yaml"]),
                          ("BACKUP_DESTINO (json)", r["backup"]["json"])]
            if r.get("origen_yaml"):
                files.append(("ORIGEN (yaml)", r["origen_yaml"]))
            if r.get("updater_yaml"):
                files.append(("UPDATER (yaml)", r["updater_yaml"]))
            if files:
                _print("\nArchivos generados:", "bold")
                for label, p in files:
                    _print(f"  {label}: {p}", "dim")
                _record_files(files)

        _print_files(res)
        if args.dry_run:
            _REPORT_META["result"] = "dry-run"
            _print("\nDry-run — no se aplicó nada en AzDO "
                   "(los YAML de arriba sí se guardaron).", "yellow")
            return 0
        if not args.yes:
            ans = _ask("\n¿Confirmar PUT sobre el destino? (s/n)", "n")
            if not ans.lower().startswith("s"):
                _REPORT_META["result"] = "cancelado"
                _print("Cancelado.", "yellow")
                return 0
        res = apply_template(client, args.target_id, tpl_def,
                             new_name=args.new_name, new_path=args.new_path,
                             dry_run=False, backup_dir=backup_dir,
                             preserve=preserve, strategy=args.strategy,
                             overwrite=overwrite, update_vars=args.update_vars,
                             ask_fn=_ask_stage, decisions=decisions,
                             comment=args.comment,
                             template_comment=template_comment,
                             description=args.description,
                             source_id=apply_src_id)
        _print_files(res)
        new_def = res["result"]
        _REPORT_META["result"] = f"aplicado — definition {new_def.get('id')}"
        _print(f"\n✓ Aplicado — definition {new_def.get('id')} "
               f"'{new_def.get('name')}' rev {new_def.get('revision')}",
               "bold green")
    return 0


def _run() -> int:
    """main() + reporte de evidencia HTML al finalizar (éxito o error)."""
    report_path: Optional[Path] = None
    rc = 0
    try:
        rc = main()
    except SystemExit:
        raise
    except Exception as e:
        _print(f"\nERROR: {e}", "bold red")
        _REPORT_META["result"] = f"error: {e}"
        rc = 1
    finally:
        try:
            report_path = write_evidence_report(
                resolve_outcome_dir() / "reports")
        except Exception:
            report_path = None
    if report_path:
        _print(f"\n  Evidencia HTML: {report_path}", "dim")
    return rc


if __name__ == "__main__":
    sys.exit(_run())
