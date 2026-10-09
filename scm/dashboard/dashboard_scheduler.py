#!/usr/bin/env python3
"""
Tool 29: Dashboard Scheduler
Ejecuta el dashboard automáticamente y envía notificaciones a Teams
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import logging

# Dependencias opcionales: el paquete debe ser importable aunque falten.
try:
    import requests
except ImportError:
    requests = None

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    BackgroundScheduler = None
    CronTrigger = None

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

# Helpers de credenciales AZDO y webhook Teams (config.json / env vars)
try:
    from dashboard.dashboard_common import resolve_credentials, resolve_webhook, resolve_cron
except ImportError:
    try:
        from dashboard_common import resolve_credentials, resolve_webhook, resolve_cron
    except ImportError:
        import os as _os2
        def _load_cfg():
            cfg_path = Path(__file__).parent.parent / "config.json"
            try:
                return json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
            except Exception:
                return {}
        def resolve_credentials(org=None, project=None, pat=None):
            azdo = _load_cfg().get("azdo", {})
            return (
                org or _os2.getenv("AZDO_ORG") or azdo.get("organization") or azdo.get("organization_url") or "",
                project or _os2.getenv("AZDO_PROJECT") or azdo.get("project") or "",
                pat or _os2.getenv("AZDO_PAT") or azdo.get("pat") or "",
            )
        def resolve_webhook(webhook=None):
            if webhook:
                return webhook
            env = _os2.getenv("TEAMS_WEBHOOK_URL")
            if env:
                return env
            dash = _load_cfg().get("dashboard", {})
            url = dash.get("webhook_url") or dash.get("notifications", {}).get("teams", {}).get("webhook_url") or ""
            return "" if url == "<TU_TEAMS_WEBHOOK_URL>" else url
        def resolve_cron(cron=None):
            if cron:
                return cron
            dash = _load_cfg().get("dashboard", {})
            return dash.get("schedule", {}).get("cron") or "0 7 * * *"

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
        if requests is None:
            logger.error("❌ 'requests' no está instalado: pip install -r scm/dashboard/requirements.txt")
            return False
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
                 consolidator_path=None,
                 generator_path=None):
        if BackgroundScheduler is None:
            raise ImportError(
                "apscheduler no está instalado. Instala con: "
                "pip install -r scm/dashboard/requirements.txt"
            )
        self.org = org
        self.project = project
        self.pat = pat
        self.webhook_url = webhook_url
        base = Path(__file__).resolve().parent
        self.consolidator_path = consolidator_path or str(base / "dashboard_consolidator.py")
        self.generator_path = generator_path or str(base / "dashboard_generator.py")
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
                sys.executable, self.consolidator_path,
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
                sys.executable, self.generator_path
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
    parser.add_argument('--org', help='Organización Azure DevOps (o env AZDO_ORG / config.json azdo.organization)')
    parser.add_argument('--project', help='Proyecto Azure DevOps (o env AZDO_PROJECT / config.json azdo.project)')
    parser.add_argument('--pat', help='Personal Access Token (o env AZDO_PAT / config.json azdo.pat)')
    parser.add_argument('--webhook', help='Webhook URL de Microsoft Teams (o env TEAMS_WEBHOOK_URL / config.json)')
    parser.add_argument('--run-once', action='store_true', help='Ejecutar una sola vez')
    parser.add_argument('--cron', help='Expresión cron (default: config.json dashboard.schedule.cron o 7 AM)')

    args = parser.parse_args()

    # Resolver credenciales: CLI > variables de entorno > config.json
    args.org, args.project, args.pat = resolve_credentials(args.org, args.project, args.pat)
    args.webhook = resolve_webhook(args.webhook)
    args.cron = resolve_cron(args.cron)

    if not (args.org and args.project and args.pat):
        print("\n❌ Se requieren credenciales AZDO: --org/--project/--pat, "
              "variables AZDO_ORG/AZDO_PROJECT/AZDO_PAT, o sección 'azdo' en scm/config.json")
        return 1

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
