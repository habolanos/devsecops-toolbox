#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Requisitos funcionales de scm/dashboard y scm/kpi_analyzer
Cubre: resolución de credenciales/webhook/cron desde config.json,
imports tolerantes a dependencias opcionales ausentes, y requirements.txt.
"""

import json
import sys
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SCM_DIR = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = SCM_DIR / "dashboard"
KPI_DIR = SCM_DIR / "kpi_analyzer"
sys.path.insert(0, str(SCM_DIR))


def _load_module(name: str, path: Path):
    """Carga un módulo por path sin importar el paquete."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def common():
    """dashboard_common aislado con config temporal."""
    mod = _load_module("dashboard_common_test", DASHBOARD_DIR / "dashboard_common.py")
    yield mod


@pytest.fixture()
def cfg_file(tmp_path, common, monkeypatch):
    """Redirige SCM_CONFIG_FILE a un config.json temporal."""
    cfg = tmp_path / "config.json"
    monkeypatch.setattr(common, "SCM_CONFIG_FILE", cfg)
    return cfg


class TestResolveCredentials:
    """Orden de precedencia: CLI > env > config.json."""

    def test_cli_args_win_over_env_and_config(self, common, cfg_file, monkeypatch):
        cfg_file.write_text(json.dumps({
            "azdo": {"organization": "cfg-org", "project": "cfg-proj", "pat": "cfg-pat"}
        }))
        monkeypatch.setenv("AZDO_ORG", "env-org")
        monkeypatch.setenv("AZDO_PROJECT", "env-proj")
        monkeypatch.setenv("AZDO_PAT", "env-pat")
        org, project, pat = common.resolve_credentials("cli-org", "cli-proj", "cli-pat")
        assert (org, project, pat) == ("cli-org", "cli-proj", "cli-pat")

    def test_env_wins_over_config(self, common, cfg_file, monkeypatch):
        cfg_file.write_text(json.dumps({
            "azdo": {"organization": "cfg-org", "project": "cfg-proj", "pat": "cfg-pat"}
        }))
        monkeypatch.setenv("AZDO_ORG", "env-org")
        monkeypatch.setenv("AZDO_PROJECT", "env-proj")
        monkeypatch.setenv("AZDO_PAT", "env-pat")
        org, project, pat = common.resolve_credentials()
        assert (org, project, pat) == ("env-org", "env-proj", "env-pat")

    def test_config_fallback(self, common, cfg_file, monkeypatch):
        cfg_file.write_text(json.dumps({
            "azdo": {"organization": "cfg-org", "project": "cfg-proj", "pat": "cfg-pat"}
        }))
        monkeypatch.delenv("AZDO_ORG", raising=False)
        monkeypatch.delenv("AZDO_PROJECT", raising=False)
        monkeypatch.delenv("AZDO_PAT", raising=False)
        org, project, pat = common.resolve_credentials()
        assert (org, project, pat) == ("cfg-org", "cfg-proj", "cfg-pat")

    def test_organization_url_fallback(self, common, cfg_file, monkeypatch):
        cfg_file.write_text(json.dumps({
            "azdo": {"organization_url": "https://dev.azure.com/myorg",
                     "project": "cfg-proj", "pat": "cfg-pat"}
        }))
        for var in ("AZDO_ORG", "AZDO_PROJECT", "AZDO_PAT"):
            monkeypatch.delenv(var, raising=False)
        org, _, _ = common.resolve_credentials()
        assert org == "https://dev.azure.com/myorg"

    def test_no_config_returns_empty(self, common, cfg_file, monkeypatch):
        for var in ("AZDO_ORG", "AZDO_PROJECT", "AZDO_PAT"):
            monkeypatch.delenv(var, raising=False)
        org, project, pat = common.resolve_credentials()
        assert (org, project, pat) == ("", "", "")

    def test_mixed_resolution(self, common, cfg_file, monkeypatch):
        """CLI para org, env para project, config para pat."""
        cfg_file.write_text(json.dumps({"azdo": {"pat": "cfg-pat"}}))
        monkeypatch.delenv("AZDO_ORG", raising=False)
        monkeypatch.setenv("AZDO_PROJECT", "env-proj")
        monkeypatch.delenv("AZDO_PAT", raising=False)
        org, project, pat = common.resolve_credentials(org="cli-org")
        assert (org, project, pat) == ("cli-org", "env-proj", "cfg-pat")


class TestResolveWebhook:
    """Orden: CLI > TEAMS_WEBHOOK_URL > config.json."""

    def test_cli_wins(self, common, cfg_file, monkeypatch):
        monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://env-hook")
        assert common.resolve_webhook("https://cli-hook") == "https://cli-hook"

    def test_env_fallback(self, common, cfg_file, monkeypatch):
        monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://env-hook")
        assert common.resolve_webhook() == "https://env-hook"

    def test_config_dashboard_webhook(self, common, cfg_file, monkeypatch):
        monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
        cfg_file.write_text(json.dumps({
            "dashboard": {"webhook_url": "https://cfg-hook"}
        }))
        assert common.resolve_webhook() == "https://cfg-hook"

    def test_config_notifications_teams(self, common, cfg_file, monkeypatch):
        monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
        cfg_file.write_text(json.dumps({
            "dashboard": {"notifications": {"teams": {"webhook_url": "https://teams-hook"}}}
        }))
        assert common.resolve_webhook() == "https://teams-hook"

    def test_placeholder_ignored(self, common, cfg_file, monkeypatch):
        monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
        cfg_file.write_text(json.dumps({
            "dashboard": {"webhook_url": "<TU_TEAMS_WEBHOOK_URL>"}
        }))
        assert common.resolve_webhook() == ""

    def test_no_webhook_returns_empty(self, common, cfg_file, monkeypatch):
        monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
        assert common.resolve_webhook() == ""


class TestResolveCron:
    """Orden: CLI > config.json dashboard.schedule.cron > default."""

    def test_cli_wins(self, common, cfg_file):
        assert common.resolve_cron("30 6 * * *") == "30 6 * * *"

    def test_config_fallback(self, common, cfg_file):
        cfg_file.write_text(json.dumps({
            "dashboard": {"schedule": {"cron": "15 8 * * 1-5"}}
        }))
        assert common.resolve_cron() == "15 8 * * 1-5"

    def test_default(self, common, cfg_file):
        assert common.resolve_cron() == "0 7 * * *"


class TestOptionalDependencyImports:
    """Los módulos deben ser importables aunque falten deps opcionales."""

    def test_scheduler_importable_without_apscheduler(self):
        mod = _load_module("dash_sched_test", DASHBOARD_DIR / "dashboard_scheduler.py")
        assert hasattr(mod, "TeamsNotifier")
        assert hasattr(mod, "DashboardScheduler")

    def test_dashboard_scheduler_requires_apscheduler(self):
        mod = _load_module("dash_sched_test2", DASHBOARD_DIR / "dashboard_scheduler.py")
        if mod.BackgroundScheduler is None:
            with pytest.raises(ImportError, match="apscheduler"):
                mod.DashboardScheduler(org="o", project="p", pat="x")
        else:
            sched = mod.DashboardScheduler(org="o", project="p", pat="x")
            assert sched.org == "o"

    def test_teams_notifier_without_requests(self):
        mod = _load_module("dash_sched_test3", DASHBOARD_DIR / "dashboard_scheduler.py")
        if mod.requests is None:
            notifier = mod.TeamsNotifier("https://hook")
            assert notifier.send_notification({"summary": {}}) is False

    def test_kpi_scheduler_importable(self):
        mod = _load_module("kpi_sched_test", KPI_DIR / "scheduler.py")
        assert hasattr(mod, "AutoScheduler")

    def test_kpi_scheduler_guard(self, tmp_path):
        mod = _load_module("kpi_sched_test2", KPI_DIR / "scheduler.py")
        auto = mod.AutoScheduler(output_dir=str(tmp_path))
        if mod.schedule is None:
            assert auto.schedule_daily() is False
            assert auto.schedule_weekly() is False
            assert auto.schedule_hourly() is False
            assert auto.clear_schedule() is False
        else:
            assert auto.schedule_daily() is True
            auto.clear_schedule()

    def test_scheduler_paths_resolved_relative_to_file(self):
        """El scheduler ya no depende del cwd para encontrar los scripts."""
        mod = _load_module("dash_sched_test4", DASHBOARD_DIR / "dashboard_scheduler.py")
        if mod.BackgroundScheduler is None:
            pytest.skip("apscheduler no instalado")
        sched = mod.DashboardScheduler(org="o", project="p", pat="x")
        assert Path(sched.consolidator_path).name == "dashboard_consolidator.py"
        assert Path(sched.consolidator_path).is_absolute()


class TestRequirementsFiles:
    """Los requirements declaran todas las deps usadas."""

    def test_dashboard_requirements_exist(self):
        req = (DASHBOARD_DIR / "requirements.txt").read_text()
        assert "requests" in req
        assert "apscheduler" in req.lower()

    def test_kpi_requirements_have_schedule_and_openpyxl(self):
        req = (KPI_DIR / "requirements.txt").read_text()
        assert "schedule" in req
        assert "openpyxl" in req
        assert "pyyaml" in req
        assert "rich" in req
        assert "streamlit" in req
        assert "plotly" in req

    def test_kpi_requirements_no_dead_deps(self):
        """reportlab/pandas/matplotlib no se importan en kpi_analyzer."""
        req = (KPI_DIR / "requirements.txt").read_text()
        for dead in ("reportlab", "pandas", "matplotlib"):
            assert dead not in req


class TestExporterNoAutoInstall:
    """exporter.to_excel no debe auto-instalar openpyxl con pip."""

    def test_no_pip_install_in_source(self):
        src = (KPI_DIR / "exporter.py").read_text(encoding="utf-8")
        # No debe invocar pip en runtime (el mensaje de ayuda sí lo menciona)
        assert "check_call" not in src
        assert '"-m", "pip"' not in src
        assert "'-m', 'pip'" not in src

    def test_to_excel_graceful_without_openpyxl(self, tmp_path, monkeypatch):
        mod = _load_module("exporter_test", KPI_DIR / "exporter.py")
        exporter = mod.ExporterPro({"a": 1}, output_dir=str(tmp_path))
        # Simular openpyxl ausente
        real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("openpyxl"):
                raise ImportError("No module named 'openpyxl'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fake_import)
        assert exporter.to_excel() is False


class TestPackageImportable:
    """El paquete dashboard debe importarse sin apscheduler/requests."""

    def test_dashboard_package_import(self):
        # SCM_DIR ya está en sys.path (insertado a nivel de módulo)
        import dashboard  # noqa: F401
        assert dashboard.__version__
