#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Azure reporting/consolidation/servicebus tools
(22, 23, 25, 35, 38) + launcher tools.py registry.

Lógica pura + try_az mockeado — sin llamadas reales a Azure.
"""

import importlib.util
import importlib
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


inv = _load("azure_resource_inventory",
            "inventory/azure_resource_inventory.py")
comp = _load("azure_compliance_report",
             "reports-viewer/azure_compliance_report.py")
dash = _load("azure_unified_dashboard",
             "consolidation/azure_unified_dashboard.py")
consol = _load("azure_infrastructure_consolidator",
               "consolidation/"
               "azure_infrastructure_consolidator.py")
sb = _load("azure_service_bus_monitor",
           "servicebus/azure_service_bus_monitor.py")


# ═══════════════════════════════════════════════════════════════════════════════
# resource inventory (22)
# ═══════════════════════════════════════════════════════════════════════════════

class TestInventory:
    def test_aggregation(self):
        resources = [
            {"name": "a", "type": "Microsoft.Web/sites",
             "rg": "rg1", "location": "eastus"},
            {"name": "b", "type": "Microsoft.Web/sites",
             "rg": "rg1", "location": "eastus"},
            {"name": "c", "type": "Microsoft.Sql/servers",
             "rg": "rg2", "location": "westus"},
        ]
        with patch.object(inv, "try_az",
                          return_value=resources):
            data = inv.collect("sub")
        assert data["total"] == 3
        assert data["by_type"]["sites"] == 2
        assert data["by_rg"]["rg1"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# compliance report (23)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompliance:
    def test_noncompliant_count(self):
        states = [{"policyDefinitionName": "abcdef123456",
                   "resourceType": "Microsoft.Web/sites",
                   "resourceGroup": "rg1",
                   "resourceId": "/x/y/app1"},
                  {"policyDefinitionName": "abcdef123456",
                   "resourceType": "Microsoft.Sql/servers",
                   "resourceGroup": "rg2",
                   "resourceId": "/x/y/sql1"}]
        with patch.object(comp, "try_az",
                          return_value=states):
            data = comp.collect("sub")
        assert data["noncompliant"] == 2
        assert data["by_type"]["sites"] == 1
        assert len(data["details"]) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# unified dashboard (25)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboard:
    def test_health_score_penalizes(self):
        def fake_az(args, sid=None, **kw):
            if args[:2] == ["vm", "list"]:
                return [{"n": "vm1", "p": "VM deallocated"}]
            if args[:2] == ["webapp", "list"]:
                return [{"n": "a1", "s": "Stopped",
                         "h": False}]
            return []
        with patch.object(dash, "try_az",
                          side_effect=fake_az):
            data = dash.collect("sub")
        assert data["health_score"] < 100
        assert data["vms"]["stopped"] == 1
        assert any("deallocated" in a
                   for a in data["alerts"])
        assert any("httpsOnly" in a for a in data["alerts"])

    def test_clean_subscription(self):
        with patch.object(dash, "try_az", return_value=[]):
            data = dash.collect("sub")
        assert data["health_score"] == 100
        assert data["alerts"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# infrastructure consolidator (35)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConsolidator:
    def test_backend_addresses(self):
        pool = {"backendAddresses": [{"fqdn": "a.net"},
                                     {"ipAddress": "1.2.3.4"}]}
        addrs = consol.backend_addresses(pool)
        assert "a.net" in addrs and "1.2.3.4" in addrs

    def test_matched_and_orphan(self):
        gws = [{"name": "gw1",
                "backendAddressPools": [
                    {"name": "pool1", "backendAddresses":
                     [{"fqdn": "app1.azurewebsites.net"}]},
                    {"name": "pool2", "backendAddresses":
                     [{"fqdn": "external.other.com"}]},
                    {"name": "empty", "backendAddresses": []},
                ]}]
        apps = [{"name": "app1",
                 "defaultHostName": "app1.azurewebsites.net"}]
        def fake_az(args, sid=None, **kw):
            if "application-gateway" in args:
                return gws
            if "webapp" in args:
                return apps
            return []
        with patch.object(consol, "try_az",
                          side_effect=fake_az):
            data = consol.consolidate("sub")
        matched = [m for m in data["mappings"]
                   if m["status"] == "matched"]
        assert len(matched) == 1
        assert matched[0]["app"] == "app1"
        assert any(o["type"] == "empty_pool"
                   for o in data["orphans"])
        assert any(o["type"] == "unknown_backend"
                   for o in data["orphans"])


# ═══════════════════════════════════════════════════════════════════════════════
# Service Bus monitor (38)
# ═══════════════════════════════════════════════════════════════════════════════

class TestServiceBus:
    def test_dlq_flagged(self):
        q = {"name": "q1", "countDetails":
             {"activeMessageCount": 5,
              "deadLetterMessageCount": 12},
             "maxSizeInMegabytes": 1024, "sizeInBytes": 1024,
             "deadLetteringOnMessageExpiration": True}
        r = sb.analyze_queue(q, "ns1")
        assert any("DLQ" in f for f in r["findings"])
        assert r["dead_letter"] == 12

    def test_queue_near_full(self):
        q = {"name": "q1",
             "countDetails": {"activeMessageCount": 0,
                              "deadLetterMessageCount": 0},
             "maxSizeInMegabytes": 100,
             "sizeInBytes": 90 * 1024 * 1024,
             "deadLetteringOnMessageExpiration": True}
        r = sb.analyze_queue(q, "ns1")
        assert any("capacidad" in f for f in r["findings"])

    def test_clean_queue(self):
        q = {"name": "q1",
             "countDetails": {"activeMessageCount": 10,
                              "deadLetterMessageCount": 0},
             "maxSizeInMegabytes": 1024, "sizeInBytes": 1024,
             "deadLetteringOnMessageExpiration": True}
        assert sb.analyze_queue(q, "ns1")["findings"] == []

    def test_namespace_tls(self):
        n = {"name": "ns1", "resourceGroup": "rg",
             "minimumTlsVersion": "1.0",
             "publicNetworkAccess": "Enabled",
             "sku": {"name": "Standard"}}
        r = sb.analyze_ns("sub", n)
        assert any("TLS" in f for f in r["findings"])
        assert any("público" in f for f in r["findings"])


# ═══════════════════════════════════════════════════════════════════════════════
# Launcher tools.py — integridad del registry y builders
# ═══════════════════════════════════════════════════════════════════════════════

def _load_tools():
    spec = importlib.util.spec_from_file_location(
        "azure_tools", _AZURE / "tools.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestLauncherRegistry:
    def test_all_paths_exist(self):
        t = _load_tools()
        missing = [k for k, v in t.TOOLS.items()
                   if not k.startswith("_")
                   and k not in ("A", "Q")
                   and not (t.BASE_DIR / v["path"]).exists()]
        assert missing == []

    def test_required_args_subset(self):
        t = _load_tools()
        for k, v in t.TOOLS.items():
            if k.startswith("_") or k in ("A", "Q"):
                continue
            req = v.get("required_args") or []
            assert set(req) <= set(v["args"]), \
                f"tool {k}: required_args no está en args"

    def test_tool_count(self):
        t = _load_tools()
        numeric = [k for k in t.TOOLS if k.isdigit()]
        assert len(numeric) == 39

    def test_auto_excludes_required_arg_tools(self):
        t = _load_tools()
        auto = set(t.TOOLS["A"]["auto_tools"])
        required = {k for k, v in t.TOOLS.items()
                    if v.get("required_args")}
        assert required.isdisjoint(auto)


class TestArgBuilders:
    def test_auto_args_subscription_and_json(self):
        t = _load_tools()
        tool = {"args": ["--subscription", "-o"]}
        args = t._build_auto_args(tool, "sub-x")
        assert "--subscription" in args
        assert "sub-x" in args
        assert args[-2:] == ["-o", "json"]

    def test_auto_args_skip_output(self):
        t = _load_tools()
        tool = {"args": ["--subscription", "-o"],
                "auto_run": {"skip_output": True}}
        args = t._build_auto_args(tool, "s")
        assert "-o" not in args

    def test_auto_args_custom_format(self):
        t = _load_tools()
        tool = {"args": ["--subscription", "--output"],
                "auto_run": {"output_format": "html"}}
        args = t._build_auto_args(tool, "s")
        assert args[-2:] == ["--output", "html"]

    def test_additional_args_appended(self):
        t = _load_tools()
        tool = {"args": ["-o"],
                "additional_args": ["--config",
                                    "scm/config.json"]}
        args = t._build_auto_args(tool, "s")
        assert "--config" in args
        idx = args.index("--config")
        assert "config.json" in args[idx + 1]

    def test_no_subscription_flag_not_passed(self):
        t = _load_tools()
        tool = {"args": ["-o"]}
        args = t._build_auto_args(tool, "sub-x")
        assert "sub-x" not in args
