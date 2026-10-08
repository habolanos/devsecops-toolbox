# -*- coding: utf-8 -*-
"""Tests para pipeline_cd_template — limpieza de definición, templates
(full + DSL updater), diff de apply y carga de templates (sin API)."""

import pytest
import yaml

from scm.azdo.pipeline_cd_template import (
    _safe_name,
    apply_diff_summary,
    apply_template,
    build_full_template,
    build_updater_template,
    clean_definition_for_template,
    load_template_definition,
    redact_secret_values,
)


def _defn(**over):
    d = {
        "id": 905, "name": "CD-Origen", "path": "\\OMS",
        "revision": 42, "createdOn": "2026-01-01", "modifiedOn": "x",
        "createdBy": {"id": "u"}, "modifiedBy": {"id": "u"},
        "_links": {"web": {}}, "url": "https://...", "badgeUrl": "b",
        "projectReference": {"id": "p"}, "isDeleted": False,
        "currentRelease": {"id": 1}, "lastRelease": {"id": 2},
        "releaseNameFormat": "Release-$(rev:r)",
        "variables": {
            "plain": {"value": "v1", "allowOverride": True},
            "topsecret": {"value": "s3cr3t", "isSecret": True},
        },
        "variableGroups": [12],
        "environments": [
            {"id": 100, "name": "Develop", "releaseId": 5, "badgeUrl": "b",
             "queue": {"name": "pool"}, "rank": 1,
             "variables": {"envsec": {"value": "e", "isSecret": True}},
             "variableGroups": [{"id": 34}],
             "preDeployApprovals": {"approvals": [{"id": 9, "rank": 1,
                                                 "approver": {"id": "u"}}]},
             "postDeployApprovals": {"approvals": []},
             "deployPhases": [{"id": 55, "rank": 1,
                               "phaseType": "agentBasedDeployment",
                               "deploymentInput": {"queueId": 77},
                               "workflowTasks": [
                                   {"name": "t1", "taskId": "g1",
                                    "task": {"id": "g1", "name": "Task"}}]}]},
            {"id": 101, "name": "Production", "releaseId": 6, "rank": 2,
             "deployPhases": []},
        ],
        "artifacts": [{"alias": "_build", "type": "Build"}],
        "triggers": [],
    }
    d.update(over)
    return d


class TestCleanDefinitionForTemplate:
    def test_strips_system_fields(self):
        d = clean_definition_for_template(_defn())
        for f in ("id", "revision", "createdOn", "modifiedOn", "_links",
                  "url", "projectReference", "isDeleted", "currentRelease",
                  "badgeUrl", "lastRelease"):
            assert f not in d
        assert d["name"] == "CD-Origen"
        assert d["releaseNameFormat"] == "Release-$(rev:r)"

    def test_strips_env_and_phase_ids(self):
        d = clean_definition_for_template(_defn())
        env = d["environments"][0]
        assert "id" not in env and "releaseId" not in env
        assert "badgeUrl" not in env and "queue" not in env
        assert env["name"] == "Develop" and env["rank"] == 1
        assert "id" not in env["deployPhases"][0]
        assert env["deployPhases"][0]["deploymentInput"]["queueId"] == 77
        assert env["deployPhases"][0]["workflowTasks"][0]["taskId"] == "g1"
        # approvals conservan approver pero sin id propio
        assert "id" not in env["preDeployApprovals"]["approvals"][0]
        assert env["preDeployApprovals"]["approvals"][0]["approver"]

    def test_does_not_mutate_original(self):
        src = _defn()
        clean_definition_for_template(src)
        assert src["id"] == 905 and src["environments"][0]["id"] == 100


class TestRedactSecretValues:
    def test_nulls_secret_values_and_lists_them(self):
        d = _defn()
        secrets = redact_secret_values(d)
        assert d["variables"]["topsecret"]["value"] is None
        assert d["variables"]["topsecret"]["isSecret"] is True
        assert d["variables"]["plain"]["value"] == "v1"
        assert d["environments"][0]["variables"]["envsec"]["value"] is None
        scopes = {(s["scope"], s["name"]) for s in secrets}
        assert scopes == {("definition", "topsecret"),
                          ("environment", "envsec")}


class TestBuildFullTemplate:
    def test_structure(self):
        src = _defn()
        clean = clean_definition_for_template(src)
        secrets = redact_secret_values(clean)
        tpl = build_full_template(clean, src, "Org", "Proj",
                                  {"agent_queues": {"77": "pool-x"}},
                                  secrets)
        assert tpl["metadata"]["source"]["definition_id"] == 905
        assert tpl["metadata"]["source"]["stages"] == ["Develop",
                                                       "Production"]
        assert "environments" in tpl["definition"]
        assert "id" not in tpl["definition"]
        assert tpl["resolved_names"]["agent_queues"]["77"] == "pool-x"
        assert len(tpl["secrets"]) == 2


class TestBuildUpdaterTemplate:
    def test_structure(self):
        clean = clean_definition_for_template(_defn())
        tpl = build_updater_template(clean, _defn())
        assert tpl["search"]["stages"] == [{"name": "*"}]
        stages = tpl["update"]["stages"]
        assert [s["name"] for s in stages] == ["Develop", "Production"]
        assert all(s["action"] == "add" and s["position"] == "end"
                   for s in stages)
        assert stages[0]["definition"]["name"] == "Develop"
        vars_ = {v["name"]: v for v in tpl["update"]["variables"]}
        assert vars_["plain"]["value"] == "v1"
        assert vars_["topsecret"]["isSecret"] is True
        assert vars_["topsecret"]["value"] == ""
        assert tpl["options"]["dry_run"] is True


class TestLoadTemplateDefinition:
    def test_wrapped(self, tmp_path):
        p = tmp_path / "t.yaml"
        p.write_text(yaml.safe_dump(
            {"metadata": {}, "definition": {"environments": []}}),
            encoding="utf-8")
        assert load_template_definition(p) == {"environments": []}

    def test_raw_definition(self, tmp_path):
        p = tmp_path / "t.yaml"
        p.write_text(yaml.safe_dump({"name": "x", "environments": []}),
                     encoding="utf-8")
        assert load_template_definition(p)["name"] == "x"

    def test_invalid_raises(self, tmp_path):
        p = tmp_path / "t.yaml"
        p.write_text("foo: bar", encoding="utf-8")
        with pytest.raises(ValueError):
            load_template_definition(p)


class TestApplyDiffSummary:
    def test_stage_and_var_diff(self):
        target = _defn(name="CD-Destino")
        tpl = clean_definition_for_template(
            _defn(environments=[{"name": "Develop", "deployPhases": []},
                                {"name": "Nuevo", "deployPhases": []}],
                  variables={"plain": {"value": "v1"},
                             "extra": {"value": "9"}}))
        lines = "\n".join(apply_diff_summary(target, tpl))
        assert "+ stages nuevos: Nuevo" in lines
        assert "- stages eliminados: Production" in lines
        assert "= stages reemplazados: Develop" in lines
        assert "+ variables: extra" in lines
        assert "- variables: topsecret" in lines


class _Client:
    base = "https://vsrm.dev.azure.com/o/p"

    def __init__(self, target):
        self.target = target
        self.put_calls = []

    def get(self, url, params=None, **kw):
        return self.target

    def put(self, url, payload, params=None):
        self.put_calls.append((url, payload))
        return {"id": payload["id"], "name": payload["name"],
                "revision": payload["revision"] + 1}


class TestApplyTemplate:
    def test_dry_run_no_put(self):
        c = _Client(_defn(id=910, name="CD-Destino", revision=7))
        tpl = clean_definition_for_template(_defn())
        res = apply_template(c, 910, tpl, dry_run=True)
        assert res["result"] is None and res["backup"] is None
        assert c.put_calls == []
        assert res["payload"]["id"] == 910
        assert res["payload"]["revision"] == 7
        # nombre/path se mantienen del destino por default
        assert res["payload"]["name"] == "CD-Destino"
        assert res["payload"]["path"] == "\\OMS"

    def test_put_with_overrides_and_backup(self, tmp_path):
        c = _Client(_defn(id=910, name="CD-Destino", revision=7))
        tpl = clean_definition_for_template(_defn())
        res = apply_template(c, 910, tpl, new_name="CD-Nuevo",
                             new_path="\\LAB", backup_dir=tmp_path)
        url, payload = c.put_calls[0]
        assert url.endswith("/definitions/910")
        assert payload["id"] == 910 and payload["name"] == "CD-Nuevo"
        assert payload["path"] == "\\LAB"
        assert "id" not in payload["environments"][0]
        assert res["backup"].exists()
        assert "910" in res["backup"].name
        assert res["result"]["revision"] == 8


class TestSafeName:
    def test_sanitizes(self):
        assert _safe_name("CD OMS/Prod: v2") == "CD_OMS_Prod__v2"
        assert _safe_name("") == "pipeline"
