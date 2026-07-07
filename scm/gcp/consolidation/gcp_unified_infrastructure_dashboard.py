#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Unified Infrastructure Dashboard v1.0.0

Dashboard ejecutivo unificado para Load Balancers, Cloud Run y Cloud Functions.
Proporciona topología de tráfico, alertas automáticas y recomendaciones.

Uso:
    python gcp_unified_infrastructure_dashboard.py --project mi-proyecto
    python gcp_unified_infrastructure_dashboard.py --project mi-proyecto --interactive

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
    from rich.layout import Layout
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from consolidation_base import (
    LoadBalancerExtractor, CloudRunExtractor, CloudFunctionsExtractor,
    RelationshipMapper
)

__version__ = "1.0.0"
__author__ = "Harold Adrian"


def get_args():
    parser = argparse.ArgumentParser(
        description="GCP Unified Infrastructure Dashboard",
        add_help=False
    )
    parser.add_argument("--project", "-p", type=str, default="cpl-corp-cial-prod-17042024")
    parser.add_argument("--interactive", "-i", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--timezone", "-tz", type=str, default="America/Mazatlan")
    parser.add_argument("--help", "-h", action="store_true")
    return parser.parse_args()


def check_gcp_connection(project_id: str, console, debug: bool = False) -> bool:
    """Verifica conexión a GCP."""
    try:
        import subprocess
        
        # Verificar sesión activa
        auth_cmd = 'gcloud auth list --filter=status:ACTIVE --format="value(account)"'
        auth_result = subprocess.run(auth_cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if auth_result.returncode != 0 or not auth_result.stdout.strip():
            console.print("[red]❌ No hay sesión activa de gcloud[/red]")
            return False
        
        console.print(f"[green]✓[/green] Sesión activa")
        
        # Verificar acceso al proyecto
        project_cmd = f'gcloud projects describe {project_id} --format="value(projectId)" 2>&1'
        project_result = subprocess.run(project_cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if project_result.returncode != 0:
            console.print(f"[red]❌ No tienes acceso al proyecto: {project_id}[/red]")
            return False
        
        console.print(f"[green]✓[/green] Proyecto accesible: [cyan]{project_id}[/cyan]")
        return True
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        return False


def create_executive_summary(consolidation: Dict) -> Panel:
    """Crea resumen ejecutivo."""
    summary = consolidation.get('summary', {})
    health = consolidation.get('health_status', {})
    
    content = f"""
[bold cyan]📊 EXECUTIVE SUMMARY[/bold cyan]

[yellow]Infrastructure Overview:[/yellow]
  • Load Balancers: [cyan]{summary.get('total_load_balancers', 0)}[/cyan]
  • Backend Services: [cyan]{summary.get('total_backend_services', 0)}[/cyan]
  • Cloud Run Services: [cyan]{summary.get('total_cloud_run_services', 0)}[/cyan]
  • Cloud Functions: [cyan]{summary.get('total_cloud_functions', 0)}[/cyan]

[yellow]Connectivity:[/yellow]
  • Mapped Relationships: [green]{summary.get('total_relationships', 0)}[/green]
  • Orphaned Services: [red]{summary.get('orphaned_services', 0)}[/red]
  • Health Score: [bold]{summary.get('health_score', 0)}%[/bold]

[yellow]Security:[/yellow]
  • Cloud Armor Policies: [cyan]{health.get('security_policies_count', 0)}[/cyan]
  • SSL Certificates: [cyan]{health.get('ssl_configured', 0)}[/cyan]
  • Cloud Run Coverage: [cyan]{health.get('cloud_run_coverage', 0)}%[/cyan]
  • Cloud Functions Coverage: [cyan]{health.get('cloud_functions_coverage', 0)}%[/cyan]
"""
    
    return Panel(content, border_style="blue", title="[bold]GCP Infrastructure Dashboard[/bold]")


def create_traffic_topology(consolidation: Dict) -> Panel:
    """Crea topología de tráfico."""
    relationships = consolidation.get('relationships', {})
    cr_rels = relationships.get('lb_to_cloud_run', [])
    cf_rels = relationships.get('lb_to_cloud_functions', [])
    
    content = "[bold cyan]🌐 TRAFFIC TOPOLOGY[/bold cyan]\n\n"
    
    if cr_rels:
        content += "[yellow]Cloud Run Backends:[/yellow]\n"
        for rel in cr_rels[:5]:
            lb = rel.get('lb_name', 'N/A')
            cr = rel.get('cloud_run_service', 'N/A').split('/')[-1]
            region = rel.get('region', 'N/A')
            content += f"  {lb} → {cr} ({region})\n"
        if len(cr_rels) > 5:
            content += f"  ... y {len(cr_rels) - 5} más\n"
    
    if cf_rels:
        content += "\n[yellow]Cloud Functions Backends:[/yellow]\n"
        for rel in cf_rels[:5]:
            lb = rel.get('lb_name', 'N/A')
            cf = rel.get('cloud_function', 'N/A').split('/')[-1]
            region = rel.get('region', 'N/A')
            content += f"  {lb} → {cf} ({region})\n"
        if len(cf_rels) > 5:
            content += f"  ... y {len(cf_rels) - 5} más\n"
    
    return Panel(content, border_style="green")


def create_alerts_panel(consolidation: Dict) -> Panel:
    """Crea panel de alertas."""
    alerts = []
    summary = consolidation.get('summary', {})
    health = consolidation.get('health_status', {})
    
    # Alerta 1: Servicios huérfanos
    if summary.get('orphaned_services', 0) > 0:
        alerts.append({
            'severity': 'HIGH',
            'message': f"{summary.get('orphaned_services')} servicios sin Load Balancer"
        })
    
    # Alerta 2: Sin Cloud Armor
    if health.get('security_policies_count', 0) == 0:
        alerts.append({
            'severity': 'CRITICAL',
            'message': 'Cloud Armor no configurado'
        })
    
    # Alerta 3: Sin SSL
    if health.get('ssl_configured', 0) == 0:
        alerts.append({
            'severity': 'CRITICAL',
            'message': 'SSL/TLS no configurado'
        })
    
    # Alerta 4: Cobertura baja
    if health.get('cloud_run_coverage', 0) < 50:
        alerts.append({
            'severity': 'MEDIUM',
            'message': f"Cloud Run coverage bajo: {health.get('cloud_run_coverage', 0)}%"
        })
    
    content = "[bold cyan]🚨 ALERTS & WARNINGS[/bold cyan]\n\n"
    
    if alerts:
        for alert in alerts:
            severity = alert['severity']
            if severity == 'CRITICAL':
                icon = "🔴"
                color = "red"
            elif severity == 'HIGH':
                icon = "🟠"
                color = "yellow"
            else:
                icon = "🟡"
                color = "yellow"
            
            content += f"{icon} [{color}]{alert['message']}[/{color}]\n"
    else:
        content += "[green]✓ No hay alertas[/green]"
    
    return Panel(content, border_style="red")


def create_recommendations_panel(consolidation: Dict) -> Panel:
    """Crea panel de recomendaciones."""
    recommendations = []
    summary = consolidation.get('summary', {})
    health = consolidation.get('health_status', {})
    
    # Recomendación 1
    if summary.get('orphaned_services', 0) > 0:
        recommendations.append(
            "Mapear servicios huérfanos a Load Balancers o eliminarlos"
        )
    
    # Recomendación 2
    if health.get('security_policies_count', 0) == 0:
        recommendations.append(
            "Habilitar Cloud Armor en todos los backends públicos"
        )
    
    # Recomendación 3
    if health.get('cloud_run_coverage', 0) < 80:
        recommendations.append(
            "Aumentar cobertura de Cloud Run con Load Balancers"
        )
    
    # Recomendación 4
    if summary.get('health_score', 0) < 80:
        recommendations.append(
            "Revisar configuración de seguridad y cobertura"
        )
    
    content = "[bold cyan]💡 RECOMMENDATIONS[/bold cyan]\n\n"
    
    for i, rec in enumerate(recommendations, 1):
        content += f"{i}. {rec}\n"
    
    if not recommendations:
        content += "[green]✓ Infraestructura bien configurada[/green]"
    
    return Panel(content, border_style="yellow")


def create_metrics_table(consolidation: Dict) -> Table:
    """Crea tabla de métricas."""
    table = Table(
        title="📈 Key Metrics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Métrica", style="white")
    table.add_column("Valor", style="cyan", justify="right")
    table.add_column("Estado", style="green", justify="center")
    
    summary = consolidation.get('summary', {})
    health = consolidation.get('health_status', {})
    
    metrics = [
        ("Load Balancers", str(summary.get('total_load_balancers', 0)), "✓"),
        ("Backend Services", str(summary.get('total_backend_services', 0)), "✓"),
        ("Cloud Run Services", str(summary.get('total_cloud_run_services', 0)), "✓"),
        ("Cloud Functions", str(summary.get('total_cloud_functions', 0)), "✓"),
        ("Mapped Relationships", str(summary.get('total_relationships', 0)), "✓"),
        ("Orphaned Services", str(summary.get('orphaned_services', 0)), "⚠" if summary.get('orphaned_services', 0) > 0 else "✓"),
        ("Cloud Run Coverage", f"{health.get('cloud_run_coverage', 0)}%", "✓" if health.get('cloud_run_coverage', 0) >= 80 else "⚠"),
        ("Cloud Functions Coverage", f"{health.get('cloud_functions_coverage', 0)}%", "✓" if health.get('cloud_functions_coverage', 0) >= 80 else "⚠"),
        ("Security Policies", str(health.get('security_policies_count', 0)), "✓" if health.get('security_policies_count', 0) > 0 else "✗"),
        ("SSL Certificates", str(health.get('ssl_configured', 0)), "✓" if health.get('ssl_configured', 0) > 0 else "✗"),
    ]
    
    for metric, value, status in metrics:
        table.add_row(metric, value, status)
    
    return table


def generate_consolidation(project_id: str, debug: bool = False) -> Dict:
    """Genera consolidado."""
    lb_extractor = LoadBalancerExtractor(project_id, debug)
    cr_extractor = CloudRunExtractor(project_id, debug)
    cf_extractor = CloudFunctionsExtractor(project_id, debug)
    
    lb_data = lb_extractor.extract_all()
    cr_data = cr_extractor.extract_all()
    cf_data = cf_extractor.extract_all()
    
    mapper = RelationshipMapper(lb_data, cr_data, cf_data)
    relationships = mapper.map_all_relationships()
    
    total_lb = len(lb_data.get('forwarding_rules', []))
    total_bs = len(lb_data.get('backend_services', []))
    total_cr = len(cr_data.get('services', []))
    total_cf = len(cf_data.get('functions', []))
    total_rel = len(relationships.get('lb_to_cloud_run', [])) + len(relationships.get('lb_to_cloud_functions', []))
    orphaned = len(relationships.get('orphaned_cloud_run', [])) + len(relationships.get('orphaned_cloud_functions', []))
    
    health_score = 100
    if orphaned > 0:
        health_score -= min(20, orphaned * 5)
    if len(lb_data.get('security_policies', [])) == 0:
        health_score -= 15
    if len(lb_data.get('ssl_certificates', [])) == 0:
        health_score -= 15
    
    return {
        "metadata": {
            "tool_name": "GCP Unified Infrastructure Dashboard",
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
        "health_status": {
            "lb_configured": total_lb,
            "backends_mapped": total_rel,
            "cloud_run_coverage": int((total_rel / total_cr * 100) if total_cr > 0 else 0),
            "cloud_functions_coverage": int((total_rel / total_cf * 100) if total_cf > 0 else 0),
            "security_policies_count": len(lb_data.get('security_policies', [])),
            "ssl_configured": len(lb_data.get('ssl_certificates', []))
        }
    }


def main():
    """Función principal."""
    if not RICH_AVAILABLE:
        print("❌ Se requiere 'rich'. Instala con: pip install rich")
        sys.exit(1)
    
    console = Console()
    args = get_args()
    
    if args.help:
        console.print(Panel(
            "[bold cyan]GCP Unified Infrastructure Dashboard[/bold cyan]\n\n"
            "Dashboard ejecutivo para Load Balancers, Cloud Run y Cloud Functions.\n\n"
            "[yellow]Uso:[/yellow]\n"
            "  python gcp_unified_infrastructure_dashboard.py --project mi-proyecto\n"
            "  python gcp_unified_infrastructure_dashboard.py --project mi-proyecto --interactive",
            border_style="blue"
        ))
        return
    
    project_id = args.project
    debug = args.debug
    
    console.print(Panel(
        f"[bold cyan]GCP Unified Infrastructure Dashboard v{__version__}[/bold cyan]\n"
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
        task = progress.add_task("Generando dashboard...", total=None)
        consolidation = generate_consolidation(project_id, debug)
    
    console.print()
    
    # Mostrar dashboard
    console.print(create_executive_summary(consolidation))
    console.print()
    
    console.print(create_traffic_topology(consolidation))
    console.print()
    
    console.print(create_alerts_panel(consolidation))
    console.print()
    
    console.print(create_recommendations_panel(consolidation))
    console.print()
    
    console.print(create_metrics_table(consolidation))
    console.print()
    
    console.print(f"[dim]⏱️  Completado | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")


if __name__ == "__main__":
    main()
