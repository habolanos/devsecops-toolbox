#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Generator Pro
Genera dashboards profesionales en HTML con Chart.js y estilos avanzados
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any
import logging

try:
    from rich.console import Console
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


class DashboardGeneratorPro:
    """Genera dashboards profesionales con Chart.js"""
    
    def __init__(self, data: Optional[Dict[str, Any]] = None, output_dir: Optional[str] = None):
        self.data = data or {}
        self.output_dir = Path(output_dir) if output_dir else get_output_dir("outcome/kpi_analyzer")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Dashboard Generator inicializado")
    
    def generate_html(self, filepath: Optional[str] = None) -> bool:
        """Genera dashboard HTML profesional"""
        try:
            if filepath is None:
                filepath = self.output_dir / f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            else:
                filepath = Path(filepath)
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            html_content = self._generate_html_content()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"✅ Dashboard generado: {filepath}")
            if RICH_AVAILABLE and console:
                console.print(f"[green]✅ Dashboard generado: {filepath}[/green]")
            return True
        except Exception as e:
            logger.error(f"Error generando dashboard: {e}")
            if RICH_AVAILABLE and console:
                console.print(f"[red]❌ Error: {e}[/red]")
            return False
    
    def _generate_html_content(self) -> str:
        """Genera contenido HTML del dashboard"""
        health_score = self.data.get("health_score", {}).get("overall_score", 0)
        health_level = self.data.get("health_score", {}).get("overall_level", "Unknown")
        
        metrics = self.data.get("metrics", {})
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KPI Analyzer Pro Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        
        .header p {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-left: 5px solid #667eea;
        }}
        
        .metric-card h3 {{
            color: #333;
            margin-bottom: 10px;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .metric-unit {{
            color: #999;
            font-size: 0.9em;
        }}
        
        .metric-level {{
            display: inline-block;
            background: #f5f5f5;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.8em;
            color: #666;
            margin-top: 10px;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .chart-container h3 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.2em;
        }}
        
        .health-score-badge {{
            display: inline-block;
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: conic-gradient(#667eea 0deg {health_score * 3.6}deg, #f0f0f0 {health_score * 3.6}deg);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        
        .footer {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            color: #999;
            font-size: 0.9em;
            margin-top: 30px;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 10px;
        }}
        
        .status-elite {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-high {{
            background: #cce5ff;
            color: #004085;
        }}
        
        .status-medium {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .status-low {{
            background: #f8d7da;
            color: #721c24;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 KPI Analyzer Pro Dashboard</h1>
            <p>Análisis integral de DevSecOps con métricas DORA y Health Score</p>
            <p style="color: #999; font-size: 0.9em; margin-top: 10px;">Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>🏆 Health Score</h3>
                <div class="metric-value">{health_score:.1f}</div>
                <div class="metric-unit">/ 100</div>
                <span class="metric-level status-{health_level.lower()}">{health_level}</span>
            </div>
            
            <div class="metric-card">
                <h3>🚀 Deployment Frequency</h3>
                <div class="metric-value">{metrics.get('deployment_frequency', 0):.2f}</div>
                <div class="metric-unit">deployments/day</div>
            </div>
            
            <div class="metric-card">
                <h3>⏱️ Lead Time</h3>
                <div class="metric-value">{metrics.get('lead_time', 0):.1f}</div>
                <div class="metric-unit">hours</div>
            </div>
            
            <div class="metric-card">
                <h3>🔧 MTTR</h3>
                <div class="metric-value">{metrics.get('mttr', 0):.1f}</div>
                <div class="metric-unit">hours</div>
            </div>
            
            <div class="metric-card">
                <h3>❌ Change Failure Rate</h3>
                <div class="metric-value">{metrics.get('change_failure_rate', 0):.1f}</div>
                <div class="metric-unit">%</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <h3>📈 DORA Metrics Comparison</h3>
                <canvas id="doraChart"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>🎯 Health Score Breakdown</h3>
                <canvas id="healthChart"></canvas>
            </div>
        </div>
        
        <div class="footer">
            <p>KPI Analyzer Pro v1.9.6 | DevSecOps Toolbox</p>
            <p>Datos consolidados de múltiples fuentes (AZDO, GCP, AWS, KPI)</p>
        </div>
    </div>
    
    <script>
        // DORA Metrics Chart
        const doraCtx = document.getElementById('doraChart').getContext('2d');
        new Chart(doraCtx, {{
            type: 'radar',
            data: {{
                labels: ['Deployment Frequency', 'Lead Time', 'MTTR', 'Change Failure Rate'],
                datasets: [{{
                    label: 'Current Performance',
                    data: [{metrics.get('deployment_frequency', 0)}, {metrics.get('lead_time', 0)}, {metrics.get('mttr', 0)}, {metrics.get('change_failure_rate', 0)}],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }}
                }},
                scales: {{
                    r: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});
        
        // Health Score Breakdown
        const healthCtx = document.getElementById('healthChart').getContext('2d');
        new Chart(healthCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Health Score', 'Remaining'],
                datasets: [{{
                    data: [{health_score:.1f}, {100 - health_score:.1f}],
                    backgroundColor: ['#667eea', '#f0f0f0'],
                    borderColor: ['#667eea', '#ddd'],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'bottom'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        return html


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dashboard Generator Pro")
    parser.add_argument("--output", help="Directorio de salida")
    
    args = parser.parse_args()
    
    # Datos de ejemplo
    sample_data = {
        "health_score": {
            "overall_score": 85.5,
            "overall_level": "High"
        },
        "metrics": {
            "deployment_frequency": 2.5,
            "lead_time": 4.5,
            "mttr": 2.0,
            "change_failure_rate": 12.5
        }
    }
    
    generator = DashboardGeneratorPro(data=sample_data, output_dir=args.output)
    generator.generate_html()


if __name__ == "__main__":
    main()
