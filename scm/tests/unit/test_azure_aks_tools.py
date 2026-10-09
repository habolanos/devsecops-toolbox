#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Azure AKS/monitoring tools

Cubre la lógica pura de las herramientas AKS (tools 2, 13, 14,
15, 16, 17, 29, 30, 37) sin kubectl ni az reales.
"""

import importlib.util
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


off = _load("aks_deployments_off_analyzer",
            "cluster-aks/aks_deployments_off_analyzer.py")
val = _load("aks_deployment_validator",
            "cluster-aks/aks_deployment_validator.py")
pod_mon = _load("aks_monitor_pod",
                "monitoring/aks_monitor_pod.py")
node_mon = _load("aks_monitor_node",
                 "monitoring/aks_monitor_node.py")
clus = _load("aks_monitor", "cluster-aks/aks_monitor.py")
np_an = _load("aks_nodepool_analyzer",
              "cluster-aks/aks_nodepool_analyzer.py")
psa = _load("pod_security_audit",
            "cluster-aks/pod_security_audit.py")
wi = _load("workload_identity_validator",
           "cluster-aks/workload_identity_validator.py")
acr = _load("acr_analyzer", "cluster-aks/acr_analyzer.py")


def _pod(name, ns, owner, waiting=None, terminated=None,
         scheduled_false=None):
    css = []
    if waiting:
        css.append({"state": {"waiting": {"reason": waiting}}})
    if terminated:
        css.append({"state": {"terminated": terminated}})
    conds = [{"type": "PodScheduled", "status": "False",
              "reason": scheduled_false}] \
        if scheduled_false else []
    return {"metadata": {"name": name, "namespace": ns,
                         "ownerReferences": [{"name": owner}]},
            "status": {"phase": "Pending",
                       "conditions": conds,
                       "containerStatuses": css}}


def _deploy(name, ns, desired, ready):
    return {"metadata": {"name": name, "namespace": ns},
            "spec": {"replicas": desired},
            "status": {"readyReplicas": ready}}


# ═══════════════════════════════════════════════════════════════════════════════
# aks_deployments_off_analyzer (tool 37)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOffClassify:
    def test_crashloop(self):
        assert off._classify("CrashLoopBackOff") == \
            "Application Error"

    def test_image_pull(self):
        assert off._classify("ImagePullBackOff") == \
            "Image Pull Error"

    def test_scheduling_longest_match(self):
        # "FailedScheduling" contiene "Failed" — la clave
        # larga debe ganar
        assert off._classify("FailedScheduling") == \
            "Resource Constraint"

    def test_unknown(self):
        assert off._classify("SomethingWeird") == "Unknown"

    def test_severity_order(self):
        assert off._severity("CrashLoopBackOff") == "critical"
        assert off._severity("FailedScheduling") in \
            ("critical", "high")


class TestOffAnalyze:
    def test_healthy_skipped(self):
        out = off.analyze([_deploy("a", "ns", 2, 2)], [])
        assert out == []

    def test_drained_is_info(self):
        out = off.analyze([_deploy("a", "ns", 0, 0)], [])
        assert out[0]["category"] == "Drained"
        assert out[0]["severity"] == "info"

    def test_crashloop_from_pod(self):
        pods = [_pod("a-1", "ns", "a-abc",
                     waiting="CrashLoopBackOff")]
        out = off.analyze([_deploy("a", "ns", 2, 0)], pods)
        assert out[0]["category"] == "Application Error"
        assert out[0]["severity"] == "critical"
        assert "CrashLoopBackOff" in out[0]["detail"]

    def test_wrong_namespace_ignored(self):
        pods = [_pod("a-1", "other", "a-abc",
                     waiting="CrashLoopBackOff")]
        out = off.analyze([_deploy("a", "ns", 2, 0)], pods)
        assert out[0]["category"] == "Unknown"

    def test_unscheduled_pods(self):
        pods = [_pod("a-1", "ns", "a-abc",
                     scheduled_false="Unschedulable")]
        out = off.analyze([_deploy("a", "ns", 1, 0)], pods)
        assert out[0]["category"] == "Resource Constraint"

    def test_remediation_present(self):
        pods = [_pod("a-1", "ns", "a-abc",
                     waiting="CrashLoopBackOff")]
        out = off.analyze([_deploy("a", "ns", 1, 0)], pods)
        assert out[0]["remediation"]


# ═══════════════════════════════════════════════════════════════════════════════
# aks_deployment_validator (tool 17)
# ═══════════════════════════════════════════════════════════════════════════════

def _deploy_with_refs():
    return {
        "spec": {"template": {"spec": {
            "containers": [{
                "env": [
                    {"name": "A", "valueFrom": {
                        "configMapKeyRef": {
                            "name": "cm1", "key": "k1"}}},
                    {"name": "B", "valueFrom": {
                        "secretKeyRef": {
                            "name": "sec1", "key": "pw"}}},
                ],
                "envFrom": [{"configMapRef": {"name": "cm2"}},
                            {"secretRef": {"name": "sec2"}}],
            }],
            "volumes": [
                {"name": "v1", "configMap": {"name": "cm3"}},
                {"name": "v2", "secret": {"secretName": "sec3"}},
            ]}}}}


class TestValidatorRefs:
    def test_all_ref_kinds(self):
        refs = val.deployment_refs(_deploy_with_refs())
        assert refs["configmaps"] == {"cm1", "cm2", "cm3"}
        assert refs["secrets"] == {"sec1", "sec2", "sec3"}

    def test_keys_referenced(self):
        keys = val.keys_referenced(_deploy_with_refs())
        assert keys["cm1"] == {"k1"}
        assert keys["sec1"] == {"pw"}

    def test_mask(self):
        assert val.mask("supersecret") == "****"
        assert val.mask("abc") == "***"


class TestValidate:
    def test_missing_configmap(self):
        deploy = _deploy_with_refs()
        with patch.object(val, "get_obj",
                          side_effect=lambda k, n, ns:
                          deploy if k == "deployment" else {}):
            result = val.validate("app", "ns", "configmaps")
        missing = [c for c in result["checks"]
                   if c["status"] == "MISSING"]
        assert len(missing) == 3
        assert result["ok"] is False

    def test_placeholder_and_endpoint(self):
        deploy = _deploy_with_refs()
        cm = {"data": {"k1": "CHANGEME",
                       "url": "https://api.example.com:443",
                       "host": "db.internal.net"}}
        def fake_get(kind, name, ns):
            if kind == "deployment":
                return deploy
            if kind == "configmap":
                return cm
            return {"data": {"pw": "e30="}}
        with patch.object(val, "get_obj",
                          side_effect=fake_get):
            result = val.validate("app", "ns", "all")
        assert result["placeholders"]
        assert any("api.example.com" in e["endpoint"] or
                   "db.internal.net" in e["endpoint"]
                   for e in result["endpoints"])

    def test_missing_key_flagged(self):
        deploy = _deploy_with_refs()
        cm = {"data": {"other": "x"}}  # falta 'k1'
        def fake_get(kind, name, ns):
            if kind == "deployment":
                return deploy
            return cm
        with patch.object(val, "get_obj",
                          side_effect=fake_get):
            result = val.validate("app", "ns", "configmaps")
        assert any(c["status"] == "MISSING_KEY"
                   for c in result["checks"])

    def test_deployment_not_found(self):
        with patch.object(val, "get_obj", return_value={}):
            result = val.validate("x", "ns", "all")
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════════
# aks_monitor_pod / aks_monitor_node (tools 29, 30)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPodMetrics:
    def test_parse_top_pods(self):
        text = ("NAMESPACE  NAME     CPU    MEMORY\n"
                "ns1        pod-a    120m   256Mi\n"
                "ns2        pod-b    1      1Gi\n")
        rows = pod_mon.parse_top_pods(text)
        assert rows[0]["pod"] == "pod-a"
        assert rows[1]["namespace"] == "ns2"

    def test_to_millicores(self):
        assert pod_mon.to_millicores("120m") == 120
        assert pod_mon.to_millicores("2") == 2000
        assert pod_mon.to_millicores("bad") == 0

    def test_to_mi(self):
        assert pod_mon.to_mi("256Mi") == 256
        assert pod_mon.to_mi("2Gi") == 2048
        assert pod_mon.to_mi("512Ki") == 0


class TestNodeMetrics:
    def test_parse_top_nodes(self):
        text = ("NAME      CPU(cores)  CPU%   MEMORY(bytes)  "
                "MEMORY%\n"
                "node-1    500m        25%    2048Mi         "
                "40%\n")
        rows = node_mon.parse_top_nodes(text)
        assert rows[0]["node"] == "node-1"
        assert rows[0]["cpu"] == "500m"
        assert rows[0]["cpu_pct"] == 25


# ═══════════════════════════════════════════════════════════════════════════════
# aks_monitor / aks_nodepool_analyzer (tools 13, 14)
# ═══════════════════════════════════════════════════════════════════════════════

class TestClusterAnalysis:
    def test_healthy_cluster(self):
        c = {"name": "aks1", "resourceGroup": "rg",
             "provisioningState": "Succeeded",
             "powerState": {"code": "Running"},
             "enableRBAC": True,
             "apiServerAccessProfile":
                 {"enablePrivateCluster": True},
             "oidcIssuerProfile": {"enabled": True},
             "kubernetesVersion": "1.29",
             "agentPoolProfiles": [
                 {"name": "sys", "orchestratorVersion":
                     "1.29", "count": 3}]}
        r = clus.analyze_cluster(c)
        assert r["findings"] == []
        assert r["private"] is True
        assert r["node_count"] == 3

    def test_public_api_and_no_rbac(self):
        c = {"name": "aks2", "resourceGroup": "rg",
             "provisioningState": "Succeeded",
             "enableRBAC": False,
             "kubernetesVersion": "1.29",
             "agentPoolProfiles": []}
        r = clus.analyze_cluster(c)
        assert any("RBAC" in f for f in r["findings"])
        assert any("público" in f for f in r["findings"])

    def test_version_skew_pool(self):
        c = {"name": "aks3", "provisioningState": "Succeeded",
             "enableRBAC": True,
             "apiServerAccessProfile":
                 {"enablePrivateCluster": True},
             "oidcIssuerProfile": {"enabled": True},
             "kubernetesVersion": "1.29",
             "agentPoolProfiles": [
                 {"name": "old", "orchestratorVersion":
                     "1.27"}]}
        r = clus.analyze_cluster(c)
        assert any("versión distinta" in f
                   for f in r["findings"])


class TestNodePool:
    def test_system_pool_spof(self):
        p = {"name": "system", "mode": "System", "count": 1,
             "enableAutoScaling": True}
        r = np_an.analyze_pool("c", "1.29", p)
        assert any("SPOF" in f for f in r["findings"])

    def test_spot_without_taints(self):
        p = {"name": "spot", "mode": "User", "count": 3,
             "enableAutoScaling": True,
             "scaleSetPriority": "Spot", "nodeTaints": []}
        r = np_an.analyze_pool("c", "1.29", p)
        assert any("Spot" in f for f in r["findings"])

    def test_ok_pool(self):
        p = {"name": "ok", "mode": "User", "count": 3,
             "enableAutoScaling": True,
             "orchestratorVersion": "1.29"}
        r = np_an.analyze_pool("c", "1.29", p)
        assert r["findings"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# pod_security_audit / workload_identity (tools 15, 16)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPodSecurity:
    def test_privileged_critical(self):
        c = {"name": "app", "securityContext":
             {"privileged": True}}
        f = psa.audit_container("p", "ns", c, {})
        assert any(x["type"] == "privileged" and
                   x["sev"] == "critical" for x in f)

    def test_root_unset_medium(self):
        c = {"name": "app", "securityContext": {}}
        f = psa.audit_container("p", "ns", c, {})
        assert any(x["type"] == "root_or_unset" for x in f)

    def test_hardened_container(self):
        c = {"name": "app",
             "securityContext": {
                 "runAsNonRoot": True, "runAsUser": 1000,
                 "readOnlyRootFilesystem": True,
                 "allowPrivilegeEscalation": False,
                 "capabilities": {"drop": ["ALL"]}},
             "resources": {"limits": {"cpu": "500m"}}}
        f = psa.audit_container("p", "ns", c, {})
        assert f == []

    def test_dangerous_caps(self):
        c = {"name": "app", "securityContext": {
            "capabilities": {"add": ["SYS_ADMIN"]}}}
        f = psa.audit_container("p", "ns", c, {})
        assert any(x["type"] == "dangerous_caps" for x in f)


class TestWorkloadIdentity:
    def test_oidc_disabled(self):
        c = {"securityProfile": {"workloadIdentity":
                                 {"enabled": True}}}
        assert any("OIDC" in f
                   for f in wi.check_cluster(c))

    def test_wi_disabled(self):
        c = {"oidcIssuerProfile": {"enabled": True},
             "securityProfile": {}}
        assert any("Workload Identity" in f
                   for f in wi.check_cluster(c))

    def test_fully_enabled(self):
        c = {"oidcIssuerProfile": {"enabled": True},
             "securityProfile": {"workloadIdentity":
                                 {"enabled": True}}}
        assert wi.check_cluster(c) == []


# ═══════════════════════════════════════════════════════════════════════════════
# acr_analyzer (tool 18)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcrAnalyzer:
    def test_findings(self):
        reg = {"name": "myacr", "resourceGroup": "rg",
               "sku": {"name": "Basic"},
               "adminUserEnabled": True,
               "publicNetworkAccess": "Enabled",
               "zoneRedundancy": "Disabled",
               "policies": {}}
        with patch.object(acr, "try_az", return_value=[]):
            r = acr.analyze("sub", reg)
        assert any("admin" in f.lower() or "Admin" in f
                   for f in r["findings"])
        assert r["registry"] == "myacr"
