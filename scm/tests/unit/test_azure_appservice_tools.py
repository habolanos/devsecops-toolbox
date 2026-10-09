#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Azure App Service tools (19,20,21,31,32,33)
y Azure Functions analyzer (34).

Lógica pura + try_az mockeado — sin llamadas reales a Azure.
"""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

_AZURE = Path(__file__).parent.parent.parent / "azure"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(
        name, _AZURE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mon = _load("appservice_monitor",
            "app-service/appservice_monitor.py")
sec = _load("appservice_security",
            "app-service/appservice_security.py")
val = _load("appservice_validator",
            "app-service/appservice_validator.py")
health = _load("appservice_health_analyzer",
               "app-service/appservice_health_analyzer.py")
cost = _load("appservice_cost_analyzer",
             "app-service/appservice_cost_analyzer.py")
traffic = _load("appservice_traffic_analyzer",
                "app-service/appservice_traffic_analyzer.py")
funcs = _load("azure_functions_analyzer",
              "consolidation/azure_functions_analyzer.py")


# ═══════════════════════════════════════════════════════════════════════════════
# appservice_monitor (19)
# ═══════════════════════════════════════════════════════════════════════════════

class TestMonitorNormalize:
    def test_stopped_flagged(self):
        app = {"name": "app1", "resourceGroup": "rg",
               "state": "Stopped", "httpsOnly": True}
        r = mon.normalize(app)
        assert any("Stopped" in f for f in r["findings"])

    def test_http_only_flagged(self):
        app = {"name": "app1", "state": "Running",
               "httpsOnly": False}
        r = mon.normalize(app)
        assert any("httpsOnly" in f for f in r["findings"])

    def test_plan_extracted(self):
        app = {"name": "app1", "state": "Running",
               "httpsOnly": True,
               "appServicePlanId": "/x/serverfarms/plan-prod"}
        assert mon.normalize(app)["plan"] == "plan-prod"


# ═══════════════════════════════════════════════════════════════════════════════
# appservice_security (20)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityAudit:
    def _app(self):
        return {"name": "app1", "resourceGroup": "rg",
                "httpsOnly": False}

    def test_http_critical(self):
        with patch.object(sec, "try_az", return_value={}):
            f = sec.audit_app("sub", self._app())
        assert any(x["check"] == "https" and
                   x["sev"] == "critical" for x in f)

    def test_old_tls_critical(self):
        def fake_az(args, sid=None, **kw):
            if "config" in args:
                return {"minTlsVersion": "1.0",
                        "ftpsState": "Disabled"}
            return {"enabled": True}
        with patch.object(sec, "try_az",
                          side_effect=fake_az):
            f = sec.audit_app("sub",
                              {"name": "a", "resourceGroup":
                               "rg", "httpsOnly": True,
                               "identity": {}})
        assert any(x["check"] == "tls" for x in f)

    def test_cors_star_high(self):
        def fake_az(args, sid=None, **kw):
            if "config" in args:
                return {"minTlsVersion": "1.2",
                        "ftpsState": "Disabled",
                        "cors": {"allowedOrigins": ["*"]},
                        "ipSecurityRestrictions":
                            [{"action": "Allow"}],
                        "vnetRouteAllEnabled": True}
            return {"enabled": True}
        with patch.object(sec, "try_az",
                          side_effect=fake_az):
            f = sec.audit_app("sub",
                              {"name": "a", "resourceGroup":
                               "rg", "httpsOnly": True,
                               "identity": {"type": "x"}})
        assert any(x["check"] == "cors" for x in f)
        assert not any(x["check"] == "auth" for x in f)


# ═══════════════════════════════════════════════════════════════════════════════
# appservice_validator (21)
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidator:
    def test_missing_basics_warns(self):
        def fake_az(args, sid=None, **kw):
            return {} if "config" in args and \
                "backup" not in args else \
                ([] if "slot" in args else None)
        with patch.object(val, "try_az",
                          side_effect=fake_az):
            f = val.validate_app("sub",
                                 {"name": "a",
                                  "resourceGroup": "rg"})
        checks = {x["check"] for x in f}
        assert {"always_on", "health_check", "backup",
                "slots"} <= checks

    def test_findings_have_fix(self):
        with patch.object(val, "try_az", return_value={}):
            f = val.validate_app("sub",
                                 {"name": "a",
                                  "resourceGroup": "rg"})
        assert all("fix" in x for x in f)


# ═══════════════════════════════════════════════════════════════════════════════
# appservice_health_analyzer (31)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthScore:
    def test_perfect(self):
        assert health.health_score({}) == 100
        assert health.status_label(100) == "HEALTHY"

    def test_5xx_penalty(self):
        assert health.health_score({"http5xx": 30}) == 60

    def test_cpu_mem(self):
        s = health.health_score({"cpu_pct": 90,
                                 "mem_pct": 90})
        assert s == 40
        assert health.status_label(s) == "CRITICAL"

    def test_degraded_band(self):
        s = health.health_score({"cpu_pct": 90})
        assert 50 <= s < 75
        assert health.status_label(s) == "DEGRADED"


# ═══════════════════════════════════════════════════════════════════════════════
# appservice_cost_analyzer (32)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCostAnalysis:
    def test_empty_plan_recommends_delete(self):
        plan = {"name": "p1", "resourceGroup": "rg",
                "sku": {"name": "B1", "capacity": 1}}
        with patch.object(cost, "try_az", return_value=[]):
            r = cost.plan_analysis("sub", plan)
        assert any("vacío" in x for x in r["recommendations"])

    def test_free_sku_warns(self):
        plan = {"name": "p1", "sku": {"name": "F1",
                                      "capacity": 1}}
        with patch.object(cost, "try_az",
                          return_value=[{"name": "app1"}]):
            r = cost.plan_analysis("sub", plan)
        assert any("Free/Shared" in x
                   for x in r["recommendations"])

    def test_monthly_est(self):
        plan = {"name": "p1",
                "sku": {"name": "S1", "capacity": 2}}
        with patch.object(cost, "try_az",
                          return_value=[{"name": "a"}]):
            r = cost.plan_analysis("sub", plan)
        assert r["monthly_est"] >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# appservice_traffic_analyzer (33)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTraffic:
    def test_slot_traffic_map(self):
        routing = [{"actionHostName": "app1.azurewebsites.net",
                    "reroutePercentage": 90},
                   {"actionHostName":
                    "app1-staging.azurewebsites.net",
                    "reroutePercentage": 10}]
        with patch.object(traffic, "try_az",
                          return_value=routing):
            t = traffic.slot_traffic("sub",
                                     {"name": "app1"})
        assert t["app1"] == 90
        assert t["app1-staging"] == 10

    def test_error_rate(self):
        def fake_metric(sub, rid, name, hours, agg="Total"):
            return {"Requests": 200.0, "Http5xx": 10.0,
                    "Http4xx": 4.0,
                    "HttpResponseTime": 0.5}.get(name)
        with patch.object(traffic, "metric",
                          side_effect=fake_metric), \
             patch.object(traffic, "slot_traffic",
                          return_value={}):
            r = traffic.analyze("sub",
                                {"name": "a", "id": "/x"},
                                24)
        assert r["error_rate"] == 5.0


# ═══════════════════════════════════════════════════════════════════════════════
# azure_functions_analyzer (34)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFunctions:
    def test_anonymous_http_trigger(self):
        fns = [{"name": "app1/f1",
                "config": {"bindings": [
                    {"type": "httpTrigger",
                     "authLevel": "anonymous"},
                    {"type": "http"}]}}]
        with patch.object(funcs, "try_az",
                          return_value=fns):
            out = funcs.list_functions("sub",
                                       {"name": "app1"})
        assert out[0]["http_anonymous"] is True
        assert "httpTrigger" in out[0]["triggers"]

    def test_auth_function(self):
        fns = [{"name": "app1/f1",
                "config": {"bindings": [
                    {"type": "httpTrigger",
                     "authLevel": "function"}]}}]
        with patch.object(funcs, "try_az",
                          return_value=fns):
            out = funcs.list_functions("sub",
                                       {"name": "app1"})
        assert out[0]["http_anonymous"] is False

    def test_empty_app_flagged(self):
        app = {"name": "app1", "resourceGroup": "rg",
               "httpsOnly": True, "identity": {"x": 1},
               "appServicePlanId": "/x/plans/p1"}
        def fake_az(args, sid=None, **kw):
            if "config" in args:
                return {"cors": {"allowedOrigins": []}}
            return []
        with patch.object(funcs, "try_az",
                          side_effect=fake_az):
            r = funcs.analyze_app("sub", app)
        assert any("vacía" in f for f in r["findings"])
