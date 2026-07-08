"""
Config Loader para Service Accounts Reporter
Carga configuración desde config.json
"""

import json
from pathlib import Path
from typing import Dict, List


class ConfigLoader:
    """Carga configuración desde config.json."""
    
    def __init__(self, config_path: str = "config.json", debug: bool = False):
        self.config_path = Path(config_path)
        self.debug = debug
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Carga el archivo config.json."""
        if not self.config_path.exists():
            if self.debug:
                print(f"⚠️  config.json no encontrado en {self.config_path}")
                print("   Usando configuración por defecto")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            if self.debug:
                print(f"❌ Error al parsear config.json: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Retorna configuración por defecto."""
        return {
            "gcp": {
                "service_accounts_reporter": {
                    "enabled": True,
                    "projects": [],
                    "defaults": {
                        "mode": "all",
                        "output_format": "json",
                        "include_activity": True,
                        "activity_days": 30,
                        "key_rotation_policy_days": 90,
                        "parallel_workers": 5,
                        "timeout_seconds": 300,
                        "cache_enabled": True,
                        "cache_ttl_minutes": 60
                    },
                    "security": {
                        "dangerous_roles": [
                            "roles/editor",
                            "roles/owner",
                            "roles/compute.admin",
                            "roles/iam.securityAdmin",
                            "roles/resourcemanager.organizationAdmin"
                        ],
                        "alert_on_risk_level": ["HIGH", "CRITICAL"],
                        "encrypt_reports": False
                    },
                    "compliance": {
                        "policies": [
                            {
                                "name": "key_rotation_90days",
                                "description": "Rotación de claves cada 90 días",
                                "enabled": True,
                                "threshold_days": 90
                            }
                        ]
                    },
                    "notifications": {
                        "enabled": False,
                        "on_high_risk": True,
                        "on_compliance_violation": True,
                        "webhook_url": ""
                    }
                }
            }
        }
    
    def get_projects(self) -> List[str]:
        """Obtiene lista de proyectos desde config.json."""
        return self.config.get('gcp', {}).get('service_accounts_reporter', {}).get('projects', [])
    
    def get_sa_reporter_config(self) -> Dict:
        """Obtiene configuración del reporte de service accounts."""
        return self.config.get('gcp', {}).get('service_accounts_reporter', {})
    
    def get_defaults(self) -> Dict:
        """Obtiene valores por defecto."""
        reporter_config = self.get_sa_reporter_config()
        return reporter_config.get('defaults', {})
    
    def get_security_config(self) -> Dict:
        """Obtiene configuración de seguridad."""
        reporter_config = self.get_sa_reporter_config()
        return reporter_config.get('security', {})
    
    def get_compliance_policies(self) -> List[Dict]:
        """Obtiene políticas de cumplimiento."""
        reporter_config = self.get_sa_reporter_config()
        return reporter_config.get('compliance', {}).get('policies', [])
    
    def get_dangerous_roles(self) -> List[str]:
        """Obtiene lista de roles peligrosos."""
        security_config = self.get_security_config()
        return security_config.get('dangerous_roles', [])
    
    def get_alert_risk_levels(self) -> List[str]:
        """Obtiene niveles de riesgo para alertas."""
        security_config = self.get_security_config()
        return security_config.get('alert_on_risk_level', ['HIGH', 'CRITICAL'])
    
    def get_notifications_config(self) -> Dict:
        """Obtiene configuración de notificaciones."""
        reporter_config = self.get_sa_reporter_config()
        return reporter_config.get('notifications', {})
    
    def is_enabled(self) -> bool:
        """Verifica si el reporte está habilitado."""
        return self.get_sa_reporter_config().get('enabled', False)
    
    def validate(self) -> tuple[bool, List[str]]:
        """Valida la configuración."""
        errors = []
        
        if not self.is_enabled():
            errors.append("Service Accounts Reporter no está habilitado en config.json")
        
        projects = self.get_projects()
        if not projects:
            errors.append("No hay proyectos configurados en config.json")
        
        defaults = self.get_defaults()
        if not defaults:
            errors.append("No hay valores por defecto configurados")
        
        return len(errors) == 0, errors
