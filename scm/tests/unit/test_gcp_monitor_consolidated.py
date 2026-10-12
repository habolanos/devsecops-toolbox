# -*- coding: utf-8 -*-
"""Tests de las tablas consolidadas de gcp_monitor (opción 1)."""
import importlib.util
import io
import sys
from pathlib import Path

import pytest

_MON = Path(__file__).resolve().parents[2] / "gcp" / "monitoring" / "gcp_monitor.py"
_spec = importlib.util.spec_from_file_location("gcp_monitor", _MON)
mon = importlib.util.module_from_spec(_spec)
sys.modules["gcp_monitor"] = mon
_spec.loader.exec_module(mon)

RICH = mon.RICH_AVAILABLE


def _all_data():
    return {
        "proj-a": {
            "services": [{"state": "ENABLED"}] * 20 + [{"state": "DISABLED"}],
            "gke_clusters": [{"name": "c1", "location": "us"}],
            "sql_instances": [{"state": "RUNNABLE"}, {"state": "SUSPENDED"}],
            "compute_instances": [{"status": "RUNNING"}] * 3
            + [{"status": "TERMINATED"}],
            "cloud_run": [{"metadata": {"annotations": {
                "run.googleapis.com/ingress": "all"}}}],
            "pubsub_topics": [{}] * 5,
        },
        "proj-b": {k: [] for k in
                   ("services", "gke_clusters", "sql_instances",
                    "compute_instances", "cloud_run", "pubsub_topics")},
    }


def _render(table):
    from rich.console import Console
    buf = io.StringIO()
    Console(file=buf, force_terminal=True, width=160).print(table)
    return buf.getvalue()


class TestProjectIssueCounts:
    def test_counts_issues(self):
        i = mon.project_issue_counts(_all_data()["proj-a"])
        assert i["compute_down"] == 1
        assert i["sql_bad"] == 1
        assert i["svc_off"] == 1
        assert i["run_public"] == 1
        assert i["total"] == 4

    def test_clean_project_zero(self):
        assert mon.project_issue_counts(_all_data()["proj-b"])["total"] == 0


@pytest.mark.skipif(not RICH, reason="rich no instalado")
class TestConsolidatedSummaryMatrix:
    def test_one_row_per_project_plus_total(self):
        t = mon.create_consolidated_summary_table(_all_data(), None)
        out = _render(t)
        assert "CONSOLIDADO" in out
        assert "proj-a" in out and "proj-b" in out and "TOTAL" in out
        # matrix: una fila por proyecto + header + total
        assert len(t.rows) == 3

    def test_totals(self):
        t = mon.create_consolidated_summary_table(_all_data(), None)
        out = _render(t)
        assert "21" in out           # servicios proj-a
        assert "34" in out           # total proj-a (21+1+2+4+1+5)


@pytest.mark.skipif(not RICH, reason="rich no instalado")
class TestConsolidatedHealthMatrix:
    def test_alert_columns(self):
        t = mon.create_consolidated_health_table(_all_data(), None)
        out = _render(t)
        assert "ATENCIÓN" in out
        assert "proj-a" in out
        assert len(t.rows) == 2       # una fila por proyecto

    def test_ok_project(self):
        t = mon.create_consolidated_health_table(
            {"p": _all_data()["proj-b"]}, None)
        assert "🟢 OK" in _render(t)


class TestAggregateGkeHealth:
    def _rows(self):
        return [
            ({'pods_running': 40, 'pods_not_running': 12, 'pods_pct': 55.2,
              'services_pct': 20.0, 'deploy_total': 30,
              'nodes_cpu_high': 1, 'nodes_mem_high': 0,
              'deployments': [{'restarts': 0, 'status': 'Running'},
                              {'restarts': 12, 'status': 'Degraded'}]},
             '🟢 OK'),
            ({'pods_running': 5, 'pods_not_running': 30, 'pods_pct': 92.0,
              'services_pct': 10.0, 'deploy_total': 8,
              'nodes_cpu_high': 0, 'nodes_mem_high': 2,
              'deployments': []}, '🔴 CRÍTICO'),
        ]

    def test_aggregate(self):
        h = mon.aggregate_gke_project_health(self._rows())
        assert h['clusters'] == 2
        assert h['pods_running'] == 45 and h['pods_not_running'] == 42
        assert h['pods_state'] == '⚠️ ATENCIÓN'   # nr>0 pero nr<=run
        assert h['deploy_attention'] == 1
        assert h['nodes_high'] == 3
        assert h['worst_ip_pct'] == 92.0
        assert h['worst_health'] == '🔴 CRÍTICO'

    def test_advertencia_when_not_running_exceeds(self):
        h = mon.aggregate_gke_project_health([
            ({'pods_running': 2, 'pods_not_running': 10,
              'pods_pct': 0, 'services_pct': 0, 'deployments': []},
             '🟡 ADVERTENCIA')])
        assert h['pods_state'] == '🟡 ADVERTENCIA'

    def test_na_pods(self):
        h = mon.aggregate_gke_project_health([
            ({'pods_running': 'N/A', 'pods_not_running': 'N/A',
              'deployments': []}, '⚪ SIN DATOS')])
        assert h['pods_known'] is False
        assert h['pods_state'] == '⚪ S/D'

    def test_empty(self):
        h = mon.aggregate_gke_project_health([])
        assert h['clusters'] == 0


@pytest.mark.skipif(not RICH, reason="rich no instalado")
class TestGkeHealthTable:
    def test_render(self):
        h = mon.aggregate_gke_project_health(
            [({'pods_running': 2, 'pods_not_running': 10,
               'pods_pct': 91.0, 'services_pct': 5.0, 'deploy_total': 4,
               'nodes_cpu_high': 1, 'nodes_mem_high': 0,
               'deployments': [{'restarts': 3, 'status': 'Progressing'}]},
              '🟡 ADVERTENCIA')])
        t = mon.create_consolidated_gke_health_table({"proj-x": h})
        out = _render(t)
        assert "proj-x" in out
        assert "ADVERTENCIA" in out
        assert "91.0%" in out
