#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
azdo_pipeline_history.py

Evolucion historica de un Pipeline CD (Release Definition) en Azure DevOps.

Recupera todas las revisiones de la definicion y los releases ejecutados
en un rango de fechas (default: 6 meses atras), calcula el diff exacto
entre revisiones consecutivas (stages, variables, tasks, agent pools,
approvals, triggers) y genera un HTML interactivo con:

  - Timeline grafica (Chart.js) con revisiones y releases
  - Tabla detallada de cambios: campo, valor anterior, valor nuevo
  - Metricas de evolucion (frecuencia de cambios, exito por epoca)

Uso:
  python azdo_pipeline_history.py --definition-id 42 --pat <PAT>
  python azdo_pipeline_history.py --id 42 --pat <PAT> --months 6

Autor: Harold Adrian
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone as dt_tz
from html import escape as html_escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None  # type: ignore

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

try:
    from utils import get_output_dir
except ImportError:
    def get_output_dir(default="."):
        env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p

__version__ = "1.0.0"
__author__ = "Harold Adrian"

DEFAULT_ORG_URL = "https://dev.azure.com/Coppel-Retail"
DEFAULT_PROJECT = "Cadena_de_Suministros"
DEFAULT_TIMEZONE = "America/Mazatlan"
DEFAULT_MONTHS = 6
API_VERSION_DEFS = "7.2-preview.4"
API_VERSION_RELS = "7.2-preview.8"
API_VERSION_GIT = "7.1"
API_VERSION_GIT_TAGS = "7.2-preview.1"


# =============================================================================
# ARGS
# =============================================================================
def get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Evolucion historica de un Pipeline CD: revisiones + releases + diff interactivo HTML"
    )
    p.add_argument("--org", "-g", default=DEFAULT_ORG_URL,
                   help=f"URL de la organizacion (default: {DEFAULT_ORG_URL})")
    p.add_argument("--project", "-p", default=DEFAULT_PROJECT,
                   help=f"Nombre del proyecto (default: {DEFAULT_PROJECT})")
    p.add_argument("--pat", required=True,
                   help="PAT con permisos Release (Read)")
    p.add_argument("--definition-id", "--id", dest="definition_id", type=int, required=True,
                   help="ID (definitionId) del Pipeline CD a analizar")
    p.add_argument("--months", type=int, default=DEFAULT_MONTHS,
                   help=f"Meses hacia atras a analizar (default: {DEFAULT_MONTHS})")
    p.add_argument("--timezone", "-tz", default=DEFAULT_TIMEZONE,
                   help=f"Zona horaria (default: {DEFAULT_TIMEZONE})")
    p.add_argument("--output", "-o", choices=["json", "csv", "excel"], default=None,
                   help="Exportar resultados adicionales (json/csv/excel). HTML se genera siempre.")
    p.add_argument("--branch", default="master",
                   help="Rama del repositorio para consultar commits/tags (default: master)")
    p.add_argument("--no-commits", action="store_true",
                   help="No descargar commits/tags del repositorio git vinculado")
    p.add_argument("--debug", action="store_true",
                   help="Mostrar errores HTTP detallados")
    return p.parse_args()


# =============================================================================
# HTTP
# =============================================================================
def make_headers(pat: str) -> Dict:
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def vsrm(org_url: str) -> str:
    return org_url.replace("dev.azure.com", "vsrm.dev.azure.com")


def api_get(url: str, headers: Dict, params: Dict = None, debug: bool = False) -> Optional[Any]:
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code >= 400:
            if debug:
                print(f"[DEBUG] HTTP {resp.status_code} {url}")
                print(f"[DEBUG] {resp.text[:500]}")
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        if debug:
            print(f"[DEBUG] {url}: {e}")
        return None


# =============================================================================
# DATE HELPERS
# =============================================================================
def parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=dt_tz.utc)
        except ValueError:
            continue
    return None


def format_date(s: str, tz_name: str) -> str:
    dt = parse_iso(s)
    if not dt:
        return "—"
    if ZoneInfo:
        try:
            dt = dt.astimezone(ZoneInfo(tz_name))
        except Exception:
            pass
    return dt.strftime("%Y-%m-%d %H:%M")


def months_ago_iso(months: int) -> str:
    dt = datetime.now(dt_tz.utc) - timedelta(days=months * 30)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# =============================================================================
# API CALLS
# =============================================================================
def get_release_definition(org: str, project: str, def_id: int,
                           headers: Dict, debug: bool) -> Optional[Dict]:
    url = f"{vsrm(org)}/{quote(project, safe='')}/_apis/release/definitions/{def_id}"
    return api_get(url, headers, {"api-version": API_VERSION_DEFS}, debug)


def get_definition_revisions(org: str, project: str, def_id: int,
                             headers: Dict, debug: bool) -> List[Dict]:
    """Obtiene la lista de revisiones de la definicion (metadata sin body completo)."""
    url = f"{vsrm(org)}/{quote(project, safe='')}/_apis/release/definitions/{def_id}/revisions"
    data = api_get(url, headers, {"api-version": API_VERSION_DEFS}, debug)
    return data.get("value", []) if data else []


def get_definition_at_revision(org: str, project: str, def_id: int,
                               revision: int, headers: Dict, debug: bool) -> Optional[Dict]:
    """Descarga la definicion completa en una revision especifica."""
    url = f"{vsrm(org)}/{quote(project, safe='')}/_apis/release/definitions/{def_id}"
    return api_get(url, headers, {"api-version": API_VERSION_DEFS, "revision": revision}, debug)


def get_releases_in_range(org: str, project: str, def_id: int,
                          min_date: str, headers: Dict, debug: bool) -> List[Dict]:
    """Obtiene releases desde min_date hasta ahora."""
    url = f"{vsrm(org)}/{quote(project, safe='')}/_apis/release/releases"
    all_releases: List[Dict] = []
    skip = 0
    top = 100
    while True:
        data = api_get(url, headers, {
            "api-version": API_VERSION_RELS,
            "definitionId": def_id,
            "minCreatedDate": min_date,
            "$top": top,
            "$skip": skip,
            "$orderBy": "createdOn asc",
            "$expand": "environments,artifacts",
        }, debug)
        if not data or not data.get("value"):
            break
        all_releases.extend(data["value"])
        if len(data["value"]) < top:
            break
        skip += top
    return all_releases


def get_release_effective_status(rel: Dict) -> Tuple[str, str]:
    """Determina el estatus efectivo del release basandose en el ultimo stage ejecutado.
    Retorna (status, stage_name) donde status es el estatus del ultimo stage
    que no sea 'notStarted', y stage_name es el nombre de ese stage.
    Si ningun stage fue ejecutado, retorna el status global del release."""
    NOT_EXECUTED = {"notStarted", "queued", "scheduled"}
    envs = rel.get("environments", [])
    # Sort by rank descending to find the last executed stage
    sorted_envs = sorted(envs, key=lambda e: e.get("rank", 0), reverse=True)
    for env in sorted_envs:
        estatus = env.get("status", "")
        if estatus and estatus not in NOT_EXECUTED:
            return estatus, env.get("name", "?")
    # No stage was executed, return global status
    return rel.get("status", "?"), ""


def extract_repo_id_from_artifacts(defn: Dict) -> Optional[str]:
    """Extrae el ID del repositorio Git desde los artifacts de la definicion.
    Busca en sourceId (formato '{projectId}:{repoId}' o '{projectId}/{repoId}')
    y en definitionReference.repository.id como fallback."""
    for a in defn.get("artifacts", []):
        if a.get("type", "").lower() == "git":
            # Try definitionReference.repository.id first (most reliable)
            def_ref = a.get("definitionReference", {})
            repo_ref = def_ref.get("repository", {})
            if repo_ref.get("id"):
                return repo_ref["id"]
            # Fallback: parse sourceId
            source_id = a.get("sourceId", "")
            if ":" in source_id:
                parts = source_id.split(":")
                if len(parts) >= 2:
                    return parts[1]  # {projectId}:{repoId}
                return parts[0]
            if "/" in source_id:
                parts = source_id.split("/")
                if len(parts) >= 2:
                    return parts[-1]  # {projectId}/{repoId}
                return parts[0]
            return source_id
    return None


def extract_repo_id_from_releases(releases: List[Dict]) -> Optional[str]:
    """Extrae el ID del repositorio Git desde los artifacts de los releases."""
    for rel in releases:
        for a in rel.get("artifacts", []):
            if a.get("type", "").lower() == "git":
                def_ref = a.get("definitionReference", {})
                repo_ref = def_ref.get("repository", {})
                if repo_ref.get("id"):
                    return repo_ref["id"]
                source_id = a.get("sourceId", "")
                if ":" in source_id:
                    parts = source_id.split(":")
                    if len(parts) >= 2:
                        return parts[1]
                    return parts[0]
                if "/" in source_id:
                    parts = source_id.split("/")
                    if len(parts) >= 2:
                        return parts[-1]
                    return parts[0]
                return source_id
    return None


def get_git_commits(org: str, project: str, repo_id: str, branch: str,
                    min_date: str, headers: Dict, debug: bool,
                    top: int = 500) -> List[Dict]:
    """Obtiene commits de la rama especificada desde min_date hasta ahora."""
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories/{repo_id}/commits"
    params = {
        "api-version": API_VERSION_GIT,
        "searchCriteria.itemVersion.version": branch,
        "searchCriteria.itemVersion.versionType": "branch",
        "searchCriteria.fromDate": min_date,
        "$top": top,
    }
    data = api_get(url, headers, params, debug)
    return data.get("value", []) if data else []


def get_git_tags(org: str, project: str, repo_id: str,
                 headers: Dict, debug: bool) -> List[Dict]:
    """Obtiene annotated tags del repositorio."""
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories/{repo_id}/annotatedtags"
    params = {"api-version": API_VERSION_GIT_TAGS}
    data = api_get(url, headers, params, debug)
    return data.get("value", []) if data else []


# =============================================================================
# DIFF LOGIC
# =============================================================================
def extract_stages(defn: Dict) -> List[Dict]:
    """Extrae stages/environments con metadatos clave."""
    stages = []
    for env in defn.get("environments", []):
        stages.append({
            "name": env.get("name", ""),
            "rank": env.get("rank", 0),
            "pre_approvals": len([
                a for a in env.get("preDeployApprovals", {}).get("approvals", [])
                if not a.get("isAutomated")
            ]),
            "post_approvals": len([
                a for a in env.get("postDeployApprovals", {}).get("approvals", [])
                if not a.get("isAutomated")
            ]),
            "agent_pool": (env.get("deployPhases", [{}])[0].get("deploymentInput", {})
                           .get("queueId", "")),
            "condition": env.get("condition", ""),
        })
    return sorted(stages, key=lambda s: s.get("rank", 0))


def extract_variables(defn: Dict) -> List[Dict]:
    """Extrae variables con scope (pipeline o stage).
    Los secrets se muestran como *** (la API no devuelve el valor real)."""
    result = []
    # Pipeline-level variables
    for k, v in defn.get("variables", {}).items():
        if isinstance(v, dict):
            secret = v.get("isSecret", False)
            val = v.get("value", "")
            if secret or val == "***":
                val = "***"
        else:
            val = str(v)
            secret = False
        result.append({"name": k, "value": val, "scope": "Pipeline", "isSecret": secret})
    # Environment/stage-level variables
    for env in defn.get("environments", []):
        env_name = env.get("name", "")
        for k, v in env.get("variables", {}).items():
            if isinstance(v, dict):
                secret = v.get("isSecret", False)
                val = v.get("value", "")
                if secret or val == "***":
                    val = "***"
            else:
                val = str(v)
                secret = False
            result.append({"name": k, "value": val, "scope": env_name, "isSecret": secret})
    return result


def extract_tasks(defn: Dict) -> List[Dict]:
    """Extrae tasks de todos los deploy phases."""
    tasks = []
    for env in defn.get("environments", []):
        env_name = env.get("name", "")
        for phase in env.get("deployPhases", []):
            for task in phase.get("workflowTasks", []):
                tasks.append({
                    "env": env_name,
                    "displayName": task.get("displayName", ""),
                    "taskId": task.get("taskId", ""),
                    "enabled": task.get("enabled", True),
                    "alwaysRun": task.get("alwaysRun", False),
                    "continueOnError": task.get("continueOnError", False),
                })
    return tasks


def extract_artifacts(defn: Dict) -> List[Dict]:
    """Extrae artefactos vinculados."""
    artifacts = []
    for a in defn.get("artifacts", []):
        artifacts.append({
            "alias": a.get("alias", ""),
            "type": a.get("type", ""),
            "sourceId": a.get("sourceId", ""),
            "isPrimary": a.get("isPrimary", False),
        })
    return artifacts


def extract_triggers(defn: Dict) -> Dict:
    """Extrae triggers de deploy automatico."""
    triggers = []
    for env in defn.get("environments", []):
        env_name = env.get("name", "")
        trigger = env.get("deployPhases", [{}])[0].get("deploymentInput", {})
        auto = trigger.get("releaseTrigger", {})
        if auto:
            triggers.append({
                "env": env_name,
                "triggerType": auto.get("releaseTriggerType", ""),
                "artifactAlias": auto.get("artifactAlias", ""),
                "artifactType": auto.get("artifactType", ""),
            })
    return triggers


def diff_stages(old_stages: List[Dict], new_stages: List[Dict]) -> List[Dict]:
    changes = []
    old_map = {s["name"]: s for s in old_stages}
    new_map = {s["name"]: s for s in new_stages}

    for name in sorted(set(new_map) - set(old_map)):
        s = new_map[name]
        changes.append({
            "category": "Stage",
            "scope": name,
            "field": f"Stage '{name}'",
            "old_value": "(no existia)",
            "new_value": f"rank={s['rank']}, pre={s['pre_approvals']}, post={s['post_approvals']}",
            "action": "added",
        })
    for name in sorted(set(old_map) - set(new_map)):
        s = old_map[name]
        changes.append({
            "category": "Stage",
            "scope": name,
            "field": f"Stage '{name}'",
            "old_value": f"rank={s['rank']}, pre={s['pre_approvals']}, post={s['post_approvals']}",
            "new_value": "(eliminado)",
            "action": "removed",
        })
    for name in sorted(set(old_map) & set(new_map)):
        old_s = old_map[name]
        new_s = new_map[name]
        for field_key, field_label in [
            ("rank", "Rank"), ("pre_approvals", "Pre-approvals"),
            ("post_approvals", "Post-approvals"), ("agent_pool", "Agent Pool"),
            ("condition", "Condition"),
        ]:
            if old_s.get(field_key) != new_s.get(field_key):
                changes.append({
                    "category": "Stage",
                    "scope": name,
                    "field": f"Stage '{name}' > {field_label}",
                    "old_value": str(old_s.get(field_key, "")),
                    "new_value": str(new_s.get(field_key, "")),
                    "action": "modified",
                })
    return changes


def diff_variables(old_vars: List[Dict], new_vars: List[Dict]) -> List[Dict]:
    changes = []
    old_map = {(v["scope"], v["name"]): v for v in old_vars}
    new_map = {(v["scope"], v["name"]): v for v in new_vars}
    all_keys = sorted(set(old_map) | set(new_map))

    for key in all_keys:
        scope, name = key
        in_old = key in old_map
        in_new = key in new_map
        if in_new and not in_old:
            v = new_map[key]
            changes.append({
                "category": "Variable",
                "scope": scope,
                "field": f"Variable '{name}'",
                "old_value": "(no existia)",
                "new_value": v["value"],
                "action": "added",
            })
        elif in_old and not in_new:
            v = old_map[key]
            changes.append({
                "category": "Variable",
                "scope": scope,
                "field": f"Variable '{name}'",
                "old_value": v["value"],
                "new_value": "(eliminada)",
                "action": "removed",
            })
        else:
            old_v = old_map[key]
            new_v = new_map[key]
            if old_v["value"] != new_v["value"]:
                old_val = old_v["value"] if old_v["value"] else "(vacio)"
                new_val = new_v["value"] if new_v["value"] else "(vacio)"
                # Preserve *** for secrets (don't replace with (vacio))
                if old_v.get("isSecret") or old_val == "***":
                    old_val = "***"
                if new_v.get("isSecret") or new_val == "***":
                    new_val = "***"
                changes.append({
                    "category": "Variable",
                    "scope": scope,
                    "field": f"Variable '{name}'",
                    "old_value": old_val,
                    "new_value": new_val,
                    "action": "modified",
                })
    return changes


def diff_tasks(old_tasks: List[Dict], new_tasks: List[Dict]) -> List[Dict]:
    changes = []
    old_keys = {(t["env"], t["displayName"]) for t in old_tasks}
    new_keys = {(t["env"], t["displayName"]) for t in new_tasks}
    old_map = {(t["env"], t["displayName"]): t for t in old_tasks}
    new_map = {(t["env"], t["displayName"]): t for t in new_tasks}

    for key in sorted(new_keys - old_keys):
        t = new_map[key]
        changes.append({
            "category": "Task",
            "scope": t['env'],
            "field": f"Task '{t['displayName']}'",
            "old_value": "(no existia)",
            "new_value": f"enabled={t['enabled']}",
            "action": "added",
        })
    for key in sorted(old_keys - new_keys):
        t = old_map[key]
        changes.append({
            "category": "Task",
            "scope": t['env'],
            "field": f"Task '{t['displayName']}'",
            "old_value": f"enabled={t['enabled']}",
            "new_value": "(eliminada)",
            "action": "removed",
        })
    for key in sorted(old_keys & new_keys):
        old_t = old_map[key]
        new_t = new_map[key]
        for field_key, field_label in [
            ("enabled", "Enabled"), ("alwaysRun", "AlwaysRun"),
            ("continueOnError", "ContinueOnError"),
        ]:
            if old_t.get(field_key) != new_t.get(field_key):
                changes.append({
                    "category": "Task",
                    "scope": old_t['env'],
                    "field": f"Task '{old_t['displayName']}' > {field_label}",
                    "old_value": str(old_t.get(field_key, "")),
                    "new_value": str(new_t.get(field_key, "")),
                    "action": "modified",
                })
    return changes


def diff_artifacts(old_arts: List[Dict], new_arts: List[Dict]) -> List[Dict]:
    changes = []
    old_map = {a["alias"]: a for a in old_arts}
    new_map = {a["alias"]: a for a in new_arts}

    for alias in sorted(set(new_map) - set(old_map)):
        changes.append({
            "category": "Artifact",
            "scope": "Pipeline",
            "field": f"Artifact '{alias}'",
            "old_value": "(no existia)",
            "new_value": f"type={new_map[alias]['type']}",
            "action": "added",
        })
    for alias in sorted(set(old_map) - set(new_map)):
        changes.append({
            "category": "Artifact",
            "scope": "Pipeline",
            "field": f"Artifact '{alias}'",
            "old_value": f"type={old_map[alias]['type']}",
            "new_value": "(eliminado)",
            "action": "removed",
        })
    for alias in sorted(set(old_map) & set(new_map)):
        for field_key in ["type", "sourceId", "isPrimary"]:
            if old_map[alias].get(field_key) != new_map[alias].get(field_key):
                changes.append({
                    "category": "Artifact",
                    "scope": "Pipeline",
                    "field": f"Artifact '{alias}' > {field_key}",
                    "old_value": str(old_map[alias].get(field_key, "")),
                    "new_value": str(new_map[alias].get(field_key, "")),
                    "action": "modified",
                })
    return changes


def compute_full_diff(old_def: Dict, new_def: Dict) -> List[Dict]:
    """Calcula todos los cambios entre dos revisiones de la definicion."""
    changes: List[Dict] = []
    changes.extend(diff_stages(extract_stages(old_def), extract_stages(new_def)))
    changes.extend(diff_variables(extract_variables(old_def), extract_variables(new_def)))
    changes.extend(diff_tasks(extract_tasks(old_def), extract_tasks(new_def)))
    changes.extend(diff_artifacts(extract_artifacts(old_def), extract_artifacts(new_def)))
    return changes


# =============================================================================
# HTML GENERATION
# =============================================================================
def generate_html(data: Dict, tz_name: str, output_path: Path) -> None:
    """Genera HTML interactivo con timeline grafica y tabla de cambios."""
    defn = data["definition"]
    revisions = data["revisions"]
    releases = data["releases"]
    diffs = data["diffs"]
    def_name = defn.get("name", "?")
    def_id = defn.get("id", "?")

    # Timeline data for Chart.js
    timeline_events = []
    for rev in revisions:
        rev_num = rev.get("revision", 0)
        modified = rev.get("modifiedOn", "") or rev.get("createdOn", "")
        modified_by = (rev.get("modifiedBy") or rev.get("createdBy") or {}).get("displayName", "?")
        comment = rev.get("comment", "") or "(sin comentario)"
        diff = diffs.get(rev_num, [])
        timeline_events.append({
            "type": "revision",
            "revision": rev_num,
            "date": modified,
            "user": modified_by,
            "comment": comment,
            "changes": len(diff),
            "diff": diff,
        })
    for rel in releases:
        envs = rel.get("environments", [])
        eff_status, eff_stage = get_release_effective_status(rel)
        timeline_events.append({
            "type": "release",
            "id": rel.get("id", 0),
            "name": rel.get("name", ""),
            "date": rel.get("createdOn", ""),
            "status": eff_status,
            "stage": eff_stage,
            "user": (rel.get("createdBy") or {}).get("displayName", "?"),
            "changes": len(envs),
            "envStatuses": [e.get("status", "?") for e in envs],
        })
    for c in data.get("commits", []):
        timeline_events.append({
            "type": "commit",
            "commitId": c.get("commitId", "")[:8],
            "date": c.get("committer", {}).get("date", "") or c.get("author", {}).get("date", ""),
            "user": (c.get("committer", {}).get("name", "") or
                     c.get("author", {}).get("name", "?")),
            "comment": c.get("comment", ""),
            "changes": len(c.get("changes", [])),
        })
    for t in data.get("git_tags", []):
        tag_date = t.get("createdDate", "") or t.get("taggedObject", {}).get("createdDate", "")
        timeline_events.append({
            "type": "tag",
            "name": t.get("name", ""),
            "date": tag_date,
            "user": t.get("createdBy", {}).get("displayName", "?"),
            "message": t.get("message", ""),
        })

    timeline_events.sort(key=lambda x: x.get("date", ""))

    # Stats
    total_revisions = len(revisions)
    total_releases = len(releases)
    total_commits = len(data.get("commits", []))
    total_tags = len(data.get("git_tags", []))
    eff_statuses = [get_release_effective_status(r)[0] for r in releases]
    succeeded = eff_statuses.count("succeeded")
    failed = eff_statuses.count("failed")
    partial = eff_statuses.count("partiallySucceeded")
    total_changes = sum(len(d) for d in diffs.values())

    # Category breakdown
    cat_counts: Dict[str, int] = {}
    for diff_list in diffs.values():
        for d in diff_list:
            cat = d.get("category", "Other")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pipeline History — {html_escape(def_name)} (ID: {def_id})</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
  :root {{
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #c9d1d9; --text-dim: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d29922;
    --purple: #bc8cff; --orange: #db6d28;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.6;
    padding: 20px; max-width: 1400px; margin: 0 auto;
  }}
  h1 {{ color: var(--accent); margin-bottom: 8px; font-size: 1.8em; }}
  h2 {{ color: var(--text); margin: 24px 0 12px; font-size: 1.3em;
       border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
  .meta {{ color: var(--text-dim); font-size: 0.9em; margin-bottom: 20px; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px; margin-bottom: 24px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border);
           border-radius: 8px; padding: 16px; text-align: center; }}
  .card .num {{ font-size: 2em; font-weight: bold; }}
  .card .label {{ color: var(--text-dim); font-size: 0.85em; margin-top: 4px; }}
  .card.green .num {{ color: var(--green); }}
  .card.red .num {{ color: var(--red); }}
  .card.yellow .num {{ color: var(--yellow); }}
  .card.blue .num {{ color: var(--accent); }}
  .card.purple .num {{ color: var(--purple); }}

  .chart-container {{ background: var(--surface); border: 1px solid var(--border);
                      border-radius: 8px; padding: 16px; margin-bottom: 24px; height: 400px; }}

  table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px;
           background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
           overflow: hidden; }}
  th {{ background: #21262d; color: var(--accent); padding: 10px 12px;
        text-align: left; font-size: 0.85em; text-transform: uppercase; cursor: pointer; }}
  th:hover {{ background: #30363d; }}
  td {{ padding: 10px 12px; border-top: 1px solid var(--border); font-size: 0.9em; }}
  tr:hover {{ background: #1c2128; }}

  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px;
            font-size: 0.75em; font-weight: 600; }}
  .badge-added {{ background: rgba(63,185,80,0.2); color: var(--green); }}
  .badge-removed {{ background: rgba(248,81,73,0.2); color: var(--red); }}
  .badge-modified {{ background: rgba(210,153,34,0.2); color: var(--yellow); }}
  .badge-succeeded {{ background: rgba(63,185,80,0.2); color: var(--green); }}
  .badge-failed {{ background: rgba(248,81,73,0.2); color: var(--red); }}
  .badge-partiallySucceeded {{ background: rgba(210,153,34,0.2); color: var(--yellow); }}
  .badge-cancelled {{ background: rgba(139,148,158,0.2); color: var(--text-dim); }}

  .old-value {{ color: var(--red); font-family: monospace; }}
  .new-value {{ color: var(--green); font-family: monospace; }}
  .arrow {{ color: var(--text-dim); margin: 0 6px; }}

  .revision-block {{ background: var(--surface); border: 1px solid var(--border);
                     border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
  .revision-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
  .revision-num {{ background: var(--accent); color: var(--bg); font-weight: bold;
                   padding: 4px 12px; border-radius: 6px; font-size: 0.85em; }}
  .revision-date {{ color: var(--text-dim); font-size: 0.85em; }}
  .revision-user {{ color: var(--purple); font-size: 0.85em; }}
  .revision-comment {{ color: var(--text); font-style: italic; margin-left: auto; }}

  .filter-bar {{ display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
  .filter-bar input, .filter-bar select {{
    background: var(--surface); border: 1px solid var(--border); color: var(--text);
    padding: 8px 12px; border-radius: 6px; font-size: 0.9em;
  }}
  .filter-bar input {{ flex: 1; min-width: 200px; }}

  .legend {{ display: flex; gap: 16px; margin-bottom: 12px; flex-wrap: wrap; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 0.85em; }}
  .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; }}

  .empty {{ color: var(--text-dim); text-align: center; padding: 40px; }}
  details {{ margin-bottom: 8px; }}
  summary {{ cursor: pointer; color: var(--accent); padding: 8px 0; }}
</style>
</head>
<body>

<h1>Pipeline History: {html_escape(def_name)}</h1>
<div class="meta">
  ID: {def_id} &nbsp;|&nbsp;
  Proyecto: {html_escape(data.get('project', ''))} &nbsp;|&nbsp;
  Rango: {data.get('range_start', '')} → {data.get('range_end', '')} &nbsp;|&nbsp;
  Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>

<div class="cards">
  <div class="card blue"><div class="num">{total_revisions}</div><div class="label">Revisiones (cambios)</div></div>
  <div class="card green"><div class="num">{succeeded}</div><div class="label">Releases exitosos</div></div>
  <div class="card red"><div class="num">{failed}</div><div class="label">Releases fallidos</div></div>
  <div class="card yellow"><div class="num">{partial}</div><div class="label">Parcialmente exitosos</div></div>
  <div class="card purple"><div class="num">{total_changes}</div><div class="label">Cambios detectados</div></div>
  <div class="card"><div class="num">{total_releases}</div><div class="label">Total releases</div></div>
  <div class="card"><div class="num">{total_commits}</div><div class="label">Commits ({html_escape(data.get("branch", "master"))})</div></div>
  <div class="card"><div class="num">{total_tags}</div><div class="label">Tags git</div></div>
</div>

<h2>Timeline Interactiva</h2>
<div class="legend">
  <div class="legend-item"><div class="legend-dot" style="background:var(--accent)"></div> Revision (cambio al pipeline)</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div> Release exitoso</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div> Release fallido</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--yellow)"></div> Release parcial</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--orange)"></div> Release rechazado</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--text-dim)"></div> Release cancelado/otros</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--purple)"></div> Commit ({html_escape(data.get("branch", "master"))})</div>
  <div class="legend-item"><div class="legend-dot" style="background:#f778ba"></div> Tag git</div>
</div>
<div class="chart-container"><canvas id="timelineChart"></canvas></div>

<h2>Desglose por Categoria</h2>
<div style="display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start">
  <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px;width:320px;height:320px">
    <canvas id="categoryChart"></canvas>
  </div>
  <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px;flex:1;min-width:300px">
    <h3 style="color:var(--accent);margin-bottom:12px">Resumen por Categoria</h3>
    {''.join(f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border)"><span style="color:var(--text)">{cat}</span><span style="color:var(--accent);font-weight:bold">{count} cambio(s)</span></div>' for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]))}
  </div>
</div>

<h2>Cambios por Revision</h2>
<div class="filter-bar">
  <input type="text" id="diffFilter" placeholder="Filtrar cambios por campo, valor, categoria..." oninput="filterDiffs()">
  <select id="catFilter" onchange="filterDiffs()">
    <option value="">Todas las categorias</option>
    {''.join(f'<option value="{c}">{c}</option>' for c in sorted(cat_counts)) }
  </select>
  <span id="diffCount" style="color:var(--text-dim);font-size:0.85em;align-self:center"></span>
</div>
<div id="diffsContainer">
"""

    for event in timeline_events:
        if event["type"] != "revision":
            continue
        rev_num = event["revision"]
        date_str = format_date(event["date"], tz_name)
        user = html_escape(event["user"])
        comment = html_escape(event["comment"])
        diff_list = event.get("diff", [])

        if not diff_list:
            html += f"""
  <div class="revision-block" data-rev="{rev_num}">
    <div class="revision-header">
      <span class="revision-num">Rev {rev_num}</span>
      <span class="revision-date">{date_str}</span>
      <span class="revision-user">por {user}</span>
      <span class="revision-comment">"{comment}"</span>
    </div>
    <div class="empty">Sin cambios detectados (o primera revision)</div>
  </div>
"""
            continue

        # Category badges for this revision
        rev_cats = {}
        for d in diff_list:
            cat = d.get("category", "Other")
            rev_cats[cat] = rev_cats.get(cat, 0) + 1
        cat_badges = ' '.join(
            f'<span class="badge badge-modified" style="margin-right:6px">{cat}: {cnt}</span>'
            for cat, cnt in sorted(rev_cats.items())
        )

        html += f"""
  <div class="revision-block" data-rev="{rev_num}">
    <div class="revision-header">
      <span class="revision-num">Rev {rev_num}</span>
      <span class="revision-date">{date_str}</span>
      <span class="revision-user">por {user}</span>
      <span class="revision-comment">"{comment}"</span>
      <span style="color:var(--orange);font-weight:bold">{len(diff_list)} cambio(s)</span>
    </div>
    <div style="margin-bottom:10px">{cat_badges}</div>
    <table class="diff-table">
      <thead><tr><th>Categoria</th><th>Scope</th><th>Campo</th><th>Valor anterior</th><th></th><th>Valor nuevo</th><th>Accion</th></tr></thead>
      <tbody>
"""
        for d in diff_list:
            cat = html_escape(d.get("category", ""))
            scope = html_escape(d.get("scope", ""))
            field = html_escape(d.get("field", ""))
            old_val = html_escape(str(d.get("old_value", "")))
            new_val = html_escape(str(d.get("new_value", "")))
            action = d.get("action", "modified")
            badge_class = f"badge-{action}"
            action_label = {"added": "Agregado", "removed": "Eliminado", "modified": "Modificado"}.get(action, action)
            html += f"""        <tr data-cat="{cat}">
          <td>{cat}</td>
          <td>{scope}</td>
          <td>{field}</td>
          <td class="old-value">{old_val}</td>
          <td class="arrow">→</td>
          <td class="new-value">{new_val}</td>
          <td><span class="badge {badge_class}">{action_label}</span></td>
        </tr>
"""
        html += "      </tbody>\n    </table>\n  </div>\n"

    # Releases table
    html += """
<h2>Releases en el Periodo</h2>
<div class="filter-bar">
  <input type="text" id="releaseFilter" placeholder="Filtrar releases por nombre, estado, stage, artifact..." oninput="filterReleases()">
  <span id="releaseCount" style="color:var(--text-dim);font-size:0.85em;align-self:center"></span>
</div>
<table id="releasesTable">
  <thead><tr><th>ID</th><th>Nombre</th><th>Estado</th><th>Fecha</th><th>Creado por</th><th>Artifact</th><th>Stages</th></tr></thead>
  <tbody>
"""
    STATUS_COLORS = {
        "succeeded": "badge-succeeded",
        "failed": "badge-failed",
        "partiallySucceeded": "badge-partiallySucceeded",
        "cancelled": "badge-cancelled",
        "abandoned": "badge-cancelled",
        "rejected": "badge-failed",
        "draft": "badge-cancelled",
        "inProgress": "badge-partiallySucceeded",
        "notDeployed": "badge-cancelled",
        "pending": "badge-partiallySucceeded",
    }
    STATUS_LABELS = {
        "succeeded": "Exitoso", "failed": "Fallido",
        "partiallySucceeded": "Parcial", "cancelled": "Cancelado",
        "abandoned": "Abandonado", "rejected": "Rechazado",
        "draft": "Borrador", "inProgress": "En progreso",
        "notDeployed": "No desplegado", "pending": "Pendiente",
    }
    ENV_STATUS_LABELS = {
        "succeeded": "ok", "failed": "fail",
        "partiallySucceeded": "partial", "cancelled": "cancel",
        "inProgress": "progress", "notDeployed": "pending",
        "queued": "queued", "rejected": "rejected",
        "scheduled": "scheduled", "phaseInProgress": "progress",
        "phaseSucceeded": "ok", "phaseFailed": "fail",
    }
    for rel in releases:
        rid = rel.get("id", "?")
        rname = html_escape(rel.get("name", ""))
        eff_status, eff_stage = get_release_effective_status(rel)
        rstatus = eff_status
        rlabel = STATUS_LABELS.get(rstatus, rstatus)
        if eff_stage:
            rlabel = f"{rlabel} ({eff_stage})"
        rdate = format_date(rel.get("createdOn", ""), tz_name)
        ruser = html_escape((rel.get("createdBy") or {}).get("displayName", "?"))
        badge = STATUS_COLORS.get(rstatus, "badge-cancelled")
        # Artifact info
        artifacts = rel.get("artifacts", [])
        art_str = html_escape(", ".join(
            f"{a.get('alias', '?')}({a.get('type', '?')})"
            for a in artifacts
        ) or "(sin artifact)")
        # Stages info
        envs = rel.get("environments", [])
        stages_parts = []
        for e in envs:
            e_name = html_escape(e.get("name", "?"))
            e_stat = e.get("status", "?")
            e_label = ENV_STATUS_LABELS.get(e_stat, e_stat)
            stages_parts.append(f"{e_name}:{e_label}")
        stages_str = html_escape(", ".join(stages_parts) or "(sin stages)")
        html += f"""    <tr>
      <td>{rid}</td>
      <td>{rname}</td>
      <td><span class="badge {badge}">{rlabel}</span></td>
      <td>{rdate}</td>
      <td>{ruser}</td>
      <td>{art_str}</td>
      <td>{stages_str}</td>
    </tr>
"""
    html += "  </tbody>\n</table>\n"

    # Commits table
    commits_data = data.get("commits", [])
    branch_name = html_escape(data.get("branch", "master"))
    html += f"""
<h2>Commits en rama '{branch_name}' ({len(commits_data)} en el periodo)</h2>
<div class="filter-bar">
  <input type="text" id="commitFilter" placeholder="Filtrar commits por autor, mensaje, hash..." oninput="filterCommits()">
  <span id="commitCount" style="color:var(--text-dim);font-size:0.85em;align-self:center"></span>
</div>
<table id="commitsTable">
  <thead><tr><th>Hash</th><th>Fecha</th><th>Autor</th><th>Mensaje</th><th>Archivos</th></tr></thead>
  <tbody>
"""
    for c in commits_data:
        c_hash = c.get("commitId", "")[:8]
        c_date = format_date(
            c.get("committer", {}).get("date", "") or c.get("author", {}).get("date", ""),
            tz_name,
        )
        c_author = html_escape(
            c.get("committer", {}).get("name", "") or c.get("author", {}).get("name", "?")
        )
        c_comment = html_escape((c.get("comment", "") or "").split("\n")[0][:120])
        c_files = len(c.get("changes", []))
        html += f"""    <tr>
      <td style="font-family:monospace;color:var(--purple)">{c_hash}</td>
      <td>{c_date}</td>
      <td>{c_author}</td>
      <td>{c_comment}</td>
      <td>{c_files}</td>
    </tr>
"""
    html += "  </tbody>\n</table>\n"

    # Tags table
    tags_data = data.get("git_tags", [])
    if tags_data:
        html += f"""
<h2>Tags Git ({len(tags_data)} en el periodo)</h2>
<table id="tagsTable">
  <thead><tr><th>Tag</th><th>Fecha</th><th>Creado por</th><th>Mensaje</th></tr></thead>
  <tbody>
"""
        for t in tags_data:
            t_name = html_escape(t.get("name", ""))
            t_date = format_date(
                t.get("createdDate", "") or t.get("taggedObject", {}).get("createdDate", ""),
                tz_name,
            )
            t_user = html_escape(t.get("createdBy", {}).get("displayName", "?"))
            t_msg = html_escape((t.get("message", "") or "")[:120])
            html += f"""    <tr>
      <td style="font-family:monospace;color:#f778ba">{t_name}</td>
      <td>{t_date}</td>
      <td>{t_user}</td>
      <td>{t_msg}</td>
    </tr>
"""
        html += "  </tbody>\n</table>\n"

    # JavaScript
    timeline_json = json.dumps(timeline_events, default=str)

    html += f"""
<script>
const timelineData = {timeline_json};

// --- Timeline Chart ---
const ctx = document.getElementById('timelineChart').getContext('2d');

const revisionPoints = timelineData
  .filter(e => e.type === 'revision')
  .map(e => ({{
    x: e.date,
    y: 2,
    revision: e.revision,
    user: e.user,
    comment: e.comment,
    changes: e.changes,
    r: Math.max(4, Math.min(20, e.changes * 1.5)),
  }}));

const releasePoints = timelineData
  .filter(e => e.type === 'release')
  .map(e => ({{
    x: e.date,
    y: e.status === 'succeeded' ? 1 : e.status === 'failed' ? 0 : e.status === 'partiallySucceeded' ? 0.5 : e.status === 'rejected' ? -0.5 : -1,
    name: e.name,
    status: e.status,
    stage: e.stage,
    user: e.user,
    changes: e.changes,
    envStatuses: e.envStatuses,
    r: Math.max(4, Math.min(20, e.changes * 1.5)),
  }}));

const commitPoints = timelineData
  .filter(e => e.type === 'commit')
  .map(e => ({{
    x: e.date,
    y: 3,
    commitId: e.commitId,
    user: e.user,
    comment: e.comment,
    changes: e.changes,
    r: Math.max(3, Math.min(12, e.changes * 0.8)),
  }}));

const tagPoints = timelineData
  .filter(e => e.type === 'tag')
  .map(e => ({{
    x: e.date,
    y: 3.5,
    name: e.name,
    user: e.user,
    message: e.message,
    r: 6,
  }}));

new Chart(ctx, {{
  type: 'scatter',
  data: {{
    datasets: [
      {{
        label: 'Revisiones',
        data: revisionPoints,
        backgroundColor: 'rgba(88,166,255,0.6)',
        borderColor: '#58a6ff',
        pointRadius: ctx => ctx.raw ? ctx.raw.r : 8,
        pointHoverRadius: ctx => ctx.raw ? ctx.raw.r + 4 : 12,
      }},
      {{
        label: 'Releases exitosos',
        data: releasePoints.filter(p => p.status === 'succeeded'),
        backgroundColor: 'rgba(63,185,80,0.6)',
        borderColor: '#3fb950',
        pointRadius: ctx => ctx.raw ? ctx.raw.r : 6,
        pointHoverRadius: ctx => ctx.raw ? ctx.raw.r + 4 : 10,
      }},
      {{
        label: 'Releases fallidos',
        data: releasePoints.filter(p => p.status === 'failed'),
        backgroundColor: 'rgba(248,81,73,0.6)',
        borderColor: '#f85149',
        pointRadius: ctx => ctx.raw ? ctx.raw.r : 6,
        pointHoverRadius: ctx => ctx.raw ? ctx.raw.r + 4 : 10,
      }},
      {{
        label: 'Releases parciales',
        data: releasePoints.filter(p => p.status === 'partiallySucceeded'),
        backgroundColor: 'rgba(210,153,34,0.6)',
        borderColor: '#d29922',
        pointRadius: ctx => ctx.raw ? ctx.raw.r : 6,
        pointHoverRadius: ctx => ctx.raw ? ctx.raw.r + 4 : 10,
      }},
      {{
        label: 'Releases rechazados',
        data: releasePoints.filter(p => p.status === 'rejected'),
        backgroundColor: 'rgba(219,109,40,0.6)',
        borderColor: '#db6d28',
        pointRadius: ctx => ctx.raw ? ctx.raw.r : 6,
        pointHoverRadius: ctx => ctx.raw ? ctx.raw.r + 4 : 10,
      }},
      {{
        label: 'Releases cancelados/otros',
        data: releasePoints.filter(p => !['succeeded','failed','partiallySucceeded','rejected'].includes(p.status)),
        backgroundColor: 'rgba(139,148,158,0.6)',
        borderColor: '#8b949e',
        pointRadius: ctx => ctx.raw ? ctx.raw.r : 6,
        pointHoverRadius: ctx => ctx.raw ? ctx.raw.r + 4 : 10,
      }},
      {{
        label: 'Commits',
        data: commitPoints,
        backgroundColor: 'rgba(188,140,255,0.5)',
        borderColor: '#bc8cff',
        pointRadius: ctx => ctx.raw ? ctx.raw.r : 4,
        pointHoverRadius: ctx => ctx.raw ? ctx.raw.r + 3 : 8,
      }},
      {{
        label: 'Tags',
        data: tagPoints,
        backgroundColor: 'rgba(247,120,186,0.7)',
        borderColor: '#f778ba',
        pointStyle: 'rectRot',
        pointRadius: ctx => ctx.raw ? ctx.raw.r : 6,
        pointHoverRadius: ctx => ctx.raw ? ctx.raw.r + 3 : 10,
      }},
    ],
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    scales: {{
      x: {{
        type: 'time',
        time: {{ unit: 'month' }},
        title: {{ display: true, text: 'Fecha', color: '#8b949e' }},
        grid: {{ color: '#30363d' }},
        ticks: {{ color: '#8b949e' }},
      }},
      y: {{
        min: -1.5,
        max: 4,
        title: {{ display: true, text: 'Tipo', color: '#8b949e' }},
        grid: {{ color: '#30363d' }},
        ticks: {{
          color: '#8b949e',
          stepSize: 0.5,
          callback: function(v) {{
            const labels = {{'-1': 'Cancelado', '-0.5': 'Rechazado', '0': 'Fallido', '0.5': 'Parcial', '1': 'Exitoso', '2': 'Revision', '3': 'Commits', '3.5': 'Tags', '4': ''}};
            return labels[v] || '';
          }},
        }},
      }},
    }},
    plugins: {{
      legend: {{ labels: {{ color: '#c9d1d9' }} }},
      tooltip: {{
        backgroundColor: '#161b22',
        borderColor: '#30363d',
        borderWidth: 1,
        titleColor: '#58a6ff',
        bodyColor: '#c9d1d9',
        callbacks: {{
          title: function(ctx) {{ return new Date(ctx[0].raw.x).toLocaleString(); }},
          label: function(ctx) {{
            const d = ctx.raw;
            if (d.revision !== undefined) {{
              return [
                'Revision #' + d.revision,
                'Usuario: ' + d.user,
                'Comentario: ' + d.comment,
                'Cambios: ' + d.changes,
              ];
            }}
            if (d.commitId !== undefined) {{
              return [
                'Commit: ' + d.commitId,
                'Usuario: ' + d.user,
                'Comentario: ' + (d.comment || '').split('\\n')[0].substring(0, 80),
                'Archivos: ' + d.changes,
              ];
            }}
            if (d.name !== undefined && d.message !== undefined) {{
              return [
                'Tag: ' + d.name,
                'Usuario: ' + d.user,
                'Mensaje: ' + (d.message || '').substring(0, 80),
              ];
            }}
            return [
              'Release: ' + d.name,
              'Estado: ' + d.status + (d.stage ? ' (' + d.stage + ')' : ''),
              'Usuario: ' + d.user,
              'Stages: ' + d.changes,
              'Detalle: ' + (d.envStatuses || []).join(', '),
            ];
          }},
        }},
      }},
    }},
  }},
}});

// --- Category Doughnut Chart ---
const catCounts = {json.dumps(cat_counts)};
const catCtx = document.getElementById('categoryChart').getContext('2d');
const catColors = ['#58a6ff', '#3fb950', '#f85149', '#d29922', '#bc8cff', '#db6d28', '#8b949e'];
new Chart(catCtx, {{
  type: 'doughnut',
  data: {{
    labels: Object.keys(catCounts),
    datasets: [{{
      data: Object.values(catCounts),
      backgroundColor: catColors.slice(0, Object.keys(catCounts).length),
      borderColor: '#161b22',
      borderWidth: 2,
    }}],
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        position: 'bottom',
        labels: {{ color: '#c9d1d9', font: {{ size: 11 }} }},
      }},
      tooltip: {{
        backgroundColor: '#161b22',
        borderColor: '#30363d',
        borderWidth: 1,
        titleColor: '#58a6ff',
        bodyColor: '#c9d1d9',
      }},
    }},
  }},
}});

// --- Filter diffs ---
function filterDiffs() {{
  const searchText = document.getElementById('diffFilter').value.toLowerCase();
  const catValue = document.getElementById('catFilter').value;
  let totalVisible = 0;

  document.querySelectorAll('.revision-block').forEach(block => {{
    let visibleRows = 0;
    block.querySelectorAll('.diff-table tbody tr').forEach(row => {{
      const cat = row.getAttribute('data-cat') || '';
      const text = row.textContent.toLowerCase();
      const catMatch = !catValue || cat === catValue;
      const textMatch = !searchText || text.includes(searchText);
      row.style.display = (catMatch && textMatch) ? '' : 'none';
      if (catMatch && textMatch) visibleRows++;
    }});
    // Hide entire revision block if no rows match (when filtering)
    const isFiltering = searchText || catValue;
    const showBlock = isFiltering ? visibleRows > 0 : true;
    block.style.display = showBlock ? '' : 'none';
    totalVisible += visibleRows;
  }});

  const countEl = document.getElementById('diffCount');
  if (searchText || catValue) {{
    countEl.textContent = totalVisible + ' coincidencia(s)';
  }} else {{
    countEl.textContent = '';
  }}
}}

// --- Filter releases ---
function filterReleases() {{
  const searchText = document.getElementById('releaseFilter').value.toLowerCase();
  let visible = 0;
  document.querySelectorAll('#releasesTable tbody tr').forEach(row => {{
    const text = row.textContent.toLowerCase();
    const match = !searchText || text.includes(searchText);
    row.style.display = match ? '' : 'none';
    if (match) visible++;
  }});
  const countEl = document.getElementById('releaseCount');
  if (searchText) {{
    countEl.textContent = visible + ' de ' + document.querySelectorAll('#releasesTable tbody tr').length + ' release(s)';
  }} else {{
    countEl.textContent = '';
  }}
}}

// --- Filter commits ---
function filterCommits() {{
  const searchText = document.getElementById('commitFilter').value.toLowerCase();
  let visible = 0;
  document.querySelectorAll('#commitsTable tbody tr').forEach(row => {{
    const text = row.textContent.toLowerCase();
    const match = !searchText || text.includes(searchText);
    row.style.display = match ? '' : 'none';
    if (match) visible++;
  }});
  const countEl = document.getElementById('commitCount');
  if (searchText) {{
    countEl.textContent = visible + ' de ' + document.querySelectorAll('#commitsTable tbody tr').length + ' commit(s)';
  }} else {{
    countEl.textContent = '';
  }}
}}
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# =============================================================================
# CONSOLE OUTPUT
# =============================================================================
def render_console(data: Dict, tz_name: str) -> None:
    if not RICH_AVAILABLE:
        _render_fallback(data, tz_name)
        return

    console = Console()
    defn = data["definition"]
    revisions = data["revisions"]
    releases = data["releases"]
    diffs = data["diffs"]

    console.rule(f"[bold cyan]Pipeline History — {defn.get('name', '?')} (ID: {defn.get('id', '?')})[/]")

    # Summary cards
    total_changes = sum(len(d) for d in diffs.values())
    eff_statuses = [get_release_effective_status(r)[0] for r in releases]
    succeeded = eff_statuses.count("succeeded")
    failed = eff_statuses.count("failed")

    console.print(Panel(
        f"  [bold blue]Revisiones:[/] {len(revisions)}    "
        f"[bold green]Releases OK:[/] {succeeded}    "
        f"[bold red]Releases FAIL:[/] {failed}    "
        f"[bold yellow]Total releases:[/] {len(releases)}    "
        f"[bold purple]Cambios detectados:[/] {total_changes}    "
        f"[bold magenta]Commits:[/] {len(data.get('commits', []))}    "
        f"[bold magenta]Tags:[/] {len(data.get('git_tags', []))}",
        title="Resumen",
        border_style="cyan",
    ))

    # Revisions table
    if revisions:
        t = Table(title="Revisiones del Pipeline", box=box.SIMPLE_HEAVY,
                  border_style="dim", show_header=True, header_style="bold cyan")
        t.add_column("Rev", width=6, justify="right")
        t.add_column("Fecha", width=18)
        t.add_column("Usuario", min_width=20)
        t.add_column("Cambios", width=8, justify="center")
        t.add_column("Comentario", min_width=30)

        for rev in revisions:
            rev_num = rev.get("revision", 0)
            diff = diffs.get(rev_num, [])
            t.add_row(
                str(rev_num),
                format_date(rev.get("modifiedOn", "") or rev.get("createdOn", ""), tz_name),
                (rev.get("modifiedBy") or rev.get("createdBy") or {}).get("displayName", "?"),
                str(len(diff)),
                rev.get("comment", "") or "(sin comentario)",
            )
        console.print(t)

    # Releases table
    if releases:
        STATUS_COLOR = {
            "succeeded": "green", "failed": "red",
            "partiallySucceeded": "yellow", "cancelled": "dim",
            "abandoned": "dim", "rejected": "red",
            "draft": "dim", "inProgress": "blue",
            "notDeployed": "dim", "pending": "blue",
        }
        STATUS_LABEL = {
            "succeeded": "Exitoso", "failed": "Fallido",
            "partiallySucceeded": "Parcial", "cancelled": "Cancelado",
            "abandoned": "Abandonado", "rejected": "Rechazado",
            "draft": "Borrador", "inProgress": "En progreso",
            "notDeployed": "No desplegado", "pending": "Pendiente",
        }
        ENV_STATUS_LABEL = {
            "succeeded": "ok", "failed": "fail",
            "partiallySucceeded": "partial", "cancelled": "cancel",
            "inProgress": "progress", "notDeployed": "pending",
            "queued": "queued", "rejected": "rejected",
            "scheduled": "scheduled", "phaseInProgress": "progress",
            "phaseSucceeded": "ok", "phaseFailed": "fail",
        }
        tr = Table(title=f"Releases ({len(releases)} en el periodo)",
                   box=box.SIMPLE_HEAVY, border_style="dim",
                   show_header=True, header_style="bold cyan",
                   show_lines=False, row_styles=["dim", ""])
        tr.add_column("ID", width=7, justify="right")
        tr.add_column("Nombre", min_width=30)
        tr.add_column("Estado", min_width=20)
        tr.add_column("Fecha", width=18, justify="center")
        tr.add_column("Creado por", min_width=20)
        tr.add_column("Artifact", min_width=20)
        tr.add_column("Stages", min_width=30)
        for r in releases:
            eff_status, eff_stage = get_release_effective_status(r)
            rstat = eff_status
            col = STATUS_COLOR.get(rstat, "white")
            rlabel = STATUS_LABEL.get(rstat, rstat)
            if eff_stage:
                rlabel = f"{rlabel} ({eff_stage})"
            ruser = ((r.get("createdBy") or {}).get("displayName", "?"))
            # Extract artifact info
            artifacts = r.get("artifacts", [])
            art_str = ", ".join(
                f"{a.get('alias', '?')}({a.get('type', '?')})"
                for a in artifacts
            ) or "(sin artifact)"
            # Extract environments/stages status with readable labels
            envs = r.get("environments", [])
            stages_parts = []
            for e in envs:
                e_name = e.get("name", "?")
                e_stat = e.get("status", "?")
                e_label = ENV_STATUS_LABEL.get(e_stat, e_stat)
                stages_parts.append(f"{e_name}:{e_label}")
            stages_str = ", ".join(stages_parts) or "(sin stages)"
            tr.add_row(
                str(r.get("id", "?")),
                r.get("name", "?"),
                f"[{col}]{rlabel}[/{col}]",
                format_date(r.get("createdOn", ""), tz_name),
                ruser,
                art_str,
                stages_str,
            )
        console.print(tr)

    # Unified diffs table
    all_diffs: List[Dict] = []
    for rev in revisions:
        rev_num = rev.get("revision", 0)
        diff = diffs.get(rev_num, [])
        if not diff:
            continue
        date_str = format_date(rev.get("modifiedOn", "") or rev.get("createdOn", ""), tz_name)
        user = (rev.get("modifiedBy") or rev.get("createdBy") or {}).get("displayName", "?")
        comment = rev.get("comment", "") or "(sin comentario)"
        for d in diff:
            all_diffs.append({
                "rev": rev_num,
                "date": date_str,
                "user": user,
                "comment": comment,
                "category": d.get("category", ""),
                "scope": d.get("scope", ""),
                "field": d.get("field", ""),
                "old_value": str(d.get("old_value", "")),
                "new_value": str(d.get("new_value", "")),
                "action": d.get("action", "modified"),
            })

    if all_diffs:
        td = Table(title="Detalle de Cambios por Revision", box=box.SIMPLE_HEAVY,
                   border_style="yellow", show_header=True, header_style="bold yellow",
                   show_lines=False, row_styles=["dim", ""])
        td.add_column("Rev", width=5, justify="right")
        td.add_column("Fecha", width=18)
        td.add_column("Usuario", min_width=20)
        td.add_column("Comentario", min_width=25)
        td.add_column("Categoria", width=12)
        td.add_column("Scope", min_width=12)
        td.add_column("Campo", min_width=30)
        td.add_column("Valor anterior", min_width=25)
        td.add_column("Valor nuevo", min_width=25)
        td.add_column("Accion", width=12)

        for d in all_diffs:
            action = d["action"]
            action_col = {"added": "green", "removed": "red", "modified": "yellow"}.get(action, "white")
            td.add_row(
                str(d["rev"]),
                d["date"],
                d["user"],
                d["comment"],
                d["category"],
                d["scope"],
                d["field"],
                d["old_value"],
                d["new_value"],
                f"[{action_col}]{action}[/{action_col}]",
            )
        console.print(td)

    # Commits table
    commits_data = data.get("commits", [])
    if commits_data:
        tc = Table(title=f"Commits en rama '{data.get('branch', 'master')}' ({len(commits_data)} en el periodo)",
                   box=box.SIMPLE_HEAVY, border_style="magenta",
                   show_header=True, header_style="bold magenta",
                   show_lines=False, row_styles=["dim", ""])
        tc.add_column("Hash", width=10)
        tc.add_column("Fecha", width=18)
        tc.add_column("Autor", min_width=20)
        tc.add_column("Mensaje", min_width=40)
        tc.add_column("Archivos", width=8, justify="center")
        for c in commits_data:
            c_hash = c.get("commitId", "")[:8]
            c_date = format_date(
                c.get("committer", {}).get("date", "") or c.get("author", {}).get("date", ""),
                tz_name,
            )
            c_author = (c.get("committer", {}).get("name", "") or
                        c.get("author", {}).get("name", "?"))
            c_comment = (c.get("comment", "") or "").split("\n")[0][:80]
            c_files = len(c.get("changes", []))
            tc.add_row(c_hash, c_date, c_author, c_comment, str(c_files))
        console.print(tc)

    # Tags table
    tags_data = data.get("git_tags", [])
    if tags_data:
        tt = Table(title=f"Tags Git ({len(tags_data)} en el periodo)",
                   box=box.SIMPLE_HEAVY, border_style="magenta",
                   show_header=True, header_style="bold magenta",
                   show_lines=False, row_styles=["dim", ""])
        tt.add_column("Tag", min_width=20)
        tt.add_column("Fecha", width=18)
        tt.add_column("Creado por", min_width=20)
        tt.add_column("Mensaje", min_width=40)
        for t in tags_data:
            t_name = t.get("name", "")
            t_date = format_date(
                t.get("createdDate", "") or t.get("taggedObject", {}).get("createdDate", ""),
                tz_name,
            )
            t_user = t.get("createdBy", {}).get("displayName", "?")
            t_msg = (t.get("message", "") or "")[:80]
            tt.add_row(t_name, t_date, t_user, t_msg)
        console.print(tt)


def _render_fallback(data: Dict, tz_name: str) -> None:
    defn = data["definition"]
    revisions = data["revisions"]
    releases = data["releases"]
    diffs = data["diffs"]
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  Pipeline History: {defn.get('name', '?')} (ID: {defn.get('id', '?')})")
    print(sep)
    print(f"  Revisiones: {len(revisions)}  |  Releases: {len(releases)}  |  Cambios: {sum(len(d) for d in diffs.values())}")
    print()
    for rev in revisions:
        rev_num = rev.get("revision", 0)
        diff = diffs.get(rev_num, [])
        date_str = format_date(rev.get("modifiedOn", "") or rev.get("createdOn", ""), tz_name)
        user = (rev.get("modifiedBy") or rev.get("createdBy") or {}).get("displayName", "?")
        comment = rev.get("comment", "") or ""
        print(f"  Rev {rev_num} — {date_str} por {user}: \"{comment}\"  ({len(diff)} cambios)")
        for d in diff:
            print(f"    [{d.get('category','')}] {d.get('field','')}: "
                  f"{d.get('old_value','')} -> {d.get('new_value','')} ({d.get('action','')})")
    print()


# =============================================================================
# EXPORT
# =============================================================================
def export_results(data: Dict, fmt: str, tz_name: str) -> None:
    def_id = data["definition"].get("id", "unknown")
    out_dir = get_output_dir()

    if not EXPORT_MANAGER_AVAILABLE:
        print(f"[WARN] ExportManager no disponible. Omitiendo export {fmt}.")
        return

    em = ExportManager(tool_name="azdo_pipeline_history")

    rows: List[Dict] = []
    for rev in data.get("revisions", []):
        rev_num = rev.get("revision", 0)
        diff = data["diffs"].get(rev_num, [])
        for d in diff:
            rows.append({
                "revision": rev_num,
                "date": format_date(rev.get("modifiedOn", "") or rev.get("createdOn", ""), tz_name),
                "user": ((rev.get("modifiedBy") or rev.get("createdBy") or {}).get("displayName", "")),
                "comment": rev.get("comment", ""),
                "category": d.get("category", ""),
                "scope": d.get("scope", ""),
                "field": d.get("field", ""),
                "old_value": str(d.get("old_value", "")),
                "new_value": str(d.get("new_value", "")),
                "action": d.get("action", ""),
            })

    if not rows:
        rows.append({
            "revision": "", "date": "", "user": "", "comment": "",
            "category": "", "scope": "", "field": "Sin cambios detectados",
            "old_value": "", "new_value": "", "action": "",
        })

    if fmt == "json":
        em.export_json(rows)
    elif fmt == "csv":
        em.export_csv(rows)
    elif fmt == "excel":
        em.export_excel(rows)


# =============================================================================
# MAIN
# =============================================================================
def main() -> int:
    args = get_args()

    if not REQUESTS_AVAILABLE:
        print("[ERROR] 'requests' no instalado. Ejecuta: pip install requests")
        return 1

    headers = make_headers(args.pat)
    out_dir = get_output_dir()

    # 1. Get current definition
    print(f"Obteniendo definicion {args.definition_id}...")
    defn = get_release_definition(args.org, args.project, args.definition_id, headers, args.debug)
    if not defn:
        print(f"[ERROR] No se pudo obtener la definicion {args.definition_id}")
        return 1

    def_name = defn.get("name", "?")
    print(f"  Pipeline: {def_name}")

    # 2. Get revisions
    print("Obteniendo revisiones...")
    revisions = get_definition_revisions(args.org, args.project, args.definition_id, headers, args.debug)
    if not revisions:
        print("  [WARN] No se pudieron obtener revisiones o no hay historial.")
        revisions = []

    min_date = months_ago_iso(args.months)
    min_dt = parse_iso(min_date)
    print(f"  Rango: desde {min_date} ({args.months} meses)")

    # 3. Download each revision's full definition, merge metadata, then filter by date
    print("Descargando definiciones por revision...")
    enriched: List[Tuple[Dict, Dict]] = []  # (revision_meta, full_definition)
    for i, rev in enumerate(revisions):
        rev_num = rev.get("revision", 0)
        rev_def = get_definition_at_revision(
            args.org, args.project, args.definition_id, rev_num, headers, args.debug
        )
        if not rev_def:
            print(f"  [WARN] No se pudo descargar rev {rev_num}")
            continue

        for k in ("modifiedOn", "modifiedBy", "createdOn", "createdBy", "comment"):
            if k in rev_def and k not in rev:
                rev[k] = rev_def[k]
            elif k in rev_def and not rev.get(k):
                rev[k] = rev_def[k]
        enriched.append((rev, rev_def))

    # Filter by date using enriched metadata
    revisions_filtered = []
    for rev, rev_def in enriched:
        rev_date_str = rev.get("modifiedOn", "") or rev.get("createdOn", "")
        rev_dt = parse_iso(rev_date_str)
        if rev_dt is None or rev_dt >= min_dt:
            revisions_filtered.append((rev, rev_def))

    revisions = [r[0] for r in revisions_filtered]
    print(f"  {len(revisions)} revisiones en los ultimos {args.months} meses")

    # Compute diffs between consecutive filtered revisions
    print("Calculando diffs...")
    diffs: Dict[int, List[Dict]] = {}
    prev_def: Optional[Dict] = None
    for rev, rev_def in revisions_filtered:
        rev_num = rev.get("revision", 0)
        if prev_def is not None:
            changes = compute_full_diff(prev_def, rev_def)
            diffs[rev_num] = changes
            if changes:
                print(f"  Rev {rev_num}: {len(changes)} cambio(s) detectado(s)")
            else:
                print(f"  Rev {rev_num}: sin cambios detectados")
        else:
            diffs[rev_num] = []
            print(f"  Rev {rev_num}: primera revision (baseline)")
        prev_def = rev_def

    # 4. Get releases in range
    print(f"Obteniendo releases desde {min_date}...")
    releases = get_releases_in_range(args.org, args.project, args.definition_id, min_date, headers, args.debug)
    print(f"  {len(releases)} releases encontrados")

    # 4b. Get git commits and tags (if not disabled)
    commits: List[Dict] = []
    git_tags: List[Dict] = []
    repo_id: Optional[str] = None
    if not args.no_commits:
        # Try definition artifacts first
        repo_id = extract_repo_id_from_artifacts(defn)
        # Fallback: search in release artifacts
        if not repo_id and releases:
            repo_id = extract_repo_id_from_releases(releases)
        if repo_id:
            print(f"Obteniendo commits de rama '{args.branch}' (repo: {repo_id[:8]}...)...")
            if args.debug:
                print(f"  [DEBUG] Artifacts en definicion: {defn.get('artifacts', [])}")
                print(f"  [DEBUG] repo_id extraido: {repo_id}")
            commits = get_git_commits(args.org, args.project, repo_id, args.branch,
                                      min_date, headers, args.debug)
            print(f"  {len(commits)} commits encontrados")
            print(f"Obteniendo tags del repositorio...")
            git_tags = get_git_tags(args.org, args.project, repo_id, headers, args.debug)
            # Filter tags by date
            if git_tags:
                filtered_tags = []
                for t in git_tags:
                    tag_date_str = t.get("taggedObject", {}).get("commitId", "")
                    # Tags API doesn't return dates directly; use creationDate if available
                    tag_date = t.get("createdDate", "") or t.get("taggedObject", {}).get("url", "")
                    if tag_date:
                        tag_dt = parse_iso(tag_date)
                        if tag_dt is None or tag_dt >= min_dt:
                            filtered_tags.append(t)
                    else:
                        filtered_tags.append(t)
                git_tags = filtered_tags
            print(f"  {len(git_tags)} tags en el rango")
        else:
            print("  [WARN] No se encontro repositorio Git en los artifacts")
            if args.debug:
                print(f"  [DEBUG] Artifacts en definicion: {defn.get('artifacts', [])}")
                if releases:
                    print(f"  [DEBUG] Artifacts en primer release: {releases[0].get('artifacts', [])}")

    # 5. Assemble data
    data = {
        "definition": defn,
        "revisions": revisions,
        "releases": releases,
        "diffs": diffs,
        "project": args.project,
        "range_start": min_date,
        "range_end": datetime.now(dt_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commits": commits,
        "git_tags": git_tags,
        "repo_id": repo_id,
        "branch": args.branch,
    }

    # 6. Console output
    render_console(data, args.timezone)

    # 7. Generate HTML (always)
    html_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = out_dir / f"azdo_pipeline_history_{html_timestamp}_{args.definition_id}.html"
    generate_html(data, args.timezone, html_path)
    print(f"\n  HTML interactivo: {html_path}")

    # 8. Export if requested
    if args.output:
        export_results(data, args.output, args.timezone)

    return 0


if __name__ == "__main__":
    sys.exit(main())
