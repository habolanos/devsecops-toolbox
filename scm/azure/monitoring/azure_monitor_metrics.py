#!/usr/bin/env python3
"""
Azure Monitor Metrics Module - Homologación a GCP Monitoring Metrics

Obtiene métricas de uso actual (CPU, Memoria, Requests, Latencia) de
Azure Container Apps, App Service y AKS a través de Azure Monitor.

Versión: 1.7.53
Fecha: 1 de Septiembre de 2026
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed


def _format_percentage(value: Optional[float]) -> str:
    """Formatea un porcentaje a string legible."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.resource import SubscriptionClient
    from azure.monitor.query import MetricsQueryClient, MetricAggregationType
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False


def _get_metrics_client() -> Optional[Any]:
    """Crea cliente de Azure Monitor Metrics."""
    if not AZURE_AVAILABLE:
        return None
    try:
        credential = DefaultAzureCredential()
        return MetricsQueryClient(credential)
    except Exception:
        return None


def _query_metric(
    client,
    resource_id: str,
    metric_name: str,
    aggregation: str = "Average",
    timespan_minutes: int = 5,
    logger: Optional[logging.Logger] = None
) -> Optional[float]:
    """Consulta una métrica de Azure Monitor."""
    if not client:
        return None
    
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=timespan_minutes)
        
        response = client.query_resource(
            resource_id=resource_id,
            metric_names=[metric_name],
            aggregations=[aggregation],
            timespan=f"{start_time.isoformat()}/{end_time.isoformat()}"
        )
        
        for metric in response.metrics:
            for time_series in metric.timeseries:
                for data in time_series.data:
                    if hasattr(data, aggregation.lower()):
                        value = getattr(data, aggregation.lower())
                        if value is not None:
                            return float(value)
        return None
    except Exception as e:
        if logger:
            logger.warning(f"No se pudo obtener {metric_name} para {resource_id}: {e}")
        return None


def get_container_app_usage_metrics(
    resource_id: str,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """Obtiene métricas de uso de una Container App via Azure Monitor.
    
    Métricas obtenidas:
    - Request count (últimos 5 min)
    - Latencia p95 (ms)
    - CPU utilizado (%)
    - Memoria utilizada (%)
    - Tasa de errores
    
    Args:
        resource_id: Azure resource ID de la Container App
        logger: Logger
    
    Returns:
        {
            'request_count': int,
            'latency_p95_ms': float,
            'cpu_percent': float,
            'memory_percent': float,
            'error_rate_percent': float,
            'status': 'success' | 'error' | 'unavailable'
        }
    """
    client = _get_metrics_client()
    
    if not client:
        return {
            "request_count": None,
            "latency_p95_ms": None,
            "cpu_percent": None,
            "memory_percent": None,
            "error_rate_percent": None,
            "status": "unavailable"
        }
    
    try:
        # Azure Container Apps métricas
        request_count = _query_metric(client, resource_id, "Requests", "Total", logger=logger)
        latency_p95 = _query_metric(client, resource_id, "ResponseTime", "Average", logger=logger)
        cpu_percent = _query_metric(client, resource_id, "CpuUsage", "Average", logger=logger)
        memory_percent = _query_metric(client, resource_id, "MemoryUsage", "Average", logger=logger)
        
        # Errores (si existe métrica de HTTP 5xx)
        error_count = _query_metric(client, resource_id, "Http5xxError", "Total", logger=logger)
        
        if request_count is not None and request_count > 0 and error_count is not None:
            error_rate = (error_count / request_count) * 100
        else:
            error_rate = None
        
        return {
            "request_count": int(request_count) if request_count is not None else None,
            "latency_p95_ms": round(latency_p95, 1) if latency_p95 is not None else None,
            "cpu_percent": round(cpu_percent, 1) if cpu_percent is not None else None,
            "memory_percent": round(memory_percent, 1) if memory_percent is not None else None,
            "error_rate_percent": round(error_rate, 2) if error_rate is not None else None,
            "status": "success" if any([request_count, latency_p95, cpu_percent, memory_percent]) else "unavailable"
        }
    
    except Exception as e:
        if logger:
            logger.error(f"Error obteniendo métricas Container App {resource_id}: {e}")
        return {
            "request_count": None,
            "latency_p95_ms": None,
            "cpu_percent": None,
            "memory_percent": None,
            "error_rate_percent": None,
            "status": "error"
        }


def get_container_app_metrics_parallel(
    apps: List[Dict[str, Any]],
    max_workers: int = 6,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Dict[str, Any]]:
    """Obtiene métricas de uso para múltiples Container Apps en paralelo.
    
    Args:
        apps: Lista de dicts con 'name' y 'resource_id'
        max_workers: Número máximo de workers
        logger: Logger
    
    Returns:
        {
            'app_name': {
                'request_count': X,
                'latency_p95_ms': Y,
                'cpu_percent': Z,
                'memory_percent': W,
                'status': 'success'|'error'|'unavailable'
            }
        }
    """
    metrics = {}
    
    if not apps:
        return metrics
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                get_container_app_usage_metrics,
                app["resource_id"],
                logger
            ): app["name"]
            for app in apps
        }
        
        for future in as_completed(futures):
            app_name = futures[future]
            try:
                result = future.result()
                metrics[app_name] = result
            except Exception as e:
                if logger:
                    logger.warning(f"Error en métricas paralelas para {app_name}: {e}")
                metrics[app_name] = {
                    "request_count": None,
                    "latency_p95_ms": None,
                    "cpu_percent": None,
                    "memory_percent": None,
                    "error_rate_percent": None,
                    "status": "error"
                }
    
    return metrics
