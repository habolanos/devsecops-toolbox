#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Service Account Checker - Herramienta SRE para gestión de Service Accounts

Lista y analiza Service Accounts en Google Cloud Platform:
- Lista todas las Service Accounts del proyecto
- Muestra estado (habilitada/deshabilitada)
- Identifica keys y su antigüedad
- Detecta Service Accounts sin uso reciente
- Analiza roles asignados (IAM bindings)

Características:
- Usa gcloud CLI (no requiere APIs de Python especiales)
- Ejecución paralela con ThreadPoolExecutor
- Validación de conexión GCP antes de ejecutar
- Exportación a TXT, CSV y JSON

El resultado se guarda en: outcome/sa_report_<project_id>_<timestamp>.<ext>

Autor: Harold Adrian
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any
from pathlib import Path

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.markdown import Markdown
    from rich.box import ROUNDED, HEAVY
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"



try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

def run_gcloud_command(cmd: str, debug: bool = False, console=None) -> Optional[Any]:
    """Ejecuta un comando gcloud y retorna el resultado como JSON."""
    try:
        if debug and console and RICH_AVAILABLE:
            console.print(f"[dim]DEBUG: {cmd}[/dim]")
        elif debug:
            print(f"DEBUG: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            if debug:
                if console and RICH_AVAILABLE:
                    console.print(f"[dim]Error: {result.stderr[:200]}[/dim]")
                else:
                    print(f"DEBUG Error: {result.stderr[:200]}")
            return None
        
        if not result.stdout.strip():
            return []
        
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip() if result.stdout else None
    except Exception as e:
        if debug:
            if console and RICH_AVAILABLE:
                console.print(f"[dim]Exception: {e}[/dim]")
            else:
                print(f"DEBUG Exception: {e}")
        return None


def get_service_accounts(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene todas las Service Accounts del proyecto."""
    cmd = f'gcloud iam service-accounts list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console)
    return result if isinstance(result, list) else []


def get_service_account_keys(email: str, project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene las keys de una Service Account."""
    cmd = f'gcloud iam service-accounts keys list --iam-account={email} --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console)
    return result if isinstance(result, list) else []


def get_iam_policy(project_id: str, debug: bool, console) -> Dict:
    """Obtiene la política IAM del proyecto."""
    cmd = f'gcloud projects get-iam-policy {project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console)
    return result if isinstance(result, dict) else {}


def get_sa_roles(email: str, iam_policy: Dict) -> List[str]:
    """Extrae los roles asignados a una Service Account desde la política IAM."""
    roles = []
    member = f"serviceAccount:{email}"
    
    for binding in iam_policy.get('bindings', []):
        if member in binding.get('members', []):
            roles.append(binding.get('role', 'N/A'))
    
    return roles


def calculate_key_age(valid_after_time: str) -> str:
    """Calcula la antigüedad de una key."""
    try:
        created = datetime.fromisoformat(valid_after_time.replace('Z', '+00:00'))
        now = datetime.now(created.tzinfo)
        delta = now - created
        
        if delta.days > 365:
            years = delta.days // 365
            return f"{years}y"
        elif delta.days > 30:
            months = delta.days // 30
            return f"{months}mo"
        elif delta.days > 0:
            return f"{delta.days}d"
        else:
            return "<1d"
    except Exception:
        return "N/A"


def check_gcp_connection(project_id: str, console, debug: bool = False) -> bool:
    """Verifica la conexión a GCP antes de ejecutar el script."""
    try:
        if RICH_AVAILABLE and console:
            with console.status("[bold cyan]Verificando conexión a GCP...[/]"):
                return _verify_gcp_auth(project_id, console, debug)
        else:
            print("Verificando conexión a GCP...")
            return _verify_gcp_auth(project_id, console, debug)
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ Error verificando conexión: {e}[/]")
        else:
            print(f"❌ Error verificando conexión: {e}")
        return False


def _verify_gcp_auth(project_id: str, console, debug: bool) -> bool:
    """Función interna para verificar autenticación GCP."""
    auth_cmd = 'gcloud auth list --filter=status:ACTIVE --format="value(account)"'
    if debug:
        if RICH_AVAILABLE and console:
            console.print(f"[dim]DEBUG: {auth_cmd}[/]")
        else:
            print(f"DEBUG: {auth_cmd}")
    
    auth_result = subprocess.run(auth_cmd, shell=True, capture_output=True, text=True)
    
    if auth_result.returncode != 0 or not auth_result.stdout.strip():
        if RICH_AVAILABLE and console:
            console.print("[red]❌ No hay sesión activa de gcloud. Ejecuta: gcloud auth login[/]")
        else:
            print("❌ No hay sesión activa de gcloud. Ejecuta: gcloud auth login")
        return False
    
    active_account = auth_result.stdout.strip().split('\n')[0]
    if RICH_AVAILABLE and console:
        console.print(f"[green]✓[/] Cuenta activa: [cyan]{active_account}[/]")
    else:
        print(f"✓ Cuenta activa: {active_account}")
    
    project_cmd = f'gcloud projects describe {project_id} --format="value(projectId)" 2>&1'
    if debug:
        if RICH_AVAILABLE and console:
            console.print(f"[dim]DEBUG: {project_cmd}[/]")
        else:
            print(f"DEBUG: {project_cmd}")
    
    project_result = subprocess.run(project_cmd, shell=True, capture_output=True, text=True)
    
    if project_result.returncode != 0:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ No tienes acceso al proyecto: {project_id}[/]")
        else:
            print(f"❌ No tienes acceso al proyecto: {project_id}")
        return False
    
    if RICH_AVAILABLE and console:
        console.print(f"[green]✓[/] Proyecto válido: [cyan]{project_id}[/]")
    else:
        print(f"✓ Proyecto válido: {project_id}")
    return True


def analyze_service_accounts(service_accounts: List[Dict], iam_policy: Dict, 
                              project_id: str, debug: bool, console) -> List[Dict]:
    """Analiza cada Service Account y agrega información de keys y roles."""
    analyzed = []
    
    for sa in service_accounts:
        email = sa.get('email', '')
        
        # Obtener keys
        keys = get_service_account_keys(email, project_id, debug, console)
        user_managed_keys = [k for k in keys if k.get('keyType') == 'USER_MANAGED']
        system_keys = [k for k in keys if k.get('keyType') == 'SYSTEM_MANAGED']
        
        # Calcular antigüedad de keys
        key_ages = []
        oldest_key_age = None
        for key in user_managed_keys:
            age = calculate_key_age(key.get('validAfterTime', ''))
            key_ages.append(age)
            if not oldest_key_age or age > oldest_key_age:
                oldest_key_age = age
        
        # Obtener roles
        roles = get_sa_roles(email, iam_policy)
        
        # Determinar estado
        disabled = sa.get('disabled', False)
        
        analyzed.append({
            'email': email,
            'name': sa.get('displayName', 'N/A'),
            'description': sa.get('description', ''),
            'disabled': disabled,
            'status': '🔴 Deshabilitada' if disabled else '🟢 Activa',
            'user_managed_keys': len(user_managed_keys),
            'system_keys': len(system_keys),
            'oldest_key_age': oldest_key_age or 'N/A',
            'roles': roles,
            'roles_count': len(roles),
            'unique_id': sa.get('uniqueId', 'N/A'),
        })
    
    return analyzed


def create_sa_table(analyzed_sas: List[Dict], console) -> Table:
    """Crea tabla de Service Accounts."""
    table = Table(title="🔐 Service Accounts", box=box.ROUNDED, show_lines=True)
    table.add_column("Email", style="cyan", max_width=50)
    table.add_column("Estado", style="green", justify="center")
    table.add_column("Keys", style="yellow", justify="center")
    table.add_column("Antigüedad", style="magenta", justify="center")
    table.add_column("Roles", style="blue", justify="center")
    
    for sa in analyzed_sas:
        status_style = "red" if sa['disabled'] else "green"
        keys_warning = ""
        if sa['user_managed_keys'] > 0:
            keys_warning = f"⚠️ {sa['user_managed_keys']}"
        else:
            keys_warning = "0"
        
        table.add_row(
            sa['email'][:50],
            f"[{status_style}]{sa['status']}[/]",
            keys_warning,
            sa['oldest_key_age'],
            str(sa['roles_count'])
        )
    
    return table


def generate_report(project_id: str, analyzed_sas: List[Dict]) -> str:
    """Genera el reporte como string."""
    lines = []
    now_local = datetime.now()
    
    lines.append("=" * 100)
    lines.append(f"🔐 REPORTE DE SERVICE ACCOUNTS - Proyecto: {project_id}")
    lines.append(f"🕐 Fecha: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"📦 Versión: {__version__}")
    lines.append("=" * 100)
    lines.append("")

    # Resumen
    total = len(analyzed_sas)
    active = sum(1 for sa in analyzed_sas if not sa['disabled'])
    disabled = sum(1 for sa in analyzed_sas if sa['disabled'])
    with_keys = sum(1 for sa in analyzed_sas if sa['user_managed_keys'] > 0)
    
    lines.append("📊 RESUMEN:")
    lines.append("-" * 100)
    lines.append(f"   Total de Service Accounts: {total}")
    lines.append(f"   🟢 Activas: {active}")
    lines.append(f"   🔴 Deshabilitadas: {disabled}")
    lines.append(f"   🔑 Con keys de usuario: {with_keys}")
    lines.append("")

    # Detalle de cada SA
    lines.append("📋 DETALLE DE SERVICE ACCOUNTS:")
    lines.append("-" * 100)
    
    for i, sa in enumerate(analyzed_sas, 1):
        lines.append(f"\n{i}. {sa['email']}")
        lines.append(f"   Nombre: {sa['name']}")
        lines.append(f"   Estado: {sa['status']}")
        lines.append(f"   Keys de usuario: {sa['user_managed_keys']}")
        if sa['user_managed_keys'] > 0:
            lines.append(f"   ⚠️  Antigüedad key más antigua: {sa['oldest_key_age']}")
        lines.append(f"   Roles asignados: {sa['roles_count']}")
        if sa['roles']:
            for role in sa['roles'][:5]:
                role_short = role.split('/')[-1] if '/' in role else role
                lines.append(f"      • {role_short}")
            if len(sa['roles']) > 5:
                lines.append(f"      ... y {len(sa['roles']) - 5} más")
    
    lines.append("")
    lines.append("=" * 100)
    
    # Alertas
    lines.append("")
    lines.append("⚠️  ALERTAS Y RECOMENDACIONES:")
    lines.append("-" * 100)
    
    alerts = []
    for sa in analyzed_sas:
        if sa['user_managed_keys'] > 0:
            alerts.append(f"🔑 {sa['email']} tiene {sa['user_managed_keys']} key(s) de usuario - considerar rotación")
        if sa['roles_count'] > 10:
            alerts.append(f"📛 {sa['email']} tiene {sa['roles_count']} roles - revisar principio de mínimo privilegio")
    
    if alerts:
        for alert in alerts:
            lines.append(f"   {alert}")
    else:
        lines.append("   ✅ No se detectaron alertas")
    
    lines.append("")
    lines.append("=" * 100)
    
    return "\n".join(lines)


def create_summary_table(analyzed_sas: List[Dict], console) -> Table:
    """Crea tabla resumen."""
    table = Table(title="📊 Resumen de Service Accounts", box=box.ROUNDED)
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green", justify="right")
    
    total = len(analyzed_sas)
    active = sum(1 for sa in analyzed_sas if not sa['disabled'])
    disabled = sum(1 for sa in analyzed_sas if sa['disabled'])
    with_keys = sum(1 for sa in analyzed_sas if sa['user_managed_keys'] > 0)
    total_keys = sum(sa['user_managed_keys'] for sa in analyzed_sas)
    
    table.add_row("Total Service Accounts", str(total))
    table.add_row("Activas", f"🟢 {active}")
    table.add_row("Deshabilitadas", f"🔴 {disabled}")
    table.add_row("Con keys de usuario", f"🔑 {with_keys}")
    table.add_row("Total keys de usuario", str(total_keys))
    
    return table


def print_execution_summary(start_time: datetime, console, project_id: str, 
                            analyzed_sas: List[Dict]) -> None:
    """Imprime tabla resumen de ejecución."""
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if RICH_AVAILABLE and console:
        table = Table(title="⏱️ Resumen de Ejecución", box=box.ROUNDED)
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        
        table.add_row("Proyecto", project_id)
        table.add_row("Tiempo de ejecución", f"{duration:.2f}s")
        table.add_row("Service Accounts analizadas", str(len(analyzed_sas)))
        
        console.print()
        console.print(Panel(table, border_style="blue"))
    else:
        print(f"\n⏱️ Resumen de Ejecución")
        print(f"  Proyecto: {project_id}")
        print(f"  Tiempo: {duration:.2f}s")
        print(f"  Service Accounts: {len(analyzed_sas)}")


def export_to_json(analyzed_sas: List[Dict], project_id: str, output_dir: str, tz_name: str = "America/Mazatlan") -> str:
    """Exporta datos a archivo JSON con metadatos completos."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"sa_report_{project_id}_{timestamp}.json")
    
    export_data = {
        "report_metadata": {
            "tool_name": "GCP Service Account Checker",
            "version": __version__,
            "project_id": project_id,
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "total": len(analyzed_sas),
            "active": sum(1 for sa in analyzed_sas if not sa['disabled']),
            "disabled": sum(1 for sa in analyzed_sas if sa['disabled']),
            "with_user_keys": sum(1 for sa in analyzed_sas if sa['user_managed_keys'] > 0),
        },
        "service_accounts": analyzed_sas
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
    
    return filepath


def export_to_csv(analyzed_sas: List[Dict], project_id: str, output_dir: str) -> str:
    """Exporta datos a archivo CSV."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"sa_report_{project_id}_{timestamp}.csv")
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['project_id', 'email', 'name', 'status', 'disabled', 
                        'user_keys', 'oldest_key_age', 'roles_count', 'roles'])
        
        for sa in analyzed_sas:
            roles_str = ';'.join(sa['roles']) if sa['roles'] else ''
            writer.writerow([
                project_id,
                sa['email'],
                sa['name'],
                'Deshabilitada' if sa['disabled'] else 'Activa',
                sa['disabled'],
                sa['user_managed_keys'],
                sa['oldest_key_age'],
                sa['roles_count'],
                roles_str
            ])
    
    return filepath


def export_to_txt(report: str, project_id: str, output_dir: str) -> str:
    """Exporta reporte a archivo TXT."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"sa_report_{project_id}_{timestamp}.txt")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return filepath


def get_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="SRE Tool: GCP Service Account Checker - Análisis de Service Accounts",
        add_help=False
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        default="cpl-corp-cial-prod-17042024",
        help="ID del proyecto GCP (Default: cpl-corp-cial-prod-17042024)"
    )
    parser.add_argument(
        "--projects",
        type=str,
        default="",
        help="Múltiples proyectos GCP separados por coma (ej: proj1,proj2,proj3)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa modo debug para ver información adicional"
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Muestra documentación completa del script"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["csv", "json", "txt"],
        default="txt",
        help="Formato de exportación (default: txt)"
    )
    parser.add_argument(
        "--no-keys",
        action="store_true",
        help="No consultar keys de cada SA (más rápido)"
    )
    return parser.parse_args()


def show_help(console) -> None:
    """Muestra la documentación completa del script leyendo el README.md."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(script_dir, "README.md")
    
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        if RICH_AVAILABLE and console:
            md = Markdown(readme_content)
            console.print(md)
        else:
            print(readme_content)
    except FileNotFoundError:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ No se encontró el archivo README.md en {script_dir}[/red]")
        else:
            print(f"❌ No se encontró el archivo README.md en {script_dir}")
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ Error leyendo README.md: {e}[/red]")
        else:
            print(f"❌ Error leyendo README.md: {e}")


def main() -> int:
    """Función principal del script."""
    args = get_args()
    
    if not RICH_AVAILABLE:
        print("⚠️ Rich no disponible. Usando salida básica.")
        console = None
    else:
        console = Console()
    
    if args.help:
        show_help(console)
        return 0
    
    start_time = datetime.now()
    debug = args.debug
    
    # Determinar proyectos
    if args.projects:
        # Si se especifica --projects, usar solo esos
        projects = [p.strip() for p in args.projects.split(',') if p.strip()]
    else:
        # Intentar cargar desde config.json
        projects = load_projects_from_config(debug, console)
        if not projects:
            # Fallback al proyecto por defecto
            projects = [args.project]
    
    # Mostrar información inicial
    if RICH_AVAILABLE and console:
        console.print(f"\n[bold cyan]Proyectos:[/bold cyan] {', '.join(projects)}")
        console.print(f"[bold cyan]Total:[/bold cyan] {len(projects)}")
    else:
        print(f"🚀 Iniciando análisis de {len(projects)} proyecto(s)...")
        print(f"   Proyectos: {', '.join(projects)}")
    
    # Procesar múltiples proyectos en paralelo
    results_summary = []
    all_analyzed_sas = {}
    
    if RICH_AVAILABLE and console:
        console.print(f"\n[bold cyan]Extrayendo datos de proyectos...[/bold cyan]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Procesando proyectos...",
                total=len(projects)
            )
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(process_project, proj, debug, console): proj
                    for proj in projects
                }
                
                for future in as_completed(futures):
                    project = futures[future]
                    try:
                        analyzed_sas = future.result()
                        all_analyzed_sas[project] = analyzed_sas
                        results_summary.append({
                            'project': project,
                            'status': '✅',
                            'sas': len(analyzed_sas)
                        })
                    except Exception as e:
                        results_summary.append({
                            'project': project,
                            'status': '❌',
                            'sas': 0
                        })
                        if debug:
                            console.print(f"[red]Error en {project}: {e}[/red]")
                    
                    progress.update(task, advance=1)
    else:
        # Fallback sin Rich
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(process_project, proj, debug, console): proj
                for proj in projects
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                project = futures[future]
                try:
                    analyzed_sas = future.result()
                    all_analyzed_sas[project] = analyzed_sas
                    print(f"[{i}/{len(projects)}] ✅ {project}: {len(analyzed_sas)} SAs")
                except Exception as e:
                    print(f"[{i}/{len(projects)}] ❌ {project}: {e}")
    
    # Mostrar tabla de resultados
    if RICH_AVAILABLE and console and results_summary:
        table = Table(
            title="📊 Resumen de Extracción por Proyecto",
            box=ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Proyecto", style="cyan", width=40)
        table.add_column("Estado", style="green", justify="center", width=10)
        table.add_column("Service Accounts", style="yellow", justify="right", width=15)
        
        for result in results_summary:
            table.add_row(
                result['project'],
                result['status'],
                str(result['sas'])
            )
        
        console.print(table)
    
    # Procesar y mostrar resultados por proyecto
    try:
        outcome_dir = str(get_output_dir("outcome"))
        os.makedirs(outcome_dir, exist_ok=True)
        
        for project_id, analyzed_sas in all_analyzed_sas.items():
            if RICH_AVAILABLE and console:
                console.print(f"\n[bold cyan]Proyecto: {project_id}[/bold cyan]")
                console.print(create_summary_table(analyzed_sas, console))
                console.print(create_sa_table(analyzed_sas, console))
            
            # Generar reporte
            report = generate_report(project_id, analyzed_sas)
            
            if not RICH_AVAILABLE:
                print(report)
            
            # Guardar en archivo
            if args.output == "json":
                filepath = export_to_json(analyzed_sas, project_id, outcome_dir, "America/Mazatlan")
            elif args.output == "csv":
                filepath = export_to_csv(analyzed_sas, project_id, outcome_dir)
            else:
                filepath = export_to_txt(report, project_id, outcome_dir)
            
            if RICH_AVAILABLE and console:
                console.print(f"[green]✅ Reporte guardado:[/] {filepath}")
        
        # Resumen final
        if RICH_AVAILABLE and console:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            summary_table = Table(
                title="📈 Resumen de Ejecución",
                box=ROUNDED,
                show_header=True,
                header_style="bold cyan"
            )
            summary_table.add_column("Métrica", style="cyan")
            summary_table.add_column("Valor", style="green", justify="right")
            
            total_sas = sum(len(sas) for sas in all_analyzed_sas.values())
            summary_table.add_row("Proyectos", str(len(projects)))
            summary_table.add_row("Service Accounts", str(total_sas))
            summary_table.add_row("Duración", f"{duration:.2f}s")
            
            console.print(summary_table)

    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ Error ejecutando el análisis: {e}[/]")
        else:
            print(f"❌ Error ejecutando el análisis: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return 1

    return 0


def load_projects_from_config(debug: bool, console) -> List[str]:
    """Carga proyectos desde config.json."""
    try:
        import json
        from pathlib import Path
        
        # Buscar config.json en diferentes ubicaciones
        config_paths = [
            Path("config.json"),
            Path("scm/config.json"),
            Path("../config.json"),
        ]
        
        config_file = None
        for path in config_paths:
            if path.exists():
                config_file = path
                break
        
        if not config_file:
            if debug and console and RICH_AVAILABLE:
                console.print("[dim]config.json no encontrado[/dim]")
            return []
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Buscar proyectos en config.json
        projects = config.get('gcp', {}).get('service_accounts_reporter', {}).get('projects', [])
        
        if projects and debug and console and RICH_AVAILABLE:
            console.print(f"[dim]Cargados {len(projects)} proyectos desde config.json[/dim]")
        
        return projects if isinstance(projects, list) else []
    
    except Exception as e:
        if debug and console and RICH_AVAILABLE:
            console.print(f"[dim]Error cargando config.json: {e}[/dim]")
        return []


def process_project(project_id: str, debug: bool, console) -> List[Dict]:
    """Procesa un proyecto individual."""
    if not check_gcp_connection(project_id, console, debug):
        raise Exception(f"No se pudo conectar a {project_id}")
    
    # Obtener SAs y política IAM en paralelo
    with ThreadPoolExecutor(max_workers=2) as executor:
        sa_future = executor.submit(get_service_accounts, project_id, debug, console)
        iam_future = executor.submit(get_iam_policy, project_id, debug, console)
        
        service_accounts = sa_future.result()
        iam_policy = iam_future.result()
    
    # Analizar SAs
    analyzed_sas = analyze_service_accounts(
        service_accounts, iam_policy, project_id, debug, console
    )
    
    return analyzed_sas


if __name__ == "__main__":
    sys.exit(main())


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
            filepath = output_path / f"gcp_service_account_checker_{ts}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": data}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"gcp_service_account_checker_{ts}.csv"
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
    manager = ExportManager("gcp_service_account_checker", "1.0.0")
    
    summary = {"total_items": len(data) if isinstance(data, list) else 1}
    
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    
    return None
