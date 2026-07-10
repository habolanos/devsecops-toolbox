# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios simplificados para herramientas AWS
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Agregar ruta de herramientas
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestAWSToolsBasic(unittest.TestCase):
    """Tests básicos para herramientas AWS"""
    
    def test_rds_comparator_import(self):
        """Test importación de RDS Comparator"""
        try:
            from rds.aws_rds_comparator import RDSComparator
            self.assertIsNotNone(RDSComparator)
        except Exception as e:
            self.fail(f"No se pudo importar RDSComparator: {e}")
    
    def test_api_gateway_checker_import(self):
        """Test importación de API Gateway Checker"""
        try:
            from vpc.aws_api_gateway_checker import APIGatewayChecker
            self.assertIsNotNone(APIGatewayChecker)
        except Exception as e:
            self.fail(f"No se pudo importar APIGatewayChecker: {e}")
    
    def test_vpc_ip_checker_import(self):
        """Test importación de VPC IP Checker"""
        try:
            from vpc.aws_vpc_ip_addresses_checker import VPCIPAddressesChecker
            self.assertIsNotNone(VPCIPAddressesChecker)
        except Exception as e:
            self.fail(f"No se pudo importar VPCIPAddressesChecker: {e}")
    
    def test_eks_pod_connectivity_import(self):
        """Test importación de EKS Pod Connectivity Checker"""
        try:
            from eks.aws_eks_pod_connectivity_checker import EKSPodConnectivityChecker
            self.assertIsNotNone(EKSPodConnectivityChecker)
        except Exception as e:
            self.fail(f"No se pudo importar EKSPodConnectivityChecker: {e}")
    
    def test_eks_deployment_validator_import(self):
        """Test importación de EKS Deployment Validator"""
        try:
            from eks.aws_eks_deployment_validator import EKSDeploymentValidator
            self.assertIsNotNone(EKSDeploymentValidator)
        except Exception as e:
            self.fail(f"No se pudo importar EKSDeploymentValidator: {e}")
    
    def test_eks_deployments_off_analyzer_import(self):
        """Test importación de EKS Deployments Off Analyzer"""
        try:
            from eks.aws_eks_deployments_off_analyzer import EKSDeploymentsOffAnalyzer
            self.assertIsNotNone(EKSDeploymentsOffAnalyzer)
        except Exception as e:
            self.fail(f"No se pudo importar EKSDeploymentsOffAnalyzer: {e}")
    
    def test_eks_deploy_dependency_checker_import(self):
        """Test importación de EKS Deploy Dependency Checker"""
        try:
            from eks.aws_eks_deploy_dependency_checker import EKSDeployDependencyChecker
            self.assertIsNotNone(EKSDeployDependencyChecker)
        except Exception as e:
            self.fail(f"No se pudo importar EKSDeployDependencyChecker: {e}")
    
    def test_iam_service_linked_roles_checker_import(self):
        """Test importación de IAM Service Linked Roles Checker"""
        try:
            from iam.aws_service_linked_roles_checker import IAMServiceLinkedRolesChecker
            self.assertIsNotNone(IAMServiceLinkedRolesChecker)
        except Exception as e:
            self.fail(f"No se pudo importar IAMServiceLinkedRolesChecker: {e}")
    
    def test_iam_service_linked_roles_reporter_import(self):
        """Test importación de IAM Service Linked Roles Reporter"""
        try:
            from iam.aws_service_linked_roles_reporter import IAMServiceLinkedRolesReporter
            self.assertIsNotNone(IAMServiceLinkedRolesReporter)
        except Exception as e:
            self.fail(f"No se pudo importar IAMServiceLinkedRolesReporter: {e}")
    
    def test_ecr_image_filter_import(self):
        """Test importación de ECR Image Filter"""
        try:
            from ecr.aws_ecr_image_filter import ECRImageFilter
            self.assertIsNotNone(ECRImageFilter)
        except Exception as e:
            self.fail(f"No se pudo importar ECRImageFilter: {e}")
    
    def test_reports_viewer_import(self):
        """Test importación de Reports Viewer"""
        try:
            from inventory.aws_reports_viewer import AWSReportsViewer
            self.assertIsNotNone(AWSReportsViewer)
        except Exception as e:
            self.fail(f"No se pudo importar AWSReportsViewer: {e}")
    
    def test_infrastructure_consolidator_import(self):
        """Test importación de Infrastructure Consolidator"""
        try:
            from inventory.aws_infrastructure_consolidator import AWSInfrastructureConsolidator
            self.assertIsNotNone(AWSInfrastructureConsolidator)
        except Exception as e:
            self.fail(f"No se pudo importar AWSInfrastructureConsolidator: {e}")
    
    def test_unified_dashboard_import(self):
        """Test importación de Unified Dashboard"""
        try:
            from inventory.aws_unified_infrastructure_dashboard import AWSUnifiedDashboard
            self.assertIsNotNone(AWSUnifiedDashboard)
        except Exception as e:
            self.fail(f"No se pudo importar AWSUnifiedDashboard: {e}")
    
    def test_inventory_consolidator_import(self):
        """Test importación de Inventory Consolidator"""
        try:
            from inventory.aws_inventory_consolidator import AWSInventoryConsolidator
            self.assertIsNotNone(AWSInventoryConsolidator)
        except Exception as e:
            self.fail(f"No se pudo importar AWSInventoryConsolidator: {e}")


class TestAWSToolsStructure(unittest.TestCase):
    """Tests de estructura de herramientas AWS"""
    
    def test_rds_comparator_has_methods(self):
        """Test que RDS Comparator tiene métodos requeridos"""
        from rds.aws_rds_comparator import RDSComparator
        self.assertTrue(hasattr(RDSComparator, 'get_instances'))
        self.assertTrue(hasattr(RDSComparator, 'compare_instances'))
    
    def test_api_gateway_checker_has_methods(self):
        """Test que API Gateway Checker tiene métodos requeridos"""
        from vpc.aws_api_gateway_checker import APIGatewayChecker
        self.assertTrue(hasattr(APIGatewayChecker, 'get_apis'))
        self.assertTrue(hasattr(APIGatewayChecker, 'analyze_api'))
        self.assertTrue(hasattr(APIGatewayChecker, 'check_all'))
    
    def test_vpc_ip_checker_has_methods(self):
        """Test que VPC IP Checker tiene métodos requeridos"""
        from vpc.aws_vpc_ip_addresses_checker import VPCIPAddressesChecker
        self.assertTrue(hasattr(VPCIPAddressesChecker, 'analyze'))


if __name__ == '__main__':
    unittest.main()
