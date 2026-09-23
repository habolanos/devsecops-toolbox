#!/usr/bin/env python3
"""
Azure DevOps Release Pipeline Explorer con Rich UI + Diff
Requiere: pip install rich
Cross-platform: Windows, Linux, macOS
"""

import argparse
import base64
import html
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Any, Tuple
from urllib.parse import urlencode

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich import box
from rich.syntax import Syntax
from rich.columns import Columns
from rich.markup import escape

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


API_VERSION = "7.0"
console = Console()


def _resolve_output_dir(default: str = "outcome") -> str:
    """Resuelve el directorio de salida según global.output_dir de config.json.

    Orden: DEVSECOPS_OUTPUT_DIR (inyectada por main.py) > scm/config.json > default.
    """
    env_dir = os.environ.get("DEVSECOPS_OUTPUT_DIR")
    if env_dir:
        return env_dir
    scm_root = Path(__file__).resolve().parent.parent
    cfg_path = scm_root / "config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        out = cfg.get("global", {}).get("output_dir", default)
        p = Path(out)
        return str(p if p.is_absolute() else (scm_root / p).resolve())
    except Exception:
        return default

STATUS_COLORS = {
    "succeeded": "green",
    "partiallysucceeded": "yellow",
    "failed": "red",
    "rejected": "red",
    "canceled": "red",
    "inprogress": "yellow",
    "notstarted": "blue",
    "queued": "blue",
    "scheduled": "blue",
}


class DevOpsClient:
    def __init__(self, org: str, project: str, pat: str):
        self.org = org
        self.project = project
        self.base_url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release"
        creds = base64.b64encode(f":{pat}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json"
        }

    def _get(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        if params:
            url = f"{url}?{urlencode(params)}"
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise Exception(f"HTTP {e.code}: {e.reason}\n{body}")

    def list_definitions(self, top: int = 100) -> List[Dict]:
        return self._get("definitions", {"api-version": API_VERSION, "$top": str(top)}).get("value", [])

    def list_releases(self, definition_id: int, top: int = 50) -> List[Dict]:
        return self._get("releases", {
            "api-version": API_VERSION,
            "$top": str(top),
            "$expand": "environments",
            "definitionId": str(definition_id)
        }).get("value", [])

    def get_release(self, release_id: int) -> Dict:
        return self._get(f"releases/{release_id}", {
            "api-version": API_VERSION,
            "$expand": "environments,artifacts,approvals,variables"
        })


# ------------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------------
def normalize_org(org: str) -> str:
    """Extrae el nombre de la organización de una URL completa o retorna el nombre si ya está normalizado."""
    if org.startswith("https://"):
        # Extraer nombre de URL: https://dev.azure.com/OrgName → OrgName
        return org.split('/')[-1]
    return org


def fmt_date(iso_str: Optional[str]) -> str:
    if not iso_str:
        return "N/A"
    return iso_str.replace("T", " ")[:19]


def extract_build_ids(artifacts: List[Dict]) -> str:
    if not artifacts:
        return "N/A"
    ids = []
    for art in artifacts:
        version_id = art.get("definitionReference", {}).get("version", {}).get("id")
        alias = art.get("alias", "artifact")
        if version_id:
            ids.append(f"{alias}:{version_id}")
    return ", ".join(ids) if ids else "N/A"


def safe_str(value: Any, default: str = "N/A") -> str:
    """Convierte cualquier valor a str seguro para renderizar con Rich."""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return str(value)


def status_color(status: str) -> str:
    return STATUS_COLORS.get(safe_str(status, "").lower().replace(" ", ""), "white")


def cell(val_a: Any, val_b: Any) -> Tuple[str, str]:
    """Retorna string con color para tabla diff."""
    sa, sb = safe_str(val_a), safe_str(val_b)
    if sa == sb:
        return f"[green]{escape(sa)}[/green]", f"[green]{escape(sb)}[/green]"
    return f"[red]{escape(sa)}[/red]", f"[red]{escape(sb)}[/red]"


def side_cell(val: str, exists: bool) -> str:
    if not exists:
        return "[yellow]<ausente>[/yellow]"
    return val


# ------------------------------------------------------------------
# Impresión con Rich
# ------------------------------------------------------------------
def print_pipelines(pipelines: List[Dict]):
    table = Table(
        title=f"🔍 Pipelines Encontrados: {len(pipelines)}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("ID", style="cyan", width=12)
    table.add_column("Nombre", style="green")
    table.add_column("Creado", width=20)
    table.add_column("Actualizado", width=20)

    for p in pipelines:
        table.add_row(
            str(p["id"]),
            p.get("name", "N/A"),
            fmt_date(p.get("createdOn")),
            fmt_date(p.get("modifiedOn"))
        )
    console.print(table)


def print_releases(rows: List[Tuple]):
    table = Table(
        title="📦 Releases",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("ReleaseId", style="cyan", width=12)
    table.add_column("Fecha Creación", width=20)
    table.add_column("Stage", width=18)
    table.add_column("Estado", width=15)
    table.add_column("BuildId(s)")

    for r in rows:
        color = status_color(r[3])
        table.add_row(
            str(r[0]),
            fmt_date(r[1]),
            r[2],
            f"[{color}]{r[3]}[/{color}]",
            r[4]
        )
    console.print(table)


def print_release_details(release: Dict):
    rel_id = release.get("id", "N/A")
    name = release.get("name", "N/A")
    desc = release.get("description") or "Sin descripción"
    status = release.get("status", "N/A")
    created_by = release.get("createdBy", {}).get("displayName", "N/A")
    created_on = fmt_date(release.get("createdOn"))
    modified_on = fmt_date(release.get("modifiedOn"))

    header = Panel.fit(
        f"[bold cyan]Release #{rel_id}[/bold cyan] - [bold green]{name}[/bold green]\n"
        f"[italic]{desc}[/italic]\n\n"
        f"Status: [{status_color(status)}]{status}[/{status_color(status)}] | "
        f"Creado por: [yellow]{created_by}[/yellow]\n"
        f"Creación: {created_on} | Modificado: {modified_on}",
        title="🚀 Detalle del Release",
        border_style="blue"
    )
    console.print(header)

    # Artifacts
    artifacts = release.get("artifacts", [])
    if artifacts:
        art_table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        art_table.add_column("Alias", style="cyan")
        art_table.add_column("Tipo")
        art_table.add_column("BuildId", style="green")
        art_table.add_column("Versión")
        for art in artifacts:
            alias = art.get("alias", "N/A")
            art_type = art.get("type", "N/A")
            ver_id = art.get("definitionReference", {}).get("version", {}).get("id", "N/A")
            ver_name = art.get("definitionReference", {}).get("version", {}).get("name", "N/A")
            art_table.add_row(alias, art_type, ver_id, ver_name)
        console.print(Panel(art_table, title="📦 Artefactos", border_style="green"))
    else:
        console.print(Panel("[dim]Sin artefactos[/dim]", title="📦 Artefactos", border_style="green"))

    # Environments / Stages
    envs = release.get("environments", [])
    if envs:
        env_table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        env_table.add_column("Stage", style="cyan")
        env_table.add_column("Estado")
        env_table.add_column("Rank")
        env_table.add_column("Pre-Approvals")
        env_table.add_column("Post-Approvals")

        for env in envs:
            stage_name = env.get("name", "N/A")
            st = env.get("status", "N/A")
            rank = str(env.get("rank", "N/A"))
            pre = ", ".join([a.get("status", "?") for a in env.get("preDeployApprovals", [])]) or "N/A"
            post = ", ".join([a.get("status", "?") for a in env.get("postDeployApprovals", [])]) or "N/A"
            color = status_color(st)
            env_table.add_row(stage_name, f"[{color}]{st}[/{color}]", rank, pre, post)
        console.print(Panel(env_table, title="🎭 Stages / Environments", border_style="yellow"))

    # Variables
    variables = release.get("variables", {})
    if variables:
        var_table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        var_table.add_column("Variable", style="cyan")
        var_table.add_column("Valor")
        for k, v in variables.items():
            val = v.get("value", "N/A") if isinstance(v, dict) else str(v)
            var_table.add_row(k, val)
        console.print(Panel(var_table, title="🔧 Variables del Release", border_style="magenta"))

    # Global Approvals
    approvals = release.get("approvals", [])
    if approvals:
        app_table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        app_table.add_column("Tipo", style="cyan")
        app_table.add_column("Estado")
        app_table.add_column("Aprobador")
        for app in approvals:
            approver = app.get("approver", {}).get("displayName", "N/A")
            st = app.get("status", "N/A")
            color = status_color(st)
            app_table.add_row(app.get("approvalType", "?"), f"[{color}]{st}[/{color}]", approver)
        console.print(Panel(app_table, title="✅ Aprobaciones Globales", border_style="red"))


# ------------------------------------------------------------------
# DIFF
# ------------------------------------------------------------------
def print_diff(release_a: Dict, release_b: Dict):
    id_a = release_a.get("id", "A")
    id_b = release_b.get("id", "B")

    # Renderizables para exportar a TXT (se re-renderizan en consola ancha)
    # y datos estructurados para el HTML custom
    exportables: List[Any] = []
    diff_rows = {
        "info": [],       # (label, val_a, val_b)
        "artifacts": [],  # (alias, bid_a, ver_a, bid_b, ver_b)
        "stages": [],     # (stage, sta_a, pra_a, poa_a, sta_b, pra_b, poa_b)
        "tasks": [],      # (stage, merged_task_rows)
        "variables": [],  # (vname, val_a, val_b)
        "summary": [],    # (label, iguales, diferentes, solo_a, solo_b)
    }

    def emit(renderable):
        console.print(renderable)
        exportables.append(renderable)

    title = f"[bold]🔍 DIFF: Release #{id_a} vs Release #{id_b}[/bold]"
    emit(Panel(title, border_style="bright_cyan", expand=False))

    # --- Info General ---
    diff_fields = [
        ("Nombre", "name"),
        ("Status", "status"),
        ("Creado por", ("createdBy", "displayName")),
        ("Fecha Creación", "createdOn"),
        ("Fecha Modif.", "modifiedOn"),
        ("Descripción", "description"),
    ]

    def info_table():
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        t.add_column("Campo")
        t.add_column(f"Release #{id_a}", style="cyan")
        t.add_column(f"Release #{id_b}", style="magenta")

        for label, key in diff_fields:
            if isinstance(key, tuple):
                val_a = (release_a.get(key[0]) or {}).get(key[1], "N/A")
                val_b = (release_b.get(key[0]) or {}).get(key[1], "N/A")
            else:
                val_a = release_a.get(key, "N/A") or "N/A"
                val_b = release_b.get(key, "N/A") or "N/A"
            diff_rows["info"].append((label, safe_str(val_a), safe_str(val_b)))
            ca, cb = cell(val_a, val_b)
            t.add_row(label, ca, cb)
        return t

    emit(Panel(info_table(), title="📋 Información General", border_style="blue"))

    # --- Artefactos ---
    def artifact_table():
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        t.add_column("Alias")
        t.add_column(f"BuildId #{id_a}")
        t.add_column(f"Versión #{id_a}")
        t.add_column(f"BuildId #{id_b}")
        t.add_column(f"Versión #{id_b}")

        arts_a = {safe_str(a.get("alias")): a for a in release_a.get("artifacts") or []}
        arts_b = {safe_str(a.get("alias")): a for a in release_b.get("artifacts") or []}
        all_aliases = sorted(set(list(arts_a.keys()) + list(arts_b.keys())))

        for alias in all_aliases:
            in_a = alias in arts_a
            in_b = alias in arts_b
            def get_vals(art):
                ref = (art.get("definitionReference") or {}).get("version") or {}
                return ref.get("id", "N/A"), ref.get("name", "N/A")
            bid_a, ver_a = get_vals(arts_a[alias]) if in_a else ("N/A", "N/A")
            bid_b, ver_b = get_vals(arts_b[alias]) if in_b else ("N/A", "N/A")
            diff_rows["artifacts"].append((safe_str(alias), safe_str(bid_a), safe_str(ver_a), safe_str(bid_b), safe_str(ver_b)))
            cbid_a, cbid_b = cell(bid_a, bid_b)
            cver_a, cver_b = cell(ver_a, ver_b)
            t.add_row(escape(safe_str(alias)), cbid_a, cver_a, cbid_b, cver_b)
        return t

    emit(Panel(artifact_table(), title="📦 Artefactos", border_style="green"))

    # --- Stages / Environments ---
    def stage_table():
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        t.add_column("Stage")
        t.add_column(f"Estado #{id_a}")
        t.add_column(f"Pre-App #{id_a}")
        t.add_column(f"Post-App #{id_a}")
        t.add_column(f"Estado #{id_b}")
        t.add_column(f"Pre-App #{id_b}")
        t.add_column(f"Post-App #{id_b}")

        envs_a = {safe_str(e.get("name")): e for e in release_a.get("environments") or []}
        envs_b = {safe_str(e.get("name")): e for e in release_b.get("environments") or []}
        all_stages = sorted(set(list(envs_a.keys()) + list(envs_b.keys())))

        for stage in all_stages:
            in_a = stage in envs_a
            in_b = stage in envs_b

            def env_vals(env):
                st = safe_str(env.get("status"))
                pre = ", ".join([safe_str(a.get("status"), "?") for a in env.get("preDeployApprovals") or []]) or "N/A"
                post = ", ".join([safe_str(a.get("status"), "?") for a in env.get("postDeployApprovals") or []]) or "N/A"
                return st, pre, post

            sta_a, pra_a, poa_a = env_vals(envs_a[stage]) if in_a else ("N/A", "N/A", "N/A")
            sta_b, pra_b, poa_b = env_vals(envs_b[stage]) if in_b else ("N/A", "N/A", "N/A")

            diff_rows["stages"].append((safe_str(stage), sta_a, pra_a, poa_a, sta_b, pra_b, poa_b))
            csta_a, csta_b = cell(sta_a, sta_b)
            cpra_a, cpra_b = cell(pra_a, pra_b)
            cpoa_a, cpoa_b = cell(poa_a, poa_b)

            t.add_row(escape(safe_str(stage)), csta_a, cpra_a, cpoa_a, csta_b, cpra_b, cpoa_b)
        return t

    def extract_tasks(env: Dict) -> List[Dict]:
        """Extrae tasks de deployPhases/deployPhasesSnapshot del environment.

        La API de releases expone las fases como 'deployPhasesSnapshot';
        'deployPhases' existe en la definición del pipeline.
        """
        tasks = []
        phases = env.get("deployPhases") or env.get("deployPhasesSnapshot") or []
        for phase in phases:
            for task in phase.get("workflowTasks") or []:
                tasks.append({
                    "name": safe_str(task.get("name")),
                    "task_id": safe_str((task.get("task") or {}).get("id")),
                    "version": safe_str(task.get("version") or (task.get("task") or {}).get("version")),
                    "enabled": task.get("enabled", True),
                    "inputs": task.get("inputs") or {},
                    "phase_name": safe_str(phase.get("name")),
                    "phase_type": safe_str(phase.get("phaseType"))
                })
        if not tasks:
            # Fallback: tasks ejecutados en el último deployStep -> deploymentJobs -> tasks
            steps = env.get("deploySteps") or []
            step = steps[-1] if steps else {}
            jobs = list(step.get("deploymentJobs") or [])
            last_job = step.get("lastDeploymentJob")
            if last_job and last_job not in jobs:
                jobs.append(last_job)
            for job in jobs:
                for task in job.get("tasks") or []:
                    tasks.append({
                        "name": safe_str(task.get("name")),
                        "task_id": safe_str((task.get("task") or {}).get("id")),
                        "version": safe_str(task.get("version") or (task.get("task") or {}).get("version")),
                        "enabled": task.get("enabled", True),
                        "inputs": task.get("inputs") or {},
                        "phase_name": safe_str(job.get("job") or step.get("operation") or "Deploy"),
                        "phase_type": "deploymentJob"
                    })
        return tasks

    def compare_inputs(inputs_a: Optional[Dict], inputs_b: Optional[Dict]) -> Tuple[str, str]:
        """Compara inputs de dos tasks y retorna representación con colores."""
        # Normalizar None a dict vacío
        inputs_a = inputs_a or {}
        inputs_b = inputs_b or {}
        
        if not inputs_a and not inputs_b:
            return "—", "—"
        
        all_keys = sorted(set(list(inputs_a.keys()) + list(inputs_b.keys())))
        parts_a = []
        parts_b = []
        missing = object()

        for key in all_keys:
            raw_a = inputs_a.get(key, missing)
            raw_b = inputs_b.get(key, missing)
            val_a = "<no definido>" if raw_a is missing else safe_str(raw_a)
            val_b = "<no definido>" if raw_b is missing else safe_str(raw_b)
            ekey = escape(safe_str(key))
            if raw_a is not missing and raw_b is not missing and safe_str(raw_a) == safe_str(raw_b):
                parts_a.append(f"[green]{ekey}={escape(val_a)}[/green]")
                parts_b.append(f"[green]{ekey}={escape(val_b)}[/green]")
            else:
                parts_a.append(f"[red]{ekey}={escape(val_a)}[/red]")
                parts_b.append(f"[red]{ekey}={escape(val_b)}[/red]")

        return " | ".join(parts_a), " | ".join(parts_b)

    def compare_tasks(tasks_a: List[Dict], tasks_b: List[Dict]) -> Table:
        """Compara tasks entre dos environments."""
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        t.add_column("Task")
        t.add_column("Phase")
        t.add_column(f"Version #{id_a}")
        t.add_column(f"Enabled #{id_a}")
        t.add_column(f"Version #{id_b}")
        t.add_column(f"Enabled #{id_b}")
        t.add_column(f"Inputs #{id_a}", ratio=1)
        t.add_column(f"Inputs #{id_b}", ratio=1)

        # Agrupar por nombre de task
        tasks_by_name_a = {task["name"]: task for task in tasks_a}
        tasks_by_name_b = {task["name"]: task for task in tasks_b}
        all_task_names = sorted(set(list(tasks_by_name_a.keys()) + list(tasks_by_name_b.keys())))

        for task_name in all_task_names:
            in_a = task_name in tasks_by_name_a
            in_b = task_name in tasks_by_name_b

            if in_a and in_b:
                task_a = tasks_by_name_a[task_name]
                task_b = tasks_by_name_b[task_name]
                phase_a = escape(safe_str(task_a.get("phase_name")))
                phase_b = escape(safe_str(task_b.get("phase_name")))
                ver_a = task_a.get("version", "N/A")
                ver_b = task_b.get("version", "N/A")
                en_a = safe_str(task_a.get("enabled", True))
                en_b = safe_str(task_b.get("enabled", True))
                cver_a, cver_b = cell(ver_a, ver_b)
                cen_a, cen_b = cell(en_a, en_b)
                inp_a, inp_b = compare_inputs(task_a.get("inputs"), task_b.get("inputs"))
                t.add_row(escape(safe_str(task_name)), f"{phase_a} / {phase_b}", cver_a, cen_a, cver_b, cen_b, inp_a, inp_b)
            elif in_a:
                task_a = tasks_by_name_a[task_name]
                phase_a = escape(safe_str(task_a.get("phase_name")))
                ver_a = escape(safe_str(task_a.get("version")))
                en_a = escape(safe_str(task_a.get("enabled", True)))
                inp_a, inp_b = compare_inputs(task_a.get("inputs"), {})
                t.add_row(escape(safe_str(task_name)), f"{phase_a} / <ausente>", f"[green]{ver_a}[/green]", f"[green]{en_a}[/green]", "[yellow]<ausente>[/yellow]", "[yellow]<ausente>[/yellow]", inp_a, inp_b)
            else:
                task_b = tasks_by_name_b[task_name]
                phase_b = escape(safe_str(task_b.get("phase_name")))
                ver_b = escape(safe_str(task_b.get("version")))
                en_b = escape(safe_str(task_b.get("enabled", True)))
                inp_a, inp_b = compare_inputs({}, task_b.get("inputs"))
                t.add_row(escape(safe_str(task_name)), f"<ausente> / {phase_b}", "[yellow]<ausente>[/yellow]", "[yellow]<ausente>[/yellow]", f"[green]{ver_b}[/green]", f"[green]{en_b}[/green]", inp_a, inp_b)
        return t

    console.print(Panel(stage_table(), title="🎭 Stages / Environments", border_style="yellow"))

    # --- Tasks (DeployPhases / WorkflowTasks) ---
    # Build tasks tables per stage
    envs_a = {safe_str(e.get("name")): e for e in release_a.get("environments") or []}
    envs_b = {safe_str(e.get("name")): e for e in release_b.get("environments") or []}
    all_stages = sorted(set(list(envs_a.keys()) + list(envs_b.keys())))

    tasks_found = False
    for stage in all_stages:
        in_a = stage in envs_a
        in_b = stage in envs_b
        tasks_a = extract_tasks(envs_a[stage]) if in_a else []
        tasks_b = extract_tasks(envs_b[stage]) if in_b else []
        if tasks_a or tasks_b:
            tasks_found = True
            task_table = compare_tasks(tasks_a, tasks_b)
            emit(Panel(task_table, title=f"⚙️ Tasks - Stage: {escape(safe_str(stage))}", border_style="cyan"))
            diff_rows["tasks"].append((safe_str(stage), tasks_a, tasks_b))

    if not tasks_found:
        emit("[dim]ℹ️ No se encontraron tasks en deployPhases/deployPhasesSnapshot de los environments.[/dim]")

    # --- Variables ---
    def variable_table():
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        t.add_column("Variable")
        t.add_column(f"Valor #{id_a}")
        t.add_column(f"Valor #{id_b}")

        vars_a = release_a.get("variables") or {}
        vars_b = release_b.get("variables") or {}
        all_vars = sorted(set(list(vars_a.keys()) + list(vars_b.keys())))

        for vname in all_vars:
            in_a = vname in vars_a
            in_b = vname in vars_b
            val_a = vars_a[vname].get("value", "N/A") if isinstance(vars_a.get(vname), dict) else vars_a.get(vname, "N/A")
            val_b = vars_b[vname].get("value", "N/A") if isinstance(vars_b.get(vname), dict) else vars_b.get(vname, "N/A")

            diff_rows["variables"].append((safe_str(vname), safe_str(val_a), safe_str(val_b)))
            cva, cvb = cell(val_a, val_b)
            t.add_row(escape(safe_str(vname)), cva, cvb)
        return t

    vars_a = release_a.get("variables") or {}
    vars_b = release_b.get("variables") or {}
    if vars_a or vars_b:
        emit(Panel(variable_table(), title="🔧 Variables del Release", border_style="magenta"))

    # --- Resumen de cambios ---
    _MISSING = object()

    def _counts(da: Dict, db: Dict, eq_fn) -> Tuple[int, int, int, int]:
        """Retorna (iguales, diferentes, solo_a, solo_b) entre dos dicts."""
        equal = diff = only_a = only_b = 0
        for k in set(da) | set(db):
            va, vb = da.get(k, _MISSING), db.get(k, _MISSING)
            if va is _MISSING:
                only_b += 1
            elif vb is _MISSING:
                only_a += 1
            elif eq_fn(va, vb):
                equal += 1
            else:
                diff += 1
        return equal, diff, only_a, only_b

    def _field_val(rel, key):
        if isinstance(key, tuple):
            return safe_str((rel.get(key[0]) or {}).get(key[1]))
        return safe_str(rel.get(key))

    info_map_a = {lbl: _field_val(release_a, k) for lbl, k in diff_fields}
    info_map_b = {lbl: _field_val(release_b, k) for lbl, k in diff_fields}
    c_info = _counts(info_map_a, info_map_b, lambda x, y: x == y)

    def _art_sig(art):
        ref = (art.get("definitionReference") or {}).get("version") or {}
        return (safe_str(ref.get("id")), safe_str(ref.get("name")))

    arts_map_a = {safe_str(a.get("alias")): _art_sig(a) for a in release_a.get("artifacts") or []}
    arts_map_b = {safe_str(a.get("alias")): _art_sig(a) for a in release_b.get("artifacts") or []}
    c_art = _counts(arts_map_a, arts_map_b, lambda x, y: x == y)

    def _env_sig(env):
        st = safe_str(env.get("status"))
        pre = ",".join(safe_str(a.get("status"), "?") for a in env.get("preDeployApprovals") or [])
        post = ",".join(safe_str(a.get("status"), "?") for a in env.get("postDeployApprovals") or [])
        return (st, pre, post)

    c_stg = _counts(envs_a, envs_b, lambda x, y: _env_sig(x) == _env_sig(y))

    tasks_map_a, tasks_map_b = {}, {}
    for stage in all_stages:
        for task in (extract_tasks(envs_a[stage]) if stage in envs_a else []):
            tasks_map_a[f"{stage}/{task['name']}"] = task
        for task in (extract_tasks(envs_b[stage]) if stage in envs_b else []):
            tasks_map_b[f"{stage}/{task['name']}"] = task

    def _task_sig(t):
        return (t.get("version"), safe_str(t.get("enabled")),
                json.dumps(t.get("inputs") or {}, sort_keys=True, default=str))

    c_task = _counts(tasks_map_a, tasks_map_b, lambda x, y: _task_sig(x) == _task_sig(y))

    def _var_val(v):
        return v.get("value") if isinstance(v, dict) else v

    vars_map_a = {k: _var_val(v) for k, v in vars_a.items()}
    vars_map_b = {k: _var_val(v) for k, v in vars_b.items()}
    c_var = _counts(vars_map_a, vars_map_b, lambda x, y: safe_str(x) == safe_str(y))

    def summary_table():
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        t.add_column("Sección")
        t.add_column("Iguales", justify="right")
        t.add_column("Diferentes", justify="right")
        t.add_column(f"Solo #{id_a}", justify="right")
        t.add_column(f"Solo #{id_b}", justify="right")

        totals = [0, 0, 0, 0]
        for label, (eq, df, oa, ob) in [
            ("Información General", c_info),
            ("Artefactos", c_art),
            ("Stages", c_stg),
            ("Tasks", c_task),
            ("Variables", c_var),
        ]:
            totals[0] += eq; totals[1] += df; totals[2] += oa; totals[3] += ob
            diff_rows["summary"].append((label, eq, df, oa, ob))
            t.add_row(
                label,
                str(eq),
                f"[red]{df}[/red]" if df else "0",
                f"[yellow]{oa}[/yellow]" if oa else "0",
                f"[yellow]{ob}[/yellow]" if ob else "0",
            )
        diff_rows["summary"].append(("TOTAL", totals[0], totals[1], totals[2], totals[3]))
        t.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{totals[0]}[/bold]",
            f"[bold red]{totals[1]}[/bold red]" if totals[1] else "[bold]0[/bold]",
            f"[bold yellow]{totals[2]}[/bold yellow]" if totals[2] else "[bold]0[/bold]",
            f"[bold yellow]{totals[3]}[/bold yellow]" if totals[3] else "[bold]0[/bold]",
        )
        return t

    emit(Panel(summary_table(), title="📊 Resumen de Cambios", border_style="bright_yellow"))

    # --- Exportar salida plana (TXT) y HTML ---
    try:
        outcome_dir = _resolve_output_dir()
        os.makedirs(outcome_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        txt_path = os.path.join(outcome_dir, f"release_diff_{id_a}_vs_{id_b}_{ts}.txt")
        html_path = os.path.join(outcome_dir, f"release_diff_{id_a}_vs_{id_b}_{ts}.html")

        # TXT: re-renderizar en consola ancha para no cortar valores
        buf = io.StringIO()
        wide_console = Console(file=buf, width=500, force_terminal=False, color_system=None)
        for renderable in exportables:
            wide_console.print(renderable)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(line.rstrip() for line in buf.getvalue().splitlines()))

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(_diff_html_report(id_a, id_b, diff_rows))

        console.print(f"[bold green]📄 TXT:[/bold green]  [bold cyan]{txt_path}[/bold cyan]")
        console.print(f"[bold green]🌐 HTML:[/bold green] [bold cyan]{html_path}[/bold cyan]")
    except Exception as e:
        console.print(f"[yellow]⚠️ No se pudo exportar el diff: {e}[/yellow]")


def _inputs_html(inputs_a: Dict, inputs_b: Dict) -> Tuple[str, str]:
    """Renderiza inputs como líneas key=value con clases eq/diff/miss."""
    inputs_a = inputs_a or {}
    inputs_b = inputs_b or {}
    if not inputs_a and not inputs_b:
        return '<span class="miss">—</span>', '<span class="miss">—</span>'
    keys = sorted(set(inputs_a) | set(inputs_b))
    missing = object()
    pa, pb = [], []
    for k in keys:
        ra, rb = inputs_a.get(k, missing), inputs_b.get(k, missing)
        va = "<no definido>" if ra is missing else safe_str(ra)
        vb = "<no definido>" if rb is missing else safe_str(rb)
        cls = "eq" if (ra is not missing and rb is not missing and safe_str(ra) == safe_str(rb)) else "diff"
        cls_a = "miss" if ra is missing else cls
        cls_b = "miss" if rb is missing else cls
        pa.append(f'<div class="kv {cls_a}"><b>{html.escape(safe_str(k))}</b>={html.escape(va)}</div>')
        pb.append(f'<div class="kv {cls_b}"><b>{html.escape(safe_str(k))}</b>={html.escape(vb)}</div>')
    return "".join(pa), "".join(pb)


def _diff_html_report(id_a: Any, id_b: Any, d: Dict) -> str:
    """Genera reporte HTML del diff con el estilo del toolbox (cards + badges)."""
    e = lambda v: html.escape(safe_str(v))  # noqa: E731

    def cmp_cls(a, b):
        return "eq" if a == b else "diff"

    totals = d["summary"][-1] if d["summary"] else ("TOTAL", 0, 0, 0, 0)

    page = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Release Diff #{e(id_a)} vs #{e(id_b)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
        .header {{ background: linear-gradient(135deg, #1e293b 0%, #334155 100%); padding: 24px 32px; border-bottom: 1px solid #475569; }}
        .header h1 {{ font-size: 1.75rem; color: #38bdf8; }}
        .header .meta {{ display: flex; gap: 24px; margin-top: 12px; flex-wrap: wrap; font-size: .875rem; color: #94a3b8; }}
        .container {{ max-width: 1600px; margin: 0 auto; padding: 24px; }}
        h2 {{ font-size: 1.25rem; font-weight: 600; margin-bottom: 16px; color: #f1f5f9; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 32px; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; transition: transform .15s, border-color .15s; }}
        .card:hover {{ transform: translateY(-2px); border-color: #475569; }}
        .card h3 {{ margin: 0 0 10px 0; color: #94a3b8; font-size: .75rem; text-transform: uppercase; letter-spacing: .5px; }}
        .card .value {{ font-size: 2rem; font-weight: 700; margin-top: 4px; }}
        .eq {{ color: #4ade80; }} .diff {{ color: #f87171; }} .miss {{ color: #facc15; }}
        table {{ width: 100%; border-collapse: collapse; font-size: .8125rem; table-layout: auto; }}
        thead th {{ text-align: left; padding: 10px 14px; background: #1e293b; color: #94a3b8; font-weight: 600; border-bottom: 1px solid #334155; white-space: nowrap; }}
        tbody td {{ padding: 8px 14px; border-bottom: 1px solid #1e293b; color: #cbd5e1; vertical-align: top; }}
        tbody tr:hover {{ background: #1e293b; }}
        .table-wrap {{ overflow-x: auto; border-radius: 8px; border: 1px solid #334155; margin-bottom: 30px; }}
        .section {{ margin-bottom: 32px; }}
        .meta {{ color: #94a3b8; font-size: .875rem; }}
        .kv {{ font-family: 'Consolas', 'Courier New', monospace; font-size: .75rem; white-space: pre-wrap; word-break: break-all; }}
        td.inputs {{ min-width: 300px; }}
        .footer {{ text-align: center; padding: 20px; color: #64748b; font-size: .75rem; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Release Diff: #{e(id_a)} vs #{e(id_b)}</h1>
        <div class="meta"><span>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span><span>Azure DevOps Release Explorer</span></div>
    </div>
    <div class="container">

        <div class="summary">
            <div class="card"><h3>Elementos Iguales</h3><div class="value eq">{totals[1]}</div></div>
            <div class="card"><h3>Diferencias</h3><div class="value diff">{totals[2]}</div></div>
            <div class="card"><h3>Solo en #{e(id_a)}</h3><div class="value miss">{totals[3]}</div></div>
            <div class="card"><h3>Solo en #{e(id_b)}</h3><div class="value miss">{totals[4]}</div></div>
        </div>
"""

    # Información General
    page += f"""
        <div class="section">
            <h2>📋 Información General</h2>
            <div class="table-wrap"><table><thead><tr><th>Campo</th><th>Release #{e(id_a)}</th><th>Release #{e(id_b)}</th></tr></thead><tbody>
"""
    for label, va, vb in d["info"]:
        page += f'                <tr><td><strong>{e(label)}</strong></td><td class="{cmp_cls(va, vb)}">{e(va)}</td><td class="{cmp_cls(va, vb)}">{e(vb)}</td></tr>\n'
    page += "            </tbody></table></div>\n        </div>\n"

    # Artefactos
    if d["artifacts"]:
        page += f"""
        <div class="section">
            <h2>📦 Artefactos</h2>
            <div class="table-wrap"><table><thead><tr><th>Alias</th><th>BuildId #{e(id_a)}</th><th>Versión #{e(id_a)}</th><th>BuildId #{e(id_b)}</th><th>Versión #{e(id_b)}</th></tr></thead><tbody>
"""
        for alias, bid_a, ver_a, bid_b, ver_b in d["artifacts"]:
            page += (f'                <tr><td><strong>{e(alias)}</strong></td>'
                     f'<td class="{cmp_cls(bid_a, bid_b)}">{e(bid_a)}</td>'
                     f'<td class="{cmp_cls(ver_a, ver_b)}">{e(ver_a)}</td>'
                     f'<td class="{cmp_cls(bid_a, bid_b)}">{e(bid_b)}</td>'
                     f'<td class="{cmp_cls(ver_a, ver_b)}">{e(ver_b)}</td></tr>\n')
        page += "            </tbody></table></div>\n        </div>\n"

    # Stages
    if d["stages"]:
        page += f"""
        <div class="section">
            <h2>🎭 Stages / Environments</h2>
            <div class="table-wrap"><table><thead><tr><th>Stage</th><th>Estado #{e(id_a)}</th><th>Pre-App #{e(id_a)}</th><th>Post-App #{e(id_a)}</th><th>Estado #{e(id_b)}</th><th>Pre-App #{e(id_b)}</th><th>Post-App #{e(id_b)}</th></tr></thead><tbody>
"""
        for stage, sta_a, pra_a, poa_a, sta_b, pra_b, poa_b in d["stages"]:
            page += (f'                <tr><td><strong>{e(stage)}</strong></td>'
                     f'<td class="{cmp_cls(sta_a, sta_b)}">{e(sta_a)}</td>'
                     f'<td class="{cmp_cls(pra_a, pra_b)}">{e(pra_a)}</td>'
                     f'<td class="{cmp_cls(poa_a, poa_b)}">{e(poa_a)}</td>'
                     f'<td class="{cmp_cls(sta_a, sta_b)}">{e(sta_b)}</td>'
                     f'<td class="{cmp_cls(pra_a, pra_b)}">{e(pra_b)}</td>'
                     f'<td class="{cmp_cls(poa_a, poa_b)}">{e(poa_b)}</td></tr>\n')
        page += "            </tbody></table></div>\n        </div>\n"

    # Tasks por stage
    for stage, tasks_a, tasks_b in d["tasks"]:
        by_a = {t["name"]: t for t in tasks_a}
        by_b = {t["name"]: t for t in tasks_b}
        names = sorted(set(by_a) | set(by_b))
        page += f"""
        <div class="section">
            <h2>⚙️ Tasks - Stage: {e(stage)}</h2>
            <div class="table-wrap"><table><thead><tr><th>Task</th><th>Phase</th><th>Version #{e(id_a)}</th><th>Enabled #{e(id_a)}</th><th>Version #{e(id_b)}</th><th>Enabled #{e(id_b)}</th><th>Inputs #{e(id_a)}</th><th>Inputs #{e(id_b)}</th></tr></thead><tbody>
"""
        for name in names:
            ta, tb = by_a.get(name), by_b.get(name)
            ph_a = safe_str(ta.get("phase_name")) if ta else "<ausente>"
            ph_b = safe_str(tb.get("phase_name")) if tb else "<ausente>"
            ver_a = safe_str(ta.get("version")) if ta else "<ausente>"
            ver_b = safe_str(tb.get("version")) if tb else "<ausente>"
            en_a = safe_str(ta.get("enabled")) if ta else "<ausente>"
            en_b = safe_str(tb.get("enabled")) if tb else "<ausente>"
            in_a, in_b = _inputs_html(ta.get("inputs") if ta else {}, tb.get("inputs") if tb else {})
            cls_ver, cls_en = cmp_cls(ver_a, ver_b), cmp_cls(en_a, en_b)
            page += (f'                <tr><td><strong>{e(name)}</strong></td><td>{e(ph_a)} / {e(ph_b)}</td>'
                     f'<td class="{cls_ver}">{e(ver_a)}</td><td class="{cls_en}">{e(en_a)}</td>'
                     f'<td class="{cls_ver}">{e(ver_b)}</td><td class="{cls_en}">{e(en_b)}</td>'
                     f'<td class="inputs">{in_a}</td><td class="inputs">{in_b}</td></tr>\n')
        page += "            </tbody></table></div>\n        </div>\n"

    # Variables
    if d["variables"]:
        page += f"""
        <div class="section">
            <h2>🔧 Variables del Release</h2>
            <div class="table-wrap"><table><thead><tr><th>Variable</th><th>Valor #{e(id_a)}</th><th>Valor #{e(id_b)}</th></tr></thead><tbody>
"""
        for vname, va, vb in d["variables"]:
            page += f'                <tr><td><strong>{e(vname)}</strong></td><td class="{cmp_cls(va, vb)}">{e(va)}</td><td class="{cmp_cls(va, vb)}">{e(vb)}</td></tr>\n'
        page += "            </tbody></table></div>\n        </div>\n"

    # Resumen
    page += f"""
        <div class="section">
            <h2>📊 Resumen de Cambios</h2>
            <div class="table-wrap"><table><thead><tr><th>Sección</th><th>Iguales</th><th>Diferentes</th><th>Solo #{e(id_a)}</th><th>Solo #{e(id_b)}</th></tr></thead><tbody>
"""
    for label, eq, df, oa, ob in d["summary"]:
        bold_a = "<strong>" if label == "TOTAL" else ""
        bold_b = "</strong>" if label == "TOTAL" else ""
        page += (f'                <tr><td>{bold_a}{e(label)}{bold_b}</td>'
                 f'<td class="eq">{eq}</td><td class="diff">{df}</td>'
                 f'<td class="miss">{oa}</td><td class="miss">{ob}</td></tr>\n')
    page += """            </tbody></table></div>
        </div>
        <div class="footer">Generado por DevSecOps Toolbox — Azure DevOps Release Explorer</div>
    </div>
</body>
</html>
"""
    return page


# ------------------------------------------------------------------
# Lógica de filtrado y búsqueda
# ------------------------------------------------------------------
def get_matching_pipelines(client: DevOpsClient, search_text: str) -> List[Dict]:
    with console.status("[bold green]Consultando pipelines en Azure DevOps...[/bold green]", spinner="dots"):
        defs = client.list_definitions(top=500)
    
    console.print(f"[dim]Total de pipelines encontrados: {len(defs)}[/dim]")
    
    pattern = search_text.lower()
    # Buscar por coincidencia parcial (contiene) en lugar de solo inicio
    matches = [d for d in defs if pattern in d.get("name", "").lower()]
    
    if not matches and defs:
        console.print(f"[dim]Pipelines disponibles (primeros 10):[/dim]")
        for d in defs[:10]:
            console.print(f"  • {d.get('name', 'N/A')}")
    
    return matches


def get_releases_rows(client: DevOpsClient,
                      definition_id: int,
                      stage_filter: Optional[str],
                      status_filter: Optional[str],
                      active_only: bool,
                      top: int = 50) -> List[Tuple]:
    with console.status(f"[bold green]Cargando releases para DefinitionId {definition_id}...[/bold green]", spinner="dots"):
        releases = client.list_releases(definition_id, top=top)

    rows = []
    active_statuses = {"notStarted", "queued", "scheduled", "inProgress"}

    for rel in releases:
        rel_id = rel.get("id")
        created = rel.get("createdOn")
        build_ids = extract_build_ids(rel.get("artifacts", []))
        environments = rel.get("environments", [])

        if not environments:
            rows.append((rel_id, created, "N/A", "N/A", build_ids))
            continue

        for env in environments:
            stage_name = env.get("name", "N/A")
            status = env.get("status", "N/A")

            if stage_filter and stage_filter.lower() != stage_name.lower():
                continue
            if status_filter and status_filter.lower() != status.lower():
                continue
            if active_only and status not in active_statuses:
                continue

            rows.append((rel_id, created, stage_name, status, build_ids))

    return rows


# ------------------------------------------------------------------
# Modos de ejecución
# ------------------------------------------------------------------
def prompt_select(options: List[Any], formatter, prompt_text: str) -> Any:
    if not options:
        console.print("[bold red]No hay opciones disponibles.[/bold red]")
        sys.exit(1)
    console.print()
    for idx, opt in enumerate(options, 1):
        console.print(f"  [{idx}] {formatter(opt)}")
    while True:
        n = IntPrompt.ask(f"\n{prompt_text}")
        if 1 <= n <= len(options):
            return options[n - 1]
        console.print("[bold red]Entrada inválida. Intente de nuevo.[/bold red]")


def interactive_mode(client: DevOpsClient, args):
    # Paso 1: Buscar pipelines
    search = args.search if args.search else Prompt.ask("Ingrese texto para buscar pipelines (búsqueda parcial)")
    with console.status("[bold cyan]Filtrando resultados...[/bold cyan]", spinner="arc"):
        pipelines = get_matching_pipelines(client, search)

    if not pipelines:
        console.print(f"[bold red]❌ No se encontraron pipelines que contengan '{search}'[/bold red]")
        return

    print_pipelines(pipelines)

    selected = prompt_select(pipelines, lambda p: f"{p['id']} - {p['name']}", "Seleccione pipeline")
    def_id = selected["id"]
    console.print(f"\n[bold green]>>> Pipeline seleccionado:[/bold green] {selected['name']} (ID: {def_id})")

    # Filtros
    stage_f = args.stage_filter
    status_f = args.status_filter
    active = args.active_only

    if not stage_f:
        stage_input = Prompt.ask("Filtrar por stage? [cyan](Enter para todos)[/cyan]", default="")
        stage_f = stage_input if stage_input else None
    if not status_f and not active:
        status_input = Prompt.ask("Filtrar por estado exacto? [cyan](Enter para todos)[/cyan]", default="")
        status_f = status_input if status_input else None

    rows = get_releases_rows(client, def_id, stage_f, status_f, active, top=args.top)
    if not rows:
        console.print("[bold yellow]⚠️  No se encontraron releases con esos filtros.[/bold yellow]")
        return

    print_releases(rows)

    # Seleccionar release único
    unique = []
    seen = set()
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            unique.append(r)

    selected_rel = prompt_select(
        unique,
        lambda r: f"Release #{r[0]} | Creado: {fmt_date(r[1])} | BuildIds: {r[4]}",
        "Seleccione release para ver detalle"
    )
    rel_id = selected_rel[0]

    with console.status(f"[bold cyan]Consultando detalle del release #{rel_id}...[/bold cyan]", spinner="earth"):
        release = client.get_release(rel_id)

    print_release_details(release)


def param_mode(client: DevOpsClient, args):
    # Modo Diff primero (tiene prioridad)
    if args.diff:
        r1, r2 = args.diff
        with console.status(f"[bold green]Cargando release #{r1}...[/bold green]", spinner="dots"):
            rel_a = client.get_release(r1)
        with console.status(f"[bold green]Cargando release #{r2}...[/bold green]", spinner="dots"):
            rel_b = client.get_release(r2)
        print_diff(rel_a, rel_b)
        return

    if args.search:
        with console.status("[bold green]Buscando pipelines...[/bold green]", spinner="dots"):
            pipelines = get_matching_pipelines(client, args.search)
        if args.json_output:
            console.print(Syntax(json.dumps(pipelines, indent=2), "json"))
            return
        print_pipelines(pipelines)
        if not args.definition_id:
            return

    if args.definition_id:
        rows = get_releases_rows(
            client, args.definition_id,
            args.stage_filter, args.status_filter, args.active_only,
            top=args.top
        )
        if args.json_output:
            out = [
                {"releaseId": r[0], "createdOn": r[1], "stage": r[2], "status": r[3], "buildIds": r[4]}
                for r in rows
            ]
            console.print(Syntax(json.dumps(out, indent=2), "json"))
            return
        print_releases(rows)
        if not args.release_id:
            return

    if args.release_id:
        with console.status(f"[bold green]Cargando detalle del release {args.release_id}...[/bold green]", spinner="dots"):
            release = client.get_release(args.release_id)
        if args.json_output:
            console.print(Syntax(json.dumps(release, indent=2), "json"))
            return
        print_release_details(release)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Explorador de Release Pipelines clásicos de Azure DevOps con Rich UI + Diff"
    )
    parser.add_argument("--org", default=os.environ.get("AZDO_ORG"), help="Organización")
    parser.add_argument("--project", default=os.environ.get("AZDO_PROJECT"), help="Proyecto")
    parser.add_argument("--pat", default=os.environ.get("AZDO_PAT"), help="Personal Access Token")
    parser.add_argument("--search", "-s", help="Filtrar pipelines por inicio de nombre (case-insensitive)")
    parser.add_argument("--definition-id", "-d", type=int, help="ID de definición de release")
    parser.add_argument("--release-id", "-r", type=int, help="ID del release a consultar en detalle")
    parser.add_argument("--stage-filter", help="Filtrar por nombre de stage")
    parser.add_argument("--status-filter", help="Filtrar por estado exacto del stage")
    parser.add_argument("--active-only", action="store_true", help="Mostrar solo stages activos")
    parser.add_argument("--top", type=int, default=50, help="Máximo de releases a traer (default 50)")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Salida en JSON crudo")
    parser.add_argument("--interactive", "-i", action="store_true", help="Forzar modo interactivo")
    parser.add_argument("--diff", nargs=2, type=int, metavar=("R1", "R2"),
                        help="Comparar dos releases lado a lado (ej: --diff 58001 58005)")

    args = parser.parse_args()

    if not args.org or not args.project or not args.pat:
        parser.error("Debe especificar --org, --project y --pat (o variables AZDO_ORG, AZDO_PROJECT, AZDO_PAT)")

    # Normalizar organización (extraer nombre de URL si es necesario)
    org_normalized = normalize_org(args.org)
    
    client = DevOpsClient(org_normalized, args.project, args.pat)

    force_interactive = args.interactive
    has_args = any([args.search, args.definition_id, args.release_id, args.stage_filter, args.status_filter, args.active_only, args.diff])

    if force_interactive:
        run_interactive = True
    elif args.json_output:
        run_interactive = False
    elif sys.stdin.isatty() and not has_args:
        run_interactive = True
    else:
        run_interactive = False

    try:
        if run_interactive:
            interactive_mode(client, args)
        else:
            param_mode(client, args)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]🚫 Cancelado por el usuario.[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def export_results(data, output_format: str = "json", output_dir: str = "outcome"):
    """Exporta resultados usando ExportManager centralizado con fallback."""
    
    from pathlib import Path
    import json
    import csv
    from datetime import datetime
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual
        if output_format == "json":
            filepath = output_path / f"azdo_release_explorer_rich_{ts}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": data}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"azdo_release_explorer_rich_{ts}.csv"
            if isinstance(data, list) and data and isinstance(data[0], dict):
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            return None
        
        print(f"✅ Resultados exportados a: {filepath}")
        return str(filepath)
    
    # Usar ExportManager
    manager = ExportManager("azdo_release_explorer_rich", "1.0.0")
    
    summary = {"total_items": len(data) if isinstance(data, list) else 1}
    
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    
    return None
