# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Tests unitarios para herramientas AWS
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Agregar ruta de herramientas
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestRDSComparator(unittest.TestCase):
    """Tests para RDS Comparator"""
    
    @patch('boto3.Session')
    def test_initialization(self, mock_session):
        """Test inicialización"""
        from rds.aws_rds_comparator import RDSComparator
        comparator = RDSComparator(profile='test')
        self.assertIsNotNone(comparator)
    
    @patch('boto3.Session')
    def test_get_instances(self, mock_session):
        """Test obtener instancias"""
        from rds.aws_rds_comparator import RDSComparator
        
        mock_client = MagicMock()
        mock_client.describe_db_instances.return_value = {
            'DBInstances': [
                {'DBInstanceIdentifier': 'test-db', 'Engine': 'postgres'}
            ]
        }
        
        with patch.object(RDSComparator, 'session') as mock_s:
            mock_s.client.return_value = mock_client
            comparator = RDSComparator()
            instances = comparator.get_instances('us-east-1')
            self.assertEqual(len(instances), 1)


class TestAPIGatewayChecker(unittest.TestCase):
    """Tests para API Gateway Checker"""
    
    @patch('boto3.Session')
    def test_initialization(self, mock_session):
        """Test inicialización"""
        from vpc.aws_api_gateway_checker import APIGatewayChecker
        checker = APIGatewayChecker(profile='test')
        self.assertIsNotNone(checker)
    
    @patch('boto3.Session')
    def test_get_apis(self, mock_session):
        """Test obtener APIs"""
        from vpc.aws_api_gateway_checker import APIGatewayChecker
        
        mock_client = MagicMock()
        mock_client.get_rest_apis.return_value = {
            'items': [{'id': 'api-1', 'name': 'test-api'}]
        }
        
        with patch.object(APIGatewayChecker, 'client', mock_client):
            checker = APIGatewayChecker()
            apis = checker.get_apis()
            self.assertEqual(len(apis), 1)


class TestLambdaAnalyzer(unittest.TestCase):
    """Tests para Lambda Analyzer"""
    
    @patch('boto3.Session')
    def test_initialization(self, mock_session):
        """Test inicialización"""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))
        from aws_lambda_analyzer import LambdaFunctionsAnalyzer
        analyzer = LambdaFunctionsAnalyzer(profile='test')
        self.assertIsNotNone(analyzer)


class TestEKSTools(unittest.TestCase):
    """Tests para herramientas EKS"""
    
    @patch('boto3.Session')
    def test_pod_connectivity_checker(self, mock_session):
        """Test EKS Pod Connectivity Checker"""
        from eks.aws_eks_pod_connectivity_checker import EKSPodConnectivityChecker
        checker = EKSPodConnectivityChecker(profile='test')
        self.assertIsNotNone(checker)
    
    @patch('boto3.Session')
    def test_deployment_validator(self, mock_session):
        """Test EKS Deployment Validator"""
        from eks.aws_eks_deployment_validator import EKSDeploymentValidator
        validator = EKSDeploymentValidator(profile='test')
        self.assertIsNotNone(validator)
    
    @patch('boto3.Session')
    def test_deployments_off_analyzer(self, mock_session):
        """Test EKS Deployments Off Analyzer"""
        from eks.aws_eks_deployments_off_analyzer import EKSDeploymentsOffAnalyzer
        analyzer = EKSDeploymentsOffAnalyzer(profile='test')
        self.assertIsNotNone(analyzer)
    
    @patch('boto3.Session')
    def test_deploy_dependency_checker(self, mock_session):
        """Test EKS Deploy Dependency Checker"""
        from eks.aws_eks_deploy_dependency_checker import EKSDeployDependencyChecker
        checker = EKSDeployDependencyChecker(profile='test')
        self.assertIsNotNone(checker)


class TestIAMTools(unittest.TestCase):
    """Tests para herramientas IAM"""
    
    @patch('boto3.Session')
    def test_service_linked_roles_checker(self, mock_session):
        """Test Service Linked Roles Checker"""
        from iam.aws_service_linked_roles_checker import IAMServiceLinkedRolesChecker
        checker = IAMServiceLinkedRolesChecker(profile='test')
        self.assertIsNotNone(checker)
    
    @patch('boto3.Session')
    def test_service_linked_roles_reporter(self, mock_session):
        """Test Service Linked Roles Reporter"""
        from iam.aws_service_linked_roles_reporter import IAMServiceLinkedRolesReporter
        reporter = IAMServiceLinkedRolesReporter(profile='test')
        self.assertIsNotNone(reporter)


class TestInventoryTools(unittest.TestCase):
    """Tests para herramientas de inventario"""
    
    def test_reports_viewer(self):
        """Test Reports Viewer"""
        from inventory.aws_reports_viewer import AWSReportsViewer
        viewer = AWSReportsViewer()
        self.assertIsNotNone(viewer)
    
    @patch('boto3.Session')
    def test_infrastructure_consolidator(self, mock_session):
        """Test Infrastructure Consolidator"""
        from inventory.aws_infrastructure_consolidator import AWSInfrastructureConsolidator
        consolidator = AWSInfrastructureConsolidator(profile='test')
        self.assertIsNotNone(consolidator)
    
    @patch('boto3.Session')
    def test_unified_dashboard(self, mock_session):
        """Test Unified Infrastructure Dashboard"""
        from inventory.aws_unified_infrastructure_dashboard import AWSUnifiedDashboard
        dashboard = AWSUnifiedDashboard(profile='test')
        self.assertIsNotNone(dashboard)
    
    @patch('boto3.Session')
    def test_inventory_consolidator(self, mock_session):
        """Test Inventory Consolidator"""
        from inventory.aws_inventory_consolidator import AWSInventoryConsolidator
        consolidator = AWSInventoryConsolidator(profile='test')
        self.assertIsNotNone(consolidator)


class TestECRTools(unittest.TestCase):
    """Tests para herramientas ECR"""
    
    @patch('boto3.Session')
    def test_ecr_image_filter(self, mock_session):
        """Test ECR Image Filter"""
        from ecr.aws_ecr_image_filter import ECRImageFilter
        filter_tool = ECRImageFilter(profile='test')
        self.assertIsNotNone(filter_tool)


class TestLambdaTools(unittest.TestCase):
    """Tests para herramientas Lambda"""
    
    @patch('boto3.Session')
    def test_lambda_cost_analyzer(self, mock_session):
        """Test Lambda Cost Analyzer"""
        from lambda_.aws_lambda_cost_analyzer import LambdaCostAnalyzer
        analyzer = LambdaCostAnalyzer(profile='test')
        self.assertIsNotNone(analyzer)
    
    @patch('boto3.Session')
    def test_lambda_health_analyzer(self, mock_session):
        """Test Lambda Health Analyzer"""
        from lambda_.aws_lambda_health_analyzer import LambdaHealthAnalyzer
        analyzer = LambdaHealthAnalyzer(profile='test')
        self.assertIsNotNone(analyzer)
    
    @patch('boto3.Session')
    def test_lambda_security_auditor(self, mock_session):
        """Test Lambda Security Auditor"""
        from lambda_.aws_lambda_security_auditor import LambdaSecurityAuditor
        auditor = LambdaSecurityAuditor(profile='test')
        self.assertIsNotNone(auditor)


class TestVPCTools(unittest.TestCase):
    """Tests para herramientas VPC"""
    
    @patch('boto3.Session')
    def test_vpc_ip_addresses_checker(self, mock_session):
        """Test VPC IP Addresses Checker"""
        from vpc.aws_vpc_ip_addresses_checker import VPCIPAddressesChecker
        checker = VPCIPAddressesChecker(profile='test')
        self.assertIsNotNone(checker)


if __name__ == '__main__':
    unittest.main()
