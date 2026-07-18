#!/usr/bin/env python3
"""
GCP Monitoring Metrics Module - Fase 2
Obtiene métricas de uso actual (CPU, Memoria, Disco) de Cloud Monitoring REST API.

Versión: 1.7.2
Fecha: 18 de Julio de 2026
Basado en: gcp-project-cluster-health.sh
"""

import json
import logging
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

MONITORING_AVAILABLE = REQUESTS_AVAILABLE
MONITORING_API = "https://monitoring.googleapis.com/v3"
WINDOW = "24h"


def _get_gcloud_token() -> Optional[str]:
    """Obtiene token de acceso de gcloud (como en el script bash).
    
    Returns:
        Token de acceso o None si falla
    """
    try:
        result = subprocess.run(
            ['gcloud', 'auth', 'print-access-token'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _query_monitoring_rest(project_id: str, mql_query: str, logger=None) -> Optional[Dict]:
    """Consulta Monitoring API REST directamente (como en el script bash).
    
    Args:
        project_id: ID del proyecto GCP
        mql_query: Query MQL
        logger: Logger
        
    Returns:
        Respuesta JSON o None si falla
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    try:
        token = _get_gcloud_token()
        if not token:
            if logger:
                logger.warning("No se pudo obtener token de gcloud")
            return None
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{MONITORING_API}/projects/{project_id}/timeSeries:query"
        payload = {'query': mql_query}
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            if logger:
                logger.warning(f"Error en Monitoring API: {response.status_code} - {response.text[:200]}")
            return None
            
    except Exception as e:
        if logger:
            logger.warning(f"Error consultando Monitoring API: {e}")
        return None


def _extract_latest_value(response: Dict) -> Optional[float]:
    """Extrae el valor más reciente de la respuesta JSON.
    
    Basado en la lógica del script bash: get_latest_value()
    
    Args:
        response: Respuesta JSON de Monitoring API
        
    Returns:
        Valor numérico o None
    """
    try:
        if not response or 'timeSeriesData' not in response:
            return None
        
        for ts_data in response.get('timeSeriesData', []):
            if 'pointData' in ts_data:
                for point_data in ts_data['pointData']:
                    if 'values' in point_data:
                        for value in point_data['values']:
                            if 'doubleValue' in value:
                                return float(value['doubleValue'])
                            elif 'int64Value' in value:
                                return float(value['int64Value'])
        
        return None
    except Exception:
        return None


def get_gke_capacity_metrics(
    project_id: str,
    cluster_name: str,
    location: str,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """Obtiene CPU Total y Memoria Total de un cluster GKE usando REST API.
    
    Basado en: gcp-project-cluster-health.sh
    
    Args:
        project_id: ID del proyecto GCP
        cluster_name: Nombre del cluster
        location: Ubicación del cluster
        logger: Logger
        
    Returns:
        {
            'cpu_total': 12.0,
            'memory_total_gb': 48.0,
            'status': 'success' | 'error' | 'unavailable'
        }
    """
    if not MONITORING_AVAILABLE:
        return {
            'cpu_total': None,
            'memory_total_gb': None,
            'status': 'unavailable'
        }
    
    try:
        # Query MQL para CPU Total (allocatable cores)
        cpu_total_query = f"""fetch k8s_node | metric 'kubernetes.io/node/cpu/allocatable_cores' | filter resource.cluster_name == '{cluster_name}' && resource.location == '{location}' | within {WINDOW} | group_by [], sum(val())"""
        
        # Query MQL para Memoria Total (allocatable bytes)
        memory_total_query = f"""fetch k8s_node | metric 'kubernetes.io/node/memory/allocatable_bytes' | filter resource.cluster_name == '{cluster_name}' && resource.location == '{location}' | within {WINDOW} | group_by [], sum(val())"""
        
        # Obtener CPU Total
        cpu_response = _query_monitoring_rest(project_id, cpu_total_query, logger)
        cpu_total = _extract_latest_value(cpu_response) if cpu_response else None
        
        # Obtener Memoria Total
        memory_response = _query_monitoring_rest(project_id, memory_total_query, logger)
        memory_total_bytes = _extract_latest_value(memory_response) if memory_response else None
        
        # Convertir memoria de bytes a GB
        memory_total_gb = None
        if memory_total_bytes is not None:
            memory_total_gb = memory_total_bytes / (1024 ** 3)
        
        return {
            'cpu_total': round(cpu_total, 1) if cpu_total is not None else None,
            'memory_total_gb': round(memory_total_gb, 1) if memory_total_gb is not None else None,
            'status': 'success' if (cpu_total is not None or memory_total_gb is not None) else 'unavailable'
        }
        
    except Exception as e:
        if logger:
            logger.error(f"Error obteniendo capacidad para cluster {cluster_name}: {e}")
        return {
            'cpu_total': None,
            'memory_total_gb': None,
            'status': 'error'
        }


def get_gke_usage_metrics(
    project_id: str,
    cluster_name: str,
    location: str,
    debug: bool = False,
    console=None,
    logger: Optional[logging.Logger] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """Obtiene métricas de uso actual de un cluster GKE usando REST API.
    
    Basado en: gcp-project-cluster-health.sh
    
    Args:
        project_id: ID del proyecto GCP
        cluster_name: Nombre del cluster
        location: Ubicación del cluster
        debug: Modo debug
        console: Console de Rich
        logger: Logger
        timeout: Timeout en segundos
        
    Returns:
        {
            'cpu_used_percent': 45.2,
            'memory_used_percent': 62.1,
            'cpu_total': 12.0,
            'memory_total_gb': 48.0,
            'status': 'success' | 'error' | 'unavailable'
        }
    """
    if not MONITORING_AVAILABLE:
        return {
            'cpu_used_percent': None,
            'memory_used_percent': None,
            'cpu_total': None,
            'memory_total_gb': None,
            'status': 'unavailable'
        }
    
    try:
        # Query MQL para CPU Utilization (idéntica al script bash)
        cpu_query = f"""fetch k8s_node | metric 'kubernetes.io/node/cpu/allocatable_utilization' | filter resource.cluster_name == '{cluster_name}' && resource.location == '{location}' | within {WINDOW} | group_by [], mean(val())"""
        
        # Query MQL para Memoria Utilization (idéntica al script bash)
        memory_query = f"""fetch k8s_node | metric 'kubernetes.io/node/memory/allocatable_utilization' | filter resource.cluster_name == '{cluster_name}' && resource.location == '{location}' | within {WINDOW} | group_by [], mean(val())"""
        
        # Query MQL para CPU Total
        cpu_total_query = f"""fetch k8s_node | metric 'kubernetes.io/node/cpu/allocatable_cores' | filter resource.cluster_name == '{cluster_name}' && resource.location == '{location}' | within {WINDOW} | group_by [], sum(val())"""
        
        # Query MQL para Memoria Total
        memory_total_query = f"""fetch k8s_node | metric 'kubernetes.io/node/memory/allocatable_bytes' | filter resource.cluster_name == '{cluster_name}' && resource.location == '{location}' | within {WINDOW} | group_by [], sum(val())"""
        
        # Obtener Utilización
        cpu_response = _query_monitoring_rest(project_id, cpu_query, logger)
        cpu_used = _extract_latest_value(cpu_response) if cpu_response else None
        
        memory_response = _query_monitoring_rest(project_id, memory_query, logger)
        memory_used = _extract_latest_value(memory_response) if memory_response else None
        
        # Obtener Capacidad
        cpu_total_response = _query_monitoring_rest(project_id, cpu_total_query, logger)
        cpu_total = _extract_latest_value(cpu_total_response) if cpu_total_response else None
        
        memory_total_response = _query_monitoring_rest(project_id, memory_total_query, logger)
        memory_total_bytes = _extract_latest_value(memory_total_response) if memory_total_response else None
        
        # Convertir a porcentaje si es necesario
        if cpu_used is not None and cpu_used <= 1:
            cpu_used = cpu_used * 100
        if memory_used is not None and memory_used <= 1:
            memory_used = memory_used * 100
        
        # Convertir memoria de bytes a GB
        memory_total_gb = None
        if memory_total_bytes is not None:
            memory_total_gb = memory_total_bytes / (1024 ** 3)
        
        return {
            'cpu_used_percent': round(cpu_used, 1) if cpu_used is not None else None,
            'memory_used_percent': round(memory_used, 1) if memory_used is not None else None,
            'cpu_total': round(cpu_total, 1) if cpu_total is not None else None,
            'memory_total_gb': round(memory_total_gb, 1) if memory_total_gb is not None else None,
            'status': 'success' if (cpu_used is not None or memory_used is not None) else 'unavailable'
        }
        
    except Exception as e:
        if logger:
            logger.error(f"Error obteniendo métricas de uso para cluster {cluster_name}: {e}")
        return {
            'cpu_used_percent': None,
            'memory_used_percent': None,
            'cpu_total': None,
            'memory_total_gb': None,
            'status': 'error'
        }


def get_compute_usage_metrics(
    project_id: str,
    instance_name: str,
    zone: str,
    debug: bool = False,
    console=None,
    logger: Optional[logging.Logger] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """Obtiene métricas de uso actual de una instancia Compute Engine.
    
    Args:
        project_id: ID del proyecto GCP
        instance_name: Nombre de la instancia
        zone: Zona de la instancia
        debug: Modo debug
        console: Console de Rich
        logger: Logger
        timeout: Timeout en segundos
        
    Returns:
        {
            'cpu_used_percent': 35.2,
            'memory_used_percent': 58.1,
            'disk_used_percent': 72.3,
            'status': 'success' | 'error' | 'unavailable'
        }
    """
    if not MONITORING_AVAILABLE:
        return {
            'cpu_used_percent': None,
            'memory_used_percent': None,
            'disk_used_percent': None,
            'status': 'unavailable'
        }
    
    try:
        client = monitoring_v3.MetricServiceClient()
        project_name = f"projects/{project_id}"
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        
        # Query para CPU
        cpu_query = f"""
        fetch gce_instance
        | metric 'compute.googleapis.com/instance/cpu/utilization'
        | filter resource.project_id == '{project_id}'
        | filter resource.instance_id == '{instance_name}'
        | filter resource.zone == '{zone}'
        | group_by [value_cpu: mean(value.utilization)]
        """
        
        cpu_used = None
        try:
            results_cpu = client.query_time_series(
                name=project_name,
                query=cpu_query
            )
            cpu_value = _extract_metric_value(results_cpu)
            cpu_used = (cpu_value * 100) if cpu_value is not None else None
        except Exception as e:
            if logger:
                logger.warning(f"No se pudo obtener CPU para {instance_name}: {e}")
        
        # Query para Memoria
        memory_query = f"""
        fetch gce_instance
        | metric 'agent.googleapis.com/memory/percent_used'
        | filter resource.project_id == '{project_id}'
        | filter resource.instance_id == '{instance_name}'
        | filter resource.zone == '{zone}'
        | group_by [value_mem: mean(value.percent_used)]
        """
        
        memory_used = None
        try:
            results_memory = client.query_time_series(
                name=project_name,
                query=memory_query
            )
            memory_used = _extract_metric_value(results_memory)
        except Exception as e:
            if logger:
                logger.warning(f"No se pudo obtener Memoria para {instance_name}: {e}")
        
        # Query para Disco
        disk_query = f"""
        fetch gce_instance
        | metric 'agent.googleapis.com/disk/percent_used'
        | filter resource.project_id == '{project_id}'
        | filter resource.instance_id == '{instance_name}'
        | filter resource.zone == '{zone}'
        | group_by [value_disk: mean(value.percent_used)]
        """
        
        disk_used = None
        try:
            results_disk = client.query_time_series(
                name=project_name,
                query=disk_query
            )
            disk_used = _extract_metric_value(results_disk)
        except Exception as e:
            if logger:
                logger.warning(f"No se pudo obtener Disco para {instance_name}: {e}")
        
        return {
            'cpu_used_percent': round(cpu_used, 1) if cpu_used is not None else None,
            'memory_used_percent': round(memory_used, 1) if memory_used is not None else None,
            'disk_used_percent': round(disk_used, 1) if disk_used is not None else None,
            'status': 'success' if any([cpu_used, memory_used, disk_used]) else 'unavailable'
        }
        
    except Exception as e:
        if logger:
            logger.error(f"Error obteniendo métricas de uso para instancia {instance_name}: {e}")
        return {
            'cpu_used_percent': None,
            'memory_used_percent': None,
            'disk_used_percent': None,
            'status': 'error'
        }


def _extract_metric_value(results) -> Optional[float]:
    """Extrae el valor de métrica de los resultados de query.
    
    Args:
        results: Resultados de query_time_series
        
    Returns:
        Valor numérico o None si no hay datos
    """
    try:
        if not results or len(results) == 0:
            return None
        
        # Obtener primer resultado
        result = results[0]
        
        if not hasattr(result, 'points') or len(result.points) == 0:
            return None
        
        # Obtener último punto (más reciente)
        point = result.points[-1]
        
        if hasattr(point, 'value'):
            value = point.value
            
            # Extraer valor según tipo
            if hasattr(value, 'double_value'):
                return float(value.double_value)
            elif hasattr(value, 'int64_value'):
                return float(value.int64_value)
            elif isinstance(value, (int, float)):
                return float(value)
        
        return None
        
    except Exception:
        return None


def get_gke_metrics_parallel(
    project_id: str,
    clusters: List[Dict[str, Any]],
    max_workers: int = 6,
    debug: bool = False,
    console=None,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Dict[str, Any]]:
    """Obtiene métricas de uso para múltiples clusters GKE en paralelo.
    
    Args:
        project_id: ID del proyecto GCP
        clusters: Lista de clusters
        max_workers: Número máximo de workers
        debug: Modo debug
        console: Console de Rich
        logger: Logger
        
    Returns:
        {
            'cluster_name': {
                'cpu_used_percent': X,
                'memory_used_percent': Y,
                'status': 'success'|'error'|'unavailable'
            }
        }
    """
    metrics = {}
    
    if not clusters:
        return metrics
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                get_gke_usage_metrics,
                project_id,
                cluster['name'],
                cluster['location'],
                debug,
                console,
                logger
            ): cluster['name']
            for cluster in clusters
        }
        
        for future in as_completed(futures):
            cluster_name = futures[future]
            try:
                result = future.result(timeout=30)
                metrics[cluster_name] = result
            except Exception as e:
                if logger:
                    logger.error(f"Error obteniendo métricas para {cluster_name}: {e}")
                metrics[cluster_name] = {
                    'cpu_used_percent': None,
                    'memory_used_percent': None,
                    'status': 'error'
                }
    
    return metrics


def get_compute_metrics_parallel(
    project_id: str,
    instances: List[Dict[str, Any]],
    max_workers: int = 6,
    debug: bool = False,
    console=None,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Dict[str, Any]]:
    """Obtiene métricas de uso para múltiples instancias Compute Engine en paralelo.
    
    Args:
        project_id: ID del proyecto GCP
        instances: Lista de instancias
        max_workers: Número máximo de workers
        debug: Modo debug
        console: Console de Rich
        logger: Logger
        
    Returns:
        {
            'instance_name': {
                'cpu_used_percent': X,
                'memory_used_percent': Y,
                'disk_used_percent': Z,
                'status': 'success'|'error'|'unavailable'
            }
        }
    """
    metrics = {}
    
    if not instances:
        return metrics
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                get_compute_usage_metrics,
                project_id,
                instance['name'],
                instance['zone'],
                debug,
                console,
                logger
            ): instance['name']
            for instance in instances
        }
        
        for future in as_completed(futures):
            instance_name = futures[future]
            try:
                result = future.result(timeout=30)
                metrics[instance_name] = result
            except Exception as e:
                if logger:
                    logger.error(f"Error obteniendo métricas para {instance_name}: {e}")
                metrics[instance_name] = {
                    'cpu_used_percent': None,
                    'memory_used_percent': None,
                    'disk_used_percent': None,
                    'status': 'error'
                }
    
    return metrics


def format_percentage(value: Optional[float]) -> str:
    """Formatea un valor de porcentaje para mostrar en tabla.
    
    Args:
        value: Valor numérico o None
        
    Returns:
        String formateado (ej: "45.2%") o "N/A"
    """
    if value is None:
        return "N/A"
    return f"{value:.1f}%"
