"""
Tests para el pipeline de inventario GCP (opción 2 - tool 22) y los helpers
de configuración global en scm/utils.py:

- resolve_outcome_dir: DEVSECOPS_OUTPUT_DIR > config.json global.output_dir > scm/outcome
- global_flag: DEVSECOPS_<NAME> env > config.json global.<name>
- is_live_terminal: isatty() o TTY_COMPATIBLE=1 (relay del launcher)
- log_command: escribe en <outcome>/commands_YYYYMMDD.log si log_commands activo
- _run_with_spinner (gcp tools.py): propaga TTY_COMPATIBLE/DEVSECOPS_* al hijo
"""

import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import pytest

SCM_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCM_DIR))

import utils  # noqa: E402

GCP_DIR = SCM_DIR / "gcp"
INVENTORY_DIR = GCP_DIR / "inventory"


def _load_module(name: str, path: Path):
    """Carga un .py por ruta (los nombres con guiones no son importables)."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class _FakeStdout:
    """stdout simulado para controlar isatty() en _run_with_spinner."""

    def __init__(self, tty: bool):
        self._tty = tty
        self.written = []

    def isatty(self):
        return self._tty

    def write(self, s):
        self.written.append(s)

    def flush(self):
        pass


# ═══════════════════════════════════════════════════════════════════════════
# scm/utils.py — helpers de config global
# ═══════════════════════════════════════════════════════════════════════════

class TestResolveOutcomeDir:
    def test_env_takes_precedence(self, monkeypatch, tmp_path):
        """DEVSECOPS_OUTPUT_DIR manda sobre config.json."""
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path / "custom"))
        assert utils.resolve_outcome_dir() == (tmp_path / "custom").resolve()

    def test_config_output_dir_relative(self, monkeypatch, tmp_path):
        """global.output_dir relativo se resuelve bajo scm/."""
        monkeypatch.delenv("DEVSECOPS_OUTPUT_DIR", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"global": {"output_dir": "mi_salida"}}))
        monkeypatch.setattr(utils, "SCM_CONFIG_FILE", cfg)
        expected = (utils.SCM_ROOT / "mi_salida").resolve()
        assert utils.resolve_outcome_dir() == expected

    def test_config_output_dir_absolute(self, monkeypatch, tmp_path):
        """global.output_dir absoluto se usa tal cual."""
        monkeypatch.delenv("DEVSECOPS_OUTPUT_DIR", raising=False)
        target = tmp_path / "abs" / "out"
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"global": {"output_dir": str(target)}}))
        monkeypatch.setattr(utils, "SCM_CONFIG_FILE", cfg)
        assert utils.resolve_outcome_dir() == target.resolve()

    def test_default_scm_outcome(self, monkeypatch, tmp_path):
        """Sin env ni config → scm/<default>."""
        monkeypatch.delenv("DEVSECOPS_OUTPUT_DIR", raising=False)
        monkeypatch.setattr(utils, "SCM_CONFIG_FILE", tmp_path / "nope.json")
        assert utils.resolve_outcome_dir() == (utils.SCM_ROOT / "outcome").resolve()


class TestGlobalFlag:
    def test_env_truthy(self, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_DEBUG", "1")
        assert utils.global_flag("debug") is True

    def test_env_falsy(self, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_DEBUG", "0")
        assert utils.global_flag("debug") is False

    def test_config_fallback(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DEVSECOPS_VERBOSE", raising=False)
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"global": {"verbose": True}}))
        monkeypatch.setattr(utils, "SCM_CONFIG_FILE", cfg)
        assert utils.global_flag("verbose") is True

    def test_missing_everything(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DEVSECOPS_DEBUG", raising=False)
        monkeypatch.setattr(utils, "SCM_CONFIG_FILE", tmp_path / "nope.json")
        assert utils.global_flag("debug") is False


class TestIsLiveTerminal:
    def test_real_tty(self, monkeypatch):
        monkeypatch.setattr(sys, "stdout", _FakeStdout(tty=True))
        monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
        assert utils.is_live_terminal() is True

    def test_forced_terminal_in_pipe(self, monkeypatch):
        """TTY_COMPATIBLE=1 (lo inyecta el launcher con TTY) habilita animación."""
        monkeypatch.setattr(sys, "stdout", _FakeStdout(tty=False))
        monkeypatch.setenv("TTY_COMPATIBLE", "1")
        assert utils.is_live_terminal() is True

    def test_forced_off(self, monkeypatch):
        monkeypatch.setattr(sys, "stdout", _FakeStdout(tty=False))
        monkeypatch.setenv("TTY_COMPATIBLE", "0")
        assert utils.is_live_terminal() is False

    def test_plain_pipe(self, monkeypatch):
        monkeypatch.setattr(sys, "stdout", _FakeStdout(tty=False))
        monkeypatch.delenv("TTY_COMPATIBLE", raising=False)
        assert utils.is_live_terminal() is False


class TestLogCommand:
    def test_writes_log_when_enabled(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEVSECOPS_LOG_COMMANDS", "1")
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        utils.log_command(["gcloud", "projects", "list"])
        logs = list(tmp_path.glob("commands_*.log"))
        assert len(logs) == 1
        content = logs[0].read_text(encoding="utf-8")
        assert "gcloud projects list" in content
        assert "[GCP]" in content and "[EXEC]" in content

    def test_noop_when_disabled(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEVSECOPS_LOG_COMMANDS", "0")
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"global": {"log_commands": False}}))
        monkeypatch.setattr(utils, "SCM_CONFIG_FILE", cfg)
        utils.log_command(["gcloud", "projects", "list"])
        assert not list(tmp_path.glob("commands_*.log"))

    def test_config_fallback_enables_logging(self, monkeypatch, tmp_path):
        """log_commands=true en config.json activa el log aun sin env var."""
        monkeypatch.delenv("DEVSECOPS_LOG_COMMANDS", raising=False)
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"global": {"log_commands": True}}))
        monkeypatch.setattr(utils, "SCM_CONFIG_FILE", cfg)
        utils.log_command(["kubectl", "get", "pods"])
        assert len(list(tmp_path.glob("commands_*.log"))) == 1


# ═══════════════════════════════════════════════════════════════════════════
# generar-inventario-csv.py
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def csv_mod(monkeypatch, tmp_path):
    """Módulo generar-inventario-csv cargado con outcome aislado en tmp."""
    monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
    mod = _load_module("generar_inventario_csv_test",
                       INVENTORY_DIR / "generar-inventario-csv.py")
    return mod


class TestInventoryCsvScript:
    def test_outcome_dir_honors_env(self, csv_mod, tmp_path):
        """OUTCOME_DIR se resuelve desde DEVSECOPS_OUTPUT_DIR, no hardcode."""
        assert csv_mod.OUTCOME_DIR == tmp_path.resolve()

    def test_run_cmd_logs_command(self, csv_mod, monkeypatch):
        calls = []
        monkeypatch.setattr(csv_mod, "log_command",
                            lambda cmd, status="EXEC", platform_name="GCP":
                            calls.append((status, " ".join(cmd))))

        fake = types.SimpleNamespace(returncode=0, stdout="out", stderr="")
        monkeypatch.setattr(csv_mod.subprocess, "run",
                            lambda *a, **k: fake)
        assert csv_mod.run_cmd(["gcloud", "x"]) == "out"
        assert ("EXEC", "gcloud x") in calls

    def test_run_cmd_logs_error_status(self, csv_mod, monkeypatch):
        calls = []
        monkeypatch.setattr(csv_mod, "log_command",
                            lambda cmd, status="EXEC", platform_name="GCP":
                            calls.append(status))
        fake = types.SimpleNamespace(returncode=2, stdout="", stderr="boom")
        monkeypatch.setattr(csv_mod.subprocess, "run",
                            lambda *a, **k: fake)
        assert csv_mod.run_cmd(["kubectl", "x"]) == ""
        assert "ERROR" in calls

    def test_run_cmd_timeout_logs(self, csv_mod, monkeypatch):
        import subprocess as sp
        calls = []
        monkeypatch.setattr(csv_mod, "log_command",
                            lambda cmd, status="EXEC", platform_name="GCP":
                            calls.append(status))

        def _timeout(*a, **k):
            raise sp.TimeoutExpired(cmd="x", timeout=300)
        monkeypatch.setattr(csv_mod.subprocess, "run", _timeout)
        assert csv_mod.run_cmd(["gcloud", "y"]) == ""
        assert "TIMEOUT" in calls

    def test_header_fallback_shows_outcome_dir(self, csv_mod, capsys):
        out_dir = Path("salida_x_test")
        csv_mod.print_header_fallback(["proj-1"], [], ";", 4, False, out_dir)
        out = capsys.readouterr().out
        assert str(out_dir) in out
        assert "outcome/" not in out

    def test_summary_fallback_shows_outcome_dir(self, csv_mod, capsys):
        out_dir = Path("salida_y_test")
        csv_mod.print_summary_fallback([{"project": "p", "steps": {}, "time": 1}],
                                       1.5, 4, out_dir)
        out = capsys.readouterr().out
        assert str(out_dir) in out

    def test_global_flag_fallback_exists(self, csv_mod, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_DEBUG", "1")
        assert csv_mod.global_flag("debug") is True

    def test_fallback_import_resolves_scm_root(self, monkeypatch):
        """Sin `utils` importable, el fallback resuelve bajo scm/ (no scm/gcp)."""
        monkeypatch.setitem(sys.modules, "utils", None)  # fuerza ImportError
        monkeypatch.delenv("DEVSECOPS_OUTPUT_DIR", raising=False)
        mod = _load_module("generar_inventario_csv_fb",
                           INVENTORY_DIR / "generar-inventario-csv.py")
        # scm/config.json define global.output_dir="outcome" → scm/outcome
        assert mod.OUTCOME_DIR == (SCM_DIR / "outcome").resolve()


# ═══════════════════════════════════════════════════════════════════════════
# run_inventory.py + combinar-a-excel.py
# ═══════════════════════════════════════════════════════════════════════════

class TestRunInventory:
    def test_ensure_output_env_sets_var(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DEVSECOPS_OUTPUT_DIR", raising=False)
        mod = _load_module("run_inventory_test",
                           INVENTORY_DIR / "run_inventory.py")
        out = mod.ensure_output_env()
        assert os.environ["DEVSECOPS_OUTPUT_DIR"] == str(out)
        assert out.exists()

    def test_ensure_output_env_keeps_existing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        mod = _load_module("run_inventory_test2",
                           INVENTORY_DIR / "run_inventory.py")
        assert mod.ensure_output_env() == tmp_path.resolve()
        assert os.environ["DEVSECOPS_OUTPUT_DIR"] == str(tmp_path)

    def test_excel_script_uses_resolved_outcome(self):
        """El consolidador lee/escribe en el outcome resuelto (no hardcode)."""
        content = (INVENTORY_DIR /
                   "generar-inventario-csv-combinar-a-excel.py").read_text(
                       encoding="utf-8")
        assert "OUTCOME_DIR = resolve_outcome_dir()" in content
        assert 'SCRIPT_DIR / "outcome"' not in content
        assert "OUTPUT_EXCEL = OUTCOME_DIR" in content


# ═══════════════════════════════════════════════════════════════════════════
# scm/gcp/tools.py — _run_with_spinner y registro del tool 22
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def gcp_tools():
    return _load_module("gcp_tools_launcher_inv", GCP_DIR / "tools.py")


class _FakeReader:
    """Stream binario tipo FileIO: devuelve chunks por read1/read."""

    def __init__(self, chunks):
        self._chunks = list(chunks)

    def read1(self, _n=-1):
        return self._chunks.pop(0) if self._chunks else b""

    def read(self, n=-1):
        return self.read1(n)


class _FakeProc:
    """Popen simulado: captura kwargs y expone stdout binario."""

    captured = {}
    chunks = [b"linea de salida\n"]

    def __init__(self, cmd, **kwargs):
        _FakeProc.captured = {"cmd": cmd, **kwargs}
        self.stdout = _FakeReader(_FakeProc.chunks)
        self.returncode = 0

    def wait(self):
        return self.returncode


class TestRunWithSpinner:
    def test_force_terminal_when_tty(self, gcp_tools, monkeypatch):
        """Con TTY real, el hijo recibe TTY_COMPATIBLE=1 → Rich anima vía relay."""
        monkeypatch.setattr(gcp_tools.subprocess, "Popen", _FakeProc)
        monkeypatch.setattr(sys, "stdout", _FakeStdout(tty=True))
        monkeypatch.delenv("DEVSECOPS_OUTPUT_DIR", raising=False)

        gcp_tools._run_with_spinner(["python", "x.py"])

        env = _FakeProc.captured["env"]
        assert env["TTY_COMPATIBLE"] == "1"
        assert "DEVSECOPS_OUTPUT_DIR" in env  # propagado desde config global

    def test_no_force_terminal_in_pipe(self, gcp_tools, monkeypatch):
        """Sin TTY (CI/archivo), TTY_COMPATIBLE=0 → salida estática limpia."""
        monkeypatch.setattr(gcp_tools.subprocess, "Popen", _FakeProc)
        monkeypatch.setattr(sys, "stdout", _FakeStdout(tty=False))

        gcp_tools._run_with_spinner(["python", "x.py"])

        assert _FakeProc.captured["env"]["TTY_COMPATIBLE"] == "0"

    def test_existing_output_env_preserved(self, gcp_tools, monkeypatch):
        """DEVSECOPS_OUTPUT_DIR ya inyectado por main.py no se sobrescribe."""
        monkeypatch.setattr(gcp_tools.subprocess, "Popen", _FakeProc)
        monkeypatch.setattr(sys, "stdout", _FakeStdout(tty=True))
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", "D:/pre")

        gcp_tools._run_with_spinner(["python", "x.py"])

        assert _FakeProc.captured["env"]["DEVSECOPS_OUTPUT_DIR"] == "D:/pre"

    def test_carriage_return_frames_relayed(self, gcp_tools, monkeypatch):
        """Frames ANSI con \\r sin \\n se retransmiten (regresion 'colgado').

        Antes: 'for line in proc.stdout' esperaba \\n, asi que los frames
        redibujados con \\r (Rich Live) quedaban retenidos y la pantalla
        parecia congelada en 'Cargando herramienta...'.
        """
        out = _FakeStdout(tty=True)
        _FakeProc.chunks = [b"\x1b[2K\rframe-sin-newline", b"fin\n"]
        monkeypatch.setattr(gcp_tools.subprocess, "Popen", _FakeProc)
        monkeypatch.setattr(sys, "stdout", out)
        try:
            gcp_tools._run_with_spinner(["python", "x.py"])
        finally:
            _FakeProc.chunks = [b"linea de salida\n"]

        emitted = "".join(out.written)
        assert "frame-sin-newline" in emitted
        assert "fin\n" in emitted

    def test_spinner_shown_when_tty(self, gcp_tools, monkeypatch):
        """Con TTY se muestra el spinner animado 'Cargando herramienta'."""
        out = _FakeStdout(tty=True)
        _FakeProc.chunks = []  # sin output: el spinner queda activo hasta EOF
        monkeypatch.setattr(gcp_tools.subprocess, "Popen", _FakeProc)
        monkeypatch.setattr(sys, "stdout", out)
        try:
            gcp_tools._run_with_spinner(["python", "x.py"])
        finally:
            _FakeProc.chunks = [b"linea de salida\n"]

        assert any("Cargando herramienta" in s for s in out.written)

    def test_loading_message_in_pipe(self, gcp_tools, monkeypatch):
        """Sin TTY se muestra el mensaje estatico de carga."""
        out = _FakeStdout(tty=False)
        monkeypatch.setattr(gcp_tools.subprocess, "Popen", _FakeProc)
        monkeypatch.setattr(sys, "stdout", out)

        gcp_tools._run_with_spinner(["python", "x.py"])

        assert any("Cargando herramienta" in s for s in out.written)


class TestToolRegistration:
    def test_tool_22_inventory_registered(self, gcp_tools):
        """La opción 2 de inventario sigue apuntando a run_inventory.py."""
        tool = gcp_tools.TOOLS.get("22")
        assert tool is not None
        assert tool["path"].endswith("run_inventory.py")
        assert tool["group"] == "inventory"

    def test_tool_2_multi_project_registered(self, gcp_tools):
        """La opción 2 (deployments) soporta --multi-project y está registrada.

        Regresión: con ALL/equipo (>1 proyecto) el launcher caía en el bucle
        por-proyecto y `args.index("--project")` lanzaba ValueError porque
        args solo contenía ['--multi-project', 'p1,...'].
        """
        assert "gke_deployments_report" in gcp_tools.MULTI_PROJECT_PARAM_SCRIPTS
        assert "--multi-project" in gcp_tools.TOOLS["2"]["args"]

    def test_every_multi_project_tool_registered(self, gcp_tools):
        """Toda tool con --multi-project en args debe estar en el set PARAM.

        Si falta, el bucle por-proyecto asume '--project' en args y crashea.
        """
        for key, tool in gcp_tools.TOOLS.items():
            stem = os.path.splitext(os.path.basename(tool.get("path", "")))[0]
            if "--multi-project" in tool.get("args", []):
                assert stem in gcp_tools.MULTI_PROJECT_PARAM_SCRIPTS, \
                    f"tool {key} ({stem}) declara --multi-project pero no está en MULTI_PROJECT_PARAM_SCRIPTS"
