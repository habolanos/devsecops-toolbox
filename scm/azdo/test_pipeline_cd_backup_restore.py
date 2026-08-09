#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para pipeline_cd_backup_restore.py

Cobertura:
- extract_secrets: deteccion de secret variables en definicion y environments
- clean_system_fields: remocion de campos del sistema
- humanize_yaml: generacion de YAML humanizado
- diff_definitions: comparacion entre backup y definicion actual
- load_backup: carga de archivo de backup
- backup_single_pipeline: backup completo con mock de API
- restore_definition: restore con dry-run y con secret values
- create_from_backup: creacion limpia campos del sistema
- convert_json_to_yaml: conversion de JSON a YAML
- list_backups: listado de backups disponibles
- normalize_org: normalizacion de organizacion
- create_auth_header: header de autenticacion
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pipeline_cd_backup_restore as mod


class TestExtractSecrets(unittest.TestCase):
    """Tests para extract_secrets."""

    def test_definition_level_secret(self):
        definition = {
            "variables": {
                "gitToken": {"value": None, "isSecret": True},
                "branchConfig": {"value": "master", "isSecret": False},
            },
            "environments": [],
        }
        secrets = mod.extract_secrets(definition)
        self.assertEqual(len(secrets), 1)
        self.assertEqual(secrets[0]["name"], "gitToken")
        self.assertEqual(secrets[0]["scope"], "definition")
        self.assertIsNone(secrets[0]["env"])

    def test_environment_level_secret(self):
        definition = {
            "variables": {},
            "environments": [
                {
                    "name": "Production",
                    "variables": {
                        "dbPassword": {"value": None, "isSecret": True},
                        "envVar": {"value": "prod", "isSecret": False},
                    },
                }
            ],
        }
        secrets = mod.extract_secrets(definition)
        self.assertEqual(len(secrets), 1)
        self.assertEqual(secrets[0]["name"], "dbPassword")
        self.assertEqual(secrets[0]["scope"], "environment")
        self.assertEqual(secrets[0]["env"], "Production")

    def test_no_secrets(self):
        definition = {
            "variables": {"var1": {"value": "val1", "isSecret": False}},
            "environments": [],
        }
        secrets = mod.extract_secrets(definition)
        self.assertEqual(len(secrets), 0)

    def test_multiple_environments_with_secrets(self):
        definition = {
            "variables": {"defSecret": {"value": None, "isSecret": True}},
            "environments": [
                {"name": "DEV", "variables": {"devSecret": {"value": None, "isSecret": True}}},
                {"name": "QA", "variables": {"qaVar": {"value": "qa", "isSecret": False}}},
                {"name": "Prod", "variables": {"prodSecret": {"value": None, "isSecret": True}}},
            ],
        }
        secrets = mod.extract_secrets(definition)
        self.assertEqual(len(secrets), 3)
        names = [s["name"] for s in secrets]
        self.assertIn("defSecret", names)
        self.assertIn("devSecret", names)
        self.assertIn("prodSecret", names)


class TestCleanSystemFields(unittest.TestCase):
    """Tests para clean_system_fields."""

    def test_removes_top_level_fields(self):
        obj = {"name": "test", "_links": {"self": {"href": "url"}}, "createdOn": "2026-01-01"}
        cleaned = mod.clean_system_fields(obj)
        self.assertNotIn("_links", cleaned)
        self.assertNotIn("createdOn", cleaned)
        self.assertIn("name", cleaned)

    def test_removes_nested_fields(self):
        obj = {
            "environments": [
                {"name": "DEV", "_links": {"self": "url"}, "createdBy": {"displayName": "user"}}
            ]
        }
        cleaned = mod.clean_system_fields(obj)
        self.assertNotIn("_links", cleaned["environments"][0])
        self.assertNotIn("createdBy", cleaned["environments"][0])
        self.assertIn("name", cleaned["environments"][0])

    def test_handles_lists(self):
        obj = [{"_links": "url", "name": "item1"}, {"name": "item2"}]
        cleaned = mod.clean_system_fields(obj)
        self.assertNotIn("_links", cleaned[0])
        self.assertIn("name", cleaned[0])

    def test_preserves_normal_fields(self):
        obj = {"name": "test", "id": 123, "variables": {"var1": {"value": "val1"}}}
        cleaned = mod.clean_system_fields(obj)
        self.assertEqual(cleaned, obj)


class TestHumanizeYaml(unittest.TestCase):
    """Tests para humanize_yaml."""

    def _make_backup_data(self):
        return {
            "metadata": {
                "pipelineId": 2758,
                "pipelineName": "Test-Pipeline",
                "revision": 5,
                "backupDate": "2026-08-09T11:00:00",
                "org": "TestOrg",
                "project": "TestProj",
                "pipelinePath": "\\Release\\Test",
            },
            "definition": {
                "variables": {
                    "branchConfig": {"value": "master", "isSecret": False},
                    "gitToken": {"value": None, "isSecret": True},
                },
                "artifacts": [
                    {"alias": "_CI", "type": "Build", "isPrimary": True,
                     "definitionReference": {"sourceId": {"id": "123:master"}}}
                ],
                "environments": [
                    {
                        "name": "DEV",
                        "rank": 1,
                        "deployPhases": [
                            {"deploymentInput": {"queueId": 1},
                             "workflowTasks": [{"displayName": "Deploy", "enabled": True,
                                                "task": {"name": "Kubectl", "versionSpec": "5.*"},
                                                "inputs": {"namespace": "dev"}}]}
                        ],
                        "variables": {"envVar": {"value": "dev-val", "isSecret": False}},
                        "preDeployApprovals": {"approvals": []},
                        "postDeployApprovals": {"approvals": [{"approvers": [{"displayName": "user@test.com"}]}]},
                    }
                ],
                "triggers": [{"triggerType": "continuousDeployment", "isContinuousDeployment": True,
                              "artifactSourceId": "master"}],
                "retentionPolicy": {"daysToKeep": 30, "releasesToKeep": 10},
            },
            "resolved_names": {
                "agent_pools": {"1": "Azure Pipelines"},
                "variable_groups": {},
                "task_groups": {},
            },
            "secrets_list": [{"scope": "definition", "name": "gitToken", "env": None}],
        }

    def test_generates_yaml_string(self):
        data = self._make_backup_data()
        yaml_str = mod.humanize_yaml(data)
        self.assertIsInstance(yaml_str, str)
        self.assertIn("Test-Pipeline", yaml_str)
        self.assertIn("2758", yaml_str)

    def test_includes_metadata(self):
        data = self._make_backup_data()
        yaml_str = mod.humanize_yaml(data)
        self.assertIn("metadata:", yaml_str)
        self.assertIn("pipeline_id: 2758", yaml_str)
        self.assertIn("revision: 5", yaml_str)

    def test_includes_variables(self):
        data = self._make_backup_data()
        yaml_str = mod.humanize_yaml(data)
        self.assertIn("variables:", yaml_str)
        self.assertIn("branchConfig", yaml_str)
        self.assertIn("gitToken", yaml_str)
        self.assertIn("SECRET", yaml_str)

    def test_includes_environments(self):
        data = self._make_backup_data()
        yaml_str = mod.humanize_yaml(data)
        self.assertIn("environments:", yaml_str)
        self.assertIn("DEV", yaml_str)
        self.assertIn("agent_pool:", yaml_str)
        self.assertIn("Azure Pipelines", yaml_str)

    def test_includes_artifacts(self):
        data = self._make_backup_data()
        yaml_str = mod.humanize_yaml(data)
        self.assertIn("artifacts:", yaml_str)
        self.assertIn("_CI", yaml_str)

    def test_includes_triggers(self):
        data = self._make_backup_data()
        yaml_str = mod.humanize_yaml(data)
        self.assertIn("triggers:", yaml_str)
        self.assertIn("continuousDeployment", yaml_str)

    def test_includes_secrets_list(self):
        data = self._make_backup_data()
        yaml_str = mod.humanize_yaml(data)
        self.assertIn("secrets_list:", yaml_str)
        self.assertIn("gitToken", yaml_str)

    def test_includes_resolved_names(self):
        data = self._make_backup_data()
        yaml_str = mod.humanize_yaml(data)
        self.assertIn("resolved_names:", yaml_str)
        self.assertIn("agent_pools:", yaml_str)

    def test_empty_environments(self):
        data = self._make_backup_data()
        data["definition"]["environments"] = []
        yaml_str = mod.humanize_yaml(data)
        self.assertIn("environments: []", yaml_str)

    def test_empty_variables(self):
        data = self._make_backup_data()
        data["definition"]["variables"] = {}
        yaml_str = mod.humanize_yaml(data)
        self.assertIn("variables: {}", yaml_str)


class TestDiffDefinitions(unittest.TestCase):
    """Tests para diff_definitions."""

    def _make_def(self, variables=None, environments=None, artifacts=None, triggers=None):
        return {
            "variables": variables or {},
            "environments": environments or [],
            "artifacts": artifacts or [],
            "triggers": triggers or [],
        }

    def test_no_diff(self):
        def1 = self._make_def(variables={"var1": {"value": "val1"}})
        def2 = self._make_def(variables={"var1": {"value": "val1"}})
        diffs = mod.diff_definitions(def1, def2)
        self.assertEqual(len(diffs), 0)

    def test_variable_added(self):
        def1 = self._make_def(variables={"var1": {"value": "val1"}})
        def2 = self._make_def(variables={"var1": {"value": "val1"}, "var2": {"value": "val2"}})
        diffs = mod.diff_definitions(def1, def2)
        added = [d for d in diffs if d["change"] == "agregado"]
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["name"], "var2")

    def test_variable_removed(self):
        def1 = self._make_def(variables={"var1": {"value": "val1"}, "var2": {"value": "val2"}})
        def2 = self._make_def(variables={"var1": {"value": "val1"}})
        diffs = mod.diff_definitions(def1, def2)
        removed = [d for d in diffs if d["change"] == "eliminado"]
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]["name"], "var2")

    def test_variable_modified(self):
        def1 = self._make_def(variables={"var1": {"value": "old"}})
        def2 = self._make_def(variables={"var1": {"value": "new"}})
        diffs = mod.diff_definitions(def1, def2)
        modified = [d for d in diffs if d["change"] == "modificado"]
        self.assertEqual(len(modified), 1)
        self.assertEqual(modified[0]["name"], "var1")

    def test_environment_added(self):
        def1 = self._make_def(environments=[{"name": "DEV", "rank": 1}])
        def2 = self._make_def(environments=[{"name": "DEV", "rank": 1}, {"name": "QA", "rank": 2}])
        diffs = mod.diff_definitions(def1, def2)
        added = [d for d in diffs if d["category"] == "environment" and d["change"] == "agregado"]
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["name"], "QA")

    def test_environment_rank_changed(self):
        def1 = self._make_def(environments=[{"name": "DEV", "rank": 1, "deployPhases": []}])
        def2 = self._make_def(environments=[{"name": "DEV", "rank": 2, "deployPhases": []}])
        diffs = mod.diff_definitions(def1, def2)
        rank_diffs = [d for d in diffs if d["category"] == "environment_rank"]
        self.assertEqual(len(rank_diffs), 1)

    def test_artifact_added(self):
        def1 = self._make_def(artifacts=[{"alias": "A1"}])
        def2 = self._make_def(artifacts=[{"alias": "A1"}, {"alias": "A2"}])
        diffs = mod.diff_definitions(def1, def2)
        added = [d for d in diffs if d["category"] == "artifact" and d["change"] == "agregado"]
        self.assertEqual(len(added), 1)

    def test_trigger_count_diff(self):
        def1 = self._make_def(triggers=[{"triggerType": "cd"}])
        def2 = self._make_def(triggers=[{"triggerType": "cd"}, {"triggerType": "scheduled"}])
        diffs = mod.diff_definitions(def1, def2)
        trigger_diffs = [d for d in diffs if d["category"] == "trigger"]
        self.assertEqual(len(trigger_diffs), 1)

    def test_task_added(self):
        def1 = self._make_def(environments=[{
            "name": "DEV", "rank": 1,
            "deployPhases": [{"workflowTasks": [{"displayName": "Task1"}]}],
        }])
        def2 = self._make_def(environments=[{
            "name": "DEV", "rank": 1,
            "deployPhases": [{"workflowTasks": [{"displayName": "Task1"}, {"displayName": "Task2"}]}],
        }])
        diffs = mod.diff_definitions(def1, def2)
        task_added = [d for d in diffs if d["category"] == "task" and d["change"] == "agregado"]
        self.assertEqual(len(task_added), 1)
        self.assertIn("Task2", task_added[0]["name"])


class TestLoadBackup(unittest.TestCase):
    """Tests para load_backup."""

    def test_loads_valid_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "test_backup.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({"metadata": {"pipelineId": 123}, "definition": {}}, f)
            result = mod.load_backup(json_path)
            self.assertEqual(result["metadata"]["pipelineId"], 123)

    def test_raises_on_not_found(self):
        with self.assertRaises(FileNotFoundError):
            mod.load_backup("nonexistent_file.json")


class TestNormalizeOrg(unittest.TestCase):
    """Tests para normalize_org."""

    def test_extracts_from_url(self):
        self.assertEqual(mod.normalize_org("https://dev.azure.com/Coppel-Retail"), "Coppel-Retail")

    def test_preserves_plain_name(self):
        self.assertEqual(mod.normalize_org("Coppel-Retail"), "Coppel-Retail")


class TestCreateAuthHeader(unittest.TestCase):
    """Tests para create_auth_header."""

    def test_returns_basic_prefix(self):
        header = mod.create_auth_header("mytoken")
        self.assertTrue(header.startswith("Basic "))

    def test_encodes_pat(self):
        header = mod.create_auth_header("test123")
        import base64
        decoded = base64.b64decode(header.split(" ")[1]).decode('ascii')
        self.assertEqual(decoded, ":test123")


class TestConvertJsonToYaml(unittest.TestCase):
    """Tests para convert_json_to_yaml."""

    def test_converts_valid_json(self):
        data = {
            "metadata": {"pipelineId": 1, "pipelineName": "Test", "revision": 1,
                         "backupDate": "2026-01-01", "org": "O", "project": "P", "pipelinePath": "\\"},
            "definition": {"variables": {}, "environments": [], "artifacts": [], "triggers": []},
            "resolved_names": {"agent_pools": {}, "variable_groups": {}, "task_groups": {}},
            "secrets_list": [],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "test.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)

            result = mod.convert_json_to_yaml(json_path)
            self.assertEqual(result["status"], "ok")
            self.assertTrue(os.path.exists(result["yaml_file"]))
            self.assertGreater(result["lines"], 0)

    def test_returns_error_for_missing_file(self):
        result = mod.convert_json_to_yaml("nonexistent.json")
        self.assertIn("error", result["status"])

    def test_converts_to_custom_output_dir(self):
        data = {
            "metadata": {"pipelineId": 1, "pipelineName": "T", "revision": 1,
                         "backupDate": "2026-01-01", "org": "O", "project": "P", "pipelinePath": "\\"},
            "definition": {"variables": {}, "environments": [], "artifacts": [], "triggers": []},
            "resolved_names": {"agent_pools": {}, "variable_groups": {}, "task_groups": {}},
            "secrets_list": [],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "test.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)

            out_dir = os.path.join(tmpdir, "yaml_output")
            result = mod.convert_json_to_yaml(json_path, out_dir)
            self.assertEqual(result["status"], "ok")
            self.assertIn("yaml_output", result["yaml_file"])


class TestListBackups(unittest.TestCase):
    """Tests para list_backups."""

    def test_lists_backup_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(3):
                data = {
                    "metadata": {"pipelineId": 100 + i, "pipelineName": f"Pipe-{i}",
                                 "revision": i + 1, "backupDate": f"2026-08-0{i+1}T10:00:00"},
                    "definition": {},
                    "resolved_names": {},
                    "secrets_list": [],
                }
                path = os.path.join(tmpdir, f"backup_def_{100+i}_Pipe-{i}_2026080{i+1}_100000.json")
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)

            backups = mod.list_backups(Path(tmpdir))
            self.assertEqual(len(backups), 3)
            self.assertEqual(backups[0]["pipeline_id"], 102)

    def test_returns_empty_for_nonexistent_dir(self):
        backups = mod.list_backups(Path("/nonexistent/path"))
        self.assertEqual(len(backups), 0)

    def test_skips_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "backup_def_1_Test_20260101_000000.json")
            with open(path, 'w', encoding='utf-8') as f:
                f.write("invalid json {{{")
            backups = mod.list_backups(Path(tmpdir))
            self.assertEqual(len(backups), 0)


class TestBackupSinglePipeline(unittest.TestCase):
    """Tests para backup_single_pipeline."""

    @patch.object(mod, "resolve_names")
    @patch.object(mod, "get_release_definition")
    def test_successful_backup_json(self, mock_get_def, mock_resolve):
        mock_get_def.return_value = {
            "id": 42, "name": "Test-Pipe", "revision": 3, "path": "\\Release",
            "variables": {"secret": {"value": None, "isSecret": True}},
            "environments": [],
        }
        mock_resolve.return_value = {"agent_pools": {}, "variable_groups": {}, "task_groups": {}}

        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.backup_single_pipeline(42, "org", "proj", "pat", Path(tmpdir), "json")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["pipeline_id"], 42)
            self.assertEqual(result["name"], "Test-Pipe")
            self.assertEqual(result["revision"], 3)
            self.assertEqual(result["secrets_count"], 1)
            self.assertEqual(len(result["files"]), 1)
            self.assertTrue(result["files"][0].endswith(".json"))

    @patch.object(mod, "resolve_names")
    @patch.object(mod, "get_release_definition")
    def test_successful_backup_yaml(self, mock_get_def, mock_resolve):
        mock_get_def.return_value = {
            "id": 42, "name": "Test-Pipe", "revision": 3, "path": "\\Release",
            "variables": {}, "environments": [],
        }
        mock_resolve.return_value = {"agent_pools": {}, "variable_groups": {}, "task_groups": {}}

        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.backup_single_pipeline(42, "org", "proj", "pat", Path(tmpdir), "yaml")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(result["files"]), 1)
            self.assertTrue(result["files"][0].endswith(".yaml"))

    @patch.object(mod, "resolve_names")
    @patch.object(mod, "get_release_definition")
    def test_successful_backup_both(self, mock_get_def, mock_resolve):
        mock_get_def.return_value = {
            "id": 42, "name": "Test-Pipe", "revision": 3, "path": "\\Release",
            "variables": {}, "environments": [],
        }
        mock_resolve.return_value = {"agent_pools": {}, "variable_groups": {}, "task_groups": {}}

        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.backup_single_pipeline(42, "org", "proj", "pat", Path(tmpdir), "both")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(len(result["files"]), 2)

    @patch.object(mod, "resolve_names")
    @patch.object(mod, "get_release_definition")
    def test_error_on_api_failure(self, mock_get_def, mock_resolve):
        mock_get_def.side_effect = Exception("API error")
        mock_resolve.return_value = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            result = mod.backup_single_pipeline(42, "org", "proj", "pat", Path(tmpdir), "json")
            self.assertIn("error", result["status"])


class TestRestoreDefinition(unittest.TestCase):
    """Tests para restore_definition."""

    def test_dry_run_does_not_call_api(self):
        backup = {
            "metadata": {"pipelineId": 42},
            "definition": {"id": 42, "name": "Test", "variables": {}},
            "secrets_list": [],
        }
        with patch.object(mod, "update_release_definition") as mock_update:
            result = mod.restore_definition(backup, "org", "proj", "pat", dry_run=True)
            self.assertEqual(result["status"], "dry_run")
            mock_update.assert_not_called()

    def test_restore_calls_api(self):
        backup = {
            "metadata": {"pipelineId": 42},
            "definition": {"id": 42, "name": "Test", "variables": {}},
            "secrets_list": [],
        }
        with patch.object(mod, "update_release_definition", return_value={"id": 42, "revision": 5}) as mock_update:
            result = mod.restore_definition(backup, "org", "proj", "pat", dry_run=False)
            self.assertEqual(result["status"], "ok")
            mock_update.assert_called_once()

    def test_restore_with_secret_values(self):
        backup = {
            "metadata": {"pipelineId": 42},
            "definition": {
                "id": 42, "name": "Test",
                "variables": {"gitToken": {"value": None, "isSecret": True}},
                "environments": [],
            },
            "secrets_list": [{"scope": "definition", "name": "gitToken", "env": None}],
        }
        with patch.object(mod, "update_release_definition", return_value={"id": 42}) as mock_update:
            result = mod.restore_definition(backup, "org", "proj", "pat",
                                            dry_run=False, secret_values={"gitToken": "newsecret"})
            self.assertEqual(result["status"], "ok")
            call_args = mock_update.call_args
            definition_arg = call_args[0][3]
            self.assertEqual(definition_arg["variables"]["gitToken"]["value"], "newsecret")

    def test_restore_environment_secret_value(self):
        backup = {
            "metadata": {"pipelineId": 42},
            "definition": {
                "id": 42, "name": "Test",
                "variables": {},
                "environments": [
                    {"name": "Prod", "variables": {"dbPass": {"value": None, "isSecret": True}}}
                ],
            },
            "secrets_list": [{"scope": "environment", "name": "dbPass", "env": "Prod"}],
        }
        with patch.object(mod, "update_release_definition", return_value={"id": 42}) as mock_update:
            result = mod.restore_definition(backup, "org", "proj", "pat",
                                            dry_run=False, secret_values={"dbPass": "secret123"})
            self.assertEqual(result["status"], "ok")
            call_args = mock_update.call_args
            definition_arg = call_args[0][3]
            self.assertEqual(definition_arg["environments"][0]["variables"]["dbPass"]["value"], "secret123")


class TestCreateFromBackup(unittest.TestCase):
    """Tests para create_from_backup."""

    def test_cleans_system_fields(self):
        backup = {
            "metadata": {"pipelineId": 42},
            "definition": {
                "id": 42, "revision": 5, "name": "Old-Name",
                "createdOn": "2026-01-01", "modifiedOn": "2026-01-02",
                "createdBy": {"displayName": "user"}, "modifiedBy": {"displayName": "user"},
                "variables": {}, "environments": [{"name": "DEV", "id": 1, "releaseId": 100}],
                "_links": {"self": "url"},
            },
            "secrets_list": [],
        }
        with patch.object(mod, "create_release_definition", return_value={"id": 99, "name": "New-Name"}) as mock_create:
            result = mod.create_from_backup(backup, "org", "proj", "pat", "New-Name")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["new_id"], 99)
            call_args = mock_create.call_args
            definition_arg = call_args[0][2]
            self.assertNotIn("id", definition_arg)
            self.assertNotIn("revision", definition_arg)
            self.assertNotIn("createdOn", definition_arg)
            self.assertNotIn("_links", definition_arg)
            self.assertEqual(definition_arg["name"], "New-Name")
            self.assertNotIn("id", definition_arg["environments"][0])
            self.assertNotIn("releaseId", definition_arg["environments"][0])

    def test_no_new_name_keeps_original(self):
        backup = {
            "metadata": {"pipelineId": 42},
            "definition": {"name": "Original", "variables": {}, "environments": []},
            "secrets_list": [],
        }
        with patch.object(mod, "create_release_definition", return_value={"id": 99, "name": "Original"}) as mock_create:
            result = mod.create_from_backup(backup, "org", "proj", "pat")
            call_args = mock_create.call_args
            definition_arg = call_args[0][2]
            self.assertEqual(definition_arg["name"], "Original")


class TestBackupAllPipelines(unittest.TestCase):
    """Tests para backup_all_pipelines."""

    @patch.object(mod, "get_all_release_definitions")
    def test_dry_run_lists_pipelines(self, mock_get_all):
        mock_get_all.return_value = [
            {"id": 1, "name": "Pipe-1"},
            {"id": 2, "name": "Pipe-2"},
        ]
        result = mod.backup_all_pipelines("org", "proj", "pat", dry_run=True)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["successful"], 0)

    @patch.object(mod, "get_all_release_definitions")
    def test_empty_pipelines(self, mock_get_all):
        mock_get_all.return_value = []
        result = mod.backup_all_pipelines("org", "proj", "pat", dry_run=False)
        self.assertEqual(result["total"], 0)

    @patch.object(mod, "backup_pipelines")
    @patch.object(mod, "get_all_release_definitions")
    def test_full_backup_all(self, mock_get_all, mock_backup):
        mock_get_all.return_value = [{"id": 1, "name": "P1"}, {"id": 2, "name": "P2"}]
        mock_backup.return_value = [
            {"pipeline_id": 1, "name": "P1", "revision": 1, "secrets_count": 0, "status": "ok", "files": ["f1.json"]},
            {"pipeline_id": 2, "name": "P2", "revision": 2, "secrets_count": 1, "status": "ok", "files": ["f2.json"]},
        ]
        result = mod.backup_all_pipelines("org", "proj", "pat", dry_run=False)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["successful"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertIn("index_file", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
