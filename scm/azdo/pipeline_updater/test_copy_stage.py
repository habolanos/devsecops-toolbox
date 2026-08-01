"""
Tests para acciones de stage: copy y add
"""

import unittest
from scm.azdo.pipeline_updater.update_engine import UpdateEngine
from scm.azdo.pipeline_updater.models import Match


class TestCopyStage(unittest.TestCase):
    """Tests para action: copy en stages"""
    
    def setUp(self):
        """Definición base para tests"""
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'Build', 'rank': 1},
                {'id': 2, 'name': 'QA', 'rank': 2},
                {'id': 3, 'name': 'Production', 'rank': 3}
            ]
        }
        self.matches = []
    
    def test_copy_stage_inserts_new_stage(self):
        """action: copy debe insertar un nuevo stage clonado"""
        update_rules = {
            'stages': [
                {
                    'action': 'copy',
                    'source_stage': 'QA',
                    'new_name': 'QA-Copia',
                    'position': 'after',
                    'reference_stage': 'QA'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()
        
        # Debe haber 4 stages
        self.assertEqual(len(self.definition['environments']), 4)
        
        # El nuevo stage debe existir
        stage_names = [s['name'] for s in self.definition['environments']]
        self.assertIn('QA-Copia', stage_names)
        
        # Debe estar después de QA
        qa_idx = stage_names.index('QA')
        copia_idx = stage_names.index('QA-Copia')
        self.assertGreater(copia_idx, qa_idx)
    
    def test_copy_stage_with_task_updates(self):
        """action: copy con task_updates debe modificar atributos de tasks"""
        definition = {
            'environments': [
                {
                    'id': 1,
                    'name': 'QA',
                    'rank': 1,
                    'deployPhases': [
                        {
                            'deploymentInput': {
                                'tasks': [
                                    {
                                        'displayName': 'Deploy to QA',
                                        'inputs': {'namespace': 'qa'}
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        
        update_rules = {
            'stages': [
                {
                    'action': 'copy',
                    'source_stage': 'QA',
                    'new_name': 'QA-Copia',
                    'task_updates': [
                        {
                            'task_name': 'Deploy to QA',
                            'fields': [
                                {'path': 'inputs.namespace', 'new_value': 'qa-copia'}
                            ]
                        }
                    ]
                }
            ]
        }
        
        engine = UpdateEngine(definition, self.matches, update_rules)
        engine.apply_updates()
        
        # Buscar el stage copiado
        copia = None
        for stage in definition['environments']:
            if stage['name'] == 'QA-Copia':
                copia = stage
                break
        
        self.assertIsNotNone(copia)
        
        # Verificar que el atributo fue modificado
        task = copia['deployPhases'][0]['deploymentInput']['tasks'][0]
        self.assertEqual(task['inputs']['namespace'], 'qa-copia')
    
    def test_copy_stage_resequences_ranks(self):
        """action: copy debe reasignar ranks secuenciales"""
        update_rules = {
            'stages': [
                {
                    'action': 'copy',
                    'source_stage': 'QA',
                    'new_name': 'QA-Copia',
                    'position': 'after',
                    'reference_stage': 'QA'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()
        
        # Ranks deben ser 1, 2, 3, 4
        ranks = [s['rank'] for s in self.definition['environments']]
        self.assertEqual(sorted(ranks), [1, 2, 3, 4])
    
    def test_copy_stage_invalid_source_returns_false(self):
        """action: copy con source_stage inexistente debe retornar False"""
        update_rules = {
            'stages': [
                {
                    'action': 'copy',
                    'source_stage': 'Inexistente',
                    'new_name': 'Copia'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        result = engine.apply_updates()
        
        self.assertFalse(result)


class TestAddStage(unittest.TestCase):
    """Tests para action: add en stages"""
    
    def setUp(self):
        """Definición base para tests"""
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'Build', 'rank': 1},
                {'id': 2, 'name': 'Deploy', 'rank': 2}
            ]
        }
        self.matches = []
    
    def test_add_stage_inserts_definition(self):
        """action: add debe insertar un stage desde definición embebida"""
        update_rules = {
            'stages': [
                {
                    'action': 'add',
                    'name': 'Security Check',
                    'definition': {
                        'id': 99,
                        'name': 'Security Check',
                        'rank': 2,
                        'deployPhases': []
                    },
                    'position': 'after',
                    'after_stage': 'Build'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()
        
        # Debe haber 3 stages
        self.assertEqual(len(self.definition['environments']), 3)
        
        # El nuevo stage debe existir
        stage_names = [s['name'] for s in self.definition['environments']]
        self.assertIn('Security Check', stage_names)
    
    def test_add_stage_between(self):
        """action: add con position: between debe insertar entre dos stages"""
        update_rules = {
            'stages': [
                {
                    'action': 'add',
                    'name': 'Security Check',
                    'definition': {
                        'id': 99,
                        'name': 'Security Check',
                        'rank': 2
                    },
                    'position': 'between',
                    'after_stage': 'Build',
                    'before_stage': 'Deploy'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()
        
        stage_names = [s['name'] for s in self.definition['environments']]
        build_idx = stage_names.index('Build')
        security_idx = stage_names.index('Security Check')
        deploy_idx = stage_names.index('Deploy')
        
        # Security Check debe estar entre Build y Deploy
        self.assertGreater(security_idx, build_idx)
        self.assertLess(security_idx, deploy_idx)
    
    def test_add_stage_resequences_ranks(self):
        """action: add debe reasignar ranks secuenciales"""
        update_rules = {
            'stages': [
                {
                    'action': 'add',
                    'name': 'Security Check',
                    'definition': {'id': 99, 'name': 'Security Check'},
                    'position': 'after',
                    'after_stage': 'Build'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()
        
        ranks = [s['rank'] for s in self.definition['environments']]
        self.assertEqual(sorted(ranks), [1, 2, 3])
    
    def test_add_stage_missing_definition_returns_false(self):
        """action: add sin definition debe retornar False"""
        update_rules = {
            'stages': [
                {
                    'action': 'add',
                    'name': 'Nuevo'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        result = engine.apply_updates()
        
        self.assertFalse(result)


class TestRenameStage(unittest.TestCase):
    """Tests para action: rename en stages"""
    
    def setUp(self):
        """Definición base para tests"""
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'Build', 'rank': 1},
                {'id': 2, 'name': 'QA', 'rank': 2},
                {'id': 3, 'name': 'Production', 'rank': 3}
            ]
        }
        self.matches = []
    
    def test_rename_stage_changes_name(self):
        """action: rename debe cambiar el nombre del stage"""
        update_rules = {
            'stages': [
                {
                    'action': 'rename',
                    'source_stage': 'QA',
                    'new_name': 'QA-Testing'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()
        
        stage_names = [s['name'] for s in self.definition['environments']]
        self.assertIn('QA-Testing', stage_names)
        self.assertNotIn('QA', stage_names)
    
    def test_rename_stage_preserves_id_and_rank(self):
        """action: rename debe preservar ID y rank del stage"""
        update_rules = {
            'stages': [
                {
                    'action': 'rename',
                    'source_stage': 'QA',
                    'new_name': 'QA-Testing'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()
        
        renamed_stage = None
        for stage in self.definition['environments']:
            if stage['name'] == 'QA-Testing':
                renamed_stage = stage
                break
        
        self.assertIsNotNone(renamed_stage)
        self.assertEqual(renamed_stage['id'], 2)
        self.assertEqual(renamed_stage['rank'], 2)
    
    def test_rename_stage_invalid_source_returns_false(self):
        """action: rename con source_stage inexistente debe retornar False"""
        update_rules = {
            'stages': [
                {
                    'action': 'rename',
                    'source_stage': 'Inexistente',
                    'new_name': 'Nuevo'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        result = engine.apply_updates()
        
        self.assertFalse(result)
    
    def test_rename_stage_records_change(self):
        """action: rename debe registrar el cambio en self.changes"""
        update_rules = {
            'stages': [
                {
                    'action': 'rename',
                    'source_stage': 'QA',
                    'new_name': 'QA-Testing'
                }
            ]
        }
        
        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()
        
        rename_change = None
        for change in engine.changes:
            if change.get('type') == 'stage_rename':
                rename_change = change
                break
        
        self.assertIsNotNone(rename_change)
        self.assertEqual(rename_change['old_name'], 'QA')
        self.assertEqual(rename_change['new_name'], 'QA-Testing')

    def test_rename_stage_updates_conditions_dependency(self):
        """action: rename debe actualizar environment.conditions[] que referencian al stage viejo"""
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'Validador', 'rank': 1},
                {
                    'id': 2, 'name': 'Production', 'rank': 2,
                    'conditions': [
                        {'name': 'Validador', 'conditionType': 'environmentState', 'value': '4'}
                    ]
                }
            ]
        }
        update_rules = {
            'stages': [
                {
                    'action': 'rename',
                    'source_stage': 'Validador',
                    'new_name': 'Validator'
                }
            ]
        }

        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()

        # El condition debe referenciar 'Validator' ahora
        prod_stage = [s for s in self.definition['environments'] if s['name'] == 'Production'][0]
        self.assertEqual(prod_stage['conditions'][0]['name'], 'Validator')

        # Debe registrar el cambio de dependencia
        dep_changes = [c for c in engine.changes if c.get('type') == 'stage_dependency_update']
        self.assertEqual(len(dep_changes), 1)
        self.assertEqual(dep_changes[0]['old_ref'], 'Validador')
        self.assertEqual(dep_changes[0]['new_ref'], 'Validator')

    def test_rename_stage_updates_condition_string_dependency(self):
        """action: rename debe actualizar deploymentInput.condition string que referencia al stage viejo"""
        self.definition = {
            'environments': [
                {
                    'id': 1, 'name': 'Validador', 'rank': 1,
                    'deployPhases': [{'deploymentInput': {'condition': 'succeeded()'}}]
                },
                {
                    'id': 2, 'name': 'Production', 'rank': 2,
                    'deployPhases': [{'deploymentInput': {'condition': "succeeded('Validador')"}}]
                }
            ]
        }
        update_rules = {
            'stages': [
                {
                    'action': 'rename',
                    'source_stage': 'Validador',
                    'new_name': 'Validator'
                }
            ]
        }

        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()

        # El condition string debe referenciar 'Validator' ahora
        prod_stage = [s for s in self.definition['environments'] if s['name'] == 'Production'][0]
        cond = prod_stage['deployPhases'][0]['deploymentInput']['condition']
        self.assertIn("'Validator'", cond)
        self.assertNotIn("'Validador'", cond)

    def test_rename_stage_no_dependencies_still_works(self):
        """action: rename sin dependencias debe funcionar igual que antes"""
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'Build', 'rank': 1},
                {'id': 2, 'name': 'QA', 'rank': 2}
            ]
        }
        update_rules = {
            'stages': [
                {
                    'action': 'rename',
                    'source_stage': 'Build',
                    'new_name': 'Compile'
                }
            ]
        }

        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()

        stage_names = [s['name'] for s in self.definition['environments']]
        self.assertIn('Compile', stage_names)
        self.assertNotIn('Build', stage_names)

        # No debe haber cambios de dependencia
        dep_changes = [c for c in engine.changes if c.get('type') == 'stage_dependency_update']
        self.assertEqual(len(dep_changes), 0)


class TestPositionBetween(unittest.TestCase):
    """Tests específicos para position: between"""
    
    def test_between_requires_both_stages(self):
        """position: between requiere after_stage y before_stage"""
        definition = {'environments': [{'id': 1, 'name': 'A', 'rank': 1}]}
        
        update_rules = {
            'stages': [
                {
                    'action': 'add',
                    'name': 'B',
                    'definition': {'id': 2, 'name': 'B'},
                    'position': 'between',
                    'after_stage': 'A'
                    # Falta before_stage
                }
            ]
        }
        
        engine = UpdateEngine(definition, [], update_rules)
        result = engine.apply_updates()
        
        self.assertFalse(result)
    
    def test_between_missing_reference_fallback_to_end(self):
        """position: between con referencias no encontradas inserta al final"""
        definition = {
            'environments': [
                {'id': 1, 'name': 'A', 'rank': 1},
                {'id': 2, 'name': 'B', 'rank': 2}
            ]
        }
        
        update_rules = {
            'stages': [
                {
                    'action': 'add',
                    'name': 'C',
                    'definition': {'id': 3, 'name': 'C'},
                    'position': 'between',
                    'after_stage': 'Inexistente',
                    'before_stage': 'B'
                }
            ]
        }
        
        engine = UpdateEngine(definition, [], update_rules)
        engine.apply_updates()
        
        # Debe insertarse al final
        stage_names = [s['name'] for s in definition['environments']]
        self.assertEqual(stage_names[-1], 'C')


class TestReorderStages(unittest.TestCase):
    """Tests para reordenamiento de stages con rank"""

    def setUp(self):
        self.matches = []

    def test_reorder_partial_stages_renumbers_all_consecutive(self):
        """Reordenar solo algunos stages debe renumerar TODOS consecutivamente desde 1"""
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'SCM Inspection', 'rank': 1},
                {'id': 2, 'name': 'Texcoco', 'rank': 2},
                {'id': 3, 'name': 'Develop', 'rank': 3},
                {'id': 4, 'name': 'QA', 'rank': 4},
                {'id': 5, 'name': 'Production', 'rank': 5},
            ]
        }
        update_rules = {
            'stages': [
                {'name': 'SCM Inspection', 'rank': 1},
                {'name': 'Develop', 'rank': 2},
                {'name': 'QA', 'rank': 3},
                {'name': 'Production', 'rank': 4},
            ]
        }

        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()

        ranks = [s['rank'] for s in self.definition['environments']]
        self.assertEqual(ranks, [1, 2, 3, 4, 5])

    def test_reorder_all_stages_consecutive(self):
        """Reordenar todos los stages debe producir ranks consecutivos desde 1"""
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'Develop', 'rank': 1},
                {'id': 2, 'name': 'QA', 'rank': 2},
                {'id': 3, 'name': 'Staging', 'rank': 3},
                {'id': 4, 'name': 'Production', 'rank': 4},
            ]
        }
        update_rules = {
            'stages': [
                {'name': 'Develop', 'rank': 1},
                {'name': 'QA', 'rank': 2},
                {'name': 'Staging', 'rank': 3},
                {'name': 'Production', 'rank': 4},
            ]
        }

        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()

        ranks = [s['rank'] for s in self.definition['environments']]
        self.assertEqual(ranks, [1, 2, 3, 4])

    def test_reorder_moves_stage_to_different_position(self):
        """Mover un stage a una posicion distinta debe renumerar consecutivamente"""
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'Develop', 'rank': 1},
                {'id': 2, 'name': 'QA', 'rank': 2},
                {'id': 3, 'name': 'Staging', 'rank': 3},
                {'id': 4, 'name': 'Production', 'rank': 4},
            ]
        }
        update_rules = {
            'stages': [
                {'name': 'Develop', 'rank': 1},
                {'name': 'Staging', 'rank': 2},
                {'name': 'QA', 'rank': 3},
                {'name': 'Production', 'rank': 4},
            ]
        }

        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()

        names = [s['name'] for s in self.definition['environments']]
        self.assertEqual(names, ['Develop', 'Staging', 'QA', 'Production'])
        ranks = [s['rank'] for s in self.definition['environments']]
        self.assertEqual(ranks, [1, 2, 3, 4])

    def test_reorder_no_duplicate_ranks(self):
        """No debe haber ranks duplicados despues del reordenamiento"""
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'SCM Inspection', 'rank': 1},
                {'id': 2, 'name': 'Develop', 'rank': 2},
                {'id': 3, 'name': 'QA', 'rank': 3},
                {'id': 4, 'name': 'Validator', 'rank': 4},
                {'id': 5, 'name': 'Production', 'rank': 5},
            ]
        }
        update_rules = {
            'stages': [
                {'name': 'SCM Inspection', 'rank': 1},
                {'name': 'Develop', 'rank': 2},
                {'name': 'QA', 'rank': 3},
                {'name': 'Validator', 'rank': 4},
                {'name': 'Production', 'rank': 5},
            ]
        }

        engine = UpdateEngine(self.definition, self.matches, update_rules)
        engine.apply_updates()

        ranks = [s['rank'] for s in self.definition['environments']]
        self.assertEqual(len(ranks), len(set(ranks)))
        self.assertEqual(ranks, [1, 2, 3, 4, 5])


if __name__ == '__main__':
    unittest.main()
