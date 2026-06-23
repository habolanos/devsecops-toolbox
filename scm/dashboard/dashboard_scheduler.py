#!/usr/bin/env python3
"""
Tool 29: Dashboard Scheduler
Ejecuta el dashboard automáticamente y envía notificaciones a Teams
"""

import json
import sys
import requests
from pathlib import Path
from datetime import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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


class TeamsNotifier:
    """Envía notificaciones a Microsoft Teams"""
    
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    def send_notification(self, dashboard_data):
        """Envía notificación a Teams"""
        try:
            summary = dashboard_data.get('summary', {})
            alerts = dashboard_data.get('alerts', {})
            
            health_score = summary.get('health_score', 0)
            code_coverage = summary.get('code_coverage', 0)
            
            # Determinar color según estado
            if alerts.get('critical'):
                color = 'ff0000'  # Rojo
                status = '🔴 CRÍTICO'
            elif alerts.get('warning'):
                color = 'ffcc00'  # Amarillo
                status = '🟡 ADVERTENCIA'
            else:
                color = '00cc00'  # Verde
                status = '🟢 SALUDABLE'
            
            # Construir mensaje adaptativo
            message = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": f"Dashboard Matutino - {status}",
                "themeColor": color,
                "sections": [
                    {
                        "activityTitle": "📊 Dashboard Matutino DevSecOps",
                        "activitySubtitle": f"Ejecución: {dashboard_data.get('timestamp', 'N/A')}",
                        "facts": [
                            {
                                "name": "Estado",
                                "value": status
                            },
                            {
                                "name": "Health Score",
                                "value": f"{health_score}/100"
                            },
                            {
                                "name": "Code Coverage",
                                "value": f"{code_coverage}%"
                            },
                            {
                                "name": "Deployment Frequency",
                                "value": f"{summary.get('deployment_frequency', 0)}/semana"
                            },
                            {
                                "name": "MTTR",
                                "value": f"{summary.get('mttr', 0)} horas"
                            },
                            {
                                "name": "System Uptime",
                                "value": f"{summary.get('system_uptime', 0)}%"
                            }
                        ]
                    }
                ]
            }
            
            # Agregar alertas si las hay
            if alerts.get('critical'):
                message['sections'].append({
                    "activityTitle": "🔴 ALERTAS CRÍTICAS",
                    "text": "\n".join([f"• {alert}" for alert in alerts['critical']])
                })
            
            if alerts.get('warning'):
                message['sections'].append({
                    "activityTitle": "🟡 ADVERTENCIAS",
                    "text": "\n".join([f"• {alert}" for alert in alerts['warning']])
                })
            
            # Agregar botón para ver dashboard
            message['potentialAction'] = [
                {
                    "@type": "OpenUri",
                    "name": "Ver Dashboard Completo",
                    "targets": [
                        {
                            "os": "default",
                            "uri": f"file:///{get_output_dir('outcome/dashboard')}/dashboard.html"
                        }
                    ]
                }
            ]
            
            # Enviar
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ Notificación enviada a Teams")
                return True
            else:
                logger.error(f"❌ Error enviando notificación: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en notificación Teams: {str(e)}")
            return False


class DashboardScheduler:
    """Ejecuta el dashboard automáticamente"""
    
    def __init__(self, org, project, pat, webhook_url=None, 
                 consolidator_path="scm/dashboard/dashboard_consolidator.py",
                 generator_path="scm/dashboard/dashboard_generator.py"):
        self.org = org
        self.project = project
        self.pat = pat
        self.webhook_url = webhook_url
        self.consolidator_path = consolidator_path
        self.generator_path = generator_path
        self.scheduler = BackgroundScheduler()
        self.notifier = TeamsNotifier(webhook_url) if webhook_url else None
        
        logger.info("Scheduler inicializado")
    
    def run_once(self):
        """Ejecuta el dashboard una sola vez"""
        try:
            logger.info("Ejecutando dashboard (una sola vez)...")
            
            # 1. Ejecutar consolidator
            logger.info("Ejecutando consolidator...")
            import subprocess
            result = subprocess.run([
                'python', self.consolidator_path,
                '--org', self.org,
                '--project', self.project,
                '--pat', self.pat
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Error en consolidator: {result.stderr}")
                return False
            
            # 2. Ejecutar generator
            logger.info("Ejecutando generator...")
            result = subprocess.run([
                'python', self.generator_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Error en generator: {result.stderr}")
                return False
            
            # 3. Enviar notificación
            if self.notifier:
                logger.info("Enviando notificación a Teams...")
                dashboard_data_file = get_output_dir('outcome/dashboard') / 'dashboard_data.json'
                with open(dashboard_data_file, 'r') as f:
                    dashboard_data = json.load(f)
                self.notifier.send_notification(dashboard_data)
            
            logger.info("✅ Dashboard ejecutado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando dashboard: {str(e)}")
            return False
    
    def start_scheduler(self, cron_expression="0 7 * * *"):
        """Inicia el scheduler con expresión cron"""
        try:
            # Agregar job
            self.scheduler.add_job(
                self.run_once,
                trigger=CronTrigger.from_crontab(cron_expression),
                id='dashboard_job',
                name='Dashboard Matutino',
                replace_existing=True
            )
            
            # Iniciar scheduler
            self.scheduler.start()
            logger.info(f"✅ Scheduler iniciado. Próxima ejecución: {cron_expression}")
            
            # Mantener scheduler activo
            try:
                while True:
                    pass
            except KeyboardInterrupt:
                logger.info("Scheduler detenido")
                self.scheduler.shutdown()
                
        except Exception as e:
            logger.error(f"❌ Error iniciando scheduler: {str(e)}")
            raise


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dashboard Scheduler - Tool 29')
    parser.add_argument('--org', required=True, help='Organización Azure DevOps')
    parser.add_argument('--project', required=True, help='Proyecto Azure DevOps')
    parser.add_argument('--pat', required=True, help='Personal Access Token')
    parser.add_argument('--webhook', help='Webhook URL de Microsoft Teams')
    parser.add_argument('--run-once', action='store_true', help='Ejecutar una sola vez')
    parser.add_argument('--cron', default='0 7 * * *', help='Expresión cron (default: 7 AM)')
    
    args = parser.parse_args()
    
    try:
        scheduler = DashboardScheduler(
            org=args.org,
            project=args.project,
            pat=args.pat,
            webhook_url=args.webhook
        )
        
        if args.run_once:
            result = scheduler.run_once()
            return 0 if result else 1
        else:
            scheduler.start_scheduler(cron_expression=args.cron)
            return 0
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    # No usar sys.exit() para permitir que el launcher continúe
    # sys.exit(exit_code)
