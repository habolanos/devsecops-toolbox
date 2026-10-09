#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Azure DB/network + IAM/security tools

Cubre la lógica pura de tools 3,4,5,6,7,9,10,11,24,27,36,39
sin llamadas a az CLI reales.
"""

import importlib.util
from datetime import datetime, timedelta, timezone
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


sql_mon = _load("azure_sql_monitor",
                "azure-sql/azure_sql_monitor.py")
cosmos = _load("cosmos_db_analyzer",
               "azure-sql/cosmos_db_analyzer.py")
nsg = _load("nsg_audit", "connectivity/nsg_audit.py")
vnet = _load("vnet_analyzer", "connectivity/vnet_analyzer.py")
appgw = _load("appgateway_monitor",
              "connectivity/appgateway_monitor.py")
waf = _load("azure_waf_checker",
            "security/azure_waf_checker.py")
kv = _load("azure_keyvault_checker",
           "secrets-configmaps/azure_keyvault_checker.py")
sp = _load("azure_sp_analyzer",
           "service-accounts/azure_sp_analyzer.py")
sp_multi = _load("azure_sp_multi_subscription_reporter",
                 "service-accounts/"
                 "azure_sp_multi_subscription_reporter.py")
roles = _load("azure_roles_audit",
              "rolesypermisos/azure_roles_audit.py")
access = _load("azure_access_validator",
               "rolesypermisos/azure_access_validator.py")
events = _load("event_tracker",
               "event-tracker/event_tracker.py")
mon = _load("azure_monitor", "monitoring/azure_monitor.py")


def _future(days):
    return (datetime.now(timezone.utc) +
            timedelta(days=days)).isoformat()


def _past(days):
    return (datetime.now(timezone.utc) -
            timedelta(days=days)).isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# Azure SQL / Cosmos (tools 6, 7)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSqlMonitor:
    def test_public_access_flagged(self):
        s = {"name": "srv", "publicNetworkAccess": "Enabled",
             "minimalTlsVersion": "1.2",
             "administratorLogin": "sa"}
        f = sql_mon.analyze_server(s)
        assert any("publicNetworkAccess" in x for x in f)

    def test_old_tls_critical(self):
        s = {"name": "srv", "minimalTlsVersion": "1.0"}
        f = sql_mon.analyze_server(s)
        assert any("🔴" in x for x in f)

    def test_clean_server(self):
        s = {"name": "srv", "minimalTlsVersion": "1.2",
             "administratorLogin": "sa",
             "publicNetworkAccess": "Disabled"}
        assert sql_mon.analyze_server(s) == []


class TestCosmos:
    def test_api_kind_serverless(self):
        acc = {"capabilities": [{"name": "EnableServerless"}]}
        assert "Serverless" in cosmos.api_kind(acc)

    def test_api_kind_default_sql(self):
        assert cosmos.api_kind({"capabilities": []}) == "SQL"

    def test_public_no_ip_rules_critical(self):
        acc = {"name": "cdb", "publicNetworkAccess": "Enabled",
               "ipRules": [], "disableLocalAuth": True}
        r = cosmos.analyze(acc)
        assert any("🔴" in f for f in r["findings"])

    def test_local_auth_warning(self):
        acc = {"name": "cdb", "publicNetworkAccess":
               "Disabled", "disableLocalAuth": False}
        r = cosmos.analyze(acc)
        assert any("Local auth" in f for f in r["findings"])


# ═══════════════════════════════════════════════════════════════════════════════
# NSG / VNet / AppGW (tools 9, 10, 11)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNsgAudit:
    def _rule(self, **kw):
        r = {"name": "r1", "direction": "Inbound",
             "access": "Allow", "protocol": "Tcp",
             "sourceAddressPrefix": "*",
             "destinationPortRange": "22"}
        r.update(kw)
        return r

    def test_ssh_open_high(self):
        f = nsg.audit_rule("nsg1", self._rule())
        assert any(x["sev"] == "high" and "22" in x["detail"]
                   for x in f)

    def test_all_ports_critical(self):
        f = nsg.audit_rule("nsg1", self._rule(
            destinationPortRange="*"))
        assert any(x["sev"] == "critical" for x in f)

    def test_outbound_ignored(self):
        assert nsg.audit_rule("nsg1", self._rule(
            direction="Outbound")) == []

    def test_deny_ignored(self):
        assert nsg.audit_rule("nsg1", self._rule(
            access="Deny")) == []

    def test_restricted_source_ok(self):
        assert nsg.audit_rule("nsg1", self._rule(
            sourceAddressPrefix="10.0.0.0/8")) == []

    def test_port_range_helpers(self):
        assert 3389 in nsg.port_range(
            {"destinationPortRange": "3300-3400"})
        assert nsg.port_range(
            {"destinationPortRange": "443"}) == [443]
        assert 22 in nsg.port_range(
            {"destinationPortRange": "*"})


class TestVnet:
    def test_subnet_without_nsg(self):
        v = {"name": "vnet1", "resourceGroup": "rg",
             "addressSpace": {"addressPrefixes":
                              ["10.0.0.0/16"]},
             "subnets": [{"name": "s1", "addressPrefix":
                          "10.0.1.0/24"}]}
        r = vnet.analyze_vnet(v)
        assert any("sin NSG" in f for f in r["findings"])
        assert r["total_ips"] == 65536

    def test_gateway_subnet_exempt(self):
        v = {"name": "vnet1",
             "addressSpace": {"addressPrefixes":
                              ["10.0.0.0/16"]},
             "subnets": [{"name": "GatewaySubnet",
                          "addressPrefix": "10.0.0.0/27"}]}
        r = vnet.analyze_vnet(v)
        assert not any("sin NSG" in f for f in r["findings"])


class TestAppGw:
    def test_http_listener_and_unhealthy(self):
        gw = {"name": "gw1", "resourceGroup": "rg",
              "httpListeners": [{"name": "l1",
                                 "protocol": "Http"}],
              "sku": {"tier": "WAF_v2", "name": "WAF_v2",
                      "capacity": 2},
              "webApplicationFirewallConfiguration":
                  {"enabled": True,
                   "firewallMode": "Prevention"},
              "backendAddressPools": [{"name": "p1"}]}
        health = {"backendAddressPools": [{
            "backendHttpSettingsCollection": [{
                "servers": [{"address": "10.0.0.4",
                             "health": "Down"}]}]}]}
        with patch.object(appgw, "backend_health",
                          return_value=health):
            r = appgw.analyze("sub", gw)
        assert any("HTTP" in f for f in r["findings"])
        assert r["unhealthy_backends"] == ["10.0.0.4"]

    def test_waf_detection_flagged(self):
        gw = {"name": "gw2", "httpListeners": [],
              "webApplicationFirewallConfiguration":
                  {"enabled": True,
                   "firewallMode": "Detection"},
              "sku": {}, "backendAddressPools": []}
        with patch.object(appgw, "backend_health",
                          return_value={}):
            r = appgw.analyze("sub", gw)
        assert any("Detection" in f for f in r["findings"])


# ═══════════════════════════════════════════════════════════════════════════════
# WAF checker (tool 27)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWaf:
    def test_detection_mode_critical(self):
        p = {"name": "pol1",
             "policySettings": {"mode": "Detection",
                                "state": "Enabled"},
             "managedRules": {"managedRuleSets": [{}]},
             "customRules": {"rules": []}}
        r = waf.analyze_policy(p)
        assert any("🔴" in f for f in r["findings"])

    def test_disabled_policy_critical(self):
        p = {"name": "pol1",
             "policySettings": {"mode": "Prevention",
                                "state": "Disabled"},
             "managedRules": {"managedRuleSets": [{}]},
             "customRules": {"rules": []}}
        r = waf.analyze_policy(p)
        assert any("deshabilitada" in f
                   for f in r["findings"])

    def test_no_managed_rulesets(self):
        p = {"name": "pol1",
             "policySettings": {"mode": "Prevention",
                                "state": "Enabled"},
             "managedRules": {},
             "customRules": {"rules": []}}
        r = waf.analyze_policy(p)
        assert any("managed rulesets" in f
                   for f in r["findings"])

    def test_frontend_without_waf(self):
        fd = {"name": "fd1",
              "frontendEndpoints": [{"hostName": "x.com"}],
              "backendPools": [{}]}
        r = waf.analyze_frontdoor(fd, [])
        assert any("sin WAF" in f for f in r["findings"])


# ═══════════════════════════════════════════════════════════════════════════════
# Key Vault / SP analyzer / SP multi (tools 39, 4, 36)
# ═══════════════════════════════════════════════════════════════════════════════

class TestKeyVault:
    def test_days_to(self):
        assert kv._days_to("") == 9999
        assert kv._days_to(_future(10)) in (9, 10)
        assert kv._days_to(_past(5)) < 0

    def test_vault_findings(self):
        v = {"name": "kv1",
             "properties": {"enableSoftDelete": False,
                            "enablePurgeProtection": False,
                            "enableRbacAuthorization": False,
                            "networkAcls":
                                {"defaultAction": "Allow"},
                            "sku": {"name": "standard"}}}
        r = kv.analyze_vault(v)
        assert any("Soft delete" in f for f in r["findings"])
        assert any("Purge" in f for f in r["findings"])
        assert any("RBAC" in f or "access policies" in f
                   for f in r["findings"])

    def test_hardened_vault(self):
        v = {"name": "kv2",
             "properties": {"enableSoftDelete": True,
                            "enablePurgeProtection": True,
                            "enableRbacAuthorization": True,
                            "publicNetworkAccess": "Disabled",
                            "networkAcls":
                                {"defaultAction": "Deny"},
                            "sku": {"name": "premium"}}}
        assert kv.analyze_vault(v)["findings"] == []

    def test_secret_expired(self):
        secrets = [{"name": "s1",
                    "attributes": {"expires": _past(3),
                                   "enabled": True}}]
        with patch.object(kv, "try_az",
                          return_value=secrets):
            rows = kv.analyze_secrets("sub", "kv1")
        assert any("Expirado" in f
                   for f in rows[0]["findings"])

    def test_secret_no_expiry_warns(self):
        secrets = [{"name": "s1",
                    "attributes": {"enabled": True}}]
        with patch.object(kv, "try_az",
                          return_value=secrets):
            rows = kv.analyze_secrets("sub", "kv1")
        assert any("expiración" in f
                   for f in rows[0]["findings"])


class TestSpAnalyzer:
    def test_expired_credential(self):
        s = {"displayName": "sp1", "appId": "x",
             "passwordCredentials":
                 [{"endDateTime": _past(10)}]}
        r = sp.analyze_sp(s, 30)
        assert r["expired"] == 1
        assert any("🔴" in f for f in r["findings"])

    def test_expiring_soon(self):
        s = {"displayName": "sp1",
             "keyCredentials": [{"endDate": _future(15)}]}
        r = sp.analyze_sp(s, 30)
        assert r["expiring"] == 1

    def test_no_credentials(self):
        r = sp.analyze_sp({"displayName": "mi"}, 30)
        assert any("Sin credenciales" in f
                   for f in r["findings"])


class TestSpMulti:
    def test_summary_counts(self):
        sub = {"id": "sub-1", "name": "prod"}
        sps = [{"passwordCredentials":
                [{"endDateTime": _past(5)}]},
               {"keyCredentials":
                [{"endDateTime": _future(10)}]}]
        assigns = [{"roleDefinitionName": "Owner"},
                   {"roleDefinitionName": "Reader"}]

        def fake_az(args, sid=None, **kw):
            if "sp" in args:
                return sps
            return assigns
        with patch.object(sp_multi, "try_az",
                          side_effect=fake_az):
            out = sp_multi.subscription_summary(sub)
        assert out["sps"] == 2
        assert out["expired_creds"] == 1
        assert out["expiring_30d"] == 1
        assert out["owners"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Roles audit / access validator (tools 3, 5)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAccessValidator:
    def test_guest_with_owner_flagged(self):
        assignments = [{"principalId": "g1",
                        "roleDefinitionName": "Owner",
                        "scope": "/subscriptions/s"}]
        guests = [{"id": "g1"}]
        def fake_az(args, sid=None, **kw):
            if "user" in args:
                return guests
            return assignments
        with patch.object(access, "try_az",
                          side_effect=fake_az):
            r = access.validate("s")
        assert any("invitados" in f for f in r["findings"])


# ═══════════════════════════════════════════════════════════════════════════════
# Event tracker (tool 24)
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventTracker:
    def test_service_health_critical(self):
        e = {"category": {"value": "ServiceHealth"},
             "level": "Informational"}
        assert events.severity_of(e) == "critical"

    def test_delete_high(self):
        e = {"operationName": {"localizedValue":
                               "Delete Virtual Machine"},
             "level": "Informational"}
        assert events.severity_of(e) == "high"

    def test_error_medium(self):
        e = {"level": "Error",
             "operationName": "Read Resource"}
        assert events.severity_of(e) == "medium"

    def test_info_low(self):
        e = {"level": "Informational",
             "operationName": "List Keys"}
        assert events.severity_of(e) == "low"

    def test_component_filter(self):
        evs = [{"resourceId": "/x/rg/app-prod",
                "operationName": "Write",
                "eventTimestamp": "2025-01-01T00:00:00Z"}]
        with patch.object(events, "try_az",
                          return_value=evs):
            kept = events.collect("s", 24, "app-prod",
                                  "", "")
            dropped = events.collect("s", 24, "other",
                                     "", "")
        assert len(kept) == 1 and len(dropped) == 0

    def test_summarize(self):
        evs = [{"severity": "critical", "caller": "a@x",
                "operation": "Delete", "status": "Failed"},
               {"severity": "low", "caller": "a@x",
                "operation": "Read", "status": "Succeeded"}]
        s = events.summarize(evs)
        assert s["total"] == 2
        assert s["failed"] == 1
        assert s["by_severity"]["critical"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Azure monitor (tool 1)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAzureMonitor:
    def test_collect_aggregates(self):
        def fake_az(args, sid=None, **kw):
            if args[:2] == ["resource", "list"]:
                return [{"type": "Microsoft.Compute/"
                                  "virtualMachines",
                         "location": "eastus",
                         "resourceGroup": "rg1"}]
            if args[:2] == ["vm", "list"]:
                return [{"name": "vm1", "power":
                         "VM running"}]
            return []
        with patch.object(mon, "try_az",
                          side_effect=fake_az):
            data = mon.collect("sub")
        assert data["total_resources"] == 1
        assert "virtualMachines" in data["by_type"]
        assert data["vm_states"]["VM running"] == 1
