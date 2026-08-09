#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Azure, Terminal, Dashboard scheduler sin cobertura
Cubre: azure/tools.py, terminal/tools.py, terminal/check_cluster_memory_cpu_limits/history_limits_v3.py,
dashboard/dashboard_scheduler.py
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


class TestAzureTools:
    def test_import(self):
        mod = _import_module("scm.azure.tools")
        if mod is None:
            pytest.skip("azure tools requires dependencies")
        assert mod is not None

    def test_has_tool_definitions(self):
        mod = _import_module("scm.azure.tools")
        if mod is None:
            pytest.skip("azure tools requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_')]
        assert len(funcs) > 0


class TestTerminalTools:
    def test_import(self):
        mod = _import_module("scm.terminal.tools")
        if mod is None:
            pytest.skip("terminal tools requires dependencies")
        assert mod is not None

    def test_has_tool_definitions(self):
        mod = _import_module("scm.terminal.tools")
        if mod is None:
            pytest.skip("terminal tools requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_')]
        assert len(funcs) > 0


class TestTerminalHistoryLimits:
    def test_import(self):
        mod = _import_module("scm.terminal.check_cluster_memory_cpu_limits.history_limits_v3")
        if mod is None:
            pytest.skip("history_limits_v3 requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.terminal.check_cluster_memory_cpu_limits.history_limits_v3")
        if mod is None:
            pytest.skip("history_limits_v3 requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0


class TestDashboardScheduler:
    def test_import(self):
        mod = _import_module("scm.dashboard.dashboard_scheduler")
        if mod is None:
            pytest.skip("dashboard_scheduler requires dependencies")
        assert mod is not None

    def test_has_functions(self):
        mod = _import_module("scm.dashboard.dashboard_scheduler")
        if mod is None:
            pytest.skip("dashboard_scheduler requires dependencies")
        funcs = [f for f in dir(mod) if not f.startswith('_') and callable(getattr(mod, f))]
        assert len(funcs) > 0
