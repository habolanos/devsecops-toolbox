"""
Tests para pipe_cd_rename_all_cedis_13-Villa_Hermosa_to_regional_13-Villa_Hermosa.yaml

Valida que el template, al ser aplicado via UpdateEngine a una definición
de pipeline simulada, produce los cambios esperados:
- Renombra "1-Culiacan" a "01-Culiacan"
- Preserva ID y rank del stage original
- Actualiza referencias de dependencias
- No-op si el stage no existe
- Opciones ignore_variable_groups y replace_agent_pools parseadas
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


class TestRenameCedisVillaHermosa(unittest.TestCase):
    """Tests para pipe_cd_rename_all_cedis_13-Villa_Hermosa_to_regional_13-Villa_Hermosa.yaml"""

    def setUp(self):
        self.template = load_template(
            "pipe_cd_rename_all_cedis_13-Villa_Hermosa_to_regional_13-Villa_Hermosa.yaml"
        )
        self.definition = {
            'id': 200,
            'name': 'Test Pipeline Rename Villa Hermosa',
            'environments': [
                {'id': 1, 'name': '1-Culiacan', 'rank': 1, 'deployPhases': [{'deploymentInput': {'tasks': []}}],
                 'conditions': [], 'deployPhases': []},
                {'id': 2, 'name': 'QA', 'rank': 2, 'deployPhases': [{'deploymentInput': {'tasks': []}}],
                 'conditions': [{'name': '1-Culiacan', 'conditionType': 'environmentState'}]},
            ],
            'artifacts': [],
            'triggers': [],
        }

    def test_template_loads_correctly(self):
        self.assertEqual(self.template['metadata']['version'], '1.1')
        self.assertEqual(self.template['update']['stages'][0]['action'], 'rename')

    def test_rename_1_culiacan_to_01_culiacan(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        names = [s['name'] for s in self.definition['environments']]
        self.assertIn('01-Culiacan', names)
        self.assertNotIn('1-Culiacan', names)

    def test_rename_preserves_id_and_rank(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        renamed = next(s for s in self.definition['environments'] if s['name'] == '01-Culiacan')
        self.assertEqual(renamed['id'], 1)
        self.assertEqual(renamed['rank'], 1)

    def test_rename_updates_dependency_references(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        qa = next(s for s in self.definition['environments'] if s['name'] == 'QA')
        cond = qa['conditions'][0]
        self.assertEqual(cond['name'], '01-Culiacan')

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

        self.assertEqual(len(definition['environments']), 1)
        self.assertEqual(definition['environments'][0]['name'], 'Other')

    def test_ignore_variable_groups_option_parsed(self):
        opts = self.template['options']
        self.assertIn('ignore_variable_groups', opts)
        self.assertIn('all', opts['ignore_variable_groups'])
        self.assertIn(186, opts['ignore_variable_groups']['all'])
        self.assertIn(196, opts['ignore_variable_groups']['all'])

    def test_replace_agent_pools_option_parsed(self):
        opts = self.template['options']
        self.assertIn('replace_agent_pools', opts)
        self.assertEqual(opts['replace_agent_pools'][1749], 5331)
        self.assertEqual(opts['replace_agent_pools'][2722], 5331)


if __name__ == '__main__':
    unittest.main()
