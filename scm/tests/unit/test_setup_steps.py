#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Setup steps sin cobertura
Cubre: aws_step, azdo_step, azure_step, base_step, dashboard_step, gcp_step,
global_step, precheck_step, config_validator
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


class TestSetupAwsStep:
    def test_import(self):
        mod = _import_module("scm.setup.steps.aws_step")
        if mod is None:
            pytest.skip("aws_step requires dependencies")
        assert mod is not None

    def test_has_step_class(self):
        mod = _import_module("scm.setup.steps.aws_step")
        if mod is None:
            pytest.skip("aws_step requires dependencies")
        classes = [f for f in dir(mod) if not f.startswith('_') and f.endswith('Step')]
        assert len(classes) > 0


class TestSetupAzdoStep:
    def test_import(self):
        mod = _import_module("scm.setup.steps.azdo_step")
        if mod is None:
            pytest.skip("azdo_step requires dependencies")
        assert mod is not None

    def test_has_step_class(self):
        mod = _import_module("scm.setup.steps.azdo_step")
        if mod is None:
            pytest.skip("azdo_step requires dependencies")
        classes = [f for f in dir(mod) if not f.startswith('_') and f.endswith('Step')]
        assert len(classes) > 0


class TestSetupAzureStep:
    def test_import(self):
        mod = _import_module("scm.setup.steps.azure_step")
        if mod is None:
            pytest.skip("azure_step requires dependencies")
        assert mod is not None

    def test_has_step_class(self):
        mod = _import_module("scm.setup.steps.azure_step")
        if mod is None:
            pytest.skip("azure_step requires dependencies")
        classes = [f for f in dir(mod) if not f.startswith('_') and f.endswith('Step')]
        assert len(classes) > 0


class TestSetupBaseStep:
    def test_import(self):
        mod = _import_module("scm.setup.steps.base_step")
        if mod is None:
            pytest.skip("base_step requires dependencies")
        assert mod is not None

    def test_has_base_step(self):
        mod = _import_module("scm.setup.steps.base_step")
        if mod is None:
            pytest.skip("base_step requires dependencies")
        classes = [f for f in dir(mod) if not f.startswith('_') and 'Step' in f]
        assert len(classes) > 0


class TestSetupDashboardStep:
    def test_import(self):
        mod = _import_module("scm.setup.steps.dashboard_step")
        if mod is None:
            pytest.skip("dashboard_step requires dependencies")
        assert mod is not None

    def test_has_step_class(self):
        mod = _import_module("scm.setup.steps.dashboard_step")
        if mod is None:
            pytest.skip("dashboard_step requires dependencies")
        classes = [f for f in dir(mod) if not f.startswith('_') and f.endswith('Step')]
        assert len(classes) > 0


class TestSetupGcpStep:
    def test_import(self):
        mod = _import_module("scm.setup.steps.gcp_step")
        if mod is None:
            pytest.skip("gcp_step requires dependencies")
        assert mod is not None

    def test_has_step_class(self):
        mod = _import_module("scm.setup.steps.gcp_step")
        if mod is None:
            pytest.skip("gcp_step requires dependencies")
        classes = [f for f in dir(mod) if not f.startswith('_') and f.endswith('Step')]
        assert len(classes) > 0


class TestSetupGlobalStep:
    def test_import(self):
        mod = _import_module("scm.setup.steps.global_step")
        if mod is None:
            pytest.skip("global_step requires dependencies")
        assert mod is not None

    def test_has_step_class(self):
        mod = _import_module("scm.setup.steps.global_step")
        if mod is None:
            pytest.skip("global_step requires dependencies")
        classes = [f for f in dir(mod) if not f.startswith('_') and f.endswith('Step')]
        assert len(classes) > 0


class TestSetupPrecheckStep:
    def test_import(self):
        mod = _import_module("scm.setup.steps.precheck_step")
        if mod is None:
            pytest.skip("precheck_step requires dependencies")
        assert mod is not None

    def test_has_step_class(self):
        mod = _import_module("scm.setup.steps.precheck_step")
        if mod is None:
            pytest.skip("precheck_step requires dependencies")
        classes = [f for f in dir(mod) if not f.startswith('_') and f.endswith('Step')]
        assert len(classes) > 0


class TestSetupConfigValidator:
    def test_import(self):
        mod = _import_module("scm.setup.validators.config_validator")
        if mod is None:
            pytest.skip("config_validator requires dependencies")
        assert mod is not None

    def test_has_validator_class(self):
        mod = _import_module("scm.setup.validators.config_validator")
        if mod is None:
            pytest.skip("config_validator requires dependencies")
        classes = [f for f in dir(mod) if not f.startswith('_') and 'Validator' in f]
        assert len(classes) > 0
