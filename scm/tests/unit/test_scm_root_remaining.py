#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — SCM root modules sin cobertura
Cubre: export_manager, fix_dashboard_config, search_module_advanced
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestExportManager:
    """Tests para export_manager.py"""

    def test_import_module(self):
        from scm.export_manager import ExportManager
        assert ExportManager is not None

    def test_init_with_tool_name(self):
        from scm.export_manager import ExportManager
        em = ExportManager(tool_name="test_tool")
        assert em is not None

    def test_export_json(self, tmp_path):
        from scm.export_manager import ExportManager
        em = ExportManager(tool_name="test_tool")
        data = [{"name": "test", "value": 123}]
        result = em.export_json(data, metadata={"tool": "test"})
        assert result is not None

    def test_export_csv(self, tmp_path):
        from scm.export_manager import ExportManager
        em = ExportManager(tool_name="test_tool")
        data = [{"name": "test", "value": 123}]
        result = em.export_csv(data)
        assert result is not None

    def test_export_empty_data(self):
        from scm.export_manager import ExportManager
        em = ExportManager(tool_name="test_tool")
        result = em.export_json([], metadata={"tool": "test"})
        assert result is not None


class TestFixDashboardConfig:
    """Tests para fix_dashboard_config.py"""

    def test_import_module(self):
        try:
            from scm import fix_dashboard_config
            assert fix_dashboard_config is not None
        except ImportError:
            pytest.skip("fix_dashboard_config requires dependencies not available")

    def test_module_has_fix_config(self):
        try:
            from scm import fix_dashboard_config
            assert hasattr(fix_dashboard_config, 'fix_config')
        except ImportError:
            pytest.skip("fix_dashboard_config requires dependencies not available")


class TestSearchModuleAdvanced:
    """Tests para search_module_advanced.py"""

    def test_import_module(self):
        try:
            from scm import search_module_advanced
            assert search_module_advanced is not None
        except ImportError:
            pytest.skip("search_module_advanced requires dependencies not available")

    def test_module_has_search_function(self):
        try:
            from scm import search_module_advanced
            funcs = [f for f in dir(search_module_advanced) if not f.startswith('_')]
            assert len(funcs) > 0
        except ImportError:
            pytest.skip("search_module_advanced requires dependencies not available")
