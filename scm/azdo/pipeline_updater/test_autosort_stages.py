"""
Tests para la funcionalidad de auto-ordenamiento de stages numericos (autosort_stages).

Cubren:
- TemplateParser.get_pipeline_action() retorna 'autosort_stages'
- TemplateParser.get_pipeline_sort_config() parsea correctamente fixed_stages, sort_pattern, sort_order
- TemplateValidator acepta templates con action: autosort_stages
- ParallelExecutor._process_pipeline con action: autosort_stages
  - Separa stages fijos de numericos
  - Ordena numericos alfanumericamente
  - Mantiene orden de fijos
  - Renumbera ranks consecutivamente
  - Registra cambios con type='stage_autosort'
  - Crea snapshot antes de ordenar
  - Llama update_release_definition
  - Maneja errores
  - Preserva isDisabled
"""

import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock

from .azdo_client import AzureDevOpsClient, AzureDevOpsError
from .template_parser import TemplateParser
from .validator import TemplateValidator
from .parallel_executor import ParallelExecutor


AUTOSORT_TEMPLATE_YAML = """\
metadata:
  name: "Auto-ordenar stages numericos"
  version: "1.0"
  description: "Reordena stages numericos alfanumericamente"

search:
  stages:
    - name: "*"

update:
  pipeline:
    action: "autosort_stages"
    fixed_stages:
      - "Develop"
      - "QA"
      - "Production"
    sort_pattern: "^\\\\d+"
    sort_order: "asc"

options:
  dry_run: false
  rollback_on_error: true
"""

AUTOSORT_TEMPLATE_DEFAULTS_YAML = """\
metadata:
  name: "Auto-sort con defaults"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  pipeline:
    action: "autosort_stages"

options:
  dry_run: false
"""

AUTOSORT_TEMPLATE_DESC_YAML = """\
metadata:
  name: "Auto-sort descendente"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  pipeline:
    action: "autosort_stages"
    fixed_stages:
      - "Develop"
      - "QA"
    sort_pattern: "^\\\\d+"
    sort_order: "desc"

options:
  dry_run: false
"""


class TestTemplateParserAutosortAction(unittest.TestCase):
    """Tests para TemplateParser con action: autosort_stages"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.template_path = os.path.join(self.tmpdir, 'autosort_template.yaml')
        with open(self.template_path, 'w', encoding='utf-8') as f:
            f.write(AUTOSORT_TEMPLATE_YAML)
        self.parser = TemplateParser(self.template_path)

    def test_get_pipeline_action_returns_autosort(self):
        self.assertEqual(self.parser.get_pipeline_action(), 'autosort_stages')

    def test_get_pipeline_sort_config_fixed_stages(self):
        config = self.parser.get_pipeline_sort_config()
        self.assertEqual(config['fixed_stages'], ['Develop', 'QA', 'Production'])

    def test_get_pipeline_sort_config_pattern(self):
        config = self.parser.get_pipeline_sort_config()
        self.assertEqual(config['sort_pattern'], r'^\d+')

    def test_get_pipeline_sort_config_order(self):
        config = self.parser.get_pipeline_sort_config()
        self.assertEqual(config['sort_order'], 'asc')

    def test_get_pipeline_sort_config_defaults(self):
        path = os.path.join(self.tmpdir, 'defaults_template.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(AUTOSORT_TEMPLATE_DEFAULTS_YAML)
        parser = TemplateParser(path)
        config = parser.get_pipeline_sort_config()
        self.assertEqual(config['fixed_stages'], [])
        self.assertEqual(config['sort_pattern'], r'^\d+')
        self.assertEqual(config['sort_order'], 'asc')


class TestValidatorAcceptsAutosortAction(unittest.TestCase):
    """Tests para que el validator acepte update.pipeline con action: autosort_stages"""

    def test_validator_accepts_autosort_template(self):
        template = {
            'metadata': {'name': 'test', 'version': '1.0'},
            'search': {'stages': [{'name': '*'}]},
            'update': {'pipeline': {'action': 'autosort_stages', 'fixed_stages': ['Develop']}},
            'options': {}
        }
        validator = TemplateValidator(template)
        self.assertTrue(validator.validate())
        self.assertEqual(validator.get_errors(), [])

    def test_validator_no_warning_for_autosort_only(self):
        template = {
            'metadata': {'name': 'test', 'version': '1.0'},
            'search': {'stages': [{'name': '*'}]},
            'update': {'pipeline': {'action': 'autosort_stages'}},
            'options': {}
        }
        validator = TemplateValidator(template)
        validator.validate()
        update_warnings = [w for w in validator.get_warnings() if 'update' in w.lower()]
        self.assertEqual(update_warnings, [])


class TestParallelExecutorAutosortFlow(unittest.TestCase):
    """Tests para ParallelExecutor._process_pipeline con action: autosort_stages"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        template_path = os.path.join(self.tmpdir, 'autosort_template.yaml')
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(AUTOSORT_TEMPLATE_YAML)
        self.parser = TemplateParser(template_path)

    def _mock_azdo_client(self, definition_id=2016, environments=None):
        client = MagicMock()
        if environments is None:
            environments = [
                {'id': 1, 'name': 'Develop', 'rank': 1},
                {'id': 2, 'name': 'QA', 'rank': 2},
                {'id': 3, 'name': 'Production', 'rank': 3},
                {'id': 4, 'name': '03-Laguna', 'rank': 4},
                {'id': 5, 'name': '01-Culiacan', 'rank': 5},
                {'id': 6, 'name': '02-Leon', 'rank': 6},
            ]
        client.get_release_definition.return_value = {
            'id': definition_id,
            'name': 'Pipeline CD Test',
            'revision': 5,
            'environments': environments
        }
        client.create_snapshot.return_value = f'snapshot_{definition_id}_1234567890'
        client.update_release_definition.return_value = True
        return client

    def test_autosort_separates_fixed_from_numeric(self):
        """Los stages fijos deben mantener su posicion antes de los numericos"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']
        names = [e['name'] for e in envs]
        self.assertEqual(names[:3], ['Develop', 'QA', 'Production'])

    def test_autosort_sorts_numeric_stages_ascending(self):
        """Los stages numericos deben quedar en orden ascendente"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']
        names = [e['name'] for e in envs]
        self.assertEqual(names[3:], ['01-Culiacan', '02-Leon', '03-Laguna'])

    def test_autosort_renumbers_ranks_consecutively(self):
        """Todos los ranks deben ser consecutivos 1..N"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']
        ranks = [e['rank'] for e in envs]
        self.assertEqual(ranks, [1, 2, 3, 4, 5, 6])

    def test_autosort_records_change_type(self):
        """Los cambios deben tener type='stage_autosort'"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        autosort_changes = [c for c in result.changes if c['type'] == 'stage_autosort']
        self.assertGreater(len(autosort_changes), 0)

    def test_autosort_creates_snapshot_before_sort(self):
        """Debe crear snapshot antes de ordenar (para rollback)"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        client.create_snapshot.assert_called_once()
        self.assertTrue(result.snapshot_id)

    def test_autosort_calls_update_release_definition(self):
        """Debe llamar update_release_definition una vez"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        client.update_release_definition.assert_called_once()

    def test_autosort_returns_success(self):
        """El resultado exitoso debe ser success=True"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertTrue(result.success)
        self.assertIsNone(result.error)

    def test_autosort_error_returns_failure(self):
        """Si update falla, el resultado debe ser success=False con error"""
        client = self._mock_azdo_client()
        client.update_release_definition.side_effect = AzureDevOpsError("API error")
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn('API error', result.error)

    def test_autosort_no_changes_when_already_sorted(self):
        """Si los stages ya estan ordenados, no debe haber cambios"""
        environments = [
            {'id': 1, 'name': 'Develop', 'rank': 1},
            {'id': 2, 'name': 'QA', 'rank': 2},
            {'id': 3, 'name': 'Production', 'rank': 3},
            {'id': 4, 'name': '01-Culiacan', 'rank': 4},
            {'id': 5, 'name': '02-Leon', 'rank': 5},
        ]
        client = self._mock_azdo_client(environments=environments)
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertTrue(result.success)
        self.assertEqual(result.changes_applied, 0)

    def test_autosort_preserves_is_disabled(self):
        """Un pipeline disabled debe permanecer disabled despues del autosort"""
        client = self._mock_azdo_client()
        client.get_release_definition.return_value['isDisabled'] = True
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        self.assertTrue(sent_def.get('isDisabled', False))

    def test_autosort_desc_order(self):
        """Con sort_order=desc, los stages numericos deben quedar descendentes"""
        desc_template_path = os.path.join(self.tmpdir, 'desc_template.yaml')
        with open(desc_template_path, 'w', encoding='utf-8') as f:
            f.write(AUTOSORT_TEMPLATE_DESC_YAML)
        desc_parser = TemplateParser(desc_template_path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, desc_parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']
        names = [e['name'] for e in envs]
        # Develop y QA son fijos, luego numericos descendentes, luego Production va a "others"
        self.assertEqual(names[:2], ['Develop', 'QA'])
        self.assertEqual(names[2:5], ['03-Laguna', '02-Leon', '01-Culiacan'])

    def test_autosort_many_stages(self):
        """Test con muchos stages numericos desordenados"""
        environments = [
            {'id': 1, 'name': 'Develop', 'rank': 1},
            {'id': 2, 'name': 'QA', 'rank': 2},
            {'id': 3, 'name': 'Production', 'rank': 3},
        ]
        for i in range(1, 32):
            cedis_names = [
                "01-Culiacan", "02-Leon", "03-Laguna", "04-Mexicali", "05-Nogales",
                "06-Monterrey", "07-Guadalajara", "08-Azcapotzalco", "09-Nvo_Laredo",
                "10-CD_Juarez", "11-Hermosillo", "12-Puebla", "13-Villa Hermosa",
                "14-La_Paz", "15-Iztapalapa", "16-Izcalli", "17-Cancun", "18-Ixtapaluca",
                "19-Los_Mochis", "20-Tecamac", "21-Veracruz", "22-Merida", "23-Tlaquepaque",
                "24-Toluca", "25-Guadalupe", "26-Texcoco", "27-Tecamac2", "28-Tijuana",
                "29-Aguascalientes", "30-Chihuahua", "31-IMPTecamac"
            ]
        # Insertar desordenados
        import random
        shuffled = list(cedis_names)
        random.seed(42)
        random.shuffle(shuffled)
        for idx, name in enumerate(shuffled):
            environments.append({'id': idx + 4, 'name': name, 'rank': idx + 4})

        client = self._mock_azdo_client(environments=environments)
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']
        names = [e['name'] for e in envs]

        # Fijos primero
        self.assertEqual(names[:3], ['Develop', 'QA', 'Production'])
        # Numericos ordenados ascendentes
        numeric_names = names[3:]
        self.assertEqual(numeric_names, sorted(numeric_names))
        # Ranks consecutivos
        ranks = [e['rank'] for e in envs]
        self.assertEqual(ranks, list(range(1, len(envs) + 1)))


class TestAutosortTemplateRealFile(unittest.TestCase):
    """Tests end-to-end cargando el template real pipe_cd_autosort_stages.yaml"""

    def setUp(self):
        from pathlib import Path
        self.templates_dir = Path(__file__).parent.parent.parent / "templates"

    def test_real_template_loads(self):
        template_path = str(self.templates_dir / "pipe_cd_autosort_stages.yaml")
        parser = TemplateParser(template_path)
        self.assertEqual(parser.get_pipeline_action(), 'autosort_stages')

    def test_real_template_metadata(self):
        template_path = str(self.templates_dir / "pipe_cd_autosort_stages.yaml")
        parser = TemplateParser(template_path)
        meta = parser.get_metadata()
        self.assertIn('ordenar', meta.name.lower())

    def test_real_template_sort_config(self):
        template_path = str(self.templates_dir / "pipe_cd_autosort_stages.yaml")
        parser = TemplateParser(template_path)
        config = parser.get_pipeline_sort_config()
        self.assertIn('Develop', config['fixed_stages'])
        self.assertIn('QA', config['fixed_stages'])
        self.assertIn('Production', config['fixed_stages'])
        self.assertEqual(config['sort_order'], 'asc')

    def test_real_template_validator_passes(self):
        template_path = str(self.templates_dir / "pipe_cd_autosort_stages.yaml")
        parser = TemplateParser(template_path)
        validator = TemplateValidator(parser.to_dict())
        self.assertTrue(validator.validate())


if __name__ == '__main__':
    unittest.main()
