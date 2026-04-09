#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Monitor v3 - Herramienta SRE de Monitoreo de Recursos GCP

Monitorea y genera reportes de recursos en Google Cloud Platform:
- Servicios habilitados en el proyecto
- Clusters GKE y sus nodos
- Instancias Cloud SQL y su estado
- Instancias Compute Engine

Características:
- Usa gcloud CLI (no requiere APIs de Python especiales)
- Ejecución paralela con ThreadPoolExecutor
- Validación de conexión GCP antes de ejecutar
- Exportación a TXT, CSV y JSON

El resultado se guarda en: outcome/gcp_report_<project_id>_<timestamp>.<ext>

Autor: Harold Adrian
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "3.0.0"


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


def get_enabled_services(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene servicios habilitados en el proyecto."""
    cmd = f'gcloud services list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console)
    return result if isinstance(result, list) else []


def get_gke_clusters(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene clusters GKE del proyecto."""
    cmd = f'gcloud container clusters list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console)
    return result if isinstance(result, list) else []


def get_cloud_sql_instances(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene instancias Cloud SQL del proyecto."""
    cmd = f'gcloud sql instances list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console)
    return result if isinstance(result, list) else []


def get_compute_instances(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene instancias Compute Engine del proyecto."""
    cmd = f'gcloud compute instances list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console)
    return result if isinstance(result, list) else []


def get_pubsub_topics(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene topics de Pub/Sub del proyecto."""
    cmd = f'gcloud pubsub topics list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console)
    return result if isinstance(result, list) else []


def get_cloud_functions(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene Cloud Functions del proyecto."""
    cmd = f'gcloud functions list --project={project_id} --format=json 2>/dev/null'
    result = run_gcloud_command(cmd, debug, console)
    return result if isinstance(result, list) else []


def get_cloud_run_services(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene servicios Cloud Run del proyecto."""
    cmd = f'gcloud run services list --project={project_id} --format=json 2>/dev/null'
    result = run_gcloud_command(cmd, debug, console)
    return result if isinstance(result, list) else []


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


def generate_report(project_id: str, data: Dict[str, Any]) -> str:
    """Genera el reporte como string."""
    lines = []
    now_local = datetime.now()
    
    lines.append("=" * 80)
    lines.append(f"📊 REPORTE DE MONITOREO GCP - Proyecto: {project_id}")
    lines.append(f"🕐 Fecha: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"📦 Versión: {__version__}")
    lines.append("=" * 80)
    lines.append("")

    # Servicios habilitados
    services = data.get('services', [])
    lines.append("📌 SERVICIOS HABILITADOS:")
    lines.append("-" * 80)
    lines.append(f"✅ {len(services)} servicios activos en el proyecto")
    if services and len(services) <= 20:
        for svc in services[:10]:
            name = svc.get('config', {}).get('title', svc.get('name', 'N/A'))
            lines.append(f"   • {name}")
        if len(services) > 10:
            lines.append(f"   ... y {len(services) - 10} más")
    lines.append("")

    # Clusters GKE
    clusters = data.get('gke_clusters', [])
    lines.append("☸️  CLUSTERS GKE:")
    lines.append("-" * 80)
    if clusters:
        lines.append(f"📊 Total de clusters: {len(clusters)}")
        for cluster in clusters:
            lines.append(f"   📦 {cluster.get('name', 'N/A')}")
            lines.append(f"      Ubicación: {cluster.get('location', 'N/A')}")
            lines.append(f"      Estado: {cluster.get('status', 'N/A')}")
            lines.append(f"      Versión: {cluster.get('currentMasterVersion', 'N/A')}")
            nodes = cluster.get('currentNodeCount', 0)
            lines.append(f"      Nodos: {nodes}")
            lines.append("")
    else:
        lines.append("ℹ️  No se encontraron clusters GKE")
    lines.append("")

    # Cloud SQL
    sql_instances = data.get('sql_instances', [])
    lines.append("🗄️  INSTANCIAS CLOUD SQL:")
    lines.append("-" * 80)
    if sql_instances:
        lines.append(f"📊 Total de instancias: {len(sql_instances)}")
        for instance in sql_instances:
            lines.append(f"   📦 {instance.get('name', 'N/A')}")
            lines.append(f"      Estado: {instance.get('state', 'N/A')}")
            lines.append(f"      Versión: {instance.get('databaseVersion', 'N/A')}")
            lines.append(f"      Tier: {instance.get('settings', {}).get('tier', 'N/A')}")
            disk_size = instance.get('settings', {}).get('dataDiskSizeGb', 'N/A')
            lines.append(f"      Disco: {disk_size} GB")
            lines.append("")
    else:
        lines.append("ℹ️  No se encontraron instancias Cloud SQL")
    lines.append("")

    # Compute Engine
    compute_instances = data.get('compute_instances', [])
    lines.append("💻 INSTANCIAS COMPUTE ENGINE:")
    lines.append("-" * 80)
    if compute_instances:
        lines.append(f"📊 Total de instancias: {len(compute_instances)}")
        for vm in compute_instances:
            lines.append(f"   📦 {vm.get('name', 'N/A')}")
            lines.append(f"      Estado: {vm.get('status', 'N/A')}")
            machine = vm.get('machineType', '').split('/')[-1] if vm.get('machineType') else 'N/A'
            lines.append(f"      Tipo: {machine}")
            zone = vm.get('zone', '').split('/')[-1] if vm.get('zone') else 'N/A'
            lines.append(f"      Zona: {zone}")
            lines.append("")
    else:
        lines.append("ℹ️  No se encontraron instancias Compute Engine")
    lines.append("")

    # Cloud Run
    run_services = data.get('cloud_run', [])
    lines.append("🚀 SERVICIOS CLOUD RUN:")
    lines.append("-" * 80)
    if run_services:
        lines.append(f"📊 Total de servicios: {len(run_services)}")
        for svc in run_services:
            metadata = svc.get('metadata', {})
            lines.append(f"   📦 {metadata.get('name', 'N/A')}")
            lines.append("")
    else:
        lines.append("ℹ️  No se encontraron servicios Cloud Run")
    lines.append("")

    # Pub/Sub
    topics = data.get('pubsub_topics', [])
    lines.append("📬 TOPICS PUB/SUB:")
    lines.append("-" * 80)
    if topics:
        lines.append(f"📊 Total de topics: {len(topics)}")
        for topic in topics[:10]:
            name = topic.get('name', '').split('/')[-1] if topic.get('name') else 'N/A'
            lines.append(f"   • {name}")
        if len(topics) > 10:
            lines.append(f"   ... y {len(topics) - 10} más")
    else:
        lines.append("ℹ️  No se encontraron topics Pub/Sub")
    lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def create_summary_table(data: Dict[str, Any], console) -> Table:
    """Crea tabla resumen de recursos."""
    table = Table(title="📊 Resumen de Recursos GCP", box=box.ROUNDED)
    table.add_column("Recurso", style="cyan")
    table.add_column("Cantidad", style="green", justify="right")
    table.add_column("Estado", style="yellow")
    
    table.add_row("Servicios habilitados", str(len(data.get('services', []))), "✅")
    table.add_row("Clusters GKE", str(len(data.get('gke_clusters', []))), "✅" if data.get('gke_clusters') else "—")
    table.add_row("Instancias Cloud SQL", str(len(data.get('sql_instances', []))), "✅" if data.get('sql_instances') else "—")
    table.add_row("Instancias Compute", str(len(data.get('compute_instances', []))), "✅" if data.get('compute_instances') else "—")
    table.add_row("Servicios Cloud Run", str(len(data.get('cloud_run', []))), "✅" if data.get('cloud_run') else "—")
    table.add_row("Topics Pub/Sub", str(len(data.get('pubsub_topics', []))), "✅" if data.get('pubsub_topics') else "—")
    
    return table


def print_execution_summary(start_time: datetime, console, project_id: str, data: Dict[str, Any]) -> None:
    """Imprime tabla resumen de ejecución."""
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if RICH_AVAILABLE and console:
        table = Table(title="⏱️ Resumen de Ejecución", box=box.ROUNDED)
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        
        table.add_row("Proyecto", project_id)
        table.add_row("Tiempo de ejecución", f"{duration:.2f}s")
        table.add_row("Recursos encontrados", str(sum(len(v) for v in data.values() if isinstance(v, list))))
        
        console.print()
        console.print(Panel(table, border_style="blue"))
    else:
        print(f"\n⏱️ Resumen de Ejecución")
        print(f"  Proyecto: {project_id}")
        print(f"  Tiempo: {duration:.2f}s")


def export_to_json(data: Dict[str, Any], project_id: str, output_dir: str, tz_name: str = "America/Mazatlan") -> str:
    """Exporta datos a archivo JSON con metadatos completos."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"gcp_report_{project_id}_{timestamp}.json")
    
    export_data = {
        "report_metadata": {
            "tool_name": "GCP Monitor",
            "version": __version__,
            "project_id": project_id,
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "total_services": len(data.get('enabled_services', [])),
            "total_gke_clusters": len(data.get('gke_clusters', [])),
            "total_sql_instances": len(data.get('sql_instances', [])),
            "total_compute_instances": len(data.get('compute_instances', [])),
            "total_cloud_run_services": len(data.get('cloud_run_services', [])),
            "total_pubsub_topics": len(data.get('pubsub_topics', []))
        },
        "data": data
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
    
    return filepath


def export_to_csv(data: Dict[str, Any], project_id: str, output_dir: str) -> str:
    """Exporta datos a archivo CSV."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"gcp_report_{project_id}_{timestamp}.csv")
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['project_id', 'resource_type', 'name', 'status', 'details'])
        
        for cluster in data.get('gke_clusters', []):
            writer.writerow([project_id, 'gke_cluster', cluster.get('name'), cluster.get('status'), cluster.get('location')])
        
        for instance in data.get('sql_instances', []):
            writer.writerow([project_id, 'cloud_sql', instance.get('name'), instance.get('state'), instance.get('databaseVersion')])
        
        for vm in data.get('compute_instances', []):
            writer.writerow([project_id, 'compute_instance', vm.get('name'), vm.get('status'), vm.get('machineType', '').split('/')[-1]])
    
    return filepath


def export_to_txt(report: str, project_id: str, output_dir: str) -> str:
    """Exporta reporte a archivo TXT."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"gcp_report_{project_id}_{timestamp}.txt")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return filepath


def get_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="SRE Tool: GCP Monitor - Monitoreo de recursos GCP",
        add_help=False
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        default="cpl-corp-cial-prod-17042024",
        help="ID del proyecto GCP (Default: cpl-corp-cial-prod-17042024)"
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
        default=6,
        help="Número máximo de workers para ejecución paralela (default: 6)"
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
    project_id = args.project
    debug = args.debug
    use_parallel = args.parallel and not args.no_parallel
    max_workers = args.max_workers
    
    if RICH_AVAILABLE and console:
        console.print(Panel(
            f"[bold cyan]GCP Monitor v{__version__}[/bold cyan]\n"
            f"Proyecto: [yellow]{project_id}[/yellow]",
            border_style="blue"
        ))
    else:
        print(f"GCP Monitor v{__version__}")
        print(f"Proyecto: {project_id}")
    
    if not check_gcp_connection(project_id, console, debug):
        return 1

    data: Dict[str, Any] = {}

    try:
        if RICH_AVAILABLE and console:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                task = progress.add_task("[cyan]Recopilando recursos GCP...", total=None)
                
                if use_parallel:
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {
                            executor.submit(get_enabled_services, project_id, debug, console): 'services',
                            executor.submit(get_gke_clusters, project_id, debug, console): 'gke_clusters',
                            executor.submit(get_cloud_sql_instances, project_id, debug, console): 'sql_instances',
                            executor.submit(get_compute_instances, project_id, debug, console): 'compute_instances',
                            executor.submit(get_cloud_run_services, project_id, debug, console): 'cloud_run',
                            executor.submit(get_pubsub_topics, project_id, debug, console): 'pubsub_topics',
                        }
                        
                        for future in as_completed(futures):
                            key = futures[future]
                            try:
                                data[key] = future.result()
                            except Exception as e:
                                console.print(f"[yellow]⚠ Error en {key}: {e}[/]")
                                data[key] = []
                else:
                    data['services'] = get_enabled_services(project_id, debug, console)
                    data['gke_clusters'] = get_gke_clusters(project_id, debug, console)
                    data['sql_instances'] = get_cloud_sql_instances(project_id, debug, console)
                    data['compute_instances'] = get_compute_instances(project_id, debug, console)
                    data['cloud_run'] = get_cloud_run_services(project_id, debug, console)
                    data['pubsub_topics'] = get_pubsub_topics(project_id, debug, console)
                
                progress.update(task, description="[green]✓ Recursos recopilados")
        else:
            print("Recopilando recursos GCP...")
            data['services'] = get_enabled_services(project_id, debug, console)
            data['gke_clusters'] = get_gke_clusters(project_id, debug, console)
            data['sql_instances'] = get_cloud_sql_instances(project_id, debug, console)
            data['compute_instances'] = get_compute_instances(project_id, debug, console)
            data['cloud_run'] = get_cloud_run_services(project_id, debug, console)
            data['pubsub_topics'] = get_pubsub_topics(project_id, debug, console)
        
        # Mostrar tabla resumen
        if RICH_AVAILABLE and console:
            console.print()
            console.print(create_summary_table(data, console))
            console.print()
        
        # Generar reporte
        report = generate_report(project_id, data)
        
        if RICH_AVAILABLE and console:
            console.print(report)
        else:
            print(report)

        # Guardar en archivo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        outcome_dir = os.path.join(script_dir, "outcome")
        os.makedirs(outcome_dir, exist_ok=True)
        
        if args.output == "json":
            filepath = export_to_json(data, project_id, outcome_dir, "America/Mazatlan")
        elif args.output == "csv":
            filepath = export_to_csv(data, project_id, outcome_dir)
        else:
            filepath = export_to_txt(report, project_id, outcome_dir)

        if RICH_AVAILABLE and console:
            console.print(f"\n[green]📁 Reporte guardado en:[/] {filepath}")
        else:
            print(f"\n📁 Reporte guardado en: {filepath}")
        
        print_execution_summary(start_time, console, project_id, data)

    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ Error ejecutando el monitoreo: {e}[/]")
        else:
            print(f"❌ Error ejecutando el monitoreo: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
