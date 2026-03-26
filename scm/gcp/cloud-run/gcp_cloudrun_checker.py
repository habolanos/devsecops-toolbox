#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud Run Checker

Herramienta SRE para monitorear y analizar servicios Cloud Run en Google Cloud Platform.
Muestra información detallada de:
- Cloud Run Services (regionales)
- Revisions y Traffic Split
- Cloud Run Jobs y Executions
- IAM Policies (público vs autenticado)
- VPC Connectors y Egress
- Domain Mappings
- Service Accounts y Secrets

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

# Consola global
console = Console() if RICH_AVAILABLE else None


def get_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SRE Tool: GCP Cloud Run Checker",
        add_help=False
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        required=True,
        help="ID del proyecto de GCP"
    )
    parser.add_argument(
        "--region", "-r",
        type=str,
        default="all",
        help="Región específica o 'all' para todas (default: all)"
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
        choices=["all", "services", "revisions", "security", "jobs", "networking"],
        default="all",
        help="Vista específica a mostrar (default: all)"
    )
    parser.add_argument(
        "--compare", "-c",
        type=str,
        help="Compara con otro proyecto GCP"
    )
    return parser.parse_args()


def show_help():
    """Muestra documentación completa del script."""
    help_text = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                       GCP CLOUD RUN CHECKER v{version}                            ║
║                    Herramienta SRE para Cloud Run                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  DESCRIPCIÓN:                                                                ║
║    Analiza y muestra información detallada de servicios Cloud Run           ║
║    incluyendo configuración, seguridad, networking y jobs.                   ║
║                                                                              ║
║  USO:                                                                        ║
║    python gcp_cloudrun_checker.py --project <PROJECT_ID> [opciones]         ║
║                                                                              ║
║  OPCIONES:                                                                   ║
║    --project, -p    ID del proyecto GCP (requerido)                          ║
║    --region, -r     Región específica o 'all' (default: all)                 ║
║    --view, -v       Vista: all, services, revisions, security, jobs,         ║
║                     networking (default: all)                                ║
║    --compare, -c    Compara con otro proyecto GCP                            ║
║    --output, -o     Exporta a json o csv                                     ║
║    --debug          Muestra comandos gcloud ejecutados                       ║
║    --timezone, -tz  Timezone para timestamps (default: America/Mazatlan)     ║
║    --help, -h       Muestra esta ayuda                                       ║
║                                                                              ║
║  EJEMPLOS:                                                                   ║
║    python gcp_cloudrun_checker.py -p mi-proyecto                             ║
║    python gcp_cloudrun_checker.py -p mi-proyecto --view security             ║
║    python gcp_cloudrun_checker.py -p prod-project --compare dev-project      ║
║    python gcp_cloudrun_checker.py -p mi-proyecto -r us-central1              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""".format(version=__version__)
    print(help_text)
    sys.exit(0)


def run_gcloud_command(command: str, project: str, debug: bool = False) -> Optional[List[Dict]]:
    """Ejecuta un comando gcloud y retorna el resultado como JSON."""
    full_command = f"{command} --project={project} --format=json"
    
    if debug:
        console.print(f"[dim]DEBUG: {full_command}[/dim]") if RICH_AVAILABLE else print(f"DEBUG: {full_command}")
    
    try:
        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            if debug:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                if RICH_AVAILABLE:
                    console.print(f"[red]Error: {error_msg}[/red]")
                else:
                    print(f"Error: {error_msg}")
            return []
        
        if result.stdout.strip():
            return json.loads(result.stdout)
        return []
        
    except subprocess.TimeoutExpired:
        if RICH_AVAILABLE:
            console.print(f"[yellow]Timeout ejecutando: {command}[/yellow]")
        return []
    except json.JSONDecodeError:
        if debug:
            if RICH_AVAILABLE:
                console.print(f"[yellow]No JSON output para: {command}[/yellow]")
        return []
    except Exception as e:
        if debug:
            if RICH_AVAILABLE:
                console.print(f"[red]Exception: {e}[/red]")
        return []


def validate_gcp_connection(project: str, debug: bool = False) -> bool:
    """Valida la conexión a GCP y permisos del proyecto."""
    if RICH_AVAILABLE:
        with console.status("[bold blue]Validando conexión a GCP...[/bold blue]"):
            result = run_gcloud_command("gcloud run services list", project, debug)
            return result is not None
    else:
        result = run_gcloud_command("gcloud run services list", project, debug)
        return result is not None


# =============================================================================
# FUNCIONES DE RECOLECCIÓN DE DATOS
# =============================================================================

def get_services(project: str, region: str = "all", debug: bool = False) -> List[Dict]:
    """Obtiene lista de servicios Cloud Run."""
    if region == "all":
        command = "gcloud run services list"
    else:
        command = f"gcloud run services list --region={region}"
    return run_gcloud_command(command, project, debug) or []


def get_service_details(project: str, service_name: str, region: str, debug: bool = False) -> Optional[Dict]:
    """Obtiene detalles de un servicio específico."""
    command = f"gcloud run services describe {service_name} --region={region}"
    result = run_gcloud_command(command, project, debug)
    return result if isinstance(result, dict) else None


def get_revisions(project: str, region: str = "all", debug: bool = False) -> List[Dict]:
    """Obtiene lista de revisiones Cloud Run."""
    if region == "all":
        command = "gcloud run revisions list"
    else:
        command = f"gcloud run revisions list --region={region}"
    return run_gcloud_command(command, project, debug) or []


def get_service_iam_policy(project: str, service_name: str, region: str, debug: bool = False) -> Dict:
    """Obtiene política IAM de un servicio."""
    command = f"gcloud run services get-iam-policy {service_name} --region={region}"
    result = run_gcloud_command(command, project, debug)
    return result if isinstance(result, dict) else {}


def get_jobs(project: str, region: str = "all", debug: bool = False) -> List[Dict]:
    """Obtiene lista de Cloud Run Jobs."""
    if region == "all":
        command = "gcloud run jobs list"
    else:
        command = f"gcloud run jobs list --region={region}"
    return run_gcloud_command(command, project, debug) or []


def get_job_executions(project: str, job_name: str, region: str, debug: bool = False) -> List[Dict]:
    """Obtiene ejecuciones de un job."""
    command = f"gcloud run jobs executions list --job={job_name} --region={region}"
    return run_gcloud_command(command, project, debug) or []


def get_domain_mappings(project: str, region: str = "all", debug: bool = False) -> List[Dict]:
    """Obtiene domain mappings."""
    if region == "all":
        command = "gcloud run domain-mappings list"
    else:
        command = f"gcloud run domain-mappings list --region={region}"
    return run_gcloud_command(command, project, debug) or []


def get_regions(project: str, debug: bool = False) -> List[str]:
    """Obtiene lista de regiones disponibles para Cloud Run."""
    command = "gcloud run regions list"
    result = run_gcloud_command(command, project, debug)
    if result:
        return [r.get("locationId", "") for r in result if r.get("locationId")]
    return []


# =============================================================================
# FUNCIONES DE ANÁLISIS
# =============================================================================

def analyze_service_security(service: Dict, iam_policy: Dict) -> Dict:
    """Analiza la configuración de seguridad de un servicio."""
    spec = service.get("spec", {}).get("template", {}).get("spec", {})
    metadata = service.get("metadata", {})
    annotations = metadata.get("annotations", {})
    
    # Verificar si es público
    is_public = False
    if iam_policy:
        bindings = iam_policy.get("bindings", [])
        for binding in bindings:
            members = binding.get("members", [])
            if "allUsers" in members or "allAuthenticatedUsers" in members:
                is_public = True
                break
    
    # Ingress setting
    ingress = annotations.get("run.googleapis.com/ingress", "all")
    
    # VPC Connector
    vpc_connector = annotations.get("run.googleapis.com/vpc-access-connector", "")
    vpc_egress = annotations.get("run.googleapis.com/vpc-access-egress", "")
    
    # Service Account
    service_account = spec.get("serviceAccountName", "default")
    
    # Binary Authorization
    binary_auth = annotations.get("run.googleapis.com/binary-authorization", "")
    
    return {
        "is_public": is_public,
        "ingress": ingress,
        "vpc_connector": vpc_connector,
        "vpc_egress": vpc_egress,
        "service_account": service_account,
        "binary_authorization": binary_auth
    }


def extract_service_config(service: Dict) -> Dict:
    """Extrae configuración de un servicio."""
    spec = service.get("spec", {}).get("template", {}).get("spec", {})
    container_spec = spec.get("containers", [{}])[0] if spec.get("containers") else {}
    metadata = service.get("metadata", {})
    annotations = metadata.get("annotations", {})
    template_annotations = service.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
    
    # Recursos
    resources = container_spec.get("resources", {}).get("limits", {})
    cpu = resources.get("cpu", "N/A")
    memory = resources.get("memory", "N/A")
    
    # Concurrencia
    container_concurrency = spec.get("containerConcurrency", 80)
    
    # Timeout
    timeout = spec.get("timeoutSeconds", 300)
    
    # Min/Max instances
    min_instances = template_annotations.get("autoscaling.knative.dev/minScale", "0")
    max_instances = template_annotations.get("autoscaling.knative.dev/maxScale", "100")
    
    # Startup CPU boost
    startup_boost = template_annotations.get("run.googleapis.com/startup-cpu-boost", "false")
    
    return {
        "cpu": cpu,
        "memory": memory,
        "concurrency": container_concurrency,
        "timeout": timeout,
        "min_instances": min_instances,
        "max_instances": max_instances,
        "startup_boost": startup_boost
    }


# =============================================================================
# TABLAS DE VISUALIZACIÓN
# =============================================================================

def create_services_table(services: List[Dict], title: str = "Cloud Run Services") -> Table:
    """Crea tabla de servicios Cloud Run."""
    table = Table(
        title=f"🚀 {title}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Servicio", style="bold white")
    table.add_column("Región", style="yellow")
    table.add_column("URL", style="blue")
    table.add_column("CPU", style="green", justify="center")
    table.add_column("Memoria", style="green", justify="center")
    table.add_column("Concurrencia", justify="center")
    table.add_column("Min/Max", justify="center")
    table.add_column("Última Revisión", style="dim")
    
    for svc in services:
        metadata = svc.get("metadata", {})
        status = svc.get("status", {})
        
        name = metadata.get("name", "N/A")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "N/A")
        url = status.get("url", "N/A")
        
        # Extraer config
        config = extract_service_config(svc)
        
        # Última revisión
        latest_revision = status.get("latestReadyRevisionName", "N/A")
        if latest_revision and len(latest_revision) > 30:
            latest_revision = "..." + latest_revision[-27:]
        
        table.add_row(
            name,
            region,
            url[:50] + "..." if len(url) > 50 else url,
            config["cpu"],
            config["memory"],
            str(config["concurrency"]),
            f"{config['min_instances']}/{config['max_instances']}",
            latest_revision
        )
    
    return table


def create_revisions_table(revisions: List[Dict], title: str = "Cloud Run Revisions") -> Table:
    """Crea tabla de revisiones."""
    table = Table(
        title=f"📋 {title}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Revisión", style="bold white")
    table.add_column("Servicio", style="yellow")
    table.add_column("Región", style="yellow")
    table.add_column("Activa", justify="center")
    table.add_column("Tráfico %", justify="center", style="green")
    table.add_column("Creada", style="dim")
    
    for rev in revisions:
        metadata = rev.get("metadata", {})
        status = rev.get("status", {})
        
        name = metadata.get("name", "N/A")
        service = metadata.get("labels", {}).get("serving.knative.dev/service", "N/A")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "N/A")
        
        # Status
        conditions = status.get("conditions", [])
        is_ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in conditions)
        active_icon = "✅" if is_ready else "❌"
        
        # Traffic (necesita info del servicio)
        traffic = "N/A"
        
        # Timestamp
        created = metadata.get("creationTimestamp", "N/A")
        if created != "N/A":
            created = created[:19].replace("T", " ")
        
        table.add_row(
            name[:40] + "..." if len(name) > 40 else name,
            service,
            region,
            active_icon,
            traffic,
            created
        )
    
    return table


def create_security_table(services: List[Dict], iam_policies: Dict[str, Dict], 
                          title: str = "Security Configuration") -> Table:
    """Crea tabla de configuración de seguridad."""
    table = Table(
        title=f"🔐 {title}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Servicio", style="bold white")
    table.add_column("Región", style="yellow")
    table.add_column("Acceso", justify="center")
    table.add_column("Ingress", style="cyan")
    table.add_column("VPC Connector", style="blue")
    table.add_column("Egress", style="blue")
    table.add_column("Service Account", style="dim")
    
    for svc in services:
        metadata = svc.get("metadata", {})
        name = metadata.get("name", "N/A")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "N/A")
        
        # Obtener IAM policy
        key = f"{name}:{region}"
        iam_policy = iam_policies.get(key, {})
        
        # Analizar seguridad
        security = analyze_service_security(svc, iam_policy)
        
        # Iconos de acceso
        if security["is_public"]:
            access_icon = "[red]🌐 PÚBLICO[/red]"
        else:
            access_icon = "[green]🔒 Autenticado[/green]"
        
        # Ingress coloreado
        ingress = security["ingress"]
        if ingress == "all":
            ingress_display = "[yellow]all[/yellow]"
        elif ingress == "internal":
            ingress_display = "[green]internal[/green]"
        else:
            ingress_display = f"[cyan]{ingress}[/cyan]"
        
        # VPC
        vpc = security["vpc_connector"] if security["vpc_connector"] else "[dim]None[/dim]"
        if len(vpc) > 25:
            vpc = "..." + vpc[-22:]
        
        egress = security["vpc_egress"] if security["vpc_egress"] else "[dim]N/A[/dim]"
        
        # Service Account
        sa = security["service_account"]
        if len(sa) > 30:
            sa = sa[:27] + "..."
        
        table.add_row(
            name,
            region,
            access_icon,
            ingress_display,
            vpc,
            egress,
            sa
        )
    
    return table


def create_jobs_table(jobs: List[Dict], title: str = "Cloud Run Jobs") -> Table:
    """Crea tabla de Cloud Run Jobs."""
    table = Table(
        title=f"⚙️ {title}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Job", style="bold white")
    table.add_column("Región", style="yellow")
    table.add_column("CPU", style="green", justify="center")
    table.add_column("Memoria", style="green", justify="center")
    table.add_column("Timeout", justify="center")
    table.add_column("Parallelism", justify="center")
    table.add_column("Última Ejecución", style="dim")
    
    for job in jobs:
        metadata = job.get("metadata", {})
        spec = job.get("spec", {}).get("template", {}).get("spec", {})
        
        name = metadata.get("name", "N/A")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "N/A")
        
        # Container spec
        container = spec.get("template", {}).get("spec", {}).get("containers", [{}])[0]
        resources = container.get("resources", {}).get("limits", {})
        cpu = resources.get("cpu", "N/A")
        memory = resources.get("memory", "N/A")
        
        timeout = spec.get("template", {}).get("spec", {}).get("timeoutSeconds", "N/A")
        parallelism = spec.get("parallelism", 1)
        
        # Última ejecución
        last_exec = metadata.get("annotations", {}).get("run.googleapis.com/lastModifier", "N/A")
        
        table.add_row(
            name,
            region,
            str(cpu),
            str(memory),
            str(timeout),
            str(parallelism),
            last_exec[:30] if len(str(last_exec)) > 30 else str(last_exec)
        )
    
    return table


def create_networking_table(services: List[Dict], domain_mappings: List[Dict],
                            title: str = "Networking Configuration") -> Table:
    """Crea tabla de configuración de networking."""
    table = Table(
        title=f"🌐 {title}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Servicio", style="bold white")
    table.add_column("Región", style="yellow")
    table.add_column("URL Default", style="blue")
    table.add_column("Custom Domain", style="green")
    table.add_column("VPC Connector", style="cyan")
    table.add_column("Ingress", style="magenta")
    
    # Crear mapa de dominios
    domain_map = {}
    for dm in domain_mappings:
        svc_name = dm.get("spec", {}).get("routeName", "")
        domain = dm.get("metadata", {}).get("name", "")
        if svc_name:
            domain_map[svc_name] = domain
    
    for svc in services:
        metadata = svc.get("metadata", {})
        status = svc.get("status", {})
        annotations = metadata.get("annotations", {})
        
        name = metadata.get("name", "N/A")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "N/A")
        url = status.get("url", "N/A")
        
        custom_domain = domain_map.get(name, "[dim]None[/dim]")
        vpc_connector = annotations.get("run.googleapis.com/vpc-access-connector", "[dim]None[/dim]")
        ingress = annotations.get("run.googleapis.com/ingress", "all")
        
        table.add_row(
            name,
            region,
            url[:45] + "..." if len(url) > 45 else url,
            custom_domain,
            vpc_connector[:25] + "..." if len(str(vpc_connector)) > 25 else vpc_connector,
            ingress
        )
    
    return table


def create_summary_table(services: List[Dict], revisions: List[Dict], 
                         jobs: List[Dict], iam_policies: Dict, project: str) -> Table:
    """Crea tabla resumen."""
    table = Table(
        title=f"📊 Resumen Cloud Run - {project}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Métrica", style="bold white")
    table.add_column("Valor", style="green", justify="right")
    
    # Contar servicios públicos
    public_count = 0
    for svc in services:
        metadata = svc.get("metadata", {})
        name = metadata.get("name", "")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "")
        key = f"{name}:{region}"
        iam = iam_policies.get(key, {})
        security = analyze_service_security(svc, iam)
        if security["is_public"]:
            public_count += 1
    
    # Contar servicios con VPC
    vpc_count = sum(1 for svc in services 
                    if svc.get("metadata", {}).get("annotations", {}).get("run.googleapis.com/vpc-access-connector"))
    
    # Regiones únicas
    regions = set()
    for svc in services:
        region = svc.get("metadata", {}).get("labels", {}).get("cloud.googleapis.com/location", "")
        if region:
            regions.add(region)
    
    table.add_row("Total Services", str(len(services)))
    table.add_row("Total Revisions", str(len(revisions)))
    table.add_row("Total Jobs", str(len(jobs)))
    table.add_row("Regiones Activas", str(len(regions)))
    table.add_row("[red]Servicios Públicos[/red]", f"[red]{public_count}[/red]")
    table.add_row("Servicios Autenticados", str(len(services) - public_count))
    table.add_row("Con VPC Connector", str(vpc_count))
    
    return table


# =============================================================================
# COMPARACIÓN ENTRE PROYECTOS
# =============================================================================

def compare_projects(project1: str, project2: str, debug: bool = False) -> Dict:
    """Compara servicios Cloud Run entre dos proyectos."""
    if RICH_AVAILABLE:
        console.print(f"\n[bold blue]Comparando proyectos:[/bold blue]")
        console.print(f"  📁 Proyecto 1: [cyan]{project1}[/cyan]")
        console.print(f"  📁 Proyecto 2: [cyan]{project2}[/cyan]\n")
    
    # Recolectar datos de ambos proyectos
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Recolectando datos...", total=4)
        
        services1 = get_services(project1, "all", debug)
        progress.advance(task)
        
        services2 = get_services(project2, "all", debug)
        progress.advance(task)
        
        jobs1 = get_jobs(project1, "all", debug)
        progress.advance(task)
        
        jobs2 = get_jobs(project2, "all", debug)
        progress.advance(task)
    
    return {
        "project1": {
            "name": project1,
            "services": services1,
            "jobs": jobs1
        },
        "project2": {
            "name": project2,
            "services": services2,
            "jobs": jobs2
        }
    }


def create_comparison_table(comparison_data: Dict) -> Table:
    """Crea tabla comparativa entre proyectos."""
    p1 = comparison_data["project1"]
    p2 = comparison_data["project2"]
    
    table = Table(
        title="🔄 Comparación de Proyectos",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Métrica", style="bold white")
    table.add_column(p1["name"], style="green", justify="center")
    table.add_column(p2["name"], style="blue", justify="center")
    table.add_column("Diferencia", style="yellow", justify="center")
    
    # Métricas
    metrics = [
        ("Total Services", len(p1["services"]), len(p2["services"])),
        ("Total Jobs", len(p1["jobs"]), len(p2["jobs"])),
    ]
    
    # Regiones
    regions1 = set(s.get("metadata", {}).get("labels", {}).get("cloud.googleapis.com/location", "") 
                   for s in p1["services"])
    regions2 = set(s.get("metadata", {}).get("labels", {}).get("cloud.googleapis.com/location", "") 
                   for s in p2["services"])
    metrics.append(("Regiones Activas", len(regions1), len(regions2)))
    
    for name, val1, val2 in metrics:
        diff = val1 - val2
        if diff > 0:
            diff_str = f"[green]+{diff}[/green]"
        elif diff < 0:
            diff_str = f"[red]{diff}[/red]"
        else:
            diff_str = "="
        
        table.add_row(name, str(val1), str(val2), diff_str)
    
    return table


def create_services_diff_table(comparison_data: Dict) -> Table:
    """Crea tabla de diferencias de servicios entre proyectos."""
    p1 = comparison_data["project1"]
    p2 = comparison_data["project2"]
    
    table = Table(
        title="📋 Diferencias de Servicios",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Servicio", style="bold white")
    table.add_column("Región", style="yellow")
    table.add_column(f"En {p1['name']}", justify="center")
    table.add_column(f"En {p2['name']}", justify="center")
    table.add_column("Estado", style="cyan")
    
    # Crear sets de servicios
    services1 = {(s.get("metadata", {}).get("name", ""), 
                  s.get("metadata", {}).get("labels", {}).get("cloud.googleapis.com/location", "")) 
                 for s in p1["services"]}
    services2 = {(s.get("metadata", {}).get("name", ""), 
                  s.get("metadata", {}).get("labels", {}).get("cloud.googleapis.com/location", "")) 
                 for s in p2["services"]}
    
    all_services = services1.union(services2)
    
    for name, region in sorted(all_services):
        in_p1 = (name, region) in services1
        in_p2 = (name, region) in services2
        
        icon1 = "✅" if in_p1 else "❌"
        icon2 = "✅" if in_p2 else "❌"
        
        if in_p1 and in_p2:
            status = "[green]Ambos[/green]"
        elif in_p1:
            status = f"[yellow]Solo {p1['name']}[/yellow]"
        else:
            status = f"[blue]Solo {p2['name']}[/blue]"
        
        table.add_row(name, region, icon1, icon2, status)
    
    return table


# =============================================================================
# EXPORTACIÓN
# =============================================================================

def export_to_json(data: Dict, project: str, tz: str) -> str:
    """Exporta datos a JSON."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    outcome_dir = os.path.join(script_dir, "outcome")
    os.makedirs(outcome_dir, exist_ok=True)
    
    try:
        local_tz = ZoneInfo(tz)
    except Exception:
        local_tz = timezone.utc
    
    timestamp = datetime.now(local_tz).strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(outcome_dir, f"cloudrun_checker_{project}_{timestamp}.json")
    
    export_data = {
        "metadata": {
            "project": project,
            "timestamp": datetime.now(local_tz).isoformat(),
            "timezone": tz,
            "version": __version__
        },
        "data": data
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, default=str)
    
    return filename


def export_to_csv(services: List[Dict], project: str, tz: str) -> str:
    """Exporta servicios a CSV."""
    import csv
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    outcome_dir = os.path.join(script_dir, "outcome")
    os.makedirs(outcome_dir, exist_ok=True)
    
    try:
        local_tz = ZoneInfo(tz)
    except Exception:
        local_tz = timezone.utc
    
    timestamp = datetime.now(local_tz).strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(outcome_dir, f"cloudrun_checker_{project}_{timestamp}.csv")
    
    headers = ["name", "region", "url", "cpu", "memory", "concurrency", "min_instances", "max_instances"]
    
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for svc in services:
            metadata = svc.get("metadata", {})
            status = svc.get("status", {})
            config = extract_service_config(svc)
            
            writer.writerow([
                metadata.get("name", ""),
                metadata.get("labels", {}).get("cloud.googleapis.com/location", ""),
                status.get("url", ""),
                config["cpu"],
                config["memory"],
                config["concurrency"],
                config["min_instances"],
                config["max_instances"]
            ])
    
    return filename


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Función principal."""
    args = get_args()
    
    if args.help:
        show_help()
    
    if not RICH_AVAILABLE:
        print("Error: La librería 'rich' no está instalada.")
        print("Instalar con: pip install rich")
        sys.exit(1)
    
    project = args.project
    region = args.region
    debug = args.debug
    view = args.view
    tz = args.timezone
    use_parallel = args.parallel and not args.no_parallel
    max_workers = args.max_workers
    
    # Banner
    console.print(Panel.fit(
        f"[bold cyan]GCP Cloud Run Checker v{__version__}[/bold cyan]\n"
        f"[dim]Proyecto: {project} | Región: {region}[/dim]",
        border_style="cyan"
    ))
    
    # Modo comparación
    if args.compare:
        comparison_data = compare_projects(project, args.compare, debug)
        
        console.print(create_comparison_table(comparison_data))
        console.print()
        console.print(create_services_diff_table(comparison_data))
        return
    
    # Validar conexión
    if not validate_gcp_connection(project, debug):
        console.print("[red]Error: No se pudo conectar a GCP o no hay permisos suficientes.[/red]")
        sys.exit(1)
    
    # Recolectar datos
    services = []
    revisions = []
    jobs = []
    domain_mappings = []
    iam_policies = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        if use_parallel:
            task = progress.add_task("Recolectando datos en paralelo...", total=4)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(get_services, project, region, debug): "services",
                    executor.submit(get_revisions, project, region, debug): "revisions",
                    executor.submit(get_jobs, project, region, debug): "jobs",
                    executor.submit(get_domain_mappings, project, region, debug): "domains"
                }
                
                for future in as_completed(futures):
                    key = futures[future]
                    try:
                        result = future.result()
                        if key == "services":
                            services = result
                        elif key == "revisions":
                            revisions = result
                        elif key == "jobs":
                            jobs = result
                        elif key == "domains":
                            domain_mappings = result
                    except Exception as e:
                        if debug:
                            console.print(f"[red]Error en {key}: {e}[/red]")
                    progress.advance(task)
        else:
            task = progress.add_task("Recolectando datos...", total=4)
            
            services = get_services(project, region, debug)
            progress.advance(task)
            
            revisions = get_revisions(project, region, debug)
            progress.advance(task)
            
            jobs = get_jobs(project, region, debug)
            progress.advance(task)
            
            domain_mappings = get_domain_mappings(project, region, debug)
            progress.advance(task)
    
    # Obtener IAM policies para cada servicio (necesario para security view)
    if view in ["all", "security"]:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Obteniendo políticas IAM...", total=len(services))
            
            for svc in services:
                name = svc.get("metadata", {}).get("name", "")
                svc_region = svc.get("metadata", {}).get("labels", {}).get("cloud.googleapis.com/location", "")
                if name and svc_region:
                    iam = get_service_iam_policy(project, name, svc_region, debug)
                    iam_policies[f"{name}:{svc_region}"] = iam
                progress.advance(task)
    
    # Mostrar tablas según vista
    console.print()
    
    if view in ["all", "services"]:
        if services:
            console.print(create_services_table(services))
            console.print()
    
    if view in ["all", "revisions"]:
        if revisions:
            console.print(create_revisions_table(revisions))
            console.print()
    
    if view in ["all", "security"]:
        if services:
            console.print(create_security_table(services, iam_policies))
            console.print()
    
    if view in ["all", "jobs"]:
        if jobs:
            console.print(create_jobs_table(jobs))
            console.print()
    
    if view in ["all", "networking"]:
        if services:
            console.print(create_networking_table(services, domain_mappings))
            console.print()
    
    # Resumen
    if view == "all":
        console.print(create_summary_table(services, revisions, jobs, iam_policies, project))
        console.print()
    
    # Exportar si se solicitó
    if args.output:
        data = {
            "services": services,
            "revisions": revisions,
            "jobs": jobs,
            "domain_mappings": domain_mappings
        }
        
        if args.output == "json":
            filename = export_to_json(data, project, tz)
        else:
            filename = export_to_csv(services, project, tz)
        
        console.print(f"[green]✅ Exportado a: {filename}[/green]")


if __name__ == "__main__":
    main()
