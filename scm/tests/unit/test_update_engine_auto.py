"""
Tests para _resolve_artifact_name y $auto en UpdateEngine.
"""

import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "azdo"))

from pipeline_updater.update_engine import UpdateEngine
from pipeline_updater.models import Match, TemplateOptions


def _make_definition(artifacts, triggers=None):
    return {
        'artifacts': artifacts,
        'triggers': triggers or [],
        'environments': [],
    }


class TestResolveArtifactName:
    """Tests para _resolve_artifact_name"""

    def test_resolve_auto_build(self):
        definition = _make_definition([
            {'alias': '_mybuild', 'type': 'Build'},
            {'alias': '_mygit', 'type': 'Git'},
        ])
        engine = UpdateEngine(definition, [], {}, TemplateOptions())
        result = engine._resolve_artifact_name('$auto')
        assert result == '_mybuild'

    def test_resolve_auto_git(self):
        definition = _make_definition([
            {'alias': '_mybuild', 'type': 'Build'},
            {'alias': '_mygit', 'type': 'Git'},
        ])
        engine = UpdateEngine(definition, [], {}, TemplateOptions())
        result = engine._resolve_artifact_name('$auto:Git')
        assert result == '_mygit'

    def test_resolve_auto_build_explicit(self):
        definition = _make_definition([
            {'alias': '_mybuild', 'type': 'Build'},
        ])
        engine = UpdateEngine(definition, [], {}, TemplateOptions())
        result = engine._resolve_artifact_name('$auto:Build')
        assert result == '_mybuild'

    def test_resolve_auto_no_artifacts(self):
        definition = _make_definition([])
        engine = UpdateEngine(definition, [], {}, TemplateOptions())
        result = engine._resolve_artifact_name('$auto')
        assert result == ''

    def test_resolve_auto_no_matching_type(self):
        definition = _make_definition([
            {'alias': '_mygit', 'type': 'Git'},
        ])
        engine = UpdateEngine(definition, [], {}, TemplateOptions())
        result = engine._resolve_artifact_name('$auto:Build')
        assert result == ''

    def test_resolve_non_auto_passthrough(self):
        definition = _make_definition([])
        engine = UpdateEngine(definition, [], {}, TemplateOptions())
        result = engine._resolve_artifact_name('_myartifact')
        assert result == '_myartifact'

    def test_resolve_empty_string(self):
        definition = _make_definition([])
        engine = UpdateEngine(definition, [], {}, TemplateOptions())
        result = engine._resolve_artifact_name('')
        assert result == ''


class TestTriggerAddWithAuto:
    """Tests para trigger add con $auto"""

    def test_add_trigger_resolves_auto(self):
        definition = _make_definition(
            [{'alias': '_mybuild', 'type': 'Build'}],
            triggers=[]
        )
        update_rules = {
            'triggers': [
                {
                    'action': 'add',
                    'triggerType': 'artifactSource',
                    'triggerConfiguration': {
                        'triggerType': 'artifactSource',
                        'artifactName': '$auto',
                        'branchFilters': ['+refs/heads/main'],
                        'useDefaultBranch': False,
                    }
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules, TemplateOptions())
        engine._process_trigger_actions(update_rules['triggers'])

        assert len(definition['triggers']) == 1
        assert definition['triggers'][0]['triggerConfiguration']['artifactName'] == '_mybuild'

    def test_add_trigger_resolves_auto_git(self):
        definition = _make_definition(
            [
                {'alias': '_mybuild', 'type': 'Build'},
                {'alias': '_myrepo', 'type': 'Git'},
            ],
            triggers=[]
        )
        update_rules = {
            'triggers': [
                {
                    'action': 'add',
                    'triggerType': 'artifactSource',
                    'triggerConfiguration': {
                        'triggerType': 'artifactSource',
                        'artifactName': '$auto:Git',
                        'branchFilters': ['+refs/heads/main'],
                        'useDefaultBranch': False,
                    }
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules, TemplateOptions())
        engine._process_trigger_actions(update_rules['triggers'])

        assert definition['triggers'][0]['triggerConfiguration']['artifactName'] == '_myrepo'


class TestTriggerUpdateWithAuto:
    """Tests para trigger update con $auto"""

    def test_update_trigger_resolves_auto(self):
        definition = _make_definition(
            [{'alias': '_mybuild', 'type': 'Build'}],
            triggers=[
                {
                    'triggerType': 'artifactSource',
                    'triggerConfiguration': {
                        'triggerType': 'artifactSource',
                        'artifactName': '_mybuild',
                        'branchFilters': ['+refs/heads/master'],
                        'useDefaultBranch': True,
                    }
                }
            ]
        )
        update_rules = {
            'triggers': [
                {
                    'action': 'update',
                    'triggerType': 'artifactSource',
                    'artifactName': '$auto',
                    'fields': [
                        {'path': 'branchFilters', 'new_value': ['+refs/heads/main']},
                        {'path': 'useDefaultBranch', 'new_value': False},
                    ]
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules, TemplateOptions())
        engine._process_trigger_actions(update_rules['triggers'])

        trig = definition['triggers'][0]['triggerConfiguration']
        assert trig['branchFilters'] == ['+refs/heads/main']
        assert trig['useDefaultBranch'] is False


class TestTriggerRemoveWithAuto:
    """Tests para trigger remove con $auto"""

    def test_remove_trigger_resolves_auto(self):
        definition = _make_definition(
            [{'alias': '_mybuild', 'type': 'Build'}],
            triggers=[
                {
                    'triggerType': 'artifactSource',
                    'triggerConfiguration': {
                        'triggerType': 'artifactSource',
                        'artifactName': '_mybuild',
                        'branchFilters': ['+refs/heads/main'],
                    }
                }
            ]
        )
        update_rules = {
            'triggers': [
                {
                    'action': 'remove',
                    'triggerType': 'artifactSource',
                    'artifactName': '$auto',
                }
            ]
        }
        engine = UpdateEngine(definition, [], update_rules, TemplateOptions())
        engine._process_trigger_actions(update_rules['triggers'])

        assert len(definition['triggers']) == 0
