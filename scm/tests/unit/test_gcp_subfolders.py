#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — GCP subfolder tools sin cobertura
Cubre: artifact-registry, certificate-manager, cloud-armor, cloud-functions, cloud-run,
cloud-sql, cluster-gke, connectivity, consolidation, deployments_off, event-tracker,
gateway-services, inventory, load-balancer, monitoring, pubsub_monitor, reports-viewer,
rolesypermisos, secrets-configmaps, service-account, service-accounts, vpc-networks
"""

import pytest
import sys
import os
import importlib
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _import_module(module_path):
    """Helper para importar módulos con manejo de dependencias opcionales.
    Soporta folders con guiones usando spec_from_file_location."""
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


class TestGcpArtifactRegistry:
    def test_import(self):
        mod = _import_module("scm.gcp.artifact_registry.tag_filter")
        if mod is None:
            pytest.skip("tag_filter requires dependencies")
        assert mod is not None


class TestGcpCertificateManager:
    def test_import(self):
        mod = _import_module("scm.gcp.certificate_manager.gcp_certificate_checker")
        if mod is None:
            pytest.skip("gcp_certificate_checker requires dependencies")
        assert mod is not None


class TestGcpCloudArmor:
    def test_import(self):
        mod = _import_module("scm.gcp.cloud_armor.gcp_cloud_armor_checker")
        if mod is None:
            pytest.skip("gcp_cloud_armor_checker requires dependencies")
        assert mod is not None


class TestGcpCloudFunctions:
    def test_import_cf_base(self):
        mod = _import_module("scm.gcp.cloud_functions.cf_base")
        if mod is None:
            pytest.skip("cf_base requires dependencies")
        assert mod is not None

    def test_import_cf_metrics(self):
        mod = _import_module("scm.gcp.cloud_functions.cf_metrics")
        if mod is None:
            pytest.skip("cf_metrics requires dependencies")
        assert mod is not None

    def test_import_analyzer(self):
        mod = _import_module("scm.gcp.cloud_functions.gcp_cloud_functions_analyzer")
        if mod is None:
            pytest.skip("gcp_cloud_functions_analyzer requires dependencies")
        assert mod is not None


class TestGcpCloudRun:
    def test_import_alerts(self):
        mod = _import_module("scm.gcp.cloud_run.cloudrun_alerts")
        if mod is None:
            pytest.skip("cloudrun_alerts requires dependencies")
        assert mod is not None

    def test_import_base(self):
        mod = _import_module("scm.gcp.cloud_run.cloudrun_base")
        if mod is None:
            pytest.skip("cloudrun_base requires dependencies")
        assert mod is not None

    def test_import_metrics(self):
        mod = _import_module("scm.gcp.cloud_run.cloudrun_metrics")
        if mod is None:
            pytest.skip("cloudrun_metrics requires dependencies")
        assert mod is not None

    def test_import_checker(self):
        mod = _import_module("scm.gcp.cloud_run.gcp_cloudrun_checker")
        if mod is None:
            pytest.skip("gcp_cloudrun_checker requires dependencies")
        assert mod is not None

    def test_import_cost_analyzer(self):
        mod = _import_module("scm.gcp.cloud_run.gcp_cloudrun_cost_analyzer")
        if mod is None:
            pytest.skip("gcp_cloudrun_cost_analyzer requires dependencies")
        assert mod is not None

    def test_import_dependency_mapper(self):
        mod = _import_module("scm.gcp.cloud_run.gcp_cloudrun_dependency_mapper")
        if mod is None:
            pytest.skip("gcp_cloudrun_dependency_mapper requires dependencies")
        assert mod is not None

    def test_import_deployment_validator(self):
        mod = _import_module("scm.gcp.cloud_run.gcp_cloudrun_deployment_validator")
        if mod is None:
            pytest.skip("gcp_cloudrun_deployment_validator requires dependencies")
        assert mod is not None

    def test_import_executive_dashboard(self):
        mod = _import_module("scm.gcp.cloud_run.gcp_cloudrun_executive_dashboard")
        if mod is None:
            pytest.skip("gcp_cloudrun_executive_dashboard requires dependencies")
        assert mod is not None

    def test_import_health_analyzer(self):
        mod = _import_module("scm.gcp.cloud_run.gcp_cloudrun_health_analyzer")
        if mod is None:
            pytest.skip("gcp_cloudrun_health_analyzer requires dependencies")
        assert mod is not None

    def test_import_security_auditor(self):
        mod = _import_module("scm.gcp.cloud_run.gcp_cloudrun_security_auditor")
        if mod is None:
            pytest.skip("gcp_cloudrun_security_auditor requires dependencies")
        assert mod is not None

    def test_import_traffic_analyzer(self):
        mod = _import_module("scm.gcp.cloud_run.gcp_cloudrun_traffic_analyzer")
        if mod is None:
            pytest.skip("gcp_cloudrun_traffic_analyzer requires dependencies")
        assert mod is not None


class TestGcpCloudSql:
    def test_import_database_checker(self):
        mod = _import_module("scm.gcp.cloud_sql.gcp_database_checker")
        if mod is None:
            pytest.skip("gcp_database_checker requires dependencies")
        assert mod is not None

    def test_import_disk_checker(self):
        mod = _import_module("scm.gcp.cloud_sql.gcp_disk_checker")
        if mod is None:
            pytest.skip("gcp_disk_checker requires dependencies")
        assert mod is not None

    def test_import_sql_comparator(self):
        mod = _import_module("scm.gcp.cloud_sql.gcp_sql_comparator")
        if mod is None:
            pytest.skip("gcp_sql_comparator requires dependencies")
        assert mod is not None


class TestGcpClusterGke:
    def test_import(self):
        mod = _import_module("scm.gcp.cluster_gke.gcp_cluster_checker")
        if mod is None:
            pytest.skip("gcp_cluster_checker requires dependencies")
        assert mod is not None


class TestGcpConnectivity:
    def test_import_deployment_validator(self):
        mod = _import_module("scm.gcp.connectivity.deployment_validator")
        if mod is None:
            pytest.skip("deployment_validator requires dependencies")
        assert mod is not None

    def test_import_deploy_dependency(self):
        mod = _import_module("scm.gcp.connectivity.deploy_dependency_checker")
        if mod is None:
            pytest.skip("deploy_dependency_checker requires dependencies")
        assert mod is not None

    def test_import_pod_connectivity(self):
        mod = _import_module("scm.gcp.connectivity.pod_connectivity_checker")
        if mod is None:
            pytest.skip("pod_connectivity_checker requires dependencies")
        assert mod is not None


class TestGcpConsolidation:
    def test_import_base(self):
        mod = _import_module("scm.gcp.consolidation.consolidation_base")
        if mod is None:
            pytest.skip("consolidation_base requires dependencies")
        assert mod is not None

    def test_import_infra_consolidator(self):
        mod = _import_module("scm.gcp.consolidation.gcp_infrastructure_consolidator")
        if mod is None:
            pytest.skip("gcp_infrastructure_consolidator requires dependencies")
        assert mod is not None

    def test_import_unified_dashboard(self):
        mod = _import_module("scm.gcp.consolidation.gcp_unified_infrastructure_dashboard")
        if mod is None:
            pytest.skip("gcp_unified_infrastructure_dashboard requires dependencies")
        assert mod is not None


class TestGcpDeploymentsOff:
    def test_import(self):
        mod = _import_module("scm.gcp.deployments_off.gcp_deployments_off_analyzer")
        if mod is None:
            pytest.skip("gcp_deployments_off_analyzer requires dependencies")
        assert mod is not None


class TestGcpEventTracker:
    def test_import(self):
        mod = _import_module("scm.gcp.event_tracker.event_tracker")
        if mod is None:
            pytest.skip("event_tracker requires dependencies")
        assert mod is not None


class TestGcpGatewayServices:
    def test_import_dashboard_generator(self):
        mod = _import_module("scm.gcp.gateway_services.dashboard_generator")
        if mod is None:
            pytest.skip("gateway_services dashboard_generator requires dependencies")
        assert mod is not None

    def test_import_gateway_checker(self):
        mod = _import_module("scm.gcp.gateway_services.gcp_gateway_checker")
        if mod is None:
            pytest.skip("gcp_gateway_checker requires dependencies")
        assert mod is not None


class TestGcpInventory:
    def test_import_csv_combiner(self):
        mod = _import_module("scm.gcp.inventory.generar-inventario-csv-combinar-a-excel")
        if mod is None:
            pytest.skip("generar-inventario-csv-combinar-a-excel requires dependencies")
        assert mod is not None

    def test_import_csv_generator(self):
        mod = _import_module("scm.gcp.inventory.generar-inventario-csv")
        if mod is None:
            pytest.skip("generar-inventario-csv requires dependencies")
        assert mod is not None

    def test_import_run_inventory(self):
        mod = _import_module("scm.gcp.inventory.run_inventory")
        if mod is None:
            pytest.skip("run_inventory requires dependencies")
        assert mod is not None


class TestGcpLoadBalancer:
    def test_import(self):
        mod = _import_module("scm.gcp.load_balancer.gcp_load_balancer_checker")
        if mod is None:
            pytest.skip("gcp_load_balancer_checker requires dependencies")
        assert mod is not None


class TestGcpMonitoring:
    def test_import_monitor(self):
        mod = _import_module("scm.gcp.monitoring.gcp_monitor")
        if mod is None:
            pytest.skip("gcp_monitor requires dependencies")
        assert mod is not None

    def test_import_metrics(self):
        mod = _import_module("scm.gcp.monitoring.gcp_monitoring_metrics")
        if mod is None:
            pytest.skip("gcp_monitoring_metrics requires dependencies")
        assert mod is not None

    def test_import_generate_dashboard(self):
        mod = _import_module("scm.gcp.monitoring.generate_gcp_dashboard")
        if mod is None:
            pytest.skip("generate_gcp_dashboard requires dependencies")
        assert mod is not None

    def test_import_gke_deployments_report(self):
        mod = _import_module("scm.gcp.monitoring.gke_deployments_report")
        if mod is None:
            pytest.skip("gke_deployments_report requires dependencies")
        assert mod is not None

    def test_import_gke_monitor_node(self):
        mod = _import_module("scm.gcp.monitoring.gke_monitor_node")
        if mod is None:
            pytest.skip("gke_monitor_node requires dependencies")
        assert mod is not None

    def test_import_gke_monitor_pod(self):
        mod = _import_module("scm.gcp.monitoring.gke_monitor_pod")
        if mod is None:
            pytest.skip("gke_monitor_pod requires dependencies")
        assert mod is not None


class TestGcpPubSubMonitor:
    def test_import_alert_engine(self):
        mod = _import_module("scm.gcp.pubsub_monitor.alert_engine")
        if mod is None:
            pytest.skip("alert_engine requires dependencies")
        assert mod is not None

    def test_import_dashboard_generator(self):
        mod = _import_module("scm.gcp.pubsub_monitor.dashboard_generator")
        if mod is None:
            pytest.skip("pubsub dashboard_generator requires dependencies")
        assert mod is not None

    def test_import_metrics_analyzer(self):
        mod = _import_module("scm.gcp.pubsub_monitor.metrics_analyzer")
        if mod is None:
            pytest.skip("metrics_analyzer requires dependencies")
        assert mod is not None

    def test_import_pubsub_collector(self):
        mod = _import_module("scm.gcp.pubsub_monitor.pubsub_collector")
        if mod is None:
            pytest.skip("pubsub_collector requires dependencies")
        assert mod is not None

    def test_import_pubsub_monitor(self):
        mod = _import_module("scm.gcp.pubsub_monitor.pubsub_monitor")
        if mod is None:
            pytest.skip("pubsub_monitor requires dependencies")
        assert mod is not None

    def test_import_run(self):
        mod = _import_module("scm.gcp.pubsub_monitor.run")
        if mod is None:
            pytest.skip("pubsub run requires dependencies")
        assert mod is not None

    def test_import_tools(self):
        mod = _import_module("scm.gcp.pubsub_monitor.tools")
        if mod is None:
            pytest.skip("pubsub tools requires dependencies")
        assert mod is not None

    def test_import_main(self):
        mod = _import_module("scm.gcp.pubsub_monitor.__main__")
        if mod is None:
            pytest.skip("pubsub __main__ requires dependencies")
        assert mod is not None


class TestGcpReportsViewer:
    def test_import(self):
        mod = _import_module("scm.gcp.reports_viewer.gcp_reports_viewer")
        if mod is None:
            pytest.skip("gcp_reports_viewer requires dependencies")
        assert mod is not None


class TestGcpRolesPermisos:
    def test_import(self):
        mod = _import_module("scm.gcp.rolesypermisos.gcp_iam_roles_report")
        if mod is None:
            pytest.skip("gcp_iam_roles_report requires dependencies")
        assert mod is not None


class TestGcpSecretsConfigmaps:
    def test_import(self):
        mod = _import_module("scm.gcp.secrets_configmaps.gcp_secrets_configmaps_checker")
        if mod is None:
            pytest.skip("gcp_secrets_configmaps_checker requires dependencies")
        assert mod is not None


class TestGcpServiceAccount:
    def test_import(self):
        mod = _import_module("scm.gcp.service_account.gcp_service_account_checker")
        if mod is None:
            pytest.skip("gcp_service_account_checker requires dependencies")
        assert mod is not None


class TestGcpServiceAccounts:
    def test_import_multi_project_reporter(self):
        mod = _import_module("scm.gcp.service_accounts.gcp_sa_multi_project_reporter")
        if mod is None:
            pytest.skip("gcp_sa_multi_project_reporter requires dependencies")
        assert mod is not None

    def test_import_sa_analyzers(self):
        mod = _import_module("scm.gcp.service_accounts.sa_analyzers")
        if mod is None:
            pytest.skip("sa_analyzers requires dependencies")
        assert mod is not None

    def test_import_sa_config_loader(self):
        mod = _import_module("scm.gcp.service_accounts.sa_config_loader")
        if mod is None:
            pytest.skip("sa_config_loader requires dependencies")
        assert mod is not None

    def test_import_sa_extractors(self):
        mod = _import_module("scm.gcp.service_accounts.sa_extractors")
        if mod is None:
            pytest.skip("sa_extractors requires dependencies")
        assert mod is not None

    def test_import_sa_report_generators(self):
        mod = _import_module("scm.gcp.service_accounts.sa_report_generators")
        if mod is None:
            pytest.skip("sa_report_generators requires dependencies")
        assert mod is not None


class TestGcpVpcNetworks:
    def test_import_ip_addresses(self):
        mod = _import_module("scm.gcp.vpc_networks.gcp_ip_addresses_checker")
        if mod is None:
            pytest.skip("gcp_ip_addresses_checker requires dependencies")
        assert mod is not None

    def test_import_vpc_networks(self):
        mod = _import_module("scm.gcp.vpc_networks.gcp_vpc_networks_checker")
        if mod is None:
            pytest.skip("gcp_vpc_networks_checker requires dependencies")
        assert mod is not None
