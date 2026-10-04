#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Enriquecimiento GKE de la opción 1 (gcp_monitor)

Cubre la funcionalidad incorporada desde las opciones 24 (recursos por nodo)
y 2 (deployments + restarts):
- gcp_monitor._pct_to_float / _deployment_status: helpers de clasificación.
- gcp_monitor.get_node_resources: CPU/memoria por nodo, kubeconfig aislado,
  métricas ausentes (sin metrics-server) y cluster inaccesible.
- gcp_monitor.get_deployments_summary: restarts por selector, estados,
  cluster inaccesible vs. vacío.
- gcp_monitor.build_gke_cluster_enrichment: agregados nodes/deployments.
- generate_gcp_dashboard.build_node_rows / build_deployment_rows / build_kpis:
  columnas Proyecto/Cluster y totales multi-proyecto.
- generate_html_dashboard: tabs/payload/clases de resaltado de restarts.
"""

import importlib
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent
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


gcp_monitor = _import_module("scm.gcp.monitoring.gcp_monitor")
dashboard = _import_module("scm.gcp.monitoring.generate_gcp_dashboard")

requires_monitor = pytest.mark.skipif(gcp_monitor is None, reason="gcp_monitor requiere dependencias")
requires_dashboard = pytest.mark.skipif(dashboard is None, reason="generate_gcp_dashboard requiere dependencias")


def _kubectl_side_effect(mapping):
    """Devuelve output segun el comando kubectl invocado."""
    def _run(command, *args, **kwargs):
        for key, value in mapping.items():
            if key in command:
                return value
        return None
    return _run


NODES_JSON = json.dumps({'items': [
    {'metadata': {'name': 'node-1', 'labels': {'topology.kubernetes.io/zone': 'us-central1-a'}},
     'status': {'allocatable': {'cpu': '4', 'memory': '16Gi', 'pods': '110'}}},
    {'metadata': {'name': 'node-2', 'labels': {'topology.kubernetes.io/zone': 'us-central1-b'}},
     'status': {'allocatable': {'cpu': '8', 'memory': '32Gi', 'pods': '110'}}},
]})

TOP_NODES_OUT = 'node-1   200m   5%   1Gi   8%\nnode-2   4000m   50%   20Gi   65%\n'

DEPLOYMENTS_JSON = json.dumps({'items': [
    {'metadata': {'name': 'web', 'namespace': 'prod'},
     'spec': {'replicas': 2, 'selector': {'matchLabels': {'app': 'web'}}}},
    {'metadata': {'name': 'idle', 'namespace': 'prod'},
     'spec': {'replicas': 0, 'selector': {'matchLabels': {'app': 'idle'}}}},
    {'metadata': {'name': 'broken', 'namespace': 'prod'},
     'spec': {'replicas': 1, 'selector': {'matchLabels': {'app': 'broken'}}}},
]})

PODS_JSON = json.dumps({'items': [
    {'metadata': {'name': 'web-a', 'namespace': 'prod', 'labels': {'app': 'web'}},
     'status': {'phase': 'Running',
                'conditions': [{'type': 'Ready', 'status': 'True'}],
                'containerStatuses': [{'restartCount': 3}]}},
    {'metadata': {'name': 'web-b', 'namespace': 'prod', 'labels': {'app': 'web'}},
     'status': {'phase': 'Running',
                'conditions': [{'type': 'Ready', 'status': 'True'}],
                'containerStatuses': [{'restartCount': 9}, {'restartCount': 4}]}},
    # Mismo label pero otro namespace: NO debe contarse en 'web'
    {'metadata': {'name': 'web-x', 'namespace': 'other', 'labels': {'app': 'web'}},
     'status': {'phase': 'Running',
                'conditions': [{'type': 'Ready', 'status': 'True'}],
                'containerStatuses': [{'restartCount': 99}]}},
    {'metadata': {'name': 'broken-0', 'namespace': 'prod', 'labels': {'app': 'broken'}},
     'status': {'phase': 'Failed', 'containerStatuses': [{'restartCount': 1}]}},
]})


# ═══════════════════════════════════════════════════════════════════════════════
# gcp_monitor._pct_to_float / _deployment_status
# ═══════════════════════════════════════════════════════════════════════════════

@requires_monitor
def test_pct_to_float_parses_percent_strings():
    assert gcp_monitor._pct_to_float('45%') == 45.0
    assert gcp_monitor._pct_to_float('80%') == 80.0
    assert gcp_monitor._pct_to_float(12.5) == 12.5
    assert gcp_monitor._pct_to_float('N/A') == 0.0
    assert gcp_monitor._pct_to_float(None) == 0.0


@requires_monitor
def test_deployment_status_classification():
    s = gcp_monitor._deployment_status
    assert s(set(), 0, 0) == 'ScaledToZero'
    assert s({'Running'}, 2, 2) == 'Running'
    assert s({'Running', 'Failed'}, 2, 1) == 'Degraded'
    assert s({'Running', 'Pending'}, 2, 1) == 'Progressing'
    assert s(set(), 2, 0) == 'Unknown'
    assert s({'Unknown'}, 1, 0) == 'Unknown'


# ═══════════════════════════════════════════════════════════════════════════════
# gcp_monitor.get_node_resources (opcion 24 en opcion 1)
# ═══════════════════════════════════════════════════════════════════════════════

@requires_monitor
def test_get_node_resources_returns_usage_per_node():
    with patch.object(gcp_monitor, 'ensure_gke_cluster_credentials', return_value=True), \
         patch.object(gcp_monitor, 'run_kubectl_command',
                      side_effect=_kubectl_side_effect({
                          'get nodes -o json': NODES_JSON,
                          'top nodes --no-headers': TOP_NODES_OUT,
                      })):
        rows = gcp_monitor.get_node_resources('proj-1', 'cluster-a', 'us-central1')

    assert rows is not None and len(rows) == 2
    assert rows[0]['name'] == 'node-1'
    assert rows[0]['zone'] == 'us-central1-a'
    assert rows[0]['cpu_alloc'] == '4'
    assert rows[0]['cpu_used'] == '200m'
    assert rows[0]['cpu_pct'] == '5%'
    assert rows[0]['mem_pct'] == '8%'
    assert rows[0]['pods_max'] == '110'
    assert rows[1]['cpu_pct'] == '50%'


@requires_monitor
def test_get_node_resources_without_metrics_server_keeps_nodes():
    """Sin metrics-server (top falla) los nodos se listan con uso N/A, no cero falso."""
    with patch.object(gcp_monitor, 'ensure_gke_cluster_credentials', return_value=True), \
         patch.object(gcp_monitor, 'run_kubectl_command',
                      side_effect=_kubectl_side_effect({'get nodes -o json': NODES_JSON})):
        rows = gcp_monitor.get_node_resources('proj-1', 'cluster-a', 'us-central1')

    assert rows is not None and len(rows) == 2
    assert rows[0]['cpu_used'] == 'N/A'
    assert rows[0]['cpu_pct'] == 'N/A'


@requires_monitor
def test_get_node_resources_inaccessible_cluster_returns_none():
    with patch.object(gcp_monitor, 'ensure_gke_cluster_credentials', return_value=False):
        assert gcp_monitor.get_node_resources('proj-1', 'cluster-a', 'us-central1') is None


@requires_monitor
def test_get_node_resources_uses_project_scoped_context():
    """El contexto y el kubeconfig se clavean por proyecto+cluster (aislamiento)."""
    seen = {}

    def _fake_env(cluster_name, project_id=None):
        seen['kube'] = (cluster_name, project_id)
        return {'KUBECONFIG': 'x'}

    def _fake_ctx(project_id, location, cluster_name):
        seen['ctx'] = (project_id, location, cluster_name)
        return 'ctx-name'

    with patch.object(gcp_monitor, 'ensure_gke_cluster_credentials', return_value=True), \
         patch.object(gcp_monitor, 'gke_kube_env', side_effect=_fake_env), \
         patch.object(gcp_monitor, 'gke_context_name', side_effect=_fake_ctx), \
         patch.object(gcp_monitor, 'run_kubectl_command',
                      side_effect=_kubectl_side_effect({'get nodes -o json': NODES_JSON})):
        gcp_monitor.get_node_resources('proj-1', 'cluster-a', 'us-central1')

    assert seen['kube'] == ('cluster-a', 'proj-1')
    assert seen['ctx'] == ('proj-1', 'us-central1', 'cluster-a')


# ═══════════════════════════════════════════════════════════════════════════════
# gcp_monitor.get_deployments_summary (opcion 2 en opcion 1)
# ═══════════════════════════════════════════════════════════════════════════════

@requires_monitor
def test_get_deployments_summary_counts_restarts_by_selector():
    with patch.object(gcp_monitor, 'ensure_gke_cluster_credentials', return_value=True), \
         patch.object(gcp_monitor, 'run_kubectl_command',
                      side_effect=_kubectl_side_effect({
                          'get deployments --all-namespaces -o json': DEPLOYMENTS_JSON,
                          'get pods --all-namespaces -o json': PODS_JSON,
                      })):
        rows = gcp_monitor.get_deployments_summary('proj-1', 'cluster-a', 'us-central1')

    assert rows is not None and len(rows) == 3
    by_name = {r['deployment']: r for r in rows}

    web = by_name['web']
    assert web['namespace'] == 'prod'
    assert web['pods'] == '2/2'
    assert web['restarts'] == 16  # 3 + 9 + 4; el pod de 'other' no cuenta
    assert web['status'] == 'Running'

    assert by_name['idle']['status'] == 'ScaledToZero'
    assert by_name['idle']['restarts'] == 0

    broken = by_name['broken']
    assert broken['status'] == 'Degraded'
    assert broken['restarts'] == 1


@requires_monitor
def test_get_deployments_summary_empty_cluster_returns_empty_list():
    """Cluster vacío (accesible) -> lista vacía, distinguible de None (fallo)."""
    with patch.object(gcp_monitor, 'ensure_gke_cluster_credentials', return_value=True), \
         patch.object(gcp_monitor, 'run_kubectl_command',
                      side_effect=_kubectl_side_effect({
                          'get deployments --all-namespaces -o json': '{"items": []}',
                          'get pods --all-namespaces -o json': '{"items": []}',
                      })):
        rows = gcp_monitor.get_deployments_summary('proj-1', 'cluster-a', 'us-central1')

    assert rows == []


@requires_monitor
def test_get_deployments_summary_inaccessible_cluster_returns_none():
    with patch.object(gcp_monitor, 'ensure_gke_cluster_credentials', return_value=False):
        assert gcp_monitor.get_deployments_summary('proj-1', 'cluster-a', 'us-central1') is None


# ═══════════════════════════════════════════════════════════════════════════════
# gcp_monitor.build_gke_cluster_enrichment — agregados nuevos
# ═══════════════════════════════════════════════════════════════════════════════

@requires_monitor
def test_build_gke_cluster_enrichment_aggregates_nodes_and_deployments():
    cluster = {
        'name': 'cluster-a',
        'location': 'us-central1',
        'status': 'RUNNING',
        'currentMasterVersion': '1.28.0',
    }
    nodes = [
        {'name': 'n1', 'cpu_pct': '90%', 'mem_pct': '50%'},
        {'name': 'n2', 'cpu_pct': '30%', 'mem_pct': '95%'},
    ]
    deployments = [
        {'deployment': 'a', 'restarts': 12, 'status': 'Running'},
        {'deployment': 'b', 'restarts': 6, 'status': 'Running'},
        {'deployment': 'c', 'restarts': 1, 'status': 'Running'},
    ]

    with patch.object(gcp_monitor, 'ensure_gke_cluster_credentials', return_value=True), \
         patch.object(gcp_monitor, 'get_pod_count', return_value=(5, 2)), \
         patch.object(gcp_monitor, 'get_cluster_network_info', return_value={
             'pods_cidr': '10.0.0.0/24', 'services_cidr': '10.1.0.0/24', 'subnet': 'subnet-1'}), \
         patch.object(gcp_monitor, 'get_services_count', return_value=3), \
         patch.object(gcp_monitor, 'get_node_resources', return_value=nodes), \
         patch.object(gcp_monitor, 'get_deployments_summary', return_value=deployments):
        extra = gcp_monitor.build_gke_cluster_enrichment('proj-1', cluster)

    assert extra['nodes'] == nodes
    assert extra['nodes_count'] == 2
    assert extra['nodes_cpu_high'] == 1   # solo n1 >80% CPU
    assert extra['nodes_mem_high'] == 1   # solo n2 >80% mem
    assert extra['deployments'] == deployments
    assert extra['deploy_total'] == 3
    assert extra['deploy_restarts_high'] == 1  # >10
    assert extra['deploy_restarts_warn'] == 1  # >4 y <=10


@requires_monitor
def test_build_gke_cluster_enrichment_tolerates_node_deploy_failures():
    """Si nodos/deployments fallan (cluster inaccesible) el resto del dict sigue."""
    cluster = {'name': 'cluster-a', 'location': 'us-central1',
               'status': 'RUNNING', 'currentMasterVersion': '1.28.0'}

    with patch.object(gcp_monitor, 'ensure_gke_cluster_credentials', return_value=True), \
         patch.object(gcp_monitor, 'get_pod_count', return_value=(5, 0)), \
         patch.object(gcp_monitor, 'get_cluster_network_info', return_value=None), \
         patch.object(gcp_monitor, 'get_services_count', return_value=None), \
         patch.object(gcp_monitor, 'get_node_resources',
                      side_effect=RuntimeError('timeout')), \
         patch.object(gcp_monitor, 'get_deployments_summary', return_value=None):
        extra = gcp_monitor.build_gke_cluster_enrichment('proj-1', cluster)

    assert extra['nodes'] == []
    assert extra['deployments'] == []
    assert extra['deploy_total'] == 0
    assert extra['pods_running'] == 5


# ═══════════════════════════════════════════════════════════════════════════════
# generate_gcp_dashboard — filas, KPIs y render
# ═══════════════════════════════════════════════════════════════════════════════

def _json_with_gke():
    return {
        'data': {
            'proj-a': {'gke_clusters': [{
                'name': 'cluster-1', 'location': 'us-central1', 'status': 'RUNNING',
                'nodes': [
                    {'name': 'node-1', 'zone': 'us-central1-a', 'cpu_alloc': '4',
                     'cpu_used': '200m', 'cpu_pct': '5%', 'mem_alloc': '16Gi',
                     'mem_used': '1Gi', 'mem_pct': '8%', 'pods_max': '110'},
                ],
                'deployments': [
                    {'namespace': 'prod', 'deployment': 'web', 'pods': '2/2',
                     'restarts': 12, 'status': 'Running'},
                ],
            }]},
            'proj-b': {'gke_clusters': [{
                'name': 'cluster-2', 'location': 'europe-west1', 'status': 'RUNNING',
                'nodes': [
                    {'name': 'node-9', 'zone': 'europe-west1-b', 'cpu_alloc': '8',
                     'cpu_used': '4', 'cpu_pct': '55%', 'mem_alloc': '32Gi',
                     'mem_used': '20Gi', 'mem_pct': '60%', 'pods_max': '110'},
                ],
                'deployments': [
                    {'namespace': 'app', 'deployment': 'api', 'pods': '1/1',
                     'restarts': 6, 'status': 'Degraded'},
                ],
            }]},
        }
    }


@requires_dashboard
def test_build_node_rows_include_project_and_cluster():
    rows = dashboard.build_node_rows(_json_with_gke())
    assert len(rows) == 2
    by_project = {r['project_id']: r for r in rows}
    assert by_project['proj-a']['cluster'] == 'cluster-1'
    assert by_project['proj-a']['node'] == 'node-1'
    assert by_project['proj-a']['cpu_pct'] == '5%'
    assert by_project['proj-b']['cluster'] == 'cluster-2'
    assert by_project['proj-b']['resource_type'] == 'GKE'


@requires_dashboard
def test_build_deployment_rows_include_project_and_cluster():
    rows = dashboard.build_deployment_rows(_json_with_gke())
    assert len(rows) == 2
    by_project = {r['project_id']: r for r in rows}
    assert by_project['proj-a']['deployment'] == 'web'
    assert by_project['proj-a']['restarts'] == 12
    assert by_project['proj-b']['deployment'] == 'api'
    assert by_project['proj-b']['status'] == 'Degraded'
    assert by_project['proj-b']['namespace'] == 'app'


@requires_dashboard
def test_build_node_rows_empty_when_no_enrichment():
    json_data = {'data': {'proj-a': {'gke_clusters': [{'name': 'c'}]}}}
    assert dashboard.build_node_rows(json_data) == []
    assert dashboard.build_deployment_rows(json_data) == []


@requires_dashboard
def test_build_kpis_counts_nodes_and_deployments():
    kpis = dashboard.build_kpis(_json_with_gke(), [], [], [], [])
    assert kpis['total_gke_nodes'] == 2
    assert kpis['total_deployments'] == 2


@requires_dashboard
def test_generate_html_dashboard_contains_new_tabs_and_restart_styles():
    html = dashboard.generate_html_dashboard(_json_with_gke(), 'out.html')

    # Tabs y payload
    assert "data-tab=\"nodos\"" in html
    assert "data-tab=\"deployments\"" in html
    assert "dataKey: 'nodes'" in html
    assert "dataKey: 'deployments'" in html
    assert '"nodes":' in html or "'nodes':" in html

    # Resaltado de restarts (>10 rojo/blanco, >4 amarillo/negro)
    assert '.restarts-high' in html
    assert '.restarts-warn' in html
    assert "type: 'restarts'" in html
    assert 'restarts > 10' in html
    assert 'restarts > 4' in html

    # % coloreados en nodos
    assert "type: 'pct'" in html

    # Datos embebidos de las nuevas filas
    assert '"deployment": "web"' in html or "'deployment': 'web'" in html.replace('"', "'")
    assert 'node-1' in html
