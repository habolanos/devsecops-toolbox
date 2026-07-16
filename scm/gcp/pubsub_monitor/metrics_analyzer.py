"""
MetricsAnalyzer - Análisis de métricas de Pub/Sub

Módulo responsable de analizar métricas y calcular KPIs,
incluyendo health scores, detección de anomalías e identificación de problemas.

Características:
- Cálculo de health scores (0-100)
- Detección de anomalías con Z-score
- Identificación automática de problemas
- Análisis de tendencias
"""

import logging
import statistics
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
logger = logging.getLogger(__name__)


class MetricsAnalyzer:
    """Analiza métricas de Pub/Sub y calcula KPIs."""

    def __init__(self, thresholds: Optional[Dict] = None):
        """
        Inicializa el analizador.

        Args:
            thresholds: Diccionario de umbrales personalizados
        """
        self.thresholds = thresholds or self._get_default_thresholds()
        self.kpis = {}

    def _get_default_thresholds(self) -> Dict:
        """Obtiene umbrales por defecto."""
        return {
            "capacity": {
                "backlog_messages_critical": 100000,
                "backlog_messages_warning": 50000,
                "oldest_message_age_critical": 60,
                "oldest_message_age_warning": 30,
                "error_rate_critical": 5,
                "error_rate_warning": 2
            },
            "performance": {
                "latency_p95_critical_ms": 5000,
                "latency_p95_warning_ms": 2000,
                "throughput_warning_percent": 70,
                "discard_rate_critical": 1,
                "discard_rate_warning": 0.5
            },
            "configuration": {
                "min_ttl_hours": 1,
                "require_dead_letter": True,
                "require_retry_policy": True
            }
        }

    def calculate_topic_health(self, topic_data: Dict) -> Dict:
        """
        Calcula salud de un topic.

        Args:
            topic_data: Datos del topic

        Returns:
            Diccionario con health score y detalles
        """
        health_score = 100
        issues = []

        # Verificar TTL
        ttl_seconds = topic_data.get("message_retention_duration")
        if ttl_seconds and ttl_seconds < 3600:
            health_score -= 10
            issues.append({
                "severity": "warning",
                "message": f"TTL bajo: {ttl_seconds}s (mínimo: 3600s)"
            })

        # Verificar encriptación
        if not topic_data.get("kms_key_name"):
            health_score -= 5
            issues.append({
                "severity": "info",
                "message": "Encriptación CMEK no habilitada"
            })

        return {
            "topic_id": topic_data.get("display_name"),
            "health_score": max(0, health_score),
            "status": self._get_status(health_score),
            "issues": issues
        }

    def calculate_subscription_health(self, sub_data: Dict) -> Dict:
        """
        Calcula salud de una subscription.

        Args:
            sub_data: Datos de la subscription

        Returns:
            Diccionario con health score y detalles
        """
        health_score = 100
        issues = []

        # Verificar dead-letter policy
        if not sub_data.get("dead_letter_policy"):
            health_score -= 15
            issues.append({
                "severity": "warning",
                "message": "Dead-letter policy no configurada"
            })

        # Verificar retry policy
        if not sub_data.get("retry_policy"):
            health_score -= 10
            issues.append({
                "severity": "warning",
                "message": "Retry policy no configurada"
            })

        # Verificar TTL
        ttl_seconds = sub_data.get("message_retention_duration")
        if ttl_seconds and ttl_seconds < 3600:
            health_score -= 10
            issues.append({
                "severity": "warning",
                "message": f"TTL bajo: {ttl_seconds}s"
            })

        # Verificar ack deadline
        ack_deadline = sub_data.get("ack_deadline_seconds", 10)
        if ack_deadline < 10:
            health_score -= 5
            issues.append({
                "severity": "info",
                "message": f"Ack deadline bajo: {ack_deadline}s"
            })

        return {
            "subscription_id": sub_data.get("display_name"),
            "health_score": max(0, health_score),
            "status": self._get_status(health_score),
            "issues": issues
        }

    def detect_anomalies(self, metrics_data: Dict, 
                        historical_data: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Detecta anomalías usando Z-score.

        Args:
            metrics_data: Datos de métricas actuales
            historical_data: Datos históricos para comparación

        Returns:
            Lista de anomalías detectadas
        """
        anomalies = []

        if not historical_data or len(historical_data) < 2:
            return anomalies

        for metric_name, current_value in metrics_data.items():
            try:
                historical_values = [d.get(metric_name, 0) for d in historical_data]
                
                if not historical_values or len(historical_values) < 2:
                    continue

                mean = statistics.mean(historical_values)
                stdev = statistics.stdev(historical_values)

                if stdev == 0:
                    continue

                z_score = (current_value - mean) / stdev

                if abs(z_score) > 2.5:
                    anomalies.append({
                        "metric": metric_name,
                        "current_value": current_value,
                        "expected_value": mean,
                        "z_score": z_score,
                        "severity": "critical" if abs(z_score) > 3 else "warning"
                    })

            except Exception as e:
                logger.debug(f"Error detectando anomalía en {metric_name}: {str(e)}")

        return anomalies

    def calculate_project_summary(self, project_data: Dict) -> Dict:
        """
        Calcula resumen del proyecto.

        Args:
            project_data: Datos del proyecto

        Returns:
            Diccionario con resumen
        """
        topics = project_data.get("topics", [])
        subscriptions = project_data.get("subscriptions", [])

        # Calcular health scores
        topic_health_scores = [
            self.calculate_topic_health(t)["health_score"] 
            for t in topics
        ]
        sub_health_scores = [
            self.calculate_subscription_health(s)["health_score"] 
            for s in subscriptions
        ]

        avg_topic_health = statistics.mean(topic_health_scores) if topic_health_scores else 100
        avg_sub_health = statistics.mean(sub_health_scores) if sub_health_scores else 100

        return {
            "total_topics": len(topics),
            "total_subscriptions": len(subscriptions),
            "avg_topic_health": round(avg_topic_health, 2),
            "avg_subscription_health": round(avg_sub_health, 2),
            "overall_health": round((avg_topic_health + avg_sub_health) / 2, 2),
            "healthy_topics": sum(1 for s in topic_health_scores if s >= 80),
            "healthy_subscriptions": sum(1 for s in sub_health_scores if s >= 80),
            "topics_with_issues": sum(1 for s in topic_health_scores if s < 80),
            "subscriptions_with_issues": sum(1 for s in sub_health_scores if s < 80)
        }

    def _get_status(self, score: int) -> str:
        """Obtiene estado basado en score."""
        if score >= 80:
            return "healthy"
        elif score >= 60:
            return "warning"
        else:
            return "critical"

    def display_analysis_summary(self, analysis_results: Dict) -> None:
        """
        Muestra resumen del análisis.

        Args:
            analysis_results: Resultados del análisis
        """
        table = Table(title="📊 Resumen de Análisis de Salud")
        table.add_column("Proyecto", style="cyan")
        table.add_column("Health Score", justify="right", style="green")
        table.add_column("Topics", justify="right")
        table.add_column("Subscriptions", justify="right")
        table.add_column("Estado", style="yellow")

        for project, summary in analysis_results.items():
            status = "✅" if summary["overall_health"] >= 80 else "⚠️"
            table.add_row(
                project,
                f"{summary['overall_health']:.1f}/100",
                str(summary["total_topics"]),
                str(summary["total_subscriptions"]),
                status
            )

        console.print(table)
