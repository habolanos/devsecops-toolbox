#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — scm/terminal/tools.py

Verifica que el menú de Terminal Tools registre correctamente los scripts,
incluida la opción 8 (Setup Entorno DevOps con install-devops-tools.sh).
"""

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent  # scm/
sys.path.insert(0, str(_PROJECT_ROOT.parent))


def _import_module(module_path):
    """Importa módulos tolerando dependencias opcionales faltantes."""
    try:
        return importlib.import_module(module_path)
    except SystemExit:
        return None
    except Exception:
        pass
    try:
        parts = module_path.split('.')
        rel_path = Path(*parts[:-1]) / (parts[-1] + '.py')
        full_path = _PROJECT_ROOT / rel_path
        if full_path.exists():
            spec = importlib.util.spec_from_file_location(module_path, full_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except SystemExit:
        return None
    except Exception:
        pass
    return None


terminal_tools = _import_module("scm.terminal.tools")
cert_tools = _import_module("scm.terminal.operation_update_certs_on_gke_gcp.tools")

requires_tools = pytest.mark.skipif(
    terminal_tools is None, reason="terminal/tools.py requiere dependencias"
)
requires_cert_tools = pytest.mark.skipif(
    cert_tools is None, reason="operation_update_certs_on_gke_gcp/tools.py requiere dependencias"
)


@requires_tools
class TestSetupEntornoDevOpsOption:
    def test_opcion_8_registrada(self):
        assert "8" in terminal_tools.SCRIPTS

    def test_opcion_8_apunta_a_install_devops_tools(self):
        script = terminal_tools.SCRIPTS["8"]
        assert script["path"] == "operation_setup_initial/install-devops-tools.sh"
        assert script["type"] == "shell"
        assert script["status"] == "ready"
        assert script["args"] == []

    def test_script_existe_en_disco(self):
        script_path = terminal_tools.BASE_DIR / terminal_tools.SCRIPTS["8"]["path"]
        assert script_path.exists(), f"No existe: {script_path}"

    def test_script_es_bash_con_shebang(self):
        script_path = terminal_tools.BASE_DIR / terminal_tools.SCRIPTS["8"]["path"]
        first_line = script_path.read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("#!") and "bash" in first_line

    def test_todos_los_scripts_tienen_archivo(self):
        """Cada opción del menú (excepto sistema/Q) debe apuntar a un archivo real."""
        for key, script in terminal_tools.SCRIPTS.items():
            if key.startswith("_") or key == "Q":
                continue
            path = terminal_tools.BASE_DIR / script["path"]
            assert path.exists(), f"Opción {key} ({script['name']}): falta {path}"


@requires_tools
class TestScmInspectionOption:
    def test_opcion_10_registrada(self):
        assert "10" in terminal_tools.SCRIPTS

    def test_opcion_10_apunta_a_inspection_errors(self):
        script = terminal_tools.SCRIPTS["10"]
        assert script["path"] == "azdo_check_scm_inspection/inspection_errors.sh"
        assert script["type"] == "shell"
        assert script["status"] == "ready"
        assert script["args"] == ["inspection"]

    def test_script_existe_y_es_bash(self):
        path = terminal_tools.BASE_DIR / terminal_tools.SCRIPTS["10"]["path"]
        assert path.exists(), f"No existe: {path}"
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("#!") and "bash" in first_line

    def test_script_sintaxis_bash_valida(self):
        import shutil
        import subprocess
        bash = shutil.which("bash")
        if not bash:
            pytest.skip("bash no disponible en este entorno")
        path = terminal_tools.BASE_DIR / terminal_tools.SCRIPTS["10"]["path"]
        result = subprocess.run([bash, "-n", str(path)], capture_output=True)
        assert result.returncode == 0, result.stderr.decode()

    def test_script_resuelve_outcome_y_config_azdo(self):
        """El script debe usar outcome resuelto y leer credenciales de config.json."""
        path = terminal_tools.BASE_DIR / terminal_tools.SCRIPTS["10"]["path"]
        content = path.read_text(encoding="utf-8")
        assert "DEVSECOPS_OUTPUT_DIR" in content
        assert "global.output_dir" in content
        assert "OUTCOME_DIR" in content
        assert ".azdo.pat" in content
        assert "scm/config.json" in content

    def test_env_prepara_credenciales_azdo(self, monkeypatch):
        """prepare_env_from_config inyecta AZDO_* desde config.json (sin pisar env)."""
        monkeypatch.setattr(terminal_tools, "load_config",
                            lambda: {"azdo": {"pat": "tok", "organization": "MyOrg",
                                              "project": "MyProj"}})
        env = terminal_tools.prepare_env_from_config()
        assert env["AZDO_PAT"] == "tok"
        assert env["AZDO_ORG"] == "MyOrg"
        assert env["AZDO_PROJECT"] == "MyProj"

    def test_env_azdo_no_pisa_env_existente(self, monkeypatch):
        monkeypatch.setenv("AZDO_PAT", "env-pat")
        monkeypatch.setattr(terminal_tools, "load_config",
                            lambda: {"azdo": {"pat": "cfg-pat"}})
        env = terminal_tools.prepare_env_from_config()
        assert env["AZDO_PAT"] == "env-pat"


@requires_tools
class TestCertManagerMenuEntry:
    def test_opcion_9_registrada(self):
        assert "9" in terminal_tools.SCRIPTS

    def test_opcion_9_es_python_submenu(self):
        script = terminal_tools.SCRIPTS["9"]
        assert script["type"] == "python"
        assert script["path"] == "operation_update_certs_on_gke_gcp/tools.py"
        assert script["status"] == "ready"

    def test_submenu_existe_en_disco(self):
        path = terminal_tools.BASE_DIR / terminal_tools.SCRIPTS["9"]["path"]
        assert path.exists(), f"No existe: {path}"


@requires_cert_tools
class TestCertManagerTools:
    def test_operaciones_registradas(self):
        for key in ("1", "2", "3", "4", "Q"):
            assert key in cert_tools.OPERATIONS

    def test_operaciones_shell_apuntan_a_scripts_reales(self):
        for key in ("1", "2", "3"):
            op = cert_tools.OPERATIONS[key]
            path = cert_tools.BASE_DIR / op["path"]
            assert path.exists(), f"Operación {key}: falta {path}"
            assert op["path"].endswith(".sh")

    def test_opcion_4_es_verificacion_prereqs(self):
        assert cert_tools.OPERATIONS["4"]["action"] == "prereqs"
        assert cert_tools.OPERATIONS["4"]["path"] is None

    def test_archivo_base_default_definido_y_gitignored(self):
        """El archivo base contiene llave privada: existe como default local,
        pero nunca debe versionarse (cubierto por .gitignore)."""
        assert cert_tools.DEFAULT_BASE_CERT.endswith((".yml", ".yaml"))
        gitignore = (cert_tools.BASE_DIR.parents[2] / ".gitignore").read_text(
            encoding="utf-8"
        )
        assert "operation_update_certs_on_gke_gcp" in gitignore

    def test_backup_script_salida_en_outcome_global(self):
        """El script de backup debe resolver el outcome global (env > config.json > scm/outcome)."""
        content = (cert_tools.BASE_DIR / "cert_backup_and_renew_tls_certs.sh").read_text(
            encoding="utf-8"
        )
        assert "DEVSECOPS_OUTPUT_DIR" in content
        assert "global.output_dir" in content
        assert "RUN_OUTCOME" in content
        assert "certs-${RUN_ID}" in content

    def test_resolve_outcome_dir_fallback(self):
        """Sin DEVSECOPS_OUTPUT_DIR debe resolver bajo scm/ usando config.json."""
        import os
        saved = os.environ.pop("DEVSECOPS_OUTPUT_DIR", None)
        try:
            resolved = cert_tools.resolve_outcome_dir()
            assert str(cert_tools.SCM_ROOT) in resolved
            assert resolved.endswith("outcome")
        finally:
            if saved is not None:
                os.environ["DEVSECOPS_OUTPUT_DIR"] = saved

    def test_resolve_outcome_dir_env_tiene_prioridad(self):
        import os
        os.environ["DEVSECOPS_OUTPUT_DIR"] = "C:\\tmp\\custom_outcome"
        try:
            assert cert_tools.resolve_outcome_dir() == "C:\\tmp\\custom_outcome"
        finally:
            os.environ.pop("DEVSECOPS_OUTPUT_DIR", None)
