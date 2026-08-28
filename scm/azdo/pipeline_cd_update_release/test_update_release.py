#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para pipeline_cd_update_release.py

Cubre:
- parse_var: parsing de variables globales NOMBRE=VALOR
- parse_env_var: parsing de variables por environment STAGE,NOMBRE=VALOR
- build_var_entry: estructura de variable para PATCH
- build_patch_payload: construccion del payload PATCH y deteccion de cambios
- normalize_org: normalizacion de organizacion
- create_auth_header: generacion de header Basic
- create_backup: generacion de backup con metadata
- export_report: generacion de reporte JSON
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pipeline_cd_update_release as mod


class TestParseVar(unittest.TestCase):
    """Tests para parse_var."""

    def test_simple_var(self):
        key, value = mod.parse_var("GIT_USER=deploy")
        self.assertEqual(key, "GIT_USER")
        self.assertEqual(value, "deploy")

    def test_value_with_equals(self):
        key, value = mod.parse_var("TOKEN=abc=def=ghi")
        self.assertEqual(key, "TOKEN")
        self.assertEqual(value, "abc=def=ghi")

    def test_value_with_spaces(self):
        key, value = mod.parse_var("NAME = value with spaces ")
        self.assertEqual(key, "NAME")
        self.assertEqual(value, "value with spaces")

    def test_empty_value(self):
        key, value = mod.parse_var("EMPTY=")
        self.assertEqual(key, "EMPTY")
        self.assertEqual(value, "")

    def test_no_equals_raises(self):
        with self.assertRaises(ValueError):
            mod.parse_var("INVALID")


class TestParseEnvVar(unittest.TestCase):
    """Tests para parse_env_var."""

    def test_simple_env_var(self):
        stage, key, value = mod.parse_env_var("QA,NODE_VERSION=18")
        self.assertEqual(stage, "QA")
        self.assertEqual(key, "NODE_VERSION")
        self.assertEqual(value, "18")

    def test_value_with_equals(self):
        stage, key, value = mod.parse_env_var("PROD,TOKEN=abc=123")
        self.assertEqual(stage, "PROD")
        self.assertEqual(key, "TOKEN")
        self.assertEqual(value, "abc=123")

    def test_no_comma_raises(self):
        with self.assertRaises(ValueError):
            mod.parse_env_var("NODE_VERSION=18")

    def test_no_equals_raises(self):
        with self.assertRaises(ValueError):
            mod.parse_env_var("QA,NODE_VERSION")


class TestBuildVarEntry(unittest.TestCase):
    """Tests para build_var_entry."""

    def test_basic_structure(self):
        entry = mod.build_var_entry("my_value")
        self.assertEqual(entry["value"], "my_value")
        self.assertTrue(entry["allowOverride"])

    def test_empty_value(self):
        entry = mod.build_var_entry("")
        self.assertEqual(entry["value"], "")
        self.assertTrue(entry["allowOverride"])


class TestBuildPatchPayload(unittest.TestCase):
    """Tests para build_patch_payload."""

    def setUp(self):
        self.release = {
            "id": 987,
            "name": "Release-987",
            "status": "active",
            "description": "Original description",
            "variables": {
                "EXISTING_VAR": {"value": "old_value", "allowOverride": True},
            },
            "environments": [
                {
                    "id": 1, "name": "QA", "status": "succeeded",
                    "variables": {
                        "DEBUG": {"value": "true", "allowOverride": True},
                        "branchConfig": {"value": "config-cadenaSuministro", "allowOverride": True},
                    },
                    "deployPhases": [
                        {
                            "name": "QA",
                            "workflowTasks": [
                                {
                                    "displayName": "get file k8-manifest",
                                    "inputs": {
                                        "script": "echo $path_pipelineConfig && kubectl apply -f $path_pipelineConfig"
                                    }
                                },
                                {
                                    "displayName": "Deploy",
                                    "inputs": {"command": "apply"}
                                }
                            ]
                        }
                    ]
                },
                {
                    "id": 2, "name": "PROD", "status": "inProgress",
                    "variables": {
                        "branchConfig": {"value": "config-cadenaSuministro", "allowOverride": True},
                    },
                    "deployPhases": [
                        {
                            "name": "PROD",
                            "workflowTasks": [
                                {
                                    "displayName": "get file k8-manifest",
                                    "inputs": {
                                        "script": "cat $path_pipelineConfig/deploy.yaml"
                                    }
                                }
                            ]
                        }
                    ]
                },
                {
                    "id": 3, "name": "Staging", "status": "notStarted",
                    "variables": {
                        "branchConfig": {"value": "other-branch", "allowOverride": True},
                    },
                    "deployPhases": [
                        {
                            "name": "Staging",
                            "workflowTasks": [
                                {
                                    "displayName": "get file k8-manifest",
                                    "inputs": {
                                        "script": "echo no_config_here"
                                    }
                                }
                            ]
                        }
                    ]
                },
            ]
        }

    def test_no_changes_empty_payload(self):
        payload, changes = mod.build_patch_payload(self.release, [], [], False, "")
        self.assertEqual(payload, {})
        self.assertEqual(changes, [])

    def test_global_var_new(self):
        payload, changes = mod.build_patch_payload(
            self.release, ["NEW_VAR=hello"], [], False, ""
        )
        self.assertIn("variables", payload)
        self.assertIn("NEW_VAR", payload["variables"])
        self.assertEqual(payload["variables"]["NEW_VAR"]["value"], "hello")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "global_var")
        self.assertEqual(changes[0]["key"], "NEW_VAR")
        self.assertIsNone(changes[0]["old"])
        self.assertEqual(changes[0]["new"], "hello")

    def test_global_var_update_existing(self):
        payload, changes = mod.build_patch_payload(
            self.release, ["EXISTING_VAR=new_value"], [], False, ""
        )
        self.assertEqual(payload["variables"]["EXISTING_VAR"]["value"], "new_value")
        self.assertEqual(changes[0]["old"], "old_value")
        self.assertEqual(changes[0]["new"], "new_value")

    def test_multiple_global_vars(self):
        payload, changes = mod.build_patch_payload(
            self.release, ["VAR_A=1", "VAR_B=2"], [], False, ""
        )
        self.assertEqual(payload["variables"]["VAR_A"]["value"], "1")
        self.assertEqual(payload["variables"]["VAR_B"]["value"], "2")
        self.assertEqual(len(changes), 2)

    def test_env_var_update_existing(self):
        payload, changes = mod.build_patch_payload(
            self.release, [], ["QA,DEBUG=false"], False, ""
        )
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "env_var")
        self.assertEqual(changes[0]["stage"], "QA")
        self.assertEqual(changes[0]["key"], "DEBUG")
        self.assertEqual(changes[0]["old"], "true")
        self.assertEqual(changes[0]["new"], "false")
        for env in payload["environments"]:
            if env["name"] == "QA":
                self.assertEqual(env["variables"]["DEBUG"]["value"], "false")

    def test_env_var_new_in_existing_stage(self):
        payload, changes = mod.build_patch_payload(
            self.release, [], ["PROD,NEW_KEY=value123"], False, ""
        )
        self.assertEqual(len(changes), 1)
        self.assertIsNone(changes[0]["old"])
        self.assertEqual(changes[0]["new"], "value123")
        for env in payload["environments"]:
            if env["name"] == "PROD":
                self.assertEqual(env["variables"]["NEW_KEY"]["value"], "value123")

    def test_env_var_stage_not_found(self):
        payload, changes = mod.build_patch_payload(
            self.release, [], ["NONEXISTENT,FOO=bar"], False, ""
        )
        self.assertEqual(len(changes), 1)
        self.assertIn("error", changes[0])
        self.assertIn("NONEXISTENT", changes[0]["error"])

    def test_env_var_case_insensitive_stage(self):
        payload, changes = mod.build_patch_payload(
            self.release, [], ["prod,DEPLOY=true"], False, ""
        )
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["stage"], "PROD")
        self.assertNotIn("error", changes[0])

    def test_abandon_sets_status(self):
        payload, changes = mod.build_patch_payload(
            self.release, [], [], True, ""
        )
        self.assertEqual(payload["status"], "abandoned")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "status")
        self.assertEqual(changes[0]["old"], "active")
        self.assertEqual(changes[0]["new"], "abandoned")

    def test_description_update(self):
        payload, changes = mod.build_patch_payload(
            self.release, [], [], False, "New description here"
        )
        self.assertEqual(payload["description"], "New description here")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "description")
        self.assertEqual(changes[0]["old"], "Original description")
        self.assertEqual(changes[0]["new"], "New description here")

    def test_combined_changes(self):
        payload, changes = mod.build_patch_payload(
            self.release, ["VAR1=a"], ["QA,VAR2=b"], True, "Updated"
        )
        self.assertEqual(len(changes), 4)
        types = [c["type"] for c in changes]
        self.assertIn("global_var", types)
        self.assertIn("env_var", types)
        self.assertIn("status", types)
        self.assertIn("description", types)
        self.assertIn("variables", payload)
        self.assertIn("environments", payload)
        self.assertEqual(payload["status"], "abandoned")
        self.assertEqual(payload["description"], "Updated")

    def test_original_release_not_mutated(self):
        original_vars = dict(self.release["variables"])
        mod.build_patch_payload(self.release, ["NEW=x"], [], False, "")
        self.assertEqual(self.release["variables"], original_vars)

    def test_wildcard_stage_updates_all(self):
        """Stage '*' should update variable in all stages."""
        payload, changes = mod.build_patch_payload(
            self.release, [], ["*,branchConfig=feature/feature-amad"], False, ""
        )
        env_var_changes = [c for c in changes if c["type"] == "env_var"]
        self.assertEqual(len(env_var_changes), 3)
        stages_updated = [c["stage"] for c in env_var_changes]
        self.assertIn("QA", stages_updated)
        self.assertIn("PROD", stages_updated)
        self.assertIn("Staging", stages_updated)
        for env in payload["environments"]:
            self.assertEqual(env["variables"]["branchConfig"]["value"], "feature/feature-amad")

    def test_wildcard_stage_with_search_value_filters(self):
        """Stage '*' with search_value should only update stages where current value matches."""
        payload, changes = mod.build_patch_payload(
            self.release, [], ["*,branchConfig=feature/feature-amad"], False, "",
            env_var_search_values=["config-cadenaSuministro"]
        )
        env_var_changes = [c for c in changes if c["type"] == "env_var"]
        self.assertEqual(len(env_var_changes), 2)
        stages_updated = [c["stage"] for c in env_var_changes]
        self.assertIn("QA", stages_updated)
        self.assertIn("PROD", stages_updated)
        self.assertNotIn("Staging", stages_updated)
        for env in payload["environments"]:
            if env["name"] in ("QA", "PROD"):
                self.assertEqual(env["variables"]["branchConfig"]["value"], "feature/feature-amad")
            elif env["name"] == "Staging":
                self.assertEqual(env["variables"]["branchConfig"]["value"], "other-branch")

    def test_wildcard_stage_with_search_value_no_match(self):
        """Stage '*' with search_value that doesn't match any stage should report error."""
        payload, changes = mod.build_patch_payload(
            self.release, [], ["*,branchConfig=new-value"], False, "",
            env_var_search_values=["nonexistent-value"]
        )
        env_var_changes = [c for c in changes if c["type"] == "env_var"]
        self.assertEqual(len(env_var_changes), 1)
        self.assertIn("error", env_var_changes[0])
        self.assertIn("nonexistent-value", env_var_changes[0]["error"])

    def test_specific_stage_with_search_value_match(self):
        """Specific stage with search_value that matches should update."""
        payload, changes = mod.build_patch_payload(
            self.release, [], ["QA,branchConfig=new-branch"], False, "",
            env_var_search_values=["config-cadenaSuministro"]
        )
        env_var_changes = [c for c in changes if c["type"] == "env_var"]
        self.assertEqual(len(env_var_changes), 1)
        self.assertEqual(env_var_changes[0]["stage"], "QA")
        self.assertEqual(env_var_changes[0]["old"], "config-cadenaSuministro")
        self.assertEqual(env_var_changes[0]["new"], "new-branch")

    def test_specific_stage_with_search_value_no_match(self):
        """Specific stage with search_value that doesn't match should report error."""
        payload, changes = mod.build_patch_payload(
            self.release, [], ["Staging,branchConfig=new-branch"], False, "",
            env_var_search_values=["config-cadenaSuministro"]
        )
        env_var_changes = [c for c in changes if c["type"] == "env_var"]
        self.assertEqual(len(env_var_changes), 1)
        self.assertIn("error", env_var_changes[0])
        self.assertIn("config-cadenaSuministro", env_var_changes[0]["error"])

    def test_wildcard_stage_var_not_found(self):
        """Stage '*' with variable that doesn't exist creates it in all stages."""
        payload, changes = mod.build_patch_payload(
            self.release, [], ["*,NONEXISTENT=value"], False, ""
        )
        env_var_changes = [c for c in changes if c["type"] == "env_var"]
        self.assertEqual(len(env_var_changes), 3)
        for c in env_var_changes:
            self.assertIsNone(c["old"])
            self.assertEqual(c["new"], "value")

    def test_wildcard_stage_var_not_in_any_env_with_search_value_skips(self):
        """Stage '*' with search_value and var not in any env should skip silently (scope '*' from release-level var)."""
        payload, changes = mod.build_patch_payload(
            self.release, [], ["*,RELEASE_ONLY_VAR=new-value"], False, "",
            env_var_search_values=["old-value"]
        )
        env_var_changes = [c for c in changes if c["type"] == "env_var"]
        self.assertEqual(len(env_var_changes), 0)

    def test_comment_in_payload(self):
        """Comment should be included in payload and changes."""
        payload, changes = mod.build_patch_payload(
            self.release, [], [], False, "", comment="Test comment for release"
        )
        comment_changes = [c for c in changes if c["type"] == "comment"]
        self.assertEqual(len(comment_changes), 1)
        self.assertEqual(comment_changes[0]["new"], "Test comment for release")
        self.assertEqual(payload["comment"], "Test comment for release")

    def test_task_update_replaces_in_script(self):
        """Task field update should replace old_value with new_value in script."""
        task_updates = [
            {"name": "get file k8-manifest", "fields": [
                {"path": "inputs.script", "old_value": "path_pipelineConfig", "new_value": "path_pipelineConfigYml"}
            ]}
        ]
        payload, changes = mod.build_patch_payload(
            self.release, [], [], False, "", task_updates=task_updates
        )
        task_changes = [c for c in changes if c["type"] == "task_field"]
        success_changes = [c for c in task_changes if "error" not in c]
        error_changes = [c for c in task_changes if "error" in c]
        self.assertEqual(len(success_changes), 2)  # QA and PROD have the old_value
        self.assertEqual(len(error_changes), 1)    # Staging has no match
        stages_changed = [c["stage"] for c in success_changes]
        self.assertIn("QA", stages_changed)
        self.assertIn("PROD", stages_changed)
        for c in success_changes:
            self.assertIn("path_pipelineConfigYml", c["new"])
            self.assertNotIn("path_pipelineConfig\n", c["new"])
            self.assertIn("path_pipelineConfig", c["old"])

    def test_task_update_no_match_skips(self):
        """Task field update should skip stages where old_value not found."""
        task_updates = [
            {"name": "get file k8-manifest", "fields": [
                {"path": "inputs.script", "old_value": "nonexistent_text", "new_value": "replacement"}
            ]}
        ]
        payload, changes = mod.build_patch_payload(
            self.release, [], [], False, "", task_updates=task_updates
        )
        task_changes = [c for c in changes if c["type"] == "task_field"]
        # Now produces error changes instead of silently skipping
        self.assertEqual(len(task_changes), 3)  # 3 environments, all error
        for c in task_changes:
            self.assertIn("error", c)

    def test_task_update_case_insensitive_name(self):
        """Task name matching should be case-insensitive."""
        task_updates = [
            {"name": "GET FILE K8-MANIFEST", "fields": [
                {"path": "inputs.script", "old_value": "path_pipelineConfig", "new_value": "path_pipelineConfigYml"}
            ]}
        ]
        payload, changes = mod.build_patch_payload(
            self.release, [], [], False, "", task_updates=task_updates
        )
        task_changes = [c for c in changes if c["type"] == "task_field"]
        success_changes = [c for c in task_changes if "error" not in c]
        error_changes = [c for c in task_changes if "error" in c]
        self.assertEqual(len(success_changes), 2)  # QA and PROD
        self.assertEqual(len(error_changes), 1)    # Staging

    def test_task_update_not_found_no_changes(self):
        """Task not found in any stage should produce no task changes."""
        task_updates = [
            {"name": "Nonexistent Task", "fields": [
                {"path": "inputs.script", "old_value": "x", "new_value": "y"}
            ]}
        ]
        payload, changes = mod.build_patch_payload(
            self.release, [], [], False, "", task_updates=task_updates
        )
        task_changes = [c for c in changes if c["type"] == "task_field"]
        # Task not found produces error change
        self.assertEqual(len(task_changes), 1)
        self.assertIn("error", task_changes[0])

    def test_combined_env_vars_and_task_updates(self):
        """Combined env_vars with search_value and task_updates should both work."""
        task_updates = [
            {"name": "get file k8-manifest", "fields": [
                {"path": "inputs.script", "old_value": "path_pipelineConfig", "new_value": "path_pipelineConfigYml"}
            ]}
        ]
        payload, changes = mod.build_patch_payload(
            self.release, [], ["*,branchConfig=feature/feature-amad"], False, "",
            env_var_search_values=["config-cadenaSuministro"],
            task_updates=task_updates
        )
        env_var_changes = [c for c in changes if c["type"] == "env_var"]
        task_changes = [c for c in changes if c["type"] == "task_field"]
        task_success = [c for c in task_changes if "error" not in c]
        task_errors = [c for c in task_changes if "error" in c]
        self.assertEqual(len(env_var_changes), 2)  # QA and PROD
        self.assertEqual(len(task_success), 2)     # QA and PROD
        self.assertEqual(len(task_errors), 1)      # Staging
        self.assertIn("environments", payload)

    def test_global_var_with_search_value_match(self):
        """Global var with matching search_value should be updated."""
        payload, changes = mod.build_patch_payload(
            self.release, ["EXISTING_VAR=new_value"], [], False, "",
            global_var_search_values=["old_value"]
        )
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["type"], "global_var")
        self.assertEqual(changes[0]["key"], "EXISTING_VAR")
        self.assertEqual(changes[0]["old"], "old_value")
        self.assertEqual(changes[0]["new"], "new_value")

    def test_global_var_with_search_value_no_match(self):
        """Global var with non-matching search_value should report error."""
        payload, changes = mod.build_patch_payload(
            self.release, ["EXISTING_VAR=new_value"], [], False, "",
            global_var_search_values=["wrong_value"]
        )
        self.assertEqual(len(changes), 1)
        self.assertIn("error", changes[0])
        self.assertNotIn("variables", payload)


class TestColorsAttributes(unittest.TestCase):
    """Tests para verificar que Colors tiene todos los atributos usados."""

    def test_colors_has_dim(self):
        """Colors must have DIM attribute used in interactive_mode and load_template."""
        self.assertTrue(hasattr(mod.Colors, 'DIM'),
                        "Colors.DIM is missing but used in interactive_mode and load_template")

    def test_colors_has_all_required(self):
        """Colors must have all attributes used throughout the script."""
        required = ['CYAN', 'GREEN', 'YELLOW', 'RED', 'ENDC', 'BOLD', 'DIM', 'MAGENTA']
        for attr in required:
            self.assertTrue(hasattr(mod.Colors, attr),
                            f"Colors.{attr} is missing")


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

    def test_returns_basic_prefix(self):
        header = mod.create_auth_header("my_token")
        self.assertTrue(header.startswith("Basic "))

    def test_encodes_pat_correctly(self):
        import base64
        header = mod.create_auth_header("abc123")
        encoded = header.split(" ")[1]
        decoded = base64.b64decode(encoded).decode()
        self.assertEqual(decoded, ":abc123")


class TestCreateBackup(unittest.TestCase):
    """Tests para create_backup."""

    def test_backup_contains_metadata_and_snapshot(self):
        release = {
            "id": 123,
            "name": "Release-123",
            "status": "active",
            "description": "Test release",
            "releaseDefinition": {"id": 456, "name": "Pipeline CD"},
            "createdOn": "2026-01-01",
            "modifiedOn": "2026-01-02",
            "createdBy": {"displayName": "testuser"},
            "artifacts": [{"alias": "drop"}],
            "variables": {"VAR1": {"value": "v1"}},
            "environments": [
                {"id": 1, "name": "QA", "status": "succeeded", "variables": {"X": {"value": "1"}}}
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath, version_label = mod.create_backup(release, tmpdir)
            self.assertTrue(os.path.exists(filepath))
            self.assertTrue(version_label.startswith("UPD_REL_123_"))
            with open(filepath, 'r', encoding='utf-8') as f:
                backup = json.load(f)
            self.assertEqual(backup["metadata"]["sourceReleaseId"], 123)
            self.assertEqual(backup["metadata"]["backupType"], "pre_update")
            self.assertEqual(backup["metadata"]["backedUpBy"], "pipeline_cd_update_release.py")
            self.assertEqual(backup["releaseSnapshot"]["releaseName"], "Release-123")
            self.assertEqual(backup["releaseSnapshot"]["originalStatus"], "active")
            self.assertEqual(len(backup["releaseSnapshot"]["environments"]), 1)

    def test_backup_creates_directory_if_not_exists(self):
        release = {"id": 999, "variables": {}, "environments": []}
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = os.path.join(tmpdir, "new_subdir", "backups")
            filepath, _ = mod.create_backup(release, backup_dir)
            self.assertTrue(os.path.exists(filepath))
            self.assertTrue(os.path.isdir(backup_dir))


class TestExportReport(unittest.TestCase):
    """Tests para export_report."""

    def test_report_contains_required_fields(self):
        stats = {
            "source_release_id": 987,
            "source_release_name": "Release-987",
            "source_release_status": "active",
            "version_label": "UPD_REL_987_20260101",
        }
        args = MagicMock()
        args.org = "Coppel-Retail"
        args.project = "Cadena_de_Suministros"
        args.release_id = "987"
        args.dry_run = False
        args.description = "Test update"
        changes = [{"type": "global_var", "key": "FOO", "old": None, "new": "bar"}]
        updated = {"id": 987, "name": "Release-987", "status": "active"}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = mod.export_report(stats, args, "/fake/backup.json", updated, changes, tmpdir)
            self.assertTrue(os.path.exists(filepath))
            with open(filepath, 'r', encoding='utf-8') as f:
                report = json.load(f)
            self.assertEqual(report["metadata"]["tool"], "Pipeline Update Release")
            self.assertEqual(report["execution"]["source_release"]["id"], 987)
            self.assertEqual(report["execution"]["changes_count"], 1)
            self.assertEqual(report["execution"]["updated_release"]["id"], 987)

    def test_report_with_none_updated_release(self):
        stats = {"source_release_id": 1, "version_label": "VL1"}
        args = MagicMock()
        args.org = "Org"
        args.project = "Proj"
        args.release_id = "1"
        args.dry_run = True
        args.description = ""
        changes = []
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = mod.export_report(stats, args, "/fake.json", None, changes, tmpdir)
            with open(filepath, 'r', encoding='utf-8') as f:
                report = json.load(f)
            self.assertIsNone(report["execution"]["updated_release"])
            self.assertTrue(report["configuration"]["dry_run"])


class TestGetRelease(unittest.TestCase):
    """Tests para get_release con mock de urllib."""

    @patch('pipeline_cd_update_release.urllib.request.urlopen')
    @patch('pipeline_cd_update_release.urllib.request.Request')
    def test_get_release_success(self, mock_req, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "id": 987, "name": "Release-987", "status": "active"
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        result = mod.get_release("Org", "Proj", 987, "fake_pat")
        self.assertEqual(result["id"], 987)
        self.assertEqual(result["name"], "Release-987")

    @patch('pipeline_cd_update_release.urllib.request.urlopen')
    @patch('pipeline_cd_update_release.urllib.request.Request')
    def test_get_release_http_error_exits(self, mock_req, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://test", code=404, msg="Not Found",
            hdrs={}, fp=MagicMock()
        )
        with self.assertRaises(SystemExit):
            mod.get_release("Org", "Proj", 999, "fake_pat")


class TestUpdateRelease(unittest.TestCase):
    """Tests para update_release con mock de urllib."""

    @patch('pipeline_cd_update_release.urllib.request.urlopen')
    @patch('pipeline_cd_update_release.urllib.request.Request')
    def test_update_release_success(self, mock_req, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "id": 987, "name": "Release-987", "status": "abandoned"
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)

        payload = {"status": "abandoned"}
        result = mod.update_release("Org", "Proj", 987, payload, "fake_pat")
        self.assertEqual(result["status"], "abandoned")

    @patch('pipeline_cd_update_release.urllib.request.urlopen')
    @patch('pipeline_cd_update_release.urllib.request.Request')
    def test_update_release_http_error_exits(self, mock_req, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://test", code=400, msg="Bad Request",
            hdrs={}, fp=MagicMock()
        )
        with self.assertRaises(SystemExit):
            mod.update_release("Org", "Proj", 987, {"status": "abandoned"}, "fake_pat")


class TestLoadTemplate(unittest.TestCase):
    """Tests para load_template."""

    def setUp(self):
        if not mod.YAML_AVAILABLE:
            self.skipTest("PyYAML no instalado")

    def _write_template(self, tmpdir, template_dict):
        import yaml as _yaml
        path = os.path.join(tmpdir, "test_template.yaml")
        with open(path, "w", encoding="utf-8") as f:
            _yaml.dump(template_dict, f)
        return path

    def test_load_valid_template_with_global_vars(self):
        template = {
            "metadata": {"name": "Test Template", "version": "1.0"},
            "release": {"ids": [123, 456]},
            "update": {
                "global_vars": [
                    {"name": "GIT_USER", "value": "deploy"},
                    {"name": "GIT_PASS", "value": "secret"},
                ],
                "env_vars": [],
                "abandon": False,
                "description": "Test update",
            },
            "options": {"dry_run": True, "backup_path": "./outcome/backups"},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(result["release_ids"], ["123", "456"])
        self.assertEqual(len(result["global_vars"]), 2)
        self.assertIn("GIT_USER=deploy", result["global_vars"])
        self.assertIn("GIT_PASS=secret", result["global_vars"])
        self.assertEqual(result["env_vars"], [])
        self.assertFalse(result["abandon"])
        self.assertEqual(result["description"], "Test update")
        self.assertTrue(result["dry_run"])

    def test_load_template_with_env_vars(self):
        template = {
            "metadata": {"name": "Env Vars Test", "version": "1.0"},
            "release": {"ids": "789, 990"},
            "update": {
                "global_vars": [],
                "env_vars": [
                    {"stage": "QA", "name": "NODE_VERSION", "value": "18"},
                    {"stage": "PROD", "name": "NODE_VERSION", "value": "20"},
                ],
                "abandon": False,
                "description": "",
            },
            "options": {"dry_run": False},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(result["release_ids"], ["789", "990"])
        self.assertEqual(len(result["env_vars"]), 2)
        self.assertIn("QA,NODE_VERSION=18", result["env_vars"])
        self.assertIn("PROD,NODE_VERSION=20", result["env_vars"])

    def test_load_template_abandon(self):
        template = {
            "metadata": {"name": "Abandon Test", "version": "1.0"},
            "release": {"ids": [111]},
            "update": {
                "global_vars": [],
                "env_vars": [],
                "abandon": True,
                "description": "Abandoned for cleanup",
            },
            "options": {"dry_run": True},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertTrue(result["abandon"])
        self.assertEqual(result["description"], "Abandoned for cleanup")

    def test_load_template_empty_ids(self):
        template = {
            "metadata": {"name": "Empty IDs", "version": "1.0"},
            "release": {"ids": []},
            "update": {"global_vars": [], "env_vars": [], "abandon": False, "description": ""},
            "options": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(result["release_ids"], [])
        self.assertEqual(result["backup_path"], "./outcome/backups")

    def test_load_template_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            mod.load_template("/nonexistent/path/template.yaml")

    def test_load_template_string_ids(self):
        template = {
            "metadata": {"name": "String IDs", "version": "1.0"},
            "release": {"ids": "100,200,300"},
            "update": {"global_vars": [], "env_vars": [], "abandon": False, "description": ""},
            "options": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(result["release_ids"], ["100", "200", "300"])

    def test_load_template_with_search_value(self):
        template = {
            "metadata": {"name": "Search Value Test", "version": "1.0"},
            "release": {"ids": [999]},
            "update": {
                "global_vars": [],
                "env_vars": [
                    {"stage": "*", "name": "branchConfig", "search_value": "config-cadenaSuministro", "value": "feature/feature-amad"},
                ],
                "abandon": False,
                "description": "Update branchConfig",
            },
            "options": {"dry_run": True},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(len(result["env_vars"]), 1)
        self.assertIn("*,branchConfig=feature/feature-amad", result["env_vars"])
        self.assertEqual(len(result["env_var_search_values"]), 1)
        self.assertEqual(result["env_var_search_values"][0], "config-cadenaSuministro")

    def test_load_template_with_search_section_wildcard(self):
        """New search section with wildcard stages and search variables."""
        template = {
            "metadata": {"name": "Search Section Test", "version": "1.2"},
            "search": {
                "stages": [{"name": "*"}],
                "variables": [{"name": "branchConfig", "value": "config-cadenaSuministro"}],
            },
            "release": {"ids": [999]},
            "update": {
                "global_vars": [],
                "env_vars": [{"name": "branchConfig", "value": "feature/feature-amad"}],
                "abandon": False,
                "description": "Update branchConfig",
            },
            "options": {"dry_run": True},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(result["search_stages"], ["*"])
        self.assertEqual(len(result["env_vars"]), 1)
        self.assertIn("*,branchConfig=feature/feature-amad", result["env_vars"])
        self.assertEqual(len(result["env_var_search_values"]), 1)
        self.assertEqual(result["env_var_search_values"][0], "config-cadenaSuministro")

    def test_load_template_with_search_section_specific_stages(self):
        """Search section with specific stages should generate env_vars per stage."""
        template = {
            "metadata": {"name": "Specific Stages Test", "version": "1.2"},
            "search": {
                "stages": [{"name": "QA"}, {"name": "PROD"}],
                "variables": [{"name": "branchConfig", "value": "config-cadenaSuministro"}],
            },
            "release": {"ids": [999]},
            "update": {
                "global_vars": [],
                "env_vars": [{"name": "branchConfig", "value": "feature/feature-amad"}],
                "abandon": False,
                "description": "",
            },
            "options": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(result["search_stages"], ["QA", "PROD"])
        self.assertEqual(len(result["env_vars"]), 2)
        self.assertIn("QA,branchConfig=feature/feature-amad", result["env_vars"])
        self.assertIn("PROD,branchConfig=feature/feature-amad", result["env_vars"])
        self.assertEqual(len(result["env_var_search_values"]), 2)
        self.assertEqual(result["env_var_search_values"][0], "config-cadenaSuministro")
        self.assertEqual(result["env_var_search_values"][1], "config-cadenaSuministro")

    def test_load_template_with_search_no_variables(self):
        """Search section without variables should have None search_values."""
        template = {
            "metadata": {"name": "No Search Vars", "version": "1.2"},
            "search": {"stages": [{"name": "*"}]},
            "release": {"ids": [999]},
            "update": {
                "global_vars": [],
                "env_vars": [{"name": "DEBUG", "value": "true"}],
                "abandon": False,
                "description": "",
            },
            "options": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(len(result["env_vars"]), 1)
        self.assertIn("*,DEBUG=true", result["env_vars"])
        self.assertEqual(len(result["env_var_search_values"]), 1)
        self.assertIsNone(result["env_var_search_values"][0])

    def test_load_template_with_search_release_ids(self):
        """Search section release_ids should be used when release.ids is empty."""
        template = {
            "metadata": {"name": "Search Release IDs", "version": "1.2"},
            "search": {"stages": [{"name": "*"}], "release_ids": [111, 222]},
            "release": {"ids": []},
            "update": {"global_vars": [], "env_vars": [], "abandon": False, "description": ""},
            "options": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(result["release_ids"], ["111", "222"])

    def test_load_template_backward_compatible_no_search(self):
        """Old format without search section should still work."""
        template = {
            "metadata": {"name": "Old Format", "version": "1.0"},
            "release": {"ids": [999]},
            "update": {
                "global_vars": [],
                "env_vars": [{"stage": "QA", "name": "DEBUG", "value": "true", "search_value": "false"}],
                "abandon": False,
                "description": "",
            },
            "options": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(result["search_stages"], ["*"])
        self.assertEqual(len(result["env_vars"]), 1)
        self.assertIn("QA,DEBUG=true", result["env_vars"])
        self.assertEqual(result["env_var_search_values"][0], "false")

    def test_load_template_with_search_release_scope(self):
        """Search variable with scope: release should produce global_vars with search_value."""
        template = {
            "metadata": {"name": "Release Scope", "version": "1.3"},
            "search": {
                "stages": [{"name": "*"}],
                "variables": [{"name": "branchConfig", "value": "config-cadena", "scope": "release"}],
            },
            "release": {"ids": []},
            "update": {
                "global_vars": [],
                "env_vars": [{"name": "branchConfig", "value": "feature/new"}],
                "abandon": False,
                "description": "",
            },
            "options": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(len(result["global_vars"]), 1)
        self.assertIn("branchConfig=feature/new", result["global_vars"])
        self.assertEqual(len(result["env_vars"]), 0)
        self.assertEqual(result["global_var_search_values"][0], "config-cadena")

    def test_load_template_with_search_global_scope_backward_compat(self):
        """Search variable with scope: global (legacy) should still work as release."""
        template = {
            "metadata": {"name": "Global Legacy", "version": "1.2"},
            "search": {
                "stages": [{"name": "*"}],
                "variables": [{"name": "branchConfig", "value": "config-cadena", "scope": "global"}],
            },
            "release": {"ids": []},
            "update": {
                "global_vars": [],
                "env_vars": [{"name": "branchConfig", "value": "feature/new"}],
                "abandon": False,
                "description": "",
            },
            "options": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(len(result["global_vars"]), 1)
        self.assertIn("branchConfig=feature/new", result["global_vars"])
        self.assertEqual(len(result["env_vars"]), 0)
        self.assertEqual(result["global_var_search_values"][0], "config-cadena")

    def test_load_template_with_search_wildcard_scope(self):
        """Search variable with scope: '*' should produce both global_vars and env_vars."""
        template = {
            "metadata": {"name": "Wildcard Scope", "version": "1.3"},
            "search": {
                "stages": [{"name": "*"}],
                "variables": [{"name": "branchConfig", "value": "config-cadena", "scope": "*"}],
            },
            "release": {"ids": []},
            "update": {
                "global_vars": [],
                "env_vars": [{"name": "branchConfig", "value": "feature/new"}],
                "abandon": False,
                "description": "",
            },
            "options": {},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_template(tmpdir, template)
            result = mod.load_template(path)
        self.assertEqual(len(result["global_vars"]), 1)
        self.assertIn("branchConfig=feature/new", result["global_vars"])
        self.assertEqual(len(result["env_vars"]), 1)
        self.assertIn("*,branchConfig=feature/new", result["env_vars"])
        self.assertEqual(result["global_var_search_values"][0], "config-cadena")
        self.assertEqual(result["env_var_search_values"][0], "config-cadena")


if __name__ == "__main__":
    unittest.main()
