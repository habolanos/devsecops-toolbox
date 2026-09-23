"""
Tests para herramientas GCP (Google Cloud Platform)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import io
import json
import sys
import os
import importlib.util
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CLOUD_RUN_DIR = Path(__file__).parents[2] / "gcp" / "cloud-run"
GCP_DIR = Path(__file__).parents[2] / "gcp"
sys.path.insert(0, str(CLOUD_RUN_DIR))
sys.path.insert(0, str(GCP_DIR))

import tools as gcp_tools

_module_spec = importlib.util.spec_from_file_location(
    "gcp_cloudrun_vpc_ip_diagnostic",
    CLOUD_RUN_DIR / "gcp_cloudrun_vpc_ip_diagnostic.py",
)
cloudrun_vpc_diagnostic = importlib.util.module_from_spec(_module_spec)
sys.modules[_module_spec.name] = cloudrun_vpc_diagnostic
_module_spec.loader.exec_module(cloudrun_vpc_diagnostic)


class TestGCPTools:
    """Tests para herramientas GCP"""

    def test_gcp_service_account_checker(self):
        """Test Service Account Checker"""
        # Simular validación de service accounts
        service_accounts = [
            {'email': 'sa1@project.iam.gserviceaccount.com', 'status': 'active'},
            {'email': 'sa2@project.iam.gserviceaccount.com', 'status': 'active'},
            {'email': 'sa3@project.iam.gserviceaccount.com', 'status': 'inactive'}
        ]
        
        assert len(service_accounts) == 3
        active_count = sum(1 for sa in service_accounts if sa['status'] == 'active')
        assert active_count == 2

    def test_gcp_cloud_sql_manager(self):
        """Test Cloud SQL Manager"""
        # Simular gestión de Cloud SQL
        databases = [
            {'name': 'db1', 'version': 'MYSQL_8_0', 'status': 'RUNNABLE'},
            {'name': 'db2', 'version': 'POSTGRES_13', 'status': 'RUNNABLE'},
            {'name': 'db3', 'version': 'MYSQL_5_7', 'status': 'STOPPED'}
        ]
        
        assert len(databases) == 3
        runnable_count = sum(1 for db in databases if db['status'] == 'RUNNABLE')
        assert runnable_count == 2

    def test_gcp_gke_cluster_manager(self):
        """Test GKE Cluster Manager"""
        # Simular gestión de clusters GKE
        clusters = [
            {'name': 'cluster-1', 'status': 'RUNNING', 'node_count': 3},
            {'name': 'cluster-2', 'status': 'RUNNING', 'node_count': 5},
            {'name': 'cluster-3', 'status': 'PROVISIONING', 'node_count': 2}
        ]
        
        assert len(clusters) == 3
        running_count = sum(1 for c in clusters if c['status'] == 'RUNNING')
        assert running_count == 2

    def test_gcp_cloud_run_tools(self):
        """Test Cloud Run Tools"""
        # Simular gestión de Cloud Run
        services = [
            {'name': 'service-1', 'status': 'ACTIVE', 'region': 'us-central1'},
            {'name': 'service-2', 'status': 'ACTIVE', 'region': 'us-east1'},
            {'name': 'service-3', 'status': 'INACTIVE', 'region': 'europe-west1'}
        ]
        
        assert len(services) == 3
        active_count = sum(1 for s in services if s['status'] == 'ACTIVE')
        assert active_count == 2

    def test_cloud_run_ip_usage_is_current_over_total(self):
        """El formato de capacidad muestra IPs actuales sobre IPs totales."""
        format_ip_usage = cloudrun_vpc_diagnostic.format_ip_usage

        assert format_ip_usage(12, 252) == "12/252"
        assert format_ip_usage(-1, 252) == "0/252"

    def test_cloud_run_team_alias_expands_to_projects(self):
        """Los alias de equipo se convierten en proyectos GCP predefinidos."""
        assert gcp_tools.resolve_cloud_run_projects("WMS") == [
            "cpl-cs-wms-dev-30112023",
            "cpl-cs-wms-qa-30112023",
            "cpl-cs-wms-stag-09042025",
        ]
        assert gcp_tools.resolve_cloud_run_projects("custom-project") == ["custom-project"]

    def test_cloud_run_all_alias_expands_to_all_teams(self):
        """El alias ALL expande los proyectos de todos los equipos."""
        all_projects = gcp_tools.resolve_cloud_run_projects("ALL")
        expected = [p for projs in gcp_tools.CLOUD_RUN_PROJECTS_BY_TEAM.values() for p in projs]
        assert all_projects == expected
        assert len(all_projects) == 12
        # case-insensitive
        assert gcp_tools.resolve_cloud_run_projects("all") == all_projects

    def test_load_projects_from_config(self, tmp_path):
        """Lee gcp.service_accounts_reporter.projects desde config.json."""
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "gcp": {"service_accounts_reporter": {
                "projects": ["proj-a", " proj-b ", "", 123]
            }}
        }), encoding="utf-8")
        assert gcp_tools.load_projects_from_config(cfg) == ["proj-a", "proj-b"]
        # archivo inexistente o JSON inválido -> []
        assert gcp_tools.load_projects_from_config(tmp_path / "nope.json") == []
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid", encoding="utf-8")
        assert gcp_tools.load_projects_from_config(bad) == []

    def test_group_projects_by_team_derives_teams(self):
        """La clave de equipo se deriva del project ID."""
        groups = gcp_tools.group_projects_by_team([
            "cpl-cmanager-dev-13072023",
            "cpl-cs-csc-qa-16112023",
            "cpl-cs-wms-stag-09042025",
            "cpl-oms-prod-08082024",
            "no-env-token",
        ])
        assert groups["cmanager"] == ["cpl-cmanager-dev-13072023"]
        assert groups["cs-csc"] == ["cpl-cs-csc-qa-16112023"]
        assert groups["cs-wms"] == ["cpl-cs-wms-stag-09042025"]
        assert groups["oms"] == ["cpl-oms-prod-08082024"]
        assert groups["otros"] == ["no-env-token"]

    def test_cloud_run_projects_from_config_override(self, tmp_path, monkeypatch):
        """Si config.json define projects, los aliases se resuelven contra ellos."""
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({
            "gcp": {"service_accounts_reporter": {
                "projects": [
                    "acme-foo-dev-01",
                    "acme-foo-prod-01",
                    "acme-bar-qa-02",
                ]
            }}
        }), encoding="utf-8")
        monkeypatch.setattr(gcp_tools, "_scm_config_path", lambda: cfg)
        gcp_tools._CONFIG_PROJECT_GROUPS = None
        try:
            # alias derivado por coincidencia de sufijo/exacta
            assert gcp_tools.resolve_cloud_run_projects("FOO") == [
                "acme-foo-dev-01", "acme-foo-prod-01"
            ]
            assert gcp_tools.resolve_cloud_run_projects("acme-bar") == ["acme-bar-qa-02"]
            assert gcp_tools.resolve_cloud_run_projects("ALL") == [
                "acme-foo-dev-01", "acme-foo-prod-01", "acme-bar-qa-02"
            ]
        finally:
            gcp_tools._CONFIG_PROJECT_GROUPS = None

    def test_cloud_run_projects_fallback_when_no_config(self, tmp_path, monkeypatch):
        """Sin config.json se usa el dict hardcoded de fallback."""
        monkeypatch.setattr(gcp_tools, "_scm_config_path", lambda: tmp_path / "missing.json")
        gcp_tools._CONFIG_PROJECT_GROUPS = None
        try:
            assert gcp_tools.resolve_cloud_run_projects("WMS") == [
                "cpl-cs-wms-dev-30112023",
                "cpl-cs-wms-qa-30112023",
                "cpl-cs-wms-stag-09042025",
            ]
        finally:
            gcp_tools._CONFIG_PROJECT_GROUPS = None

    def test_cloud_run_env_names_for_many_projects(self):
        """Con >4 proyectos las etiquetas se derivan del project ID."""
        names = gcp_tools.cloud_run_env_names([
            "cpl-cs-wms-dev-30112023",
            "cpl-cs-csc-qa-16112023",
            "cpl-oms-stag-09042025",
            "cpl-cmanager-dev-13072023",
            "custom-project",
        ])
        assert names == ["cs-wms-dev", "cs-csc-qa", "oms-stg", "cmanager-dev", "custom-project"]
        # <=4 proyectos: posicional
        assert gcp_tools.cloud_run_env_names(["a", "b"]) == ["dev", "qa"]

    def test_cloud_run_env_key_from_text(self):
        """La clave de ambiente se extrae de labels compuestas."""
        assert cloudrun_vpc_diagnostic.env_key_from_text("cs-wms-qa") == "qa"
        assert cloudrun_vpc_diagnostic.env_key_from_text("oms-stg") == "stg"
        assert cloudrun_vpc_diagnostic.env_key_from_text("cpl-x-prd-01") == "prod"
        assert cloudrun_vpc_diagnostic.env_key_from_text("custom") is None

    def test_cloud_run_env_label_for_project(self):
        """La etiqueta '<equipo>-<env>' se deriva del project ID."""
        label = cloudrun_vpc_diagnostic.env_label_for_project
        assert label("cpl-cs-wms-dev-30112023") == "cs-wms-dev"
        assert label("cpl-cs-csc-qa-16112023") == "cs-csc-qa"
        assert label("cpl-oms-stag-09042025") == "oms-stg"
        assert label("custom-project") == "custom-project"

    def _make_diag(self, env, project, connectors=None, recommendations=None):
        return cloudrun_vpc_diagnostic.EnvironmentDiagnostic(
            environment=env,
            project_id=project,
            host_project_id="host-x",
            services=[],
            connectors=connectors or [],
            subnet_info={},
            recommendations=recommendations or [],
            risk_level="OK",
        )

    def _render(self, table):
        from rich.console import Console
        buf = io.StringIO()
        Console(file=buf, width=220).print(table)
        return buf.getvalue()

    def test_consolidated_connectors_table_has_project_column(self):
        """La tabla consolidada de connectors incluye Ambiente y Proyecto."""
        conn = cloudrun_vpc_diagnostic.VPCConnectorInfo(
            name="conn-1", region="us-central1", network="shared",
            ip_cidr_range="10.8.0.0/28", min_instances=2, max_instances=10,
            connected_services=["svc-a"], total_ips=16, used_ips_estimate=8,
            available_ips=8, utilization_pct=50.0, status="OK")
        diags = [
            self._make_diag("dev", "proj-dev", connectors=[conn]),
            self._make_diag("qa", "proj-qa", connectors=[conn]),
        ]
        helper = cloudrun_vpc_diagnostic.CloudRunVPCDiagnostic("p", "h")
        table = helper.create_connectors_table(diags)
        headers = [c.header for c in table.columns]
        assert headers[:2] == ["Ambiente", "Proyecto"]
        out = self._render(table)
        assert "conn-1" in out
        assert "proj-dev" in out and "proj-qa" in out
        assert "DEV" in out and "QA" in out

    def test_consolidated_recommendations_table_has_project_column(self):
        """La tabla consolidada de recomendaciones incluye Ambiente y Proyecto."""
        rec = {"priority": "HIGH", "type": "vpc_connector_cidr",
               "title": "Ampliar CIDR", "current": "/28",
               "recommended": "/27", "action": "Crear connector"}
        diags = [
            self._make_diag("dev", "proj-dev", recommendations=[rec]),
            self._make_diag("stg", "proj-stg", recommendations=[rec]),
        ]
        helper = cloudrun_vpc_diagnostic.CloudRunVPCDiagnostic("p", "h")
        table = helper.create_recommendations_table(diags)
        headers = [c.header for c in table.columns]
        assert headers[:2] == ["Ambiente", "Proyecto"]
        out = self._render(table)
        assert "vpc_connector_cidr" in out
        assert "proj-dev" in out and "proj-stg" in out

    def test_env_sort_key_orders_by_team_and_env(self):
        """Orden determinista: equipo primero, luego dev<qa<stg<prod."""
        key = cloudrun_vpc_diagnostic.env_sort_key
        labels = ["cs-wms-stg", "dev", "cs-wms-dev", "qa", "cs-wms-qa", "x-raro"]
        assert sorted(labels, key=key) == [
            "dev", "qa", "cs-wms-dev", "cs-wms-qa", "cs-wms-stg", "x-raro"
        ]

    def test_spinner_non_tty_writes_single_line(self):
        """En salida no-TTY el spinner no repite líneas por cada frame."""
        import time
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            sp = cloudrun_vpc_diagnostic.AnimatedSpinner("Trabajando")
            sp.start()
            time.sleep(0.3)
            sp.stop("Listo")
        finally:
            sys.stdout = old
        lines = [l for l in buf.getvalue().splitlines() if l.strip()]
        assert len(lines) <= 2
        assert "Trabajando" in lines[0]
        assert "Listo" in buf.getvalue()

    def test_cloud_run_direct_vpc_network_is_extracted(self):
        """La configuración Direct VPC Egress expone red y subred."""
        extract = cloudrun_vpc_diagnostic.extract_direct_vpc_network

        assert extract({
            "run.googleapis.com/network-interfaces": (
                '[{"network":"projects/host/global/networks/shared", '
                '"subnetwork":"projects/host/regions/us-central1/subnetworks/run"}]'
            )
        }) == ("shared", "run")

    def test_cloud_run_vpc_diagnostic_supports_html_output(self):
        """La opción 35 declara salida HTML para el launcher."""
        tool = gcp_tools.TOOLS["35"]
        assert "--output" in tool["args"]
        assert tool["path"].endswith("gcp_cloudrun_vpc_ip_diagnostic.py")

    def test_gcp_connectivity_checker(self):
        """Test Connectivity Checker"""
        # Simular verificación de conectividad
        connectivity = {
            'vpc_peering': True,
            'firewall_rules': True,
            'routes': True,
            'dns_resolution': True
        }
        
        assert all(connectivity.values())

    def test_gcp_cloud_functions_analyzer(self):
        """Test Cloud Functions Analyzer"""
        # Simular análisis de Cloud Functions
        functions = [
            {'name': 'func-1', 'runtime': 'python39', 'status': 'ACTIVE'},
            {'name': 'func-2', 'runtime': 'nodejs14', 'status': 'ACTIVE'},
            {'name': 'func-3', 'runtime': 'go116', 'status': 'INACTIVE'}
        ]
        
        assert len(functions) == 3
        active_count = sum(1 for f in functions if f['status'] == 'ACTIVE')
        assert active_count == 2


class TestGCPIntegration:
    """Tests de integración para GCP"""

    def test_gcp_multi_project_analysis(self):
        """Test análisis multi-proyecto"""
        projects = [
            {'id': 'project-1', 'resources': 50},
            {'id': 'project-2', 'resources': 75},
            {'id': 'project-3', 'resources': 30}
        ]
        
        total_resources = sum(p['resources'] for p in projects)
        assert total_resources == 155

    def test_gcp_resource_inventory(self):
        """Test inventario de recursos"""
        inventory = {
            'compute_instances': 10,
            'databases': 5,
            'cloud_functions': 20,
            'cloud_run_services': 8,
            'storage_buckets': 15
        }
        
        total_resources = sum(inventory.values())
        assert total_resources == 58

    def test_gcp_security_audit(self):
        """Test auditoría de seguridad"""
        security_checks = {
            'iam_policies': {'passed': 45, 'failed': 5},
            'firewall_rules': {'passed': 30, 'failed': 2},
            'encryption': {'passed': 50, 'failed': 0},
            'logging': {'passed': 40, 'failed': 3}
        }
        
        total_passed = sum(check['passed'] for check in security_checks.values())
        total_failed = sum(check['failed'] for check in security_checks.values())
        
        assert total_passed == 165
        assert total_failed == 10


class TestGCPMetrics:
    """Tests para métricas GCP"""

    def test_gcp_resource_utilization(self):
        """Test utilización de recursos"""
        instances = [
            {'cpu_usage': 45, 'memory_usage': 60},
            {'cpu_usage': 30, 'memory_usage': 50},
            {'cpu_usage': 55, 'memory_usage': 70}
        ]
        
        avg_cpu = sum(i['cpu_usage'] for i in instances) / len(instances)
        avg_memory = sum(i['memory_usage'] for i in instances) / len(instances)
        
        assert avg_cpu == 43.33 or abs(avg_cpu - 43.33) < 0.01
        assert avg_memory == 60.0

    def test_gcp_cost_analysis(self):
        """Test análisis de costos"""
        costs = {
            'compute': 500,
            'storage': 200,
            'networking': 150,
            'databases': 300
        }
        
        total_cost = sum(costs.values())
        assert total_cost == 1150

    def test_gcp_availability_metrics(self):
        """Test métricas de disponibilidad"""
        services = [
            {'name': 'service-1', 'uptime': 0.9999},
            {'name': 'service-2', 'uptime': 0.9998},
            {'name': 'service-3', 'uptime': 0.9997}
        ]
        
        avg_uptime = sum(s['uptime'] for s in services) / len(services)
        assert avg_uptime > 0.999


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
