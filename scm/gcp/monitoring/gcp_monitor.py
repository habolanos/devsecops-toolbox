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
import logging
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
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.markdown import Markdown
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "3.0.0"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def setup_logger(project_id: str, output_dir: str = "outcome") -> logging.Logger:
    """Configura el logger para registrar comandos ejecutados."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(output_dir, f"gcp_monitor_{project_id}_{timestamp}.log")
    
    logger = logging.getLogger("gcp_monitor")
    logger.setLevel(logging.INFO)
    
    # Handler para archivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Formato del log
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Evitar duplicados
    if not logger.handlers:
        logger.addHandler(file_handler)
    
    return logger, log_file

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

def run_gcloud_command(cmd: str, debug: bool = False, console=None, logger=None, timeout: int = 60) -> Optional[Any]:
    """Ejecuta un comando gcloud y retorna el resultado como JSON."""
    try:
        # Registrar comando en log
        if logger:
            logger.info(f"Ejecutando: {cmd}")
        
        if debug and console and RICH_AVAILABLE:
            console.print(f"[dim]DEBUG: {cmd}[/dim]")
        elif debug:
            print(f"DEBUG: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        
        if result.returncode != 0:
            if logger:
                logger.error(f"Error en comando: {cmd} - {result.stderr[:200]}")
            if debug:
                if console and RICH_AVAILABLE:
                    console.print(f"[dim]Error: {result.stderr[:200]}[/dim]")
                else:
                    print(f"DEBUG Error: {result.stderr[:200]}")
            return None
        
        if logger:
            logger.info(f"Comando exitoso: {cmd[:80]}...")
        
        if not result.stdout.strip():
            return []
        
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        if logger:
            logger.warning(f"No se pudo parsear JSON en: {cmd[:80]}...")
        return result.stdout.strip() if result.stdout else None
    except subprocess.TimeoutExpired:
        if logger:
            logger.error(f"Timeout (>{timeout}s) en comando: {cmd[:80]}...")
        if console and RICH_AVAILABLE:
            console.print(f"[yellow]⚠ Timeout en: {cmd[:60]}...[/yellow]")
        return None
    except Exception as e:
        if logger:
            logger.error(f"Excepción en comando: {cmd} - {str(e)}")
        if debug:
            if console and RICH_AVAILABLE:
                console.print(f"[dim]Exception: {e}[/dim]")
            else:
                print(f"DEBUG Exception: {e}")
        return None


def get_enabled_services(project_id: str, debug: bool, console, logger=None) -> List[Dict]:
    """Obtiene servicios habilitados en el proyecto."""
    cmd = f'gcloud services list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console, logger)
    return result if isinstance(result, list) else []


def get_gke_clusters(project_id: str, debug: bool, console, logger=None) -> List[Dict]:
    """Obtiene clusters GKE del proyecto."""
    cmd = f'gcloud container clusters list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console, logger)
    return result if isinstance(result, list) else []


def get_cloud_sql_instances(project_id: str, debug: bool, console, logger=None) -> List[Dict]:
    """Obtiene instancias Cloud SQL del proyecto."""
    cmd = f'gcloud sql instances list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console, logger)
    return result if isinstance(result, list) else []


def get_compute_instances(project_id: str, debug: bool, console, logger=None) -> List[Dict]:
    """Obtiene instancias Compute Engine del proyecto."""
    cmd = f'gcloud compute instances list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console, logger)
    return result if isinstance(result, list) else []


def get_pubsub_topics(project_id: str, debug: bool, console, logger=None) -> List[Dict]:
    """Obtiene topics de Pub/Sub del proyecto."""
    cmd = f'gcloud pubsub topics list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console, logger)
    return result if isinstance(result, list) else []


def get_cloud_functions(project_id: str, debug: bool, console, logger=None) -> List[Dict]:
    """Obtiene Cloud Functions del proyecto."""
    cmd = f'gcloud functions list --project={project_id} --format=json 2>/dev/null'
    result = run_gcloud_command(cmd, debug, console, logger)
    return result if isinstance(result, list) else []


def get_cloud_run_services(project_id: str, debug: bool, console, logger=None) -> List[Dict]:
    """Obtiene servicios Cloud Run del proyecto."""
    cmd = f'gcloud run services list --project={project_id} --format=json 2>/dev/null'
    result = run_gcloud_command(cmd, debug, console, logger)
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


def create_detailed_tables(data: Dict[str, Any], console) -> None:
    """Crea y muestra tablas detalladas de recursos con Rich."""
    if not RICH_AVAILABLE or not console:
        return
    
    # Tabla de Servicios
    services = data.get('services', [])
    if services:
        table = Table(title="📌 Servicios Habilitados", box=box.ROUNDED)
        table.add_column("Nombre", style="cyan")
        table.add_column("Estado", style="green")
        for svc in services:
            name = svc.get('config', {}).get('title', svc.get('name', 'N/A'))
            table.add_row(name, "✅ Activo")
        console.print(table)
        console.print()
    
    # Tabla de Clusters GKE
    clusters = data.get('gke_clusters', [])
    if clusters:
        table = Table(title="☸️  Clusters GKE", box=box.ROUNDED)
        table.add_column("Nombre", style="cyan")
        table.add_column("Ubicación", style="yellow")
        table.add_column("Estado", style="green")
        table.add_column("Versión", style="magenta")
        table.add_column("Nodos", style="blue", justify="right")
        for cluster in clusters:
            table.add_row(
                cluster.get('name', 'N/A')[:30],
                cluster.get('location', 'N/A'),
                cluster.get('status', 'N/A'),
                cluster.get('currentMasterVersion', 'N/A')[:15],
                str(cluster.get('currentNodeCount', 0))
            )
        console.print(table)
        console.print()
    
    # Tabla de Cloud SQL
    sql_instances = data.get('sql_instances', [])
    if sql_instances:
        table = Table(title="🗄️  Instancias Cloud SQL", box=box.ROUNDED)
        table.add_column("Nombre", style="cyan")
        table.add_column("Estado", style="green")
        table.add_column("Versión", style="yellow")
        table.add_column("Tier", style="magenta")
        table.add_column("Disco (GB)", style="blue", justify="right")
        for instance in sql_instances[:10]:
            disk = instance.get('settings', {}).get('dataDiskSizeGb', 'N/A')
            table.add_row(
                instance.get('name', 'N/A')[:30],
                instance.get('state', 'N/A'),
                instance.get('databaseVersion', 'N/A')[:20],
                instance.get('settings', {}).get('tier', 'N/A')[:20],
                str(disk)
            )
        if len(sql_instances) > 10:
            table.add_row(f"... y {len(sql_instances) - 10} más", "", "", "", "")
        console.print(table)
        console.print()
    
    # Tabla de Compute Engine
    compute_instances = data.get('compute_instances', [])
    if compute_instances:
        table = Table(title="💻 Instancias Compute Engine", box=box.ROUNDED)
        table.add_column("Nombre", style="cyan")
        table.add_column("Estado", style="green")
        table.add_column("Tipo", style="yellow")
        table.add_column("Zona", style="magenta")
        for vm in compute_instances[:15]:
            machine = vm.get('machineType', '').split('/')[-1] if vm.get('machineType') else 'N/A'
            zone = vm.get('zone', '').split('/')[-1] if vm.get('zone') else 'N/A'
            table.add_row(
                vm.get('name', 'N/A')[:30],
                vm.get('status', 'N/A'),
                machine[:20],
                zone
            )
        if len(compute_instances) > 15:
            table.add_row(f"... y {len(compute_instances) - 15} más", "", "", "")
        console.print(table)
        console.print()
    
    # Tabla de Cloud Run
    run_services = data.get('cloud_run', [])
    if run_services:
        table = Table(title="🚀 Servicios Cloud Run", box=box.ROUNDED)
        table.add_column("Nombre", style="cyan")
        table.add_column("Región", style="yellow")
        table.add_column("Estado", style="green")
        for svc in run_services[:10]:
            metadata = svc.get('metadata', {})
            table.add_row(
                metadata.get('name', 'N/A')[:40],
                metadata.get('namespace', 'N/A')[:20],
                "✅ Activo"
            )
        if len(run_services) > 10:
            table.add_row(f"... y {len(run_services) - 10} más", "", "")
        console.print(table)
        console.print()
    
    # Tabla de Pub/Sub
    topics = data.get('pubsub_topics', [])
    if topics:
        table = Table(title="📬 Topics Pub/Sub", box=box.ROUNDED)
        table.add_column("Nombre", style="cyan")
        table.add_column("Estado", style="green")
        for topic in topics:
            name = topic.get('name', '').split('/')[-1] if topic.get('name') else 'N/A'
            table.add_row(name, "✅ Activo")
        console.print(table)
        console.print()


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


def get_status_semaphore(count: int, resource_type: str) -> str:
    """
    Retorna un semáforo (🟢🟡🔴) basado en el count y tipo de recurso.
    Esquema de semáforo:
    - 🟢 Verde: Cantidad óptima
    - 🟡 Amarillo: Cantidad moderada (requiere revisión)
    - 🔴 Rojo: Cantidad crítica o cero
    """
    thresholds = {
        'services': {'green': (1, float('inf')), 'yellow': (1, 50), 'red': (0, 0)},
        'gke_clusters': {'green': (1, float('inf')), 'yellow': (1, 5), 'red': (0, 0)},
        'sql_instances': {'green': (1, float('inf')), 'yellow': (1, 10), 'red': (0, 0)},
        'compute_instances': {'green': (1, float('inf')), 'yellow': (1, 20), 'red': (0, 0)},
        'cloud_run': {'green': (1, float('inf')), 'yellow': (1, 10), 'red': (0, 0)},
        'pubsub_topics': {'green': (1, float('inf')), 'yellow': (1, 50), 'red': (0, 0)},
    }
    
    thresholds_config = thresholds.get(resource_type, {'green': (1, float('inf')), 'yellow': (1, 100), 'red': (0, 0)})
    
    if count == 0:
        return "🔴"  # Rojo: sin recursos
    elif count >= thresholds_config['green'][0]:
        return "🟢"  # Verde: cantidad óptima
    elif count >= thresholds_config['yellow'][0]:
        return "🟡"  # Amarillo: cantidad moderada
    else:
        return "🔴"  # Rojo: crítico


def create_summary_table(data: Dict[str, Any], console, project_id: str = None) -> Table:
    """Crea tabla resumen de recursos."""
    table = Table(title="📊 Resumen de Recursos GCP", box=box.ROUNDED)
    if project_id:
        table.add_column("Proyecto", style="magenta")
    table.add_column("Recurso", style="cyan")
    table.add_column("Cantidad", style="green", justify="right")
    table.add_column("Estado", style="yellow")
    
    # Datos de recursos
    resources = [
        ("Servicios habilitados", 'services', "Servicios activos"),
        ("Clusters GKE", 'gke_clusters', "Orquestación"),
        ("Instancias Cloud SQL", 'sql_instances', "Bases de datos"),
        ("Instancias Compute", 'compute_instances', "Máquinas virtuales"),
        ("Servicios Cloud Run", 'cloud_run', "Serverless"),
        ("Topics Pub/Sub", 'pubsub_topics', "Mensajería"),
    ]
    
    for label, key, description in resources:
        count = len(data.get(key, []))
        status = "✅ Activo" if count > 0 else "⚠️ Inactivo"
        if project_id:
            table.add_row(project_id, label, str(count), status)
        else:
            table.add_row(label, str(count), status)
    
    return table


def create_health_table(data: Dict[str, Any], console) -> Table:
    """Crea tabla de salud general del proyecto."""
    table = Table(title="🏥 Salud General del Proyecto", box=box.ROUNDED)
    table.add_column("Aspecto", style="cyan")
    table.add_column("Valor", style="green", justify="right")
    
    # Calcular métricas de salud
    total_resources = sum(len(v) for v in data.values() if isinstance(v, list))
    services_count = len(data.get('services', []))
    clusters_count = len(data.get('gke_clusters', []))
    sql_count = len(data.get('sql_instances', []))
    compute_count = len(data.get('compute_instances', []))
    
    table.add_row("Recursos Totales", str(total_resources))
    table.add_row("Infraestructura", f"{clusters_count} clusters + {compute_count} máquinas")
    table.add_row("Datos", f"{sql_count} instancias SQL")
    table.add_row("Servicios Activos", str(services_count))
    
    return table


def get_performance_semaphore(duration: float) -> str:
    """
    Retorna semáforo basado en tiempo de ejecución.
    - 🟢 Verde: < 10 segundos (excelente)
    - 🟡 Amarillo: 10-30 segundos (aceptable)
    - 🔴 Rojo: > 30 segundos (lento)
    """
    if duration < 10:
        return "🟢"  # Excelente
    elif duration < 30:
        return "🟡"  # Aceptable
    else:
        return "🔴"  # Lento


def print_execution_summary(start_time: datetime, console, project_id: str, data: Dict[str, Any]) -> None:
    """Imprime tabla resumen de ejecución."""
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    total_resources = sum(len(v) for v in data.values() if isinstance(v, list))
    
    if RICH_AVAILABLE and console:
        table = Table(title="⏱️ Resumen de Ejecución", box=box.ROUNDED)
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        
        table.add_row("Proyecto", project_id)
        table.add_row("Tiempo de ejecución", f"{duration:.2f}s")
        table.add_row("Recursos encontrados", str(total_resources))
        
        console.print()
        console.print(Panel(table, border_style="blue"))
    else:
        print(f"\n⏱️ Resumen de Ejecución")
        print(f"  Proyecto: {project_id}")
        print(f"  Tiempo: {duration:.2f}s")
        print(f"  Recursos: {total_resources}")


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
        default="cpl-cs-wms-dev-30112023",
        help="ID(s) del proyecto GCP, separados por comas (Default: cpl-cs-wms-dev-30112023)"
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
    # Procesar múltiples proyectos separados por comas
    project_ids = [p.strip() for p in args.project.split(',')]
    debug = args.debug
    use_parallel = args.parallel and not args.no_parallel
    max_workers = args.max_workers
    
    # Inicializar logger
    outcome_dir = str(get_output_dir("outcome"))
    logger, log_file = setup_logger(project_ids[0], outcome_dir)
    logger.info(f"═══════════════════════════════════════════════════════════════")
    logger.info(f"GCP Monitor v{__version__} - Inicio de ejecución")
    logger.info(f"Proyectos: {', '.join(project_ids)}")
    logger.info(f"Modo debug: {debug}")
    logger.info(f"Ejecución paralela: {use_parallel}")
    logger.info(f"═══════════════════════════════════════════════════════════════")
    
    if RICH_AVAILABLE and console:
        console.print(Panel(
            f"[bold cyan]GCP Monitor v{__version__}[/bold cyan]\n"
            f"Proyectos: [yellow]{', '.join(project_ids)}[/yellow]",
            border_style="blue"
        ))
    else:
        print(f"GCP Monitor v{__version__}")
        print(f"Proyectos: {', '.join(project_ids)}")
    
    # Verificar conexión para cada proyecto
    for project_id in project_ids:
        if not check_gcp_connection(project_id, console, debug):
            return 1

    all_data: Dict[str, Dict[str, Any]] = {}

    try:
        # Procesar cada proyecto
        for project_id in project_ids:
            if RICH_AVAILABLE and console:
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                    task = progress.add_task(f"[cyan]Recopilando recursos de {project_id}...", total=None)
                    
                    data: Dict[str, Any] = {}
                    if use_parallel:
                        with ThreadPoolExecutor(max_workers=max_workers) as executor:
                            futures = {
                                executor.submit(get_enabled_services, project_id, debug, console, logger): 'services',
                                executor.submit(get_gke_clusters, project_id, debug, console, logger): 'gke_clusters',
                                executor.submit(get_cloud_sql_instances, project_id, debug, console, logger): 'sql_instances',
                                executor.submit(get_compute_instances, project_id, debug, console, logger): 'compute_instances',
                                executor.submit(get_cloud_run_services, project_id, debug, console, logger): 'cloud_run',
                                executor.submit(get_pubsub_topics, project_id, debug, console, logger): 'pubsub_topics',
                            }
                            
                            for future in as_completed(futures, timeout=120):
                                key = futures[future]
                                try:
                                    data[key] = future.result(timeout=120)
                                except Exception as e:
                                    console.print(f"[yellow]⚠ Error en {key}: {e}[/]")
                                    data[key] = []
                    else:
                        data['services'] = get_enabled_services(project_id, debug, console, logger)
                        data['gke_clusters'] = get_gke_clusters(project_id, debug, console, logger)
                        data['sql_instances'] = get_cloud_sql_instances(project_id, debug, console, logger)
                        data['compute_instances'] = get_compute_instances(project_id, debug, console, logger)
                        data['cloud_run'] = get_cloud_run_services(project_id, debug, console, logger)
                        data['pubsub_topics'] = get_pubsub_topics(project_id, debug, console, logger)
                    
                    progress.update(task, description=f"[green]✓ Recursos recopilados de {project_id}")
            else:
                print(f"Recopilando recursos de {project_id}...")
                data: Dict[str, Any] = {}
                data['services'] = get_enabled_services(project_id, debug, console, logger)
                data['gke_clusters'] = get_gke_clusters(project_id, debug, console, logger)
                data['sql_instances'] = get_cloud_sql_instances(project_id, debug, console, logger)
                data['compute_instances'] = get_compute_instances(project_id, debug, console, logger)
                data['cloud_run'] = get_cloud_run_services(project_id, debug, console, logger)
                data['pubsub_topics'] = get_pubsub_topics(project_id, debug, console, logger)
            
            all_data[project_id] = data
        
        # Mostrar tablas de resumen y salud para cada proyecto
        if RICH_AVAILABLE and console:
            console.print()
            for project_id, data in all_data.items():
                console.print(create_summary_table(data, console, project_id))
                console.print()
            
            console.print()
            for project_id, data in all_data.items():
                console.print(create_health_table(data, console))
                console.print()
            
            # Mostrar tablas detalladas de recursos
            console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/]")
            console.print("[bold cyan]📊 DETALLES DE RECURSOS[/]")
            console.print("[bold cyan]═══════════════════════════════════════════════════════════════[/]")
            console.print()
            for project_id, data in all_data.items():
                create_detailed_tables(data, console)
        
        # Generar reporte para el primer proyecto (o consolidado)
        project_id = project_ids[0]
        data = all_data.get(project_id, {})
        report = generate_report(project_id, data)
        
        if RICH_AVAILABLE and console:
            console.print(report)
        else:
            print(report)

        # Guardar en archivo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        outcome_dir = str(get_output_dir("outcome"))
        os.makedirs(outcome_dir, exist_ok=True)
        
        if args.output == "json":
            filepath = export_to_json(data, project_id, outcome_dir, "America/Mazatlan")
        elif args.output == "csv":
            filepath = export_to_csv(data, project_id, outcome_dir)
        else:
            filepath = export_to_txt(report, project_id, outcome_dir)

        if RICH_AVAILABLE and console:
            console.print(f"\n[green]📁 Reporte guardado en:[/] {filepath}")
            console.print(f"[green]📋 Log de comandos:[/] {log_file}")
        else:
            print(f"\n📁 Reporte guardado en: {filepath}")
            print(f"📋 Log de comandos: {log_file}")
        
        logger.info(f"═══════════════════════════════════════════════════════════════")
        logger.info(f"Ejecución completada exitosamente")
        logger.info(f"Reporte guardado en: {filepath}")
        logger.info(f"═══════════════════════════════════════════════════════════════")
        
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
            filepath = output_path / f"gcp_monitor_{ts}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": data}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"gcp_monitor_{ts}.csv"
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
    manager = ExportManager("gcp_monitor", "1.0.0")
    
    summary = {"total_items": len(data) if isinstance(data, list) else 1}
    
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    
    return None
