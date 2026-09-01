#!/usr/bin/env python3
"""
AWS CloudWatch Metrics Module - Homologación a GCP Monitoring Metrics

Obtiene métricas de uso actual (CPU, Memoria, Requests, Latencia) de
ECS Fargate, EKS y Lambda a través de CloudWatch.

Versión: 1.7.50
Fecha: 31 de Agosto de 2026
"""

import json
import logging
import boto3
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


def _format_percentage(value: Optional[float]) -> str:
    """Formatea un porcentaje a string legible."""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"


def _get_cloudwatch_client(profile: str = "default", region: str = "us-east-1"):
    """Crea cliente boto3 de CloudWatch."""
    try:
        session = boto3.Session(profile_name=profile)
        return session.client("cloudwatch", region_name=region)
    except Exception:
        return None


def _get_metric_statistics(
    cloudwatch,
    namespace: str,
    metric_name: str,
    dimensions: List[Dict[str, str]],
    statistic: str,
    minutes: int = 5
) -> Optional[float]:
    """Consulta CloudWatch GetMetricStatistics y retorna el último dato."""
    if not cloudwatch:
        return None

    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=minutes)

        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=60,
            Statistics=[statistic],
            Unit="Count" if "Count" in metric_name else None
        )

        datapoints = response.get("Datapoints", [])
        if not datapoints:
            return None

        # Ordenar por timestamp descendente y tomar el más reciente
        datapoints_sorted = sorted(
            datapoints,
            key=lambda x: x.get("Timestamp", datetime.min),
            reverse=True
        )
        return float(datapoints_sorted[0][statistic])
    except Exception:
        return None


def get_ecs_fargate_usage_metrics(
    cluster: str,
    service_name: str,
    profile: str = "default",
    region: str = "us-east-1",
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """Obtiene métricas de uso de un servicio ECS Fargate via CloudWatch.

    Métricas obtenidas:
    - Request count (últimos 5 min)
    - Latencia p95 (ms)
    - CPU utilizado (%)
    - Memoria utilizada (%)
    - Tasa de errores (4xx+5xx / total)

    Args:
        cluster: Nombre del cluster ECS
        service_name: Nombre del servicio ECS
        profile: AWS profile
        region: AWS region
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
    cloudwatch = _get_cloudwatch_client(profile, region)

    if not cloudwatch:
        return {
            "request_count": None,
            "latency_p95_ms": None,
            "cpu_percent": None,
            "memory_percent": None,
            "error_rate_percent": None,
            "status": "unavailable"
        }

    try:
        base_dimensions = [
            {"Name": "ClusterName", "Value": cluster},
            {"Name": "ServiceName", "Value": service_name}
        ]

        # Request count (AWS ApplicationELB si service está detrás de ALB,
        # o contadores personalizados; usamos RequestCount si está disponible)
        request_count = _get_metric_statistics(
            cloudwatch,
            "AWS/ApplicationELB",
            "RequestCount",
            [{"Name": "LoadBalancer", "Value": service_name}],
            "Sum"
        )

        # Latencia p95 (ALB)
        latency_p95 = _get_metric_statistics(
            cloudwatch,
            "AWS/ApplicationELB",
            "TargetResponseTime",
            [{"Name": "LoadBalancer", "Value": service_name}],
            "p95"
        )

        # CPU utilizado (%)
        cpu_percent = _get_metric_statistics(
            cloudwatch,
            "AWS/ECS",
            "CPUUtilization",
            base_dimensions,
            "Average"
        )

        # Memoria utilizada (%)
        memory_percent = _get_metric_statistics(
            cloudwatch,
            "AWS/ECS",
            "MemoryUtilization",
            base_dimensions,
            "Average"
        )

        # Error rate: HTTPCode_Target_4XX_Count + 5XX / RequestCount
        error_4xx = _get_metric_statistics(
            cloudwatch,
            "AWS/ApplicationELB",
            "HTTPCode_Target_4XX_Count",
            [{"Name": "LoadBalancer", "Value": service_name}],
            "Sum"
        ) or 0

        error_5xx = _get_metric_statistics(
            cloudwatch,
            "AWS/ApplicationELB",
            "HTTPCode_Target_5XX_Count",
            [{"Name": "LoadBalancer", "Value": service_name}],
            "Sum"
        ) or 0

        if request_count and request_count > 0:
            error_rate = ((error_4xx + error_5xx) / request_count) * 100
        else:
            error_rate = None

        return {
            "request_count": int(request_count) if request_count is not None else None,
            "latency_p95_ms": round(latency_p95 * 1000, 1) if latency_p95 is not None else None,
            "cpu_percent": round(cpu_percent, 1) if cpu_percent is not None else None,
            "memory_percent": round(memory_percent, 1) if memory_percent is not None else None,
            "error_rate_percent": round(error_rate, 2) if error_rate is not None else None,
            "status": "success" if any([request_count, latency_p95, cpu_percent, memory_percent]) else "unavailable"
        }

    except Exception as e:
        if logger:
            logger.error(f"Error obteniendo métricas ECS Fargate para {service_name}: {e}")
        return {
            "request_count": None,
            "latency_p95_ms": None,
            "cpu_percent": None,
            "memory_percent": None,
            "error_rate_percent": None,
            "status": "error"
        }


def get_ecs_fargate_metrics_parallel(
    cluster: str,
    services: List[Dict[str, Any]],
    profile: str = "default",
    region: str = "us-east-1",
    max_workers: int = 6,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Dict[str, Any]]:
    """Obtiene métricas de uso para múltiples servicios ECS Fargate en paralelo.

    Args:
        cluster: Nombre del cluster ECS
        services: Lista de dicts con 'name'
        profile: AWS profile
        region: AWS region
        max_workers: Número máximo de workers
        logger: Logger

    Returns:
        {
            'service_name': {
                'request_count': X,
                'latency_p95_ms': Y,
                'cpu_percent': Z,
                'memory_percent': W,
                'status': 'success'|'error'|'unavailable'
            }
        }
    """
    metrics = {}

    if not services:
        return metrics

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                get_ecs_fargate_usage_metrics,
                cluster,
                svc["name"],
                profile,
                region,
                logger
            ): svc["name"]
            for svc in services
        }

        for future in as_completed(futures):
            service_name = futures[future]
            try:
                result = future.result()
                metrics[service_name] = result
            except Exception as e:
                if logger:
                    logger.warning(f"Error en métricas paralelas para {service_name}: {e}")
                metrics[service_name] = {
                    "request_count": None,
                    "latency_p95_ms": None,
                    "cpu_percent": None,
                    "memory_percent": None,
                    "error_rate_percent": None,
                    "status": "error"
                }

    return metrics
