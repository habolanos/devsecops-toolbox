#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para Cloud Functions Analyzer (Tool 35)

Suite de tests unitarios para validar funcionalidad de análisis de Cloud Functions.

Autor: Harold Adrian
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Agregar ruta de scm/gcp/cloud-functions
sys.path.insert(0, str(Path(__file__).parent.parent / "scm" / "gcp" / "cloud-functions"))

from cf_base import CloudFunctionsBase
from cf_metrics import CloudFunctionsMetrics


class TestCloudFunctionsBase(unittest.TestCase):
    """Tests para CloudFunctionsBase."""
    
    def setUp(self):
        """Configuración inicial para cada test."""
        self.base = CloudFunctionsBase("test-project", debug=False)
    
    def test_init(self):
        """Test inicialización de CloudFunctionsBase."""
        self.assertEqual(self.base.project_id, "test-project")
        self.assertFalse(self.base.debug)
    
    def test_analyze_function_security_public(self):
        """Test análisis de seguridad - función pública."""
        function = {
            'serviceConfig': {
                'ingressSettings': 'ALLOW_ALL',
                'securityLevel': 'SECURE_ALWAYS',
                'serviceAccountEmail': 'default@project.iam.gserviceaccount.com',
                'environmentVariables': {}
            }
        }
        
        security = self.base.analyze_function_security(function)
        
        self.assertTrue(security['is_public'])
        self.assertTrue(security['requires_authentication'])
        self.assertEqual(security['ingress_settings'], 'ALLOW_ALL')
    
    def test_analyze_function_security_private(self):
        """Test análisis de seguridad - función privada."""
        function = {
            'serviceConfig': {
                'ingressSettings': 'INTERNAL_ONLY',
                'securityLevel': 'SECURE_ALWAYS',
                'serviceAccountEmail': 'custom@project.iam.gserviceaccount.com',
                'environmentVariables': {}
            }
        }
        
        security = self.base.analyze_function_security(function)
        
        self.assertFalse(security['is_public'])
    
    def test_analyze_function_performance(self):
        """Test análisis de performance."""
        function = {
            'serviceConfig': {
                'availableMemoryMb': 512,
                'timeoutSeconds': 120,
                'maxInstanceCount': 100,
                'minInstanceCount': 0,
                'cpu': '0.333'
            },
            'runtime': 'python39'
        }
        
        performance = self.base.analyze_function_performance(function)
        
        self.assertEqual(performance['memory_mb'], 512)
        self.assertEqual(performance['timeout_seconds'], 120)
        self.assertEqual(performance['max_instances'], 100)
        self.assertEqual(performance['min_instances'], 0)
        self.assertEqual(performance['runtime'], 'python39')
    
    def test_analyze_function_triggers_http(self):
        """Test análisis de triggers - HTTP."""
        function = {
            'serviceConfig': {
                'uri': 'https://us-central1-project.cloudfunctions.net/my-function'
            }
        }
        
        triggers = self.base.analyze_function_triggers(function)
        
        self.assertEqual(triggers['type'], 'HTTP')
        self.assertIn('uri', triggers)
    
    def test_analyze_function_triggers_event(self):
        """Test análisis de triggers - Event."""
        function = {
            'eventTrigger': {
                'eventType': 'google.pubsub.topic.publish',
                'resource': 'projects/project/topics/my-topic',
                'service': 'pubsub.googleapis.com'
            }
        }
        
        triggers = self.base.analyze_function_triggers(function)
        
        self.assertEqual(triggers['type'], 'EVENT')
        self.assertEqual(triggers['event_type'], 'google.pubsub.topic.publish')
    
    def test_calculate_estimated_cost(self):
        """Test cálculo de costo estimado."""
        function = {
            'serviceConfig': {
                'availableMemoryMb': 256,
                'timeoutSeconds': 60
            }
        }
        
        cost = self.base.calculate_estimated_cost(function, monthly_invocations=1000000)
        
        self.assertIn('monthly_invocations', cost)
        self.assertIn('gb_seconds', cost)
        self.assertIn('invocation_cost', cost)
        self.assertIn('compute_cost', cost)
        self.assertIn('total_monthly_estimate', cost)
        self.assertGreaterEqual(cost['total_monthly_estimate'], 0)


class TestCloudFunctionsMetrics(unittest.TestCase):
    """Tests para CloudFunctionsMetrics."""
    
    def test_calculate_health_score_excellent(self):
        """Test health score - excelente."""
        function = {
            'serviceConfig': {
                'ingressSettings': 'INTERNAL_ONLY',
                'timeoutSeconds': 60,
                'availableMemoryMb': 512,
                'minInstanceCount': 0
            }
        }
        
        score = CloudFunctionsMetrics.calculate_health_score(function)
        
        self.assertGreaterEqual(score, 80)
    
    def test_calculate_health_score_poor(self):
        """Test health score - pobre."""
        function = {
            'serviceConfig': {
                'ingressSettings': 'ALLOW_ALL',
                'timeoutSeconds': 10,
                'availableMemoryMb': 128,
                'minInstanceCount': 20
            }
        }
        
        score = CloudFunctionsMetrics.calculate_health_score(function)
        
        self.assertLess(score, 60)
    
    def test_calculate_security_score_secure(self):
        """Test security score - segura."""
        function = {
            'serviceConfig': {
                'ingressSettings': 'INTERNAL_ONLY',
                'securityLevel': 'SECURE_ALWAYS',
                'serviceAccountEmail': 'custom@project.iam.gserviceaccount.com',
                'environmentVariables': {'APP_ENV': 'prod'}
            }
        }
        
        score = CloudFunctionsMetrics.calculate_security_score(function)
        
        self.assertGreater(score, 70)
    
    def test_calculate_security_score_insecure(self):
        """Test security score - insegura."""
        function = {
            'serviceConfig': {
                'ingressSettings': 'ALLOW_ALL',
                'securityLevel': 'SECURE_OPTIONAL',
                'serviceAccountEmail': 'default@project.iam.gserviceaccount.com',
                'environmentVariables': {'DATABASE_PASSWORD': 'secret123'}
            }
        }
        
        score = CloudFunctionsMetrics.calculate_security_score(function)
        
        self.assertLess(score, 70)
    
    def test_calculate_cost_efficiency_score_efficient(self):
        """Test cost efficiency score - eficiente."""
        function = {
            'serviceConfig': {
                'availableMemoryMb': 256,
                'timeoutSeconds': 60,
                'minInstanceCount': 0
            }
        }
        
        score = CloudFunctionsMetrics.calculate_cost_efficiency_score(function)
        
        self.assertGreater(score, 80)
    
    def test_calculate_cost_efficiency_score_inefficient(self):
        """Test cost efficiency score - ineficiente."""
        function = {
            'serviceConfig': {
                'availableMemoryMb': 4096,
                'timeoutSeconds': 540,
                'minInstanceCount': 10
            }
        }
        
        score = CloudFunctionsMetrics.calculate_cost_efficiency_score(function)
        
        self.assertLess(score, 60)
    
    def test_categorize_function_http(self):
        """Test categorización - HTTP."""
        function = {
            'serviceConfig': {
                'uri': 'https://example.com/function'
            }
        }
        
        category = CloudFunctionsMetrics.categorize_function(function)
        
        self.assertEqual(category, 'HTTP')
    
    def test_categorize_function_pubsub(self):
        """Test categorización - Pub/Sub."""
        function = {
            'eventTrigger': {
                'eventType': 'google.pubsub.topic.publish'
            }
        }
        
        category = CloudFunctionsMetrics.categorize_function(function)
        
        self.assertEqual(category, 'PUBSUB')
    
    def test_categorize_function_storage(self):
        """Test categorización - Storage."""
        function = {
            'eventTrigger': {
                'eventType': 'google.storage.object.finalize'
            }
        }
        
        category = CloudFunctionsMetrics.categorize_function(function)
        
        self.assertEqual(category, 'STORAGE')
    
    def test_estimate_monthly_cost(self):
        """Test estimación de costo mensual."""
        function = {
            'serviceConfig': {
                'availableMemoryMb': 256,
                'timeoutSeconds': 60
            }
        }
        
        cost = CloudFunctionsMetrics.estimate_monthly_cost(function, invocations=1000000)
        
        self.assertGreaterEqual(cost, 0)
        self.assertIsInstance(cost, float)
    
    def test_compare_functions(self):
        """Test comparación de funciones."""
        functions = [
            {
                'name': 'func1',
                'runtime': 'python39',
                'serviceConfig': {
                    'availableMemoryMb': 256,
                    'timeoutSeconds': 60,
                    'minInstanceCount': 0,
                    'region': 'us-central1',
                    'ingressSettings': 'ALLOW_ALL'
                },
                'eventTrigger': {}
            },
            {
                'name': 'func2',
                'runtime': 'node16',
                'serviceConfig': {
                    'availableMemoryMb': 512,
                    'timeoutSeconds': 120,
                    'minInstanceCount': 1,
                    'region': 'us-east1',
                    'ingressSettings': 'INTERNAL_ONLY'
                },
                'eventTrigger': {'eventType': 'google.pubsub.topic.publish'}
            }
        ]
        
        comparison = CloudFunctionsMetrics.compare_functions(functions)
        
        self.assertEqual(comparison['total_functions'], 2)
        self.assertIn('by_runtime', comparison)
        self.assertIn('by_trigger_type', comparison)
        self.assertIn('by_region', comparison)
        self.assertGreater(comparison['avg_memory_mb'], 0)
        self.assertGreater(comparison['avg_timeout_seconds'], 0)


class TestCloudFunctionsIntegration(unittest.TestCase):
    """Tests de integración para Cloud Functions."""
    
    def test_full_analysis_workflow(self):
        """Test flujo completo de análisis."""
        function = {
            'name': 'projects/test-project/locations/us-central1/functions/my-function',
            'runtime': 'python39',
            'state': 'ACTIVE',
            'serviceConfig': {
                'availableMemoryMb': 512,
                'timeoutSeconds': 120,
                'maxInstanceCount': 100,
                'minInstanceCount': 0,
                'cpu': '0.333',
                'region': 'us-central1',
                'ingressSettings': 'ALLOW_ALL',
                'securityLevel': 'SECURE_ALWAYS',
                'serviceAccountEmail': 'custom@project.iam.gserviceaccount.com',
                'environmentVariables': {'APP_ENV': 'prod'},
                'uri': 'https://us-central1-test-project.cloudfunctions.net/my-function'
            },
            'updateTime': '2026-07-07T12:00:00Z'
        }
        
        base = CloudFunctionsBase("test-project")
        
        # Análisis de seguridad
        security = base.analyze_function_security(function)
        self.assertIsNotNone(security)
        
        # Análisis de performance
        performance = base.analyze_function_performance(function)
        self.assertIsNotNone(performance)
        
        # Análisis de triggers
        triggers = base.analyze_function_triggers(function)
        self.assertIsNotNone(triggers)
        
        # Cálculo de costo
        cost = base.calculate_estimated_cost(function)
        self.assertIsNotNone(cost)
        
        # Métricas
        health_score = CloudFunctionsMetrics.calculate_health_score(function)
        security_score = CloudFunctionsMetrics.calculate_security_score(function)
        cost_score = CloudFunctionsMetrics.calculate_cost_efficiency_score(function)
        
        self.assertGreaterEqual(health_score, 0)
        self.assertGreaterEqual(security_score, 0)
        self.assertGreaterEqual(cost_score, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
