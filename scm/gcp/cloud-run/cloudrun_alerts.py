#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloud Run Alerts Module

Sistema de alertas para Cloud Run.
Gestiona creación, evaluación y formato de alertas.

Autor: Harold Adrian
"""

from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime


class AlertSeverity(Enum):
    """Niveles de severidad de alertas"""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    OK = "OK"


class AlertType(Enum):
    """Tipos de alertas"""
    PERFORMANCE = "PERFORMANCE"
    SECURITY = "SECURITY"
    COST = "COST"
    CONFIGURATION = "CONFIGURATION"
    AVAILABILITY = "AVAILABILITY"
    SCALING = "SCALING"


class AlertManager:
    """Gestor de alertas"""
    
    def __init__(self):
        self.alerts: List[Dict] = []
        self.thresholds: Dict = {}
    
    def set_thresholds(self, thresholds: Dict):
        """
        Establece umbrales para alertas.
        
        Args:
            thresholds: Diccionario con umbrales
        """
        self.thresholds = thresholds
    
    def create_alert(
        self,
        service: str,
        severity: AlertSeverity,
        alert_type: AlertType,
        message: str,
        metric: str,
        threshold: float,
        current_value: float,
        recommendation: str = ""
    ) -> Dict:
        """
        Crea una alerta.
        
        Args:
            service: Nombre del servicio
            severity: Nivel de severidad
            alert_type: Tipo de alerta
            message: Mensaje de alerta
            metric: Métrica que disparó la alerta
            threshold: Umbral configurado
            current_value: Valor actual
            recommendation: Recomendación de solución
        
        Returns:
            Diccionario con detalles de la alerta
        """
        alert = {
            "service": service,
            "severity": severity.value,
            "type": alert_type.value,
            "message": message,
            "metric": metric,
            "threshold": threshold,
            "current_value": current_value,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        }
        
        self.alerts.append(alert)
        return alert
    
    def evaluate_thresholds(
        self,
        service: Dict,
        metrics: Dict,
        thresholds: Dict
    ) -> List[Dict]:
        """
        Evalúa métricas contra umbrales.
        
        Args:
            service: Datos del servicio
            metrics: Métricas calculadas
            thresholds: Umbrales configurados
        
        Returns:
            Lista de alertas generadas
        """
        alerts = []
        service_name = service.get("metadata", {}).get("name", "unknown")
        
        # Evaluar error rate
        if "error_rate" in thresholds:
            error_rate = metrics.get("error_rate", 0)
            threshold = thresholds["error_rate"]
            
            if error_rate > threshold:
                severity = AlertSeverity.CRITICAL if error_rate > threshold * 2 else AlertSeverity.WARNING
                alert = self.create_alert(
                    service=service_name,
                    severity=severity,
                    alert_type=AlertType.PERFORMANCE,
                    message=f"Error rate alto detectado",
                    metric="error_rate",
                    threshold=threshold,
                    current_value=error_rate,
                    recommendation="Revisar logs de error y configuración del servicio"
                )
                alerts.append(alert)
        
        # Evaluar latencia
        if "latency_p99" in thresholds:
            latency = metrics.get("latency_p99", 0)
            threshold = thresholds["latency_p99"]
            
            if latency > threshold:
                severity = AlertSeverity.CRITICAL if latency > threshold * 1.5 else AlertSeverity.WARNING
                alert = self.create_alert(
                    service=service_name,
                    severity=severity,
                    alert_type=AlertType.PERFORMANCE,
                    message=f"Latencia P99 alta detectada",
                    metric="latency_p99",
                    threshold=threshold,
                    current_value=latency,
                    recommendation="Optimizar código o aumentar recursos (CPU/memoria)"
                )
                alerts.append(alert)
        
        # Evaluar disponibilidad
        if "availability" in thresholds:
            availability = metrics.get("availability", 100)
            threshold = thresholds["availability"]
            
            if availability < threshold:
                severity = AlertSeverity.CRITICAL if availability < threshold - 5 else AlertSeverity.WARNING
                alert = self.create_alert(
                    service=service_name,
                    severity=severity,
                    alert_type=AlertType.AVAILABILITY,
                    message=f"Disponibilidad por debajo de SLA",
                    metric="availability",
                    threshold=threshold,
                    current_value=availability,
                    recommendation="Investigar causas de indisponibilidad y aplicar mitigaciones"
                )
                alerts.append(alert)
        
        # Evaluar uso de recursos
        if "cpu_usage" in thresholds:
            cpu_usage = metrics.get("cpu_usage", 0)
            threshold = thresholds["cpu_usage"]
            
            if cpu_usage > threshold:
                severity = AlertSeverity.WARNING if cpu_usage > threshold else AlertSeverity.INFO
                alert = self.create_alert(
                    service=service_name,
                    severity=severity,
                    alert_type=AlertType.SCALING,
                    message=f"Uso de CPU alto",
                    metric="cpu_usage",
                    threshold=threshold,
                    current_value=cpu_usage,
                    recommendation="Considere aumentar CPU allocation o optimizar código"
                )
                alerts.append(alert)
        
        # Evaluar memoria
        if "memory_usage" in thresholds:
            memory_usage = metrics.get("memory_usage", 0)
            threshold = thresholds["memory_usage"]
            
            if memory_usage > threshold:
                severity = AlertSeverity.WARNING if memory_usage > threshold else AlertSeverity.INFO
                alert = self.create_alert(
                    service=service_name,
                    severity=severity,
                    alert_type=AlertType.SCALING,
                    message=f"Uso de memoria alto",
                    metric="memory_usage",
                    threshold=threshold,
                    current_value=memory_usage,
                    recommendation="Considere aumentar memory allocation o optimizar código"
                )
                alerts.append(alert)
        
        return alerts
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Dict]:
        """
        Obtiene alertas por nivel de severidad.
        
        Args:
            severity: Nivel de severidad
        
        Returns:
            Lista de alertas del nivel especificado
        """
        return [a for a in self.alerts if a["severity"] == severity.value]
    
    def get_alerts_by_type(self, alert_type: AlertType) -> List[Dict]:
        """
        Obtiene alertas por tipo.
        
        Args:
            alert_type: Tipo de alerta
        
        Returns:
            Lista de alertas del tipo especificado
        """
        return [a for a in self.alerts if a["type"] == alert_type.value]
    
    def get_alerts_by_service(self, service: str) -> List[Dict]:
        """
        Obtiene alertas de un servicio específico.
        
        Args:
            service: Nombre del servicio
        
        Returns:
            Lista de alertas del servicio
        """
        return [a for a in self.alerts if a["service"] == service]
    
    def get_critical_alerts(self) -> List[Dict]:
        """Obtiene todas las alertas críticas"""
        return self.get_alerts_by_severity(AlertSeverity.CRITICAL)
    
    def get_warning_alerts(self) -> List[Dict]:
        """Obtiene todas las alertas de advertencia"""
        return self.get_alerts_by_severity(AlertSeverity.WARNING)
    
    def clear_alerts(self):
        """Limpia todas las alertas"""
        self.alerts = []
    
    def clear_service_alerts(self, service: str):
        """Limpia alertas de un servicio específico"""
        self.alerts = [a for a in self.alerts if a["service"] != service]
    
    def get_summary(self) -> Dict:
        """
        Obtiene resumen de alertas.
        
        Returns:
            Diccionario con resumen
        """
        critical = len(self.get_critical_alerts())
        warning = len(self.get_warning_alerts())
        info = len(self.get_alerts_by_severity(AlertSeverity.INFO))
        
        return {
            "total_alerts": len(self.alerts),
            "critical": critical,
            "warning": warning,
            "info": info,
            "services_affected": len(set(a["service"] for a in self.alerts)),
            "alert_types": list(set(a["type"] for a in self.alerts))
        }


class SecurityAlertManager(AlertManager):
    """Gestor de alertas de seguridad"""
    
    def check_iam_policy(
        self,
        service: str,
        iam_policy: Dict,
        is_public: bool
    ) -> Optional[Dict]:
        """
        Verifica política IAM y crea alerta si es pública.
        
        Args:
            service: Nombre del servicio
            iam_policy: Política IAM
            is_public: Si el servicio es público
        
        Returns:
            Alerta si se detecta problema, None si todo está bien
        """
        if is_public:
            return self.create_alert(
                service=service,
                severity=AlertSeverity.WARNING,
                alert_type=AlertType.SECURITY,
                message="Servicio es públicamente accesible",
                metric="iam_policy",
                threshold=0,
                current_value=1,
                recommendation="Considere restringir acceso a usuarios autenticados"
            )
        return None
    
    def check_vpc_connector(
        self,
        service: str,
        vpc_connector: str
    ) -> Optional[Dict]:
        """
        Verifica si el servicio usa VPC connector.
        
        Args:
            service: Nombre del servicio
            vpc_connector: Nombre del VPC connector
        
        Returns:
            Alerta si no hay VPC connector, None si está configurado
        """
        if not vpc_connector:
            return self.create_alert(
                service=service,
                severity=AlertSeverity.INFO,
                alert_type=AlertType.SECURITY,
                message="Servicio no usa VPC connector",
                metric="vpc_connector",
                threshold=1,
                current_value=0,
                recommendation="Considere usar VPC connector para conectar a recursos privados"
            )
        return None
    
    def check_binary_authorization(
        self,
        service: str,
        binary_auth: str
    ) -> Optional[Dict]:
        """
        Verifica si binary authorization está habilitado.
        
        Args:
            service: Nombre del servicio
            binary_auth: Configuración de binary authorization
        
        Returns:
            Alerta si no está habilitado, None si está configurado
        """
        if not binary_auth or binary_auth.lower() == "disabled":
            return self.create_alert(
                service=service,
                severity=AlertSeverity.INFO,
                alert_type=AlertType.SECURITY,
                message="Binary authorization no está habilitado",
                metric="binary_authorization",
                threshold=1,
                current_value=0,
                recommendation="Considere habilitar binary authorization para mayor seguridad"
            )
        return None


class CostAlertManager(AlertManager):
    """Gestor de alertas de costos"""
    
    def check_cost_threshold(
        self,
        service: str,
        monthly_cost: float,
        cost_threshold: float
    ) -> Optional[Dict]:
        """
        Verifica si el costo mensual excede el umbral.
        
        Args:
            service: Nombre del servicio
            monthly_cost: Costo mensual proyectado
            cost_threshold: Umbral de costo
        
        Returns:
            Alerta si excede umbral, None si está dentro del límite
        """
        if monthly_cost > cost_threshold:
            severity = AlertSeverity.CRITICAL if monthly_cost > cost_threshold * 1.5 else AlertSeverity.WARNING
            return self.create_alert(
                service=service,
                severity=severity,
                alert_type=AlertType.COST,
                message=f"Costo mensual proyectado excede umbral",
                metric="monthly_cost",
                threshold=cost_threshold,
                current_value=monthly_cost,
                recommendation="Revisar configuración de recursos y considerar optimizaciones"
            )
        return None
    
    def check_cost_increase(
        self,
        service: str,
        current_cost: float,
        previous_cost: float,
        increase_threshold: float = 10.0
    ) -> Optional[Dict]:
        """
        Verifica si hay un aumento significativo de costos.
        
        Args:
            service: Nombre del servicio
            current_cost: Costo actual
            previous_cost: Costo anterior
            increase_threshold: Umbral de aumento (%)
        
        Returns:
            Alerta si hay aumento significativo, None si está dentro de lo normal
        """
        if previous_cost > 0:
            increase_percent = ((current_cost - previous_cost) / previous_cost) * 100
            
            if increase_percent > increase_threshold:
                severity = AlertSeverity.WARNING if increase_percent > increase_threshold else AlertSeverity.INFO
                return self.create_alert(
                    service=service,
                    severity=severity,
                    alert_type=AlertType.COST,
                    message=f"Aumento significativo de costos detectado",
                    metric="cost_increase_percent",
                    threshold=increase_threshold,
                    current_value=increase_percent,
                    recommendation="Investigar causa del aumento y aplicar optimizaciones"
                )
        return None
