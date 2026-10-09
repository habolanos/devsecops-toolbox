#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — AWS paridad GCP restante (Tools 52-54)

- apprunner checker (equiv. gcp_cloudrun_checker)
- iam service accounts checker (equiv. gcp_service_account_checker)
- iam multi-account reporter (equiv. gcp_sa_multi_project_reporter)
"""

import importlib.util
import sys
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

_AWS = Path(__file__).parent.parent.parent / "aws"


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name,
                                                  _AWS / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# aws_ecs_common primero (los otros lo importan por path)
_load("aws_ecs_common", "ecs/aws_ecs_common.py")
apprunner = _load("aws_apprunner_checker",
                  "apprunner/aws_apprunner_checker.py")
sac = _load("aws_iam_service_accounts_checker",
            "iam/aws_iam_service_accounts_checker.py")
reporter = _load("aws_iam_multi_account_reporter",
                 "iam/aws_iam_multi_account_reporter.py")


NOW = datetime.now(timezone.utc)


# ═══════════ apprunner ═══════════

def _svc(**kw):
    base = {
        "ServiceName": "api", "Status": "RUNNING",
        "ServiceUrl": "x.awsapprunner.com",
        "CreatedAt": NOW - timedelta(days=30),
        "SourceConfiguration": {
            "ImageRepository": {
                "ImageIdentifier": "123.dkr.ecr.us/r:1",
                "ImageRepositoryType": "ECR"},
            "AutoDeploymentsEnabled": True},
        "NetworkConfiguration": {
            "EgressConfiguration": {"EgressType": "VPC"}},
        "InstanceConfiguration": {"Cpu": "1024",
                                  "Memory": "2048"},
        "HealthCheckConfiguration": {"Protocol": "HTTP",
                                     "Interval": 5},
    }
    base.update(kw)
    return base


class TestAppRunner:
    def test_source_image(self):
        info = apprunner.source_info(_svc())
        assert info["type"] == "image/ECR"
        assert info["auto_deploy"] is True

    def test_source_code(self):
        info = apprunner.source_info(_svc(
            SourceConfiguration={
                "CodeRepository": {
                    "RepositoryUrl": "https://github.com/x/y"},
                "AutoDeploymentsEnabled": False}))
        assert info["type"] == "code/github"

    def test_running_no_critical_findings(self):
        r = apprunner.analyze(_svc())
        assert r["status"] == "RUNNING"
        assert not any("🔴" in f for f in r["findings"])

    def test_create_failed_flagged(self):
        r = apprunner.analyze(_svc(Status="CREATE_FAILED"))
        assert any("CREATE_FAILED" in f for f in r["findings"])

    def test_paused_flagged(self):
        r = apprunner.analyze(_svc(Status="PAUSED"))
        assert any("Pausado" in f for f in r["findings"])

    def test_no_auto_deploy_flagged(self):
        r = apprunner.analyze(_svc(SourceConfiguration={
            "ImageRepository": {"ImageIdentifier": "i:1",
                                "ImageRepositoryType": "ECR"},
            "AutoDeploymentsEnabled": False}))
        assert any("Auto-deploys" in f for f in r["findings"])

    def test_age_days_computed(self):
        r = apprunner.analyze(_svc(
            CreatedAt=NOW - timedelta(days=30)))
        assert r["age_days"] == 30

    def test_describe_error_tolerated(self):
        client = MagicMock()
        client.describe_service.side_effect = Exception("x")
        r = apprunner.describe_service(client, "arn:x/y/1")
        assert r["Status"] == "DESCRIBE_ERROR"


# ═══════════ iam_service_accounts_checker ═══════════

def _role(name, principals, last_used=None):
    return {
        "RoleName": name, "Arn": f"arn:role/{name}",
        "CreateDate": "2026-01-01",
        "AssumeRolePolicyDocument": {"Statement": [
            {"Principal": {"Service": p}}
            for p in principals]},
        "RoleLastUsed": ({"LastUsedDate": last_used}
                         if last_used else {}),
    }


class TestServiceAccountsChecker:
    def test_roles_with_service_trust(self):
        iam = MagicMock()
        iam.get_paginator.return_value.paginate.return_value = [{
            "Roles": [
                _role("svc-role", ["ecs.amazonaws.com"],
                      NOW - timedelta(days=1)),
                _role("user-role", [],
                      NOW - timedelta(days=1)),
            ]}]
        roles = sac.list_service_roles(iam)
        assert len(roles) == 1
        assert roles[0]["name"] == "svc-role"

    def test_never_used_role_flagged(self):
        roles = [{"name": "r", "days_since_use": -1,
                  "created": "2026-01-01"}]
        f = sac.analyze_roles(roles, 90)
        assert f[0]["type"] == "role_never_used"

    def test_stale_role_info(self):
        roles = [{"name": "r", "days_since_use": 120,
                  "created": "x"}]
        f = sac.analyze_roles(roles, 90)
        assert f[0]["type"] == "role_stale"

    def test_old_active_key_warns(self):
        keys = [{"user": "u", "key_id": "AK1", "status": "Active",
                 "age_days": 200, "last_used_days": 5,
                 "last_service": "s3"}]
        f = sac.analyze_keys(keys, 90)
        assert any(x["type"] == "key_old" for x in f)

    def test_never_used_active_key_warns(self):
        keys = [{"user": "u", "key_id": "AK1", "status": "Active",
                 "age_days": 10, "last_used_days": -1,
                 "last_service": None}]
        f = sac.analyze_keys(keys, 90)
        assert any(x["type"] == "key_never_used" for x in f)

    def test_inactive_key_only_info(self):
        keys = [{"user": "u", "key_id": "AK1",
                 "status": "Inactive", "age_days": 300,
                 "last_used_days": -1, "last_service": None}]
        f = sac.analyze_keys(keys, 90)
        assert all(x["severity"] == "info" for x in f)

    def test_days_ago_none(self):
        assert sac._days_ago(None) == -1

    def test_list_users_paginator_search(self):
        # users con search() en main — verificamos que paginate
        # con dict funciona para list_service_roles
        iam = MagicMock()
        iam.get_paginator.side_effect = lambda op: {
            "list_roles": MagicMock(paginate=lambda: [{
                "Roles": [_role("r", ["lambda.amazonaws.com"],
                                NOW)]}]),
            "list_instance_profiles": MagicMock(
                paginate=lambda: [{"InstanceProfiles": [
                    {"InstanceProfileName": "p1",
                     "Arn": "a", "Roles": [{"RoleName": "r"}],
                     "CreateDate": "x"}]}]),
        }[op]
        roles = sac.list_service_roles(iam)
        profiles = sac.list_instance_profiles(iam)
        assert roles[0]["trusted_services"] == \
            ["lambda.amazonaws.com"]
        assert profiles[0]["roles"] == ["r"]


# ═══════════ iam_multi_account_reporter ═══════════

class TestMultiAccountReporter:
    def test_available_profiles_fallback(self):
        with patch.object(reporter, "boto3") as b:
            b.Session.return_value.available_profiles = ["a", "b"]
            assert reporter.available_profiles() == ["a", "b"]

    def test_available_profiles_exception(self):
        with patch.object(reporter, "boto3") as b:
            b.Session.side_effect = Exception()
            assert reporter.available_profiles() == ["default"]

    def test_account_summary_error(self):
        with patch.object(reporter, "make_session") as ms:
            ms.side_effect = Exception("no creds")
            r = reporter.account_summary("p1", "us-east-1")
            assert r["error"] == "no creds"
            assert r["profile"] == "p1"

    def test_account_summary_counts(self):
        iam = MagicMock()
        sts = MagicMock()
        sts.get_caller_identity.return_value = {
            "Account": "1234"}
        iam.list_account_aliases.return_value = {
            "AccountAliases": ["prod"]}

        def paginator_for(op):
            m = MagicMock()
            pages = {"list_users": [{"Users": [{"UserName": "u1"}]}],
                     "list_roles": [{"Roles": [{"RoleName": "r1"},
                                               {"RoleName": "r2"}]}],
                     "list_policies": [{"Policies": [{}] * 3}],
                     "list_groups": [{"Groups": []}]}
            m.paginate.return_value = pages[op]
            return m
        iam.get_paginator.side_effect = paginator_for
        iam.list_mfa_devices.return_value = {"MFADevices": [{}]}
        iam.list_access_keys.return_value = {
            "AccessKeyMetadata": [{"AccessKeyId": "k1"}]}

        session = MagicMock()
        session.client.side_effect = lambda s: \
            {"iam": iam, "sts": sts}[s]
        with patch.object(reporter, "make_session",
                          return_value=session):
            r = reporter.account_summary("p1", "us-east-1")
        assert r["account"] == "1234"
        assert r["users"] == 1
        assert r["roles"] == 2
        assert r["mfa_pct"] == 100.0
        assert r["access_keys"] == 1
        assert r["error"] is None


# ═══════════ CLI (--help) ═══════════

@pytest.mark.parametrize("mod", [apprunner, sac, reporter])
def test_help(monkeypatch, mod):
    monkeypatch.setattr(sys, "argv", ["x.py", "--help"])
    with pytest.raises(SystemExit) as e:
        mod.get_args()
    assert e.value.code == 0
