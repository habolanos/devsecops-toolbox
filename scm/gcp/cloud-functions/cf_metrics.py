#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloud Functions Metrics Module

Cálculos de métricas y análisis para Cloud Functions.

Autor: Harold Adrian
"""

from typing import List, Dict, Any
from datetime import datetime


class CloudFunctionsMetrics:
    """Clase para cálculos de métricas de Cloud Functions."""
    
    @staticmethod
    def calculate_health_score(function: Dict) -> int:
        """Calcula score de salud de una función (0-100)."""
        score = 100
        
        # Penalización por configuración de seguridad
        service_config = function.get('serviceConfig', {})
        
        if service_config.get('ingressSettings') == 'ALLOW_ALL':
            score -= 20  # Función pública
        
        # Penalización por timeout bajo
        timeout = service_config.get('timeoutSeconds', 60)
        if timeout < 30:
            score -= 10
        
        # Penalización por memoria baja
        memory = service_config.get('availableMemoryMb', 256)
        if memory < 256:
            score -= 15
        
        # Penalización por min instances alto
        min_instances = service_config.get('minInstanceCount', 0)
        if min_instances > 10:
            score -= 10
        
        return max(0, score)
    
    @staticmethod
    def calculate_security_score(function: Dict) -> int:
        """Calcula score de seguridad (0-100)."""
        score = 100
        
        service_config = function.get('serviceConfig', {})
        
        # Verificar acceso público
        if service_config.get('ingressSettings') == 'ALLOW_ALL':
            score -= 30
        
        # Verificar autenticación
        if not service_config.get('securityLevel') == 'SECURE_ALWAYS':
            score -= 20
        
        # Verificar service account
        sa = service_config.get('serviceAccountEmail', '')
        if 'default' in sa.lower():
            score -= 15
        
        # Verificar variables de entorno (posibles secretos)
        env_vars = service_config.get('environmentVariables', {})
        for key in env_vars:
            if any(x in key.upper() for x in ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']):
                score -= 10
                break
        
        return max(0, score)
    
    @staticmethod
    def calculate_cost_efficiency_score(function: Dict, monthly_invocations: int = 1000000) -> int:
        """Calcula score de eficiencia de costos (0-100)."""
        score = 100
        
        service_config = function.get('serviceConfig', {})
        memory = service_config.get('availableMemoryMb', 256)
        timeout = service_config.get('timeoutSeconds', 60)
        
        # Penalización por memoria alta sin justificación
        if memory > 2048:
            score -= 20
        elif memory > 1024:
            score -= 10
        
        # Penalización por timeout alto
        if timeout > 300:
            score -= 15
        elif timeout > 120:
            score -= 5
        
        # Penalización por min instances alto
        min_instances = service_config.get('minInstanceCount', 0)
        if min_instances > 5:
            score -= 20
        elif min_instances > 0:
            score -= 10
        
        return max(0, score)
    
    @staticmethod
    def categorize_function(function: Dict) -> str:
        """Categoriza una función por tipo."""
        event_trigger = function.get('eventTrigger', {})
        
        if event_trigger:
            event_type = event_trigger.get('eventType', '')
            if 'pubsub' in event_type.lower():
                return 'PUBSUB'
            elif 'storage' in event_type.lower():
                return 'STORAGE'
            elif 'firestore' in event_type.lower():
                return 'FIRESTORE'
            elif 'database' in event_type.lower():
                return 'REALTIME_DB'
            else:
                return 'EVENT'
        
        return 'HTTP'
    
    @staticmethod
    def estimate_monthly_cost(function: Dict, invocations: int = 1000000) -> float:
        """Estima costo mensual de una función."""
        service_config = function.get('serviceConfig', {})
        memory_mb = service_config.get('availableMemoryMb', 256)
        timeout_seconds = service_config.get('timeoutSeconds', 60)
        
        # Cálculo de GB-segundos
        gb_seconds = (memory_mb / 1024) * (timeout_seconds / 60) * invocations
        
        # Pricing de GCP (aproximado)
        # Primeros 2M invocaciones gratis
        invocation_cost = max(0, (invocations - 2000000) / 1000000 * 0.40)
        
        # Compute: $0.0000025 por GB-segundo
        compute_cost = gb_seconds * 0.0000025
        
        return round(invocation_cost + compute_cost, 2)
    
    @staticmethod
    def get_runtime_status(function: Dict) -> str:
        """Obtiene estado del runtime."""
        state = function.get('state', 'UNKNOWN')
        
        if state == 'ACTIVE':
            return 'ACTIVE'
        elif state == 'OFFLINE':
            return 'OFFLINE'
        elif state == 'DEPLOY_IN_PROGRESS':
            return 'DEPLOYING'
        elif state == 'DELETE_IN_PROGRESS':
            return 'DELETING'
        else:
            return 'UNKNOWN'
    
    @staticmethod
    def get_update_status(function: Dict) -> Dict:
        """Obtiene información de última actualización."""
        update_time = function.get('updateTime', '')
        
        if update_time:
            try:
                update_dt = datetime.fromisoformat(update_time.replace('Z', '+00:00'))
                days_ago = (datetime.now(update_dt.tzinfo) - update_dt).days
                return {
                    'last_update': update_time,
                    'days_since_update': days_ago,
                    'status': 'RECENT' if days_ago < 30 else 'STALE' if days_ago > 180 else 'MODERATE'
                }
            except:
                pass
        
        return {
            'last_update': 'UNKNOWN',
            'days_since_update': -1,
            'status': 'UNKNOWN'
        }
    
    @staticmethod
    def compare_functions(functions: List[Dict]) -> Dict:
        """Compara múltiples funciones."""
        if not functions:
            return {}
        
        return {
            'total_functions': len(functions),
            'by_runtime': CloudFunctionsMetrics._group_by_runtime(functions),
            'by_trigger_type': CloudFunctionsMetrics._group_by_trigger(functions),
            'by_region': CloudFunctionsMetrics._group_by_region(functions),
            'avg_memory_mb': CloudFunctionsMetrics._calculate_avg_memory(functions),
            'avg_timeout_seconds': CloudFunctionsMetrics._calculate_avg_timeout(functions),
            'public_functions': CloudFunctionsMetrics._count_public_functions(functions),
            'total_estimated_cost': CloudFunctionsMetrics._calculate_total_cost(functions)
        }
    
    @staticmethod
    def _group_by_runtime(functions: List[Dict]) -> Dict:
        """Agrupa funciones por runtime."""
        groups = {}
        for func in functions:
            runtime = func.get('runtime', 'UNKNOWN')
            groups[runtime] = groups.get(runtime, 0) + 1
        return groups
    
    @staticmethod
    def _group_by_trigger(functions: List[Dict]) -> Dict:
        """Agrupa funciones por tipo de trigger."""
        groups = {}
        for func in functions:
            trigger_type = CloudFunctionsMetrics.categorize_function(func)
            groups[trigger_type] = groups.get(trigger_type, 0) + 1
        return groups
    
    @staticmethod
    def _group_by_region(functions: List[Dict]) -> Dict:
        """Agrupa funciones por región."""
        groups = {}
        for func in functions:
            region = func.get('serviceConfig', {}).get('region', 'UNKNOWN')
            groups[region] = groups.get(region, 0) + 1
        return groups
    
    @staticmethod
    def _calculate_avg_memory(functions: List[Dict]) -> float:
        """Calcula memoria promedio."""
        if not functions:
            return 0
        total = sum(f.get('serviceConfig', {}).get('availableMemoryMb', 256) for f in functions)
        return round(total / len(functions), 2)
    
    @staticmethod
    def _calculate_avg_timeout(functions: List[Dict]) -> float:
        """Calcula timeout promedio."""
        if not functions:
            return 0
        total = sum(f.get('serviceConfig', {}).get('timeoutSeconds', 60) for f in functions)
        return round(total / len(functions), 2)
    
    @staticmethod
    def _count_public_functions(functions: List[Dict]) -> int:
        """Cuenta funciones públicas."""
        return sum(
            1 for f in functions
            if f.get('serviceConfig', {}).get('ingressSettings') == 'ALLOW_ALL'
        )
    
    @staticmethod
    def _calculate_total_cost(functions: List[Dict]) -> float:
        """Calcula costo total estimado."""
        total = 0
        for func in functions:
            total += CloudFunctionsMetrics.estimate_monthly_cost(func)
        return round(total, 2)
