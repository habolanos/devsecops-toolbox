"""
Extractores para Service Accounts
Extrae datos de GCP usando gcloud CLI
"""

import json
import subprocess
from typing import Dict, List, Optional
from datetime import datetime


def run_gcloud_command(cmd: str, debug: bool = False) -> Optional[Dict]:
    """Ejecuta comando gcloud y retorna JSON."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            if debug:
                print(f"❌ Error en gcloud: {result.stderr}")
            return None
        return json.loads(result.stdout) if result.stdout else None
    except json.JSONDecodeError:
        if debug:
            print(f"❌ Error al parsear JSON de gcloud")
        return None
    except Exception as e:
        if debug:
            print(f"❌ Error ejecutando gcloud: {e}")
        return None


class ServiceAccountExtractor:
    """Extrae service accounts de un proyecto."""
    
    def __init__(self, project_id: str, debug: bool = False):
        self.project_id = project_id
        self.debug = debug
    
    def extract_all(self) -> Dict:
        """Extrae todos los datos de service accounts."""
        return {
            'project_id': self.project_id,
            'service_accounts': self.get_service_accounts(),
            'iam_bindings': self.get_iam_bindings()
        }
    
    def get_service_accounts(self) -> List[Dict]:
        """Obtiene lista de service accounts."""
        cmd = f'gcloud iam service-accounts list --project={self.project_id} --format=json'
        result = run_gcloud_command(cmd, self.debug)
        
        if not result:
            return []
        
        # Procesar y enriquecer datos
        service_accounts = []
        for sa in result:
            sa_data = {
                'email': sa.get('email', ''),
                'display_name': sa.get('displayName', ''),
                'disabled': sa.get('disabled', False),
                'created_at': sa.get('createTime', ''),
                'description': sa.get('description', '')
            }
            
            # Obtener claves
            sa_data['keys'] = self.get_keys(sa_data['email'])
            
            service_accounts.append(sa_data)
        
        return service_accounts
    
    def get_iam_bindings(self) -> List[Dict]:
        """Obtiene bindings IAM del proyecto."""
        cmd = f'gcloud projects get-iam-policy {self.project_id} --format=json'
        result = run_gcloud_command(cmd, self.debug)
        
        if not result:
            return []
        
        return result.get('bindings', [])
    
    def get_keys(self, sa_email: str) -> List[Dict]:
        """Obtiene claves de un service account."""
        cmd = f'gcloud iam service-accounts keys list --iam-account={sa_email} --format=json'
        result = run_gcloud_command(cmd, self.debug)
        
        if not result:
            return []
        
        # Procesar claves
        keys = []
        for key in result:
            key_data = {
                'key_id': key.get('name', '').split('/')[-1],
                'key_type': key.get('keyType', ''),
                'created_at': key.get('validAfterTime', ''),
                'valid_before': key.get('validBeforeTime', ''),
                'algorithm': key.get('keyAlgorithm', ''),
                'age_days': self._calculate_age_days(key.get('validAfterTime', '')),
                'days_until_expiry': self._calculate_days_until_expiry(key.get('validBeforeTime', ''))
            }
            keys.append(key_data)
        
        return keys
    
    def _calculate_age_days(self, created_at: str) -> int:
        """Calcula edad de la clave en días."""
        if not created_at:
            return 0
        try:
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            today = datetime.now(created.tzinfo)
            return (today - created).days
        except:
            return 0
    
    def _calculate_days_until_expiry(self, expires_at: str) -> int:
        """Calcula días hasta expiración."""
        if not expires_at:
            return None
        try:
            expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            today = datetime.now(expiry.tzinfo)
            days = (expiry - today).days
            return days if days >= 0 else None
        except:
            return None
