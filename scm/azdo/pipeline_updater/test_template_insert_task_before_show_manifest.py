"""
Tests para pipe_cd_insert_task_before_show_manifest.yaml

Valida que el template, al ser aplicado via UpdateEngine a una definición
de pipeline simulada, produce los cambios esperados:
- Inserta task "clean Manifest" antes de "show Manifest" en todos los stages
- La task insertada tiene las propiedades del template
- No inserta si "show Manifest" no existe
- Conteo de inserciones = una por stage que tiene "show Manifest"
- Usa filePath como input
"""

import unittest
import yaml
from pathlib import Path
from .update_engine import UpdateEngine
from .models import TemplateOptions

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def load_template(filename: str) -> dict:
    path = TEMPLATES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Template no encontrado: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestInsertTaskBeforeShowManifest(unittest.TestCase):
    """Tests para pipe_cd_insert_task_before_show_manifest.yaml"""

    def setUp(self):
        self.template = load_template("pipe_cd_insert_task_before_show_manifest.yaml")
        self.definition = {
            'id': 400,
            'name': 'Test Pipeline Insert Task',
            'environments': [
                {
                    'id': 1, 'name': 'Develop', 'rank': 1,
                    'deployPhases': [{
                        'deploymentInput': {
                            'tasks': [
                                {'displayName': 'Deploy', 'enabled': True, 'task': {'id': 't1'}, 'inputs': {}},
                                {'displayName': 'show Manifest', 'enabled': True, 'task': {'id': 't2'}, 'inputs': {}},
                            ]
                        }
                    }]
                },
                {
                    'id': 2, 'name': 'QA', 'rank': 2,
                    'deployPhases': [{
                        'deploymentInput': {
                            'tasks': [
                                {'displayName': 'Deploy', 'enabled': True, 'task': {'id': 't1'}, 'inputs': {}},
                                {'displayName': 'show Manifest', 'enabled': True, 'task': {'id': 't2'}, 'inputs': {}},
                            ]
                        }
                    }]
                },
            ],
            'artifacts': [],
            'triggers': [],
        }

    def test_template_loads_correctly(self):
        self.assertEqual(self.template['metadata']['version'], '1.0')
        self.assertEqual(self.template['update']['tasks'][0]['action'], 'add')
        self.assertEqual(self.template['update']['tasks'][0]['before_task'], 'show Manifest')

    def test_insert_task_before_show_manifest_all_stages(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        for env in self.definition['environments']:
            tasks = env['deployPhases'][0]['deploymentInput']['tasks']
            names = [t['displayName'] for t in tasks]
            self.assertIn('clean Manifest', names)
            self.assertLess(names.index('clean Manifest'), names.index('show Manifest'))

    def test_inserted_task_has_correct_properties(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        dev = self.definition['environments'][0]
        tasks = dev['deployPhases'][0]['deploymentInput']['tasks']
        clean_task = next(t for t in tasks if t['displayName'] == 'clean Manifest')
        self.assertTrue(clean_task['enabled'])
        self.assertFalse(clean_task['alwaysRun'])
        self.assertEqual(clean_task['timeoutInMinutes'], 5)
        self.assertEqual(clean_task['task']['id'], '6C731787-BC2C-4436-8290-A81493FFEA35')

    def test_no_insertion_when_show_manifest_absent(self):
        definition = {
            'environments': [
                {
                    'id': 1, 'name': 'Develop', 'rank': 1,
                    'deployPhases': [{
                        'deploymentInput': {
                            'tasks': [
                                {'displayName': 'Deploy', 'enabled': True, 'task': {'id': 't1'}, 'inputs': {}},
                            ]
                        }
                    }]
                },
            ],
            'artifacts': [], 'triggers': [],
        }
        update_rules = self.template['update']
        engine = UpdateEngine(definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        tasks = definition['environments'][0]['deployPhases'][0]['deploymentInput']['tasks']
        self.assertEqual(len(tasks), 1)

    def test_insertion_count_matches_stages(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        changes = [c for c in engine.get_changes() if c['type'] == 'task_add']
        self.assertEqual(len(changes), 2)

    def test_inserted_task_uses_filepath_input(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        dev = self.definition['environments'][0]
        tasks = dev['deployPhases'][0]['deploymentInput']['tasks']
        clean_task = next(t for t in tasks if t['displayName'] == 'clean Manifest')
        self.assertIn('filePath', clean_task['inputs'])
        self.assertIn('clean_manifest', clean_task['inputs']['filePath'])


if __name__ == '__main__':
    unittest.main()
