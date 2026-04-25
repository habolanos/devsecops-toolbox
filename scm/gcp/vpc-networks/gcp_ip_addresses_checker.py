#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP IP Addresses Checker - Herramienta SRE para análisis de capacidad de red

Analiza la utilización de IPs en clusters GKE:
- Obtiene metadatos de red desde GCP (rangos CIDR para pods y servicios)
- Cuenta IPs ocupadas por pods activos usando kubectl
- Cuenta IPs ocupadas por servicios con ClusterIP
- Calcula porcentaje de utilización y genera alertas
- Identifica riesgo de agotamiento de IPs

Características:
- Usa gcloud CLI y kubectl (no requiere APIs especiales)
- Validación de conexión GCP antes de ejecutar
- Exportación a CSV y JSON
- Interfaz enriquecida con Rich

El resultado se guarda en: outcome/ip_addresses_report_<project_id>_<timestamp>.<ext>

Autor: Harold Adrian
"""

import argparse
import subprocess
import json
import csv
import os
import time
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any, Tuple

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
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

def get_args():
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="SRE Tool: GKE IP Addresses Capacity Analysis (gcloud + kubectl)",
        add_help=False
    )
    parser.add_argument(
        "--project",
        type=str,
        default="cpl-corp-cial-prod-17042024",
        help="ID del proyecto de GCP (Default: cpl-corp-cial-prod-17042024)"
    )
    parser.add_argument(
        "--cluster",
        type=str,
        default="gke-corp-cial-prod-01",
        help="Nombre del cluster GKE (Default: gke-corp-cial-prod-01)"
    )
    parser.add_argument(
        "--region",
        type=str,
        default="us-central1",
        help="Región del cluster GKE (Default: us-central1)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa modo debug para ver comandos ejecutados"
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
        help="Zona horaria para mostrar fechas (default: America/Mazatlan)"
    )
    return parser.parse_args()

def show_help(console):
    """Muestra ayuda del script."""
    help_text = """# GCP IP Addresses Checker

## Descripción
Herramienta SRE para analizar la capacidad de red de clusters GKE, verificando la utilización de IPs para pods y servicios.

## Uso
```bash
python gcp_ip_addresses_checker.py --project <PROJECT_ID> --cluster <CLUSTER_NAME> --region <REGION> [opciones]
```

## Opciones
- `--project`: ID del proyecto GCP
- `--cluster`: Nombre del cluster GKE
- `--region`: Región del cluster GKE
- `--output, -o`: Formato de exportación (csv, json)
- `--debug`: Modo debug
- `--timezone, -tz`: Zona horaria para fechas

## Ejemplos
```bash
# Analizar cluster default
python gcp_ip_addresses_checker.py

# Exportar a JSON
python gcp_ip_addresses_checker.py --project mi-proyecto --cluster mi-cluster --region us-central1 -o json

# Modo debug
python gcp_ip_addresses_checker.py --debug
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

def run_gcloud_command(command: str, debug: bool = False) -> Optional[str]:
    """Ejecuta un comando gcloud y retorna el resultado como texto."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if debug:
            print(f"[DEBUG] Command: {command}")
            print(f"[DEBUG] Return code: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] Stderr: {result.stderr[:200]}")
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception as e:
        if debug:
            print(f"[DEBUG] Exception: {e}")
        return None

def run_kubectl_command(command: str, debug: bool = False) -> Optional[str]:
    """Ejecuta un comando kubectl y retorna el resultado como texto."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if debug:
            print(f"[DEBUG] kubectl Command: {command}")
            print(f"[DEBUG] Return code: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] Stderr: {result.stderr[:200]}")
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception as e:
        if debug:
            print(f"[DEBUG] Exception: {e}")
        return None

def get_cluster_network_info(project_id: str, cluster_name: str, region: str, debug: bool = False) -> Optional[Dict[str, str]]:
    """Obtiene metadatos de red desde GCP."""
    cmd = (f'gcloud container clusters describe {cluster_name} --region {region} --project {project_id} '
           f'--format="value(ipAllocationPolicy.clusterIpv4CidrBlock, ipAllocationPolicy.servicesIpv4CidrBlock, networkConfig.subnetwork)"')

    result = run_gcloud_command(cmd, debug)
    if not result:
        return None

    parts = result.split()
    if len(parts) < 3:
        return None

    return {
        'pods_cidr': parts[0],
        'services_cidr': parts[1],
        'subnet': parts[2]
    }


def get_active_pods_count(project_id: str, cluster_name: str, region: str, debug: bool = False) -> Optional[int]:
    """Cuenta pods activos con IP asignada usando kubectl."""
    location_flag = f'--zone={region}' if region.count('-') == 2 else f'--region={region}'
    context_name = f'gke_{project_id}_{region}_{cluster_name}'

    try:
        # Obtener credenciales del cluster
        get_creds = f'gcloud container clusters get-credentials {cluster_name} --project={project_id} {location_flag} --quiet 2>/dev/null'
        creds_result = subprocess.run(get_creds, shell=True, capture_output=True, text=True)

        if debug:
            print(f"[DEBUG] get-credentials returncode: {creds_result.returncode}")
            if creds_result.stderr:
                print(f"[DEBUG] get-credentials stderr: {creds_result.stderr[:200]}")

        # Obtener pods con IP asignada (excluyendo Succeeded/Failed)
        cmd = f'kubectl --context={context_name} get pods --all-namespaces -o json 2>/dev/null'
        result = run_kubectl_command(cmd, debug)

        if not result:
            return None

        try:
            data = json.loads(result)
            items = data.get('items', [])

            active_pods = 0
            for pod in items:
                # Verificar que tenga IP asignada
                pod_ip = pod.get('status', {}).get('podIP')
                if not pod_ip:
                    continue

                # Excluir pods en estado Succeeded/Failed
                phase = pod.get('status', {}).get('phase', '')
                if phase in ['Succeeded', 'Failed']:
                    continue

                active_pods += 1

            if debug:
                print(f"[DEBUG] Active pods count: {active_pods}")
            return active_pods

        except json.JSONDecodeError as e:
            if debug:
                print(f"[DEBUG] JSON decode error: {e}")
            return None

    except Exception as e:
        if debug:
            print(f"[DEBUG] Pod count error: {e}")
        return None

def get_services_count(project_id: str, cluster_name: str, region: str, debug: bool = False) -> Optional[int]:
    """Cuenta servicios con ClusterIP usando kubectl."""
    location_flag = f'--zone={region}' if region.count('-') == 2 else f'--region={region}'
    context_name = f'gke_{project_id}_{region}_{cluster_name}'

    try:
        # Obtener credenciales del cluster
        get_creds = f'gcloud container clusters get-credentials {cluster_name} --project={project_id} {location_flag} --quiet 2>/dev/null'
        creds_result = subprocess.run(get_creds, shell=True, capture_output=True, text=True)

        if debug:
            print(f"[DEBUG] get-credentials returncode: {creds_result.returncode}")
            if creds_result.stderr:
                print(f"[DEBUG] get-credentials stderr: {creds_result.stderr[:200]}")

        # Obtener servicios con ClusterIP
        cmd = f'kubectl --context={context_name} get svc --all-namespaces --no-headers 2>/dev/null'
        result = run_kubectl_command(cmd, debug)

        if not result:
            return None

        # Contar servicios que tienen IP (ClusterIP)
        lines = result.strip().split('\n')
        services_with_ip = 0

        for line in lines:
            if not line.strip():
                continue

            # Formato: namespace name type cluster-ip external-ip port(s) age
            parts = line.split()
            if len(parts) >= 4:
                cluster_ip = parts[3]
                # Verificar que sea una IP válida (no "None" o "<none>")
                if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', cluster_ip):
                    services_with_ip += 1

        if debug:
            print(f"[DEBUG] Services with ClusterIP count: {services_with_ip}")
        return services_with_ip

    except Exception as e:
        if debug:
            print(f"[DEBUG] Services count error: {e}")
        return None

def calculate_total_ips(cidr: str) -> int:
    """Calcula el total de IPs disponibles en un rango CIDR."""
    if not cidr or '/' not in cidr:
        return 0

    try:
        mask = int(cidr.split('/')[1])
        if mask < 0 or mask > 32:
            return 0
        return (2 ** (32 - mask)) - 2  # Restar network y broadcast
    except (ValueError, IndexError):
        return 0

def get_utilization_status(pods_pct: float, services_pct: float) -> Tuple[str, str, List[str]]:
    """Determina el estado de alerta basado en porcentajes de utilización."""
    alerts = []

    if services_pct > 90:
        alerts.append("[CRÍTICO] IPs de Servicios agotadas. No se pueden desplegar más Apps.")
    if pods_pct > 80:
        alerts.append("[WARNING] IPs de Pods cerca del límite.")

    if not alerts:
        alerts.append("[OK] Capacidad dentro de rangos normales.")

    # Determinar estado general
    if services_pct > 90:
        status = "CRITICAL"
        status_style = "red"
    elif pods_pct > 80:
        status = "WARNING"
        status_style = "yellow"
    else:
        status = "OK"
        status_style = "green"
    
    return status, status_style, alerts

def create_capacity_table(data: Dict, console) -> Table:
    """Crea la tabla de capacidad de red."""
    table = Table(
        title="🌐 Capacidad de Red del Cluster",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim",
        box=box.ROUNDED
    )

    table.add_column("Componente", style="white")
    table.add_column("Rango CIDR", style="cyan")
    table.add_column("Máscara", justify="center")
    table.add_column("IPs Ocupadas", justify="right")
    table.add_column("IPs Totales", justify="right")
    table.add_column("Utilización", justify="center")
    table.add_column("Estado", justify="center")

    # Pods row
    pods_pct = data['pods_utilization_pct']
    pods_style = "red" if pods_pct > 80 else "yellow" if pods_pct > 60 else "green"

    table.add_row(
        "📦 Pods ",
        data['pods_cidr'],
        f"/{data['pods_mask']}",
        str(data['pods_used']),
        str(data['pods_total']),
        f"[{pods_style}]{pods_pct:.2f}%[/{pods_style}]",
        f"[{pods_style}]{'⚠️' if pods_pct > 80 else '✓'}[/{pods_style}]"
    )

    # Services row
    svc_pct = data['services_utilization_pct']
    svc_style = "red" if svc_pct > 90 else "yellow" if svc_pct > 70 else "green"

    table.add_row(
        "🌐 Servicios ",
        data['services_cidr'],
        f"/{data['services_mask']}",
        str(data['services_used']),
        str(data['services_total']),
        f"[{svc_style}]{svc_pct:.2f}%[/{svc_style}]",
        f"[{svc_style}]{'🚨' if svc_pct > 90 else '✓'}[/{svc_style}]"
    )

    return table

def create_alerts_panel(alerts: List[str], console) -> Panel:
    """Crea el panel de alertas."""
    alert_text = "\n".join(f"• {alert}" for alert in alerts)
    return Panel(
        alert_text,
        title="🚨 Estado de Alerta",
        border_style="red" if "CRÍTICO" in alert_text else "yellow" if "WARNING" in alert_text else "green",
        expand=False
    )

def export_to_csv(data: Dict, filepath: str):
    """Exporta los datos a un archivo CSV."""
    flat_data = [{
        'project': data['project'],
        'cluster': data['cluster'],
        'region': data['region'],
        'subnet': data['subnet'],
        'component': 'Pods',
        'cidr': data['pods_cidr'],
        'mask': data['pods_mask'],
        'used_ips': data['pods_used'],
        'total_ips': data['pods_total'],
        'utilization_pct': data['pods_utilization_pct'],
        'status': data['status'],
        'revision_time': data['revision_time']
    }, {
        'project': data['project'],
        'cluster': data['cluster'],
        'region': data['region'],
        'subnet': data['subnet'],
        'component': 'Services',
        'cidr': data['services_cidr'],
        'mask': data['services_mask'],
        'used_ips': data['services_used'],
        'total_ips': data['services_total'],
        'utilization_pct': data['services_utilization_pct'],
        'status': data['status'],
        'revision_time': data['revision_time']
    }]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=flat_data[0].keys())
        writer.writeheader()
        writer.writerows(flat_data)

def export_to_json(data: Dict, filepath: str, tz_name: str = "America/Mazatlan"):
    """Exporta los datos a un archivo JSON con metadatos completos."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    export_data = {
        "report_metadata": {
            "tool_name": "GCP IP Addresses Checker",
            "version": __version__,
            "author": __author__,
            "project_id": data['project'],
            "cluster_name": data['cluster'],
            "region": data['region'],
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "cluster_info": {
            "project": data['project'],
            "cluster": data['cluster'],
            "region": data['region'],
            "subnet": data['subnet']
        },
        "capacity_analysis": {
            "pods": {
                "cidr": data['pods_cidr'],
                "mask": data['pods_mask'],
                "used_ips": data['pods_used'],
                "total_ips": data['pods_total'],
                "utilization_pct": data['pods_utilization_pct']
            },
            "services": {
                "cidr": data['services_cidr'],
                "mask": data['services_mask'],
                "used_ips": data['services_used'],
                "total_ips": data['services_total'],
                "utilization_pct": data['services_utilization_pct']
            }
        },
        "status": {
            "overall": data['status'],
            "alerts": data['alerts']
        },
        "revision_time": data['revision_time']
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

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
    cluster_name = args.cluster
    region = args.region
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
        console.print(f"\n[bold blue]🌐 Analizando capacidad de red del cluster:[/] [white underline]{cluster_name}[/]")
        console.print(f"[dim]📍 Proyecto: {project_id} | Región: {region}[/]")
        console.print(f"[dim]🕐 Fecha y hora de revisión: {revision_time}[/]")
    else:
        print(f"\n🌐 Analizando capacidad de red del cluster: {cluster_name}")
        print(f"📍 Proyecto: {project_id} | Región: {region}")
        print(f"🕐 Fecha y hora de revisión: {revision_time}")

    if not check_gcp_connection(project_id, console, args.debug):
        print_execution_time(start_time, console, tz_name)
        return 1

    if RICH_AVAILABLE:
        console.print()

    try:
        # Obtener información de red del cluster
        if RICH_AVAILABLE:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                task = progress.add_task("Obteniendo metadatos de red...", total=None)
                network_info = get_cluster_network_info(project_id, cluster_name, region, args.debug)
        else:
            print("Obteniendo metadatos de red...")
            network_info = get_cluster_network_info(project_id, cluster_name, region, args.debug)

        if not network_info:
            if RICH_AVAILABLE:
                console.print(f"[red]❌ No se pudo obtener información de red del cluster {cluster_name}[/]")
            else:
                print(f"❌ No se pudo obtener información de red del cluster {cluster_name}")
            print_execution_time(start_time, console, tz_name)
            return 1

        # Obtener conteo de pods y servicios
        if RICH_AVAILABLE:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                task = progress.add_task("Contando IPs ocupadas...", total=None)
                pods_used = get_active_pods_count(project_id, cluster_name, region, args.debug)
                services_used = get_services_count(project_id, cluster_name, region, args.debug)
        else:
            print("Contando IPs ocupadas...")
            pods_used = get_active_pods_count(project_id, cluster_name, region, args.debug)
            services_used = get_services_count(project_id, cluster_name, region, args.debug)
        
        if pods_used is None or services_used is None:
            if RICH_AVAILABLE:
                console.print(f"[red]❌ No se pudo obtener el conteo de IPs del cluster[/]")
            else:
                print(f"❌ No se pudo obtener el conteo de IPs del cluster")
            print_execution_time(start_time, console, tz_name)
            return 1

        # Calcular totales y porcentajes
        pods_cidr = network_info['pods_cidr']
        services_cidr = network_info['services_cidr']
        subnet = network_info['subnet']

        pods_total = calculate_total_ips(pods_cidr)
        services_total = calculate_total_ips(services_cidr)

        pods_mask = pods_cidr.split('/')[1] if '/' in pods_cidr else 'N/A'
        services_mask = services_cidr.split('/')[1] if '/' in services_cidr else 'N/A'

        pods_utilization_pct = (pods_used / pods_total * 100) if pods_total > 0 else 0
        services_utilization_pct = (services_used / services_total * 100) if services_total > 0 else 0

        # Determinar estado y alertas
        status, status_style, alerts = get_utilization_status(pods_utilization_pct, services_utilization_pct)

        # Consolidar datos
        data = {
            'project': project_id,
            'cluster': cluster_name,
            'region': region,
            'subnet': subnet,
            'pods_cidr': pods_cidr,
            'pods_mask': pods_mask,
            'pods_used': pods_used,
            'pods_total': pods_total,
            'pods_utilization_pct': pods_utilization_pct,
            'services_cidr': services_cidr,
            'services_mask': services_mask,
            'services_used': services_used,
            'services_total': services_total,
            'services_utilization_pct': services_utilization_pct,
            'status': status,
            'alerts': alerts,
            'revision_time': revision_time
        }

        # Mostrar resultados
        if RICH_AVAILABLE:
            console.print(create_capacity_table(data, console))
            console.print()
            console.print(create_alerts_panel(alerts, console))
        else:
            print("\n" + "="*60)
            print("REPORTE DE CAPACIDAD DE RED - CLUSTER COMERCIAL")
            print("="*60)
            print(f"SUBNET VPC  : {subnet}")
            print("")
            print(f"RANGO PODS  : {pods_cidr} (Máscara /{pods_mask})")
            print(f"IPS DE PODS : {pods_used} ocupadas de {pods_total} totales")
            print(f"UTILIZACIÓN : {pods_utilization_pct:.2f}%")
            print("")
            print(f"RANGO SVCS  : {services_cidr} (Máscara /{services_mask})")
            print(f"IPS DE SVC  : {services_used} ocupadas de {services_total} totales")
            print(f"UTILIZACIÓN : {services_utilization_pct:.2f}%")
            print("="*60)
            print("ESTADO DE ALERTA:")
            for alert in alerts:
                print(f"  {alert}")
            print("="*60)
        
        # Exportar si se solicita
        if args.output:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            outcome_dir = os.path.join(script_dir, 'outcome')
            os.makedirs(outcome_dir, exist_ok=True)

            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"ip_addresses_report_{project_id}_{timestamp}"

            if args.output == 'csv':
                filepath = os.path.join(outcome_dir, f"{filename}.csv")
                export_to_csv(data, filepath)
            else:  # json
                filepath = os.path.join(outcome_dir, f"{filename}.json")
                export_to_json(data, filepath, tz_name)

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
