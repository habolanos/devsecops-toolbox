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
        pr_metrics = metrics.get('pr_metrics', {})
        branch_compliance = metrics.get('branch_compliance', {})
        pipeline_status = metrics.get('pipeline_status', {})
        security = metrics.get('security', {})
        pending_approvals = metrics.get('pending_approvals', {})
        cicd_inventory = metrics.get('cicd_inventory', {})
        prod_deploy = metrics.get('prod_deploy', {})
        
        # Determinar colores según estado
        health_color = self._get_color(health_score)
        pr_approval = pr_metrics.get('approval_rate_percentage', 0) if isinstance(pr_metrics, dict) else 0
        branch_pct = branch_compliance.get('compliance_percentage', 0) if isinstance(branch_compliance, dict) else 0
        pipeline_sr = pipeline_status.get('success_rate', 0) if isinstance(pipeline_status, dict) else 0
        
        sec_vulns = security.get('repo_vulnerabilities', {})
        sec_logs = security.get('pipeline_logs', {})
        vuln_count = sec_vulns.get('total_findings', sec_vulns.get('summary', {}).get('total', 0)) if isinstance(sec_vulns, dict) else 0
        log_alerts = sec_logs.get('total_matches', sec_logs.get('summary', {}).get('total_matches', 0)) if isinstance(sec_logs, dict) else 0
        pending_count = pending_approvals.get('total', 0) if isinstance(pending_approvals, dict) else 0
        overdue_count = prod_deploy.get('pipelines_overdue', 0) if isinstance(prod_deploy, dict) else 0
        
        # Health Score breakdown para radar
        breakdown = metrics.get('health_score', {}).get('breakdown', {}) if isinstance(metrics.get('health_score'), dict) else {}
        
        # Pipeline status para doughnut
        ps_total = pipeline_status.get('total_pipelines', 0) if isinstance(pipeline_status, dict) else 0
        ps_success = pipeline_status.get('successful', 0) if isinstance(pipeline_status, dict) else 0
        ps_failed = pipeline_status.get('failed', 0) if isinstance(pipeline_status, dict) else 0
        ps_progress = pipeline_status.get('in_progress', 0) if isinstance(pipeline_status, dict) else 0
        
        # CI/CD Inventory
        inv_repos = cicd_inventory.get('total_repos', 0) if isinstance(cicd_inventory, dict) else 0
        inv_ci = cicd_inventory.get('total_ci_pipelines', 0) if isinstance(cicd_inventory, dict) else 0
        inv_cd = cicd_inventory.get('total_cd_pipelines', 0) if isinstance(cicd_inventory, dict) else 0
        
        # Prod Deploy
        pd_total = prod_deploy.get('total_pipelines', 0) if isinstance(prod_deploy, dict) else 0
        pd_within = prod_deploy.get('pipelines_within_deadline', 0) if isinstance(prod_deploy, dict) else 0
        pd_overdue = overdue_count
        
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
        
        .section-title {{
            color: #333;
            font-size: 18px;
            font-weight: bold;
            margin: 30px 0 15px 0;
            padding-left: 10px;
            border-left: 4px solid #667eea;
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
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            position: relative;
            height: 350px;
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
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }}
        
        .data-table th {{
            background: #667eea;
            color: white;
            padding: 12px 15px;
            text-align: left;
            font-size: 13px;
            text-transform: uppercase;
        }}
        
        .data-table td {{
            padding: 10px 15px;
            border-bottom: 1px solid #eee;
            color: #333;
            font-size: 13px;
        }}
        
        .data-table tr:hover {{
            background: #f5f5ff;
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
        
        <!-- DORA Metrics -->
        <div class="section-title">🚀 DORA Metrics & Health Score</div>
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
                <h3>Deployment Frequency</h3>
                <div class="metric-value">{metrics.get('health_score', {}).get('deployment_frequency', 0)}</div>
                <div class="metric-unit">/ semana</div>
                <div class="metric-status status-good">DORA</div>
            </div>
            
            <div class="metric-card">
                <h3>MTTR</h3>
                <div class="metric-value">{metrics.get('health_score', {}).get('mttr_hours', 0)}</div>
                <div class="metric-unit">horas</div>
                <div class="metric-status status-excellent">DORA</div>
            </div>
            
            <div class="metric-card">
                <h3>Change Failure Rate</h3>
                <div class="metric-value">{metrics.get('health_score', {}).get('change_failure_rate', 0)}</div>
                <div class="metric-unit">%</div>
                <div class="metric-status status-good">DORA</div>
            </div>
            
            <div class="metric-card">
                <h3>System Uptime</h3>
                <div class="metric-value">{metrics.get('health_score', {}).get('system_uptime', 0)}</div>
                <div class="metric-unit">%</div>
                <div class="metric-status status-excellent">SLO</div>
            </div>
        </div>
        
        <!-- PR & Branch Compliance -->
        <div class="section-title">📬 Pull Requests & Branch Policies</div>
        <div class="metrics-grid">
            <div class="metric-card" style="border-left-color: {self._get_color(pr_approval)};">
                <h3>PR Approval Rate</h3>
                <div class="metric-value" style="color: {self._get_color(pr_approval)};">{pr_approval}</div>
                <div class="metric-unit">%</div>
                <div class="metric-status status-{self._get_status_class(pr_approval)}">
                    {self._get_status_text(pr_approval)}
                </div>
            </div>
            
            <div class="metric-card" style="border-left-color: #17a2b8;">
                <h3>Total PRs</h3>
                <div class="metric-value" style="color: #17a2b8;">{pr_metrics.get('total_prs', 0) if isinstance(pr_metrics, dict) else 0}</div>
                <div class="metric-unit">período</div>
            </div>
            
            <div class="metric-card" style="border-left-color: {self._get_color(branch_pct)};">
                <h3>Branch Compliance</h3>
                <div class="metric-value" style="color: {self._get_color(branch_pct)};">{branch_pct}</div>
                <div class="metric-unit">%</div>
                <div class="metric-status status-{self._get_status_class(branch_pct)}">
                    {self._get_status_text(branch_pct)}
                </div>
            </div>
            
            <div class="metric-card" style="border-left-color: {self._get_color(pipeline_sr)};">
                <h3>Pipeline Success Rate</h3>
                <div class="metric-value" style="color: {self._get_color(pipeline_sr)};">{pipeline_sr}</div>
                <div class="metric-unit">%</div>
                <div class="metric-status status-{self._get_status_class(pipeline_sr)}">
                    {self._get_status_text(pipeline_sr)}
                </div>
            </div>
        </div>
        
        <!-- Security & Approvals -->
        <div class="section-title">🛡️ Security & Approvals</div>
        <div class="metrics-grid">
            <div class="metric-card" style="border-left-color: {'#dc3545' if vuln_count > 0 else '#28a745'};">
                <h3>Repo Vulnerabilities</h3>
                <div class="metric-value" style="color: {'#dc3545' if vuln_count > 0 else '#28a745'};">{vuln_count}</div>
                <div class="metric-unit">findings</div>
                <div class="metric-status status-{'critical' if vuln_count > 0 else 'excellent'}">
                    {'🔴 Requiere atención' if vuln_count > 0 else '✅ Sin vulnerabilidades'}
                </div>
            </div>
            
            <div class="metric-card" style="border-left-color: {'#ffc107' if log_alerts > 0 else '#28a745'};">
                <h3>Pipeline Log Alerts</h3>
                <div class="metric-value" style="color: {'#ffc107' if log_alerts > 0 else '#28a745'};">{log_alerts}</div>
                <div class="metric-unit">coincidencias</div>
                <div class="metric-status status-{'warning' if log_alerts > 0 else 'excellent'}">
                    {'🟡 Revisar logs' if log_alerts > 0 else '✅ Sin alertas'}
                </div>
            </div>
            
            <div class="metric-card" style="border-left-color: {'#dc3545' if pending_count > 5 else '#ffc107' if pending_count > 0 else '#28a745'};">
                <h3>Pending Approvals</h3>
                <div class="metric-value" style="color: {'#dc3545' if pending_count > 5 else '#ffc107' if pending_count > 0 else '#28a745'};">{pending_count}</div>
                <div class="metric-unit">releases</div>
                <div class="metric-status status-{'critical' if pending_count > 5 else 'warning' if pending_count > 0 else 'excellent'}">
                    {'🔴 Crítico' if pending_count > 5 else '🟡 Pendiente' if pending_count > 0 else '✅ Al día'}
                </div>
            </div>
            
            <div class="metric-card" style="border-left-color: {'#dc3545' if overdue_count > 0 else '#28a745'};">
                <h3>Prod Deploy Overdue</h3>
                <div class="metric-value" style="color: {'#dc3545' if overdue_count > 0 else '#28a745'};">{overdue_count}</div>
                <div class="metric-unit">pipelines</div>
                <div class="metric-status status-{'critical' if overdue_count > 0 else 'excellent'}">
                    {'🔴 Vencido' if overdue_count > 0 else '✅ Al día'}
                </div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="section-title">📈 Gráficos</div>
        <div class="charts-grid">
            <div class="chart-container">
                <h3>Health Score Breakdown</h3>
                <canvas id="healthRadar"></canvas>
            </div>
            <div class="chart-container">
                <h3>Pipeline Status</h3>
                <canvas id="pipelineDoughnut"></canvas>
            </div>
            <div class="chart-container">
                <h3>Security Overview</h3>
                <canvas id="securityBar"></canvas>
            </div>
            <div class="chart-container">
                <h3>CI/CD Inventory</h3>
                <canvas id="inventoryBar"></canvas>
            </div>
        </div>
        
        <!-- Alerts -->
        <div class="alerts">
            <h3>🚨 Alertas Activas</h3>
            {self._generate_alerts_html(dashboard_data.get('alerts', {}))}
        </div>
        
        <!-- CI/CD Inventory Table -->
        {self._generate_inventory_table(cicd_inventory)}
        
        <!-- Prod Deploy Table -->
        {self._generate_prod_deploy_table(prod_deploy)}
        
        <div class="footer">
            <p>Dashboard Matutino DevSecOps v2.0 | Generado automáticamente | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </div>

<script>
    // Health Score Radar
    new Chart(document.getElementById('healthRadar'), {{
        type: 'radar',
        data: {{
            labels: ['Deploy Freq', 'Lead Time', 'MTTR', 'CFR', 'Uptime'],
            datasets: [{{
                label: 'Score',
                data: [{breakdown.get('deployment_frequency_score', 0)}, {breakdown.get('lead_time_score', 0)}, {breakdown.get('mttr_score', 0)}, {breakdown.get('cfr_score', 0)}, {breakdown.get('uptime_score', 0)}],
                backgroundColor: 'rgba(102, 126, 234, 0.2)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(102, 126, 234, 1)'
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{ r: {{ beginAtZero: true, max: 100 }} }}
        }}
    }});
    
    // Pipeline Status Doughnut
    new Chart(document.getElementById('pipelineDoughnut'), {{
        type: 'doughnut',
        data: {{
            labels: ['Exitosos', 'Fallidos', 'En progreso'],
            datasets: [{{
                data: [{ps_success}, {ps_failed}, {ps_progress}],
                backgroundColor: ['#28a745', '#dc3545', '#ffc107']
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ position: 'bottom' }} }}
        }}
    }});
    
    // Security Bar
    new Chart(document.getElementById('securityBar'), {{
        type: 'bar',
        data: {{
            labels: ['Repo Vulnerabilities', 'Pipeline Log Alerts', 'Pending Approvals', 'Prod Overdue'],
            datasets: [{{
                label: 'Count',
                data: [{vuln_count}, {log_alerts}, {pending_count}, {overdue_count}],
                backgroundColor: ['rgba(220, 53, 69, 0.6)', 'rgba(255, 193, 7, 0.6)', 'rgba(255, 193, 7, 0.6)', 'rgba(220, 53, 69, 0.6)'],
                borderColor: ['#dc3545', '#ffc107', '#ffc107', '#dc3545'],
                borderWidth: 1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ display: false }} }}
        }}
    }});
    
    // CI/CD Inventory Bar
    new Chart(document.getElementById('inventoryBar'), {{
        type: 'bar',
        data: {{
            labels: ['Repos', 'CI Pipelines', 'CD Pipelines'],
            datasets: [{{
                label: 'Total',
                data: [{inv_repos}, {inv_ci}, {inv_cd}],
                backgroundColor: ['rgba(102, 126, 234, 0.6)', 'rgba(23, 162, 184, 0.6)', 'rgba(40, 167, 69, 0.6)'],
                borderWidth: 1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ display: false }} }}
        }}
    }});
</script>
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
        info = alerts.get('info', [])
        
        if not critical and not warning:
            html += '<div class="alert-item status-excellent">✅ Sin alertas críticas ni advertencias</div>'
        else:
            for alert in critical:
                html += f'<div class="alert-item alert-critical">🔴 {alert}</div>'
            
            for alert in warning:
                html += f'<div class="alert-item alert-warning">🟡 {alert}</div>'
        
        return html
    
    def _generate_inventory_table(self, cicd_inventory):
        """Genera tabla HTML del inventario CI/CD"""
        if not isinstance(cicd_inventory, dict) or not cicd_inventory:
            return ''
        
        repos = cicd_inventory.get('repos', cicd_inventory.get('data', []))
        if not isinstance(repos, list) or not repos:
            return ''
        
        rows_html = ''
        for repo in repos[:20]:
            if not isinstance(repo, dict):
                continue
            rows_html += f"""
            <tr>
                <td>{repo.get('repo_name', repo.get('name', 'N/A'))}</td>
                <td>{repo.get('default_branch', 'N/A')}</td>
                <td>{repo.get('last_commit_date', 'N/A')}</td>
                <td>{repo.get('total_commits', 'N/A')}</td>
            </tr>"""
        
        if not rows_html:
            return ''
        
        return f"""
        <div class="section-title">📋 CI/CD Inventory (Top 20)</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Repository</th>
                    <th>Default Branch</th>
                    <th>Last Commit</th>
                    <th>Total Commits</th>
                </tr>
            </thead>
            <tbody>{rows_html}
            </tbody>
        </table>"""
    
    def _generate_prod_deploy_table(self, prod_deploy):
        """Genera tabla HTML de prod deploy tracking"""
        if not isinstance(prod_deploy, dict) or not prod_deploy:
            return ''
        
        pipelines = prod_deploy.get('pipelines', prod_deploy.get('data', []))
        if not isinstance(pipelines, list) or not pipelines:
            return ''
        
        rows_html = ''
        for p in pipelines[:20]:
            if not isinstance(p, dict):
                continue
            status = p.get('deadline_status', 'N/A')
            status_color = '#dc3545' if 'overdue' in str(status).lower() or 'vencido' in str(status).lower() else '#28a745'
            rows_html += f"""
            <tr>
                <td>{p.get('cd_pipeline_name', p.get('name', 'N/A'))}</td>
                <td>{p.get('last_prod_deploy_date', 'N/A')}</td>
                <td>{p.get('last_prod_deploy_status', 'N/A')}</td>
                <td>{p.get('days_since_prod_deploy', 'N/A')}</td>
                <td style="color: {status_color}; font-weight: bold;">{status}</td>
            </tr>"""
        
        if not rows_html:
            return ''
        
        return f"""
        <div class="section-title">🚀 Prod Deploy Tracking (Top 20)</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Pipeline CD</th>
                    <th>Last Prod Deploy</th>
                    <th>Status</th>
                    <th>Days Since</th>
                    <th>Deadline</th>
                </tr>
            </thead>
            <tbody>{rows_html}
            </tbody>
        </table>"""


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
