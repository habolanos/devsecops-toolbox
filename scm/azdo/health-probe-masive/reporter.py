"""
Reporter - Genera reportes de validación en múltiples formatos
"""
import json
import logging
import os
from datetime import datetime
from typing import List

import pandas as pd
from rich.console import Console
from rich.table import Table

from .config import OUTPUT_DIR
from .models import HealthCheckResult

logger = logging.getLogger(__name__)


class HealthProbeReporter:
    """Generador de reportes de validación"""
    
    def __init__(self, results: List[HealthCheckResult], console: Console = None):
        self.results = results
        self.console = console or Console()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    def print_summary_table(self):
        """Imprime tabla ejecutiva en consola"""
        table = Table(title="🏥 Health Probe Validation Results", show_header=True, header_style="bold cyan")
        
        table.add_column("Deployment", style="cyan", width=20)
        table.add_column("Stage", style="magenta", width=12)
        table.add_column("Pod Status", justify="center", width=12)
        table.add_column("Probes", justify="center", width=10)
        table.add_column("Conectividad", justify="center", width=12)
        table.add_column("Latencia (ms)", justify="right", width=12)
        table.add_column("Estado", justify="center", width=15)
        
        for result in self.results:
            probes_status = "✅" if (result.liveness_probe and result.readiness_probe) else "⚠️" if (result.liveness_probe or result.readiness_probe) else "❌"
            
            table.add_row(
                result.deployment,
                result.stage,
                result.pod_status_emoji,
                probes_status,
                result.connectivity_emoji,
                f"{result.latency_ms:.0f}",
                result.overall_status
            )
        
        self.console.print(table)
    
    def to_json(self, filepath: str = None) -> bool:
        """Exporta a JSON"""
        if filepath is None:
            filepath = os.path.join(OUTPUT_DIR, "health_probe_report.json")
        
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "total_deployments": len(self.results),
                "healthy": sum(1 for r in self.results if r.overall_status == "✅ HEALTHY"),
                "warning": sum(1 for r in self.results if r.overall_status == "⚠️ WARNING"),
                "critical": sum(1 for r in self.results if r.overall_status == "❌ CRITICAL"),
                "results": [
                    {
                        "deployment": r.deployment,
                        "stage": r.stage,
                        "pod_status": r.pod_status,
                        "pod_count": r.pod_count,
                        "ready_count": r.ready_count,
                        "liveness_probe": r.liveness_probe,
                        "readiness_probe": r.readiness_probe,
                        "connectivity": r.connectivity,
                        "latency_ms": r.latency_ms,
                        "overall_status": r.overall_status,
                        "errors": r.errors,
                        "recommendations": r.recommendations
                    }
                    for r in self.results
                ]
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported JSON report to {filepath}")
            self.console.print(f"[green]✅ JSON report saved to {filepath}[/green]")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            return False
    
    def to_csv(self, filepath: str = None) -> bool:
        """Exporta a CSV"""
        if filepath is None:
            filepath = os.path.join(OUTPUT_DIR, "health_probe_report.csv")
        
        try:
            data = [
                {
                    "Deployment": r.deployment,
                    "Stage": r.stage,
                    "Pod Status": r.pod_status,
                    "Pod Count": r.pod_count,
                    "Ready Count": r.ready_count,
                    "Liveness Probe": r.liveness_probe,
                    "Readiness Probe": r.readiness_probe,
                    "Connectivity": r.connectivity,
                    "Latencia (ms)": f"{r.latency_ms:.2f}",
                    "Overall Status": r.overall_status,
                    "Errors": "; ".join(r.errors) if r.errors else "",
                    "Recommendations": "; ".join(r.recommendations) if r.recommendations else ""
                }
                for r in self.results
            ]
            
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False)
            
            logger.info(f"Exported CSV report to {filepath}")
            self.console.print(f"[green]✅ CSV report saved to {filepath}[/green]")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            return False
    
    def to_html(self, filepath: str = None) -> bool:
        """Exporta a HTML"""
        if filepath is None:
            filepath = os.path.join(OUTPUT_DIR, "health_probe_report.html")
        
        try:
            data = [
                {
                    "Deployment": r.deployment,
                    "Stage": r.stage,
                    "Pod Status": r.pod_status,
                    "Connectivity": r.connectivity,
                    "Latencia (ms)": f"{r.latency_ms:.2f}",
                    "Status": r.overall_status
                }
                for r in self.results
            ]
            
            df = pd.DataFrame(data)
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Health Probe Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                    th {{ background-color: #4CAF50; color: white; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    .healthy {{ color: green; font-weight: bold; }}
                    .warning {{ color: orange; font-weight: bold; }}
                    .critical {{ color: red; font-weight: bold; }}
                    .summary {{ margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <h1>🏥 Health Probe Validation Report</h1>
                <div class="summary">
                    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Total Deployments:</strong> {len(self.results)}</p>
                    <p><strong>Healthy:</strong> <span class="healthy">{sum(1 for r in self.results if r.overall_status == '✅ HEALTHY')}</span></p>
                    <p><strong>Warning:</strong> <span class="warning">{sum(1 for r in self.results if r.overall_status == '⚠️ WARNING')}</span></p>
                    <p><strong>Critical:</strong> <span class="critical">{sum(1 for r in self.results if r.overall_status == '❌ CRITICAL')}</span></p>
                </div>
                {df.to_html(index=False, classes='report-table')}
            </body>
            </html>
            """
            
            with open(filepath, 'w') as f:
                f.write(html_content)
            
            logger.info(f"Exported HTML report to {filepath}")
            self.console.print(f"[green]✅ HTML report saved to {filepath}[/green]")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export HTML: {e}")
            return False
    
    def to_excel(self, filepath: str = None) -> bool:
        """Exporta a Excel con estilos"""
        if filepath is None:
            filepath = os.path.join(OUTPUT_DIR, "health_probe_report.xlsx")
        
        try:
            data = [
                {
                    "Deployment": r.deployment,
                    "Stage": r.stage,
                    "Pod Status": r.pod_status,
                    "Pod Count": r.pod_count,
                    "Ready Count": r.ready_count,
                    "Liveness Probe": "✅" if r.liveness_probe else "❌",
                    "Readiness Probe": "✅" if r.readiness_probe else "❌",
                    "Connectivity": r.connectivity,
                    "Latencia (ms)": f"{r.latency_ms:.2f}",
                    "Overall Status": r.overall_status
                }
                for r in self.results
            ]
            
            df = pd.DataFrame(data)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Health Probe Results')
                
                # Ajustar ancho de columnas
                worksheet = writer.sheets['Health Probe Results']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info(f"Exported Excel report to {filepath}")
            self.console.print(f"[green]✅ Excel report saved to {filepath}[/green]")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export Excel: {e}")
            return False
    
    def export_all(self, base_path: str = None) -> dict:
        """Exporta a todos los formatos"""
        if base_path is None:
            base_path = os.path.join(OUTPUT_DIR, "health_probe_report")
        
        results = {
            "json": self.to_json(f"{base_path}.json"),
            "csv": self.to_csv(f"{base_path}.csv"),
            "html": self.to_html(f"{base_path}.html"),
            "excel": self.to_excel(f"{base_path}.xlsx")
        }
        
        self.console.print("\n[bold cyan]📊 Export Summary:[/bold cyan]")
        for fmt, success in results.items():
            status = "[green]✅[/green]" if success else "[red]❌[/red]"
            self.console.print(f"  {status} {fmt.upper()}")
        
        return results
    
    def generate_recommendations(self) -> List[str]:
        """Genera recomendaciones basadas en resultados"""
        recommendations = []
        
        critical_count = sum(1 for r in self.results if r.overall_status == "❌ CRITICAL")
        warning_count = sum(1 for r in self.results if r.overall_status == "⚠️ WARNING")
        
        if critical_count > 0:
            recommendations.append(f"🔴 {critical_count} deployment(s) en estado CRÍTICO - Acción inmediata requerida")
        
        if warning_count > 0:
            recommendations.append(f"🟡 {warning_count} deployment(s) con advertencias - Revisar y monitorear")
        
        no_probes = sum(1 for r in self.results if not r.liveness_probe or not r.readiness_probe)
        if no_probes > 0:
            recommendations.append(f"⚙️ {no_probes} deployment(s) sin health probes configurados - Agregar probes")
        
        high_latency = sum(1 for r in self.results if r.latency_ms > 5000)
        if high_latency > 0:
            recommendations.append(f"⏱️ {high_latency} endpoint(s) con latencia alta - Revisar red/infraestructura")
        
        if not recommendations:
            recommendations.append("✅ Todos los deployments están en estado saludable")
        
        return recommendations
