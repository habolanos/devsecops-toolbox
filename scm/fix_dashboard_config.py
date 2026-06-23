#!/usr/bin/env python3
"""
Script para agregar la sección 'dashboard' a config.json si no existe
"""

import json
import sys
from pathlib import Path

def fix_config():
    """Agrega sección dashboard a config.json si no existe"""
    
    config_file = Path(__file__).parent / "config.json"
    
    if not config_file.exists():
        print(f"❌ No se encontró: {config_file}")
        return False
    
    try:
        # Leer config actual
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Verificar si ya tiene dashboard
        if "dashboard" in config:
            print("✅ config.json ya tiene sección 'dashboard'")
            return True
        
        # Agregar sección dashboard
        print("⚠️ Agregando sección 'dashboard' a config.json...")
        
        config["dashboard"] = {
            "enabled": True,
            "webhook_url": "",
            "schedule": {
                "enabled": True,
                "cron": "0 7 * * *",
                "timezone": "America/Mexico_City"
            },
            "metrics": {
                "health_score": {
                    "enabled": True,
                    "weights": {
                        "deployment_frequency": 0.20,
                        "lead_time": 0.20,
                        "mttr": 0.25,
                        "change_failure_rate": 0.20,
                        "system_uptime": 0.15
                    }
                },
                "code_coverage": {
                    "enabled": True,
                    "thresholds": {
                        "critical": 60,
                        "acceptable": 75,
                        "good": 85,
                        "excellent": 95
                    }
                },
                "pr_metrics": {"enabled": True},
                "branch_compliance": {"enabled": True},
                "pipeline_status": {"enabled": True}
            },
            "alerts": {
                "critical": {
                    "health_score": 40,
                    "code_coverage": 60,
                    "deployment_failure_rate": 15,
                    "mttr_hours": 4,
                    "system_uptime": 99,
                    "review_time_minutes": 120,
                    "approval_rate": 70
                },
                "warning": {
                    "health_score": 60,
                    "code_coverage": 75,
                    "system_uptime": 99.5,
                    "review_time_minutes": 60,
                    "approval_rate": 80
                }
            },
            "notifications": {
                "teams": {
                    "enabled": True,
                    "webhook_url": "",
                    "group_name": "Equipo Comercial/CDS",
                    "mention_on_critical": True,
                    "retry_attempts": 3,
                    "timeout_seconds": 30
                },
                "email": {"enabled": False, "recipients": []},
                "slack": {"enabled": False, "webhook_url": ""}
            },
            "output": {
                "directory": "outcome/dashboard",
                "history_directory": "outcome/dashboard/history",
                "retention_days": 90,
                "formats": ["json", "html"]
            },
            "tools": {
                "consolidator": {
                    "enabled": True,
                    "tool_id": 26,
                    "name": "Dashboard Consolidator",
                    "timeout_seconds": 300,
                    "parallel_execution": True,
                    "max_workers": 8
                },
                "generator": {
                    "enabled": True,
                    "tool_id": 27,
                    "name": "Dashboard Generator",
                    "timeout_seconds": 60,
                    "output_format": "html"
                },
                "scheduler": {
                    "enabled": True,
                    "tool_id": 29,
                    "name": "Dashboard Scheduler",
                    "run_consolidator": True,
                    "run_generator": True,
                    "send_notifications": True
                }
            }
        }
        
        # Guardar config actualizado
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Sección 'dashboard' agregada a {config_file}")
        print("\n📝 Próximos pasos:")
        print("1. Editar config.json")
        print("2. Agregar webhook_url en sección 'dashboard' (opcional)")
        print("3. Ejecutar: python scm/main.py")
        print("4. Seleccionar opción: 6")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: config.json tiene JSON inválido: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_config()
    sys.exit(0 if success else 1)
