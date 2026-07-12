"""
Tests unitarios para Health Probe Masivo Validator
"""
import unittest
from datetime import datetime

from .azdo_parser import parse_input
from .models import (
    DeploymentInput, DeploymentStatus, HealthCheckResult, ProbeStatus,
    StageInfo, TestResult
)


class TestModels(unittest.TestCase):
    """Tests para dataclasses"""
    
    def test_deployment_input_basic(self):
        """Test DeploymentInput básico"""
        dep = DeploymentInput(name="web-prod")
        self.assertEqual(dep.name, "web-prod")
        self.assertIsNone(dep.definition_id)
        self.assertEqual(dep.namespace, "default")
    
    def test_deployment_input_with_definition(self):
        """Test DeploymentInput con definition ID"""
        dep = DeploymentInput(name="release_3388", definition_id=3388)
        self.assertEqual(dep.definition_id, 3388)
    
    def test_deployment_status_ready(self):
        """Test DeploymentStatus en estado Ready"""
        status = DeploymentStatus(
            name="web",
            namespace="prod",
            replicas=3,
            ready_replicas=3,
            updated_replicas=3,
            available_replicas=3
        )
        self.assertEqual(status.status, "Ready")
    
    def test_deployment_status_partial(self):
        """Test DeploymentStatus en estado Partial"""
        status = DeploymentStatus(
            name="web",
            namespace="prod",
            replicas=3,
            ready_replicas=2,
            updated_replicas=3,
            available_replicas=2
        )
        self.assertEqual(status.status, "Partial")
    
    def test_deployment_status_not_ready(self):
        """Test DeploymentStatus en estado NotReady"""
        status = DeploymentStatus(
            name="web",
            namespace="prod",
            replicas=3,
            ready_replicas=0,
            updated_replicas=0,
            available_replicas=0
        )
        self.assertEqual(status.status, "NotReady")
    
    def test_probe_status_healthy(self):
        """Test ProbeStatus saludable"""
        probes = ProbeStatus(
            liveness_configured=True,
            liveness_timeout=10,
            readiness_configured=True,
            readiness_timeout=5
        )
        self.assertTrue(probes.is_healthy)
        self.assertEqual(probes.status_emoji, "✅")
    
    def test_probe_status_warning(self):
        """Test ProbeStatus con advertencia"""
        probes = ProbeStatus(
            liveness_configured=True,
            liveness_timeout=10,
            readiness_configured=False
        )
        self.assertFalse(probes.is_healthy)
        self.assertEqual(probes.status_emoji, "⚠️")
    
    def test_probe_status_error(self):
        """Test ProbeStatus con error"""
        probes = ProbeStatus(
            liveness_configured=False,
            readiness_configured=False
        )
        self.assertFalse(probes.is_healthy)
        self.assertEqual(probes.status_emoji, "❌")
    
    def test_test_result_success(self):
        """Test TestResult exitoso"""
        result = TestResult(
            host="google.com",
            port=443,
            protocol="https",
            success=True,
            latency_ms=45.5,
            timeout=False
        )
        self.assertEqual(result.status, "OK")
    
    def test_test_result_timeout(self):
        """Test TestResult con timeout"""
        result = TestResult(
            host="10.255.255.1",
            port=80,
            protocol="tcp",
            success=False,
            latency_ms=30000,
            timeout=True
        )
        self.assertEqual(result.status, "TIMEOUT")
    
    def test_test_result_failed(self):
        """Test TestResult fallido"""
        result = TestResult(
            host="invalid.host",
            port=80,
            protocol="tcp",
            success=False,
            latency_ms=100,
            timeout=False
        )
        self.assertEqual(result.status, "FAILED")
    
    def test_health_check_result_healthy(self):
        """Test HealthCheckResult saludable"""
        result = HealthCheckResult(
            deployment="web-prod",
            stage="Prod",
            pod_status="Ready",
            pod_count=3,
            ready_count=3,
            liveness_probe=True,
            readiness_probe=True,
            connectivity="OK",
            latency_ms=45.5
        )
        self.assertEqual(result.overall_status, "✅ HEALTHY")
        self.assertEqual(result.pod_status_emoji, "✅")
        self.assertEqual(result.connectivity_emoji, "✅")
    
    def test_health_check_result_warning(self):
        """Test HealthCheckResult con advertencia"""
        result = HealthCheckResult(
            deployment="api-prod",
            stage="Prod",
            pod_status="Partial",
            pod_count=3,
            ready_count=2,
            liveness_probe=True,
            readiness_probe=True,
            connectivity="OK",
            latency_ms=100
        )
        self.assertEqual(result.overall_status, "⚠️ WARNING")
    
    def test_health_check_result_critical(self):
        """Test HealthCheckResult crítico"""
        result = HealthCheckResult(
            deployment="db-prod",
            stage="Prod",
            pod_status="NotReady",
            pod_count=1,
            ready_count=0,
            liveness_probe=False,
            readiness_probe=False,
            connectivity="FAILED",
            latency_ms=0
        )
        self.assertEqual(result.overall_status, "❌ CRITICAL")


class TestAzDOParser(unittest.TestCase):
    """Tests para AZDO Parser"""
    
    def test_parse_input_deployment_names(self):
        """Test parsing de nombres de deployments"""
        input_str = "deployment-web-prod,deployment-api-prod"
        result = parse_input(input_str)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "deployment-web-prod")
        self.assertEqual(result[1].name, "deployment-api-prod")
    
    def test_parse_input_definition_ids_with_prefix(self):
        """Test parsing de definition IDs con prefijo"""
        input_str = "definitionId=3388,definitionId=3389"
        result = parse_input(input_str)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].definition_id, 3388)
        self.assertEqual(result[1].definition_id, 3389)
    
    def test_parse_input_definition_ids_numeric(self):
        """Test parsing de definition IDs numéricos"""
        input_str = "3388,3389,3390"
        result = parse_input(input_str)
        
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].definition_id, 3388)
        self.assertEqual(result[2].definition_id, 3390)
    
    def test_parse_input_mixed(self):
        """Test parsing mixto"""
        input_str = "deployment-web-prod,definitionId=3388"
        result = parse_input(input_str)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "deployment-web-prod")
        self.assertEqual(result[1].definition_id, 3388)
    
    def test_parse_input_with_spaces(self):
        """Test parsing con espacios"""
        input_str = "deployment-web-prod , deployment-api-prod"
        result = parse_input(input_str)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "deployment-web-prod")
        self.assertEqual(result[1].name, "deployment-api-prod")


class TestStageInfo(unittest.TestCase):
    """Tests para StageInfo"""
    
    def test_stage_info_creation(self):
        """Test creación de StageInfo"""
        stage = StageInfo(
            name="Prod",
            definition_id=3388,
            target_deployment="deployment-web",
            target_namespace="production",
            endpoints=["api.prod.internal"],
            ports=[8080, 443],
            environment="Prod"
        )
        
        self.assertEqual(stage.name, "Prod")
        self.assertEqual(stage.definition_id, 3388)
        self.assertEqual(len(stage.endpoints), 1)
        self.assertEqual(len(stage.ports), 2)


if __name__ == "__main__":
    unittest.main()
