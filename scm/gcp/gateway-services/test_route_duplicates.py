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


if __name__ == '__main__':
    unittest.main()
