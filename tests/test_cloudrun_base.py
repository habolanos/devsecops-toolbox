#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para módulos base de Cloud Run

Autor: Harold Adrian
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open

# Agregar ruta del módulo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scm', 'gcp', 'cloud-run'))

from cloudrun_base import CloudRunBase
from cloudrun_metrics import CloudRunMetrics
from cloudrun_alerts import AlertManager, AlertSeverity, AlertType, SecurityAlertManager, CostAlertManager


class TestCloudRunBase(unittest.TestCase):
    """Tests para CloudRunBase"""
    
    def setUp(self):
        """Configuración inicial"""
        self.base = CloudRunBase(project="test-project", region="us-central1", debug=False)
    
    def test_init(self):
        """Test inicialización"""
        self.assertEqual(self.base.project, "test-project")
        self.assertEqual(self.base.region, "us-central1")
        self.assertFalse(self.base.debug)
    
    @patch('cloudrun_base.subprocess.run')
    def test_run_gcloud_command_success(self, mock_run):
        """Test ejecución exitosa de comando gcloud"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name": "service-1"}]',
            stderr=''
        )
        
        result = self.base.run_gcloud_command("gcloud run services list")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "service-1")
    
    @patch('cloudrun_base.subprocess.run')
    def test_run_gcloud_command_failure(self, mock_run):
        """Test fallo de comando gcloud"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='Error: Permission denied'
        )
        
        result = self.base.run_gcloud_command("gcloud run services list")
        
        self.assertEqual(result, [])
    
    @patch('cloudrun_base.subprocess.run')
    def test_validate_connection_success(self, mock_run):
        """Test validación de conexión exitosa"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[]',
            stderr=''
        )
        
        result = self.base.validate_connection()
        
        self.assertTrue(result)
    
    @patch('cloudrun_base.subprocess.run')
    def test_validate_connection_failure(self, mock_run):
        """Test fallo de validación de conexión"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='Error'
        )
        
        result = self.base.validate_connection()
        
        self.assertFalse(result)
    
    def test_export_results_json(self):
        """Test exportación a JSON"""
        data = {"test": "data"}
        
        with patch('cloudrun_base.Path') as mock_path:
            mock_path.return_value.mkdir = MagicMock()
            with patch('builtins.open', mock_open()):
                result = self.base.export_results(data, format="json")
                self.assertIsNotNone(result)
    
    def test_print_success(self):
        """Test impresión de éxito"""
        with patch('cloudrun_base.Console') as mock_console:
            self.base.print_success("Test message")
    
    def test_print_error(self):
        """Test impresión de error"""
        with patch('cloudrun_base.Console') as mock_console:
            self.base.print_error("Test error")
    
    def test_print_warning(self):
        """Test impresión de advertencia"""
        with patch('cloudrun_base.Console') as mock_console:
            self.base.print_warning("Test warning")


class TestCloudRunMetrics(unittest.TestCase):
    """Tests para CloudRunMetrics"""
    
    def test_calculate_health_score(self):
        """Test cálculo de health score"""
        service = {}
        metrics = {
            "availability": 99.5,
            "performance": 95.0,
            "error_rate": 0.5,
            "resource_usage": 45.0
        }
        
        score = CloudRunMetrics.calculate_health_score(service, metrics)
        
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        self.assertGreater(score, 80)
    
    def test_calculate_health_score_low(self):
        """Test cálculo de health score bajo"""
        service = {}
        metrics = {
            "availability": 50.0,
            "performance": 30.0,
            "error_rate": 20.0,
            "resource_usage": 90.0
        }
        
        score = CloudRunMetrics.calculate_health_score(service, metrics)
        
        self.assertLess(score, 50)
    
    def test_calculate_costs(self):
        """Test cálculo de costos"""
        service = {}
        costs = CloudRunMetrics.calculate_costs(
            service,
            "us-central1",
            invocations=1000000,
            cpu_seconds=1000,
            memory_gb_seconds=500
        )
        
        self.assertIn("invocation_cost", costs)
        self.assertIn("cpu_cost", costs)
        self.assertIn("memory_cost", costs)
        self.assertIn("total_cost", costs)
        self.assertGreater(costs["total_cost"], 0)
    
    def test_calculate_monthly_projection(self):
        """Test proyección mensual"""
        projection = CloudRunMetrics.calculate_monthly_projection(
            daily_cost=10.0,
            days_of_data=7
        )
        
        self.assertEqual(projection["daily_average"], 10.0)
        self.assertEqual(projection["monthly_projection"], 300.0)
        self.assertEqual(projection["yearly_projection"], 3650.0)
    
    def test_detect_anomalies(self):
        """Test detección de anomalías"""
        metrics_history = [
            {"latency": 100, "timestamp": "2026-01-01"},
            {"latency": 105, "timestamp": "2026-01-02"},
            {"latency": 102, "timestamp": "2026-01-03"},
            {"latency": 500, "timestamp": "2026-01-04"},  # Anomalía
        ]
        
        anomalies = CloudRunMetrics.detect_anomalies(metrics_history, "latency", threshold_std_dev=2.0)
        
        self.assertGreater(len(anomalies), 0)
    
    def test_analyze_scaling_efficiency(self):
        """Test análisis de eficiencia de escalado"""
        service = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "autoscaling.knative.dev/minScale": "0",
                            "autoscaling.knative.dev/maxScale": "100"
                        }
                    },
                    "spec": {}
                }
            }
        }
        metrics = {
            "current_instances": 5,
            "avg_instances": 10,
            "peak_instances": 50
        }
        
        efficiency = CloudRunMetrics.analyze_scaling_efficiency(service, metrics)
        
        self.assertIn("min_instances", efficiency)
        self.assertIn("max_instances", efficiency)
        self.assertIn("efficiency_score", efficiency)
    
    def test_calculate_sla_compliance_compliant(self):
        """Test cumplimiento de SLA (compliant)"""
        sla = CloudRunMetrics.calculate_sla_compliance(99.95, target_sla=99.9)
        
        self.assertTrue(sla["compliant"])
        self.assertEqual(sla["status"], "COMPLIANT")
    
    def test_calculate_sla_compliance_non_compliant(self):
        """Test cumplimiento de SLA (no compliant)"""
        sla = CloudRunMetrics.calculate_sla_compliance(99.5, target_sla=99.9)
        
        self.assertFalse(sla["compliant"])
        self.assertEqual(sla["status"], "NON-COMPLIANT")


class TestAlertManager(unittest.TestCase):
    """Tests para AlertManager"""
    
    def setUp(self):
        """Configuración inicial"""
        self.manager = AlertManager()
    
    def test_create_alert(self):
        """Test creación de alerta"""
        alert = self.manager.create_alert(
            service="test-service",
            severity=AlertSeverity.WARNING,
            alert_type=AlertType.PERFORMANCE,
            message="Test alert",
            metric="latency",
            threshold=100,
            current_value=150,
            recommendation="Optimize code"
        )
        
        self.assertEqual(alert["service"], "test-service")
        self.assertEqual(alert["severity"], "WARNING")
        self.assertEqual(alert["type"], "PERFORMANCE")
        self.assertEqual(len(self.manager.alerts), 1)
    
    def test_evaluate_thresholds(self):
        """Test evaluación de umbrales"""
        service = {"metadata": {"name": "test-service"}}
        metrics = {
            "error_rate": 10.0,
            "latency_p99": 500,
            "availability": 95.0
        }
        thresholds = {
            "error_rate": 5.0,
            "latency_p99": 300,
            "availability": 99.0
        }
        
        alerts = self.manager.evaluate_thresholds(service, metrics, thresholds)
        
        self.assertGreater(len(alerts), 0)
    
    def test_get_alerts_by_severity(self):
        """Test obtener alertas por severidad"""
        self.manager.create_alert(
            "service1", AlertSeverity.CRITICAL, AlertType.PERFORMANCE,
            "msg", "metric", 0, 0
        )
        self.manager.create_alert(
            "service2", AlertSeverity.WARNING, AlertType.PERFORMANCE,
            "msg", "metric", 0, 0
        )
        
        critical = self.manager.get_alerts_by_severity(AlertSeverity.CRITICAL)
        
        self.assertEqual(len(critical), 1)
    
    def test_get_critical_alerts(self):
        """Test obtener alertas críticas"""
        self.manager.create_alert(
            "service1", AlertSeverity.CRITICAL, AlertType.PERFORMANCE,
            "msg", "metric", 0, 0
        )
        
        critical = self.manager.get_critical_alerts()
        
        self.assertEqual(len(critical), 1)
    
    def test_clear_alerts(self):
        """Test limpiar alertas"""
        self.manager.create_alert(
            "service1", AlertSeverity.WARNING, AlertType.PERFORMANCE,
            "msg", "metric", 0, 0
        )
        
        self.manager.clear_alerts()
        
        self.assertEqual(len(self.manager.alerts), 0)
    
    def test_get_summary(self):
        """Test obtener resumen"""
        self.manager.create_alert(
            "service1", AlertSeverity.CRITICAL, AlertType.PERFORMANCE,
            "msg", "metric", 0, 0
        )
        self.manager.create_alert(
            "service2", AlertSeverity.WARNING, AlertType.SECURITY,
            "msg", "metric", 0, 0
        )
        
        summary = self.manager.get_summary()
        
        self.assertEqual(summary["total_alerts"], 2)
        self.assertEqual(summary["critical"], 1)
        self.assertEqual(summary["warning"], 1)


class TestSecurityAlertManager(unittest.TestCase):
    """Tests para SecurityAlertManager"""
    
    def setUp(self):
        """Configuración inicial"""
        self.manager = SecurityAlertManager()
    
    def test_check_iam_policy_public(self):
        """Test verificación de política IAM pública"""
        alert = self.manager.check_iam_policy("service", {}, is_public=True)
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "WARNING")
    
    def test_check_iam_policy_private(self):
        """Test verificación de política IAM privada"""
        alert = self.manager.check_iam_policy("service", {}, is_public=False)
        
        self.assertIsNone(alert)
    
    def test_check_vpc_connector_missing(self):
        """Test verificación de VPC connector faltante"""
        alert = self.manager.check_vpc_connector("service", "")
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "INFO")
    
    def test_check_vpc_connector_present(self):
        """Test verificación de VPC connector presente"""
        alert = self.manager.check_vpc_connector("service", "my-vpc-connector")
        
        self.assertIsNone(alert)


class TestCostAlertManager(unittest.TestCase):
    """Tests para CostAlertManager"""
    
    def setUp(self):
        """Configuración inicial"""
        self.manager = CostAlertManager()
    
    def test_check_cost_threshold_exceeded(self):
        """Test verificación de umbral de costo excedido"""
        alert = self.manager.check_cost_threshold("service", 150.0, 100.0)
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "WARNING")
    
    def test_check_cost_threshold_ok(self):
        """Test verificación de umbral de costo OK"""
        alert = self.manager.check_cost_threshold("service", 50.0, 100.0)
        
        self.assertIsNone(alert)
    
    def test_check_cost_increase(self):
        """Test verificación de aumento de costo"""
        alert = self.manager.check_cost_increase("service", 150.0, 100.0, increase_threshold=10.0)
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert["severity"], "WARNING")


if __name__ == "__main__":
    unittest.main()
