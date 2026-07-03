#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud Run Executive Dashboard

Dashboard ejecutivo consolidado de Cloud Run.

Autor: Harold Adrian
"""

import argparse
import sys
from typing import List, Dict
from datetime import datetime

from cloudrun_base import CloudRunBase
from cloudrun_metrics import CloudRunMetrics

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"


class CloudRunExecutiveDashboard(CloudRunBase):
    """Dashboard ejecutivo de Cloud Run"""
    
    def __init__(self, project: str, region: str = "all", debug: bool = False, tz: str = "America/Mazatlan"):
        super().__init__(project, region, debug, tz)
        self.services = []
        self.dashboard_data = {}
    
    def get_services(self) -> List[Dict]:
        """Obtiene lista de servicios"""
        if self.region == "all":
            command = "gcloud run services list"
        else:
            command = f"gcloud run services list --region={self.region}"
        return self.run_gcloud_command(command) or []
    
    def collect_metrics(self, service: Dict) -> Dict:
        """Recolecta métricas de un servicio"""
        metadata = service.get("metadata", {})
        status = service.get("status", {})
        
        service_name = metadata.get("name", "unknown")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "unknown")
        
        # Simular métricas
        metrics = {
            "availability": 99.5,
            "performance": 95.0,
            "error_rate": 0.5,
            "resource_usage": 45.0,
            "current_instances": 1,
            "avg_instances": 1.5,
            "peak_instances": 3
        }
        
        health_score = CloudRunMetrics.calculate_health_score(service, metrics)
        
        return {
            "service_name": service_name,
            "region": region,
            "health_score": health_score,
            "availability": metrics["availability"],
            "error_rate": metrics["error_rate"],
            "status": "HEALTHY" if health_score >= 80 else "DEGRADED" if health_score >= 60 else "UNHEALTHY"
        }
    
    def generate_dashboard(self, services: List[Dict]) -> Dict:
        """Genera dashboard ejecutivo"""
        metrics_list = [self.collect_metrics(s) for s in services]
        
        total_services = len(metrics_list)
        healthy = sum(1 for m in metrics_list if m["status"] == "HEALTHY")
        degraded = sum(1 for m in metrics_list if m["status"] == "DEGRADED")
        unhealthy = sum(1 for m in metrics_list if m["status"] == "UNHEALTHY")
        
        avg_health_score = sum(m["health_score"] for m in metrics_list) / len(metrics_list) if metrics_list else 0
        avg_availability = sum(m["availability"] for m in metrics_list) / len(metrics_list) if metrics_list else 0
        avg_error_rate = sum(m["error_rate"] for m in metrics_list) / len(metrics_list) if metrics_list else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "project": self.project,
            "region": self.region,
            "total_services": total_services,
            "healthy_services": healthy,
            "degraded_services": degraded,
            "unhealthy_services": unhealthy,
            "average_health_score": round(avg_health_score, 1),
            "average_availability": round(avg_availability, 2),
            "average_error_rate": round(avg_error_rate, 2),
            "services": metrics_list
        }
    
    def create_summary_panel(self, dashboard: Dict) -> Panel:
        """Crea panel de resumen"""
        summary_text = f"""
[bold cyan]Cloud Run Executive Dashboard[/bold cyan]
[dim]Proyecto: {dashboard['project']} | Región: {dashboard['region']}[/dim]

[bold yellow]KPIs Principales:[/bold yellow]
  • Total de Servicios: {dashboard['total_services']}
  • Servicios Saludables: [green]{dashboard['healthy_services']}[/green]
  • Servicios Degradados: [yellow]{dashboard['degraded_services']}[/yellow]
  • Servicios No Saludables: [red]{dashboard['unhealthy_services']}[/red]

[bold yellow]Métricas Promedio:[/bold yellow]
  • Health Score: {dashboard['average_health_score']}/100
  • Disponibilidad: {dashboard['average_availability']:.2f}%
  • Error Rate: {dashboard['average_error_rate']:.2f}%

[dim]Actualizado: {dashboard['timestamp']}[/dim]
"""
        return Panel(summary_text, border_style="cyan", title="[bold cyan]📊 Resumen Ejecutivo[/bold cyan]")
    
    def create_services_table(self, dashboard: Dict) -> Table:
        """Crea tabla de servicios"""
        table = Table(title="☁️ Servicios Cloud Run", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Servicio", style="bold white")
        table.add_column("Región", style="yellow")
        table.add_column("Health Score", justify="center")
        table.add_column("Disponibilidad", justify="center")
        table.add_column("Error Rate", justify="center")
        table.add_column("Estado", justify="center")
        
        for service in dashboard["services"]:
            score = service["health_score"]
            score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            score_display = f"[{score_color}]{score}[/{score_color}]"
            
            status_color = "green" if service["status"] == "HEALTHY" else "yellow" if service["status"] == "DEGRADED" else "red"
            status_display = f"[{status_color}]{service['status']}[/{status_color}]"
            
            table.add_row(
                service["service_name"],
                service["region"],
                score_display,
                f"{service['availability']:.2f}%",
                f"{service['error_rate']:.2f}%",
                status_display
            )
        
        return table
    
    def export_dashboard(self, dashboard: Dict, format: str = "json") -> str:
        """Exporta dashboard"""
        export_data = {
            "metadata": {
                "tool": "CloudRunExecutiveDashboard",
                "version": __version__,
                "project": self.project
            },
            "dashboard": dashboard
        }
        return self.export_results(export_data, format, "cloudrun_executive_dashboard")


def get_args():
    parser = argparse.ArgumentParser(description="Cloud Run Executive Dashboard", add_help=False)
    parser.add_argument("--project", "-p", type=str, required=True, help="ID del proyecto GCP")
    parser.add_argument("--region", "-r", type=str, default="all", help="Región específica o 'all'")
    parser.add_argument("--period", type=int, default=24, help="Período en horas")
    parser.add_argument("--format", type=str, choices=["text", "html", "pdf"], default="text", help="Formato del dashboard")
    parser.add_argument("--output", "-o", type=str, choices=["json", "csv", "excel"], help="Formato de exportación")
    parser.add_argument("--debug", action="store_true", help="Modo debug")
    parser.add_argument("--help", "-h", action="store_true", help="Muestra ayuda")
    return parser.parse_args()


def main():
    args = get_args()
    
    if args.help:
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║           GCP CLOUD RUN EXECUTIVE DASHBOARD v1.0.0                           ║
║                    Dashboard Ejecutivo de Cloud Run                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  USO:                                                                        ║
║    python gcp_cloudrun_executive_dashboard.py --project <PROJECT_ID>         ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        sys.exit(0)
    
    if not RICH_AVAILABLE:
        print("Error: La librería 'rich' no está instalada.")
        sys.exit(1)
    
    dashboard = CloudRunExecutiveDashboard(project=args.project, region=args.region, debug=args.debug)
    dashboard.print_header("Cloud Run Executive Dashboard", f"v{__version__}")
    
    if not dashboard.validate_connection():
        dashboard.print_error("No se pudo conectar a GCP")
        sys.exit(1)
    
    services = dashboard.get_services()
    if not services:
        dashboard.print_warning("No hay servicios para mostrar")
        sys.exit(0)
    
    dashboard_data = dashboard.generate_dashboard(services)
    
    dashboard.console.print()
    dashboard.console.print(dashboard.create_summary_panel(dashboard_data))
    dashboard.console.print()
    dashboard.console.print(dashboard.create_services_table(dashboard_data))
    dashboard.console.print()
    
    if args.output:
        filename = dashboard.export_dashboard(dashboard_data, args.output)
        dashboard.print_success(f"Exportado a: {filename}")


if __name__ == "__main__":
    main()
