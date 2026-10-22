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
             variables=None, createdOn="2026-10-15T10:00:00Z"):
    return {
        "id": rel_id,
        "name": name,
        "status": "active",
        "createdOn": createdOn,
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
                    commit="9dad7445abcd1234",
                    artifact_name="wms-sys-originalorder",
                    primary=True):
    return {
        "type": "Build",
        "alias": "_wms-CI",
        "name": artifact_name,
        "isPrimary": primary,
        "definitionReference": {
            "version": {"id": build_id, "name": build_number},
            "sourceVersion": {"id": commit},
            # OJO: este repository es el repo del YAML CI
            # (pipelines-projects), NO el repo fuente del componente.
            "repository": {"id": "ci-repo", "name": "pipelines-projects"},
        },
    }


def _build_detail(source_version="9dad7445abcd1234",
                  repo_name="wms-sys-originalorder", repo_id="r-src",
                  props_commit="a16b06c8", pr_ref="refs/pull/521334/merge"):
    """Replica la seccion 'Repositories' del build (screenshot AzDO):
    self=pipelines-projects (YAML CI), sources=repo fuente,
    archetype=pipeline-archetype-yml, properties=repo de propiedades."""
    return {
        "sourceVersion": source_version,
        "sourceBranch": pr_ref or "",
        "repository": {
            "id": "ci-repo", "name": "pipelines-projects",
            "url": "https://dev.azure.com/o/p/_git/pipelines-projects",
        },
        "sourceRepositories": [
            {"alias": "self",
             "repository": {"id": "ci-repo", "name": "pipelines-projects",
                            "url": "https://dev.azure.com/o/p/_git/pipelines-projects"},
             "sourceVersion": "9acc8cc3", "sourceBranch": "refs/heads/master"},
            {"alias": "sources",
             "repository": {"id": repo_id, "name": repo_name,
                            "url": f"https://dev.azure.com/o/p/_git/{repo_name}"},
             "sourceVersion": source_version, "sourceBranch": pr_ref},
            {"alias": "archetype",
             "repository": {"id": "arch-1", "name": "pipeline-archetype-yml",
                            "url": "https://dev.azure.com/o/p/_git/pipeline-archetype-yml"},
             "sourceVersion": "20691efb",
             "sourceBranch": "refs/heads/feature/feature-amad"},
            {"alias": "properties",
             "repository": {"id": "props-1", "name": "properties",
                            "url": "https://dev.azure.com/o/p/_git/properties"},
             "sourceVersion": props_commit,
             "sourceBranch": "refs/heads/master"},
        ],
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
    # artifact.name = componente fuente, NO el repo del YAML CI
    assert info["artifact_name"] == "wms-sys-originalorder"


def test_artifact_info_name_fallback_alias():
    art = _build_artifact()
    del art["name"]
    assert rdc.artifact_info(art)["artifact_name"] == "_wms-CI"


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
# folder_commits / commit por fecha / find_properties_repo
# ═══════════════════════════════════════════════════════════════════════════
def test_folder_commits(monkeypatch):
    calls = {}

    def fake_get(url, headers, params=None, debug=False):
        calls["params"] = params
        return {"value": [{"commitId": "a16b06c8"},
                          {"commitId": "ffffff"}]}

    monkeypatch.setattr(rdc, "api_get", fake_get)
    commits = rdc.folder_commits("o", "p", "repo-1",
                                 "/wms-sys-originalorder", "master",
                                 {}, False)
    assert commits[0]["commitId"] == "a16b06c8"
    assert calls["params"]["searchCriteria.itemPath"] == \
        "/wms-sys-originalorder"
    assert calls["params"]["searchCriteria.itemVersion.version"] == "master"


def test_commit_matching_date():
    commits = [
        {"commitId": "n1", "author": {"date": "2026-10-21T10:00:00Z"}},
        {"commitId": "n2", "author": {"date": "2026-10-10T10:00:00Z"}},
        {"commitId": "n3", "author": {"date": "2026-10-01T10:00:00Z"}},
        {"commitId": "n4", "author": {"date": "2026-09-01T10:00:00Z"}},
    ]
    # release ejecutado el 2026-10-07 → el ultimo commit en o antes: n4?
    # no: n3 es 2026-10-01 <= 10-07 → n3
    assert rdc.commit_matching_date(commits, "2026-10-07T00:00:00Z")["commitId"] == "n3"
    # exactamente en la fecha del commit → ese commit
    assert rdc.commit_matching_date(commits, "2026-10-10T10:00:00Z")["commitId"] == "n2"
    # fecha anterior a todos → el mas antiguo disponible
    assert rdc.commit_matching_date(commits, "2026-01-01T00:00:00Z")["commitId"] == "n4"
    # sin fecha → el ultimo (HEAD)
    assert rdc.commit_matching_date(commits, "")["commitId"] == "n1"
    assert rdc.commit_matching_date([], "2026-10-07T00:00:00Z") is None


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


def test_releases_table_mas_de_30_dias_tenue(monkeypatch):
    """Releases con >30 dias se renderizan con estilo dim (SGR 2)."""
    if not rdc.RICH:
        pytest.skip("rich no disponible")
    from datetime import datetime, timedelta, timezone
    from rich.console import Console
    buf = io.StringIO()
    monkeypatch.setattr(rdc, "console",
                        Console(file=buf, force_terminal=True, width=120))
    old = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    new = datetime.now(timezone.utc).isoformat()
    rels = [dict(_release(rel_id=1, name="Release-1"), createdOn=old),
            dict(_release(rel_id=2, name="Release-2"), createdOn=new)]
    rdc.print_releases_table(rels)
    out = buf.getvalue()
    old_line = next(l for l in out.splitlines() if "Release-1" in l)
    new_line = next(l for l in out.splitlines() if "Release-2" in l)
    # dim en la celda RELEASE: SGR combinado 2;36 (dim+cyan)
    assert "\x1b[2;36m" in old_line
    assert "\x1b[2;36m" not in new_line
    assert "\x1b[36mRelease-2" in new_line   # cyan sin dim


# ═══════════════════════════════════════════════════════════════════════════
# release_block — integracion con API mockeada
# ═══════════════════════════════════════════════════════════════════════════
def _mock_apis(monkeypatch, pr=None, props_folder_commit="a16b06c8",
               build=None, pr_by_id=None):
    detail = _release(
        rel_id=61949, name="Release-382",
        artifacts=[_build_artifact()],
        variables={"RELASE_ID": {"value": "61344"}},
    )
    monkeypatch.setattr(rdc, "get_release_detail",
                        lambda *a, **k: detail)
    monkeypatch.setattr(rdc, "get_build",
                        lambda *a, **k: build or _build_detail())
    monkeypatch.setattr(rdc, "find_pr_for_commit",
                        lambda *a, **k: pr)
    monkeypatch.setattr(rdc, "get_pull_request",
                        lambda *a, **k: pr_by_id)
    monkeypatch.setattr(rdc, "get_build_changes", lambda *a, **k: [])
    monkeypatch.setattr(rdc, "get_repository", lambda *a, **k: None)
    monkeypatch.setattr(rdc, "folder_commits",
                        lambda *a, **k: [{"commitId": props_folder_commit}]
                        if props_folder_commit else [])


def _git_artifact(repo_name="oms-com-order", commit="7ab55d31",
                  repo_id="r-oms", primary=False):
    """Artifact SOURCE (tipo Git) del release: repo real + commit."""
    return {
        "type": "Git", "alias": repo_name, "isPrimary": primary,
        "definitionReference": {
            "repository": {"id": repo_id, "name": repo_name},
            "version": {"id": commit},
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# extract_artifacts / git_artifact_info / classify
# ═══════════════════════════════════════════════════════════════════════════
def test_extract_artifacts_build_y_source():
    rel = _release(artifacts=[_build_artifact(), _git_artifact()])
    build_art, git_arts = rdc.extract_artifacts(rel)
    assert build_art["type"] == "Build"
    assert len(git_arts) == 1 and git_arts[0]["type"] == "Git"
    # sin build → fallback al primero
    rel2 = _release(artifacts=[_git_artifact()])
    build_art2, _ = rdc.extract_artifacts(rel2)
    assert build_art2["type"] == "Git"


def test_git_artifact_info():
    gi = rdc.git_artifact_info(_git_artifact())
    assert gi["repo_id"] == "r-oms"
    assert gi["repo_name"] == "oms-com-order"
    assert gi["commit"] == "7ab55d31"
    assert rdc.git_artifact_info(None)["commit"] == ""


def test_classify_git_artifacts():
    git_arts = [_git_artifact(repo_name="properties", commit="1ae6cb",
                              repo_id="props1"),
                _git_artifact()]
    src, props = rdc.classify_git_artifacts(git_arts)
    assert src["repo_name"] == "oms-com-order"
    assert props["repo_name"] == "properties"


def test_release_block_con_source_artifact(monkeypatch):
    """Release con 2 artifacts (Build + Git source): el commit del
    release viene del SOURCE artifact (Git), no del build/CI, y el repo
    del componente del artifact. Del build se toman los commits de
    sources y properties."""
    git_arts = [_git_artifact()]
    detail = _release(artifacts=[_build_artifact(commit="cf6e2244ci"),
                                 _git_artifact()])
    pr = {"pullRequestId": 4210,
          "lastMergeCommit": {"commitId": "7ab55d31"}}
    _mock_apis(monkeypatch, pr_by_id=pr)
    monkeypatch.setattr(rdc, "get_release_detail",
                        lambda *a, **k: detail)
    # build: sources y properties con sus commits de compilacion
    build = {"sourceVersion": "cf6e2244ci",
             "sourceBranch": "refs/pull/4210/merge",
             "repository": {"id": "ci-repo", "name": "pipelines-projects"},
             "sourceRepositories": [
                 {"alias": "self",
                  "repository": {"id": "ci-repo",
                                 "name": "pipelines-projects"},
                  "sourceVersion": "cf6e2244ci"},
                 {"alias": "sources",
                  "repository": {"id": "r-oms", "name": "oms-com-order"},
                  "sourceVersion": "7ab55d31",
                  "sourceBranch": "refs/pull/4210/merge"},
                 {"alias": "properties",
                  "repository": {"id": "props1", "name": "properties"},
                  "sourceVersion": "1ae6cb17"}]}
    monkeypatch.setattr(rdc, "get_build", lambda *a, **k: build)
    rel = _release(artifacts=[_build_artifact(commit="cf6e2244ci"),
                              _git_artifact()])
    b = rdc.release_block("o", "p", rel, "cd", {}, None, {}, "master",
                          False)
    # commit del release = source artifact (Git)
    assert b["commit"] == "7ab55d31"
    assert b["artifact_commit"] == "cf6e2244ci"   # commit del CI (build art)
    # repo del componente desde el artifact Git
    assert b["src_repo_name"] == "oms-com-order"
    # commit sources del build comparado con el del release
    assert b["build_commit"] == "7ab55d31"
    assert b["commit_matches_build"] is True
    # commit properties de la compilacion
    assert b["props_commit"] == "1ae6cb17"
    # PR con el commit del source artifact
    assert b["pr"] is pr
    assert b["pr_commit_matches"] is True
    pr = {"pullRequestId": 42, "title": "feat",
          "lastMergeCommit": {"commitId": "9dad7445abcd1234"}}
    _mock_apis(monkeypatch, pr_by_id=pr)
    rel = _release(rel_id=61949, name="Release-382",
                   artifacts=[_build_artifact()])
    b = rdc.release_block("https://dev.azure.com/o", "proj", rel,
                          "cd-pipe", {}, None, {}, "master", False)
    assert b["component"] == "wms-sys-originalorder"
    assert b["component_matches_build_repo"] is True
    assert b["release_name"] == "Release-382"
    assert b["build_number"] == "20261015.7"
    assert b["commit_short"] == "9dad7445"
    # Commit Properties = sourceVersion del repo properties en el build
    assert b["props_commit"] == "a16b06c8"
    assert b["props_folder_commit"] == "a16b06c8"
    assert b["props_match"] is True
    # Ruta del repo = entry 'sources' del build (repo fuente)
    assert "wms-sys-originalorder" in b["repo_url"]
    assert "pipelines-projects" not in b["repo_url"]
    assert "@" not in b["repo_url"]
    assert b["commit_matches_build"] is True
    # PR resuelto por ref refs/pull/521334/merge del sourceBranch
    assert b["pr"] is pr
    assert b["pr_ref"] == "refs/pull/521334/merge"
    assert b["pr_url"] == ("https://dev.azure.com/o/proj/_git/"
                           "wms-sys-originalorder/pullrequest/42")
    assert b["pr_commit"] == "9dad7445abcd1234"
    assert b["pr_commit_matches"] is True
    assert "releaseId=61949" in b["url"]
    assert b["variables"]["RELASE_ID"] == "61344"
    assert b["excepto_a"] == "N/A"


def test_release_block_pr_fallback_scan(monkeypatch):
    """Sin ref refs/pull en el build → scan de PRs completados."""
    pr = {"pullRequestId": 7,
          "lastMergeCommit": {"commitId": "9dad7445abcd1234"}}
    _mock_apis(monkeypatch, pr=pr, pr_by_id=None,
               build=_build_detail(pr_ref=""))
    rel = _release(artifacts=[_build_artifact()])
    b = rdc.release_block("o", "p", rel, "cd", {}, None, {}, "master",
                          False)
    assert b["pr"] is pr
    assert b["pr_ref"] == ""


def test_release_block_pr_buscado_en_repo_fuente(monkeypatch):
    """La PR se busca en el repo fuente (entry 'sources'), no en
    pipelines-projects."""
    seen = {}

    def fake_pr(org, project, repo_id, commit, headers, debug):
        seen["repo_id"] = repo_id
        return None

    _mock_apis(monkeypatch, build=_build_detail(pr_ref=""))
    monkeypatch.setattr(rdc, "find_pr_for_commit", fake_pr)
    rel = _release(artifacts=[_build_artifact()])
    rdc.release_block("o", "p", rel, "cd", {}, None, {}, "master", False)
    assert seen["repo_id"] == "r-src"


def test_release_block_props_folder_contrast(monkeypatch):
    _mock_apis(monkeypatch, props_folder_commit="otro-commit")
    rel = _release(artifacts=[_build_artifact()])
    b = rdc.release_block("o", "p", rel, "cd", {}, None, {}, "master",
                          False)
    assert b["props_commit"] == "a16b06c8"        # commit compilación
    assert b["props_folder_commit"] == "otro-commit"
    assert b["props_match"] is False


def test_release_block_component_desde_repo_resuelto(monkeypatch):
    """component = repo fuente resuelto; artifact.name distinto queda
    como anotacion (CI: ...)."""
    _mock_apis(monkeypatch,
               build=_build_detail(repo_name="otro-repo"))
    rel = _release(artifacts=[_build_artifact()])
    b = rdc.release_block("o", "p", rel, "cd", {}, None, {}, "master",
                          False)
    assert b["component"] == "otro-repo"          # repo fuente manda
    assert b["artifact_clean"] == "wms-sys-originalorder"
    assert b["src_repo_name"] == "otro-repo"
    assert b["component_matches_build_repo"] is True


def test_release_block_repo_por_prefijo(monkeypatch):
    """Sin sourceRepositories ni changes: el repo se resuelve como
    prefijo del artifact.name sobre la lista de repos del proyecto."""
    build = {"sourceVersion": "cf6e2244",
             "repository": {"id": "ci-repo", "name": "pipelines-projects"}}
    _mock_apis(monkeypatch, build=build)
    repos_by_name = {
        "oms-com-order": {"id": "r-oms", "name": "oms-com-order",
                          "remoteUrl": "https://o@dev.azure.com/o/p/"
                                       "_git/oms-com-order"},
        "properties": {"id": "props1", "name": "properties"},
    }
    art = _build_artifact(
        artifact_name="_oms-com-order-springboot-java17-GKE-TMS-OMS-CI")
    rel = _release(artifacts=[art])
    # el detail mockeado tambien debe traer este artifact
    detail = _release(artifacts=[art])
    monkeypatch.setattr(rdc, "get_release_detail",
                        lambda *a, **k: detail)
    b = rdc.release_block("o", "p", rel, "cd", {}, None, repos_by_name,
                          "master", False)
    assert b["component"] == "oms-com-order"
    assert b["src_repo_name"] == "oms-com-order"
    assert b["repo_url"] == "https://dev.azure.com/o/p/_git/oms-com-order"
    # el PR se busca en el repo resuelto
    # (find_pr_for_commit mockeado devuelve None, pero repo_id quedo)
    assert b["commit"] == "9dad7445abcd1234"


def test_release_block_sin_source_repositories(monkeypatch):
    """Build sin sourceRepositories (api vieja): el repo fuente se
    resuelve buscando el commit del release en builds/{id}/changes."""
    build = {"sourceVersion": "9dad7445abcd1234",
             "sourceBranch": "",
             "repository": {"id": "ci-repo", "name": "pipelines-projects",
                            "url": "https://dev.azure.com/o/p/_git/pipelines-projects"}}
    changes = [{"id": "9dad7445abcd1234",
                "location": "https://dev.azure.com/o/p/_apis/git/"
                            "repositories/r-src/commits/9dad7445abcd1234",
                "type": "TfsGit"}]
    repo = {"id": "r-src", "name": "wms-sys-originalorder",
            "remoteUrl": "https://Coppel-Retail@dev.azure.com/o/p/"
                         "_git/wms-sys-originalorder"}
    pr = {"pullRequestId": 55,
          "lastMergeCommit": {"commitId": "9dad7445abcd1234"}}

    _mock_apis(monkeypatch, build=build, pr=pr)
    monkeypatch.setattr(rdc, "get_build_changes", lambda *a, **k: changes)
    monkeypatch.setattr(rdc, "get_repository", lambda *a, **k: repo)

    rel = _release(artifacts=[_build_artifact()])
    b = rdc.release_block("o", "p", rel, "cd", {}, None, {}, "master",
                          False)
    assert b["repo_url"] == \
        "https://dev.azure.com/o/p/_git/wms-sys-originalorder"
    assert "pipelines-projects" not in b["repo_url"]
    assert "@" not in b["repo_url"]
    assert b["src_repo_name"] == "wms-sys-originalorder"
    # el PR se busco en el repo fuente resuelto por changes
    assert b["pr"] is pr


def test_release_block_changes_prefiere_repo_no_ci(monkeypatch):
    """En builds multi-checkout los changes traen commits de varios repos:
    si el commit aparece en el repo del CI y en el del componente, gana
    el del componente."""
    build = {"sourceVersion": "9dad7445abcd1234",
             "repository": {"id": "ci-repo", "name": "pipelines-projects"}}
    changes = [
        {"id": "9dad7445abcd1234",
         "location": "https://dev.azure.com/o/p/_apis/git/"
                     "repositories/ci-repo/commits/9dad7445abcd1234"},
        {"id": "9dad7445abcd1234",
         "location": "https://dev.azure.com/o/p/_apis/git/"
                     "repositories/r-src/commits/9dad7445abcd1234"},
    ]
    repos = {"ci-repo": {"id": "ci-repo", "name": "pipelines-projects",
                         "remoteUrl": "https://x@dev.azure.com/o/p/_git/pipelines-projects"},
             "r-src": {"id": "r-src", "name": "wms-sys-originalorder",
                       "remoteUrl": "https://x@dev.azure.com/o/p/_git/wms-sys-originalorder"}}
    _mock_apis(monkeypatch, build=build)
    monkeypatch.setattr(rdc, "get_build_changes", lambda *a, **k: changes)
    monkeypatch.setattr(rdc, "get_repository",
                        lambda org, p, rid, h, d: repos.get(rid))
    rel = _release(artifacts=[_build_artifact()])
    b = rdc.release_block("o", "p", rel, "cd", {}, None, {}, "master",
                          False)
    assert b["src_repo_name"] == "wms-sys-originalorder"
    assert "pipelines-projects" not in b["repo_url"]


def test_release_block_changes_solo_repo_ci_cae_a_prefijo(monkeypatch):
    """Si el commit solo aparece en changes del repo del CI, se ignora y
    la resolucion cae al prefijo del artifact.name."""
    build = {"sourceVersion": "cf6e2244",
             "repository": {"id": "ci-repo", "name": "pipelines-projects"}}
    changes = [{"id": "cf6e2244",
                "location": "https://dev.azure.com/o/p/_apis/git/"
                            "repositories/ci-repo/commits/cf6e2244"}]
    repos = {"ci-repo": {"id": "ci-repo", "name": "pipelines-projects",
                         "remoteUrl": "https://dev.azure.com/o/p/_git/pipelines-projects"}}
    repos_by_name = {"oms-com-order": {"id": "r-oms",
                                       "name": "oms-com-order",
                                       "remoteUrl": "https://dev.azure.com/o/p/_git/oms-com-order"}}
    art = _build_artifact(
        artifact_name="_oms-com-order-springboot-java17-GKE-TMS-OMS-CI")
    _mock_apis(monkeypatch, build=build)
    detail = _release(artifacts=[art])
    monkeypatch.setattr(rdc, "get_release_detail",
                        lambda *a, **k: detail)
    monkeypatch.setattr(rdc, "get_build_changes", lambda *a, **k: changes)
    monkeypatch.setattr(rdc, "get_repository",
                        lambda org, p, rid, h, d: repos.get(rid))
    b = rdc.release_block("o", "p", _release(artifacts=[art]), "cd", {},
                          None, repos_by_name, "master", False)
    assert b["src_repo_name"] == "oms-com-order"
    assert b["repo_url"].endswith("/_git/oms-com-order")


def test_repo_id_from_location():
    assert rdc.repo_id_from_location(
        "https://dev.azure.com/o/p/_apis/git/repositories/abc-123/"
        "commits/0f5f937b") == "abc-123"
    assert rdc.repo_id_from_location("") == ""
    assert rdc.repo_id_from_location("no-match") == ""


@pytest.mark.parametrize("raw,expected", [
    ("_wms-front-motosmanagement-cloudrun-angular21-CI",
     "wms-front-motosmanagement-cloudrun-angular21"),
    ("wms-sys-originalorder", "wms-sys-originalorder"),
    ("_repo-CD", "repo"),
    ("", ""),
    (None, ""),
])
def test_clean_component_name(raw, expected):
    assert rdc.clean_component_name(raw) == expected


def test_release_block_commit_mismatch(monkeypatch):
    """El commit del release (source artifact Git) difiere del commit del
    source en el build → comparacion en rojo."""
    detail = _release(artifacts=[
        _build_artifact(),
        _git_artifact(commit="otro-distinto")])
    _mock_apis(monkeypatch)
    monkeypatch.setattr(rdc, "get_release_detail",
                        lambda *a, **k: detail)
    rel = _release(artifacts=[_build_artifact(),
                              _git_artifact(commit="otro-distinto")])
    b = rdc.release_block("o", "p", rel, "cd", {}, None, {}, "master",
                          False)
    assert b["commit"] == "otro-distinto"          # source artifact manda
    assert b["build_commit"] == "9dad7445abcd1234"  # sources del build
    assert b["commit_matches_build"] is False


def test_release_block_commit_sigue_hasta_repo_componente(monkeypatch):
    """El sourceVersion del artifact es el commit del repo del CI
    (pipeline yaml): el commit del release debe seguir buscando hasta el
    source del build cuyo repo hace match con el componente."""
    art = _build_artifact(commit="aaaaciii")   # commit del pipeline CI
    detail = _release(artifacts=[art])
    # build: entry 'sources' → componente con su commit real
    build = _build_detail(source_version="9dad7445abcd1234")
    seen = {}

    def fake_pr(org, project, repo_id, commit, headers, debug):
        seen["commit"] = commit
        return None

    _mock_apis(monkeypatch, build=build)
    monkeypatch.setattr(rdc, "get_release_detail",
                        lambda *a, **k: detail)
    monkeypatch.setattr(rdc, "find_pr_for_commit", fake_pr)
    b = rdc.release_block("o", "p", _release(artifacts=[art]), "cd", {},
                          None, {}, "master", False)
    # Commit Release = el del componente, no el del CI
    assert b["commit"] == "9dad7445abcd1234"
    assert b["artifact_commit"] == "aaaaciii"
    assert b["commit_short"] == "9dad7445"
    assert b["artifact_commit_short"] == "aaaaciii"
    # el PR se busca con el commit del componente
    assert seen["commit"] == "9dad7445abcd1234"
    # comparacion: commit del release (componente) vs sources del build
    assert b["build_commit"] == "9dad7445abcd1234"
    assert b["commit_matches_build"] is True


def test_print_block_commit_artifact_ci(monkeypatch):
    """Cuando el commit del artifact (CI) difiere del commit del
    release, se muestra la linea de referencia."""
    buf = _capture_plain(monkeypatch)
    rdc.print_block(_block(artifact_commit="aaaaciii",
                           artifact_commit_short="aaaaciii"),
                    "org")
    out = buf.getvalue()
    assert "Commit Release: 9dad7445" in out
    assert "Commit Artifact (CI): aaaaciii" in out


def test_strip_userinfo():
    assert rdc.strip_userinfo(
        "https://Coppel-Retail@dev.azure.com/o/p/_git/r") == \
        "https://dev.azure.com/o/p/_git/r"
    assert rdc.strip_userinfo("https://dev.azure.com/o/p/_git/r") == \
        "https://dev.azure.com/o/p/_git/r"


def test_props_source_from_build():
    out = rdc.props_source_from_build(_build_detail(props_commit="deadbeef"))
    assert out["repo_id"] == "props-1"
    assert out["repo_name"] == "properties"
    assert out["commit"] == "deadbeef"
    assert rdc.props_source_from_build({})["commit"] == ""
    # build sin sourceRepositories (APIs viejas)
    assert rdc.props_source_from_build(
        {"sourceVersion": "x"})["commit"] == ""


# ═══════════════════════════════════════════════════════════════════════════
# sourceRepositories — seccion 'Repositories' del build
# ═══════════════════════════════════════════════════════════════════════════
def test_build_source_entries():
    entries = rdc.build_source_entries(_build_detail())
    assert len(entries) == 4
    by_alias = {e["alias"]: e for e in entries}
    assert by_alias["self"]["repo_name"] == "pipelines-projects"
    assert by_alias["sources"]["commit"] == "9dad7445abcd1234"
    assert by_alias["sources"]["branch"] == "refs/pull/521334/merge"
    assert by_alias["properties"]["commit"] == "a16b06c8"
    assert by_alias["archetype"]["repo_name"] == "pipeline-archetype-yml"


def test_find_source_entry():
    entries = rdc.build_source_entries(_build_detail())
    # por artifact.name
    e = rdc.find_source_entry(entries, "wms-sys-originalorder")
    assert e["alias"] == "sources"
    # por alias sources
    e = rdc.find_source_entry(entries, "otro-nombre")
    assert e["alias"] == "sources"
    # sin alias sources → match por prefijo de nombre
    build = _build_detail()
    for sr in build["sourceRepositories"]:
        if sr["alias"] == "sources":
            sr["alias"] = "custom"
    e = rdc.find_source_entry(
        rdc.build_source_entries(build),
        "wms-sys-originalorder-springboot-java17")
    assert e["repo_name"] == "wms-sys-originalorder"
    # NUNCA cae a pipelines-projects/self con nombre ajeno
    assert rdc.find_source_entry(
        rdc.build_source_entries(build), "otro-totalmente-distinto"
    ) is None
    assert rdc.find_source_entry([], "x") is None


def test_find_source_entry_excluye_repo_ci():
    """Caso real: alias 'sources' apunta a pipelines-projects (repo del
    YAML CI) — con exclude debe ignorarlo y resolver por prefijo."""
    build = {"sourceRepositories": [
        {"alias": "sources",
         "repository": {"id": "ci-repo", "name": "pipelines-projects"},
         "sourceVersion": "9acc"},
        {"alias": "app",
         "repository": {"id": "r-src", "name": "oms-com-order"},
         "sourceVersion": "cf6e2244"},
    ]}
    entries = rdc.build_source_entries(build)
    # sin exclude → ganaria 'sources' = pipelines-projects (el bug real)
    assert rdc.find_source_entry(
        entries, "x")["repo_name"] == "pipelines-projects"
    # con exclude → prefijo sobre el nombre del artifact
    e = rdc.find_source_entry(
        entries, "_oms-com-order-springboot-java17-GKE-TMS-OMS-CI",
        exclude="pipelines-projects")
    assert e["repo_name"] == "oms-com-order"


def test_release_block_sources_alias_es_repo_ci(monkeypatch):
    """El alias 'sources' → pipelines-projects (repo del CI) no debe
    ganar: se resuelve el repo real por prefijo del artifact.name."""
    build = {"sourceVersion": "cf6e2244",
             "repository": {"id": "ci-repo", "name": "pipelines-projects",
                            "url": "https://dev.azure.com/o/p/_git/pipelines-projects"},
             "sourceRepositories": [
                 {"alias": "sources",
                  "repository": {"id": "ci-repo",
                                 "name": "pipelines-projects",
                                 "url": "https://dev.azure.com/o/p/_git/pipelines-projects"},
                  "sourceVersion": "9acc"}]}
    _mock_apis(monkeypatch, build=build)
    repos_by_name = {
        "oms-com-order": {"id": "r-oms", "name": "oms-com-order",
                          "remoteUrl": "https://dev.azure.com/o/p/"
                                       "_git/oms-com-order"},
    }
    art = _build_artifact(
        artifact_name="_oms-com-order-springboot-java17-GKE-TMS-OMS-CI")
    detail = _release(artifacts=[art])
    monkeypatch.setattr(rdc, "get_release_detail",
                        lambda *a, **k: detail)
    b = rdc.release_block("o", "p", _release(artifacts=[art]), "cd", {},
                          None, repos_by_name, "master", False)
    assert b["src_repo_name"] == "oms-com-order"
    assert "pipelines-projects" not in b["repo_url"]


def test_repo_prefix_candidates():
    assert rdc.repo_prefix_candidates("a-b-c") == ["a-b-c", "a-b", "a"]
    assert rdc.repo_prefix_candidates("solo") == ["solo"]
    assert rdc.repo_prefix_candidates("") == []


def test_resolve_repo_by_prefix():
    repos = {"oms-com-order": {"id": "r1", "name": "oms-com-order"},
             "properties": {"id": "p1", "name": "properties"}}
    hit = rdc.resolve_repo_by_prefix(
        "oms-com-order-springboot-java17-GKE-TMS-OMS", repos)
    assert hit["id"] == "r1"
    assert rdc.resolve_repo_by_prefix("sin-match-xyz", repos) is None
    # el prefijo mas largo gana
    repos["oms-com"] = {"id": "r0"}
    hit = rdc.resolve_repo_by_prefix("oms-com-order-x", repos)
    assert hit["id"] == "r1"


def test_find_props_entry():
    entries = rdc.build_source_entries(_build_detail())
    assert rdc.find_props_entry(entries)["repo_name"] == "properties"
    assert rdc.find_props_entry([]) is None


# ═══════════════════════════════════════════════════════════════════════════
# PR — refs/pull/{id} y commit definitivo
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("ref,expected", [
    ("refs/pull/521334/merge", 521334),
    ("refs/pull/42/head", 42),
    ("refs/heads/master", None),
    ("master", None),
    ("", None),
    (None, None),
])
def test_pr_id_from_ref(ref, expected):
    assert rdc.pr_id_from_ref(ref) == expected


def test_pr_commit_info():
    pr = {"lastMergeCommit": {"commitId": "m1"},
          "lastMergeSourceCommit": {"commitId": "s1"},
          "lastMergeTargetCommit": {"commitId": "t1"}}
    info = rdc.pr_commit_info(pr)
    assert info == {"merge": "m1", "source": "s1", "target": "t1"}
    assert rdc.pr_commit_info(None) == {"merge": "", "source": "",
                                        "target": ""}


def test_pr_matches_commit():
    pr = {"lastMergeCommit": {"commitId": "AAA"},
          "lastMergeSourceCommit": {"commitId": "BBB"}}
    assert rdc.pr_matches_commit(pr, "aaa") is True
    assert rdc.pr_matches_commit(pr, "BBB") is True
    assert rdc.pr_matches_commit(pr, "ccc") is False
    assert rdc.pr_matches_commit(pr, "") is False
    assert rdc.pr_matches_commit(None, "aaa") is False


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
        "artifact_commit": "9dad7445abcd",
        "artifact_commit_short": "9dad7445",
        "build_commit": "9dad7445abcd", "commit_matches_build": True,
        "component_matches_build_repo": True,
        "pr": None, "pr_ref": "", "pr_url": "", "pr_commit": "",
        "pr_commit_short": "", "pr_commit_matches": False,
        "props_commit": "a16b06c8",
        "props_folder_commit": "a16b06c8", "props_match": True,
        "props_folder": "wms-sys-originalorder",
        "props_folder_mode": "último",
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
    rdc.print_block(_block(pr=pr, pr_url="https://dev.azure.com/o/p/_git/"
                                         "wms-sys-originalorder/pullrequest/42"),
                    "org")
    assert "PR asociado: #42" in buf.getvalue()
    assert "URL Pull Request: https://dev.azure.com/o/p/_git/" \
           "wms-sys-originalorder/pullrequest/42" in buf.getvalue()


def test_print_block_props_desde_folder(monkeypatch):
    """Sin commit de compilacion, Commit Properties muestra el commit
    del folder con su modo (ultimo / a la fecha del release)."""
    buf = _capture_plain(monkeypatch)
    rdc.print_block(_block(props_commit="",
                           props_folder_mode="a la fecha del release"),
                    "org")
    out = buf.getvalue()
    assert "Commit Properties: a16b06c8" in out
    assert "(folder /wms-sys-originalorder, a la fecha del release)" in out


# ═══════════════════════════════════════════════════════════════════════════
# release_block — commit de properties por fecha (rollback)
# ═══════════════════════════════════════════════════════════════════════════
def test_release_block_rollback_commit_por_fecha(monkeypatch):
    """props_date_match=True: toma el commit del folder que coincide con
    la fecha de creacion del release, no el ultimo."""
    folder_log = [
        {"commitId": "n1", "author": {"date": "2026-10-21T10:00:00Z"}},
        {"commitId": "n2", "author": {"date": "2026-10-08T10:00:00Z"}},
        {"commitId": "n3", "author": {"date": "2026-10-05T10:00:00Z"}},
    ]
    seen = {}

    def fake_folder_commits(org, project, rid, path, branch, headers,
                            debug, top=100):
        seen["path"] = path
        return folder_log

    _mock_apis(monkeypatch, props_folder_commit="")
    monkeypatch.setattr(rdc, "folder_commits", fake_folder_commits)
    rel = _release(rel_id=61276, name="Release-39",
                   createdOn="2026-10-07T10:00:00Z",
                   artifacts=[_build_artifact()])
    detail = _release(rel_id=61276, name="Release-39",
                      createdOn="2026-10-07T10:00:00Z",
                      artifacts=[_build_artifact()])
    monkeypatch.setattr(rdc, "get_release_detail",
                        lambda *a, **k: detail)
    # props_repo presente para que consulte el folder
    props = {"id": "props-1", "name": "properties"}
    b = rdc.release_block("o", "p", rel, "cd", {}, props, {}, "master",
                          False, props_date_match=True)
    assert seen["path"] == "/wms-sys-originalorder"
    assert b["props_folder_commit"] == "n3"   # 2026-10-05 <= 10-07
    assert b["props_folder_mode"] == "a la fecha del release"


def test_release_block_install_commit_ultimo(monkeypatch):
    """props_date_match=False (default): toma el ultimo commit del
    folder."""
    folder_log = [
        {"commitId": "n1", "author": {"date": "2026-10-21T10:00:00Z"}},
        {"commitId": "n2", "author": {"date": "2026-10-05T10:00:00Z"}},
    ]
    _mock_apis(monkeypatch, props_folder_commit="")
    monkeypatch.setattr(rdc, "folder_commits",
                        lambda *a, **k: folder_log)
    rel = _release(artifacts=[_build_artifact()])
    b = rdc.release_block("o", "p", rel, "cd", {},
                          {"id": "props-1", "name": "properties"}, {},
                          "master", False)
    assert b["props_folder_commit"] == "n1"
    assert b["props_folder_mode"] == "último"
