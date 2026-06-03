#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_azdo_repo_branch_diff.py

Pruebas unitarias para azdo_repo_branch_diff.py

Cubre:
  - classify_file: clasificación de archivos por riesgo y categoría
  - BranchDiffReport._calc_impact: cálculo del score de impacto
  - BranchDiffReport.category_stats: agrupación por categoría
  - BranchDiffReport.author_stats: agrupación por autor
  - BranchDiffReport._max_risk: nivel de riesgo máximo
  - FileChange.to_dict / CommitInfo.to_dict: serialización
  - _build_recommendations: generación de recomendaciones
  - analyze_branches: integración con mocks de API
  - make_headers: autenticación HTTP
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from azdo_repo_branch_diff import (
    RISK_CRITICAL, RISK_HIGH, RISK_MEDIUM, RISK_LOW, RISK_NONE,
    CHANGE_ADD, CHANGE_DELETE, CHANGE_EDIT,
    FileChange, CommitInfo, BranchDiffReport,
    classify_file,
    _normalize_change_type,
    _build_recommendations,
    analyze_branches,
    make_headers,
)


# ═══════════════════════════════════════════════════════════════════════════════
# classify_file
# ═══════════════════════════════════════════════════════════════════════════════
class TestClassifyFile(unittest.TestCase):

    # CRITICAL — CI/CD
    def test_dockerfile_is_critical_cicd(self):
        risk, cat = classify_file("/app/Dockerfile")
        self.assertEqual(risk, RISK_CRITICAL)
        self.assertEqual(cat, "cicd")

    def test_docker_compose_is_critical_cicd(self):
        risk, cat = classify_file("/docker-compose.yml")
        self.assertEqual(risk, RISK_CRITICAL)
        self.assertEqual(cat, "cicd")

    def test_azure_pipelines_is_critical_cicd(self):
        risk, cat = classify_file("/azure-pipelines.yml")
        self.assertEqual(risk, RISK_CRITICAL)
        self.assertEqual(cat, "cicd")

    def test_github_workflow_is_critical_cicd(self):
        risk, cat = classify_file("/.github/workflows/ci.yml")
        self.assertEqual(risk, RISK_CRITICAL)
        self.assertEqual(cat, "cicd")

    def test_jenkinsfile_is_critical_cicd(self):
        risk, cat = classify_file("/Jenkinsfile")
        self.assertEqual(risk, RISK_CRITICAL)
        self.assertEqual(cat, "cicd")

    # CRITICAL — Seguridad
    def test_pem_file_is_critical_security(self):
        risk, cat = classify_file("/certs/server.pem")
        self.assertEqual(risk, RISK_CRITICAL)
        self.assertEqual(cat, "security")

    def test_key_file_is_critical_security(self):
        risk, cat = classify_file("/infra/private.key")
        self.assertEqual(risk, RISK_CRITICAL)
        self.assertEqual(cat, "security")

    def test_secret_config_is_critical_security(self):
        risk, cat = classify_file("/config/secrets.yml")
        self.assertEqual(risk, RISK_CRITICAL)
        self.assertEqual(cat, "security")

    # CRITICAL — Infra
    def test_k8s_manifest_is_critical_infra(self):
        risk, cat = classify_file("/k8s/deployment.yaml")
        self.assertEqual(risk, RISK_CRITICAL)
        self.assertEqual(cat, "infra")

    def test_helm_chart_is_critical_infra(self):
        risk, cat = classify_file("/helm/values.yaml")
        self.assertEqual(risk, RISK_CRITICAL)
        self.assertEqual(cat, "infra")

    # HIGH — Build
    def test_pom_is_high_build(self):
        risk, cat = classify_file("/pom.xml")
        self.assertEqual(risk, RISK_HIGH)
        self.assertEqual(cat, "build")

    def test_package_json_is_high_build(self):
        risk, cat = classify_file("/package.json")
        self.assertEqual(risk, RISK_HIGH)
        self.assertEqual(cat, "build")

    def test_requirements_txt_is_high_build(self):
        risk, cat = classify_file("/requirements.txt")
        self.assertEqual(risk, RISK_HIGH)
        self.assertEqual(cat, "build")

    # HIGH — Base de datos
    def test_sql_migration_is_high_database(self):
        risk, cat = classify_file("/db/migration/V1__create_table.sql")
        self.assertEqual(risk, RISK_HIGH)
        self.assertEqual(cat, "database")

    def test_flyway_is_high_database(self):
        risk, cat = classify_file("/src/main/resources/flyway/V2__alter_column.sql")
        self.assertEqual(risk, RISK_HIGH)
        self.assertEqual(cat, "database")

    # HIGH — Config
    def test_application_yml_is_high_config(self):
        risk, cat = classify_file("/src/main/resources/application.yml")
        self.assertEqual(risk, RISK_HIGH)
        self.assertEqual(cat, "config")

    def test_application_properties_is_high_config(self):
        risk, cat = classify_file("/src/main/resources/application-prod.properties")
        self.assertEqual(risk, RISK_HIGH)
        self.assertEqual(cat, "config")

    # MEDIUM — Código
    def test_java_is_medium_code(self):
        risk, cat = classify_file("/src/main/java/com/example/Service.java")
        self.assertEqual(risk, RISK_MEDIUM)
        self.assertEqual(cat, "code")

    def test_python_is_medium_code(self):
        risk, cat = classify_file("/scripts/deploy.py")
        self.assertEqual(risk, RISK_MEDIUM)
        self.assertEqual(cat, "code")

    def test_typescript_is_medium_code(self):
        risk, cat = classify_file("/src/app/component.ts")
        self.assertEqual(risk, RISK_MEDIUM)
        self.assertEqual(cat, "code")

    # LOW — Tests
    def test_java_test_is_low_test(self):
        risk, cat = classify_file("/src/test/java/com/example/ServiceTest.java")
        self.assertEqual(risk, RISK_LOW)
        self.assertEqual(cat, "test")

    def test_spec_file_is_low_test(self):
        risk, cat = classify_file("/spec/unit/service_spec.rb")
        self.assertEqual(risk, RISK_LOW)
        self.assertEqual(cat, "test")

    # LOW — Docs
    def test_readme_is_low_docs(self):
        risk, cat = classify_file("/README.md")
        self.assertEqual(risk, RISK_LOW)
        self.assertEqual(cat, "docs")

    def test_txt_is_low_docs(self):
        risk, cat = classify_file("/docs/notes.txt")
        self.assertEqual(risk, RISK_LOW)
        self.assertEqual(cat, "docs")

    # NONE — otros
    def test_unknown_extension_is_none_other(self):
        risk, cat = classify_file("/data/output.xyz")
        self.assertEqual(risk, RISK_NONE)
        self.assertEqual(cat, "other")


# ═══════════════════════════════════════════════════════════════════════════════
# FileChange
# ═══════════════════════════════════════════════════════════════════════════════
class TestFileChange(unittest.TestCase):

    def test_filename_extracted(self):
        fc = FileChange("/src/main/java/Service.java", CHANGE_EDIT)
        self.assertEqual(fc.filename, "Service.java")

    def test_ext_extracted(self):
        fc = FileChange("/src/config.yml", CHANGE_ADD)
        self.assertEqual(fc.ext, ".yml")

    def test_to_dict_keys(self):
        fc = FileChange("/pom.xml", CHANGE_DELETE)
        d  = fc.to_dict()
        for k in ("path", "filename", "ext", "change_type", "risk", "category"):
            self.assertIn(k, d)

    def test_pom_xml_classified_correctly(self):
        fc = FileChange("/pom.xml", CHANGE_EDIT)
        self.assertEqual(fc.risk, RISK_HIGH)
        self.assertEqual(fc.category, "build")


# ═══════════════════════════════════════════════════════════════════════════════
# CommitInfo
# ═══════════════════════════════════════════════════════════════════════════════
class TestCommitInfo(unittest.TestCase):

    def test_short_sha(self):
        c = CommitInfo("abcdef1234567890", "dev", "2026-06-01T10:00:00Z", "Fix bug")
        self.assertEqual(c.short_sha, "abcdef12")

    def test_message_truncated(self):
        long_msg = "A" * 200
        c = CommitInfo("abc", "dev", "", long_msg)
        self.assertLessEqual(len(c.message), 80)

    def test_multiline_message_first_line(self):
        c = CommitInfo("abc", "dev", "", "First line\nSecond line\nThird")
        self.assertEqual(c.message, "First line")

    def test_to_dict_keys(self):
        c = CommitInfo("abcdef1234567890", "alice", "2026-06-01", "feat: add")
        d = c.to_dict()
        for k in ("sha", "author", "date", "message"):
            self.assertIn(k, d)


# ═══════════════════════════════════════════════════════════════════════════════
# BranchDiffReport
# ═══════════════════════════════════════════════════════════════════════════════
def _make_report(files=None, commits=None, ahead=5, behind=0):
    return BranchDiffReport(
        repo_name="test-repo", source_branch="feature", target_branch="master",
        ahead_count=ahead, behind_count=behind, common_commit="abc123",
        files=files or [], commits=commits or [],
        generated_at="2026-06-03 15:00:00 CST",
    )


class TestBranchDiffReport(unittest.TestCase):

    def test_max_risk_empty_is_none(self):
        r = _make_report()
        self.assertEqual(r.max_risk, RISK_NONE)

    def test_max_risk_single_critical(self):
        r = _make_report(files=[FileChange("/Dockerfile", CHANGE_EDIT)])
        self.assertEqual(r.max_risk, RISK_CRITICAL)

    def test_max_risk_mixed_returns_highest(self):
        files = [
            FileChange("/README.md", CHANGE_EDIT),
            FileChange("/pom.xml", CHANGE_EDIT),
            FileChange("/Dockerfile", CHANGE_EDIT),
        ]
        r = _make_report(files=files)
        self.assertEqual(r.max_risk, RISK_CRITICAL)

    def test_impact_score_zero_no_files(self):
        r = _make_report(ahead=0)
        self.assertEqual(r.impact_score, 0)

    def test_impact_score_increases_with_risk(self):
        r_low  = _make_report(files=[FileChange("/README.md", CHANGE_EDIT)], ahead=1)
        r_crit = _make_report(files=[FileChange("/Dockerfile", CHANGE_EDIT)], ahead=1)
        self.assertGreater(r_crit.impact_score, r_low.impact_score)

    def test_impact_score_max_100(self):
        files = [FileChange("/Dockerfile", CHANGE_EDIT)] * 20
        r = _make_report(files=files, ahead=500)
        self.assertLessEqual(r.impact_score, 100)

    def test_impact_score_min_0(self):
        r = _make_report(files=[], ahead=0)
        self.assertGreaterEqual(r.impact_score, 0)

    def test_category_stats_grouped(self):
        files = [
            FileChange("/Service.java", CHANGE_EDIT),
            FileChange("/Controller.java", CHANGE_ADD),
            FileChange("/pom.xml", CHANGE_EDIT),
        ]
        r     = _make_report(files=files)
        stats = r.category_stats()
        self.assertIn("code",  stats)
        self.assertIn("build", stats)
        self.assertEqual(stats["code"]["count"], 2)
        self.assertEqual(stats["build"]["count"], 1)

    def test_category_stats_counts_change_types(self):
        files = [
            FileChange("/A.java", CHANGE_ADD),
            FileChange("/B.java", CHANGE_DELETE),
        ]
        r     = _make_report(files=files)
        stats = r.category_stats()
        self.assertEqual(stats["code"][CHANGE_ADD], 1)
        self.assertEqual(stats["code"][CHANGE_DELETE], 1)

    def test_author_stats_counts_correctly(self):
        commits = [
            CommitInfo("a1", "alice", "2026-06-01", "feat"),
            CommitInfo("a2", "alice", "2026-06-02", "fix"),
            CommitInfo("b1", "bob",   "2026-06-01", "feat"),
        ]
        r = _make_report(commits=commits)
        a = r.author_stats()
        alice = next(x for x in a if x["author"] == "alice")
        bob   = next(x for x in a if x["author"] == "bob")
        self.assertEqual(alice["commits"], 2)
        self.assertEqual(bob["commits"], 1)

    def test_author_stats_sorted_by_commits(self):
        commits = [
            CommitInfo("a", "alice", "", "m"),
            CommitInfo("b", "bob",   "", "m"),
            CommitInfo("c", "bob",   "", "m"),
        ]
        r = _make_report(commits=commits)
        a = r.author_stats()
        self.assertEqual(a[0]["author"], "bob")

    def test_to_dict_structure(self):
        r = _make_report(
            files=[FileChange("/Service.java", CHANGE_EDIT)],
            commits=[CommitInfo("abc123", "alice", "2026-06-01", "feat")],
        )
        d = r.to_dict()
        for k in ("repo", "source_branch", "target_branch", "ahead_count",
                  "impact_score", "max_risk", "files", "commits"):
            self.assertIn(k, d)
        self.assertIsInstance(d["files"], list)
        self.assertIsInstance(d["commits"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# _build_recommendations
# ═══════════════════════════════════════════════════════════════════════════════
class TestBuildRecommendations(unittest.TestCase):

    def test_critical_file_triggers_review_recommendation(self):
        r    = _make_report(files=[FileChange("/Dockerfile", CHANGE_EDIT)])
        recs = _build_recommendations(r)
        self.assertTrue(any("Revisión obligatoria" in rec for rec in recs))

    def test_security_file_triggers_audit_recommendation(self):
        r    = _make_report(files=[FileChange("/config/secrets.yml", CHANGE_EDIT)])
        recs = _build_recommendations(r)
        self.assertTrue(any("Auditoría de seguridad" in rec for rec in recs))

    def test_database_triggers_maintenance_window(self):
        r    = _make_report(files=[FileChange("/db/migration/V1.sql", CHANGE_ADD)])
        recs = _build_recommendations(r)
        self.assertTrue(any("ventana de mantenimiento" in rec for rec in recs))

    def test_build_file_triggers_vulnerability_scan(self):
        r    = _make_report(files=[FileChange("/pom.xml", CHANGE_EDIT)])
        recs = _build_recommendations(r)
        self.assertTrue(any("vulnerabilidades" in rec for rec in recs))

    def test_behind_commits_triggers_merge_recommendation(self):
        r    = _make_report(files=[], behind=3)
        recs = _build_recommendations(r)
        self.assertTrue(any("atrás" in rec for rec in recs))

    def test_many_files_triggers_incremental_recommendation(self):
        files = [FileChange(f"/src/File{i}.java", CHANGE_EDIT) for i in range(55)]
        r     = _make_report(files=files)
        recs  = _build_recommendations(r)
        self.assertTrue(any("incremental" in rec for rec in recs))

    def test_no_issues_returns_ok_message(self):
        r    = _make_report(files=[FileChange("/README.md", CHANGE_EDIT)])
        recs = _build_recommendations(r)
        self.assertTrue(any("Sin hallazgos críticos" in rec for rec in recs))

    def test_recommendations_are_nonempty_list(self):
        r    = _make_report()
        recs = _build_recommendations(r)
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)


# ═══════════════════════════════════════════════════════════════════════════════
# _normalize_change_type
# ═══════════════════════════════════════════════════════════════════════════════
class TestNormalizeChangeType(unittest.TestCase):

    def test_add(self):
        self.assertEqual(_normalize_change_type("sourceAdd"), CHANGE_ADD)
        self.assertEqual(_normalize_change_type("add"),       CHANGE_ADD)

    def test_delete(self):
        self.assertEqual(_normalize_change_type("delete"),    CHANGE_DELETE)
        self.assertEqual(_normalize_change_type("DELETE"),    CHANGE_DELETE)

    def test_edit_default(self):
        self.assertEqual(_normalize_change_type("edit"),      CHANGE_EDIT)
        self.assertEqual(_normalize_change_type("unknown"),   CHANGE_EDIT)


# ═══════════════════════════════════════════════════════════════════════════════
# make_headers
# ═══════════════════════════════════════════════════════════════════════════════
class TestMakeHeaders(unittest.TestCase):

    def test_basic_auth_header(self):
        h = make_headers("my-pat")
        self.assertIn("Authorization", h)
        self.assertTrue(h["Authorization"].startswith("Basic "))

    def test_accept_json(self):
        h = make_headers("t")
        self.assertEqual(h["Accept"], "application/json")


# ═══════════════════════════════════════════════════════════════════════════════
# analyze_branches (integración con mocks)
# ═══════════════════════════════════════════════════════════════════════════════
class TestAnalyzeBranches(unittest.TestCase):

    def _fake_headers(self):
        return make_headers("fake")

    @patch("azdo_repo_branch_diff.get_commits_ahead")
    @patch("azdo_repo_branch_diff.get_branch_diff_raw")
    def test_report_built_from_api_data(self, mock_diff, mock_commits):
        mock_diff.return_value = {
            "aheadCount": 3, "behindCount": 0, "commonCommit": "abc",
            "changes": [
                {"changeType": "edit", "item": {"path": "/pom.xml",   "gitObjectType": "blob"}},
                {"changeType": "add",  "item": {"path": "/Dockerfile", "gitObjectType": "blob"}},
            ],
        }
        mock_commits.return_value = [
            {"commitId": "111", "author": {"name": "alice", "date": "2026-06-01"},
             "comment": "feat: add CI"},
            {"commitId": "222", "author": {"name": "bob",   "date": "2026-06-02"},
             "comment": "fix: pom"},
        ]
        r = analyze_branches(
            "https://org", "proj", "repo-id", "test-repo",
            "feature", "master",
            self._fake_headers(), False, None, "America/Mazatlan",
        )
        self.assertEqual(r.ahead_count, 3)
        self.assertEqual(len(r.files), 2)
        self.assertEqual(len(r.commits), 2)
        self.assertEqual(r.max_risk, RISK_CRITICAL)  # Dockerfile es CRITICAL

    @patch("azdo_repo_branch_diff.get_commits_ahead")
    @patch("azdo_repo_branch_diff.get_branch_diff_raw")
    def test_empty_diff_produces_empty_report(self, mock_diff, mock_commits):
        mock_diff.return_value   = {"aheadCount": 0, "behindCount": 0, "changes": []}
        mock_commits.return_value = []
        r = analyze_branches(
            "https://org", "proj", "repo-id", "test-repo",
            "feature", "master",
            self._fake_headers(), False, None, "America/Mazatlan",
        )
        self.assertEqual(len(r.files), 0)
        self.assertEqual(r.max_risk, RISK_NONE)
        self.assertEqual(r.impact_score, 0)

    @patch("azdo_repo_branch_diff.get_commits_ahead")
    @patch("azdo_repo_branch_diff.get_branch_diff_raw")
    def test_tree_items_excluded(self, mock_diff, mock_commits):
        mock_diff.return_value = {
            "aheadCount": 1, "behindCount": 0, "changes": [
                {"changeType": "edit", "item": {"path": "/src", "gitObjectType": "tree"}},
                {"changeType": "edit", "item": {"path": "/src/Main.java", "gitObjectType": "blob"}},
            ],
        }
        mock_commits.return_value = []
        r = analyze_branches(
            "https://org", "proj", "repo-id", "test-repo",
            "feature", "master",
            self._fake_headers(), False, None, "America/Mazatlan",
        )
        self.assertEqual(len(r.files), 1)
        self.assertEqual(r.files[0].path, "/src/Main.java")

    @patch("azdo_repo_branch_diff.get_commits_ahead")
    @patch("azdo_repo_branch_diff.get_branch_diff_raw")
    def test_api_failure_returns_empty_report(self, mock_diff, mock_commits):
        mock_diff.return_value    = {}
        mock_commits.return_value = []
        r = analyze_branches(
            "https://org", "proj", "repo-id", "test-repo",
            "feature", "master",
            self._fake_headers(), False, None, "America/Mazatlan",
        )
        self.assertEqual(r.files, [])
        self.assertEqual(r.commits, [])

    @patch("azdo_repo_branch_diff.get_commits_ahead")
    @patch("azdo_repo_branch_diff.get_branch_diff_raw")
    def test_behind_count_captured(self, mock_diff, mock_commits):
        mock_diff.return_value   = {"aheadCount": 2, "behindCount": 5, "changes": []}
        mock_commits.return_value = []
        r = analyze_branches(
            "https://org", "proj", "repo-id", "repo",
            "source", "target",
            self._fake_headers(), False, None, "America/Mazatlan",
        )
        self.assertEqual(r.behind_count, 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
