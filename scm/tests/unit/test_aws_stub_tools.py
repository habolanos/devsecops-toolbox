#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — AWS tools antes stubs (Tools 23-25, 28-38, 40)

Cubre la lógica pura de las implementaciones reales:
- rds_comparator, api_gateway_checker, vpc_ip_addresses_checker
- lambda analyzer/cost/health/security
- ecr_image_filter, reports_viewer
- infrastructure/unified/inventory consolidators
- service_linked_roles checker/reporter
"""

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import importlib.util

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

_AWS_DIR = Path(__file__).parent.parent.parent / "aws"


def _load(name: str, rel: str):
    """Carga un módulo por ruta (para dirs como 'lambda/' que no son
    importables como paquete)."""
    spec = importlib.util.spec_from_file_location(name,
                                                  _AWS_DIR / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


from aws.rds import aws_rds_comparator as rds_cmp
from aws.vpc import aws_api_gateway_checker as apigw
from aws.vpc import aws_vpc_ip_addresses_checker as vpcip
lam_an = _load("aws_lambda_analyzer",
               "lambda/aws_lambda_analyzer.py")
lam_cost = _load("aws_lambda_cost_analyzer",
                 "lambda/aws_lambda_cost_analyzer.py")
lam_health = _load("aws_lambda_health_analyzer",
                   "lambda/aws_lambda_health_analyzer.py")
lam_sec = _load("aws_lambda_security_auditor",
                "lambda/aws_lambda_security_auditor.py")
from aws.ecr import aws_ecr_image_filter as ecrf
from aws.inventory import aws_reports_viewer as repv
from aws.inventory import aws_inventory_consolidator as invc
from aws.inventory import aws_unified_infrastructure_dashboard as dash
from aws.iam import aws_service_linked_roles_checker as slrc
from aws.iam import aws_service_linked_roles_reporter as slrr


# ═══════════════════════════════════════════════════════════════════════════════
# rds_comparator
# ═══════════════════════════════════════════════════════════════════════════════

def _rds_instance(**kw):
    base = {
        "DBInstanceIdentifier": "mydb",
        "Engine": "postgres", "EngineVersion": "15.4",
        "DBInstanceClass": "db.t3.medium",
        "AllocatedStorage": 100, "StorageType": "gp3",
        "MultiAZ": True, "PubliclyAccessible": False,
        "StorageEncrypted": True, "BackupRetentionPeriod": 7,
        "AutoMinorVersionUpgrade": True, "DeletionProtection": True,
        "Endpoint": {"Address": "h", "Port": 5432},
        "DBSubnetGroup": {"VpcId": "vpc-1",
                          "DBSubnetGroupName": "dbsub"},
        "DBParameterGroups": [{"DBParameterGroupName": "pg15"}],
        "PerformanceInsightsEnabled": True,
        "MonitoringInterval": 60, "CopyTagsToSnapshot": True,
        "PreferredBackupWindow": "03:00-04:00",
        "PreferredMaintenanceWindow": "sun:04:00-sun:05:00",
    }
    base.update(kw)
    return base


class TestRdsComparator:
    def test_extract_attributes(self):
        attrs = rds_cmp.extract_attributes(_rds_instance())
        assert attrs["engine"] == "postgres"
        assert attrs["engine_version"] == "15.4"
        assert attrs["port"] == 5432
        assert attrs["parameter_group"] == "pg15"

    def test_compare_match(self):
        a = rds_cmp.extract_attributes(_rds_instance())
        comp = rds_cmp.compare_instance(a, dict(a),
                                        rds_cmp.DEFAULT_ATTRIBUTES)
        assert comp["status"] == "MATCH"
        assert comp["differences"] == []

    def test_compare_version_differs(self):
        a1 = rds_cmp.extract_attributes(_rds_instance())
        a2 = rds_cmp.extract_attributes(
            _rds_instance(EngineVersion="16.1"))
        comp = rds_cmp.compare_instance(a1, a2,
                                        rds_cmp.DEFAULT_ATTRIBUTES)
        assert comp["status"] == "VERSION_DIFFERS"
        assert comp["differences"][0]["attribute"] == "engine_version"

    def test_compare_differs(self):
        a1 = rds_cmp.extract_attributes(_rds_instance())
        a2 = rds_cmp.extract_attributes(_rds_instance(MultiAZ=False))
        comp = rds_cmp.compare_instance(a1, a2,
                                        rds_cmp.DEFAULT_ATTRIBUTES)
        assert comp["status"] == "DIFFERS"
        assert comp["differences"][0]["attribute"] == "multi_az"

    def test_compare_all_missing(self):
        i1 = {"db1": _rds_instance()}
        results = rds_cmp.compare_all(i1, {}, ["engine"])
        assert results[0]["presence"] == "ONLY_REGION1"
        assert results[0]["status"] == "MISSING"

    def test_compare_all_filter_instance(self):
        i1 = {"db1": _rds_instance(), "db2": _rds_instance()}
        results = rds_cmp.compare_all(i1, dict(i1), ["engine"],
                                      only_instance="db2")
        assert len(results) == 1 and results[0]["instance"] == "db2"


# ═══════════════════════════════════════════════════════════════════════════════
# api_gateway_checker
# ═══════════════════════════════════════════════════════════════════════════════

class TestApiGateway:
    def test_rest_api_open_method_finding(self):
        client = MagicMock()
        client.get_resources.return_value = {"items": [{
            "path": "/users",
            "resourceMethods": {
                "GET": {"authorizationType": "NONE",
                        "apiKeyRequired": False},
                "POST": {"authorizationType": "AWS_IAM"},
                "OPTIONS": {"authorizationType": "NONE"},
            }}]}
        client.get_authorizers.return_value = {"items": []}
        client.get_stage.return_value = {
            "methodSettings": {"*/*": {"loggingLevel": "OFF"}}}
        api = {"id": "abc", "name": "myapi", "stages": ["prod"],
               "endpointConfiguration": {"types": ["REGIONAL"]}}
        findings = []
        result = apigw.analyze_rest_api(client, api, findings)
        assert result["open_methods"] == 1      # OPTIONS no cuenta
        assert any("sin autorización" in f.message for f in findings)
        assert any("logging" in f.message for f in findings)

    def test_http_api_counts_routes(self):
        client = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [{"Items": [
            {"RouteKey": "GET /a", "AuthorizationType": "JWT"},
            {"RouteKey": "POST /b", "AuthorizationType": "NONE"}]}]
        client.get_paginator.return_value = paginator
        client.get_authorizers.return_value = {"Items": [{
            "AuthorizerType": "JWT"}]}
        client.get_stages.return_value = {"Items": [{
            "StageName": "$default",
            "AccessLogSettings": {"DestinationArn": "x"}}]}
        api = {"ApiId": "x1", "Name": "httpapi",
               "ProtocolType": "HTTP"}
        findings = []
        result = apigw.analyze_http_api(client, api, findings)
        assert result["method_count"] == 2
        assert result["open_methods"] == 1
        assert result["stages"][0]["logging"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# vpc_ip_addresses_checker
# ═══════════════════════════════════════════════════════════════════════════════

class TestVpcIpChecker:
    def test_cidr_total(self):
        assert vpcip.cidr_total_ips("10.0.0.0/24") == 256
        assert vpcip.cidr_total_ips("bad") == 0

    def test_subnet_status_ok(self):
        assert vpcip.subnet_status(200, 251) == "OK"

    def test_subnet_status_exhausted(self):
        assert vpcip.subnet_status(0, 251) == "EXHAUSTED"

    def test_subnet_status_critical(self):
        # usable 251, available 20 → 92% usado
        assert vpcip.subnet_status(20, 251) == "CRITICAL"

    def test_subnet_status_warning(self):
        assert vpcip.subnet_status(60, 251) == "WARNING"

    def test_analyze_subnet(self):
        subnet = {
            "SubnetId": "s-1", "VpcId": "vpc-1",
            "AvailabilityZone": "us-east-1a",
            "CidrBlock": "10.0.1.0/24",
            "AvailableIpAddressCount": 250,
            "Tags": [{"Key": "Name", "Value": "web-subnet"}],
        }
        result = vpcip.analyze_subnet(subnet)
        assert result["name"] == "web-subnet"
        assert result["usable_ips"] == 251     # 256 - 5 reservadas
        assert result["status"] == "OK"

    def test_aggregate_alerts(self):
        subnets = [
            {"name": "s1", "cidr": "10.0.0.0/24", "status":
                "EXHAUSTED", "used_pct": 100, "available_ips": 0},
            {"name": "s2", "cidr": "10.0.1.0/24", "status": "OK",
                "used_pct": 10, "available_ips": 200},
        ]
        alerts = vpcip.aggregate_alerts(subnets)
        assert len(alerts) == 1
        assert "SIN IPs" in alerts[0]


# ═══════════════════════════════════════════════════════════════════════════════
# lambda_analyzer
# ═══════════════════════════════════════════════════════════════════════════════

def _lambda_fn(**kw):
    base = {
        "FunctionName": "my-fn", "Runtime": "python3.12",
        "MemorySize": 256, "Timeout": 30,
        "Environment": {"Variables": {"DB_PASS": "x", "LOG": "info"}},
        "VpcConfig": {"SubnetIds": []},
        "TracingConfig": {"Mode": "PassThrough"},
        "Layers": [],
    }
    base.update(kw)
    return base


class TestLambdaAnalyzer:
    def test_policy_is_public(self):
        assert lam_an.policy_is_public(None) is False
        assert lam_an.policy_is_public({
            "Statement": [{"Effect": "Allow",
                           "Principal": "*"}]}) is True
        assert lam_an.policy_is_public({
            "Statement": [{"Effect": "Allow",
                           "Principal": {"Service": "s3"} }]}) is False

    def test_analyze_function_issues(self):
        client = MagicMock()
        from botocore.exceptions import ClientError
        client.get_policy.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}},
            "GetPolicy")
        fn = _lambda_fn(Runtime="python3.8")
        result = lam_an.analyze_function(client, fn)
        assert "runtime EOL/deprecado" in result["issues"]
        assert "sin VPC" in result["issues"]
        assert "sin DLQ" in result["issues"]
        assert result["sensitive_env_vars"] == ["DB_PASS"]

    def test_analyze_function_clean(self):
        client = MagicMock()
        from botocore.exceptions import ClientError
        client.get_policy.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}},
            "GetPolicy")
        fn = _lambda_fn(
            Environment={"Variables": {"LOG_LEVEL": "info"}},
            VpcConfig={"SubnetIds": ["s-1"]},
            DeadLetterConfig={"TargetArn": "arn:aws:sqs:q"},
            TracingConfig={"Mode": "Active"})
        result = lam_an.analyze_function(client, fn)
        assert result["issues"] == []
        assert result["vpc"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# lambda_cost_analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestLambdaCost:
    def test_estimate_cost_math(self):
        cost = lam_cost.estimate_cost(512, 200, 1_000_000)
        # 0.5 GB * 0.2s * 1e6 = 100000 GB-s → ~$1.6667 + $0.20
        assert cost["gb_seconds"] == 100000.0
        assert cost["request_cost"] == pytest.approx(0.2, abs=0.01)
        assert cost["compute_cost"] == pytest.approx(1.6667, abs=0.01)

    def test_estimate_zero_invocations(self):
        cost = lam_cost.estimate_cost(128, 0, 0)
        assert cost["total_cost"] == 0

    def test_recommendation_zombie(self):
        recs = lam_cost.cost_recommendations(
            {"memory_mb": 256, "invocations": 0,
             "avg_duration_ms": 0})
        assert any("ZOMBIE" in r for r in recs)

    def test_recommendation_oversized(self):
        recs = lam_cost.cost_recommendations(
            {"memory_mb": 3008, "invocations": 1000,
             "avg_duration_ms": 100})
        assert any("reducir" in r for r in recs)

    def test_recommendation_undersized(self):
        recs = lam_cost.cost_recommendations(
            {"memory_mb": 128, "invocations": 1000,
             "avg_duration_ms": 8000})
        assert any("más memoria" in r for r in recs)


# ═══════════════════════════════════════════════════════════════════════════════
# lambda_health_analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestLambdaHealth:
    def test_idle_function(self):
        h = lam_health.compute_health({"invocations": 0})
        assert h["grade"] == "IDLE"
        assert h["score"] is None

    def test_healthy(self):
        h = lam_health.compute_health({
            "invocations": 1000, "errors": 0, "throttles": 0,
            "timeout_s": 30, "duration_p95_ms": 500})
        assert h["grade"] == "HEALTHY"
        assert h["score"] == 100.0

    def test_high_error_rate_failing(self):
        h = lam_health.compute_health({
            "invocations": 100, "errors": 10, "throttles": 50,
            "timeout_s": 3, "duration_p95_ms": 2950})
        assert h["grade"] in ("CRITICAL", "FAILING")
        assert any("error rate" in i for i in h["issues"])
        assert any("throttles" in i for i in h["issues"])

    def test_timeout_risk(self):
        h = lam_health.compute_health({
            "invocations": 100, "errors": 0, "throttles": 0,
            "timeout_s": 10, "duration_p95_ms": 9500})
        assert h["score"] <= 75
        assert any("timeout" in i for i in h["issues"])


# ═══════════════════════════════════════════════════════════════════════════════
# lambda_security_auditor
# ═══════════════════════════════════════════════════════════════════════════════

class TestLambdaSecurity:
    def test_env_aws_key_critical(self):
        findings = []
        lam_sec.check_env_secrets(_lambda_fn(Environment={
            "Variables": {"AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
                          "OTHER": "x"}}), findings)
        assert findings[0].severity == lam_sec.Severity.CRITICAL

    def test_env_secret_name_high(self):
        findings = []
        lam_sec.check_env_secrets(_lambda_fn(Environment={
            "Variables": {"DB_PASSWORD": "hidden"}}), findings)
        assert findings[0].severity == lam_sec.Severity.HIGH

    def test_runtime_eol(self):
        findings = []
        lam_sec.check_config(_lambda_fn(Runtime="nodejs14.x"),
                             findings)
        assert any(f.check == "runtime" for f in findings)

    def test_public_policy_critical(self):
        client = MagicMock()
        client.get_policy.return_value = {"Policy": json.dumps({
            "Statement": [{"Effect": "Allow",
                           "Principal": {"AWS": "*"}}]})}
        findings = []
        lam_sec.check_public_policy(client, _lambda_fn(), findings)
        assert findings[0].severity == lam_sec.Severity.CRITICAL

    def test_function_url_none_auth(self):
        client = MagicMock()
        client.get_function_url_config.return_value = {
            "AuthType": "NONE",
            "FunctionUrl": "https://x.lambda-url.aws"}
        findings = []
        lam_sec.check_function_url(client, _lambda_fn(), findings)
        assert findings[0].severity == lam_sec.Severity.HIGH


# ═══════════════════════════════════════════════════════════════════════════════
# ecr_image_filter
# ═══════════════════════════════════════════════════════════════════════════════

class TestEcrImageFilter:
    @pytest.mark.parametrize("tag", ["1.2.3-dev", "2.0.0-qa",
                                     "10.5.1-prod"])
    def test_semver_tags_kept(self, tag):
        assert ecrf.keep_tag(tag) is True

    @pytest.mark.parametrize("tag", ["latest", "1.2.3-master",
                                     "feature-branch", "v1",
                                     "sha-abc123"])
    def test_non_semver_excluded(self, tag):
        assert ecrf.keep_tag(tag) is False

    def test_all_tags_mode(self):
        assert ecrf.keep_tag("feature-x", semver_only=False) is True
        assert ecrf.keep_tag("latest", semver_only=False) is False

    def test_custom_exclude(self):
        import re
        custom = re.compile(r"-dev$")
        assert ecrf.keep_tag("1.2.3-dev", True, custom) is False
        assert ecrf.keep_tag("1.2.3-qa", True, custom) is True

    def test_filter_tags_list(self):
        out = ecrf.filter_tags(["1.0.0-dev", "latest",
                                "2.0.0-master", "3.0.0-qa"])
        assert out == ["1.0.0-dev", "3.0.0-qa"]

    def test_collect_from_csv(self, tmp_path):
        csv_file = tmp_path / "images.csv"
        csv_file.write_text(
            "repository,tag,fecha_creacion\n"
            "repo1,1.0.0-dev,2024-01-01\n"
            "repo2,2.0.0-qa,2024-01-02\n")
        rows = ecrf.collect_from_csv(str(csv_file))
        assert len(rows) == 2
        assert rows[0]["repository"] == "repo1"
        assert rows[0]["pushed_at"] == "2024-01-01"


# ═══════════════════════════════════════════════════════════════════════════════
# reports_viewer
# ═══════════════════════════════════════════════════════════════════════════════

class TestReportsViewer:
    def test_extract_findings_variants(self):
        assert repv.extract_findings({"findings": [1, 2]}) == [1, 2]
        assert repv.extract_findings({"issues": [1]}) == [1]
        assert repv.extract_findings({"a": {"findings": [1, 2],
                                            "b": "x"}}) == [1, 2]
        assert repv.extract_findings({"nothing": []}) == []

    def test_severity_of(self):
        assert repv.severity_of({"severity": "CRITICAL"}) == "critical"
        assert repv.severity_of({"status": "FAIL"}) == "fail"
        assert repv.severity_of({"grade": "HEALTHY"}) == "healthy"
        assert repv.severity_of({"x": 1}) == "info"

    def test_scan_and_render(self, tmp_path):
        (tmp_path / "report_1.json").write_text(json.dumps({
            "timestamp": "2024-01-01",
            "findings": [{"severity": "critical",
                          "message": "bad thing"},
                         {"severity": "info", "message": "note"}]}))
        reports = repv.scan_reports(tmp_path)
        assert len(reports) == 1
        assert reports[0]["item_count"] == 2
        html_out = repv.render_html(reports)
        assert "bad thing" in html_out
        assert "Chart" in html_out


# ═══════════════════════════════════════════════════════════════════════════════
# inventory_consolidator / unified_dashboard
# ═══════════════════════════════════════════════════════════════════════════════

class TestInventoryConsolidator:
    def test_counters_exist(self):
        for svc in ["ec2", "rds", "lambda", "eks", "ecr", "elb",
                    "vpc"]:
            assert svc in invc.COUNTERS

    def test_count_eks_pagination(self):
        eks = MagicMock()
        eks.list_clusters.side_effect = [
            {"clusters": ["a", "b"], "nextToken": "t"},
            {"clusters": ["c"], "nextToken": None}]
        session = MagicMock()
        session.client.return_value = eks
        assert invc.count_eks(session) == 3


class TestUnifiedDashboard:
    def test_health_score_degradation(self):
        assert dash.health_score([]) == 100
        assert dash.health_score(["🟡 minor"]) == 95
        assert dash.health_score(["🔴 critical"]) == 85
        assert dash.health_score(["🔴 a", "🟠 b", "🟡 c"]) == 70


# ═══════════════════════════════════════════════════════════════════════════════
# service_linked_roles
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlrChecker:
    def test_service_from_slr(self):
        role = {"Path": "/aws-service-role/ec2.amazonaws.com/",
                "Description": "x"}
        assert slrc.service_from_slr(role) == "ec2.amazonaws.com"

    def test_list_slrs_pagination(self):
        iam = MagicMock()
        paginator = MagicMock()
        paginator.paginate.return_value = [{"Roles": [
            {"RoleName": "AWSServiceRoleForEC2",
             "Arn": "arn:x", "CreateDate": "2024-01-01",
             "Path": "/aws-service-role/ec2.amazonaws.com/",
             "Description": "SLR"}]}]
        iam.get_paginator.return_value = paginator
        roles = slrc.list_slrs(iam)
        assert roles[0]["name"] == "AWSServiceRoleForEC2"
        assert roles[0]["service"] == "ec2.amazonaws.com"


class TestSlrReporter:
    def test_expected_slrs_defined(self):
        assert "AWSServiceRoleForRDS" in slrr.EXPECTED_SLRS
        assert slrr.EXPECTED_SLRS["AWSServiceRoleForAmazonEKS"] == \
            "eks.amazonaws.com"


# ═══════════════════════════════════════════════════════════════════════════════
# Arg parsing
# ═══════════════════════════════════════════════════════════════════════════════

class TestArgParsing:
    def test_rds_comparator_args(self):
        with patch.object(sys, "argv",
                          ["prog", "--region1", "us-east-1",
                           "--region2", "eu-west-1"]):
            args = rds_cmp.get_args()
        assert args.region1 == "us-east-1"
        assert args.region2 == "eu-west-1"

    def test_vpc_ip_args(self):
        with patch.object(sys, "argv", ["prog", "--vpc", "vpc-1"]):
            args = vpcip.get_args()
        assert args.vpc == "vpc-1"

    def test_lambda_health_args(self):
        with patch.object(sys, "argv",
                          ["prog", "--function", "fn", "--period",
                           "14"]):
            args = lam_health.get_args()
        assert args.function == "fn" and args.period == 14

    def test_ecr_filter_args(self):
        with patch.object(sys, "argv",
                          ["prog", "--csv-file", "x.csv", "-o",
                           "csv"]):
            args = ecrf.get_args()
        assert args.csv_file == "x.csv"

    def test_slr_reporter_args(self):
        with patch.object(sys, "argv",
                          ["prog", "--profiles", "dev,prod"]):
            args = slrr.get_args()
        assert args.profiles == "dev,prod"

    def test_inventory_args(self):
        with patch.object(sys, "argv",
                          ["prog", "--regions",
                           "us-east-1,us-west-2"]):
            args = invc.get_args()
        assert "us-east-1" in args.regions
