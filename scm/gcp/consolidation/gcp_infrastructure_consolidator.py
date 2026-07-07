#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Infrastructure Consolidator v1.0.0

Herramienta profesional para consolidar Load Balancers, Cloud Run y Cloud Functions.
Mapea relaciones, identifica servicios huérfanos y genera matriz de cobertura.

Uso:
    python gcp_infrastructure_consolidator.py --project mi-proyecto
    python gcp_infrastructure_consolidator.py --project mi-proyecto --view relationships
    python gcp_infrastructure_consolidator.py --project mi-proyecto --output json

Autor: Harold Adrian
"""

import sys
import os
import argparse
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

from consolidation_base import (
    LoadBalancerExtractor, CloudRunExtractor, CloudFunctionsExtractor,
    RelationshipMapper, run_gcloud_command
)

__version__ = "1.0.0"
__author__ = "Harold Adrian"


def get_args():
    parser = argparse.ArgumentParser(
        description="GCP Infrastructure Consolidator",
        add_help=False
    )
    parser.add_argument("--project", "-p", type=str, default="cpl-corp-cial-prod-17042024")
    parser.add_argument("--view", "-v", type=str, choices=["all", "summary", "relationships", "orphaned", "health"], default="all")
    parser.add_argument("--output", "-o", type=str, choices=["json", "csv", "excel"])
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--timezone", "-tz", type=str, default="America/Mazatlan")
    parser.add_argument("--help", "-h", action="store_true")
    return parser.parse_args()


def check_gcp_connection(project_id: str, console, debug: bool = False) -> bool:
    """Verifica conexión a GCP."""
    try:
        import subprocess
        auth_cmd = 'gcloud auth list --filter=status:ACTIVE --format="value(account)"'
        auth_result = subprocess.run(auth_cmd, shell=True, capture_output=True, text=True)
        
        if auth_result.returncode != 0:
            console.print("[red]❌ No hay sesión activa de gcloud[/red]")
            return False
        
        console.print(f"[green]✓[/green] Sesión activa")
        
        project_cmd = f'gcloud projects describe {project_id} --format="value(projectId)" 2>&1'
        project_result = subprocess.run(project_cmd, shell=True, capture_output=True, text=True)
        
        if project_result.returncode != 0:
            console.print(f"[red]❌ No tienes acceso al proyecto: {project_id}[/red]")
            return False
        
        console.print(f"[green]✓[/green] Proyecto accesible: [cyan]{project_id}[/cyan]")
        return True
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        return False


def create_summary_table(consolidation: Dict, console) -> Table:
    """Crea tabla de resumen."""
    table = Table(
        title="📊 Infrastructure Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Componente", style="white")
    table.add_column("Total", style="cyan", justify="right")
    
    summary = consolidation.get('summary', {})
    
    table.add_row("Load Balancers", str(summary.get('total_load_balancers', 0)))
    table.add_row("Backend Services", str(summary.get('total_backend_services', 0)))
    table.add_row("Cloud Run Services", str(summary.get('total_cloud_run_services', 0)))
    table.add_row("Cloud Functions", str(summary.get('total_cloud_functions', 0)))
    table.add_row("Relationships", str(summary.get('total_relationships', 0)))
    table.add_row("Orphaned Services", str(summary.get('orphaned_services', 0)))
    table.add_row("Health Score", f"{summary.get('health_score', 0)}%")
    
    return table


def create_relationships_table(relationships: List[Dict], console) -> Table:
    """Crea tabla de relaciones."""
    table = Table(
        title="🔗 Load Balancer → Cloud Run/Functions Relationships",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Load Balancer", style="white", no_wrap=True)
    table.add_column("Backend Service", style="yellow")
    table.add_column("Target Type", style="blue")
    table.add_column("Target Name", style="green")
    table.add_column("Region", style="magenta")
    table.add_column("Status", style="cyan")
    
    for rel in relationships:
        lb_name = rel.get('lb_name', 'N/A')
        bs_name = rel.get('backend_service', 'N/A').split('/')[-1]
        
        if 'cloud_run_service' in rel:
            target_type = "Cloud Run"
            target_name = rel.get('cloud_run_service', 'N/A').split('/')[-1]
        else:
            target_type = "Cloud Functions"
            target_name = rel.get('cloud_function', 'N/A').split('/')[-1]
        
        region = rel.get('region', 'N/A')
        status = rel.get('status', 'UNKNOWN')
        
        status_color = "green" if status == "MAPPED" else "yellow"
        status_str = f"[{status_color}]{status}[/{status_color}]"
        
        table.add_row(lb_name, bs_name, target_type, target_name, region, status_str)
    
    return table


def create_orphaned_table(orphaned: Dict, console) -> Table:
    """Crea tabla de servicios huérfanos."""
    table = Table(
        title="🔴 Orphaned Services (Sin Load Balancer)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Tipo", style="white")
    table.add_column("Nombre", style="yellow")
    table.add_column("Región", style="blue")
    table.add_column("Estado", style="green")
    
    for cr in orphaned.get('cloud_run', []):
        name = cr.get('name', 'N/A')
        if isinstance(name, str) and '/' in name:
            name = name.split('/')[-1]
        else:
            name = str(name) if not isinstance(name, str) else name
        
        region = cr.get('location', 'N/A')
        if isinstance(region, dict):
            region = region.get('name', 'N/A')
        
        status = cr.get('status', 'UNKNOWN')
        if isinstance(status, dict):
            status = status.get('conditions', [{}])[0].get('type', 'UNKNOWN') if status.get('conditions') else 'UNKNOWN'
        
        table.add_row("Cloud Run", str(name), str(region), str(status))
    
    for cf in orphaned.get('cloud_functions', []):
        name = cf.get('name', 'N/A')
        if isinstance(name, str) and '/' in name:
            name = name.split('/')[-1]
        else:
            name = str(name) if not isinstance(name, str) else name
        
        region = cf.get('serviceConfig', {}).get('region', 'N/A')
        if isinstance(region, dict):
            region = region.get('name', 'N/A')
        
        state = cf.get('state', 'UNKNOWN')
        if isinstance(state, dict):
            state = str(state)
        
        table.add_row("Cloud Functions", str(name), str(region), str(state))
    
    return table


def create_health_table(consolidation: Dict, console) -> Table:
    """Crea tabla de salud."""
    table = Table(
        title="💚 Health Status",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Aspecto", style="white")
    table.add_column("Estado", style="cyan")
    
    health = consolidation.get('health_status', {})
    
    table.add_row("Load Balancers Configurados", f"[green]{health.get('lb_configured', 0)}[/green]")
    table.add_row("Backends Mapeados", f"[green]{health.get('backends_mapped', 0)}[/green]")
    table.add_row("Cloud Run Cubierto", f"{health.get('cloud_run_coverage', 0)}%")
    table.add_row("Cloud Functions Cubierto", f"{health.get('cloud_functions_coverage', 0)}%")
    table.add_row("Security Policies", f"[green]{health.get('security_policies_count', 0)}[/green]")
    table.add_row("SSL Configurado", f"[green]{health.get('ssl_configured', 0)}[/green]")
    
    return table


def generate_consolidation(project_id: str, debug: bool = False) -> Dict:
    """Genera consolidado completo."""
    # Extraer datos
    lb_extractor = LoadBalancerExtractor(project_id, debug)
    cr_extractor = CloudRunExtractor(project_id, debug)
    cf_extractor = CloudFunctionsExtractor(project_id, debug)
    
    lb_data = lb_extractor.extract_all()
    cr_data = cr_extractor.extract_all()
    cf_data = cf_extractor.extract_all()
    
    # Mapear relaciones
    mapper = RelationshipMapper(lb_data, cr_data, cf_data)
    relationships = mapper.map_all_relationships()
    
    # Calcular métricas
    total_lb = len(lb_data.get('forwarding_rules', []))
    total_bs = len(lb_data.get('backend_services', []))
    total_cr = len(cr_data.get('services', []))
    total_cf = len(cf_data.get('functions', []))
    total_rel = len(relationships.get('lb_to_cloud_run', [])) + len(relationships.get('lb_to_cloud_functions', []))
    orphaned = len(relationships.get('orphaned_cloud_run', [])) + len(relationships.get('orphaned_cloud_functions', []))
    
    # Calcular health score
    health_score = 100
    if orphaned > 0:
        health_score -= min(20, orphaned * 5)
    if len(lb_data.get('security_policies', [])) == 0:
        health_score -= 15
    if len(lb_data.get('ssl_certificates', [])) == 0:
        health_score -= 15
    
    return {
        "metadata": {
            "tool_name": "GCP Infrastructure Consolidator",
            "version": __version__,
            "project_id": project_id,
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "total_load_balancers": total_lb,
            "total_backend_services": total_bs,
            "total_cloud_run_services": total_cr,
            "total_cloud_functions": total_cf,
            "total_relationships": total_rel,
            "orphaned_services": orphaned,
            "health_score": max(0, health_score)
        },
        "relationships": relationships,
        "orphaned": {
            "cloud_run": relationships.get('orphaned_cloud_run', []),
            "cloud_functions": relationships.get('orphaned_cloud_functions', [])
        },
        "health_status": {
            "lb_configured": total_lb,
            "backends_mapped": total_rel,
            "cloud_run_coverage": int((total_rel / total_cr * 100) if total_cr > 0 else 0),
            "cloud_functions_coverage": int((total_rel / total_cf * 100) if total_cf > 0 else 0),
            "security_policies_count": len(lb_data.get('security_policies', [])),
            "ssl_configured": len(lb_data.get('ssl_certificates', []))
        }
    }


def export_consolidation(consolidation: Dict, project_id: str, output_format: str):
    """Exporta consolidado."""
    output_dir = Path("outcome")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        filepath = output_dir / f"consolidation_{project_id}_{timestamp}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(consolidation, f, indent=2, default=str)
        return str(filepath)
    
    manager = ExportManager("gcp_infrastructure_consolidator", __version__)
    
    if output_format == "json":
        return manager.export_json([consolidation], summary=consolidation.get('summary', {}))
    elif output_format == "csv":
        # Exportar relaciones como CSV
        relationships = consolidation.get('relationships', {})
        all_rels = relationships.get('lb_to_cloud_run', []) + relationships.get('lb_to_cloud_functions', [])
        return manager.export_csv(all_rels)
    elif output_format == "excel":
        return manager.export_excel([consolidation], sheet_name="Consolidation", summary=consolidation.get('summary', {}))


def main():
    """Función principal."""
    if not RICH_AVAILABLE:
        print("❌ Se requiere 'rich'. Instala con: pip install rich")
        sys.exit(1)
    
    console = Console()
    args = get_args()
    
    if args.help:
        console.print(Panel(
            "[bold cyan]GCP Infrastructure Consolidator[/bold cyan]\n\n"
            "Consolida Load Balancers, Cloud Run y Cloud Functions.\n\n"
            "[yellow]Uso:[/yellow]\n"
            "  python gcp_infrastructure_consolidator.py --project mi-proyecto\n"
            "  python gcp_infrastructure_consolidator.py --project mi-proyecto --view relationships\n"
            "  python gcp_infrastructure_consolidator.py --project mi-proyecto --output json",
            border_style="blue"
        ))
        return
    
    project_id = args.project
    view = args.view
    debug = args.debug
    
    console.print(Panel(
        f"[bold cyan]GCP Infrastructure Consolidator v{__version__}[/bold cyan]\n"
        f"Proyecto: [yellow]{project_id}[/yellow]",
        border_style="blue"
    ))
    
    if not check_gcp_connection(project_id, console, debug):
        return
    
    console.print()
    
    # Generar consolidado
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generando consolidado...", total=None)
        consolidation = generate_consolidation(project_id, debug)
    
    console.print()
    
    # Mostrar vistas
    if view in ['all', 'summary']:
        console.print(create_summary_table(consolidation, console))
        console.print()
    
    if view in ['all', 'relationships']:
        relationships = consolidation.get('relationships', {})
        all_rels = relationships.get('lb_to_cloud_run', []) + relationships.get('lb_to_cloud_functions', [])
        if all_rels:
            console.print(create_relationships_table(all_rels, console))
            console.print()
    
    if view in ['all', 'orphaned']:
        orphaned = consolidation.get('orphaned', {})
        if orphaned.get('cloud_run') or orphaned.get('cloud_functions'):
            console.print(create_orphaned_table(orphaned, console))
            console.print()
    
    if view in ['all', 'health']:
        console.print(create_health_table(consolidation, console))
        console.print()
    
    # Exportar si se especificó
    if args.output:
        filepath = export_consolidation(consolidation, project_id, args.output)
        console.print(f"[green]✓ Exportado a:[/green] {filepath}")
    
    console.print(f"[dim]⏱️  Completado[/dim]")


if __name__ == "__main__":
    main()
