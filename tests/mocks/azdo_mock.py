"""
Mock utilities para Azure DevOps API
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock


class AZDOMock:
    """Mock para APIs de Azure DevOps."""
    
    def __init__(self):
        self.projects = []
        self.repositories = []
        self.pull_requests = []
        self.pipelines = []
        self.releases = []
    
    def mock_project_response(self, 
                            project_id: str = "test-project-id",
                            project_name: str = "test-project") -> Dict[str, Any]:
        """Retorna respuesta mock de proyecto Azure DevOps."""
        return {
            "id": project_id,
            "name": project_name,
            "description": f"Test project {project_name}",
            "url": f"https://dev.azure.com/test-org/_apis/projects/{project_id}",
            "state": "wellFormed",
            "revision": 1,
            "visibility": "private",
            "lastUpdateTime": "2024-01-01T00:00:00.000Z"
        }
    
    def mock_repository_response(self,
                                  repo_id: str = "test-repo-id",
                                  repo_name: str = "test-repo") -> Dict[str, Any]:
        """Retorna respuesta mock de repositorio."""
        return {
            "id": repo_id,
            "name": repo_name,
            "url": f"https://dev.azure.com/test-org/test-project/_apis/git/repositories/{repo_id}",
            "project": {
                "id": "test-project-id",
                "name": "test-project",
                "description": "Test project",
                "url": "https://dev.azure.com/test-org/_apis/projects/test-project-id"
            },
            "defaultBranch": "refs/heads/master",
            "size": 1024000,
            "remoteUrl": f"https://dev.azure.com/test-org/test-project/_git/{repo_name}",
            "sshUrl": f"git@ssh.dev.azure.com:v3/test-org/test-project/{repo_name}",
            "webUrl": f"https://dev.azure.com/test-org/test-project/_git/{repo_name}"
        }
    
    def mock_pull_request_response(self,
                                    pr_id: int = 123,
                                    title: str = "Test PR",
                                    status: str = "active") -> Dict[str, Any]:
        """Retorna respuesta mock de Pull Request."""
        return {
            "pullRequestId": pr_id,
            "codeReviewId": pr_id,
            "status": status,
            "createdBy": {
                "id": "test-user-id",
                "displayName": "Test User",
                "uniqueName": "test.user@example.com",
                "url": "https://dev.azure.com/test-org/_apis/Identities/test-user-id",
                "imageUrl": "https://dev.azure.com/test-org/_api/_common/identityImage?id=test-user-id"
            },
            "creationDate": "2024-01-15T10:30:00.000Z",
            "title": title,
            "description": f"Description for {title}",
            "sourceRefName": "refs/heads/feature/test-branch",
            "targetRefName": "refs/heads/master",
            "mergeStatus": "succeeded",
            "mergeId": f"{pr_id}",
            "lastMergeSourceCommit": {
                "commitId": "abc123def456",
                "url": f"https://dev.azure.com/test-org/test-project/_apis/git/repositories/test-repo/commits/abc123def456"
            },
            "lastMergeTargetCommit": {
                "commitId": "def789abc012",
                "url": f"https://dev.azure.com/test-org/test-project/_apis/git/repositories/test-repo/commits/def789abc012"
            },
            "reviewers": [
                {
                    "reviewerUrl": f"https://dev.azure.com/test-org/test-project/_apis/git/repositories/test-repo/pullRequests/{pr_id}/reviewers/test-user-id",
                    "vote": 5,
                    "id": "test-user-id",
                    "displayName": "Test User",
                    "uniqueName": "test.user@example.com",
                    "isContainer": False
                }
            ],
            "url": f"https://dev.azure.com/test-org/test-project/_apis/git/repositories/test-repo/pullRequests/{pr_id}"
        }
    
    def mock_pipeline_response(self,
                               pipeline_id: int = 1,
                               pipeline_name: str = "test-pipeline") -> Dict[str, Any]:
        """Retorna respuesta mock de Pipeline."""
        return {
            "_links": {
                "self": {"href": f"https://dev.azure.com/test-org/test-project/_apis/pipelines/{pipeline_id}"},
                "web": {"href": f"https://dev.azure.com/test-org/test-project/_build/definition?definitionId={pipeline_id}"}
            },
            "configuration": {
                "type": "yaml",
                "path": "/azure-pipelines.yml",
                "repository": {
                    "id": "test-repo-id",
                    "type": "azureReposGit"
                }
            },
            "url": f"https://dev.azure.com/test-org/test-project/_apis/pipelines/{pipeline_id}?revision=1",
            "id": pipeline_id,
            "name": pipeline_name,
            "folder": "\\"
        }
    
    def mock_release_response(self,
                              release_id: int = 1,
                              release_name: str = "Release-1") -> Dict[str, Any]:
        """Retorna respuesta mock de Release."""
        return {
            "id": release_id,
            "name": release_name,
            "status": "succeeded",
            "createdOn": "2024-01-15T10:30:00.000Z",
            "modifiedOn": "2024-01-15T11:30:00.000Z",
            "createdBy": {
                "id": "test-user-id",
                "displayName": "Test User",
                "uniqueName": "test.user@example.com"
            },
            "modifiedBy": {
                "id": "test-user-id",
                "displayName": "Test User",
                "uniqueName": "test.user@example.com"
            },
            "variables": {},
            "variableGroups": [],
            "environments": [
                {
                    "id": 1,
                    "name": "dev",
                    "status": "succeeded",
                    "variables": {}
                },
                {
                    "id": 2,
                    "name": "qa",
                    "status": "succeeded",
                    "variables": {}
                },
                {
                    "id": 3,
                    "name": "prod",
                    "status": "succeeded",
                    "variables": {},
                    "preDeployApprovals": {
                        "approvals": [
                            {
                                "id": "approval-1",
                                "approver": {
                                    "id": "approver-id",
                                    "displayName": "Release Approver"
                                },
                                "status": "approved"
                            }
                        ]
                    }
                }
            ],
            "artifacts": [
                {
                    "alias": "_test-repo",
                    "instanceReference": {
                        "id": "12345",
                        "name": "20240115.1"
                    }
                }
            ],
            "comment": "",
            "url": f"https://dev.azure.com/test-org/test-project/_apis/Release/releases/{release_id}"
        }
    
    def mock_branch_policy_response(self,
                                    branch_name: str = "master") -> Dict[str, Any]:
        """Retorna respuesta mock de política de rama."""
        return {
            "value": [
                {
                    "id": 1,
                    "type": {
                        "id": "fa4e907d-c16b-4a4c-9dfa-4906e5d171dd",
                        "displayName": "Minimum number of reviewers",
                        "url": "https://dev.azure.com/test-org/test-project/_apis/policy/types/fa4e907d-c16b-4a4c-9dfa-4906e5d171dd"
                    },
                    "revision": 1,
                    "isBlocking": True,
                    "isEnabled": True,
                    "settings": {
                        "minimumApproverCount": 2,
                        "creatorVoteCounts": False,
                        "allowDownvotes": False,
                        "resetOnSourcePush": False
                    },
                    "url": "https://dev.azure.com/test-org/test-project/_apis/policy/configurations/1"
                },
                {
                    "id": 2,
                    "type": {
                        "id": "40e92b21-2e1c-4fc0-8b1d-6f4e5d9c8a7b",
                        "displayName": "Work item linking",
                        "url": "https://dev.azure.com/test-org/test-project/_apis/policy/types/40e92b21-2e1c-4fc0-8b1d-6f4e5d9c8a7b"
                    },
                    "revision": 1,
                    "isBlocking": True,
                    "isEnabled": True,
                    "settings": {
                        "scope": [
                            {
                                "repositoryId": "test-repo-id",
                                "refName": f"refs/heads/{branch_name}",
                                "matchKind": "Exact"
                            }
                        ]
                    },
                    "url": "https://dev.azure.com/test-org/test-project/_apis/policy/configurations/2"
                }
            ],
            "count": 2
        }
    
    def mock_build_response(self,
                           build_id: int = 1,
                           build_number: str = "20240115.1") -> Dict[str, Any]:
        """Retorna respuesta mock de Build."""
        return {
            "_links": {
                "self": {"href": f"https://dev.azure.com/test-org/test-project/_apis/build/Builds/{build_id}"},
                "web": {"href": f"https://dev.azure.com/test-org/test-project/_build/results?buildId={build_id}"}
            },
            "id": build_id,
            "buildNumber": build_number,
            "status": "completed",
            "result": "succeeded",
            "queueTime": "2024-01-15T10:00:00.000Z",
            "startTime": "2024-01-15T10:05:00.000Z",
            "finishTime": "2024-01-15T10:30:00.000Z",
            "definition": {
                "id": 1,
                "name": "test-pipeline",
                "url": "https://dev.azure.com/test-org/test-project/_apis/build/Definitions/1"
            },
            "project": {
                "id": "test-project-id",
                "name": "test-project",
                "url": "https://dev.azure.com/test-org/_apis/projects/test-project-id"
            },
            "uri": f"vstfs:///Build/Build/{build_id}",
            "sourceBranch": "refs/heads/master",
            "sourceVersion": "abc123def456",
            "reason": "manual",
            "requestedFor": {
                "id": "test-user-id",
                "displayName": "Test User",
                "uniqueName": "test.user@example.com"
            }
        }
    
    def mock_error_response(self, status_code: int = 401, message: str = "Unauthorized") -> Dict[str, Any]:
        """Retorna respuesta de error de Azure DevOps API."""
        return {
            "$id": "1",
            "innerException": None,
            "message": message,
            "typeName": "Microsoft.TeamFoundation.Core.WebApi.ProjectDoesNotExistException",
            "typeKey": "ProjectDoesNotExistException",
            "errorCode": status_code,
            "eventId": 3000
        }
    
    def mock_empty_list_response(self) -> Dict[str, Any]:
        """Retorna respuesta de lista vacía."""
        return {
            "value": [],
            "count": 0
        }


class AZDORequestMock:
    """Mock para requests HTTP a Azure DevOps API."""
    
    BASE_URL = "https://dev.azure.com/test-org"
    API_VERSION = "6.0"
    
    def __init__(self, pat: str = "test-pat-token"):
        self.pat = pat
        self.auth_header = self._create_auth_header()
        self.responses = {}
        self._setup_default_responses()
    
    def _create_auth_header(self) -> str:
        """Crea header de autenticación básica."""
        import base64
        credentials = f":{self.pat}"
        return f"Basic {base64.b64encode(credentials.encode()).decode()}"
    
    def _setup_default_responses(self):
        """Configura respuestas mock por defecto."""
        azdo_mock = AZDOMock()
        
        self.responses = {
            "GET /_apis/projects": {
                "status": 200,
                "json": {
                    "value": [azdo_mock.mock_project_response()],
                    "count": 1
                }
            },
            "GET /test-project/_apis/git/repositories": {
                "status": 200,
                "json": {
                    "value": [azdo_mock.mock_repository_response()],
                    "count": 1
                }
            },
            "GET /test-project/_apis/git/pullrequests": {
                "status": 200,
                "json": {
                    "value": [azdo_mock.mock_pull_request_response()],
                    "count": 1
                }
            },
            "GET /test-project/_apis/pipelines": {
                "status": 200,
                "json": {
                    "value": [azdo_mock.mock_pipeline_response()],
                    "count": 1
                }
            },
            "GET /test-project/_apis/release/releases": {
                "status": 200,
                "json": {
                    "value": [azdo_mock.mock_release_response()],
                    "count": 1
                }
            },
            "GET /test-project/_apis/policy/configurations": {
                "status": 200,
                "json": azdo_mock.mock_branch_policy_response()
            },
            "GET /test-project/_apis/build/builds": {
                "status": 200,
                "json": {
                    "value": [azdo_mock.mock_build_response()],
                    "count": 1
                }
            }
        }
    
    def get_response(self, method: str, endpoint: str, **kwargs) -> tuple:
        """Retorna respuesta mock para request."""
        key = f"{method} {endpoint}"
        
        # Buscar coincidencia exacta o parcial
        response = self.responses.get(key)
        if response:
            return (response["status"], response["json"])
        
        # Buscar coincidencia parcial
        for pattern, resp in self.responses.items():
            if endpoint in pattern or pattern.replace("GET ", "").replace("POST ", "") in endpoint:
                return (resp["status"], resp["json"])
        
        # Default: 404
        return (404, {"message": "Not found"})


def mock_ado_connection(mock_connection_class, project_name: str = "test-project"):
    """Crea mock de ADO Connection para azdo tools."""
    mock_conn = MagicMock()
    mock_conn.base_url = f"https://dev.azure.com/test-org"
    mock_conn.last_used_project = project_name
    mock_conn.last_used_org = "test-org"
    
    # Mock clients
    mock_conn.clients = MagicMock()
    mock_conn.clients.get_git_client.return_value = MagicMock()
    mock_conn.clients.get_build_client.return_value = MagicMock()
    mock_conn.clients.get_release_client.return_value = MagicMock()
    mock_conn.clients.get_core_client.return_value = MagicMock()
    
    # Configurar comportamiento
    mock_git = mock_conn.clients.get_git_client.return_value
    mock_git.get_repositories.return_value = [
        MagicMock(id="test-repo-id", name="test-repo", web_url="https://dev.azure.com/test-org/test-project/_git/test-repo")
    ]
    
    return mock_conn
