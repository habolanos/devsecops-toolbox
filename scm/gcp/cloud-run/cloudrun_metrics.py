#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloud Run Metrics Module

Módulo de cálculo de métricas para Cloud Run.
Proporciona funciones para análisis de rendimiento, costos, etc.

Autor: Harold Adrian
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics


class CloudRunMetrics:
    """Cálculo de métricas para Cloud Run"""
    
    # Costos por región (USD por millón de invocaciones)
    INVOCATION_COSTS = {
        "us-central1": 0.40,
        "us-east1": 0.40,
        "us-west1": 0.40,
        "europe-west1": 0.44,
        "asia-northeast1": 0.44,
        "default": 0.40
    }
    
    # Costos de CPU (USD por CPU-segundo)
    CPU_COSTS = {
        "us-central1": 0.000024,
        "us-east1": 0.000024,
        "us-west1": 0.000024,
        "europe-west1": 0.000026,
        "asia-northeast1": 0.000026,
        "default": 0.000024
    }
    
    # Costos de memoria (USD por GB-segundo)
    MEMORY_COSTS = {
        "us-central1": 0.0000025,
        "us-east1": 0.0000025,
        "us-west1": 0.0000025,
        "europe-west1": 0.0000027,
        "asia-northeast1": 0.0000027,
        "default": 0.0000025
    }
    
    @staticmethod
    def calculate_health_score(
        service: Dict,
        metrics: Dict
    ) -> int:
        """
        Calcula score de salud (0-100).
        
        Factores:
        - Availability (30%)
        - Performance (30%)
        - Error Rate (20%)
        - Resource Usage (20%)
        
        Args:
            service: Datos del servicio
            metrics: Métricas calculadas
        
        Returns:
            Score de salud (0-100)
        """
        availability = metrics.get("availability", 100)
        performance = metrics.get("performance", 100)
        error_rate = metrics.get("error_rate", 0)
        resource_usage = metrics.get("resource_usage", 50)
        
        # Validar rangos
        availability = max(0, min(100, availability))
        performance = max(0, min(100, performance))
        error_rate = max(0, min(100, error_rate))
        resource_usage = max(0, min(100, resource_usage))
        
        score = (
            availability * 0.30 +
            performance * 0.30 +
            (100 - error_rate) * 0.20 +
            (100 - resource_usage) * 0.20
        )
        
        return int(score)
    
    @staticmethod
    def calculate_costs(
        service: Dict,
        region: str,
        invocations: int = 0,
        cpu_seconds: float = 0.0,
        memory_gb_seconds: float = 0.0
    ) -> Dict:
        """
        Calcula costos estimados.
        
        Basado en:
        - CPU allocation
        - Memory allocation
        - Invocations
        - Outbound traffic
        
        Args:
            service: Datos del servicio
            region: Región GCP
            invocations: Número de invocaciones
            cpu_seconds: CPU-segundos consumidos
            memory_gb_seconds: GB-segundos de memoria consumida
        
        Returns:
            Diccionario con desglose de costos
        """
        invocation_cost = CloudRunMetrics.INVOCATION_COSTS.get(region, CloudRunMetrics.INVOCATION_COSTS["default"])
        cpu_cost = CloudRunMetrics.CPU_COSTS.get(region, CloudRunMetrics.CPU_COSTS["default"])
        memory_cost = CloudRunMetrics.MEMORY_COSTS.get(region, CloudRunMetrics.MEMORY_COSTS["default"])
        
        # Calcular costos
        invocation_total = (invocations / 1_000_000) * invocation_cost if invocations > 0 else 0
        cpu_total = cpu_seconds * cpu_cost if cpu_seconds > 0 else 0
        memory_total = memory_gb_seconds * memory_cost if memory_gb_seconds > 0 else 0
        
        total = invocation_total + cpu_total + memory_total
        
        return {
            "invocation_cost": round(invocation_total, 4),
            "cpu_cost": round(cpu_total, 4),
            "memory_cost": round(memory_total, 4),
            "total_cost": round(total, 4),
            "currency": "USD"
        }
    
    @staticmethod
    def calculate_monthly_projection(
        daily_cost: float,
        days_of_data: int = 7
    ) -> Dict:
        """
        Proyecta costos mensuales.
        
        Args:
            daily_cost: Costo diario promedio
            days_of_data: Días de datos disponibles
        
        Returns:
            Diccionario con proyecciones
        """
        monthly_projection = daily_cost * 30
        yearly_projection = daily_cost * 365
        
        return {
            "daily_average": round(daily_cost, 2),
            "monthly_projection": round(monthly_projection, 2),
            "yearly_projection": round(yearly_projection, 2),
            "days_of_data": days_of_data,
            "currency": "USD"
        }
    
    @staticmethod
    def detect_anomalies(
        metrics_history: List[Dict],
        metric_name: str,
        threshold_std_dev: float = 2.0
    ) -> List[Dict]:
        """
        Detecta anomalías en métricas.
        
        Usa desviación estándar para identificar valores anómalos.
        
        Args:
            metrics_history: Histórico de métricas
            metric_name: Nombre de la métrica a analizar
            threshold_std_dev: Número de desviaciones estándar para considerar anomalía
        
        Returns:
            Lista de anomalías detectadas
        """
        if not metrics_history or len(metrics_history) < 3:
            return []
        
        values = [m.get(metric_name, 0) for m in metrics_history if metric_name in m]
        
        if len(values) < 3:
            return []
        
        try:
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            
            if stdev == 0:
                return []
            
            anomalies = []
            for i, metric in enumerate(metrics_history):
                if metric_name not in metric:
                    continue
                
                value = metric[metric_name]
                z_score = abs((value - mean) / stdev)
                
                if z_score > threshold_std_dev:
                    anomalies.append({
                        "index": i,
                        "timestamp": metric.get("timestamp", ""),
                        "value": value,
                        "mean": round(mean, 2),
                        "z_score": round(z_score, 2),
                        "severity": "critical" if z_score > 3 else "warning"
                    })
            
            return anomalies
        
        except (ValueError, statistics.StatisticsError):
            return []
    
    @staticmethod
    def analyze_scaling_efficiency(
        service: Dict,
        metrics: Dict
    ) -> Dict:
        """
        Analiza eficiencia de escalado.
        
        Args:
            service: Datos del servicio
            metrics: Métricas calculadas
        
        Returns:
            Análisis de eficiencia de escalado
        """
        spec = service.get("spec", {}).get("template", {}).get("spec", {})
        template_annotations = service.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
        
        min_instances = int(template_annotations.get("autoscaling.knative.dev/minScale", "0"))
        max_instances = int(template_annotations.get("autoscaling.knative.dev/maxScale", "100"))
        
        current_instances = metrics.get("current_instances", 1)
        avg_instances = metrics.get("avg_instances", 1)
        peak_instances = metrics.get("peak_instances", 1)
        
        # Calcular eficiencia
        utilization = (avg_instances / max_instances * 100) if max_instances > 0 else 0
        scaling_range = max_instances - min_instances
        
        efficiency_score = 100
        if utilization < 20:
            efficiency_score -= 20
        elif utilization > 90:
            efficiency_score -= 10
        
        return {
            "min_instances": min_instances,
            "max_instances": max_instances,
            "current_instances": current_instances,
            "avg_instances": round(avg_instances, 2),
            "peak_instances": peak_instances,
            "utilization_percent": round(utilization, 2),
            "scaling_range": scaling_range,
            "efficiency_score": efficiency_score,
            "recommendation": CloudRunMetrics._get_scaling_recommendation(utilization, min_instances, max_instances)
        }
    
    @staticmethod
    def _get_scaling_recommendation(utilization: float, min_instances: int, max_instances: int) -> str:
        """Genera recomendación de escalado"""
        if utilization < 20:
            return "Considere reducir max_instances para ahorrar costos"
        elif utilization > 90:
            return "Considere aumentar max_instances para mejorar rendimiento"
        elif min_instances == 0:
            return "Cold starts detectados. Considere min_instances > 0 si es crítico"
        else:
            return "Configuración de escalado óptima"
    
    @staticmethod
    def calculate_cold_start_impact(
        service: Dict,
        metrics: Dict
    ) -> Dict:
        """
        Calcula impacto de cold starts.
        
        Args:
            service: Datos del servicio
            metrics: Métricas calculadas
        
        Returns:
            Análisis de impacto de cold starts
        """
        template_annotations = service.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
        min_instances = int(template_annotations.get("autoscaling.knative.dev/minScale", "0"))
        
        cold_starts = metrics.get("cold_starts", 0)
        total_invocations = metrics.get("total_invocations", 1)
        avg_cold_start_latency = metrics.get("avg_cold_start_latency", 0)
        avg_warm_latency = metrics.get("avg_warm_latency", 0)
        
        cold_start_rate = (cold_starts / total_invocations * 100) if total_invocations > 0 else 0
        latency_impact = avg_cold_start_latency - avg_warm_latency
        
        return {
            "cold_starts": cold_starts,
            "total_invocations": total_invocations,
            "cold_start_rate_percent": round(cold_start_rate, 2),
            "avg_cold_start_latency_ms": round(avg_cold_start_latency, 2),
            "avg_warm_latency_ms": round(avg_warm_latency, 2),
            "latency_impact_ms": round(latency_impact, 2),
            "min_instances_configured": min_instances,
            "recommendation": "Aumentar min_instances para reducir cold starts" if cold_start_rate > 10 else "Cold start rate aceptable"
        }
    
    @staticmethod
    def calculate_error_rate_severity(error_rate: float) -> str:
        """
        Determina severidad basada en error rate.
        
        Args:
            error_rate: Porcentaje de errores
        
        Returns:
            Nivel de severidad
        """
        if error_rate > 5:
            return "CRITICAL"
        elif error_rate > 1:
            return "WARNING"
        elif error_rate > 0.1:
            return "INFO"
        else:
            return "OK"
    
    @staticmethod
    def calculate_sla_compliance(
        availability: float,
        target_sla: float = 99.9
    ) -> Dict:
        """
        Calcula cumplimiento de SLA.
        
        Args:
            availability: Disponibilidad actual (%)
            target_sla: SLA objetivo (%)
        
        Returns:
            Análisis de cumplimiento de SLA
        """
        compliant = availability >= target_sla
        difference = availability - target_sla
        
        return {
            "current_availability": round(availability, 3),
            "target_sla": target_sla,
            "compliant": compliant,
            "difference": round(difference, 3),
            "status": "COMPLIANT" if compliant else "NON-COMPLIANT",
            "downtime_minutes_per_month": round((100 - availability) / 100 * 43200, 2)
        }
