#!/usr/bin/env python3
"""
Tests unitarios para scm/base_launcher.py

Cubre:
- clear_screen()
- print_header()
- print_menu()
- get_menu_order()
- get_auto_tools()
- build_system_options()
- log_command()
- run_tool()
- Colors class
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO

# Agregar scm/ al path para importar base_launcher
sys.path.insert(0, str(Path(__file__).parent.parent / "scm"))

from base_launcher import (
    clear_screen, print_header, print_menu,
    get_menu_order, get_auto_tools, build_system_options,
    log_command, run_tool, Colors, _menu_sort_key
)


class TestColors(unittest.TestCase):
    """Tests para la clase Colors"""
    
    def test_colors_exist(self):
        """Verifica que los códigos de color existan"""
        self.assertTrue(hasattr(Colors, 'HEADER'))
        self.assertTrue(hasattr(Colors, 'BLUE'))
        self.assertTrue(hasattr(Colors, 'CYAN'))
        self.assertTrue(hasattr(Colors, 'GREEN'))
        self.assertTrue(hasattr(Colors, 'WARNING'))
        self.assertTrue(hasattr(Colors, 'FAIL'))
        self.assertTrue(hasattr(Colors, 'ENDC'))
        self.assertTrue(hasattr(Colors, 'BOLD'))
    
    def test_colors_are_strings(self):
        """Verifica que los códigos de color sean strings"""
        self.assertIsInstance(Colors.HEADER, str)
        self.assertIsInstance(Colors.ENDC, str)
        self.assertIsInstance(Colors.BOLD, str)
    
    def test_endc_resets_color(self):
        """Verifica que ENDC sea el código de reset"""
        self.assertEqual(Colors.ENDC, '\033[0m')


class TestMenuSortKey(unittest.TestCase):
    """Tests para la función _menu_sort_key"""
    
    def test_numeric_keys_sorted_first(self):
        """Verifica que las claves numéricas se ordenen primero"""
        result = _menu_sort_key("5")
        self.assertEqual(result[0], 0)  # Tipo 0 = numérico
    
    def test_numeric_keys_ordered_by_value(self):
        """Verifica que las claves numéricas se ordenen por valor"""
        key1 = _menu_sort_key("1")
        key2 = _menu_sort_key("10")
        self.assertLess(key1, key2)
    
    def test_non_numeric_keys_sorted_after(self):
        """Verifica que las claves no numéricas se ordenen después"""
        numeric = _menu_sort_key("5")
        non_numeric = _menu_sort_key("A")
        self.assertLess(numeric, non_numeric)
    
    def test_sorting_mixed_keys(self):
        """Verifica el ordenamiento de claves mixtas"""
        keys = ["10", "2", "A", "1", "Q"]
        sorted_keys = sorted(keys, key=_menu_sort_key)
        # Esperado: 1, 2, 10, A, Q
        self.assertEqual(sorted_keys[0], "1")
        self.assertEqual(sorted_keys[1], "2")
        self.assertEqual(sorted_keys[2], "10")


class TestGetMenuOrder(unittest.TestCase):
    """Tests para la función get_menu_order"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.tools = {
            "1": {"name": "Tool 1", "group": "core"},
            "2": {"name": "Tool 2", "group": "core"},
            "3": {"name": "Tool 3", "group": "analysis"},
            "A": {"name": "Auto Run", "group": "system"},
            "Q": {"name": "Quit", "group": "system"},
        }
        self.group_order = ["core", "analysis", "system"]
    
    def test_returns_list(self):
        """Verifica que retorna una lista"""
        result = get_menu_order(self.tools, self.group_order)
        self.assertIsInstance(result, list)
    
    def test_includes_all_non_system_keys(self):
        """Verifica que incluye todas las claves no del sistema"""
        result = get_menu_order(self.tools, self.group_order)
        self.assertIn("1", result)
        self.assertIn("2", result)
        self.assertIn("3", result)
    
    def test_system_keys_at_end(self):
        """Verifica que las claves del sistema estén al final"""
        result = get_menu_order(self.tools, self.group_order, system_keys=["A", "Q"])
        self.assertEqual(result[-2], "A")
        self.assertEqual(result[-1], "Q")
    
    def test_respects_group_order(self):
        """Verifica que respeta el orden de grupos"""
        result = get_menu_order(self.tools, self.group_order)
        # Las herramientas de "core" deben venir antes que "analysis"
        core_idx = result.index("1")
        analysis_idx = result.index("3")
        self.assertLess(core_idx, analysis_idx)


class TestGetAutoTools(unittest.TestCase):
    """Tests para la función get_auto_tools"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.tools = {
            "1": {"name": "Tool 1", "group": "core"},
            "2": {"name": "Tool 2", "group": "core"},
            "3": {"name": "Tool 3", "group": "analysis"},
            "A": {"name": "Auto Run", "group": "system"},
            "Q": {"name": "Quit", "group": "system"},
        }
        self.group_order = ["core", "analysis", "system"]
    
    def test_returns_list(self):
        """Verifica que retorna una lista"""
        result = get_auto_tools(self.tools, self.group_order)
        self.assertIsInstance(result, list)
    
    def test_excludes_system_keys(self):
        """Verifica que excluye las claves del sistema"""
        result = get_auto_tools(self.tools, self.group_order)
        self.assertNotIn("Q", result)
        self.assertNotIn("A", result)
    
    def test_excludes_specified_keys(self):
        """Verifica que excluye las claves especificadas"""
        result = get_auto_tools(self.tools, self.group_order, exclude_list=["1"])
        self.assertNotIn("1", result)
        self.assertIn("2", result)
    
    def test_includes_regular_tools(self):
        """Verifica que incluye las herramientas regulares"""
        result = get_auto_tools(self.tools, self.group_order)
        self.assertIn("1", result)
        self.assertIn("2", result)
        self.assertIn("3", result)


class TestBuildSystemOptions(unittest.TestCase):
    """Tests para la función build_system_options"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.tools = {
            "1": {"name": "Tool 1", "group": "core"},
            "2": {"name": "Tool 2", "group": "core"},
            "_system_options": {
                "A": {
                    "name": "Auto Run",
                    "description": "Run all tools",
                    "type": "auto_run",
                    "exclude": []
                },
                "Q": {
                    "name": "Quit",
                    "description": "Exit",
                    "type": "exit"
                }
            }
        }
        self.group_order = ["core", "system"]
    
    def test_removes_system_options_key(self):
        """Verifica que elimina la clave _system_options"""
        build_system_options(self.tools, self.group_order)
        self.assertNotIn("_system_options", self.tools)
    
    def test_creates_system_keys(self):
        """Verifica que crea las claves del sistema"""
        build_system_options(self.tools, self.group_order)
        self.assertIn("A", self.tools)
        self.assertIn("Q", self.tools)
    
    def test_auto_run_has_auto_tools(self):
        """Verifica que auto_run tenga auto_tools"""
        build_system_options(self.tools, self.group_order)
        self.assertIn("auto_tools", self.tools["A"])
        self.assertIsInstance(self.tools["A"]["auto_tools"], list)


class TestClearScreen(unittest.TestCase):
    """Tests para la función clear_screen"""
    
    @patch('os.system')
    def test_clear_screen_windows(self, mock_system):
        """Verifica que usa 'cls' en Windows"""
        with patch('platform.system', return_value='Windows'):
            clear_screen()
            mock_system.assert_called_with('cls')
    
    @patch('os.system')
    def test_clear_screen_linux(self, mock_system):
        """Verifica que usa 'clear' en Linux"""
        with patch('platform.system', return_value='Linux'):
            clear_screen()
            mock_system.assert_called_with('clear')


class TestPrintHeader(unittest.TestCase):
    """Tests para la función print_header"""
    
    @patch('base_launcher.clear_screen')
    def test_print_header_with_fallback(self, mock_clear):
        """Verifica que imprime el encabezado sin Rich"""
        with patch('builtins.print') as mock_print:
            print_header(
                title="Test Title",
                subtitle="v1.0.0",
                description="Test Description",
                platform_name="TEST"
            )
            # Verifica que se llamó a clear_screen
            mock_clear.assert_called()
    
    def test_print_header_returns_none(self):
        """Verifica que print_header retorna None"""
        with patch('builtins.print'):
            result = print_header(
                title="Test",
                subtitle="v1.0.0",
                description="Test",
                platform_name="TEST"
            )
            self.assertIsNone(result)


class TestLogCommand(unittest.TestCase):
    """Tests para la función log_command"""
    
    @patch.dict(os.environ, {'DEVSECOPS_LOG_COMMANDS': '1'})
    @patch('builtins.open', new_callable=mock_open)
    def test_log_command_writes_to_file(self, mock_file):
        """Verifica que log_command escribe en el archivo"""
        log_command(["python", "test.py"], status="EXEC", platform="test")
        mock_file.assert_called()
    
    @patch.dict(os.environ, {'DEVSECOPS_LOG_COMMANDS': '0'})
    @patch('builtins.open', new_callable=mock_open)
    def test_log_command_skips_if_disabled(self, mock_file):
        """Verifica que log_command se salta si está deshabilitado"""
        log_command(["python", "test.py"], status="EXEC", platform="test")
        mock_file.assert_not_called()


class TestRunTool(unittest.TestCase):
    """Tests para la función run_tool"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.tools = {
            "1": {
                "name": "Test Tool",
                "description": "Test Description",
                "path": "test.py",
                "args": []
            },
            "Q": {
                "name": "Quit",
                "description": "Exit"
            }
        }
        self.base_dir = Path(__file__).parent.parent / "scm"
    
    def test_run_tool_invalid_key(self):
        """Verifica que run_tool maneja claves inválidas"""
        with patch('builtins.print'):
            run_tool("INVALID", self.tools, self.base_dir)
            # No debería lanzar excepción


class TestIntegration(unittest.TestCase):
    """Tests de integración"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.tools = {
            "1": {"name": "Tool 1", "group": "core"},
            "2": {"name": "Tool 2", "group": "core"},
            "3": {"name": "Tool 3", "group": "analysis"},
            "_system_options": {
                "A": {
                    "name": "Auto Run",
                    "description": "Run all",
                    "type": "auto_run",
                    "exclude": []
                },
                "Q": {
                    "name": "Quit",
                    "description": "Exit",
                    "type": "exit"
                }
            }
        }
        self.group_order = ["core", "analysis", "system"]
    
    def test_build_and_get_menu_order(self):
        """Verifica que build_system_options y get_menu_order funcionan juntos"""
        build_system_options(self.tools, self.group_order)
        menu_order = get_menu_order(self.tools, self.group_order, system_keys=["A", "Q"])
        
        # Verifica que el menú tiene los elementos esperados
        self.assertIn("1", menu_order)
        self.assertIn("2", menu_order)
        self.assertIn("3", menu_order)
        self.assertIn("A", menu_order)
        self.assertIn("Q", menu_order)
        
        # Verifica que Q está al final
        self.assertEqual(menu_order[-1], "Q")
    
    def test_get_auto_tools_after_build_system_options(self):
        """Verifica que get_auto_tools funciona después de build_system_options"""
        build_system_options(self.tools, self.group_order)
        auto_tools = get_auto_tools(self.tools, self.group_order)
        
        # Verifica que no incluye claves del sistema
        self.assertNotIn("A", auto_tools)
        self.assertNotIn("Q", auto_tools)
        
        # Verifica que incluye herramientas regulares
        self.assertIn("1", auto_tools)
        self.assertIn("2", auto_tools)
        self.assertIn("3", auto_tools)


if __name__ == '__main__':
    unittest.main()
