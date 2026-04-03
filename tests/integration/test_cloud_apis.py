"""
Tests de integración para APIs Cloud con mocking

Estos tests verifican la integración entre los módulos y las APIs cloud
usando mocks para simular las respuestas sin requerir credenciales reales.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Asegurar importaciones
devsecops_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(devsecops_root / "scm"))
sys.path.insert(0, str(devsecops_root / "tests"))


class TestGCPIntegration:
    """Tests de integración para GCP."""
    
    @pytest.mark.integration
    @pytest.mark.gcp
    def test_gcp_project_api_mock(self):
        """Test: Integración con GCP Projects API usando mock."""
        from mocks.gcp_mock import GCPMock
        
        gcp_mock = GCPMock()
        
        # Simular respuesta de API
        project_data = gcp_mock.mock_project_response("my-gcp-project")
        
        assert project_data["projectId"] == "my-gcp-project"
        assert project_data["lifecycleState"] == "ACTIVE"
        assert "projectNumber" in project_data
    
    @pytest.mark.integration
    @pytest.mark.gcp
    def test_gcp_cluster_api_mock(self):
        """Test: Integración con GKE API usando mock."""
        from mocks.gcp_mock import GCPMock
        
        gcp_mock = GCPMock()
        
        cluster_data = gcp_mock.mock_cluster_response("prod-cluster", "prod-project")
        
        assert cluster_data["name"] == "prod-cluster"
        assert cluster_data["status"] == "RUNNING"
        assert cluster_data["nodeConfig"]["machineType"] == "e2-medium"
    
    @pytest.mark.integration
    @pytest.mark.gcp
    def test_gcp_mock_client(self):
        """Test: Uso de cliente mock de GCP."""
        from mocks.gcp_mock import GCPMock
        
        gcp_mock = GCPMock()
        mock_client = gcp_mock.create_mock_client()
        
        # Simular llamada a API
        result = mock_client.projects().list().execute()
        
        assert "projects" in result
        assert len(result["projects"]) == 1
        assert result["projects"][0]["projectId"] == "test-project-123"
    
    @pytest.mark.integration
    @pytest.mark.gcp
    def test_gcloud_command_mock(self):
        """Test: Mock de comandos gcloud CLI."""
        from mocks.gcp_mock import GCPCommandMock, mock_gcloud_command
        
        cmd_mock = GCPCommandMock()
        returncode, stdout, stderr = cmd_mock.get_command_response("gcloud projects list")
        
        assert returncode == 0
        assert "test-project-123" in stdout
    
    @pytest.mark.integration
    @pytest.mark.gcp
    def test_gcp_error_handling(self):
        """Test: Manejo de errores de GCP API."""
        from mocks.gcp_mock import GCPMock
        
        gcp_mock = GCPMock()
        error_response = gcp_mock.mock_error_response(404, "Project not found")
        
        assert error_response["error"]["code"] == 404
        assert error_response["error"]["message"] == "Project not found"


class TestAZDOIntegration:
    """Tests de integración para Azure DevOps."""
    
    @pytest.mark.integration
    @pytest.mark.azdo
    def test_azdo_project_api_mock(self):
        """Test: Integración con AZDO Projects API usando mock."""
        from mocks.azdo_mock import AZDOMock
        
        azdo_mock = AZDOMock()
        project_data = azdo_mock.mock_project_response("proj-123", "Test Project")
        
        assert project_data["id"] == "proj-123"
        assert project_data["name"] == "Test Project"
        assert project_data["state"] == "wellFormed"
    
    @pytest.mark.integration
    @pytest.mark.azdo
    def test_azdo_pr_api_mock(self):
        """Test: Integración con AZDO Pull Requests API."""
        from mocks.azdo_mock import AZDOMock
        
        azdo_mock = AZDOMock()
        pr_data = azdo_mock.mock_pull_request_response(42, "Fix critical bug", "active")
        
        assert pr_data["pullRequestId"] == 42
        assert pr_data["title"] == "Fix critical bug"
        assert pr_data["status"] == "active"
        assert pr_data["sourceRefName"] == "refs/heads/feature/test-branch"
    
    @pytest.mark.integration
    @pytest.mark.azdo
    def test_azdo_pipeline_api_mock(self):
        """Test: Integración con AZDO Pipelines API."""
        from mocks.azdo_mock import AZDOMock
        
        azdo_mock = AZDOMock()
        pipeline_data = azdo_mock.mock_pipeline_response(5, "ci-pipeline")
        
        assert pipeline_data["id"] == 5
        assert pipeline_data["name"] == "ci-pipeline"
        assert pipeline_data["configuration"]["type"] == "yaml"
    
    @pytest.mark.integration
    @pytest.mark.azdo
    def test_azdo_release_api_mock(self):
        """Test: Integración con AZDO Releases API."""
        from mocks.azdo_mock import AZDOMock
        
        azdo_mock = AZDOMock()
        release_data = azdo_mock.mock_release_response(10, "Release-2024.1")
        
        assert release_data["id"] == 10
        assert release_data["name"] == "Release-2024.1"
        assert len(release_data["environments"]) == 3  # dev, qa, prod
    
    @pytest.mark.integration
    @pytest.mark.azdo
    def test_azdo_branch_policy_mock(self):
        """Test: Integración con AZDO Branch Policies API."""
        from mocks.azdo_mock import AZDOMock
        
        azdo_mock = AZDOMock()
        policy_data = azdo_mock.mock_branch_policy_response("main")
        
        assert policy_data["count"] == 2
        assert policy_data["value"][0]["type"]["displayName"] == "Minimum number of reviewers"
        assert policy_data["value"][0]["settings"]["minimumApproverCount"] == 2
    
    @pytest.mark.integration
    @pytest.mark.azdo
    def test_azdo_request_mock(self):
        """Test: Mock de requests HTTP a AZDO API."""
        from mocks.azdo_mock import AZDORequestMock
        
        request_mock = AZDORequestMock(pat="test-token-123")
        status, response = request_mock.get_response("GET", "/_apis/projects")
        
        assert status == 200
        assert "value" in response
        assert response["count"] == 1
    
    @pytest.mark.integration
    @pytest.mark.azdo
    def test_azdo_error_handling(self):
        """Test: Manejo de errores de AZDO API."""
        from mocks.azdo_mock import AZDOMock
        
        azdo_mock = AZDOMock()
        error_response = azdo_mock.mock_error_response(401, "Invalid PAT token")
        
        assert error_response["errorCode"] == 401
        assert "Invalid PAT token" in error_response["message"]


class TestAWSIntegration:
    """Tests de integración para AWS."""
    
    @pytest.mark.integration
    @pytest.mark.aws
    def test_aws_sts_mock(self):
        """Test: Integración con AWS STS usando mock."""
        from mocks.aws_mock import AWSMock
        
        aws_mock = AWSMock()
        identity = aws_mock.mock_sts_caller_identity()
        
        assert identity["Account"] == "123456789012"
        assert identity["UserId"] == "AIDACKCEVSQ6C2EXAMPLE"
        assert "arn:aws:iam::123456789012:user/test-user" in identity["Arn"]
    
    @pytest.mark.integration
    @pytest.mark.aws
    def test_aws_iam_user_mock(self):
        """Test: Integración con AWS IAM usando mock."""
        from mocks.aws_mock import AWSMock
        
        aws_mock = AWSMock()
        user_data = aws_mock.mock_iam_user_response("admin-user")
        
        assert user_data["User"]["UserName"] == "admin-user"
        assert user_data["User"]["Arn"] == "arn:aws:iam::123456789012:user/admin-user"
        assert len(user_data["User"]["Tags"]) == 2
    
    @pytest.mark.integration
    @pytest.mark.aws
    def test_aws_ec2_instance_mock(self):
        """Test: Integración con AWS EC2 usando mock."""
        from mocks.aws_mock import AWSMock
        
        aws_mock = AWSMock()
        instance_data = aws_mock.mock_ec2_instance_response("i-abcdef1234567890", "running")
        
        assert instance_data["InstanceId"] == "i-abcdef1234567890"
        assert instance_data["State"]["Name"] == "running"
        assert instance_data["InstanceType"] == "t3.medium"
    
    @pytest.mark.integration
    @pytest.mark.aws
    def test_aws_rds_instance_mock(self):
        """Test: Integración con AWS RDS usando mock."""
        from mocks.aws_mock import AWSMock
        
        aws_mock = AWSMock()
        rds_data = aws_mock.mock_rds_instance_response("production-db")
        
        assert rds_data["DBInstanceIdentifier"] == "production-db"
        assert rds_data["Engine"] == "postgres"
        assert rds_data["DBInstanceStatus"] == "available"
        assert rds_data["StorageEncrypted"] is True
    
    @pytest.mark.integration
    @pytest.mark.aws
    def test_aws_lambda_function_mock(self):
        """Test: Integración con AWS Lambda usando mock."""
        from mocks.aws_mock import AWSMock
        
        aws_mock = AWSMock()
        lambda_data = aws_mock.mock_lambda_function_response("process-data")
        
        assert lambda_data["FunctionName"] == "process-data"
        assert lambda_data["Runtime"] == "python3.11"
        assert lambda_data["MemorySize"] == 128
    
    @pytest.mark.integration
    @pytest.mark.aws
    def test_aws_eks_cluster_mock(self):
        """Test: Integración con AWS EKS usando mock."""
        from mocks.aws_mock import AWSMock
        
        aws_mock = AWSMock()
        eks_data = aws_mock.mock_eks_cluster_response("k8s-production")
        
        assert eks_data["cluster"]["name"] == "k8s-production"
        assert eks_data["cluster"]["version"] == "1.28"
        assert eks_data["cluster"]["status"] == "ACTIVE"
    
    @pytest.mark.integration
    @pytest.mark.aws
    def test_aws_boto3_client_mock(self):
        """Test: Uso de cliente mock de boto3."""
        from mocks.aws_mock import AWSMock
        
        aws_mock = AWSMock()
        
        # Probar diferentes servicios
        ec2_client = aws_mock.create_mock_boto3_client("ec2")
        result = ec2_client.describe_instances()
        
        assert "Reservations" in result
        assert len(result["Reservations"]) == 1
        
        # Probar otro servicio
        rds_client = aws_mock.create_mock_boto3_client("rds")
        rds_result = rds_client.describe_db_instances()
        
        assert "DBInstances" in rds_result
        assert len(rds_result["DBInstances"]) == 1
    
    @pytest.mark.integration
    @pytest.mark.aws
    def test_aws_cli_command_mock(self):
        """Test: Mock de comandos AWS CLI."""
        from mocks.aws_mock import AWSCLIMock
        
        cli_mock = AWSCLIMock()
        returncode, stdout, stderr = cli_mock.get_command_response("aws sts get-caller-identity")
        
        assert returncode == 0
        output = json.loads(stdout)
        assert output["Account"] == "123456789012"
    
    @pytest.mark.integration
    @pytest.mark.aws
    def test_aws_error_handling(self):
        """Test: Manejo de errores de AWS API."""
        from mocks.aws_mock import AWSMock
        
        aws_mock = AWSMock()
        error_response = aws_mock.mock_error_response("AccessDenied", "User not authorized")
        
        assert error_response["Error"]["Code"] == "AccessDenied"
        assert "not authorized" in error_response["Error"]["Message"]


class TestMultiCloudIntegration:
    """Tests de integración multi-cloud."""
    
    @pytest.mark.integration
    def test_cross_cloud_config_loading(self, sample_config_data):
        """Test: Carga de configuración para múltiples clouds."""
        from main import load_config, get_platform_config
        
        with patch("main.load_config", return_value=sample_config_data):
            gcp_config = get_platform_config("1")
            azdo_config = get_platform_config("2")
            aws_config = get_platform_config("3")
        
        assert gcp_config is not None
        assert azdo_config is not None
        assert aws_config is not None
        
        assert gcp_config["project_id"] == "test-project-123"
        assert azdo_config["organization_url"] == "https://dev.azure.com/test-org"
        assert aws_config["region"] == "us-east-1"
    
    @pytest.mark.integration
    def test_environment_variables_propagation(self, sample_config_data, clean_env):
        """Test: Propagación de variables de entorno a todos los clouds."""
        from main import prepare_env_for_platform
        import os
        
        with patch("main.load_config", return_value=sample_config_data):
            # Probar GCP
            gcp_env = prepare_env_for_platform("1")
            assert "GCP_PROJECT_ID" in gcp_env
            assert "CLOUDSDK_CORE_PROJECT" in gcp_env
            
            # Probar AZDO
            azdo_env = prepare_env_for_platform("2")
            assert "AZDO_ORG_URL" in azdo_env
            assert "AZDO_PAT" in azdo_env
            
            # Probar AWS
            aws_env = prepare_env_for_platform("3")
            assert "AWS_PROFILE" in aws_env
            assert "AWS_REGION" in aws_env
    
    @pytest.mark.integration
    def test_global_config_propagation(self, sample_config_data, clean_env):
        """Test: Propagación de configuración global."""
        from main import prepare_env_for_platform
        
        sample_config_data["global"]["debug"] = True
        sample_config_data["global"]["proxy"]["enabled"] = True
        sample_config_data["global"]["proxy"]["http"] = "http://proxy:8080"
        
        with patch("main.load_config", return_value=sample_config_data):
            env = prepare_env_for_platform("1")
        
        assert env["DEVSECOPS_DEBUG"] == "1"
        assert env["HTTP_PROXY"] == "http://proxy:8080"


class TestEndToEndWorkflows:
    """Tests de flujos end-to-end con mocks."""
    
    @pytest.mark.e2e
    def test_full_azdo_pr_workflow_mock(self):
        """Test E2E: Flujo completo de PRs en AZDO."""
        from mocks.azdo_mock import AZDOMock
        
        azdo_mock = AZDOMock()
        
        # 1. Obtener proyecto
        project = azdo_mock.mock_project_response()
        assert project["state"] == "wellFormed"
        
        # 2. Obtener repositorios
        repo = azdo_mock.mock_repository_response()
        assert repo["defaultBranch"] == "refs/heads/master"
        
        # 3. Obtener PRs
        pr = azdo_mock.mock_pull_request_response(100, "Feature implementation")
        assert pr["targetRefName"] == "refs/heads/master"
        
        # 4. Verificar políticas
        policies = azdo_mock.mock_branch_policy_response("master")
        assert policies["value"][0]["isBlocking"] is True
    
    @pytest.mark.e2e
    def test_full_gcp_deployment_workflow_mock(self):
        """Test E2E: Flujo completo de deployment en GCP."""
        from mocks.gcp_mock import GCPMock
        
        gcp_mock = GCPMock()
        
        # 1. Verificar proyecto
        project = gcp_mock.mock_project_response("my-project")
        assert project["lifecycleState"] == "ACTIVE"
        
        # 2. Verificar cluster GKE
        cluster = gcp_mock.mock_cluster_response("production-cluster")
        assert cluster["status"] == "RUNNING"
        
        # 3. Verificar Cloud Run
        service = gcp_mock.mock_cloud_run_service("api-service")
        assert service["status"]["conditions"][0]["status"] == "True"
    
    @pytest.mark.e2e
    def test_full_aws_infrastructure_workflow_mock(self):
        """Test E2E: Flujo completo de infraestructura AWS."""
        from mocks.aws_mock import AWSMock
        
        aws_mock = AWSMock()
        
        # 1. Verificar identidad
        identity = aws_mock.mock_sts_caller_identity()
        assert identity["Account"] == "123456789012"
        
        # 2. Verificar VPC
        vpc = aws_mock.mock_vpc_response("vpc-prod")
        assert vpc["State"] == "available"
        
        # 3. Verificar instancias EC2
        instance = aws_mock.mock_ec2_instance_response("i-prod-01")
        assert instance["State"]["Name"] == "running"
        
        # 4. Verificar RDS
        rds = aws_mock.mock_rds_instance_response("prod-database")
        assert rds["DBInstanceStatus"] == "available"
