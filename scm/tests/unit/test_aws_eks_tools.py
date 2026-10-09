#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — AWS EKS tools (Tools 26, 27, 35, 39)

Cubre la lógica pura de las herramientas EKS portadas desde GCP:
- aws_eks_deployments_off_analyzer   (clasificación, severidad, recomendaciones)
- aws_eks_deploy_dependency_checker  (parsers de conexiones/Secrets Manager)
- aws_eks_deployment_validator       (placeholders, masking, refs)
- aws_eks_pod_connectivity_checker   (resultados, checker init)
"""

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aws.eks import aws_eks_deployments_off_analyzer as off_analyzer
from aws.eks import aws_eks_deploy_dependency_checker as dep_checker
from aws.eks import aws_eks_deployment_validator as validator
from aws.eks import aws_eks_pod_connectivity_checker as conn_checker


# ═══════════════════════════════════════════════════════════════════════════════
# deployments_off_analyzer
# ═══════════════════════════════════════════════════════════════════════════════

def _make_pod(name, phase="Pending", conditions=None, container_states=None):
    cs_list = []
    for state in container_states or []:
        cs_list.append({"name": "app", "ready": False,
                        "restartCount": 5, "state": state})
    return {
        "metadata": {"name": name},
        "status": {"phase": phase,
                   "conditions": conditions or [],
                   "containerStatuses": cs_list},
    }


class TestContainerState:
    def test_running(self):
        cs = {"state": {"running": {"startedAt": "x"}}}
        assert off_analyzer.EKSDeploymentsOffAnalyzer._container_state(
            cs)["type"] == "Running"

    def test_waiting_reason(self):
        cs = {"state": {"waiting": {"reason": "CrashLoopBackOff",
                                    "message": "back-off"}}}
        state = off_analyzer.EKSDeploymentsOffAnalyzer._container_state(cs)
        assert state["type"] == "Waiting"
        assert state["reason"] == "CrashLoopBackOff"

    def test_terminated(self):
        cs = {"state": {"terminated": {"exitCode": 1,
                                       "reason": "Error"}}}
        state = off_analyzer.EKSDeploymentsOffAnalyzer._container_state(cs)
        assert state["type"] == "Terminated"
        assert state["exit_code"] == 1

    def test_unknown(self):
        assert off_analyzer.EKSDeploymentsOffAnalyzer._container_state(
            {})["type"] == "Unknown"


class TestRootCauseClassification:
    def setup_method(self):
        self.analyzer = off_analyzer.EKSDeploymentsOffAnalyzer(
            cluster="test-cluster")

    def test_event_image_pull(self):
        events = [{"reason": "Failed",
                   "message": "Failed to pull image",
                   "type": "Warning"}]
        # reason 'Failed' clasifica como Application Error
        causes = self.analyzer._identify_root_causes([], events)
        assert any(c["category"] == "Application Error"
                   for c in causes if "category" in c)

    def test_event_failed_scheduling(self):
        events = [{"reason": "FailedScheduling",
                   "message": "Insufficient cpu", "type": "Warning"}]
        causes = self.analyzer._identify_root_causes([], events)
        assert causes[0]["category"] == "Resource Constraint"
        assert causes[0]["source"] == "Event"

    def test_container_crashloop(self):
        pods = [{"conditions": [],
                 "container_statuses": [{
                     "name": "app", "ready": False, "restart_count": 10,
                     "state": {"type": "Waiting",
                               "reason": "CrashLoopBackOff",
                               "message": "crash"}}]}]
        causes = self.analyzer._identify_root_causes(pods, [])
        assert causes[0]["reason"] == "CrashLoopBackOff"
        assert causes[0]["source"] == "Container State"

    def test_pod_condition_unschedulable(self):
        pods = [{"conditions": [{"type": "PodScheduled", "status": "False",
                                 "reason": "Unschedulable",
                                 "message": "0/3 nodes"}],
                 "container_statuses": []}]
        causes = self.analyzer._identify_root_causes(pods, [])
        assert causes[0]["type"] == "PodScheduled"
        assert causes[0]["source"] == "Pod Condition"

    def test_dedup(self):
        events = [{"reason": "FailedScheduling", "message": "x"},
                  {"reason": "FailedScheduling", "message": "y"}]
        causes = self.analyzer._identify_root_causes([], events)
        assert len(causes) == 1


class TestSeverityAndRecommendations:
    def test_severity_critical_on_crashloop(self):
        causes = [{"type": "Waiting", "reason": "CrashLoopBackOff"}]
        assert off_analyzer.EKSDeploymentsOffAnalyzer._calculate_severity(
            causes) == "CRITICAL"

    def test_severity_critical_on_imagepull(self):
        causes = [{"type": "ImagePullBackOff"}]
        assert off_analyzer.EKSDeploymentsOffAnalyzer._calculate_severity(
            causes) == "CRITICAL"

    def test_severity_high_generic(self):
        causes = [{"type": "PodScheduled", "reason": "Unschedulable"}]
        assert off_analyzer.EKSDeploymentsOffAnalyzer._calculate_severity(
            causes) == "HIGH"

    def test_severity_low_empty(self):
        assert off_analyzer.EKSDeploymentsOffAnalyzer._calculate_severity(
            []) == "LOW"

    def test_recommendations_imagepull(self):
        causes = [{"type": "ImagePullBackOff"}]
        recs = off_analyzer.EKSDeploymentsOffAnalyzer._generate_recommendations(
            causes)
        assert any("imagen" in r["action"].lower() for r in recs)
        assert recs[0]["priority"] == "HIGH"

    def test_recommendations_crashloop_critical(self):
        causes = [{"type": "CrashLoopBackOff"}]
        recs = off_analyzer.EKSDeploymentsOffAnalyzer._generate_recommendations(
            causes)
        assert recs[0]["priority"] == "CRITICAL"
        assert any("logs" in s for s in recs[0]["steps"])

    def test_recommendations_scheduling(self):
        causes = [{"type": "FailedScheduling"}]
        recs = off_analyzer.EKSDeploymentsOffAnalyzer._generate_recommendations(
            causes)
        assert any("capacidad" in r["action"].lower() for r in recs)

    def test_recommendations_dedup_types(self):
        causes = [{"type": "ImagePullBackOff"},
                  {"type": "ErrImagePull"}]
        recs = off_analyzer.EKSDeploymentsOffAnalyzer._generate_recommendations(
            causes)
        image_recs = [r for r in recs
                      if "imagen" in r["action"].lower()]
        # ImagePullBackOff y ErrImagePull son tipos distintos → misma acción
        assert len(image_recs) == 2


class TestAnalyzePods:
    def test_filters_by_deployment_name(self):
        analyzer = off_analyzer.EKSDeploymentsOffAnalyzer(cluster="c")
        pods = [
            _make_pod("myapp-abc123", container_states=[
                {"waiting": {"reason": "CrashLoopBackOff"}}]),
            _make_pod("other-xyz", container_states=[]),
        ]
        result = analyzer._analyze_pods("ns", "myapp", pods)
        assert len(result) == 1
        assert result[0]["name"] == "myapp-abc123"
        assert result[0]["restart_count"] == 5

    def test_deployment_events_filtered_and_sorted(self):
        analyzer = off_analyzer.EKSDeploymentsOffAnalyzer(cluster="c")
        events = [
            {"involvedObject": {"name": "myapp-rs-1"},
             "reason": "FailedScheduling", "message": "m1",
             "lastTimestamp": "2024-01-01T00:00:00Z"},
            {"involvedObject": {"name": "myapp-rs-1"},
             "reason": "Failed", "message": "m2",
             "lastTimestamp": "2024-01-02T00:00:00Z"},
            {"involvedObject": {"name": "other-rs"},
             "reason": "Failed", "message": "m3",
             "lastTimestamp": "2024-01-03T00:00:00Z"},
        ]
        filtered = analyzer._deployment_events("ns", "myapp", events)
        assert len(filtered) == 2
        assert filtered[0]["message"] == "m2"  # más reciente primero


class TestNonRunningDeployments:
    def test_detects_non_running(self):
        analyzer = off_analyzer.EKSDeploymentsOffAnalyzer(cluster="c")
        dep_list = {"items": [
            {"metadata": {"name": "ok"}, "status": {"replicas": 2,
                                                    "readyReplicas": 2}},
            {"metadata": {"name": "bad"}, "status": {"replicas": 3,
                                                     "readyReplicas": 1}},
            {"metadata": {"name": "scaled0"}, "status": {"replicas": 0}},
        ]}
        with patch.object(off_analyzer, "kubectl_json",
                          return_value=dep_list):
            result = analyzer._get_non_running_deployments("ns")
        names = [d["name"] for d in result]
        assert "bad" in names and "scaled0" in names and "ok" not in names


class TestExportFunctions:
    def test_export_json(self, tmp_path):
        results = [{"deployment": "app", "severity": "CRITICAL"}]
        out = tmp_path / "r.json"
        off_analyzer.export_json(results, out)
        data = json.loads(out.read_text())
        assert data["deployments"][0]["deployment"] == "app"
        assert data["critical_count"] == 1
        assert "timestamp" in data

    def test_export_csv(self, tmp_path):
        results = [{
            "namespace": "ns", "deployment": "app", "severity": "HIGH",
            "replica_status": {"desired": 2, "ready": 1, "updated": 2,
                               "available": 1},
            "root_causes": [{"type": "Waiting", "reason": "CrashLoop"}],
            "recommendations": [{"action": "Analizar logs"}],
            "pods": [{}], "events": [{}],
        }]
        out = tmp_path / "r.csv"
        off_analyzer.export_csv(results, out)
        content = out.read_text()
        assert "app" in content and "HIGH" in content


# ═══════════════════════════════════════════════════════════════════════════════
# deploy_dependency_checker — parsers
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseConnectionValues:
    def test_jdbc_url(self):
        conns = dep_checker.parse_connection_values(
            "jdbc:postgresql://db.example.com:5432/mydb")
        assert len(conns) == 1
        assert conns[0]["host"] == "db.example.com"
        assert conns[0]["port"] == 5432

    def test_url_default_port(self):
        conns = dep_checker.parse_connection_values(
            "postgres://db.example.com/mydb")
        assert conns[0]["port"] == 5432
        assert conns[0]["type"] == "postgres"

    def test_mysql_default_port(self):
        conns = dep_checker.parse_connection_values(
            "mysql://db.example.com/")
        assert conns[0]["port"] == 3306

    def test_bare_host_port(self):
        conns = dep_checker.parse_connection_values(
            "cache.cluster-xyz.cache.amazonaws.com:6379")
        assert any(c["host"] == "cache.cluster-xyz.cache.amazonaws.com"
                   and c["port"] == 6379 for c in conns)

    def test_ip_port(self):
        conns = dep_checker.parse_connection_values("10.0.1.50:1433")
        assert conns[0]["host"] == "10.0.1.50"
        assert conns[0]["port"] == 1433

    def test_no_duplicates(self):
        conns = dep_checker.parse_connection_values(
            "postgres://h.example.com:5432/db h.example.com:5432")
        matching = [c for c in conns
                    if c["host"] == "h.example.com" and c["port"] == 5432]
        assert len(matching) == 1

    def test_invalid_port_rejected(self):
        conns = dep_checker.parse_connection_values("host.com:99999")
        assert conns == []

    def test_empty(self):
        assert dep_checker.parse_connection_values("") == []
        assert dep_checker.parse_connection_values(None) == []


class TestParseSecretsManagerRefs:
    def test_yaml_format(self):
        value = """
awsSecretsManager:
  secrets:
    db:
      name: "prod/db-creds"
      version: "AWSCURRENT"
"""
        refs = dep_checker.parse_secrets_manager_references(value)
        assert len(refs) == 1
        assert refs[0]["connection_key"] == "db"
        assert refs[0]["secret_id"] == "prod/db-creds"

    def test_secret_id_key(self):
        value = """
secretsManager:
  region: us-east-1
  secrets:
    api:
      secretId: "prod/api-key"
      version: "v1"
"""
        refs = dep_checker.parse_secrets_manager_references(value)
        assert refs[0]["secret_id"] == "prod/api-key"
        assert refs[0]["version"] == "v1"
        assert refs[0]["region"] == "us-east-1"

    def test_no_reference(self):
        assert dep_checker.parse_secrets_manager_references(
            "just a normal string") == []

    def test_empty(self):
        assert dep_checker.parse_secrets_manager_references("") == []
        assert dep_checker.parse_secrets_manager_references(None) == []


class TestFetchAwsSecret:
    def test_fetches_secret_string(self):
        session = MagicMock()
        client = session.client.return_value
        client.get_secret_value.return_value = {
            "SecretString": '{"user": "u", "pass": "p"}'}
        result = dep_checker.fetch_aws_secret("prod/db", "AWSCURRENT",
                                              session)
        assert result == {"user": "u", "pass": "p"}
        kwargs = client.get_secret_value.call_args[1]
        assert kwargs == {"SecretId": "prod/db"}

    def test_version_stage(self):
        session = MagicMock()
        client = session.client.return_value
        client.get_secret_value.return_value = {"SecretString": "{}"}
        dep_checker.fetch_aws_secret("s", "AWSPREVIOUS", session)
        kwargs = client.get_secret_value.call_args[1]
        assert kwargs["VersionStage"] == "AWSPREVIOUS"

    def test_version_id_uuid(self):
        session = MagicMock()
        client = session.client.return_value
        client.get_secret_value.return_value = {"SecretString": "{}"}
        vid = "12345678-1234-1234-1234-123456789012"
        dep_checker.fetch_aws_secret("s", vid, session)
        kwargs = client.get_secret_value.call_args[1]
        assert kwargs["VersionId"] == vid

    def test_non_json_secret(self):
        session = MagicMock()
        session.client.return_value.get_secret_value.return_value = {
            "SecretString": "raw-password"}
        result = dep_checker.fetch_aws_secret("s", "AWSCURRENT", session)
        assert result == {"raw": "raw-password"}

    def test_none_inputs(self):
        assert dep_checker.fetch_aws_secret("", "v", MagicMock()) is None
        assert dep_checker.fetch_aws_secret("s", "v", None) is None

    def test_client_error_returns_none(self):
        session = MagicMock()
        session.client.return_value.get_secret_value.side_effect = \
            Exception("denied")
        assert dep_checker.fetch_aws_secret("s", "v", session) is None


class TestExtractResourceRefsDepChecker:
    def test_extracts_refs(self):
        dep = {
            "metadata": {"name": "app", "namespace": "prod"},
            "spec": {"template": {"spec": {
                "serviceAccountName": "app-sa",
                "containers": [{
                    "envFrom": [
                        {"configMapRef": {"name": "cm1"}},
                        {"secretRef": {"name": "sec1"}},
                    ],
                    "env": [
                        {"name": "X", "valueFrom":
                            {"configMapKeyRef": {"name": "cm2"}}},
                        {"name": "Y", "valueFrom":
                            {"secretKeyRef": {"name": "sec2"}}},
                    ],
                }],
                "volumes": [
                    {"configMap": {"name": "cm3"}},
                    {"secret": {"secretName": "sec3"}},
                ],
            }}},
        }
        ns, sa, cms, secs = dep_checker.extract_resource_refs(dep)
        assert ns == "prod" and sa == "app-sa"
        assert sorted(cms) == ["cm1", "cm2", "cm3"]
        assert sorted(secs) == ["sec1", "sec2", "sec3"]

    def test_defaults(self):
        dep = {"metadata": {"name": "app"}, "spec": {"template": {
            "spec": {"containers": []}}}}
        ns, sa, cms, secs = dep_checker.extract_resource_refs(dep)
        assert ns == "default" and sa == "default"
        assert cms == [] and secs == []


class TestKubectlJsonDepChecker:
    def test_returns_json(self):
        with patch.object(dep_checker, "run_command",
                          return_value=(0, '{"items": []}', "")):
            assert dep_checker.kubectl_json(["get", "pods"]) == \
                {"items": []}

    def test_failed_command(self):
        with patch.object(dep_checker, "run_command",
                          return_value=(1, "", "error")):
            assert dep_checker.kubectl_json(["get", "pods"]) is None

    def test_invalid_json(self):
        with patch.object(dep_checker, "run_command",
                          return_value=(0, "not json", "")):
            assert dep_checker.kubectl_json(["get", "pods"]) is None


# ═══════════════════════════════════════════════════════════════════════════════
# deployment_validator
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlaceholderAndSensitive:
    @pytest.mark.parametrize("val", ["", "changeme", "TODO", "xxx",
                                     "localhost", "****", "n/a"])
    def test_placeholders(self, val):
        assert validator.is_placeholder_value(val) is True

    @pytest.mark.parametrize("val", ["real-value", "prod.example.com",
                                     "5432"])
    def test_non_placeholders(self, val):
        assert validator.is_placeholder_value(val) is False

    def test_none_placeholder(self):
        assert validator.is_placeholder_value(None) is True

    @pytest.mark.parametrize("key", ["DB_PASSWORD", "api_token",
                                     "SECRET_KEY", "aws_access_key_id"])
    def test_sensitive_keys(self, key):
        assert validator.is_sensitive_key(key) is True

    @pytest.mark.parametrize("key", ["DB_HOST", "APP_NAME", "LOG_LEVEL"])
    def test_non_sensitive_keys(self, key):
        assert validator.is_sensitive_key(key) is False

    def test_mask_value(self):
        assert validator.mask_value("supersecretpass") == "supe********"
        assert validator.mask_value("abc") == "****"
        assert validator.mask_value("") == "****"


class TestParseEndpointsValidator:
    def test_jdbc(self):
        eps = validator.parse_endpoints(
            "jdbc:mysql://db:3306/schema", "cm/db")
        assert eps[0].host == "db" and eps[0].port == 3306

    def test_host_port(self):
        eps = validator.parse_endpoints("redis.svc.local:6379", "cm/x")
        assert eps[0].host == "redis.svc.local" and eps[0].port == 6379

    def test_source_recorded(self):
        eps = validator.parse_endpoints("10.0.0.1:443", "secret/s:k")
        assert eps[0].source == "secret/s:k"

    def test_no_endpoints(self):
        assert validator.parse_endpoints("plain text", "x") == []


class TestValidateConfigmaps:
    def test_missing_configmap_critical(self):
        findings, endpoints = [], []
        with patch.object(validator, "kubectl_json", return_value=None):
            validator.validate_configmaps({"cm-missing"}, "ns",
                                          findings, endpoints)
        assert findings[0].severity == validator.Severity.CRITICAL
        assert findings[0].resource_name == "cm-missing"

    def test_empty_configmap_warns(self):
        findings = []
        cm = {"data": {}}
        with patch.object(validator, "kubectl_json", return_value=cm):
            validator.validate_configmaps({"cm"}, "ns", findings, [])
        assert findings[0].severity == validator.Severity.WARNING

    def test_placeholder_value_warns(self):
        findings = []
        cm = {"data": {"DB_HOST": "changeme"}}
        with patch.object(validator, "kubectl_json", return_value=cm):
            validator.validate_configmaps({"cm"}, "ns", findings, [])
        assert findings[0].severity == validator.Severity.WARNING
        assert "placeholder" in findings[0].message.lower()

    def test_endpoint_extracted(self):
        findings, endpoints = [], []
        cm = {"data": {"DB_URL": "postgres://h:5432/d"}}
        with patch.object(validator, "kubectl_json", return_value=cm):
            validator.validate_configmaps({"cm"}, "ns", findings,
                                          endpoints)
        assert findings == []
        assert endpoints[0].host == "h"


class TestValidateSecrets:
    import base64 as _b64

    def _b64(self, s):
        import base64
        return base64.b64encode(s.encode()).decode()

    def test_missing_secret_critical(self):
        findings = []
        with patch.object(validator, "kubectl_json", return_value=None):
            validator.validate_secrets({"sec"}, "ns", findings, [])
        assert findings[0].severity == validator.Severity.CRITICAL

    def test_placeholder_secret_warns(self):
        findings = []
        sec = {"data": {"password": self._b64("changeme")}}
        with patch.object(validator, "kubectl_json", return_value=sec):
            validator.validate_secrets({"sec"}, "ns", findings, [])
        assert findings[0].severity == validator.Severity.WARNING


class TestValidatorArgs:
    def test_required_deployment(self):
        with patch.object(sys, "argv",
                          ["prog", "--deployment", "app"]):
            args = validator.get_args()
        assert args.deployment == "app"
        assert args.validate == "all"

    def test_validate_choices(self):
        with patch.object(sys, "argv",
                          ["prog", "-d", "app", "--validate", "secrets"]):
            args = validator.get_args()
        assert args.validate == "secrets"


# ═══════════════════════════════════════════════════════════════════════════════
# pod_connectivity_checker
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckResult:
    def test_as_dict(self):
        r = conn_checker.CheckResult(
            "1. EKS", "cluster", conn_checker.CheckStatus.PASS,
            "ok", "fix-it")
        d = r.as_dict()
        assert d["status"] == "PASS" and d["check"] == "cluster"
        assert d["remediation"] == "fix-it"

    def test_status_enum_values(self):
        assert {s.value for s in conn_checker.CheckStatus} == {
            "PASS", "FAIL", "WARN", "INFO", "SKIP"}


def _new_checker(**kwargs):
    """Instancia el checker con boto3.Session mockeada (sin perfil real)."""
    defaults = dict(profile="p", region="us-east-1", cluster_name="c",
                    deployment="app", namespace="ns", rds_instance="db")
    defaults.update(kwargs)
    if conn_checker.BOTO3_AVAILABLE:
        with patch.object(conn_checker.boto3, "Session",
                          return_value=MagicMock()):
            return conn_checker.EKSConnectivityChecker(**defaults)
    return conn_checker.EKSConnectivityChecker(**defaults)


class TestConnectivityCheckerInit:
    def test_defaults(self):
        checker = _new_checker()
        assert checker.namespace == "ns"
        assert checker.results == []
        assert checker.session is not None or \
            not conn_checker.BOTO3_AVAILABLE

    def test_empty_namespace_defaults(self):
        checker = _new_checker(namespace="")
        assert checker.namespace == "default"


class TestCheckDeployment:
    def _checker(self):
        return _new_checker()

    def test_deployment_found(self):
        dep = {"metadata": {"name": "app", "namespace": "ns"},
               "spec": {"template": {"spec": {
                   "serviceAccountName": "app-sa"}}},
               "status": {"replicas": 2, "readyReplicas": 2}}
        sa = {"metadata": {"annotations": {
            "eks.amazonaws.com/role-arn":
                "arn:aws:iam::123:role/app-role"}}}
        checker = self._checker()

        def fake_kubectl(args, debug=False, timeout=60):
            if "deployment" in args:
                return dep
            if "serviceaccount" in args:
                return sa
            return None

        with patch.object(conn_checker, "kubectl_json",
                          side_effect=fake_kubectl):
            checker.check_deployment()

        statuses = {r.name: r.status for r in checker.results}
        assert statuses["deployment"] == conn_checker.CheckStatus.PASS
        assert checker.irsa_role == "arn:aws:iam::123:role/app-role"

    def test_deployment_missing_fails(self):
        checker = self._checker()
        with patch.object(conn_checker, "kubectl_json",
                          return_value=None):
            checker.check_deployment()
        assert any(r.status == conn_checker.CheckStatus.FAIL
                   for r in checker.results)

    def test_replica_warn(self):
        dep = {"metadata": {"name": "app", "namespace": "ns"},
               "spec": {"template": {"spec": {}}},
               "status": {"replicas": 3, "readyReplicas": 1}}
        checker = self._checker()
        with patch.object(conn_checker, "kubectl_json",
                          side_effect=lambda *a, **k: dep
                          if "deployment" in a[0] else None):
            checker.check_deployment()
        assert any(r.name == "replicas"
                   and r.status == conn_checker.CheckStatus.WARN
                   for r in checker.results)


class TestCheckVpc:
    def _checker_with(self, cluster_vpc, rds_vpc):
        checker = _new_checker(deployment="")
        checker.cluster = {"resourcesVpcConfig": {"vpcId": cluster_vpc}}
        checker.rds = {"DBSubnetGroup": {"VpcId": rds_vpc},
                       "Endpoint": {"Address": "h", "Port": 5432}}
        return checker

    def test_same_vpc_pass(self):
        checker = self._checker_with("vpc-1", "vpc-1")
        checker.check_vpc()
        assert checker.results[0].status == conn_checker.CheckStatus.PASS

    def test_different_vpc_warns(self):
        checker = self._checker_with("vpc-1", "vpc-2")
        checker.check_vpc()
        assert checker.results[0].status == conn_checker.CheckStatus.WARN
        assert "peering" in checker.results[0].message

    def test_skip_without_resources(self):
        checker = _new_checker(deployment="")
        checker.check_vpc()
        assert checker.results[0].status == conn_checker.CheckStatus.SKIP


class TestSecurityGroups:
    def _checker(self):
        checker = _new_checker(deployment="")
        checker.rds = {
            "Endpoint": {"Port": 5432},
            "VpcSecurityGroups": [{"VpcSecurityGroupId": "sg-rds",
                                   "Status": "active"}],
        }
        checker.cluster = {"resourcesVpcConfig": {
            "securityGroupIds": ["sg-cluster"],
            "clusterSecurityGroupId": "sg-cp"}}
        return checker

    def _ec2(self, rules):
        ec2 = MagicMock()
        ec2.describe_security_groups.return_value = {
            "SecurityGroups": [{"IpPermissions": rules}]}
        return ec2

    def test_sg_open_to_cluster_pass(self):
        checker = self._checker()
        ec2 = self._ec2([{
            "FromPort": 5432, "ToPort": 5432,
            "UserIdGroupPairs": [{"GroupId": "sg-cluster"}],
            "IpRanges": []}])
        checker._aws = lambda svc: ec2
        checker.check_security_groups()
        assert checker.results[0].status == conn_checker.CheckStatus.PASS

    def test_sg_open_to_world_warns(self):
        checker = self._checker()
        ec2 = self._ec2([{
            "FromPort": 0, "ToPort": 65535,
            "UserIdGroupPairs": [],
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        checker._aws = lambda svc: ec2
        checker.check_security_groups()
        assert checker.results[0].status == conn_checker.CheckStatus.WARN

    def test_sg_closed_fails(self):
        checker = self._checker()
        ec2 = self._ec2([{
            "FromPort": 22, "ToPort": 22,
            "UserIdGroupPairs": [{"GroupId": "sg-other"}],
            "IpRanges": []}])
        checker._aws = lambda svc: ec2
        checker.check_security_groups()
        assert checker.results[0].status == conn_checker.CheckStatus.FAIL
        assert "authorize-security-group-ingress" in \
            checker.results[0].remediation

    def test_port_not_covered_fails(self):
        checker = self._checker()
        ec2 = self._ec2([{
            "FromPort": 3306, "ToPort": 3306,
            "UserIdGroupPairs": [{"GroupId": "sg-cluster"}],
            "IpRanges": []}])
        checker._aws = lambda svc: ec2
        checker.check_security_groups()
        # :3306 ≠ :5432 → no cubre
        assert checker.results[0].status == conn_checker.CheckStatus.FAIL


class TestArgsParsing:
    def test_connectivity_args(self):
        with patch.object(sys, "argv",
                          ["prog", "--rds-instance", "mydb",
                           "--cluster", "eks", "--deployment", "app"]):
            args = conn_checker.get_args()
        assert args.rds_instance == "mydb"
        assert args.cluster == "eks"
        assert args.timeout == conn_checker.DEFAULT_TIMEOUT

    def test_analyzer_args(self):
        with patch.object(sys, "argv",
                          ["prog", "--cluster", "eks", "-o", "json"]):
            args = off_analyzer.get_args()
        assert args.cluster == "eks" and args.output == "json"

    def test_dep_checker_args(self):
        with patch.object(sys, "argv",
                          ["prog", "--deployment", "app",
                           "--namespace", "ns"]):
            args = dep_checker.get_args()
        assert args.deployment == "app"
        assert args.namespace == "ns"
