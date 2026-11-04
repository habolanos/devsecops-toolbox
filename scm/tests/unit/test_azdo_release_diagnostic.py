# -*- coding: utf-8 -*-
"""Tests unitarios de azdo_release_diagnostic (opción 50)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "azdo"))
import azdo_release_diagnostic as rd  # noqa: E402


# ═════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════════
def _git_artifact(repo="ps-om-com-availability", commit="c2f98ce5",
                  branch="master", alias=None):
    return {"type": "Git", "alias": alias or f"_{repo}",
            "definitionReference": {
                "repository": {"id": "r-1", "name": repo,
                               "url": "https://dev.azure.com/o/p/_git/" + repo},
                "version": {"id": commit},
                "branch": {"id": branch}}}


def _build_artifact(build_id="7001", number="20261024.3",
                    branch="refs/pull/176/merge"):
    return {"type": "Build",
            "definitionReference": {
                "version": {"id": build_id, "name": number},
                "branch": {"id": branch}}}


def _release(rid=62650, name="Release-80", prod_status="notStarted",
             validator=True, variables=None, git_art=None):
    envs = [{"name": "Production", "status": prod_status,
             "deploySteps": []}]
    if validator:
        envs.append({"name": "Validator", "status": "succeeded",
                     "deploySteps": [{"attempt": 1}]})
    return {"id": rid, "name": name, "environments": envs,
            "artifacts": [_build_artifact(),
                          git_art or _git_artifact()],
            "variables": variables or {}}


# ═════════════════════════════════════════════════════════════════════════════
# Artifacts / variables
# ═════════════════════════════════════════════════════════════════════════════
def test_extract_artifacts():
    rel = _release()
    ba, ga = rd.extract_artifacts(rel)
    assert ba["type"] == "Build" and len(ga) == 1


def test_build_artifact_info():
    bi = rd.build_artifact_info(_build_artifact())
    assert bi["build_id"] == "7001"
    assert bi["build_number"] == "20261024.3"
    assert bi["branch"] == "refs/pull/176/merge"


def test_git_artifact_info():
    gi = rd.git_artifact_info(_git_artifact())
    assert gi["repo_name"] == "ps-om-com-availability"
    assert gi["commit"] == "c2f98ce5"
    assert gi["branch"] == "master"


def test_classify_git_artifacts_src_vs_props():
    props = _git_artifact(repo="properties-repo")
    src, pr = rd.classify_git_artifacts(
        [_git_artifact(), props])
    assert src["repo_name"] == "ps-om-com-availability"
    assert pr["repo_name"] == "properties-repo"


def test_release_variables():
    rel = _release(variables={"commitPropertiesRollback":
                              {"value": "e244302b"},
                              "RELEASE_ID": {"value": "63042"}})
    v = rd.release_variables(rel)
    assert v["COMMITPROPERTIESROLLBACK"] == "e244302b"
    assert v["RELEASE_ID"] == "63042"


def test_pr_id_from_build_branch():
    assert rd.pr_id_from_build_branch("refs/pull/176/merge") == 176
    assert rd.pr_id_from_build_branch("refs/pull/5/head") == 5
    assert rd.pr_id_from_build_branch("refs/heads/master") is None


def test_relase_id_matches_rollback():
    assert rd.relase_id_matches_rollback("63042", "Release-9", 63042)
    assert rd.relase_id_matches_rollback("Release-9", "Release-9", 63042)
    assert not rd.relase_id_matches_rollback("123", "Release-9", 63042)


# ═════════════════════════════════════════════════════════════════════════════
# Parsers del log del Validator
# ═════════════════════════════════════════════════════════════════════════════
def test_extract_images_labels():
    text = ("image actual: gcr.io/p/app:1.0.0\n"
            "image nueva: gcr.io/p/app:1.1.0\n")
    img = rd.extract_images_from_log(text)
    assert img["install_image"] == "gcr.io/p/app:1.1.0"
    assert img["prod_image"] == "gcr.io/p/app:1.0.0"


def test_extract_images_env_vars():
    text = ("IMAGE_ACTUAL=us-docker.pkg.dev/x/y:old\n"
            "IMAGE_NUEVA=us-docker.pkg.dev/x/y:new\n")
    img = rd.extract_images_from_log(text)
    assert img["install_image"].endswith(":new")
    assert img["prod_image"].endswith(":old")


def test_extract_images_fallback_hosts():
    text = "aplicando us-docker.pkg.dev/x/y:2.0 y previo us-docker.pkg.dev/x/y:1.0"
    img = rd.extract_images_from_log(text)
    assert "pkg.dev" in img["install_image"]


def test_extract_images_formato_real_validar_images():
    """Formato real del task 'Validar images' (Imagen actual/nueva)."""
    text = (" Imagen actual : artifact.coppel.io/cs/app:2.1.2\n"
            " Imagen nueva  : artifact.coppel.io/cs/app:2.2.0\n")
    img = rd.extract_images_from_log(text)
    assert img["install_image"].endswith(":2.2.0")
    assert img["prod_image"].endswith(":2.1.2")


def test_aggregate_prefiere_patron_explicito_sobre_fallback():
    """Un task de manifest con la imagen actual NO debe ganar sobre el
    'Imagen nueva' explícito de 'Validar images'."""
    texts = [
        ("manifest task", "aplicando artifact.coppel.io/cs/app:2.1.2"),
        ("Validar images",
         " Imagen actual : artifact.coppel.io/cs/app:2.1.2\n"
         " Imagen nueva  : artifact.coppel.io/cs/app:2.2.0\n"),
    ]
    agg = rd.aggregate_validator(texts)
    assert agg["install_image"].endswith(":2.2.0")
    assert agg["prod_image"].endswith(":2.1.2")


def test_extract_images_none():
    assert rd.extract_images_from_log("sin imagenes") == {
        "install_image": "", "prod_image": ""}


def test_extract_excepto():
    assert rd.extract_excepto("excepto a: team-sre") == "team-sre"
    assert rd.extract_excepto("nada") == "N/A"


def test_detect_kubectl_apply():
    assert rd.detect_kubectl_apply("running kubectl apply -f x.yaml")
    assert rd.detect_kubectl_apply("task kubectl-apply terminó")
    assert not rd.detect_kubectl_apply("solo pytest")


def test_extract_props_commit_from_log():
    t1 = "##vso[task.setvariable variable=commitPropertiesRollback]e244302b8"
    assert rd.extract_props_commit_from_log(t1) == "e244302b8"
    t2 = "commitPropertiesRollback=c4e33bf3d"
    assert rd.extract_props_commit_from_log(t2) == "c4e33bf3d"
    assert rd.extract_props_commit_from_log("nada") == ""


def test_aggregate_validator():
    texts = [("t1", "image nueva: gcr.io/p/a:2\nkubectl apply -f m.yaml"),
             ("t2", "image actual: gcr.io/p/a:1\nexcepto a: ops")]
    agg = rd.aggregate_validator(texts)
    assert agg["install_image"] == "gcr.io/p/a:2"
    assert agg["prod_image"] == "gcr.io/p/a:1"
    assert agg["excepto"] == "ops"
    assert agg["kubectl_apply"] is True


# ═════════════════════════════════════════════════════════════════════════════
# Comparativo y folio
# ═════════════════════════════════════════════════════════════════════════════
def _install(props_match=True, relase_id="63042"):
    return {"release_id": 62650, "release_name": "Release-80",
            "component": "ps-om-com-availability",
            "build_id": "7001", "build_number": "20261024.3",
            "git_commit": "c2f98ce584e9ad4dbac94c0ebedc8f2f93e597f2",
            "git_branch": "master",
            "repo_url": "https://dev.azure.com/o/p/_git/ps-om-com-availability",
            "props_artifact_commit": "",
            "props_commit_var": "e244302b8646",
            "relase_id_var": relase_id,
            "url": "https://dev.azure.com/o/p/_releaseProgress?releaseId=62650",
            "stages": [("Validator", "succeeded"),
                       ("Production", "notStarted")],
            "pr": {"pullRequestId": 176},
            "pr_commit": "c2f98ce584e9ad4dbac94c0ebedc8f2f93e597f2",
            "pr_matches": True,
            "validator_ran": True, "validator_errors": [],
            "install_image": "gcr.io/p/a:2", "prod_image": "gcr.io/p/a:1",
            "excepto": "N/A", "kubectl_apply": True,
            "props_commit_log": "",
            "props_folder_commit": "e244302b8646",
            "props_folder_path": "ps-om-com-availability",
            "props_commit": "e244302b8646",
            "props_match": props_match,
            "props_evaluable": True}


def _rollback():
    return {"release_id": 63042, "release_name": "Release-9",
            "component": "di-wms-capacityenabling",
            "build_id": "7002", "build_number": "20261025.2",
            "git_commit": "b933814d60755b37926011a9ed84fe22eb89cf94",
            "props_commit_var": "c4e33bf3db",
            "props_commit": "c4e33bf3db",
            "props_commit_log": "",
            "props_folder_commit": "c4e33bf3db",
            "props_folder_path": "di-wms-capacityenabling",
            "props_match": True,
            "relase_id_var": "",
            "url": "https://dev.azure.com/o/p/_releaseProgress?releaseId=63042",
            "stages": [("Validator", "succeeded")],
            "pr": None, "pr_commit": "", "pr_matches": False,
            "install_image": "", "prod_image": "",
            "excepto": "N/A", "kubectl_apply": False,
            "validator_ran": True, "validator_errors": []}


def test_build_checks_all_ok():
    checks = rd.build_checks(_install(), _rollback())
    pr_c = next(c for c in checks
                if c["check"].startswith("Artifact Git Source"))
    assert pr_c["ok"] is True
    props_c = next(c for c in checks
                   if c["check"].startswith("commitProperties"))
    assert props_c["ok"] is True
    rid_c = next(c for c in checks if c["check"].startswith("RELEASE_ID"))
    assert rid_c["ok"] is True


def test_build_checks_props_mismatch():
    i = _install(props_match=False)
    checks = rd.build_checks(i, _rollback())
    props_c = next(c for c in checks
                   if c["check"].startswith("commitProperties"))
    assert props_c["ok"] is False


def test_check_props_no_evaluable_sin_folder_commit():
    """Folder sin commits → N/A, no ✘."""
    i = _install()
    i["props_evaluable"] = False
    i["props_folder_commit"] = ""
    checks = rd.build_checks(i, _rollback())
    c = next(c for c in checks
             if c["check"].startswith("commitProperties"))
    assert c["ok"] is None
    assert "sin commits" in c["detail"]


def test_check_imagen_misma_en_install_y_prod_no_falla():
    """install==prod (fallback del regex) → N/A, no ✘."""
    i = _install()
    i["prod_image"] = i["install_image"]
    checks = rd.build_checks(i, _rollback())
    c = next(c for c in checks if c["check"].startswith("Imagen"))
    assert c["ok"] is None
    assert "misma imagen" in c["detail"]


def test_check_imagen_sin_prod_no_falla():
    i = _install()
    i["prod_image"] = ""
    checks = rd.build_checks(i, _rollback())
    c = next(c for c in checks if c["check"].startswith("Imagen"))
    assert c["ok"] is None


def test_verdict():
    checks_ok = rd.build_checks(_install(), _rollback())
    ok, n = rd.verdict(checks_ok)
    assert ok is True and n == 0
    checks_bad = rd.build_checks(_install(props_match=False), _rollback())
    ok2, n2 = rd.verdict(checks_bad)
    assert ok2 is False and n2 == 1


def test_build_folio_formato():
    folio = rd.build_folio(_install(), _rollback())
    assert "Componente: ps-om-com-availability" in folio
    assert "* Release: Release-80" in folio
    assert "releaseId=62650" in folio
    assert "* Commit: c2f98ce584e9ad4dbac94c0ebedc8f2f93e597f2" in folio
    assert "* Version Build: 20261024.3" in folio
    assert "* Commit properties deploy: e244302b8646" in folio
    assert "* Folio PR master : N/A" in folio
    assert "Componente: di-wms-capacityenabling" in folio
    assert "• Release Rollback Release-9" in folio
    assert "releaseId=63042" in folio
    assert "• Commit Rollback Release: b933814d60755b37926011a9ed84fe22eb89cf94" in folio
    assert "• Commit properties Rollback : c4e33bf3db" in folio
    assert "kubectl apply se cambia el comando apply por delete" in folio


def test_build_folio_sin_rollback_release0():
    folio = rd.build_folio(_install(), None)
    assert "estrategia release 0" in folio
    assert "• Release Rollback N/A" in folio


def test_build_folio_sin_kubectl():
    i = _install()
    i["kubectl_apply"] = False
    folio = rd.build_folio(i, _rollback())
    assert "kubectl apply se cambia" not in folio


def test_export_check_rows():
    rows = rd.export_check_rows(rd.build_checks(_install(), _rollback()))
    assert all("resultado" in r and "check" in r for r in rows)
    assert any(r["resultado"] == "OK" for r in rows)


def test_vsrm_and_helpers():
    assert rd.vsrm("https://dev.azure.com/o") == \
        "https://vsrm.dev.azure.com/o"
    assert rd._short("abcdef12345", 6) == "abcdef"
    assert rd.stage_env(_release(), "Validator") is not None
    assert rd.stage_env(_release(), "Nope") is None
