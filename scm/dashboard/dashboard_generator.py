#!/usr/bin/env python3
"""
Tool 27: Dashboard Generator
Genera dashboard HTML interactivo a partir de dashboard_data.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import logging

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
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
# -------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DashboardGenerator:
    """Genera dashboard HTML a partir de datos consolidados"""
    
    def __init__(self, input_file=None, output_file=None):
        if input_file is None:
            # Usar directorio centralizado
            output_dir = get_output_dir("outcome/dashboard")
            self.input_file = output_dir / "dashboard_data.json"
        else:
            self.input_file = Path(input_file)
        
        if output_file is None:
            # Usar directorio centralizado
            output_dir = get_output_dir("outcome/dashboard")
            self.output_file = output_dir / "dashboard.html"
        else:
            self.output_file = Path(output_file)
        
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Input: {self.input_file}")
        logger.info(f"Output: {self.output_file}")
    
    def generate(self):
        """Genera el dashboard HTML"""
        try:
            logger.info(f"Leyendo datos de {self.input_file}...")
            
            with open(self.input_file, 'r') as f:
                dashboard_data = json.load(f)
            
            logger.info("Generando HTML...")
            html_content = self._generate_html(dashboard_data)
            
            logger.info(f"Guardando dashboard en {self.output_file}...")
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info("✅ Dashboard generado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error generando dashboard: {str(e)}")
            raise
    
    def _generate_html(self, dashboard_data):
        """Genera contenido HTML del dashboard"""
        metrics = dashboard_data.get('metrics', {})
        summary = dashboard_data.get('summary', {})
        
        health_score = metrics.get('health_score', {}).get('overall_score', 0)
        code_coverage = metrics.get('code_coverage', {}).get('overall_coverage', 0)
        
        # Determinar colores según estado
        health_color = self._get_color(health_score)
        coverage_color = self._get_color(code_coverage)
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Matutino DevSecOps</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
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
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .header h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #666;
            font-size: 14px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-left: 4px solid {health_color};
        }}
        
        .metric-card h3 {{
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
            text-transform: uppercase;
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: {health_color};
            margin-bottom: 5px;
        }}
        
        .metric-unit {{
            color: #999;
            font-size: 12px;
        }}
        
        .metric-status {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-top: 10px;
        }}
        
        .status-excellent {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-good {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        
        .status-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .status-critical {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            position: relative;
            height: 400px;
        }}
        
        .chart-container h3 {{
            margin-bottom: 20px;
            color: #333;
        }}
        
        .alerts {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .alerts h3 {{
            margin-bottom: 15px;
            color: #333;
        }}
        
        .alert-item {{
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 4px;
            border-left: 4px solid;
        }}
        
        .alert-critical {{
            background: #f8d7da;
            border-left-color: #dc3545;
            color: #721c24;
        }}
        
        .alert-warning {{
            background: #fff3cd;
            border-left-color: #ffc107;
            color: #856404;
        }}
        
        .footer {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Dashboard Matutino DevSecOps</h1>
            <p>Última actualización: {dashboard_data.get('timestamp', 'N/A')}</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Health Score</h3>
                <div class="metric-value">{health_score}</div>
                <div class="metric-unit">/ 100</div>
                <div class="metric-status status-{self._get_status_class(health_score)}">
                    {self._get_status_text(health_score)}
                </div>
            </div>
            
            <div class="metric-card">
                <h3>Code Coverage</h3>
                <div class="metric-value">{code_coverage}</div>
                <div class="metric-unit">%</div>
                <div class="metric-status status-{self._get_status_class(code_coverage)}">
                    {self._get_status_text(code_coverage)}
                </div>
            </div>
            
            <div class="metric-card">
                <h3>Deployment Frequency</h3>
                <div class="metric-value">{metrics.get('health_score', {}).get('deployment_frequency', 0)}</div>
                <div class="metric-unit">/ semana</div>
                <div class="metric-status status-good">Bueno</div>
            </div>
            
            <div class="metric-card">
                <h3>MTTR</h3>
                <div class="metric-value">{metrics.get('health_score', {}).get('mttr_hours', 0)}</div>
                <div class="metric-unit">horas</div>
                <div class="metric-status status-excellent">Excelente</div>
            </div>
            
            <div class="metric-card">
                <h3>Change Failure Rate</h3>
                <div class="metric-value">{metrics.get('health_score', {}).get('change_failure_rate', 0)}</div>
                <div class="metric-unit">%</div>
                <div class="metric-status status-good">Bueno</div>
            </div>
            
            <div class="metric-card">
                <h3>System Uptime</h3>
                <div class="metric-value">{metrics.get('health_score', {}).get('system_uptime', 0)}</div>
                <div class="metric-unit">%</div>
                <div class="metric-status status-excellent">Excelente</div>
            </div>
        </div>
        
        <div class="alerts">
            <h3>🚨 Alertas</h3>
            {self._generate_alerts_html(dashboard_data.get('alerts', {}))}
        </div>
        
        <div class="footer">
            <p>Dashboard Matutino DevSecOps v1.0 | Generado automáticamente</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def _get_color(self, score):
        """Obtiene color según score"""
        if score >= 80:
            return '#28a745'  # Verde
        elif score >= 60:
            return '#17a2b8'  # Azul
        elif score >= 40:
            return '#ffc107'  # Amarillo
        else:
            return '#dc3545'  # Rojo
    
    def _get_status_class(self, score):
        """Obtiene clase de estado"""
        if score >= 80:
            return 'excellent'
        elif score >= 60:
            return 'good'
        elif score >= 40:
            return 'warning'
        else:
            return 'critical'
    
    def _get_status_text(self, score):
        """Obtiene texto de estado"""
        if score >= 80:
            return '✅ Excelente'
        elif score >= 60:
            return '🟢 Bueno'
        elif score >= 40:
            return '🟡 Aceptable'
        else:
            return '🔴 Crítico'
    
    def _generate_alerts_html(self, alerts):
        """Genera HTML de alertas"""
        html = ""
        
        critical = alerts.get('critical', [])
        warning = alerts.get('warning', [])
        
        if not critical and not warning:
            html += '<div class="alert-item status-excellent">✅ Sin alertas críticas</div>'
        else:
            for alert in critical:
                html += f'<div class="alert-item alert-critical">🔴 {alert}</div>'
            
            for alert in warning:
                html += f'<div class="alert-item alert-warning">🟡 {alert}</div>'
        
        return html


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dashboard Generator - Tool 27')
    parser.add_argument('--input', default='outcome/dashboard/dashboard_data.json', 
                       help='Archivo de entrada dashboard_data.json')
    parser.add_argument('--output', default='outcome/dashboard/dashboard.html', 
                       help='Archivo de salida HTML')
    
    args = parser.parse_args()
    
    try:
        generator = DashboardGenerator(input_file=args.input, output_file=args.output)
        generator.generate()
        
        print(f"\n✅ Dashboard generado: {args.output}")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    # No usar sys.exit() para permitir que el launcher continúe
    # sys.exit(exit_code)
