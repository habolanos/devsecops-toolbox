"""
Tests para Production Pre-Install Validator
(azdo_prod_preinstall_validator.py)

Cubre: filtro de CD con artifact Git master, exclusion de releases con
Production instalado, PR desde la rama del build (refs/pull/N/merge),
parseo de violaciones del Validator (reglas opcion 44 + genericos),
score del CD (formula opcion 3), commit de properties, rollback desde
RELEASE_ID y render del listado.
"""

import io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "azdo"))

import azdo_prod_preinstall_validator as pv  # noqa: E402


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════
def _git_artifact(repo="oms-com-order", commit="aacda92cbd18",
                  branch="master", repo_id="r-oms"):
    return {"type": "Git", "alias": f"_{repo}",
            "definitionReference": {
                "repository": {"id": repo_id, "name": repo},
                "version": {"id": commit},
                "branch": {"id": branch}}}


def _build_artifact(build_id="495667", number="20240926.5",
                    branch="refs/pull/176004/merge"):
    return {"type": "Build", "isPrimary": True,
            "definitionReference": {
                "version": {"id": build_id, "name": number},
                "branch": {"id": branch},
                "repository": {"id": "ci-repo",
                               "name": "pipelines-projects"}}}


def _rel(rid=60995, name="Release-40", prod_status="notStarted",
         prod_steps=None, validator_steps=None, git_art=None,
         build_art=None, variables=None, envs=None):
    """Release con environments Production y Validator configurables."""
    environments = envs if envs is not None else [
        {"name": "Production", "status": prod_status,
         "deploySteps": prod_steps or []},
        {"name": "Validator", "status": "succeeded"
         if validator_steps else "notStarted",
         "deploySteps": validator_steps or []},
    ]
    return {
        "id": rid, "name": name, "status": "active",
        "createdOn": "2026-10-03T00:25:00Z",
        "environments": environments,
        "artifacts": [build_art or _build_artifact(),
                      git_art or _git_artifact()],
        "variables": variables or {},
    }


def _validator_step_with_log(log_text):
    """deployStep del Validator con una tarea cuyo logUrl se mockea."""
    return {"id": 1, "attempt": 1, "deploymentStatus": "succeeded",
            "releaseDeployPhases": [{
                "id": 107, "deploymentJobs": [{
                    "job": {"id": 1, "name": "Agent job"},
                    "tasks": [{"id": 12, "name": "Validar images",
                               "status": "succeeded",
                               "logUrl": "fake://log/12"}],
                }],
            }]}


# ═════════════════════════════════════════════════════════════════════════════
# Filtro de CD: artifact Git branch master
# ═════════════════════════════════════════════════════════════════════════════
def test_cd_master_git_artifact_encuentra():
    detail = {"artifacts": [_build_artifact(), _git_artifact()]}
    gi = pv.cd_master_git_artifact(detail, "master")
    assert gi and gi["repo_name"] == "oms-com-order"
    assert gi["branch"] == "master"


def test_cd_master_git_artifact_otra_rama():
    detail = {"artifacts": [_git_artifact(branch="develop")]}
    assert pv.cd_master_git_artifact(detail, "master") is None


def test_cd_master_git_artifact_sin_git():
    detail = {"artifacts": [_build_artifact()]}
    assert pv.cd_master_git_artifact(detail, "master") is None


# ═════════════════════════════════════════════════════════════════════════════
# Production instalado → excluir
# ═════════════════════════════════════════════════════════════════════════════
def test_prod_installed_succeeded():
    env = {"deploySteps": [{"deploymentStatus": "succeeded"}]}
    assert pv.prod_installed(env) is True


def test_prod_installed_partial():
    env = {"deploySteps": [{"deploymentStatus": "failed"},
                           {"deploymentStatus": "partiallySucceeded"}]}
    assert pv.prod_installed(env) is True


def test_prod_not_installed():
    assert pv.prod_installed(None) is False
    env = {"deploySteps": [{"deploymentStatus": "failed"}]}
    assert pv.prod_installed(env) is False
    assert pv.prod_installed({"deploySteps": []}) is False


def test_stage_env_por_nombre_normalizado():
    rel = _rel()
    assert pv.stage_env(rel, "production") is not None
    assert pv.stage_env(rel, "VALIDATOR") is not None
    assert pv.stage_env(rel, "Develop") is None


def test_stage_snapshot():
    rel = _rel()
    snap = pv.stage_snapshot(rel)
    assert ("Production", "notStarted", "0") in snap
    assert ("Validator", "notStarted", "0") in snap


# ═════════════════════════════════════════════════════════════════════════════
# PR desde la rama del build
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("ref,expected", [
    ("refs/pull/176004/merge", 176004),
    ("refs/pull/42/head", 42),
    ("refs/heads/master", None),
    ("", None),
    (None, None),
])
def test_pr_id_from_build_branch(ref, expected):
    assert pv.pr_id_from_build_branch(ref) == expected


# ═════════════════════════════════════════════════════════════════════════════
# parse_log (reglas opcion 44) + issues genericos
# ═════════════════════════════════════════════════════════════════════════════
RULE_LOG = (
    "2026-10-03T00:29:05Z##[warning]  [MEDIUM] RULE_5_OVERRIDE\n"
    "2026-10-03T00:29:05Z##[warning]   Environment: 'Production'\n"
    "2026-10-03T00:29:05Z##[warning]   Variable: tuSecret\n"
    "2026-10-03T00:29:05Z##[warning]   Reason: allowOverride activo\n"
    "linea normal\n"
    "2026-10-03T00:29:07Z##[error]  [HIGH] RULE_1_SECRET\n"
    "2026-10-03T00:29:07Z##[error]   Variable: passAzure\n"
)


def test_parse_log_reglas_44():
    v = pv.parse_log(RULE_LOG, "SCM Inspection")
    assert len(v) == 2
    assert v[0]["severity"] == "MEDIUM"      # orden: WARNING=2 > ERROR? no
    rules = {x["rule"]: x for x in v}
    assert rules["RULE_5_OVERRIDE"]["variable"] == "tuSecret"
    assert rules["RULE_5_OVERRIDE"]["environment"] == "Production"
    assert rules["RULE_1_SECRET"]["severity"] == "HIGH"


def test_parse_generic_issues():
    text = ("2026-10-13T05:14:13Z##[warning]   variable not found: "
            "artifact.gcpBalancer\n"
            "2026-10-13T05:14:14Z##[error] The process kubectl failed\n"
            "2026-10-13T05:14:14Z##[warning]  [LOW] RULE_X\n")
    issues = pv.parse_generic_issues(text, "Replace tokens")
    # la linea con formato de regla se excluye de genericos
    assert len(issues) == 2
    assert issues[0]["rule"] == "TASK_ISSUE"
    assert "variable not found" in issues[0]["detail"]
    assert issues[1]["severity"] == "ERROR"


def test_validator_task_logs(monkeypatch):
    step = _validator_step_with_log(RULE_LOG)
    monkeypatch.setattr(pv, "api_get_text",
                        lambda url, headers, debug=False: RULE_LOG)
    rel = _rel(validator_steps=[step])
    venv = pv.stage_env(rel, "Validator")
    violations, errors = pv.validator_task_logs(rel, venv, {}, False)
    assert not errors
    rules = {v["rule"] for v in violations}
    assert "RULE_5_OVERRIDE" in rules
    assert "RULE_1_SECRET" in rules


def test_validator_task_logs_sin_ejecucion():
    rel = _rel(validator_steps=[])
    venv = pv.stage_env(rel, "Validator")
    v, e = pv.validator_task_logs(rel, venv, {}, False)
    assert v == [] and e == []


def test_validator_task_logs_stage_ausente():
    v, e = pv.validator_task_logs(_rel(), None, {}, False)
    assert v == [] and e == []


def test_violations_summary():
    v = [{"severity": "HIGH"}, {"severity": "HIGH"},
         {"severity": "MEDIUM"}]
    s = pv.violations_summary(v)
    assert s == {"HIGH": 2, "MEDIUM": 1}


# ═════════════════════════════════════════════════════════════════════════════
# Score CD (formula opcion 3)
# ═══════════════════════════════════════════════════════════════════════════════
def test_compute_score_nunca_desplegado():
    s = pv.compute_score(None, None, None)
    assert s["total"] == 0 and s["ever"] is False
    assert pv.get_rating(0, False) == ("🔴", "Nunca")


def test_compute_score_recente_estable():
    from datetime import datetime, timezone
    now = datetime(2026, 10, 22, tzinfo=timezone.utc)
    recent = datetime(2026, 10, 20, tzinfo=timezone.utc)  # 2 dias
    class FakeDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return now
    monkey_dt = FakeDT
    orig = pv.datetime
    pv.datetime = monkey_dt
    try:
        s = pv.compute_score(recent, 1, None)
        # recencia ~70*(1-2/365)≈69.6, estabilidad 20 → ~89-90
        assert 85 <= s["total"] <= 95
        assert s["ever"] is True
        assert s["stability"] == 20
    finally:
        pv.datetime = orig


def test_compute_score_intentos_restan():
    from datetime import datetime, timezone
    recent = datetime(2026, 10, 20, tzinfo=timezone.utc)
    s1 = pv.compute_score(recent, 1, None)
    s3 = pv.compute_score(recent, 4, None)
    assert s3["stability"] < s1["stability"]


def test_get_rating_bands():
    assert pv.get_rating(95, True)[1] == "Excelente"
    assert pv.get_rating(75, True)[1] == "Bueno"
    assert pv.get_rating(50, True)[1] == "Regular"
    assert pv.get_rating(20, True)[1] == "Bajo"
    assert pv.get_rating(90, False)[1] == "Nunca"


# ═════════════════════════════════════════════════════════════════════════════
# Variables + rollback
# ═══════════════════════════════════════════════════════════════════════════════
def test_release_vars():
    rel = {"variables": {"RELEASE_ID": {"value": "60993"},
                         "commitPropertiesRollback": {"value": "107cd5c8"},
                         "plain": "x"}}
    v = pv.release_vars(rel)
    assert v["RELEASE_ID"] == "60993"
    assert v["COMMITPROPERTIESROLLBACK"] == "107cd5c8"
    assert v["PLAIN"] == "x"


def test_rollback_info(monkeypatch):
    rb_rel = {"id": 60993, "name": "Release-39",
              "artifacts": [_build_artifact(build_id="4990",
                                           number="20240926.4"),
                            _git_artifact(commit="f228b069c0")],
              "variables": {"commitPropertiesRollback":
                            {"value": "107cd5c84656"}}}
    monkeypatch.setattr(pv, "get_release_detail",
                        lambda *a, **k: rb_rel)
    rel = _rel(rid=60995)
    vars_ = {"RELEASE_ID": "60993"}
    rb = pv.rollback_info("o", "p", rel, vars_, {}, False)
    assert rb["valid"] is True
    assert rb["release_id"] == "60993"
    assert rb["build_id"] == "4990"
    assert rb["build_number"] == "20240926.4"
    assert rb["git_commit"] == "f228b069c0"
    assert rb["props_commit"] == "107cd5c84656"


def test_rollback_info_apunta_a_si_mismo():
    rel = _rel(rid=60995)
    rb = pv.rollback_info("o", "p", rel, {"RELEASE_ID": "60995"}, {}, False)
    assert rb["valid"] is False
    rb2 = pv.rollback_info("o", "p", rel, {}, {}, False)
    assert rb2["valid"] is False


# ═════════════════════════════════════════════════════════════════════════════
# process_cd: exclusion de instalados + extraccion de fila
# ═══════════════════════════════════════════════════════════════════════════════
def _mock_apis(monkeypatch, releases, pr=None):
    monkeypatch.setattr(pv, "get_releases",
                        lambda *a, **k: releases)
    monkeypatch.setattr(pv, "get_pull_request",
                        lambda *a, **k: pr)
    monkeypatch.setattr(pv, "find_pr_for_commit",
                        lambda *a, **k: pr)
    monkeypatch.setattr(pv, "api_get_text", lambda *a, **k: None)


def _args():
    return pv.get_args.__wrapped__() if hasattr(pv.get_args, "__wrapped__") \
        else None


class _A:
    master_branch = "master"
    prod_stage = "Production"
    validator_stage = "Validator"
    top_releases = 10
    debug = False


def test_process_cd_excluye_instalados(monkeypatch):
    installed = _rel(rid=60994, name="Release-38",
                     prod_status="succeeded",
                     prod_steps=[{"deploymentStatus": "succeeded"}])
    pending = _rel(rid=60995, name="Release-40", prod_status="notStarted")
    _mock_apis(monkeypatch, [installed, pending])
    cd = {"id": 1403, "name": "oms-com-order-CD"}
    detail = {"artifacts": [_build_artifact(), _git_artifact()],
              "modifiedOn": "2026-09-01T00:00:00Z"}
    res = pv.process_cd("o", "p", cd, detail, _A(), {}, {})
    assert len(res["rows"]) == 1
    row = res["rows"][0]
    assert row["release_id"] == 60995
    assert row["build_id"] == "495667"
    assert row["git_commit"] == "aacda92cbd18"
    assert row["pr_id"] == 176004  # desde refs/pull/176004/merge
    assert row["prod_status"] == "notStarted"


def test_process_cd_validator_logs(monkeypatch):
    step = _validator_step_with_log(RULE_LOG)
    pending = _rel(rid=60995, prod_status="notStarted",
                   validator_steps=[step],
                   variables={"RELEASE_ID": {"value": "60993"},
                              "commitPropertiesRollback":
                              {"value": "107cd5c84656"}})
    monkeypatch.setattr(pv, "get_releases", lambda *a, **k: [pending])
    monkeypatch.setattr(pv, "get_pull_request", lambda *a, **k: None)
    monkeypatch.setattr(pv, "find_pr_for_commit", lambda *a, **k: None)
    monkeypatch.setattr(pv, "api_get_text",
                        lambda *a, **k: RULE_LOG)
    rb_rel = {"id": 60993, "artifacts": [_build_artifact("4990"),
                                         _git_artifact(commit="f228b069")],
              "variables": {"commitPropertiesRollback":
                            {"value": "107cd5c846"}}}
    monkeypatch.setattr(pv, "get_release_detail",
                        lambda *a, **k: rb_rel)
    cd = {"id": 1403, "name": "oms-CD"}
    detail = {"artifacts": [_build_artifact(), _git_artifact()],
              "modifiedOn": "2026-09-01T00:00:00Z"}
    res = pv.process_cd("o", "p", cd, detail, _A(), {}, {})
    row = res["rows"][0]
    assert row["validator_ran"] is True
    assert {v["rule"] for v in row["violations"]} == \
        {"RULE_5_OVERRIDE", "RULE_1_SECRET"}
    assert row["props_commit"] == "107cd5c84656"
    assert row["rb_valid"] is True
    assert row["rb_build_id"] == "4990"
    assert row["rb_git_commit"] == "f228b069"


def test_process_cd_sin_releases(monkeypatch):
    _mock_apis(monkeypatch, [])
    cd = {"id": 1, "name": "x"}
    res = pv.process_cd("o", "p", cd, {"artifacts": [_git_artifact()]},
                        _A(), {}, {})
    assert res["rows"] == [] and res["error"] == "sin releases"


# ═════════════════════════════════════════════════════════════════════════════
# Render
# ═════════════════════════════════════════════════════════════════════════════
def _row(**kw):
    base = {
        "cd_id": 1403, "cd_name": "oms-com-order-CD",
        "release_id": 60995, "release_name": "Release-40",
        "created_on": "2026-10-03T00:25:00Z",
        "repo": "oms-com-order", "repo_id": "r-oms",
        "pr_id": 176004, "pr_title": "Consulta Remisiones",
        "pr_target": "refs/heads/master",
        "build_id": "495667", "build_number": "20240926.5",
        "git_commit": "aacda92cbd18", "score": 85, "rating": ("🟢", "X"),
        "props_commit": "107cd5c84656",
        "rb_release_id": "60993", "rb_build_id": "4990",
        "rb_build_number": "20240926.4", "rb_git_commit": "f228b069",
        "rb_props_commit": "107cd5c8465", "rb_valid": True,
        "validator_ran": True, "violations": [], "log_errors": [],
        "prod_status": "notStarted", "prod_attempts": 0,
        "stages": [("SCM Inspection", "succeeded", "1"),
                   ("Production", "notStarted", "0")],
    }
    base.update(kw)
    return base


def test_print_table_y_detalles(monkeypatch):
    """Render completo sin Rich: tabla + paneles + summary en stdout."""
    monkeypatch.setattr(pv, "RICH", False)
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    rows = [_row(),
            _row(release_name="Release-41", pr_id=None,
                 violations=[{"severity": "HIGH", "rule": "RULE_1_SECRET",
                              "environment": "Production",
                              "variable": "passAzure", "reason": "",
                              "detail": "secreto sin isSecret",
                              "task": "SCM", "generic": False}],
                 rb_valid=False, validator_ran=True)]
    pv.print_main_table(rows)
    pv.print_row_details(rows, _A())
    pv.print_summary([{"error": "", "rows": rows}], rows)
    out = buf.getvalue()
    assert "oms-com-order-CD" in out
    assert "PR#176004" in out
    assert "20240926.5" in out
    assert "aacda92c" in out
    assert "107cd5c8" in out
    assert "Release-40" in out
    assert "RULE_1_SECRET" in out
    assert "Releases pendientes de Production: 2" in out
    assert "sin validar" in out


def test_props_commit_desde_violaciones():
    v = [{"severity": "WARNING", "rule": "TASK_ISSUE", "variable": "",
          "environment": "", "reason": "",
          "detail": "Commit actual en prod: "
                    "107cd5c8465654c4526eae2f28d203952f1e421c",
          "task": "t", "generic": True}]
    assert pv.props_commit_from_logs(v) == \
        "107cd5c8465654c4526eae2f28d203952f1e421c"
    assert pv.props_commit_from_logs([]) == ""


def test_viol_cell():
    cell = pv._viol_cell([{"severity": "HIGH"}])
    assert "HIGH" in cell


def test_score_cell():
    assert "85" in pv._score_cell(85, ("🟢", "Excelente"))


def test_export_row_aplana_campos():
    """export_row produce una fila plana serializable para JSON/HTML/Excel."""
    r = _row(violations=[{"severity": "HIGH", "rule": "RULE_1_SECRET",
                          "environment": "Production", "variable": "passAzure",
                          "reason": "", "detail": "secreto sin isSecret",
                          "task": "t", "generic": False}])
    flat = pv.export_row(r)
    assert flat["cd_pipeline"] == "oms-com-order-CD"
    assert flat["build_id"] == "495667"
    assert flat["git_commit"] == "aacda92cbd18"
    assert flat["rating"] == "X"          # label, no emoji
    assert flat["rollback_release_id"] == "60993"
    assert flat["rollback_git_commit"] == "f228b069"
    assert flat["rollback_props_commit"] == "107cd5c8465"
    assert flat["violations_count"] == 1
    assert "RULE_1_SECRET" in flat["violations"]
    assert "var=passAzure" in flat["violations"]
    assert "SCM Inspection:succeeded" in flat["stages"]
    assert "Production:notStarted" in flat["stages"]
    # todo el valor es escalar (str/int/bool) — serializable directo
    import json as _json
    _json.dumps(flat)


def test_print_row_details_sin_paneles(monkeypatch):
    """El detalle ya no usa fichas/Panel: solo tablas."""
    import io as _io
    assert not hasattr(pv, "Panel"), "print_row_details ya no debe usar Panel"
    # modo Rich (si disponible): imprime tablas sin error
    if pv.RICH:
        buf = _io.StringIO()
        monkeypatch.setattr(pv.console, "print",
                            lambda *a, **k: buf.write(str(a[0]) + "\n"))
        pv.print_row_details([_row()], _A())
        assert buf.getvalue()
