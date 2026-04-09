import argparse
import subprocess
import json
import csv
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import os

__version__ = "1.2.0"

_token_cache = None

def get_args():
    parser = argparse.ArgumentParser(description="SRE Tool: GCP Certificate Manager Monitoring (gcloud)", add_help=False)
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

def get_certificates(project_id, debug=False):
    """Obtiene lista de certificados de Certificate Manager usando gcloud"""
    cmd = f'gcloud certificate-manager certificates list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug) or []

def get_certificate_maps(project_id, debug=False):
    """Obtiene lista de certificate maps usando gcloud"""
    cmd = f'gcloud certificate-manager maps list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug) or []

def get_dns_authorizations(project_id, debug=False):
    """Obtiene lista de DNS authorizations usando gcloud"""
    cmd = f'gcloud certificate-manager dns-authorizations list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug) or []

def parse_certificate_name(full_name):
    """Extrae el nombre corto del certificado desde el path completo"""
    if full_name and '/' in full_name:
        return full_name.split('/')[-1]
    return full_name or 'UNKNOWN'

def calculate_days_to_expiry(expire_time_str):
    """Calcula los días restantes hasta la expiración"""
    if not expire_time_str:
        return None
    try:
        expire_time = datetime.fromisoformat(expire_time_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = expire_time - now
        return delta.days
    except Exception:
        return None

def get_status_summary(days_to_expiry, state):
    """Lógica de Semáforo SRE para Certificados"""
    if state != 'ACTIVE':
        return "[bold white on red] INACTIVE [/]"
    if days_to_expiry is None:
        return "[dim] N/A [/]"
    if days_to_expiry <= 7:
        return "[bold white on red] CRITICAL [/]"
    elif days_to_expiry <= 30:
        return "[bold black on yellow] WARNING [/]"
    elif days_to_expiry <= 60:
        return "[bold cyan] ATTENTION [/]"
    return "[bold green] HEALTHY [/]"

def get_status_text(days_to_expiry, state):
    """Retorna el estado en texto plano para exportación"""
    if state != 'ACTIVE':
        return "INACTIVE"
    if days_to_expiry is None:
        return "N/A"
    if days_to_expiry <= 7:
        return "CRITICAL"
    elif days_to_expiry <= 30:
        return "WARNING"
    elif days_to_expiry <= 60:
        return "ATTENTION"
    return "HEALTHY"

def export_to_csv(data, filepath):
    """Exporta los datos a un archivo CSV"""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def export_to_json(data, filepath, project_id, tz_name="America/Mazatlan"):
    """Exporta los datos a un archivo JSON con metadatos completos"""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    
    export_data = {
        "report_metadata": {
            "tool_name": "GCP Certificate Manager Checker",
            "version": __version__,
            "project_id": project_id,
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "total_certificates": len(data),
            "critical": sum(1 for r in data if r.get('status') == 'CRITICAL'),
            "warning": sum(1 for r in data if r.get('status') == 'WARNING'),
            "attention": sum(1 for r in data if r.get('status') == 'ATTENTION'),
            "healthy": sum(1 for r in data if r.get('status') == 'HEALTHY'),
            "inactive": sum(1 for r in data if r.get('status') == 'INACTIVE')
        },
        "certificates": data
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

def print_summary(console, results):
    """Imprime resumen ejecutivo con conteo de estados"""
    critical = sum(1 for r in results if r['status'] == 'CRITICAL')
    warning = sum(1 for r in results if r['status'] == 'WARNING')
    attention = sum(1 for r in results if r['status'] == 'ATTENTION')
    healthy = sum(1 for r in results if r['status'] == 'HEALTHY')
    inactive = sum(1 for r in results if r['status'] == 'INACTIVE')
    total = len(results)
    
    summary_text = (
        f"[bold red]🚨 CRITICAL: {critical}[/]  "
        f"[bold yellow]⚠️  WARNING: {warning}[/]  "
        f"[bold cyan]👁️  ATTENTION: {attention}[/]  "
        f"[bold green]✅ HEALTHY: {healthy}[/]  "
        f"[dim]⏸️  INACTIVE: {inactive}[/]  "
        f"[dim]| Total: {total}[/]"
    )
    
    console.print(Panel(summary_text, title="📊 Resumen Ejecutivo", border_style="blue", expand=False))

def print_execution_time(start_time, console, tz_name="America/Mazatlan"):
    """Imprime el tiempo de ejecución del script"""
    end_time = time.time()
    duration = end_time - start_time

    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = duration % 60

    if hours > 0:
        duration_str = f"{hours}h {minutes}m {seconds:.2f}s"
    elif minutes > 0:
        duration_str = f"{minutes}m {seconds:.2f}s"
    else:
        duration_str = f"{seconds:.2f}s"

    tz = ZoneInfo(tz_name)
    start_ts = datetime.fromtimestamp(start_time, tz=tz).strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})')
    end_ts = datetime.fromtimestamp(end_time, tz=tz).strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})')

    time_panel = Panel(
        f"[bold cyan]🚀 Inicio:[/] {start_ts}\n"
        f"[bold cyan]🏁 Fin:[/]    {end_ts}\n"
        f"[bold green]⏱️  Duración:[/] {duration_str}",
        title="⏱️  Tiempo de Ejecución",
        border_style="blue",
        expand=False
    )
    console.print(time_panel)

def main():
    start_time = time.time()
    args = get_args()
    
    if args.help:
        show_help()
        return
    
    project_id = args.project
    console = Console()
    tz_name = args.timezone

    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        console.print(f"[red]⚠️ Zona horaria inválida: {tz_name}. Usando America/Mazatlan[/]")
        tz_name = "America/Mazatlan"
        tz = ZoneInfo(tz_name)

    revision_time = datetime.now(tz).strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})')
    console.print(f"\n[bold blue]🔐 Iniciando escaneo de Certificate Manager en:[/] [white underline]{project_id}[/]")
    console.print(f"[dim]🕐 Fecha y hora de revisión: {revision_time}[/]")

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
            task = progress.add_task("Recolectando certificados...", total=None)
            certificates = get_certificates(project_id, args.debug)
        
        table = Table(
            title=f"🔒 Certificate Manager: {project_id}",
            title_style="bold magenta",
            header_style="bold cyan",
            border_style="dim"
        )
        
        table.add_column("Certificado", style="white")
        table.add_column("Tipo", justify="center")
        table.add_column("Dominios", justify="left")
        table.add_column("Estado", justify="center")
        table.add_column("Expiración", justify="center")
        table.add_column("Días Rest.", justify="right")
        table.add_column("Semáforo SRE", justify="left")

        results = []

        if not certificates:
            console.print(f"[yellow]⚠️  No se detectaron certificados en {project_id}.[/]")
        else:
            certificates = sorted(certificates, key=lambda x: parse_certificate_name(x.get('name', '')))
            for cert in certificates:
                cert_name = parse_certificate_name(cert.get('name', ''))
                
                san_domains = cert.get('sanDnsnames', [])
                domains_display = ', '.join(san_domains[:2])
                if len(san_domains) > 2:
                    domains_display += f" (+{len(san_domains) - 2})"
                
                cert_type = 'MANAGED' if cert.get('managed') else 'SELF_MANAGED'
                state = cert.get('managed', {}).get('state', 'ACTIVE') if cert.get('managed') else 'ACTIVE'
                
                expire_time = cert.get('expireTime', '')
                expire_display = expire_time[:10] if expire_time else 'N/A'
                days_to_expiry = calculate_days_to_expiry(expire_time)
                days_display = str(days_to_expiry) if days_to_expiry is not None else 'N/A'
                
                status = get_status_text(days_to_expiry, state)
                
                results.append({
                    'project': project_id,
                    'certificate': cert_name,
                    'type': cert_type,
                    'domains': ', '.join(san_domains),
                    'state': state,
                    'expire_time': expire_time,
                    'days_to_expiry': days_to_expiry if days_to_expiry is not None else 'N/A',
                    'status': status,
                    'revision_time': revision_time
                })
                
                row_style = ""
                if days_to_expiry is not None:
                    if days_to_expiry <= 7:
                        row_style = "red"
                    elif days_to_expiry <= 30:
                        row_style = "yellow"

                table.add_row(
                    cert_name,
                    cert_type,
                    domains_display,
                    f"[green]{state}[/]" if state == 'ACTIVE' else f"[red]{state}[/]",
                    expire_display,
                    days_display,
                    get_status_summary(days_to_expiry, state),
                    style=row_style
                )
            
            console.print(table)
            print_summary(console, results)
            
            if args.output and results:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                outcome_dir = os.path.join(script_dir, 'outcome')
                os.makedirs(outcome_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"cert_check_{project_id}_{timestamp}"
                
                if args.output == 'csv':
                    filepath = os.path.join(outcome_dir, f"{filename}.csv")
                    export_to_csv(results, filepath)
                elif args.output == 'json':
                    filepath = os.path.join(outcome_dir, f"{filename}.json")
                    export_to_json(results, filepath, project_id, tz_name)
                
                console.print(f"\n[bold green]📁 Archivo exportado:[/] {filepath}")
            
            console.print(f"\n[dim]Tip: Los certificados con menos de 30 días para expirar requieren atención.[/]\n")

    except Exception as e:
        console.print(f"[bold red]❌ Error ejecutando gcloud:[/]\n{e}")

    print_execution_time(start_time, console, tz_name)

if __name__ == "__main__":
    main()
