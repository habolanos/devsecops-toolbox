#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GCP VPC Networks Checker

Herramienta SRE para visualizar información detallada de VPC Networks en GCP:
- Redes VPC y sus configuraciones
- Subnets con rangos CIDR
- Direcciones IP (internas y externas)
- Firewall rules
- Rutas personalizadas

Uso:
    python gcp_vpc_networks_checker.py --project <PROJECT_ID>
    python gcp_vpc_networks_checker.py --project <PROJECT_ID> --view subnets
    python gcp_vpc_networks_checker.py --project <PROJECT_ID> --output csv
"""

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


def get_args():
    parser = argparse.ArgumentParser(
        description="SRE Tool: GCP VPC Networks Checker (gcloud)",
        add_help=False
    )
    parser.add_argument(
        "--project",
        type=str,
        required=False,
        default="cpl-corp-cial-prod-17042024",
        help="ID del proyecto de GCP (Default: cpl-corp-cial-prod-17042024)"
    )
    parser.add_argument(
        "--view",
        type=str,
        choices=["all", "networks", "subnets", "ips", "firewall", "routes"],
        default="all",
        help="Vista específica a mostrar (Default: all)"
    )
    parser.add_argument(
        "--network",
        type=str,
        help="Filtrar por nombre de red VPC específica"
    )
    parser.add_argument(
        "--region",
        type=str,
        help="Filtrar por región específica"
    )
    parser.add_argument(
        "--host-project",
        type=str,
        help="ID del proyecto host en Shared VPC (para ver networks/subnets/firewall/routes)"
    )
    parser.add_argument(
        "--all-ips",
        action="store_true",
        help="Muestra todas las IPs incluyendo efímeras de VMs (por defecto solo estáticas)"
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


def run_gcloud_command(command, debug=False, console=None):
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
        elif result.returncode != 0 and result.stderr:
            # Mostrar error si hay problemas de permisos u otros
            if console and ("permission" in result.stderr.lower() or "denied" in result.stderr.lower()):
                console.print(f"[yellow]⚠️  Permisos insuficientes para: {command.split()[2]}[/]")
            elif debug:
                print(f"[DEBUG] Error: {result.stderr}")
        return None
    except (json.JSONDecodeError, Exception) as e:
        if debug:
            print(f"[DEBUG] Exception: {e}")
        return None


def get_shared_vpc_host_project(project_id, debug=False):
    """Detecta el host project de Shared VPC si el proyecto es un service project"""
    cmd = f'gcloud compute shared-vpc get-host-project {project_id} --format="value(name)"'
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        if debug:
            print(f"[DEBUG] Shared VPC check: {cmd}")
            print(f"[DEBUG] Return code: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] Stderr: {result.stderr}")
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception as e:
        if debug:
            print(f"[DEBUG] Exception checking Shared VPC: {e}")
        return None


def get_vpc_networks(project_id, debug=False):
    """Obtiene lista de redes VPC"""
    cmd = f'gcloud compute networks list --project={project_id} --format=json'
    return run_gcloud_command(cmd, debug) or []


def get_subnets(project_id, network=None, region=None, debug=False):
    """Obtiene lista de subnets"""
    cmd = f'gcloud compute networks subnets list --project={project_id} --format=json'
    if region:
        cmd += f' --regions={region}'
    subnets = run_gcloud_command(cmd, debug) or []
    
    if network:
        subnets = [s for s in subnets if network in s.get('network', '')]
    
    return subnets


def get_usable_subnets(service_project_id, debug=False):
    """Obtiene subnets usables en Shared VPC (desde el service project)"""
    cmd = f'gcloud compute networks subnets list-usable --project={service_project_id} --format=json'
    usable_subnets = run_gcloud_command(cmd, debug) or []
    
    # Normalizar formato de list-usable al formato estándar de subnets list
    normalized = []
    for subnet in usable_subnets:
        # list-usable usa 'subnetwork' en lugar de 'name' y tiene formato URL
        subnetwork_url = subnet.get('subnetwork', '')
        # Extraer nombre de la URL: projects/.../regions/.../subnetworks/<name>
        name = subnetwork_url.split('/')[-1] if subnetwork_url else 'UNKNOWN'
        
        # Extraer region de la URL
        region_url = ''
        if '/regions/' in subnetwork_url:
            parts = subnetwork_url.split('/regions/')
            if len(parts) > 1:
                region_url = parts[1].split('/')[0]
        
        normalized.append({
            'name': name,
            'network': subnet.get('network', ''),
            'region': region_url,
            'ipCidrRange': subnet.get('ipCidrRange', ''),
            'purpose': subnet.get('purpose', 'PRIVATE'),
            'secondaryIpRanges': subnet.get('secondaryIpRanges', []),
            'privateIpGoogleAccess': subnet.get('privateIpGoogleAccess', False),
            'project': subnet.get('project', '')
        })
    
    return normalized


def infer_subnets_from_addresses(addresses, host_project=None, debug=False):
    """Infiere subnets usadas a partir de las direcciones IP"""
    subnet_map = {}
    
    for addr in addresses:
        subnetwork = addr.get('subnetwork', '')
        if subnetwork and subnetwork != '-':
            # Extraer nombre de subnet de la URL
            subnet_name = subnetwork.split('/')[-1] if '/' in subnetwork else subnetwork
            
            if subnet_name not in subnet_map:
                # Extraer region de la URL de subnetwork
                region = ''
                if '/regions/' in subnetwork:
                    parts = subnetwork.split('/regions/')
                    if len(parts) > 1:
                        region = parts[1].split('/')[0]
                
                subnet_map[subnet_name] = {
                    'name': subnet_name,
                    'network': 'Shared VPC',
                    'region': region,
                    'ipCidrRange': 'Ver host project',
                    'purpose': 'INFERRED',
                    'secondaryIpRanges': [],
                    'privateIpGoogleAccess': False,
                    'project': host_project or 'unknown',
                    'inferred': True
                }
    
    return list(subnet_map.values())


def get_addresses(project_id, region=None, debug=False):
    """Obtiene lista de direcciones IP reservadas (estáticas)"""
    cmd = f'gcloud compute addresses list --project={project_id} --format=json'
    if region:
        cmd += f' --regions={region}'
    addresses = run_gcloud_command(cmd, debug) or []
    # Marcar como estáticas
    for addr in addresses:
        addr['ipType'] = 'Static'
    return addresses


def get_vm_ips(project_id, debug=False):
    """Obtiene IPs de instancias de VM (efímeras y estáticas asignadas)"""
    cmd = f'gcloud compute instances list --project={project_id} --format=json'
    instances = run_gcloud_command(cmd, debug) or []
    
    vm_ips = []
    for instance in instances:
        name = instance.get('name', 'UNKNOWN')
        zone = instance.get('zone', '').split('/')[-1]
        region = '-'.join(zone.split('-')[:-1]) if zone else ''
        
        for nic in instance.get('networkInterfaces', []):
            # IP interna
            internal_ip = nic.get('networkIP', '')
            network = nic.get('network', '').split('/')[-1]
            subnetwork = nic.get('subnetwork', '').split('/')[-1]
            
            if internal_ip:
                vm_ips.append({
                    'name': name,
                    'address': internal_ip,
                    'addressType': 'INTERNAL',
                    'ipType': 'Ephemeral',
                    'purpose': 'VM instance',
                    'region': region,
                    'subnetwork': subnetwork,
                    'network': network,
                    'status': 'IN_USE',
                    'users': [f'VM: {name}'],
                    'networkTier': 'PREMIUM',
                    'zone': zone
                })
            
            # IPs externas (NAT)
            for access_config in nic.get('accessConfigs', []):
                external_ip = access_config.get('natIP', '')
                ip_type = 'Static' if access_config.get('type') == 'ONE_TO_ONE_NAT' and 'natIP' in access_config else 'Ephemeral'
                network_tier = access_config.get('networkTier', 'PREMIUM')
                
                if external_ip:
                    vm_ips.append({
                        'name': name,
                        'address': external_ip,
                        'addressType': 'EXTERNAL',
                        'ipType': ip_type,
                        'purpose': 'VM instance',
                        'region': region,
                        'subnetwork': subnetwork,
                        'network': network,
                        'status': 'IN_USE',
                        'users': [f'VM: {name}'],
                        'networkTier': network_tier,
                        'zone': zone
                    })
    
    return vm_ips


def get_firewall_rules(project_id, network=None, debug=False):
    """Obtiene lista de reglas de firewall"""
    cmd = f'gcloud compute firewall-rules list --project={project_id} --format=json'
    rules = run_gcloud_command(cmd, debug) or []
    
    if network:
        rules = [r for r in rules if network in r.get('network', '')]
    
    return rules


def get_routes(project_id, network=None, debug=False):
    """Obtiene lista de rutas"""
    cmd = f'gcloud compute routes list --project={project_id} --format=json'
    routes = run_gcloud_command(cmd, debug) or []
    
    if network:
        routes = [r for r in routes if network in r.get('network', '')]
    
    return routes


def get_peerings(project_id, debug=False):
    """Obtiene lista de VPC peerings"""
    networks = get_vpc_networks(project_id, debug)
    peerings = []
    for net in networks:
        net_peerings = net.get('peerings', [])
        for p in net_peerings:
            p['sourceNetwork'] = net.get('name', 'UNKNOWN')
            peerings.append(p)
    return peerings


def extract_network_name(network_url):
    """Extrae el nombre de la red desde la URL completa"""
    if network_url and '/' in network_url:
        return network_url.split('/')[-1]
    return network_url or 'UNKNOWN'


def extract_region(zone_or_region_url):
    """Extrae la región desde la URL completa"""
    if zone_or_region_url and '/' in zone_or_region_url:
        return zone_or_region_url.split('/')[-1]
    return zone_or_region_url or 'GLOBAL'


def calculate_ip_count(cidr):
    """Calcula el número de IPs disponibles en un rango CIDR"""
    try:
        prefix = int(cidr.split('/')[-1])
        return 2 ** (32 - prefix) - 4  # Restamos 4 IPs reservadas por GCP
    except:
        return 0


def get_subnet_purpose_display(purpose):
    """Retorna el propósito de la subnet con formato"""
    purposes = {
        'PRIVATE': '[green]PRIVATE[/]',
        'INTERNAL_HTTPS_LOAD_BALANCER': '[cyan]ILB[/]',
        'REGIONAL_MANAGED_PROXY': '[yellow]PROXY[/]',
        'PRIVATE_SERVICE_CONNECT': '[magenta]PSC[/]',
        'PRIVATE_RFC_1918': '[green]RFC1918[/]',
    }
    return purposes.get(purpose, purpose or 'STANDARD')


def get_firewall_direction_display(direction):
    """Retorna la dirección del firewall con formato"""
    if direction == 'INGRESS':
        return '[cyan]INGRESS[/]'
    elif direction == 'EGRESS':
        return '[yellow]EGRESS[/]'
    return direction


def get_firewall_action_display(rule):
    """Determina si la regla es ALLOW o DENY"""
    if rule.get('allowed'):
        return '[green]ALLOW[/]'
    elif rule.get('denied'):
        return '[red]DENY[/]'
    return 'UNKNOWN'


def format_ports(rule):
    """Formatea los puertos de una regla de firewall"""
    allowed = rule.get('allowed', [])
    denied = rule.get('denied', [])
    rules_list = allowed or denied
    
    if not rules_list:
        return 'ALL'
    
    ports = []
    for r in rules_list:
        protocol = r.get('IPProtocol', 'all')
        port_list = r.get('ports', [])
        if port_list:
            ports.append(f"{protocol}:{','.join(port_list)}")
        else:
            ports.append(protocol)
    
    return '; '.join(ports)


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
            "tool_name": "GCP VPC Networks Checker",
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


def print_networks_table(console, networks, project_id):
    """Imprime tabla de redes VPC"""
    table = Table(
        title=f"🌐 VPC Networks: {project_id}",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Nombre Red", style="white")
    table.add_column("Modo Subnet", justify="center")
    table.add_column("MTU", justify="right")
    table.add_column("Routing Mode", justify="center")
    table.add_column("Peerings", justify="right")
    table.add_column("Descripción", max_width=40)
    
    results = []
    for net in sorted(networks, key=lambda x: x.get('name', '')):
        name = net.get('name', 'UNKNOWN')
        subnet_mode = net.get('autoCreateSubnetworks', False)
        mode_display = '[cyan]AUTO[/]' if subnet_mode else '[green]CUSTOM[/]'
        mtu = net.get('mtu', 1460)
        routing_mode = net.get('routingConfig', {}).get('routingMode', 'REGIONAL')
        peerings = net.get('peerings', [])
        peering_count = len(peerings)
        description = net.get('description', '-')[:40] if net.get('description') else '-'
        
        results.append({
            'project': project_id,
            'network': name,
            'subnet_mode': 'AUTO' if subnet_mode else 'CUSTOM',
            'mtu': mtu,
            'routing_mode': routing_mode,
            'peering_count': peering_count,
            'description': description
        })
        
        table.add_row(
            name,
            mode_display,
            str(mtu),
            routing_mode,
            str(peering_count),
            description
        )
    
    console.print(table)
    return results


def print_subnets_table(console, subnets, project_id):
    """Imprime tabla de subnets"""
    table = Table(
        title=f"📡 Subnets: {project_id}",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Subnet", style="white")
    table.add_column("Red", justify="left")
    table.add_column("Región", justify="center")
    table.add_column("CIDR Primario", justify="left")
    table.add_column("IPs Disp.", justify="right")
    table.add_column("Propósito", justify="center")
    table.add_column("Rangos Sec.", justify="right")
    table.add_column("Private Google", justify="center")
    
    results = []
    for subnet in sorted(subnets, key=lambda x: (x.get('network', ''), x.get('name', ''))):
        name = subnet.get('name', 'UNKNOWN')
        network = extract_network_name(subnet.get('network', ''))
        region = extract_region(subnet.get('region', ''))
        cidr = subnet.get('ipCidrRange', 'N/A')
        ip_count = calculate_ip_count(cidr)
        purpose = subnet.get('purpose', 'PRIVATE')
        secondary_ranges = subnet.get('secondaryIpRanges', [])
        sec_count = len(secondary_ranges)
        private_google = subnet.get('privateIpGoogleAccess', False)
        
        results.append({
            'project': project_id,
            'subnet': name,
            'network': network,
            'region': region,
            'cidr': cidr,
            'available_ips': ip_count,
            'purpose': purpose,
            'secondary_ranges': sec_count,
            'private_google_access': private_google
        })
        
        table.add_row(
            name,
            network,
            region,
            f"[bold]{cidr}[/]",
            str(ip_count),
            get_subnet_purpose_display(purpose),
            str(sec_count) if sec_count > 0 else '-',
            '[green]✓[/]' if private_google else '[dim]-[/]'
        )
    
    console.print(table)
    
    # Mostrar rangos secundarios si existen
    has_secondary = any(s.get('secondaryIpRanges') for s in subnets)
    if has_secondary:
        console.print()
        sec_table = Table(
            title="📊 Rangos Secundarios (Secondary Ranges)",
            title_style="bold blue",
            header_style="bold cyan",
            border_style="dim"
        )
        sec_table.add_column("Subnet", style="white")
        sec_table.add_column("Nombre Rango", justify="left")
        sec_table.add_column("CIDR", justify="left")
        sec_table.add_column("IPs Disponibles", justify="right")
        
        for subnet in subnets:
            subnet_name = subnet.get('name', 'UNKNOWN')
            for sec_range in subnet.get('secondaryIpRanges', []):
                range_name = sec_range.get('rangeName', 'UNKNOWN')
                range_cidr = sec_range.get('ipCidrRange', 'N/A')
                range_ips = calculate_ip_count(range_cidr)
                
                sec_table.add_row(
                    subnet_name,
                    range_name,
                    f"[cyan]{range_cidr}[/]",
                    str(range_ips)
                )
        
        console.print(sec_table)
    
    return results


def print_addresses_table(console, addresses, project_id):
    """Imprime tabla de direcciones IP (formato original simple)"""
    table = Table(
        title=f"🔢 Direcciones IP Estáticas: {project_id}",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Nombre", style="white")
    table.add_column("Dirección IP", justify="left")
    table.add_column("Tipo", justify="center")
    table.add_column("Propósito", justify="center")
    table.add_column("Región", justify="center")
    table.add_column("Subnetwork", justify="left")
    table.add_column("Estado", justify="center")
    table.add_column("Usuario", max_width=30)
    
    results = []
    # Filtrar solo IPs estáticas para esta tabla
    static_addresses = [a for a in addresses if a.get('ipType', 'Static') == 'Static']
    
    for addr in sorted(static_addresses, key=lambda x: x.get('name', '')):
        name = addr.get('name', 'UNKNOWN')
        ip = addr.get('address', 'N/A')
        addr_type = addr.get('addressType', 'INTERNAL')
        purpose = addr.get('purpose', '-')
        region = extract_region(addr.get('region', 'GLOBAL'))
        subnetwork = extract_network_name(addr.get('subnetwork', '-'))
        status = addr.get('status', 'UNKNOWN')
        users = addr.get('users', [])
        user_display = extract_network_name(users[0]) if users else '-'
        
        results.append({
            'project': project_id,
            'name': name,
            'address': ip,
            'type': addr_type,
            'purpose': purpose,
            'region': region,
            'subnetwork': subnetwork,
            'status': status,
            'user': user_display
        })
        
        type_display = '[cyan]INTERNAL[/]' if addr_type == 'INTERNAL' else '[yellow]EXTERNAL[/]'
        status_display = '[green]IN_USE[/]' if status == 'IN_USE' else '[dim]RESERVED[/]'
        
        table.add_row(
            name,
            f"[bold]{ip}[/]",
            type_display,
            purpose or '-',
            region,
            subnetwork,
            status_display,
            user_display
        )
    
    console.print(table)
    return results


def print_addresses_table_gcp(console, addresses, project_id, show_all=False):
    """Imprime tabla de direcciones IP (formato similar a consola GCP)"""
    # Filtrar según el parámetro show_all
    if show_all:
        filtered_addresses = addresses
        title = f"🔢 Todas las Direcciones IP: {project_id}"
    else:
        filtered_addresses = [a for a in addresses if a.get('ipType', 'Static') == 'Static']
        title = f"🔢 Direcciones IP Estáticas: {project_id}"
    
    table = Table(
        title=title,
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Nombre", style="white", max_width=30)
    table.add_column("Dirección IP", justify="left")
    table.add_column("Access Type", justify="center")
    table.add_column("Región", justify="center")
    table.add_column("Type", justify="center")
    table.add_column("In use by", max_width=25)
    table.add_column("Subnetwork", justify="left", max_width=25)
    table.add_column("VPC Network", justify="left", max_width=20)
    table.add_column("Network Tier", justify="center")
    
    results = []
    for addr in sorted(filtered_addresses, key=lambda x: (x.get('addressType', ''), x.get('name', ''))):
        name = addr.get('name', 'UNKNOWN')
        ip = addr.get('address', 'N/A')
        addr_type = addr.get('addressType', 'INTERNAL')
        ip_type = addr.get('ipType', 'Static')
        region = extract_region(addr.get('region', 'GLOBAL'))
        subnetwork = addr.get('subnetwork', '-')
        if '/' in subnetwork:
            subnetwork = subnetwork.split('/')[-1]
        network = addr.get('network', '-')
        if '/' in network:
            network = network.split('/')[-1]
        network_tier = addr.get('networkTier', 'PREMIUM')
        users = addr.get('users', [])
        user_display = users[0].split('/')[-1] if users else '-'
        purpose = addr.get('purpose', '')
        
        # Para IPs estáticas, el "In use by" puede incluir el propósito
        if purpose and purpose != '-' and user_display == '-':
            user_display = purpose
        
        results.append({
            'project': project_id,
            'name': name,
            'address': ip,
            'access_type': addr_type,
            'ip_type': ip_type,
            'region': region,
            'subnetwork': subnetwork,
            'network': network,
            'network_tier': network_tier,
            'in_use_by': user_display
        })
        
        # Formato de display
        type_display = '[cyan]Internal[/]' if addr_type == 'INTERNAL' else '[yellow]External[/]'
        ip_type_display = '[green]Static[/]' if ip_type == 'Static' else '[dim]Ephemeral[/]'
        tier_display = '[green]Premium[/]' if network_tier == 'PREMIUM' else '[dim]Standard[/]'
        
        table.add_row(
            name,
            f"[bold]{ip}[/]",
            type_display,
            region,
            ip_type_display,
            user_display,
            subnetwork if subnetwork != '-' else '-',
            network if network != '-' else '-',
            tier_display
        )
    
    console.print(table)
    return results


def print_subnet_ip_summary(console, addresses, project_id):
    """Imprime resumen de IPs por subnet"""
    # Agrupar IPs por subnet
    subnet_counts = {}
    for addr in addresses:
        subnetwork = addr.get('subnetwork', '-')
        if '/' in subnetwork:
            subnetwork = subnetwork.split('/')[-1]
        if subnetwork and subnetwork != '-':
            if subnetwork not in subnet_counts:
                subnet_counts[subnetwork] = {'static': 0, 'ephemeral': 0, 'internal': 0, 'external': 0}
            
            ip_type = addr.get('ipType', 'Static')
            addr_type = addr.get('addressType', 'INTERNAL')
            
            if ip_type == 'Static':
                subnet_counts[subnetwork]['static'] += 1
            else:
                subnet_counts[subnetwork]['ephemeral'] += 1
            
            if addr_type == 'INTERNAL':
                subnet_counts[subnetwork]['internal'] += 1
            else:
                subnet_counts[subnetwork]['external'] += 1
    
    if not subnet_counts:
        return []
    
    table = Table(
        title=f"📊 Resumen de IPs por Subnet: {project_id}",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Subnetwork", style="white")
    table.add_column("Total IPs", justify="right")
    table.add_column("Estáticas", justify="right")
    table.add_column("Efímeras", justify="right")
    table.add_column("Internas", justify="right")
    table.add_column("Externas", justify="right")
    
    results = []
    for subnet, counts in sorted(subnet_counts.items()):
        total = counts['static'] + counts['ephemeral']
        results.append({
            'subnet': subnet,
            'total': total,
            'static': counts['static'],
            'ephemeral': counts['ephemeral'],
            'internal': counts['internal'],
            'external': counts['external']
        })
        
        table.add_row(
            subnet,
            f"[bold]{total}[/]",
            f"[green]{counts['static']}[/]" if counts['static'] > 0 else '[dim]0[/]',
            f"[yellow]{counts['ephemeral']}[/]" if counts['ephemeral'] > 0 else '[dim]0[/]',
            f"[cyan]{counts['internal']}[/]" if counts['internal'] > 0 else '[dim]0[/]',
            f"[yellow]{counts['external']}[/]" if counts['external'] > 0 else '[dim]0[/]'
        )
    
    console.print(table)
    console.print("[dim]💡 Usa --all-ips para ver el detalle de todas las IPs incluyendo efímeras[/]")
    return results


def print_firewall_table(console, rules, project_id):
    """Imprime tabla de reglas de firewall"""
    table = Table(
        title=f"🔥 Firewall Rules: {project_id}",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Nombre", style="white", max_width=35)
    table.add_column("Red", justify="left")
    table.add_column("Dir", justify="center")
    table.add_column("Acción", justify="center")
    table.add_column("Prioridad", justify="right")
    table.add_column("Protocolos/Puertos", max_width=25)
    table.add_column("Origen/Destino", max_width=25)
    table.add_column("Habilitada", justify="center")
    
    results = []
    for rule in sorted(rules, key=lambda x: (x.get('network', ''), x.get('priority', 1000))):
        name = rule.get('name', 'UNKNOWN')
        network = extract_network_name(rule.get('network', ''))
        direction = rule.get('direction', 'INGRESS')
        priority = rule.get('priority', 1000)
        ports = format_ports(rule)
        disabled = rule.get('disabled', False)
        
        # Determinar origen o destino
        if direction == 'INGRESS':
            source_ranges = rule.get('sourceRanges', [])
            source_tags = rule.get('sourceTags', [])
            target = ', '.join(source_ranges[:2]) if source_ranges else ', '.join(source_tags[:2])
        else:
            dest_ranges = rule.get('destinationRanges', [])
            target = ', '.join(dest_ranges[:2]) if dest_ranges else 'ALL'
        
        action = 'ALLOW' if rule.get('allowed') else 'DENY'
        
        results.append({
            'project': project_id,
            'name': name,
            'network': network,
            'direction': direction,
            'action': action,
            'priority': priority,
            'protocols_ports': ports,
            'source_dest': target,
            'enabled': not disabled
        })
        
        table.add_row(
            name,
            network,
            get_firewall_direction_display(direction),
            get_firewall_action_display(rule),
            str(priority),
            ports[:25],
            target[:25] if target else '-',
            '[green]✓[/]' if not disabled else '[red]✗[/]'
        )
    
    console.print(table)
    return results


def print_routes_table(console, routes, project_id):
    """Imprime tabla de rutas"""
    table = Table(
        title=f"🛤️  Rutas: {project_id}",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim"
    )
    
    table.add_column("Nombre", style="white", max_width=40)
    table.add_column("Red", justify="left")
    table.add_column("Destino CIDR", justify="left")
    table.add_column("Next Hop", justify="left", max_width=35)
    table.add_column("Prioridad", justify="right")
    table.add_column("Tags", max_width=20)
    
    results = []
    # Filtrar rutas del sistema por defecto si hay muchas
    custom_routes = [r for r in routes if not r.get('name', '').startswith('default-route-')]
    display_routes = custom_routes if len(routes) > 20 else routes
    
    for route in sorted(display_routes, key=lambda x: (x.get('network', ''), x.get('priority', 1000))):
        name = route.get('name', 'UNKNOWN')
        network = extract_network_name(route.get('network', ''))
        dest_range = route.get('destRange', 'N/A')
        priority = route.get('priority', 1000)
        tags = route.get('tags', [])
        
        # Determinar next hop
        next_hop = '-'
        if route.get('nextHopGateway'):
            next_hop = 'default-internet-gateway'
        elif route.get('nextHopInstance'):
            next_hop = extract_network_name(route.get('nextHopInstance'))
        elif route.get('nextHopIp'):
            next_hop = route.get('nextHopIp')
        elif route.get('nextHopNetwork'):
            next_hop = extract_network_name(route.get('nextHopNetwork'))
        elif route.get('nextHopPeering'):
            next_hop = f"peering:{route.get('nextHopPeering')}"
        elif route.get('nextHopIlb'):
            next_hop = extract_network_name(route.get('nextHopIlb'))
        
        results.append({
            'project': project_id,
            'name': name,
            'network': network,
            'dest_range': dest_range,
            'next_hop': next_hop,
            'priority': priority,
            'tags': ','.join(tags) if tags else '-'
        })
        
        table.add_row(
            name,
            network,
            f"[bold]{dest_range}[/]",
            next_hop,
            str(priority),
            ','.join(tags[:2]) if tags else '-'
        )
    
    if len(routes) > len(display_routes):
        console.print(f"[dim]Mostrando {len(display_routes)} rutas personalizadas. {len(routes) - len(display_routes)} rutas del sistema omitidas.[/]")
    
    console.print(table)
    return results


def print_summary(console, networks, subnets, addresses, firewall_rules, routes):
    """Imprime resumen ejecutivo"""
    internal_ips = sum(1 for a in addresses if a.get('addressType') == 'INTERNAL')
    external_ips = sum(1 for a in addresses if a.get('addressType') == 'EXTERNAL')
    in_use_ips = sum(1 for a in addresses if a.get('status') == 'IN_USE')
    reserved_ips = len(addresses) - in_use_ips
    
    ingress_rules = sum(1 for r in firewall_rules if r.get('direction') == 'INGRESS')
    egress_rules = sum(1 for r in firewall_rules if r.get('direction') == 'EGRESS')
    disabled_rules = sum(1 for r in firewall_rules if r.get('disabled'))
    
    summary_text = (
        f"[bold blue]🌐 Networks: {len(networks)}[/]  "
        f"[bold cyan]📡 Subnets: {len(subnets)}[/]  "
        f"[bold green]🔢 IPs: {len(addresses)}[/] "
        f"([cyan]Int:{internal_ips}[/] [yellow]Ext:{external_ips}[/] "
        f"[green]InUse:{in_use_ips}[/] [dim]Reserved:{reserved_ips}[/])  "
        f"[bold magenta]🔥 FW: {len(firewall_rules)}[/] "
        f"([cyan]In:{ingress_rules}[/] [yellow]Out:{egress_rules}[/]"
        f"{f' [red]Disabled:{disabled_rules}[/]' if disabled_rules else ''})  "
        f"[bold yellow]🛤️  Routes: {len(routes)}[/]"
    )
    
    console.print(Panel(summary_text, title="📊 Resumen VPC Networks", border_style="blue", expand=False))


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
    
    if not args.project:
        # Intentar obtener el proyecto por defecto
        result = subprocess.run(
            'gcloud config get-value project',
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            project_id = result.stdout.strip()
        else:
            Console().print("[bold red]❌ Error: Se requiere --project o tener un proyecto configurado en gcloud[/]")
            return
    else:
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
    
    # Determinar proyecto para recursos de red (puede ser diferente en Shared VPC)
    host_project = args.host_project
    if not host_project:
        # Intentar detectar automáticamente si es un service project de Shared VPC
        console.print(f"[dim]🔍 Verificando si el proyecto es parte de Shared VPC...[/]")
        detected_host = get_shared_vpc_host_project(project_id, args.debug)
        if detected_host and detected_host != project_id:
            host_project = detected_host
            console.print(f"[green]✓ Shared VPC detectado automáticamente[/]")
    
    network_project_id = host_project if host_project else project_id
    
    console.print(f"\n[bold blue]🌐 Iniciando escaneo de VPC Networks en:[/] [white underline]{project_id}[/]")
    if host_project:
        console.print(f"[bold cyan]🔗 Host Project (Shared VPC):[/] [white underline]{host_project}[/]")
    console.print(f"[dim]🕐 Fecha y hora de revisión: {revision_time}[/]")
    if args.network:
        console.print(f"[dim]🔍 Filtro de red: {args.network}[/]")
    if args.region:
        console.print(f"[dim]📍 Filtro de región: {args.region}[/]")

    if not check_gcp_connection(project_id, console, args.debug):
        print_execution_time(start_time, console, tz_name)
        return

    console.print()

    try:
        all_results = {}
        
        # Obtener datos según la vista seleccionada
        networks = []
        subnets = []
        addresses = []
        firewall_rules = []
        routes = []
        
        # Networks, subnets, firewall y routes vienen del host project en Shared VPC
        is_shared_vpc = host_project is not None
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Recolectando datos de VPC...", total=None)
            
            if args.view in ['all', 'networks']:
                networks = get_vpc_networks(network_project_id, args.debug)
            if not networks and is_shared_vpc:
                console.print(f"[yellow]⚠️  Sin permisos en host project para listar networks[/]")
            if args.network:
                networks = [n for n in networks if args.network in n.get('name', '')]
        
        # IPs siempre del service project (obtener primero para posible inferencia de subnets)
        if args.view in ['all', 'ips', 'subnets']:
            # Obtener IPs estáticas reservadas
            addresses = get_addresses(project_id, args.region, args.debug)
            # Obtener IPs de VMs (efímeras)
            vm_ips = get_vm_ips(project_id, args.debug)
            # Combinar, evitando duplicados por IP
            existing_ips = {addr.get('address') for addr in addresses}
            for vm_ip in vm_ips:
                if vm_ip.get('address') not in existing_ips:
                    addresses.append(vm_ip)
                    existing_ips.add(vm_ip.get('address'))
        
        if args.view in ['all', 'subnets']:
            subnets = get_subnets(network_project_id, args.network, args.region, args.debug)
            # Si no hay subnets y es Shared VPC, intentar con list-usable
            if not subnets and is_shared_vpc:
                console.print(f"[dim]🔄 Intentando obtener subnets usables desde service project...[/]")
                subnets = get_usable_subnets(project_id, args.debug)
                if subnets:
                    console.print(f"[green]✓ Se encontraron {len(subnets)} subnets usables[/]")
            # Si aún no hay subnets, inferir desde las IPs
            if not subnets and is_shared_vpc and addresses:
                console.print(f"[dim]🔄 Infiriendo subnets desde direcciones IP...[/]")
                subnets = infer_subnets_from_addresses(addresses, host_project, args.debug)
                if subnets:
                    console.print(f"[yellow]⚠️  Se infirieron {len(subnets)} subnets desde IPs (info limitada)[/]")
        
        if args.view in ['all', 'firewall']:
            firewall_rules = get_firewall_rules(network_project_id, args.network, args.debug)
            if not firewall_rules and is_shared_vpc:
                console.print(f"[yellow]⚠️  Sin permisos en host project para listar firewall rules[/]")
        
        if args.view in ['all', 'routes']:
            routes = get_routes(network_project_id, args.network, args.debug)
            if not routes and is_shared_vpc:
                console.print(f"[yellow]⚠️  Sin permisos en host project para listar routes[/]")
        
        # Mostrar tablas según la vista
        if args.view in ['all', 'networks'] and networks:
            all_results['networks'] = print_networks_table(console, networks, project_id)
            console.print()
        elif args.view == 'networks' and not networks:
            console.print(f"[yellow]⚠️  No se encontraron redes VPC en {project_id}.[/]")
        
        if args.view in ['all', 'subnets'] and subnets:
            all_results['subnets'] = print_subnets_table(console, subnets, project_id)
            console.print()
        elif args.view == 'subnets' and not subnets:
            console.print(f"[yellow]⚠️  No se encontraron subnets en {project_id}.[/]")
        
        if args.view == 'ips' and not addresses:
            console.print(f"[yellow]⚠️  No se encontraron direcciones IP en {project_id}.[/]")
        
        if args.view in ['all', 'firewall'] and firewall_rules:
            all_results['firewall'] = print_firewall_table(console, firewall_rules, project_id)
            console.print()
        elif args.view == 'firewall' and not firewall_rules:
            console.print(f"[yellow]⚠️  No se encontraron reglas de firewall en {project_id}.[/]")
        
        if args.view in ['all', 'routes'] and routes:
            all_results['routes'] = print_routes_table(console, routes, project_id)
            console.print()
        elif args.view == 'routes' and not routes:
            console.print(f"[yellow]⚠️  No se encontraron rutas en {project_id}.[/]")
        
        # Mostrar resumen solo en vista 'all'
        if args.view == 'all':
            print_summary(console, networks, subnets, addresses, firewall_rules, routes)
        
        # Mostrar resumen de IPs por subnet o tabla completa según --all-ips
        if args.view in ['all', 'ips'] and addresses:
            console.print()
            if args.all_ips:
                # Mostrar todas las IPs incluyendo efímeras
                all_results['addresses_gcp'] = print_addresses_table_gcp(console, addresses, project_id, show_all=True)
            else:
                # Mostrar resumen por subnet + solo estáticas
                all_results['subnet_summary'] = print_subnet_ip_summary(console, addresses, project_id)
                console.print()
                all_results['addresses_gcp'] = print_addresses_table_gcp(console, addresses, project_id, show_all=False)
        
        # Exportar resultados
        if args.output and all_results:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            outcome_dir = os.path.join(script_dir, 'outcome')
            os.makedirs(outcome_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for data_type, data in all_results.items():
                if data:
                    filename = f"vpc_{data_type}_{project_id}_{timestamp}"
                    
                    if args.output == 'csv':
                        filepath = os.path.join(outcome_dir, f"{filename}.csv")
                        export_to_csv(data, filepath)
                    elif args.output == 'json':
                        filepath = os.path.join(outcome_dir, f"{filename}.json")
                        export_to_json(data, filepath, project_id, tz_name)
                    
                    console.print(f"[bold green]📁 Exportado:[/] {filepath}")
        
        console.print(f"\n[dim]Tip: Usa --view [networks|subnets|ips|firewall|routes] para ver una sección específica.[/]\n")

    except Exception as e:
        console.print(f"[bold red]❌ Error ejecutando gcloud:[/]\n{e}")
        if args.debug:
            import traceback
            traceback.print_exc()

    print_execution_time(start_time, console, tz_name)


if __name__ == "__main__":
    main()
