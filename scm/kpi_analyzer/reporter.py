#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KPI Reporter Module — DevSecOps Toolbox
Generadores de reportes JSON, CSV, HTML

Version: 1.0.0
Author: Harold Adrian
"""

import json
import csv
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


class KPIReporter:
    """Generador de reportes de KPIs"""
    
    def __init__(self, output_dir: Path = None):
        """
        Inicializa el reporter.
        
        Args:
            output_dir: Directorio de salida
        """
        self.output_dir = output_dir or get_output_dir("outcome")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_json(self, data: Dict[str, Any], filename: str = None) -> Path:
        """
        Exporta datos a JSON.
        
        Args:
            data: Datos a exportar
            filename: Nombre del archivo (opcional)
            
        Returns:
            Ruta al archivo generado
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kpi_report_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return filepath
    
    def export_csv(self, data: Dict[str, Any], filename: str = None) -> Path:
        """
        Exporta KPIs a CSV.
        
        Args:
            data: Datos de KPIs
            filename: Nombre del archivo (opcional)
            
        Returns:
            Ruta al archivo generado
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kpi_report_{timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        # Flatten KPIs for CSV
        rows = []
        for kpi in data.get('kpis', []):
            row = {
                'ID': kpi.get('id'),
                'Name': kpi.get('name'),
                'Value': kpi.get('value'),
                'Unit': kpi.get('unit'),
                'Benchmark Elite': kpi.get('benchmarks', {}).get('elite'),
                'Benchmark High': kpi.get('benchmarks', {}).get('high'),
                'Benchmark Medium': kpi.get('benchmarks', {}).get('medium'),
                'Benchmark Low': kpi.get('benchmarks', {}).get('low'),
                'Frameworks': ', '.join(kpi.get('frameworks', [])),
                'Maturity Level Required': kpi.get('maturity_level_required'),
            }
            rows.append(row)
        
        if not rows:
            return filepath
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        return filepath
    
    def export_html_simple(self, data: Dict[str, Any], filename: str = None) -> Path:
        """
        Exporta reporte HTML simple (sin dashboard completo).
        
        Args:
            data: Datos de KPIs
            filename: Nombre del archivo (opcional)
            
        Returns:
            Ruta al archivo generado
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kpi_report_{timestamp}.html"
        
        filepath = self.output_dir / filename
        
        html_content = self._generate_simple_html(data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _generate_simple_html(self, data: Dict[str, Any]) -> str:
        """
        Genera HTML simple para reporte de KPIs.
        
        Args:
            data: Datos de KPIs
            
        Returns:
            Contenido HTML
        """
        metadata = data.get('metadata', {})
        dimensions = data.get('dimensions', {})
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KPI Report — DevSecOps Toolbox</title>
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
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 20px 30px;
            border-bottom: 1px solid #dee2e6;
        }}
        .metadata p {{
            margin: 5px 0;
            color: #6c757d;
        }}
        .dimension {{
            padding: 30px;
            border-bottom: 1px solid #dee2e6;
        }}
        .dimension:last-child {{
            border-bottom: none;
        }}
        .dimension h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        .kpi-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #667eea;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .kpi-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .kpi-card h3 {{
            font-size: 1.2em;
            margin-bottom: 10px;
            color: #2c3e50;
        }}
        .kpi-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .kpi-unit {{
            font-size: 0.9em;
            color: #6c757d;
        }}
        .kpi-benchmarks {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #dee2e6;
        }}
        .benchmark {{
            display: flex;
            justify-content: space-between;
            margin: 5px 0;
            font-size: 0.9em;
        }}
        .benchmark-label {{
            color: #6c757d;
        }}
        .benchmark-value {{
            font-weight: 600;
        }}
        .elite {{ color: #2ecc71; }}
        .high {{ color: #27ae60; }}
        .medium {{ color: #f39c12; }}
        .low {{ color: #e74c3c; }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 KPI Report</h1>
            <p>DevSecOps Toolbox — Análisis de Métricas</p>
        </div>
        
        <div class="metadata">
            <p><strong>Generado:</strong> {metadata.get('generated_at', 'N/A')}</p>
            <p><strong>Plataforma:</strong> {metadata.get('platform', 'all').upper()}</p>
            <p><strong>Versión:</strong> {metadata.get('analyzer_version', '1.0.0')}</p>
        </div>
"""
        
        for dimension_name, dimension_data in dimensions.items():
            html += f"""
        <div class="dimension">
            <h2>{dimension_name.replace('_', ' ').title()}</h2>
            <div class="kpi-grid">
"""
            
            for kpi in dimension_data.get('kpis', []):
                value = kpi.get('value')
                value_str = f"{value:.2f}" if isinstance(value, (int, float)) and value is not None else "N/A"
                unit = kpi.get('unit', '')
                benchmarks = kpi.get('benchmarks', {})
                
                html += f"""
                <div class="kpi-card">
                    <h3>{kpi.get('name', 'N/A')}</h3>
                    <div class="kpi-value">
                        {value_str} <span class="kpi-unit">{unit}</span>
                    </div>
                    <div class="kpi-benchmarks">
                        <div class="benchmark">
                            <span class="benchmark-label">Elite:</span>
                            <span class="benchmark-value elite">{benchmarks.get('elite', 'N/A')}</span>
                        </div>
                        <div class="benchmark">
                            <span class="benchmark-label">High:</span>
                            <span class="benchmark-value high">{benchmarks.get('high', 'N/A')}</span>
                        </div>
                        <div class="benchmark">
                            <span class="benchmark-label">Medium:</span>
                            <span class="benchmark-value medium">{benchmarks.get('medium', 'N/A')}</span>
                        </div>
                        <div class="benchmark">
                            <span class="benchmark-label">Low:</span>
                            <span class="benchmark-value low">{benchmarks.get('low', 'N/A')}</span>
                        </div>
                    </div>
                </div>
"""
            
            html += """
            </div>
        </div>
"""
        
        html += f"""
        <div class="footer">
            <p>Generated by DevSecOps Toolbox KPI Analyzer v1.0.0</p>
            <p>&copy; {datetime.now().year} — All rights reserved</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def save_to_cache(self, data: Dict[str, Any]) -> Path:
        """
        Guarda reporte en caché para análisis histórico.
        
        Args:
            data: Datos de KPIs
            
        Returns:
            Ruta al archivo de caché
        """
        cache_dir = self.output_dir / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"kpi_history_{date_str}_{timestamp}.json"
        
        filepath = cache_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return filepath
