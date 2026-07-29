"""
Tests unitarios para dashboard_generator.py
"""
import os
import json
import tempfile
import unittest
from datetime import datetime

from dashboard_generator import generate_dashboard


class TestDashboardGenerator(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.output_path = os.path.join(self.tmpdir, "test_dashboard.html")
        self.revision_time = "2026-07-29 12:00:00 (UTC-05:00)"
        self.project_id = "test-project-123"

    def _sample_results(self, **overrides):
        defaults = {
            'gateways': [
                {'name': 'gw-1', 'status': 'Healthy', 'gateway_class': 'gke-l7-ril',
                 'type': 'Single', 'load_balancer': 'lb-1', 'ip_addresses': '10.0.0.1',
                 'namespace': 'default', 'ports': '80,443', 'cluster': 'cluster-a',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
                {'name': 'gw-2', 'status': 'Unhealthy', 'gateway_class': 'gke-l7-ril',
                 'type': 'Multi', 'load_balancer': 'lb-2', 'ip_addresses': '10.0.0.2',
                 'namespace': 'prod', 'ports': '80', 'cluster': 'cluster-b',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
            ],
            'routes': [
                {'name': 'route-1', 'namespace': 'default', 'hostnames': 'api.example.com',
                 'date_created': '2026-01-01', 'rules_count': 2,
                 'path_prefix': '/api/v1', 'method': 'GET', 'headers': 'X-Service=A', 'query_params': '*',
                 'attached_gateways': 'gw-1', 'has_gateway': True, 'cluster': 'cluster-a',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
                {'name': 'route-2', 'namespace': 'prod', 'hostnames': 'svc.example.com',
                 'date_created': '2026-02-01', 'rules_count': 0,
                 'path_prefix': '*', 'method': '*', 'headers': '*', 'query_params': '*',
                 'attached_gateways': '', 'has_gateway': False, 'cluster': 'cluster-b',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
            ],
            'services': [
                {'name': 'svc-1', 'status': 'OK', 'type': 'ClusterIP',
                 'endpoints': '10.0.1.1', 'pods_ready': 3, 'pods_total': 3,
                 'namespace': 'default', 'cluster': 'cluster-a',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
                {'name': 'svc-2', 'status': 'OK', 'type': 'ClusterIP',
                 'endpoints': '10.0.1.2', 'pods_ready': 1, 'pods_total': 3,
                 'namespace': 'prod', 'cluster': 'cluster-b',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
                {'name': 'svc-3', 'status': 'Pending', 'type': 'ClusterIP',
                 'endpoints': 'None', 'pods_ready': 0, 'pods_total': 0,
                 'namespace': 'prod', 'cluster': 'cluster-b',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
            ],
            'policies': [
                {'name': 'pol-1', 'status': 'Healthy', 'kind': 'HealthCheckPolicy',
                 'policy_type': 'HTTP health check', 'target_kind': 'Gateway',
                 'target_name': 'gw-1', 'namespace': 'default',
                 'date_created': '2026-01-01', 'cluster': 'cluster-a',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
            ],
            'duplicates': [
                {'severity': 'CRITICAL', 'gateway': 'default/gw-1', 'listener': 'http',
                 'hostname': 'api.example.com', 'path': '/api', 'method': 'GET',
                 'headers': 'X-Service=A', 'query_params': '*',
                 'route_1': 'default/route-1', 'route_2': 'default/route-3',
                 'conflict_type': 'Duplicidad exacta', 'cluster': 'cluster-a',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
                {'severity': 'HIGH', 'gateway': 'default/gw-1', 'listener': 'http',
                 'hostname': 'api.example.com', 'path': '/api ~ /api/v1', 'method': '*',
                 'headers': '*', 'query_params': 'debug=true',
                 'route_1': 'default/route-1', 'route_2': 'default/route-2',
                 'conflict_type': 'Paths solapados', 'cluster': 'cluster-a',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
                {'severity': 'MEDIUM', 'gateway': 'prod/gw-2', 'listener': '*',
                 'hostname': 'svc.example.com', 'path': '*', 'method': '*',
                 'headers': '*', 'query_params': '*',
                 'route_1': 'prod/route-2', 'route_2': 'prod/route-4',
                 'conflict_type': 'Mismo hostname sin sectionName', 'cluster': 'cluster-b',
                 'revision_time': '2026-07-29 12:00:00 (UTC-05:00)'},
            ],
        }
        defaults.update(overrides)
        return defaults

    def test_generates_html_file(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith('.html'))

    def test_html_contains_project_id(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn(self.project_id, content)

    def test_html_contains_revision_time(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn(self.revision_time, content)

    def test_html_contains_gateway_names(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('gw-1', content)
        self.assertIn('gw-2', content)

    def test_html_contains_route_names(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('route-1', content)
        self.assertIn('route-2', content)

    def test_html_contains_service_names(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('svc-1', content)
        self.assertIn('svc-2', content)
        self.assertIn('svc-3', content)

    def test_html_contains_policy_names(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('pol-1', content)

    def test_html_contains_duplicate_info(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('CRITICAL', content)
        self.assertIn('Duplicidad exacta', content)

    def test_empty_results(self):
        results = {k: [] for k in ['gateways', 'routes', 'services', 'policies', 'duplicates']}
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        self.assertTrue(os.path.exists(path))
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('No se detectaron Gateways', content)
        self.assertIn('No se detectaron HTTPRoutes', content)
        self.assertIn('No se detectaron Services', content)
        self.assertIn('No se detectaron Policies', content)
        self.assertIn('No se detectaron duplicidades', content)

    def test_html_has_tabs(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('tab-gateways', content)
        self.assertIn('tab-routes', content)
        self.assertIn('tab-services', content)
        self.assertIn('tab-policies', content)
        self.assertIn('tab-duplicates', content)

    def test_html_has_cards(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('Gateways Healthy', content)
        self.assertIn('HTTPRoutes Healthy', content)
        self.assertIn('Services Healthy', content)
        self.assertIn('Duplicates CRITICAL', content)

    def test_html_escapes_xss(self):
        results = self._sample_results()
        results['gateways'][0]['name'] = '<script>alert("xss")</script>'
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertNotIn('<script>alert', content)
        self.assertIn('&lt;script&gt;', content)

    def test_clusters_scanned_displayed(self):
        results = self._sample_results()
        clusters = ['cluster-a', 'cluster-b']
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path, clusters)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('cluster-a', content)
        self.assertIn('cluster-b', content)

    def test_html_has_sortable_tables(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('sortTable', content)
        self.assertIn('filterTable', content)

    def test_html_has_search_boxes(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('Buscar gateway', content)
        self.assertIn('Buscar httproute', content)
        self.assertIn('Buscar service', content)
        self.assertIn('Buscar policy', content)
        self.assertIn('Buscar conflicto', content)

    def test_html_contains_generated_at(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('Generado:', content)

    def test_html_has_load_json_button(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('Cargar JSON', content)
        self.assertIn('json-input', content)
        self.assertIn('FileReader', content)

    def test_html_has_embedded_data(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('dashboard-data', content)
        self.assertIn('dashboardData', content)

    def test_html_has_revision_time_column(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        # The revision_time from sample data should appear in table rows
        self.assertIn('2026-07-29 12:00:00', content)

    def test_html_has_detect_resource_type(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('detectResourceType', content)

    def test_html_contains_headers_and_query_params_columns(self):
        results = self._sample_results()
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('Headers', content)
        self.assertIn('Query Params', content)
        self.assertIn('X-Service=A', content)
        self.assertIn('debug=true', content)

    def test_html_duplicate_empty_colspan_13(self):
        results = self._sample_results(overrides={'duplicates': []})
        path = generate_dashboard(results, self.project_id, self.revision_time, self.output_path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('colspan="13"', content)


if __name__ == '__main__':
    unittest.main()
