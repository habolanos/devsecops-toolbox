#!/usr/bin/env python3
"""
Azure DevOps Release Pipeline Explorer con Rich UI + Diff
Requiere: pip install rich
Cross-platform: Windows, Linux, macOS
"""

import argparse
import base64
import json
import os
import sys
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

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


API_VERSION = "7.0"
console = Console()

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


def status_color(status: str) -> str:
    return STATUS_COLORS.get(status.lower().replace(" ", ""), "white")


def cell(val_a: str, val_b: str) -> Tuple[str, str]:
    """Retorna string con color para tabla diff."""
    if val_a == val_b:
        return f"[green]{val_a}[/green]", f"[green]{val_b}[/green]"
    return f"[red]{val_a}[/red]", f"[red]{val_b}[/red]"


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
    title = f"[bold]🔍 DIFF: Release #{id_a} vs Release #{id_b}[/bold]"
    console.print(Panel(title, border_style="bright_cyan", expand=False))

    # --- Info General ---
    def info_table():
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        t.add_column("Campo")
        t.add_column(f"Release #{id_a}", style="cyan")
        t.add_column(f"Release #{id_b}", style="magenta")

        fields = [
            ("Nombre", "name"),
            ("Status", "status"),
            ("Creado por", ("createdBy", "displayName")),
            ("Fecha Creación", "createdOn"),
            ("Fecha Modif.", "modifiedOn"),
            ("Descripción", "description"),
        ]

        for label, key in fields:
            if isinstance(key, tuple):
                val_a = release_a.get(key[0], {}).get(key[1], "N/A")
                val_b = release_b.get(key[0], {}).get(key[1], "N/A")
            else:
                val_a = release_a.get(key, "N/A") or "N/A"
                val_b = release_b.get(key, "N/A") or "N/A"
            ca, cb = cell(val_a, val_b)
            t.add_row(label, ca, cb)
        return t

    console.print(Panel(info_table(), title="📋 Información General", border_style="blue"))

    # --- Artefactos ---
    def artifact_table():
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        t.add_column("Alias")
        t.add_column(f"BuildId #{id_a}")
        t.add_column(f"Versión #{id_a}")
        t.add_column(f"BuildId #{id_b}")
        t.add_column(f"Versión #{id_b}")

        arts_a = {a.get("alias", "N/A"): a for a in release_a.get("artifacts", [])}
        arts_b = {a.get("alias", "N/A"): a for a in release_b.get("artifacts", [])}
        all_aliases = sorted(set(list(arts_a.keys()) + list(arts_b.keys())))

        for alias in all_aliases:
            in_a = alias in arts_a
            in_b = alias in arts_b
            def get_vals(art):
                ref = art.get("definitionReference", {}).get("version", {})
                return ref.get("id", "N/A"), ref.get("name", "N/A")
            bid_a, ver_a = get_vals(arts_a[alias]) if in_a else ("N/A", "N/A")
            bid_b, ver_b = get_vals(arts_b[alias]) if in_b else ("N/A", "N/A")
            cbid_a, cbid_b = cell(bid_a, bid_b)
            cver_a, cver_b = cell(ver_a, ver_b)
            t.add_row(alias, cbid_a, cver_a, cbid_b, cver_b)
        return t

    console.print(Panel(artifact_table(), title="📦 Artefactos", border_style="green"))

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

        envs_a = {e.get("name", "N/A"): e for e in release_a.get("environments", [])}
        envs_b = {e.get("name", "N/A"): e for e in release_b.get("environments", [])}
        all_stages = sorted(set(list(envs_a.keys()) + list(envs_b.keys())))

        for stage in all_stages:
            in_a = stage in envs_a
            in_b = stage in envs_b

            def env_vals(env):
                st = env.get("status", "N/A")
                pre = ", ".join([a.get("status", "?") for a in env.get("preDeployApprovals", [])]) or "N/A"
                post = ", ".join([a.get("status", "?") for a in env.get("postDeployApprovals", [])]) or "N/A"
                return st, pre, post

            sta_a, pra_a, poa_a = env_vals(envs_a[stage]) if in_a else ("N/A", "N/A", "N/A")
            sta_b, pra_b, poa_b = env_vals(envs_b[stage]) if in_b else ("N/A", "N/A", "N/A")

            csta_a, csta_b = cell(sta_a, sta_b)
            cpra_a, cpra_b = cell(pra_a, pra_b)
            cpoa_a, cpoa_b = cell(poa_a, poa_b)

            t.add_row(stage, csta_a, cpra_a, cpoa_a, csta_b, cpra_b, cpoa_b)
        return t

    console.print(Panel(stage_table(), title="🎭 Stages / Environments", border_style="yellow"))

    # --- Variables ---
    def variable_table():
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
        t.add_column("Variable")
        t.add_column(f"Valor #{id_a}")
        t.add_column(f"Valor #{id_b}")

        vars_a = release_a.get("variables", {})
        vars_b = release_b.get("variables", {})
        all_vars = sorted(set(list(vars_a.keys()) + list(vars_b.keys())))

        for vname in all_vars:
            in_a = vname in vars_a
            in_b = vname in vars_b
            val_a = vars_a[vname].get("value", "N/A") if isinstance(vars_a.get(vname), dict) else str(vars_a.get(vname, "N/A"))
            val_b = vars_b[vname].get("value", "N/A") if isinstance(vars_b.get(vname), dict) else str(vars_b.get(vname, "N/A"))

            cva, cvb = cell(val_a, val_b)
            t.add_row(vname, cva, cvb)
        return t

    vars_a = release_a.get("variables", {})
    vars_b = release_b.get("variables", {})
    if vars_a or vars_b:
        console.print(Panel(variable_table(), title="🔧 Variables del Release", border_style="magenta"))


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
