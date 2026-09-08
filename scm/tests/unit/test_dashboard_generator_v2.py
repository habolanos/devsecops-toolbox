#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Dashboard Generator v2.0
Tests para validar funcionalidad del generador de dashboards HTML.

Version: 2.0.0
Author: Harold Adrian
"""

import pytest
import json
import sys
from pathlib import Path

# Add scm to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    'dashboard_generator',
    str(Path(__file__).parent.parent.parent / 'dashboard' / 'dashboard_generator.py')
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
DashboardGenerator = _mod.DashboardGenerator


class TestDashboardGeneratorInit:
    """Tests para inicialización de DashboardGenerator."""

    @pytest.mark.unit
    def test_generator_init_default(self, tmp_path):
        """Test: Inicializar DashboardGenerator con defaults."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        assert gen.input_file == tmp_path / "data.json"
        assert gen.output_file == tmp_path / "out.html"

    @pytest.mark.unit
    def test_generator_init_creates_output_dir(self, tmp_path):
        """Test: DashboardGenerator crea directorio de salida."""
        out = tmp_path / "subdir" / "dashboard.html"
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=out
        )
        assert out.parent.exists()


class TestGenerateHTML:
    """Tests para _generate_html."""

    @pytest.mark.unit
    def test_generate_html_basic(self, tmp_path):
        """Test: _generate_html genera HTML válido."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        data = {
            'timestamp': '2026-07-15T07:00:00Z',
            'metrics': {
                'health_score': {'overall_score': 75, 'deployment_frequency': 2.5, 'mttr_hours': 1.5, 'change_failure_rate': 8.5, 'system_uptime': 99.8, 'breakdown': {}},
                'pr_metrics': {'total_prs': 10, 'approval_rate_percentage': 92},
                'branch_compliance': {'total_repos': 50, 'compliance_percentage': 96},
                'pipeline_status': {'total_pipelines': 95, 'successful': 85, 'failed': 5, 'in_progress': 5, 'success_rate': 94.4},
                'security': {
                    'pipeline_logs': {'total_matches': 0},
                    'repo_vulnerabilities': {'total_findings': 0},
                },
                'pending_approvals': {'total': 3},
                'cicd_inventory': {'total_repos': 50, 'total_ci_pipelines': 45, 'total_cd_pipelines': 40},
                'prod_deploy': {'total_pipelines': 40, 'pipelines_within_deadline': 38, 'pipelines_overdue': 2},
            },
            'alerts': {'critical': [], 'warning': [], 'info': []},
            'summary': {},
        }
        html = gen._generate_html(data)
        assert '<!DOCTYPE html>' in html
        assert '<html' in html
        assert 'Dashboard Matutino DevSecOps' in html

    @pytest.mark.unit
    def test_generate_html_no_code_coverage(self, tmp_path):
        """Test: HTML no contiene Code Coverage (eliminado en v2.0)."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        data = {
            'timestamp': '2026-07-15T07:00:00Z',
            'metrics': {
                'health_score': {'overall_score': 75, 'breakdown': {}},
                'pr_metrics': {},
                'branch_compliance': {},
                'pipeline_status': {},
                'security': {'pipeline_logs': {}, 'repo_vulnerabilities': {}},
                'pending_approvals': {},
                'cicd_inventory': {},
                'prod_deploy': {},
            },
            'alerts': {},
            'summary': {},
        }
        html = gen._generate_html(data)
        assert 'Code Coverage' not in html

    @pytest.mark.unit
    def test_generate_html_has_security_section(self, tmp_path):
        """Test: HTML contiene sección de Security & Approvals."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        data = {
            'timestamp': '2026-07-15T07:00:00Z',
            'metrics': {
                'health_score': {'overall_score': 75, 'breakdown': {}},
                'pr_metrics': {},
                'branch_compliance': {},
                'pipeline_status': {},
                'security': {
                    'pipeline_logs': {'total_matches': 5},
                    'repo_vulnerabilities': {'total_findings': 3},
                },
                'pending_approvals': {'total': 7},
                'cicd_inventory': {},
                'prod_deploy': {'pipelines_overdue': 1},
            },
            'alerts': {},
            'summary': {},
        }
        html = gen._generate_html(data)
        assert 'Security & Approvals' in html
        assert 'Repo Vulnerabilities' in html
        assert 'Pipeline Log Alerts' in html
        assert 'Pending Approvals' in html
        assert 'Prod Deploy Overdue' in html

    @pytest.mark.unit
    def test_generate_html_has_charts(self, tmp_path):
        """Test: HTML contiene canvas para gráficos Chart.js."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        data = {
            'timestamp': '2026-07-15T07:00:00Z',
            'metrics': {
                'health_score': {'overall_score': 75, 'breakdown': {'deployment_frequency_score': 75, 'lead_time_score': 75, 'mttr_score': 100, 'cfr_score': 100, 'uptime_score': 100}},
                'pr_metrics': {},
                'branch_compliance': {},
                'pipeline_status': {'successful': 85, 'failed': 5, 'in_progress': 5},
                'security': {'pipeline_logs': {'total_matches': 3}, 'repo_vulnerabilities': {'total_findings': 2}},
                'pending_approvals': {'total': 4},
                'cicd_inventory': {'total_repos': 50, 'total_ci_pipelines': 45, 'total_cd_pipelines': 40},
                'prod_deploy': {'pipelines_overdue': 1},
            },
            'alerts': {},
            'summary': {},
        }
        html = gen._generate_html(data)
        assert 'healthRadar' in html
        assert 'pipelineDoughnut' in html
        assert 'securityBar' in html
        assert 'inventoryBar' in html
        assert 'Chart.js' in html or 'chart.js' in html

    @pytest.mark.unit
    def test_generate_html_has_dora_section(self, tmp_path):
        """Test: HTML contiene sección DORA Metrics."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        data = {
            'timestamp': '2026-07-15T07:00:00Z',
            'metrics': {
                'health_score': {'overall_score': 75, 'deployment_frequency': 2.5, 'mttr_hours': 1.5, 'change_failure_rate': 8.5, 'system_uptime': 99.8, 'breakdown': {}},
                'pr_metrics': {},
                'branch_compliance': {},
                'pipeline_status': {},
                'security': {'pipeline_logs': {}, 'repo_vulnerabilities': {}},
                'pending_approvals': {},
                'cicd_inventory': {},
                'prod_deploy': {},
            },
            'alerts': {},
            'summary': {},
        }
        html = gen._generate_html(data)
        assert 'DORA Metrics' in html
        assert 'Health Score' in html
        assert 'Deployment Frequency' in html
        assert 'MTTR' in html
        assert 'Change Failure Rate' in html
        assert 'System Uptime' in html

    @pytest.mark.unit
    def test_generate_html_has_pr_section(self, tmp_path):
        """Test: HTML contiene sección PR & Branch Policies."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        data = {
            'timestamp': '2026-07-15T07:00:00Z',
            'metrics': {
                'health_score': {'overall_score': 75, 'breakdown': {}},
                'pr_metrics': {'total_prs': 150, 'approval_rate_percentage': 92},
                'branch_compliance': {'compliance_percentage': 96},
                'pipeline_status': {'success_rate': 94.4},
                'security': {'pipeline_logs': {}, 'repo_vulnerabilities': {}},
                'pending_approvals': {},
                'cicd_inventory': {},
                'prod_deploy': {},
            },
            'alerts': {},
            'summary': {},
        }
        html = gen._generate_html(data)
        assert 'Pull Requests' in html
        assert 'PR Approval Rate' in html
        assert 'Branch Compliance' in html
        assert 'Pipeline Success Rate' in html


class TestAlertsHTML:
    """Tests para _generate_alerts_html."""

    @pytest.mark.unit
    def test_alerts_no_alerts(self, tmp_path):
        """Test: HTML de alertas cuando no hay alertas."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        html = gen._generate_alerts_html({'critical': [], 'warning': [], 'info': []})
        assert 'Sin alertas' in html

    @pytest.mark.unit
    def test_alerts_critical(self, tmp_path):
        """Test: HTML de alertas críticas."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        html = gen._generate_alerts_html({'critical': ['Test critical'], 'warning': [], 'info': []})
        assert 'alert-critical' in html
        assert 'Test critical' in html

    @pytest.mark.unit
    def test_alerts_warning(self, tmp_path):
        """Test: HTML de alertas de advertencia."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        html = gen._generate_alerts_html({'critical': [], 'warning': ['Test warning'], 'info': []})
        assert 'alert-warning' in html
        assert 'Test warning' in html


class TestColorHelpers:
    """Tests para métodos de color."""

    @pytest.mark.unit
    def test_get_color_excellent(self, tmp_path):
        """Test: Color verde para score >= 80."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        assert gen._get_color(85) == '#28a745'

    @pytest.mark.unit
    def test_get_color_good(self, tmp_path):
        """Test: Color azul para score 60-79."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        assert gen._get_color(65) == '#17a2b8'

    @pytest.mark.unit
    def test_get_color_warning(self, tmp_path):
        """Test: Color amarillo para score 40-59."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        assert gen._get_color(45) == '#ffc107'

    @pytest.mark.unit
    def test_get_color_critical(self, tmp_path):
        """Test: Color rojo para score < 40."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        assert gen._get_color(30) == '#dc3545'


class TestInventoryTable:
    """Tests para _generate_inventory_table."""

    @pytest.mark.unit
    def test_inventory_table_empty(self, tmp_path):
        """Test: Tabla vacía cuando no hay datos."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        html = gen._generate_inventory_table({})
        assert html == ''

    @pytest.mark.unit
    def test_inventory_table_with_data(self, tmp_path):
        """Test: Tabla con datos de inventario."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        inventory = {
            'repos': [
                {'repo_name': 'repo-1', 'default_branch': 'main', 'last_commit_date': '2026-07-15', 'total_commits': 100},
                {'repo_name': 'repo-2', 'default_branch': 'develop', 'last_commit_date': '2026-07-14', 'total_commits': 50},
            ]
        }
        html = gen._generate_inventory_table(inventory)
        assert 'CI/CD Inventory' in html
        assert 'repo-1' in html
        assert 'repo-2' in html
        assert 'Repository' in html

    @pytest.mark.unit
    def test_inventory_table_max_20(self, tmp_path):
        """Test: Tabla limita a 20 filas."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        repos = [{'repo_name': f'repo-{i}', 'default_branch': 'main'} for i in range(30)]
        html = gen._generate_inventory_table({'repos': repos})
        assert 'repo-0' in html
        assert 'repo-19' in html
        assert 'repo-29' not in html


class TestProdDeployTable:
    """Tests para _generate_prod_deploy_table."""

    @pytest.mark.unit
    def test_prod_deploy_table_empty(self, tmp_path):
        """Test: Tabla vacía cuando no hay datos."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        html = gen._generate_prod_deploy_table({})
        assert html == ''

    @pytest.mark.unit
    def test_prod_deploy_table_with_data(self, tmp_path):
        """Test: Tabla con datos de prod deploy."""
        gen = DashboardGenerator(
            input_file=tmp_path / "data.json",
            output_file=tmp_path / "out.html"
        )
        prod_deploy = {
            'pipelines': [
                {'cd_pipeline_name': 'pipe-1', 'last_prod_deploy_date': '2026-07-10', 'last_prod_deploy_status': 'succeeded', 'days_since_prod_deploy': 5, 'deadline_status': 'Al día'},
                {'cd_pipeline_name': 'pipe-2', 'last_prod_deploy_date': '2026-06-01', 'last_prod_deploy_status': 'failed', 'days_since_prod_deploy': 44, 'deadline_status': 'Vencido'},
            ]
        }
        html = gen._generate_prod_deploy_table(prod_deploy)
        assert 'Prod Deploy Tracking' in html
        assert 'pipe-1' in html
        assert 'pipe-2' in html
        assert 'Pipeline CD' in html


class TestGenerateFile:
    """Tests para el método generate que escribe archivo."""

    @pytest.mark.unit
    def test_generate_creates_html_file(self, tmp_path):
        """Test: generate crea archivo HTML desde JSON."""
        data = {
            'timestamp': '2026-07-15T07:00:00Z',
            'metrics': {
                'health_score': {'overall_score': 75, 'breakdown': {}},
                'pr_metrics': {},
                'branch_compliance': {},
                'pipeline_status': {},
                'security': {'pipeline_logs': {}, 'repo_vulnerabilities': {}},
                'pending_approvals': {},
                'cicd_inventory': {},
                'prod_deploy': {},
            },
            'alerts': {'critical': [], 'warning': [], 'info': []},
            'summary': {},
        }
        input_file = tmp_path / "dashboard_data.json"
        output_file = tmp_path / "dashboard.html"

        with open(input_file, 'w') as f:
            json.dump(data, f)

        gen = DashboardGenerator(input_file=input_file, output_file=output_file)
        result = gen.generate()

        assert result is True
        assert output_file.exists()
        content = output_file.read_text(encoding='utf-8')
        assert '<!DOCTYPE html>' in content
        assert 'Dashboard Matutino DevSecOps' in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
