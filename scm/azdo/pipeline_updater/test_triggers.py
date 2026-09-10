"""Tests para triggers, artifact filters y variables en UpdateEngine."""

import copy
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


class TestVariableActions(unittest.TestCase):
    """Tests para _process_variable_actions (add/update/remove)"""

    def setUp(self):
        self.definition = {
            'environments': [
                {'id': 1, 'name': 'Develop', 'rank': 1},
                {'id': 2, 'name': 'QA', 'rank': 2},
                {'id': 3, 'name': 'Production', 'rank': 3},
            ],
            'variables': {
                'ExistingVar': {
                    'value': 'old_value',
                    'allowOverride': True
                }
            }
        }

    def test_add_new_variable(self):
        """Agregar una variable que no existe"""
        update_rules = {
            'variables': [
                {
                    'name': 'DataDogScriptPermission',
                    'action': 'add',
                    'value': 'base64encodedvalue',
                    'allowOverride': True
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        self.assertIn('DataDogScriptPermission', self.definition['variables'])
        self.assertEqual(
            self.definition['variables']['DataDogScriptPermission']['value'],
            'base64encodedvalue'
        )
        self.assertTrue(
            self.definition['variables']['DataDogScriptPermission']['allowOverride']
        )

        add_changes = [c for c in engine.get_changes() if c['type'] == 'variable_add']
        self.assertEqual(len(add_changes), 1)
        self.assertEqual(add_changes[0]['name'], 'DataDogScriptPermission')

    def test_add_existing_variable_updates_value(self):
        """Agregar variable que ya existe actualiza el valor"""
        update_rules = {
            'variables': [
                {
                    'name': 'ExistingVar',
                    'action': 'add',
                    'value': 'new_value'
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        self.assertEqual(
            self.definition['variables']['ExistingVar']['value'],
            'new_value'
        )

        update_changes = [c for c in engine.get_changes() if c['type'] == 'variable_update']
        self.assertEqual(len(update_changes), 1)

    def test_update_existing_variable(self):
        """Actualizar una variable existente con action: update"""
        update_rules = {
            'variables': [
                {
                    'name': 'ExistingVar',
                    'action': 'update',
                    'value': 'updated_value',
                    'allowOverride': False
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        self.assertEqual(
            self.definition['variables']['ExistingVar']['value'],
            'updated_value'
        )
        self.assertFalse(
            self.definition['variables']['ExistingVar']['allowOverride']
        )

    def test_update_nonexistent_variable_skipped(self):
        """Actualizar variable que no existe es skip silencioso"""
        update_rules = {
            'variables': [
                {
                    'name': 'NonExistent',
                    'action': 'update',
                    'value': 'value'
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        self.assertNotIn('NonExistent', self.definition['variables'])
        changes = [c for c in engine.get_changes() if c['type'] == 'variable_update']
        self.assertEqual(len(changes), 0)

    def test_remove_existing_variable(self):
        """Eliminar una variable existente"""
        update_rules = {
            'variables': [
                {
                    'name': 'ExistingVar',
                    'action': 'remove'
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        self.assertNotIn('ExistingVar', self.definition['variables'])
        remove_changes = [c for c in engine.get_changes() if c['type'] == 'variable_remove']
        self.assertEqual(len(remove_changes), 1)

    def test_remove_nonexistent_variable_skipped(self):
        """Eliminar variable que no existe es skip silencioso"""
        update_rules = {
            'variables': [
                {
                    'name': 'NonExistent',
                    'action': 'remove'
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        remove_changes = [c for c in engine.get_changes() if c['type'] == 'variable_remove']
        self.assertEqual(len(remove_changes), 0)

    def test_add_secret_variable(self):
        """Agregar una variable con isSecret: true"""
        update_rules = {
            'variables': [
                {
                    'name': 'SecretVar',
                    'action': 'add',
                    'value': 'secret_value',
                    'isSecret': True
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        self.assertIn('SecretVar', self.definition['variables'])
        self.assertTrue(self.definition['variables']['SecretVar']['isSecret'])

    def test_add_variable_default_allow_override(self):
        """Agregar variable sin allowOverride usa default True"""
        update_rules = {
            'variables': [
                {
                    'name': 'DefaultVar',
                    'action': 'add',
                    'value': 'val'
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        self.assertTrue(
            self.definition['variables']['DefaultVar']['allowOverride']
        )

    def test_add_variable_scope_release_explicit(self):
        """Agregar variable con scope: release explicito"""
        update_rules = {
            'variables': [
                {
                    'name': 'ReleaseVar',
                    'action': 'add',
                    'scope': 'release',
                    'value': 'release_value'
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        self.assertIn('ReleaseVar', self.definition['variables'])
        self.assertEqual(
            self.definition['variables']['ReleaseVar']['value'],
            'release_value'
        )
        add_changes = [c for c in engine.get_changes() if c['type'] == 'variable_add']
        self.assertEqual(add_changes[0]['scope'], 'release')

    def test_add_variable_scope_environment(self):
        """Agregar variable con scope: environment a un stage especifico"""
        self.definition['environments'][0]['variables'] = {}
        update_rules = {
            'variables': [
                {
                    'name': 'StageVar',
                    'action': 'add',
                    'scope': 'environment',
                    'stage': 'Develop',
                    'value': 'stage_value'
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        env_vars = self.definition['environments'][0].get('variables', {})
        self.assertIn('StageVar', env_vars)
        self.assertEqual(env_vars['StageVar']['value'], 'stage_value')
        add_changes = [c for c in engine.get_changes() if c['type'] == 'variable_add']
        self.assertEqual(add_changes[0]['scope'], 'environment:Develop')

    def test_add_variable_scope_environment_nonexistent_stage(self):
        """Agregar variable con scope environment a stage inexistente es skip"""
        update_rules = {
            'variables': [
                {
                    'name': 'StageVar',
                    'action': 'add',
                    'scope': 'environment',
                    'stage': 'NonExistent',
                    'value': 'val'
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        add_changes = [c for c in engine.get_changes() if c['type'] == 'variable_add']
        self.assertEqual(len(add_changes), 0)

    def test_add_variable_scope_environment_without_stage_raises(self):
        """Scope environment sin stage lanza ValueError capturado por apply_updates"""
        update_rules = {
            'variables': [
                {
                    'name': 'StageVar',
                    'action': 'add',
                    'scope': 'environment',
                    'value': 'val'
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        result = engine.apply_updates()
        self.assertFalse(result)
        self.assertEqual(len(engine.get_changes()), 0)

    def test_remove_variable_scope_environment(self):
        """Eliminar variable con scope environment"""
        self.definition['environments'][0]['variables'] = {
            'StageVar': {'value': 'val', 'allowOverride': True}
        }
        update_rules = {
            'variables': [
                {
                    'name': 'StageVar',
                    'action': 'remove',
                    'scope': 'environment',
                    'stage': 'Develop'
                }
            ]
        }
        engine = UpdateEngine(self.definition, [], update_rules)
        engine.apply_updates()

        self.assertNotIn('StageVar', self.definition['environments'][0].get('variables', {}))
        remove_changes = [c for c in engine.get_changes() if c['type'] == 'variable_remove']
        self.assertEqual(len(remove_changes), 1)


class TestCreateFoldersLogsAddVariableTemplate(unittest.TestCase):
    """Tests para el template pipe_cd_update_task_create_folders_logs_add_var_datadogscriptpermision.yaml

    Valida el flujo completo:
    1. Search: stages Develop, QA y patron ^\\d{2}-
    2. Search: task "Create folders logs" en los stages encontrados
    3. Update: inputs.inline de la task encontrada (SSH task usa inputs.inline)
    4. Update: add variable DataDogScriptPermission scope release
    """

    SEARCH_RULES = {
        'stages': [
            {'name': 'Develop'},
            {'name': 'QA'},
            {'pattern': r'^\d{2}-'},
        ],
        'tasks': [
            {'name': 'Create folders logs'},
        ],
    }

    EXPECTED_SCRIPT = (
        "printf '%s' \"$(DataDogScriptPermission)\" | base64 -d | sh -s -- "
        "\"$(pathConfig)\" \"$(artifact.fileProperties)\"\n"
    )

    UPDATE_RULES = {
        'tasks': [
            {
                'name': 'Create folders logs',
                'fields': [
                    {
                        'path': 'inputs.inline',
                        'new_value': EXPECTED_SCRIPT,
                    }
                ],
            }
        ],
        'variables': [
            {
                'name': 'DataDogScriptPermission',
                'action': 'add',
                'scope': 'release',
                'value': 'IyEvYmluL3NoCnNldCAtZXUKCkJBU0VfUEFUSD0kMQ==',
                'allowOverride': True,
                'isSecret': False,
            }
        ],
    }

    def setUp(self):
        self.definition = {
            'environments': [
                {
                    'id': 1, 'name': 'Develop', 'rank': 1,
                    'deployPhases': [{
                        'deploymentInput': {
                            'tasks': [{
                                'displayName': 'Create folders logs',
                                'enabled': True,
                                'task': {'id': 'task-id', 'versionSpec': '1.*'},
                                'inputs': {'inline': 'old_inline_develop'},
                            }]
                        }
                    }]
                },
                {
                    'id': 2, 'name': 'QA', 'rank': 2,
                    'deployPhases': [{
                        'deploymentInput': {
                            'tasks': [{
                                'displayName': 'Create folders logs',
                                'enabled': True,
                                'task': {'id': 'task-id', 'versionSpec': '1.*'},
                                'inputs': {'inline': 'old_inline_qa'},
                            }]
                        }
                    }]
                },
                {
                    'id': 3, 'name': '01-Cedis Norte', 'rank': 3,
                    'deployPhases': [{
                        'deploymentInput': {
                            'tasks': [{
                                'displayName': 'Create folders logs',
                                'enabled': True,
                                'task': {'id': 'task-id', 'versionSpec': '1.*'},
                                'inputs': {'inline': 'old_inline_01'},
                            }]
                        }
                    }]
                },
                {
                    'id': 4, 'name': '02-Cedis Sur', 'rank': 4,
                    'deployPhases': [{
                        'deploymentInput': {
                            'tasks': [{
                                'displayName': 'Create folders logs',
                                'enabled': True,
                                'task': {'id': 'task-id', 'versionSpec': '1.*'},
                                'inputs': {'inline': 'old_inline_02'},
                            }]
                        }
                    }]
                },
                {
                    'id': 5, 'name': 'Production', 'rank': 5,
                    'deployPhases': [{
                        'deploymentInput': {
                            'tasks': [{
                                'displayName': 'Create folders logs',
                                'enabled': True,
                                'task': {'id': 'task-id', 'versionSpec': '1.*'},
                                'inputs': {'inline': 'old_inline_prod'},
                            }]
                        }
                    }]
                },
            ],
            'variables': {},
        }

    def test_search_finds_correct_stages(self):
        """Search debe encontrar Develop, QA, 01-Cedis Norte, 02-Cedis Sur (NO Production)"""
        engine = SearchEngine(self.definition, self.SEARCH_RULES)
        matches = engine.search_all()

        stage_matches = [m for m in matches if m.type == 'stage']
        stage_names = {m.name for m in stage_matches}
        self.assertIn('Develop', stage_names)
        self.assertIn('QA', stage_names)
        self.assertIn('01-Cedis Norte', stage_names)
        self.assertIn('02-Cedis Sur', stage_names)
        self.assertNotIn('Production', stage_names)

    def test_search_finds_tasks_in_all_stages(self):
        """Search encuentra 'Create folders logs' en TODOS los stages (sin filtro stage en criterio)"""
        engine = SearchEngine(self.definition, self.SEARCH_RULES)
        matches = engine.search_all()

        task_matches = [m for m in matches if m.type == 'task']
        # Sin campo 'stage' en el criterio de task, search_tasks busca en todos los stages
        self.assertEqual(len(task_matches), 5)

        task_stage_names = {m.stage_name for m in task_matches}
        self.assertIn('Develop', task_stage_names)
        self.assertIn('QA', task_stage_names)
        self.assertIn('01-Cedis Norte', task_stage_names)
        self.assertIn('02-Cedis Sur', task_stage_names)
        self.assertIn('Production', task_stage_names)

    def test_update_modifies_inline_in_all_stages(self):
        """Update modifica inputs.inline en TODOS los stages donde encontro la task"""
        engine = SearchEngine(self.definition, self.SEARCH_RULES)
        matches = engine.search_all()

        update_engine = UpdateEngine(
            self.definition, matches, self.UPDATE_RULES
        )
        update_engine.apply_updates()

        for env in self.definition['environments']:
            for phase in env.get('deployPhases', []):
                tasks = phase.get('deploymentInput', {}).get('tasks', [])
                for task in tasks:
                    if task.get('displayName') == 'Create folders logs':
                        # Sin filtro stage en task criteria, la task se actualiza en todos los stages
                        self.assertEqual(
                            task['inputs']['inline'],
                            self.EXPECTED_SCRIPT,
                            f"Inline no actualizado en stage {env['name']}"
                        )

    def test_variable_added_to_release_scope(self):
        """La variable DataDogScriptPermission debe agregarse a definition.variables"""
        engine = SearchEngine(self.definition, self.SEARCH_RULES)
        matches = engine.search_all()

        update_engine = UpdateEngine(
            self.definition, matches, self.UPDATE_RULES
        )
        update_engine.apply_updates()

        self.assertIn('DataDogScriptPermission', self.definition['variables'])
        var = self.definition['variables']['DataDogScriptPermission']
        self.assertEqual(
            var['value'],
            'IyEvYmluL3NoCnNldCAtZXUKCkJBU0VfUEFUSD0kMQ=='
        )
        self.assertTrue(var['allowOverride'])

    def test_combined_task_and_variable_changes(self):
        """El engine debe reportar tanto cambios de task como de variable"""
        engine = SearchEngine(self.definition, self.SEARCH_RULES)
        matches = engine.search_all()

        update_engine = UpdateEngine(
            self.definition, matches, self.UPDATE_RULES
        )
        update_engine.apply_updates()

        changes = update_engine.get_changes()
        task_changes = [c for c in changes if c['type'] == 'task_field']
        var_changes = [c for c in changes if c['type'] == 'variable_add']

        # 5 stages con la task (sin filtro stage en criterio)
        self.assertEqual(len(task_changes), 5)
        self.assertEqual(len(var_changes), 1)
        self.assertEqual(var_changes[0]['name'], 'DataDogScriptPermission')
        self.assertEqual(var_changes[0]['scope'], 'release')

    def test_no_task_changes_when_task_not_found(self):
        """Si la task no existe en ningun stage, solo se agrega la variable"""
        no_task_def = {
            'environments': [
                {
                    'id': 1, 'name': 'Develop', 'rank': 1,
                    'deployPhases': [{
                        'deploymentInput': {
                            'tasks': [{
                                'displayName': 'Other Task',
                                'enabled': True,
                                'inputs': {'inline': 'original'},
                            }]
                        }
                    }]
                }
            ],
            'variables': {},
        }
        engine = SearchEngine(no_task_def, self.SEARCH_RULES)
        matches = engine.search_all()

        update_engine = UpdateEngine(
            no_task_def, matches, self.UPDATE_RULES
        )
        update_engine.apply_updates()

        task_changes = [c for c in update_engine.get_changes() if c['type'] == 'task_field']
        var_changes = [c for c in update_engine.get_changes() if c['type'] == 'variable_add']
        self.assertEqual(len(task_changes), 0)
        self.assertEqual(len(var_changes), 1)

    def test_variable_added_even_if_task_not_found(self):
        """La variable se agrega aunque la task no exista en los stages"""
        def_no_task = copy.deepcopy(self.definition)
        for env in def_no_task['environments']:
            for phase in env.get('deployPhases', []):
                tasks = phase.get('deploymentInput', {}).get('tasks', [])
                for t in tasks:
                    t['displayName'] = 'Other Task'

        engine = SearchEngine(def_no_task, self.SEARCH_RULES)
        matches = engine.search_all()

        update_engine = UpdateEngine(
            def_no_task, matches, self.UPDATE_RULES
        )
        update_engine.apply_updates()

        self.assertIn('DataDogScriptPermission', def_no_task['variables'])
        var_changes = [c for c in update_engine.get_changes() if c['type'] == 'variable_add']
        self.assertEqual(len(var_changes), 1)
        task_changes = [c for c in update_engine.get_changes() if c['type'] == 'task_field']
        self.assertEqual(len(task_changes), 0)

    def test_existing_variable_gets_updated_not_duplicated(self):
        """Si la variable ya existe, se actualiza el valor (no se duplica)"""
        self.definition['variables']['DataDogScriptPermission'] = {
            'value': 'old_base64_value',
            'allowOverride': False,
        }
        engine = SearchEngine(self.definition, self.SEARCH_RULES)
        matches = engine.search_all()

        update_engine = UpdateEngine(
            self.definition, matches, self.UPDATE_RULES
        )
        update_engine.apply_updates()

        var = self.definition['variables']['DataDogScriptPermission']
        self.assertEqual(
            var['value'],
            'IyEvYmluL3NoCnNldCAtZXUKCkJBU0VfUEFUSD0kMQ=='
        )
        self.assertTrue(var['allowOverride'])

        update_changes = [c for c in update_engine.get_changes() if c['type'] == 'variable_update']
        self.assertEqual(len(update_changes), 1)
        add_changes = [c for c in update_engine.get_changes() if c['type'] == 'variable_add']
        self.assertEqual(len(add_changes), 0)

    def test_workflow_tasks_format_also_updated(self):
        """El engine debe actualizar tasks en formato workflowTasks tambien"""
        def_workflow = {
            'environments': [
                {
                    'id': 1, 'name': 'Develop', 'rank': 1,
                    'deployPhases': [{
                        'workflowTasks': [{
                            'name': 'Create folders logs',
                            'enabled': True,
                            'inputs': {'inline': 'old_workflow_inline'},
                        }]
                    }]
                },
                {
                    'id': 2, 'name': 'QA', 'rank': 2,
                    'deployPhases': [{
                        'workflowTasks': [{
                            'name': 'Create folders logs',
                            'enabled': True,
                            'inputs': {'inline': 'old_workflow_qa'},
                        }]
                    }]
                },
            ],
            'variables': {},
        }
        engine = SearchEngine(def_workflow, self.SEARCH_RULES)
        matches = engine.search_all()

        update_engine = UpdateEngine(
            def_workflow, matches, self.UPDATE_RULES
        )
        update_engine.apply_updates()

        for env in def_workflow['environments']:
            for phase in env.get('deployPhases', []):
                for task in phase.get('workflowTasks', []):
                    if task.get('name') == 'Create folders logs':
                        self.assertEqual(
                            task['inputs']['inline'],
                            self.EXPECTED_SCRIPT,
                            f"Inline no actualizado en {env['name']}"
                        )


if __name__ == '__main__':
    unittest.main()
