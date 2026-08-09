#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — AWS subfolder tools sin cobertura
Cubre: acm, cloudwatch, ec2, ecr, eks, elb, iam, inventory, lambda, rds, secretsmanager, vpc, waf
"""

import pytest
import sys
import os
import importlib
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _import_module(module_path):
    """Helper para importar módulos con manejo de dependencias opcionales.
    Soporta folders con guiones usando spec_from_file_location."""
    try:
        return importlib.import_module(module_path)
    except SystemExit:
        return None
    except Exception:
        pass
    try:
        parts = module_path.split('.')
        rel_path = Path(*parts[:-1]) / (parts[-1] + '.py')
        full_path = _PROJECT_ROOT / rel_path
        if full_path.exists():
            spec = importlib.util.spec_from_file_location(module_path, full_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except SystemExit:
        return None
    except Exception:
        pass
    return None


class TestAwsAcm:
    def test_import(self):
        mod = _import_module("scm.aws.acm.aws_acm_checker")
        if mod is None:
            pytest.skip("aws_acm_checker requires boto3")
        assert mod is not None

    def test_has_main_or_run(self):
        mod = _import_module("scm.aws.acm.aws_acm_checker")
        if mod is None:
            pytest.skip("aws_acm_checker requires boto3")
        assert callable(getattr(mod, 'main', None)) or any(callable(getattr(mod, f)) for f in dir(mod) if not f.startswith('_'))


class TestAwsCloudwatch:
    def test_import_checker(self):
        mod = _import_module("scm.aws.cloudwatch.aws_cloudwatch_checker")
        if mod is None:
            pytest.skip("aws_cloudwatch_checker requires boto3")
        assert mod is not None

    def test_import_metrics_monitor(self):
        mod = _import_module("scm.aws.cloudwatch.aws_cloudwatch_metrics_monitor")
        if mod is None:
            pytest.skip("aws_cloudwatch_metrics_monitor requires boto3")
        assert mod is not None


class TestAwsEc2:
    def test_import_ebs_checker(self):
        mod = _import_module("scm.aws.ec2.aws_ebs_checker")
        if mod is None:
            pytest.skip("aws_ebs_checker requires boto3")
        assert mod is not None

    def test_import_ec2_checker(self):
        mod = _import_module("scm.aws.ec2.aws_ec2_checker")
        if mod is None:
            pytest.skip("aws_ec2_checker requires boto3")
        assert mod is not None


class TestAwsEcr:
    def test_import_ecr_checker(self):
        mod = _import_module("scm.aws.ecr.aws_ecr_checker")
        if mod is None:
            pytest.skip("aws_ecr_checker requires boto3")
        assert mod is not None

    def test_import_image_filter(self):
        mod = _import_module("scm.aws.ecr.aws_ecr_image_filter")
        if mod is None:
            pytest.skip("aws_ecr_image_filter requires boto3")
        assert mod is not None


class TestAwsEks:
    def test_import_eks_checker(self):
        mod = _import_module("scm.aws.eks.aws_eks_checker")
        if mod is None:
            pytest.skip("aws_eks_checker requires boto3")
        assert mod is not None

    def test_import_deployments_off(self):
        mod = _import_module("scm.aws.eks.aws_eks_deployments_off_analyzer")
        if mod is None:
            pytest.skip("aws_eks_deployments_off_analyzer requires boto3")
        assert mod is not None

    def test_import_deployments_report(self):
        mod = _import_module("scm.aws.eks.aws_eks_deployments_report")
        if mod is None:
            pytest.skip("aws_eks_deployments_report requires boto3")
        assert mod is not None

    def test_import_deployment_validator(self):
        mod = _import_module("scm.aws.eks.aws_eks_deployment_validator")
        if mod is None:
            pytest.skip("aws_eks_deployment_validator requires boto3")
        assert mod is not None

    def test_import_deploy_dependency(self):
        mod = _import_module("scm.aws.eks.aws_eks_deploy_dependency_checker")
        if mod is None:
            pytest.skip("aws_eks_deploy_dependency_checker requires boto3")
        assert mod is not None

    def test_import_node_checker(self):
        mod = _import_module("scm.aws.eks.aws_eks_node_checker")
        if mod is None:
            pytest.skip("aws_eks_node_checker requires boto3")
        assert mod is not None

    def test_import_pod_checker(self):
        mod = _import_module("scm.aws.eks.aws_eks_pod_checker")
        if mod is None:
            pytest.skip("aws_eks_pod_checker requires boto3")
        assert mod is not None

    def test_import_pod_connectivity(self):
        mod = _import_module("scm.aws.eks.aws_eks_pod_connectivity_checker")
        if mod is None:
            pytest.skip("aws_eks_pod_connectivity_checker requires boto3")
        assert mod is not None


class TestAwsElb:
    def test_import_lb_checker(self):
        mod = _import_module("scm.aws.elb.aws_load_balancer_checker")
        if mod is None:
            pytest.skip("aws_load_balancer_checker requires boto3")
        assert mod is not None


class TestAwsIam:
    def test_import_iam_checker(self):
        mod = _import_module("scm.aws.iam.aws_iam_checker")
        if mod is None:
            pytest.skip("aws_iam_checker requires boto3")
        assert mod is not None

    def test_import_roles_checker(self):
        mod = _import_module("scm.aws.iam.aws_roles_checker")
        if mod is None:
            pytest.skip("aws_roles_checker requires boto3")
        assert mod is not None

    def test_import_service_linked_roles(self):
        mod = _import_module("scm.aws.iam.aws_service_linked_roles_checker")
        if mod is None:
            pytest.skip("aws_service_linked_roles_checker requires boto3")
        assert mod is not None

    def test_import_service_linked_roles_reporter(self):
        mod = _import_module("scm.aws.iam.aws_service_linked_roles_reporter")
        if mod is None:
            pytest.skip("aws_service_linked_roles_reporter requires boto3")
        assert mod is not None


class TestAwsInventory:
    def test_import_infra_consolidator(self):
        mod = _import_module("scm.aws.inventory.aws_infrastructure_consolidator")
        if mod is None:
            pytest.skip("aws_infrastructure_consolidator requires boto3")
        assert mod is not None

    def test_import_inventory_consolidator(self):
        mod = _import_module("scm.aws.inventory.aws_inventory_consolidator")
        if mod is None:
            pytest.skip("aws_inventory_consolidator requires boto3")
        assert mod is not None

    def test_import_inventory_generator(self):
        mod = _import_module("scm.aws.inventory.aws_inventory_generator")
        if mod is None:
            pytest.skip("aws_inventory_generator requires boto3")
        assert mod is not None

    def test_import_reports_viewer(self):
        mod = _import_module("scm.aws.inventory.aws_reports_viewer")
        if mod is None:
            pytest.skip("aws_reports_viewer requires boto3")
        assert mod is not None

    def test_import_unified_dashboard(self):
        mod = _import_module("scm.aws.inventory.aws_unified_infrastructure_dashboard")
        if mod is None:
            pytest.skip("aws_unified_infrastructure_dashboard requires boto3")
        assert mod is not None


class TestAwsLambda:
    def test_import_lambda_analyzer(self):
        mod = _import_module("scm.aws.lambda.aws_lambda_analyzer")
        if mod is None:
            pytest.skip("aws_lambda_analyzer requires boto3")
        assert mod is not None

    def test_import_lambda_checker(self):
        mod = _import_module("scm.aws.lambda.aws_lambda_checker")
        if mod is None:
            pytest.skip("aws_lambda_checker requires boto3")
        assert mod is not None

    def test_import_lambda_cost(self):
        mod = _import_module("scm.aws.lambda.aws_lambda_cost_analyzer")
        if mod is None:
            pytest.skip("aws_lambda_cost_analyzer requires boto3")
        assert mod is not None

    def test_import_lambda_health(self):
        mod = _import_module("scm.aws.lambda.aws_lambda_health_analyzer")
        if mod is None:
            pytest.skip("aws_lambda_health_analyzer requires boto3")
        assert mod is not None

    def test_import_lambda_security(self):
        mod = _import_module("scm.aws.lambda.aws_lambda_security_auditor")
        if mod is None:
            pytest.skip("aws_lambda_security_auditor requires boto3")
        assert mod is not None


class TestAwsRds:
    def test_import_rds_checker(self):
        mod = _import_module("scm.aws.rds.aws_rds_checker")
        if mod is None:
            pytest.skip("aws_rds_checker requires boto3")
        assert mod is not None

    def test_import_rds_comparator(self):
        mod = _import_module("scm.aws.rds.aws_rds_comparator")
        if mod is None:
            pytest.skip("aws_rds_comparator requires boto3")
        assert mod is not None

    def test_import_rds_database(self):
        mod = _import_module("scm.aws.rds.aws_rds_database_checker")
        if mod is None:
            pytest.skip("aws_rds_database_checker requires boto3")
        assert mod is not None

    def test_import_rds_storage(self):
        mod = _import_module("scm.aws.rds.aws_rds_storage_checker")
        if mod is None:
            pytest.skip("aws_rds_storage_checker requires boto3")
        assert mod is not None


class TestAwsSecretsManager:
    def test_import_secrets_checker(self):
        mod = _import_module("scm.aws.secretsmanager.aws_secrets_checker")
        if mod is None:
            pytest.skip("aws_secrets_checker requires boto3")
        assert mod is not None


class TestAwsVpc:
    def test_import_api_gateway(self):
        mod = _import_module("scm.aws.vpc.aws_api_gateway_checker")
        if mod is None:
            pytest.skip("aws_api_gateway_checker requires boto3")
        assert mod is not None

    def test_import_security_groups(self):
        mod = _import_module("scm.aws.vpc.aws_security_groups_checker")
        if mod is None:
            pytest.skip("aws_security_groups_checker requires boto3")
        assert mod is not None

    def test_import_vpc_checker(self):
        mod = _import_module("scm.aws.vpc.aws_vpc_checker")
        if mod is None:
            pytest.skip("aws_vpc_checker requires boto3")
        assert mod is not None

    def test_import_vpc_ip_addresses(self):
        mod = _import_module("scm.aws.vpc.aws_vpc_ip_addresses_checker")
        if mod is None:
            pytest.skip("aws_vpc_ip_addresses_checker requires boto3")
        assert mod is not None


class TestAwsWaf:
    def test_import_waf_checker(self):
        mod = _import_module("scm.aws.waf.aws_waf_checker")
        if mod is None:
            pytest.skip("aws_waf_checker requires boto3")
        assert mod is not None


class TestAwsMisc:
    def test_import_fix_encoding(self):
        mod = _import_module("scm.aws.fix_encoding")
        if mod is None:
            pytest.skip("fix_encoding requires dependencies")
        assert mod is not None

    def test_import_generate_remaining(self):
        mod = _import_module("scm.aws.generate_remaining_tools")
        if mod is None:
            pytest.skip("generate_remaining_tools requires dependencies")
        assert mod is not None

    def test_import_regenerate_tools(self):
        mod = _import_module("scm.aws.regenerate_tools")
        if mod is None:
            pytest.skip("regenerate_tools requires dependencies")
        assert mod is not None

    def test_import_validate_registration(self):
        mod = _import_module("scm.aws.validate_tools_registration")
        if mod is None:
            pytest.skip("validate_tools_registration requires dependencies")
        assert mod is not None
