"""Tests para Pub/Sub Monitor (opción 43) — modo CLI no-interactivo y multi-proyecto."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import scm.gcp.tools as gcp_tools
from scm.gcp.pubsub_monitor import pubsub_monitor as pm


# ---------- wiring del launcher ----------

class TestLauncherWiring:
    def test_args_declaran_project_multi_output(self):
        args = gcp_tools.TOOLS["43"]["args"]
        assert "--project" in args
        assert "--multi-project" in args
        assert "-o" in args

    def test_run_stem_en_multi_project_scripts(self):
        assert "run" in gcp_tools.MULTI_PROJECT_PARAM_SCRIPTS

    def test_export_choices_coherentes_con_script(self):
        tool = gcp_tools.TOOLS["43"]
        assert set(tool["export_choices"]) == {"all", "html", "json", "excel", "console"}
        assert tool["export_default"] == "all"


# ---------- PubSubMonitor ----------

def _bare_monitor(projects):
    """Instancia sin constructor (evita clientes GCP reales)."""
    m = object.__new__(pm.PubSubMonitor)
    m.projects = list(projects)
    m.collector = MagicMock()
    m.analyzer = MagicMock()
    m.alert_engine = MagicMock()
    m.results = {}
    m.config = {}
    return m


class TestProjectsOverride:
    def test_projects_override_reemplaza_config(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text(
            '{"gcp": {"service_accounts_reporter": {"projects": ["p-config"]}}}',
            encoding="utf-8")
        with patch.object(pm, "PubSubCollector"), patch.object(pm, "MetricsAnalyzer"), \
                patch.object(pm, "AlertEngine"):
            m = pm.PubSubMonitor(str(cfg), projects=["p1", "p2"])
        assert m.projects == ["p1", "p2"]

    def test_projects_desde_config_si_no_override(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text(
            '{"gcp": {"service_accounts_reporter": {"projects": ["p-config"]}}}',
            encoding="utf-8")
        with patch.object(pm, "PubSubCollector"), patch.object(pm, "MetricsAnalyzer"), \
                patch.object(pm, "AlertEngine"):
            m = pm.PubSubMonitor(str(cfg))
        assert m.projects == ["p-config"]


class TestExecuteAnalysis:
    def test_errores_por_proyecto_no_abortan_y_se_conservan(self):
        m = _bare_monitor(["p1", "p2"])
        m.collector.collect_all_data.return_value = {
            "timestamp": "t",
            "projects": {"p1": {"topics": [], "subscriptions": [], "metrics": {}}},
            "errors": ["Error en p2: denied"],
        }
        m.analyzer.calculate_project_summary.return_value = {"ok": True}
        m.alert_engine.evaluate_all_alerts.return_value = []

        m._execute_analysis(show_steps=False)

        assert set(m.results["projects"].keys()) == {"p1"}
        assert m.results["errors"] == ["Error en p2: denied"]

    def test_run_full_analysis_no_pausa_en_cli(self):
        m = _bare_monitor(["p1"])
        m.collector.collect_all_data.return_value = {
            "timestamp": "t", "projects": {}, "errors": []}
        with patch.object(pm.Prompt, "ask") as ask:
            m.run_full_analysis(pause=False)
        ask.assert_not_called()


class TestGenerateReports:
    def _monitor_con_resultados(self):
        m = _bare_monitor(["p1"])
        m.results = {"timestamp": "t", "projects": {"p1": {}}, "errors": []}
        return m

    def test_all_genera_tres_formatos(self, tmp_path):
        m = self._monitor_con_resultados()
        dash = MagicMock()
        dash.generate_html_dashboard.return_value = "f.html"
        dash.generate_json_report.return_value = "f.json"
        dash.generate_excel_report.return_value = "f.xlsx"
        with patch.object(pm, "DashboardGenerator", return_value=dash):
            m.generate_reports(pause=False, output="all", output_dir=tmp_path)
        dash.generate_html_dashboard.assert_called_once()
        dash.generate_json_report.assert_called_once()
        dash.generate_excel_report.assert_called_once()

    def test_formato_console_no_genera_archivos(self, tmp_path):
        m = self._monitor_con_resultados()
        dash = MagicMock()
        with patch.object(pm, "DashboardGenerator", return_value=dash):
            m.generate_reports(pause=False, output="console", output_dir=tmp_path)
        dash.generate_html_dashboard.assert_not_called()
        dash.generate_json_report.assert_not_called()
        dash.generate_excel_report.assert_not_called()

    def test_default_dir_bajo_outcome_resuelto(self, tmp_path):
        m = self._monitor_con_resultados()
        captured = {}

        def _capture(path):
            captured["path"] = path
            return path

        dash = MagicMock()
        dash.generate_json_report.side_effect = _capture
        fake_outcome = tmp_path / "outcome"
        with patch.object(pm, "DashboardGenerator", return_value=dash), \
                patch.object(pm, "resolve_outcome_dir", return_value=fake_outcome):
            m.generate_reports(pause=False, output="json")
        assert str(captured["path"]).replace("\\", "/").startswith(
            str(fake_outcome).replace("\\", "/"))
        assert "pubsub_monitor" in str(captured["path"])


class TestRunCli:
    def test_sin_proyectos_retorna_1(self):
        m = _bare_monitor([])
        assert m.run_cli() == 1

    def test_alerts_no_genera_reportes(self):
        m = _bare_monitor(["p1"])
        m.collector.collect_all_data.return_value = {
            "timestamp": "t", "projects": {}, "errors": []}
        with patch.object(pm.PubSubMonitor, "generate_reports") as gen:
            assert m.run_cli(action="alerts") == 0
        gen.assert_not_called()

    def test_full_genera_reportes_con_output(self):
        m = _bare_monitor(["p1"])
        m.collector.collect_all_data.return_value = {
            "timestamp": "t", "projects": {}, "errors": []}
        with patch.object(pm.PubSubMonitor, "generate_reports") as gen:
            assert m.run_cli(action="full", output="html") == 0
        gen.assert_called_once_with(pause=False, output="html")


class TestMain:
    def test_sin_tty_y_sin_args_sale_2(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["run.py"])
        monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
        with patch.object(pm, "PubSubMonitor", return_value=MagicMock()):
            with pytest.raises(SystemExit) as e:
                pm.main()
        assert e.value.code == 2

    def test_multi_project_invoca_run_cli(self, monkeypatch):
        monkeypatch.setattr(sys, "argv",
                            ["run.py", "--multi-project", "p1,p2", "-o", "json"])
        inst = MagicMock()
        inst.run_cli.return_value = 0
        ctor = MagicMock(return_value=inst)
        with patch.object(pm, "PubSubMonitor", ctor):
            with pytest.raises(SystemExit) as e:
                pm.main()
        assert e.value.code == 0
        assert ctor.call_args.kwargs["projects"] == ["p1", "p2"]
        inst.run_cli.assert_called_once_with(action="full", output="json")
