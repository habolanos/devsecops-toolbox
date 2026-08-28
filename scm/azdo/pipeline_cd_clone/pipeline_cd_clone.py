#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Pipeline CD Clone

Clona un Pipeline CD completo a partir de un definition ID existente.
Crea una nueva definición con nuevo nombre (default: LAB-{nombre_actual}),
limpieza de campos del sistema, backup previo y dry-run.

Uso:
    python pipeline_cd_clone.py --source-id 2758 --pat TOKEN
    python pipeline_cd_clone.py --source-id 2758 --new-name "Mi-Pipeline" --new-path "\\Pipelines\\LAB" --pat TOKEN
    python pipeline_cd_clone.py --source-id 2758 --dry-run --pat TOKEN
    python pipeline_cd_clone.py --interactive
"""

import argparse
import base64
import copy
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.error
import urllib.request

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

console = Console()

__version__ = "1.0.0"
__author__ = "Harold Adrian"

API_VERSION = "7.0"

BACKUP_DIR = Path("outcome") / "backups" / "clone"

SYSTEM_FIELDS_TO_CLEAN = [
    "id", "revision", "createdOn", "modifiedOn", "createdBy", "modifiedBy",
    "createdBy@type", "modifiedBy@type", "_links", "url", "projectReference",
    "isDeleted", "currentRelease", "badgeUrl", "lastRelease",
]

ENV_FIELDS_TO_CLEAN = ["id", "releaseId"]


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
    """Carga configuración desde scm/config.json si existe."""
    config_file = Path(__file__).parent.parent.parent / "config.json"
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
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ No se pudo cargar config.json: {e}{Colors.ENDC}")
    return {}


def create_auth_header(pat: str) -> str:
    credentials = f":{pat}"
    encoded = base64.b64encode(credentials.encode('ascii')).decode('ascii')
    return f"Basic {encoded}"


def normalize_org(org: str) -> str:
    if org.startswith("https://"):
        return org.rstrip('/').split('/')[-1]
    return org


# ═══════════════════════════════════════════════════════════════════════════════
# API CALLS
# ═══════════════════════════════════════════════════════════════════════════════
def _parse_error_body(body: str) -> str:
    """Extrae el mensaje de error de una respuesta HTTP de Azure DevOps."""
    try:
        err = json.loads(body)
        msg = err.get('message', '')
        if msg:
            return msg
        inner = err.get('innerException', {})
        if inner and inner.get('message'):
            return inner['message']
    except Exception:
        pass
    return body[:500] if body else ''


def api_get(url: str, pat: str) -> Dict:
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json',
    }
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        msg = _parse_error_body(error_body)
        raise urllib.error.HTTPError(e.url, e.code, f"{e.reason} - {msg}", e.headers, None)


def api_post(url: str, pat: str, body: Dict) -> Dict:
    headers = {
        'Authorization': create_auth_header(pat),
        'Content-Type': 'application/json',
    }
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        msg = _parse_error_body(error_body)
        raise urllib.error.HTTPError(e.url, e.code, f"{e.reason} - {msg}", e.headers, None)


def get_release_definition(org: str, project: str, def_id: int, pat: str) -> Dict:
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{def_id}?api-version={API_VERSION}"
    return api_get(url, pat)


def create_release_definition(org: str, project: str, definition: Dict, pat: str) -> Dict:
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions?api-version={API_VERSION}"
    return api_post(url, pat, definition)


# ═══════════════════════════════════════════════════════════════════════════════
# CLONE LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def clean_definition_for_clone(definition: Dict) -> Dict:
    """Limpia campos del sistema para crear una nueva definición."""
    cleaned = copy.deepcopy(definition)

    for field in SYSTEM_FIELDS_TO_CLEAN:
        cleaned.pop(field, None)

    for env in cleaned.get("environments", []):
        for field in ENV_FIELDS_TO_CLEAN:
            env.pop(field, None)

    return cleaned


def extract_secrets(definition: Dict) -> List[Dict]:
    """Detecta variables secretas en la definición."""
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


def build_clone_payload(definition: Dict, new_name: str, new_path: Optional[str] = None) -> Dict:
    """Construye el payload para crear la nueva definición clonada."""
    payload = clean_definition_for_clone(definition)
    payload["name"] = new_name
    if new_path is not None:
        payload["path"] = new_path
    return payload


def create_clone_backup(definition: Dict, source_id: int, backup_path: str) -> str:
    """Crea backup de la definición origen antes de clonar."""
    os.makedirs(backup_path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = definition.get("name", f"pipeline-{source_id}")
    safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    filename = f"clone_source_{source_id}_{safe_name}_{timestamp}.json"
    filepath = os.path.join(backup_path, filename)

    backup_data = {
        "metadata": {
            "tool": "pipeline_cd_clone",
            "version": __version__,
            "backupDate": datetime.now().isoformat(),
            "sourcePipelineId": source_id,
            "sourcePipelineName": name,
            "revision": definition.get("revision", 0),
        },
        "definition": definition,
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)

    return filepath


# ═══════════════════════════════════════════════════════════════════════════════
# DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════
def show_source_info(definition: Dict) -> None:
    """Muestra información de la definición origen en tabla Rich."""
    table = Table(title=f"Pipeline #{definition.get('id')} - {definition.get('name', 'N/A')}", show_header=False)
    table.add_column("Campo", style="cyan", no_wrap=True)
    table.add_column("Valor", style="white")
    table.add_row("ID", str(definition.get('id', 'N/A')))
    table.add_row("Name", definition.get('name', 'N/A'))
    table.add_row("Path", definition.get('path', '\\'))
    table.add_row("Revision", str(definition.get('revision', 'N/A')))
    envs = definition.get('environments', [])
    env_summary = ", ".join([f"{e.get('name', '?')}" for e in envs])
    table.add_row("Environments", f"{len(envs)} ({env_summary})")
    vars_count = len(definition.get('variables', {}))
    table.add_row("Variables", f"{vars_count} variables")
    artifacts = definition.get('artifacts', [])
    table.add_row("Artifacts", f"{len(artifacts)} artifacts")
    console.print(table)


def show_clone_summary(source_def: Dict, new_name: str, new_path: str, secrets: List[Dict]) -> None:
    """Muestra resumen del clon a crear."""
    envs = source_def.get('environments', [])
    vars_count = len(source_def.get('variables', {}))
    artifacts = source_def.get('artifacts', [])

    table = Table(title="Resumen del Clon", show_header=False)
    table.add_column("Campo", style="cyan", no_wrap=True)
    table.add_column("Valor", style="white")
    table.add_row("Source ID", str(source_def.get('id', 'N/A')))
    table.add_row("Source Name", source_def.get('name', 'N/A'))
    table.add_row("Source Path", source_def.get('path', '\\'))
    table.add_row("New Name", new_name)
    table.add_row("New Path", new_path)
    table.add_row("Environments", f"{len(envs)} stages")
    table.add_row("Variables", f"{vars_count} ({len(secrets)} secrets)")
    table.add_row("Artifacts", f"{len(artifacts)}")
    console.print(table)


def show_dry_run(source_def: Dict, new_name: str, new_path: str, secrets: List[Dict]) -> None:
    """Muestra qué se haría en dry-run."""
    console.print(Panel(
        f"[yellow]DRY-RUN: No se creará el pipeline[/yellow]\n\n"
        f"  Source ID:    {source_def.get('id', 'N/A')}\n"
        f"  Source Name:  {source_def.get('name', 'N/A')}\n"
        f"  Source Path:  {source_def.get('path', '\\')}\n"
        f"  New Name:     {new_name}\n"
        f"  New Path:     {new_path}\n"
        f"  Environments: {len(source_def.get('environments', []))}\n"
        f"  Variables:    {len(source_def.get('variables', {}))} ({len(secrets)} secrets - no se copian valores)\n"
        f"  Artifacts:    {len(source_def.get('artifacts', []))}",
        title="🔍 Dry-Run",
        border_style="yellow",
    ))


def show_result(result: Dict) -> None:
    """Muestra el resultado de la creación."""
    console.print(Panel(
        f"[green]✅ Pipeline creado exitosamente[/green]\n\n"
        f"  New ID:       {result.get('id', 'N/A')}\n"
        f"  New Name:     {result.get('name', 'N/A')}\n"
        f"  New Path:     {result.get('path', '\\')}\n"
        f"  Revision:     {result.get('revision', 1)}\n"
        f"  URL:          {result.get('_links', {}).get('web', {}).get('href', 'N/A')}",
        title="Pipeline Creado",
        border_style="green",
    ))


# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE MODE
# ═══════════════════════════════════════════════════════════════════════════════
def interactive_mode() -> Dict:
    """Modo interactivo para clonar un pipeline."""
    console.print(Panel(
        "[bold]Azure DevOps Pipeline CD Clone - Modo Interactivo[/bold]",
        border_style="cyan",
    ))

    config = load_config()

    if config:
        console.print(f"[green]✓ Configuración cargada desde config.json[/green]")
    else:
        console.print(f"[yellow]⚠ No se encontró config.json[/yellow]")

    org = config.get('organization', 'Coppel-Retail')
    project = config.get('project', 'Cadena_de_Suministros')
    pat = config.get('pat', '')

    console.print(f"\n  Organización: [cyan]{org}[/cyan]  (informativo)")
    console.print(f"  Proyecto:      [cyan]{project}[/cyan]  (informativo)")
    console.print(f"  PAT:           [cyan]{'****' if pat else 'N/A'}[/cyan]  (informativo)")

    if not pat:
        pat = Prompt.ask("[bold]PAT[/bold]", password=True)

    source_id_str = Prompt.ask("[bold]ID del Pipeline origen a clonar[/bold]")
    try:
        source_id = int(source_id_str)
    except ValueError:
        console.print("[red]✗ Error: El ID debe ser un número entero[/red]")
        sys.exit(1)

    # Obtener definición con spinner
    with console.status("[cyan]Obteniendo definición...[/cyan]", spinner="dots"):
        try:
            definition = get_release_definition(org, project, source_id, pat)
        except urllib.error.HTTPError as e:
            console.print(f"\n[red]✗ Error HTTP {e.code}: {e.reason}[/red]")
            if e.code == 404:
                console.print(f"[yellow]  El pipeline #{source_id} no existe o no tienes acceso.[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]✗ Error: {e}[/red]")
            sys.exit(1)

    console.print(f"[green]✓ Pipeline encontrado: {definition.get('name', 'N/A')}[/green]")
    current_name = definition.get("name", "")
    current_path = definition.get("path", "\\")
    console.print(f"  Path actual: [dim]{current_path}[/dim]\n")

    show_source_info(definition)

    # Preguntar nombre
    default_name = f"LAB-{current_name}"
    new_name = Prompt.ask("[bold]Nombre del nuevo pipeline[/bold]", default=default_name)

    # Preguntar path
    new_path = Prompt.ask("[bold]Path del nuevo pipeline[/bold]", default=current_path)

    # Dry-run?
    dry_run = Confirm.ask("[bold]Modo dry-run (solo simular)?[/bold]", default=False)

    return {
        'org': org,
        'project': project,
        'source_id': source_id,
        'new_name': new_name,
        'new_path': new_path,
        'pat': pat,
        'dry_run': dry_run,
        'definition': definition,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="Clona un Pipeline CD completo a partir de un definition ID existente."
    )
    parser.add_argument('--org', default='', help='Organización de Azure DevOps')
    parser.add_argument('--project', default='', help='Proyecto')
    parser.add_argument('--source-id', type=int, help='ID de la definición origen a clonar')
    parser.add_argument('--new-name', default='', help='Nombre del nuevo pipeline (default: LAB-{nombre_actual})')
    parser.add_argument('--new-path', default='', help='Path del nuevo pipeline (default: mismo que origen)')
    parser.add_argument('--pat', default='', help='Personal Access Token')
    parser.add_argument('--dry-run', action='store_true', help='Solo simular, no crear')
    parser.add_argument('--backup', action='store_true', default=True, help='Crear backup del origen antes de clonar')
    parser.add_argument('--backup-path', default=str(BACKUP_DIR), help='Carpeta de backups')
    parser.add_argument('--interactive', action='store_true', help='Modo interactivo')
    args = parser.parse_args()

    console.print(Panel(
        f"[bold]Azure DevOps Pipeline CD Clone v{__version__}[/bold]",
        border_style="cyan",
    ))

    if args.interactive:
        params = interactive_mode()
        org = params['org']
        project = params['project']
        source_id = params['source_id']
        new_name = params['new_name']
        new_path = params['new_path']
        pat = params['pat']
        dry_run = params['dry_run']
        definition = params['definition']
    else:
        # Cargar config si faltan args
        config = load_config()
        org = args.org or config.get('organization', '')
        project = args.project or config.get('project', '')
        pat = args.pat or config.get('pat', '')

        if not source_id_check(args.source_id):
            console.print("[red]✗ Error: --source-id es requerido[/red]")
            sys.exit(1)
        if not pat:
            console.print("[red]✗ Error: --pat es requerido (no encontrado en config.json ni CLI)[/red]")
            sys.exit(1)
        if not org or not project:
            console.print("[red]✗ Error: --org y --project son requeridos[/red]")
            sys.exit(1)

        org = normalize_org(org)
        source_id = args.source_id
        dry_run = args.dry_run

        # Obtener definición con spinner
        with console.status(f"[cyan]Obteniendo definición #{source_id}...[/cyan]", spinner="dots"):
            try:
                definition = get_release_definition(org, project, source_id, pat)
            except urllib.error.HTTPError as e:
                console.print(f"[red]✗ Error HTTP {e.code}: {e.reason}[/red]")
                sys.exit(1)
            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/red]")
                sys.exit(1)

        console.print(f"[green]✓ Pipeline encontrado: {definition.get('name', 'N/A')}[/green]")

        # Defaults
        current_name = definition.get("name", "")
        current_path = definition.get("path", "\\")
        new_name = args.new_name or f"LAB-{current_name}"
        new_path = args.new_path or current_path

    # Info mostrada en ambos modos
    console.print(f"\n  Organización: [cyan]{org}[/cyan]")
    console.print(f"  Proyecto:      [cyan]{project}[/cyan]")
    console.print(f"  Source ID:     [cyan]#{source_id}[/cyan]")
    console.print(f"  New Name:      [cyan]{new_name}[/cyan]")
    console.print(f"  New Path:      [cyan]{new_path}[/cyan]")
    console.print(f"  Dry-run:       [{'yellow]Si[/]' if dry_run else '[green]No[/green]'}\n")

    # Detectar secrets
    secrets = extract_secrets(definition)
    if secrets:
        console.print(f"[yellow]⚠ {len(secrets)} variable(s) secreta(s) detectada(s) - los valores no se copian[/yellow]")
        for s in secrets:
            scope_str = f"{s['scope']}" + (f" ({s['env']})" if s.get('env') else "")
            console.print(f"  [dim]{scope_str}: {s['name']}[/dim]")

    # Mostrar info de la definición origen
    show_source_info(definition)

    # Resumen del clon
    show_clone_summary(definition, new_name, new_path, secrets)

    if dry_run:
        show_dry_run(definition, new_name, new_path, secrets)
        console.print(f"\n[yellow]🔍 DRY-RUN completado. No se creó ningún pipeline.[/yellow]")
        return

    # Confirmar
    if not args.interactive:
        if not Confirm.ask(f"[bold]¿Crear pipeline '{new_name}'?[/bold]", default=False):
            console.print("[yellow]Operación cancelada.[/yellow]")
            return

    # Backup
    if args.backup:
        with console.status("[cyan]Creando backup del origen...[/cyan]", spinner="dots"):
            backup_file = create_clone_backup(definition, source_id, args.backup_path)
        console.print(f"[green]✓ Backup guardado: {backup_file}[/green]")

    # Construir payload
    with console.status("[cyan]Construyendo payload del clon...[/cyan]", spinner="dots"):
        payload = build_clone_payload(definition, new_name, new_path)

    # Crear con barra de progreso
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Creando nuevo pipeline...", total=1)
        try:
            result = create_release_definition(org, project, payload, pat)
            progress.update(task, advance=1, description="[green]✓ Pipeline creado")
        except urllib.error.HTTPError as e:
            progress.update(task, description=f"[red]✗ Error HTTP {e.code}")
            console.print(f"\n[red]✗ Error HTTP {e.code}: {e.reason}[/red]")
            if e.code == 403:
                console.print(f"[yellow]  ⚠ Error de permisos (403 Forbidden).[/yellow]")
                console.print(f"[yellow]  Posibles causas:[/yellow]")
                console.print(f"[dim]    • El PAT no tiene permisos de 'Create' en Release Definitions[/dim]")
                console.print(f"[dim]    • El usuario no tiene permisos 'Use' sobre los agent pools referenciados[/dim]")
                console.print(f"[dim]    • Contacta al administrador de Azure DevOps para solicitar permisos[/dim]")
            sys.exit(1)
        except Exception as e:
            progress.update(task, description=f"[red]✗ Error")
            console.print(f"\n[red]✗ Error: {e}[/red]")
            sys.exit(1)

    # Mostrar resultado
    show_result(result)

    # Reporte JSON
    report = {
        "tool": "pipeline_cd_clone",
        "version": __version__,
        "timestamp": datetime.now().isoformat(),
        "source": {
            "id": source_id,
            "name": definition.get("name", ""),
            "path": definition.get("path", ""),
        },
        "target": {
            "id": result.get("id"),
            "name": result.get("name", new_name),
            "path": result.get("path", new_path),
            "revision": result.get("revision", 1),
        },
        "secrets": secrets,
        "backup_file": backup_file if args.backup else None,
    }

    report_dir = Path("outcome")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"clone_report_{source_id}_to_{result.get('id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    console.print(f"\n[dim]📄 Reporte exportado: {report_path}[/dim]")

    console.print(f"\n[green bold]✅ Clone completado exitosamente.[/green bold]")


def source_id_check(source_id) -> bool:
    return source_id is not None and source_id > 0


if __name__ == '__main__':
    main()
