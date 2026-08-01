"""
Tests para funcionalidad de deshabilitar (soft-delete) pipelines CD.

Cubren:
- TemplateParser.get_pipeline_action() parsea correctamente 'disable'
- TemplateParser.get_pipeline_action() retorna None para templates normales
- AzureDevOpsClient.delete_release_definition() llama DELETE correctamente
- ParallelExecutor._process_pipeline() ramifica al flujo de disable
- Validator acepta templates con update.pipeline.action
"""

import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock, PropertyMock

from .azdo_client import AzureDevOpsClient, AzureDevOpsError, PipelineNotFoundError, PermissionDeniedError
from .template_parser import TemplateParser
from .validator import TemplateValidator
from .parallel_executor import ParallelExecutor
from .models import UpdateResult


DISABLE_TEMPLATE_YAML = """\
metadata:
  name: "Deshabilitar Pipeline CD"
  version: "1.0"
  description: "Soft-delete pipeline"
  comment: "Pipeline deshabilitado via pipeline_updater"
  author: "test"
  created_at: "2026-07-31"

search:
  stages:
    - name: "Production"

update:
  pipeline:
    action: "disable"

options:
  dry_run: false
  rollback_on_error: true
"""

NORMAL_TEMPLATE_YAML = """\
metadata:
  name: "Update normal"
  version: "1.0"
  description: "Update normal template"

search:
  stages:
    - name: "Production"

update:
  stages:
    - name: "Production"
      rank: 1

options:
  dry_run: false
  rollback_on_error: true
"""


class TestTemplateParserPipelineAction(unittest.TestCase):
    """Tests para TemplateParser.get_pipeline_action"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _write_template(self, content):
        path = os.path.join(self.tmpdir, 'template.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_get_pipeline_action_returns_disable(self):
        """get_pipeline_action debe retornar 'disable' cuando el template lo especifica"""
        path = self._write_template(DISABLE_TEMPLATE_YAML)
        parser = TemplateParser(path)
        self.assertEqual(parser.get_pipeline_action(), 'disable')

    def test_get_pipeline_action_returns_none_for_normal_template(self):
        """get_pipeline_action debe retornar None para templates normales"""
        path = self._write_template(NORMAL_TEMPLATE_YAML)
        parser = TemplateParser(path)
        self.assertIsNone(parser.get_pipeline_action())

    def test_get_pipeline_action_returns_none_when_no_pipeline_key(self):
        """get_pipeline_action debe retornar None cuando no hay clave pipeline"""
        yaml_no_pipeline = """\
metadata:
  name: "test"
  version: "1.0"
search:
  stages:
    - name: "QA"
update:
  stages:
    - name: "QA"
      rank: 1
options:
  dry_run: false
"""
        path = self._write_template(yaml_no_pipeline)
        parser = TemplateParser(path)
        self.assertIsNone(parser.get_pipeline_action())


class TestValidatorAcceptsPipelineAction(unittest.TestCase):
    """Tests para que el validator acepte update.pipeline como regla valida"""

    def test_validator_accepts_disable_template(self):
        """Validator no debe generar errores para un template con pipeline.action: disable"""
        template = {
            'metadata': {'name': 'test', 'version': '1.0'},
            'search': {'stages': [{'name': 'Production'}]},
            'update': {'pipeline': {'action': 'disable'}},
            'options': {'dry_run': False, 'rollback_on_error': True}
        }
        validator = TemplateValidator(template)
        self.assertTrue(validator.validate())
        self.assertEqual(validator.get_errors(), [])

    def test_validator_no_warning_for_pipeline_only(self):
        """Validator no debe generar warning cuando update solo tiene pipeline"""
        template = {
            'metadata': {'name': 'test', 'version': '1.0'},
            'search': {'stages': [{'name': 'Production'}]},
            'update': {'pipeline': {'action': 'disable'}},
            'options': {}
        }
        validator = TemplateValidator(template)
        validator.validate()
        warnings_about_update = [w for w in validator.get_warnings() if 'update' in w.lower()]
        self.assertEqual(warnings_about_update, [])


class TestDisableReleaseDefinition(unittest.TestCase):
    """Tests para AzureDevOpsClient.update_release_definition con disable=True"""

    def setUp(self):
        self.client = AzureDevOpsClient(
            pat="dummy_pat",
            org="https://dev.azure.com/Coppel-Retail",
            project="Cadena_de_Suministros"
        )
        self.definition = {
            'id': 2016,
            'name': 'Pipeline CD',
            'revision': 23,
            'environments': [],
            'isDisabled': False,
        }

    def _mock_response(self, status_code=200, text=''):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.raise_for_status = MagicMock()
        return response

    @patch('scm.azdo.pipeline_updater.azdo_client.requests.put')
    def test_disable_sets_is_disabled_true(self, mock_put):
        """update_release_definition con disable=True debe setear isDisabled=true en el body"""
        mock_put.return_value = self._mock_response(200)

        self.client.update_release_definition(2016, self.definition, disable=True)

        sent_body = mock_put.call_args.kwargs['json']
        self.assertTrue(sent_body.get('isDisabled'))

    @patch('scm.azdo.pipeline_updater.azdo_client.requests.put')
    def test_disable_keeps_is_disabled_in_body(self, mock_put):
        """update_release_definition con disable=True NO debe remover isDisabled del body"""
        mock_put.return_value = self._mock_response(200)

        self.client.update_release_definition(2016, self.definition, disable=True)

        sent_body = mock_put.call_args.kwargs['json']
        self.assertIn('isDisabled', sent_body)

    @patch('scm.azdo.pipeline_updater.azdo_client.requests.put')
    def test_normal_update_strips_is_disabled(self, mock_put):
        """update_release_definition sin disable debe remover isDisabled del body"""
        mock_put.return_value = self._mock_response(200)

        self.client.update_release_definition(2016, self.definition)

        sent_body = mock_put.call_args.kwargs['json']
        self.assertNotIn('isDisabled', sent_body)

    @patch('scm.azdo.pipeline_updater.azdo_client.requests.put')
    def test_disable_returns_true_on_200(self, mock_put):
        """update_release_definition con disable=True debe retornar True en 200"""
        mock_put.return_value = self._mock_response(200)

        result = self.client.update_release_definition(2016, self.definition, disable=True)
        self.assertTrue(result)

    @patch('scm.azdo.pipeline_updater.azdo_client.requests.put')
    def test_disable_raises_error_on_500(self, mock_put):
        """update_release_definition con disable=True debe lanzar AzureDevOpsError en 500"""
        mock_put.return_value = self._mock_response(500, 'Internal server error')

        with self.assertRaises(AzureDevOpsError):
            self.client.update_release_definition(2016, self.definition, disable=True)


class TestParallelExecutorDisableFlow(unittest.TestCase):
    """Tests para ParallelExecutor._process_pipeline con action: disable"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        template_path = os.path.join(self.tmpdir, 'disable_template.yaml')
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(DISABLE_TEMPLATE_YAML)
        self.parser = TemplateParser(template_path)

    def _mock_azdo_client(self, definition_id=2016):
        client = MagicMock()
        client.get_release_definition.return_value = {
            'id': definition_id,
            'name': 'Pipeline CD Test',
            'revision': 5,
            'environments': [
                {'id': 1, 'name': 'Production', 'rank': 1}
            ]
        }
        client.create_snapshot.return_value = f'snapshot_{definition_id}_1234567890'
        client.update_release_definition.return_value = True
        return client

    def test_disable_flow_calls_update_with_disable_true(self):
        """Cuando pipeline_action='disable', debe llamar update_release_definition con disable=True"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertTrue(result.success)
        client.update_release_definition.assert_called_once()
        call_kwargs = client.update_release_definition.call_args
        self.assertEqual(call_kwargs.args[0], 2016)
        self.assertTrue(call_kwargs.kwargs.get('disable'))

    def test_disable_flow_creates_snapshot_before_disable(self):
        """El flujo disable debe crear snapshot antes de deshabilitar (para rollback)"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        client.create_snapshot.assert_called_once()
        self.assertTrue(result.snapshot_id)
        self.assertIn('snapshot', result.snapshot_id)

    def test_disable_flow_records_change_type(self):
        """El resultado del disable debe tener changes con type='pipeline_disable'"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0]['type'], 'pipeline_disable')
        self.assertEqual(result.changes[0]['definition_id'], 2016)

    def test_disable_flow_still_searches_matches(self):
        """El flujo disable debe buscar coincidencias para validar que el pipeline aplica"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        # El pipeline tiene "Production" y el template busca "Production"
        self.assertGreater(result.matches_found, 0)

    def test_disable_flow_error_returns_failure(self):
        """Si update con disable falla, el resultado debe ser success=False con error"""
        client = self._mock_azdo_client()
        client.update_release_definition.side_effect = AzureDevOpsError("API error")
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2016, self.parser, client)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn('API error', result.error)
