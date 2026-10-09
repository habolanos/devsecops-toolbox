#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Azure common helpers + ACR image filter

Cubre la lógica pura de scm/azure/azure_common.py y el filtrado
semver de artifacts/azure_acr_image_filter.py (tool 28).
Sin llamadas a Azure CLI reales — todo mockeado.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_AZURE = Path(__file__).parent.parent.parent / "azure"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(
        name, _AZURE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ac = _load("azure_common", "azure_common.py")
acr_filter = _load("azure_acr_image_filter",
                   "artifacts/azure_acr_image_filter.py")


# ═══════════════════════════════════════════════════════════════════════════════
# azure_common
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunAz:
    def _proc(self, rc=0, out="[]", err=""):
        p = MagicMock()
        p.returncode, p.stdout, p.stderr = rc, out, err
        return p

    def test_parses_json_and_adds_subscription(self):
        with patch.object(ac.subprocess, "run",
                          return_value=self._proc(
                              out='[{"a":1}]')) as run:
            result = ac.run_az(["vm", "list"], "sub-1")
        assert result == [{"a": 1}]
        cmd = run.call_args[0][0]
        assert cmd[:2] == ["az", "vm"]
        assert "--subscription" in cmd and "sub-1" in cmd
        assert cmd[-2:] == ["-o", "json"] or \
            cmd[2:4] == ["list", "-o"]

    def test_empty_stdout_returns_none(self):
        with patch.object(ac.subprocess, "run",
                          return_value=self._proc(out="")):
            assert ac.run_az(["account", "show"]) is None

    def test_nonzero_raises_runtime_error(self):
        with patch.object(ac.subprocess, "run",
                          return_value=self._proc(
                              rc=1, err="bad")):
            with pytest.raises(RuntimeError, match="rc=1"):
                ac.run_az(["vm", "list"])

    def test_try_az_returns_default_on_error(self):
        with patch.object(ac.subprocess, "run",
                          return_value=self._proc(rc=2)):
            assert ac.try_az(["x"], default=[]) == []


class TestResolveSubscription:
    def test_cli_value_wins(self):
        assert ac.resolve_subscription("sub-abc") == "sub-abc"

    def test_placeholder_ignored(self):
        with patch.object(ac, "load_config",
                          return_value={}), \
             patch.object(ac, "run_az", return_value="sub-x"):
            assert ac.resolve_subscription(
                "<TU_SUBSCRIPTION_ID>") == "sub-x"

    def test_config_fallback(self):
        with patch.object(ac, "load_config", return_value={
                "subscription_id": "sub-cfg"}):
            assert ac.resolve_subscription("") == "sub-cfg"


class TestRgOf:
    def test_field(self):
        assert ac.rg_of({"resourceGroup": "rg1"}) == "rg1"

    def test_derived_from_id(self):
        rid = ("/subscriptions/s/resourceGroups/RG-2/"
               "providers/Microsoft.Web/sites/app1")
        assert ac.rg_of({"id": rid}) == "RG-2"

    def test_missing(self):
        assert ac.rg_of({}) == ""


class TestExports:
    def test_export_json(self, tmp_path):
        out = tmp_path / "r.json"
        ac.export_json(out, {"a": 1})
        assert json.loads(out.read_text())["a"] == 1

    def test_export_csv(self, tmp_path):
        out = tmp_path / "r.csv"
        ac.export_csv(out, ["a", "b"], [{"a": 1, "b": 2,
                                         "extra": 9}])
        text = out.read_text(encoding="utf-8")
        assert "a,b" in text and "1,2" in text
        assert "extra" not in text


# ═══════════════════════════════════════════════════════════════════════════════
# acr_image_filter — semver y matching
# ═══════════════════════════════════════════════════════════════════════════════

class TestSemver:
    @pytest.mark.parametrize("tag,expected", [
        ("1.2.3", (1, 2, 3)),
        ("v2.0.1", (2, 0, 1)),
        ("10.20.30-rc1", (10, 20, 30)),
    ])
    def test_parse(self, tag, expected):
        assert acr_filter.parse_semver(tag) == expected

    @pytest.mark.parametrize("tag", ["latest", "dev", "1.2", ""])
    def test_non_semver(self, tag):
        assert acr_filter.parse_semver(tag) is None


class TestSplitFilter:
    def test_operator(self):
        assert acr_filter._split_filter(">=1.2.0") == (
            ">=", "1.2.0")

    def test_regex(self):
        assert acr_filter._split_filter("prod.*") == (
            None, "prod.*")


class TestMatchesFilter:
    @pytest.mark.parametrize("tag,flt,expected", [
        ("1.5.0", ">=1.2.0", True),
        ("1.0.0", ">=1.2.0", False),
        ("2.0.0", "<2.0.0", False),
        ("1.4.2", "=1.4.2", True),
        ("1.4.3", "!=1.4.2", True),
        ("prod-v1.0.0", "prod", True),       # regex substring
        ("dev-v1.0.0", "prod", False),
        ("latest", ">=1.0.0", False),        # no semver → no match
    ])
    def test_match(self, tag, flt, expected):
        assert acr_filter.matches_filter(tag, flt) is expected


class TestLoadCsvTags:
    def test_reads_tag_columns(self, tmp_path):
        csv = tmp_path / "tags.csv"
        csv.write_text(
            "registry,repository,tag,created\n"
            "acr1,app1,1.2.3,2025-01-01\n", encoding="utf-8")
        rows = acr_filter.load_csv_tags(str(csv))
        assert rows[0]["tag"] == "1.2.3"
        assert rows[0]["repository"] == "app1"
