#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Secret Manager functionality in deploy_dependency_checker.py
"""

import unittest
import sys
import os

# Add parent directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deploy_dependency_checker import (
    parse_secret_manager_references,
    parse_connection_values,
    _make_connection_dict
)


class TestSecretManagerParsing(unittest.TestCase):
    """Test Secret Manager reference parsing from ConfigMap values."""

    def test_parse_secret_manager_yaml_format(self):
        """Test parsing YAML-formatted Secret Manager references."""
        yaml_content = """
connections:
    timeout: 30000
    readTimeout: 30000
    maxAttempts: 3
    retryTimeInterval: 1000
    secretManager:
      projectId: cpl-oms-qa-08062023
      secrets:
        reservation:
          name: secretpscomitemstransition
          version: latest
        itemtocanonical:
          name: secretItemtocanonical
          version: latest
"""
        results = parse_secret_manager_references(yaml_content)
        
        self.assertEqual(len(results), 2)
        
        # Check first secret
        self.assertEqual(results[0]['connection_key'], 'reservation')
        self.assertEqual(results[0]['project_id'], 'cpl-oms-qa-08062023')
        self.assertEqual(results[0]['secret_name'], 'secretpscomitemstransition')
        self.assertEqual(results[0]['secret_version'], 'latest')
        
        # Check second secret
        self.assertEqual(results[1]['connection_key'], 'itemtocanonical')
        self.assertEqual(results[1]['project_id'], 'cpl-oms-qa-08062023')
        self.assertEqual(results[1]['secret_name'], 'secretItemtocanonical')
        self.assertEqual(results[1]['secret_version'], 'latest')

    def test_parse_secret_manager_no_references(self):
        """Test that non-Secret Manager content returns empty list."""
        normal_content = """
database:
  host: localhost
  port: 5432
  name: mydb
"""
        results = parse_secret_manager_references(normal_content)
        self.assertEqual(len(results), 0)

    def test_parse_secret_manager_empty_string(self):
        """Test empty string returns empty list."""
        results = parse_secret_manager_references("")
        self.assertEqual(len(results), 0)

    def test_parse_secret_manager_none(self):
        """Test None value returns empty list."""
        results = parse_secret_manager_references(None)
        self.assertEqual(len(results), 0)


class TestConnectionDict(unittest.TestCase):
    """Test connection dictionary creation."""

    def test_make_connection_dict_basic(self):
        """Test basic connection dict without Secret Manager."""
        conn = _make_connection_dict(
            configmap='my-config',
            key='database-url',
            host='10.0.0.1',
            port=5432,
            raw_value='postgresql://10.0.0.1:5432/mydb',
            status='PENDING',
            message='Pending validation',
            db_type='postgresql'
        )
        
        self.assertEqual(conn['configmap'], 'my-config')
        self.assertEqual(conn['key'], 'database-url')
        self.assertEqual(conn['host'], '10.0.0.1')
        self.assertEqual(conn['port'], 5432)
        self.assertEqual(conn['db_type'], 'postgresql')
        self.assertEqual(conn['status'], 'PENDING')
        self.assertEqual(conn['source_type'], 'configmap')
        self.assertEqual(conn['secret_project'], '')
        self.assertEqual(conn['secret_name'], '')

    def test_make_connection_dict_with_secret_manager(self):
        """Test connection dict with Secret Manager metadata."""
        conn = _make_connection_dict(
            configmap='my-config',
            key='connections',
            host='10.148.110.66',
            port=5432,
            raw_value='{"host":"10.148.110.66","port":5432}',
            status='PENDING',
            message='Pending validation',
            db_type='postgresql',
            source_type='secretmanager',
            secret_project='cpl-oms-qa-08062023',
            secret_name='secretItemtocanonical',
            secret_version='1',
            sm_key='itemtocanonical'
        )
        
        self.assertEqual(conn['source_type'], 'secretmanager')
        self.assertEqual(conn['secret_project'], 'cpl-oms-qa-08062023')
        self.assertEqual(conn['secret_name'], 'secretItemtocanonical')
        self.assertEqual(conn['secret_version'], '1')
        self.assertEqual(conn['sm_key'], 'itemtocanonical')


class TestConnectionValueParsing(unittest.TestCase):
    """Test parsing of connection values from secrets."""

    def test_parse_json_secret_value(self):
        """Test parsing JSON secret value with host and port."""
        secret_json = '{"host":"10.148.110.66","user":"sysmulesoft","pass":"#ZAQwsx!","db":"itemtocanonical","port":5432,"type":"postgresql"}'
        
        # This would be parsed as a string, not JSON in parse_connection_values
        # The JSON parsing happens in collect_connections
        results = parse_connection_values(secret_json)
        
        # Should find host:port pattern
        self.assertGreaterEqual(len(results), 1)
        found = False
        for host, port, raw, db_type in results:
            if host == '10.148.110.66' and port == 5432:
                found = True
                break
        self.assertTrue(found, "Should find host:port from JSON string")


if __name__ == '__main__':
    unittest.main()
