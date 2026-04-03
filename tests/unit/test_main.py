"""
Tests unitarios para main.py - Launcher principal
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Asegurar que main.py está importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scm"))


class TestLoadConfig:
    """Tests para la función load_config()."""

    @pytest.mark.unit
    def test_load_config_success(self, tmp_path, sample_config_data):
        """Test: Cargar configuración válida exitosamente."""
        from main import load_config, _config
        
        # Limpiar cache
        import main
        main._config = None
        
        # Crear archivo de config temporal
        config_path = tmp_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(sample_config_data, f)
        
        # Parchar la ruta del config
        with patch("main.CONFIG_FILE", config_path):
            result = load_config()
        
        assert result is not None
        assert result["azdo"]["project"] == "test-project"
        assert result["gcp"]["project_id"] == "test-project-123"
        assert result["aws"]["region"] == "us-east-1"

    @pytest.mark.unit
    def test_load_config_file_not_exists(self):
        """Test: Retornar None cuando el archivo no existe."""
        from main import load_config
        
        # Limpiar cache
        import main
        main._config = None
        
        # Parchar con ruta inexistente
        with patch("main.CONFIG_FILE", Path("/nonexistent/path/config.json")):
            result = load_config()
        
        assert result is None

    @pytest.mark.unit
    def test_load_config_invalid_json(self, tmp_path):
        """Test: Manejar JSON inválido correctamente."""
        from main import load_config
        
        # Limpiar cache
        import main
        main._config = None
        
        # Crear archivo con JSON inválido
        config_path = tmp_path / "config.json"
        config_path.write_text("{invalid json", encoding="utf-8")
        
        with patch("main.CONFIG_FILE", config_path):
            result = load_config()
        
        assert result is None

    @pytest.mark.unit
    def test_load_config_uses_cache(self, tmp_path, sample_config_data):
        """Test: Usar cache en llamadas subsiguientes."""
        from main import load_config
        
        # Limpiar cache
        import main
        main._config = sample_config_data  # Simular cache
        
        # No debería intentar leer el archivo
        with patch("builtins.open") as mock_open:
            result = load_config()
            mock_open.assert_not_called()
        
        assert result == sample_config_data


class TestGetPlatformConfig:
    """Tests para get_platform_config()."""

    @pytest.mark.unit
    def test_get_azdo_config(self, sample_config_data):
        """Test: Obtener configuración de AZDO."""
        from main import get_platform_config
        
        with patch("main.load_config", return_value=sample_config_data):
            result = get_platform_config("2")  # AZDO es "2"
        
        assert result is not None
        assert result["organization_url"] == "https://dev.azure.com/test-org"
        assert result["pat"] == "test-pat-token-12345"

    @pytest.mark.unit
    def test_get_gcp_config(self, sample_config_data):
        """Test: Obtener configuración de GCP."""
        from main import get_platform_config
        
        with patch("main.load_config", return_value=sample_config_data):
            result = get_platform_config("1")  # GCP es "1"
        
        assert result is not None
        assert result["project_id"] == "test-project-123"
        assert result["region"] == "us-central1"

    @pytest.mark.unit
    def test_get_aws_config(self, sample_config_data):
        """Test: Obtener configuración de AWS."""
        from main import get_platform_config
        
        with patch("main.load_config", return_value=sample_config_data):
            result = get_platform_config("3")  # AWS es "3"
        
        assert result is not None
        assert result["profile"] == "test-profile"
        assert result["region"] == "us-east-1"

    @pytest.mark.unit
    def test_get_config_no_config(self):
        """Test: Retornar None cuando no hay configuración."""
        from main import get_platform_config
        
        with patch("main.load_config", return_value=None):
            result = get_platform_config("1")
        
        assert result is None

    @pytest.mark.unit
    def test_get_config_invalid_key(self, sample_config_data):
        """Test: Retornar None para clave de plataforma inválida."""
        from main import get_platform_config
        
        with patch("main.load_config", return_value=sample_config_data):
            result = get_platform_config("invalid")
        
        assert result is None


class TestIsPlatformConfigured:
    """Tests para is_platform_configured()."""

    @pytest.mark.unit
    def test_azdo_configured(self, sample_config_data):
        """Test: AZDO configurado correctamente."""
        from main import is_platform_configured
        
        with patch("main.load_config", return_value=sample_config_data):
            result = is_platform_configured("2")
        
        assert result is True

    @pytest.mark.unit
    def test_azdo_not_configured_placeholder(self):
        """Test: AZDO no configurado (tiene placeholders)."""
        from main import is_platform_configured
        
        config = {
            "azdo": {
                "enabled": True,
                "organization_url": "https://dev.azure.com/<TU_ORGANIZACION>",
                "pat": "<TU_PAT_TOKEN>"
            }
        }
        
        with patch("main.load_config", return_value=config):
            result = is_platform_configured("2")
        
        assert result is False

    @pytest.mark.unit
    def test_azdo_disabled(self):
        """Test: AZDO deshabilitado."""
        from main import is_platform_configured
        
        config = {
            "azdo": {
                "enabled": False,
                "organization_url": "https://dev.azure.com/test",
                "pat": "valid-token"
            }
        }
        
        with patch("main.load_config", return_value=config):
            result = is_platform_configured("2")
        
        assert result is False

    @pytest.mark.unit
    def test_gcp_configured(self, sample_config_data):
        """Test: GCP configurado correctamente."""
        from main import is_platform_configured
        
        with patch("main.load_config", return_value=sample_config_data):
            result = is_platform_configured("1")
        
        assert result is True

    @pytest.mark.unit
    def test_gcp_not_configured_placeholder(self):
        """Test: GCP no configurado (tiene placeholders)."""
        from main import is_platform_configured
        
        config = {
            "gcp": {
                "enabled": True,
                "project_id": "<TU_PROJECT_ID>"
            }
        }
        
        with patch("main.load_config", return_value=config):
            result = is_platform_configured("1")
        
        assert result is False

    @pytest.mark.unit
    def test_aws_configured_profile(self, sample_config_data):
        """Test: AWS configurado con profile."""
        from main import is_platform_configured
        
        with patch("main.load_config", return_value=sample_config_data):
            result = is_platform_configured("3")
        
        assert result is True

    @pytest.mark.unit
    def test_aws_configured_keys(self):
        """Test: AWS configurado con access keys."""
        from main import is_platform_configured
        
        config = {
            "aws": {
                "enabled": True,
                "credentials": {
                    "type": "keys",
                    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                    "secret_access_key": "secret123"
                }
            }
        }
        
        with patch("main.load_config", return_value=config):
            result = is_platform_configured("3")
        
        assert result is True

    @pytest.mark.unit
    def test_aws_not_configured_missing_keys(self):
        """Test: AWS no configurado (faltan keys)."""
        from main import is_platform_configured
        
        config = {
            "aws": {
                "enabled": True,
                "credentials": {
                    "type": "keys",
                    "access_key_id": "",
                    "secret_access_key": ""
                }
            }
        }
        
        with patch("main.load_config", return_value=config):
            result = is_platform_configured("3")
        
        assert result is False


class TestPrepareEnvForPlatform:
    """Tests para prepare_env_for_platform()."""

    @pytest.mark.unit
    def test_prepare_azdo_env(self, sample_config_data, clean_env):
        """Test: Preparar variables de entorno para AZDO."""
        from main import prepare_env_for_platform
        
        with patch("main.load_config", return_value=sample_config_data):
            env = prepare_env_for_platform("2")
        
        assert env["AZDO_ORG_URL"] == "https://dev.azure.com/test-org"
        assert env["AZDO_PROJECT"] == "test-project"
        assert env["AZDO_PAT"] == "test-pat-token-12345"
        assert env["AZDO_TIMEZONE"] == "America/Mazatlan"

    @pytest.mark.unit
    def test_prepare_gcp_env(self, sample_config_data, clean_env):
        """Test: Preparar variables de entorno para GCP."""
        from main import prepare_env_for_platform
        
        with patch("main.load_config", return_value=sample_config_data):
            env = prepare_env_for_platform("1")
        
        assert env["GCP_PROJECT_ID"] == "test-project-123"
        assert env["GCP_REGION"] == "us-central1"
        assert env["CLOUDSDK_CORE_PROJECT"] == "test-project-123"
        assert env["GKE_CLUSTER_NAME"] == "test-cluster"

    @pytest.mark.unit
    def test_prepare_aws_env(self, sample_config_data, clean_env):
        """Test: Preparar variables de entorno para AWS."""
        from main import prepare_env_for_platform
        
        with patch("main.load_config", return_value=sample_config_data):
            env = prepare_env_for_platform("3")
        
        assert env["AWS_PROFILE"] == "test-profile"
        assert env["AWS_REGION"] == "us-east-1"
        assert env["AWS_DEFAULT_REGION"] == "us-east-1"

    @pytest.mark.unit
    def test_prepare_env_with_global_settings(self, sample_config_data, clean_env):
        """Test: Incluir configuración global en variables de entorno."""
        from main import prepare_env_for_platform
        
        sample_config_data["global"]["debug"] = True
        sample_config_data["global"]["verbose"] = True
        sample_config_data["global"]["output_dir"] = "custom_output"
        
        with patch("main.load_config", return_value=sample_config_data):
            env = prepare_env_for_platform("1")
        
        assert env["DEVSECOPS_DEBUG"] == "1"
        assert env["DEVSECOPS_VERBOSE"] == "1"
        assert env["DEVSECOPS_OUTPUT_DIR"] == "custom_output"

    @pytest.mark.unit
    def test_prepare_env_with_proxy(self, sample_config_data, clean_env):
        """Test: Configurar variables de proxy."""
        from main import prepare_env_for_platform
        
        sample_config_data["global"]["proxy"] = {
            "enabled": True,
            "http": "http://proxy.example.com:8080",
            "https": "https://proxy.example.com:8080",
            "no_proxy": ["localhost", "127.0.0.1", "internal.example.com"]
        }
        
        with patch("main.load_config", return_value=sample_config_data):
            env = prepare_env_for_platform("1")
        
        assert env["HTTP_PROXY"] == "http://proxy.example.com:8080"
        assert env["HTTPS_PROXY"] == "https://proxy.example.com:8080"
        assert env["NO_PROXY"] == "localhost,127.0.0.1,internal.example.com"

    @pytest.mark.unit
    def test_prepare_env_preserves_existing(self, sample_config_data):
        """Test: Preservar variables de entorno existentes."""
        from main import prepare_env_for_platform
        
        # Establecer variable previa
        os.environ["PRE_EXISTING_VAR"] = "should_remain"
        
        with patch("main.load_config", return_value=sample_config_data):
            env = prepare_env_for_platform("1")
        
        assert env["PRE_EXISTING_VAR"] == "should_remain"


class TestGetConfigStatus:
    """Tests para get_config_status()."""

    @pytest.mark.unit
    def test_all_configured(self, sample_config_data):
        """Test: Todas las plataformas configuradas."""
        from main import get_config_status
        
        with patch("main.load_config", return_value=sample_config_data):
            with patch("main.is_platform_configured", return_value=True):
                result = get_config_status()
        
        assert result["1"] == "configured"
        assert result["2"] == "configured"
        assert result["3"] == "configured"

    @pytest.mark.unit
    def test_no_config(self):
        """Test: Sin archivo de configuración."""
        from main import get_config_status
        
        with patch("main.load_config", return_value=None):
            result = get_config_status()
        
        assert result["1"] == "no_config"
        assert result["2"] == "no_config"
        assert result["3"] == "no_config"

    @pytest.mark.unit
    def test_mixed_status(self, sample_config_data):
        """Test: Estado mixto de configuración."""
        from main import get_config_status
        
        def mock_is_configured(key):
            return key == "1"  # Solo GCP configurado
        
        with patch("main.load_config", return_value=sample_config_data):
            with patch("main.is_platform_configured", side_effect=mock_is_configured):
                result = get_config_status()
        
        assert result["1"] == "configured"
        assert result["2"] == "incomplete"
        assert result["3"] == "incomplete"


class TestLaunchPlatform:
    """Tests para launch_platform()."""

    @pytest.mark.unit
    def test_launch_configured_platform(self, sample_config_data, mock_subprocess_run):
        """Test: Lanzar plataforma configurada."""
        from main import launch_platform
        
        with patch("main.load_config", return_value=sample_config_data):
            with patch("main.is_platform_configured", return_value=True):
                with patch("main.BASE_DIR", Path("/fake/path")):
                    launch_platform("1")
        
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]
        assert "gcp/tools.py" in call_args[1]

    @pytest.mark.unit
    def test_exit_option(self):
        """Test: Opción de salida termina el programa."""
        from main import launch_platform
        
        with pytest.raises(SystemExit) as exc_info:
            launch_platform("Q")
        
        assert exc_info.value.code == 0

    @pytest.mark.unit
    def test_invalid_platform(self):
        """Test: Plataforma inválida muestra error."""
        from main import launch_platform
        
        # No debería lanzar excepción, solo mostrar mensaje
        launch_platform("999")
        # La función imprime mensaje de error y retorna


class TestShowConfigDetails:
    """Tests para show_config_details()."""

    @pytest.mark.unit
    def test_show_details_with_config(self, sample_config_data, capsys):
        """Test: Mostrar detalles con configuración existente."""
        from main import show_config_details
        
        with patch("main.load_config", return_value=sample_config_data):
            with patch("main.is_platform_configured", return_value=True):
                with patch("builtins.input"):  # Mock input
                    show_config_details()
        
        captured = capsys.readouterr()
        # Verificar que se muestra información de configuración
        assert "Configuración" in captured.out or "GCP" in captured.out or "AZDO" in captured.out or "AWS" in captured.out

    @pytest.mark.unit
    def test_show_details_no_config(self, capsys):
        """Test: Mostrar detalles sin configuración."""
        from main import show_config_details
        
        with patch("main.load_config", return_value=None):
            with patch("builtins.input"):
                show_config_details()
        
        captured = capsys.readouterr()
        # Verificar mensaje de que no hay config
        assert "config.json" in captured.out.lower() or "No se encontró" in captured.out


class TestEdgeCases:
    """Tests para casos edge y manejo de errores."""

    @pytest.mark.unit
    def test_load_config_permission_error(self, tmp_path):
        """Test: Manejar error de permisos al leer config."""
        from main import load_config
        
        import main
        main._config = None
        
        config_path = tmp_path / "config.json"
        config_path.write_text('{"test": "data"}')
        
        with patch("main.CONFIG_FILE", config_path):
            with patch("builtins.open", side_effect=PermissionError("Access denied")):
                result = load_config()
        
        assert result is None

    @pytest.mark.unit
    def test_unicode_in_config(self, tmp_path):
        """Test: Manejar caracteres unicode en configuración."""
        from main import load_config
        
        import main
        main._config = None
        
        config_with_unicode = {
            "azdo": {
                "organization_url": "https://dev.azure.com/测试组织",
                "project": "Proyecto Español Ñ"
            }
        }
        
        config_path = tmp_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_with_unicode, f, ensure_ascii=False)
        
        with patch("main.CONFIG_FILE", config_path):
            result = load_config()
        
        assert result is not None
        assert "测试组织" in result["azdo"]["organization_url"]

    @pytest.mark.unit
    def test_empty_strings_in_config(self):
        """Test: Manejar strings vacíos en configuración."""
        from main import is_platform_configured
        
        config = {
            "azdo": {
                "enabled": True,
                "organization_url": "",
                "pat": ""
            }
        }
        
        with patch("main.load_config", return_value=config):
            result = is_platform_configured("2")
        
        assert result is False
