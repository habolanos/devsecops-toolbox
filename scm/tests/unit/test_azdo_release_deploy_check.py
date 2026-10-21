"""
Tests para Release Deploy Check (azdo_release_deploy_check.py)

Cubre: filtrado de envs prod, extraccion de artifacts (build id / build
number / commit sourceVersion), variables del release, match RELASE_ID
contra rollback, busqueda del PR por merge commit, commit del folder en
el repo de propiedades, seleccion interactiva y render del comparativo.
"""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "azdo"))

import azdo_release_deploy_check as rdc  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures de datos
# ═══════════════════════════════════════════════════════════════════════════
def _release(rel_id=61949, name="Release-382", envs=None, artifacts=None,
             variables=None):
    return {
        "id": rel_id,
        "name": name,
        "status": "active",
        "createdOn": "2026-10-15T10:00:00Z",
        "environments": envs if envs is not None else [],
        "artifacts": artifacts if artifacts is not None else [],
        "variables": variables or {},
    }


def _prod_env(status="succeeded", when="2026-10-16T08:00:00Z"):
    return {
        "name": "GKE-Prod",
        "status": status,
        "deploySteps": [{"deploymentStatus": status, "finishedOn": when}],
        "modifiedOn": when,
    }


def _build_artifact(build_id="5001", build_number="20261015.7",
                    commit="9dad7445abcd1234", repo_name="wms-sys-originalorder",
                    primary=True):
    return {
        "type": "Build",
        "alias": repo_name,
        "isPrimary": primary,
        "definitionReference": {
            "version": {"id": build_id, "name": build_number},
            "sourceVersion": {"id": commit},
            "repository": {"id": "repo-1", "name": repo_name},
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# _is_prod_env / release_prod_status
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("env,expected", [
    ("GKE-Prod", True), ("prod-eastus", True), ("PRD", True),
    ("production-aks", True), ("QA", False), ("dev", False),
    ("GKE-Stag", False), ("", False),
])
def test_is_prod_env(env, expected):
    assert rdc._is_prod_env(env) is expected


def test_release_prod_status_succeeded():
    rel = _release(envs=[{"name": "Dev", "status": "succeeded",
                          "deploySteps": [], "modifiedOn": ""},
                         _prod_env()])
    status, when = rdc.release_prod_status(rel)
    assert status == "succeeded"
    assert when == "2026-10-16T08:00:00Z"


def test_release_prod_status_no_prod():
    rel = _release(envs=[{"name": "QA", "status": "succeeded",
                          "deploySteps": [], "modifiedOn": ""}])
    status, when = rdc.release_prod_status(rel)
    assert status == ""
    assert when == ""


# ═══════════════════════════════════════════════════════════════════════════
# artifact_info / extract_primary_artifact
# ═══════════════════════════════════════════════════════════════════════════
def test_artifact_info_build_fields():
    info = rdc.artifact_info(_build_artifact())
    assert info["build_id"] == "5001"
    assert info["build_number"] == "20261015.7"
    assert info["commit"] == "9dad7445abcd1234"
    assert info["repo_name"] == "wms-sys-originalorder"


def test_artifact_info_empty():
    info = rdc.artifact_info(None)
    assert info["build_id"] == "" and info["commit"] == ""


def test_extract_primary_prefers_build():
    git_art = {"type": "Git", "alias": "cfg", "isPrimary": True,
               "definitionReference": {"version": {"id": "abc"}}}
    rel = _release(artifacts=[git_art, _build_artifact(primary=False)])
    art = rdc.extract_primary_artifact(rel)
    assert art["type"] == "Build"


def test_extract_primary_fallback_first():
    git_art = {"type": "Git", "alias": "cfg",
               "definitionReference": {}}
    rel = _release(artifacts=[git_art])
    assert rdc.extract_primary_artifact(rel) is git_art
    assert rdc.extract_primary_artifact(_release(artifacts=[])) is None


# ═══════════════════════════════════════════════════════════════════════════
# release_variables / relase_id_matches_rollback
# ═══════════════════════════════════════════════════════════════════════════
def test_release_variables_dict_and_plain():
    rel = _release(variables={
        "RELASE_ID": {"value": "61344", "allowOverride": True},
        "FOO": "bar",
    })
    v = rdc.release_variables(rel)
    assert v["RELASE_ID"] == "61344"
    assert v["FOO"] == "bar"


@pytest.mark.parametrize("value,name,rid,expected", [
    ("61344", "Release-368", 61344, True),        # por id
    ("Release-368", "Release-368", 61344, True),  # por nombre
    ("release-368", "Release-368", 61344, True),  # case-insensitive
    ("061344", "Release-368", 61344, True),       # ceros a la izquierda
    ("61949", "Release-368", 61344, False),       # id distinto
    ("", "Release-368", 61344, False),            # vacio
    ("Release-382", "Release-368", 61344, False),
])
def test_relase_id_matches_rollback(value, name, rid, expected):
    assert rdc.relase_id_matches_rollback(value, name, rid) is expected


# ═══════════════════════════════════════════════════════════════════════════
# find_pr_for_commit — comparacion PR ↔ commit
# ═══════════════════════════════════════════════════════════════════════════
def test_find_pr_for_commit_matches_last_merge(monkeypatch):
    prs = {"value": [
        {"pullRequestId": 10, "title": "otro",
         "lastMergeCommit": {"commitId": "ffff"}},
        {"pullRequestId": 99, "title": "feat: fix",
         "lastMergeCommit": {"commitId": "9dad7445abcd1234"}},
    ]}
    monkeypatch.setattr(rdc, "api_get", lambda *a, **k: prs)
    pr = rdc.find_pr_for_commit("o", "p", "repo-1",
                                "9DAD7445ABCD1234", {}, False)
    assert pr["pullRequestId"] == 99


def test_find_pr_for_commit_target_or_source(monkeypatch):
    prs = {"value": [
        {"pullRequestId": 7,
         "lastMergeTargetCommit": {"commitId": "abc123"},
         "lastMergeSourceCommit": {"commitId": "xyz"}},
    ]}
    monkeypatch.setattr(rdc, "api_get", lambda *a, **k: prs)
    assert rdc.find_pr_for_commit("o", "p", "r", "abc123", {},
                                  False)["pullRequestId"] == 7
    assert rdc.find_pr_for_commit("o", "p", "r", "xyz", {},
                                  False)["pullRequestId"] == 7


def test_find_pr_for_commit_no_match(monkeypatch):
    monkeypatch.setattr(rdc, "api_get",
                        lambda *a, **k: {"value": [{"pullRequestId": 1,
                                                    "lastMergeCommit":
                                                     {"commitId": "ff"}}]})
    assert rdc.find_pr_for_commit("o", "p", "r", "aa", {}, False) is None
    # sin repo o commit → ni consulta
    assert rdc.find_pr_for_commit("o", "p", "", "aa", {}, False) is None
    assert rdc.find_pr_for_commit("o", "p", "r", "", {}, False) is None


# ═══════════════════════════════════════════════════════════════════════════
# last_commit_in_path / find_properties_repo
# ═══════════════════════════════════════════════════════════════════════════
def test_last_commit_in_path(monkeypatch):
    calls = {}

    def fake_get(url, headers, params=None, debug=False):
        calls["params"] = params
        return {"value": [{"commitId": "a16b06c8"}]}

    monkeypatch.setattr(rdc, "api_get", fake_get)
    c = rdc.last_commit_in_path("o", "p", "repo-1",
                              "/wms-sys-originalorder", "master", {}, False)
    assert c["commitId"] == "a16b06c8"
    assert calls["params"]["searchCriteria.itemPath"] == "/wms-sys-originalorder"
    assert calls["params"]["searchCriteria.itemVersion.version"] == "master"


def test_find_properties_repo():
    repos = [{"name": "wms-sys-originalorder"},
             {"name": "devsecops-properties"},
             {"name": "other"}]
    assert rdc.find_properties_repo(repos, "")["name"] == "devsecops-properties"
    assert rdc.find_properties_repo(repos, "other")["name"] == "other"
    assert rdc.find_properties_repo(
        [{"name": "a"}], "") is None


# ═══════════════════════════════════════════════════════════════════════════
# choose_release (input mockeado)
# ═══════════════════════════════════════════════════════════════════════════
def test_choose_release_by_index(monkeypatch):
    rels = [_release(rel_id=1, name="Release-1"),
            _release(rel_id=2, name="Release-2")]
    monkeypatch.setattr("builtins.input", lambda *a: "2")
    assert rdc.choose_release(rels, "pick")["id"] == 2


def test_choose_release_by_name(monkeypatch):
    rels = [_release(rel_id=1, name="Release-1"),
            _release(rel_id=2, name="Release-2")]
    monkeypatch.setattr("builtins.input", lambda *a: "Release-1")
    assert rdc.choose_release(rels, "pick")["id"] == 1


def test_choose_release_exclude_then_pick(monkeypatch):
    rels = [_release(rel_id=1, name="Release-1"),
            _release(rel_id=2, name="Release-2")]
    answers = iter(["1", "2"])  # primero intenta el excluido
    monkeypatch.setattr("builtins.input", lambda *a: next(answers))
    assert rdc.choose_release(rels, "pick", exclude_id=1)["id"] == 2


def test_choose_release_quit(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a: "q")
    assert rdc.choose_release([_release()], "pick") is None


# ═══════════════════════════════════════════════════════════════════════════
# print_releases_table — coloreo de status
# ═══════════════════════════════════════════════════════════════════════════
def test_releases_table_inprogress_amarillo(monkeypatch):
    """Los releases con status inProgress se pintan de amarillo (SGR 33)."""
    if not rdc.RICH:
        pytest.skip("rich no disponible")
    from rich.console import Console
    buf = io.StringIO()
    monkeypatch.setattr(rdc, "console",
                        Console(file=buf, force_terminal=True, width=120))
    rels = [_release(rel_id=1, name="Release-1"),
            dict(_release(rel_id=2, name="Release-2"),
                 status="inProgress")]
    rdc.print_releases_table(rels)
    out = buf.getvalue()
    assert "inProgress" in out
    # el amarillo de Rich es SGR 33: debe aparecer justo antes del texto
    line = next(l for l in out.splitlines() if "inProgress" in l)
    assert "\x1b[33m" in line or "\x1b[1;33m" in line


# ═══════════════════════════════════════════════════════════════════════════
# release_block — integracion con API mockeada
# ═══════════════════════════════════════════════════════════════════════════
def _mock_apis(monkeypatch, pr=None, props_commit="a16b06c8",
               build_commit="9dad7445abcd1234"):
    detail = _release(
        rel_id=61949, name="Release-382",
        artifacts=[_build_artifact()],
        variables={"RELASE_ID": {"value": "61344"}},
    )
    monkeypatch.setattr(rdc, "get_release_detail",
                        lambda *a, **k: detail)
    monkeypatch.setattr(rdc, "get_build",
                        lambda *a, **k: {"sourceVersion": build_commit})
    monkeypatch.setattr(rdc, "find_pr_for_commit",
                        lambda *a, **k: pr)
    monkeypatch.setattr(rdc, "last_commit_in_path",
                        lambda *a, **k: {"commitId": props_commit})


def test_release_block_fields(monkeypatch):
    pr = {"pullRequestId": 42, "title": "feat"}
    _mock_apis(monkeypatch, pr=pr)
    repos = [{"name": "wms-sys-originalorder",
              "remoteUrl": "https://dev.azure.com/o/p/_git/wms-sys-originalorder",
              "id": "repo-1"}]
    props = {"name": "devsecops-properties", "id": "props-1"}
    rel = _release(rel_id=61949, name="Release-382",
                   artifacts=[_build_artifact()])
    b = rdc.release_block("https://dev.azure.com/o", "proj", rel,
                          "cd-pipe", {}, props,
                          {"wms-sys-originalorder": repos[0]},
                          "master", False)
    assert b["component"] == "wms-sys-originalorder"
    assert b["release_name"] == "Release-382"
    assert b["build_number"] == "20261015.7"
    assert b["commit_short"] == "9dad7445"
    assert b["props_commit"] == "a16b06c8"
    assert b["commit_matches_build"] is True
    assert b["pr"] is pr
    assert "releaseId=61949" in b["url"]
    assert b["variables"]["RELASE_ID"] == "61344"
    assert b["excepto_a"] == "N/A"


def test_release_block_commit_mismatch(monkeypatch):
    _mock_apis(monkeypatch, build_commit="diferente")
    rel = _release(artifacts=[_build_artifact()])
    b = rdc.release_block("o", "p", rel, "cd", {}, None, {}, "master",
                          False)
    assert b["commit_matches_build"] is False


# ═══════════════════════════════════════════════════════════════════════════
# print_block — render del comparativo
# ═══════════════════════════════════════════════════════════════════════════
def _capture_plain(monkeypatch):
    """Fuerza salida plain y captura stdout."""
    monkeypatch.setattr(rdc, "RICH", False)
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    return buf


def _block(**kw):
    base = {
        "component": "wms-sys-originalorder",
        "release_name": "Release-382", "release_id": 61949,
        "pipeline": "wms-cd", "url": "http://x",
        "build_id": "5001", "build_number": "20261015.7",
        "commit": "9dad7445abcd", "commit_short": "9dad7445",
        "build_commit": "9dad7445abcd", "commit_matches_build": True,
        "pr": None, "props_commit": "a16b06c8",
        "repo_url": "http://repo", "variables": {},
        "excepto_a": "N/A",
    }
    base.update(kw)
    return base


def test_print_block_formato(monkeypatch):
    buf = _capture_plain(monkeypatch)
    rdc.print_block(_block(), "Cadena de Suministros")
    out = buf.getvalue()
    assert "Nombre del componente: wms-sys-originalorder" in out
    assert "Nombre Organización: Cadena de Suministros" in out
    assert "Nombre del Release: Release-382" in out
    assert "Pipeline de CD: wms-cd" in out
    assert "No. compilación: 20261015.7" in out
    assert "Commit Release: 9dad7445" in out
    assert "Commit Properties: a16b06c8" in out
    assert "Ruta del Repositorio en Azure: http://repo" in out
    assert "Excepto a: N/A" in out


def test_print_block_relase_id_verde(monkeypatch):
    buf = _capture_plain(monkeypatch)
    rdc.print_block(_block(), "org", rollback_match=True,
                    release_id_var="61344")
    assert "RELASE_ID: 61344" in buf.getvalue()
    assert "coincide" in buf.getvalue()


def test_print_block_pr_line(monkeypatch):
    buf = _capture_plain(monkeypatch)
    pr = {"pullRequestId": 42, "title": "feat: cosa"}
    rdc.print_block(_block(pr=pr), "org")
    assert "PR asociado: #42" in buf.getvalue()
