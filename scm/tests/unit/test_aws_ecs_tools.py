#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — AWS ECS suite (Tools 44-51)

Cubre: aws_ecs_common helpers, health_analyzer, security_auditor,
cost_analyzer, deployment_validator, dependency_mapper,
traffic_analyzer, vpc_ip_diagnostic, executive_dashboard.
"""

import importlib.util
import json
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

_ECS = Path(__file__).parent.parent.parent / "aws" / "ecs"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name,
                                                  _ECS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


common = _load("aws_ecs_common")
health = _load("aws_ecs_health_analyzer")
security = _load("aws_ecs_security_auditor")
cost = _load("aws_ecs_cost_analyzer")
deployv = _load("aws_ecs_deployment_validator")
depmap = _load("aws_ecs_dependency_mapper")
traffic = _load("aws_ecs_traffic_analyzer")
vpcip = _load("aws_ecs_vpc_ip_diagnostic")
dash = _load("aws_ecs_executive_dashboard")


def svc(**kw):
    base = {
        "serviceName": "my-svc", "status": "ACTIVE",
        "desiredCount": 2, "runningCount": 2, "pendingCount": 0,
        "launchType": "FARGATE",
        "taskDefinition": "arn:aws:ecs:::task-definition/my:1",
        "deployments": [{"status": "PRIMARY",
                         "rolloutState": "COMPLETED",
                         "desiredCount": 2, "runningCount": 2,
                         "taskDefinition": "arn:.../my:1"}],
        "loadBalancers": [], "events": [],
    }
    base.update(kw)
    return base


# ═══════════ aws_ecs_common ═══════════

class TestCommon:
    def test_service_status_healthy(self):
        assert common.service_status(svc()) == "HEALTHY"

    def test_service_status_critical(self):
        assert common.service_status(svc(runningCount=0)) == \
            "CRITICAL"

    def test_service_status_degraded(self):
        assert common.service_status(svc(runningCount=1)) == \
            "DEGRADED"

    def test_service_status_drained(self):
        assert common.service_status(svc(desiredCount=0,
                                         runningCount=0)) == \
            "DRAINED"

    def test_service_status_inactive(self):
        assert common.service_status(svc(status="DRAINING")) == \
            "INACTIVE"

    def test_is_fargate_launch_type(self):
        assert common.is_fargate(svc()) is True

    def test_is_fargate_capacity_provider(self):
        assert common.is_fargate(
            svc(launchType=None, capacityProviderStrategy=[
                {"capacityProvider": "FARGATE_SPOT"}])) is True

    def test_is_fargate_ec2(self):
        assert common.is_fargate(svc(launchType="EC2")) is False

    def test_task_cpu_memory_task_level(self):
        res = common.task_cpu_memory({"cpu": "512",
                                      "memory": "1024"})
        assert res == {"cpu_units": 512, "memory_mb": 1024}

    def test_task_cpu_memory_container_sum(self):
        res = common.task_cpu_memory({"containerDefinitions": [
            {"cpu": 256, "memory": 512},
            {"cpu": 256, "memory": 512}]})
        assert res["memory_mb"] == 1024

    def test_env_secrets_detects(self):
        td = {"containerDefinitions": [{"environment": [
            {"name": "DB_PASSWORD", "value": "x"},
            {"name": "NORMAL", "value": "y"}]}]}
        assert common.env_secrets(td) == ["DB_PASSWORD"]

    def test_service_lb_targets(self):
        s = svc(loadBalancers=[{"targetGroupArn": "arn:tg/1"},
                               {"loadBalancerName": "x"}])
        assert common.service_lb_targets(s) == ["arn:tg/1"]


# ═══════════ health_analyzer ═══════════

class TestHealth:
    def test_analyze_healthy(self):
        ecs = MagicMock()
        ecs.list_tasks.return_value = {"taskArns": []}
        r = health.analyze_service(ecs, svc(_cluster="prod"))
        assert r["status"] == "HEALTHY"
        assert r["deployments_failed"] == 0

    def test_analyze_failed_rollout(self):
        ecs = MagicMock()
        ecs.list_tasks.return_value = {"taskArns": []}
        r = health.analyze_service(ecs, svc(_cluster="c", deployments=[
            {"rolloutState": "FAILED"}]))
        assert r["deployments_failed"] == 1

    def test_stopped_tasks_reason(self):
        ecs = MagicMock()
        ecs.list_tasks.return_value = {
            "taskArns": ["arn:t/abc"]}
        ecs.describe_tasks.return_value = {"tasks": [{
            "taskArn": "arn:t/abc",
            "stoppedReason": "OutOfMemory",
            "containers": [{"exitCode": 137}]}]}
        out = health.stopped_tasks(ecs, "c", "s")
        assert out[0]["reason"] == "OutOfMemory"
        assert out[0]["exit_code"] == 137

    def test_stopped_tasks_handles_error(self):
        ecs = MagicMock()
        ecs.list_tasks.side_effect = Exception("denied")
        assert health.stopped_tasks(ecs, "c", "s") == []


# ═══════════ security_auditor ═══════════

class TestSecurity:
    def _taskdef(self, **kw):
        td = {"containerDefinitions": [{"name": "app"}],
              "volumes": []}
        td.update(kw)
        return td

    def test_public_ip_high(self):
        ecs = MagicMock()
        ecs.describe_task_definition.return_value = {
            "taskDefinition": self._taskdef()}
        findings = security.audit_service(ecs, svc(
            networkConfiguration={"awsvpcConfiguration":
                                  {"assignPublicIp": "ENABLED"}}))
        assert any(f.check == "public_ip" and
                   f.severity == security.Severity.HIGH
                   for f in findings)

    def test_env_secrets_critical(self):
        ecs = MagicMock()
        ecs.describe_task_definition.return_value = {
            "taskDefinition": self._taskdef(
                containerDefinitions=[{"name": "a", "environment": [
                    {"name": "API_TOKEN", "value": "secret"}]}])}
        findings = security.audit_service(ecs, svc())
        assert any(f.check == "env_secrets" and
                   f.severity == security.Severity.CRITICAL
                   for f in findings)

    def test_privileged_critical(self):
        ecs = MagicMock()
        ecs.describe_task_definition.return_value = {
            "taskDefinition": self._taskdef(
                containerDefinitions=[{"name": "a",
                                       "privileged": True}])}
        findings = security.audit_service(ecs, svc())
        assert any(f.check == "privileged" and
                   f.severity == security.Severity.CRITICAL
                   for f in findings)

    def test_efs_unencrypted_medium(self):
        ecs = MagicMock()
        ecs.describe_task_definition.return_value = {
            "taskDefinition": self._taskdef(volumes=[{
                "name": "v", "efsVolumeConfiguration": {
                    "transitEncryption": "DISABLED"}}])}
        findings = security.audit_service(ecs, svc())
        assert any(f.check == "efs_encryption" for f in findings)

    def test_taskdef_unreachable(self):
        ecs = MagicMock()
        from botocore.exceptions import ClientError
        ecs.describe_task_definition.side_effect = ClientError(
            {"Error": {"Code": "X"}}, "op")
        # sin network flags → sin findings adicionales
        findings = security.audit_service(ecs, svc())
        assert isinstance(findings, list)


# ═══════════ cost_analyzer ═══════════

class TestCost:
    def test_estimate_zero_tasks(self):
        r = cost.estimate_service_cost(svc(runningCount=0),
                                       {"cpu": "512",
                                        "memory": "1024"})
        assert r["monthly_estimate"] == 0

    def test_estimate_formula(self):
        # 1 task × (0.5 vCPU × 0.04048 + 1GB × 0.004445) × 730
        r = cost.estimate_service_cost(svc(runningCount=1),
                                       {"cpu": "512",
                                        "memory": "1024"})
        expected = (0.5 * cost.VCPU_PER_HOUR +
                    1 * cost.GB_PER_HOUR) * cost.HOURS_MONTH
        assert abs(r["monthly_estimate"] - expected) < 0.5


# ═══════════ deployment_validator ═══════════

class TestDeployValidator:
    def _ecs(self, taskdef):
        ecs = MagicMock()
        ecs.describe_task_definition.return_value = {
            "taskDefinition": taskdef}
        return ecs

    def _td(self, **kw):
        td = {"containerDefinitions": [
            {"name": "app", "image": "123.dkr.ecr.us/x:1.2",
             "memory": 512, "healthCheck": {}}]}
        td.update(kw)
        return td

    def test_circuit_breaker_disabled_warns(self):
        ecs = self._ecs(self._td())
        findings = deployv.validate_service(ecs, None, svc())
        assert any(f.check == "circuit_breaker" for f in findings)

    def test_circuit_breaker_enabled_ok(self):
        ecs = self._ecs(self._td())
        s = svc(deploymentConfiguration={
            "deploymentCircuitBreaker": {"enable": True}})
        findings = deployv.validate_service(ecs, None, s)
        assert not any(f.check == "circuit_breaker"
                       for f in findings)

    def test_lb_without_grace_warns(self):
        ecs = self._ecs(self._td())
        s = svc(loadBalancers=[{"targetGroupArn": "arn:tg"}])
        findings = deployv.validate_service(ecs, None, s)
        assert any(f.check == "health_grace" for f in findings)

    def test_latest_tag_warns(self):
        ecs = self._ecs({"containerDefinitions": [
            {"name": "a", "image": "img:latest", "memory": 1}]})
        findings = deployv.validate_service(ecs, None, svc())
        assert any(f.check == "image_tag" for f in findings)

    def test_missing_ecr_image_critical(self):
        ecs = self._ecs({"containerDefinitions": [
            {"name": "a",
             "image": "123.dkr.ecr.us-east-1.amazonaws.com/r:2",
             "memory": 1}]})
        ecr = MagicMock()
        ecr.describe_images.side_effect = Exception("not found")
        findings = deployv.validate_service(ecs, ecr, svc())
        assert any(f.check == "image_missing" and
                   f.severity == deployv.Severity.CRITICAL
                   for f in findings)

    def test_taskdef_unreachable_critical(self):
        ecs = MagicMock()
        from botocore.exceptions import ClientError
        ecs.describe_task_definition.side_effect = ClientError(
            {"Error": {"Code": "X"}}, "op")
        findings = deployv.validate_service(ecs, None, svc())
        assert any(f.check == "taskdef" and
                   f.severity == deployv.Severity.CRITICAL
                   for f in findings)


# ═══════════ dependency_mapper ═══════════

class TestDepMapper:
    def test_service_with_lb(self):
        ecs = MagicMock()
        elbv2 = MagicMock()
        elbv2.describe_target_groups.return_value = {
            "TargetGroups": [{
                "TargetGroupName": "tg-1",
                "LoadBalancerArns": ["arn:lb/app/x/1"]}]}
        m = depmap.build_map(ecs, elbv2, svc(
            loadBalancers=[{"targetGroupArn": "arn:tg/1"}]))
        assert m["load_balancers"] == ["arn:lb/app/x/1"]
        assert m["target_groups"] == ["tg-1"]
        assert not m["internal_only"]

    def test_internal_service(self):
        m = depmap.build_map(MagicMock(), MagicMock(), svc())
        assert m["internal_only"] is True
        assert m["load_balancers"] == []

    def test_tg_lookup_error_tolerated(self):
        elbv2 = MagicMock()
        elbv2.describe_target_groups.side_effect = Exception()
        m = depmap.build_map(MagicMock(), elbv2, svc(
            loadBalancers=[{"targetGroupArn": "arn:tg/1"}]))
        assert m["load_balancers"] == []


# ═══════════ traffic_analyzer ═══════════

class TestTraffic:
    def test_deployments_parsed(self):
        r = traffic.analyze_service(MagicMock(), MagicMock(),
                                    svc(_cluster="c"), 24)
        assert r["deployments"][0]["status"] == "PRIMARY"
        assert r["active_rollouts"] == 0

    def test_rollouts_counted(self):
        s = svc(deployments=[
            {"rolloutState": "IN_PROGRESS"},
            {"rolloutState": "FAILED"}])
        r = traffic.analyze_service(MagicMock(), MagicMock(), s, 24)
        assert r["active_rollouts"] == 1
        assert r["failed_rollouts"] == 1

    def test_tg_requests_sums_datapoints(self):
        cw = MagicMock()
        cw.get_metric_statistics.return_value = {
            "Datapoints": [{"Sum": 100.0}, {"Sum": 50.0}]}
        total = traffic.tg_requests(
            cw, "arn:...:targetgroup/tg/1",
            "arn:...:loadbalancer/app/lb/1", 24)
        assert total == 150.0

    def test_tg_requests_error_returns_zero(self):
        cw = MagicMock()
        cw.get_metric_statistics.side_effect = Exception()
        assert traffic.tg_requests(
            cw, "x/targetgroup/t/1", "x/loadbalancer/a/1", 1) == 0.0


# ═══════════ vpc_ip_diagnostic ═══════════

class TestVpcIp:
    def _subnets(self):
        return {"s1": {"cidr": "10.0.0.0/24", "total": 256,
                       "usable": 251, "available": 200}}

    def test_ok_headroom(self):
        s = svc(networkConfiguration={
            "awsvpcConfiguration": {"subnets": ["s1"]}})
        r = vpcip.diagnose_service(s, self._subnets())
        assert r["status"] == "OK"
        assert r["subnets"][0]["headroom"] == 200

    def test_low_headroom_warns(self):
        subnets = self._subnets()
        subnets["s1"]["available"] = 5
        s = svc(networkConfiguration={
            "awsvpcConfiguration": {"subnets": ["s1"]}})
        r = vpcip.diagnose_service(s, subnets)
        assert r["status"] == "WARNING"

    def test_no_ips_critical(self):
        subnets = self._subnets()
        subnets["s1"]["available"] = 0
        s = svc(desiredCount=5, runningCount=0,
                networkConfiguration={
                    "awsvpcConfiguration": {"subnets": ["s1"]}})
        r = vpcip.diagnose_service(s, subnets)
        assert r["status"] == "CRITICAL"

    def test_no_awsvpc_config(self):
        r = vpcip.diagnose_service(svc(), {})
        assert any("awsvpc" in i for i in r["issues"])


# ═══════════ executive_dashboard ═══════════

class TestDashboard:
    def test_collect_kpis(self):
        ecs = MagicMock()
        ecs.get_paginator.return_value.paginate.side_effect = [
            [{"clusterArns": ["arn:cluster/prod"]}],
            [{"serviceArns": ["arn:service/prod/s1"]}]]
        ecs.describe_services.return_value = {
            "services": [svc()]}
        data = dash.collect(ecs)
        assert data["clusters"] == 1
        assert len(data["services"]) == 1
        assert data["status_counts"]["HEALTHY"] == 1
        assert data["total_running"] == 2


# ═══════════ CLI (--help) ═══════════

MODS = [health, security, cost, deployv, depmap, traffic,
        vpcip, dash]


@pytest.mark.parametrize("mod", MODS)
def test_help(monkeypatch, mod):
    monkeypatch.setattr(sys, "argv", ["x.py", "--help"])
    with pytest.raises(SystemExit) as e:
        mod.get_args()
    assert e.value.code == 0
