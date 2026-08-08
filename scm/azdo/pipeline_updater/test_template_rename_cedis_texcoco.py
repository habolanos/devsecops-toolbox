"""
Tests para pipe_cd_rename_all_cedis_texcoco_to_regional_24-Texcoco.yaml

Valida que el template, al ser aplicado via UpdateEngine a una definición
de pipeline simulada, produce los cambios esperados:
- Renombra "Cedis Texcoco" a "24-Texcoco"
- Preserva ID y rank del stage original
- Actualiza referencias de dependencias
- No-op si el stage no existe
- Sin ignore_variable_groups
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


class TestRenameCedisTexcoco(unittest.TestCase):
    """Tests para pipe_cd_rename_all_cedis_texcoco_to_regional_24-Texcoco.yaml"""

    def setUp(self):
        self.template = load_template(
            "pipe_cd_rename_all_cedis_texcoco_to_regional_24-Texcoco.yaml"
        )
        self.definition = {
            'id': 300,
            'name': 'Test Pipeline Rename Texcoco',
            'environments': [
                {'id': 1, 'name': 'Develop', 'rank': 1, 'deployPhases': [], 'conditions': []},
                {'id': 2, 'name': 'Cedis Texcoco', 'rank': 2, 'deployPhases': [], 'conditions': []},
                {'id': 3, 'name': 'Production', 'rank': 3, 'deployPhases': [],
                 'conditions': [{'name': 'Cedis Texcoco', 'conditionType': 'environmentState'}]},
            ],
            'artifacts': [],
            'triggers': [],
        }

    def test_template_loads_correctly(self):
        self.assertEqual(self.template['metadata']['version'], '1.1')
        self.assertEqual(self.template['update']['stages'][0]['action'], 'rename')

    def test_rename_cedis_texcoco_to_24_texcoco(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        names = [s['name'] for s in self.definition['environments']]
        self.assertIn('24-Texcoco', names)
        self.assertNotIn('Cedis Texcoco', names)

    def test_rename_preserves_id_and_rank(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        renamed = next(s for s in self.definition['environments'] if s['name'] == '24-Texcoco')
        self.assertEqual(renamed['id'], 2)
        self.assertEqual(renamed['rank'], 2)

    def test_rename_updates_dependency_references(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        prod = next(s for s in self.definition['environments'] if s['name'] == 'Production')
        cond = prod['conditions'][0]
        self.assertEqual(cond['name'], '24-Texcoco')

    def test_rename_nonexistent_stage_is_noop(self):
        definition = {
            'environments': [
                {'id': 1, 'name': 'Other', 'rank': 1, 'deployPhases': []},
            ],
            'artifacts': [], 'triggers': [],
        }
        update_rules = self.template['update']
        engine = UpdateEngine(definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        self.assertEqual(definition['environments'][0]['name'], 'Other')

    def test_no_ignore_variable_groups(self):
        opts = self.template['options']
        self.assertNotIn('ignore_variable_groups', opts)


if __name__ == '__main__':
    unittest.main()
