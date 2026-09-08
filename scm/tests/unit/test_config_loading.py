"""
Pruebas unitarias para verificación de carga de configuración desde scm/config.json

Verifica que los programas:
- health-probe-masive
- pipeline_cd_clone
- pipeline_cd_update_release
- pipeline_updater
- tools.py (launcher unificado)

carguen correctamente scm/config.json y usen global.output_dir.
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Asegurar que scm/ está en el path
SCM_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCM_DIR))


# ─── Fixtures ────────────────────────────────────────────────────────────────

SAMPLE_CONFIG = {
    "global": {
        "output_dir": "outcome",
        "log_level": "INFO",
    },
    "azdo": {
        "organization_url": "https://dev.azure.com/TestOrg",
        "project": "TestProject",
        "pat": "test-pat-token",
    }
}


@pytest.fixture
def temp_config():
    """Crea un config.json temporal en scm/ y restaura el original después."""
    config_path = SCM_DIR / "config.json"
    original_content = None
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(SAMPLE_CONFIG, f)
    yield config_path
    if original_content is not None:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
    else:
        config_path.unlink()


# ─── pipeline_cd_update_release ──────────────────────────────────────────────

class TestPipelineCdUpdateReleaseConfig:
    """Tests para pipeline_cd_update_release.load_config()"""

    def test_load_config_returns_dict(self, temp_config):
        """load_config() debe retornar un diccionario con las claves correctas."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_cd_update_release"))
        try:
            import importlib
            mod = importlib.import_module("pipeline_cd_update_release")
            importlib.reload(mod)
            config = mod.load_config()
            assert isinstance(config, dict)
            assert config.get('organization') == 'TestOrg'
            assert config.get('project') == 'TestProject'
            assert config.get('pat') == 'test-pat-token'
        finally:
            sys.path.pop()

    def test_load_config_includes_output_dir(self, temp_config):
        """load_config() debe incluir output_dir desde global.output_dir."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_cd_update_release"))
        try:
            import importlib
            mod = importlib.import_module("pipeline_cd_update_release")
            importlib.reload(mod)
            config = mod.load_config()
            assert 'output_dir' in config
            assert 'outcome' in config['output_dir']
        finally:
            sys.path.pop()

    def test_output_dir_is_absolute(self, temp_config):
        """output_dir debe resolverse a una ruta absoluta."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_cd_update_release"))
        try:
            import importlib
            mod = importlib.import_module("pipeline_cd_update_release")
            importlib.reload(mod)
            config = mod.load_config()
            output_dir = Path(config['output_dir'])
            assert output_dir.is_absolute()
        finally:
            sys.path.pop()

    def test_module_output_dir_variable(self, temp_config):
        """_OUTPUT_DIR debe estar actualizado después de load_config()."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_cd_update_release"))
        try:
            import importlib
            mod = importlib.import_module("pipeline_cd_update_release")
            importlib.reload(mod)
            mod.load_config()
            assert mod._OUTPUT_DIR != "outcome"
            assert Path(mod._OUTPUT_DIR).is_absolute()
        finally:
            sys.path.pop()

    def test_config_file_path_is_correct(self, temp_config):
        """El path del config.json debe ser scm/config.json (3 niveles arriba)."""
        script_path = SCM_DIR / "azdo" / "pipeline_cd_update_release" / "pipeline_cd_update_release.py"
        expected_config = script_path.parent.parent.parent / "config.json"
        assert expected_config == SCM_DIR / "config.json"


# ─── health-probe-masive ─────────────────────────────────────────────────────

class TestHealthProbeMasiveConfig:
    """Tests para health-probe-masive/config.py"""

    def test_config_loads_azdo_settings(self, temp_config):
        """config.py debe cargar AZDO_ORG, AZDO_PROJECT, AZDO_PAT desde config.json."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "health-probe-masive"))
        try:
            import importlib
            mod = importlib.import_module("config")
            importlib.reload(mod)
            assert mod.AZDO_ORG == "TestOrg"
            assert mod.AZDO_PROJECT == "TestProject"
            assert mod.AZDO_PAT == "test-pat-token"
        finally:
            sys.path.pop()

    def test_output_dir_uses_global_output_dir(self, temp_config):
        """OUTPUT_DIR debe basarse en global.output_dir de config.json."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "health-probe-masive"))
        try:
            import importlib
            mod = importlib.import_module("config")
            importlib.reload(mod)
            assert "health_probe" in mod.OUTPUT_DIR
            assert Path(mod.OUTPUT_DIR).is_absolute() or mod.OUTPUT_DIR.startswith(str(SCM_DIR))
        finally:
            sys.path.pop()

    def test_env_var_overrides_config(self, temp_config):
        """OUTPUT_DIR env var debe tener prioridad sobre config.json."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "health-probe-masive"))
        try:
            with patch.dict(os.environ, {"OUTPUT_DIR": "/tmp/custom_output"}):
                import importlib
                mod = importlib.import_module("config")
                importlib.reload(mod)
                assert mod.OUTPUT_DIR == "/tmp/custom_output"
        finally:
            sys.path.pop()

    def test_log_file_in_output_dir(self, temp_config):
        """LOG_FILE debe estar dentro de OUTPUT_DIR."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "health-probe-masive"))
        try:
            import importlib
            mod = importlib.import_module("config")
            importlib.reload(mod)
            assert mod.LOG_FILE.startswith(mod.OUTPUT_DIR)
        finally:
            sys.path.pop()


# ─── pipeline_updater ────────────────────────────────────────────────────────

class TestPipelineUpdaterConfig:
    """Tests para pipeline_updater/config.py"""

    def test_load_config_returns_dict(self, temp_config):
        """load_config() debe retornar un diccionario con las claves correctas."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_updater"))
        try:
            import importlib
            mod = importlib.import_module("config")
            importlib.reload(mod)
            config = mod.load_config()
            assert isinstance(config, dict)
            assert config.get('organization') == 'TestOrg'
            assert config.get('project') == 'TestProject'
            assert config.get('pat') == 'test-pat-token'
        finally:
            sys.path.pop()

    def test_load_config_includes_output_dir(self, temp_config):
        """load_config() debe incluir output_dir desde global.output_dir."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_updater"))
        try:
            import importlib
            mod = importlib.import_module("config")
            importlib.reload(mod)
            config = mod.load_config()
            assert 'output_dir' in config
            assert 'outcome' in config['output_dir']
        finally:
            sys.path.pop()

    def test_output_dir_is_absolute(self, temp_config):
        """output_dir debe resolverse a una ruta absoluta."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_updater"))
        try:
            import importlib
            mod = importlib.import_module("config")
            importlib.reload(mod)
            config = mod.load_config()
            assert Path(config['output_dir']).is_absolute()
        finally:
            sys.path.pop()

    def test_snapshot_dir_uses_global_output_dir(self, temp_config):
        """SNAPSHOT_DIR debe basarse en global.output_dir."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_updater"))
        try:
            import importlib
            mod = importlib.import_module("config")
            importlib.reload(mod)
            assert "snapshots" in mod.SNAPSHOT_DIR
            assert Path(mod.SNAPSHOT_DIR).is_absolute()
        finally:
            sys.path.pop()

    def test_report_dir_uses_global_output_dir(self, temp_config):
        """REPORT_DIR debe basarse en global.output_dir."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_updater"))
        try:
            import importlib
            mod = importlib.import_module("config")
            importlib.reload(mod)
            assert "pipeline_updates" in mod.REPORT_DIR
            assert Path(mod.REPORT_DIR).is_absolute()
        finally:
            sys.path.pop()

    def test_log_dir_uses_global_output_dir(self, temp_config):
        """LOG_DIR debe basarse en global.output_dir."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_updater"))
        try:
            import importlib
            mod = importlib.import_module("config")
            importlib.reload(mod)
            assert "logs" in mod.LOG_DIR
            assert Path(mod.LOG_DIR).is_absolute()
        finally:
            sys.path.pop()

    def test_config_file_path_is_correct(self, temp_config):
        """El path del config.json debe ser scm/config.json (3 niveles arriba)."""
        script_path = SCM_DIR / "azdo" / "pipeline_updater" / "config.py"
        expected_config = script_path.parent.parent.parent / "config.json"
        assert expected_config == SCM_DIR / "config.json"


# ─── pipeline_cd_clone (ya funcionaba, verificar que sigue) ──────────────────

class TestPipelineCdCloneConfig:
    """Tests para pipeline_cd_clone.load_config() - ya funcionaba correctamente"""

    def test_load_config_returns_dict(self, temp_config):
        """load_config() debe retornar un diccionario con las claves correctas."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_cd_clone"))
        try:
            import importlib
            mod = importlib.import_module("pipeline_cd_clone")
            importlib.reload(mod)
            config = mod.load_config()
            assert isinstance(config, dict)
            assert config.get('organization') == 'TestOrg'
            assert config.get('project') == 'TestProject'
            assert config.get('pat') == 'test-pat-token'
        finally:
            sys.path.pop()

    def test_load_config_includes_output_dir(self, temp_config):
        """load_config() debe incluir output_dir desde global.output_dir."""
        sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_cd_clone"))
        try:
            import importlib
            mod = importlib.import_module("pipeline_cd_clone")
            importlib.reload(mod)
            config = mod.load_config()
            assert 'output_dir' in config
            assert 'outcome' in config['output_dir']
        finally:
            sys.path.pop()

    def test_config_file_path_is_correct(self, temp_config):
        """El path del config.json debe ser scm/config.json (3 niveles arriba)."""
        script_path = SCM_DIR / "azdo" / "pipeline_cd_clone" / "pipeline_cd_clone.py"
        expected_config = script_path.parent.parent.parent / "config.json"
        assert expected_config == SCM_DIR / "config.json"


# ─── Sin config.json (fallback) ──────────────────────────────────────────────

class TestConfigFallback:
    """Tests de fallback cuando config.json no existe"""

    def test_pipeline_updater_load_config_empty_without_file(self):
        """load_config() debe retornar dict vacío si config.json no existe."""
        config_path = SCM_DIR / "config.json"
        original_content = None
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            config_path.unlink()
        try:
            sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_updater"))
            import importlib
            mod = importlib.import_module("config")
            importlib.reload(mod)
            config = mod.load_config()
            assert config == {}
        finally:
            sys.path.pop()
            if original_content is not None:
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)

    def test_pipeline_cd_update_release_load_config_empty_without_file(self):
        """load_config() debe retornar dict vacío si config.json no existe."""
        config_path = SCM_DIR / "config.json"
        original_content = None
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            config_path.unlink()
        try:
            sys.path.insert(0, str(SCM_DIR / "azdo" / "pipeline_cd_update_release"))
            import importlib
            mod = importlib.import_module("pipeline_cd_update_release")
            importlib.reload(mod)
            config = mod.load_config()
            assert config == {}
        finally:
            sys.path.pop()
            if original_content is not None:
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)


# ─── Tests para tools.py _OUTPUT_DIR ─────────────────────────────────────────

class TestToolsPyOutputDir:
    """Verifica que tools.py resuelva _OUTPUT_DIR desde config.json."""

    def test_tools_py_output_dir_resolved(self):
        """tools.py debe tener _OUTPUT_DIR apuntando a SCM_ROOT/output_dir."""
        sys.path.insert(0, str(SCM_DIR / "azdo"))
        try:
            import importlib
            mod = importlib.import_module("tools")
            importlib.reload(mod)
            assert hasattr(mod, "_OUTPUT_DIR")
            assert "outcome" in mod._OUTPUT_DIR.lower()
        finally:
            sys.path.pop()

    def test_tools_py_output_dir_uses_config(self, temp_config):
        """_OUTPUT_DIR debe reflejar global.output_dir de config.json."""
        config_path = SCM_DIR / "config.json"
        original_content = None
        if config_path.exists():
            original_content = config_path.read_text(encoding="utf-8")
        test_config = {
            "global": {"output_dir": "custom_output"},
            "azdo": {
                "organization_url": "https://dev.azure.com/TestOrg",
                "project": "TestProject",
                "pat": "test-pat-12345",
            },
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(test_config, f)
        try:
            sys.path.insert(0, str(SCM_DIR / "azdo"))
            import importlib
            mod = importlib.import_module("tools")
            importlib.reload(mod)
            assert "custom_output" in mod._OUTPUT_DIR
        finally:
            sys.path.pop()
            if original_content is not None:
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(original_content)

    def test_tools_py_defaults_use_output_dir(self):
        """TOOLS defaults para 23, 24, 42, 43 deben usar _OUTPUT_DIR."""
        sys.path.insert(0, str(SCM_DIR / "azdo"))
        try:
            import importlib
            mod = importlib.import_module("tools")
            importlib.reload(mod)
            output_dir = mod._OUTPUT_DIR
            for key in ("23", "24", "42"):
                defaults = mod.TOOLS[key].get("defaults", {})
                backup_path = defaults.get("backup_path", "")
                assert "outcome" in backup_path.lower() or "custom" in backup_path.lower(), \
                    f"Tool {key} backup_path should reference output_dir, got: {backup_path}"
            clone_defaults = mod.TOOLS["43"].get("defaults", {})
            clone_backup = clone_defaults.get("backup_path", "")
            assert "clone" in clone_backup, \
                f"Tool 43 backup_path should include 'clone', got: {clone_backup}"
        finally:
            sys.path.pop()

    def test_tools_py_fallback_no_config(self):
        """Si config.json no existe, _OUTPUT_DIR debe ser SCM_ROOT/outcome."""
        config_path = SCM_DIR / "config.json"
        original_content = None
        if config_path.exists():
            original_content = config_path.read_text(encoding="utf-8")
            config_path.unlink()
        try:
            sys.path.insert(0, str(SCM_DIR / "azdo"))
            import importlib
            mod = importlib.import_module("tools")
            importlib.reload(mod)
            assert mod._OUTPUT_DIR.endswith("outcome")
        finally:
            sys.path.pop()
            if original_content is not None:
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(original_content)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
