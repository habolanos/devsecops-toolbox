import argparse
import subprocess
import json
import csv
import urllib.parse
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Version
__version__ = "2.3.0"

# Lock para escritura thread-safe
_print_lock = Lock()

_token_cache = None

def get_args():
    parser = argparse.ArgumentParser(description="SRE Tool: GKE Cluster Monitoring (gcloud)", add_help=False)
    parser.add_argument(
        "--project",
        type=str,
        default="cpl-xxxx-yyyy-zzzz-99999999",
        help="ID del proyecto de GCP (Default: cpl-xxxx-yyyy-zzzz-99999999)"
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
        help="Ejecuta procesamiento de clusters en paralelo (default: True)"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Desactiva procesamiento en paralelo"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Número máximo de workers para procesamiento paralelo (default: 4)"
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

def get_clusters(project_id, debug=False):
    """Obtiene lista de clusters GKE usando gcloud"""
    cmd = f'gcloud container clusters list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug) or []

def get_access_token():
    """Obtiene el token de acceso de gcloud con caché"""
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

def get_cluster_metric(project_id, cluster_name, metric_type, debug=False):
    """Consulta Cloud Monitoring API para obtener métricas del cluster"""
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    filter_str = (
        f'metric.type="kubernetes.io/container/{metric_type}" '
        f'AND resource.labels.cluster_name="{cluster_name}"'
    )
    encoded_filter = urllib.parse.quote(filter_str)
    
    token = get_access_token()
    if not token:
        return None
    
    url = (
        f'https://monitoring.googleapis.com/v3/projects/{project_id}/timeSeries'
        f'?filter={encoded_filter}'
        f'&interval.startTime={start_time}'
        f'&interval.endTime={end_time}'
        f'&aggregation.alignmentPeriod=300s'
        f'&aggregation.perSeriesAligner=ALIGN_MEAN'
        f'&aggregation.crossSeriesReducer=REDUCE_MEAN'
        f'&aggregation.groupByFields=resource.labels.cluster_name'
    )
    
    cmd = f'curl -s -H "Authorization: Bearer {token}" "{url}"'
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if debug:
            print(f"[DEBUG] Metric {metric_type}: {result.returncode}")
        
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
            print(f"[DEBUG] Metric Exception: {e}")
    return None

def get_cluster_metric_raw(project_id, cluster_name, metric_type, debug=False):
    """Consulta Cloud Monitoring API para obtener métricas absolutas (sin multiplicar por 100)"""
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    filter_str = (
        f'metric.type="kubernetes.io/container/{metric_type}" '
        f'AND resource.labels.cluster_name="{cluster_name}"'
    )
    encoded_filter = urllib.parse.quote(filter_str)
    
    token = get_access_token()
    if not token:
        return None
    
    url = (
        f'https://monitoring.googleapis.com/v3/projects/{project_id}/timeSeries'
        f'?filter={encoded_filter}'
        f'&interval.startTime={start_time}'
        f'&interval.endTime={end_time}'
        f'&aggregation.alignmentPeriod=300s'
        f'&aggregation.perSeriesAligner=ALIGN_MEAN'
        f'&aggregation.crossSeriesReducer=REDUCE_SUM'
        f'&aggregation.groupByFields=resource.labels.cluster_name'
    )
    
    cmd = f'curl -s -H "Authorization: Bearer {token}" "{url}"'
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if debug:
            print(f"[DEBUG] Metric raw {metric_type}: {result.returncode}")
        
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            time_series = data.get('timeSeries', [])
            if time_series and len(time_series) > 0:
                points = time_series[0].get('points', [])
                if points:
                    value = points[0].get('value', {})
                    return float(value.get('doubleValue', 0.0) or value.get('int64Value', 0))
    except Exception as e:
        if debug:
            print(f"[DEBUG] Metric raw Exception: {e}")
    return None

def format_bytes(bytes_val):
    """Convierte bytes a la escala apropiada (KB, MB, GB, TB)"""
    if bytes_val is None:
        return 'N/A'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def format_cpu_cores(cores):
    """Formatea CPU cores"""
    if cores is None:
        return 'N/A'
    if cores >= 1:
        return f"{cores:.2f} cores"
    return f"{cores*1000:.0f} mCores"

def get_cluster_utilization(project_id, cluster_name, debug=False):
    """Obtiene todas las métricas de utilización del cluster"""
    metrics = {
        'cpu_request_util': get_cluster_metric(project_id, cluster_name, 'cpu/request_utilization', debug),
        'cpu_limit_util': get_cluster_metric(project_id, cluster_name, 'cpu/limit_utilization', debug),
        'memory_request_util': get_cluster_metric(project_id, cluster_name, 'memory/request_utilization', debug),
        'memory_limit_util': get_cluster_metric(project_id, cluster_name, 'memory/limit_utilization', debug),
        'cpu_request_cores': get_cluster_metric_raw(project_id, cluster_name, 'cpu/request_cores', debug),
        'cpu_limit_cores': get_cluster_metric_raw(project_id, cluster_name, 'cpu/limit_cores', debug),
        'memory_request_bytes': get_cluster_metric_raw(project_id, cluster_name, 'memory/request_bytes', debug),
        'memory_limit_bytes': get_cluster_metric_raw(project_id, cluster_name, 'memory/limit_bytes', debug),
    }
    return metrics

def get_pod_count(project_id, cluster_name, location, debug=False):
    """Obtiene el conteo de pods running y not running del cluster"""
    location_flag = f'--zone={location}' if location.count('-') == 2 else f'--region={location}'
    
    # El contexto generado por gcloud tiene formato: gke_PROJECT_LOCATION_CLUSTER
    context_name = f'gke_{project_id}_{location}_{cluster_name}'
    
    try:
        # Obtener credenciales del cluster
        get_creds = f'gcloud container clusters get-credentials {cluster_name} --project={project_id} {location_flag} --quiet 2>/dev/null'
        creds_result = subprocess.run(get_creds, shell=True, capture_output=True, text=True)
        
        if debug:
            print(f"[DEBUG] get-credentials returncode: {creds_result.returncode}")
            if creds_result.stderr:
                print(f"[DEBUG] get-credentials stderr: {creds_result.stderr[:200]}")
        
        # Usar JSON output para contar pods (más confiable que wc -l)
        cmd_all_pods = f'kubectl --context={context_name} get pods --all-namespaces -o json 2>/dev/null'
        result = subprocess.run(cmd_all_pods, shell=True, capture_output=True, text=True)
        
        if debug:
            print(f"[DEBUG] kubectl get pods returncode: {result.returncode}, stdout length: {len(result.stdout)}")
        
        running = 0
        not_running = 0
        
        if result.returncode == 0 and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                items = data.get('items', [])
                for pod in items:
                    phase = pod.get('status', {}).get('phase', 'Unknown')
                    if phase == 'Running':
                        running += 1
                    else:
                        not_running += 1
                
                if debug:
                    print(f"[DEBUG] Pods {cluster_name}: total={len(items)}, running={running}, not_running={not_running}")
            except json.JSONDecodeError as je:
                if debug:
                    print(f"[DEBUG] JSON decode error: {je}")
        else:
            if debug:
                print(f"[DEBUG] kubectl failed or empty output for {cluster_name}")
        
        return running, not_running
    except Exception as e:
        if debug:
            print(f"[DEBUG] Pod count error: {e}")
        return None, None

def get_not_running_pods_detail(project_id, cluster_name, location, debug=False):
    """Obtiene detalle de pods que no están en estado Running"""
    location_flag = f'--zone={location}' if location.count('-') == 2 else f'--region={location}'
    pods_detail = []
    
    context_name = f'gke_{project_id}_{location}_{cluster_name}'
    
    try:
        get_creds = f'gcloud container clusters get-credentials {cluster_name} --project={project_id} {location_flag} --quiet 2>/dev/null'
        subprocess.run(get_creds, shell=True, capture_output=True, text=True)
        
        cmd = f"kubectl --context={context_name} get pods --all-namespaces --field-selector=status.phase!=Running -o json 2>/dev/null"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            items = data.get('items', [])
            
            for pod in items:
                namespace = pod.get('metadata', {}).get('namespace', 'N/A')
                pod_name = pod.get('metadata', {}).get('name', 'N/A')
                phase = pod.get('status', {}).get('phase', 'Unknown')
                
                owner_refs = pod.get('metadata', {}).get('ownerReferences', [])
                owner_kind = owner_refs[0].get('kind', 'N/A') if owner_refs else 'N/A'
                owner_name = owner_refs[0].get('name', 'N/A') if owner_refs else 'N/A'
                
                container_statuses = pod.get('status', {}).get('containerStatuses', [])
                reason = 'N/A'
                if container_statuses:
                    waiting = container_statuses[0].get('state', {}).get('waiting', {})
                    reason = waiting.get('reason', phase)
                else:
                    conditions = pod.get('status', {}).get('conditions', [])
                    for cond in conditions:
                        if cond.get('status') == 'False':
                            reason = cond.get('reason', phase)
                            break
                    if reason == 'N/A':
                        reason = phase
                
                pods_detail.append({
                    'cluster': cluster_name,
                    'namespace': namespace,
                    'owner_kind': owner_kind,
                    'owner_name': owner_name,
                    'pod': pod_name,
                    'phase': phase,
                    'reason': reason
                })
        
        if debug:
            print(f"[DEBUG] Not running pods in {cluster_name}: {len(pods_detail)}")
        
        return pods_detail
    except Exception as e:
        if debug:
            print(f"[DEBUG] Not running pods detail error: {e}")
        return []

def parse_cluster_name(full_name):
    """Extrae el nombre corto del cluster desde el path completo"""
    if full_name and '/' in full_name:
        return full_name.split('/')[-1]
    return full_name or 'UNKNOWN'

def get_version_status(current_version, release_channel):
    """Determina el estado de la versión del cluster"""
    if not current_version:
        return "UNKNOWN"
    
    version_parts = current_version.split('.')
    if len(version_parts) >= 2:
        minor_version = int(version_parts[1]) if version_parts[1].isdigit() else 0
        if minor_version < 27:
            return "OUTDATED"
        elif minor_version < 29:
            return "UPDATE_AVAILABLE"
    
    if release_channel and release_channel.get('channel') == 'UNSPECIFIED':
        return "NO_CHANNEL"
    
    return "CURRENT"

def get_status_summary(cluster_status, version_status, autopilot):
    """Lógica de Semáforo SRE para Clusters GKE"""
    if cluster_status != 'RUNNING':
        return "[bold white on red] NOT RUNNING [/]"
    if version_status == 'OUTDATED':
        return "[bold white on red] OUTDATED [/]"
    if version_status == 'UPDATE_AVAILABLE':
        return "[bold black on yellow] UPDATE [/]"
    if version_status == 'NO_CHANNEL':
        return "[bold cyan] NO CHANNEL [/]"
    if autopilot:
        return "[bold green] AUTOPILOT ✨ [/]"
    return "[bold green] HEALTHY [/]"

def get_status_text(cluster_status, version_status, autopilot):
    """Retorna el estado en texto plano para exportación"""
    if cluster_status != 'RUNNING':
        return "NOT_RUNNING"
    if version_status == 'OUTDATED':
        return "OUTDATED"
    if version_status == 'UPDATE_AVAILABLE':
        return "UPDATE_AVAILABLE"
    if version_status == 'NO_CHANNEL':
        return "NO_CHANNEL"
    if autopilot:
        return "AUTOPILOT"
    return "HEALTHY"

def process_cluster(cluster, project_id, revision_time, debug=False):
    """Procesa un cluster completo y retorna sus datos (thread-safe)"""
    cluster_name = cluster.get('name', 'UNKNOWN')
    location = cluster.get('location', 'N/A')
    
    is_autopilot = cluster.get('autopilot', {}).get('enabled', False)
    mode = 'AUTOPILOT' if is_autopilot else 'STANDARD'
    
    current_version = cluster.get('currentMasterVersion', 'N/A')
    node_count = cluster.get('currentNodeCount', 0)
    cluster_status = cluster.get('status', 'UNKNOWN')
    
    release_channel = cluster.get('releaseChannel', {})
    channel_name = release_channel.get('channel', 'UNSPECIFIED') if release_channel else 'UNSPECIFIED'
    
    version_status = get_version_status(current_version, release_channel)
    status = get_status_text(cluster_status, version_status, is_autopilot)
    
    metrics = get_cluster_utilization(project_id, cluster_name, debug)
    cpu_req_pct = metrics.get('cpu_request_util')
    mem_req_pct = metrics.get('memory_request_util')
    cpu_req_cores = metrics.get('cpu_request_cores')
    mem_req_bytes = metrics.get('memory_request_bytes')
    
    pods_running, pods_not_running = get_pod_count(project_id, cluster_name, location, debug)
    
    not_running_pods_detail = []
    if pods_not_running and pods_not_running > 0:
        not_running_pods_detail = get_not_running_pods_detail(project_id, cluster_name, location, debug)
    
    return {
        'cluster_obj': cluster,
        'project': project_id,
        'cluster': cluster_name,
        'location': location,
        'mode': mode,
        'version': current_version,
        'node_count': node_count,
        'pods_running': pods_running if pods_running is not None else 'N/A',
        'pods_not_running': pods_not_running if pods_not_running is not None else 'N/A',
        'cpu_request': format_cpu_cores(cpu_req_cores),
        'cpu_request_util': round(cpu_req_pct, 2) if cpu_req_pct else 'N/A',
        'memory_request': format_bytes(mem_req_bytes),
        'memory_request_util': round(mem_req_pct, 2) if mem_req_pct else 'N/A',
        'cluster_status': cluster_status,
        'release_channel': channel_name,
        'status': status,
        'revision_time': revision_time,
        'is_autopilot': is_autopilot,
        'version_status': version_status,
        'cpu_req_pct': cpu_req_pct,
        'mem_req_pct': mem_req_pct,
        'cpu_req_cores': cpu_req_cores,
        'mem_req_bytes': mem_req_bytes,
        'not_running_pods_detail': not_running_pods_detail
    }

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
            "tool_name": "GCP GKE Cluster Checker",
            "version": __version__,
            "project_id": project_id,
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "total_clusters": len(data),
            "not_running": sum(1 for r in data if r.get('status') == 'NOT_RUNNING'),
            "outdated": sum(1 for r in data if r.get('status') == 'OUTDATED'),
            "update_available": sum(1 for r in data if r.get('status') == 'UPDATE_AVAILABLE'),
            "no_channel": sum(1 for r in data if r.get('status') == 'NO_CHANNEL'),
            "healthy": sum(1 for r in data if r.get('status') in ['HEALTHY', 'AUTOPILOT'])
        },
        "clusters": data
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

def print_summary(console, results):
    """Imprime resumen ejecutivo con conteo de estados"""
    not_running = sum(1 for r in results if r['status'] == 'NOT_RUNNING')
    outdated = sum(1 for r in results if r['status'] == 'OUTDATED')
    update_available = sum(1 for r in results if r['status'] == 'UPDATE_AVAILABLE')
    no_channel = sum(1 for r in results if r['status'] == 'NO_CHANNEL')
    healthy = sum(1 for r in results if r['status'] in ['HEALTHY', 'AUTOPILOT'])
    total = len(results)
    
    summary_text = (
        f"[bold red]🚨 NOT RUNNING: {not_running}[/]  "
        f"[bold red]⏰ OUTDATED: {outdated}[/]  "
        f"[bold yellow]⚠️  UPDATE: {update_available}[/]  "
        f"[bold cyan]📢 NO CHANNEL: {no_channel}[/]  "
        f"[bold green]✅ HEALTHY: {healthy}[/]  "
        f"[dim]| Total: {total}[/]"
    )
    
    console.print(Panel(summary_text, title="📊 Resumen Ejecutivo", border_style="blue", expand=False))

def print_not_running_pods_table(console, all_pods_detail):
    """Imprime tabla con detalle de pods que no están corriendo"""
    if not all_pods_detail:
        return
    
    table = Table(
        title="🚨 Pods No Running",
        title_style="bold red",
        header_style="bold cyan",
        border_style="red"
    )
    
    table.add_column("Cluster", style="white")
    table.add_column("Namespace", style="cyan")
    table.add_column("Owner", style="yellow")
    table.add_column("Pod", style="white")
    table.add_column("Phase", justify="center")
    table.add_column("Reason", style="red")
    
    for pod in all_pods_detail:
        phase = pod.get('phase', 'Unknown')
        phase_style = "[red]" if phase in ['Failed', 'Unknown'] else "[yellow]"
        
        owner = f"{pod.get('owner_kind', 'N/A')}/{pod.get('owner_name', 'N/A')}"
        if len(owner) > 40:
            owner = owner[:37] + "..."
        
        pod_name = pod.get('pod', 'N/A')
        if len(pod_name) > 50:
            pod_name = pod_name[:47] + "..."
        
        table.add_row(
            pod.get('cluster', 'N/A'),
            pod.get('namespace', 'N/A'),
            owner,
            pod_name,
            f"{phase_style}{phase}[/]",
            pod.get('reason', 'N/A')
        )
    
    console.print(f"\n")
    console.print(table)
    console.print(f"[dim]Total pods no running: {len(all_pods_detail)}[/]")

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
    console.print(f"\n[bold blue]☸️  Iniciando escaneo de Clusters GKE en:[/] [white underline]{project_id}[/]")
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
            task = progress.add_task("Recolectando clusters GKE...", total=None)
            clusters = get_clusters(project_id, args.debug)
        
        table = Table(
            title=f"☸️  GKE Clusters: {project_id}",
            title_style="bold magenta",
            header_style="bold cyan",
            border_style="dim"
        )
        
        table.add_column("Cluster", style="white")
        table.add_column("Ubicación", justify="center")
        table.add_column("Modo", justify="center")
        table.add_column("Nodos", justify="right")
        table.add_column("Pods", justify="center")
        table.add_column("CPU Req", justify="right")
        table.add_column("CPU Req%", justify="right")
        table.add_column("Mem Req", justify="right")
        table.add_column("Mem Req%", justify="right")
        table.add_column("Estado", justify="center")
        table.add_column("Semáforo SRE", justify="left")

        results = []

        if not clusters:
            console.print(f"[yellow]⚠️  No se detectaron clusters GKE en {project_id}.[/]")
        else:
            clusters = sorted(clusters, key=lambda x: x.get('name', ''))
            total_clusters = len(clusters)
            
            def format_metric(val):
                if val is None:
                    return "[dim]N/A[/]"
                if val >= 80:
                    return f"[red]{val:.1f}[/]"
                elif val >= 60:
                    return f"[yellow]{val:.1f}[/]"
                return f"[green]{val:.1f}[/]"

            def format_pods(running, not_running):
                if running is None:
                    return "[dim]N/A[/]"
                if not_running and not_running > 0:
                    return f"[green]{running}[/]/[red]{not_running}[/]"
                return f"[green]{running}[/]/0"

            def format_resource(val):
                if val is None or val == 'N/A':
                    return "[dim]N/A[/]"
                return f"[cyan]{val}[/]"
            
            if use_parallel and total_clusters > 1:
                console.print(f"[cyan]⚡ Procesando {total_clusters} clusters en paralelo...[/]")
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(process_cluster, cluster, project_id, revision_time, args.debug): cluster
                        for cluster in clusters
                    }
                    
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            results.append(result)
                        except Exception as e:
                            if args.debug:
                                console.print(f"[red]Error procesando cluster: {e}[/]")
                
                results = sorted(results, key=lambda x: x.get('cluster', ''))
            else:
                for idx, cluster in enumerate(clusters, 1):
                    console.print(f"[dim]Procesando [{idx}/{total_clusters}]: {cluster.get('name', 'UNKNOWN')}...[/]")
                    result = process_cluster(cluster, project_id, revision_time, args.debug)
                    results.append(result)
            
            for r in results:
                cluster_name = r['cluster']
                location = r['location']
                node_count = r['node_count']
                is_autopilot = r['is_autopilot']
                cluster_status = r['cluster_status']
                version_status = r['version_status']
                cpu_req_pct = r['cpu_req_pct']
                mem_req_pct = r['mem_req_pct']
                cpu_req_cores = r['cpu_req_cores']
                mem_req_bytes = r['mem_req_bytes']
                pods_running = r['pods_running']
                pods_not_running = r['pods_not_running']
                
                row_style = ""
                if cluster_status != 'RUNNING':
                    row_style = "red"
                elif version_status == 'OUTDATED':
                    row_style = "red"
                elif version_status == 'UPDATE_AVAILABLE':
                    row_style = "yellow"

                mode_display = "[magenta]AUTOPILOT[/]" if is_autopilot else "STANDARD"
                status_display = f"[green]{cluster_status}[/]" if cluster_status == 'RUNNING' else f"[red]{cluster_status}[/]"

                table.add_row(
                    cluster_name,
                    location,
                    mode_display,
                    str(node_count),
                    format_pods(pods_running if pods_running != 'N/A' else None, 
                               pods_not_running if pods_not_running != 'N/A' else None),
                    format_resource(format_cpu_cores(cpu_req_cores)),
                    format_metric(cpu_req_pct),
                    format_resource(format_bytes(mem_req_bytes)),
                    format_metric(mem_req_pct),
                    status_display,
                    get_status_summary(cluster_status, version_status, is_autopilot),
                    style=row_style
                )
            
            console.print(table)
            
            export_results = [{k: v for k, v in r.items() 
                             if k not in ['cluster_obj', 'is_autopilot', 'version_status', 
                                         'cpu_req_pct', 'mem_req_pct', 'cpu_req_cores', 'mem_req_bytes',
                                         'not_running_pods_detail']} 
                            for r in results]
            print_summary(console, export_results)
            
            all_not_running_pods = []
            for r in results:
                all_not_running_pods.extend(r.get('not_running_pods_detail', []))
            
            if all_not_running_pods:
                print_not_running_pods_table(console, all_not_running_pods)
            
            if args.output and export_results:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                outcome_dir = os.path.join(script_dir, 'outcome')
                os.makedirs(outcome_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"gke_check_{project_id}_{timestamp}"
                
                if args.output == 'csv':
                    filepath = os.path.join(outcome_dir, f"{filename}.csv")
                    export_to_csv(export_results, filepath)
                elif args.output == 'json':
                    filepath = os.path.join(outcome_dir, f"{filename}.json")
                    export_to_json(export_results, filepath, project_id, tz_name)
                
                console.print(f"\n[bold green]📁 Archivo exportado:[/] {filepath}")
            
            console.print(f"\n[dim]Tip: Mantén tus clusters en un Release Channel para actualizaciones automáticas.[/]\n")

    except Exception as e:
        console.print(f"[bold red]❌ Error ejecutando gcloud:[/]\n{e}")
    
    print_execution_time(start_time, console, tz_name)

if __name__ == "__main__":
    main()
