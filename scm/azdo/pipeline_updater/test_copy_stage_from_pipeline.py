"""
Tests para action: copy_from en stages (cross-pipeline copy)
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock

from scm.azdo.pipeline_updater.parallel_executor import ParallelExecutor
from scm.azdo.pipeline_updater.template_parser import TemplateParser
from scm.azdo.pipeline_updater.validator import TemplateValidator


COPY_FROM_TEMPLATE_YAML = """\
metadata:
  name: "Copiar stage desde otro pipeline"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758
      source_stage: "QA"
      new_name: "QA-Copia"
      position: "after"
      reference_stage: "Develop"
      task_updates:
        - task_name: "Deploy to QA"
          fields:
            - path: "inputs.namespace"
              new_value: "qa-copia"

options:
  dry_run: false
  rollback_on_error: true
"""


class TestTemplateParserCopyFrom(unittest.TestCase):
    """Tests para el parser con action: copy_from"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.template_path = os.path.join(self.tmpdir, 'copy_from_template.yaml')
        with open(self.template_path, 'w', encoding='utf-8') as f:
            f.write(COPY_FROM_TEMPLATE_YAML)
        self.parser = TemplateParser(self.template_path)

    def test_parser_loads_copy_from_rule(self):
        stages = self.parser.get_update_rules().get('stages', [])
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0]['action'], 'copy_from')

    def test_parser_extracts_source_definition_id(self):
        stages = self.parser.get_update_rules().get('stages', [])
        self.assertEqual(stages[0]['source_definition_id'], 2758)

    def test_parser_extracts_source_stage(self):
        stages = self.parser.get_update_rules().get('stages', [])
        self.assertEqual(stages[0]['source_stage'], 'QA')

    def test_parser_extracts_new_name(self):
        stages = self.parser.get_update_rules().get('stages', [])
        self.assertEqual(stages[0]['new_name'], 'QA-Copia')

    def test_parser_extracts_task_updates(self):
        stages = self.parser.get_update_rules().get('stages', [])
        task_updates = stages[0].get('task_updates', [])
        self.assertEqual(len(task_updates), 1)
        self.assertEqual(task_updates[0]['task_name'], 'Deploy to QA')

    def test_validator_accepts_copy_from(self):
        validator = TemplateValidator(self.parser.to_dict())
        self.assertTrue(validator.validate())
        self.assertEqual(validator.get_errors(), [])


class TestParallelExecutorCopyFrom(unittest.TestCase):
    """Tests para ParallelExecutor con action: copy_from"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.template_path = os.path.join(self.tmpdir, 'copy_from_template.yaml')
        with open(self.template_path, 'w', encoding='utf-8') as f:
            f.write(COPY_FROM_TEMPLATE_YAML)
        self.parser = TemplateParser(self.template_path)

    def _mock_azdo_client(self, target_id=2760, source_id=2758):
        client = MagicMock()

        # Pipeline destino (sin stage "QA-Copia")
        client.get_release_definition.side_effect = lambda def_id: {
            def_id: {
                'id': def_id,
                'name': f'Pipeline {def_id}',
                'revision': 5,
                'environments': [
                    {'id': 1, 'name': 'Develop', 'rank': 1},
                    {'id': 2, 'name': 'Production', 'rank': 2},
                ]
            },
            source_id: {
                'id': source_id,
                'name': f'Pipeline {source_id}',
                'revision': 10,
                'environments': [
                    {'id': 1, 'name': 'Build', 'rank': 1},
                    {
                        'id': 2,
                        'name': 'QA',
                        'rank': 2,
                        'deployPhases': [{
                            'deploymentInput': {
                                'tasks': [{
                                    'displayName': 'Deploy to QA',
                                    'inputs': {'namespace': 'qa'}
                                }]
                            }
                        }]
                    },
                    {'id': 3, 'name': 'Production', 'rank': 3},
                ]
            }
        }.get(def_id, {})

        client.create_snapshot.return_value = f'snapshot_{target_id}_1234567890'
        client.update_release_definition.return_value = True
        return client

    def test_copy_from_downloads_source_pipeline(self):
        """copy_from debe descargar el pipeline origen"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, self.parser, client)

        self.assertTrue(result.success)
        # get_release_definition debe llamarse al menos 2 veces:
        # 1 para el pipeline destino, 1 para el origen
        self.assertGreaterEqual(client.get_release_definition.call_count, 2)

    def test_copy_from_inserts_stage_in_target(self):
        """copy_from debe insertar el stage copiado en el pipeline destino"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, self.parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']
        names = [e['name'] for e in envs]
        self.assertIn('QA-Copia', names)

    def test_copy_from_inserts_after_reference_stage(self):
        """copy_from debe insertar despues del reference_stage"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, self.parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']
        names = [e['name'] for e in envs]
        develop_idx = names.index('Develop')
        copia_idx = names.index('QA-Copia')
        self.assertGreater(copia_idx, develop_idx)

    def test_copy_from_applies_task_updates(self):
        """copy_from debe aplicar task_updates al stage copiado"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, self.parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']
        copia_stage = next(e for e in envs if e['name'] == 'QA-Copia')
        tasks = copia_stage['deployPhases'][0]['deploymentInput']['tasks']
        deploy_task = next(t for t in tasks if t['displayName'] == 'Deploy to QA')
        self.assertEqual(deploy_task['inputs']['namespace'], 'qa-copia')

    def test_copy_from_renumbers_ranks(self):
        """copy_from debe renumerar ranks consecutivamente"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, self.parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']
        ranks = [e['rank'] for e in envs]
        self.assertEqual(ranks, list(range(1, len(envs) + 1)))

    def test_copy_from_missing_source_definition_id_raises(self):
        """copy_from sin source_definition_id debe fallar"""
        bad_template = """\
metadata:
  name: "Bad copy_from"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_stage: "QA"
      new_name: "QA-Copia"

options:
  dry_run: false
"""
        path = os.path.join(self.tmpdir, 'bad_template.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(bad_template)
        bad_parser = TemplateParser(path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, bad_parser, client)

        self.assertFalse(result.success)
        self.assertIn('source_definition_id', result.error)

    def test_copy_from_source_stage_not_found_raises(self):
        """copy_from con source_stage inexistente debe fallar"""
        bad_template = """\
metadata:
  name: "Bad copy_from"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758
      source_stage: "NonExistent"
      new_name: "QA-Copia"

options:
  dry_run: false
"""
        path = os.path.join(self.tmpdir, 'bad_template2.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(bad_template)
        bad_parser = TemplateParser(path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, bad_parser, client)

        self.assertFalse(result.success)
        self.assertIn('NonExistent', result.error)

    def test_copy_from_preserves_source_stage_structure(self):
        """copy_from debe preservar la estructura del stage origen"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, self.parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']
        copia_stage = next(e for e in envs if e['name'] == 'QA-Copia')
        # Debe tener deployPhases como el stage original
        self.assertIn('deployPhases', copia_stage)
        self.assertEqual(len(copia_stage['deployPhases']), 1)

    def test_copy_from_creates_snapshot(self):
        """copy_from debe crear snapshot antes de modificar"""
        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, self.parser, client)

        self.assertTrue(result.success)
        self.assertTrue(client.create_snapshot.called)
        self.assertTrue(result.snapshot_id)

    def test_copy_from_trigger_after_release(self):
        """trigger: after_release debe setear condition ReleaseStarted"""
        template = """\
metadata:
  name: "Copy with trigger"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758
      source_stage: "QA"
      new_name: "QA-Copia"
      position: "start"
      trigger: "after_release"

options:
  dry_run: false
"""
        path = os.path.join(self.tmpdir, 'trigger_template.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(template)
        parser = TemplateParser(path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        copia_stage = next(e for e in sent_def['environments'] if e['name'] == 'QA-Copia')
        conditions = copia_stage.get('conditions', [])
        event_conds = [c for c in conditions if c.get('conditionType') == 'event']
        self.assertEqual(len(event_conds), 1)
        self.assertEqual(event_conds[0]['name'], 'ReleaseStarted')

    def test_copy_from_trigger_after_stage(self):
        """trigger: after_stage debe setear dependency a reference_stage"""
        template = """\
metadata:
  name: "Copy with trigger after_stage"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758
      source_stage: "QA"
      new_name: "QA-Copia"
      position: "after"
      reference_stage: "Develop"
      trigger: "after_stage"

options:
  dry_run: false
"""
        path = os.path.join(self.tmpdir, 'trigger_after_stage.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(template)
        parser = TemplateParser(path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        copia_stage = next(e for e in sent_def['environments'] if e['name'] == 'QA-Copia')
        conditions = copia_stage.get('conditions', [])
        state_conds = [c for c in conditions if c.get('conditionType') == 'environmentState']
        self.assertEqual(len(state_conds), 1)
        self.assertEqual(state_conds[0]['name'], 'Develop')

    def test_copy_from_trigger_none(self):
        """trigger: none debe dejar conditions vacias (excepto artifact filters)"""
        template = """\
metadata:
  name: "Copy with trigger none"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758
      source_stage: "QA"
      new_name: "QA-Copia"
      position: "start"
      trigger: "none"

options:
  dry_run: false
"""
        path = os.path.join(self.tmpdir, 'trigger_none.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(template)
        parser = TemplateParser(path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        copia_stage = next(e for e in sent_def['environments'] if e['name'] == 'QA-Copia')
        conditions = copia_stage.get('conditions', [])
        # No debe haber conditions de tipo event o environmentState
        non_artifact = [c for c in conditions if c.get('conditionType') != 'artifact']
        self.assertEqual(len(non_artifact), 0)

    def test_copy_from_trigger_preserves_artifact_filters(self):
        """trigger override debe preservar artifact filters"""
        client = MagicMock()

        source_stage = {
            'id': 2,
            'name': 'QA',
            'rank': 2,
            'conditions': [
                {'name': 'Develop', 'conditionType': 'environmentState', 'value': '4', 'result': None},
                {'name': '_artifact', 'conditionType': 'artifact', 'value': '{"sourceBranch":"develop"}', 'result': None},
            ],
            'deployPhases': [{'deploymentInput': {'tasks': []}}],
        }

        client.get_release_definition.side_effect = lambda def_id: {
            2760: {
                'id': 2760, 'name': 'Target', 'revision': 1,
                'environments': [
                    {'id': 1, 'name': 'Develop', 'rank': 1, 'conditions': []},
                ]
            },
            2758: {
                'id': 2758, 'name': 'Source', 'revision': 1,
                'environments': [source_stage],
            }
        }.get(def_id, {})

        client.create_snapshot.return_value = 'snap_123'
        client.update_release_definition.return_value = True

        template = """\
metadata:
  name: "Copy with artifact preservation"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758
      source_stage: "QA"
      new_name: "QA-Copia"
      position: "start"
      trigger: "after_release"

options:
  dry_run: false
"""
        path = os.path.join(self.tmpdir, 'trigger_artifact.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(template)
        parser = TemplateParser(path)

        executor = ParallelExecutor(max_workers=1)
        result = executor._process_pipeline(2760, parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        copia_stage = next(e for e in sent_def['environments'] if e['name'] == 'QA-Copia')
        conditions = copia_stage.get('conditions', [])
        artifact_conds = [c for c in conditions if c.get('conditionType') == 'artifact']
        self.assertEqual(len(artifact_conds), 1)
        self.assertEqual(artifact_conds[0]['name'], '_artifact')

    def test_copy_from_make_dependents(self):
        """make_dependents debe hacer que otros stages dependan del copiado"""
        template = """\
metadata:
  name: "Copy with make_dependents"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758
      source_stage: "QA"
      new_name: "SCM Inspection"
      position: "start"
      trigger: "after_release"
      make_dependents:
        - stage: "Develop"
        - stage: "Production"

options:
  dry_run: false
"""
        path = os.path.join(self.tmpdir, 'make_dependents.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(template)
        parser = TemplateParser(path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        envs = sent_def['environments']

        for dep_name in ('Develop', 'Production'):
            dep_stage = next(e for e in envs if e['name'] == dep_name)
            conditions = dep_stage.get('conditions', [])
            state_conds = [c for c in conditions if c.get('conditionType') == 'environmentState']
            self.assertEqual(len(state_conds), 1, f'{dep_name} should depend on SCM Inspection')
            self.assertEqual(state_conds[0]['name'], 'SCM Inspection')

    def test_copy_from_make_dependents_preserves_artifact_filters(self):
        """make_dependents debe preservar artifact filters de los stages dependientes"""
        client = MagicMock()

        source_stage = {
            'id': 2, 'name': 'SCM Inspection', 'rank': 1,
            'conditions': [{'name': 'ReleaseStarted', 'conditionType': 'event', 'value': '', 'result': None}],
            'deployPhases': [{'deploymentInput': {'tasks': []}}],
        }

        client.get_release_definition.side_effect = lambda def_id: {
            2760: {
                'id': 2760, 'name': 'Target', 'revision': 1,
                'environments': [
                    {
                        'id': 1, 'name': 'Develop', 'rank': 1,
                        'conditions': [
                            {'name': 'ReleaseStarted', 'conditionType': 'event', 'value': '', 'result': None},
                            {'name': '_artifact', 'conditionType': 'artifact', 'value': '{"sourceBranch":"develop"}', 'result': None},
                        ],
                    },
                ]
            },
            2758: {
                'id': 2758, 'name': 'Source', 'revision': 1,
                'environments': [source_stage],
            }
        }.get(def_id, {})

        client.create_snapshot.return_value = 'snap_123'
        client.update_release_definition.return_value = True

        template = """\
metadata:
  name: "Copy with make_dependents artifact"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758
      source_stage: "SCM Inspection"
      new_name: "SCM Inspection"
      position: "start"
      trigger: "after_release"
      make_dependents:
        - stage: "Develop"

options:
  dry_run: false
"""
        path = os.path.join(self.tmpdir, 'make_deps_artifact.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(template)
        parser = TemplateParser(path)

        executor = ParallelExecutor(max_workers=1)
        result = executor._process_pipeline(2760, parser, client)

        self.assertTrue(result.success)
        sent_def = client.update_release_definition.call_args.args[1]
        develop_stage = next(e for e in sent_def['environments'] if e['name'] == 'Develop')
        conditions = develop_stage.get('conditions', [])
        artifact_conds = [c for c in conditions if c.get('conditionType') == 'artifact']
        self.assertEqual(len(artifact_conds), 1)
        self.assertEqual(artifact_conds[0]['name'], '_artifact')

    def test_copy_from_trigger_invalid_raises(self):
        """trigger invalido debe fallar"""
        template = """\
metadata:
  name: "Copy with bad trigger"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758
      source_stage: "QA"
      new_name: "QA-Copia"
      position: "start"
      trigger: "invalid_trigger"

options:
  dry_run: false
"""
        path = os.path.join(self.tmpdir, 'bad_trigger.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(template)
        parser = TemplateParser(path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, parser, client)

        self.assertFalse(result.success)

    def test_copy_from_trigger_after_stage_without_reference_raises(self):
        """trigger after_stage sin reference_stage debe fallar"""
        template = """\
metadata:
  name: "Copy after_stage no ref"
  version: "1.0"

search:
  stages:
    - name: "*"

update:
  stages:
    - action: "copy_from"
      source_definition_id: 2758
      source_stage: "QA"
      new_name: "QA-Copia"
      position: "start"
      trigger: "after_stage"

options:
  dry_run: false
"""
        path = os.path.join(self.tmpdir, 'after_stage_no_ref.yaml')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(template)
        parser = TemplateParser(path)

        client = self._mock_azdo_client()
        executor = ParallelExecutor(max_workers=1)

        result = executor._process_pipeline(2760, parser, client)

        self.assertFalse(result.success)


class TestCopyFromTemplateRealFile(unittest.TestCase):
    """Tests con el archivo real de template"""

    def setUp(self):
        # Subir 3 niveles: pipeline_updater -> azdo -> scm -> templates
        self.templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)
            ))),
            'templates'
        )

    def test_real_template_loads(self):
        path = os.path.join(
            self.templates_dir,
            'pipe_cd_copy_stage_from_pipeline.yaml'
        )
        self.assertTrue(os.path.exists(path))
        parser = TemplateParser(path)
        meta = parser.get_metadata()
        self.assertIn('copiar', meta.name.lower())

    def test_real_template_has_copy_from_action(self):
        path = os.path.join(
            self.templates_dir,
            'pipe_cd_copy_stage_from_pipeline.yaml'
        )
        parser = TemplateParser(path)
        stages = parser.get_update_rules().get('stages', [])
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0]['action'], 'copy_from')

    def test_real_template_validator_passes(self):
        path = os.path.join(
            self.templates_dir,
            'pipe_cd_copy_stage_from_pipeline.yaml'
        )
        parser = TemplateParser(path)
        validator = TemplateValidator(parser.to_dict())
        self.assertTrue(validator.validate())


if __name__ == '__main__':
    unittest.main()
