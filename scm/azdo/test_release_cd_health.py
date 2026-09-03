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
from datetime import datetime, timedelta, timezone
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

    def _make_detail(self, is_disabled=False, stages=None, modified_on=None):
        """Crea un detail de pipeline mock."""
        if stages is None:
            stages = [
                {"name": "DEV", "rank": 1},
                {"name": "QA", "rank": 2},
                {"name": "Production", "rank": 3},
            ]
        detail = {
            "id": 42,
            "name": "Test-Pipeline",
            "isDisabled": is_disabled,
            "environments": stages,
        }
        if modified_on:
            detail["modifiedOn"] = modified_on
        return detail

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

    @patch.object(mod, "get_latest_releases")
    @patch.object(mod, "get_release_def_detail")
    def test_process_pipeline_captures_folder(self, mock_detail, mock_releases):
        """Verifica que process_pipeline captura el folder/path del summary."""
        mock_detail.return_value = self._make_detail()
        mock_releases.return_value = []
        result = mod.process_pipeline(
            summary={"id": 42, "name": "Test-Pipeline", "path": "\\Release\\Prod"},
            org="https://dev.azure.com/test",
            project="test-proj",
            headers={"Authorization": "Basic test"},
            top=5,
            debug=False,
        )
        self.assertEqual(result["folder"], "\\Release\\Prod")

    @patch.object(mod, "get_latest_releases")
    @patch.object(mod, "get_release_def_detail")
    def test_process_pipeline_default_folder(self, mock_detail, mock_releases):
        """Verifica que process_pipeline usa \\ como folder por defecto."""
        mock_detail.return_value = self._make_detail()
        mock_releases.return_value = []
        result = mod.process_pipeline(
            summary={"id": 42, "name": "Test-Pipeline"},
            org="https://dev.azure.com/test",
            project="test-proj",
            headers={"Authorization": "Basic test"},
            top=5,
            debug=False,
        )
        self.assertEqual(result["folder"], "\\")


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
                "folder": f"\\Release\\Folder-{i}",
                "stages": ["DEV", "QA", "Production"],
                "stages_norm": ["dev", "qa", "production"],
                "prod_stage": "Production",
                "last_prod_dt": datetime(2025, 1, 15, tzinfo=timezone.utc),
                "prod_attempts": 1,
                "ever_deployed": True,
                "last_release_id": 200 + i,
                "last_release_name": f"Release-{200 + i}",
                "last_release_date": datetime(2025, 1, 15, tzinfo=timezone.utc),
                "score": 85,
                "score_recency": 42,
                "score_stability": 20,
                "score_definition": 20,
                "days_since": 30,
                "days_modified": 200,
                "modified_on": datetime(2025, 1, 15, tzinfo=timezone.utc),
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
                "folder": f"\\Release\\Folder-{i}",
                "stages": ["DEV", "QA", "Production"],
                "stages_norm": ["dev", "qa", "production"],
                "prod_stage": "Production",
                "last_prod_dt": datetime(2025, 1, 15, tzinfo=timezone.utc) if i > 0 else None,
                "prod_attempts": 1 if i > 0 else None,
                "ever_deployed": i > 0,
                "last_release_id": 200 + i,
                "last_release_name": f"Release-{200 + i}",
                "last_release_date": datetime(2025, 1, 15, tzinfo=timezone.utc) if i > 0 else None,
                "score": 85 - i * 20,
                "score_recency": 42,
                "score_stability": 20,
                "score_definition": 20,
                "days_since": 30,
                "days_modified": 200,
                "modified_on": datetime(2025, 1, 15, tzinfo=timezone.utc) if i > 0 else None,
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

    def test_html_contains_folder_column(self):
        """Verifica que el HTML contiene la columna Folder."""
        rows = self._make_rows()
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(mod, "get_output_dir", return_value=Path(tmpdir)):
                filepath = mod.generate_html_dashboard(rows, "UTC")
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("Folder", content)
                self.assertIn("folder", content)

    def test_flat_data_contains_folder(self):
        """Verifica que el flat data de export_results incluye folder."""
        rows = self._make_rows(count=2)
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
            call_args = mock_manager.export_json.call_args
            flat_data = call_args[0][0]
            self.assertIn("folder", flat_data[0])


class TestComputeScore(unittest.TestCase):
    """Tests para la nueva formula de compute_score con 3 componentes."""

    def test_never_deployed_returns_zero(self):
        """Pipeline sin deploy a produccion debe retornar score 0."""
        result = mod.compute_score(None, None)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["recency"], 0)
        self.assertEqual(result["stability"], 0)
        self.assertEqual(result["definition"], 0)

    def test_recent_deploy_one_attempt_old_definition(self):
        """Deploy reciente, 1 intento, definicion sin modificar por 180+ dias."""
        now = datetime.now(timezone.utc)
        last_deploy = now - timedelta(days=10)
        modified = now - timedelta(days=200)
        result = mod.compute_score(last_deploy, 1, modified)
        # Recency: 70 * (1 - 10/365) = ~68.08 -> 68
        # Stability: 20 - 0 = 20
        # Definition: min(10, 10 * 200/180) = 10
        # Total: 68 + 20 + 10 = 98
        self.assertEqual(result["recency"], 68)
        self.assertEqual(result["stability"], 20)
        self.assertEqual(result["definition"], 10)
        self.assertEqual(result["total"], 98)

    def test_old_deploy_many_attempts_recent_definition(self):
        """Deploy antiguo, muchos intentos, definicion modificada recientemente."""
        now = datetime.now(timezone.utc)
        last_deploy = now - timedelta(days=300)
        modified = now - timedelta(days=5)
        result = mod.compute_score(last_deploy, 4, modified)
        # Recency: 70 * (1 - 300/365) = ~12.47
        # Stability: 20 - 3*7 = -1 -> max(0, -1) = 0
        # Definition: min(10, 10 * 5/180) = ~0.28
        # Total: round(12.47 + 0 + 0.28) = round(12.75) = 13
        self.assertEqual(result["recency"], 12)
        self.assertEqual(result["stability"], 0)
        self.assertEqual(result["definition"], 0)
        self.assertEqual(result["total"], 13)

    def test_no_modified_on_definition_zero(self):
        """Sin modifiedOn, definition debe ser 0."""
        now = datetime.now(timezone.utc)
        last_deploy = now - timedelta(days=30)
        result = mod.compute_score(last_deploy, 1, None)
        self.assertEqual(result["definition"], 0)
        self.assertIsNone(result["days_modified"])

    def test_two_attempts_stability(self):
        """2 intentos deben dar estabilidad 13."""
        now = datetime.now(timezone.utc)
        last_deploy = now - timedelta(days=30)
        modified = now - timedelta(days=90)
        result = mod.compute_score(last_deploy, 2, modified)
        # Stability: 20 - 1*7 = 13
        self.assertEqual(result["stability"], 13)

    def test_definition_caps_at_10(self):
        """Definition no debe exceder 10 pts."""
        now = datetime.now(timezone.utc)
        last_deploy = now - timedelta(days=10)
        modified = now - timedelta(days=365)
        result = mod.compute_score(last_deploy, 1, modified)
        self.assertEqual(result["definition"], 10)

    def test_total_capped_at_100(self):
        """Total no debe exceder 100."""
        now = datetime.now(timezone.utc)
        last_deploy = now  # 0 dias
        modified = now - timedelta(days=365)
        result = mod.compute_score(last_deploy, 1, modified)
        # Recency: 70, Stability: 20, Definition: 10 = 100
        self.assertEqual(result["total"], 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
