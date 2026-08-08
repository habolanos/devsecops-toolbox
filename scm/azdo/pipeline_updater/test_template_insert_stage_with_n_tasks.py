"""
Tests para pipe_cd_insert_stage_with_n_tasks.yaml

Valida que el template, al ser aplicado via UpdateEngine a una definición
de pipeline simulada, produce los cambios esperados:
- Inserta stage "Pre Deploy Validation" entre Staging y Producción
- Reordena ranks (Staging=1, Pre Deploy Validation=2, Producción=3)
- Actualiza dependencia de Producción
- Agrega trigger con $auto resuelto al alias del Build artifact
- Actualiza artifact branch filter a refs/heads/main
"""

import unittest
import yaml
from pathlib import Path
from .update_engine import UpdateEngine
from .search_engine import SearchEngine
from .models import TemplateOptions

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def load_template(filename: str) -> dict:
    path = TEMPLATES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Template no encontrado: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestInsertStageWithNTasks(unittest.TestCase):
    """Tests para pipe_cd_insert_stage_with_n_tasks.yaml"""

    def setUp(self):
        self.template = load_template("pipe_cd_insert_stage_with_n_tasks.yaml")
        self.definition = {
            'id': 100,
            'name': 'Test Pipeline CD',
            'environments': [
                {
                    'id': 1, 'name': 'Staging', 'rank': 1,
                    'deployPhases': [{'deploymentInput': {'tasks': []}}],
                    'preDeployApprovals': {'approvals': [{'rank': 1, 'isAutomated': True,
                        'approver': {'displayName': 'Automated'}}]},
                    'postDeployApprovals': {'approvals': []},
                },
                {
                    'id': 2, 'name': 'Producción', 'rank': 2,
                    'deployPhases': [{'deploymentInput': {'tasks': []}}],
                    'preDeployApprovals': {'approvals': [{'rank': 1, 'isAutomated': True,
                        'approver': {'displayName': 'Staging'}}]},
                    'postDeployApprovals': {'approvals': []},
                },
            ],
            'artifacts': [
                {'alias': '_mybuild', 'type': 'Build',
                 'definitionReference': {'branch': {'id': 'refs/heads/master', 'name': 'master'}}},
            ],
            'triggers': [],
        }

    def test_template_loads_correctly(self):
        self.assertEqual(self.template['metadata']['version'], '2.1')
        self.assertIn('search', self.template)
        self.assertIn('update', self.template)

    def test_search_finds_stages_and_artifacts(self):
        search = SearchEngine(self.definition, self.template['search'])
        matches = search.search_all()
        stage_matches = [m for m in matches if m.type == 'stage']
        artifact_matches = [m for m in matches if m.type == 'artifact']
        self.assertEqual(len(stage_matches), 2)
        self.assertGreaterEqual(len(artifact_matches), 1)

    def test_insert_new_stage_between(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        names = [s['name'] for s in self.definition['environments']]
        self.assertIn('Pre Deploy Validation', names)
        self.assertGreater(names.index('Pre Deploy Validation'), names.index('Staging'))
        self.assertLess(names.index('Pre Deploy Validation'), names.index('Producción'))

    def test_new_stage_has_3_tasks(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        new_stage = next(s for s in self.definition['environments'] if s['name'] == 'Pre Deploy Validation')
        tasks = new_stage['deployPhases'][0]['deploymentInput']['tasks']
        self.assertEqual(len(tasks), 3)

    def test_produccion_rank_is_3(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        prod = next(s for s in self.definition['environments'] if s['name'] == 'Producción')
        self.assertEqual(prod['rank'], 3)

    def test_trigger_add_resolves_auto(self):
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        triggers = self.definition.get('triggers', [])
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]['triggerConfiguration']['artifactName'], '_mybuild')

    def test_artifact_branch_updated_to_main(self):
        search = SearchEngine(self.definition, self.template['search'])
        matches = search.search_all()

        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, matches, update_rules, TemplateOptions())
        engine.apply_updates()

        art = self.definition['artifacts'][0]
        self.assertEqual(art['definitionReference']['branch']['id'], 'refs/heads/main')
        self.assertEqual(art['definitionReference']['branch']['name'], 'main')

    def test_produccion_dependency_updated(self):
        search = SearchEngine(self.definition, self.template['search'])
        matches = search.search_all()

        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, matches, update_rules, TemplateOptions())
        engine.apply_updates()

        prod = next(s for s in self.definition['environments'] if s['name'] == 'Producción')
        approver = prod['preDeployApprovals']['approvals'][0]['approver']['displayName']
        self.assertEqual(approver, 'Pre Deploy Validation')


if __name__ == '__main__':
    unittest.main()
