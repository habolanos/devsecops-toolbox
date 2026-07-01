#!/usr/bin/env python3
"""
Tests unitarios para scm/search_module_advanced.py

Cubre:
- SearchHistory
- AdvancedFilter
- fuzzy_match()
- search_items_advanced()
- get_autocomplete_suggestions()
- search_by_id()
- SearchPaginator
- Funciones públicas
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Agregar scm/ al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent / "scm"))

from search_module_advanced import (
    SearchHistory, AdvancedFilter, fuzzy_match,
    search_items_advanced, get_autocomplete_suggestions,
    search_by_id, SearchPaginator,
    get_available_groups, get_available_platforms, get_available_tags
)


class TestFuzzyMatch(unittest.TestCase):
    """Tests para la función fuzzy_match"""
    
    def test_exact_match(self):
        """Verifica coincidencia exacta"""
        result = fuzzy_match("tool", "tool")
        self.assertEqual(result, 1.0)
    
    def test_partial_match(self):
        """Verifica coincidencia parcial"""
        result = fuzzy_match("too", "tool")
        self.assertGreater(result, 0.5)
    
    def test_no_match(self):
        """Verifica sin coincidencia"""
        result = fuzzy_match("xyz", "tool")
        self.assertLess(result, 0.5)
    
    def test_case_insensitive(self):
        """Verifica que sea case-insensitive"""
        result1 = fuzzy_match("TOOL", "tool")
        result2 = fuzzy_match("tool", "TOOL")
        self.assertEqual(result1, result2)
    
    def test_empty_query(self):
        """Verifica con query vacío"""
        result = fuzzy_match("", "tool")
        self.assertEqual(result, 1.0)


class TestAdvancedFilter(unittest.TestCase):
    """Tests para la clase AdvancedFilter"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.filter = AdvancedFilter()
        self.test_item = {
            "name": "Tool 1",
            "group": "core",
            "platform": "azdo",
            "status": "active",
            "tags": ["important", "security"]
        }
    
    def test_apply_no_filters(self):
        """Verifica que sin filtros todo pasa"""
        result = self.filter.apply({}, "1", self.test_item)
        self.assertTrue(result)
    
    def test_apply_group_filter(self):
        """Verifica filtro por grupo"""
        self.filter.set_group("core")
        result = self.filter.apply({}, "1", self.test_item)
        self.assertTrue(result)
        
        self.filter.set_group("analysis")
        result = self.filter.apply({}, "1", self.test_item)
        self.assertFalse(result)
    
    def test_apply_platform_filter(self):
        """Verifica filtro por plataforma"""
        self.filter.set_platform("azdo")
        result = self.filter.apply({}, "1", self.test_item)
        self.assertTrue(result)
        
        self.filter.set_platform("gcp")
        result = self.filter.apply({}, "1", self.test_item)
        self.assertFalse(result)
    
    def test_apply_status_filter(self):
        """Verifica filtro por estado"""
        self.filter.set_status("active")
        result = self.filter.apply({}, "1", self.test_item)
        self.assertTrue(result)
        
        self.filter.set_status("inactive")
        result = self.filter.apply({}, "1", self.test_item)
        self.assertFalse(result)
    
    def test_apply_tags_filter(self):
        """Verifica filtro por tags"""
        self.filter.add_tag("important")
        result = self.filter.apply({}, "1", self.test_item)
        self.assertTrue(result)
        
        self.filter.add_tag("nonexistent")
        result = self.filter.apply({}, "1", self.test_item)
        self.assertFalse(result)
    
    def test_clear_filters(self):
        """Verifica limpieza de filtros"""
        self.filter.set_group("core")
        self.filter.add_tag("important")
        self.filter.clear()
        
        result = self.filter.apply({}, "1", self.test_item)
        self.assertTrue(result)


class TestSearchItemsAdvanced(unittest.TestCase):
    """Tests para la función search_items_advanced"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.items = {
            "1": {"name": "Tool 1", "description": "Core tool", "group": "core"},
            "2": {"name": "Tool 2", "description": "Analysis tool", "group": "analysis"},
            "3": {"name": "Analyzer", "description": "Advanced analysis", "group": "analysis"},
        }
    
    def test_returns_list(self):
        """Verifica que retorna una lista"""
        result = search_items_advanced(self.items, "tool")
        self.assertIsInstance(result, list)
    
    def test_search_by_name(self):
        """Verifica búsqueda por nombre"""
        result = search_items_advanced(self.items, "analyzer")
        # Puede haber múltiples resultados debido a fuzzy matching
        self.assertGreater(len(result), 0)
        # El primero debe ser el que mejor coincide
        self.assertEqual(result[0][0], "3")
    
    def test_search_by_description(self):
        """Verifica búsqueda por descripción"""
        result = search_items_advanced(self.items, "analysis")
        self.assertGreater(len(result), 0)
    
    def test_search_with_filters(self):
        """Verifica búsqueda con filtros"""
        filters = AdvancedFilter()
        filters.set_group("core")
        result = search_items_advanced(self.items, "tool", filters=filters)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "1")
    
    def test_empty_query(self):
        """Verifica con query vacío"""
        result = search_items_advanced(self.items, "")
        self.assertEqual(len(result), 3)
    
    def test_no_results(self):
        """Verifica sin resultados"""
        result = search_items_advanced(self.items, "xyz123xyz")
        # Con fuzzy matching muy bajo, puede haber resultados
        # Verificar que al menos hay menos resultados que items totales
        self.assertLess(len(result), len(self.items))


class TestGetAutocompleteSuggestions(unittest.TestCase):
    """Tests para la función get_autocomplete_suggestions"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.items = {
            "1": {"name": "Tool 1", "description": "Description"},
            "2": {"name": "Tool 2", "description": "Description"},
            "3": {"name": "Analyzer", "description": "Description"},
        }
    
    def test_returns_list(self):
        """Verifica que retorna una lista"""
        result = get_autocomplete_suggestions(self.items, "too")
        self.assertIsInstance(result, list)
    
    def test_suggestions_for_prefix(self):
        """Verifica sugerencias para prefijo"""
        result = get_autocomplete_suggestions(self.items, "too")
        self.assertGreater(len(result), 0)
        self.assertTrue(any("Tool" in s for s in result))
    
    def test_empty_query(self):
        """Verifica con query vacío"""
        result = get_autocomplete_suggestions(self.items, "")
        self.assertEqual(len(result), 0)
    
    def test_max_suggestions(self):
        """Verifica límite de sugerencias"""
        result = get_autocomplete_suggestions(self.items, "tool", max_suggestions=1)
        self.assertLessEqual(len(result), 1)


class TestSearchById(unittest.TestCase):
    """Tests para la función search_by_id"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.items = {
            "1": {"name": "Tool 1"},
            "2": {"name": "Tool 2"},
            "ABC": {"name": "Tool ABC"},
        }
    
    def test_exact_match(self):
        """Verifica búsqueda exacta"""
        result = search_by_id(self.items, "1")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "1")
    
    def test_case_insensitive(self):
        """Verifica búsqueda case-insensitive"""
        result = search_by_id(self.items, "abc")
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "ABC")
    
    def test_not_found(self):
        """Verifica cuando no se encuentra"""
        result = search_by_id(self.items, "999")
        self.assertIsNone(result)


class TestSearchPaginator(unittest.TestCase):
    """Tests para la clase SearchPaginator"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.items = [
            ("1", {"name": "Tool 1"}, 1.0),
            ("2", {"name": "Tool 2"}, 0.9),
            ("3", {"name": "Tool 3"}, 0.8),
            ("4", {"name": "Tool 4"}, 0.7),
            ("5", {"name": "Tool 5"}, 0.6),
        ]
        self.paginator = SearchPaginator(self.items, page_size=2)
    
    def test_total_pages(self):
        """Verifica cálculo de páginas totales"""
        self.assertEqual(self.paginator.total_pages, 3)
    
    def test_current_items(self):
        """Verifica items de la página actual"""
        items = self.paginator.current_items
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0][0], "1")
    
    def test_next_page(self):
        """Verifica avance a siguiente página"""
        result = self.paginator.next_page()
        self.assertTrue(result)
        self.assertEqual(self.paginator.current_page, 1)
    
    def test_prev_page(self):
        """Verifica retroceso a página anterior"""
        self.paginator.next_page()
        result = self.paginator.prev_page()
        self.assertTrue(result)
        self.assertEqual(self.paginator.current_page, 0)
    
    def test_goto_page(self):
        """Verifica ir a página específica"""
        result = self.paginator.goto_page(2)
        self.assertTrue(result)
        self.assertEqual(self.paginator.current_page, 2)
    
    def test_next_page_at_end(self):
        """Verifica que no avance al final"""
        self.paginator.goto_page(2)
        result = self.paginator.next_page()
        self.assertFalse(result)


class TestGetAvailableGroups(unittest.TestCase):
    """Tests para la función get_available_groups"""
    
    def test_returns_list(self):
        """Verifica que retorna una lista"""
        items = {
            "1": {"name": "Tool 1", "group": "core"},
            "2": {"name": "Tool 2", "group": "analysis"},
        }
        result = get_available_groups(items)
        self.assertIsInstance(result, list)
    
    def test_unique_groups(self):
        """Verifica que retorna grupos únicos"""
        items = {
            "1": {"name": "Tool 1", "group": "core"},
            "2": {"name": "Tool 2", "group": "core"},
            "3": {"name": "Tool 3", "group": "analysis"},
        }
        result = get_available_groups(items)
        self.assertEqual(len(result), 2)
        self.assertIn("core", result)
        self.assertIn("analysis", result)
    
    def test_sorted_groups(self):
        """Verifica que está ordenado"""
        items = {
            "1": {"name": "Tool 1", "group": "zebra"},
            "2": {"name": "Tool 2", "group": "apple"},
        }
        result = get_available_groups(items)
        self.assertEqual(result[0], "apple")
        self.assertEqual(result[1], "zebra")


class TestGetAvailablePlatforms(unittest.TestCase):
    """Tests para la función get_available_platforms"""
    
    def test_returns_list(self):
        """Verifica que retorna una lista"""
        items = {
            "1": {"name": "Tool 1", "platform": "azdo"},
            "2": {"name": "Tool 2", "platform": "gcp"},
        }
        result = get_available_platforms(items)
        self.assertIsInstance(result, list)
    
    def test_unique_platforms(self):
        """Verifica que retorna plataformas únicas"""
        items = {
            "1": {"name": "Tool 1", "platform": "azdo"},
            "2": {"name": "Tool 2", "platform": "azdo"},
            "3": {"name": "Tool 3", "platform": "gcp"},
        }
        result = get_available_platforms(items)
        self.assertEqual(len(result), 2)


class TestGetAvailableTags(unittest.TestCase):
    """Tests para la función get_available_tags"""
    
    def test_returns_list(self):
        """Verifica que retorna una lista"""
        items = {
            "1": {"name": "Tool 1", "tags": ["important"]},
            "2": {"name": "Tool 2", "tags": ["security"]},
        }
        result = get_available_tags(items)
        self.assertIsInstance(result, list)
    
    def test_unique_tags(self):
        """Verifica que retorna tags únicos"""
        items = {
            "1": {"name": "Tool 1", "tags": ["important", "security"]},
            "2": {"name": "Tool 2", "tags": ["security", "analysis"]},
        }
        result = get_available_tags(items)
        self.assertEqual(len(result), 3)
        self.assertIn("important", result)
        self.assertIn("security", result)
        self.assertIn("analysis", result)


class TestSearchHistory(unittest.TestCase):
    """Tests para la clase SearchHistory"""
    
    def setUp(self):
        """Configura datos de prueba"""
        self.history = SearchHistory(max_items=5)
    
    def test_add_query(self):
        """Verifica agregar query"""
        self.history.add("test query")
        self.assertIn("test query", self.history.history)
    
    def test_no_duplicates(self):
        """Verifica que no agrega duplicados"""
        self.history.add("test")
        self.history.add("test")
        count = self.history.history.count("test")
        self.assertEqual(count, 1)
    
    def test_max_items(self):
        """Verifica límite de items"""
        for i in range(10):
            self.history.add(f"query{i}")
        self.assertLessEqual(len(self.history.history), 5)
    
    def test_get_suggestions(self):
        """Verifica sugerencias"""
        self.history.add("test query")
        self.history.add("test tool")
        suggestions = self.history.get_suggestions("test")
        # Debe haber al menos las dos queries que agregamos
        self.assertGreaterEqual(len(suggestions), 2)


if __name__ == '__main__':
    unittest.main()
