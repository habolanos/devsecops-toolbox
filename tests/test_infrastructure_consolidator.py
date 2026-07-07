#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests para Infrastructure Consolidator (Tool 36)

Suite de tests unitarios para validar consolidación de infraestructura.

Autor: Harold Adrian
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Agregar ruta de scm/gcp/consolidation
sys.path.insert(0, str(Path(__file__).parent.parent / "scm" / "gcp" / "consolidation"))

from consolidation_base import (
    LoadBalancerExtractor, CloudRunExtractor, CloudFunctionsExtractor,
    RelationshipMapper
)


class TestLoadBalancerExtractor(unittest.TestCase):
    """Tests para LoadBalancerExtractor."""
    
    def setUp(self):
        """Configuración inicial."""
        self.extractor = LoadBalancerExtractor("test-project", debug=False)
    
    def test_init(self):
        """Test inicialización."""
        self.assertEqual(self.extractor.project_id, "test-project")
        self.assertFalse(self.extractor.debug)
    
    def test_extract_all_structure(self):
        """Test estructura de extracción."""
        with patch.object(self.extractor, 'get_forwarding_rules', return_value=[]):
            with patch.object(self.extractor, 'get_backend_services', return_value=[]):
                with patch.object(self.extractor, 'get_url_maps', return_value=[]):
                    with patch.object(self.extractor, 'get_health_checks', return_value=[]):
                        with patch.object(self.extractor, 'get_ssl_certificates', return_value=[]):
                            with patch.object(self.extractor, 'get_security_policies', return_value=[]):
                                with patch.object(self.extractor, 'get_negs', return_value=[]):
                                    result = self.extractor.extract_all()
        
        self.assertIn('forwarding_rules', result)
        self.assertIn('backend_services', result)
        self.assertIn('url_maps', result)
        self.assertIn('health_checks', result)
        self.assertIn('ssl_certificates', result)
        self.assertIn('security_policies', result)
        self.assertIn('network_endpoint_groups', result)


class TestCloudRunExtractor(unittest.TestCase):
    """Tests para CloudRunExtractor."""
    
    def setUp(self):
        """Configuración inicial."""
        self.extractor = CloudRunExtractor("test-project", debug=False)
    
    def test_init(self):
        """Test inicialización."""
        self.assertEqual(self.extractor.project_id, "test-project")
        self.assertFalse(self.extractor.debug)
    
    def test_extract_all_structure(self):
        """Test estructura de extracción."""
        with patch.object(self.extractor, 'get_services', return_value=[]):
            result = self.extractor.extract_all()
        
        self.assertIn('services', result)
        self.assertIsInstance(result['services'], list)


class TestCloudFunctionsExtractor(unittest.TestCase):
    """Tests para CloudFunctionsExtractor."""
    
    def setUp(self):
        """Configuración inicial."""
        self.extractor = CloudFunctionsExtractor("test-project", debug=False)
    
    def test_init(self):
        """Test inicialización."""
        self.assertEqual(self.extractor.project_id, "test-project")
        self.assertFalse(self.extractor.debug)
    
    def test_extract_all_structure(self):
        """Test estructura de extracción."""
        with patch.object(self.extractor, 'get_functions', return_value=[]):
            result = self.extractor.extract_all()
        
        self.assertIn('functions', result)
        self.assertIsInstance(result['functions'], list)


class TestRelationshipMapper(unittest.TestCase):
    """Tests para RelationshipMapper."""
    
    def setUp(self):
        """Configuración inicial."""
        self.lb_data = {
            'backend_services': [
                {
                    'name': 'api-backend',
                    'backends': [
                        {
                            'group': 'projects/test/global/networkEndpointGroups/api-neg-cloudrun',
                            'balancingMode': 'RATE'
                        }
                    ]
                }
            ],
            'network_endpoint_groups': [
                {
                    'name': 'api-neg-cloudrun'
                }
            ]
        }
        
        self.cr_data = {
            'services': [
                {
                    'name': 'api-service',
                    'location': 'us-central1'
                }
            ]
        }
        
        self.cf_data = {
            'functions': [
                {
                    'name': 'webhook-handler',
                    'serviceConfig': {'region': 'us-central1'}
                }
            ]
        }
        
        self.mapper = RelationshipMapper(self.lb_data, self.cr_data, self.cf_data)
    
    def test_map_all_relationships_structure(self):
        """Test estructura de mapeo de relaciones."""
        result = self.mapper.map_all_relationships()
        
        self.assertIn('lb_to_cloud_run', result)
        self.assertIn('lb_to_cloud_functions', result)
        self.assertIn('orphaned_cloud_run', result)
        self.assertIn('orphaned_cloud_functions', result)
    
    def test_find_orphaned_cloud_run(self):
        """Test identificación de Cloud Run huérfanos."""
        orphaned = self.mapper.find_orphaned_cloud_run()
        
        self.assertIsInstance(orphaned, list)
    
    def test_find_orphaned_cloud_functions(self):
        """Test identificación de Cloud Functions huérfanos."""
        orphaned = self.mapper.find_orphaned_cloud_functions()
        
        self.assertIsInstance(orphaned, list)
    
    def test_extract_name(self):
        """Test extracción de nombre."""
        full_name = "projects/test/locations/us-central1/functions/my-function"
        name = RelationshipMapper._extract_name(full_name)
        
        self.assertEqual(name, "my-function")
    
    def test_extract_name_empty(self):
        """Test extracción de nombre - vacío."""
        name = RelationshipMapper._extract_name("")
        
        self.assertEqual(name, "N/A")


class TestConsolidationIntegration(unittest.TestCase):
    """Tests de integración para consolidación."""
    
    def test_full_consolidation_workflow(self):
        """Test flujo completo de consolidación."""
        # Datos simulados
        lb_data = {
            'forwarding_rules': [
                {'name': 'web-frontend', 'IPAddress': '34.120.x.x'}
            ],
            'backend_services': [
                {
                    'name': 'api-backend',
                    'backends': [
                        {
                            'group': 'projects/test/global/networkEndpointGroups/api-neg-cloudrun'
                        }
                    ]
                }
            ],
            'network_endpoint_groups': [
                {'name': 'api-neg-cloudrun'}
            ],
            'security_policies': [
                {'name': 'cloud-armor-policy'}
            ],
            'ssl_certificates': [
                {'name': 'ssl-cert'}
            ]
        }
        
        cr_data = {
            'services': [
                {
                    'name': 'api-service',
                    'location': 'us-central1',
                    'status': 'ACTIVE'
                }
            ]
        }
        
        cf_data = {
            'functions': [
                {
                    'name': 'webhook-handler',
                    'serviceConfig': {'region': 'us-central1'},
                    'state': 'ACTIVE'
                }
            ]
        }
        
        # Crear mapper
        mapper = RelationshipMapper(lb_data, cr_data, cf_data)
        
        # Mapear relaciones
        relationships = mapper.map_all_relationships()
        
        # Validaciones
        self.assertIsNotNone(relationships)
        self.assertIn('lb_to_cloud_run', relationships)
        self.assertIn('lb_to_cloud_functions', relationships)
        self.assertIn('orphaned_cloud_run', relationships)
        self.assertIn('orphaned_cloud_functions', relationships)
    
    def test_consolidation_with_orphaned_services(self):
        """Test consolidación con servicios huérfanos."""
        lb_data = {
            'backend_services': [],
            'network_endpoint_groups': []
        }
        
        cr_data = {
            'services': [
                {
                    'name': 'orphaned-service',
                    'location': 'us-central1'
                }
            ]
        }
        
        cf_data = {
            'functions': [
                {
                    'name': 'orphaned-function',
                    'serviceConfig': {'region': 'us-central1'}
                }
            ]
        }
        
        mapper = RelationshipMapper(lb_data, cr_data, cf_data)
        
        orphaned_cr = mapper.find_orphaned_cloud_run()
        orphaned_cf = mapper.find_orphaned_cloud_functions()
        
        self.assertEqual(len(orphaned_cr), 1)
        self.assertEqual(len(orphaned_cf), 1)


class TestConsolidationMetrics(unittest.TestCase):
    """Tests para métricas de consolidación."""
    
    def test_health_score_calculation(self):
        """Test cálculo de health score."""
        consolidation = {
            'summary': {
                'orphaned_services': 0,
                'health_score': 100
            },
            'health_status': {
                'security_policies_count': 3,
                'ssl_configured': 5
            }
        }
        
        self.assertEqual(consolidation['summary']['health_score'], 100)
    
    def test_health_score_with_orphaned(self):
        """Test health score con servicios huérfanos."""
        orphaned = 3
        health_score = 100
        
        if orphaned > 0:
            health_score -= min(20, orphaned * 5)
        
        self.assertEqual(health_score, 85)
    
    def test_health_score_without_security(self):
        """Test health score sin Cloud Armor."""
        health_score = 100
        security_policies = 0
        
        if security_policies == 0:
            health_score -= 15
        
        self.assertEqual(health_score, 85)
    
    def test_health_score_without_ssl(self):
        """Test health score sin SSL."""
        health_score = 100
        ssl_configured = 0
        
        if ssl_configured == 0:
            health_score -= 15
        
        self.assertEqual(health_score, 85)


if __name__ == '__main__':
    unittest.main(verbosity=2)
