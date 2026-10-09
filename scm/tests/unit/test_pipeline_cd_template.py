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
        assert "- stages solo en destino: Production" in lines
        assert "= stages en ambos: Develop" in lines
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
        # merge (default): stage existente en destino se conserva con su id
        assert payload["environments"][0]["id"] == 100
        assert res["backup"]["yaml"].exists()
        assert res["backup"]["json"].exists()
        assert "910" in res["backup"]["yaml"].name
        assert res["result"]["revision"] == 8


class TestSafeName:
    def test_sanitizes(self):
        assert _safe_name("CD OMS/Prod: v2") == "CD_OMS_Prod__v2"
        assert _safe_name("") == "pipeline"


# ═══════════════════════════════════════════════════════════════════════════
# Placeholders [[target.*]] — valores tomados de la definición destino
# ═══════════════════════════════════════════════════════════════════════════

from scm.azdo.pipeline_cd_template import (
    _target_lookup, resolve_target_placeholders,
)


def _target():
    d = _defn(id=910, name="CD-Destino", path=r"\OMS\Sub",
              artifacts=[
                  {"alias": "_MiBuild",
                   "definitionReference": {"definition": {"name": "CI-Main"}}},
                  {"alias": "_Repo",
                   "definitionReference": {"definition": {"name": "repo-x"}}},
              ])
    d["variables"]["TargetVar"] = {"value": "valor-destino"}
    d["environments"][0]["variables"]["EnvVar"] = {"value": "env-valor"}
    return d


class TestTargetLookup:
    T = _target()

    def test_scalars(self):
        assert _target_lookup(self.T, "name") == "CD-Destino"
        assert _target_lookup(self.T, "id") == 910
        assert _target_lookup(self.T, "path") == r"\OMS\Sub"

    def test_artifact_alias_and_name(self):
        assert _target_lookup(self.T, "artifact.alias") == "_MiBuild"
        assert _target_lookup(self.T, "artifact.name") == "CI-Main"
        assert _target_lookup(self.T, "artifact.1.alias") == "_Repo"

    def test_artifact_out_of_range(self):
        assert _target_lookup(self.T, "artifact.9.alias") is None

    def test_vars(self):
        assert _target_lookup(self.T, "var.TargetVar") == "valor-destino"
        assert _target_lookup(self.T, "var.NoExiste") is None

    def test_env_var_case_insensitive_stage(self):
        assert _target_lookup(self.T, "env.Develop.var.EnvVar") \
            == "env-valor"
        assert _target_lookup(self.T, "env.develop.var.EnvVar") \
            == "env-valor"
        assert _target_lookup(self.T, "env.QA.var.EnvVar") is None

    def test_unknown_path(self):
        assert _target_lookup(self.T, "otro.campo") is None


class TestResolveTargetPlaceholders:
    def test_substitutes_nested(self):
        node = {"variables": {"Art": {"value": "[[target.artifact.alias]]"}},
                "environments": [
                    {"name": "Develop",
                     "deployPhases": [{"workflowTasks": [
                         {"inputs": {"script": "deploy [[target.name]] "
                                               "[[target.env.Develop.var.EnvVar]]"}}]}]}]}
        out = resolve_target_placeholders(node, _target())
        assert out["variables"]["Art"]["value"] == "_MiBuild"
        script = out["environments"][0]["deployPhases"][0] \
            ["workflowTasks"][0]["inputs"]["script"]
        assert script == "deploy CD-Destino env-valor"

    def test_unresolved_stays_literal_and_reported(self):
        unresolved = []
        out = resolve_target_placeholders(
            {"v": "[[target.var.NoExiste]]"}, _target(), unresolved)
        assert out["v"] == "[[target.var.NoExiste]]"
        assert unresolved == ["[[target.var.NoExiste]]"]

    def test_no_collide_with_azdo_macros(self):
        node = {"v": "$(var) #{tok}# {{jinja}} {ps:block}"}
        assert resolve_target_placeholders(node, _target())["v"] == \
            "$(var) #{tok}# {{jinja}} {ps:block}"


class TestApplyTemplatePlaceholders:
    def test_apply_resolves_placeholders_against_target(self, tmp_path):
        c = _Client(_target())
        tpl = clean_definition_for_template(_defn())
        tpl["variables"]["Art"] = {"value": "[[target.artifact.alias]]"}
        res = apply_template(c, 910, tpl, backup_dir=tmp_path)
        _, payload = c.put_calls[0]
        assert payload["variables"]["Art"]["value"] == "_MiBuild"

    def test_unresolved_reported_in_summary(self):
        c = _Client(_target())
        tpl = clean_definition_for_template(_defn())
        tpl["variables"]["X"] = {"value": "[[target.var.Inexistente]]"}
        res = apply_template(c, 910, tpl, dry_run=True)
        assert any("sin resolver" in l for l in res["summary"])


# ═══════════════════════════════════════════════════════════════════════════
# Preserve — valores del destino que no se sobrescriben
# ═══════════════════════════════════════════════════════════════════════════

from scm.azdo.pipeline_cd_template import (
    DEFAULT_PRESERVE_PATHS,
    _parse_preserve,
    load_target_backup,
    preserve_from_target,
)


class TestPreserveFromTarget:
    def test_artifacts_and_triggers_preserved(self):
        payload = {"artifacts": [{"alias": "_origen"}],
                   "triggers": [{"x": 1}], "name": "tpl"}
        target = {"artifacts": [{"alias": "_destino"}],
                  "triggers": [{"y": 2}]}
        applied, skipped = preserve_from_target(payload, target,
                                                ["artifacts", "triggers"])
        assert applied == ["artifacts", "triggers"]
        assert skipped == []
        assert payload["artifacts"] == [{"alias": "_destino"}]
        assert payload["triggers"] == [{"y": 2}]

    def test_missing_in_target_skipped(self):
        payload = {"artifacts": [{"alias": "_origen"}]}
        applied, skipped = preserve_from_target(payload, {}, ["artifacts"])
        assert applied == [] and skipped == ["artifacts"]
        assert payload["artifacts"] == [{"alias": "_origen"}]

    def test_var_path(self):
        payload = {"variables": {}}
        target = {"variables": {"Art": {"value": "v"}}}
        applied, _ = preserve_from_target(payload, target, ["var.Art"])
        assert applied == ["var.Art"]
        assert payload["variables"]["Art"] == {"value": "v"}

    def test_env_field_path(self):
        payload = {"environments": [{"name": "Prod", "variables": {}}]}
        target = {"environments": [{"name": "prod",
                                    "variables": {"K": {"value": "1"}}}]}
        applied, _ = preserve_from_target(payload, target,
                                          ["env.Prod.variables"])
        assert applied == ["env.Prod.variables"]
        assert payload["environments"][0]["variables"]["K"]["value"] == "1"

    def test_env_not_in_payload_skipped(self):
        payload = {"environments": [{"name": "Dev"}]}
        target = {"environments": [{"name": "Prod", "variables": {}}]}
        applied, skipped = preserve_from_target(payload, target,
                                                ["env.Prod.variables"])
        assert applied == [] and skipped == ["env.Prod.variables"]

    def test_env_whole_stage_replaces_same_name(self):
        payload = {"environments": [{"name": "QA", "rank": 1,
                                     "variables": {"T": {"value": "tpl"}}}]}
        target = {"environments": [{"name": "qa", "id": 7, "releaseId": 3,
                                    "badgeUrl": "b",
                                    "variables": {"K": {"value": "dst"}}}]}
        applied, _ = preserve_from_target(payload, target, ["env.QA"])
        assert applied == ["env.QA"]
        env = payload["environments"][0]
        assert env["variables"]["K"]["value"] == "dst"   # del destino
        assert env["id"] == 7                            # id del destino se conserva
        assert "releaseId" not in env and "badgeUrl" not in env

    def test_env_whole_stage_appended_if_missing_in_template(self):
        payload = {"environments": [{"name": "Dev"}]}
        target = {"environments": [{"name": "SCM Inspection", "id": 9,
                                    "variables": {"A": {"value": "1"}}}]}
        applied, _ = preserve_from_target(payload, target,
                                          ["env.SCM Inspection"])
        assert applied == ["env.SCM Inspection"]
        assert [e["name"] for e in payload["environments"]] == \
            ["Dev", "SCM Inspection"]

    def test_env_wildcard_preserves_all_target_stages(self):
        payload = {"environments": [{"name": "QA", "variables": {"T": {"v": "t"}}},
                                    {"name": "NuevoStage"}]}
        target = {"environments": [{"name": "Develop"}, {"name": "QA"},
                                   {"name": "Production"}]}
        applied, _ = preserve_from_target(payload, target, ["env.*"])
        names = [e["name"] for e in payload["environments"]]
        assert applied == ["env.Develop", "env.QA", "env.Production"]
        assert names == ["QA", "NuevoStage", "Develop", "Production"]

    def test_env_stage_absent_in_target_skipped(self):
        payload = {"environments": []}
        applied, skipped = preserve_from_target(
            payload, {"environments": []}, ["env.Inexistente"])
        assert applied == [] and skipped == ["env.Inexistente"]

    def test_deepcopy_no_aliasing(self):
        target = {"artifacts": [{"alias": "_d"}]}
        payload = {}
        preserve_from_target(payload, target, ["artifacts"])
        payload["artifacts"][0]["alias"] = "mutado"
        assert target["artifacts"][0]["alias"] == "_d"


class TestParsePreserve:
    def test_empty_is_default(self):
        assert _parse_preserve("") is None
    def test_none_disables(self):
        assert _parse_preserve("none") == []
        assert _parse_preserve("NO") == []
    def test_list(self):
        assert _parse_preserve("artifacts, var.X ,env.Prod.variables") == \
            ["artifacts", "var.X", "env.Prod.variables"]


class TestApplyTemplatePreserve:
    def test_default_preserves_target_artifacts(self):
        tgt = _target()
        tgt["triggers"] = [{"triggerType": "artifactSource"}]
        c = _Client(tgt)
        tpl = clean_definition_for_template(_defn())
        tpl["artifacts"] = [{"alias": "_ORIGEN", "type": "Build"}]
        res = apply_template(c, 910, tpl, dry_run=True)
        assert res["payload"]["artifacts"] == tgt["artifacts"]
        assert res["payload"]["triggers"] == tgt["triggers"]
        assert res["preserve_applied"] == DEFAULT_PRESERVE_PATHS

    def test_preserve_none_keeps_template_values(self):
        c = _Client(_target())
        tpl = clean_definition_for_template(_defn())
        tpl["artifacts"] = [{"alias": "_ORIGEN"}]
        res = apply_template(c, 910, tpl, dry_run=True, preserve=[])
        assert res["payload"]["artifacts"] == [{"alias": "_ORIGEN"}]

    def test_custom_preserve_path(self):
        tgt = _target()
        tgt["releaseNameFormat"] = "Rel-$(rev:r)-DEST"
        c = _Client(tgt)
        tpl = clean_definition_for_template(_defn())
        tpl["releaseNameFormat"] = "Rel-$(rev:r)-ORIGEN"
        res = apply_template(c, 910, tpl, dry_run=True,
                             preserve=["releaseNameFormat"])
        assert res["payload"]["releaseNameFormat"] == "Rel-$(rev:r)-DEST"

    def test_backup_yaml_written_and_reread(self, tmp_path):
        c = _Client(_target())
        tpl = clean_definition_for_template(_defn())
        res = apply_template(c, 910, tpl, backup_dir=tmp_path)
        yml = res["backup"]["yaml"]
        assert yml.suffix == ".yaml" and yml.exists()
        reloaded = load_target_backup(yml)
        assert reloaded["id"] == 910
        assert reloaded["name"] == "CD-Destino"
        # el payload conserva artifacts del destino leído del yaml
        _, payload = c.put_calls[0]
        assert payload["artifacts"] == _target()["artifacts"]


# ═══════════════════════════════════════════════════════════════════════════
# Merge — upsert sin planchar el destino
# ═══════════════════════════════════════════════════════════════════════════

from scm.azdo.pipeline_cd_template import merge_definitions


def _tpl_env(name, **kw):
    e = {"name": name, "variables": {"TVar": {"value": "tpl"}},
         "deployPhases": [{"workflowTasks": [{"name": "t"}]}]}
    e.update(kw)
    return e


class TestMergeDefinitions:
    def _target_def(self):
        return {
            "id": 910, "revision": 7, "name": "CD-Dest",
            "variables": {"Keep": {"value": "dst"},
                          "Shared": {"value": "dst-val"}},
            "environments": [
                {"id": 11, "name": "QA",
                 "variables": {"QaVar": {"value": "dst"}}},
                {"id": 12, "name": "Production",
                 "variables": {"PVar": {"value": "dst"}}},
            ],
        }

    def test_adds_only_new_stages_by_default(self):
        tpl = {"environments": [_tpl_env("QA"), _tpl_env("NewStage")],
               "variables": {"NewVar": {"value": "n"},
                             "Shared": {"value": "tpl-val"}}}
        merged, rep = merge_definitions(tpl, self._target_def(),
                                        overwrite="none")
        names = [e["name"] for e in merged["environments"]]
        # QA del destino (conservado), NewStage agregado, Production intacto
        assert names == ["QA", "NewStage", "Production"]
        qa = merged["environments"][0]
        assert qa["variables"]["QaVar"]["value"] == "dst"   # vars del destino
        assert qa["id"] == 11                                # linkage destino
        # variables release: nuevas agregadas, existentes preservadas
        assert merged["variables"]["NewVar"]["value"] == "n"
        assert merged["variables"]["Shared"]["value"] == "dst-val"

    def test_overwrite_all_replaces_stages_but_keeps_vars(self):
        tpl = {"environments": [_tpl_env("QA", rank=9)], "variables": {}}
        merged, _ = merge_definitions(tpl, self._target_def(),
                                      overwrite="all")
        qa = merged["environments"][0]
        assert qa["rank"] == 9                     # contenido de la template
        assert qa["id"] == 11                      # id del destino
        assert qa["variables"]["QaVar"]["value"] == "dst"  # vars preservadas

    def test_update_vars_overlays_template_vars(self):
        tpl = {"environments": [_tpl_env("QA")],
               "variables": {"Shared": {"value": "tpl-val"}}}
        merged, _ = merge_definitions(tpl, self._target_def(),
                                      overwrite="all", update_vars=True)
        qa = merged["environments"][0]
        assert qa["variables"]["QaVar"]["value"] == "dst"   # extra del destino
        assert qa["variables"]["TVar"]["value"] == "tpl"    # nueva de template
        assert merged["variables"]["Shared"]["value"] == "tpl-val"

    def test_ask_fn_decides_per_stage_and_caches(self):
        tpl = {"environments": [_tpl_env("QA"), _tpl_env("Production")],
               "variables": {}}
        decisions = {}
        asked = []

        def ask(name):
            asked.append(name)
            return name == "QA"

        merged, _ = merge_definitions(tpl, self._target_def(),
                                      overwrite="ask", ask_fn=ask,
                                      decisions=decisions)
        qa, prod = merged["environments"][0], merged["environments"][1]
        assert qa["deployPhases"]                      # sobrescrito (template)
        assert prod.get("variables") == {"PVar": {"value": "dst"}}  # conservado
        # segunda pasada (dry-run → real) no vuelve a preguntar
        merge_definitions(tpl, self._target_def(), overwrite="ask",
                          ask_fn=ask, decisions=decisions)
        assert asked == ["QA", "Production"]

    def test_ask_without_ask_fn_conserves(self):
        tpl = {"environments": [_tpl_env("QA")], "variables": {}}
        merged, _ = merge_definitions(tpl, self._target_def(),
                                      overwrite="ask", ask_fn=None)
        assert "deployPhases" not in merged["environments"][0]

    def test_overwrite_csv_list(self):
        tpl = {"environments": [_tpl_env("QA"), _tpl_env("Production")],
               "variables": {}}
        merged, _ = merge_definitions(tpl, self._target_def(),
                                      overwrite="Production")
        assert "deployPhases" not in merged["environments"][0]   # QA conservado
        assert "deployPhases" in merged["environments"][1]       # Prod sobrescrito

    def test_strategy_merge_in_apply(self):
        tgt = self._target_def()
        c = _Client(tgt)
        tpl = {"environments": [_tpl_env("QA"), _tpl_env("Nuevo")],
               "variables": {}}
        res = apply_template(c, 910, tpl, dry_run=True,
                             strategy="merge", overwrite="none")
        names = [e["name"] for e in res["payload"]["environments"]]
        assert names == ["QA", "Nuevo", "Production"]
        assert any("stage conservado" in l for l in res["summary"])

    def test_strategy_replace_keeps_old_behavior(self):
        c = _Client(self._target_def())
        tpl = {"environments": [_tpl_env("Solo")], "variables": {}}
        res = apply_template(c, 910, tpl, dry_run=True,
                             strategy="replace", preserve=[])
        names = [e["name"] for e in res["payload"]["environments"]]
        assert names == ["Solo"]

    def test_ranks_renumbered_consecutive(self):
        """VS402874: ranks deben ser naturales consecutivos desde 1."""
        tgt = self._target_def()
        tgt["environments"][0]["rank"] = 5
        tgt["environments"][1]["rank"] = 17
        c = _Client(tgt)
        tpl = {"environments": [_tpl_env("QA", rank=3),
                                _tpl_env("Nuevo", rank=9)],
               "variables": {}}
        res = apply_template(c, 910, tpl, dry_run=True,
                             strategy="merge", overwrite="none")
        ranks = [e["rank"] for e in res["payload"]["environments"]]
        assert ranks == [1, 2, 3]

    def test_dry_run_writes_target_and_updater_yaml(self, tmp_path):
        c = _Client(self._target_def())
        tpl = {"environments": [_tpl_env("QA")], "variables": {}}
        res = apply_template(c, 910, tpl, dry_run=True, backup_dir=tmp_path,
                             overwrite="none")
        assert res["backup"]["yaml"].exists()
        assert res["backup"]["json"].exists()
        assert res["updater_yaml"].exists()
        data = yaml.safe_load(res["updater_yaml"].read_text())
        assert data["metadata"]["dryRun"] is True
        assert data["metadata"]["targetId"] == 910
        assert data["definition"]["id"] == 910
        assert c.put_calls == []   # dry-run no toca AzDO


# ═══════════════════════════════════════════════════════════════════════════
# Artifact alias remap — conditions de stages nuevos apuntan al alias destino
# ═══════════════════════════════════════════════════════════════════════════

from scm.azdo.pipeline_cd_template import (
    _artifact_alias_map, remap_artifact_aliases,
)


class TestArtifactAliasRemap:
    def test_map_by_definition_name(self):
        tpl = {"artifacts": [{"alias": "_ORIGEN_CI",
                              "definitionReference":
                              {"definition": {"name": "CI-Main"}}}]}
        tgt = {"artifacts": [{"alias": "_DESTINO_CI",
                              "definitionReference":
                              {"definition": {"name": "CI-Main"}}}]}
        assert _artifact_alias_map(tpl, tgt) == {"_ORIGEN_CI": "_DESTINO_CI"}

    def test_map_by_position_when_names_differ(self):
        tpl = {"artifacts": [{"alias": "_A"}, {"alias": "_B"}]}
        tgt = {"artifacts": [{"alias": "_X"}]}
        m = _artifact_alias_map(tpl, tgt)
        assert m == {"_A": "_X"}   # solo el 1ro mapea por posición

    def test_same_alias_no_mapping(self):
        tpl = {"artifacts": [{"alias": "_CI"}]}
        tgt = {"artifacts": [{"alias": "_CI"}]}
        assert _artifact_alias_map(tpl, tgt) == {}

    def test_remap_conditions_artifact_filter(self):
        payload = {"environments": [
            {"name": "Team-01-oms-dev",
             "conditions": [{"name": "_ORIGEN_CI",
                             "conditionType": "artifact",
                             "value": "{...}"}]},
            {"name": "Otro", "conditions": []},
        ]}
        touched = remap_artifact_aliases(payload,
                                         {"_ORIGEN_CI": "_DESTINO_CI"})
        cond = payload["environments"][0]["conditions"][0]
        assert cond["name"] == "_DESTINO_CI"
        assert touched == ["Team-01-oms-dev"]

    def test_remap_does_not_touch_env_name(self):
        payload = {"environments": [{"name": "_ORIGEN_CI",
                                     "conditions": []}]}
        remap_artifact_aliases(payload, {"_ORIGEN_CI": "_X"})
        assert payload["environments"][0]["name"] == "_ORIGEN_CI"

    def test_apply_remaps_stage_filters_when_artifacts_preserved(self):
        tgt = _target()   # artifacts: _MiBuild, _Repo
        c = _Client(tgt)
        tpl = clean_definition_for_template(_defn())
        tpl["artifacts"] = [{"alias": "_ORIGEN",
                             "definitionReference":
                             {"definition": {"name": "CI-Main"}}}]
        tpl["environments"].append({
            "name": "NewStage",
            "conditions": [{"name": "_ORIGEN",
                            "conditionType": "artifact"}],
            "deployPhases": []})
        res = apply_template(c, 910, tpl, dry_run=True, overwrite="none")
        new_env = [e for e in res["payload"]["environments"]
                   if e["name"] == "NewStage"][0]
        assert new_env["conditions"][0]["name"] == "_MiBuild"
        assert any("alias de artifact remapeados" in l
                   for l in res["summary"])
