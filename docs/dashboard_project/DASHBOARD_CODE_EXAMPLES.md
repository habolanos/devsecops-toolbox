# EJEMPLOS DE CÓDIGO - Dashboard Matutino

## 🚀 Estructura Base para Tool 26: Dashboard Consolidator

### dashboard_consolidator.py

```python
#!/usr/bin/env python3
"""
Tool 26: Dashboard Consolidator
Orquesta la ejecución de múltiples herramientas y consolida outputs.
"""

import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DashboardConsolidator:
    """Orquesta la ejecución de herramientas y consolida datos."""
    
    def __init__(self, org: str, project: str, pat: str, 
                 gcp_project: Optional[str] = None, 
                 aws_profile: Optional[str] = None):
        self.org = org
        self.project = project
        self.pat = pat
        self.gcp_project = gcp_project
        self.aws_profile = aws_profile
        self.output_dir = Path("outcome/dashboard")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def run_all_tools(self) -> Dict[str, Any]:
        """Ejecuta todas las herramientas en paralelo."""
        logger.info("Iniciando ejecución de herramientas en paralelo...")
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                'ci_inventory': executor.submit(self._run_tool_14),
                'cd_inventory': executor.submit(self._run_tool_15),
                'health_score': executor.submit(self._run_tool_16),
                'branch_policy': executor.submit(self._run_tool_1),
                'branch_locks': executor.submit(self._run_tool_2b),
                'gcp_monitor': executor.submit(self._run_gcp_tool_1),
                'sql_disk': executor.submit(self._run_gcp_tool_7),
                'rds_status': executor.submit(self._run_aws_tool_4),
                'pr_metrics': executor.submit(self._run_tool_28),
            }
            
            results = {}
            for key, future in futures.items():
                try:
                    logger.info(f"Esperando resultado de {key}...")
                    results[key] = future.result(timeout=300)
                    logger.info(f"✓ {key} completado")
                except Exception as e:
                    logger.error(f"✗ {key} falló: {str(e)}")
                    results[key] = {'error': str(e), 'status': 'failed'}
        
        return results
    
    def _run_tool_14(self) -> Dict[str, Any]:
        """Ejecuta Tool 14: CI Inventory."""
        try:
            # Intenta usar cache primero
            cache_file = Path("outcome/ci_raw.json")
            if cache_file.exists():
                with open(cache_file) as f:
                    logger.info("Usando cache de CI Inventory")
                    return json.load(f)
            
            # Si no hay cache, ejecuta la herramienta
            logger.info("Ejecutando Tool 14: CI Inventory...")
            # Aquí iría la lógica de ejecución real
            return {'status': 'success', 'repos': []}
        except Exception as e:
            logger.error(f"Error en Tool 14: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _run_tool_15(self) -> Dict[str, Any]:
        """Ejecuta Tool 15: CD Inventory."""
        try:
            cache_file = Path("outcome/cd_raw.json")
            if cache_file.exists():
                with open(cache_file) as f:
                    logger.info("Usando cache de CD Inventory")
                    return json.load(f)
            
            logger.info("Ejecutando Tool 15: CD Inventory...")
            return {'status': 'success', 'repos': []}
        except Exception as e:
            logger.error(f"Error en Tool 15: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _run_tool_16(self) -> Dict[str, Any]:
        """Ejecuta Tool 16: Health Score."""
        try:
            logger.info("Ejecutando Tool 16: Health Score...")
            return {'status': 'success', 'overall_score': 75}
        except Exception as e:
            logger.error(f"Error en Tool 16: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _run_tool_1(self) -> Dict[str, Any]:
        """Ejecuta Tool 1: Branch Policy Checker."""
        try:
            logger.info("Ejecutando Tool 1: Branch Policy Checker...")
            return {'status': 'success', 'compliance_percentage': 85}
        except Exception as e:
            logger.error(f"Error en Tool 1: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _run_tool_2b(self) -> Dict[str, Any]:
        """Ejecuta Tool 2b: Branch Lock Checker."""
        try:
            logger.info("Ejecutando Tool 2b: Branch Lock Checker...")
            return {'status': 'success', 'locked_branches': []}
        except Exception as e:
            logger.error(f"Error en Tool 2b: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _run_gcp_tool_1(self) -> Dict[str, Any]:
        """Ejecuta GCP Tool 1: Monitor."""
        try:
            logger.info("Ejecutando GCP Tool 1: Monitor...")
            return {'status': 'success', 'services': []}
        except Exception as e:
            logger.error(f"Error en GCP Tool 1: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _run_gcp_tool_7(self) -> Dict[str, Any]:
        """Ejecuta GCP Tool 7: Cloud SQL Disk Monitor."""
        try:
            logger.info("Ejecutando GCP Tool 7: Cloud SQL Disk Monitor...")
            return {'status': 'success', 'databases': []}
        except Exception as e:
            logger.error(f"Error en GCP Tool 7: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _run_aws_tool_4(self) -> Dict[str, Any]:
        """Ejecuta AWS Tool 4: RDS Checker."""
        try:
            logger.info("Ejecutando AWS Tool 4: RDS Checker...")
            return {'status': 'success', 'instances': []}
        except Exception as e:
            logger.error(f"Error en AWS Tool 4: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def _run_tool_28(self) -> Dict[str, Any]:
        """Ejecuta Tool 28: PR Metrics Analyzer."""
        try:
            logger.info("Ejecutando Tool 28: PR Metrics Analyzer...")
            return {
                'status': 'success',
                'total_prs': 150,
                'avg_time_to_merge_hours': 24.5,
                'sla_compliance': 95.2
            }
        except Exception as e:
            logger.error(f"Error en Tool 28: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def consolidate(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Consolida todos los resultados en un JSON único."""
        logger.info("Consolidando resultados...")
        
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'status': 'success' if all(
                r.get('status') != 'failed' for r in results.values()
            ) else 'partial',
            'data': {
                'azdo': {
                    'ci_inventory': results.get('ci_inventory'),
                    'cd_inventory': results.get('cd_inventory'),
                    'health_score': results.get('health_score'),
                    'branch_policy': results.get('branch_policy'),
                    'branch_locks': results.get('branch_locks'),
                    'pr_metrics': results.get('pr_metrics'),
                },
                'gcp': {
                    'monitor': results.get('gcp_monitor'),
                    'sql_disk': results.get('sql_disk'),
                },
                'aws': {
                    'rds_status': results.get('rds_status'),
                },
            },
            'summary': self._generate_summary(results),
        }
        
        # Guardar archivo con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.output_dir / f"dashboard_data_{timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        
        logger.info(f"Dashboard consolidado guardado en: {output_file}")
        return dashboard_data
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Genera resumen ejecutivo."""
        ci_data = results.get('ci_inventory', {})
        cd_data = results.get('cd_inventory', {})
        health = results.get('health_score', {})
        branch = results.get('branch_policy', {})
        pr = results.get('pr_metrics', {})
        
        repos = ci_data.get('repos', [])
        repos_with_ci = len([r for r in repos if r.get('ci_pipeline')])
        repos_with_cd = len([r for r in repos if r.get('cd_pipeline')])
        repos_without_pipeline = len([r for r in repos 
                                     if not r.get('ci_pipeline') and not r.get('cd_pipeline')])
        
        return {
            'total_repos': len(repos),
            'repos_with_ci': repos_with_ci,
            'repos_with_cd': repos_with_cd,
            'repos_without_pipeline': repos_without_pipeline,
            'health_score': health.get('overall_score', 0),
            'branch_compliance': branch.get('compliance_percentage', 0),
            'pr_avg_time_to_merge_hours': pr.get('avg_time_to_merge_hours', 0),
            'pr_sla_compliance': pr.get('sla_compliance', 0),
        }
    
    def run(self) -> Dict[str, Any]:
        """Ejecuta el flujo completo."""
        try:
            logger.info("=" * 60)
            logger.info("INICIANDO CONSOLIDACIÓN DE DASHBOARD")
            logger.info("=" * 60)
            
            results = self.run_all_tools()
            dashboard_data = self.consolidate(results)
            
            logger.info("=" * 60)
            logger.info("CONSOLIDACIÓN COMPLETADA")
            logger.info("=" * 60)
            
            return dashboard_data
        except Exception as e:
            logger.error(f"Error fatal: {e}")
            raise


def main():
    """Punto de entrada."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Dashboard Consolidator - Tool 26'
    )
    parser.add_argument('--org', required=True, help='Azure DevOps organization')
    parser.add_argument('--project', required=True, help='Azure DevOps project')
    parser.add_argument('--pat', required=True, help='Azure DevOps PAT')
    parser.add_argument('--gcp-project', help='GCP project ID')
    parser.add_argument('--aws-profile', help='AWS profile name')
    
    args = parser.parse_args()
    
    consolidator = DashboardConsolidator(
        org=args.org,
        project=args.project,
        pat=args.pat,
        gcp_project=args.gcp_project,
        aws_profile=args.aws_profile
    )
    
    dashboard_data = consolidator.run()
    print(json.dumps(dashboard_data['summary'], indent=2))


if __name__ == '__main__':
    main()
```

---

## 🎨 Estructura Base para Tool 27: Dashboard Generator

### dashboard_generator.py

```python
#!/usr/bin/env python3
"""
Tool 27: Dashboard Generator
Genera HTML interactivo desde dashboard_data.json.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from jinja2 import Template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DashboardGenerator:
    """Genera dashboard HTML desde datos consolidados."""
    
    def __init__(self, input_file: str, output_file: str = None):
        self.input_file = Path(input_file)
        self.output_file = Path(output_file or "outcome/dashboard/dashboard.html")
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
    def load_data(self) -> dict:
        """Carga dashboard_data.json."""
        logger.info(f"Cargando datos desde {self.input_file}...")
        with open(self.input_file) as f:
            return json.load(f)
    
    def generate(self):
        """Genera el HTML del dashboard."""
        data = self.load_data()
        summary = data.get('summary', {})
        
        html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Matutino - DevSecOps</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }
        
        .kpi-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        
        .kpi-card.critical {
            border-left-color: #dc3545;
        }
        
        .kpi-card.warning {
            border-left-color: #ffc107;
        }
        
        .kpi-card h3 {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .kpi-card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }
        
        .kpi-card .unit {
            font-size: 0.8em;
            color: #999;
            margin-left: 5px;
        }
        
        section {
            padding: 30px;
            border-top: 1px solid #eee;
        }
        
        section h2 {
            font-size: 1.8em;
            color: #333;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        table thead {
            background: #f8f9fa;
        }
        
        table th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #dee2e6;
        }
        
        table td {
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }
        
        table tr:hover {
            background: #f8f9fa;
        }
        
        .alert {
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid;
        }
        
        .alert.critical {
            background: #f8d7da;
            border-left-color: #dc3545;
            color: #721c24;
        }
        
        .alert.warning {
            background: #fff3cd;
            border-left-color: #ffc107;
            color: #856404;
        }
        
        .alert.success {
            background: #d4edda;
            border-left-color: #28a745;
            color: #155724;
        }
        
        .chart-container {
            position: relative;
            height: 400px;
            margin: 20px 0;
        }
        
        footer {
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #dee2e6;
        }
        
        @media (max-width: 768px) {
            header h1 {
                font-size: 1.8em;
            }
            
            .summary-grid {
                grid-template-columns: 1fr;
            }
            
            table {
                font-size: 0.9em;
            }
            
            table th, table td {
                padding: 8px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Dashboard Matutino DevSecOps</h1>
            <p>Última actualización: {{ timestamp }}</p>
        </header>
        
        <div class="summary-grid">
            <div class="kpi-card">
                <h3>Repositorios Totales</h3>
                <div class="value">{{ total_repos }}</div>
            </div>
            
            <div class="kpi-card {% if repos_without_pipeline > 0 %}critical{% endif %}">
                <h3>Sin Pipeline CI/CD</h3>
                <div class="value">{{ repos_without_pipeline }}</div>
            </div>
            
            <div class="kpi-card {% if health_score < 70 %}warning{% endif %}">
                <h3>Health Score</h3>
                <div class="value">{{ health_score }}<span class="unit">/100</span></div>
            </div>
            
            <div class="kpi-card {% if branch_compliance < 80 %}warning{% endif %}">
                <h3>Branch Compliance</h3>
                <div class="value">{{ branch_compliance }}<span class="unit">%</span></div>
            </div>
        </div>
        
        <section id="alerts">
            <h2>🚨 Alertas Críticas</h2>
            {% if repos_without_pipeline > 0 %}
            <div class="alert critical">
                <strong>⚠️ Crítico:</strong> {{ repos_without_pipeline }} repositorio(s) sin pipeline CI/CD
            </div>
            {% endif %}
            
            {% if health_score < 70 %}
            <div class="alert warning">
                <strong>⚠️ Advertencia:</strong> Health Score bajo ({{ health_score }}/100)
            </div>
            {% endif %}
            
            {% if branch_compliance < 80 %}
            <div class="alert warning">
                <strong>⚠️ Advertencia:</strong> Branch compliance bajo ({{ branch_compliance }}%)
            </div>
            {% endif %}
        </section>
        
        <section id="repositories">
            <h2>📁 Repositorios</h2>
            <p>Total: {{ total_repos }} repositorios</p>
            <ul>
                <li>Con CI: {{ repos_with_ci }}</li>
                <li>Con CD: {{ repos_with_cd }}</li>
                <li>Sin Pipeline: {{ repos_without_pipeline }}</li>
            </ul>
        </section>
        
        <section id="pipelines">
            <h2>🚀 Pipelines CI/CD</h2>
            <div class="chart-container">
                <canvas id="healthChart"></canvas>
            </div>
        </section>
        
        <section id="pull-requests">
            <h2>📬 Pull Requests</h2>
            <p>Tiempo promedio a merge: <strong>{{ pr_avg_time_to_merge_hours }}h</strong></p>
            <p>SLA Compliance: <strong>{{ pr_sla_compliance }}%</strong></p>
        </section>
        
        <footer>
            <p>Generado automáticamente por DevSecOps Toolbox</p>
        </footer>
    </div>
    
    <script>
        // Gráfico de Health Score
        const ctx = document.getElementById('healthChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Health Score'],
                datasets: [{
                    label: 'Score',
                    data: [{{ health_score }}],
                    backgroundColor: '{{ "rgba(40, 167, 69, 0.5)" if health_score >= 70 else "rgba(220, 53, 69, 0.5)" }}',
                    borderColor: '{{ "rgb(40, 167, 69)" if health_score >= 70 else "rgb(220, 53, 69)" }}',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    </script>
</body>
</html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            timestamp=data.get('timestamp', datetime.now().isoformat()),
            total_repos=summary.get('total_repos', 0),
            repos_with_ci=summary.get('repos_with_ci', 0),
            repos_with_cd=summary.get('repos_with_cd', 0),
            repos_without_pipeline=summary.get('repos_without_pipeline', 0),
            health_score=summary.get('health_score', 0),
            branch_compliance=summary.get('branch_compliance', 0),
            pr_avg_time_to_merge_hours=summary.get('pr_avg_time_to_merge_hours', 0),
            pr_sla_compliance=summary.get('pr_sla_compliance', 0),
        )
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Dashboard generado en: {self.output_file}")


def main():
    """Punto de entrada."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Dashboard Generator - Tool 27'
    )
    parser.add_argument('--input', required=True, help='Input JSON file')
    parser.add_argument('--output', help='Output HTML file')
    
    args = parser.parse_args()
    
    generator = DashboardGenerator(
        input_file=args.input,
        output_file=args.output
    )
    generator.generate()


if __name__ == '__main__':
    main()
```

---

## 📊 Estructura Base para Tool 28: PR Metrics Analyzer

```python
#!/usr/bin/env python3
"""
Tool 28: PR Metrics Analyzer
Analiza tiempo de atención de PRs.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PRMetricsAnalyzer:
    """Analiza métricas de PRs."""
    
    def __init__(self, org: str, project: str, pat: str, days: int = 30):
        self.org = org
        self.project = project
        self.pat = pat
        self.days = days
    
    def analyze(self) -> Dict[str, Any]:
        """Analiza PRs y calcula métricas."""
        logger.info(f"Analizando PRs de los últimos {self.days} días...")
        
        prs = self._fetch_prs()
        metrics = self._calculate_metrics(prs)
        
        return metrics
    
    def _fetch_prs(self) -> List[Dict[str, Any]]:
        """Obtiene PRs desde AZDO API."""
        # Aquí iría la lógica de consulta a AZDO API
        logger.info("Obteniendo PRs desde AZDO API...")
        return []
    
    def _calculate_metrics(self, prs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula métricas de PRs."""
        if not prs:
            return {
                'status': 'success',
                'total_prs': 0,
                'merged_prs': 0,
                'avg_time_to_merge_hours': 0,
                'sla_compliance': 0,
            }
        
        merged_prs = [pr for pr in prs if pr.get('status') == 'completed']
        times_to_merge = []
        
        for pr in merged_prs:
            created = datetime.fromisoformat(pr.get('creationDate', ''))
            closed = datetime.fromisoformat(pr.get('closedDate', ''))
            hours = (closed - created).total_seconds() / 3600
            times_to_merge.append(hours)
        
        times_to_merge.sort()
        
        sla_threshold = 48  # horas
        sla_compliant = len([t for t in times_to_merge if t <= sla_threshold])
        sla_compliance = (sla_compliant / len(times_to_merge) * 100) if times_to_merge else 0
        
        return {
            'status': 'success',
            'total_prs': len(prs),
            'merged_prs': len(merged_prs),
            'abandoned_prs': len([pr for pr in prs if pr.get('status') == 'abandoned']),
            'active_prs': len([pr for pr in prs if pr.get('status') == 'active']),
            'avg_time_to_merge_hours': sum(times_to_merge) / len(times_to_merge) if times_to_merge else 0,
            'median_time_to_merge_hours': times_to_merge[len(times_to_merge)//2] if times_to_merge else 0,
            'p95_time_to_merge_hours': times_to_merge[int(len(times_to_merge)*0.95)] if times_to_merge else 0,
            'prs_blocked_24h': len([t for t in times_to_merge if t > 24]),
            'prs_blocked_48h': len([t for t in times_to_merge if t > 48]),
            'sla_compliance': round(sla_compliance, 2),
        }


def main():
    """Punto de entrada."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='PR Metrics Analyzer - Tool 28'
    )
    parser.add_argument('--org', required=True, help='Azure DevOps organization')
    parser.add_argument('--project', required=True, help='Azure DevOps project')
    parser.add_argument('--pat', required=True, help='Azure DevOps PAT')
    parser.add_argument('--days', type=int, default=30, help='Days to analyze')
    parser.add_argument('--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    analyzer = PRMetricsAnalyzer(
        org=args.org,
        project=args.project,
        pat=args.pat,
        days=args.days
    )
    
    metrics = analyzer.analyze()
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
```

---

## ⏰ Estructura Base para Tool 29: Dashboard Scheduler

```python
#!/usr/bin/env python3
"""
Tool 29: Dashboard Scheduler
Automatiza ejecución diaria del dashboard.
"""

import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DashboardScheduler:
    """Scheduler para ejecución automática del dashboard."""
    
    def __init__(self, config_file: str = "config.json"):
        self.config = self._load_config(config_file)
        self.scheduler = BackgroundScheduler()
        
    def _load_config(self, config_file: str) -> dict:
        """Carga configuración."""
        with open(config_file) as f:
            return json.load(f)
    
    def start_daemon(self):
        """Inicia el scheduler como daemon."""
        dashboard_config = self.config.get('dashboard', {})
        schedule = dashboard_config.get('schedule', '0 7 * * *')
        
        logger.info(f"Iniciando scheduler con schedule: {schedule}")
        
        self.scheduler.add_job(
            self.run_dashboard,
            CronTrigger.from_crontab(schedule),
            id='dashboard_job',
            name='Dashboard Consolidator'
        )
        
        self.scheduler.start()
        logger.info("Scheduler iniciado. Presiona Ctrl+C para detener.")
        
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.scheduler.shutdown()
            logger.info("Scheduler detenido.")
    
    def run_once(self):
        """Ejecuta el dashboard una sola vez."""
        logger.info("Ejecutando dashboard una sola vez...")
        self.run_dashboard()
    
    def run_dashboard(self):
        """Ejecuta Tool 26 y Tool 27."""
        try:
            logger.info("=" * 60)
            logger.info("EJECUTANDO DASHBOARD")
            logger.info("=" * 60)
            
            # Ejecutar Tool 26
            logger.info("Ejecutando Tool 26: Consolidator...")
            consolidator_result = subprocess.run([
                'python', 'scm/azdo/dashboard_consolidator.py',
                '--org', self.config.get('org'),
                '--project', self.config.get('project'),
                '--pat', self.config.get('pat'),
            ], capture_output=True, text=True)
            
            if consolidator_result.returncode != 0:
                logger.error(f"Error en Tool 26: {consolidator_result.stderr}")
                return
            
            # Ejecutar Tool 27
            logger.info("Ejecutando Tool 27: Generator...")
            latest_json = self._get_latest_dashboard_json()
            generator_result = subprocess.run([
                'python', 'scm/dashboard/dashboard_generator.py',
                '--input', str(latest_json),
            ], capture_output=True, text=True)
            
            if generator_result.returncode != 0:
                logger.error(f"Error en Tool 27: {generator_result.stderr}")
                return
            
            # Enviar notificaciones
            self._send_notifications()
            
            logger.info("=" * 60)
            logger.info("DASHBOARD EJECUTADO EXITOSAMENTE")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error fatal: {e}")
    
    def _get_latest_dashboard_json(self) -> Path:
        """Obtiene el archivo JSON más reciente."""
        dashboard_dir = Path("outcome/dashboard")
        json_files = sorted(dashboard_dir.glob("dashboard_data_*.json"))
        return json_files[-1] if json_files else None
    
    def _send_notifications(self):
        """Envía notificaciones."""
        dashboard_config = self.config.get('dashboard', {})
        notifications = dashboard_config.get('notifications', {})
        
        if notifications.get('email', {}).get('enabled'):
            self._send_email(notifications['email'])
        
        if notifications.get('slack', {}).get('enabled'):
            self._send_slack(notifications['slack'])
        
        if notifications.get('teams', {}).get('enabled'):
            self._send_teams(notifications['teams'])
    
    def _send_email(self, config: dict):
        """Envía notificación por email."""
        logger.info("Enviando notificación por email...")
        # Aquí iría la lógica de envío de email
    
    def _send_slack(self, config: dict):
        """Envía notificación por Slack."""
        logger.info("Enviando notificación por Slack...")
        # Aquí iría la lógica de envío a Slack
    
    def _send_teams(self, config: dict):
        """Envía notificación por Teams."""
        logger.info("Enviando notificación por Teams...")
        # Aquí iría la lógica de envío a Teams


def main():
    """Punto de entrada."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Dashboard Scheduler - Tool 29'
    )
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--run-once', action='store_true', help='Run once')
    parser.add_argument('--config', default='config.json', help='Config file')
    
    args = parser.parse_args()
    
    scheduler = DashboardScheduler(config_file=args.config)
    
    if args.daemon:
        scheduler.start_daemon()
    elif args.run_once:
        scheduler.run_once()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
```

---

## 📝 Ejemplo de dashboard_data.json

```json
{
  "timestamp": "2026-06-22T07:00:00Z",
  "status": "success",
  "data": {
    "azdo": {
      "ci_inventory": {
        "status": "success",
        "repos": [
          {
            "name": "repo-1",
            "ci_pipeline": "CI-Repo1",
            "cd_pipeline": "CD-Repo1"
          }
        ]
      },
      "cd_inventory": {
        "status": "success",
        "repos": []
      },
      "health_score": {
        "overall_score": 75,
        "ci_health": 80,
        "cd_health": 70
      },
      "branch_policy": {
        "compliance_percentage": 85
      },
      "pr_metrics": {
        "total_prs": 150,
        "avg_time_to_merge_hours": 24.5,
        "sla_compliance": 95.2
      }
    }
  },
  "summary": {
    "total_repos": 50,
    "repos_without_pipeline": 2,
    "health_score": 75,
    "branch_compliance": 85,
    "pr_avg_time_to_merge_hours": 24.5,
    "pr_sla_compliance": 95.2
  }
}
```

---

## 🚀 Cómo Empezar

1. **Crear archivos base:**
   ```bash
   touch scm/azdo/dashboard_consolidator.py
   touch scm/azdo/pr_metrics_analyzer.py
   touch scm/dashboard/dashboard_generator.py
   touch scm/dashboard/dashboard_scheduler.py
   ```

2. **Copiar código de ejemplos** a cada archivo

3. **Instalar dependencias:**
   ```bash
   pip install apscheduler jinja2
   ```

4. **Crear directorio de salida:**
   ```bash
   mkdir -p outcome/dashboard/history
   ```

5. **Probar Tool 26:**
   ```bash
   python scm/azdo/dashboard_consolidator.py \
     --org "Coppel-Retail" \
     --project "Cadena_de_Suministros" \
     --pat "$AZDO_PAT"
   ```

6. **Probar Tool 27:**
   ```bash
   python scm/dashboard/dashboard_generator.py \
     --input "outcome/dashboard/dashboard_data_*.json"
   ```

7. **Probar Tool 29:**
   ```bash
   python scm/dashboard/dashboard_scheduler.py --run-once
   ```
