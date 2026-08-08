"""
Tests para las 4 templates más recientes.

Valida que cada template, al ser aplicada via UpdateEngine a una definición
de pipeline simulada, produce los cambios esperados.

Templates cubiertas:
1. pipe_cd_insert_stage_with_n_tasks.yaml
2. pipe_cd_rename_all_cedis_13-Villa_Hermosa_to_regional_13-Villa_Hermosa.yaml
3. pipe_cd_rename_all_cedis_texcoco_to_regional_24-Texcoco.yaml
4. pipe_cd_insert_task_before_show_manifest.yaml
"""

import unittest
import yaml
from pathlib import Path
from .update_engine import UpdateEngine
from .search_engine import SearchEngine
from .template_parser import TemplateParser
from .models import TemplateOptions

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def load_template(filename: str) -> dict:
    """Cargar template YAML desde el directorio de templates."""
    path = TEMPLATES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Template no encontrado: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# =============================================================================
# 1. pipe_cd_insert_stage_with_n_tasks.yaml
# =============================================================================
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
        """El template carga y tiene la estructura esperada"""
        self.assertEqual(self.template['metadata']['version'], '2.1')
        self.assertIn('search', self.template)
        self.assertIn('update', self.template)

    def test_search_finds_stages_and_artifacts(self):
        """Search encuentra Staging, Producción y el Build artifact"""
        search = SearchEngine(self.definition, self.template['search'])
        matches = search.search_all()
        stage_matches = [m for m in matches if m.type == 'stage']
        artifact_matches = [m for m in matches if m.type == 'artifact']
        self.assertEqual(len(stage_matches), 2)
        self.assertGreaterEqual(len(artifact_matches), 1)

    def test_insert_new_stage_between(self):
        """Inserta 'Pre Deploy Validation' entre Staging y Producción"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        names = [s['name'] for s in self.definition['environments']]
        self.assertIn('Pre Deploy Validation', names)
        self.assertGreater(names.index('Pre Deploy Validation'), names.index('Staging'))
        self.assertLess(names.index('Pre Deploy Validation'), names.index('Producción'))

    def test_new_stage_has_3_tasks(self):
        """El nuevo stage contiene 3 tasks"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        new_stage = next(s for s in self.definition['environments'] if s['name'] == 'Pre Deploy Validation')
        tasks = new_stage['deployPhases'][0]['deploymentInput']['tasks']
        self.assertEqual(len(tasks), 3)

    def test_produccion_rank_is_3(self):
        """Producción queda con rank 3 después del reordenamiento"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        prod = next(s for s in self.definition['environments'] if s['name'] == 'Producción')
        self.assertEqual(prod['rank'], 3)

    def test_trigger_add_resolves_auto(self):
        """El trigger add con $auto resuelve al alias del Build artifact"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        triggers = self.definition.get('triggers', [])
        self.assertEqual(len(triggers), 1)
        self.assertEqual(triggers[0]['triggerConfiguration']['artifactName'], '_mybuild')

    def test_artifact_branch_updated_to_main(self):
        """El artifact branch se actualiza a refs/heads/main"""
        # Necesitamos que search encuentre el artifact para que _update_artifact se ejecute
        search = SearchEngine(self.definition, self.template['search'])
        matches = search.search_all()
        artifact_matches = [m for m in matches if m.type == 'artifact']

        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, matches, update_rules, TemplateOptions())
        engine.apply_updates()

        art = self.definition['artifacts'][0]
        self.assertEqual(art['definitionReference']['branch']['id'], 'refs/heads/main')
        self.assertEqual(art['definitionReference']['branch']['name'], 'main')

    def test_produccion_dependency_updated(self):
        """Producción depende de 'Pre Deploy Validation' (no de Staging)"""
        # Necesitamos matches para que _update_stage procese los fields
        search = SearchEngine(self.definition, self.template['search'])
        matches = search.search_all()

        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, matches, update_rules, TemplateOptions())
        engine.apply_updates()

        prod = next(s for s in self.definition['environments'] if s['name'] == 'Producción')
        approver = prod['preDeployApprovals']['approvals'][0]['approver']['displayName']
        self.assertEqual(approver, 'Pre Deploy Validation')


# =============================================================================
# 2. pipe_cd_rename_all_cedis_13-Villa_Hermosa_to_regional_13-Villa_Hermosa.yaml
# =============================================================================
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
        """El template carga correctamente"""
        self.assertEqual(self.template['metadata']['version'], '1.1')
        self.assertEqual(self.template['update']['stages'][0]['action'], 'rename')

    def test_rename_1_culiacan_to_01_culiacan(self):
        """Renombra '1-Culiacan' a '01-Culiacan'"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        names = [s['name'] for s in self.definition['environments']]
        self.assertIn('01-Culiacan', names)
        self.assertNotIn('1-Culiacan', names)

    def test_rename_preserves_id_and_rank(self):
        """El rename preserva el ID y rank del stage original"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        renamed = next(s for s in self.definition['environments'] if s['name'] == '01-Culiacan')
        self.assertEqual(renamed['id'], 1)
        self.assertEqual(renamed['rank'], 1)

    def test_rename_updates_dependency_references(self):
        """Las dependencias que referencian al stage viejo se actualizan"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        qa = next(s for s in self.definition['environments'] if s['name'] == 'QA')
        cond = qa['conditions'][0]
        self.assertEqual(cond['name'], '01-Culiacan')

    def test_rename_nonexistent_stage_is_noop(self):
        """Si el stage no existe, el rename es silencioso (no-op)"""
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
        """La opción ignore_variable_groups se parsea correctamente"""
        opts = self.template['options']
        self.assertIn('ignore_variable_groups', opts)
        self.assertIn('all', opts['ignore_variable_groups'])
        self.assertIn(186, opts['ignore_variable_groups']['all'])
        self.assertIn(196, opts['ignore_variable_groups']['all'])

    def test_replace_agent_pools_option_parsed(self):
        """La opción replace_agent_pools se parsea correctamente"""
        opts = self.template['options']
        self.assertIn('replace_agent_pools', opts)
        self.assertEqual(opts['replace_agent_pools'][1749], 5331)
        self.assertEqual(opts['replace_agent_pools'][2722], 5331)


# =============================================================================
# 3. pipe_cd_rename_all_cedis_texcoco_to_regional_24-Texcoco.yaml
# =============================================================================
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
        """El template carga correctamente"""
        self.assertEqual(self.template['metadata']['version'], '1.1')
        self.assertEqual(self.template['update']['stages'][0]['action'], 'rename')

    def test_rename_cedis_texcoco_to_24_texcoco(self):
        """Renombra 'Cedis Texcoco' a '24-Texcoco'"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        names = [s['name'] for s in self.definition['environments']]
        self.assertIn('24-Texcoco', names)
        self.assertNotIn('Cedis Texcoco', names)

    def test_rename_preserves_id_and_rank(self):
        """El rename preserva el ID y rank del stage original"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        renamed = next(s for s in self.definition['environments'] if s['name'] == '24-Texcoco')
        self.assertEqual(renamed['id'], 2)
        self.assertEqual(renamed['rank'], 2)

    def test_rename_updates_dependency_references(self):
        """Las dependencias que referencian a 'Cedis Texcoco' se actualizan"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        prod = next(s for s in self.definition['environments'] if s['name'] == 'Production')
        cond = prod['conditions'][0]
        self.assertEqual(cond['name'], '24-Texcoco')

    def test_rename_nonexistent_stage_is_noop(self):
        """Si el stage no existe, el rename es silencioso"""
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
        """Este template no tiene ignore_variable_groups"""
        opts = self.template['options']
        self.assertNotIn('ignore_variable_groups', opts)


# =============================================================================
# 4. pipe_cd_insert_task_before_show_manifest.yaml
# =============================================================================
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
        """El template carga correctamente"""
        self.assertEqual(self.template['metadata']['version'], '1.0')
        self.assertEqual(self.template['update']['tasks'][0]['action'], 'add')
        self.assertEqual(self.template['update']['tasks'][0]['before_task'], 'show Manifest')

    def test_insert_task_before_show_manifest_all_stages(self):
        """Inserta task 'clean Manifest' antes de 'show Manifest' en todos los stages"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        for env in self.definition['environments']:
            tasks = env['deployPhases'][0]['deploymentInput']['tasks']
            names = [t['displayName'] for t in tasks]
            self.assertIn('clean Manifest', names)
            self.assertLess(names.index('clean Manifest'), names.index('show Manifest'))

    def test_inserted_task_has_correct_properties(self):
        """La task insertada tiene las propiedades del template"""
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
        """No inserta nada si 'show Manifest' no existe en el stage"""
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
        """Se inserta exactamente una task por stage que tiene 'show Manifest'"""
        update_rules = self.template['update']
        engine = UpdateEngine(self.definition, [], update_rules, TemplateOptions())
        engine.apply_updates()

        changes = [c for c in engine.get_changes() if c['type'] == 'task_add']
        self.assertEqual(len(changes), 2)

    def test_inserted_task_uses_filepath_input(self):
        """La task insertada usa filePath (no script) como input"""
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
