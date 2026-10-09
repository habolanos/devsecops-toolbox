# -*- coding: utf-8 -*-
"""Tests para pipeline_cd_backup_restore — rollback por revision historica."""
from unittest.mock import MagicMock, patch

import pytest

from scm.azdo import pipeline_cd_backup_restore as m


@pytest.fixture
def current_def():
    return {
        "id": 905,
        "name": "pipeline-test",
        "path": "\\",
        "revision": 10,
        "variables": {"Var1": {"value": "cur"}},
        "environments": [{"name": "Production", "id": 5, "releaseId": 99}],
    }


@pytest.fixture
def revision_def():
    return {
        "id": 905,
        "name": "pipeline-test",
        "path": "\\",
        "revision": 7,
        "variables": {"Var1": {"value": "old"}},
        "environments": [{"name": "Production", "id": 5, "releaseId": 80}],
    }


# ───────────────────────────── get_definition_revisions ──────────────────────
def test_get_revisions_sorts_desc_and_limits():
    fake = {"value": [{"revision": 5}, {"revision": 9}, {"revision": 8},
                      {"revision": 7}, {"revision": 6}, {"revision": 10}]}
    with patch.object(m, "api_get", return_value=fake):
        revs = m.get_definition_revisions("o", "p", 905, "pat", top=5)
    assert [r["revision"] for r in revs] == [10, 9, 8, 7, 6]


def test_get_revisions_url():
    with patch.object(m, "api_get", return_value={"value": []}) as mock_get:
        m.get_definition_revisions("org", "proj", 905, "pat", top=5)
    url = mock_get.call_args[0][0]
    assert "/definitions/905/revisions" in url


def test_get_revisions_fewer_than_five():
    with patch.object(m, "api_get", return_value={"value": [{"revision": 3}, {"revision": 2}]}):
        revs = m.get_definition_revisions("o", "p", 1, "pat", top=5)
    assert len(revs) == 2


def test_get_revisions_direct_list_response():
    with patch.object(m, "api_get", return_value=[{"revision": 4}, {"revision": 3}]):
        revs = m.get_definition_revisions("o", "p", 1, "pat", top=5)
    assert [r["revision"] for r in revs] == [4, 3]


def test_get_revisions_skips_non_dict_entries():
    with patch.object(m, "api_get", return_value={"value": [{"revision": 2}, "junk", {}]}):
        revs = m.get_definition_revisions("o", "p", 1, "pat", top=5)
    assert revs == [{"revision": 2}]


def test_get_definition_at_revision_url():
    with patch.object(m, "api_get", return_value={"revision": 7}) as mock_get:
        out = m.get_definition_at_revision("o", "p", 905, 7, "pat")
    assert "revision=7" in mock_get.call_args[0][0]
    assert out["revision"] == 7


# ───────────────────────────── build_rollback_payload ────────────────────────
def test_build_payload_uses_current_id_and_revision(current_def, revision_def):
    payload = m.build_rollback_payload(revision_def, current_def)
    assert payload["id"] == 905
    assert payload["revision"] == 10          # concurrency check = revision actual
    assert payload["variables"]["Var1"]["value"] == "old"  # contenido historico


def test_build_payload_strips_env_release_id(current_def, revision_def):
    payload = m.build_rollback_payload(revision_def, current_def)
    assert "releaseId" not in payload["environments"][0]


def test_build_payload_comment_default(current_def, revision_def):
    payload = m.build_rollback_payload(revision_def, current_def)
    assert "Rollback" in payload["comment"]


def test_build_payload_keeps_secret_null(current_def):
    rev = {"id": 905, "name": "p", "revision": 3,
           "variables": {"Sec": {"value": None, "isSecret": True}},
           "environments": []}
    payload = m.build_rollback_payload(rev, current_def)
    assert payload["variables"]["Sec"]["value"] is None


# ───────────────────────────── rollback_to_revision ──────────────────────────
def test_rollback_dry_run_no_side_effects(current_def, revision_def, tmp_path):
    with patch.object(m, "get_release_definition", return_value=current_def), \
         patch.object(m, "get_definition_at_revision", return_value=revision_def), \
         patch.object(m, "backup_single_pipeline") as mock_bak, \
         patch.object(m, "update_release_definition") as mock_put:
        result = m.rollback_to_revision("o", "p", 905, 7, "pat", dry_run=True)
    assert result["status"] == "dry_run"
    assert result["from_revision"] == 10
    assert result["to_revision"] == 7
    assert isinstance(result["diffs"], list)
    mock_bak.assert_not_called()
    mock_put.assert_not_called()


def test_rollback_success_backups_then_puts(current_def, revision_def):
    calls = []
    with patch.object(m, "get_release_definition", return_value=current_def), \
         patch.object(m, "get_definition_at_revision", return_value=revision_def), \
         patch.object(m, "backup_single_pipeline",
                      return_value={"status": "ok", "files": ["outcome/backups/b.json"]}) as mock_bak, \
         patch.object(m, "update_release_definition",
                      return_value={"revision": 11, "id": 905}) as mock_put:
        mock_bak.side_effect = lambda *a, **k: (calls.append("backup"), {"status": "ok", "files": ["b.json"]})[1]
        mock_put.side_effect = lambda *a, **k: (calls.append("put"), {"revision": 11, "id": 905})[1]
        result = m.rollback_to_revision("o", "p", 905, 7, "pat", dry_run=False)
    assert result["status"] == "ok"
    assert result["new_revision"] == 11
    assert result["backup_file"] == "b.json"
    assert calls == ["backup", "put"]  # backup ANTES del PUT
    sent = mock_put.call_args[0][3]
    assert sent["revision"] == 10      # concurrency = revision actual
    assert sent["id"] == 905


def test_rollback_backup_failure_aborts(current_def, revision_def):
    with patch.object(m, "get_release_definition", return_value=current_def), \
         patch.object(m, "get_definition_at_revision", return_value=revision_def), \
         patch.object(m, "backup_single_pipeline", return_value={"status": "error: disk", "files": []}), \
         patch.object(m, "update_release_definition") as mock_put:
        result = m.rollback_to_revision("o", "p", 905, 7, "pat")
    assert result["status"] == "error"
    assert "backup" in result["message"].lower()
    mock_put.assert_not_called()


def test_rollback_api_error_propagates(current_def):
    with patch.object(m, "get_release_definition", return_value=current_def), \
         patch.object(m, "get_definition_at_revision", side_effect=Exception("HTTP 404")):
        with pytest.raises(Exception, match="404"):
            m.rollback_to_revision("o", "p", 905, 7, "pat")


# ───────────────────────────── resolve_names (int variableGroups) ────────────
def test_resolve_names_accepts_int_variable_groups():
    """AzDO puede devolver variableGroups como lista de ints, no de dicts."""
    definition = {
        "variableGroups": [123, {"id": 456}],
        "environments": [{
            "name": "Prod",
            "variableGroups": [789],
            "deployPhases": [{"deploymentInput": {"queueId": 9}, "workflowTasks": []}],
        }],
    }
    with patch.object(m, "get_agent_queue_name", return_value="pool"), \
         patch.object(m, "get_variable_group_name", return_value="vg") as mock_vg, \
         patch.object(m, "get_task_group_name", return_value="tg"):
        resolved = m.resolve_names(definition, "o", "p", "pat")
    assert set(resolved["variable_groups"].keys()) == {"123", "456", "789"}
    assert resolved["agent_pools"] == {"9": "pool"}


# ───────────────────────────── print_revisions_table ─────────────────────────
def test_print_revisions_table_marks_current():
    revs = [{"revision": 10, "changedDate": "2026-01-01T10:00:00Z",
             "changedBy": {"displayName": "Ana"}, "changeType": "update", "comment": "fix"},
            {"revision": 9, "changedBy": {"displayName": "Bob"}}]
    m.print_revisions_table(revs, current_revision=10)  # no exception
