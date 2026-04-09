#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GCP Gateway Services Checker

Herramienta SRE para monitorear y diagnosticar Gateways, Routes, Services y Policies
en clusters GKE usando la API de Kubernetes Gateway.

Autor: SRE Team
"""

import argparse
import subprocess
import json
import csv
import time
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

__version__ = "2.1.0"

print_lock = Lock()

def get_args():
    parser = argparse.ArgumentParser(
        description="SRE Tool: GKE Gateway Services Checker (kubectl)",
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
        help="Nombre del cluster GKE específico (si no se especifica, lista todos los clusters)"
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="",
        help="Namespace específico (default: todos los namespaces)"
    )
    parser.add_argument(
        "--view",
        type=str,
        choices=["all", "gateways", "routes", "services", "policies"],
        default="all",
        help="Vista específica a mostrar (default: all)"
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
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Ejecuta procesamiento en paralelo (default: True)"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Desactiva procesamiento paralelo"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Número máximo de workers paralelos (default: 4)"
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


def run_kubectl_command(command, debug=False):
    """Ejecuta un comando kubectl y retorna el resultado como JSON"""
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


def get_clusters(project_id, debug=False):
    """Obtiene lista de clusters GKE del proyecto"""
    cmd = f'gcloud container clusters list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug) or []


def get_cluster_credentials(project_id, cluster_name, location, debug=False):
    """Obtiene las credenciales de un cluster GKE"""
    location_flag = f'--zone={location}' if location.count('-') == 2 else f'--region={location}'
    cmd = f'gcloud container clusters get-credentials {cluster_name} --project={project_id} {location_flag} --quiet'
    
    if debug:
        print(f"[DEBUG] Getting credentials: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        if debug:
            print(f"[DEBUG] Credentials error: {e}")
        return False


def get_current_context(debug=False):
    """Obtiene el contexto actual de kubectl"""
    try:
        result = subprocess.run(
            'kubectl config current-context',
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        if debug:
            print(f"[DEBUG] Context error: {e}")
    return "unknown"


def get_gateways(namespace="", debug=False):
    """Obtiene lista de Gateways usando kubectl"""
    ns_flag = f"-n {namespace}" if namespace else "-A"
    cmd = f'kubectl get gateways {ns_flag} -o json'
    result = run_kubectl_command(cmd, debug)
    return result.get('items', []) if result else []


def get_httproutes(namespace="", debug=False):
    """Obtiene lista de HTTPRoutes usando kubectl"""
    ns_flag = f"-n {namespace}" if namespace else "-A"
    cmd = f'kubectl get httproutes {ns_flag} -o json'
    result = run_kubectl_command(cmd, debug)
    return result.get('items', []) if result else []


def get_services(namespace="", debug=False):
    """Obtiene lista de Services usando kubectl"""
    ns_flag = f"-n {namespace}" if namespace else "-A"
    cmd = f'kubectl get services {ns_flag} -o json'
    result = run_kubectl_command(cmd, debug)
    return result.get('items', []) if result else []


def get_healthcheckpolicies(namespace="", debug=False):
    """Obtiene lista de HealthCheckPolicies usando kubectl"""
    ns_flag = f"-n {namespace}" if namespace else "-A"
    cmd = f'kubectl get healthcheckpolicies {ns_flag} -o json 2>/dev/null'
    result = run_kubectl_command(cmd, debug)
    return result.get('items', []) if result else []


def get_gcpbackendpolicies(namespace="", debug=False):
    """Obtiene lista de GCPBackendPolicies usando kubectl"""
    ns_flag = f"-n {namespace}" if namespace else "-A"
    cmd = f'kubectl get gcpbackendpolicies {ns_flag} -o json 2>/dev/null'
    result = run_kubectl_command(cmd, debug)
    return result.get('items', []) if result else []


def get_gateway_status(gateway):
    """Determina el estado del Gateway basado en condiciones"""
    conditions = gateway.get('status', {}).get('conditions', [])
    for cond in conditions:
        if cond.get('type') == 'Programmed' and cond.get('status') == 'True':
            return 'Healthy'
        if cond.get('type') == 'Accepted' and cond.get('status') == 'True':
            return 'Accepted'
    
    for cond in conditions:
        if cond.get('status') == 'False':
            return 'Unhealthy'
    
    return 'Unknown'


def get_service_status(service):
    """Determina el estado del Service"""
    svc_type = service.get('spec', {}).get('type', 'ClusterIP')
    
    if svc_type == 'LoadBalancer':
        ingress = service.get('status', {}).get('loadBalancer', {}).get('ingress', [])
        if ingress:
            return 'OK'
        return 'Pending'
    
    cluster_ip = service.get('spec', {}).get('clusterIP', '')
    if cluster_ip and cluster_ip != 'None':
        return 'OK'
    
    return 'Unknown'


def get_policy_status(policy):
    """Determina el estado de una Policy"""
    conditions = policy.get('status', {}).get('conditions', [])
    for cond in conditions:
        if cond.get('type') == 'Attached' and cond.get('status') == 'True':
            return 'Attached'
    return 'Detached'


def get_status_color(status):
    """Retorna el color para un estado"""
    status_colors = {
        'Healthy': 'green',
        'OK': 'green',
        'Attached': 'green',
        'Accepted': 'yellow',
        'Pending': 'yellow',
        'Unhealthy': 'red',
        'Detached': 'red',
        'Unknown': 'dim'
    }
    return status_colors.get(status, 'white')


def get_gateway_sre_status(status):
    """Lógica de Semáforo SRE para Gateways"""
    if status == 'Healthy':
        return "[bold green] HEALTHY [/]"
    elif status == 'Accepted':
        return "[bold yellow] ACCEPTED [/]"
    elif status == 'Unhealthy':
        return "[bold white on red] UNHEALTHY [/]"
    return "[dim] UNKNOWN [/]"


def get_route_sre_status(has_gateway, rules_count):
    """Lógica de Semáforo SRE para Routes"""
    if not has_gateway:
        return "[bold white on red] NO GATEWAY [/]"
    if rules_count == 0:
        return "[bold yellow] NO RULES [/]"
    return "[bold green] HEALTHY [/]"


def get_service_sre_status(status, pods_ready, pods_total):
    """Lógica de Semáforo SRE para Services"""
    if status != 'OK':
        return "[bold yellow] PENDING [/]"
    if pods_total == 0:
        return "[bold white on red] NO PODS [/]"
    if pods_ready < pods_total:
        return "[bold yellow] DEGRADED [/]"
    return "[bold green] HEALTHY [/]"


def get_policy_sre_status(status):
    """Lógica de Semáforo SRE para Policies"""
    if status == 'Attached':
        return "[bold green] ATTACHED [/]"
    return "[bold white on red] DETACHED [/]"


def parse_creation_date(timestamp):
    """Parsea timestamp de Kubernetes y retorna fecha formateada"""
    if not timestamp:
        return 'N/A'
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y')
    except Exception:
        return timestamp[:10] if len(timestamp) >= 10 else timestamp


def get_endpoints_count(service, debug=False):
    """Obtiene el conteo de endpoints para un service"""
    name = service.get('metadata', {}).get('name', '')
    namespace = service.get('metadata', {}).get('namespace', '')
    
    cmd = f'kubectl get endpoints {name} -n {namespace} -o json'
    result = run_kubectl_command(cmd, debug)
    
    if not result:
        return 0, 0
    
    subsets = result.get('subsets', [])
    ready = 0
    not_ready = 0
    
    for subset in subsets:
        addresses = subset.get('addresses', [])
        not_ready_addresses = subset.get('notReadyAddresses', [])
        ready += len(addresses)
        not_ready += len(not_ready_addresses)
    
    return ready, ready + not_ready


def export_to_csv(data, filepath):
    """Exporta los datos a un archivo CSV"""
    if not data:
        return
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
            "tool_name": "GCP Gateway Services Checker",
            "version": __version__,
            "project_id": project_id,
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "data": data
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)


def print_gateways_table(console, gateways, revision_time, debug=False):
    """Imprime tabla de Gateways"""
    table = Table(
        title="🚪 Gateways",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Name", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Gateway Class", justify="left")
    table.add_column("Type", justify="center")
    table.add_column("Load Balancer", justify="left")
    table.add_column("IP Addresses", justify="left")
    table.add_column("Namespace", justify="left")
    table.add_column("Ports", justify="center")
    table.add_column("Semáforo SRE", justify="left")
    
    results = []
    
    if not gateways:
        console.print("[yellow]⚠️  No se detectaron Gateways.[/]")
        return results
    
    gateways = sorted(gateways, key=lambda x: x.get('metadata', {}).get('name', ''))
    
    for gw in gateways:
        metadata = gw.get('metadata', {})
        spec = gw.get('spec', {})
        status = gw.get('status', {})
        
        name = metadata.get('name', 'N/A')
        namespace = metadata.get('namespace', 'N/A')
        gw_class = spec.get('gatewayClassName', 'N/A')
        
        gw_status = get_gateway_status(gw)
        
        addresses = status.get('addresses', [])
        ip_list = [addr.get('value', '') for addr in addresses]
        ip_display = ', '.join(ip_list[:2])
        if len(ip_list) > 2:
            ip_display += f" (+{len(ip_list) - 2})"
        
        lb_name = "N/A"
        annotations = metadata.get('annotations', {})
        for key, value in annotations.items():
            if 'load-balancer' in key.lower() or 'forwarding-rule' in key.lower():
                lb_name = value.split('/')[-1] if '/' in value else value
                break
        
        if lb_name == "N/A" and addresses:
            lb_name = f"gkegw1-{namespace[:10]}-{name[:15]}"
        
        listeners = spec.get('listeners', [])
        ports = [str(l.get('port', '')) for l in listeners]
        ports_display = ', '.join(ports)
        
        gw_type = 'Single'
        if len(listeners) > 1:
            gw_type = 'Multi'
        
        results.append({
            'name': name,
            'status': gw_status,
            'gateway_class': gw_class,
            'type': gw_type,
            'load_balancer': lb_name,
            'ip_addresses': ', '.join(ip_list),
            'namespace': namespace,
            'ports': ports_display,
            'revision_time': revision_time
        })
        
        status_color = get_status_color(gw_status)
        
        table.add_row(
            name,
            f"[{status_color}]{gw_status}[/]",
            gw_class,
            gw_type,
            lb_name,
            ip_display,
            namespace,
            ports_display,
            get_gateway_sre_status(gw_status)
        )
    
    console.print(table)
    
    healthy = sum(1 for r in results if r['status'] == 'Healthy')
    unhealthy = sum(1 for r in results if r['status'] == 'Unhealthy')
    other = len(results) - healthy - unhealthy
    
    summary = (
        f"[bold green]✅ HEALTHY: {healthy}[/]  "
        f"[bold red]🚨 UNHEALTHY: {unhealthy}[/]  "
        f"[dim]⏸️  OTHER: {other}[/]  "
        f"[dim]| Total: {len(results)}[/]"
    )
    console.print(Panel(summary, title="📊 Resumen Gateways", border_style="blue", expand=False))
    
    return results


def print_routes_table(console, routes, revision_time, debug=False):
    """Imprime tabla de HTTPRoutes"""
    table = Table(
        title="🛤️  HTTPRoutes",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Name", style="white")
    table.add_column("Namespace", justify="left")
    table.add_column("Hostnames", justify="left")
    table.add_column("Date Created", justify="center")
    table.add_column("Rules", justify="center")
    table.add_column("Attached Gateways", justify="left")
    table.add_column("Semáforo SRE", justify="left")
    
    results = []
    
    if not routes:
        console.print("[yellow]⚠️  No se detectaron HTTPRoutes.[/]")
        return results
    
    routes = sorted(routes, key=lambda x: x.get('metadata', {}).get('name', ''))
    
    for route in routes:
        metadata = route.get('metadata', {})
        spec = route.get('spec', {})
        status = route.get('status', {})
        
        name = metadata.get('name', 'N/A')
        namespace = metadata.get('namespace', 'N/A')
        creation = parse_creation_date(metadata.get('creationTimestamp', ''))
        
        hostnames = spec.get('hostnames', [])
        hostnames_display = ', '.join(hostnames[:2])
        if len(hostnames) > 2:
            hostnames_display += f" (+{len(hostnames) - 2})"
        
        rules = spec.get('rules', [])
        rules_count = len(rules)
        
        parent_refs = spec.get('parentRefs', [])
        attached_gateways = [p.get('name', '') for p in parent_refs]
        gateways_display = ', '.join(attached_gateways[:2])
        if len(attached_gateways) > 2:
            gateways_display += f" (+{len(attached_gateways) - 2})"
        
        has_gateway = len(attached_gateways) > 0
        
        results.append({
            'name': name,
            'namespace': namespace,
            'hostnames': ', '.join(hostnames),
            'date_created': creation,
            'rules_count': rules_count,
            'attached_gateways': ', '.join(attached_gateways),
            'has_gateway': has_gateway,
            'revision_time': revision_time
        })
        
        table.add_row(
            name,
            namespace,
            hostnames_display,
            creation,
            str(rules_count),
            gateways_display,
            get_route_sre_status(has_gateway, rules_count)
        )
    
    console.print(table)
    
    healthy = sum(1 for r in results if r['has_gateway'] and r['rules_count'] > 0)
    no_gateway = sum(1 for r in results if not r['has_gateway'])
    no_rules = sum(1 for r in results if r['has_gateway'] and r['rules_count'] == 0)
    
    summary = (
        f"[bold green]✅ HEALTHY: {healthy}[/]  "
        f"[bold red]🚨 NO GATEWAY: {no_gateway}[/]  "
        f"[bold yellow]⚠️  NO RULES: {no_rules}[/]  "
        f"[dim]| Total: {len(results)}[/]"
    )
    console.print(Panel(summary, title="📊 Resumen Routes", border_style="blue", expand=False))
    
    return results


def print_services_table(console, services, revision_time, debug=False, use_parallel=True, max_workers=4):
    """Imprime tabla de Services"""
    table = Table(
        title="🔌 Services",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Name", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Type", justify="center")
    table.add_column("Endpoints", justify="left")
    table.add_column("Pods", justify="center")
    table.add_column("Namespace", justify="left")
    table.add_column("Semáforo SRE", justify="left")
    
    results = []
    
    system_namespaces = ['kube-system', 'kube-public', 'kube-node-lease', 'gke-managed-system']
    filtered_services = [s for s in services if s.get('metadata', {}).get('namespace', '') not in system_namespaces]
    
    if not filtered_services:
        console.print("[yellow]⚠️  No se detectaron Services (excluyendo system).[/]")
        return results
    
    filtered_services = sorted(filtered_services, key=lambda x: x.get('metadata', {}).get('name', ''))
    
    endpoints_cache = {}
    if use_parallel and len(filtered_services) > 1:
        def fetch_endpoints(svc):
            name = svc.get('metadata', {}).get('name', 'N/A')
            namespace = svc.get('metadata', {}).get('namespace', 'N/A')
            pods_ready, pods_total = get_endpoints_count(svc, debug)
            return (f"{namespace}/{name}", (pods_ready, pods_total))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_endpoints, svc): svc for svc in filtered_services}
            for future in as_completed(futures):
                try:
                    key, value = future.result()
                    endpoints_cache[key] = value
                except Exception:
                    pass
    
    for svc in filtered_services:
        metadata = svc.get('metadata', {})
        spec = svc.get('spec', {})
        
        name = metadata.get('name', 'N/A')
        namespace = metadata.get('namespace', 'N/A')
        svc_type = spec.get('type', 'ClusterIP')
        
        cluster_ip = spec.get('clusterIP', 'N/A')
        if cluster_ip == 'None':
            cluster_ip = 'Headless'
        
        svc_status = get_service_status(svc)
        
        cache_key = f"{namespace}/{name}"
        if cache_key in endpoints_cache:
            pods_ready, pods_total = endpoints_cache[cache_key]
        else:
            pods_ready, pods_total = get_endpoints_count(svc, debug)
        pods_display = f"{pods_ready}/{pods_total}"
        
        results.append({
            'name': name,
            'status': svc_status,
            'type': svc_type,
            'endpoints': cluster_ip,
            'pods_ready': pods_ready,
            'pods_total': pods_total,
            'namespace': namespace,
            'revision_time': revision_time
        })
        
        status_color = get_status_color(svc_status)
        
        pods_color = 'green'
        if pods_total == 0:
            pods_color = 'red'
        elif pods_ready < pods_total:
            pods_color = 'yellow'
        
        table.add_row(
            name,
            f"[{status_color}]{svc_status}[/]",
            svc_type,
            cluster_ip,
            f"[{pods_color}]{pods_display}[/]",
            namespace,
            get_service_sre_status(svc_status, pods_ready, pods_total)
        )
    
    console.print(table)
    
    healthy = sum(1 for r in results if r['status'] == 'OK' and r['pods_ready'] == r['pods_total'] and r['pods_total'] > 0)
    degraded = sum(1 for r in results if r['status'] == 'OK' and r['pods_ready'] < r['pods_total'] and r['pods_total'] > 0)
    no_pods = sum(1 for r in results if r['pods_total'] == 0)
    pending = sum(1 for r in results if r['status'] != 'OK')
    
    summary = (
        f"[bold green]✅ HEALTHY: {healthy}[/]  "
        f"[bold yellow]⚠️  DEGRADED: {degraded}[/]  "
        f"[bold red]🚨 NO PODS: {no_pods}[/]  "
        f"[dim]⏸️  PENDING: {pending}[/]  "
        f"[dim]| Total: {len(results)}[/]"
    )
    console.print(Panel(summary, title="📊 Resumen Services", border_style="blue", expand=False))
    
    return results


def print_policies_table(console, policies, revision_time, debug=False):
    """Imprime tabla de Policies (HealthCheckPolicies y GCPBackendPolicies)"""
    table = Table(
        title="📋 Policies",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Name", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Kind", justify="center")
    table.add_column("Policy Type", justify="left")
    table.add_column("Target Kind", justify="center")
    table.add_column("Target Name", justify="left")
    table.add_column("Namespace", justify="left")
    table.add_column("Date Created", justify="center")
    table.add_column("Semáforo SRE", justify="left")
    
    results = []
    
    if not policies:
        console.print("[yellow]⚠️  No se detectaron Policies.[/]")
        return results
    
    policies = sorted(policies, key=lambda x: x.get('metadata', {}).get('name', ''))
    
    for policy in policies:
        metadata = policy.get('metadata', {})
        spec = policy.get('spec', {})
        
        name = metadata.get('name', 'N/A')
        namespace = metadata.get('namespace', 'N/A')
        kind = policy.get('kind', 'Unknown')
        creation = parse_creation_date(metadata.get('creationTimestamp', ''))
        
        policy_status = get_policy_status(policy)
        
        if kind == 'HealthCheckPolicy':
            policy_type = 'HTTP health check'
        elif kind == 'GCPBackendPolicy':
            policy_type = 'Backend service timeout'
        else:
            policy_type = kind
        
        target_ref = spec.get('targetRef', {})
        target_kind = target_ref.get('kind', 'N/A')
        target_name = target_ref.get('name', 'N/A')
        
        results.append({
            'name': name,
            'status': policy_status,
            'kind': kind,
            'policy_type': policy_type,
            'target_kind': target_kind,
            'target_name': target_name,
            'namespace': namespace,
            'date_created': creation,
            'revision_time': revision_time
        })
        
        status_color = get_status_color(policy_status)
        
        table.add_row(
            name,
            f"[{status_color}]{policy_status}[/]",
            kind,
            policy_type,
            target_kind,
            target_name,
            namespace,
            creation,
            get_policy_sre_status(policy_status)
        )
    
    console.print(table)
    
    attached = sum(1 for r in results if r['status'] == 'Attached')
    detached = sum(1 for r in results if r['status'] != 'Attached')
    
    summary = (
        f"[bold green]✅ ATTACHED: {attached}[/]  "
        f"[bold red]🚨 DETACHED: {detached}[/]  "
        f"[dim]| Total: {len(results)}[/]"
    )
    console.print(Panel(summary, title="📊 Resumen Policies", border_style="blue", expand=False))
    
    return results


def fetch_all_resources_parallel(namespace, view, debug=False, max_workers=4):
    """Obtiene todos los recursos en paralelo"""
    resources = {
        'gateways': [],
        'routes': [],
        'services': [],
        'health_policies': [],
        'backend_policies': []
    }
    
    tasks = []
    if view in ['all', 'gateways']:
        tasks.append(('gateways', get_gateways, [namespace, debug]))
    if view in ['all', 'routes']:
        tasks.append(('routes', get_httproutes, [namespace, debug]))
    if view in ['all', 'services']:
        tasks.append(('services', get_services, [namespace, debug]))
    if view in ['all', 'policies']:
        tasks.append(('health_policies', get_healthcheckpolicies, [namespace, debug]))
        tasks.append(('backend_policies', get_gcpbackendpolicies, [namespace, debug]))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for key, func, args in tasks:
            futures[executor.submit(func, *args)] = key
        
        for future in as_completed(futures):
            key = futures[future]
            try:
                resources[key] = future.result() or []
            except Exception:
                resources[key] = []
    
    return resources


def scan_cluster_resources(console, cluster_name, namespace, view, revision_time, debug=False, use_parallel=True, max_workers=4):
    """Escanea los recursos de Gateway API en un cluster específico"""
    results = {
        'gateways': [],
        'routes': [],
        'services': [],
        'policies': []
    }
    
    with print_lock:
        console.print(f"\n[bold magenta]☸️  Cluster: {cluster_name}[/]")
        console.print(f"[dim]{'─' * 60}[/]")
    
    if use_parallel:
        resources = fetch_all_resources_parallel(namespace, view, debug, max_workers)
        gateways = resources['gateways']
        routes = resources['routes']
        services = resources['services']
        all_policies = resources['health_policies'] + resources['backend_policies']
    else:
        gateways = get_gateways(namespace, debug) if view in ['all', 'gateways'] else []
        routes = get_httproutes(namespace, debug) if view in ['all', 'routes'] else []
        services = get_services(namespace, debug) if view in ['all', 'services'] else []
        health_policies = get_healthcheckpolicies(namespace, debug) if view in ['all', 'policies'] else []
        backend_policies = get_gcpbackendpolicies(namespace, debug) if view in ['all', 'policies'] else []
        all_policies = health_policies + backend_policies
    
    with print_lock:
        if view in ['all', 'gateways']:
            console.print("[bold cyan]═══ GATEWAYS ═══[/]\n")
            gw_results = print_gateways_table(console, gateways, revision_time, debug)
            for r in gw_results:
                r['cluster'] = cluster_name
            results['gateways'] = gw_results
            console.print()
        
        if view in ['all', 'routes']:
            console.print("[bold cyan]═══ ROUTES ═══[/]\n")
            rt_results = print_routes_table(console, routes, revision_time, debug)
            for r in rt_results:
                r['cluster'] = cluster_name
            results['routes'] = rt_results
            console.print()
        
        if view in ['all', 'services']:
            console.print("[bold cyan]═══ SERVICES ═══[/]\n")
            svc_results = print_services_table(console, services, revision_time, debug, use_parallel, max_workers)
            for r in svc_results:
                r['cluster'] = cluster_name
            results['services'] = svc_results
            console.print()
        
        if view in ['all', 'policies']:
            console.print("[bold cyan]═══ POLICIES ═══[/]\n")
            pol_results = print_policies_table(console, all_policies, revision_time, debug)
            for r in pol_results:
                r['cluster'] = cluster_name
            results['policies'] = pol_results
            console.print()
    
    return results


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


def create_progress_table(clusters_status):
    """Crea tabla de progreso dinámica para clusters"""
    table = Table(title="⚡ Progreso de Escaneo", box=None, expand=False)
    table.add_column("Cluster", style="cyan", no_wrap=True)
    table.add_column("Estado", justify="center")
    table.add_column("Recursos", justify="right")
    
    for cluster_name, status_info in clusters_status.items():
        status = status_info.get('status', 'pending')
        resources = status_info.get('resources', 0)
        
        if status == 'connecting':
            status_display = Text("🔌 Conectando...", style="yellow")
        elif status == 'scanning':
            status_display = Text("🔍 Escaneando...", style="blue")
        elif status == 'done':
            status_display = Text("✅ Completado", style="green")
        elif status == 'error':
            status_display = Text("❌ Error", style="red")
        else:
            status_display = Text("⏳ Pendiente", style="dim")
        
        resources_str = str(resources) if resources > 0 else "-"
        table.add_row(cluster_name, status_display, resources_str)
    
    return table


def main():
    start_time = time.time()
    args = get_args()
    
    if args.help:
        show_help()
        return
    
    console = Console()
    project_id = args.project
    tz_name = args.timezone

    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        console.print(f"[red]⚠️ Zona horaria inválida: {tz_name}. Usando America/Mazatlan[/]")
        tz_name = "America/Mazatlan"
        tz = ZoneInfo(tz_name)

    revision_time = datetime.now(tz).strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})')
    
    use_parallel = args.parallel and not args.no_parallel
    max_workers = args.max_workers
    
    console.print(f"\n[bold blue]🌐 Iniciando escaneo de Gateway Services[/]")
    console.print(f"[dim]📦 Proyecto: {project_id}[/]")
    console.print(f"[dim]🕐 Fecha y hora de revisión: {revision_time}[/]")
    console.print(f"[dim]⚡ Modo paralelo (recursos): {'Sí' if use_parallel else 'No'} (max_workers: {max_workers})[/]")
    
    if not check_gcp_connection(project_id, console, args.debug):
        print_execution_time(start_time, console, tz_name)
        return

    console.print()
    
    namespace = args.namespace
    view = args.view
    
    all_results = {
        'gateways': [],
        'routes': [],
        'services': [],
        'policies': []
    }
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Recolectando clusters y gateways...", total=None)
            clusters = get_clusters(project_id, args.debug)
        
        if not clusters:
            console.print(f"[yellow]⚠️  No se detectaron clusters GKE en {project_id}.[/]")
            return
        
        if args.cluster:
            clusters = [c for c in clusters if c.get('name') == args.cluster]
            if not clusters:
                console.print(f"[red]❌ Cluster '{args.cluster}' no encontrado en el proyecto {project_id}.[/]")
                return
            console.print(f"[dim]🎯 Filtrando por cluster: {args.cluster}[/]")
        else:
            console.print(f"[dim]☸️  Clusters detectados: {len(clusters)}[/]")
        
        clusters_status = {c.get('name', 'unknown'): {'status': 'pending', 'resources': 0} for c in clusters}
        
        def process_cluster_with_status(cluster, live):
            """Procesa un cluster individual con actualización de estado"""
            cluster_name = cluster.get('name', 'unknown')
            location = cluster.get('location', '')
            
            clusters_status[cluster_name]['status'] = 'connecting'
            live.update(create_progress_table(clusters_status))
            
            if not get_cluster_credentials(project_id, cluster_name, location, args.debug):
                clusters_status[cluster_name]['status'] = 'error'
                live.update(create_progress_table(clusters_status))
                return None
            
            clusters_status[cluster_name]['status'] = 'scanning'
            live.update(create_progress_table(clusters_status))
            
            result = scan_cluster_resources(
                console, cluster_name, namespace, view, revision_time, args.debug, use_parallel, max_workers
            )
            
            if result:
                total_resources = sum(len(v) for v in result.values())
                clusters_status[cluster_name]['resources'] = total_resources
            
            clusters_status[cluster_name]['status'] = 'done'
            live.update(create_progress_table(clusters_status))
            return result
        
        with Live(create_progress_table(clusters_status), console=console, refresh_per_second=4, transient=True) as live:
            for cluster in clusters:
                cluster_results = process_cluster_with_status(cluster, live)
                if cluster_results:
                    for key in all_results:
                        all_results[key].extend(cluster_results[key])
        
        if args.output:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            outcome_dir = os.path.join(script_dir, 'outcome')
            os.makedirs(outcome_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            cluster_suffix = f"_{args.cluster}" if args.cluster else ""
            
            for resource_type, data in all_results.items():
                if data:
                    filename = f"gateway_{resource_type}{cluster_suffix}_{timestamp}"
                    
                    if args.output == 'csv':
                        filepath = os.path.join(outcome_dir, f"{filename}.csv")
                        export_to_csv(data, filepath)
                        console.print(f"[bold green]📁 Exportado:[/] {filepath}")
                    elif args.output == 'json':
                        filepath = os.path.join(outcome_dir, f"{filename}.json")
                        export_to_json(data, filepath, project_id, tz_name)
                        console.print(f"[bold green]📁 Exportado:[/] {filepath}")
        
        console.print(f"\n[dim]Tip: Usa --cluster para filtrar por un cluster específico.[/]\n")
    
    except Exception as e:
        console.print(f"[bold red]❌ Error ejecutando comando:[/]\n{e}")

    print_execution_time(start_time, console, tz_name)


if __name__ == "__main__":
    main()
