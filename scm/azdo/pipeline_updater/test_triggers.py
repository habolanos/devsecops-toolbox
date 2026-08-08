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


if __name__ == '__main__':
    unittest.main()
