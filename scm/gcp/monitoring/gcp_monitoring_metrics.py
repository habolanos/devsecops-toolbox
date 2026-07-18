#!/usr/bin/env python3
"""
GCP Monitoring Metrics Module - Fase 2
Obtiene métricas de uso actual (CPU, Memoria, Disco) de Cloud Monitoring API.

Versión: 1.7.2
Fecha: 18 de Julio de 2026
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from google.cloud import monitoring_v3
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


def get_gke_usage_metrics(
    project_id: str,
    cluster_name: str,
    location: str,
    debug: bool = False,
    console=None,
    logger: Optional[logging.Logger] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """Obtiene métricas de uso actual de un cluster GKE.
    
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
            'status': 'success' | 'error' | 'unavailable'
        }
    """
    if not MONITORING_AVAILABLE:
        return {
            'cpu_used_percent': None,
            'memory_used_percent': None,
            'status': 'unavailable'
        }
    
    try:
        # Inicializar cliente de Monitoring
        client = monitoring_v3.MetricServiceClient()
        project_name = f"projects/{project_id}"
        
        # Construir query MQL para CPU
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        
        interval = monitoring_v3.TimeInterval(
            {
                "end_time": {"seconds": int(end_time.timestamp())},
                "start_time": {"seconds": int(start_time.timestamp())},
            }
        )
        
        # Query para CPU del cluster
        cpu_query = f"""
        fetch k8s_cluster
        | metric 'kubernetes.io/container/cpu/core_usage_time'
        | filter resource.project_id == '{project_id}'
        | filter resource.cluster_name == '{cluster_name}'
        | filter resource.location == '{location}'
        | group_by [value_cpu: mean(value.cpu_usage)]
        """
        
        try:
            results_cpu = client.query_time_series(
                name=project_name,
                query=cpu_query
            )
            cpu_used = _extract_metric_value(results_cpu)
        except Exception as e:
            if logger:
                logger.warning(f"No se pudo obtener CPU para {cluster_name}: {e}")
            cpu_used = None
        
        # Query para Memoria del cluster
        memory_query = f"""
        fetch k8s_cluster
        | metric 'kubernetes.io/container/memory/used_bytes'
        | filter resource.project_id == '{project_id}'
        | filter resource.cluster_name == '{cluster_name}'
        | filter resource.location == '{location}'
        | group_by [value_mem: mean(value.memory_used)]
        """
        
        try:
            results_memory = client.query_time_series(
                name=project_name,
                query=memory_query
            )
            memory_used = _extract_metric_value(results_memory)
        except Exception as e:
            if logger:
                logger.warning(f"No se pudo obtener Memoria para {cluster_name}: {e}")
            memory_used = None
        
        return {
            'cpu_used_percent': round(cpu_used, 1) if cpu_used is not None else None,
            'memory_used_percent': round(memory_used, 1) if memory_used is not None else None,
            'status': 'success' if (cpu_used is not None or memory_used is not None) else 'unavailable'
        }
        
    except Exception as e:
        if logger:
            logger.error(f"Error obteniendo métricas de uso para cluster {cluster_name}: {e}")
        return {
            'cpu_used_percent': None,
            'memory_used_percent': None,
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
