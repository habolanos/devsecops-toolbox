#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Load Balancer Checker

Herramienta SRE para monitorear y analizar Load Balancers en Google Cloud Platform.
Muestra información detallada de:
- HTTP(S) Load Balancers (Global y Regional)
- TCP/UDP Load Balancers
- Internal Load Balancers
- Network Load Balancers
- Backend Services y Health Checks
- URL Maps y Target Proxies
- Forwarding Rules
- SSL Certificates asociados

Autor: Harold Adrian
"""

import subprocess
import json
import argparse
import sys
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.live import Live
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"


def get_args():
    parser = argparse.ArgumentParser(
        description="SRE Tool: GCP Load Balancer Checker",
        add_help=False
    )
    parser.add_argument(
        "--project", "-p",
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
    parser.add_argument(
        "--timezone", "-tz",
        type=str,
        default="America/Mazatlan",
        help="Timezone para mostrar timestamps (default: America/Mazatlan)"
    )
    parser.add_argument(
        "--view", "-v",
        type=str,
        choices=["all", "forwarding", "backends", "urlmaps", "healthchecks", "ssl"],
        default="all",
        help="Vista específica a mostrar (default: all)"
    )
    return parser.parse_args()


def show_help(console):
    """Muestra la documentación completa del script leyendo el README.md."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(script_dir, "README.md")
    
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        from rich.markdown import Markdown
        md = Markdown(readme_content)
        console.print(md)
    except FileNotFoundError:
        console.print(f"[red]❌ No se encontró el archivo README.md en {script_dir}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error leyendo README.md: {e}[/red]")


def check_gcp_connection(project_id: str, console, debug: bool = False) -> bool:
    """
    Verifica la conexión a GCP antes de ejecutar el script.
    
    Args:
        project_id: ID del proyecto GCP
        console: Consola Rich para output
        debug: Modo debug
    
    Returns:
        True si la conexión es válida, False en caso contrario
    """
    try:
        # Verificar sesión activa de gcloud
        auth_cmd = 'gcloud auth list --filter=status:ACTIVE --format="value(account)"'
        if debug:
            console.print(f"[dim]DEBUG: {auth_cmd}[/dim]")
        
        auth_result = subprocess.run(auth_cmd, shell=True, capture_output=True, text=True)
        
        if auth_result.returncode != 0 or not auth_result.stdout.strip():
            console.print("[red]❌ No hay sesión activa de gcloud. Ejecuta: gcloud auth login[/]")
            return False
        
        active_account = auth_result.stdout.strip().split('\n')[0]
        console.print(f"[green]✓[/green] Sesión activa: [cyan]{active_account}[/cyan]")
        
        # Verificar acceso al proyecto
        project_cmd = f'gcloud projects describe {project_id} --format="value(projectId)" 2>&1'
        if debug:
            console.print(f"[dim]DEBUG: {project_cmd}[/dim]")
        
        project_result = subprocess.run(project_cmd, shell=True, capture_output=True, text=True)
        
        if project_result.returncode != 0:
            error_msg = project_result.stdout.strip() or project_result.stderr.strip()
            console.print(f"[red]❌ No tienes acceso al proyecto: {project_id}[/]")
            if debug:
                console.print(f"[dim]Error: {error_msg}[/dim]")
            return False
        
        console.print(f"[green]✓[/green] Proyecto accesible: [cyan]{project_id}[/cyan]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Error verificando conexión: {e}[/]")
        return False


def run_gcloud_command(cmd: str, debug: bool = False, console=None) -> Optional[List[Dict]]:
    """Ejecuta un comando gcloud y retorna el resultado como JSON."""
    try:
        if debug and console:
            console.print(f"[dim]DEBUG: {cmd}[/dim]")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            if debug and console:
                console.print(f"[dim]Error: {result.stderr}[/dim]")
            return None
        
        if not result.stdout.strip():
            return []
        
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    except Exception as e:
        if debug and console:
            console.print(f"[dim]Exception: {e}[/dim]")
        return None


def get_forwarding_rules_global(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene forwarding rules globales."""
    cmd = f'gcloud compute forwarding-rules list --global --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console)
    return result if result else []


def get_forwarding_rules_regional(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene forwarding rules regionales."""
    cmd = f'gcloud compute forwarding-rules list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console)
    # Filtrar solo las regionales (las que tienen region)
    return [r for r in (result or []) if 'region' in r]


def get_target_http_proxies(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene target HTTP proxies."""
    cmd = f'gcloud compute target-http-proxies list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_target_https_proxies(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene target HTTPS proxies."""
    cmd = f'gcloud compute target-https-proxies list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_target_tcp_proxies(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene target TCP proxies."""
    cmd = f'gcloud compute target-tcp-proxies list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_target_ssl_proxies(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene target SSL proxies."""
    cmd = f'gcloud compute target-ssl-proxies list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_url_maps(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene URL maps."""
    cmd = f'gcloud compute url-maps list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_backend_services_global(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene backend services globales."""
    cmd = f'gcloud compute backend-services list --global --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_backend_services_regional(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene backend services regionales."""
    cmd = f'gcloud compute backend-services list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug, console) or []
    return [r for r in result if 'region' in r]


def get_backend_buckets(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene backend buckets."""
    cmd = f'gcloud compute backend-buckets list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_health_checks(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene health checks."""
    cmd = f'gcloud compute health-checks list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_ssl_certificates(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene SSL certificates."""
    cmd = f'gcloud compute ssl-certificates list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_ssl_policies(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene SSL policies."""
    cmd = f'gcloud compute ssl-policies list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_target_pools(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene target pools (Network LB)."""
    cmd = f'gcloud compute target-pools list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def get_target_instances(project_id: str, debug: bool, console) -> List[Dict]:
    """Obtiene target instances."""
    cmd = f'gcloud compute target-instances list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug, console) or []


def extract_name_from_url(url: str) -> str:
    """Extrae el nombre del recurso de una URL de GCP."""
    if not url:
        return "N/A"
    return url.split('/')[-1]


def extract_region_from_url(url: str) -> str:
    """Extrae la región de una URL de GCP."""
    if not url:
        return "global"
    parts = url.split('/')
    if 'regions' in parts:
        idx = parts.index('regions')
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "global"


def format_backends(backends: List[Dict]) -> str:
    """Formatea la lista de backends para mostrar."""
    if not backends:
        return "N/A"
    
    backend_info = []
    for b in backends[:3]:  # Mostrar máximo 3
        group = extract_name_from_url(b.get('group', ''))
        backend_info.append(group)
    
    result = ", ".join(backend_info)
    if len(backends) > 3:
        result += f" (+{len(backends) - 3} más)"
    return result


def create_forwarding_rules_table(forwarding_rules: List[Dict], console) -> Table:
    """Crea tabla de forwarding rules."""
    table = Table(
        title="🔀 Forwarding Rules",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Nombre", style="white", no_wrap=True)
    table.add_column("Tipo", style="yellow")
    table.add_column("Scope", style="blue")
    table.add_column("IP Address", style="green")
    table.add_column("Protocolo", style="magenta")
    table.add_column("Puertos", style="cyan")
    table.add_column("Target", style="white")
    table.add_column("Network Tier", style="yellow")
    
    for rule in forwarding_rules:
        name = rule.get('name', 'N/A')
        
        # Determinar tipo basado en el target
        target = rule.get('target', '')
        target_name = extract_name_from_url(target)
        
        if 'targetHttpProxies' in target or 'targetHttpsProxies' in target:
            lb_type = "HTTP(S)"
        elif 'targetTcpProxies' in target:
            lb_type = "TCP Proxy"
        elif 'targetSslProxies' in target:
            lb_type = "SSL Proxy"
        elif 'targetPools' in target:
            lb_type = "Network LB"
        elif 'targetInstances' in target:
            lb_type = "Target Instance"
        elif rule.get('loadBalancingScheme', '').startswith('INTERNAL'):
            lb_type = "Internal"
        else:
            lb_type = "External"
        
        scope = "Regional" if 'region' in rule else "Global"
        ip_address = rule.get('IPAddress', 'N/A')
        protocol = rule.get('IPProtocol', 'N/A')
        
        ports = rule.get('ports', rule.get('portRange', 'All'))
        if isinstance(ports, list):
            ports = ", ".join(ports[:5])
            if len(rule.get('ports', [])) > 5:
                ports += "..."
        
        network_tier = rule.get('networkTier', 'PREMIUM')
        
        table.add_row(
            name,
            lb_type,
            scope,
            ip_address,
            protocol,
            str(ports),
            target_name,
            network_tier
        )
    
    return table


def create_backend_services_table(backend_services: List[Dict], console) -> Table:
    """Crea tabla de backend services."""
    table = Table(
        title="🔧 Backend Services",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Nombre", style="white", no_wrap=True)
    table.add_column("Protocolo", style="yellow")
    table.add_column("Scope", style="blue")
    table.add_column("Balancing Mode", style="green")
    table.add_column("Health Check", style="magenta")
    table.add_column("Backends", style="cyan")
    table.add_column("Timeout (s)", style="white")
    table.add_column("Session Affinity", style="yellow")
    
    for svc in backend_services:
        name = svc.get('name', 'N/A')
        protocol = svc.get('protocol', 'N/A')
        scope = "Regional" if 'region' in svc else "Global"
        
        backends = svc.get('backends', [])
        balancing_mode = backends[0].get('balancingMode', 'N/A') if backends else 'N/A'
        backends_str = format_backends(backends)
        
        health_checks = svc.get('healthChecks', [])
        hc_name = extract_name_from_url(health_checks[0]) if health_checks else 'N/A'
        
        timeout = svc.get('timeoutSec', 'N/A')
        affinity = svc.get('sessionAffinity', 'NONE')
        
        table.add_row(
            name,
            protocol,
            scope,
            balancing_mode,
            hc_name,
            backends_str,
            str(timeout),
            affinity
        )
    
    return table


def create_url_maps_table(url_maps: List[Dict], console) -> Table:
    """Crea tabla de URL maps."""
    table = Table(
        title="🗺️ URL Maps",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Nombre", style="white", no_wrap=True)
    table.add_column("Default Service", style="yellow")
    table.add_column("Host Rules", style="blue")
    table.add_column("Path Matchers", style="green")
    table.add_column("Descripción", style="dim")
    
    for um in url_maps:
        name = um.get('name', 'N/A')
        default_svc = extract_name_from_url(um.get('defaultService', ''))
        
        host_rules = um.get('hostRules', [])
        host_rules_count = len(host_rules)
        
        path_matchers = um.get('pathMatchers', [])
        path_matchers_count = len(path_matchers)
        
        description = um.get('description', '')[:40] if um.get('description') else ''
        
        table.add_row(
            name,
            default_svc,
            str(host_rules_count),
            str(path_matchers_count),
            description
        )
    
    return table


def create_health_checks_table(health_checks: List[Dict], console) -> Table:
    """Crea tabla de health checks."""
    table = Table(
        title="💓 Health Checks",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Nombre", style="white", no_wrap=True)
    table.add_column("Tipo", style="yellow")
    table.add_column("Puerto", style="blue")
    table.add_column("Intervalo (s)", style="green")
    table.add_column("Timeout (s)", style="magenta")
    table.add_column("Healthy", style="cyan")
    table.add_column("Unhealthy", style="red")
    table.add_column("Path/Host", style="dim")
    
    for hc in health_checks:
        name = hc.get('name', 'N/A')
        
        # Determinar tipo de health check
        hc_type = "N/A"
        port = "N/A"
        path_or_host = ""
        
        for check_type in ['httpHealthCheck', 'httpsHealthCheck', 'http2HealthCheck', 
                           'tcpHealthCheck', 'sslHealthCheck', 'grpcHealthCheck']:
            if check_type in hc:
                hc_type = check_type.replace('HealthCheck', '').upper()
                check_config = hc[check_type]
                port = check_config.get('port', check_config.get('portName', 'N/A'))
                if 'requestPath' in check_config:
                    path_or_host = check_config.get('requestPath', '')
                elif 'host' in check_config:
                    path_or_host = check_config.get('host', '')
                break
        
        interval = hc.get('checkIntervalSec', 'N/A')
        timeout = hc.get('timeoutSec', 'N/A')
        healthy = hc.get('healthyThreshold', 'N/A')
        unhealthy = hc.get('unhealthyThreshold', 'N/A')
        
        table.add_row(
            name,
            hc_type,
            str(port),
            str(interval),
            str(timeout),
            str(healthy),
            str(unhealthy),
            path_or_host[:30]
        )
    
    return table


def create_ssl_certificates_table(ssl_certs: List[Dict], console, tz_name: str) -> Table:
    """Crea tabla de SSL certificates."""
    table = Table(
        title="🔒 SSL Certificates",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Nombre", style="white", no_wrap=True)
    table.add_column("Tipo", style="yellow")
    table.add_column("Dominios", style="blue")
    table.add_column("Estado", style="green")
    table.add_column("Expiración", style="magenta")
    table.add_column("Días Restantes", style="cyan")
    
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    
    for cert in ssl_certs:
        name = cert.get('name', 'N/A')
        cert_type = cert.get('type', 'SELF_MANAGED')
        
        # Dominios
        domains = cert.get('subjectAlternativeNames', [])
        if domains:
            domains_str = ", ".join(domains[:2])
            if len(domains) > 2:
                domains_str += f" (+{len(domains) - 2})"
        else:
            domains_str = cert.get('managed', {}).get('domains', ['N/A'])[0] if cert.get('managed') else 'N/A'
        
        # Estado para managed certs
        status = "N/A"
        if cert.get('managed'):
            status = cert['managed'].get('status', 'N/A')
        elif cert_type == 'SELF_MANAGED':
            status = 'ACTIVE'
        
        # Expiración
        expire_time = cert.get('expireTime', '')
        days_remaining = "N/A"
        expire_display = "N/A"
        
        if expire_time:
            try:
                expire_dt = datetime.fromisoformat(expire_time.replace('Z', '+00:00'))
                expire_display = expire_dt.strftime('%Y-%m-%d')
                delta = expire_dt - now.replace(tzinfo=expire_dt.tzinfo)
                days_remaining = delta.days
                
                if days_remaining < 0:
                    days_remaining = f"[red]EXPIRADO ({abs(days_remaining)}d)[/red]"
                elif days_remaining < 30:
                    days_remaining = f"[yellow]{days_remaining}[/yellow]"
                else:
                    days_remaining = f"[green]{days_remaining}[/green]"
            except:
                pass
        
        # Color para estado
        if status == 'ACTIVE':
            status = f"[green]{status}[/green]"
        elif status == 'PROVISIONING':
            status = f"[yellow]{status}[/yellow]"
        elif status in ['FAILED', 'RENEWAL_FAILED']:
            status = f"[red]{status}[/red]"
        
        table.add_row(
            name,
            cert_type,
            domains_str,
            status,
            expire_display,
            str(days_remaining)
        )
    
    return table


def create_target_pools_table(target_pools: List[Dict], console) -> Table:
    """Crea tabla de target pools."""
    table = Table(
        title="🎯 Target Pools (Network LB)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Nombre", style="white", no_wrap=True)
    table.add_column("Región", style="yellow")
    table.add_column("Session Affinity", style="blue")
    table.add_column("Health Check", style="green")
    table.add_column("Instancias", style="magenta")
    table.add_column("Backup Pool", style="cyan")
    
    for pool in target_pools:
        name = pool.get('name', 'N/A')
        region = extract_region_from_url(pool.get('region', ''))
        affinity = pool.get('sessionAffinity', 'NONE')
        
        health_checks = pool.get('healthChecks', [])
        hc = extract_name_from_url(health_checks[0]) if health_checks else 'N/A'
        
        instances = pool.get('instances', [])
        instances_count = len(instances)
        
        backup = extract_name_from_url(pool.get('backupPool', '')) if pool.get('backupPool') else 'N/A'
        
        table.add_row(
            name,
            region,
            affinity,
            hc,
            str(instances_count),
            backup
        )
    
    return table


def create_summary_table(data: Dict, console) -> Table:
    """Crea tabla resumen de todos los recursos."""
    table = Table(
        title="📊 Resumen de Load Balancers",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Componente", style="white")
    table.add_column("Global", style="cyan", justify="right")
    table.add_column("Regional", style="yellow", justify="right")
    table.add_column("Total", style="green", justify="right")
    
    # Forwarding Rules
    global_fr = len([r for r in data.get('forwarding_rules_global', []) if 'region' not in r])
    regional_fr = len(data.get('forwarding_rules_regional', []))
    table.add_row("Forwarding Rules", str(global_fr), str(regional_fr), str(global_fr + regional_fr))
    
    # Backend Services
    global_bs = len([b for b in data.get('backend_services_global', []) if 'region' not in b])
    regional_bs = len(data.get('backend_services_regional', []))
    table.add_row("Backend Services", str(global_bs), str(regional_bs), str(global_bs + regional_bs))
    
    # URL Maps
    url_maps = len(data.get('url_maps', []))
    table.add_row("URL Maps", str(url_maps), "-", str(url_maps))
    
    # Target Proxies
    http_proxies = len(data.get('target_http_proxies', []))
    https_proxies = len(data.get('target_https_proxies', []))
    tcp_proxies = len(data.get('target_tcp_proxies', []))
    ssl_proxies = len(data.get('target_ssl_proxies', []))
    total_proxies = http_proxies + https_proxies + tcp_proxies + ssl_proxies
    table.add_row("Target Proxies (HTTP/HTTPS/TCP/SSL)", str(total_proxies), "-", str(total_proxies))
    
    # Health Checks
    hc = len(data.get('health_checks', []))
    table.add_row("Health Checks", str(hc), "-", str(hc))
    
    # SSL Certificates
    ssl_certs = len(data.get('ssl_certificates', []))
    table.add_row("SSL Certificates", str(ssl_certs), "-", str(ssl_certs))
    
    # Target Pools
    target_pools = len(data.get('target_pools', []))
    table.add_row("Target Pools (Network LB)", "-", str(target_pools), str(target_pools))
    
    # Backend Buckets
    bb = len(data.get('backend_buckets', []))
    table.add_row("Backend Buckets", str(bb), "-", str(bb))
    
    return table


def export_to_json(data: Dict, project_id: str, output_dir: str, tz_name: str) -> str:
    """Exporta los datos a JSON con metadatos completos."""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"lb_checker_{project_id}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    all_forwarding = data.get('forwarding_rules_global', []) + data.get('forwarding_rules_regional', [])
    all_backends = data.get('backend_services_global', []) + data.get('backend_services_regional', [])
    
    export_data = {
        "report_metadata": {
            "tool_name": "GCP Load Balancer Checker",
            "version": __version__,
            "project_id": project_id,
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "total_forwarding_rules": len(all_forwarding),
            "total_backend_services": len(all_backends),
            "total_url_maps": len(data.get('url_maps', [])),
            "total_health_checks": len(data.get('health_checks', [])),
            "total_ssl_certificates": len(data.get('ssl_certificates', []))
        },
        "data": data
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    return filepath


def export_to_csv(data: Dict, project_id: str, output_dir: str, tz_name: str) -> str:
    """Exporta los datos principales a CSV."""
    import csv
    
    tz = ZoneInfo(tz_name)
    timestamp = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
    filename = f"lb_checker_{project_id}_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)
    
    # Exportar forwarding rules como tabla principal
    all_rules = data.get('forwarding_rules_global', []) + data.get('forwarding_rules_regional', [])
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Name', 'Type', 'Scope', 'IP Address', 'Protocol', 
            'Ports', 'Target', 'Network Tier', 'Load Balancing Scheme'
        ])
        
        for rule in all_rules:
            target = rule.get('target', '')
            if 'targetHttpProxies' in target or 'targetHttpsProxies' in target:
                lb_type = "HTTP(S)"
            elif 'targetTcpProxies' in target:
                lb_type = "TCP Proxy"
            elif 'targetSslProxies' in target:
                lb_type = "SSL Proxy"
            elif 'targetPools' in target:
                lb_type = "Network LB"
            else:
                lb_type = rule.get('loadBalancingScheme', 'External')
            
            ports = rule.get('ports', rule.get('portRange', 'All'))
            if isinstance(ports, list):
                ports = ", ".join(ports)
            
            writer.writerow([
                rule.get('name', ''),
                lb_type,
                "Regional" if 'region' in rule else "Global",
                rule.get('IPAddress', ''),
                rule.get('IPProtocol', ''),
                ports,
                extract_name_from_url(rule.get('target', '')),
                rule.get('networkTier', 'PREMIUM'),
                rule.get('loadBalancingScheme', '')
            ])
    
    return filepath


def print_execution_time(start_time: float, console, tz_name: str):
    """Imprime el tiempo de ejecución."""
    elapsed = datetime.now().timestamp() - start_time
    tz = ZoneInfo(tz_name)
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
    
    console.print(f"\n[dim]⏱️  Tiempo de ejecución: {elapsed:.2f}s | {current_time}[/dim]")


def main():
    """Función principal."""
    start_time = datetime.now().timestamp()
    
    if RICH_AVAILABLE:
        console = Console()
    else:
        print("❌ Se requiere la librería 'rich'. Instala con: pip install rich")
        sys.exit(1)
    
    args = get_args()
    
    if args.help:
        show_help(console)
        return
    
    project_id = args.project
    debug = args.debug
    tz_name = args.timezone
    use_parallel = args.parallel and not args.no_parallel
    max_workers = args.max_workers
    view = args.view
    
    console.print(Panel(
        f"[bold cyan]GCP Load Balancer Checker v{__version__}[/bold cyan]\n"
        f"Proyecto: [yellow]{project_id}[/yellow]",
        border_style="blue"
    ))
    
    # Verificar conexión GCP
    if not check_gcp_connection(project_id, console, debug):
        print_execution_time(start_time, console, tz_name)
        return
    
    console.print()
    
    # Recolectar datos
    data = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        if use_parallel:
            task = progress.add_task("Recolectando datos de Load Balancers (paralelo)...", total=None)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(get_forwarding_rules_global, project_id, debug, console): 'forwarding_rules_global',
                    executor.submit(get_forwarding_rules_regional, project_id, debug, console): 'forwarding_rules_regional',
                    executor.submit(get_target_http_proxies, project_id, debug, console): 'target_http_proxies',
                    executor.submit(get_target_https_proxies, project_id, debug, console): 'target_https_proxies',
                    executor.submit(get_target_tcp_proxies, project_id, debug, console): 'target_tcp_proxies',
                    executor.submit(get_target_ssl_proxies, project_id, debug, console): 'target_ssl_proxies',
                    executor.submit(get_url_maps, project_id, debug, console): 'url_maps',
                    executor.submit(get_backend_services_global, project_id, debug, console): 'backend_services_global',
                    executor.submit(get_backend_services_regional, project_id, debug, console): 'backend_services_regional',
                    executor.submit(get_backend_buckets, project_id, debug, console): 'backend_buckets',
                    executor.submit(get_health_checks, project_id, debug, console): 'health_checks',
                    executor.submit(get_ssl_certificates, project_id, debug, console): 'ssl_certificates',
                    executor.submit(get_ssl_policies, project_id, debug, console): 'ssl_policies',
                    executor.submit(get_target_pools, project_id, debug, console): 'target_pools',
                    executor.submit(get_target_instances, project_id, debug, console): 'target_instances',
                }
                
                for future in as_completed(futures):
                    key = futures[future]
                    try:
                        data[key] = future.result()
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Error obteniendo {key}: {e}[/yellow]")
                        data[key] = []
        else:
            task = progress.add_task("Recolectando datos de Load Balancers...", total=None)
            data['forwarding_rules_global'] = get_forwarding_rules_global(project_id, debug, console)
            data['forwarding_rules_regional'] = get_forwarding_rules_regional(project_id, debug, console)
            data['target_http_proxies'] = get_target_http_proxies(project_id, debug, console)
            data['target_https_proxies'] = get_target_https_proxies(project_id, debug, console)
            data['target_tcp_proxies'] = get_target_tcp_proxies(project_id, debug, console)
            data['target_ssl_proxies'] = get_target_ssl_proxies(project_id, debug, console)
            data['url_maps'] = get_url_maps(project_id, debug, console)
            data['backend_services_global'] = get_backend_services_global(project_id, debug, console)
            data['backend_services_regional'] = get_backend_services_regional(project_id, debug, console)
            data['backend_buckets'] = get_backend_buckets(project_id, debug, console)
            data['health_checks'] = get_health_checks(project_id, debug, console)
            data['ssl_certificates'] = get_ssl_certificates(project_id, debug, console)
            data['ssl_policies'] = get_ssl_policies(project_id, debug, console)
            data['target_pools'] = get_target_pools(project_id, debug, console)
            data['target_instances'] = get_target_instances(project_id, debug, console)
    
    # Mostrar tablas según la vista seleccionada
    console.print()
    
    # Siempre mostrar resumen
    summary_table = create_summary_table(data, console)
    console.print(summary_table)
    console.print()
    
    all_forwarding = data.get('forwarding_rules_global', []) + data.get('forwarding_rules_regional', [])
    all_backends = data.get('backend_services_global', []) + data.get('backend_services_regional', [])
    
    if view in ['all', 'forwarding'] and all_forwarding:
        console.print(create_forwarding_rules_table(all_forwarding, console))
        console.print()
    
    if view in ['all', 'backends'] and all_backends:
        console.print(create_backend_services_table(all_backends, console))
        console.print()
    
    if view in ['all', 'urlmaps'] and data.get('url_maps'):
        console.print(create_url_maps_table(data['url_maps'], console))
        console.print()
    
    if view in ['all', 'healthchecks'] and data.get('health_checks'):
        console.print(create_health_checks_table(data['health_checks'], console))
        console.print()
    
    if view in ['all', 'ssl'] and data.get('ssl_certificates'):
        console.print(create_ssl_certificates_table(data['ssl_certificates'], console, tz_name))
        console.print()
    
    if view == 'all' and data.get('target_pools'):
        console.print(create_target_pools_table(data['target_pools'], console))
        console.print()
    
    # Exportar si se especificó
    if args.output:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outcome')
        os.makedirs(output_dir, exist_ok=True)
        
        if args.output == 'json':
            filepath = export_to_json(data, project_id, output_dir, tz_name)
        else:
            filepath = export_to_csv(data, project_id, output_dir, tz_name)
        
        console.print(f"[green]✓ Exportado a:[/green] {filepath}")
    
    print_execution_time(start_time, console, tz_name)


if __name__ == "__main__":
    main()
