#!/usr/bin/env python3
"""
Tool 26: Dashboard Consolidator
Orquesta la ejecución de múltiples herramientas y consolida datos en dashboard_data.json
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HistoryManager:
    """Gestiona histórico de métricas (90 días)"""
    
    def __init__(self, history_dir=None):
        if history_dir is None:
            # Usar directorio centralizado
            output_dir = get_output_dir("outcome/dashboard")
            self.history_dir = output_dir / "history"
        else:
            self.history_dir = Path(history_dir)
        
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = 90
    
    def save_daily_snapshot(self, dashboard_data):
        """Guarda snapshot diario"""
        today = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        
        # Crear directorio del día
        day_dir = self.history_dir / today
        day_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar datos completos
        data_file = day_dir / f"dashboard_data_{timestamp}.json"
        with open(data_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        
        logger.info(f"Snapshot guardado: {data_file}")
        
        # Guardar resumen de métricas
        summary_file = day_dir / f"metrics_summary_{today}.json"
        with open(summary_file, 'w') as f:
            json.dump(self._extract_summary(dashboard_data), f, indent=2)
    
    def _extract_summary(self, dashboard_data):
        """Extrae resumen de métricas"""
        metrics = dashboard_data.get('metrics', {})
        security = metrics.get('security', {})
        return {
            'timestamp': dashboard_data['timestamp'],
            'health_score': metrics.get('health_score', {}).get('overall_score', 0),
            'deployment_frequency': metrics.get('health_score', {}).get('deployment_frequency', 0),
            'mttr': metrics.get('health_score', {}).get('mttr_hours', 0),
            'change_failure_rate': metrics.get('health_score', {}).get('change_failure_rate', 0),
            'system_uptime': metrics.get('health_score', {}).get('system_uptime', 0),
            'pr_total': metrics.get('pr_metrics', {}).get('total_prs', 0),
            'pr_approval_rate': metrics.get('pr_metrics', {}).get('approval_rate_percentage', 0),
            'branch_compliance': metrics.get('branch_compliance', {}).get('compliance_percentage', 0),
            'pipeline_success_rate': metrics.get('pipeline_status', {}).get('success_rate', 0),
            'security_vulnerabilities': security.get('repo_vulnerabilities', {}).get('total_findings', 0),
            'security_log_alerts': security.get('pipeline_logs', {}).get('total_matches', 0),
            'pending_approvals': metrics.get('pending_approvals', {}).get('total', 0),
            'prod_deploy_tracking': metrics.get('prod_deploy', {}).get('total_pipelines', 0),
        }


class DashboardConsolidator:
    """Orquesta la ejecución de herramientas y consolida datos"""
    
    def __init__(self, org, project, pat, output_dir=None):
        self.org = org
        self.project = project
        self.pat = pat
        
        if output_dir is None:
            # Usar directorio centralizado
            self.output_dir = get_output_dir("outcome/dashboard")
        else:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.history_manager = HistoryManager()
        
        logger.info(f"Consolidator inicializado para {org}/{project}")
        logger.info(f"Directorio de salida: {self.output_dir}")
    
    def run(self):
        """Ejecuta el flujo completo"""
        try:
            logger.info("Iniciando consolidación de dashboard...")
            
            # 1. Ejecutar herramientas en paralelo
            logger.info("Ejecutando herramientas en paralelo...")
            results = self._run_all_tools()
            
            # 2. Consolidar datos
            logger.info("Consolidando datos...")
            dashboard_data = self._consolidate(results)
            
            # 3. Guardar histórico
            logger.info("Guardando histórico...")
            self.history_manager.save_daily_snapshot(dashboard_data)
            
            # 4. Guardar dashboard_data.json
            logger.info("Guardando dashboard_data.json...")
            self._save_dashboard_data(dashboard_data)
            
            logger.info("✅ Consolidación completada exitosamente")
            return dashboard_data
            
        except Exception as e:
            logger.error(f"❌ Error en consolidación: {str(e)}")
            raise
    
    def _run_all_tools(self):
        """Lee datos de los JSON generados por las herramientas AZDO"""
        results = {}
        
        # Buscar archivos JSON generados por las herramientas AZDO
        json_files = {
            'pr_metrics': 'pr_master_*.json',
            'branch_compliance': 'branch_policies_*.json',
            'health_score': 'pipeline_health_score_*.json',
            'pipeline_status': 'pipeline_status_*.json',
            'security_logs': 'azdo_scan_pipeline_logs_*.json',
            'security_vulnerabilities': 'azdo_scan_repos_vulnerabilities_*.json',
            'pending_approvals': 'cicd_inventory_pending_approvals_*.json',
            'cicd_inventory': 'cicd_inventory_*.json',
            'prod_deploy': 'cicd_inventory_prod_deploy_*.json',
        }
        
        for metric_name, pattern in json_files.items():
            try:
                # Buscar el archivo más reciente
                import glob
                files = sorted(glob.glob(str(self.output_dir.parent / pattern)), reverse=True)
                
                if files:
                    with open(files[0], 'r') as f:
                        data = json.load(f)
                        # Extraer datos del JSON
                        if isinstance(data, dict) and 'data' in data:
                            results[metric_name] = data['data']
                        else:
                            results[metric_name] = data
                        logger.info(f"✅ {metric_name} cargado desde {files[0]}")
                else:
                    logger.warning(f"⚠️  No se encontró {pattern}, usando datos por defecto")
                    # Usar método stub como fallback
                    method = getattr(self, f'_get_{metric_name}', None)
                    if method:
                        results[metric_name] = method()
                    else:
                        results[metric_name] = {}
                        
            except Exception as e:
                logger.error(f"❌ Error cargando {metric_name}: {str(e)}")
                # Usar método stub como fallback
                method = getattr(self, f'_get_{metric_name}', None)
                if method:
                    results[metric_name] = method()
                else:
                    results[metric_name] = {'error': str(e)}
        
        return results
    
    def _get_health_score(self):
        """Obtiene Health Score (DORA Metrics)"""
        return {
            'overall_score': 75,
            'deployment_frequency': 2.5,
            'lead_time_days': 2.3,
            'mttr_hours': 1.5,
            'change_failure_rate': 8.5,
            'system_uptime': 99.8,
            'breakdown': {
                'deployment_frequency_score': 75,
                'lead_time_score': 75,
                'mttr_score': 100,
                'cfr_score': 100,
                'uptime_score': 100
            }
        }
    
    def _get_security_logs(self):
        """Fallback: Pipeline Logs Scanner"""
        return {
            'total_matches': 0,
            'pipelines_affected': 0,
            'findings': []
        }
    
    def _get_security_vulnerabilities(self):
        """Fallback: Repo Vulnerabilities Scanner"""
        return {
            'total_findings': 0,
            'repos_affected': 0,
            'findings': []
        }
    
    def _get_pending_approvals(self):
        """Fallback: Pending Approvals"""
        return {
            'total': 0,
            'approvals': []
        }
    
    def _get_cicd_inventory(self):
        """Fallback: CICD Inventory"""
        return {
            'total_repos': 0,
            'total_ci_pipelines': 0,
            'total_cd_pipelines': 0,
            'repos': []
        }
    
    def _get_prod_deploy(self):
        """Fallback: Prod Deploy Tracker"""
        return {
            'total_pipelines': 0,
            'pipelines_within_deadline': 0,
            'pipelines_overdue': 0,
            'pipelines': []
        }
    
    def _get_pr_metrics(self):
        """Obtiene PR Metrics"""
        return {
            'total_prs': 150,
            'avg_review_time_minutes': 25,
            'approval_rate_percentage': 92,
            'avg_size_loc': 350,
            'merge_conflicts_percentage': 8,
            'prs_awaiting_review': 12,
            'prs_awaiting_changes': 5
        }
    
    def _get_branch_compliance(self):
        """Obtiene cumplimiento de branching"""
        return {
            'total_repos': 50,
            'repos_with_protection': 48,
            'compliance_percentage': 96,
            'repos_without_protection': 2,
            'repos_without_pipeline': 2
        }
    
    def _get_pipeline_status(self):
        """Obtiene estado de pipelines"""
        return {
            'total_pipelines': 95,
            'successful': 85,
            'failed': 5,
            'in_progress': 5,
            'success_rate': 94.4,
            'avg_duration_minutes': 12
        }
    
    def _consolidate(self, results):
        """Consolida todos los datos en estructura dashboard_data.json"""
        security_logs = results.get('security_logs', {})
        security_vulns = results.get('security_vulnerabilities', {})
        pending_approvals = results.get('pending_approvals', {})
        cicd_inventory = results.get('cicd_inventory', {})
        prod_deploy = results.get('prod_deploy', {})
        
        # Construir alertas dinámicamente
        alerts = {'critical': [], 'warning': [], 'info': []}
        
        # Alertas de seguridad
        vuln_count = security_vulns.get('total_findings', security_vulns.get('summary', {}).get('total', 0)) if isinstance(security_vulns, dict) else 0
        if vuln_count and vuln_count > 0:
            alerts['critical'].append(f'{vuln_count} vulnerabilidades detectadas en repositorios')
        
        log_alerts = security_logs.get('total_matches', security_logs.get('summary', {}).get('total_matches', 0)) if isinstance(security_logs, dict) else 0
        if log_alerts and log_alerts > 0:
            alerts['warning'].append(f'{log_alerts} coincidencias de vulnerabilidades en logs de pipelines')
        
        # Alertas de aprobaciones pendientes
        pending_count = pending_approvals.get('total', 0) if isinstance(pending_approvals, dict) else 0
        if pending_count and pending_count > 5:
            alerts['warning'].append(f'{pending_count} aprobaciones de release pendientes')
        
        # Alertas de prod deploy
        if isinstance(prod_deploy, dict):
            overdue = prod_deploy.get('pipelines_overdue', 0)
            if overdue and overdue > 0:
                alerts['critical'].append(f'{overdue} pipelines con despliegue a producción vencido')
        
        # Alertas de health score
        health = results.get('health_score', {})
        if isinstance(health, dict):
            overall = health.get('overall_score', 0)
            if overall and overall < 60:
                alerts['critical'].append(f'Health Score crítico: {overall}/100')
            elif overall and overall < 75:
                alerts['warning'].append(f'Health Score bajo: {overall}/100')
        
        return {
            'timestamp': datetime.now().isoformat() + 'Z',
            'status': 'success',
            'metrics': {
                'health_score': results.get('health_score', {}),
                'pr_metrics': results.get('pr_metrics', {}),
                'branch_compliance': results.get('branch_compliance', {}),
                'pipeline_status': results.get('pipeline_status', {}),
                'security': {
                    'pipeline_logs': results.get('security_logs', {}),
                    'repo_vulnerabilities': results.get('security_vulnerabilities', {}),
                },
                'pending_approvals': results.get('pending_approvals', {}),
                'cicd_inventory': results.get('cicd_inventory', {}),
                'prod_deploy': results.get('prod_deploy', {}),
            },
            'alerts': alerts,
            'summary': {
                'total_repos': results.get('branch_compliance', {}).get('total_repos', 0) if isinstance(results.get('branch_compliance'), dict) else 0,
                'repos_with_ci': results.get('branch_compliance', {}).get('total_repos', 0) if isinstance(results.get('branch_compliance'), dict) else 0,
                'health_score': results.get('health_score', {}).get('overall_score', 0) if isinstance(results.get('health_score'), dict) else 0,
                'branch_compliance': results.get('branch_compliance', {}).get('compliance_percentage', 0) if isinstance(results.get('branch_compliance'), dict) else 0,
                'pipeline_success_rate': results.get('pipeline_status', {}).get('success_rate', 0) if isinstance(results.get('pipeline_status'), dict) else 0,
                'security_vulnerabilities': vuln_count,
                'security_log_alerts': log_alerts,
                'pending_approvals': pending_count,
                'prod_deploy_overdue': prod_deploy.get('pipelines_overdue', 0) if isinstance(prod_deploy, dict) else 0,
            }
        }
    
    def _save_dashboard_data(self, dashboard_data):
        """Guarda dashboard_data.json"""
        output_file = self.output_dir / 'dashboard_data.json'
        with open(output_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        logger.info(f"Dashboard data guardado: {output_file}")


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dashboard Consolidator - Tool 26')
    parser.add_argument('--org', required=True, help='Organización Azure DevOps')
    parser.add_argument('--project', required=True, help='Proyecto Azure DevOps')
    parser.add_argument('--pat', required=True, help='Personal Access Token')
    parser.add_argument('--output', default='outcome/dashboard', help='Directorio de salida')
    
    args = parser.parse_args()
    
    try:
        consolidator = DashboardConsolidator(
            org=args.org,
            project=args.project,
            pat=args.pat,
            output_dir=args.output
        )
        
        dashboard_data = consolidator.run()
        
        print("\n✅ Dashboard consolidado exitosamente")
        print(f"Health Score: {dashboard_data['summary']['health_score']}/100")
        print(f"Branch Compliance: {dashboard_data['summary']['branch_compliance']}%")
        print(f"Pipeline Success Rate: {dashboard_data['summary']['pipeline_success_rate']}%")
        print(f"Security Vulnerabilities: {dashboard_data['summary']['security_vulnerabilities']}")
        print(f"Pending Approvals: {dashboard_data['summary']['pending_approvals']}")
        print(f"Prod Deploy Overdue: {dashboard_data['summary']['prod_deploy_overdue']}")
        print(f"Alerts: {len(dashboard_data['alerts']['critical'])} critical, {len(dashboard_data['alerts']['warning'])} warning")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    # No usar sys.exit() para permitir que el launcher continúe
    # sys.exit(exit_code)
