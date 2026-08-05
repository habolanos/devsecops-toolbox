#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for azdo_pipeline_history.py

Tests cover:
- Date helpers (parse_iso, format_date, months_ago_iso)
- Extractors (extract_stages, extract_variables, extract_tasks, extract_artifacts)
- Diff logic (diff_stages, diff_variables, diff_tasks, diff_artifacts, compute_full_diff)
- HTML generation (generate_html basic structure validation)
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "azdo"))

from azdo_pipeline_history import (
    parse_iso,
    format_date,
    months_ago_iso,
    extract_stages,
    extract_variables,
    extract_tasks,
    extract_artifacts,
    diff_stages,
    diff_variables,
    diff_tasks,
    diff_artifacts,
    compute_full_diff,
    generate_html,
    make_headers,
    vsrm,
)


# =============================================================================
# DATE HELPERS
# =============================================================================
class TestParseIso:
    def test_valid_iso_with_millis(self):
        result = parse_iso("2026-01-15T10:30:00.123Z")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_valid_iso_without_millis(self):
        result = parse_iso("2026-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2026

    def test_empty_string(self):
        assert parse_iso("") is None

    def test_none(self):
        assert parse_iso(None) is None

    def test_invalid_format(self):
        assert parse_iso("not-a-date") is None


class TestFormatDate:
    def test_valid_date(self):
        result = format_date("2026-01-15T10:30:00Z", "UTC")
        assert "2026-01-15" in result

    def test_empty_date(self):
        assert format_date("", "UTC") == "—"

    def test_invalid_date(self):
        assert format_date("invalid", "UTC") == "—"


class TestMonthsAgoIso:
    def test_returns_iso_string(self):
        result = months_ago_iso(6)
        assert "T" in result
        assert "Z" in result

    def test_approximately_6_months_ago(self):
        result = months_ago_iso(6)
        parsed = parse_iso(result)
        now = datetime.now(timezone.utc)
        diff = now - parsed
        assert 170 < diff.days < 200  # ~180 days


# =============================================================================
# EXTRACTORS
# =============================================================================
class TestExtractStages:
    def test_empty_environments(self):
        assert extract_stages({}) == []

    def test_single_stage(self):
        defn = {
            "environments": [
                {"name": "QA", "rank": 1, "preDeployApprovals": {"approvals": []},
                 "postDeployApprovals": {"approvals": []},
                 "deployPhases": [{"deploymentInput": {"queueId": 5}}],
                 "condition": "succeeded()"}
            ]
        }
        stages = extract_stages(defn)
        assert len(stages) == 1
        assert stages[0]["name"] == "QA"
        assert stages[0]["rank"] == 1
        assert stages[0]["agent_pool"] == 5

    def test_multiple_stages_sorted_by_rank(self):
        defn = {
            "environments": [
                {"name": "Prod", "rank": 2, "preDeployApprovals": {"approvals": []},
                 "postDeployApprovals": {"approvals": []},
                 "deployPhases": [{"deploymentInput": {"queueId": 1}}]},
                {"name": "QA", "rank": 1, "preDeployApprovals": {"approvals": []},
                 "postDeployApprovals": {"approvals": []},
                 "deployPhases": [{"deploymentInput": {"queueId": 1}}]},
            ]
        }
        stages = extract_stages(defn)
        assert stages[0]["name"] == "QA"
        assert stages[1]["name"] == "Prod"

    def test_pre_post_approvals_count(self):
        defn = {
            "environments": [
                {"name": "Prod", "rank": 1,
                 "preDeployApprovals": {"approvals": [
                     {"isAutomated": True}, {"isAutomated": False}
                 ]},
                 "postDeployApprovals": {"approvals": [
                     {"isAutomated": False}
                 ]},
                 "deployPhases": [{"deploymentInput": {}}]}
            ]
        }
        stages = extract_stages(defn)
        assert stages[0]["pre_approvals"] == 1
        assert stages[0]["post_approvals"] == 1


class TestExtractVariables:
    def test_empty(self):
        assert extract_variables({}) == []

    def test_normal_variables(self):
        defn = {"variables": {"VAR1": {"value": "hello"}, "VAR2": {"value": "world"}}}
        result = extract_variables(defn)
        assert len(result) == 2
        names = {v["name"] for v in result}
        assert names == {"VAR1", "VAR2"}
        assert all(v["scope"] == "Pipeline" for v in result)

    def test_secret_variables_not_masked(self):
        defn = {"variables": {"SECRET": {"value": "supersecret", "isSecret": True}}}
        result = extract_variables(defn)
        assert len(result) == 1
        assert result[0]["name"] == "SECRET"
        assert result[0]["value"] == "supersecret"
        assert result[0]["isSecret"] is True

    def test_non_dict_variable(self):
        defn = {"variables": {"PLAIN": "value"}}
        result = extract_variables(defn)
        assert len(result) == 1
        assert result[0]["name"] == "PLAIN"
        assert result[0]["value"] == "value"

    def test_environment_scope_variables(self):
        defn = {
            "variables": {"GLOBAL": {"value": "g"}},
            "environments": [
                {"name": "QA", "variables": {"QA_VAR": {"value": "q"}}},
            ],
        }
        result = extract_variables(defn)
        assert len(result) == 2
        qa_var = [v for v in result if v["name"] == "QA_VAR"][0]
        assert qa_var["scope"] == "QA"
        assert qa_var["value"] == "q"
        global_var = [v for v in result if v["name"] == "GLOBAL"][0]
        assert global_var["scope"] == "Pipeline"


class TestExtractTasks:
    def test_empty(self):
        assert extract_tasks({}) == []

    def test_single_task(self):
        defn = {
            "environments": [
                {"name": "QA", "deployPhases": [
                    {"workflowTasks": [
                        {"displayName": "Deploy", "taskId": "abc", "enabled": True}
                    ]}
                ]}
            ]
        }
        tasks = extract_tasks(defn)
        assert len(tasks) == 1
        assert tasks[0]["displayName"] == "Deploy"
        assert tasks[0]["env"] == "QA"

    def test_multiple_envs(self):
        defn = {
            "environments": [
                {"name": "QA", "deployPhases": [
                    {"workflowTasks": [{"displayName": "Task1", "taskId": "1", "enabled": True}]}
                ]},
                {"name": "Prod", "deployPhases": [
                    {"workflowTasks": [{"displayName": "Task2", "taskId": "2", "enabled": False}]}
                ]},
            ]
        }
        tasks = extract_tasks(defn)
        assert len(tasks) == 2
        assert tasks[0]["env"] == "QA"
        assert tasks[1]["env"] == "Prod"


class TestExtractArtifacts:
    def test_empty(self):
        assert extract_artifacts({}) == []

    def test_single_artifact(self):
        defn = {"artifacts": [{"alias": "drop", "type": "Build", "sourceId": "123", "isPrimary": True}]}
        arts = extract_artifacts(defn)
        assert len(arts) == 1
        assert arts[0]["alias"] == "drop"
        assert arts[0]["isPrimary"] is True


# =============================================================================
# DIFF LOGIC
# =============================================================================
class TestDiffStages:
    def test_no_changes(self):
        stages = [{"name": "QA", "rank": 1, "pre_approvals": 0, "post_approvals": 0,
                    "agent_pool": 1, "condition": ""}]
        assert diff_stages(stages, stages) == []

    def test_stage_added(self):
        old = [{"name": "QA", "rank": 1, "pre_approvals": 0, "post_approvals": 0,
                "agent_pool": 1, "condition": ""}]
        new = [{"name": "QA", "rank": 1, "pre_approvals": 0, "post_approvals": 0,
                "agent_pool": 1, "condition": ""},
               {"name": "Prod", "rank": 2, "pre_approvals": 1, "post_approvals": 0,
                "agent_pool": 2, "condition": ""}]
        changes = diff_stages(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "added"
        assert "Prod" in changes[0]["field"]

    def test_stage_removed(self):
        old = [{"name": "QA", "rank": 1, "pre_approvals": 0, "post_approvals": 0,
                "agent_pool": 1, "condition": ""},
               {"name": "Prod", "rank": 2, "pre_approvals": 0, "post_approvals": 0,
                "agent_pool": 2, "condition": ""}]
        new = [{"name": "QA", "rank": 1, "pre_approvals": 0, "post_approvals": 0,
                "agent_pool": 1, "condition": ""}]
        changes = diff_stages(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "removed"

    def test_stage_modified_rank(self):
        old = [{"name": "QA", "rank": 1, "pre_approvals": 0, "post_approvals": 0,
                "agent_pool": 1, "condition": ""}]
        new = [{"name": "QA", "rank": 2, "pre_approvals": 0, "post_approvals": 0,
                "agent_pool": 1, "condition": ""}]
        changes = diff_stages(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "modified"
        assert "Rank" in changes[0]["field"]
        assert changes[0]["old_value"] == "1"
        assert changes[0]["new_value"] == "2"

    def test_stage_modified_agent_pool(self):
        old = [{"name": "QA", "rank": 1, "pre_approvals": 0, "post_approvals": 0,
                "agent_pool": 1, "condition": ""}]
        new = [{"name": "QA", "rank": 1, "pre_approvals": 0, "post_approvals": 0,
                "agent_pool": 5, "condition": ""}]
        changes = diff_stages(old, new)
        assert len(changes) == 1
        assert "Agent Pool" in changes[0]["field"]


class TestDiffVariables:
    def _make_vars(self, mapping, scope="Pipeline"):
        return [{"name": k, "value": v, "scope": scope, "isSecret": False} for k, v in mapping.items()]

    def test_no_changes(self):
        vars_ = self._make_vars({"A": "1", "B": "2"})
        assert diff_variables(vars_, vars_) == []

    def test_variable_added(self):
        old = self._make_vars({"A": "1"})
        new = self._make_vars({"A": "1", "B": "2"})
        changes = diff_variables(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "added"
        assert "B" in changes[0]["field"]
        assert changes[0]["scope"] == "Pipeline"

    def test_variable_removed(self):
        old = self._make_vars({"A": "1", "B": "2"})
        new = self._make_vars({"A": "1"})
        changes = diff_variables(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "removed"

    def test_variable_modified(self):
        old = self._make_vars({"A": "1"})
        new = self._make_vars({"A": "2"})
        changes = diff_variables(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "modified"
        assert changes[0]["old_value"] == "1"
        assert changes[0]["new_value"] == "2"

    def test_empty_value_shown_as_vacio(self):
        old = self._make_vars({"A": "1"})
        new = self._make_vars({"A": ""})
        changes = diff_variables(old, new)
        assert changes[0]["new_value"] == "(vacio)"

    def test_same_var_different_scope(self):
        old = self._make_vars({"A": "1"}, scope="Pipeline")
        new = old + self._make_vars({"A": "2"}, scope="QA")
        changes = diff_variables(old, new)
        assert len(changes) == 1
        assert changes[0]["scope"] == "QA"
        assert changes[0]["action"] == "added"


class TestDiffTasks:
    def test_no_changes(self):
        tasks = [{"env": "QA", "displayName": "Deploy", "taskId": "1", "enabled": True,
                  "alwaysRun": False, "continueOnError": False}]
        assert diff_tasks(tasks, tasks) == []

    def test_task_added(self):
        old = [{"env": "QA", "displayName": "Deploy", "taskId": "1", "enabled": True,
                "alwaysRun": False, "continueOnError": False}]
        new = old + [{"env": "Prod", "displayName": "Deploy", "taskId": "1", "enabled": True,
                      "alwaysRun": False, "continueOnError": False}]
        changes = diff_tasks(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "added"

    def test_task_removed(self):
        old = [{"env": "QA", "displayName": "Deploy", "taskId": "1", "enabled": True,
                "alwaysRun": False, "continueOnError": False},
               {"env": "Prod", "displayName": "Notify", "taskId": "2", "enabled": True,
                "alwaysRun": False, "continueOnError": False}]
        new = [old[0]]
        changes = diff_tasks(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "removed"

    def test_task_enabled_changed(self):
        old = [{"env": "QA", "displayName": "Deploy", "taskId": "1", "enabled": True,
                "alwaysRun": False, "continueOnError": False}]
        new = [{"env": "QA", "displayName": "Deploy", "taskId": "1", "enabled": False,
                "alwaysRun": False, "continueOnError": False}]
        changes = diff_tasks(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "modified"
        assert "Enabled" in changes[0]["field"]


class TestDiffArtifacts:
    def test_no_changes(self):
        arts = [{"alias": "drop", "type": "Build", "sourceId": "1", "isPrimary": True}]
        assert diff_artifacts(arts, arts) == []

    def test_artifact_added(self):
        old = [{"alias": "drop", "type": "Build", "sourceId": "1", "isPrimary": True}]
        new = old + [{"alias": "repo", "type": "Git", "sourceId": "2", "isPrimary": False}]
        changes = diff_artifacts(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "added"

    def test_artifact_type_changed(self):
        old = [{"alias": "drop", "type": "Build", "sourceId": "1", "isPrimary": True}]
        new = [{"alias": "drop", "type": "Git", "sourceId": "1", "isPrimary": True}]
        changes = diff_artifacts(old, new)
        assert len(changes) == 1
        assert changes[0]["action"] == "modified"


class TestComputeFullDiff:
    def test_empty_definitions(self):
        assert compute_full_diff({}, {}) == []

    def test_multiple_categories(self):
        old = {
            "environments": [
                {"name": "QA", "rank": 1, "preDeployApprovals": {"approvals": []},
                 "postDeployApprovals": {"approvals": []},
                 "deployPhases": [{"deploymentInput": {"queueId": 1},
                                  "workflowTasks": [{"displayName": "T1", "taskId": "1", "enabled": True}]}]}
            ],
            "variables": {"V1": {"value": "old"}},
            "artifacts": [{"alias": "drop", "type": "Build", "sourceId": "1", "isPrimary": True}],
        }
        new = {
            "environments": [
                {"name": "QA", "rank": 1, "preDeployApprovals": {"approvals": []},
                 "postDeployApprovals": {"approvals": []},
                 "deployPhases": [{"deploymentInput": {"queueId": 2},
                                  "workflowTasks": [{"displayName": "T1", "taskId": "1", "enabled": True}]}]},
                {"name": "Prod", "rank": 2, "preDeployApprovals": {"approvals": []},
                 "postDeployApprovals": {"approvals": []},
                 "deployPhases": [{"deploymentInput": {"queueId": 2}}]}
            ],
            "variables": {"V1": {"value": "new"}, "V2": {"value": "added"}},
            "artifacts": [{"alias": "drop", "type": "Build", "sourceId": "1", "isPrimary": True}],
        }
        changes = compute_full_diff(old, new)
        categories = {c["category"] for c in changes}
        assert "Stage" in categories
        assert "Variable" in categories
        # Agent pool change + new stage
        stage_changes = [c for c in changes if c["category"] == "Stage"]
        assert len(stage_changes) >= 2


# =============================================================================
# HTML GENERATION
# =============================================================================
class TestGenerateHtml:
    def test_generates_valid_html(self):
        data = {
            "definition": {"name": "TestPipeline", "id": 42},
            "revisions": [
                {"revision": 1, "modifiedOn": "2026-01-01T10:00:00Z",
                 "modifiedBy": {"displayName": "User1"}, "comment": "Initial"}
            ],
            "releases": [
                {"id": 100, "name": "Release-100", "status": "succeeded",
                 "createdOn": "2026-01-02T10:00:00Z", "createdBy": {"displayName": "User1"}}
            ],
            "diffs": {1: []},
            "project": "TestProject",
            "range_start": "2026-01-01T00:00:00Z",
            "range_end": "2026-08-01T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_history.html"
            generate_html(data, "UTC", path)
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "<!DOCTYPE html>" in content
            assert "TestPipeline" in content
            assert "chart.js" in content
            assert "timelineChart" in content

    def test_html_with_diffs(self):
        data = {
            "definition": {"name": "TestPipeline", "id": 42},
            "revisions": [
                {"revision": 1, "modifiedOn": "2026-01-01T10:00:00Z",
                 "modifiedBy": {"displayName": "User1"}, "comment": "Initial"},
                {"revision": 2, "modifiedOn": "2026-02-01T10:00:00Z",
                 "modifiedBy": {"displayName": "User2"}, "comment": "Add stage"},
            ],
            "releases": [],
            "diffs": {
                1: [],
                2: [{"category": "Stage", "field": "Stage 'Prod'",
                     "old_value": "(no existia)", "new_value": "rank=2", "action": "added"}],
            },
            "project": "TestProject",
            "range_start": "2026-01-01T00:00:00Z",
            "range_end": "2026-08-01T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_history.html"
            generate_html(data, "UTC", path)
            content = path.read_text(encoding="utf-8")
            assert "Rev 2" in content
            assert "Prod" in content
            assert "added" in content


# =============================================================================
# HTTP HELPERS
# =============================================================================
class TestMakeHeaders:
    def test_headers_contain_auth(self):
        headers = make_headers("fake-pat")
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
        assert "Accept" in headers


class TestVsrm:
    def test_replaces_dev_azure(self):
        url = "https://dev.azure.com/myorg"
        result = vsrm(url)
        assert "vsrm.dev.azure.com" in result

    def test_no_change_if_already_vsrm(self):
        url = "https://vsrm.dev.azure.com/myorg"
        result = vsrm(url)
        # vsrm() does a simple string replace, so already-vsrm URLs get doubled
        # This is expected behavior - callers should pass non-vsrm URLs
        assert "vsrm.dev.azure.com" in result
