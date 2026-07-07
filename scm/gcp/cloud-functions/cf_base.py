#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloud Functions Base Module

Módulo base para análisis de Cloud Functions.
Proporciona utilidades compartidas para todas las herramientas de CF.

Autor: Harold Adrian
"""

import subprocess
import json
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path


def run_gcloud_command(command: str, debug: bool = False) -> Optional[List[Dict]]:
    """Ejecuta un comando gcloud y retorna el resultado como JSON."""
    try:
        if debug:
            print(f"[DEBUG] {command}")
        
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            if debug:
                print(f"[ERROR] {result.stderr}")
            return None
        
        if not result.stdout.strip():
            return []
        
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        if debug:
            print(f"[EXCEPTION] {e}")
        return None


def get_output_dir(default: str = "outcome") -> Path:
    """Obtiene directorio de salida."""
    env = os.getenv("DEVSECOPS_OUTPUT_DIR")
    if env:
        p = Path(env)
        p.mkdir(parents=True, exist_ok=True)
        return p
    
    p = Path(default)
    p.mkdir(parents=True, exist_ok=True)
    return p


class CloudFunctionsBase:
    """Clase base para análisis de Cloud Functions."""
    
    def __init__(self, project_id: str, debug: bool = False):
        self.project_id = project_id
        self.debug = debug
    
    def validate_connection(self) -> bool:
        """Valida conexión a GCP."""
        try:
            cmd = f'gcloud projects describe {self.project_id} --format="value(projectId)" 2>&1'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def get_functions(self, region: str = "all") -> List[Dict]:
        """Obtiene funciones Cloud Functions."""
        if region == "all":
            cmd = f'gcloud functions list --project={self.project_id} --format=json'
        else:
            cmd = f'gcloud functions list --project={self.project_id} --region={region} --format=json'
        
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_function_details(self, function_name: str, region: str) -> Optional[Dict]:
        """Obtiene detalles de una función específica."""
        cmd = f'gcloud functions describe {function_name} --region={region} --project={self.project_id} --format=json'
        result = run_gcloud_command(cmd, self.debug)
        return result[0] if result else None
    
    def get_function_logs(self, function_name: str, region: str, limit: int = 50) -> List[Dict]:
        """Obtiene logs de una función."""
        cmd = f'gcloud functions logs read {function_name} --region={region} --project={self.project_id} --limit={limit} --format=json'
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_function_executions(self, function_name: str, region: str) -> List[Dict]:
        """Obtiene ejecuciones de una función (Cloud Run compatible)."""
        cmd = f'gcloud run executions list --service={function_name} --region={region} --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_iam_policy(self, function_name: str, region: str) -> Optional[Dict]:
        """Obtiene política IAM de una función."""
        cmd = f'gcloud functions get-iam-policy {function_name} --region={region} --project={self.project_id} --format=json'
        result = run_gcloud_command(cmd, self.debug)
        return result[0] if result else None
    
    def analyze_function_security(self, function: Dict) -> Dict:
        """Analiza seguridad de una función."""
        return {
            "is_public": self._check_public_access(function),
            "requires_authentication": function.get('serviceConfig', {}).get('securityLevel') == 'SECURE_ALWAYS',
            "ingress_settings": function.get('serviceConfig', {}).get('ingressSettings', 'ALLOW_ALL'),
            "service_account": function.get('serviceConfig', {}).get('serviceAccountEmail', 'default'),
            "environment_variables_count": len(function.get('serviceConfig', {}).get('environmentVariables', {}))
        }
    
    def _check_public_access(self, function: Dict) -> bool:
        """Verifica si la función es pública."""
        ingress = function.get('serviceConfig', {}).get('ingressSettings', 'ALLOW_ALL')
        return ingress == 'ALLOW_ALL'
    
    def analyze_function_performance(self, function: Dict) -> Dict:
        """Analiza performance de una función."""
        service_config = function.get('serviceConfig', {})
        
        return {
            "memory_mb": service_config.get('availableMemoryMb', 256),
            "timeout_seconds": service_config.get('timeoutSeconds', 60),
            "max_instances": service_config.get('maxInstanceCount', 100),
            "min_instances": service_config.get('minInstanceCount', 0),
            "cpu": service_config.get('cpu', '0.166'),
            "runtime": function.get('runtime', 'N/A')
        }
    
    def analyze_function_triggers(self, function: Dict) -> Dict:
        """Analiza triggers de una función."""
        event_trigger = function.get('eventTrigger', {})
        
        if event_trigger:
            return {
                "type": "EVENT",
                "event_type": event_trigger.get('eventType', 'N/A'),
                "resource": event_trigger.get('resource', 'N/A'),
                "service": event_trigger.get('service', 'N/A')
            }
        
        service_config = function.get('serviceConfig', {})
        if service_config.get('uri'):
            return {
                "type": "HTTP",
                "uri": service_config.get('uri', 'N/A'),
                "method": "POST"
            }
        
        return {"type": "UNKNOWN"}
    
    def calculate_estimated_cost(self, function: Dict, monthly_invocations: int = 1000000) -> Dict:
        """Calcula costo estimado de una función."""
        service_config = function.get('serviceConfig', {})
        memory_mb = service_config.get('availableMemoryMb', 256)
        timeout_seconds = service_config.get('timeoutSeconds', 60)
        
        # Estimación simplificada (basada en pricing de GCP)
        gb_seconds = (memory_mb / 1024) * (timeout_seconds / 60) * monthly_invocations
        
        # Primeros 2M invocaciones gratis, después $0.40 por millón
        invocation_cost = max(0, (monthly_invocations - 2000000) / 1000000 * 0.40)
        
        # Costo de compute: $0.0000025 por GB-segundo
        compute_cost = gb_seconds * 0.0000025
        
        return {
            "monthly_invocations": monthly_invocations,
            "gb_seconds": round(gb_seconds, 2),
            "invocation_cost": round(invocation_cost, 2),
            "compute_cost": round(compute_cost, 2),
            "total_monthly_estimate": round(invocation_cost + compute_cost, 2)
        }
    
    def get_function_metrics(self, function_name: str, region: str) -> Dict:
        """Obtiene métricas de una función."""
        # Nota: Requiere Cloud Monitoring API
        # Esta es una implementación simplificada
        return {
            "executions_count": 0,
            "error_count": 0,
            "error_rate": 0.0,
            "avg_duration_ms": 0,
            "p99_duration_ms": 0
        }
