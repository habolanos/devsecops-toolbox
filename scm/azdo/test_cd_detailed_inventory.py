#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para cicd_inventory_cd_detailed.py

Cobertura:
- _extract_variables: extraccion de variables del definition detail
- _variables_to_string: conversion a string legible
- _fetch_cd_pipeline: integracion de variables en el resultado
- _count_stage_tasks: conteo de workflowTasks por stage (deployPhases)
- Filtrado por --var-name y --var-value
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Asegurar que el directorio del script esta en sys.path
SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cicd_inventory_cd_detailed as mod


class TestExtractVariables(unittest.TestCase):
    """Tests para _extract_variables."""

    def test_extract_variables_with_branch_config(self):
        """Verifica extraccion de variable branchConfig."""
        detail = {
            "variables": {
                "branchConfig": {"value": "cadenaSuministro", "allowOverride": False},
                "otherVar": {"value": "test123"},
            }
        }
        result = mod._extract_variables(detail)
        self.assertEqual(len(result), 2)
        names = [v["name"] for v in result]
        self.assertIn("branchConfig", names)
        self.assertIn("otherVar", names)
        branch_config = next(v for v in result if v["name"] == "branchConfig")
        self.assertEqual(branch_config["value"], "cadenaSuministro")

    def test_extract_variables_empty(self):
        """Verifica extraccion con definition sin variables."""
        result = mod._extract_variables({})
        self.assertEqual(result, [])

    def test_extract_variables_none(self):
        """Verifica extraccion con variables=None."""
        detail = {"variables": None}
        result = mod._extract_variables(detail)
        self.assertEqual(result, [])

    def test_extract_variables_non_dict_value(self):
        """Verifica extraccion cuando el valor no es dict (string directa)."""
        detail = {
            "variables": {
                "simpleVar": "plainStringValue",
            }
        }
        result = mod._extract_variables(detail)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "simpleVar")
        self.assertEqual(result[0]["value"], "plainStringValue")

    def test_extract_variables_empty_value(self):
        """Verifica extraccion cuando value esta vacio."""
        detail = {
            "variables": {
                "emptyVar": {"value": ""},
            }
        }
        result = mod._extract_variables(detail)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["value"], "")


class TestVariablesToString(unittest.TestCase):
    """Tests para _variables_to_string."""

    def test_empty_list(self):
        """Verifica string vacio para lista vacia."""
        self.assertEqual(mod._variables_to_string([]), "")

    def test_single_variable(self):
        """Verifica string para una variable."""
        var_list = [{"name": "branchConfig", "value": "cadenaSuministro"}]
        result = mod._variables_to_string(var_list)
        self.assertEqual(result, "branchConfig=cadenaSuministro")

    def test_multiple_variables(self):
        """Verifica string para multiples variables."""
        var_list = [
            {"name": "branchConfig", "value": "cadenaSuministro"},
            {"name": "env", "value": "prod"},
        ]
        result = mod._variables_to_string(var_list)
        self.assertEqual(result, "branchConfig=cadenaSuministro; env=prod")


class TestFetchCdPipelineVariables(unittest.TestCase):
    """Tests para verificar que _fetch_cd_pipeline incluye variables."""

    def _make_definition(self, def_id=100, name="Test-Pipeline"):
        return {
            "id": def_id,
            "name": name,
            "path": "\\TestFolder",
            "url": f"https://dev.azure.com/org/proj/_apis/release/definitions/{def_id}",
            "createdOn": "2025-01-01T00:00:00Z",
            "modifiedOn": "2025-06-01T00:00:00Z",
        }

    @patch.object(mod, "safe_az_get")
    def test_fetch_includes_variables(self, mock_get):
        """Verifica que el resultado incluye variables extraidas."""
        full_detail = {
            "environments": [{"name": "DEV"}, {"name": "PROD"}],
            "variables": {
                "branchConfig": {"value": "cadenaSuministro"},
                "env": {"value": "prod"},
            },
        }
        releases = {"value": [{"createdOn": "2025-07-01", "status": "succeeded"}]}

        mock_get.side_effect = [full_detail, releases]

        result = mod._fetch_cd_pipeline(
            self._make_definition(),
            headers={"Authorization": "Basic test"},
            org="org",
            project="proj",
        )

        self.assertIn("variableCount", result)
        self.assertEqual(result["variableCount"], 2)
        self.assertIn("variableNames", result)
        self.assertIn("branchConfig", result["variableNames"])
        self.assertIn("variables", result)
        self.assertIn("branchConfig=cadenaSuministro", result["variables"])
        self.assertIn("var_branchConfig", result)
        self.assertEqual(result["var_branchConfig"], "cadenaSuministro")
        self.assertEqual(result["var_env"], "prod")

    @patch.object(mod, "safe_az_get")
    def test_fetch_no_variables(self, mock_get):
        """Verifica que el resultado maneja definition sin variables."""
        full_detail = {
            "environments": [{"name": "DEV"}],
            "variables": {},
        }
        releases = {"value": []}

        mock_get.side_effect = [full_detail, releases]

        result = mod._fetch_cd_pipeline(
            self._make_definition(),
            headers={"Authorization": "Basic test"},
            org="org",
            project="proj",
        )

        self.assertEqual(result["variableCount"], 0)
        self.assertEqual(result["variableNames"], "")
        self.assertEqual(result["variables"], "")

    @patch.object(mod, "safe_az_get")
    def test_fetch_fallback_to_definition_when_detail_fails(self, mock_get):
        """Verifica que usa definition basico cuando full_detail falla."""
        definition = self._make_definition()
        definition["environments"] = [{"name": "QA"}]
        definition["variables"] = {"branchConfig": {"value": "cadenaSuministro"}}

        mock_get.side_effect = [{}, {"value": []}]

        result = mod._fetch_cd_pipeline(
            definition,
            headers={"Authorization": "Basic test"},
            org="org",
            project="proj",
        )

        self.assertIn("var_branchConfig", result)
        self.assertEqual(result["var_branchConfig"], "cadenaSuministro")


class TestVariableFiltering(unittest.TestCase):
    """Tests para el filtrado por variable en la logica de main()."""

    def _make_rows(self):
        """Crea rows mock con variables."""
        return [
            {
                "id": 1,
                "name": "Pipeline-A",
                "var_branchConfig": "cadenaSuministro",
                "variableCount": 1,
                "variableNames": "branchConfig",
                "variables": "branchConfig=cadenaSuministro",
            },
            {
                "id": 2,
                "name": "Pipeline-B",
                "var_branchConfig": "otroValor",
                "variableCount": 1,
                "variableNames": "branchConfig",
                "variables": "branchConfig=otroValor",
            },
            {
                "id": 3,
                "name": "Pipeline-C",
                "var_otherVar": "test",
                "variableCount": 1,
                "variableNames": "otherVar",
                "variables": "otherVar=test",
            },
        ]

    def test_filter_by_var_name_only(self):
        """Verifica filtrado por nombre de variable (sin valor)."""
        rows = self._make_rows()
        var_key = "var_branchConfig"
        filtered = [r for r in rows if r.get(var_key) is not None]
        self.assertEqual(len(filtered), 2)
        names = [r["name"] for r in filtered]
        self.assertIn("Pipeline-A", names)
        self.assertIn("Pipeline-B", names)

    def test_filter_by_var_name_and_value(self):
        """Verifica filtrado por nombre y valor de variable."""
        rows = self._make_rows()
        var_key = "var_branchConfig"
        var_value = "cadenaSuministro"
        filtered = [r for r in rows if r.get(var_key) is not None and str(r.get(var_key)) == var_value]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["name"], "Pipeline-A")

    def test_filter_by_nonexistent_var(self):
        """Verifica filtrado por variable que no existe."""
        rows = self._make_rows()
        var_key = "var_nonexistent"
        filtered = [r for r in rows if r.get(var_key) is not None]
        self.assertEqual(len(filtered), 0)

    def test_filter_by_var_value_no_match(self):
        """Verifica filtrado por valor que no existe."""
        rows = self._make_rows()
        var_key = "var_branchConfig"
        var_value = "noExiste"
        filtered = [r for r in rows if r.get(var_key) is not None and str(r.get(var_key)) == var_value]
        self.assertEqual(len(filtered), 0)


class TestCountStageTasks(unittest.TestCase):
    """Tests para _count_stage_tasks (v1.0.1)."""

    ENVS = [
        {"id": 11, "name": "Develop", "deployPhases": [
            {"workflowTasks": [{"taskId": "t1"}, {"taskId": "t2"}]},
        ]},
        {"id": 22, "name": "QA", "deployPhases": [
            {"workflowTasks": [{"taskId": "t3"}]},
            {"workflowTasks": [{"taskId": "t4"}, {"taskId": "t5"}]},
        ]},
        {"id": 33, "name": "Prod"},  # sin deployPhases
    ]

    def test_counts_workflow_tasks_per_stage(self):
        """Suma workflowTasks de todas las fases de cada stage."""
        per_stage, total = mod._count_stage_tasks(self.ENVS)
        self.assertEqual(per_stage, [("Develop", 2), ("QA", 3), ("Prod", 0)])
        self.assertEqual(total, 5)

    def test_empty_and_none_envs(self):
        """Env vacio o None → cero tareas sin error."""
        self.assertEqual(mod._count_stage_tasks([]), ([], 0))
        self.assertEqual(mod._count_stage_tasks(None), ([], 0))

    def test_phase_without_workflow_tasks(self):
        """deployPhase sin workflowTasks cuenta 0."""
        envs = [{"name": "S", "deployPhases": [{"rank": 1}]}]
        per_stage, total = mod._count_stage_tasks(envs)
        self.assertEqual(per_stage, [("S", 0)])
        self.assertEqual(total, 0)


class TestFetchCdPipelineTasks(unittest.TestCase):
    """Integracion de columnas de tareas en _fetch_cd_pipeline."""

    DETAIL = {
        "environments": TestCountStageTasks.ENVS,
        "variables": {"branchConfig": {"value": "main"}},
    }

    def test_task_columns_present(self):
        """totalTasks + columna tasksPerStage_<stage> por cada stage."""
        with patch.object(mod, "safe_az_get",
                          side_effect=[self.DETAIL, {"value": []}]):
            row = mod._fetch_cd_pipeline(
                {"id": 42, "name": "demo-CD"}, {}, "org", "proj")
        self.assertEqual(row["totalTasks"], 5)
        self.assertEqual(row["tasksPerStage_Develop"], 2)
        self.assertEqual(row["tasksPerStage_QA"], 3)
        self.assertEqual(row["tasksPerStage_Prod"], 0)
        self.assertNotIn("tasksPerStage", row)
        self.assertEqual(row["environmentsCount"], 3)
        self.assertEqual(row["environments"], "Develop / QA / Prod")

    def test_fallback_definition_without_detail(self):
        """Si falla el GET del detalle, usa definition basico → 0 tareas."""
        with patch.object(mod, "safe_az_get",
                          side_effect=[{}, {"value": []}]):
            row = mod._fetch_cd_pipeline(
                {"id": 7, "name": "x-CD", "environments": []}, {}, "org", "proj")
        self.assertEqual(row["totalTasks"], 0)
        self.assertFalse(any(k.startswith("tasksPerStage_") for k in row))


class TestReleaseStageStats(unittest.TestCase):
    """Tests para _release_stage_stats (v1.0.3): conteo, frecuencia y gaps."""

    def _env_step(self, ts, status="succeeded"):
        return {"status": status, "lastModifiedOn": ts}

    RELEASES = [
        # Release 1: Develop y QA desplegaron (QA 2h después), Prod no llegó
        {"environments": [
            {"definitionEnvironmentId": 11, "name": "Develop",
             "deploySteps": [{"status": "succeeded",
                              "lastModifiedOn": "2026-10-01T10:00:00Z"}]},
            {"definitionEnvironmentId": 22, "name": "QA",
             "deploySteps": [{"status": "succeeded",
                              "lastModifiedOn": "2026-10-01T12:00:00Z"}]},
        ]},
        # Release 2: Develop, QA (gap 4h) y Prod (gap 48h desde QA)
        {"environments": [
            {"definitionEnvironmentId": 11, "name": "Develop",
             "deploySteps": [{"status": "succeeded",
                              "lastModifiedOn": "2026-10-05T08:00:00Z"}]},
            {"definitionEnvironmentId": 22, "name": "QA",
             "deploySteps": [{"status": "succeeded",
                              "lastModifiedOn": "2026-10-05T12:00:00Z"}]},
            {"definitionEnvironmentId": 33, "name": "Prod",
             "deploySteps": [{"status": "succeeded",
                              "lastModifiedOn": "2026-10-07T12:00:00Z"}]},
        ]},
        # Release 3: solo Develop (falló QA)
        {"environments": [
            {"definitionEnvironmentId": 11, "name": "Develop",
             "deploySteps": [{"status": "succeeded",
                              "lastModifiedOn": "2026-10-09T10:00:00Z"}]},
            {"definitionEnvironmentId": 22, "name": "QA",
             "deploySteps": [{"status": "failed",
                              "lastModifiedOn": "2026-10-09T11:00:00Z"}]},
        ]},
    ]

    def test_counts_and_averages(self):
        stats = mod._release_stage_stats(TestCountStageTasks.ENVS,
                                         self.RELEASES)
        dev, qa, prod = {s["stage"]: s for s in stats}.values()
        # Develop llegó en los 3 releases
        self.assertEqual(dev["releases"], 3)
        # avg días entre deploys a Develop: (oct1 → oct9) / 2 = 4.0
        self.assertEqual(dev["avg_days"], 4.0)
        # QA: 2 llegadas, oct1→oct5 = 4.0 días
        self.assertEqual(qa["releases"], 2)
        self.assertEqual(qa["avg_days"], 4.0)
        # gap Develop→QA: (2h + 4h)/2 = 3.0
        self.assertEqual(qa["avg_gap_hours"], 3.0)
        # Prod llegó 1 vez → avg_days None; gap QA→Prod = 48h
        self.assertEqual(prod["releases"], 1)
        self.assertIsNone(prod["avg_days"])
        self.assertEqual(prod["avg_gap_hours"], 48.0)
        # Develop es primer stage → sin gap previo
        self.assertIsNone(dev["avg_gap_hours"])

    def test_no_releases(self):
        stats = mod._release_stage_stats(TestCountStageTasks.ENVS, [])
        for s in stats:
            self.assertEqual(s["releases"], 0)
            self.assertIsNone(s["avg_days"])
            self.assertIsNone(s["avg_gap_hours"])

    def test_survives_stage_rename(self):
        """Matcheo por definitionEnvironmentId aunque el nombre cambió."""
        envs = [{"id": 11, "name": "Dev-Nuevo"}]
        releases = [{"environments": [
            {"definitionEnvironmentId": 11, "name": "Develop",
             "deploySteps": [{"status": "succeeded",
                              "lastModifiedOn": "2026-10-01T10:00:00Z"}]},
        ]}]
        stats = mod._release_stage_stats(envs, releases)
        self.assertEqual(stats[0]["stage"], "Dev-Nuevo")
        self.assertEqual(stats[0]["releases"], 1)


class TestFetchCdPipelineStageStats(unittest.TestCase):
    """Integración de columnas releasesPerStage_/avgDaysPerStage_/avgHrsFromPrev_."""

    def test_release_stat_columns(self):
        with patch.object(mod, "safe_az_get", side_effect=[
                TestFetchCdPipelineTasks.DETAIL,
                {"value": TestReleaseStageStats.RELEASES}]):
            row = mod._fetch_cd_pipeline(
                {"id": 42, "name": "demo-CD"}, {}, "org", "proj")
        self.assertEqual(row["totalReleasesAnalyzed"], 3)
        self.assertEqual(row["releasesPerStage_Develop"], 3)
        self.assertEqual(row["releasesPerStage_QA"], 2)
        self.assertEqual(row["releasesPerStage_Prod"], 1)
        self.assertEqual(row["avgDaysPerStage_Develop"], 4.0)
        self.assertEqual(row["avgDaysPerStage_Prod"], "")
        self.assertEqual(row["avgHrsFromPrev_Develop"], "")
        self.assertEqual(row["avgHrsFromPrev_QA"], 3.0)
        self.assertEqual(row["avgHrsFromPrev_Prod"], 48.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
