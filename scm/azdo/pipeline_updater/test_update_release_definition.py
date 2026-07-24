"""
Tests para AzureDevOpsClient.update_release_definition

Cubren el fix de persistencia del PUT a Azure DevOps:
- NO se debe incrementar la revisión (concurrencia optimista).
- La definición original no debe mutarse (deepcopy).
- Los campos de solo lectura deben eliminarse del cuerpo enviado.
- El cuerpo del error de la API debe incluirse en la excepción en HTTP 400.
"""

import unittest
from unittest.mock import patch, MagicMock

from .azdo_client import AzureDevOpsClient, AzureDevOpsError


class TestUpdateReleaseDefinition(unittest.TestCase):
    """Tests para update_release_definition"""

    def setUp(self):
        self.client = AzureDevOpsClient(
            pat="dummy_pat",
            org="Coppel-Retail",
            project="Cadena_de_Suministros"
        )
        self.definition = {
            'id': 2016,
            'name': 'Pipeline CD',
            'revision': 23,
            'environments': [
                {'id': 1, 'name': 'Develop', 'rank': 4},
                {'id': 2, 'name': 'QA', 'rank': 1},
            ],
            # Campos de solo lectura que deben eliminarse
            '_links': {'self': {'href': 'http://x'}},
            'url': 'http://x',
            'projectReference': None,
            'createdBy': {'displayName': 'user'},
            'createdOn': '2025-01-01',
            'modifiedBy': {'displayName': 'user'},
            'modifiedOn': '2025-01-02',
            'isDeleted': False,
            'isDisabled': False,
            'currentRelease': {'id': 1},
            'badgeUrl': 'http://badge',
            'lastRelease': {'id': 99},
        }

    def _mock_response(self, status_code=200, text=''):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.raise_for_status = MagicMock()
        return response

    @patch('scm.azdo.pipeline_updater.azdo_client.requests.put')
    def test_revision_not_incremented(self, mock_put):
        """La revisión enviada debe ser la MISMA que la descargada."""
        mock_put.return_value = self._mock_response(status_code=200)

        self.client.update_release_definition(2016, self.definition)

        sent_body = mock_put.call_args.kwargs['json']
        self.assertEqual(sent_body['revision'], 23)

    @patch('scm.azdo.pipeline_updater.azdo_client.requests.put')
    def test_original_definition_not_mutated(self, mock_put):
        """La definición original no debe modificarse (deepcopy)."""
        mock_put.return_value = self._mock_response(status_code=200)

        self.client.update_release_definition(2016, self.definition)

        # Campos de solo lectura siguen presentes en el original
        self.assertIn('_links', self.definition)
        self.assertIn('lastRelease', self.definition)
        self.assertEqual(self.definition['revision'], 23)

    @patch('scm.azdo.pipeline_updater.azdo_client.requests.put')
    def test_readonly_fields_removed(self, mock_put):
        """Los campos de solo lectura deben eliminarse del cuerpo enviado."""
        mock_put.return_value = self._mock_response(status_code=200)

        self.client.update_release_definition(2016, self.definition)

        sent_body = mock_put.call_args.kwargs['json']
        readonly_fields = [
            '_links', 'url', 'projectReference', 'createdBy', 'createdOn',
            'modifiedBy', 'modifiedOn', 'isDeleted', 'isDisabled',
            'currentRelease', 'badgeUrl', 'lastRelease'
        ]
        for field in readonly_fields:
            self.assertNotIn(field, sent_body)

        # Campos válidos se conservan
        self.assertIn('environments', sent_body)
        self.assertIn('name', sent_body)

    @patch('scm.azdo.pipeline_updater.azdo_client.requests.put')
    def test_success_returns_true(self, mock_put):
        """HTTP 200 debe retornar True."""
        mock_put.return_value = self._mock_response(status_code=200)

        result = self.client.update_release_definition(2016, self.definition)
        self.assertTrue(result)

    @patch('scm.azdo.pipeline_updater.azdo_client.requests.put')
    def test_http_400_includes_error_body(self, mock_put):
        """HTTP 400 debe lanzar AzureDevOpsError incluyendo el cuerpo del error."""
        error_body = '{"message":"You are using an old copy of the release pipeline."}'
        mock_put.return_value = self._mock_response(status_code=400, text=error_body)

        with self.assertRaises(AzureDevOpsError) as ctx:
            self.client.update_release_definition(2016, self.definition)

        self.assertIn('400', str(ctx.exception))
        self.assertIn('old copy', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
