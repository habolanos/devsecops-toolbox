"""
conftest.py - Fixtures y configuración global para pytest

Este archivo proporciona fixtures compartidas para todos los tests del proyecto.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# PATH CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
def pytest_configure(config):
    """Configuración inicial de pytest."""
    # Agregar scm al path para importaciones
    scm_path = Path(__file__).parent.parent / "scm"
    if str(scm_path) not in sys.path:
        sys.path.insert(0, str(scm_path))


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE DIRECTORIOS
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="session")
def project_root() -> Path:
    """Retorna la ruta raíz del proyecto."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def scm_dir(project_root) -> Path:
    """Retorna la ruta del directorio scm."""
    return project_root / "scm"


@pytest.fixture(scope="session")
def tests_dir(project_root) -> Path:
    """Retorna la ruta del directorio de tests."""
    return project_root / "tests"


@pytest.fixture(scope="session")
def fixtures_dir(tests_dir) -> Path:
    """Retorna la ruta del directorio de fixtures."""
    return tests_dir / "fixtures"


@pytest.fixture(scope="session")
def outcome_dir(project_root) -> Path:
    """Retorna la ruta del directorio de resultados."""
    outcome = project_root / "outcome"
    outcome.mkdir(exist_ok=True)
    return outcome


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="session")
def sample_config_data() -> Dict[str, Any]:
    """Retorna datos de configuración de ejemplo válidos."""
    return {
        "azdo": {
            "enabled": True,
            "organization_url": "https://dev.azure.com/test-org",
            "project": "test-project",
            "pat": "test-pat-token-12345",
            "defaults": {
                "timezone": "America/Mazatlan",
                "threads": 4,
                "output_format": "csv"
            }
        },
        "gcp": {
            "enabled": True,
            "project_id": "test-project-123",
            "region": "us-central1",
            "credentials": {
                "type": "adc",
                "service_account_key_path": "",
                "impersonate_service_account": ""
            },
            "kubernetes": {
                "cluster_name": "test-cluster",
                "cluster_region": "us-central1"
            },
            "defaults": {
                "timezone": "America/Mazatlan",
                "output_format": "json"
            }
        },
        "aws": {
            "enabled": True,
            "profile": "test-profile",
            "region": "us-east-1",
            "account_id": "123456789012",
            "credentials": {
                "type": "profile",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "session_token": "",
                "role_arn": ""
            },
            "defaults": {
                "output_format": "json",
                "output_dir": "outcome"
            }
        },
        "global": {
            "debug": False,
            "verbose": False,
            "output_dir": "outcome",
            "log_level": "INFO",
            "proxy": {
                "enabled": False,
                "http": "",
                "https": "",
                "no_proxy": ["localhost", "127.0.0.1"]
            }
        }
    }


@pytest.fixture
def temp_config_file(tmp_path, sample_config_data) -> Generator[Path, None, None]:
    """Crea un archivo de configuración temporal válido."""
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(sample_config_data, f, indent=2)
    yield config_path
    # Limpieza automática por tmp_path


@pytest.fixture
def empty_config_file(tmp_path) -> Generator[Path, None, None]:
    """Crea un archivo de configuración vacío."""
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    yield config_path


@pytest.fixture
def invalid_config_file(tmp_path) -> Generator[Path, None, None]:
    """Crea un archivo de configuración con JSON inválido."""
    config_path = tmp_path / "config.json"
    config_path.write_text("{invalid json", encoding="utf-8")
    yield config_path


@pytest.fixture
def incomplete_config_file(tmp_path) -> Generator[Path, None, None]:
    """Crea un archivo de configuración incompleto (con placeholders)."""
    config_data = {
        "azdo": {
            "enabled": True,
            "organization_url": "https://dev.azure.com/<TU_ORGANIZACION>",
            "project": "<TU_PROYECTO>",
            "pat": "<TU_PAT_TOKEN>"
        },
        "gcp": {
            "enabled": True,
            "project_id": "<TU_PROJECT_ID>",
            "region": "us-central1"
        }
    }
    config_path = tmp_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)
    yield config_path


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Limpia variables de entorno relacionadas con el toolbox antes y después del test."""
    # Guardar variables originales
    env_vars = [
        "AZDO_ORG_URL", "AZDO_PROJECT", "AZDO_PAT", "AZDO_TIMEZONE",
        "GCP_PROJECT_ID", "GCP_REGION", "GOOGLE_APPLICATION_CREDENTIALS",
        "GKE_CLUSTER_NAME", "GKE_CLUSTER_REGION",
        "AWS_PROFILE", "AWS_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN", "AWS_DEFAULT_REGION",
        "DEVSECOPS_DEBUG", "DEVSECOPS_VERBOSE", "DEVSECOPS_OUTPUT_DIR",
        "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"
    ]
    original_values = {var: os.environ.get(var) for var in env_vars}
    
    # Limpiar variables
    for var in env_vars:
        os.environ.pop(var, None)
    
    yield
    
    # Restaurar variables originales
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        else:
            os.environ.pop(var, None)


@pytest.fixture
def mock_azdo_env(clean_env) -> None:
    """Configura variables de entorno mock para Azure DevOps."""
    os.environ["AZDO_ORG_URL"] = "https://dev.azure.com/test-org"
    os.environ["AZDO_PROJECT"] = "test-project"
    os.environ["AZDO_PAT"] = "test-pat-token"
    os.environ["AZDO_TIMEZONE"] = "America/Mazatlan"


@pytest.fixture
def mock_gcp_env(clean_env) -> None:
    """Configura variables de entorno mock para GCP."""
    os.environ["GCP_PROJECT_ID"] = "test-project-123"
    os.environ["GCP_REGION"] = "us-central1"
    os.environ["CLOUDSDK_CORE_PROJECT"] = "test-project-123"
    os.environ["GKE_CLUSTER_NAME"] = "test-cluster"
    os.environ["GKE_CLUSTER_REGION"] = "us-central1"


@pytest.fixture
def mock_aws_env(clean_env) -> None:
    """Configura variables de entorno mock para AWS."""
    os.environ["AWS_PROFILE"] = "test-profile"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_ACCESS_KEY_ID"] = "AKIAIOSFODNN7EXAMPLE"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE MOCKS
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def mock_subprocess_run() -> Generator[MagicMock, None, None]:
    """Mock para subprocess.run."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="mocked output",
            stderr=""
        )
        yield mock_run


@pytest.fixture
def mock_console() -> Generator[MagicMock, None, None]:
    """Mock para Rich Console."""
    with patch("main.console") as mock:
        mock.print = MagicMock()
        yield mock


@pytest.fixture
def mock_rich_available() -> Generator[None, None, None]:
    """Mock para simular que Rich está disponible."""
    with patch("main.RICH_AVAILABLE", True):
        yield


@pytest.fixture
def mock_rich_unavailable() -> Generator[None, None, None]:
    """Mock para simular que Rich no está disponible."""
    with patch("main.RICH_AVAILABLE", False):
        yield


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE DATOS DE RESPUESTA
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def sample_gcp_project_response() -> Dict[str, Any]:
    """Retorna respuesta de ejemplo de GCP Projects API."""
    return {
        "projectId": "test-project-123",
        "projectNumber": "123456789",
        "displayName": "Test Project",
        "lifecycleState": "ACTIVE",
        "createTime": "2024-01-01T00:00:00.000Z"
    }


@pytest.fixture
def sample_azdo_project_response() -> Dict[str, Any]:
    """Retorna respuesta de ejemplo de Azure DevOps Projects API."""
    return {
        "id": "test-project-id",
        "name": "test-project",
        "description": "Test project for unit tests",
        "url": "https://dev.azure.com/test-org/_apis/projects/test-project-id",
        "state": "wellFormed",
        "revision": 1,
        "visibility": "private"
    }


@pytest.fixture
def sample_aws_sts_response() -> Dict[str, Any]:
    """Retorna respuesta de ejemplo de AWS STS GetCallerIdentity."""
    return {
        "UserId": "AIDACKCEVSQ6C2EXAMPLE",
        "Account": "123456789012",
        "Arn": "arn:aws:iam::123456789012:user/test-user"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES DE MARKERS PERSONALIZADOS
# ═══════════════════════════════════════════════════════════════════════════════
def pytest_collection_modifyitems(config, items):
    """Modifica los items de la colección para agregar markers automáticamente."""
    for item in items:
        # Agregar marker unit si no tiene ningún marker de tipo
        if not any(marker.name in ["unit", "integration", "e2e"] for marker in item.own_markers):
            item.add_marker(pytest.mark.unit)


def pytest_runtest_setup(item):
    """Configuración antes de cada test."""
    # Verificar si se requieren credenciales reales
    if "integration" in item.keywords and not os.environ.get("ALLOW_INTEGRATION_TESTS"):
        pytest.skip("Integration tests require ALLOW_INTEGRATION_TESTS environment variable")
    
    if "e2e" in item.keywords and not os.environ.get("ALLOW_E2E_TESTS"):
        pytest.skip("E2E tests require ALLOW_E2E_TESTS environment variable")
