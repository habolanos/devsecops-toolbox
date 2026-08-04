#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para cicd_inventory_cd_detailed.py

Cobertura:
- _extract_variables: extraccion de variables del definition detail
- _variables_to_string: conversion a string legible
- _fetch_cd_pipeline: integracion de variables en el resultado
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
