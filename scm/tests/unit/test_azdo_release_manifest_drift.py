# -*- coding: utf-8 -*-
"""Tests para azdo_release_manifest_drift — parsers puros, diff y análisis
de señales (sin llamadas a la API de AzDO)."""

import pytest

from scm.azdo.azdo_release_manifest_drift import (
    _APPLY_VERDICTS,
    analyze_manifest,
    apply_resource_key,
    applyish_task_names,
    build_html_report,
    build_object_rows,
    diff_env_def_vs_release,
    diff_has_changes,
    extract_manifest_docs,
    extract_stage_tasks,
    find_effective_deployments,
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

    def test_old_kubectl_quoted_format(self):
        """kubectl < 1.18 imprime 'kind "name" verdict' (con comillas)."""
        log = _log([
            'deployment.apps "web" configured',
            'service "web-svc" unchanged',
            'configmap "cfg" created',
        ])
        r = parse_apply_log(log)
        assert r["verdicts"] == {
            "deployment.apps/web": "configured",
            "service/web-svc": "unchanged",
            "configmap/cfg": "created",
        }

    def test_replaced_and_dry_run_verdicts(self):
        log = _log([
            "deployment.apps/web replaced",
            "service/svc configured (server dry run)",
            "configmap/cfg configured (dry run)",
        ])
        r = parse_apply_log(log)
        assert r["verdicts"]["deployment.apps/web"] == "replaced"
        assert r["verdicts"]["service/svc"] == "configured"
        assert r["verdicts"]["configmap/cfg"] == "configured"

    def test_old_generic_apply_warning(self):
        log = _log([
            "Warning: kubectl apply should be used on resource created by "
            "either kubectl create --save-config or kubectl apply",
        ])
        r = parse_apply_log(log)
        assert r["old_warn"] is True


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


class TestAnalyzeManifestDiagnostics:
    """Nuevas señales de diagnóstico de logs y placeholders."""

    _OBJS = {"deployment/ns/web": {"kind": "Deployment", "namespace": "ns",
                                   "name": "web", "canonical": "c"}}

    def test_unrendered_placeholder_is_info_not_medium(self):
        objs = dict(self._OBJS)
        objs["horizontalpodautoscaler/ns/hpa-#{ns}#-#{n}#"] = {
            "kind": "HorizontalPodAutoscaler", "namespace": "ns",
            "name": "hpa-#{ns}#-#{n}#", "canonical": "c"}
        findings = analyze_manifest(objs, {"verdicts": {}})
        rules = {f["rule"]: f["severity"] for f in findings}
        assert rules["UNRENDERED_NAME"] == "INFO"
        # el objeto con placeholder NO genera NOT_APPLIED
        assert not any(f["rule"] == "NOT_APPLIED" and "#{" in f["object"]
                       for f in findings)

    def test_apply_no_verdicts_medium(self):
        apply = {"verdicts": {}, "log_names": ["kubectl apply"],
                 "empty_logs": []}
        findings = analyze_manifest(self._OBJS, apply)
        assert any(f["rule"] == "APPLY_NO_VERDICTS"
                   and f["severity"] == "MEDIUM" for f in findings)

    def test_apply_no_verdicts_skipped_when_all_empty(self):
        apply = {"verdicts": {}, "log_names": ["kubectl apply"],
                 "empty_logs": ["kubectl apply"]}
        findings = analyze_manifest(self._OBJS, apply)
        assert not any(f["rule"] == "APPLY_NO_VERDICTS" for f in findings)
        assert any(f["rule"] == "EMPTY_LOG" for f in findings)

    def test_old_apply_warning_low(self):
        findings = analyze_manifest(self._OBJS,
                                    {"verdicts": {}, "old_warn": True})
        assert any(f["rule"] == "OLD_APPLY_WARNING"
                   and f["severity"] == "LOW" for f in findings)


class TestDiffHasChangesEmpty:
    def test_empty_dict_no_crash(self):
        assert diff_has_changes({}) is False


class TestInputsEquivalence:
    """Inputs ausentes (None) equivalen a defaults falsy explícitos."""

    def _env(self, inputs):
        return {"deployPhases": [{"workflowTasks": [
            {"taskId": "T1", "name": "t", "version": "1.*",
             "inputs": inputs}]}]}

    def test_none_vs_false_is_no_diff(self):
        cur = self._env({"flag": "false"})
        snap = self._env({})  # input ausente en el snapshot
        d = diff_env_def_vs_release(cur, snap)
        assert not d["task_inputs_changed"]

    def test_none_vs_true_is_diff(self):
        cur = self._env({"flag": "true"})
        snap = self._env({})
        d = diff_env_def_vs_release(cur, snap)
        assert d["task_inputs_changed"]

    def test_none_vs_number_is_diff(self):
        cur = self._env({"concurrentUploads": "10"})
        snap = self._env({})
        d = diff_env_def_vs_release(cur, snap)
        assert d["task_inputs_changed"]


class TestApplyishTaskNames:
    def test_kubernetes_task_command_apply(self):
        wfs = [{"name": "Deploy manifests",
                "inputs": {"command": "apply",
                           "manifests": "$(k8s)/*.yaml"}},
               {"name": "Lint", "inputs": {"command": "get"}}]
        assert applyish_task_names(wfs) == {"Deploy manifests"}

    def test_inline_script_with_kubectl_apply(self):
        wfs = [{"name": "Deploy",
                "inputs": {"inlineScript": "kubectl apply -f m.yaml"}},
               {"name": "Show", "inputs": {"inlineScript": "cat m.yaml"}}]
        assert applyish_task_names(wfs) == {"Deploy"}

    def test_create_and_replace_commands(self):
        wfs = [{"name": "t1", "inputs": {"command": "create"}},
               {"name": "t2", "inputs": {"command": "replace"}},
               {"name": "t3", "inputs": {"command": "delete"}}]
        assert applyish_task_names(wfs) == {"t1", "t2"}


class TestEffectiveDeploymentsDedup:
    """La Deployments API devuelve una entrada por attempt — dedup por
    release.id para que 'prev release' sea un release distinto."""

    class _Client:
        base = "https://vsrm.dev.azure.com/o/p"

        def get(self, url, params=None):
            assert url.endswith("/deployments")
            return {"value": [
                {"release": {"id": 10, "name": "R-3"},
                 "deploymentStatus": "succeeded"},   # attempt 2
                {"release": {"id": 10, "name": "R-3"},
                 "deploymentStatus": "failed"},      # attempt 1
                {"release": {"id": 9, "name": "R-2"},
                 "deploymentStatus": "succeeded"},
                {"release": {"id": 8, "name": "R-1"},
                 "deploymentStatus": "notDeployed"},
            ]}

    def test_dedup_by_release_id(self):
        eff = find_effective_deployments(self._Client(), 1, 2, limit=2)
        assert [d["release"]["id"] for d in eff] == [10, 9]

    def test_respects_limit(self):
        eff = find_effective_deployments(self._Client(), 1, 2, limit=1)
        assert len(eff) == 1


def _result(**over):
    """Resultado mínimo de analyze_definition para tests de reporte."""
    r = {
        "definition_id": 1, "definition_name": "pipe-x",
        "stage": "production",
        "release_id": 99, "release_name": "Release-9",
        "release_created": "2026-01-01T00:00", "deployment_status": "succeeded",
        "task_logs": ["show manifest", "kubectl apply"],
        "manifest_objects": 0, "objects": {}, "apply_verdicts": {},
        "apply_counts": {v: 0 for v in _APPLY_VERDICTS},
        "def_release_diff": None, "findings": [], "error": "",
        "severity": "NONE",
    }
    r.update(over)
    return r


class TestBuildObjectRows:
    def test_manifest_object_with_verdict_and_finding(self):
        objects = {"deployment/ns/web": {"kind": "Deployment",
                                         "namespace": "ns", "name": "web",
                                         "canonical": "c"}}
        r = _result(objects=objects,
                    apply_verdicts={"deployment.apps/web": "configured"},
                    findings=analyze_manifest(
                        objects, {"verdicts": {"deployment.apps/web":
                                               "configured"}}))
        rows, other = build_object_rows(r)
        assert len(rows) == 1
        assert rows[0]["in_manifest"] == "✓"
        assert rows[0]["verdict"] == "configured"
        assert "CONFIGURED" in rows[0]["rules"]
        assert other == []

    def test_apply_only_resource_row(self):
        r = _result(apply_verdicts={"secret/x": "created"},
                    findings=analyze_manifest(
                        {}, {"verdicts": {"secret/x": "created"}}))
        rows, _ = build_object_rows(r)
        assert len(rows) == 1
        assert rows[0]["in_manifest"] == "✗"
        assert rows[0]["severity"] == "LOW"  # APPLIED_NOT_IN_MANIFEST

    def test_non_object_findings_apart(self):
        r = _result(findings=[{"severity": "MEDIUM", "rule": "APPLY_ERROR",
                               "object": "", "detail": "boom"}])
        rows, other = build_object_rows(r)
        assert rows == [] and other[0]["rule"] == "APPLY_ERROR"


class TestBuildHtmlReport:
    def test_html_contains_pipeline_and_table(self):
        objects = {"deployment/ns/web": {"kind": "Deployment",
                                         "namespace": "ns", "name": "web",
                                         "canonical": "c"}}
        r = _result(manifest_objects=1, objects=objects,
                    apply_verdicts={"deployment.apps/web": "configured"},
                    findings=analyze_manifest(
                        objects, {"verdicts": {"deployment.apps/web":
                                               "configured"}}))
        r["severity"] = "INFO"
        out = build_html_report([r])
        assert "pipe-x" in out
        assert "Deployment/web" in out
        assert "configured" in out
        assert "CONFIGURED" in out
        assert "Release-9" in out

    def test_html_skipped_collapsed(self):
        skip = _result(definition_name="pipe-skip",
                       error="stage 'production' no existe en la definición")
        out = build_html_report([skip])
        assert "Omitidos (1)" in out
        assert "pipe-skip" in out

    def test_html_escapes_content(self):
        r = _result(definition_name="<script>alert(1)</script>",
                    findings=[{"severity": "MEDIUM", "rule": "X",
                               "object": "", "detail": "<img onerror=x>"}])
        out = build_html_report([r])
        assert "<script>alert" not in out
        assert "&lt;script&gt;" in out
