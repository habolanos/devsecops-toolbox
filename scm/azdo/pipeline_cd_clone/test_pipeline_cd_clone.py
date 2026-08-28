#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para pipeline_cd_clone.py
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from scm.azdo.pipeline_cd_clone import pipeline_cd_clone as mod


class TestNormalizeOrg(unittest.TestCase):
    """Tests para normalize_org."""

    def test_plain_name(self):
        self.assertEqual(mod.normalize_org("Coppel-Retail"), "Coppel-Retail")

    def test_url_extracts_name(self):
        self.assertEqual(mod.normalize_org("https://dev.azure.com/Coppel-Retail"), "Coppel-Retail")

    def test_url_with_trailing_slash(self):
        self.assertEqual(mod.normalize_org("https://dev.azure.com/MyOrg/"), "MyOrg")


class TestCreateAuthHeader(unittest.TestCase):
    """Tests para create_auth_header."""

    def test_returns_basic_auth(self):
        header = mod.create_auth_header("mytoken123")
        self.assertTrue(header.startswith("Basic "))
        import base64
        decoded = base64.b64decode(header[6:]).decode('ascii')
        self.assertEqual(decoded, ":mytoken123")


class TestCleanDefinitionForClone(unittest.TestCase):
    """Tests para clean_definition_for_clone."""

    def setUp(self):
        self.definition = {
            "id": 2758,
            "revision": 15,
            "name": "Test-Pipeline",
            "path": "\\Pipelines\\Prod",
            "createdOn": "2026-01-01T00:00:00",
            "modifiedOn": "2026-06-01T00:00:00",
            "createdBy": {"displayName": "User1"},
            "modifiedBy": {"displayName": "User2"},
            "_links": {"self": {"href": "http://..."}},
            "url": "http://...",
            "variables": {
                "VAR1": {"value": "val1", "isSecret": False},
                "SECRET_VAR": {"value": "secret", "isSecret": True},
            },
            "environments": [
                {"id": 1, "name": "QA", "rank": 1, "variables": {}, "deployPhases": []},
                {"id": 2, "name": "PROD", "rank": 2, "variables": {}, "deployPhases": []},
            ],
            "artifacts": [{"alias": "main", "type": "Build"}],
        }

    def test_removes_system_fields(self):
        cleaned = mod.clean_definition_for_clone(self.definition)
        for field in ["id", "revision", "createdOn", "modifiedOn", "createdBy", "modifiedBy", "_links", "url"]:
            self.assertNotIn(field, cleaned, f"Field {field} should be removed")

    def test_preserves_name_path_variables(self):
        cleaned = mod.clean_definition_for_clone(self.definition)
        self.assertEqual(cleaned["name"], "Test-Pipeline")
        self.assertEqual(cleaned["path"], "\\Pipelines\\Prod")
        self.assertIn("variables", cleaned)
        self.assertIn("VAR1", cleaned["variables"])
        self.assertIn("environments", cleaned)
        self.assertEqual(len(cleaned["environments"]), 2)

    def test_cleans_environment_fields(self):
        cleaned = mod.clean_definition_for_clone(self.definition)
        for env in cleaned["environments"]:
            self.assertNotIn("id", env)
            self.assertNotIn("releaseId", env)

    def test_does_not_mutate_original(self):
        original_id = self.definition["id"]
        mod.clean_definition_for_clone(self.definition)
        self.assertEqual(self.definition["id"], original_id)


class TestExtractSecrets(unittest.TestCase):
    """Tests para extract_secrets."""

    def test_detects_definition_level_secrets(self):
        definition = {
            "variables": {
                "SECRET1": {"value": "s1", "isSecret": True},
                "VAR1": {"value": "v1", "isSecret": False},
            },
            "environments": [],
        }
        secrets = mod.extract_secrets(definition)
        self.assertEqual(len(secrets), 1)
        self.assertEqual(secrets[0]["name"], "SECRET1")
        self.assertEqual(secrets[0]["scope"], "definition")

    def test_detects_environment_level_secrets(self):
        definition = {
            "variables": {},
            "environments": [
                {"name": "QA", "variables": {"SECRET_ENV": {"value": "s", "isSecret": True}}},
            ],
        }
        secrets = mod.extract_secrets(definition)
        self.assertEqual(len(secrets), 1)
        self.assertEqual(secrets[0]["name"], "SECRET_ENV")
        self.assertEqual(secrets[0]["scope"], "environment")
        self.assertEqual(secrets[0]["env"], "QA")

    def test_no_secrets_returns_empty(self):
        definition = {"variables": {"VAR1": {"value": "v1"}}, "environments": []}
        secrets = mod.extract_secrets(definition)
        self.assertEqual(len(secrets), 0)


class TestBuildClonePayload(unittest.TestCase):
    """Tests para build_clone_payload."""

    def setUp(self):
        self.definition = {
            "id": 100,
            "revision": 5,
            "name": "Original-Pipeline",
            "path": "\\Original",
            "createdBy": {"displayName": "User"},
            "variables": {"VAR1": {"value": "v1"}},
            "environments": [{"id": 1, "name": "QA", "rank": 1}],
            "artifacts": [],
        }

    def test_sets_new_name(self):
        payload = mod.build_clone_payload(self.definition, "New-Pipeline")
        self.assertEqual(payload["name"], "New-Pipeline")

    def test_sets_new_path(self):
        payload = mod.build_clone_payload(self.definition, "New-Pipeline", "\\NewPath")
        self.assertEqual(payload["path"], "\\NewPath")

    def test_keeps_original_path_if_not_provided(self):
        payload = mod.build_clone_payload(self.definition, "New-Pipeline")
        self.assertEqual(payload["path"], "\\Original")

    def test_cleans_system_fields(self):
        payload = mod.build_clone_payload(self.definition, "New-Pipeline")
        self.assertNotIn("id", payload)
        self.assertNotIn("revision", payload)
        self.assertNotIn("createdBy", payload)

    def test_default_lab_name(self):
        current_name = self.definition["name"]
        new_name = f"LAB-{current_name}"
        payload = mod.build_clone_payload(self.definition, new_name)
        self.assertEqual(payload["name"], "LAB-Original-Pipeline")


class TestCreateCloneBackup(unittest.TestCase):
    """Tests para create_clone_backup."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.definition = {
            "id": 2758,
            "name": "Test-Pipeline",
            "revision": 10,
            "variables": {},
            "environments": [],
        }

    def test_creates_backup_file(self):
        filepath = mod.create_clone_backup(self.definition, 2758, self.tmpdir)
        self.assertTrue(os.path.exists(filepath))
        self.assertIn("clone_source_2758", filepath)

    def test_backup_contains_metadata(self):
        filepath = mod.create_clone_backup(self.definition, 2758, self.tmpdir)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertIn("metadata", data)
        self.assertEqual(data["metadata"]["sourcePipelineId"], 2758)
        self.assertEqual(data["metadata"]["sourcePipelineName"], "Test-Pipeline")
        self.assertEqual(data["metadata"]["tool"], "pipeline_cd_clone")

    def test_backup_contains_definition(self):
        filepath = mod.create_clone_backup(self.definition, 2758, self.tmpdir)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertIn("definition", data)
        self.assertEqual(data["definition"]["name"], "Test-Pipeline")


class TestSourceIdCheck(unittest.TestCase):
    """Tests para source_id_check."""

    def test_valid_id(self):
        self.assertTrue(mod.source_id_check(2758))

    def test_none_id(self):
        self.assertFalse(mod.source_id_check(None))

    def test_zero_id(self):
        self.assertFalse(mod.source_id_check(0))

    def test_negative_id(self):
        self.assertFalse(mod.source_id_check(-1))


class TestColorsAttributes(unittest.TestCase):
    """Tests para verificar que Colors tiene todos los atributos usados."""

    def test_colors_has_all_required(self):
        required = ['CYAN', 'GREEN', 'YELLOW', 'RED', 'ENDC', 'BOLD', 'DIM', 'MAGENTA']
        for attr in required:
            self.assertTrue(hasattr(mod.Colors, attr), f"Colors.{attr} is missing")


class TestExtractAgentPools(unittest.TestCase):
    """Tests para extract_agent_pools."""

    def test_no_environments(self):
        result = mod.extract_agent_pools({})
        self.assertEqual(result, [])

    def test_env_with_queue_id(self):
        definition = {
            "environments": [
                {"name": "DEV", "queueId": 1, "queue": {"name": "Azure Pipelines"}},
            ]
        }
        result = mod.extract_agent_pools(definition)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["name"], "Azure Pipelines")
        self.assertEqual(result[0]["env"], "DEV")

    def test_env_without_queue(self):
        definition = {
            "environments": [
                {"name": "DEV"},
            ]
        }
        result = mod.extract_agent_pools(definition)
        self.assertEqual(result, [])

    def test_multiple_envs_same_pool_dedup(self):
        definition = {
            "environments": [
                {"name": "DEV", "queueId": 1, "queue": {"name": "Pool1"}},
                {"name": "QA", "queueId": 1, "queue": {"name": "Pool1"}},
            ]
        }
        result = mod.extract_agent_pools(definition)
        self.assertEqual(len(result), 1)

    def test_multiple_envs_different_pools(self):
        definition = {
            "environments": [
                {"name": "DEV", "queueId": 1, "queue": {"name": "Pool1"}},
                {"name": "QA", "queueId": 2, "queue": {"name": "Pool2"}},
            ]
        }
        result = mod.extract_agent_pools(definition)
        self.assertEqual(len(result), 2)

    def test_deploy_phase_deployment_input_queue_id(self):
        definition = {
            "environments": [
                {"name": "DEV",
                 "deployPhases": [
                     {"deploymentInput": {"queueId": 5238}},
                 ]},
            ]
        }
        result = mod.extract_agent_pools(definition)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 5238)
        self.assertEqual(result[0]["scope"], "deploymentInput")
        self.assertEqual(result[0]["env"], "DEV")

    def test_deploy_phase_queue_id(self):
        definition = {
            "environments": [
                {"name": "DEV", "queueId": 1, "queue": {"name": "Pool1"},
                 "deployPhases": [
                     {"phaseInput": {"queueId": 99}},
                 ]},
            ]
        }
        result = mod.extract_agent_pools(definition)
        self.assertEqual(len(result), 2)
        ids = [p["id"] for p in result]
        self.assertIn(99, ids)

    def test_real_azure_devops_structure(self):
        definition = {
            "environments": [
                {"name": "Develop-ingress",
                 "deployPhases": [
                     {"deploymentInput": {"queueId": 5238, "parallelExecution": {"parallelExecutionType": 0}}},
                 ]},
                {"name": "Production",
                 "deployPhases": [
                     {"deploymentInput": {"queueId": 5331}},
                 ]},
            ]
        }
        result = mod.extract_agent_pools(definition)
        self.assertEqual(len(result), 2)
        ids = [p["id"] for p in result]
        self.assertIn(5238, ids)
        self.assertIn(5331, ids)

    def test_no_queue_name_uses_default(self):
        definition = {
            "environments": [
                {"name": "DEV", "queueId": 5},
            ]
        }
        result = mod.extract_agent_pools(definition)
        self.assertEqual(result[0]["name"], "pool-5")


class TestReplaceAgentPools(unittest.TestCase):
    """Tests para replace_agent_pools."""

    def test_replace_env_queue(self):
        definition = {
            "environments": [
                {"name": "DEV", "queueId": 1, "queue": {"name": "Pool1"}},
            ]
        }
        changes = mod.replace_agent_pools(definition, 5331)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["old_id"], 1)
        self.assertEqual(changes[0]["new_id"], 5331)
        self.assertEqual(definition["environments"][0]["queueId"], 5331)
        self.assertNotIn("queue", definition["environments"][0])

    def test_replace_deployment_input_queue(self):
        definition = {
            "environments": [
                {"name": "DEV",
                 "deployPhases": [
                     {"deploymentInput": {"queueId": 5238}},
                 ]},
            ]
        }
        changes = mod.replace_agent_pools(definition, 5331)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["old_id"], 5238)
        self.assertEqual(changes[0]["new_id"], 5331)
        self.assertEqual(definition["environments"][0]["deployPhases"][0]["deploymentInput"]["queueId"], 5331)

    def test_replace_deploy_phase_queue(self):
        definition = {
            "environments": [
                {"name": "DEV", "queueId": 1, "queue": {"name": "Pool1"},
                 "deployPhases": [
                     {"phaseInput": {"queueId": 99}},
                 ]},
            ]
        }
        changes = mod.replace_agent_pools(definition, 5331)
        self.assertEqual(len(changes), 2)
        self.assertEqual(definition["environments"][0]["deployPhases"][0]["phaseInput"]["queueId"], 5331)

    def test_no_replace_if_already_target(self):
        definition = {
            "environments": [
                {"name": "DEV", "queueId": 5331, "queue": {"name": "MyPool"}},
            ]
        }
        changes = mod.replace_agent_pools(definition, 5331)
        self.assertEqual(len(changes), 0)

    def test_no_env_queue_no_changes(self):
        definition = {
            "environments": [
                {"name": "DEV"},
            ]
        }
        changes = mod.replace_agent_pools(definition, 5331)
        self.assertEqual(len(changes), 0)

    def test_real_structure_replace_5238(self):
        definition = {
            "environments": [
                {"name": "DEV",
                 "deployPhases": [
                     {"deploymentInput": {"queueId": 5238}},
                 ]},
                {"name": "QA",
                 "deployPhases": [
                     {"deploymentInput": {"queueId": 5238}},
                 ]},
                {"name": "PROD",
                 "deployPhases": [
                     {"deploymentInput": {"queueId": 5331}},
                 ]},
            ]
        }
        changes = mod.replace_agent_pools(definition, 5331)
        self.assertEqual(len(changes), 2)
        for c in changes:
            self.assertEqual(c["old_id"], 5238)
            self.assertEqual(c["new_id"], 5331)
        for env in definition["environments"]:
            self.assertEqual(env["deployPhases"][0]["deploymentInput"]["queueId"], 5331)

    def test_no_environments(self):
        definition = {}
        changes = mod.replace_agent_pools(definition, 5331)
        self.assertEqual(changes, [])

    def test_multiple_envs_all_replaced(self):
        definition = {
            "environments": [
                {"name": "DEV", "queueId": 1, "queue": {"name": "Pool1"}},
                {"name": "QA", "queueId": 2, "queue": {"name": "Pool2"}},
            ]
        }
        changes = mod.replace_agent_pools(definition, 5331)
        self.assertEqual(len(changes), 2)
        self.assertEqual(definition["environments"][0]["queueId"], 5331)
        self.assertEqual(definition["environments"][1]["queueId"], 5331)


class TestParseErrorBody(unittest.TestCase):
    """Tests para _parse_error_body."""

    def test_valid_json_with_message(self):
        body = json.dumps({"$id": "1", "message": "Access denied.", "innerException": None})
        result = mod._parse_error_body(body)
        self.assertEqual(result, "Access denied.")

    def test_valid_json_with_inner_exception(self):
        body = json.dumps({"$id": "1", "message": "", "innerException": {"message": "Inner error"}})
        result = mod._parse_error_body(body)
        self.assertEqual(result, "Inner error")

    def test_invalid_json_returns_raw(self):
        body = "not json at all"
        result = mod._parse_error_body(body)
        self.assertEqual(result, "not json at all")

    def test_empty_body_returns_empty(self):
        result = mod._parse_error_body("")
        self.assertEqual(result, "")

    def test_json_without_message_returns_raw(self):
        body = json.dumps({"$id": "1", "someField": "value"})
        result = mod._parse_error_body(body)
        self.assertIn("someField", result)


if __name__ == '__main__':
    unittest.main()
