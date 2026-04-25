import argparse
import subprocess
import json
import csv
import urllib.parse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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

__version__ = "2.3.1"

_token_cache = None

def get_args():
    parser = argparse.ArgumentParser(description="SRE Tool: Cloud SQL Database Disk Monitoring (gcloud)", add_help=False)
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
        choices=["csv", "json"],
        help="Exporta resultados a archivo (csv o json) en carpeta outcome/"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Ejecuta consultas de métricas en paralelo (default: activado)"
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
        help="Zona horaria para mostrar fechas (default: America/Mazatlan - Culiacán)"
    )
    return parser.parse_args()

def show_help():
    """Muestra el README.md con formato enriquecido en consola"""
    console = Console()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(script_dir, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
        console.print(Markdown(readme_content))
    else:
        console.print("[yellow]README.md no encontrado[/]")

def check_gcp_connection(project_id, console, debug=False):
    """Valida conexión a GCP antes de ejecutar el script"""
    try:
        auth_cmd = 'gcloud auth list --filter=status:ACTIVE --format="value(account)"'
        auth_result = subprocess.run(auth_cmd, shell=True, capture_output=True, text=True)
        
        if debug:
            print(f"[DEBUG] Auth command: {auth_cmd}")
            print(f"[DEBUG] Auth result: {auth_result.stdout.strip()}")
        
        if auth_result.returncode != 0 or not auth_result.stdout.strip():
            console.print("[red]❌ No hay sesión activa de gcloud. Ejecuta: gcloud auth login[/]")
            return False
        
        active_account = auth_result.stdout.strip().split('\n')[0]
        console.print(f"[dim]🔐 Cuenta activa: {active_account}[/]")
        
        project_cmd = f'gcloud projects describe {project_id} --format="value(projectId)" 2>&1'
        project_result = subprocess.run(project_cmd, shell=True, capture_output=True, text=True)
        
        if debug:
            print(f"[DEBUG] Project command: {project_cmd}")
            print(f"[DEBUG] Project result: {project_result.stdout.strip()}")
            if project_result.stderr:
                print(f"[DEBUG] Project stderr: {project_result.stderr}")
        
        if project_result.returncode != 0:
            error_msg = project_result.stderr or project_result.stdout
            if "not found" in error_msg.lower() or "permission" in error_msg.lower():
                console.print(f"[red]❌ No tienes acceso al proyecto: {project_id}[/]")
            else:
                console.print(f"[red]❌ Error de conexión: {error_msg.strip()}[/]")
            return False
        
        console.print(f"[dim]✅ Conexión verificada al proyecto: {project_id}[/]")
        return True
        
    except Exception as e:
        if debug:
            print(f"[DEBUG] Connection check exception: {e}")
        console.print(f"[red]❌ Error verificando conexión: {e}[/]")
        return False

def run_gcloud_command(command, debug=False):
    """Ejecuta un comando gcloud y retorna el resultado como JSON"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        if debug:
            print(f"[DEBUG] Command: {command}")
            print(f"[DEBUG] Return code: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] Stderr: {result.stderr}")
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except (json.JSONDecodeError, Exception) as e:
        if debug:
            print(f"[DEBUG] Exception: {e}")
        return None

def get_access_token():
    """Obtiene el token de acceso de gcloud con caché para evitar múltiples llamadas"""
    global _token_cache
    if _token_cache is not None:
        return _token_cache
    try:
        result = subprocess.run(
            'gcloud auth print-access-token',
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            _token_cache = result.stdout.strip()
            return _token_cache
    except Exception:
        pass
    return None

def get_sql_instances(project_id, debug=False):
    """Obtiene lista de instancias Cloud SQL usando gcloud"""
    cmd = f'gcloud sql instances list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug) or []

def get_disk_utilization(project_id, instance_id, debug=False):
    """Consulta Cloud Monitoring API para obtener el uso real del disco de la DB"""
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = now.strftime('%Y-%m-%dT%H:%M:%SZ')

    filter_str = (
        f'metric.type="cloudsql.googleapis.com/database/disk/utilization" '
        f'AND resource.labels.database_id="{project_id}:{instance_id}"'
    )
    encoded_filter = urllib.parse.quote(filter_str)

    token = get_access_token()
    if not token:
        if debug:
            print("[DEBUG] No se pudo obtener access token")
        return 0.0

    url = (
        f'https://monitoring.googleapis.com/v3/projects/{project_id}/timeSeries'
        f'?filter={encoded_filter}'
        f'&interval.startTime={start_time}'
        f'&interval.endTime={end_time}'
    )

    cmd = f'curl -s -H "Authorization: Bearer {token}" "{url}"'

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if debug:
            print(f"[DEBUG] Curl URL: {url[:100]}...")
            print(f"[DEBUG] Return code: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] Stderr: {result.stderr[:200]}")

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            time_series = data.get('timeSeries', [])
            if time_series and len(time_series) > 0:
                points = time_series[0].get('points', [])
                if points:
                    value = points[0].get('value', {}).get('doubleValue', 0.0)
                    return float(value) * 100
    except Exception as e:
        if debug:
            print(f"[DEBUG] Exception: {e}")
        return 0.0
    return 0.0

def get_status_summary(utilization, auto_resize):
    """Lógica de Semáforo SRE para Bases de Datos"""
    if utilization >= 90:
        return "[bold white on red] CRITICAL [/]"
    elif utilization >= 75:
        return "[bold black on yellow] WARNING [/]"
    elif not auto_resize:
        return "[bold cyan] MANUAL OK [/]"
    return "[bold green] HEALTHY [/]"

def get_status_text(utilization, auto_resize):
    """Retorna el estado en texto plano para exportación"""
    if utilization >= 90:
        return "CRITICAL"
    elif utilization >= 75:
        return "WARNING"
    elif not auto_resize:
        return "MANUAL_OK"
    return "HEALTHY"

def export_to_csv(data, filepath):
    """Exporta los datos a un archivo CSV"""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def export_to_json(data, filepath, project_id=None, tz_name="America/Mazatlan"):
    """Exporta los datos a un archivo JSON con metadatos completos"""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    
    export_data = {
        "report_metadata": {
            "tool_name": "GCP Cloud SQL Disk Checker",
            "version": __version__,
            "project_id": project_id,
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "total_instances": len(data),
            "critical": sum(1 for r in data if r.get('status') == 'CRITICAL'),
            "warning": sum(1 for r in data if r.get('status') == 'WARNING'),
            "manual_ok": sum(1 for r in data if r.get('status') == 'MANUAL_OK'),
            "healthy": sum(1 for r in data if r.get('status') == 'HEALTHY')
        },
        "instances": data
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

def print_summary(console, results):
    """Imprime resumen ejecutivo con conteo de estados"""
    critical = sum(1 for r in results if r['status'] == 'CRITICAL')
    warning = sum(1 for r in results if r['status'] == 'WARNING')
    manual_ok = sum(1 for r in results if r['status'] == 'MANUAL_OK')
    healthy = sum(1 for r in results if r['status'] == 'HEALTHY')
    total = len(results)

    summary_text = (
        f"[bold red]🚨 CRITICAL: {critical}[/]  "
        f"[bold yellow]⚠️  WARNING: {warning}[/]  "
        f"[bold cyan]ℹ️  MANUAL OK: {manual_ok}[/]  "
        f"[bold green]✅ HEALTHY: {healthy}[/]  "
        f"[dim]| Total: {total}[/]"
    )
    
    console.print(Panel(summary_text, title="📊 Resumen Ejecutivo", border_style="blue", expand=False))

def process_instance(instance, project_id, revision_time, debug=False):
    """Procesa una instancia de Cloud SQL y retorna sus datos"""
    instance_name = instance.get('name', 'UNKNOWN')
    util = get_disk_utilization(project_id, instance_name, debug)
    settings = instance.get('settings', {})
    resize_enabled = settings.get('storageAutoResize', False)
    db_engine = instance.get('databaseVersion', 'UNKNOWN').split('_')[0]
    disk_size = settings.get('dataDiskSizeGb', 0)
    disk_size_int = int(disk_size) if disk_size else 0
    used_gb = round((util / 100) * disk_size_int, 2)
    status = get_status_text(util, resize_enabled)

    return {
        'project': project_id,
        'instance': instance_name,
        'engine': db_engine,
        'capacity_gb': disk_size_int,
        'used_gb': used_gb,
        'utilization_pct': round(util, 2),
        'auto_resize': resize_enabled,
        'status': status,
        'revision_time': revision_time
    }

def print_execution_time(start_time, console, tz_name="America/Mazatlan"):
    """Imprime el tiempo de ejecución del script"""
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

    time_table = Table(title="⏱️  Tiempo de Ejecución", title_style="bold cyan", border_style="dim")
    time_table.add_column("Métrica", style="white")
    time_table.add_column("Valor", style="green")
    time_table.add_row("🚀 Inicio", start_dt.strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})'))
    time_table.add_row("🏁 Fin", end_dt.strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})'))
    time_table.add_row("⏳ Duración", duration_str)

    console.print(f"\n")
    console.print(time_table)

def main():
    start_time = time.time()
    args = get_args()

    if args.help:
        show_help()
        return

    project_id = args.project
    console = Console()
    use_parallel = args.parallel and not args.no_parallel
    max_workers = args.max_workers
    tz_name = args.timezone

    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        console.print(f"[red]⚠️ Zona horaria inválida: {tz_name}. Usando America/Mazatlan[/]")
        tz_name = "America/Mazatlan"
        tz = ZoneInfo(tz_name)

    revision_time = datetime.now(tz).strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})')
    console.print(f"\n[bold blue]📡 Iniciando escaneo de Base de Datos en:[/] [white underline]{project_id}[/]")
    console.print(f"[dim]🕐 Fecha y hora de revisión: {revision_time}[/]")
    console.print(f"[dim]⚡ Modo: {'Paralelo (' + str(max_workers) + ' workers)' if use_parallel else 'Secuencial'}[/]")

    if not check_gcp_connection(project_id, console, args.debug):
        print_execution_time(start_time, console, tz_name)
        return

    console.print()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Recolectando instancias Cloud SQL...", total=None)
            instances = get_sql_instances(project_id, args.debug)

        table = Table(
            title=f"📊 Database Storage Health: {project_id}",
            title_style="bold magenta",
            header_style="bold cyan",
            border_style="dim"
        )

        table.add_column("Instancia DB", style="white")
        table.add_column("Motor", justify="center")
        table.add_column("Capacidad", justify="right")
        table.add_column("Uso (GB)", justify="right")
        table.add_column("Uso (%)", justify="right")
        table.add_column("Auto-Resize", justify="center")
        table.add_column("Semaforo SRE", justify="left")

        results = []

        if not instances:
            console.print(f"[yellow]⚠️ No se detectaron instancias de Cloud SQL en {project_id}.[/]")
        else:
            instances = sorted(instances, key=lambda x: x.get('name', ''))
            total_instances = len(instances)
            
            if use_parallel and total_instances > 1:
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

                results = sorted(results, key=lambda x: x.get('instance', ''))
            else:
                for idx, instance in enumerate(instances, 1):
                    console.print(f"[dim]Procesando [{idx}/{total_instances}]: {instance.get('name', 'UNKNOWN')}...[/]")
                    result = process_instance(instance, project_id, revision_time, args.debug)
                    results.append(result)

            for r in results:
                util = r['utilization_pct']
                resize_enabled = r['auto_resize']
                
                row_style = ""
                if util > 90: row_style = "red"
                elif util > 75: row_style = "yellow"

                table.add_row(
                    r['instance'],
                    r['engine'],
                    f"{r['capacity_gb']} GB",
                    f"{r['used_gb']} GB",
                    f"{util:.2f}%",
                    "[green]ENABLED[/]" if resize_enabled else "[red]DISABLED[/]",
                    get_status_summary(util, resize_enabled),
                    style=row_style
                )

            console.print(table)

            export_results = []
            for r in results:
                export_res = r.copy()
                export_res['auto_resize'] = 'ENABLED' if r['auto_resize'] else 'DISABLED'
                export_results.append(export_res)

            print_summary(console, export_results)

            if args.output and export_results:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                outcome_dir = os.path.join(script_dir, 'outcome')
                os.makedirs(outcome_dir, exist_ok=True)
                
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                filename = f"disk_check_{project_id}_{timestamp}"
                
                if args.output == 'csv':
                    filepath = os.path.join(outcome_dir, f"{filename}.csv")
                    export_to_csv(export_results, filepath)
                elif args.output == 'json':
                    filepath = os.path.join(outcome_dir, f"{filename}.json")
                    export_to_json(export_results, filepath, project_id, tz_name)

                console.print(f"\n[bold green]📁 Archivo exportado:[/] {filepath}")

            console.print(f"\n[dim]Tip: Las alertas se disparan basándose en la métrica de 'utilization' de Cloud Monitoring.[/]\n")

    except Exception as e:
        console.print(f"[bold red]❌ Error ejecutando gcloud:[/]\n{e}")

    print_execution_time(start_time, console, tz_name)

if __name__ == "__main__":
    main()