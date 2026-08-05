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
DEFAULT_PROJECT = "Compras.RMI"
DEFAULT_TIMEZONE = "America/Mazatlan"
DEFAULT_MONTHS = 6
API_VERSION_DEFS = "7.2-preview.4"
API_VERSION_RELS = "7.2-preview.8"


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
        }, debug)
        if not data or not data.get("value"):
            break
        all_releases.extend(data["value"])
        if len(data["value"]) < top:
            break
        skip += top
    return all_releases


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


def extract_variables(defn: Dict) -> Dict[str, str]:
    """Extrae variables como {nombre: valor}."""
    result = {}
    for k, v in defn.get("variables", {}).items():
        if isinstance(v, dict):
            val = v.get("value", "")
            result[k] = val
        else:
            result[k] = str(v)
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
            "field": f"Stage '{name}'",
            "old_value": "(no existia)",
            "new_value": f"rank={s['rank']}, pre={s['pre_approvals']}, post={s['post_approvals']}",
            "action": "added",
        })
    for name in sorted(set(old_map) - set(new_map)):
        s = old_map[name]
        changes.append({
            "category": "Stage",
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
                    "field": f"Stage '{name}' > {field_label}",
                    "old_value": str(old_s.get(field_key, "")),
                    "new_value": str(new_s.get(field_key, "")),
                    "action": "modified",
                })
    return changes


def diff_variables(old_vars: Dict[str, str], new_vars: Dict[str, str]) -> List[Dict]:
    changes = []
    for k in sorted(set(new_vars) - set(old_vars)):
        changes.append({
            "category": "Variable",
            "field": f"Variable '{k}'",
            "old_value": "(no existia)",
            "new_value": new_vars[k],
            "action": "added",
        })
    for k in sorted(set(old_vars) - set(new_vars)):
        changes.append({
            "category": "Variable",
            "field": f"Variable '{k}'",
            "old_value": old_vars[k],
            "new_value": "(eliminada)",
            "action": "removed",
        })
    for k in sorted(set(old_vars) & set(new_vars)):
        if old_vars[k] != new_vars[k]:
            changes.append({
                "category": "Variable",
                "field": f"Variable '{k}'",
                "old_value": old_vars[k] if old_vars[k] else "(vacio)",
                "new_value": new_vars[k] if new_vars[k] else "(vacio)",
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
            "field": f"Task '{t['displayName']}' ({t['env']})",
            "old_value": "(no existia)",
            "new_value": f"enabled={t['enabled']}",
            "action": "added",
        })
    for key in sorted(old_keys - new_keys):
        t = old_map[key]
        changes.append({
            "category": "Task",
            "field": f"Task '{t['displayName']}' ({t['env']})",
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
                    "field": f"Task '{old_t['displayName']}' ({old_t['env']}) > {field_label}",
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
            "field": f"Artifact '{alias}'",
            "old_value": "(no existia)",
            "new_value": f"type={new_map[alias]['type']}",
            "action": "added",
        })
    for alias in sorted(set(old_map) - set(new_map)):
        changes.append({
            "category": "Artifact",
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
        timeline_events.append({
            "type": "release",
            "id": rel.get("id", 0),
            "name": rel.get("name", ""),
            "date": rel.get("createdOn", ""),
            "status": rel.get("status", ""),
            "user": (rel.get("createdBy") or {}).get("displayName", "?"),
        })

    timeline_events.sort(key=lambda x: x.get("date", ""))

    # Stats
    total_revisions = len(revisions)
    total_releases = len(releases)
    succeeded = len([r for r in releases if r.get("status") == "succeeded"])
    failed = len([r for r in releases if r.get("status") == "failed"])
    partial = len([r for r in releases if r.get("status") == "partiallySucceeded"])
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
</div>

<h2>Timeline Interactiva</h2>
<div class="legend">
  <div class="legend-item"><div class="legend-dot" style="background:var(--accent)"></div> Revision (cambio al pipeline)</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div> Release exitoso</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div> Release fallido</div>
  <div class="legend-item"><div class="legend-dot" style="background:var(--yellow)"></div> Release parcial</div>
</div>
<div class="chart-container"><canvas id="timelineChart"></canvas></div>

<h2>Cambios por Revision</h2>
<div class="filter-bar">
  <input type="text" id="diffFilter" placeholder="Filtrar cambios por campo, valor, categoria..." oninput="filterDiffs()">
  <select id="catFilter" onchange="filterDiffs()">
    <option value="">Todas las categorias</option>
    {''.join(f'<option value="{c}">{c}</option>' for c in sorted(cat_counts)) }
  </select>
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

        html += f"""
  <div class="revision-block" data-rev="{rev_num}">
    <div class="revision-header">
      <span class="revision-num">Rev {rev_num}</span>
      <span class="revision-date">{date_str}</span>
      <span class="revision-user">por {user}</span>
      <span class="revision-comment">"{comment}"</span>
      <span style="color:var(--orange);font-weight:bold">{len(diff_list)} cambio(s)</span>
    </div>
    <table class="diff-table">
      <thead><tr><th>Categoria</th><th>Campo</th><th>Valor anterior</th><th></th><th>Valor nuevo</th><th>Accion</th></tr></thead>
      <tbody>
"""
        for d in diff_list:
            cat = html_escape(d.get("category", ""))
            field = html_escape(d.get("field", ""))
            old_val = html_escape(str(d.get("old_value", "")))
            new_val = html_escape(str(d.get("new_value", "")))
            action = d.get("action", "modified")
            badge_class = f"badge-{action}"
            action_label = {"added": "Agregado", "removed": "Eliminado", "modified": "Modificado"}.get(action, action)
            html += f"""        <tr data-cat="{cat}">
          <td>{cat}</td>
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
<table id="releasesTable">
  <thead><tr><th>ID</th><th>Nombre</th><th>Estado</th><th>Fecha</th><th>Creado por</th></tr></thead>
  <tbody>
"""
    STATUS_COLORS = {
        "succeeded": "badge-succeeded",
        "failed": "badge-failed",
        "partiallySucceeded": "badge-partiallySucceeded",
        "cancelled": "badge-cancelled",
    }
    for rel in releases:
        rid = rel.get("id", "?")
        rname = html_escape(rel.get("name", ""))
        rstatus = rel.get("status", "?")
        rdate = format_date(rel.get("createdOn", ""), tz_name)
        ruser = html_escape((rel.get("createdBy") or {}).get("displayName", "?"))
        badge = STATUS_COLORS.get(rstatus, "badge-cancelled")
        html += f"""    <tr>
      <td>{rid}</td>
      <td>{rname}</td>
      <td><span class="badge {badge}">{rstatus}</span></td>
      <td>{rdate}</td>
      <td>{ruser}</td>
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
  }}));

const releasePoints = timelineData
  .filter(e => e.type === 'release')
  .map(e => ({{
    x: e.date,
    y: e.status === 'succeeded' ? 1 : e.status === 'failed' ? 0 : 0.5,
    name: e.name,
    status: e.status,
    user: e.user,
  }}));

new Chart(ctx, {{
  type: 'scatter',
  data: {{
    datasets: [
      {{
        label: 'Revisiones',
        data: revisionPoints,
        backgroundColor: '#58a6ff',
        borderColor: '#58a6ff',
        pointRadius: 8,
        pointHoverRadius: 12,
      }},
      {{
        label: 'Releases exitosos',
        data: releasePoints.filter(p => p.status === 'succeeded'),
        backgroundColor: '#3fb950',
        borderColor: '#3fb950',
        pointRadius: 6,
        pointHoverRadius: 10,
      }},
      {{
        label: 'Releases fallidos',
        data: releasePoints.filter(p => p.status === 'failed'),
        backgroundColor: '#f85149',
        borderColor: '#f85149',
        pointRadius: 6,
        pointHoverRadius: 10,
      }},
      {{
        label: 'Releases parciales',
        data: releasePoints.filter(p => p.status === 'partiallySucceeded'),
        backgroundColor: '#d29922',
        borderColor: '#d29922',
        pointRadius: 6,
        pointHoverRadius: 10,
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
        min: -0.5,
        max: 3,
        title: {{ display: true, text: 'Tipo', color: '#8b949e' }},
        grid: {{ color: '#30363d' }},
        ticks: {{
          color: '#8b949e',
          stepSize: 1,
          callback: function(v) {{
            const labels = {{0: 'Fallido', 0.5: 'Parcial', 1: 'Exitoso', 2: 'Revision', 3: ''}};
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
            return [
              'Release: ' + d.name,
              'Estado: ' + d.status,
              'Usuario: ' + d.user,
            ];
          }},
        }},
      }},
    }},
  }},
}});

// --- Filter diffs ---
function filterDiffs() {{
  const searchText = document.getElementById('diffFilter').value.toLowerCase();
  const catValue = document.getElementById('catFilter').value;

  document.querySelectorAll('.revision-block').forEach(block => {{
    let anyVisible = false;
    block.querySelectorAll('.diff-table tbody tr').forEach(row => {{
      const cat = row.getAttribute('data-cat') || '';
      const text = row.textContent.toLowerCase();
      const catMatch = !catValue || cat === catValue;
      const textMatch = !searchText || text.includes(searchText);
      row.style.display = (catMatch && textMatch) ? '' : 'none';
      if (catMatch && textMatch) anyVisible = true;
    }});
    // Show revision block if it has any visible rows (or no rows at all)
    const hasTable = block.querySelector('.diff-table');
    block.style.display = (!hasTable || anyVisible || (!searchText && !catValue)) ? '' : 'none';
  }});
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
    succeeded = len([r for r in releases if r.get("status") == "succeeded"])
    failed = len([r for r in releases if r.get("status") == "failed"])

    console.print(Panel(
        f"  [bold blue]Revisiones:[/] {len(revisions)}    "
        f"[bold green]Releases OK:[/] {succeeded}    "
        f"[bold red]Releases FAIL:[/] {failed}    "
        f"[bold yellow]Total releases:[/] {len(releases)}    "
        f"[bold purple]Cambios detectados:[/] {total_changes}",
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
        }
        tr = Table(title=f"Releases ({len(releases)} en el periodo)",
                   box=box.SIMPLE_HEAVY, border_style="dim",
                   show_header=True, header_style="bold cyan")
        tr.add_column("ID", width=7, justify="right")
        tr.add_column("Nombre", min_width=38)
        tr.add_column("Estado", width=22)
        tr.add_column("Fecha", width=18, justify="center")
        for r in releases:
            rstat = r.get("status", "?")
            col = STATUS_COLOR.get(rstat, "white")
            tr.add_row(
                str(r.get("id", "?")),
                r.get("name", "?"),
                f"[{col}]{rstat}[/{col}]",
                format_date(r.get("createdOn", ""), tz_name),
            )
        console.print(tr)

    # Diffs detail
    for rev in revisions:
        rev_num = rev.get("revision", 0)
        diff = diffs.get(rev_num, [])
        if not diff:
            continue
        date_str = format_date(rev.get("modifiedOn", "") or rev.get("createdOn", ""), tz_name)
        user = (rev.get("modifiedBy") or rev.get("createdBy") or {}).get("displayName", "?")
        comment = rev.get("comment", "") or "(sin comentario)"

        td = Table(
            title=f"Rev {rev_num} — {date_str} por {user}: \"{comment}\"",
            box=box.SIMPLE_HEAVY, border_style="yellow",
            show_header=True, header_style="bold yellow",
        )
        td.add_column("Categoria", width=12)
        td.add_column("Campo", min_width=30)
        td.add_column("Valor anterior", min_width=25)
        td.add_column("Valor nuevo", min_width=25)
        td.add_column("Accion", width=12)

        for d in diff:
            action = d.get("action", "modified")
            action_col = {"added": "green", "removed": "red", "modified": "yellow"}.get(action, "white")
            td.add_row(
                d.get("category", ""),
                d.get("field", ""),
                str(d.get("old_value", "")),
                str(d.get("new_value", "")),
                f"[{action_col}]{action}[/{action_col}]",
            )
        console.print(td)


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
                "field": d.get("field", ""),
                "old_value": str(d.get("old_value", "")),
                "new_value": str(d.get("new_value", "")),
                "action": d.get("action", ""),
            })

    if not rows:
        rows.append({
            "revision": "", "date": "", "user": "", "comment": "",
            "category": "", "field": "Sin cambios detectados",
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

    # Filter revisions by date range
    min_date = months_ago_iso(args.months)
    revisions_filtered = [
        r for r in revisions
        if parse_iso(r.get("modifiedOn", "") or "") is None
        or parse_iso(r.get("modifiedOn", "") or "") >= parse_iso(min_date)
    ]
    if revisions_filtered:
        revisions = revisions_filtered
    print(f"  {len(revisions)} revisiones en los ultimos {args.months} meses")

    # 3. Download each revision's full definition and compute diffs
    print("Descargando definiciones por revision y calculando diffs...")
    diffs: Dict[int, List[Dict]] = {}
    prev_def: Optional[Dict] = None

    for i, rev in enumerate(revisions):
        rev_num = rev.get("revision", 0)
        rev_def = get_definition_at_revision(
            args.org, args.project, args.definition_id, rev_num, headers, args.debug
        )
        if not rev_def:
            print(f"  [WARN] No se pudo descargar rev {rev_num}")
            diffs[rev_num] = []
            continue

        # Merge metadata from full definition (has modifiedOn/modifiedBy/createdOn/createdBy)
        for k in ("modifiedOn", "modifiedBy", "createdOn", "createdBy", "comment"):
            if k in rev_def and k not in rev:
                rev[k] = rev_def[k]
            elif k in rev_def and not rev.get(k):
                rev[k] = rev_def[k]

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

    # 5. Assemble data
    data = {
        "definition": defn,
        "revisions": revisions,
        "releases": releases,
        "diffs": diffs,
        "project": args.project,
        "range_start": min_date,
        "range_end": datetime.now(dt_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # 6. Console output
    render_console(data, args.timezone)

    # 7. Generate HTML (always)
    html_path = out_dir / f"pipeline_history_{args.definition_id}.html"
    generate_html(data, args.timezone, html_path)
    print(f"\n  HTML interactivo: {html_path}")

    # 8. Export if requested
    if args.output:
        export_results(data, args.output, args.timezone)

    return 0


if __name__ == "__main__":
    sys.exit(main())
