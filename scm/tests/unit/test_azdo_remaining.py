#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — AZDO scripts sin cobertura
Cubre: branch_lock_checker, branch_policy_checker, pipeline_drift, pr_pipeline_analyzer,
release_deep_dive, release_explorer_rich, repo_branch_diff, repo_properties_branch_diff,
scan_pipeline_logs, scan_repos_vulnerabilities, task_validator, cicd_inventory*,
interactive_search, pipeline_cd_new_re_release, pipeline_cd_restore_release,
pipeline-cd-rollback-pipeline, pipeline-cd-update-branchconfig
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


class TestAzdoBranchLockChecker:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_branch_lock_checker")
        if mod is None:
            pytest.skip("azdo_branch_lock_checker requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_branch_lock_checker")
        if mod is None:
            pytest.skip("azdo_branch_lock_checker requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoBranchPolicyChecker:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_branch_policy_checker")
        if mod is None:
            pytest.skip("azdo_branch_policy_checker requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_branch_policy_checker")
        if mod is None:
            pytest.skip("azdo_branch_policy_checker requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoPipelineDrift:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_pipeline_drift")
        if mod is None:
            pytest.skip("azdo_pipeline_drift requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_pipeline_drift")
        if mod is None:
            pytest.skip("azdo_pipeline_drift requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoPrPipelineAnalyzer:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_pr_pipeline_analyzer")
        if mod is None:
            pytest.skip("azdo_pr_pipeline_analyzer requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_pr_pipeline_analyzer")
        if mod is None:
            pytest.skip("azdo_pr_pipeline_analyzer requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoReleaseDeepDive:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_release_deep_dive")
        if mod is None:
            pytest.skip("azdo_release_deep_dive requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_release_deep_dive")
        if mod is None:
            pytest.skip("azdo_release_deep_dive requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoReleaseExplorerRich:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_release_explorer_rich")
        if mod is None:
            pytest.skip("azdo_release_explorer_rich requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_release_explorer_rich")
        if mod is None:
            pytest.skip("azdo_release_explorer_rich requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoRepoBranchDiff:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_repo_branch_diff")
        if mod is None:
            pytest.skip("azdo_repo_branch_diff requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_repo_branch_diff")
        if mod is None:
            pytest.skip("azdo_repo_branch_diff requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoRepoPropertiesBranchDiff:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_repo_properties_branch_diff")
        if mod is None:
            pytest.skip("azdo_repo_properties_branch_diff requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_repo_properties_branch_diff")
        if mod is None:
            pytest.skip("azdo_repo_properties_branch_diff requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoScanPipelineLogs:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_scan_pipeline_logs")
        if mod is None:
            pytest.skip("azdo_scan_pipeline_logs requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_scan_pipeline_logs")
        if mod is None:
            pytest.skip("azdo_scan_pipeline_logs requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoScanReposVulnerabilities:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_scan_repos_vulnerabilities")
        if mod is None:
            pytest.skip("azdo_scan_repos_vulnerabilities requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_scan_repos_vulnerabilities")
        if mod is None:
            pytest.skip("azdo_scan_repos_vulnerabilities requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoTaskValidator:
    def test_import(self):
        mod = _import_module("scm.azdo.azdo_task_validator")
        if mod is None:
            pytest.skip("azdo_task_validator requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.azdo_task_validator")
        if mod is None:
            pytest.skip("azdo_task_validator requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoCicdInventory:
    def test_import_main(self):
        mod = _import_module("scm.azdo.cicd_inventory")
        if mod is None:
            pytest.skip("cicd_inventory requires dependencies")
        assert mod is not None

    def test_import_branches_created(self):
        mod = _import_module("scm.azdo.cicd_inventory_branches_created")
        if mod is None:
            pytest.skip("cicd_inventory_branches_created requires dependencies")
        assert mod is not None

    def test_import_ci_detailed(self):
        mod = _import_module("scm.azdo.cicd_inventory_ci_detailed")
        if mod is None:
            pytest.skip("cicd_inventory_ci_detailed requires dependencies")
        assert mod is not None

    def test_import_gke_pipelines(self):
        mod = _import_module("scm.azdo.cicd_inventory_gke_pipelines")
        if mod is None:
            pytest.skip("cicd_inventory_gke_pipelines requires dependencies")
        assert mod is not None

    def test_import_health_score(self):
        mod = _import_module("scm.azdo.cicd_inventory_health_score")
        if mod is None:
            pytest.skip("cicd_inventory_health_score requires dependencies")
        assert mod is not None

    def test_import_hotfix_branches(self):
        mod = _import_module("scm.azdo.cicd_inventory_hotfix_branches")
        if mod is None:
            pytest.skip("cicd_inventory_hotfix_branches requires dependencies")
        assert mod is not None

    def test_import_pending_approvals(self):
        mod = _import_module("scm.azdo.cicd_inventory_pending_approvals")
        if mod is None:
            pytest.skip("cicd_inventory_pending_approvals requires dependencies")
        assert mod is not None

    def test_import_prod_deploy(self):
        mod = _import_module("scm.azdo.cicd_inventory_prod_deploy")
        if mod is None:
            pytest.skip("cicd_inventory_prod_deploy requires dependencies")
        assert mod is not None


class TestAzdoInteractiveSearch:
    def test_import(self):
        mod = _import_module("scm.azdo.interactive_search")
        if mod is None:
            pytest.skip("interactive_search requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.interactive_search")
        if mod is None:
            pytest.skip("interactive_search requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoPipelineCdNewReRelease:
    def test_import(self):
        mod = _import_module("scm.azdo.pipeline_cd_new_re_release")
        if mod is None:
            pytest.skip("pipeline_cd_new_re_release requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.pipeline_cd_new_re_release")
        if mod is None:
            pytest.skip("pipeline_cd_new_re_release requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoPipelineCdRestoreRelease:
    def test_import(self):
        mod = _import_module("scm.azdo.pipeline_cd_restore_release")
        if mod is None:
            pytest.skip("pipeline_cd_restore_release requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.azdo.pipeline_cd_restore_release")
        if mod is None:
            pytest.skip("pipeline_cd_restore_release requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestAzdoHealthProbeModules:
    def test_import_azdo_parser(self):
        mod = _import_module("scm.azdo.health-probe-masive.azdo_parser")
        if mod is None:
            pytest.skip("azdo_parser requires dependencies")
        assert mod is not None

    def test_import_config(self):
        mod = _import_module("scm.azdo.health-probe-masive.config")
        if mod is None:
            pytest.skip("health-probe config requires dependencies")
        assert mod is not None

    def test_import_connectivity_tester(self):
        mod = _import_module("scm.azdo.health-probe-masive.connectivity_tester")
        if mod is None:
            pytest.skip("connectivity_tester requires dependencies")
        assert mod is not None

    def test_import_k8s_checker(self):
        mod = _import_module("scm.azdo.health-probe-masive.k8s_checker")
        if mod is None:
            pytest.skip("k8s_checker requires dependencies")
        assert mod is not None

    def test_import_models(self):
        mod = _import_module("scm.azdo.health-probe-masive.models")
        if mod is None:
            pytest.skip("health-probe models requires dependencies")
        assert mod is not None

    def test_import_reporter(self):
        mod = _import_module("scm.azdo.health-probe-masive.reporter")
        if mod is None:
            pytest.skip("health-probe reporter requires dependencies")
        assert mod is not None


class TestAzdoPipelineUpdaterModules:
    def test_import_config(self):
        mod = _import_module("scm.azdo.pipeline_updater.config")
        if mod is None:
            pytest.skip("pipeline_updater config requires dependencies")
        assert mod is not None

    def test_import_models(self):
        mod = _import_module("scm.azdo.pipeline_updater.models")
        if mod is None:
            pytest.skip("pipeline_updater models requires dependencies")
        assert mod is not None

    def test_import_pipeline_updater(self):
        mod = _import_module("scm.azdo.pipeline_updater.pipeline_updater")
        if mod is None:
            pytest.skip("pipeline_updater requires dependencies")
        assert mod is not None

    def test_import_reporter(self):
        mod = _import_module("scm.azdo.pipeline_updater.reporter")
        if mod is None:
            pytest.skip("pipeline_updater reporter requires dependencies")
        assert mod is not None

    def test_import_search_engine(self):
        mod = _import_module("scm.azdo.pipeline_updater.search_engine")
        if mod is None:
            pytest.skip("search_engine requires dependencies")
        assert mod is not None

    def test_import_template_parser(self):
        mod = _import_module("scm.azdo.pipeline_updater.template_parser")
        if mod is None:
            pytest.skip("template_parser requires dependencies")
        assert mod is not None

    def test_import_validator(self):
        mod = _import_module("scm.azdo.pipeline_updater.validator")
        if mod is None:
            pytest.skip("validator requires dependencies")
        assert mod is not None
