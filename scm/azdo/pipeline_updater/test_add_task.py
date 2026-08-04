"""
Tests para la acción add_task en UpdateEngine.

Cubren:
- Inserción de task antes de una task existente (before_task)
- Inserción de task después de una task existente (after_task)
- Filtrado por stage específico
- Inserción en todos los stages (sin filtro de stage)
- Error cuando falta before_task y after_task
- Error cuando falta la definición de task
- No inserción cuando la task de referencia no existe
- Soporte de comodines (fnmatch) en before_task
"""

import unittest
from .update_engine import UpdateEngine
from .models import Match, TemplateOptions


class TestAddTask(unittest.TestCase):
    """Tests para _process_add_task_actions"""

    def _make_definition(self, stages=None):
        """Crear definición mínima con stages y tasks."""
        if stages is None:
            stages = ['Develop', 'QA']
        environments = []
        for i, name in enumerate(stages):
            environments.append({
                'id': i + 1,
                'name': name,
                'rank': i + 1,
                'deployPhases': [{
                    'deploymentInput': {
                        'tasks': [
                            {
                                'displayName': 'Deploy',
                                'enabled': True,
                                'task': {'id': 'task-deploy', 'versionSpec': '1.*'},
                                'inputs': {}
                            },
                            {
                                'displayName': 'show Manifest',
                                'enabled': True,
                                'task': {'id': 'task-show', 'versionSpec': '1.*'},
                                'inputs': {}
                            }
                        ]
                    }
                }]
            })
        return {
            'id': 1,
            'name': 'Test Pipeline',
            'environments': environments
        }

    def _new_task_def(self, display_name='New Script Task'):
        return {
            'displayName': display_name,
            'enabled': True,
            'alwaysRun': False,
            'continueOnError': False,
            'timeoutInMinutes': 5,
            'task': {
                'id': '6C731787-BC2C-4436-8290-A81493FFEA35',
                'versionSpec': '3.*',
                'definitionType': 'task'
            },
            'inputs': {
                'script': 'echo "hello"'
            }
        }

    def test_insert_before_task_all_stages(self):
        """Inserta task antes de 'show Manifest' en todos los stages."""
        definition = self._make_definition()
        update_rules = {
            'tasks': [
                {
                    'action': 'add',
                    'before_task': 'show Manifest',
                    'task': self._new_task_def()
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules)
        result = engine.apply_updates()
        self.assertTrue(result)

        # Verificar que se insertó en ambos stages
        for env in definition['environments']:
            tasks = env['deployPhases'][0]['deploymentInput']['tasks']
            self.assertEqual(len(tasks), 3)
            self.assertEqual(tasks[1]['displayName'], 'New Script Task')
            self.assertEqual(tasks[2]['displayName'], 'show Manifest')

        # Verificar cambios registrados
        task_adds = [c for c in engine.changes if c['type'] == 'task_add']
        self.assertEqual(len(task_adds), 2)

    def test_insert_after_task_all_stages(self):
        """Inserta task después de 'Deploy' en todos los stages."""
        definition = self._make_definition()
        update_rules = {
            'tasks': [
                {
                    'action': 'add',
                    'after_task': 'Deploy',
                    'task': self._new_task_def()
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules)
        result = engine.apply_updates()
        self.assertTrue(result)

        for env in definition['environments']:
            tasks = env['deployPhases'][0]['deploymentInput']['tasks']
            self.assertEqual(len(tasks), 3)
            self.assertEqual(tasks[0]['displayName'], 'Deploy')
            self.assertEqual(tasks[1]['displayName'], 'New Script Task')

    def test_insert_in_specific_stage(self):
        """Inserta task solo en el stage 'QA'."""
        definition = self._make_definition()
        update_rules = {
            'tasks': [
                {
                    'action': 'add',
                    'before_task': 'show Manifest',
                    'stage': 'QA',
                    'task': self._new_task_def()
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules)
        result = engine.apply_updates()
        self.assertTrue(result)

        # Develop no debe tener la task nueva
        dev_tasks = definition['environments'][0]['deployPhases'][0]['deploymentInput']['tasks']
        self.assertEqual(len(dev_tasks), 2)

        # QA debe tener la task nueva
        qa_tasks = definition['environments'][1]['deployPhases'][0]['deploymentInput']['tasks']
        self.assertEqual(len(qa_tasks), 3)
        self.assertEqual(qa_tasks[1]['displayName'], 'New Script Task')

        task_adds = [c for c in engine.changes if c['type'] == 'task_add']
        self.assertEqual(len(task_adds), 1)
        self.assertEqual(task_adds[0]['stage'], 'QA')

    def test_no_insertion_when_ref_task_missing(self):
        """No inserta si la task de referencia no existe."""
        definition = self._make_definition()
        update_rules = {
            'tasks': [
                {
                    'action': 'add',
                    'before_task': 'NonExistent Task',
                    'task': self._new_task_def()
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules)
        result = engine.apply_updates()
        self.assertTrue(result)

        for env in definition['environments']:
            tasks = env['deployPhases'][0]['deploymentInput']['tasks']
            self.assertEqual(len(tasks), 2)

        task_adds = [c for c in engine.changes if c['type'] == 'task_add']
        self.assertEqual(len(task_adds), 0)

    def test_error_when_no_before_or_after(self):
        """Error si no se especifica before_task ni after_task."""
        definition = self._make_definition()
        update_rules = {
            'tasks': [
                {
                    'action': 'add',
                    'task': self._new_task_def()
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules)
        result = engine.apply_updates()
        self.assertFalse(result)

    def test_error_when_no_task_def(self):
        """Error si no se proporciona la definición de task."""
        definition = self._make_definition()
        update_rules = {
            'tasks': [
                {
                    'action': 'add',
                    'before_task': 'show Manifest'
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules)
        result = engine.apply_updates()
        self.assertFalse(result)

    def test_wildcard_before_task(self):
        """Soporta comodines en before_task (fnmatch)."""
        definition = self._make_definition()
        update_rules = {
            'tasks': [
                {
                    'action': 'add',
                    'before_task': 'show*',
                    'task': self._new_task_def()
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules)
        result = engine.apply_updates()
        self.assertTrue(result)

        for env in definition['environments']:
            tasks = env['deployPhases'][0]['deploymentInput']['tasks']
            self.assertEqual(len(tasks), 3)
            self.assertEqual(tasks[1]['displayName'], 'New Script Task')

    def test_task_content_preserved(self):
        """El contenido del script se preserva exactamente."""
        script_content = 'echo "hello world"\n# multiline\nexit 0'
        definition = self._make_definition()
        task_def = self._new_task_def()
        task_def['inputs']['script'] = script_content
        update_rules = {
            'tasks': [
                {
                    'action': 'add',
                    'before_task': 'show Manifest',
                    'task': task_def
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules)
        result = engine.apply_updates()
        self.assertTrue(result)

        for env in definition['environments']:
            tasks = env['deployPhases'][0]['deploymentInput']['tasks']
            inserted = tasks[1]
            self.assertEqual(inserted['inputs']['script'], script_content)

    def test_non_add_rules_ignored(self):
        """Las reglas sin action='add' no se procesan en _process_add_task_actions."""
        definition = self._make_definition()
        update_rules = {
            'tasks': [
                {
                    'action': 'add',
                    'before_task': 'show Manifest',
                    'task': self._new_task_def()
                },
                {
                    'name': 'Deploy',
                    'fields': [
                        {'path': 'inputs.namespace', 'new_value': 'prod'}
                    ]
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules)
        result = engine.apply_updates()
        self.assertTrue(result)

        # La task nueva debe estar insertada
        for env in definition['environments']:
            tasks = env['deployPhases'][0]['deploymentInput']['tasks']
            self.assertEqual(len(tasks), 3)


if __name__ == '__main__':
    unittest.main()
