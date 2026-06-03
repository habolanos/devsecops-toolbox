#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_azdo_properties_branch_diff.py

Pruebas unitarias para azdo_properties_branch_diff.py

Cubre:
  - build_unified_diff: generación de diff y conteo de líneas
  - classify_diff_content: detección de cambios funcionales vs formato
  - FileDiff.to_dict: serialización del modelo
  - _normalize_change_type: normalización de tipos de cambio
  - _initial_severity: severidad inicial por tipo de cambio
  - _analyze_by_items (lógica interna con mocks de API)
"""

import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Asegurar que el módulo es importable desde el mismo directorio
sys.path.insert(0, str(Path(__file__).parent))

from azdo_properties_branch_diff import (
    FileDiff,
    SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM, SEV_LOW, SEV_NONE,
    CHANGE_ADD, CHANGE_DELETE, CHANGE_EDIT, CHANGE_RENAME, CHANGE_NONE,
    build_unified_diff,
    classify_diff_content,
    _normalize_change_type,
    _initial_severity,
    analyze_component,
    get_branch_diffs,
    get_items_in_path,
    get_file_content,
    make_headers,
)


# ═══════════════════════════════════════════════════════════════════════════════
# build_unified_diff
# ═══════════════════════════════════════════════════════════════════════════════
class TestBuildUnifiedDiff(unittest.TestCase):

    def test_identical_content_no_diff(self):
        content = "spring:\n  datasource:\n    url: jdbc:postgresql://db:5432/app\n"
        diff, added, removed = build_unified_diff(content, content, "application.yml",
                                                  "source", "target")
        self.assertEqual(diff, [])
        self.assertEqual(added, 0)
        self.assertEqual(removed, 0)

    def test_add_line_diff(self):
        old = "spring:\n  port: 8080\n"
        new = "spring:\n  port: 8080\n  timeout: 30\n"
        diff, added, removed = build_unified_diff(new, old, "app.yml", "src", "tgt")
        self.assertGreater(added, 0)
        self.assertEqual(removed, 0)
        self.assertTrue(any(l.startswith("+") and "timeout" in l for l in diff))

    def test_remove_line_diff(self):
        old = "key1: val1\nkey2: val2\n"
        new = "key1: val1\n"
        diff, added, removed = build_unified_diff(new, old, "cfg.yml", "src", "tgt")
        self.assertEqual(added, 0)
        self.assertGreater(removed, 0)

    def test_both_none_no_diff(self):
        diff, added, removed = build_unified_diff(None, None, "file.yml", "src", "tgt")
        self.assertEqual(diff, [])
        self.assertEqual(added, 0)
        self.assertEqual(removed, 0)

    def test_new_file_source_only(self):
        new = "server:\n  port: 9090\n"
        diff, added, removed = build_unified_diff(new, None, "new.yml", "src", "tgt")
        # All lines in new are additions
        self.assertGreater(added, 0)
        self.assertEqual(removed, 0)

    def test_deleted_file_target_only(self):
        old = "legacy:\n  key: value\n"
        diff, added, removed = build_unified_diff(None, old, "old.yml", "src", "tgt")
        self.assertEqual(added, 0)
        self.assertGreater(removed, 0)

    def test_context_lines(self):
        content_a = "\n".join(f"line{i}: value{i}" for i in range(20)) + "\n"
        content_b = content_a.replace("value10", "CHANGED")
        diff, _, _ = build_unified_diff(content_b, content_a, "f.yml", "s", "t", context=2)
        hunk_headers = [l for l in diff if l.startswith("@@")]
        self.assertTrue(len(hunk_headers) >= 1)


# ═══════════════════════════════════════════════════════════════════════════════
# classify_diff_content
# ═══════════════════════════════════════════════════════════════════════════════
class TestClassifyDiffContent(unittest.TestCase):

    def _make_diff(self, added_lines, removed_lines):
        """Helper: genera líneas de diff simples para testing."""
        lines = ["--- old", "+++ new"]
        for l in removed_lines:
            lines.append(f"-{l}")
        for l in added_lines:
            lines.append(f"+{l}")
        return lines

    def test_only_comments_is_low(self):
        diff = self._make_diff(
            ["# nuevo comentario"],
            ["# viejo comentario"],
        )
        self.assertEqual(classify_diff_content(diff), SEV_LOW)

    def test_only_whitespace_is_low(self):
        diff = self._make_diff(["   "], [""])
        self.assertEqual(classify_diff_content(diff), SEV_LOW)

    def test_functional_change_is_high(self):
        diff = self._make_diff(
            ["spring.datasource.url=jdbc:postgresql://new-db:5432/app"],
            ["spring.datasource.url=jdbc:postgresql://old-db:5432/app"],
        )
        self.assertEqual(classify_diff_content(diff), SEV_HIGH)

    def test_mixed_comment_and_value_is_high(self):
        diff = self._make_diff(
            ["# updated url", "url: new-value"],
            ["# old url", "url: old-value"],
        )
        self.assertEqual(classify_diff_content(diff), SEV_HIGH)

    def test_empty_diff_is_low(self):
        self.assertEqual(classify_diff_content([]), SEV_LOW)

    def test_header_lines_excluded(self):
        diff = ["--- file_old", "+++ file_new", " context line"]
        self.assertEqual(classify_diff_content(diff), SEV_LOW)


# ═══════════════════════════════════════════════════════════════════════════════
# _normalize_change_type
# ═══════════════════════════════════════════════════════════════════════════════
class TestNormalizeChangeType(unittest.TestCase):

    def test_add(self):
        self.assertEqual(_normalize_change_type("add"),         CHANGE_ADD)
        self.assertEqual(_normalize_change_type("Add"),         CHANGE_ADD)
        self.assertEqual(_normalize_change_type("sourceAdd"),   CHANGE_ADD)

    def test_delete(self):
        self.assertEqual(_normalize_change_type("delete"),      CHANGE_DELETE)
        self.assertEqual(_normalize_change_type("DELETE"),      CHANGE_DELETE)

    def test_rename(self):
        self.assertEqual(_normalize_change_type("rename"),      CHANGE_RENAME)
        self.assertEqual(_normalize_change_type("sourceRename"),CHANGE_RENAME)

    def test_edit_default(self):
        self.assertEqual(_normalize_change_type("edit"),        CHANGE_EDIT)
        self.assertEqual(_normalize_change_type("unknown"),     CHANGE_EDIT)
        self.assertEqual(_normalize_change_type(""),            CHANGE_EDIT)


# ═══════════════════════════════════════════════════════════════════════════════
# _initial_severity
# ═══════════════════════════════════════════════════════════════════════════════
class TestInitialSeverity(unittest.TestCase):

    def test_delete_is_critical(self):
        self.assertEqual(_initial_severity(CHANGE_DELETE), SEV_CRITICAL)

    def test_add_is_medium(self):
        self.assertEqual(_initial_severity(CHANGE_ADD), SEV_MEDIUM)

    def test_edit_is_high(self):
        self.assertEqual(_initial_severity(CHANGE_EDIT), SEV_HIGH)

    def test_rename_is_high(self):
        self.assertEqual(_initial_severity(CHANGE_RENAME), SEV_HIGH)


# ═══════════════════════════════════════════════════════════════════════════════
# FileDiff
# ═══════════════════════════════════════════════════════════════════════════════
class TestFileDiff(unittest.TestCase):

    def _make(self, path="/comp/application.yml", change_type=CHANGE_EDIT,
              severity=SEV_HIGH, added=2, removed=1):
        return FileDiff(
            path=path,
            change_type=change_type,
            severity=severity,
            diff_lines=["--- old", "+++ new", "-old: val", "+new: val"],
            lines_added=added,
            lines_removed=removed,
            source_content="new: val\n",
            target_content="old: val\n",
        )

    def test_filename_extracted(self):
        fd = self._make(path="/comp/sub/file.yml")
        self.assertEqual(fd.filename, "file.yml")

    def test_filename_root(self):
        fd = self._make(path="/application.yml")
        self.assertEqual(fd.filename, "application.yml")

    def test_to_dict_keys(self):
        fd = self._make()
        d  = fd.to_dict()
        for key in ("path", "filename", "change_type", "severity",
                    "lines_added", "lines_removed", "diff"):
            self.assertIn(key, d)

    def test_to_dict_values(self):
        fd = self._make(added=3, removed=2)
        d  = fd.to_dict()
        self.assertEqual(d["lines_added"],   3)
        self.assertEqual(d["lines_removed"], 2)
        self.assertEqual(d["severity"],      SEV_HIGH)
        self.assertEqual(d["change_type"],   CHANGE_EDIT)

    def test_to_dict_diff_joined(self):
        fd = self._make()
        d  = fd.to_dict()
        self.assertIn("---", d["diff"])
        self.assertIn("+++", d["diff"])

    def test_to_dict_empty_diff(self):
        fd = FileDiff(
            path="/comp/f.yml", change_type=CHANGE_NONE, severity=SEV_NONE,
            diff_lines=[], lines_added=0, lines_removed=0,
            source_content="same\n", target_content="same\n",
        )
        d = fd.to_dict()
        self.assertEqual(d["diff"], "")


# ═══════════════════════════════════════════════════════════════════════════════
# analyze_component (integración con mocks)
# ═══════════════════════════════════════════════════════════════════════════════
class TestAnalyzeComponent(unittest.TestCase):

    def _fake_headers(self):
        return make_headers("fake-token")

    @patch("azdo_properties_branch_diff.get_branch_diffs")
    @patch("azdo_properties_branch_diff.get_file_content")
    def test_edit_detected_high(self, mock_content, mock_diffs):
        mock_diffs.return_value = [{
            "changeType": "edit",
            "item": {"path": "/comp/application.yml"},
        }]
        mock_content.side_effect = lambda *a, **kw: (
            "url: jdbc:postgresql://NEW:5432/db\n"
            if a[4] == "source" else
            "url: jdbc:postgresql://OLD:5432/db\n"
        )
        results = analyze_component(
            "https://org", "proj", "repo-id",
            "/comp", "source", "target",
            self._fake_headers(), 3, False, None,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].change_type, CHANGE_EDIT)
        self.assertEqual(results[0].severity, SEV_HIGH)

    @patch("azdo_properties_branch_diff.get_branch_diffs")
    @patch("azdo_properties_branch_diff.get_file_content")
    def test_delete_detected_critical(self, mock_content, mock_diffs):
        mock_diffs.return_value = [{
            "changeType": "delete",
            "item": {"path": "/comp/secrets.yml"},
        }]
        mock_content.return_value = "secret: mysecret\n"
        results = analyze_component(
            "https://org", "proj", "repo-id",
            "/comp", "source", "target",
            self._fake_headers(), 3, False, None,
        )
        self.assertEqual(results[0].severity, SEV_CRITICAL)
        self.assertEqual(results[0].change_type, CHANGE_DELETE)

    @patch("azdo_properties_branch_diff.get_branch_diffs")
    @patch("azdo_properties_branch_diff.get_file_content")
    def test_add_detected_medium(self, mock_content, mock_diffs):
        mock_diffs.return_value = [{
            "changeType": "add",
            "item": {"path": "/comp/newfeature.yml"},
        }]
        mock_content.return_value = "feature:\n  enabled: true\n"
        results = analyze_component(
            "https://org", "proj", "repo-id",
            "/comp", "source", "target",
            self._fake_headers(), 3, False, None,
        )
        self.assertEqual(results[0].severity, SEV_MEDIUM)
        self.assertEqual(results[0].change_type, CHANGE_ADD)

    @patch("azdo_properties_branch_diff.get_branch_diffs")
    @patch("azdo_properties_branch_diff.get_items_in_path")
    @patch("azdo_properties_branch_diff.get_file_content")
    def test_fallback_to_items_when_diffs_empty(
        self, mock_content, mock_items, mock_diffs
    ):
        mock_diffs.return_value = []  # API diffs vacia → fallback
        mock_items.side_effect = lambda *a, **kw: (
            [{"path": "/comp/application.yml", "gitObjectType": "blob"}]
            if a[4] == "source" else
            [{"path": "/comp/application.yml", "gitObjectType": "blob"}]
        )
        mock_content.side_effect = lambda *a, **kw: (
            "port: 9090\n" if a[4] == "source" else "port: 8080\n"
        )
        results = analyze_component(
            "https://org", "proj", "repo-id",
            "/comp", "source", "target",
            self._fake_headers(), 3, False, None,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].change_type, CHANGE_EDIT)

    @patch("azdo_properties_branch_diff.get_branch_diffs")
    @patch("azdo_properties_branch_diff.get_items_in_path")
    @patch("azdo_properties_branch_diff.get_file_content")
    def test_identical_files_yield_none_severity(
        self, mock_content, mock_items, mock_diffs
    ):
        same = "key: value\n"
        mock_diffs.return_value = []
        mock_items.return_value = [
            {"path": "/comp/application.yml", "gitObjectType": "blob"}
        ]
        mock_content.return_value = same
        results = analyze_component(
            "https://org", "proj", "repo-id",
            "/comp", "source", "target",
            self._fake_headers(), 3, False, None,
        )
        self.assertTrue(all(r.severity == SEV_NONE for r in results))

    @patch("azdo_properties_branch_diff.get_branch_diffs")
    @patch("azdo_properties_branch_diff.get_items_in_path")
    @patch("azdo_properties_branch_diff.get_file_content")
    def test_file_only_in_target_is_critical(
        self, mock_content, mock_items, mock_diffs
    ):
        mock_diffs.return_value = []
        mock_items.side_effect = lambda *a, **kw: (
            []  # source: vacío
            if a[4] == "source"
            else [{"path": "/comp/orphan.yml", "gitObjectType": "blob"}]
        )
        mock_content.return_value = "legacy: true\n"
        results = analyze_component(
            "https://org", "proj", "repo-id",
            "/comp", "source", "target",
            self._fake_headers(), 3, False, None,
        )
        self.assertEqual(results[0].change_type, CHANGE_DELETE)
        self.assertEqual(results[0].severity, SEV_CRITICAL)

    @patch("azdo_properties_branch_diff.get_branch_diffs")
    @patch("azdo_properties_branch_diff.get_items_in_path")
    @patch("azdo_properties_branch_diff.get_file_content")
    def test_only_comment_changes_is_low(
        self, mock_content, mock_items, mock_diffs
    ):
        mock_diffs.return_value = []
        mock_items.return_value = [
            {"path": "/comp/config.yml", "gitObjectType": "blob"}
        ]
        mock_content.side_effect = lambda *a, **kw: (
            "# author: dev-team v2\nkey: value\n"
            if a[4] == "source"
            else "# author: dev-team v1\nkey: value\n"
        )
        results = analyze_component(
            "https://org", "proj", "repo-id",
            "/comp", "source", "target",
            self._fake_headers(), 3, False, None,
        )
        self.assertEqual(results[0].severity, SEV_LOW)


# ═══════════════════════════════════════════════════════════════════════════════
# make_headers
# ═══════════════════════════════════════════════════════════════════════════════
class TestMakeHeaders(unittest.TestCase):

    def test_basic_auth_present(self):
        h = make_headers("my-token")
        self.assertIn("Authorization", h)
        self.assertTrue(h["Authorization"].startswith("Basic "))

    def test_accept_json(self):
        h = make_headers("t")
        self.assertEqual(h["Accept"], "application/json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
