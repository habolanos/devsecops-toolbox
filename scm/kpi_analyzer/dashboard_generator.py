#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Generator Module — DevSecOps Toolbox KPI Analyzer
Generador de dashboard HTML estático con Chart.js

Version: 1.0.0
Author: Harold Adrian
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

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


class DashboardGenerator:
    """Generador de dashboards HTML interactivos"""
    
    def __init__(self, output_dir: Path = None):
        """
        Inicializa el generador de dashboards.
        
        Args:
            output_dir: Directorio de salida
        """
        self.output_dir = output_dir or get_output_dir("outcome")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_dashboard(self, kpi_data: Dict[str, Any], maturity_data: Dict[str, Any] = None, filename: str = None) -> Path:
        """
        Genera un dashboard HTML completo con Chart.js.
        
        Args:
            kpi_data: Datos de KPIs
            maturity_data: Datos de evaluación de madurez (opcional)
            filename: Nombre del archivo (opcional)
            
        Returns:
            Ruta al archivo HTML generado
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kpi_dashboard_{timestamp}.html"
        
        filepath = self.output_dir / filename
        
        html_content = self._generate_dashboard_html(kpi_data, maturity_data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _generate_dashboard_html(self, kpi_data: Dict[str, Any], maturity_data: Dict[str, Any] = None) -> str:
        """
        Genera el contenido HTML del dashboard.
        
        Args:
            kpi_data: Datos de KPIs
            maturity_data: Datos de madurez
            
        Returns:
            Contenido HTML
        """
        metadata = kpi_data.get('metadata', {})
        dimensions = kpi_data.get('dimensions', {})
        
        # Preparar datos para Chart.js
        dimension_names = []
        dimension_scores = []
        dimension_colors = []
        
        color_map = {
            "entrega_continua": "#3498db",
            "confiabilidad": "#2ecc71",
            "seguridad": "#e74c3c",
            "observabilidad": "#f39c12",
            "cumplimiento": "#9b59b6",
            "eficiencia_operativa": "#1abc9c"
        }
        
        for dim_name, dim_data in dimensions.items():
            dimension_names.append(dim_name.replace('_', ' ').title())
            # Calculate average score for dimension
            kpis = dim_data.get('kpis', [])
            if kpis:
                avg_score = sum(k.get('value', 0) or 0 for k in kpis) / len(kpis)
                dimension_scores.append(round(avg_score, 2))
            else:
                dimension_scores.append(0)
            dimension_colors.append(color_map.get(dim_name, "#95a5a6"))
        
        # Preparar datos de KPIs para tabla
        kpis_table_rows = ""
        for kpi in kpi_data.get('kpis', []):
            value = kpi.get('value')
            value_str = f"{value:.2f}" if isinstance(value, (int, float)) and value is not None else "N/A"
            unit = kpi.get('unit', '')
            benchmarks = kpi.get('benchmarks', {})
            
            # Determine badge color based on benchmarks
            badge_color = "#95a5a6"  # Gray default
            if isinstance(value, (int, float)) and value is not None:
                elite = benchmarks.get('elite', '')
                if elite:
                    try:
                        if '>=' in str(elite) or '>' in str(elite):
                            threshold = float(str(elite).replace('>=', '').replace('>', '').strip())
                            if value >= threshold:
                                badge_color = "#2ecc71"  # Green
                        elif '<=' in str(elite) or '<' in str(elite):
                            threshold = float(str(elite).replace('<=', '').replace('<', '').strip())
                            if value <= threshold:
                                badge_color = "#2ecc71"  # Green
                    except:
                        pass
            
            kpis_table_rows += f"""
                <tr>
                    <td><strong>{kpi.get('name', 'N/A')}</strong></td>
                    <td><span class="badge" style="background-color: {badge_color};">{value_str} {unit}</span></td>
                    <td>{benchmarks.get('elite', 'N/A')}</td>
                    <td>{', '.join(kpi.get('frameworks', []))}</td>
                </tr>
            """
        
        # Maturity gauge data
        maturity_level = 0
        maturity_name = "N/A"
        maturity_score = 0
        if maturity_data:
            maturity_level = maturity_data.get('global_level', 0)
            maturity_name = maturity_data.get('global_level_name', 'N/A')
            maturity_score = maturity_data.get('global_score', 0) * 20  # Convert 0-5 to 0-100
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KPI Dashboard — DevSecOps Toolbox</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #2c3e50;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 30px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .header p {{
            color: #6c757d;
            font-size: 1.1em;
        }}
        .metadata {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 20px 30px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
        }}
        .metadata-item {{
            text-align: center;
            padding: 10px 20px;
        }}
        .metadata-item .label {{
            color: #6c757d;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        .metadata-item .value {{
            font-size: 1.3em;
            font-weight: bold;
            color: #667eea;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 25px;
        }}
        .card h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }}
        .chart-container {{
            position: relative;
            height: 350px;
        }}
        .table-container {{
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            color: white;
            font-weight: 600;
            font-size: 0.9em;
        }}
        .footer {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 20px;
        }}
        .gauge-container {{
            position: relative;
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
        }}
        .gauge-label {{
            font-size: 3em;
            font-weight: bold;
            color: #667eea;
            margin-top: 20px;
        }}
        .gauge-sublabel {{
            font-size: 1.2em;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 KPI Dashboard</h1>
            <p>DevSecOps Toolbox — Análisis de Métricas y Madurez</p>
        </div>
        
        <div class="metadata">
            <div class="metadata-item">
                <div class="label">Generado</div>
                <div class="value">{metadata.get('generated_at', 'N/A')[:19]}</div>
            </div>
            <div class="metadata-item">
                <div class="label">Plataforma</div>
                <div class="value">{metadata.get('platform', 'all').upper()}</div>
            </div>
            <div class="metadata-item">
                <div class="label">Versión Analyzer</div>
                <div class="value">{metadata.get('analyzer_version', '1.0.0')}</div>
            </div>
            <div class="metadata-item">
                <div class="label">Total KPIs</div>
                <div class="value">{len(kpi_data.get('kpis', []))}</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>🎯 Nivel de Madurez Global</h2>
                <div class="gauge-container">
                    <canvas id="maturityGauge"></canvas>
                    <div class="gauge-label">{maturity_name}</div>
                    <div class="gauge-sublabel">Nivel {maturity_level}/5</div>
                </div>
            </div>
            
            <div class="card">
                <h2>📈 Scores por Dimensión</h2>
                <div class="chart-container">
                    <canvas id="dimensionChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📊 Radar de Dimensiones</h2>
            <div class="chart-container">
                <canvas id="radarChart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>📋 Detalle de KPIs</h2>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>KPI</th>
                            <th>Valor Actual</th>
                            <th>Benchmark Elite</th>
                            <th>Frameworks</th>
                        </tr>
                    </thead>
                    <tbody>
                        {kpis_table_rows}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by DevSecOps Toolbox KPI Analyzer v1.0.0</p>
            <p>&copy; {datetime.now().year} — All rights reserved</p>
        </div>
    </div>
    
    <script>
        // Maturity Gauge (Doughnut)
        const maturityCtx = document.getElementById('maturityGauge').getContext('2d');
        new Chart(maturityCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Nivel Actual', 'Restante'],
                datasets: [{{
                    data: [{maturity_score:.1f}, {100 - maturity_score:.1f}],
                    backgroundColor: ['#667eea', '#e0e0e0'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        enabled: false
                    }}
                }}
            }}
        }});
        
        // Dimension Bar Chart
        const dimensionCtx = document.getElementById('dimensionChart').getContext('2d');
        new Chart(dimensionCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(dimension_names)},
                datasets: [{{
                    label: 'Score Promedio',
                    data: {json.dumps(dimension_scores)},
                    backgroundColor: {json.dumps(dimension_colors)},
                    borderRadius: 8,
                    borderSkipped: false
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{
                            color: '#f0f0f0'
                        }}
                    }},
                    x: {{
                        grid: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});
        
        // Radar Chart
        const radarCtx = document.getElementById('radarChart').getContext('2d');
        new Chart(radarCtx, {{
            type: 'radar',
            data: {{
                labels: {json.dumps(dimension_names)},
                datasets: [{{
                    label: 'Score Actual',
                    data: {json.dumps(dimension_scores)},
                    fill: true,
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: '#667eea',
                    pointBackgroundColor: '#667eea',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#667eea'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    r: {{
                        beginAtZero: true,
                        grid: {{
                            color: '#f0f0f0'
                        }},
                        angleLines: {{
                            color: '#f0f0f0'
                        }},
                        pointLabels: {{
                            font: {{
                                size: 12
                            }}
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        
        return html
