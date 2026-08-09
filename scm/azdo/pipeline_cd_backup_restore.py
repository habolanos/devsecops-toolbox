#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Pipeline CD Backup & Restore

Descarga, restaura, crea, compara y convierte definiciones de Pipeline CD
(Release Definitions) con backup completo al 100%.

Submenu:
  1. Backup Completo (uno o varios, max 500 IDs separados por coma)
  2. Restore Definicion
  3. Crear Pipeline desde Backup
  4. Comparar Backup vs Actual (Diff)
  5. Listar Backups Disponibles
  6. Backup Masivo (todos los pipelines del proyecto)
  7. Convertir Backup JSON -> YAML

Uso:
    # Submenu interactivo
    python pipeline_cd_backup_restore.py --interactive

    # Backup de pipelines especificos
    python pipeline_cd_backup_restore.py --mode backup --pipeline-ids 2758,2759 --org X --project Y --pat Z

    # Backup masivo
    python pipeline_cd_backup_restore.py --mode backup-all --org X --project Y --pat Z

    # Restore
    python pipeline_cd_backup_restore.py --mode restore --backup-files b1.json,b2.json --org X --project Y --pat Z

    # Crear nuevo pipeline desde backup
    python pipeline_cd_backup_restore.py --mode create --backup-file b1.json --new-name "Nuevo-Pipeline" --org X --project Y --pat Z

    # Diff
    python pipeline_cd_backup_restore.py --mode diff --backup-files b1.json --org X --project Y --pat Z

    # Listar backups
    python pipeline_cd_backup_restore.py --mode list

    # Convertir JSON a YAML
    python pipeline_cd_backup_restore.py --mode convert-yaml --backup-files b1.json,b2.json
"""

import argparse
import base64
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


console = Console()

__version__ = "1.0.0"
__author__ = "Harold Adrian"

API_VERSION = "7.0"
MAX_PIPELINE_IDS = 500
DEFAULT_WORKERS = 10
BACKUP_DIR = Path("outcome") / "backups" / "definitions"

SYSTEM_FIELDS_TO_CLEAN = [
    "_links", "self", "web", "artifactsLocation",
    "createdOn", "modifiedOn", "createdBy", "modifiedBy",
    "createdBy@type", "modifiedBy@type",
]


# ═══════════════════════════════════════════════════════════════════════════════
# COLORS FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    MAGENTA = '\033[95m'


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
def load_config() -> Dict:
    config_file = Path(__file__).parent.parent / "config.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                azdo = config.get('azdo', {})
                org_url = azdo.get('organization_url', '')
                organization = org_url.split('/')[-1] if org_url else ''
                return {
                    'organization': organization,
                    'project': azdo.get('project', ''),
                    'pat': azdo.get('pat', ''),
                }
        except Exception:
            pass
    return {}


def create_auth_header(pat: str) -> str:
    credentials = f":{pat}"
    encoded = base64.b64encode(credentials.encode('ascii')).decode('ascii')
    return f"Basic {encoded}"


def normalize_org(org: str) -> str:
    if org.startswith("https://"):
        return org.split('/')[-1]
    return org


def prompt_with_default(prompt_text: str, default_value: str, required: bool = False) -> str:
    default_str = str(default_value) if default_value is not None else ""
    if default_str:
        if prompt_text == "PAT":
            display_default = "****"
        else:
            display_default = default_str
        value = Prompt.ask(f"[bold]{prompt_text}[/bold]", default=display_default)
    else:
        value = Prompt.ask(f"[bold]{prompt_text}[/bold]")
    value = value.strip()
    if not value or (default_str and value == "****" and prompt_text == "PAT"):
        if required and not default_str:
            console.print("[red]Este campo es requerido[/red]")
            return prompt_with_default(prompt_text, default_value, required)
        return default_str
    return value


# ═══════════════════════════════════════════════════════════════════════════════
# API CALLS
# ═══════════════════════════════════════════════════════════════════════════════
def api_get(url: str, pat: str) -> Dict:
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json',
    }
    req = urllib.request.Request(url, headers=headers, method='GET')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))


def api_put(url: str, pat: str, body: Dict) -> Dict:
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json',
    }
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='PUT')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))


def api_post(url: str, pat: str, body: Dict) -> Dict:
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json',
    }
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))


def get_release_definition(org: str, project: str, def_id: int, pat: str) -> Dict:
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{def_id}?api-version={API_VERSION}"
    return api_get(url, pat)


def get_all_release_definitions(org: str, project: str, pat: str, path_filter: str = "") -> List[Dict]:
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions?$top=1000&api-version={API_VERSION}"
    if path_filter:
        url += f"&path={urllib.parse.quote(path_filter)}"
    data = api_get(url, pat)
    return data.get("value", [])


def get_agent_queue_name(org: str, project: str, queue_id: int, pat: str) -> str:
    try:
        url = f"https://dev.azure.com/{org}/{project}/_apis/distributedtask/queues/{queue_id}?api-version={API_VERSION}"
        data = api_get(url, pat)
        return data.get("name", str(queue_id))
    except Exception:
        return str(queue_id)


def get_variable_group_name(org: str, project: str, group_id: int, pat: str) -> str:
    try:
        url = f"https://dev.azure.com/{org}/{project}/_apis/distributedtask/variablegroups/{group_id}?api-version={API_VERSION}"
        data = api_get(url, pat)
        return data.get("name", str(group_id))
    except Exception:
        return str(group_id)


def get_task_group_name(org: str, project: str, task_group_id: str, pat: str) -> str:
    try:
        url = f"https://dev.azure.com/{org}/{project}/_apis/distributedtask/taskgroups/{task_group_id}?api-version={API_VERSION}"
        data = api_get(url, pat)
        return data.get("name", str(task_group_id))
    except Exception:
        return str(task_group_id)


def update_release_definition(org: str, project: str, def_id: int, definition: Dict, pat: str) -> Dict:
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{def_id}?api-version={API_VERSION}"
    return api_put(url, pat, definition)


def create_release_definition(org: str, project: str, definition: Dict, pat: str) -> Dict:
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions?api-version={API_VERSION}"
    return api_post(url, pat, definition)


# ═══════════════════════════════════════════════════════════════════════════════
# RESOLVE NAMES
# ═══════════════════════════════════════════════════════════════════════════════
def resolve_names(definition: Dict, org: str, project: str, pat: str) -> Dict:
    resolved = {"agent_pools": {}, "variable_groups": {}, "task_groups": {}}

    queue_ids = set()
    for env in definition.get("environments", []):
        for phase in env.get("deployPhases", []):
            deployment_input = phase.get("deploymentInput", {})
            qid = deployment_input.get("queueId")
            if qid:
                queue_ids.add(qid)

    for qid in queue_ids:
        resolved["agent_pools"][str(qid)] = get_agent_queue_name(org, project, qid, pat)

    vg_ids = set()
    for vg_ref in definition.get("variableGroups", []):
        vg_ids.add(vg_ref.get("id"))
    for env in definition.get("environments", []):
        for vg_ref in env.get("variableGroups", []):
            vg_ids.add(vg_ref.get("id"))

    for vgid in vg_ids:
        if vgid:
            resolved["variable_groups"][str(vgid)] = get_variable_group_name(org, project, vgid, pat)

    tg_ids = set()
    for env in definition.get("environments", []):
        for phase in env.get("deployPhases", []):
            for task in phase.get("workflowTasks", []):
                tt = task.get("task", {})
                if tt.get("taskGroup"):
                    tg_id = tt.get("id")
                    if tg_id:
                        tg_ids.add(str(tg_id))

    for tgid in tg_ids:
        resolved["task_groups"][tgid] = get_task_group_name(org, project, tgid, pat)

    return resolved


# ═══════════════════════════════════════════════════════════════════════════════
# SECRETS DETECTION
# ═══════════════════════════════════════════════════════════════════════════════
def extract_secrets(definition: Dict) -> List[Dict]:
    secrets = []
    for var_name, var_val in definition.get("variables", {}).items():
        if isinstance(var_val, dict) and var_val.get("isSecret", False):
            secrets.append({"scope": "definition", "name": var_name, "env": None})

    for env in definition.get("environments", []):
        env_name = env.get("name", "Unknown")
        for var_name, var_val in env.get("variables", {}).items():
            if isinstance(var_val, dict) and var_val.get("isSecret", False):
                secrets.append({"scope": "environment", "name": var_name, "env": env_name})

    return secrets


# ═══════════════════════════════════════════════════════════════════════════════
# BACKUP
# ═══════════════════════════════════════════════════════════════════════════════
def backup_single_pipeline(
    def_id: int,
    org: str,
    project: str,
    pat: str,
    backup_dir: Path,
    fmt: str = "json",
) -> Dict:
    try:
        definition = get_release_definition(org, project, def_id, pat)
        resolved = resolve_names(definition, org, project, pat)
        secrets = extract_secrets(definition)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = definition.get("name", f"pipeline-{def_id}")
        safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        revision = definition.get("revision", 0)
        path_val = definition.get("path", "\\")

        backup_data = {
            "metadata": {
                "tool": "pipeline_cd_backup_restore",
                "version": __version__,
                "backupDate": datetime.now().isoformat(),
                "org": org,
                "project": project,
                "pipelineId": def_id,
                "pipelineName": name,
                "revision": revision,
                "pipelinePath": path_val,
            },
            "definition": definition,
            "resolved_names": resolved,
            "secrets_list": secrets,
        }

        backup_dir.mkdir(parents=True, exist_ok=True)
        results = {"pipeline_id": def_id, "name": name, "revision": revision,
                    "secrets_count": len(secrets), "status": "ok", "files": []}

        if fmt in ("json", "both"):
            json_filename = f"backup_def_{def_id}_{safe_name}_{timestamp}.json"
            json_path = backup_dir / json_filename
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            results["files"].append(str(json_path))

        if fmt in ("yaml", "both"):
            yaml_filename = f"backup_def_{def_id}_{safe_name}_{timestamp}.yaml"
            yaml_path = backup_dir / yaml_filename
            yaml_content = humanize_yaml(backup_data)
            with open(yaml_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            results["files"].append(str(yaml_path))

        return results

    except Exception as e:
        return {"pipeline_id": def_id, "name": "", "revision": 0,
                "secrets_count": 0, "status": f"error: {e}", "files": []}


def backup_pipelines(
    pipeline_ids: List[int],
    org: str,
    project: str,
    pat: str,
    fmt: str = "json",
    workers: int = DEFAULT_WORKERS,
) -> List[Dict]:
    backup_dir = BACKUP_DIR
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[cyan]{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Backing up pipelines...", total=len(pipeline_ids))

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(backup_single_pipeline, pid, org, project, pat, backup_dir, fmt): pid
                for pid in pipeline_ids
            }
            for future in as_completed(futures):
                pid = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = {"pipeline_id": pid, "name": "", "revision": 0,
                              "secrets_count": 0, "status": f"error: {e}", "files": []}
                results.append(result)
                status_icon = "OK" if result["status"] == "ok" else "ERR"
                progress.update(task, advance=1,
                                description=f"[cyan]Backing up pipelines... [{status_icon}] ID {pid}")

    return results


def backup_all_pipelines(
    org: str,
    project: str,
    pat: str,
    path_filter: str = "",
    fmt: str = "json",
    workers: int = DEFAULT_WORKERS,
    dry_run: bool = False,
) -> Dict:
    with console.status("[cyan]Obteniendo lista de pipelines...", spinner="dots"):
        definitions = get_all_release_definitions(org, project, pat, path_filter)

    if dry_run:
        console.print(f"[yellow]DRY-RUN: {len(definitions)} pipelines serian respaldados[/yellow]")
        for d in definitions:
            console.print(f"  ID: {d.get('id'):>6}  Name: {d.get('name', 'N/A')}")
        return {"total": len(definitions), "successful": 0, "failed": 0, "backups": []}

    if not definitions:
        console.print("[yellow]No se encontraron pipelines[/yellow]")
        return {"total": 0, "successful": 0, "failed": 0, "backups": []}

    pipeline_ids = [d["id"] for d in definitions]
    console.print(f"[cyan]>>> {len(pipeline_ids)} pipelines encontrados. Iniciando backup...[/cyan]")

    start_time = time.time()
    results = backup_pipelines(pipeline_ids, org, project, pat, fmt, workers)
    duration = time.time() - start_time

    successful = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] != "ok")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    index_path = BACKUP_DIR / f"backup_index_{timestamp}.json"
    index_data = {
        "metadata": {
            "tool": "pipeline_cd_backup_restore",
            "version": __version__,
            "backupDate": datetime.now().isoformat(),
            "org": org,
            "project": project,
            "totalPipelines": len(pipeline_ids),
            "successful": successful,
            "failed": failed,
            "duration": str(datetime.utcfromtimestamp(duration).strftime("%H:%M:%S")),
        },
        "backups": [
            {
                "pipelineId": r["pipeline_id"],
                "pipelineName": r["name"],
                "revision": r["revision"],
                "secrets": r["secrets_count"],
                "status": r["status"],
                "files": r["files"],
            }
            for r in results
        ],
    }
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    return {
        "total": len(pipeline_ids),
        "successful": successful,
        "failed": failed,
        "duration": str(datetime.utcfromtimestamp(duration).strftime("%H:%M:%S")),
        "index_file": str(index_path),
        "backups": results,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# YAML HUMANIZATION
# ═══════════════════════════════════════════════════════════════════════════════
def clean_system_fields(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: clean_system_fields(v)
            for k, v in obj.items()
            if k not in SYSTEM_FIELDS_TO_CLEAN
        }
    elif isinstance(obj, list):
        return [clean_system_fields(item) for item in obj]
    return obj


def humanize_yaml(backup_data: Dict) -> str:
    meta = backup_data.get("metadata", {})
    definition = backup_data.get("definition", {})
    resolved = backup_data.get("resolved_names", {})
    secrets = backup_data.get("secrets_list", [])

    lines = []
    lines.append(f"# {'='*60}")
    lines.append(f"# Pipeline CD Backup -- {meta.get('pipelineName', 'N/A')} (ID: {meta.get('pipelineId', 'N/A')})")
    lines.append(f"# Revision: {meta.get('revision', 'N/A')} | Fecha: {meta.get('backupDate', 'N/A')}")
    lines.append(f"# Org: {meta.get('org', 'N/A')} | Project: {meta.get('project', 'N/A')}")
    lines.append(f"# Path: {meta.get('pipelinePath', 'N/A')}")
    lines.append(f"# {'='*60}")
    lines.append("")

    lines.append("metadata:")
    lines.append(f"  pipeline_id: {meta.get('pipelineId', 'N/A')}")
    lines.append(f"  pipeline_name: \"{meta.get('pipelineName', 'N/A')}\"")
    lines.append(f"  revision: {meta.get('revision', 0)}")
    lines.append(f"  backup_date: \"{meta.get('backupDate', 'N/A')}\"")
    lines.append(f"  path: \"{meta.get('pipelinePath', 'N/A')}\"")
    lines.append("")

    # Variables de definicion
    def_vars = definition.get("variables", {})
    lines.append(f"# {'─'*48}")
    lines.append("# Variables de Definicion")
    lines.append(f"# {'─'*48}")
    if def_vars:
        lines.append("variables:")
        for var_name, var_val in def_vars.items():
            if isinstance(var_val, dict):
                is_secret = var_val.get("isSecret", False)
                value = var_val.get("value")
                if is_secret:
                    lines.append(f"  {var_name}:")
                    lines.append(f"    value: null  # SECRET -- re-ingresar al restaurar")
                    lines.append(f"    is_secret: true")
                else:
                    str_val = str(value) if value is not None else ""
                    lines.append(f"  {var_name}:")
                    lines.append(f"    value: \"{str_val}\"")
                    lines.append(f"    is_secret: false")
            else:
                lines.append(f"  {var_name}: \"{var_val}\"")
    else:
        lines.append("variables: {}")
    lines.append("")

    # Artifacts
    artifacts = definition.get("artifacts", [])
    lines.append(f"# {'─'*48}")
    lines.append("# Artifacts")
    lines.append(f"# {'─'*48}")
    if artifacts:
        lines.append("artifacts:")
        for art in artifacts:
            lines.append(f"  - alias: \"{art.get('alias', 'N/A')}\"")
            lines.append(f"    type: \"{art.get('type', 'N/A')}\"")
            def_ref = art.get("definitionReference", {})
            source_id = def_ref.get("sourceId", {}).get("id", "N/A") if isinstance(def_ref.get("sourceId"), dict) else def_ref.get("sourceId", "N/A")
            lines.append(f"    source_id: \"{source_id}\"")
            lines.append(f"    is_primary: {art.get('isPrimary', False)}")
    else:
        lines.append("artifacts: []")
    lines.append("")

    # Environments / Stages
    environments = definition.get("environments", [])
    lines.append(f"# {'─'*48}")
    lines.append("# Environments / Stages")
    lines.append(f"# {'─'*48}")
    if environments:
        lines.append("environments:")
        for env in environments:
            lines.append(f"  - name: \"{env.get('name', 'N/A')}\"")
            lines.append(f"    rank: {env.get('rank', 'N/A')}")

            # Agent pool
            deploy_phases = env.get("deployPhases", [])
            if deploy_phases:
                di = deploy_phases[0].get("deploymentInput", {})
                qid = di.get("queueId")
                pool_name = resolved.get("agent_pools", {}).get(str(qid), str(qid)) if qid else "N/A"
                lines.append(f"    agent_pool: \"{pool_name}\"")

            # Environment variables
            env_vars = env.get("variables", {})
            if env_vars:
                lines.append(f"    variables:")
                for var_name, var_val in env_vars.items():
                    if isinstance(var_val, dict):
                        is_secret = var_val.get("isSecret", False)
                        value = var_val.get("value")
                        if is_secret:
                            lines.append(f"      {var_name}:")
                            lines.append(f"        value: null  # SECRET")
                            lines.append(f"        is_secret: true")
                        else:
                            str_val = str(value) if value is not None else ""
                            lines.append(f"      {var_name}:")
                            lines.append(f"        value: \"{str_val}\"")
                            lines.append(f"        is_secret: false")
                    else:
                        lines.append(f"      {var_name}: \"{var_val}\"")

            # Approvals
            pre_approvals = env.get("preDeployApprovals", {})
            pre_approvers = pre_approvals.get("approvals", []) if isinstance(pre_approvals, dict) else []
            post_approvals = env.get("postDeployApprovals", {})
            post_approvers = post_approvals.get("approvals", []) if isinstance(post_approvals, dict) else []

            lines.append(f"    pre_deploy_approvals:")
            approver_names = []
            for ap in pre_approvers:
                if isinstance(ap, dict):
                    for a in ap.get("approvers", []):
                        if isinstance(a, dict):
                            approver_names.append(a.get("displayName", a.get("id", "unknown")))
            lines.append(f"      approvers: {approver_names if approver_names else '[]'}")
            lines.append(f"      count: {len(approver_names)}")

            lines.append(f"    post_deploy_approvals:")
            approver_names = []
            for ap in post_approvers:
                if isinstance(ap, dict):
                    for a in ap.get("approvers", []):
                        if isinstance(a, dict):
                            approver_names.append(a.get("displayName", a.get("id", "unknown")))
            lines.append(f"      approvers: {approver_names if approver_names else '[]'}")
            lines.append(f"      count: {len(approver_names)}")

            # Tasks
            tasks = []
            for phase in deploy_phases:
                for task in phase.get("workflowTasks", []):
                    tasks.append(task)

            if tasks:
                lines.append(f"    tasks:")
                for task in tasks:
                    lines.append(f"      - display_name: \"{task.get('displayName', 'N/A')}\"")
                    lines.append(f"        enabled: {task.get('enabled', True)}")
                    tt = task.get("task", {})
                    lines.append(f"        task_type: \"{tt.get('name', 'N/A')}\"")
                    lines.append(f"        version: \"{tt.get('versionSpec', 'N/A')}\"")
                    inputs = task.get("inputs", {})
                    if inputs:
                        lines.append(f"        inputs:")
                        for ik, iv in inputs.items():
                            str_iv = str(iv) if iv is not None else ""
                            lines.append(f"          {ik}: \"{str_iv}\"")
            lines.append("")
    else:
        lines.append("environments: []")
    lines.append("")

    # Triggers
    triggers = definition.get("triggers", [])
    lines.append(f"# {'─'*48}")
    lines.append("# Triggers")
    lines.append(f"# {'─'*48}")
    if triggers:
        lines.append("triggers:")
        for trig in triggers:
            lines.append(f"  - type: \"{trig.get('triggerType', 'N/A')}\"")
            lines.append(f"    enabled: {trig.get('isContinuousDeployment', trig.get('enabled', False))}")
            branch_ref = trig.get("artifactSourceId", "N/A")
            lines.append(f"    branch: \"{branch_ref}\"")
    else:
        lines.append("triggers: []")
    lines.append("")

    # Retention
    retention = definition.get("retentionPolicy", {})
    lines.append(f"# {'─'*48}")
    lines.append("# Retention")
    lines.append(f"# {'─'*48}")
    if retention:
        lines.append("retention_policy:")
        lines.append(f"  days_to_keep: {retention.get('daysToKeep', 'N/A')}")
        lines.append(f"  releases_to_keep: {retention.get('releasesToKeep', 'N/A')}")
    else:
        lines.append("retention_policy: {}")
    lines.append("")

    # Secrets
    lines.append(f"# {'─'*48}")
    lines.append("# Secrets Detectados (requieren re-ingreso)")
    lines.append(f"# {'─'*48}")
    if secrets:
        lines.append("secrets_list:")
        for s in secrets:
            lines.append(f"  - scope: \"{s.get('scope', 'N/A')}\"")
            lines.append(f"    name: \"{s.get('name', 'N/A')}\"")
            lines.append(f"    env: \"{s.get('env', 'N/A')}\"")
    else:
        lines.append("secrets_list: []")
    lines.append("")

    # Resolved names
    lines.append(f"# {'─'*48}")
    lines.append("# Nombres Resueltos")
    lines.append(f"# {'─'*48}")
    lines.append("resolved_names:")
    for category, mappings in resolved.items():
        lines.append(f"  {category}:")
        for kid, kname in mappings.items():
            lines.append(f"    \"{kid}\": \"{kname}\"")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# RESTORE
# ═══════════════════════════════════════════════════════════════════════════════
def load_backup(backup_file: str, backup_path: str = "") -> Dict:
    if not os.path.exists(backup_file) and backup_path:
        if os.path.exists(backup_path):
            for f in os.listdir(backup_path):
                if backup_file in f or f.endswith(backup_file):
                    backup_file = os.path.join(backup_path, f)
                    break

    if not os.path.exists(backup_file):
        raise FileNotFoundError(f"Backup no encontrado: {backup_file}")

    with open(backup_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def restore_definition(
    backup: Dict,
    org: str,
    project: str,
    pat: str,
    dry_run: bool = False,
    secret_values: Optional[Dict[str, str]] = None,
) -> Dict:
    meta = backup.get("metadata", {})
    definition = backup.get("definition", {})
    def_id = meta.get("pipelineId") or definition.get("id")
    secrets = backup.get("secrets_list", [])

    if secret_values:
        for s in secrets:
            var_name = s["name"]
            scope = s["scope"]
            env_name = s.get("env")
            if var_name in secret_values:
                if scope == "definition":
                    if var_name in definition.get("variables", {}):
                        definition["variables"][var_name]["value"] = secret_values[var_name]
                elif scope == "environment" and env_name:
                    for env in definition.get("environments", []):
                        if env.get("name") == env_name:
                            if var_name in env.get("variables", {}):
                                env["variables"][var_name]["value"] = secret_values[var_name]

    if dry_run:
        return {"status": "dry_run", "pipeline_id": def_id, "message": "Dry-run: no se aplicaron cambios"}

    result = update_release_definition(org, project, def_id, definition, pat)
    return {"status": "ok", "pipeline_id": def_id, "result": result}


# ═══════════════════════════════════════════════════════════════════════════════
# CREATE FROM BACKUP
# ═══════════════════════════════════════════════════════════════════════════════
def create_from_backup(
    backup: Dict,
    org: str,
    project: str,
    pat: str,
    new_name: str = "",
) -> Dict:
    definition = backup.get("definition", {})

    for field in ["id", "revision", "createdOn", "modifiedOn", "createdBy", "modifiedBy",
                   "createdBy@type", "modifiedBy@type", "_links"]:
        definition.pop(field, None)

    for env in definition.get("environments", []):
        for field in ["id", "releaseId"]:
            env.pop(field, None)

    if new_name:
        definition["name"] = new_name

    result = create_release_definition(org, project, definition, pat)
    return {"status": "ok", "new_id": result.get("id"), "new_name": result.get("name"), "result": result}


# ═══════════════════════════════════════════════════════════════════════════════
# DIFF
# ═══════════════════════════════════════════════════════════════════════════════
def diff_definitions(backup_def: Dict, current_def: Dict) -> List[Dict]:
    diffs = []

    # Variables de definicion
    bk_vars = backup_def.get("variables", {})
    cur_vars = current_def.get("variables", {})
    all_var_names = set(bk_vars.keys()) | set(cur_vars.keys())
    for var_name in all_var_names:
        bk_val = bk_vars.get(var_name, {}).get("value") if isinstance(bk_vars.get(var_name), dict) else bk_vars.get(var_name)
        cur_val = cur_vars.get(var_name, {}).get("value") if isinstance(cur_vars.get(var_name), dict) else cur_vars.get(var_name)
        if var_name not in cur_vars:
            diffs.append({"category": "variable", "change": "eliminado", "name": var_name,
                          "backup_value": str(bk_val), "current_value": "N/A"})
        elif var_name not in bk_vars:
            diffs.append({"category": "variable", "change": "agregado", "name": var_name,
                          "backup_value": "N/A", "current_value": str(cur_val)})
        elif bk_val != cur_val:
            diffs.append({"category": "variable", "change": "modificado", "name": var_name,
                          "backup_value": str(bk_val), "current_value": str(cur_val)})

    # Environments
    bk_envs = {e.get("name"): e for e in backup_def.get("environments", [])}
    cur_envs = {e.get("name"): e for e in current_def.get("environments", [])}
    all_env_names = set(bk_envs.keys()) | set(cur_envs.keys())

    for env_name in all_env_names:
        if env_name not in cur_envs:
            diffs.append({"category": "environment", "change": "eliminado", "name": env_name,
                          "backup_value": "exists", "current_value": "N/A"})
        elif env_name not in bk_envs:
            diffs.append({"category": "environment", "change": "agregado", "name": env_name,
                          "backup_value": "N/A", "current_value": "exists"})
        else:
            bk_env = bk_envs[env_name]
            cur_env = cur_envs[env_name]
            if bk_env.get("rank") != cur_env.get("rank"):
                diffs.append({"category": "environment_rank", "change": "modificado", "name": env_name,
                              "backup_value": str(bk_env.get("rank")), "current_value": str(cur_env.get("rank"))})

            bk_tasks = set()
            cur_tasks = set()
            for phase in bk_env.get("deployPhases", []):
                for t in phase.get("workflowTasks", []):
                    bk_tasks.add(t.get("displayName", ""))
            for phase in cur_env.get("deployPhases", []):
                for t in phase.get("workflowTasks", []):
                    cur_tasks.add(t.get("displayName", ""))

            for t_name in bk_tasks - cur_tasks:
                diffs.append({"category": "task", "change": "eliminado", "name": f"{env_name}/{t_name}",
                              "backup_value": "exists", "current_value": "N/A"})
            for t_name in cur_tasks - bk_tasks:
                diffs.append({"category": "task", "change": "agregado", "name": f"{env_name}/{t_name}",
                              "backup_value": "N/A", "current_value": "exists"})

    # Artifacts
    bk_arts = {a.get("alias"): a for a in backup_def.get("artifacts", [])}
    cur_arts = {a.get("alias"): a for a in current_def.get("artifacts", [])}
    all_art_aliases = set(bk_arts.keys()) | set(cur_arts.keys())
    for alias in all_art_aliases:
        if alias not in cur_arts:
            diffs.append({"category": "artifact", "change": "eliminado", "name": alias,
                          "backup_value": "exists", "current_value": "N/A"})
        elif alias not in bk_arts:
            diffs.append({"category": "artifact", "change": "agregado", "name": alias,
                          "backup_value": "N/A", "current_value": "exists"})

    # Triggers
    bk_triggers = backup_def.get("triggers", [])
    cur_triggers = current_def.get("triggers", [])
    if len(bk_triggers) != len(cur_triggers):
        diffs.append({"category": "trigger", "change": "modificado", "name": "trigger_count",
                      "backup_value": str(len(bk_triggers)), "current_value": str(len(cur_triggers))})

    return diffs


def print_diff_table(diffs: List[Dict], pipeline_name: str) -> None:
    if not diffs:
        console.print(f"[green]No hay diferencias entre el backup y la definicion actual de {pipeline_name}[/green]")
        return

    tbl = Table(title=f"Diff: {pipeline_name}", show_lines=True)
    tbl.add_column("Categoria", style="cyan", min_width=15)
    tbl.add_column("Cambio", style="bold", min_width=12)
    tbl.add_column("Elemento", min_width=30)
    tbl.add_column("Backup", style="dim", min_width=20)
    tbl.add_column("Actual", style="dim", min_width=20)

    for d in diffs:
        change = d["change"]
        if change == "agregado":
            change_str = "[green]+ Agregado[/green]"
        elif change == "eliminado":
            change_str = "[red]- Eliminado[/red]"
        else:
            change_str = "[yellow]~ Modificado[/yellow]"
        tbl.add_row(d["category"], change_str, d["name"], d["backup_value"], d["current_value"])

    console.print(tbl)


# ═══════════════════════════════════════════════════════════════════════════════
# LIST BACKUPS
# ═══════════════════════════════════════════════════════════════════════════════
def list_backups(backup_dir: Path = None) -> List[Dict]:
    if backup_dir is None:
        backup_dir = BACKUP_DIR

    if not backup_dir.exists():
        return []

    backups = []
    for f in backup_dir.glob("backup_def_*.json"):
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            meta = data.get("metadata", {})
            size = f.stat().st_size
            backups.append({
                "file": f.name,
                "path": str(f),
                "pipeline_id": meta.get("pipelineId", "N/A"),
                "pipeline_name": meta.get("pipelineName", "N/A"),
                "revision": meta.get("revision", 0),
                "backup_date": meta.get("backupDate", "N/A"),
                "secrets_count": len(data.get("secrets_list", [])),
                "size_bytes": size,
                "size_kb": round(size / 1024, 1),
            })
        except Exception:
            continue

    backups.sort(key=lambda x: x["backup_date"], reverse=True)
    return backups


def print_backups_table(backups: List[Dict]) -> None:
    if not backups:
        console.print(f"[yellow]No hay backups disponibles en {BACKUP_DIR}[/yellow]")
        return

    tbl = Table(title="Backups Disponibles", show_lines=True)
    tbl.add_column("#", style="dim", width=4)
    tbl.add_column("Pipeline ID", justify="right", min_width=10)
    tbl.add_column("Pipeline Name", min_width=25)
    tbl.add_column("Revision", justify="right", min_width=8)
    tbl.add_column("Fecha", min_width=20)
    tbl.add_column("Secrets", justify="right", min_width=8)
    tbl.add_column("Tamano", justify="right", min_width=10)

    for idx, b in enumerate(backups, 1):
        tbl.add_row(
            str(idx),
            str(b["pipeline_id"]),
            b["pipeline_name"],
            str(b["revision"]),
            b["backup_date"][:19],
            str(b["secrets_count"]),
            f"{b['size_kb']} KB",
        )

    console.print(tbl)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERT YAML
# ═══════════════════════════════════════════════════════════════════════════════
def convert_json_to_yaml(backup_file: str, output_dir: str = "") -> Dict:
    if not os.path.exists(backup_file):
        return {"file": backup_file, "status": "error: file not found"}

    with open(backup_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    yaml_content = humanize_yaml(data)

    base_name = Path(backup_file).stem
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        yaml_path = out_path / f"{base_name}.yaml"
    else:
        yaml_path = Path(backup_file).parent / f"{base_name}.yaml"

    with open(yaml_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)

    line_count = yaml_content.count('\n') + 1
    size = yaml_path.stat().st_size

    return {
        "file": backup_file,
        "yaml_file": str(yaml_path),
        "status": "ok",
        "lines": line_count,
        "size_kb": round(size / 1024, 1),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PRINT RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
def print_backup_results(results: List[Dict]) -> None:
    tbl = Table(title="Resultados de Backup", show_lines=True)
    tbl.add_column("Pipeline ID", justify="right", min_width=10)
    tbl.add_column("Name", min_width=25)
    tbl.add_column("Revision", justify="right", min_width=8)
    tbl.add_column("Secrets", justify="right", min_width=8)
    tbl.add_column("Estado", min_width=15)
    tbl.add_column("Archivos", min_width=40)

    for r in results:
        status_str = "[green]OK[/green]" if r["status"] == "ok" else f"[red]{r['status']}[/red]"
        files_str = "\n".join(r["files"]) if r["files"] else "N/A"
        tbl.add_row(str(r["pipeline_id"]), r["name"], str(r["revision"]),
                     str(r["secrets_count"]), status_str, files_str)

    console.print(tbl)

    ok = sum(1 for r in results if r["status"] == "ok")
    fail = sum(1 for r in results if r["status"] != "ok")
    console.print(f"\n[green]Exitosos: {ok}[/green] | [red]Fallidos: {fail}[/red] | [cyan]Total: {len(results)}[/cyan]")


def print_backup_all_results(result: Dict) -> None:
    console.print()
    console.print(Panel(
        f"[bold]RESUMEN DE BACKUP MASIVO[/bold]\n\n"
        f"[cyan]Total pipelines:[/cyan]    {result['total']}\n"
        f"[green]Exitosos:[/green]           {result['successful']}\n"
        f"[red]Fallidos:[/red]           {result['failed']}\n"
        f"[yellow]Duracion:[/yellow]           {result['duration']}"
        + (f"\n[cyan]Indice:[/cyan]             {result['index_file']}" if result.get("index_file") else ""),
        border_style="cyan",
        expand=False,
    ))

    print_backup_results(result["backups"])


# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE MODE
# ═══════════════════════════════════════════════════════════════════════════════
def interactive_mode() -> int:
    config = load_config()

    console.print()
    console.print(Panel(
        f"[bold cyan]Pipeline CD Backup & Restore[/bold cyan] [dim]v{__version__}[/dim]",
        border_style="cyan",
        expand=False,
    ))
    console.print()

    org = prompt_with_default("Organizacion", config.get('organization', 'Coppel-Retail'))
    project = prompt_with_default("Proyecto", config.get('project', ''))
    pat = prompt_with_default("PAT", config.get('pat', ''), required=True)

    menu_options = [
        ("1", "Backup Completo (uno o varios)", "cyan"),
        ("2", "Restore Definicion", "cyan"),
        ("3", "Crear Pipeline desde Backup", "cyan"),
        ("4", "Comparar Backup vs Actual (Diff)", "cyan"),
        ("5", "Listar Backups Disponibles", "cyan"),
        ("6", "Backup Masivo (todos los pipelines)", "cyan"),
        ("7", "Convertir Backup JSON -> YAML", "cyan"),
        ("Q", "Volver", "red"),
    ]

    while True:
        menu_table = Table(show_header=False, box=None, padding=(0, 2))
        menu_table.add_column("Key", style="bold", width=4)
        menu_table.add_column("Opcion")
        for key, label, color in menu_options:
            menu_table.add_row(f"[{color}]{key}[/{color}]", label)

        console.print()
        console.print(Panel(menu_table, title="[bold]Submenu[/bold]", border_style="cyan", expand=False))
        choice = Prompt.ask("[bold]Seleccione opcion[/bold]").strip().lower()

        if choice == 'q':
            return 0

        elif choice == '1':
            ids_str = prompt_with_default("Pipeline IDs (separados por coma, max 500)", "")
            if not ids_str:
                continue
            ids = [int(x.strip()) for x in ids_str.split(",") if x.strip()]
            if len(ids) > MAX_PIPELINE_IDS:
                console.print(f"[red]Maximo {MAX_PIPELINE_IDS} IDs[/red]")
                continue
            fmt = prompt_with_default("Formato (json/yaml/both)", "json")
            workers = int(prompt_with_default("Workers", str(DEFAULT_WORKERS)))
            results = backup_pipelines(ids, org, project, pat, fmt, workers)
            print_backup_results(results)

        elif choice == '2':
            bfiles_str = prompt_with_default("Archivo(s) de backup (separados por coma)", "", required=True)
            bfiles = [f.strip() for f in bfiles_str.split(",") if f.strip()]
            dry = Confirm.ask("Dry-run?", default=False)
            for bf in bfiles:
                try:
                    with console.status(f"[cyan]Cargando backup: {Path(bf).name}...", spinner="dots"):
                        backup = load_backup(bf, str(BACKUP_DIR))
                    meta = backup.get("metadata", {})
                    secrets = backup.get("secrets_list", [])
                    console.print(f"\n[cyan]Pipeline: {meta.get('pipelineName', 'N/A')} (ID: {meta.get('pipelineId', 'N/A')})[/cyan]")

                    with console.status(f"[cyan]Obteniendo definicion actual del pipeline {meta.get('pipelineId', 'N/A')}...", spinner="dots"):
                        current_def = get_release_definition(org, project, meta["pipelineId"], pat)
                    with console.status("[cyan]Comparando backup vs definicion actual...", spinner="dots"):
                        diffs = diff_definitions(backup.get("definition", {}), current_def)
                    print_diff_table(diffs, meta.get("pipelineName", "N/A"))

                    if secrets:
                        console.print(f"\n[yellow]Secrets detectados ({len(secrets)}):[/yellow]")
                        for s in secrets:
                            console.print(f"  - {s['name']} ({s['scope']}/{s.get('env', 'N/A')})")
                        secret_values = {}
                        if not dry:
                            for s in secrets:
                                val = Prompt.ask(f"  Valor para {s['name']}", default="")
                                if val:
                                    secret_values[s["name"]] = val
                    else:
                        secret_values = None

                    if not dry:
                        confirm = Confirm.ask("Confirmar restore?", default=False)
                        if not confirm:
                            console.print("[yellow]Skip[/yellow]")
                            continue

                    with console.status(f"[cyan]Restaurando definicion del pipeline {meta.get('pipelineId', 'N/A')}...", spinner="dots"):
                        result = restore_definition(backup, org, project, pat, dry, secret_values)
                    status = result.get("status")
                    if status == "ok":
                        console.print(f"[green]Restore exitoso para pipeline {result['pipeline_id']}[/green]")
                    elif status == "dry_run":
                        console.print("[yellow]Dry-run: no se aplicaron cambios[/yellow]")
                    else:
                        console.print(f"[red]Error: {result}[/red]")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")

        elif choice == '3':
            bf = prompt_with_default("Archivo de backup", "", required=True)
            new_name = prompt_with_default("Nuevo nombre del pipeline", "")
            try:
                with console.status(f"[cyan]Cargando backup: {Path(bf).name}...", spinner="dots"):
                    backup = load_backup(bf, str(BACKUP_DIR))
                with console.status("[cyan]Creando nuevo pipeline desde backup...", spinner="dots"):
                    result = create_from_backup(backup, org, project, pat, new_name)
                console.print(f"[green]Pipeline creado: ID={result['new_id']}, Name={result['new_name']}[/green]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        elif choice == '4':
            bfiles_str = prompt_with_default("Archivo(s) de backup (separados por coma)", "", required=True)
            bfiles = [f.strip() for f in bfiles_str.split(",") if f.strip()]
            for bf in bfiles:
                try:
                    with console.status(f"[cyan]Cargando backup: {Path(bf).name}...", spinner="dots"):
                        backup = load_backup(bf, str(BACKUP_DIR))
                    meta = backup.get("metadata", {})
                    with console.status(f"[cyan]Obteniendo definicion actual del pipeline {meta.get('pipelineId', 'N/A')}...", spinner="dots"):
                        current_def = get_release_definition(org, project, meta["pipelineId"], pat)
                    with console.status("[cyan]Comparando backup vs definicion actual...", spinner="dots"):
                        diffs = diff_definitions(backup.get("definition", {}), current_def)
                    print_diff_table(diffs, meta.get("pipelineName", "N/A"))
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")

        elif choice == '5':
            with console.status("[cyan]Escaneando directorio de backups...", spinner="dots"):
                backups = list_backups()
            print_backups_table(backups)

        elif choice == '6':
            path_filter = prompt_with_default("Filtro por carpeta (Enter=todos)", "")
            fmt = prompt_with_default("Formato (json/yaml/both)", "json")
            workers = int(prompt_with_default("Workers", str(DEFAULT_WORKERS)))
            dry = Confirm.ask("Dry-run?", default=False)
            result = backup_all_pipelines(org, project, pat, path_filter, fmt, workers, dry)
            if not dry:
                print_backup_all_results(result)

        elif choice == '7':
            bfiles_str = prompt_with_default("Archivo(s) JSON (separados por coma, o Enter=todos)", "")
            if bfiles_str:
                bfiles = [f.strip() for f in bfiles_str.split(",") if f.strip()]
            else:
                bfiles = [str(f) for f in BACKUP_DIR.glob("backup_def_*.json")] if BACKUP_DIR.exists() else []
            if not bfiles:
                console.print("[yellow]No hay archivos para convertir[/yellow]")
                continue
            if len(bfiles) == 1:
                with console.status(f"[cyan]Convirtiendo {Path(bfiles[0]).name} a YAML...", spinner="dots"):
                    result = convert_json_to_yaml(bfiles[0])
                if result["status"] == "ok":
                    console.print(f"[green]OK: {result['yaml_file']} ({result['lines']} lineas, {result['size_kb']} KB)[/green]")
                else:
                    console.print(f"[red]Error: {result}[/red]")
            else:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as prog:
                    task = prog.add_task("[cyan]Convirtiendo JSON a YAML...", total=len(bfiles))
                    for bf in bfiles:
                        result = convert_json_to_yaml(bf)
                        prog.update(task, advance=1, description=f"[cyan]Convirtiendo: {Path(bf).name}")
                        if result["status"] != "ok":
                            console.print(f"[red]Error: {result}[/red]")
                    prog.update(task, description="[green]Conversion completada")
                console.print(f"[green]Convertidos {len(bfiles)} archivos a YAML[/green]")

        else:
            console.print("[red]Opcion invalida[/red]")


# ═══════════════════════════════════════════════════════════════════════════════
# ARGS & MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def get_args():
    parser = argparse.ArgumentParser(
        description='Pipeline CD Backup & Restore - Backup completo de definiciones de Pipeline CD',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--org', '--organization', default='Coppel-Retail', help='Organizacion de Azure DevOps')
    parser.add_argument('--project', default='', help='Proyecto')
    parser.add_argument('--pat', required=False, help='Personal Access Token')
    parser.add_argument('--mode', choices=['backup', 'backup-all', 'restore', 'create', 'diff', 'list', 'convert-yaml'],
                        help='Modo de operacion')
    parser.add_argument('--pipeline-ids', default='', help='IDs separados por coma (max 500)')
    parser.add_argument('--backup-files', default='', help='Archivo(s) de backup separados por coma')
    parser.add_argument('--backup-file', default='', help='Archivo de backup unico')
    parser.add_argument('--new-name', default='', help='Nuevo nombre para crear pipeline')
    parser.add_argument('--path-filter', default='', help='Filtro por carpeta para backup masivo')
    parser.add_argument('--format', choices=['json', 'yaml', 'both'], default='json', help='Formato de backup')
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS, help='Workers paralelos')
    parser.add_argument('--dry-run', action='store_true', help='No aplicar cambios')
    parser.add_argument('--interactive', '-i', action='store_true', help='Modo interactivo con submenu')
    parser.add_argument('--output', default='', help='Directorio de salida para convert-yaml')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    return parser.parse_args()


def main():
    args = get_args()

    if args.interactive:
        return interactive_mode()

    if not args.mode:
        console.print("[red]Especifique --mode o --interactive[/red]")
        return 1

    org = normalize_org(args.org)
    project = args.project
    pat = args.pat

    if args.mode == 'list':
        with console.status("[cyan]Escaneando directorio de backups...", spinner="dots"):
            backups = list_backups()
        print_backups_table(backups)
        return 0

    if args.mode == 'convert-yaml':
        if args.backup_files:
            bfiles = [f.strip() for f in args.backup_files.split(",") if f.strip()]
        elif BACKUP_DIR.exists():
            bfiles = [str(f) for f in BACKUP_DIR.glob("backup_def_*.json")]
        else:
            console.print("[red]No hay archivos para convertir[/red]")
            return 1
        if len(bfiles) == 1:
            with console.status(f"[cyan]Convirtiendo {Path(bfiles[0]).name} a YAML...", spinner="dots"):
                result = convert_json_to_yaml(bfiles[0], args.output)
            if result["status"] == "ok":
                console.print(f"[green]OK: {result['yaml_file']} ({result['lines']} lineas, {result['size_kb']} KB)[/green]")
            else:
                console.print(f"[red]Error: {result}[/red]")
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as prog:
                task = prog.add_task("[cyan]Convirtiendo JSON a YAML...", total=len(bfiles))
                for bf in bfiles:
                    result = convert_json_to_yaml(bf, args.output)
                    prog.update(task, advance=1, description=f"[cyan]Convirtiendo: {Path(bf).name}")
                    if result["status"] != "ok":
                        console.print(f"[red]Error: {result}[/red]")
                prog.update(task, description="[green]Conversion completada")
            console.print(f"[green]Convertidos {len(bfiles)} archivos a YAML[/green]")
        return 0

    if not pat:
        config = load_config()
        pat = config.get('pat', '')
        if not pat:
            console.print("[red]PAT requerido[/red]")
            return 1
    if not project:
        config = load_config()
        project = config.get('project', '')
        if not project:
            console.print("[red]Project requerido[/red]")
            return 1

    if args.mode == 'backup':
        if not args.pipeline_ids:
            console.print("[red]--pipeline-ids requerido para backup[/red]")
            return 1
        ids = [int(x.strip()) for x in args.pipeline_ids.split(",") if x.strip()]
        if len(ids) > MAX_PIPELINE_IDS:
            console.print(f"[red]Maximo {MAX_PIPELINE_IDS} IDs[/red]")
            return 1
        results = backup_pipelines(ids, org, project, pat, args.format, args.workers)
        print_backup_results(results)
        return 0

    if args.mode == 'backup-all':
        result = backup_all_pipelines(org, project, pat, args.path_filter, args.format, args.workers, args.dry_run)
        if not args.dry_run:
            print_backup_all_results(result)
        return 0

    if args.mode == 'restore':
        if not args.backup_files:
            print(f"{Colors.RED}--backup-files requerido para restore{Colors.ENDC}")
            return 1
        bfiles = [f.strip() for f in args.backup_files.split(",") if f.strip()]
        for bf in bfiles:
            try:
                with console.status(f"[cyan]Cargando backup: {Path(bf).name}...", spinner="dots"):
                    backup = load_backup(bf, str(BACKUP_DIR))
                meta = backup.get("metadata", {})
                secrets = backup.get("secrets_list", [])
                console.print(f"\n[cyan]Pipeline: {meta.get('pipelineName', 'N/A')} (ID: {meta.get('pipelineId', 'N/A')})[/cyan]")

                with console.status(f"[cyan]Obteniendo definicion actual del pipeline {meta.get('pipelineId', 'N/A')}...", spinner="dots"):
                    current_def = get_release_definition(org, project, meta["pipelineId"], pat)
                with console.status("[cyan]Comparando backup vs definicion actual...", spinner="dots"):
                    diffs = diff_definitions(backup.get("definition", {}), current_def)
                print_diff_table(diffs, meta.get("pipelineName", "N/A"))

                if not args.dry_run:
                    confirm = Confirm.ask("Confirmar restore?", default=False)
                    if not confirm:
                        console.print("[yellow]Skip[/yellow]")
                        continue

                with console.status(f"[cyan]Restaurando definicion del pipeline {meta.get('pipelineId', 'N/A')}...", spinner="dots"):
                    result = restore_definition(backup, org, project, pat, args.dry_run)
                status = result.get("status")
                if status == "ok":
                    console.print(f"[green]Restore exitoso para pipeline {result['pipeline_id']}[/green]")
                elif status == "dry_run":
                    console.print("[yellow]Dry-run: no se aplicaron cambios[/yellow]")
                else:
                    console.print(f"[red]Error: {result}[/red]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        return 0

    if args.mode == 'create':
        if not args.backup_file:
            console.print("[red]--backup-file requerido para create[/red]")
            return 1
        try:
            with console.status(f"[cyan]Cargando backup: {Path(args.backup_file).name}...", spinner="dots"):
                backup = load_backup(args.backup_file, str(BACKUP_DIR))
            with console.status("[cyan]Creando nuevo pipeline desde backup...", spinner="dots"):
                result = create_from_backup(backup, org, project, pat, args.new_name)
            console.print(f"[green]Pipeline creado: ID={result['new_id']}, Name={result['new_name']}[/green]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
        return 0

    if args.mode == 'diff':
        if not args.backup_files:
            console.print("[red]--backup-files requerido para diff[/red]")
            return 1
        bfiles = [f.strip() for f in args.backup_files.split(",") if f.strip()]
        for bf in bfiles:
            try:
                with console.status(f"[cyan]Cargando backup: {Path(bf).name}...", spinner="dots"):
                    backup = load_backup(bf, str(BACKUP_DIR))
                meta = backup.get("metadata", {})
                with console.status(f"[cyan]Obteniendo definicion actual del pipeline {meta.get('pipelineId', 'N/A')}...", spinner="dots"):
                    current_def = get_release_definition(org, project, meta["pipelineId"], pat)
                with console.status("[cyan]Comparando backup vs definicion actual...", spinner="dots"):
                    diffs = diff_definitions(backup.get("definition", {}), current_def)
                print_diff_table(diffs, meta.get("pipelineName", "N/A"))
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        return 0

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        console.print("\n[yellow]Proceso interrumpido[/yellow]")
        sys.exit(130)
