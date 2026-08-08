"""
Tests para pipe_cd_move_to_folder.yaml

Valida que el template de movimiento de pipeline funcione correctamente:
- El template carga y parsea action="move" con path destino
- TemplateParser.get_pipeline_action() retorna "move"
- TemplateParser.get_pipeline_path() retorna el path especificado
- ParallelExecutor._process_pipeline() ramifica al flujo de move
- El flujo move setea definition["path"] al valor del template
- El flujo move llama update_release_definition con la definicion modificada
- El resultado registra change type="pipeline_move" con old_path y new_path
- El flujo move crea snapshot antes de mover (para rollback)
- El flujo move busca coincidencias para validar que el pipeline aplica
- Si falta path, se genera error
- Validator acepta templates con update.pipeline.action: move
"""

import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock

from .azdo_client import AzureDevOpsError
from .template_parser import TemplateParser
from .validator import TemplateValidator
from .parallel_executor import ParallelExecutor
from .models import UpdateResult

import yaml
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def load_template(filename: str) -> dict:
    path = TEMPLATES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Template no encontrado: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


MOVE_TEMPLATE_YAML = """\
metadata:
  name: "Mover Pipeline CD a otra carpeta"
  version: "1.0"
  description: "Mover pipeline de carpeta"
  comment: "Pipeline movido via pipeline_updater"
  author: "test"
  created_at: "2026-08-08"

search:
  stages:
    - name: "*"

update:
  pipeline:
    action: "move"
    path: '\\Decomiso{current}'

options:
  dry_run: false
  rollback_on_error: true
"""

MOVE_TEMPLATE_ABSOLUTE_YAML = """\
metadata:
  name: "Mover Pipeline CD a path absoluto"
  version: "1.0"
  description: "Mover pipeline a path fijo"
  comment: "Pipeline movido via pipeline_updater"
  author: "test"
  created_at: "2026-08-08"

search:
  stages:
    - name: "*"

update:
  pipeline:
    action: "move"
    path: '\\Decomiso\\GCP\\Proyecto WMS\\Equipo WMS'

options:
  dry_run: false
  rollback_on_error: true
"""

MOVE_TEMPLATE_NO_PATH_YAML = """\
metadata:
  name: "Mover Pipeline CD sin path"
  version: "1.0"
  description: "Template invalido sin path"
  author: "test"
  created_at: "2026-08-08"

search:
  stages:
    - name: "*"

update:
  pipeline:
    action: "move"

options:
  dry_run: false
  rollback_on_error: true
"""


class TestMoveTemplateLoads(unittest.TestCase):
    """Tests de carga del template YAML"""

    def test_template_loads_correctly(self):
        template = load_template("pipe_cd_move_to_folder.yaml")
        self.assertEqual(template['metadata']['version'], '1.0')
        self.assertEqual(template['update']['pipeline']['action'], 'move')
        self.assertIn('path', template['update']['pipeline'])

    def test_template_has_path_value(self):
        template = load_template("pipe_cd_move_to_folder.yaml")
        path = template['update']['pipeline']['path']
        self.assertTrue(path.startswith('\\'))
        self.assertIn('Decomiso', path)
        self.assertIn('{current}', path)


class TestTemplateParserMoveAction(unittest.TestCase):
    """Tests para TemplateParser con action: move"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _write_template(self, content):
        path = os.path.join(self.tmpdir, 'template.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_get_pipeline_action_returns_move(self):
        path = self._write_template(MOVE_TEMPLATE_YAML)
        parser = TemplateParser(path)
        self.assertEqual(parser.get_pipeline_action(), 'move')

    def test_get_pipeline_path_returns_target(self):
        path = self._write_template(MOVE_TEMPLATE_YAML)
        parser = TemplateParser(path)
        result = parser.get_pipeline_path()
        self.assertIsNotNone(result)
        self.assertIn('Decomiso', result)
        self.assertIn('{current}', result)

    def test_get_pipeline_path_returns_none_when_missing(self):
        path = self._write_template(MOVE_TEMPLATE_NO_PATH_YAML)
        parser = TemplateParser(path)
        self.assertEqual(parser.get_pipeline_action(), 'move')
        self.assertIsNone(parser.get_pipeline_path())


class TestValidatorAcceptsMoveAction(unittest.TestCase):
    """Tests para que el validator acepte update.pipeline con action: move"""

    def test_validator_accepts_move_template(self):
        template = {
            'metadata': {'name': 'test', 'version': '1.0'},
            'search': {'stages': [{'name': '*'}]},
            'update': {'pipeline': {'action': 'move', 'path': '\\Folder\\Subfolder'}},
            'options': {'dry_run': False, 'rollback_on_error': True}
        }
        validator = TemplateValidator(template)
        self.assertTrue(validator.validate())
        self.assertEqual(validator.get_errors(), [])

    def test_validator_no_warning_for_move_only(self):
        template = {
            'metadata': {'name': 'test', 'version': '1.0'},
            'search': {'stages': [{'name': '*'}]},
            'update': {'pipeline': {'action': 'move', 'path': '\\Folder'}},
            'options': {}
        }
        validator = TemplateValidator(template)
        validator.validate()
        warnings_about_update = [w for w in validator.get_warnings() if 'update' in w.lower()]
        self.assertEqual(warnings_about_update, [])


class TestParallelExecutorMoveFlow(unittest.TestCase):
    """Tests para ParallelExecutor._process_pipeline con action: move"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        template_path = os.path.join(self.tmpdir, 'move_template.yaml')
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(MOVE_TEMPLATE_YAML)
        self.parser = TemplateParser(template_path)

    def _mock_azdo_client(self, definition_id=500, old_path='\\GCP\\Proyecto WMS\\Equipo WMS'):
        client = MagicMock()
        client.get_release_definition.return_value = {
            'id': definition_id,
            'name': 'Pipeline CD Test',
            'revision': 5,
            'path': old_path,
            'environments': [
                {'id': 1, 'name': 'Production', 'rank': 1}
            ]
        }
        client.create_snapshot.return_value = f'snapshot_{definition_id}_1234567890'
        client.update_release_definition.return_value = True
        return client

    def test_move_flow_sets_definition_path(self):
        """El flujo move debe resolver {current} y setear definition['path']"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        executor._process_pipeline(500, self.parser, client)

        sent_body = client.update_release_definition.call_args.args[1]
        # {current} se reemplaza por el path actual del pipeline
        self.assertEqual(sent_body['path'], '\\Decomiso\\GCP\\Proyecto WMS\\Equipo WMS')

    def test_move_flow_absolute_path_no_placeholder(self):
        """Path absoluto sin {current} se usa tal cual"""
        template_path = os.path.join(self.tmpdir, 'absolute_template.yaml')
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(MOVE_TEMPLATE_ABSOLUTE_YAML)
        parser = TemplateParser(template_path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        executor._process_pipeline(500, parser, client)

        sent_body = client.update_release_definition.call_args.args[1]
        self.assertEqual(sent_body['path'], '\\Decomiso\\GCP\\Proyecto WMS\\Equipo WMS')

    def test_move_flow_current_placeholder_with_empty_path(self):
        """{current} con path vacio resulta en solo el prefijo"""
        client = self._mock_azdo_client(old_path='')
        executor = ParallelExecutor(max_workers=1)

        executor._process_pipeline(500, self.parser, client)

        sent_body = client.update_release_definition.call_args.args[1]
        self.assertEqual(sent_body['path'], '\\Decomiso')

    def test_move_flow_calls_update_release_definition(self):
        """El flujo move debe llamar update_release_definition una vez"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        executor._process_pipeline(500, self.parser, client)

        client.update_release_definition.assert_called_once()

    def test_move_flow_creates_snapshot_before_move(self):
        """El flujo move debe crear snapshot antes de mover (para rollback)"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(500, self.parser, client)

        client.create_snapshot.assert_called_once()
        self.assertTrue(result.snapshot_id)
        self.assertIn('snapshot', result.snapshot_id)

    def test_move_flow_records_change_type(self):
        """El resultado del move debe tener changes con type='pipeline_move'"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(500, self.parser, client)

        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0]['type'], 'pipeline_move')
        self.assertEqual(result.changes[0]['definition_id'], 500)
        self.assertEqual(result.changes[0]['old_path'], '\\GCP\\Proyecto WMS\\Equipo WMS')
        self.assertEqual(result.changes[0]['new_path'], '\\Decomiso\\GCP\\Proyecto WMS\\Equipo WMS')

    def test_move_flow_different_current_paths(self):
        """{current} se resuelve correctamente con diferentes paths actuales"""
        client = self._mock_azdo_client(old_path='\\Other\\Folder')
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(500, self.parser, client)

        self.assertEqual(result.changes[0]['old_path'], '\\Other\\Folder')
        self.assertEqual(result.changes[0]['new_path'], '\\Decomiso\\Other\\Folder')

    def test_move_flow_still_searches_matches(self):
        """El flujo move debe buscar coincidencias para validar que el pipeline aplica"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(500, self.parser, client)

        self.assertGreater(result.matches_found, 0)

    def test_move_flow_returns_success(self):
        """El flujo move exitoso debe retornar success=True"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(500, self.parser, client)

        self.assertTrue(result.success)
        self.assertIsNone(result.error)

    def test_move_flow_error_returns_failure(self):
        """Si update falla en move, el resultado debe ser success=False con error"""
        client = self._mock_azdo_client()
        client.update_release_definition.side_effect = AzureDevOpsError("API error")
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(500, self.parser, client)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn('API error', result.error)

    def test_move_flow_without_path_raises_error(self):
        """Si el template no tiene path, el flujo move debe fallar"""
        template_path = os.path.join(self.tmpdir, 'no_path_template.yaml')
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(MOVE_TEMPLATE_NO_PATH_YAML)
        parser = TemplateParser(template_path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(500, parser, client)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn('path', result.error)

    def test_move_flow_with_empty_old_path(self):
        """Si el pipeline no tiene path previo, {current} se reemplaza por vacio"""
        client = self._mock_azdo_client(old_path='')
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(500, self.parser, client)

        self.assertTrue(result.success)
        self.assertEqual(result.changes[0]['old_path'], '')
        self.assertEqual(result.changes[0]['new_path'], '\\Decomiso')


if __name__ == '__main__':
    unittest.main()
