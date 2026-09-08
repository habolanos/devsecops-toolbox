#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Dashboard Consolidator v2.0
Tests para validar funcionalidad del consolidador de datos del dashboard.

Version: 2.0.0
Author: Harold Adrian
"""

import pytest
import json
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add scm to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    'dashboard_consolidator',
    str(Path(__file__).parent.parent.parent / 'dashboard' / 'dashboard_consolidator.py')
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
DashboardConsolidator = _mod.DashboardConsolidator
HistoryManager = _mod.HistoryManager


class TestDashboardConsolidatorInit:
    """Tests para inicialización de DashboardConsolidator."""

    @pytest.mark.unit
    def test_consolidator_init(self, tmp_path):
        """Test: Inicializar DashboardConsolidator."""
        consolidator = DashboardConsolidator(
            org="test-org",
            project="test-project",
            pat="test-pat",
            output_dir=tmp_path
        )
        assert consolidator.org == "test-org"
        assert consolidator.project == "test-project"
        assert consolidator.output_dir == tmp_path

    @pytest.mark.unit
    def test_consolidator_init_creates_directory(self, tmp_path):
        """Test: DashboardConsolidator crea directorio si no existe."""
        new_dir = tmp_path / "dashboard_out"
        consolidator = DashboardConsolidator(
            org="org",
            project="proj",
            pat="pat",
            output_dir=new_dir
        )
        assert new_dir.exists()


class TestConsolidatorFallbacks:
    """Tests para métodos fallback del consolidador."""

    @pytest.mark.unit
    def test_get_security_logs_fallback(self, tmp_path):
        """Test: Fallback de security_logs retorna estructura válida."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        result = consolidator._get_security_logs()
        assert isinstance(result, dict)
        assert 'total_matches' in result
        assert result['total_matches'] == 0

    @pytest.mark.unit
    def test_get_security_vulnerabilities_fallback(self, tmp_path):
        """Test: Fallback de security_vulnerabilities retorna estructura válida."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        result = consolidator._get_security_vulnerabilities()
        assert isinstance(result, dict)
        assert 'total_findings' in result
        assert result['total_findings'] == 0

    @pytest.mark.unit
    def test_get_pending_approvals_fallback(self, tmp_path):
        """Test: Fallback de pending_approvals retorna estructura válida."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        result = consolidator._get_pending_approvals()
        assert isinstance(result, dict)
        assert 'total' in result
        assert result['total'] == 0

    @pytest.mark.unit
    def test_get_cicd_inventory_fallback(self, tmp_path):
        """Test: Fallback de cicd_inventory retorna estructura válida."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        result = consolidator._get_cicd_inventory()
        assert isinstance(result, dict)
        assert 'total_repos' in result
        assert 'total_ci_pipelines' in result
        assert 'total_cd_pipelines' in result

    @pytest.mark.unit
    def test_get_prod_deploy_fallback(self, tmp_path):
        """Test: Fallback de prod_deploy retorna estructura válida."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        result = consolidator._get_prod_deploy()
        assert isinstance(result, dict)
        assert 'total_pipelines' in result
        assert 'pipelines_overdue' in result


class TestConsolidate:
    """Tests para el método _consolidate."""

    @pytest.mark.unit
    def test_consolidate_basic_structure(self, tmp_path):
        """Test: _consolidate genera estructura básica válida."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        results = {
            'health_score': {'overall_score': 80, 'deployment_frequency': 2.5},
            'pr_metrics': {'total_prs': 10, 'approval_rate_percentage': 95},
            'branch_compliance': {'total_repos': 50, 'compliance_percentage': 96},
            'pipeline_status': {'total_pipelines': 95, 'success_rate': 94.4},
            'security_logs': {'total_matches': 0},
            'security_vulnerabilities': {'total_findings': 0},
            'pending_approvals': {'total': 3},
            'cicd_inventory': {'total_repos': 50, 'total_ci_pipelines': 45},
            'prod_deploy': {'total_pipelines': 40, 'pipelines_overdue': 0},
        }
        data = consolidator._consolidate(results)

        assert 'timestamp' in data
        assert data['status'] == 'success'
        assert 'metrics' in data
        assert 'alerts' in data
        assert 'summary' in data

    @pytest.mark.unit
    def test_consolidate_security_alerts(self, tmp_path):
        """Test: _consolidate genera alerta crítica cuando hay vulnerabilidades."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        results = {
            'security_vulnerabilities': {'total_findings': 5},
            'security_logs': {'total_matches': 0},
            'pending_approvals': {'total': 0},
            'prod_deploy': {'pipelines_overdue': 0},
            'health_score': {'overall_score': 85},
        }
        data = consolidator._consolidate(results)
        assert len(data['alerts']['critical']) > 0
        assert any('vulnerabilidades' in a for a in data['alerts']['critical'])

    @pytest.mark.unit
    def test_consolidate_prod_deploy_alert(self, tmp_path):
        """Test: _consolidate genera alerta crítica cuando hay pipelines overdue."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        results = {
            'security_vulnerabilities': {'total_findings': 0},
            'security_logs': {'total_matches': 0},
            'pending_approvals': {'total': 0},
            'prod_deploy': {'pipelines_overdue': 3},
            'health_score': {'overall_score': 85},
        }
        data = consolidator._consolidate(results)
        assert len(data['alerts']['critical']) > 0
        assert any('vencido' in a for a in data['alerts']['critical'])

    @pytest.mark.unit
    def test_consolidate_health_score_low_alert(self, tmp_path):
        """Test: _consolidate genera alerta cuando health score < 60."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        results = {
            'security_vulnerabilities': {'total_findings': 0},
            'security_logs': {'total_matches': 0},
            'pending_approvals': {'total': 0},
            'prod_deploy': {'pipelines_overdue': 0},
            'health_score': {'overall_score': 50},
        }
        data = consolidator._consolidate(results)
        assert len(data['alerts']['critical']) > 0
        assert any('Health Score' in a for a in data['alerts']['critical'])

    @pytest.mark.unit
    def test_consolidate_pending_approvals_warning(self, tmp_path):
        """Test: _consolidate genera warning cuando pending > 5."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        results = {
            'security_vulnerabilities': {'total_findings': 0},
            'security_logs': {'total_matches': 0},
            'pending_approvals': {'total': 10},
            'prod_deploy': {'pipelines_overdue': 0},
            'health_score': {'overall_score': 85},
        }
        data = consolidator._consolidate(results)
        assert len(data['alerts']['warning']) > 0
        assert any('aprobaciones' in a for a in data['alerts']['warning'])

    @pytest.mark.unit
    def test_consolidate_no_alerts_when_clean(self, tmp_path):
        """Test: _consolidate sin alertas cuando todo está bien."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        results = {
            'security_vulnerabilities': {'total_findings': 0},
            'security_logs': {'total_matches': 0},
            'pending_approvals': {'total': 0},
            'prod_deploy': {'pipelines_overdue': 0},
            'health_score': {'overall_score': 85},
        }
        data = consolidator._consolidate(results)
        assert len(data['alerts']['critical']) == 0
        assert len(data['alerts']['warning']) == 0

    @pytest.mark.unit
    def test_consolidate_summary_fields(self, tmp_path):
        """Test: _consolidate summary contiene todos los campos nuevos."""
        consolidator = DashboardConsolidator("org", "proj", "pat", tmp_path)
        results = {
            'branch_compliance': {'total_repos': 50, 'compliance_percentage': 96},
            'pipeline_status': {'success_rate': 94.4},
            'security_vulnerabilities': {'total_findings': 2},
            'security_logs': {'total_matches': 3},
            'pending_approvals': {'total': 4},
            'prod_deploy': {'pipelines_overdue': 1},
            'health_score': {'overall_score': 75},
        }
        data = consolidator._consolidate(results)
        s = data['summary']
        assert s['total_repos'] == 50
        assert s['branch_compliance'] == 96
        assert s['pipeline_success_rate'] == 94.4
        assert s['security_vulnerabilities'] == 2
        assert s['security_log_alerts'] == 3
        assert s['pending_approvals'] == 4
        assert s['prod_deploy_overdue'] == 1


class TestExtractSummary:
    """Tests para _extract_summary del HistoryManager."""

    @pytest.mark.unit
    def test_extract_summary_new_fields(self, tmp_path):
        """Test: _extract_summary incluye nuevos campos de métricas."""
        hm = HistoryManager(history_dir=tmp_path)
        dashboard_data = {
            'timestamp': '2026-07-15T07:00:00Z',
            'metrics': {
                'health_score': {'overall_score': 80, 'deployment_frequency': 2.5, 'mttr_hours': 1.5, 'change_failure_rate': 8.5, 'system_uptime': 99.8},
                'pr_metrics': {'total_prs': 150, 'approval_rate_percentage': 92},
                'branch_compliance': {'compliance_percentage': 96},
                'pipeline_status': {'success_rate': 94.4},
                'security': {
                    'repo_vulnerabilities': {'total_findings': 2},
                    'pipeline_logs': {'total_matches': 3},
                },
                'pending_approvals': {'total': 4},
                'prod_deploy': {'total_pipelines': 40},
            }
        }
        summary = hm._extract_summary(dashboard_data)
        assert summary['health_score'] == 80
        assert summary['pr_total'] == 150
        assert summary['pr_approval_rate'] == 92
        assert summary['branch_compliance'] == 96
        assert summary['pipeline_success_rate'] == 94.4
        assert summary['security_vulnerabilities'] == 2
        assert summary['security_log_alerts'] == 3
        assert summary['pending_approvals'] == 4
        assert summary['prod_deploy_tracking'] == 40


class TestRunAllTools:
    """Tests para _run_all_tools con JSON files simulados."""

    @pytest.mark.unit
    def test_run_all_tools_reads_json(self, tmp_path):
        """Test: _run_all_tools lee archivos JSON del directorio outcome."""
        outcome_dir = tmp_path / "outcome"
        outcome_dir.mkdir()
        dashboard_dir = tmp_path / "outcome" / "dashboard"
        dashboard_dir.mkdir()

        # Crear archivos JSON simulados
        (outcome_dir / "pr_master_20260715_070000.json").write_text(
            json.dumps({"data": {"total_prs": 10, "approval_rate_percentage": 95}})
        )
        (outcome_dir / "azdo_scan_pipeline_logs_20260715_070000.json").write_text(
            json.dumps({"data": [{"match": "test"}], "summary": {"total_matches": 1}})
        )
        (outcome_dir / "cicd_inventory_pending_approvals_20260715_070000.json").write_text(
            json.dumps({"data": [{"approval": "test"}], "total": 1})
        )

        consolidator = DashboardConsolidator("org", "proj", "pat", dashboard_dir)
        results = consolidator._run_all_tools()

        assert 'pr_metrics' in results
        assert 'security_logs' in results
        assert 'pending_approvals' in results

    @pytest.mark.unit
    def test_run_all_tools_fallback_when_no_json(self, tmp_path):
        """Test: _run_all_tools usa fallback cuando no hay JSON."""
        dashboard_dir = tmp_path / "dashboard"
        dashboard_dir.mkdir()
        (tmp_path / "outcome").mkdir(exist_ok=True)

        consolidator = DashboardConsolidator("org", "proj", "pat", dashboard_dir)
        results = consolidator._run_all_tools()

        # Debe usar fallbacks (valores por defecto)
        assert 'pr_metrics' in results
        assert 'security_logs' in results
        assert 'security_vulnerabilities' in results
        assert 'pending_approvals' in results
        assert 'cicd_inventory' in results
        assert 'prod_deploy' in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
