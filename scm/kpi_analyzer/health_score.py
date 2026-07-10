#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Score DORA Calculator
Calcula Health Score usando métricas DORA (Deployment Frequency, Lead Time, MTTR, Change Failure Rate)
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p


class HealthScoreDORA:
    """Calcula Health Score usando métricas DORA"""
    
    def __init__(self, org: Optional[str] = None, project: Optional[str] = None, pat: Optional[str] = None):
        self.org = org
        self.project = project
        self.pat = pat
        self.output_dir = get_output_dir("outcome/kpi_analyzer")
        self.metrics = {}
        self.health_score = 0
    
    def calculate_deployment_frequency(self) -> Dict:
        """
        Calcula frecuencia de despliegue (Deployment Frequency)
        Métrica DORA: Cuántas veces se despliega a producción
        
        Escala:
        - Elite: > 1 vez por día
        - High: 1 vez por semana a 1 vez por día
        - Medium: 1 vez por mes a 1 vez por semana
        - Low: < 1 vez por mes
        """
        try:
            # Simulación de datos (en producción, obtener de AZDO/GitHub)
            deployments_per_day = 2.5
            
            if deployments_per_day > 1:
                level = "Elite"
                score = 100
            elif deployments_per_day >= 0.14:  # 1 por semana
                level = "High"
                score = 75
            elif deployments_per_day >= 0.03:  # 1 por mes
                level = "Medium"
                score = 50
            else:
                level = "Low"
                score = 25
            
            result = {
                "metric": "Deployment Frequency",
                "value": deployments_per_day,
                "unit": "deployments/day",
                "level": level,
                "score": score,
                "description": f"Se despliega {deployments_per_day:.2f} veces por día"
            }
            
            logger.info(f"Deployment Frequency: {level} ({score}/100)")
            return result
        except Exception as e:
            logger.error(f"Error calculando Deployment Frequency: {e}")
            return {"metric": "Deployment Frequency", "score": 0, "error": str(e)}
    
    def calculate_lead_time(self) -> Dict:
        """
        Calcula tiempo de entrega (Lead Time for Changes)
        Métrica DORA: Tiempo desde commit a producción
        
        Escala:
        - Elite: < 1 hora
        - High: 1 hora a 1 día
        - Medium: 1 día a 1 semana
        - Low: > 1 semana
        """
        try:
            # Simulación de datos (en producción, obtener de AZDO/GitHub)
            lead_time_hours = 4.5
            
            if lead_time_hours < 1:
                level = "Elite"
                score = 100
            elif lead_time_hours <= 24:
                level = "High"
                score = 75
            elif lead_time_hours <= 168:  # 1 semana
                level = "Medium"
                score = 50
            else:
                level = "Low"
                score = 25
            
            result = {
                "metric": "Lead Time for Changes",
                "value": lead_time_hours,
                "unit": "hours",
                "level": level,
                "score": score,
                "description": f"Tiempo promedio de entrega: {lead_time_hours:.1f} horas"
            }
            
            logger.info(f"Lead Time: {level} ({score}/100)")
            return result
        except Exception as e:
            logger.error(f"Error calculando Lead Time: {e}")
            return {"metric": "Lead Time for Changes", "score": 0, "error": str(e)}
    
    def calculate_mttr(self) -> Dict:
        """
        Calcula tiempo de recuperación (Mean Time to Recovery)
        Métrica DORA: Tiempo para recuperarse de fallos en producción
        
        Escala:
        - Elite: < 1 hora
        - High: 1 hora a 1 día
        - Medium: 1 día a 1 semana
        - Low: > 1 semana
        """
        try:
            # Simulación de datos (en producción, obtener de AZDO/GitHub)
            mttr_hours = 2.0
            
            if mttr_hours < 1:
                level = "Elite"
                score = 100
            elif mttr_hours <= 24:
                level = "High"
                score = 75
            elif mttr_hours <= 168:  # 1 semana
                level = "Medium"
                score = 50
            else:
                level = "Low"
                score = 25
            
            result = {
                "metric": "Mean Time to Recovery",
                "value": mttr_hours,
                "unit": "hours",
                "level": level,
                "score": score,
                "description": f"Tiempo promedio de recuperación: {mttr_hours:.1f} horas"
            }
            
            logger.info(f"MTTR: {level} ({score}/100)")
            return result
        except Exception as e:
            logger.error(f"Error calculando MTTR: {e}")
            return {"metric": "Mean Time to Recovery", "score": 0, "error": str(e)}
    
    def calculate_change_failure_rate(self) -> Dict:
        """
        Calcula tasa de fallos (Change Failure Rate)
        Métrica DORA: Porcentaje de cambios que causan incidentes
        
        Escala:
        - Elite: 0-15%
        - High: 16-30%
        - Medium: 31-45%
        - Low: > 45%
        """
        try:
            # Simulación de datos (en producción, obtener de AZDO/GitHub)
            failure_rate = 12.5  # porcentaje
            
            if failure_rate <= 15:
                level = "Elite"
                score = 100
            elif failure_rate <= 30:
                level = "High"
                score = 75
            elif failure_rate <= 45:
                level = "Medium"
                score = 50
            else:
                level = "Low"
                score = 25
            
            result = {
                "metric": "Change Failure Rate",
                "value": failure_rate,
                "unit": "%",
                "level": level,
                "score": score,
                "description": f"Tasa de fallos: {failure_rate:.1f}%"
            }
            
            logger.info(f"Change Failure Rate: {level} ({score}/100)")
            return result
        except Exception as e:
            logger.error(f"Error calculando Change Failure Rate: {e}")
            return {"metric": "Change Failure Rate", "score": 0, "error": str(e)}
    
    def get_overall_score(self) -> Dict:
        """Calcula puntuación general de Health Score"""
        try:
            # Calcular todas las métricas
            df = self.calculate_deployment_frequency()
            lt = self.calculate_lead_time()
            mttr = self.calculate_mttr()
            cfr = self.calculate_change_failure_rate()
            
            # Promediar puntuaciones
            scores = [
                df.get("score", 0),
                lt.get("score", 0),
                mttr.get("score", 0),
                cfr.get("score", 0)
            ]
            
            overall_score = sum(scores) / len(scores) if scores else 0
            
            # Determinar nivel general
            if overall_score >= 90:
                overall_level = "Elite"
            elif overall_score >= 75:
                overall_level = "High"
            elif overall_score >= 50:
                overall_level = "Medium"
            else:
                overall_level = "Low"
            
            result = {
                "overall_score": round(overall_score, 2),
                "overall_level": overall_level,
                "metrics": {
                    "deployment_frequency": df,
                    "lead_time": lt,
                    "mttr": mttr,
                    "change_failure_rate": cfr
                },
                "timestamp": datetime.now().isoformat(),
                "organization": self.org,
                "project": self.project
            }
            
            self.health_score = overall_score
            self.metrics = result
            
            logger.info(f"Overall Health Score: {overall_level} ({overall_score:.2f}/100)")
            return result
        except Exception as e:
            logger.error(f"Error calculando Overall Score: {e}")
            return {"error": str(e)}
    
    def export_json(self, filepath: Optional[str] = None) -> bool:
        """Exporta Health Score a JSON"""
        try:
            if not self.metrics:
                self.get_overall_score()
            
            if filepath is None:
                filepath = self.output_dir / "health_score_dora.json"
            else:
                filepath = Path(filepath)
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Health Score exportado a {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exportando JSON: {e}")
            return False
    
    def display_report(self):
        """Muestra reporte de Health Score"""
        if not self.metrics:
            self.get_overall_score()
        
        if RICH_AVAILABLE and console:
            # Tabla de métricas DORA
            table = Table(title="📊 Health Score DORA Metrics", box=None)
            table.add_column("Métrica", style="cyan")
            table.add_column("Valor", style="magenta")
            table.add_column("Nivel", style="yellow")
            table.add_column("Score", style="green")
            
            metrics = self.metrics.get("metrics", {})
            for key, metric in metrics.items():
                table.add_row(
                    metric.get("metric", ""),
                    f"{metric.get('value', 0):.2f} {metric.get('unit', '')}",
                    metric.get("level", ""),
                    f"{metric.get('score', 0)}/100"
                )
            
            console.print(table)
            
            # Panel de puntuación general
            overall = self.metrics.get("overall_score", 0)
            level = self.metrics.get("overall_level", "Unknown")
            
            panel_text = f"[bold green]{overall:.2f}/100[/bold green]\nNivel: [bold yellow]{level}[/bold yellow]"
            console.print(Panel(panel_text, title="🏆 Overall Health Score", expand=False))
        else:
            print("\n📊 Health Score DORA Metrics")
            print("=" * 60)
            metrics = self.metrics.get("metrics", {})
            for key, metric in metrics.items():
                print(f"\n{metric.get('metric', '')}:")
                print(f"  Valor: {metric.get('value', 0):.2f} {metric.get('unit', '')}")
                print(f"  Nivel: {metric.get('level', '')}")
                print(f"  Score: {metric.get('score', 0)}/100")
            
            overall = self.metrics.get("overall_score", 0)
            level = self.metrics.get("overall_level", "Unknown")
            print(f"\n🏆 Overall Health Score: {overall:.2f}/100 ({level})")


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Health Score DORA Calculator")
    parser.add_argument("--org", help="Organización AZDO")
    parser.add_argument("--project", help="Proyecto AZDO")
    parser.add_argument("--pat", help="Personal Access Token")
    parser.add_argument("--output", choices=["json", "display"], default="display", help="Formato de salida")
    
    args = parser.parse_args()
    
    calculator = HealthScoreDORA(org=args.org, project=args.project, pat=args.pat)
    calculator.get_overall_score()
    
    if args.output == "json":
        calculator.export_json()
        print("✅ Health Score exportado a JSON")
    else:
        calculator.display_report()


if __name__ == "__main__":
    main()
