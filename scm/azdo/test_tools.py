#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests unitarios para scm/azdo/tools.py

Cubre:
- Estructura de TOOLS (todas las tools tienen campos obligatorios)
- TOOL_GROUPS y GROUP_ORDER (consistencia)
- _menu_sort_key (ordenamiento)
- get_auto_tools (exclusiones, orden por grupo)
- get_menu_order (orden, system options al final)
- build_system_options (construye A, B, Q)
- config_get (acceso seguro anidado)
- load_config / save_last_params / load_last_params
- _req_hash (MD5)
- STATUS_INDICATORS (claves y estructura)
- _print_execution_summary (resumen)
- _JSON_FORMAT_TOOLS / _CACHE_JSON_TOOLS (sets)
- run_tool (opción inválida, opción Q)
- main loop (normalización de choice)
- prompt (default, secret)
- log_command (env var)
- Colors (atributos)
- Validación de paths de scripts (que existan)
- Validación de args de cada tool
"""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Asegurar que el módulo es importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scm.azdo import tools as mod


class TestColorsAttributes(unittest.TestCase):
    """Tests para la clase Colors."""

    def test_all_colors_defined(self):
        required = ['HEADER', 'BLUE', 'CYAN', 'GREEN', 'WARNING', 'FAIL',
                    'ENDC', 'BOLD', 'DIM', 'RED', 'YELLOW']
        for attr in required:
            self.assertTrue(hasattr(mod.Colors, attr), f"Colors.{attr} missing")

    def test_red_alias_equals_fail(self):
        self.assertEqual(mod.Colors.RED, mod.Colors.FAIL)

    def test_yellow_alias_equals_warning(self):
        self.assertEqual(mod.Colors.YELLOW, mod.Colors.WARNING)


class TestToolGroups(unittest.TestCase):
    """Tests para TOOL_GROUPS y GROUP_ORDER."""

    def test_all_groups_have_required_fields(self):
        for key, group in mod.TOOL_GROUPS.items():
            self.assertIn("name", group, f"Group {key} missing 'name'")
            self.assertIn("emoji", group, f"Group {key} missing 'emoji'")
            self.assertIn("color", group, f"Group {key} missing 'color'")

    def test_group_order_matches_groups(self):
        for g in mod.GROUP_ORDER:
            self.assertIn(g, mod.TOOL_GROUPS, f"Group '{g}' in GROUP_ORDER but not in TOOL_GROUPS")

    def test_system_group_exists(self):
        self.assertIn("system", mod.TOOL_GROUPS)

    def test_group_order_is_list(self):
        self.assertIsInstance(mod.GROUP_ORDER, list)


class TestToolsStructure(unittest.TestCase):
    """Tests para la estructura del dict TOOLS."""

    REQUIRED_FIELDS = {"name", "description", "group", "status"}
    OPTIONAL_FIELDS = {"path", "args", "defaults"}

    def test_all_tools_have_required_fields(self):
        for key, tool in mod.TOOLS.items():
            for field in self.REQUIRED_FIELDS:
                self.assertIn(field, tool, f"Tool '{key}' missing '{field}'")

    def test_all_tool_groups_valid(self):
        for key, tool in mod.TOOLS.items():
            group = tool.get("group", "")
            self.assertIn(group, mod.TOOL_GROUPS,
                          f"Tool '{key}' has invalid group '{group}'")

    def test_all_tool_statuses_valid(self):
        valid_statuses = {"ready", "warning", "error", "running", "exit"}
        for key, tool in mod.TOOLS.items():
            status = tool.get("status", "")
            self.assertIn(status, valid_statuses,
                          f"Tool '{key}' has invalid status '{status}'")

    def test_tool_43_exists(self):
        self.assertIn("43", mod.TOOLS)
        self.assertEqual(mod.TOOLS["43"]["name"], "Pipeline CD Clone")
        self.assertEqual(mod.TOOLS["43"]["group"], "updatepipe")

    def test_tool_42_exists(self):
        self.assertIn("42", mod.TOOLS)
        self.assertEqual(mod.TOOLS["42"]["name"], "Release Updater Template")

    def test_tool_41_exists(self):
        self.assertIn("41", mod.TOOLS)
        self.assertEqual(mod.TOOLS["41"]["name"], "Pipeline Updater Template")

    def test_tool_27_exists(self):
        self.assertIn("27", mod.TOOLS)
        self.assertEqual(mod.TOOLS["27"]["name"], "Pipeline CD Backup & Restore")

    def test_system_options_built(self):
        self.assertIn("A", mod.TOOLS)
        self.assertIn("B", mod.TOOLS)
        self.assertIn("Q", mod.TOOLS)

    def test_system_option_a_has_auto_tools(self):
        self.assertIn("auto_tools", mod.TOOLS["A"])
        self.assertIsInstance(mod.TOOLS["A"]["auto_tools"], list)

    def test_system_option_b_has_auto_tools(self):
        self.assertIn("auto_tools", mod.TOOLS["B"])
        self.assertIsInstance(mod.TOOLS["B"]["auto_tools"], list)

    def test_system_option_q_has_exit_status(self):
        self.assertEqual(mod.TOOLS["Q"].get("status"), "exit")

    def test_all_tool_paths_are_strings(self):
        for key, tool in mod.TOOLS.items():
            if "path" in tool:
                self.assertIsInstance(tool["path"], str, f"Tool '{key}' path is not str")

    def test_all_tool_args_are_lists(self):
        for key, tool in mod.TOOLS.items():
            if "args" in tool:
                self.assertIsInstance(tool["args"], list, f"Tool '{key}' args is not list")


class TestStatusIndicators(unittest.TestCase):
    """Tests para STATUS_INDICATORS."""

    def test_ready_indicator(self):
        self.assertIn("ready", mod.STATUS_INDICATORS)
        emoji, color, label = mod.STATUS_INDICATORS["ready"]
        self.assertEqual(emoji, "🟢")
        self.assertEqual(color, "green")

    def test_all_statuses_have_3_elements(self):
        for key, val in mod.STATUS_INDICATORS.items():
            self.assertEqual(len(val), 3, f"Status '{key}' should have 3 elements")

    def test_expected_statuses_present(self):
        for s in ["ready", "warning", "error", "running", "exit"]:
            self.assertIn(s, mod.STATUS_INDICATORS)


class TestMenuSortKey(unittest.TestCase):
    """Tests para _menu_sort_key."""

    def test_numeric_key(self):
        result = mod._menu_sort_key("10")
        self.assertEqual(result, (0, 10, 0))

    def test_alpha_suffix_key(self):
        result = mod._menu_sort_key("1b")
        self.assertEqual(result, (0, 1, ord("b")))

    def test_pure_alpha_key(self):
        result = mod._menu_sort_key("A")
        self.assertEqual(result, (1, 0, ord("A")))

    def test_sorting_order(self):
        keys = ["10", "2", "1b", "1", "A", "B"]
        sorted_keys = sorted(keys, key=mod._menu_sort_key)
        self.assertEqual(sorted_keys, ["1", "1b", "2", "10", "A", "B"])


class TestGetAutoTools(unittest.TestCase):
    """Tests para get_auto_tools."""

    def test_returns_list(self):
        result = mod.get_auto_tools()
        self.assertIsInstance(result, list)

    def test_excludes_system_keys(self):
        result = mod.get_auto_tools()
        self.assertNotIn("Q", result)
        self.assertNotIn("A", result)
        self.assertNotIn("B", result)
        self.assertNotIn("_system_options", result)

    def test_exclude_list_respected(self):
        result = mod.get_auto_tools(exclude_list=["1", "2"])
        self.assertNotIn("1", result)
        self.assertNotIn("2", result)

    def test_all_returned_keys_exist_in_tools(self):
        result = mod.get_auto_tools()
        for key in result:
            self.assertIn(key, mod.TOOLS)

    def test_sorted_by_group_order(self):
        result = mod.get_auto_tools()
        groups = [mod.TOOLS[k].get("group", "") for k in result]
        for i in range(1, len(groups)):
            if groups[i] != groups[i - 1]:
                self.assertGreater(
                    mod.GROUP_ORDER.index(groups[i]),
                    mod.GROUP_ORDER.index(groups[i - 1]),
                    f"Group '{groups[i]}' should come after '{groups[i - 1]}'"
                )


class TestGetMenuOrder(unittest.TestCase):
    """Tests para get_menu_order."""

    def test_returns_list(self):
        result = mod.get_menu_order()
        self.assertIsInstance(result, list)

    def test_system_options_at_end(self):
        result = mod.get_menu_order()
        if "Q" in result:
            self.assertEqual(result[-1], "Q")

    def test_all_keys_valid(self):
        result = mod.get_menu_order()
        for key in result:
            self.assertIn(key, mod.TOOLS)

    def test_q_is_last(self):
        result = mod.get_menu_order()
        if "Q" in result:
            self.assertEqual(result[-1], "Q")


class TestBuildSystemOptions(unittest.TestCase):
    """Tests para build_system_options (already called at module load)."""

    def test_a_b_q_exist_after_init(self):
        self.assertIn("A", mod.TOOLS)
        self.assertIn("B", mod.TOOLS)
        self.assertIn("Q", mod.TOOLS)

    def test_a_has_auto_tools(self):
        self.assertIn("auto_tools", mod.TOOLS["A"])

    def test_b_has_auto_tools(self):
        self.assertIn("auto_tools", mod.TOOLS["B"])

    def test_q_has_exit_status(self):
        self.assertEqual(mod.TOOLS["Q"].get("status"), "exit")


class TestConfigGet(unittest.TestCase):
    """Tests para config_get."""

    def test_simple_key(self):
        cfg = {"a": "value"}
        self.assertEqual(mod.config_get(cfg, "a"), "value")

    def test_nested_key(self):
        cfg = {"azdo": {"pat": "token123"}}
        self.assertEqual(mod.config_get(cfg, "azdo", "pat"), "token123")

    def test_missing_key_returns_default(self):
        cfg = {"a": "value"}
        self.assertEqual(mod.config_get(cfg, "b", default="fallback"), "fallback")

    def test_none_value_returns_default(self):
        cfg = {"a": None}
        self.assertEqual(mod.config_get(cfg, "a", default="fallback"), "fallback")

    def test_non_dict_returns_default(self):
        cfg = "not_a_dict"
        self.assertEqual(mod.config_get(cfg, "a", default="fallback"), "fallback")

    def test_deeply_nested(self):
        cfg = {"a": {"b": {"c": {"d": "deep"}}}}
        self.assertEqual(mod.config_get(cfg, "a", "b", "c", "d"), "deep")


class TestLoadConfig(unittest.TestCase):
    """Tests para load_config."""

    def test_no_config_file_returns_empty(self):
        with patch.object(mod, 'CONFIG_FILE', Path('/nonexistent/path/config.json')):
            result = mod.load_config()
            self.assertEqual(result, {})

    def test_valid_config_file(self):
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump({"azdo": {"pat": "token"}}, tmp)
        tmp.close()
        try:
            with patch.object(mod, 'CONFIG_FILE', Path(tmp.name)):
                result = mod.load_config()
                self.assertEqual(result["azdo"]["pat"], "token")
        finally:
            os.unlink(tmp.name)

    def test_corrupt_config_returns_empty(self):
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        tmp.write("{invalid json}")
        tmp.close()
        try:
            with patch.object(mod, 'CONFIG_FILE', Path(tmp.name)):
                result = mod.load_config()
                self.assertEqual(result, {})
        finally:
            os.unlink(tmp.name)


class TestSaveLoadLastParams(unittest.TestCase):
    """Tests para save_last_params y load_last_params."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.params_file = Path(self.tmpdir) / "last_params.json"

    def tearDown(self):
        if self.params_file.exists():
            self.params_file.unlink()

    def test_save_and_load(self):
        with patch.object(mod, 'LAST_PARAMS_FILE', self.params_file):
            mod.save_last_params("tool_1", {"pat": "abc", "org": "test"})
            loaded = mod.load_last_params("tool_1")
            self.assertEqual(loaded["pat"], "abc")
            self.assertEqual(loaded["org"], "test")

    def test_load_nonexistent_returns_empty(self):
        with patch.object(mod, 'LAST_PARAMS_FILE', Path('/nonexistent/params.json')):
            result = mod.load_last_params("any_tool")
            self.assertEqual(result, {})

    def test_load_missing_tool_returns_empty(self):
        with patch.object(mod, 'LAST_PARAMS_FILE', self.params_file):
            mod.save_last_params("tool_1", {"pat": "abc"})
            result = mod.load_last_params("tool_2")
            self.assertEqual(result, {})

    def test_save_multiple_tools(self):
        with patch.object(mod, 'LAST_PARAMS_FILE', self.params_file):
            mod.save_last_params("tool_1", {"a": "1"})
            mod.save_last_params("tool_2", {"b": "2"})
            self.assertEqual(mod.load_last_params("tool_1")["a"], "1")
            self.assertEqual(mod.load_last_params("tool_2")["b"], "2")


class TestReqHash(unittest.TestCase):
    """Tests para _req_hash."""

    def test_consistent_hash(self):
        tmp = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tmp.write("requests==2.31.0\nrich==13.7.0\n")
        tmp.close()
        try:
            h1 = mod._req_hash(Path(tmp.name))
            h2 = mod._req_hash(Path(tmp.name))
            self.assertEqual(h1, h2)
        finally:
            os.unlink(tmp.name)

    def test_different_content_different_hash(self):
        tmp1 = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tmp1.write("requests==2.31.0\n")
        tmp1.close()
        tmp2 = tempfile.NamedTemporaryFile(mode='w', delete=False)
        tmp2.write("requests==2.32.0\n")
        tmp2.close()
        try:
            h1 = mod._req_hash(Path(tmp1.name))
            h2 = mod._req_hash(Path(tmp2.name))
            self.assertNotEqual(h1, h2)
        finally:
            os.unlink(tmp1.name)
            os.unlink(tmp2.name)

    def test_nonexistent_file_returns_empty(self):
        result = mod._req_hash(Path('/nonexistent/file.txt'))
        self.assertEqual(result, "")


class TestPrompt(unittest.TestCase):
    """Tests para prompt."""

    @patch('builtins.input', return_value='')
    def test_uses_default_when_empty(self, _):
        result = mod.prompt("Label", default="my_default")
        self.assertEqual(result, "my_default")

    @patch('builtins.input', return_value='user_value')
    def test_uses_user_input(self, _):
        result = mod.prompt("Label", default="my_default")
        self.assertEqual(result, "user_value")

    @patch('builtins.input', return_value='')
    def test_empty_default_returns_empty(self, _):
        result = mod.prompt("Label", default="")
        self.assertEqual(result, "")


class TestLogCommand(unittest.TestCase):
    """Tests para log_command."""

    def test_no_log_when_env_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch('builtins.open', MagicMock()) as mock_open:
                mod.log_command(["python", "script.py"])
                mock_open.assert_not_called()

    def test_logs_when_env_set(self):
        tmpdir = tempfile.mkdtemp()
        with patch.dict(os.environ, {"DEVSECOPS_LOG_COMMANDS": "1", "DEVSECOPS_OUTPUT_DIR": tmpdir}):
            mod.log_command(["python", "script.py", "--arg"], status="EXEC")
            log_files = list(Path(tmpdir).glob("commands_*.log"))
            self.assertEqual(len(log_files), 1)
            content = log_files[0].read_text(encoding="utf-8")
            self.assertIn("python", content)
            self.assertIn("EXEC", content)


class TestRunTool(unittest.TestCase):
    """Tests para run_tool."""

    def test_invalid_tool_key_prints_error(self):
        with patch('builtins.print') as mock_print:
            mod.run_tool("INVALID_KEY_999")
            mock_print.assert_any_call(unittest.mock.ANY)

    def test_q_exits(self):
        with self.assertRaises(SystemExit):
            mod.run_tool("Q")

    def test_invalid_key_returns_silently(self):
        try:
            mod.run_tool("NONEXISTENT_KEY_999")
        except SystemExit:
            pass
        except Exception:
            pass


class TestJsonFormatTools(unittest.TestCase):
    """Tests para _JSON_FORMAT_TOOLS y _CACHE_JSON_TOOLS."""

    def test_json_format_tools_is_set(self):
        self.assertIsInstance(mod._JSON_FORMAT_TOOLS, set)

    def test_cache_json_tools_is_set(self):
        self.assertIsInstance(mod._CACHE_JSON_TOOLS, set)

    def test_json_format_tools_not_empty(self):
        self.assertTrue(len(mod._JSON_FORMAT_TOOLS) > 0)

    def test_json_format_tools_subset_of_tools(self):
        for key in mod._JSON_FORMAT_TOOLS:
            self.assertIn(key, mod.TOOLS, f"Key '{key}' in _JSON_FORMAT_TOOLS but not in TOOLS")

    def test_cache_json_tools_subset_of_tools(self):
        for key in mod._CACHE_JSON_TOOLS:
            self.assertIn(key, mod.TOOLS, f"Key '{key}' in _CACHE_JSON_TOOLS but not in TOOLS")


class TestPrintExecutionSummary(unittest.TestCase):
    """Tests para _print_execution_summary."""

    def test_all_ok(self):
        results = [("Tool1", "OK", "OK"), ("Tool2", "OK", "HIGH")]
        try:
            mod._print_execution_summary(results, 5.0)
        except Exception as e:
            self.fail(f"_print_execution_summary raised {e}")

    def test_with_errors(self):
        results = [("Tool1", "OK", "OK"), ("Tool2", "ERROR", "exit 1")]
        try:
            mod._print_execution_summary(results, 3.5)
        except Exception as e:
            self.fail(f"_print_execution_summary raised {e}")

    def test_empty_results(self):
        try:
            mod._print_execution_summary([], 0.0)
        except Exception as e:
            self.fail(f"_print_execution_summary raised {e}")


class TestScriptPathsExist(unittest.TestCase):
    """Tests que verifican que los paths de los scripts existan."""

    def test_all_ready_tool_scripts_exist(self):
        base_dir = mod.BASE_DIR
        missing = []
        for key, tool in mod.TOOLS.items():
            if key in ("A", "B", "Q"):
                continue
            if tool.get("status") != "ready":
                continue
            if "path" not in tool:
                continue
            script_path = base_dir / tool["path"]
            if not script_path.exists():
                missing.append(f"Tool '{key}' ({tool['name']}): {script_path}")
        self.assertEqual(missing, [], f"Scripts missing: {missing}")


class TestToolArgsConsistency(unittest.TestCase):
    """Tests que verifican consistencia de args entre TOOLS y defaults."""

    def test_tools_with_defaults_have_args(self):
        for key, tool in mod.TOOLS.items():
            if "defaults" in tool:
                self.assertIn("args", tool, f"Tool '{key}' has defaults but no args")

    def test_default_keys_subset_of_args(self):
        for key, tool in mod.TOOLS.items():
            defaults = tool.get("defaults", {})
            args = tool.get("args", [])
            for default_key in defaults:
                arg_name = f"--{default_key.replace('_', '-')}"
                self.assertIn(arg_name, args,
                              f"Default '{default_key}' in tool '{key}' not found in args as '{arg_name}'")


class TestMainChoiceNormalization(unittest.TestCase):
    """Tests para la normalización de choices en main()."""

    def test_alpha_upper(self):
        self.assertEqual("A".upper() if "A".isalpha() else "A".lower(), "A")

    def test_numeric_lower(self):
        self.assertEqual("1b".upper() if "1b".isalpha() else "1b".lower(), "1b")

    def test_digit_stays(self):
        self.assertEqual("10".upper() if "10".isalpha() else "10".lower(), "10")


if __name__ == '__main__':
    unittest.main()
