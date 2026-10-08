# -*- coding: utf-8 -*-
"""Tests para azdo_release_manifest_drift — parsers puros, diff y análisis
de señales (sin llamadas a la API de AzDO)."""

import pytest

from scm.azdo.azdo_release_manifest_drift import (
    _APPLY_VERDICTS,
    analyze_manifest,
    apply_resource_key,
    diff_env_def_vs_release,
    diff_has_changes,
    extract_manifest_docs,
    extract_stage_tasks,
    find_stage_env,
    manifest_key,
    parse_apply_log,
    parse_manifest_objects,
    select_definitions,
)

TS = "2026-10-08T14:22:33.1234567Z "


def _log(lines):
    return "\n".join(TS + l for l in lines)


# ═══════════════════════════════════════════════════════════════════════════
# parse_apply_log
# ═══════════════════════════════════════════════════════════════════════════

class TestParseApplyLog:
    def test_verdicts_basic(self):
        log = _log([
            "deployment.apps/web configured",
            "service/web-svc unchanged",
            "configmap/cfg created",
        ])
        r = parse_apply_log(log)
        assert r["verdicts"] == {
            "deployment.apps/web": "configured",
            "service/web-svc": "unchanged",
            "configmap/cfg": "created",
        }
        assert not r["missing_annotation"]

    def test_missing_last_applied_annotation(self):
        log = _log([
            "Warning: resource deployments/web is missing the "
            "kubectl.kubernetes.io/last-applied-configuration annotation "
            "which is required by kubectl apply. kubectl apply should only "
            "be used on resources created declaratively",
            "deployment.apps/web configured",
        ])
        r = parse_apply_log(log)
        assert "deployments/web" in r["missing_annotation"]

    def test_errors_captured(self):
        log = _log([
            "Error from server (NotFound): error when creating "
            "\"manifest.yaml\": namespaces \"x\" not found",
        ])
        r = parse_apply_log(log)
        assert r["errors"]

    def test_empty_and_noise(self):
        assert parse_apply_log("")["verdicts"] == {}
        r = parse_apply_log(_log(["##[section]Finishing: kubectl apply",
                                  "random noise line"]))
        assert r["verdicts"] == {}


# ═══════════════════════════════════════════════════════════════════════════
# extract_manifest_docs / parse_manifest_objects
# ═══════════════════════════════════════════════════════════════════════════

_DEPLOY_YAML = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: prod-ns
spec:
  replicas: 2"""

_SVC_YAML = """apiVersion: v1
kind: Service
metadata:
  name: web-svc
  namespace: prod-ns"""


class TestManifestExtraction:
    def test_extract_docs_from_cat_log(self):
        log = _log([
            "##[section]Starting: Show manifest",
            "/usr/bin/cat /tmp/manifest.yaml",
            *_DEPLOY_YAML.split("\n"),
            "---",
            *_SVC_YAML.split("\n"),
            "##[section]Finishing: Show manifest",
        ])
        docs = extract_manifest_docs(log)
        assert len(docs) == 2

    def test_noise_ignored(self):
        log = _log(["not yaml at all", "just text {{{", _DEPLOY_YAML])
        docs = extract_manifest_docs(log)
        assert len(docs) == 1

    def test_parse_objects_keys_and_canonical(self):
        objs = parse_manifest_objects([_DEPLOY_YAML, _SVC_YAML])
        assert "deployment/prod-ns/web" in objs
        assert "service/prod-ns/web-svc" in objs
        assert objs["deployment/prod-ns/web"]["canonical"]
        assert objs["deployment/prod-ns/web"]["kind"] == "Deployment"

    def test_manifest_key_no_namespace(self):
        assert manifest_key("Namespace", "", "prod-ns") == "namespace//prod-ns"


# ═══════════════════════════════════════════════════════════════════════════
# analyze_manifest — señales de drift
# ═══════════════════════════════════════════════════════════════════════════

def _objects(*names):
    docs = []
    for kind, ns, name, extra in names:
        docs.append(f"apiVersion: v1\nkind: {kind}\nmetadata:\n"
                    f"  name: {name}\n  namespace: {ns}\n{extra}")
    return parse_manifest_objects(docs)


def _apply(verdicts=None, missing=None):
    return {"verdicts": verdicts or {},
            "missing_annotation": set(missing or []), "errors": []}


class TestAnalyzeManifest:
    def test_not_managed_by_apply_high(self):
        objs = _objects(("Deployment", "ns", "web", ""))
        apply = _apply({"deployment.apps/web": "configured"},
                       missing=["deployments/web"])
        f = analyze_manifest(objs, apply)
        hi = [x for x in f if x["rule"] == "NOT_MANAGED_BY_APPLY"]
        assert len(hi) == 1 and hi[0]["severity"] == "HIGH"

    def test_not_applied_medium(self):
        objs = _objects(("Deployment", "ns", "web", ""),
                        ("Service", "ns", "svc", ""))
        apply = _apply({"deployment.apps/web": "unchanged"})
        f = analyze_manifest(objs, apply)
        med = [x for x in f if x["rule"] == "NOT_APPLIED"]
        assert len(med) == 1 and med[0]["severity"] == "MEDIUM"
        assert "svc" in med[0]["object"]

    def test_applied_not_in_manifest_low(self):
        objs = _objects(("Deployment", "ns", "web", ""))
        apply = _apply({"deployment.apps/web": "configured",
                        "configmap/extra": "configured"})
        f = analyze_manifest(objs, apply)
        low = [x for x in f if x["rule"] == "APPLIED_NOT_IN_MANIFEST"]
        assert len(low) == 1 and low[0]["severity"] == "LOW"

    def test_external_modification_high(self):
        objs = _objects(("Deployment", "ns", "web",
                         "spec:\n  replicas: 2"))
        prev = _objects(("Deployment", "ns", "web",
                         "spec:\n  replicas: 2"))
        apply = _apply({"deployment.apps/web": "configured"})
        f = analyze_manifest(objs, apply, prev_objects=prev)
        hi = [x for x in f if x["rule"] == "EXTERNAL_MODIFICATION"]
        assert len(hi) == 1 and hi[0]["severity"] == "HIGH"

    def test_expected_config_when_manifest_changed(self):
        objs = _objects(("Deployment", "ns", "web",
                         "spec:\n  replicas: 3"))
        prev = _objects(("Deployment", "ns", "web",
                         "spec:\n  replicas: 2"))
        apply = _apply({"deployment.apps/web": "configured"})
        f = analyze_manifest(objs, apply, prev_objects=prev)
        info = [x for x in f if x["rule"] == "EXPECTED_CONFIG"]
        assert len(info) == 1 and info[0]["severity"] == "INFO"
        assert not any(x["rule"] == "EXTERNAL_MODIFICATION" for x in f)

    def test_configured_without_prev_is_info(self):
        objs = _objects(("Deployment", "ns", "web", ""))
        apply = _apply({"deployment.apps/web": "configured"})
        f = analyze_manifest(objs, apply)
        assert any(x["rule"] == "CONFIGURED" and x["severity"] == "INFO"
                   for x in f)

    def test_created_info(self):
        objs = _objects(("Deployment", "ns", "web", ""))
        apply = _apply({"deployment.apps/web": "created"})
        f = analyze_manifest(objs, apply)
        assert any(x["rule"] == "CREATED" for x in f)

    def test_unchanged_no_findings_for_object(self):
        objs = _objects(("Deployment", "ns", "web", ""))
        apply = _apply({"deployment.apps/web": "unchanged"})
        f = analyze_manifest(objs, apply)
        assert not any(x["object"] for x in f)


# ═══════════════════════════════════════════════════════════════════════════
# diff_env_def_vs_release
# ═══════════════════════════════════════════════════════════════════════════

def _task(name, tid, version, inputs=None):
    return {"name": name, "taskId": tid, "version": version,
            "inputs": inputs or {}}


class TestDiffEnvDefVsRelease:
    def _def_env(self):
        return {
            "name": "Production",
            "deployPhases": [{"workflowTasks": [
                _task("show manifest", "t1", "1.*", {"filePath": "m.yaml"}),
                _task("kubectl apply", "t2", "3.*",
                      {"arguments": "apply -f m.yaml"}),
                _task("new task", "t3", "1.*"),
            ]}],
            "variables": {"A": {}, "B": {}},
        }

    def _rel_env_snapshot(self):
        return {
            "name": "Production",
            "releaseDefinitionEnvironment": {
                "deployPhases": [{"workflowTasks": [
                    _task("show manifest", "t1", "1.*", {"filePath": "m.yaml"}),
                    _task("kubectl apply", "t2", "2.*",
                          {"arguments": "apply -f OLD.yaml"}),
                    _task("old task", "t4", "1.*"),
                ]}],
                "variables": {"A": {}, "C": {}},
            },
        }

    def test_full_diff(self):
        d = diff_env_def_vs_release(self._def_env(), self._rel_env_snapshot())
        assert d["tasks_added"] == ["new task"]
        assert d["tasks_removed"] == ["old task"]
        assert any("kubectl apply" in v for v in d["tasks_version_changed"])
        inp = [i for i in d["task_inputs_changed"] if i["task"] == "kubectl apply"]
        assert inp and inp[0]["input"] == "arguments"
        assert d["vars_added"] == ["B"]
        assert d["vars_removed"] == ["C"]
        assert diff_has_changes(d)

    def test_snapshot_via_deployphases_snapshot(self):
        rel_env = {"name": "Production",
                   "deployPhasesSnapshot": [{"workflowTasks": [
                       _task("show manifest", "t1", "1.*",
                             {"filePath": "m.yaml"}),
                       _task("kubectl apply", "t2", "3.*",
                             {"arguments": "apply -f m.yaml"}),
                       _task("new task", "t3", "1.*"),
                   ]}],
                   "variables": {"A": {}, "B": {}}}
        d = diff_env_def_vs_release(self._def_env(), rel_env)
        assert not d["tasks_added"] and not d["tasks_removed"]
        assert not diff_has_changes(d)

    def test_no_changes(self):
        env = self._def_env()
        rel = {"name": "Production",
               "releaseDefinitionEnvironment": env}
        d = diff_env_def_vs_release(env, rel)
        # el snapshot comparte el objeto → mismo contenido
        assert not d["tasks_added"] and not d["tasks_removed"]
        assert not d["tasks_version_changed"]


# ═══════════════════════════════════════════════════════════════════════════
# Selección / stage / tasks
# ═══════════════════════════════════════════════════════════════════════════

class TestSelectDefinitions:
    DEFS = [{"id": 1, "name": "CD-WMS-Prod"},
            {"id": 2, "name": "CD-OMS-Prod"},
            {"id": 3, "name": "CI-Build"}]

    def test_all(self):
        assert len(select_definitions(self.DEFS, "all")) == 3

    def test_single_id(self):
        sel = select_definitions(self.DEFS, "2")
        assert [d["id"] for d in sel] == [2]

    def test_csv_ids(self):
        sel = select_definitions(self.DEFS, "1,3")
        assert {d["id"] for d in sel} == {1, 3}

    def test_name_substring(self):
        sel = select_definitions(self.DEFS, "prod")
        assert {d["id"] for d in sel} == {1, 2}


class TestFindStageEnv:
    DEF = {"environments": [{"id": 11, "name": "Develop"},
                            {"id": 12, "name": "QA"},
                            {"id": 13, "name": "Production"}]}

    def test_exact_match_case_insensitive(self):
        assert find_stage_env(self.DEF, "production")["id"] == 13

    def test_prod_token(self):
        d = {"environments": [{"id": 9, "name": "Deploy PROD"}]}
        assert find_stage_env(d, "production")["id"] == 9

    def test_produccion_suffix_duccion(self):
        d = {"environments": [{"id": 21, "name": "Develop"},
                              {"id": 22, "name": "Producción"}]}
        assert find_stage_env(d, "production")["id"] == 22

    def test_stage_produccion_matches_production(self):
        d = {"environments": [{"id": 23, "name": "Production"}]}
        assert find_stage_env(d, "producción")["id"] == 23

    def test_not_found(self):
        assert find_stage_env({"environments": []}, "production") is None


class TestAzdoClientOrgNormalization:
    """El launcher pasa --org como URL completa (azdo.organization_url);
    AzdoClient debe usar solo el nombre de la organización."""

    def test_client_with_org_url(self):
        from scm.azdo.scm_inspection_remediator import AzdoClient
        c = AzdoClient("https://dev.azure.com/MyOrg", "Proj", "pat")
        assert c.base == ("https://vsrm.dev.azure.com/MyOrg/Proj"
                          "/_apis/release")

    def test_client_with_org_name(self):
        from scm.azdo.scm_inspection_remediator import AzdoClient
        c = AzdoClient("MyOrg", "Proj", "pat")
        assert "MyOrg/Proj" in c.base

    def test_get_azdo_params_normalizes_url(self, monkeypatch):
        import argparse
        import scm.azdo.scm_inspection_remediator as rem
        monkeypatch.setattr(rem, "load_config", lambda: {})
        args = argparse.Namespace(
            org="https://dev.azure.com/MyOrg/", project="Proj", pat="x")
        org, project, pat = rem.get_azdo_params(args)
        assert org == "MyOrg" and project == "Proj"


class TestExtractStageTasks:
    def test_last_attempt_and_skip(self):
        env = {"deploySteps": [
            {"attempt": 1, "releaseDeployPhases": [
                {"id": 101, "deploymentJobs": [
                    {"tasks": [
                        {"id": "a", "name": "old", "status": "succeeded"},
                    ]}]}]},
            {"attempt": 2, "releaseDeployPhases": [
                {"id": 102, "deploymentJobs": [
                    {"tasks": [
                        {"id": "b", "name": "show manifest",
                         "status": "succeeded", "logUrl": "u1"},
                        {"id": "c", "name": "skipped-task",
                         "status": "skipped"},
                        {"id": "d", "name": "kubectl apply",
                         "status": "failed", "logUrl": "u2"},
                    ]}]}]},
        ]}
        tasks = extract_stage_tasks(env)
        names = {t["name"] for t in tasks}
        assert names == {"show manifest", "kubectl apply"}
        assert all(t["phase_id"] == 102 for t in tasks)

    def test_empty_env(self):
        assert extract_stage_tasks({}) == []


class TestApplyResourceKey:
    def test_grouped_kind(self):
        assert apply_resource_key("deployment.apps/web") == "deployment//web"

    def test_core_kind(self):
        assert apply_resource_key("service/x") == "service//x"
