#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud Run Cost Analyzer

Herramienta SRE para análisis de costos y optimización de recursos.

Autor: Harold Adrian
"""

import argparse
import sys
from typing import List, Dict, Optional

from cloudrun_base import CloudRunBase
from cloudrun_metrics import CloudRunMetrics
from cloudrun_alerts import CostAlertManager, AlertSeverity, AlertType

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


class CloudRunCostAnalyzer(CloudRunBase):
    """Analizador de costos de Cloud Run"""
    
    def __init__(self, project: str, region: str = "all", debug: bool = False, tz: str = "America/Mazatlan"):
        super().__init__(project, region, debug, tz)
        self.alert_manager = CostAlertManager()
        self.services = []
        self.cost_analysis = {}
    
    def get_services(self) -> List[Dict]:
        """Obtiene lista de servicios Cloud Run"""
        if self.region == "all":
            command = "gcloud run services list"
        else:
            command = f"gcloud run services list --region={self.region}"
        
        return self.run_gcloud_command(command) or []
    
    def analyze_service_costs(self, service: Dict) -> Dict:
        """Analiza costos de un servicio"""
        metadata = service.get("metadata", {})
        spec = service.get("spec", {}).get("template", {}).get("spec", {})
        
        service_name = metadata.get("name", "unknown")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "unknown")
        
        # Extraer configuración de recursos
        container_spec = spec.get("containers", [{}])[0] if spec.get("containers") else {}
        resources = container_spec.get("resources", {}).get("limits", {})
        
        cpu = resources.get("cpu", "1")
        memory = resources.get("memory", "512Mi")
        
        # Simular métricas de uso (en producción vendrían de Cloud Monitoring)
        invocations_per_day = 10000
        avg_execution_time_ms = 200
        
        # Calcular CPU-segundos y memoria-segundos
        cpu_seconds_per_day = (invocations_per_day * avg_execution_time_ms / 1000)
        memory_gb_seconds_per_day = (invocations_per_day * avg_execution_time_ms / 1000 * 0.5)  # Asumir 0.5GB
        
        # Calcular costos
        daily_costs = CloudRunMetrics.calculate_costs(
            service,
            region,
            invocations=invocations_per_day,
            cpu_seconds=cpu_seconds_per_day,
            memory_gb_seconds=memory_gb_seconds_per_day
        )
        
        # Proyectar costos mensuales
        monthly_projection = CloudRunMetrics.calculate_monthly_projection(
            daily_cost=daily_costs["total_cost"],
            days_of_data=1
        )
        
        # Analizar oportunidades de optimización
        optimization_opportunities = self._analyze_optimization_opportunities(service, daily_costs)
        
        return {
            "service_name": service_name,
            "region": region,
            "cpu": cpu,
            "memory": memory,
            "invocations_per_day": invocations_per_day,
            "avg_execution_time_ms": avg_execution_time_ms,
            "daily_costs": daily_costs,
            "monthly_projection": monthly_projection,
            "optimization_opportunities": optimization_opportunities
        }
    
    def _analyze_optimization_opportunities(self, service: Dict, costs: Dict) -> List[Dict]:
        """Analiza oportunidades de optimización"""
        opportunities = []
        
        spec = service.get("spec", {}).get("template", {}).get("spec", {})
        template_annotations = service.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
        
        min_instances = int(template_annotations.get("autoscaling.knative.dev/minScale", "0"))
        max_instances = int(template_annotations.get("autoscaling.knative.dev/maxScale", "100"))
        
        # Oportunidad 1: Reducir min_instances
        if min_instances > 0:
            opportunities.append({
                "title": "Reducir min_instances",
                "current_value": min_instances,
                "recommended_value": 0,
                "potential_savings": "Hasta 30% en costos de CPU",
                "risk": "Aumentará cold starts"
            })
        
        # Oportunidad 2: Reducir max_instances
        if max_instances > 100:
            opportunities.append({
                "title": "Reducir max_instances",
                "current_value": max_instances,
                "recommended_value": 100,
                "potential_savings": "Hasta 20% en costos de CPU",
                "risk": "Puede afectar escalabilidad"
            })
        
        # Oportunidad 3: Optimizar CPU
        container_spec = spec.get("containers", [{}])[0] if spec.get("containers") else {}
        resources = container_spec.get("resources", {}).get("limits", {})
        cpu = resources.get("cpu", "1")
        
        if cpu == "4":
            opportunities.append({
                "title": "Reducir CPU allocation",
                "current_value": cpu,
                "recommended_value": "2",
                "potential_savings": "Hasta 50% en costos de CPU",
                "risk": "Puede afectar rendimiento"
            })
        
        return opportunities
    
    def analyze_all_services(self) -> Dict:
        """Analiza costos de todos los servicios"""
        self.services = self.get_services()
        
        if not self.services:
            self.print_warning("No se encontraron servicios Cloud Run")
            return {}
        
        cost_analysis = {}
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Analizando costos...", total=len(self.services))
                
                for service in self.services:
                    service_name = service.get("metadata", {}).get("name", "unknown")
                    analysis = self.analyze_service_costs(service)
                    cost_analysis[service_name] = analysis
                    progress.advance(task)
        else:
            for service in self.services:
                service_name = service.get("metadata", {}).get("name", "unknown")
                analysis = self.analyze_service_costs(service)
                cost_analysis[service_name] = analysis
        
        return cost_analysis
    
    def create_cost_table(self, cost_analysis: Dict) -> Table:
        """Crea tabla de costos"""
        table = Table(
            title="💰 Cloud Run Cost Analysis",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Servicio", style="bold white")
        table.add_column("Región", style="yellow")
        table.add_column("CPU/Mem", style="cyan")
        table.add_column("Costo Diario", justify="right", style="green")
        table.add_column("Proyección Mensual", justify="right", style="green")
        table.add_column("Oportunidades", justify="center")
        
        total_monthly = 0
        
        for service_name, analysis in cost_analysis.items():
            daily_cost = analysis["daily_costs"]["total_cost"]
            monthly_cost = analysis["monthly_projection"]["monthly_projection"]
            opportunities_count = len(analysis["optimization_opportunities"])
            
            total_monthly += monthly_cost
            
            # Colorear costo
            if monthly_cost > 100:
                cost_display = f"[red]${monthly_cost:.2f}[/red]"
            elif monthly_cost > 50:
                cost_display = f"[yellow]${monthly_cost:.2f}[/yellow]"
            else:
                cost_display = f"[green]${monthly_cost:.2f}[/green]"
            
            # Colorear oportunidades
            opp_display = f"[yellow]{opportunities_count}[/yellow]" if opportunities_count > 0 else f"[green]0[/green]"
            
            table.add_row(
                service_name,
                analysis["region"],
                f"{analysis['cpu']}/{analysis['memory']}",
                f"${daily_cost:.4f}",
                cost_display,
                opp_display
            )
        
        # Agregar fila de total
        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            "",
            "",
            f"[bold green]${total_monthly:.2f}[/bold green]",
            ""
        )
        
        return table
    
    def create_opportunities_panel(self, cost_analysis: Dict) -> Panel:
        """Crea panel de oportunidades de optimización"""
        opportunities_text = "[bold cyan]Oportunidades de Optimización:[/bold cyan]\n\n"
        
        total_savings = 0
        for service_name, analysis in cost_analysis.items():
            if analysis["optimization_opportunities"]:
                opportunities_text += f"[bold yellow]{service_name}:[/bold yellow]\n"
                for opp in analysis["optimization_opportunities"]:
                    opportunities_text += f"  • {opp['title']}\n"
                    opportunities_text += f"    Actual: {opp['current_value']} → Recomendado: {opp['recommended_value']}\n"
                    opportunities_text += f"    Ahorro Potencial: {opp['potential_savings']}\n"
                    opportunities_text += f"    Riesgo: {opp['risk']}\n\n"
        
        if not total_savings:
            opportunities_text += "[green]No hay oportunidades de optimización detectadas[/green]"
        
        return Panel(
            opportunities_text,
            border_style="cyan"
        )
    
    def export_analysis(self, cost_analysis: Dict, format: str = "json") -> str:
        """Exporta análisis de costos"""
        total_monthly = sum(a["monthly_projection"]["monthly_projection"] for a in cost_analysis.values())
        
        export_data = {
            "metadata": {
                "tool": "CloudRunCostAnalyzer",
                "version": __version__,
                "project": self.project,
                "region": self.region
            },
            "cost_analysis": cost_analysis,
            "summary": {
                "total_services": len(cost_analysis),
                "total_daily_cost": sum(a["daily_costs"]["total_cost"] for a in cost_analysis.values()),
                "total_monthly_projection": total_monthly,
                "total_yearly_projection": total_monthly * 12,
                "average_service_cost": total_monthly / len(cost_analysis) if cost_analysis else 0
            }
        }
        
        return self.export_results(export_data, format, "cloudrun_cost_analysis")


def get_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Cloud Run Cost Analyzer",
        add_help=False
    )
    parser.add_argument("--project", "-p", type=str, required=True, help="ID del proyecto GCP")
    parser.add_argument("--region", "-r", type=str, default="all", help="Región específica o 'all'")
    parser.add_argument("--compare", type=str, help="Comparar con otro proyecto")
    parser.add_argument("--period", type=int, default=30, help="Período de análisis en días")
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
║                  GCP CLOUD RUN COST ANALYZER v1.0.0                          ║
║                    Análisis de Costos de Cloud Run                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  DESCRIPCIÓN:                                                                ║
║    Analiza costos y proporciona recomendaciones de optimización.            ║
║                                                                              ║
║  USO:                                                                        ║
║    python gcp_cloudrun_cost_analyzer.py --project <PROJECT_ID>               ║
║                                                                              ║
║  OPCIONES:                                                                   ║
║    --project, -p    ID del proyecto GCP (requerido)                          ║
║    --region, -r     Región específica o 'all' (default: all)                 ║
║    --compare        Comparar con otro proyecto                              ║
║    --period         Período de análisis en días (default: 30)                ║
║    --output, -o     Exportar a json, csv o excel                             ║
║    --debug          Modo debug                                              ║
║    --timezone, -tz  Timezone (default: America/Mazatlan)                     ║
║    --help, -h       Muestra esta ayuda                                       ║
║                                                                              ║
║  EJEMPLOS:                                                                   ║
║    python gcp_cloudrun_cost_analyzer.py -p mi-proyecto                       ║
║    python gcp_cloudrun_cost_analyzer.py -p mi-proyecto -r us-central1        ║
║    python gcp_cloudrun_cost_analyzer.py -p prod-project --compare dev-proj   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        sys.exit(0)
    
    if not RICH_AVAILABLE:
        print("Error: La librería 'rich' no está instalada.")
        print("Instalar con: pip install rich")
        sys.exit(1)
    
    # Crear analizador
    analyzer = CloudRunCostAnalyzer(
        project=args.project,
        region=args.region,
        debug=args.debug,
        tz=args.timezone
    )
    
    # Mostrar encabezado
    analyzer.print_header(
        title="Cloud Run Cost Analyzer",
        subtitle=f"v{__version__}",
        description=f"Proyecto: {args.project} | Período: {args.period} días"
    )
    
    # Validar conexión
    if not analyzer.validate_connection():
        analyzer.print_error("No se pudo conectar a GCP o no hay permisos suficientes")
        sys.exit(1)
    
    # Analizar costos
    cost_analysis = analyzer.analyze_all_services()
    
    if not cost_analysis:
        analyzer.print_warning("No hay servicios para analizar")
        sys.exit(0)
    
    # Mostrar tabla de costos
    analyzer.console.print()
    analyzer.console.print(analyzer.create_cost_table(cost_analysis))
    analyzer.console.print()
    
    # Mostrar oportunidades
    analyzer.console.print(analyzer.create_opportunities_panel(cost_analysis))
    analyzer.console.print()
    
    # Exportar si se solicitó
    if args.output:
        filename = analyzer.export_analysis(cost_analysis, args.output)
        analyzer.print_success(f"Exportado a: {filename}")


if __name__ == "__main__":
    main()
