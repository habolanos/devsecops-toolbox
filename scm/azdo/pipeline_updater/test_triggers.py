"""Tests para triggers y artifact filters en UpdateEngine."""

import unittest
import json
from .update_engine import UpdateEngine
from .search_engine import SearchEngine
from .models import Match, TemplateOptions


class TestTriggers(unittest.TestCase):
    """Tests para _process_trigger_actions y _update_trigger"""

    def setUp(self):
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'Staging', 'rank': 1},
                {'id': 2, 'name': 'Produccion', 'rank': 2},
            ],
            'triggers': [
                {
                    'triggerType': 'artifactSource',
                    'triggerConfiguration': {
                        'artifactName': '_myartifact',
                        'branchFilters': ['+refs/heads/dev'],
                        'useDefaultBranch': True,
                    }
                }
            ],
            'artifacts': [
                {
                    'alias': '_myartifact',
                    'type': 'Build',
                    'definitionReference': {
                        'branch': {'id': 'refs/heads/dev', 'name': 'dev'}
                    }
                }
            ]
        }

    def test_add_trigger(self):
        """Agregar un nuevo artifact trigger."""
        update_rules = {
            'triggers': [
                {
                    'action': 'add',
                    'triggerType': 'schedule',
                    'triggerConfiguration': {
                        'triggerType': 'schedule',
                        'scheduleDays': 'Monday',
                        'scheduleTime': '03:00',
                    }
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        triggers = self.definition['triggers']
        self.assertEqual(len(triggers), 2)
        self.assertEqual(triggers[1]['triggerType'], 'schedule')

        changes = engine.get_changes()
        add_changes = [c for c in changes if c['type'] == 'trigger_add']
        self.assertEqual(len(add_changes), 1)

    def test_update_trigger_branch_filters(self):
        """Actualizar branchFilters de un trigger existente."""
        update_rules = {
            'triggers': [
                {
                    'action': 'update',
                    'triggerType': 'artifactSource',
                    'artifactName': '_myartifact',
                    'fields': [
                        {'path': 'branchFilters', 'new_value': ['+refs/heads/main']},
                        {'path': 'useDefaultBranch', 'new_value': False},
                    ]
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        trig_config = self.definition['triggers'][0]['triggerConfiguration']
        self.assertEqual(trig_config['branchFilters'], ['+refs/heads/main'])
        self.assertFalse(trig_config['useDefaultBranch'])

        changes = engine.get_changes()
        update_changes = [c for c in changes if c['type'] == 'trigger_update']
        self.assertEqual(len(update_changes), 2)

    def test_remove_trigger(self):
        """Remover un trigger existente."""
        update_rules = {
            'triggers': [
                {
                    'action': 'remove',
                    'triggerType': 'artifactSource',
                    'artifactName': '_myartifact',
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        triggers = self.definition['triggers']
        self.assertEqual(len(triggers), 0)

        changes = engine.get_changes()
        remove_changes = [c for c in changes if c['type'] == 'trigger_remove']
        self.assertEqual(len(remove_changes), 1)

    def test_update_artifact_branch_filter(self):
        """Actualizar branch filter de un artifact via fields."""
        # Primero buscar el artifact
        search_rules = {
            'stages': [{'name': 'Staging'}],
            'artifacts': [{'alias': '_myartifact', 'type': 'Build'}],
        }
        se = SearchEngine(self.definition, search_rules)
        matches = se.search_all()

        artifact_matches = [m for m in matches if m.type == 'artifact']
        self.assertEqual(len(artifact_matches), 1)

        update_rules = {
            'artifacts': [
                {
                    'name': '_myartifact',
                    'fields': [
                        {'path': 'definitionReference.branch.id', 'new_value': 'refs/heads/main'},
                        {'path': 'definitionReference.branch.name', 'new_value': 'main'},
                    ]
                }
            ]
        }
        engine = UpdateEngine(self.definition, matches, update_rules)
        engine.apply_updates()

        artifact = self.definition['artifacts'][0]
        self.assertEqual(artifact['definitionReference']['branch']['id'], 'refs/heads/main')
        self.assertEqual(artifact['definitionReference']['branch']['name'], 'main')

        changes = engine.get_changes()
        artifact_changes = [c for c in changes if c['type'] == 'artifact_field']
        self.assertEqual(len(artifact_changes), 2)

    def test_search_triggers(self):
        """Buscar triggers via search_engine."""
        search_rules = {
            'stages': [{'name': 'Staging'}],
            'triggers': [{'triggerType': 'artifactSource'}],
        }
        se = SearchEngine(self.definition, search_rules)
        matches = se.search_all()

        trigger_matches = [m for m in matches if m.type == 'trigger']
        self.assertEqual(len(trigger_matches), 1)
        self.assertEqual(trigger_matches[0].name, 'artifactSource')

    def test_no_triggers_in_definition(self):
        """Manejar definicion sin triggers (lista vacia o ausente)."""
        definition = {'environments': [{'id': 1, 'name': 'Staging', 'rank': 1}]}
        update_rules = {
            'triggers': [
                {
                    'action': 'add',
                    'triggerType': 'artifactSource',
                    'triggerConfiguration': {
                        'artifactName': '_artifact',
                        'branchFilters': ['+refs/heads/main'],
                    }
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules)
        engine.apply_updates()

        self.assertIn('triggers', definition)
        self.assertEqual(len(definition['triggers']), 1)


class TestStageTriggerOnExisting(unittest.TestCase):
    """Tests for trigger override on existing stages via _update_stage."""

    def setUp(self):
        self.definition = {
            'environments': [
                {
                    'id': 1, 'name': 'SCM Inspection', 'rank': 1,
                    'conditions': [
                        {'name': 'ReleaseStarted', 'conditionType': 'event', 'value': '', 'result': None}
                    ]
                },
                {
                    'id': 2, 'name': 'Develop', 'rank': 2,
                    'conditions': [
                        {'name': 'ReleaseStarted', 'conditionType': 'event', 'value': '', 'result': None},
                        {'name': '_myartifact', 'conditionType': 'artifact', 'value': '', 'result': None}
                    ]
                },
                {
                    'id': 3, 'name': 'QA', 'rank': 3,
                    'conditions': [
                        {'name': 'ReleaseStarted', 'conditionType': 'event', 'value': '', 'result': None},
                        {'name': '_myartifact', 'conditionType': 'artifact', 'value': '', 'result': None}
                    ]
                },
            ]
        }

    def test_trigger_after_stage_on_existing(self):
        """Configurar trigger after_stage en un stage existente."""
        search_rules = {
            'stages': [{'name': 'Develop'}, {'name': 'QA'}]
        }
        se = SearchEngine(self.definition, search_rules)
        matches = se.search_all()

        update_rules = {
            'stages': [
                {'name': 'SCM Inspection', 'rank': 1},
                {'name': 'Develop', 'rank': 2, 'trigger': 'after_stage', 'reference_stage': 'SCM Inspection'},
                {'name': 'QA', 'rank': 3, 'trigger': 'after_stage', 'reference_stage': 'SCM Inspection'},
            ]
        }
        engine = UpdateEngine(self.definition, matches, update_rules)
        engine.apply_updates()

        develop = self.definition['environments'][1]
        qa = self.definition['environments'][2]

        # Verificar que conditions tienen environmentState apuntando a SCM Inspection
        dev_conditions = develop['conditions']
        self.assertEqual(len(dev_conditions), 2)
        self.assertEqual(dev_conditions[0]['name'], 'SCM Inspection')
        self.assertEqual(dev_conditions[0]['conditionType'], 'environmentState')
        self.assertEqual(dev_conditions[0]['value'], '4')

        # Verificar que artifact filter se preservó
        self.assertEqual(dev_conditions[1]['conditionType'], 'artifact')
        self.assertEqual(dev_conditions[1]['name'], '_myartifact')

        # Mismo check para QA
        qa_conditions = qa['conditions']
        self.assertEqual(len(qa_conditions), 2)
        self.assertEqual(qa_conditions[0]['name'], 'SCM Inspection')
        self.assertEqual(qa_conditions[0]['conditionType'], 'environmentState')
        self.assertEqual(qa_conditions[1]['conditionType'], 'artifact')

        # Verificar changes registrados
        changes = engine.get_changes()
        trigger_changes = [c for c in changes if c['type'] == 'stage_trigger_override']
        self.assertEqual(len(trigger_changes), 2)

    def test_trigger_after_release_on_existing(self):
        """Configurar trigger after_release en un stage existente."""
        search_rules = {'stages': [{'name': 'Develop'}]}
        se = SearchEngine(self.definition, search_rules)
        matches = se.search_all()

        update_rules = {
            'stages': [
                {'name': 'Develop', 'trigger': 'after_release'}
            ]
        }
        engine = UpdateEngine(self.definition, matches, update_rules)
        engine.apply_updates()

        develop = self.definition['environments'][1]
        conditions = develop['conditions']
        self.assertEqual(len(conditions), 2)
        self.assertEqual(conditions[0]['name'], 'ReleaseStarted')
        self.assertEqual(conditions[0]['conditionType'], 'event')
        # Artifact filter preservado
        self.assertEqual(conditions[1]['conditionType'], 'artifact')

    def test_trigger_none_on_existing(self):
        """Configurar trigger none (manual) en un stage existente."""
        search_rules = {'stages': [{'name': 'Develop'}]}
        se = SearchEngine(self.definition, search_rules)
        matches = se.search_all()

        update_rules = {
            'stages': [
                {'name': 'Develop', 'trigger': 'none'}
            ]
        }
        engine = UpdateEngine(self.definition, matches, update_rules)
        engine.apply_updates()

        develop = self.definition['environments'][1]
        conditions = develop['conditions']
        # Solo debe quedar el artifact filter
        self.assertEqual(len(conditions), 1)
        self.assertEqual(conditions[0]['conditionType'], 'artifact')

    def test_trigger_after_stage_without_reference_raises(self):
        """trigger after_stage sin reference_stage debe lanzar error."""
        search_rules = {'stages': [{'name': 'Develop'}]}
        se = SearchEngine(self.definition, search_rules)
        matches = se.search_all()

        update_rules = {
            'stages': [
                {'name': 'Develop', 'trigger': 'after_stage'}
            ]
        }
        engine = UpdateEngine(self.definition, matches, update_rules)
        # apply_updates captura excepciones y retorna False
        result = engine.apply_updates()
        self.assertFalse(result)


class TestDryRunExecution(unittest.TestCase):
    """Tests para dry-run en ParallelExecutor."""

    def setUp(self):
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'SCM Inspection', 'rank': 1},
                {'id': 2, 'name': 'Develop', 'rank': 2},
                {'id': 3, 'name': 'QA', 'rank': 3},
                {'id': 4, 'name': 'Validator', 'rank': 4},
                {'id': 5, 'name': 'Production', 'rank': 5},
            ],
            'triggers': [],
            'artifacts': [],
        }

    def test_dry_run_skips_snapshot_and_put(self):
        """En dry-run, no se crea snapshot ni se envia PUT a AzDO."""
        from .parallel_executor import ParallelExecutor
        from unittest.mock import MagicMock

        class FakeParser:
            def get_search_rules(self):
                return {'stages': [{'name': 'SCM Inspection'}, {'name': 'Develop'}]}
            def get_update_rules(self):
                return {'stages': [
                    {'name': 'SCM Inspection', 'rank': 1},
                    {'name': 'Develop', 'rank': 2, 'trigger': 'after_stage', 'reference_stage': 'SCM Inspection'},
                ]}
            def get_template_options(self):
                return TemplateOptions(dry_run=True)
            def get_pipeline_action(self):
                return None
            def get_metadata(self):
                from .models import TemplateMetadata
                return TemplateMetadata(
                    name='test', version='1.0', description='test',
                    comment='test', author='test', created_at='2026-01-01'
                )

        azdo_client = MagicMock()
        azdo_client.get_release_definition.return_value = self.definition

        executor = ParallelExecutor(max_workers=1)
        result = executor.execute(
            [1], FakeParser(), azdo_client, dry_run=True
        )

        # No snapshot created
        azdo_client.create_snapshot.assert_not_called()
        # No PUT to Azure DevOps
        azdo_client.update_release_definition.assert_not_called()
        # But definition was downloaded (read-only)
        azdo_client.get_release_definition.assert_called_once_with(1)
        # Result should be successful
        self.assertEqual(result['success'], 1)
        self.assertEqual(result['failed'], 0)

    def test_non_dry_run_makes_snapshot_and_put(self):
        """En modo normal, se crea snapshot y se envia PUT a AzDO."""
        from .parallel_executor import ParallelExecutor
        from unittest.mock import MagicMock

        class FakeParser:
            def get_search_rules(self):
                return {'stages': [{'name': 'SCM Inspection'}, {'name': 'Develop'}]}
            def get_update_rules(self):
                return {'stages': [
                    {'name': 'SCM Inspection', 'rank': 1},
                    {'name': 'Develop', 'rank': 2, 'trigger': 'after_stage', 'reference_stage': 'SCM Inspection'},
                ]}
            def get_template_options(self):
                return TemplateOptions(dry_run=False)
            def get_pipeline_action(self):
                return None
            def get_metadata(self):
                from .models import TemplateMetadata
                return TemplateMetadata(
                    name='test', version='1.0', description='test',
                    comment='test', author='test', created_at='2026-01-01'
                )

        azdo_client = MagicMock()
        azdo_client.get_release_definition.return_value = self.definition
        azdo_client.create_snapshot.return_value = 'snap_123'
        azdo_client.update_release_definition.return_value = True

        executor = ParallelExecutor(max_workers=1)
        result = executor.execute(
            [1], FakeParser(), azdo_client, dry_run=False
        )

        # Snapshot created
        azdo_client.create_snapshot.assert_called_once()
        # PUT to Azure DevOps
        azdo_client.update_release_definition.assert_called_once()
        # Result should be successful
        self.assertEqual(result['success'], 1)
        self.assertEqual(result['failed'], 0)


if __name__ == '__main__':
    unittest.main()
