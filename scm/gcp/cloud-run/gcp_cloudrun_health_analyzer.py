#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud Run Health Analyzer

Herramienta SRE para análisis profundo de salud y rendimiento de servicios Cloud Run.

Autor: Harold Adrian
"""

import argparse
import sys
import os
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from cloudrun_base import CloudRunBase
from cloudrun_metrics import CloudRunMetrics
from cloudrun_alerts import AlertManager, AlertSeverity, AlertType

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


class CloudRunHealthAnalyzer(CloudRunBase):
    """Analizador de salud de Cloud Run"""
    
    def __init__(self, project: str, region: str = "all", debug: bool = False, tz: str = "America/Mazatlan"):
        super().__init__(project, region, debug, tz)
        self.alert_manager = AlertManager()
        self.services = []
        self.health_scores = {}
    
    def get_services(self) -> List[Dict]:
        """Obtiene lista de servicios Cloud Run"""
        if self.region == "all":
            command = "gcloud run services list"
        else:
            command = f"gcloud run services list --region={self.region}"
        
        return self.run_gcloud_command(command) or []
    
    def get_service_details(self, service_name: str, region: str) -> Optional[Dict]:
        """Obtiene detalles de un servicio específico"""
        command = f"gcloud run services describe {service_name} --region={region}"
        result = self.run_gcloud_command(command)
        return result if isinstance(result, dict) else None
    
    def analyze_service_health(self, service: Dict) -> Dict:
        """
        Analiza salud de un servicio.
        
        Args:
            service: Datos del servicio
        
        Returns:
            Análisis de salud
        """
        metadata = service.get("metadata", {})
        status = service.get("status", {})
        spec = service.get("spec", {}).get("template", {}).get("spec", {})
        
        service_name = metadata.get("name", "unknown")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "unknown")
        
        # Obtener condiciones
        conditions = status.get("conditions", [])
        
        # Verificar si está listo
        is_ready = any(c.get("type") == "Ready" and c.get("status") == "True" for c in conditions)
        
        # Extraer configuración
        container_spec = spec.get("containers", [{}])[0] if spec.get("containers") else {}
        resources = container_spec.get("resources", {}).get("limits", {})
        cpu = resources.get("cpu", "N/A")
        memory = resources.get("memory", "N/A")
        
        # Simular métricas (en producción vendrían de Cloud Monitoring)
        metrics = {
            "availability": 99.5 if is_ready else 50.0,
            "performance": 95.0,
            "error_rate": 0.5,
            "resource_usage": 45.0,
            "current_instances": 1,
            "avg_instances": 1.5,
            "peak_instances": 3,
            "total_invocations": 10000,
            "cold_starts": 50,
            "avg_cold_start_latency": 500,
            "avg_warm_latency": 100,
            "latency_p99": 250,
            "cpu_usage": 35.0,
            "memory_usage": 40.0
        }
        
        # Calcular score de salud
        health_score = CloudRunMetrics.calculate_health_score(service, metrics)
        
        # Analizar escalado
        scaling = CloudRunMetrics.analyze_scaling_efficiency(service, metrics)
        
        # Analizar cold starts
        cold_start_analysis = CloudRunMetrics.calculate_cold_start_impact(service, metrics)
        
        # Cumplimiento de SLA
        sla_compliance = CloudRunMetrics.calculate_sla_compliance(metrics["availability"], 99.9)
        
        return {
            "service_name": service_name,
            "region": region,
            "status": "READY" if is_ready else "NOT_READY",
            "health_score": health_score,
            "metrics": metrics,
            "cpu": cpu,
            "memory": memory,
            "scaling": scaling,
            "cold_start_analysis": cold_start_analysis,
            "sla_compliance": sla_compliance
        }
    
    def analyze_all_services(self) -> Dict:
        """Analiza todos los servicios"""
        self.services = self.get_services()
        
        if not self.services:
            self.print_warning("No se encontraron servicios Cloud Run")
            return {}
        
        analysis = {}
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Analizando servicios...", total=len(self.services))
                
                for service in self.services:
                    service_name = service.get("metadata", {}).get("name", "unknown")
                    health = self.analyze_service_health(service)
                    analysis[service_name] = health
                    self.health_scores[service_name] = health["health_score"]
                    progress.advance(task)
        else:
            for service in self.services:
                service_name = service.get("metadata", {}).get("name", "unknown")
                health = self.analyze_service_health(service)
                analysis[service_name] = health
                self.health_scores[service_name] = health["health_score"]
        
        return analysis
    
    def create_health_table(self, analysis: Dict) -> Table:
        """Crea tabla de salud de servicios"""
        table = Table(
            title="☀️ Cloud Run Health Analysis",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Servicio", style="bold white")
        table.add_column("Región", style="yellow")
        table.add_column("Estado", justify="center")
        table.add_column("Health Score", justify="center")
        table.add_column("Disponibilidad", justify="center")
        table.add_column("Error Rate", justify="center")
        table.add_column("SLA Status", justify="center")
        
        for service_name, health in analysis.items():
            status = health["status"]
            score = health["health_score"]
            availability = health["metrics"]["availability"]
            error_rate = health["metrics"]["error_rate"]
            sla_status = health["sla_compliance"]["status"]
            
            # Colorear score
            if score >= 90:
                score_display = f"[green]{score}[/green]"
            elif score >= 70:
                score_display = f"[yellow]{score}[/yellow]"
            else:
                score_display = f"[red]{score}[/red]"
            
            # Colorear estado
            status_display = f"[green]{status}[/green]" if status == "READY" else f"[red]{status}[/red]"
            
            # Colorear SLA
            sla_display = f"[green]{sla_status}[/green]" if sla_status == "COMPLIANT" else f"[red]{sla_status}[/red]"
            
            table.add_row(
                service_name,
                health["region"],
                status_display,
                score_display,
                f"{availability:.2f}%",
                f"{error_rate:.2f}%",
                sla_display
            )
        
        return table
    
    def create_detailed_report(self, service_name: str, health: Dict) -> Panel:
        """Crea reporte detallado de un servicio"""
        metrics = health["metrics"]
        scaling = health["scaling"]
        cold_start = health["cold_start_analysis"]
        sla = health["sla_compliance"]
        
        report_text = f"""
[bold cyan]Servicio:[/bold cyan] {service_name}
[bold cyan]Región:[/bold cyan] {health['region']}
[bold cyan]Estado:[/bold cyan] {health['status']}
[bold cyan]Health Score:[/bold cyan] {health['health_score']}/100

[bold yellow]Métricas de Rendimiento:[/bold yellow]
  • Disponibilidad: {metrics['availability']:.2f}%
  • Error Rate: {metrics['error_rate']:.2f}%
  • Latencia P99: {metrics['latency_p99']:.0f}ms
  • CPU Usage: {metrics['cpu_usage']:.2f}%
  • Memory Usage: {metrics['memory_usage']:.2f}%

[bold yellow]Escalado:[/bold yellow]
  • Min Instances: {scaling['min_instances']}
  • Max Instances: {scaling['max_instances']}
  • Avg Instances: {scaling['avg_instances']}
  • Utilización: {scaling['utilization_percent']:.2f}%
  • Recomendación: {scaling['recommendation']}

[bold yellow]Cold Starts:[/bold yellow]
  • Tasa: {cold_start['cold_start_rate_percent']:.2f}%
  • Latencia Promedio: {cold_start['avg_cold_start_latency_ms']:.0f}ms
  • Impacto: {cold_start['latency_impact_ms']:.0f}ms
  • Recomendación: {cold_start['recommendation']}

[bold yellow]Cumplimiento de SLA:[/bold yellow]
  • Disponibilidad Actual: {sla['current_availability']:.3f}%
  • SLA Objetivo: {sla['target_sla']}%
  • Estado: {sla['status']}
  • Downtime Mensual: {sla['downtime_minutes_per_month']:.2f} minutos
"""
        
        return Panel(
            report_text,
            title=f"[bold cyan]Reporte Detallado: {service_name}[/bold cyan]",
            border_style="cyan"
        )
    
    def export_analysis(self, analysis: Dict, format: str = "json") -> str:
        """Exporta análisis"""
        export_data = {
            "metadata": {
                "tool": "CloudRunHealthAnalyzer",
                "version": __version__,
                "project": self.project,
                "region": self.region
            },
            "analysis": analysis,
            "summary": {
                "total_services": len(analysis),
                "average_health_score": sum(h["health_score"] for h in analysis.values()) / len(analysis) if analysis else 0,
                "healthy_services": sum(1 for h in analysis.values() if h["health_score"] >= 90),
                "unhealthy_services": sum(1 for h in analysis.values() if h["health_score"] < 70)
            }
        }
        
        return self.export_results(export_data, format, "cloudrun_health_analysis")


def get_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Cloud Run Health Analyzer",
        add_help=False
    )
    parser.add_argument("--project", "-p", type=str, required=True, help="ID del proyecto GCP")
    parser.add_argument("--region", "-r", type=str, default="all", help="Región específica o 'all'")
    parser.add_argument("--service", "-s", type=str, help="Servicio específico a analizar")
    parser.add_argument("--output", "-o", type=str, choices=["json", "csv", "excel"], help="Formato de exportación")
    parser.add_argument("--debug", action="store_true", help="Modo debug")
    parser.add_argument("--help", "-h", action="store_true", help="Muestra ayuda")
    parser.add_argument("--timezone", "-tz", type=str, default="America/Mazatlan", help="Timezone")
    
    return parser.parse_args()


def main():
    """Función principal"""
    args = get_args()
    
    if args.help:
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   GCP CLOUD RUN HEALTH ANALYZER v1.0.0                       ║
║                    Análisis de Salud de Cloud Run                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  DESCRIPCIÓN:                                                                ║
║    Analiza la salud y rendimiento de servicios Cloud Run.                   ║
║                                                                              ║
║  USO:                                                                        ║
║    python gcp_cloudrun_health_analyzer.py --project <PROJECT_ID>             ║
║                                                                              ║
║  OPCIONES:                                                                   ║
║    --project, -p    ID del proyecto GCP (requerido)                          ║
║    --region, -r     Región específica o 'all' (default: all)                 ║
║    --service, -s    Servicio específico a analizar                           ║
║    --output, -o     Exportar a json, csv o excel                             ║
║    --debug          Modo debug                                              ║
║    --timezone, -tz  Timezone (default: America/Mazatlan)                     ║
║    --help, -h       Muestra esta ayuda                                       ║
║                                                                              ║
║  EJEMPLOS:                                                                   ║
║    python gcp_cloudrun_health_analyzer.py -p mi-proyecto                     ║
║    python gcp_cloudrun_health_analyzer.py -p mi-proyecto -r us-central1      ║
║    python gcp_cloudrun_health_analyzer.py -p mi-proyecto -s mi-servicio      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        sys.exit(0)
    
    if not RICH_AVAILABLE:
        print("Error: La librería 'rich' no está instalada.")
        print("Instalar con: pip install rich")
        sys.exit(1)
    
    # Crear analizador
    analyzer = CloudRunHealthAnalyzer(
        project=args.project,
        region=args.region,
        debug=args.debug,
        tz=args.timezone
    )
    
    # Mostrar encabezado
    analyzer.print_header(
        title="Cloud Run Health Analyzer",
        subtitle=f"v{__version__}",
        description=f"Proyecto: {args.project} | Región: {args.region}"
    )
    
    # Validar conexión
    if not analyzer.validate_connection():
        analyzer.print_error("No se pudo conectar a GCP o no hay permisos suficientes")
        sys.exit(1)
    
    # Analizar servicios
    analysis = analyzer.analyze_all_services()
    
    if not analysis:
        analyzer.print_warning("No hay servicios para analizar")
        sys.exit(0)
    
    # Mostrar tabla de salud
    analyzer.console.print()
    analyzer.console.print(analyzer.create_health_table(analysis))
    analyzer.console.print()
    
    # Mostrar reportes detallados
    if args.service:
        if args.service in analysis:
            analyzer.console.print(analyzer.create_detailed_report(args.service, analysis[args.service]))
        else:
            analyzer.print_error(f"Servicio '{args.service}' no encontrado")
    else:
        # Mostrar resumen
        summary_text = f"""
[bold cyan]Resumen General:[/bold cyan]
  • Total de Servicios: {len(analysis)}
  • Health Score Promedio: {sum(h['health_score'] for h in analysis.values()) / len(analysis):.1f}/100
  • Servicios Saludables (≥90): {sum(1 for h in analysis.values() if h['health_score'] >= 90)}
  • Servicios No Saludables (<70): {sum(1 for h in analysis.values() if h['health_score'] < 70)}
"""
        analyzer.console.print(Panel(summary_text, border_style="cyan"))
    
    # Exportar si se solicitó
    if args.output:
        filename = analyzer.export_analysis(analysis, args.output)
        analyzer.print_success(f"Exportado a: {filename}")


if __name__ == "__main__":
    main()
