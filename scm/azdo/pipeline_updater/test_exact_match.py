"""
Tests para validar el parámetro exact_match en SearchEngine
"""

import unittest
from .search_engine import SearchEngine


class TestExactMatch(unittest.TestCase):
    """Tests para exact_match"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        self.definition_4_stages = {
            'environments': [
                {'id': '1', 'name': 'Build'},
                {'id': '2', 'name': 'Test'},
                {'id': '3', 'name': 'Deploy'},
                {'id': '4', 'name': 'Validate'},
            ]
        }
        
        self.definition_5_stages = {
            'environments': [
                {'id': '1', 'name': 'Build'},
                {'id': '2', 'name': 'Test'},
                {'id': '3', 'name': 'Deploy'},
                {'id': '4', 'name': 'Validate'},
                {'id': '5', 'name': 'Security'},
            ]
        }
        
        self.definition_3_stages = {
            'environments': [
                {'id': '1', 'name': 'Build'},
                {'id': '2', 'name': 'Test'},
                {'id': '3', 'name': 'Deploy'},
            ]
        }
    
    def test_exact_match_true_with_4_stages(self):
        """Test: exact_match=true con pipeline de 4 stages (debe pasar)"""
        search_rules = {
            'exact_match': True,
            'stages': ['Build', 'Test', 'Deploy', 'Validate']
        }
        
        engine = SearchEngine(self.definition_4_stages, search_rules)
        matches = engine.search_all()
        
        # Debe encontrar los 4 stages
        self.assertEqual(len(matches), 4)
        self.assertTrue(any(m.name == 'Build' for m in matches))
        self.assertTrue(any(m.name == 'Test' for m in matches))
        self.assertTrue(any(m.name == 'Deploy' for m in matches))
        self.assertTrue(any(m.name == 'Validate' for m in matches))
    
    def test_exact_match_true_with_5_stages(self):
        """Test: exact_match=true con pipeline de 5 stages (debe fallar)"""
        search_rules = {
            'exact_match': True,
            'stages': ['Build', 'Test', 'Deploy', 'Validate']
        }
        
        engine = SearchEngine(self.definition_5_stages, search_rules)
        matches = engine.search_all()
        
        # No debe encontrar nada porque el pipeline tiene 5 stages, no 4
        self.assertEqual(len(matches), 0)
    
    def test_exact_match_true_with_3_stages(self):
        """Test: exact_match=true con pipeline de 3 stages (debe fallar)"""
        search_rules = {
            'exact_match': True,
            'stages': ['Build', 'Test', 'Deploy', 'Validate']
        }
        
        engine = SearchEngine(self.definition_3_stages, search_rules)
        matches = engine.search_all()
        
        # No debe encontrar nada porque el pipeline tiene 3 stages, no 4
        self.assertEqual(len(matches), 0)
    
    def test_exact_match_false_with_4_stages(self):
        """Test: exact_match=false con pipeline de 4 stages (debe pasar)"""
        search_rules = {
            'exact_match': False,
            'stages': ['Build', 'Test', 'Deploy', 'Validate']
        }
        
        engine = SearchEngine(self.definition_4_stages, search_rules)
        matches = engine.search_all()
        
        # Debe encontrar los 4 stages
        self.assertEqual(len(matches), 4)
    
    def test_exact_match_false_with_5_stages(self):
        """Test: exact_match=false con pipeline de 5 stages (debe pasar)"""
        search_rules = {
            'exact_match': False,
            'stages': ['Build', 'Test', 'Deploy', 'Validate']
        }
        
        engine = SearchEngine(self.definition_5_stages, search_rules)
        matches = engine.search_all()
        
        # Debe encontrar los 4 stages buscados (ignora Security)
        self.assertEqual(len(matches), 4)
    
    def test_exact_match_false_with_3_stages(self):
        """Test: exact_match=false con pipeline de 3 stages (debe fallar)"""
        search_rules = {
            'exact_match': False,
            'stages': ['Build', 'Test', 'Deploy', 'Validate']
        }
        
        engine = SearchEngine(self.definition_3_stages, search_rules)
        matches = engine.search_all()
        
        # No debe encontrar nada porque falta 'Validate'
        self.assertEqual(len(matches), 3)  # Solo encuentra Build, Test, Deploy
    
    def test_exact_match_default_is_false(self):
        """Test: exact_match por defecto es false"""
        search_rules = {
            'stages': ['Build', 'Test', 'Deploy', 'Validate']
            # exact_match no especificado, debe ser false
        }
        
        engine = SearchEngine(self.definition_5_stages, search_rules)
        matches = engine.search_all()
        
        # Debe encontrar los 4 stages (exact_match=false por defecto)
        self.assertEqual(len(matches), 4)
    
    def test_exact_match_with_partial_stages(self):
        """Test: exact_match=true buscando solo 2 de 4 stages"""
        search_rules = {
            'exact_match': True,
            'stages': ['Build', 'Deploy']
        }
        
        definition = {
            'environments': [
                {'id': '1', 'name': 'Build'},
                {'id': '2', 'name': 'Deploy'},
            ]
        }
        
        engine = SearchEngine(definition, search_rules)
        matches = engine.search_all()
        
        # Debe encontrar los 2 stages
        self.assertEqual(len(matches), 2)
    
    def test_exact_match_with_pattern_matching(self):
        """Test: exact_match=true con pattern matching"""
        search_rules = {
            'exact_match': True,
            'stages': ['Build*', '*Deploy*', 'Validate']
        }
        
        definition = {
            'environments': [
                {'id': '1', 'name': 'Build Stage'},
                {'id': '2', 'name': 'Pre-Deploy'},
                {'id': '3', 'name': 'Validate'},
            ]
        }
        
        engine = SearchEngine(definition, search_rules)
        matches = engine.search_all()
        
        # Debe encontrar los 3 stages con pattern matching
        self.assertEqual(len(matches), 3)


if __name__ == '__main__':
    unittest.main()
