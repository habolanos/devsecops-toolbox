#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud SQL Database Checker - Herramienta SRE para gestión de bases de datos

Lista y analiza las bases de datos por instancia de Cloud SQL:
- Lista todas las instancias Cloud SQL del proyecto
- Muestra las bases de datos de cada instancia
- Identifica estado de la instancia (RUNNING, STOPPED, etc.)
- Detecta tipo de base de datos (MySQL, PostgreSQL, SQL Server)
- Muestra información de réplicas y backups

Características:
- Usa gcloud CLI (no requiere APIs de Python especiales)
- Ejecución paralela con ThreadPoolExecutor
- Validación de conexión GCP antes de ejecutar
- Exportación a TXT, CSV y JSON

El resultado se guarda en: outcome/db_report_<project_id>_<timestamp>.<ext>

Autor: Harold Adrian
"""

import argparse
import subprocess
import json
import csv
import os
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any

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
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"


def get_args():
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="SRE Tool: Cloud SQL Database Inventory (gcloud)",
        add_help=False
    )
    parser.add_argument(
        "--project",
        type=str,
        default="cpl-corp-cial-prod-17042024",
        help="ID del proyecto de GCP (Default: cpl-corp-cial-prod-17042024)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa modo debug para ver comandos gcloud ejecutados"
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
        help="Exporta resultados a archivo (csv, json o txt) en carpeta outcome/"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Ejecuta consultas en paralelo (default: activado)"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Desactiva ejecución paralela"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Número máximo de workers para ejecución paralela (default: 4)"
    )
    parser.add_argument(
        "--timezone", "-tz",
        type=str,
        default="America/Mazatlan",
        help="Zona horaria para mostrar fechas (default: America/Mazatlan)"
    )
    return parser.parse_args()


def show_help(console):
    """Muestra ayuda del script."""
    help_text = """
# GCP Cloud SQL Database Checker

## Descripción
Herramienta SRE para listar y analizar bases de datos en instancias Cloud SQL.

## Uso
```bash
python gcp_database_checker.py --project <PROJECT_ID> [opciones]
```

## Opciones
- `--project`: ID del proyecto GCP
- `--output, -o`: Formato de exportación (csv, json, txt)
- `--debug`: Modo debug
- `--parallel/--no-parallel`: Control de ejecución paralela
- `--max-workers`: Número de workers paralelos
- `--timezone, -tz`: Zona horaria para fechas

## Ejemplos
```bash
# Listar bases de datos del proyecto default
python gcp_database_checker.py

# Exportar a JSON
python gcp_database_checker.py --project mi-proyecto -o json

# Modo debug
python gcp_database_checker.py --debug
```
"""
    if RICH_AVAILABLE:
        console.print(Markdown(help_text))
    else:
        print(help_text)


def check_gcp_connection(project_id: str, console, debug: bool = False) -> bool:
    """Valida conexión a GCP antes de ejecutar el script."""
    try:
        auth_cmd = 'gcloud auth list --filter=status:ACTIVE --format="value(account)"'
        auth_result = subprocess.run(auth_cmd, shell=True, capture_output=True, text=True)
        
        if debug:
            print(f"[DEBUG] Auth command: {auth_cmd}")
            print(f"[DEBUG] Auth result: {auth_result.stdout.strip()}")
        
        if auth_result.returncode != 0 or not auth_result.stdout.strip():
            if RICH_AVAILABLE:
                console.print("[red]❌ No hay sesión activa de gcloud. Ejecuta: gcloud auth login[/]")
            else:
                print("❌ No hay sesión activa de gcloud. Ejecuta: gcloud auth login")
            return False
        
        active_account = auth_result.stdout.strip().split('\n')[0]
        if RICH_AVAILABLE:
            console.print(f"[dim]🔐 Cuenta activa: {active_account}[/]")
        else:
            print(f"🔐 Cuenta activa: {active_account}")
        
        project_cmd = f'gcloud projects describe {project_id} --format="value(projectId)" 2>&1'
        project_result = subprocess.run(project_cmd, shell=True, capture_output=True, text=True)
        
        if debug:
            print(f"[DEBUG] Project command: {project_cmd}")
            print(f"[DEBUG] Project result: {project_result.stdout.strip()}")
        
        if project_result.returncode != 0:
            error_msg = project_result.stderr or project_result.stdout
            if RICH_AVAILABLE:
                if "not found" in error_msg.lower() or "permission" in error_msg.lower():
                    console.print(f"[red]❌ No tienes acceso al proyecto: {project_id}[/]")
                else:
                    console.print(f"[red]❌ Error de conexión: {error_msg.strip()}[/]")
            else:
                print(f"❌ Error de conexión: {error_msg.strip()}")
            return False
        
        if RICH_AVAILABLE:
            console.print(f"[dim]✅ Conexión verificada al proyecto: {project_id}[/]")
        else:
            print(f"✅ Conexión verificada al proyecto: {project_id}")
        return True
        
    except Exception as e:
        if debug:
            print(f"[DEBUG] Connection check exception: {e}")
        if RICH_AVAILABLE:
            console.print(f"[red]❌ Error verificando conexión: {e}[/]")
        else:
            print(f"❌ Error verificando conexión: {e}")
        return False


def run_gcloud_command(command: str, debug: bool = False) -> Optional[Any]:
    """Ejecuta un comando gcloud y retorna el resultado como JSON."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if debug:
            print(f"[DEBUG] Command: {command}")
            print(f"[DEBUG] Return code: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] Stderr: {result.stderr[:200]}")
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except json.JSONDecodeError:
        return result.stdout.strip() if result.stdout else None
    except Exception as e:
        if debug:
            print(f"[DEBUG] Exception: {e}")
        return None


def get_sql_instances(project_id: str, debug: bool = False) -> List[Dict]:
    """Obtiene lista de instancias Cloud SQL usando gcloud."""
    cmd = f'gcloud sql instances list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug)
    return result if isinstance(result, list) else []


def get_databases_for_instance(instance_name: str, project_id: str, debug: bool = False) -> List[Dict]:
    """Obtiene las bases de datos de una instancia Cloud SQL."""
    cmd = f'gcloud sql databases list --instance={instance_name} --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug)
    return result if isinstance(result, list) else []


def get_instance_status_style(state: str) -> tuple:
    """Retorna el estilo y emoji según el estado de la instancia."""
    status_map = {
        "RUNNABLE": ("green", "🟢", "RUNNING"),
        "RUNNING": ("green", "🟢", "RUNNING"),
        "STOPPED": ("red", "🔴", "STOPPED"),
        "SUSPENDED": ("yellow", "🟡", "SUSPENDED"),
        "PENDING_CREATE": ("cyan", "🔵", "CREATING"),
        "MAINTENANCE": ("yellow", "🟡", "MAINTENANCE"),
        "FAILED": ("red", "❌", "FAILED"),
    }
    return status_map.get(state.upper(), ("white", "⚪", state))


def get_db_engine_info(db_version: str) -> tuple:
    """Extrae información del motor de base de datos."""
    if not db_version:
        return ("UNKNOWN", "UNKNOWN", "white")
    
    version_upper = db_version.upper()
    if "MYSQL" in version_upper:
        version = db_version.replace("MYSQL_", "").replace("_", ".")
        return ("MySQL", version, "cyan")
    elif "POSTGRES" in version_upper:
        version = db_version.replace("POSTGRES_", "").replace("_", ".")
        return ("PostgreSQL", version, "blue")
    elif "SQLSERVER" in version_upper:
        version = db_version.replace("SQLSERVER_", "").replace("_", " ")
        return ("SQL Server", version, "yellow")
    else:
        return (db_version, "", "white")


def process_instance(instance: Dict, project_id: str, revision_time: str, debug: bool = False) -> Dict:
    """Procesa una instancia de Cloud SQL y retorna sus datos con bases de datos."""
    instance_name = instance.get('name', 'UNKNOWN')
    state = instance.get('state', 'UNKNOWN')
    db_version = instance.get('databaseVersion', 'UNKNOWN')
    settings = instance.get('settings', {})
    
    # Obtener bases de datos de la instancia
    databases = []
    if state.upper() in ['RUNNABLE', 'RUNNING']:
        databases = get_databases_for_instance(instance_name, project_id, debug)
    
    # Información del motor
    engine, version, _ = get_db_engine_info(db_version)
    
    # Información de almacenamiento
    disk_size = settings.get('dataDiskSizeGb', 0)
    disk_type = settings.get('dataDiskType', 'UNKNOWN')
    auto_resize = settings.get('storageAutoResize', False)
    
    # Información de backup
    backup_config = settings.get('backupConfiguration', {})
    backup_enabled = backup_config.get('enabled', False)
    
    # Información de réplica
    replica_type = instance.get('instanceType', 'PRIMARY')
    master_instance = instance.get('masterInstanceName', None)
    
    # Región y zona
    region = instance.get('region', 'UNKNOWN')
    gce_zone = instance.get('gceZone', 'UNKNOWN')
    
    # IPs
    ip_addresses = instance.get('ipAddresses', [])
    primary_ip = next((ip.get('ipAddress') for ip in ip_addresses if ip.get('type') == 'PRIMARY'), 'N/A')
    private_ip = next((ip.get('ipAddress') for ip in ip_addresses if ip.get('type') == 'PRIVATE'), 'N/A')
    
    # Lista de nombres de bases de datos
    db_names = [db.get('name', 'UNKNOWN') for db in databases]
    
    return {
        'project': project_id,
        'instance': instance_name,
        'state': state,
        'engine': engine,
        'version': version,
        'region': region,
        'zone': gce_zone,
        'disk_size_gb': int(disk_size) if disk_size else 0,
        'disk_type': disk_type,
        'auto_resize': auto_resize,
        'backup_enabled': backup_enabled,
        'instance_type': replica_type,
        'master_instance': master_instance,
        'primary_ip': primary_ip,
        'private_ip': private_ip,
        'database_count': len(databases),
        'databases': db_names,
        'revision_time': revision_time
    }


def create_instances_table(results: List[Dict], console) -> Table:
    """Crea la tabla de instancias Cloud SQL."""
    table = Table(
        title="📊 Cloud SQL Instances",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim",
        box=box.ROUNDED
    )
    
    table.add_column("#", justify="center", style="dim", width=3)
    table.add_column("Instancia", style="white")
    table.add_column("Estado", justify="center")
    table.add_column("Motor", justify="center")
    table.add_column("Versión", justify="center")
    table.add_column("Región", justify="center")
    table.add_column("Disco", justify="right")
    table.add_column("Auto-Resize", justify="center")
    table.add_column("Backup", justify="center")
    table.add_column("DBs", justify="center")
    
    for idx, r in enumerate(results, 1):
        color, emoji, status_text = get_instance_status_style(r['state'])
        _, _, engine_color = get_db_engine_info(f"{r['engine']}_{r['version']}")
        
        table.add_row(
            str(idx),
            r['instance'],
            f"[{color}]{emoji} {status_text}[/{color}]",
            f"[{engine_color}]{r['engine']}[/{engine_color}]",
            r['version'],
            r['region'],
            f"{r['disk_size_gb']} GB",
            "[green]✓[/]" if r['auto_resize'] else "[red]✗[/]",
            "[green]✓[/]" if r['backup_enabled'] else "[red]✗[/]",
            f"[cyan]{r['database_count']}[/]"
        )
    
    return table


def create_databases_table(results: List[Dict], console) -> Table:
    """Crea la tabla detallada de bases de datos por instancia."""
    table = Table(
        title="🗄️  Bases de Datos por Instancia",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim",
        box=box.ROUNDED
    )
    
    table.add_column("Instancia", style="white")
    table.add_column("Motor", justify="center")
    table.add_column("Bases de Datos", style="cyan")
    
    for r in results:
        if r['database_count'] > 0:
            _, _, engine_color = get_db_engine_info(f"{r['engine']}_{r['version']}")
            db_list = ", ".join(r['databases'][:10])  # Limitar a 10 DBs
            if len(r['databases']) > 10:
                db_list += f" ... (+{len(r['databases']) - 10} más)"
            
            table.add_row(
                r['instance'],
                f"[{engine_color}]{r['engine']} {r['version']}[/{engine_color}]",
                db_list
            )
    
    return table


def print_summary(console, results: List[Dict]):
    """Imprime resumen ejecutivo con conteo de estados."""
    running = sum(1 for r in results if r['state'].upper() in ['RUNNABLE', 'RUNNING'])
    stopped = sum(1 for r in results if r['state'].upper() == 'STOPPED')
    other = len(results) - running - stopped
    total_dbs = sum(r['database_count'] for r in results)
    
    # Contar por motor
    engines = {}
    for r in results:
        engine = r['engine']
        engines[engine] = engines.get(engine, 0) + 1
    
    engine_summary = "  ".join([f"[cyan]{k}: {v}[/]" for k, v in engines.items()])
    
    summary_text = (
        f"[bold green]🟢 Running: {running}[/]  "
        f"[bold red]🔴 Stopped: {stopped}[/]  "
        f"[bold yellow]🟡 Other: {other}[/]  "
        f"[dim]| Total Instancias: {len(results)} | Total DBs: {total_dbs}[/]\n"
        f"[dim]Motores: {engine_summary}[/]"
    )
    
    if RICH_AVAILABLE:
        console.print(Panel(summary_text, title="📊 Resumen Ejecutivo", border_style="blue", expand=False))
    else:
        print(f"\n=== Resumen Ejecutivo ===")
        print(f"Running: {running} | Stopped: {stopped} | Other: {other}")
        print(f"Total Instancias: {len(results)} | Total DBs: {total_dbs}")


def export_to_csv(data: List[Dict], filepath: str):
    """Exporta los datos a un archivo CSV."""
    if not data:
        return
    
    # Aplanar los datos para CSV
    flat_data = []
    for r in data:
        flat_record = r.copy()
        flat_record['databases'] = "; ".join(r['databases'])
        flat_record['auto_resize'] = 'ENABLED' if r['auto_resize'] else 'DISABLED'
        flat_record['backup_enabled'] = 'ENABLED' if r['backup_enabled'] else 'DISABLED'
        flat_data.append(flat_record)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=flat_data[0].keys())
        writer.writeheader()
        writer.writerows(flat_data)


def export_to_json(data: List[Dict], filepath: str, project_id: str, tz_name: str = "America/Mazatlan"):
    """Exporta los datos a un archivo JSON con metadatos completos."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    
    # Contar estadísticas
    running = sum(1 for r in data if r['state'].upper() in ['RUNNABLE', 'RUNNING'])
    stopped = sum(1 for r in data if r['state'].upper() == 'STOPPED')
    total_dbs = sum(r['database_count'] for r in data)
    
    export_data = {
        "report_metadata": {
            "tool_name": "GCP Cloud SQL Database Checker",
            "version": __version__,
            "author": __author__,
            "project_id": project_id,
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "total_instances": len(data),
            "running": running,
            "stopped": stopped,
            "other": len(data) - running - stopped,
            "total_databases": total_dbs
        },
        "instances": data
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)


def export_to_txt(data: List[Dict], filepath: str, project_id: str, tz_name: str = "America/Mazatlan"):
    """Exporta los datos a un archivo TXT."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    
    lines = []
    lines.append("=" * 80)
    lines.append("GCP Cloud SQL Database Checker Report")
    lines.append("=" * 80)
    lines.append(f"Project: {project_id}")
    lines.append(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} ({tz_name})")
    lines.append(f"Total Instances: {len(data)}")
    lines.append(f"Total Databases: {sum(r['database_count'] for r in data)}")
    lines.append("=" * 80)
    lines.append("")
    
    for r in data:
        lines.append(f"Instance: {r['instance']}")
        lines.append(f"  State: {r['state']}")
        lines.append(f"  Engine: {r['engine']} {r['version']}")
        lines.append(f"  Region: {r['region']}")
        lines.append(f"  Disk: {r['disk_size_gb']} GB (Auto-resize: {'Yes' if r['auto_resize'] else 'No'})")
        lines.append(f"  Backup: {'Enabled' if r['backup_enabled'] else 'Disabled'}")
        lines.append(f"  Primary IP: {r['primary_ip']}")
        lines.append(f"  Private IP: {r['private_ip']}")
        lines.append(f"  Databases ({r['database_count']}):")
        for db in r['databases']:
            lines.append(f"    - {db}")
        lines.append("")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))


def print_execution_time(start_time: float, console, tz_name: str = "America/Mazatlan"):
    """Imprime el tiempo de ejecución del script."""
    end_time = time.time()
    duration = end_time - start_time
    
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = duration % 60
    
    tz = ZoneInfo(tz_name)
    start_dt = datetime.fromtimestamp(start_time, tz=tz)
    end_dt = datetime.fromtimestamp(end_time, tz=tz)
    
    time_parts = []
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    time_parts.append(f"{seconds:.2f}s")
    duration_str = " ".join(time_parts)
    
    if RICH_AVAILABLE:
        time_table = Table(title="⏱️  Tiempo de Ejecución", title_style="bold cyan", border_style="dim")
        time_table.add_column("Métrica", style="white")
        time_table.add_column("Valor", style="green")
        time_table.add_row("🚀 Inicio", start_dt.strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})'))
        time_table.add_row("🏁 Fin", end_dt.strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})'))
        time_table.add_row("⏳ Duración", duration_str)
        console.print("\n")
        console.print(time_table)
    else:
        print(f"\n⏱️ Tiempo de Ejecución: {duration_str}")


def main():
    """Función principal del script."""
    start_time = time.time()
    args = get_args()
    
    console = Console() if RICH_AVAILABLE else None
    
    if args.help:
        show_help(console)
        return 0
    
    project_id = args.project
    use_parallel = args.parallel and not args.no_parallel
    max_workers = args.max_workers
    tz_name = args.timezone
    
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        if RICH_AVAILABLE:
            console.print(f"[red]⚠️ Zona horaria inválida: {tz_name}. Usando America/Mazatlan[/]")
        else:
            print(f"⚠️ Zona horaria inválida: {tz_name}. Usando America/Mazatlan")
        tz_name = "America/Mazatlan"
        tz = ZoneInfo(tz_name)
    
    revision_time = datetime.now(tz).strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})')
    
    if RICH_AVAILABLE:
        console.print(f"\n[bold blue]📡 Iniciando escaneo de Cloud SQL en:[/] [white underline]{project_id}[/]")
        console.print(f"[dim]🕐 Fecha y hora de revisión: {revision_time}[/]")
        console.print(f"[dim]⚡ Modo: {'Paralelo (' + str(max_workers) + ' workers)' if use_parallel else 'Secuencial'}[/]")
    else:
        print(f"\n📡 Iniciando escaneo de Cloud SQL en: {project_id}")
        print(f"🕐 Fecha y hora de revisión: {revision_time}")
    
    if not check_gcp_connection(project_id, console, args.debug):
        print_execution_time(start_time, console, tz_name)
        return 1
    
    if RICH_AVAILABLE:
        console.print()
    
    try:
        # Obtener instancias
        if RICH_AVAILABLE:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                task = progress.add_task("Recolectando instancias Cloud SQL...", total=None)
                instances = get_sql_instances(project_id, args.debug)
        else:
            print("Recolectando instancias Cloud SQL...")
            instances = get_sql_instances(project_id, args.debug)
        
        if not instances:
            if RICH_AVAILABLE:
                console.print(f"[yellow]⚠️ No se detectaron instancias de Cloud SQL en {project_id}.[/]")
            else:
                print(f"⚠️ No se detectaron instancias de Cloud SQL en {project_id}.")
            print_execution_time(start_time, console, tz_name)
            return 0
        
        instances = sorted(instances, key=lambda x: x.get('name', ''))
        total_instances = len(instances)
        results = []
        
        # Procesar instancias
        if use_parallel and total_instances > 1:
            if RICH_AVAILABLE:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task(f"Procesando {total_instances} instancias...", total=total_instances)
                    
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {
                            executor.submit(process_instance, instance, project_id, revision_time, args.debug): instance
                            for instance in instances
                        }
                        
                        for future in as_completed(futures):
                            try:
                                result = future.result()
                                results.append(result)
                            except Exception as e:
                                if args.debug:
                                    console.print(f"[red]Error procesando instancia: {e}[/]")
                            progress.advance(task)
            else:
                print(f"Procesando {total_instances} instancias...")
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(process_instance, instance, project_id, revision_time, args.debug): instance
                        for instance in instances
                    }
                    for future in as_completed(futures):
                        try:
                            results.append(future.result())
                        except Exception as e:
                            if args.debug:
                                print(f"Error procesando instancia: {e}")
        else:
            for idx, instance in enumerate(instances, 1):
                if RICH_AVAILABLE:
                    console.print(f"[dim]Procesando [{idx}/{total_instances}]: {instance.get('name', 'UNKNOWN')}...[/]")
                else:
                    print(f"Procesando [{idx}/{total_instances}]: {instance.get('name', 'UNKNOWN')}...")
                result = process_instance(instance, project_id, revision_time, args.debug)
                results.append(result)
        
        results = sorted(results, key=lambda x: x.get('instance', ''))
        
        # Mostrar tablas
        if RICH_AVAILABLE:
            console.print()
            console.print(create_instances_table(results, console))
            console.print()
            console.print(create_databases_table(results, console))
            console.print()
        
        # Mostrar resumen
        print_summary(console, results)
        
        # Exportar si se solicita
        if args.output and results:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            outcome_dir = os.path.join(script_dir, 'outcome')
            os.makedirs(outcome_dir, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"db_report_{project_id}_{timestamp}"
            
            if args.output == 'csv':
                filepath = os.path.join(outcome_dir, f"{filename}.csv")
                export_to_csv(results, filepath)
            elif args.output == 'json':
                filepath = os.path.join(outcome_dir, f"{filename}.json")
                export_to_json(results, filepath, project_id, tz_name)
            else:  # txt
                filepath = os.path.join(outcome_dir, f"{filename}.txt")
                export_to_txt(results, filepath, project_id, tz_name)
            
            if RICH_AVAILABLE:
                console.print(f"\n[bold green]📁 Archivo exportado:[/] {filepath}")
            else:
                print(f"\n📁 Archivo exportado: {filepath}")
        
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[bold red]❌ Error ejecutando el análisis:[/]\n{e}")
        else:
            print(f"❌ Error ejecutando el análisis: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    print_execution_time(start_time, console, tz_name)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
