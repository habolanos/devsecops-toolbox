#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para azdo_release_cd_health.py

Cobertura:
- is_disabled en process_pipeline
- is_disabled en export_results (flat data)
- generate_html_dashboard genera archivo valido
- generate_html_dashboard incluye columna Disabled
- generate_html_dashboard retorna None con rows vacio
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

# Asegurar que el directorio del script esta en sys.path
SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import azdo_release_cd_health as mod


class TestIsDisabledInProcessPipeline(unittest.TestCase):
    """Tests para verificar que is_disabled se captura correctamente en process_pipeline."""

    def _make_detail(self, is_disabled=False, stages=None):
        """Crea un detail de pipeline mock."""
        if stages is None:
            stages = [
                {"name": "DEV", "rank": 1},
                {"name": "QA", "rank": 2},
                {"name": "Production", "rank": 3},
            ]
        return {
            "id": 42,
            "name": "Test-Pipeline",
            "isDisabled": is_disabled,
            "environments": stages,
        }

    @patch.object(mod, "get_latest_releases")
    @patch.object(mod, "get_release_def_detail")
    def test_disabled_pipeline_sets_is_disabled_true(self, mock_detail, mock_releases):
        """Verifica que is_disabled=True se propaga al resultado."""
        mock_detail.return_value = self._make_detail(is_disabled=True)
        mock_releases.return_value = []

        result = mod.process_pipeline(
            summary={"id": 42, "name": "Test-Pipeline"},
            org="https://dev.azure.com/test",
            project="test-proj",
            headers={"Authorization": "Basic test"},
            top=5,
            debug=False,
        )
        self.assertTrue(result["is_disabled"])

    @patch.object(mod, "get_latest_releases")
    @patch.object(mod, "get_release_def_detail")
    def test_active_pipeline_sets_is_disabled_false(self, mock_detail, mock_releases):
        """Verifica que is_disabled=False se propaga al resultado."""
        mock_detail.return_value = self._make_detail(is_disabled=False)
        mock_releases.return_value = []

        result = mod.process_pipeline(
            summary={"id": 42, "name": "Test-Pipeline"},
            org="https://dev.azure.com/test",
            project="test-proj",
            headers={"Authorization": "Basic test"},
            top=5,
            debug=False,
        )
        self.assertFalse(result["is_disabled"])

    @patch.object(mod, "get_latest_releases")
    @patch.object(mod, "get_release_def_detail")
    def test_missing_is_disabled_defaults_false(self, mock_detail, mock_releases):
        """Verifica que si isDisabled no esta presente, defaults to False."""
        detail = self._make_detail()
        del detail["isDisabled"]
        mock_detail.return_value = detail
        mock_releases.return_value = []

        result = mod.process_pipeline(
            summary={"id": 42, "name": "Test-Pipeline"},
            org="https://dev.azure.com/test",
            project="test-proj",
            headers={"Authorization": "Basic test"},
            top=5,
            debug=False,
        )
        self.assertFalse(result["is_disabled"])


class TestIsDisabledInExportResults(unittest.TestCase):
    """Tests para verificar que is_disabled esta en los datos exportados."""

    def _make_rows(self, count=2, disabled_indices=None):
        """Crea rows mock para export."""
        if disabled_indices is None:
            disabled_indices = []
        rows = []
        for i in range(count):
            rows.append({
                "id": 100 + i,
                "name": f"Pipeline-{i}",
                "stages": ["DEV", "QA", "Production"],
                "stages_norm": ["dev", "qa", "production"],
                "prod_stage": "Production",
                "last_prod_dt": datetime(2025, 1, 15, tzinfo=timezone.utc),
                "prod_attempts": 1,
                "ever_deployed": True,
                "last_release_id": 200 + i,
                "score": 85,
                "score_recency": 60,
                "score_stability": 25,
                "days_since": 30,
                "rating_emoji": "🟢",
                "rating_label": "Bueno",
                "consistency": mod.CONS_OK,
                "cons_detail": "",
                "is_disabled": i in disabled_indices,
            })
        return rows

    def test_flat_data_contains_is_disabled(self):
        """Verifica que el flat data de export_results incluye is_disabled."""
        rows = self._make_rows(count=2, disabled_indices=[0])

        # Usar export_results con formato json para obtener flat data
        # Necesitamos mockear ExportManager
        import azdo_release_cd_health as mod_fresh
        mock_manager = MagicMock()
        mock_manager.export_json.return_value = "/tmp/test.json"
        with patch.object(mod_fresh, "EXPORT_MANAGER_AVAILABLE", True), \
             patch.object(mod_fresh, "ExportManager", return_value=mock_manager, create=True):
            mod_fresh.export_results(
                rows, "json",
                str(Path(__file__).parent),
                "UTC",
            )
            # Verificar que export_json fue llamado con flat data que incluye is_disabled
            call_args = mock_manager.export_json.call_args
            flat_data = call_args[0][0]
            self.assertIn("is_disabled", flat_data[0])
            self.assertTrue(flat_data[0]["is_disabled"])
            self.assertFalse(flat_data[1]["is_disabled"])


class TestHtmlDashboard(unittest.TestCase):
    """Tests para generate_html_dashboard."""

    def _make_rows(self, count=3, disabled_indices=None):
        """Crea rows mock para dashboard."""
        if disabled_indices is None:
            disabled_indices = []
        rows = []
        for i in range(count):
            rows.append({
                "id": 100 + i,
                "name": f"Pipeline-{i}",
                "stages": ["DEV", "QA", "Production"],
                "stages_norm": ["dev", "qa", "production"],
                "prod_stage": "Production",
                "last_prod_dt": datetime(2025, 1, 15, tzinfo=timezone.utc) if i > 0 else None,
                "prod_attempts": 1 if i > 0 else None,
                "ever_deployed": i > 0,
                "last_release_id": 200 + i,
                "score": 85 - i * 20,
                "score_recency": 60,
                "score_stability": 25,
                "days_since": 30,
                "rating_emoji": "🟢",
                "rating_label": "Bueno" if i > 0 else "Nunca",
                "consistency": mod.CONS_OK if i > 0 else mod.CONS_UNIQUE,
                "cons_detail": "",
                "is_disabled": i in disabled_indices,
            })
        return rows

    def test_generates_html_file(self):
        """Verifica que se genera un archivo HTML."""
        rows = self._make_rows()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(mod, "get_output_dir", return_value=Path(tmpdir)):
                filepath = mod.generate_html_dashboard(rows, "UTC", org="test-org", project="test-proj")
                self.assertIsNotNone(filepath)
                self.assertTrue(os.path.exists(filepath))
                self.assertTrue(filepath.endswith(".html"))

    def test_html_contains_disabled_column(self):
        """Verifica que el HTML contiene la columna Disabled."""
        rows = self._make_rows(disabled_indices=[0])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(mod, "get_output_dir", return_value=Path(tmpdir)):
                filepath = mod.generate_html_dashboard(rows, "UTC", org="test-org", project="test-proj")
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("Disabled", content)
                self.assertIn("is_disabled", content)

    def test_html_contains_project(self):
        """Verifica que el HTML contiene el nombre del proyecto."""
        rows = self._make_rows()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(mod, "get_output_dir", return_value=Path(tmpdir)):
                filepath = mod.generate_html_dashboard(rows, "UTC", org="test-org", project="my-project")
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("my-project", content)

    def test_html_contains_chart_js(self):
        """Verifica que el HTML incluye Chart.js."""
        rows = self._make_rows()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(mod, "get_output_dir", return_value=Path(tmpdir)):
                filepath = mod.generate_html_dashboard(rows, "UTC")
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("chart.js", content.lower())
                self.assertIn("scoreChart", content)
                self.assertIn("consChart", content)

    def test_html_contains_disabled_count(self):
        """Verifica que el HTML muestra el conteo de pipelines disabled."""
        rows = self._make_rows(count=3, disabled_indices=[0, 1])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(mod, "get_output_dir", return_value=Path(tmpdir)):
                filepath = mod.generate_html_dashboard(rows, "UTC")
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("Pipelines Disabled", content)
                # 2 disabled, 1 active
                self.assertIn(">2<", content)

    def test_empty_rows_returns_none(self):
        """Verifica que con rows vacio retorna None."""
        result = mod.generate_html_dashboard([], "UTC")
        self.assertIsNone(result)

    def test_html_contains_sortable_table(self):
        """Verifica que la tabla tiene funcionalidad de sort."""
        rows = self._make_rows()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(mod, "get_output_dir", return_value=Path(tmpdir)):
                filepath = mod.generate_html_dashboard(rows, "UTC")
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("sortTable", content)
                self.assertIn("sort-arrow", content)

    def test_html_contains_filter_bar(self):
        """Verifica que el HTML tiene barra de filtros."""
        rows = self._make_rows()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(mod, "get_output_dir", return_value=Path(tmpdir)):
                filepath = mod.generate_html_dashboard(rows, "UTC")
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("searchInput", content)
                self.assertIn("filterDisabled", content)
                self.assertIn("filterRating", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
