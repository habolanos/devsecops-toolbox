"""
Mock utilities para APIs de Google Cloud Platform
"""

import json
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock


class GCPMock:
    """Mock para servicios de Google Cloud Platform."""
    
    def __init__(self):
        self.projects = []
        self.clusters = []
        self.instances = []
        self.buckets = []
        self.service_accounts = []
    
    def mock_project_response(self, project_id: str = "test-project-123") -> Dict[str, Any]:
        """Retorna respuesta mock de proyecto GCP."""
        return {
            "projectId": project_id,
            "projectNumber": "123456789",
            "displayName": "Test Project",
            "lifecycleState": "ACTIVE",
            "createTime": "2024-01-01T00:00:00.000Z",
            "labels": {"env": "test", "team": "devops"}
        }
    
    def mock_cluster_response(self, 
                              cluster_name: str = "test-cluster",
                              project_id: str = "test-project-123") -> Dict[str, Any]:
        """Retorna respuesta mock de cluster GKE."""
        return {
            "name": cluster_name,
            "description": "Test GKE Cluster",
            "initialNodeCount": 3,
            "nodeConfig": {
                "machineType": "e2-medium",
                "diskSizeGb": 100,
                "oauthScopes": ["https://www.googleapis.com/auth/cloud-platform"]
            },
            "status": "RUNNING",
            "endpoint": "35.184.123.45",
            "locations": ["us-central1-a", "us-central1-b", "us-central1-c"],
            "network": f"projects/{project_id}/global networks/default",
            "subnetwork": f"projects/{project_id}/regions/us-central1/subnetworks/default",
            "currentMasterVersion": "1.27.3-gke.100",
            "currentNodeVersion": "1.27.3-gke.100",
            "resourceLabels": {"env": "test"}
        }
    
    def mock_instance_response(self,
                               instance_name: str = "test-instance",
                               project_id: str = "test-project-123") -> Dict[str, Any]:
        """Retorna respuesta mock de instancia Compute."""
        return {
            "id": "123456789",
            "name": instance_name,
            "machineType": f"projects/{project_id}/zones/us-central1-a/machineTypes/e2-medium",
            "status": "RUNNING",
            "zone": f"projects/{project_id}/zones/us-central1-a",
            "networkInterfaces": [{
                "network": f"projects/{project_id}/global/networks/default",
                "subnetwork": f"projects/{project_id}/regions/us-central1/subnetworks/default",
                "networkIP": "10.128.0.2",
                "accessConfigs": [{
                    "type": "ONE_TO_ONE_NAT",
                    "name": "External NAT",
                    "natIP": "35.192.123.45"
                }]
            }],
            "tags": {"items": ["http-server", "https-server"]},
            "labels": {"env": "test"},
            "metadata": {
                "items": [
                    {"key": "startup-script", "value": "#!/bin/bash echo Hello"}
                ]
            },
            "creationTimestamp": "2024-01-01T00:00:00.000-08:00"
        }
    
    def mock_service_account_response(self,
                                      account_id: str = "test-sa",
                                      project_id: str = "test-project-123") -> Dict[str, Any]:
        """Retorna respuesta mock de Service Account."""
        return {
            "name": f"projects/{project_id}/serviceAccounts/{account_id}@{project_id}.iam.gserviceaccount.com",
            "projectId": project_id,
            "uniqueId": "123456789012345678901",
            "email": f"{account_id}@{project_id}.iam.gserviceaccount.com",
            "displayName": "Test Service Account",
            "oauth2ClientId": "123456789012345678901",
            "disabled": False
        }
    
    def mock_bucket_response(self, bucket_name: str = "test-bucket") -> Dict[str, Any]:
        """Retorna respuesta mock de Cloud Storage bucket."""
        return {
            "kind": "storage#bucket",
            "id": bucket_name,
            "selfLink": f"https://www.googleapis.com/storage/v1/b/{bucket_name}",
            "name": bucket_name,
            "timeCreated": "2024-01-01T00:00:00.000Z",
            "updated": "2024-01-01T00:00:00.000Z",
            "metageneration": "1",
            "location": "US-CENTRAL1",
            "storageClass": "STANDARD",
            "etag": "CAE=",
            "labels": {"env": "test"},
            "iamConfiguration": {
                "uniformBucketLevelAccess": {"enabled": True}
            }
        }
    
    def mock_cloud_run_service(self, service_name: str = "test-service") -> Dict[str, Any]:
        """Retorna respuesta mock de Cloud Run service."""
        return {
            "apiVersion": "serving.knative.dev/v1",
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": "test-project-123",
                "creationTimestamp": "2024-01-01T00:00:00Z",
                "generation": 1,
                "labels": {"env": "test"}
            },
            "spec": {
                "template": {
                    "spec": {
                        "containerConcurrency": 1000,
                        "timeoutSeconds": 300,
                        "serviceAccountName": "test-sa@test-project-123.iam.gserviceaccount.com",
                        "containers": [{
                            "image": "gcr.io/test-project-123/test-image:v1.0.0",
                            "ports": [{"containerPort": 8080}],
                            "resources": {
                                "limits": {"cpu": "1000m", "memory": "512Mi"}
                            }
                        }]
                    }
                }
            },
            "status": {
                "observedGeneration": 1,
                "conditions": [{"type": "Ready", "status": "True"}],
                "url": f"https://{service_name}-abc123-uc.a.run.app",
                "address": {"url": f"https://{service_name}-abc123-uc.a.run.app"}
            }
        }
    
    def mock_error_response(self, status: int = 404, message: str = "Not found") -> Dict[str, Any]:
        """Retorna respuesta de error de GCP API."""
        return {
            "error": {
                "code": status,
                "message": message,
                "status": "NOT_FOUND" if status == 404 else "ERROR"
            }
        }
    
    def create_mock_client(self) -> MagicMock:
        """Crea un cliente mock de GCP."""
        mock_client = MagicMock()
        
        # Mock projects
        mock_projects = MagicMock()
        mock_projects.list.return_value.execute.return_value = {
            "projects": [self.mock_project_response()]
        }
        mock_client.projects.return_value = mock_projects
        
        # Mock compute instances
        mock_instances = MagicMock()
        mock_instances.list.return_value.execute.return_value = {
            "items": [self.mock_instance_response()]
        }
        mock_client.instances.return_value = mock_instances
        
        return mock_client


def mock_gcloud_command(command: List[str], returncode: int = 0, 
                        stdout: str = "", stderr: str = "") -> tuple:
    """Genera respuesta mock para comando gcloud."""
    return (returncode, stdout, stderr)


class GCPCommandMock:
    """Mock para comandos gcloud CLI."""
    
    COMMON_COMMANDS = {
        "config get-value project": (0, "test-project-123\n", ""),
        "config get-value account": (0, "test-user@example.com\n", ""),
        "projects list": (0, """PROJECT_ID          NAME              PROJECT_NUMBER
test-project-123    Test Project      123456789
another-project     Another Project   987654321
""", ""),
        "container clusters list": (0, """NAME          LOCATION      MASTER_VERSION  MASTER_IP      MACHINE_TYPE  NODE_VERSION    NUM_NODES  STATUS
test-cluster  us-central1   1.27.3-gke.100  35.184.123.45  e2-medium     1.27.3-gke.100  3          RUNNING
""", ""),
        "compute instances list": (0, """NAME           ZONE           MACHINE_TYPE   INTERNAL_IP  EXTERNAL_IP    STATUS
test-instance  us-central1-a  e2-medium      10.128.0.2   35.192.123.45  RUNNING
""", ""),
    }
    
    def get_command_response(self, command: str) -> tuple:
        """Retorna respuesta mock para comando gcloud."""
        for cmd_pattern, response in self.COMMON_COMMANDS.items():
            if cmd_pattern in command:
                return response
        
        # Default response
        return (0, "", "")
    
    def mock_subprocess_run(self, mock_run: MagicMock, command: str = None) -> None:
        """Configura mock de subprocess.run para comandos gcloud."""
        returncode, stdout, stderr = self.get_command_response(command or "")
        
        mock_run.return_value = MagicMock(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr
        )
