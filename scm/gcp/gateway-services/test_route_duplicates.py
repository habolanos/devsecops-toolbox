#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para deteccion de HTTPRoutes duplicadas por Gateway.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gcp_gateway_checker import (
    detect_route_duplicates,
    _extract_route_keys,
    _paths_overlap,
    _normalize_headers,
    _normalize_query_params,
    _normalize_path,
)


def _make_route(name, namespace, hostnames, parent_refs, rules=None):
    """Factory para crear HTTPRoute dicts de prueba."""
    route = {
        'metadata': {'name': name, 'namespace': namespace},
        'spec': {
            'hostnames': hostnames,
            'parentRefs': parent_refs,
        }
    }
    if rules is not None:
        route['spec']['rules'] = rules
    return route


class TestPathsOverlap(unittest.TestCase):

    def test_identical_paths(self):
        self.assertTrue(_paths_overlap('/api', 'PathPrefix', '/api', 'PathPrefix'))

    def test_prefix_overlap(self):
        self.assertTrue(_paths_overlap('/api', 'PathPrefix', '/api/v1', 'PathPrefix'))
        self.assertTrue(_paths_overlap('/api/v1', 'PathPrefix', '/api', 'PathPrefix'))

    def test_no_overlap(self):
        self.assertFalse(_paths_overlap('/api', 'PathPrefix', '/web', 'PathPrefix'))

    def test_wildcard_matches_all(self):
        self.assertTrue(_paths_overlap('*', 'PathPrefix', '/api', 'PathPrefix'))
        self.assertTrue(_paths_overlap('/api', 'PathPrefix', '*', 'PathPrefix'))

    def test_exact_vs_exact_same(self):
        self.assertTrue(_paths_overlap('/api', 'Exact', '/api', 'Exact'))

    def test_exact_vs_exact_different(self):
        self.assertFalse(_paths_overlap('/api', 'Exact', '/api/v1', 'Exact'))

    def test_exact_inside_prefix(self):
        self.assertTrue(_paths_overlap('/api/v1', 'Exact', '/api', 'PathPrefix'))
        self.assertTrue(_paths_overlap('/api', 'PathPrefix', '/api/v1', 'Exact'))

    def test_prefix_no_false_positive_non_segment(self):
        self.assertFalse(_paths_overlap('/api', 'PathPrefix', '/api-v1', 'PathPrefix'))
        self.assertFalse(_paths_overlap('/api-v1', 'PathPrefix', '/api', 'PathPrefix'))

    def test_prefix_root_matches_all(self):
        self.assertTrue(_paths_overlap('/', 'PathPrefix', '/api', 'PathPrefix'))
        self.assertTrue(_paths_overlap('/api', 'PathPrefix', '/', 'PathPrefix'))

    def test_prefix_trailing_slash_normalized(self):
        self.assertTrue(_paths_overlap('/api/', 'PathPrefix', '/api', 'PathPrefix'))
        self.assertTrue(_paths_overlap('/api', 'PathPrefix', '/api/', 'PathPrefix'))

    def test_exact_inside_prefix_root(self):
        self.assertTrue(_paths_overlap('/api/v1', 'Exact', '/', 'PathPrefix'))
        self.assertTrue(_paths_overlap('/', 'PathPrefix', '/api/v1', 'Exact'))

    def test_exact_not_inside_prefix_non_segment(self):
        self.assertFalse(_paths_overlap('/api-v1', 'Exact', '/api', 'PathPrefix'))
        self.assertFalse(_paths_overlap('/api', 'PathPrefix', '/api-v1', 'Exact'))


class TestExtractRouteKeys(unittest.TestCase):

    def test_simple_route(self):
        route = _make_route(
            'route1', 'ns1',
            ['api.example.com'],
            [{'name': 'gw1', 'namespace': 'gw-ns'}],
            rules=[{
                'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'},
                    'method': 'GET'
                }]
            }]
        )
        keys = _extract_route_keys(route)
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]['gateway_name'], 'gw1')
        self.assertEqual(keys[0]['gateway_ns'], 'gw-ns')
        self.assertEqual(keys[0]['hostname'], 'api.example.com')
        self.assertEqual(keys[0]['path'], '/api')
        self.assertEqual(keys[0]['method'], 'GET')
        self.assertEqual(keys[0]['section'], '*')
        self.assertEqual(keys[0]['headers'], frozenset())
        self.assertEqual(keys[0]['query_params'], frozenset())

    def test_route_with_section_name(self):
        route = _make_route(
            'route1', 'ns1',
            ['api.example.com'],
            [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
            rules=[{
                'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'}
                }]
            }]
        )
        keys = _extract_route_keys(route)
        self.assertEqual(keys[0]['section'], 'https')

    def test_route_no_rules(self):
        route = _make_route(
            'route1', 'ns1',
            ['api.example.com'],
            [{'name': 'gw1'}]
        )
        keys = _extract_route_keys(route)
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]['path'], '*')
        self.assertEqual(keys[0]['method'], '*')
        self.assertEqual(keys[0]['headers'], frozenset())
        self.assertEqual(keys[0]['query_params'], frozenset())

    def test_multiple_hostnames_and_rules(self):
        route = _make_route(
            'route1', 'ns1',
            ['api.example.com', 'admin.example.com'],
            [{'name': 'gw1'}],
            rules=[
                {'matches': [{'path': {'value': '/api'}}]},
                {'matches': [{'path': {'value': '/admin'}}]}
            ]
        )
        keys = _extract_route_keys(route)
        self.assertEqual(len(keys), 4)

    def test_route_with_headers_and_query_params(self):
        route = _make_route(
            'route1', 'ns1',
            ['api.example.com'],
            [{'name': 'gw1', 'namespace': 'gw-ns'}],
            rules=[{
                'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'},
                    'headers': [
                        {'name': 'X-Service', 'value': 'A', 'type': 'Exact'},
                        {'name': 'X-Version', 'value': '1', 'type': 'Exact'}
                    ],
                    'queryParams': [
                        {'name': 'debug', 'value': 'true', 'type': 'Exact'}
                    ]
                }]
            }]
        )
        keys = _extract_route_keys(route)
        self.assertEqual(len(keys), 1)
        self.assertEqual(len(keys[0]['headers']), 2)
        self.assertIn(('Exact', 'X-Service', 'A'), keys[0]['headers'])
        self.assertIn(('Exact', 'X-Version', '1'), keys[0]['headers'])
        self.assertEqual(len(keys[0]['query_params']), 1)
        self.assertIn(('Exact', 'debug', 'true'), keys[0]['query_params'])

    def test_no_parent_refs(self):
        route = _make_route(
            'route1', 'ns1',
            ['api.example.com'],
            []
        )
        keys = _extract_route_keys(route)
        self.assertEqual(len(keys), 0)


class TestDetectRouteDuplicates(unittest.TestCase):

    def test_no_routes(self):
        self.assertEqual(detect_route_duplicates([]), [])

    def test_no_duplicates(self):
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
                rules=[{'matches': [{'path': {'value': '/api'}}]}]
            ),
            _make_route(
                'route2', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
                rules=[{'matches': [{'path': {'value': '/web'}}]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        self.assertEqual(len(conflicts), 0)

    def test_critical_duplicate(self):
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{'path': {'value': '/api'}, 'method': 'GET'}]}]
            ),
            _make_route(
                'route2', 'ns2', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{'path': {'value': '/api'}, 'method': 'GET'}]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['severity'], 'CRITICAL')
        self.assertEqual(conflicts[0]['path'], '/api')
        self.assertEqual(conflicts[0]['method'], 'GET')

    def test_high_path_overlap(self):
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
                rules=[{'matches': [{'path': {'type': 'PathPrefix', 'value': '/api'}}]}]
            ),
            _make_route(
                'route2', 'ns2', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
                rules=[{'matches': [{'path': {'type': 'PathPrefix', 'value': '/api/v1'}}]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        high_conflicts = [c for c in conflicts if c['severity'] == 'HIGH']
        self.assertGreaterEqual(len(high_conflicts), 1)
        self.assertIn('~', high_conflicts[0]['path'])

    def test_medium_same_hostname_no_section(self):
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{'path': {'value': '/api'}}]}]
            ),
            _make_route(
                'route2', 'ns2', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{'path': {'value': '/web'}}]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        medium_conflicts = [c for c in conflicts if c['severity'] == 'MEDIUM']
        self.assertEqual(len(medium_conflicts), 1)

    def test_different_gateways_no_conflict(self):
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{'path': {'value': '/api'}, 'method': 'GET'}]}]
            ),
            _make_route(
                'route2', 'ns2', ['api.example.com'],
                [{'name': 'gw2', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{'path': {'value': '/api'}, 'method': 'GET'}]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        self.assertEqual(len(conflicts), 0)

    def test_different_hostnames_no_conflict(self):
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
                rules=[{'matches': [{'path': {'value': '/api'}, 'method': 'GET'}]}]
            ),
            _make_route(
                'route2', 'ns2', ['web.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
                rules=[{'matches': [{'path': {'value': '/api'}, 'method': 'GET'}]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        self.assertEqual(len(conflicts), 0)

    def test_same_route_no_self_conflict(self):
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[
                    {'matches': [{'path': {'value': '/api'}, 'method': 'GET'}]},
                    {'matches': [{'path': {'value': '/api'}, 'method': 'GET'}]}
                ]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        self.assertEqual(len(conflicts), 0)

    def test_severity_ordering(self):
        routes = [
            _make_route(
                'route-a', 'ns1', ['host.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{'path': {'value': '/x'}, 'method': 'GET'}]}]
            ),
            _make_route(
                'route-b', 'ns2', ['host.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{'path': {'value': '/x'}, 'method': 'GET'}]}]
            ),
            _make_route(
                'route-c', 'ns3', ['host.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{'path': {'type': 'PathPrefix', 'value': '/x'}}]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        severities = [c['severity'] for c in conflicts]
        self.assertEqual(severities, sorted(severities, key=lambda s: {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2}[s]))


class TestHeadersQueryParamsDifferentiation(unittest.TestCase):
    """Tests para verificar que headers y queryParams diferencian routes."""

    def test_same_path_different_headers_no_conflict(self):
        """Dos routes con mismo path pero diferentes headers NO son duplicadas."""
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/ds-scm-wm-iteminventory/api/v1'},
                    'headers': [{'name': 'X-Service', 'value': 'A', 'type': 'Exact'}]
                }]}]
            ),
            _make_route(
                'route2', 'ns2', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/ds-scm-wm-iteminventory/api/v1'},
                    'headers': [{'name': 'X-Service', 'value': 'B', 'type': 'Exact'}]
                }]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        self.assertEqual(len(conflicts), 0)

    def test_same_path_same_headers_critical_conflict(self):
        """Dos routes con mismo path y mismos headers SI son duplicadas (CRITICAL)."""
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'},
                    'headers': [{'name': 'X-Service', 'value': 'A', 'type': 'Exact'}]
                }]}]
            ),
            _make_route(
                'route2', 'ns2', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'},
                    'headers': [{'name': 'X-Service', 'value': 'A', 'type': 'Exact'}]
                }]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['severity'], 'CRITICAL')

    def test_same_path_different_query_params_no_conflict(self):
        """Dos routes con mismo path pero diferentes queryParams NO son duplicadas."""
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'},
                    'queryParams': [{'name': 'debug', 'value': 'true', 'type': 'Exact'}]
                }]}]
            ),
            _make_route(
                'route2', 'ns2', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'},
                    'queryParams': [{'name': 'debug', 'value': 'false', 'type': 'Exact'}]
                }]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        self.assertEqual(len(conflicts), 0)

    def test_same_path_one_with_headers_one_without_no_conflict(self):
        """Route con headers y otra sin headers en mismo path NO son duplicadas."""
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'},
                    'headers': [{'name': 'X-Service', 'value': 'A', 'type': 'Exact'}]
                }]}]
            ),
            _make_route(
                'route2', 'ns2', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'}
                }]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        self.assertEqual(len(conflicts), 0)

    def test_prefix_overlap_different_headers_no_high_conflict(self):
        """PathPrefix solapados con diferentes headers NO generan HIGH."""
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'},
                    'headers': [{'name': 'X-Service', 'value': 'A', 'type': 'Exact'}]
                }]}]
            ),
            _make_route(
                'route2', 'ns2', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api/v1'},
                    'headers': [{'name': 'X-Service', 'value': 'B', 'type': 'Exact'}]
                }]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        high_conflicts = [c for c in conflicts if c['severity'] == 'HIGH']
        self.assertEqual(len(high_conflicts), 0)

    def test_prefix_overlap_same_headers_high_conflict(self):
        """PathPrefix solapados con mismos headers SI generan HIGH."""
        routes = [
            _make_route(
                'route1', 'ns1', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api'},
                    'headers': [{'name': 'X-Service', 'value': 'A', 'type': 'Exact'}]
                }]}]
            ),
            _make_route(
                'route2', 'ns2', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns', 'sectionName': 'https'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/api/v1'},
                    'headers': [{'name': 'X-Service', 'value': 'A', 'type': 'Exact'}]
                }]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        high_conflicts = [c for c in conflicts if c['severity'] == 'HIGH']
        self.assertGreaterEqual(len(high_conflicts), 1)

    def test_real_world_example_no_false_positive(self):
        """Caso real: mismo PathPrefix sin headers/queryParams en diferentes routes."""
        routes = [
            _make_route(
                'route-inv', 'ns-scm', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/ds-scm-wm-iteminventory/api/v1'}
                }]}]
            ),
            _make_route(
                'route-inv-2', 'ns-scm', ['api.example.com'],
                [{'name': 'gw1', 'namespace': 'gw-ns'}],
                rules=[{'matches': [{
                    'path': {'type': 'PathPrefix', 'value': '/ds-scm-wm-iteminventory/api/v1'}
                }]}]
            ),
        ]
        conflicts = detect_route_duplicates(routes)
        critical = [c for c in conflicts if c['severity'] == 'CRITICAL']
        self.assertEqual(len(critical), 1)
        self.assertEqual(critical[0]['headers'], '*')
        self.assertEqual(critical[0]['query_params'], '*')


class TestNormalizeHeaders(unittest.TestCase):

    def test_empty_headers(self):
        self.assertEqual(_normalize_headers([]), frozenset())
        self.assertEqual(_normalize_headers(None), frozenset())

    def test_single_header(self):
        result = _normalize_headers([{'name': 'X-Service', 'value': 'A', 'type': 'Exact'}])
        self.assertEqual(result, frozenset({('Exact', 'X-Service', 'A')}))

    def test_multiple_headers(self):
        result = _normalize_headers([
            {'name': 'X-Service', 'value': 'A', 'type': 'Exact'},
            {'name': 'X-Version', 'value': '1', 'type': 'Exact'}
        ])
        self.assertEqual(len(result), 2)

    def test_default_type_is_exact(self):
        result = _normalize_headers([{'name': 'X-Service', 'value': 'A'}])
        self.assertIn(('Exact', 'X-Service', 'A'), result)

    def test_order_independent(self):
        h1 = _normalize_headers([
            {'name': 'A', 'value': '1', 'type': 'Exact'},
            {'name': 'B', 'value': '2', 'type': 'Exact'}
        ])
        h2 = _normalize_headers([
            {'name': 'B', 'value': '2', 'type': 'Exact'},
            {'name': 'A', 'value': '1', 'type': 'Exact'}
        ])
        self.assertEqual(h1, h2)


class TestNormalizeQueryParams(unittest.TestCase):

    def test_empty_query_params(self):
        self.assertEqual(_normalize_query_params([]), frozenset())
        self.assertEqual(_normalize_query_params(None), frozenset())

    def test_single_query_param(self):
        result = _normalize_query_params([{'name': 'debug', 'value': 'true', 'type': 'Exact'}])
        self.assertEqual(result, frozenset({('Exact', 'debug', 'true')}))

    def test_order_independent(self):
        q1 = _normalize_query_params([
            {'name': 'a', 'value': '1', 'type': 'Exact'},
            {'name': 'b', 'value': '2', 'type': 'Exact'}
        ])
        q2 = _normalize_query_params([
            {'name': 'b', 'value': '2', 'type': 'Exact'},
            {'name': 'a', 'value': '1', 'type': 'Exact'}
        ])
        self.assertEqual(q1, q2)


class TestNormalizePath(unittest.TestCase):

    def test_root_unchanged(self):
        self.assertEqual(_normalize_path('/'), '/')

    def test_wildcard_unchanged(self):
        self.assertEqual(_normalize_path('*'), '*')

    def test_trailing_slash_removed(self):
        self.assertEqual(_normalize_path('/api/'), '/api')
        self.assertEqual(_normalize_path('/api/v1/'), '/api/v1')

    def test_no_trailing_slash_unchanged(self):
        self.assertEqual(_normalize_path('/api'), '/api')


if __name__ == '__main__':
    unittest.main()
