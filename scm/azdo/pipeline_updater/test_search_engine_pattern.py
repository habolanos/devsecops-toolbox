"""
Tests unitarios para soporte de pattern (regex) en search.stages.
"""

import unittest
from scm.azdo.pipeline_updater.search_engine import SearchEngine


class TestSearchEnginePattern(unittest.TestCase):

    def _build_definition(self, stage_names):
        return {
            'environments': [
                {'name': name, 'id': idx + 1}
                for idx, name in enumerate(stage_names)
            ]
        }

    def test_pattern_matches_numeric_stages(self):
        definition = self._build_definition([
            'SCM Inspection', 'Develop', 'QA', 'Production',
            '01-Culiacan', '02-Leon', '03-Laguna'
        ])
        rules = {
            'stages': [
                {'pattern': r'^\d{2}-.*'}
            ]
        }
        engine = SearchEngine(definition, rules)
        matches = engine.search_stages(rules['stages'])
        matched_names = [m.name for m in matches]
        self.assertEqual(matched_names, ['01-Culiacan', '02-Leon', '03-Laguna'])

    def test_fixed_names_and_pattern_combined(self):
        definition = self._build_definition([
            'SCM Inspection', 'Develop', 'QA', 'Production',
            '01-Culiacan', '02-Leon'
        ])
        rules = {
            'stages': [
                {'name': 'Develop'},
                {'name': 'QA'},
                {'pattern': r'^\d{2}-.*'}
            ]
        }
        engine = SearchEngine(definition, rules)
        matches = engine.search_stages(rules['stages'])
        matched_names = sorted(m.name for m in matches)
        self.assertEqual(matched_names, ['01-Culiacan', '02-Leon', 'Develop', 'QA'])

    def test_string_name_still_works(self):
        definition = self._build_definition(['Develop', 'QA'])
        rules = {'stages': ['Develop']}
        engine = SearchEngine(definition, rules)
        matches = engine.search_stages(rules['stages'])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].name, 'Develop')

    def test_pattern_no_match(self):
        definition = self._build_definition(['Develop', 'QA'])
        rules = {'stages': [{'pattern': r'^\d{2}-.*'}]}
        engine = SearchEngine(definition, rules)
        matches = engine.search_stages(rules['stages'])
        self.assertEqual(matches, [])

    def test_search_tasks_in_workflowTasks(self):
        """Las tasks deben encontrarse en workflowTasks (formato actual de Azure DevOps)."""
        definition = {
            'environments': [
                {
                    'name': 'Develop',
                    'deployPhases': [
                        {
                            'workflowTasks': [
                                {'name': 'DataDog', 'inputs': {'script': 'old'}},
                                {'name': 'SFTP Upload', 'inputs': {'Contents': 'old'}},
                            ]
                        }
                    ]
                }
            ]
        }
        rules = {'tasks': [{'name': 'DataDog'}]}
        engine = SearchEngine(definition, rules)
        matches = engine.search_tasks(rules['tasks'])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].name, 'DataDog')

    def test_search_tasks_in_deploymentInput(self):
        """Las tasks deben encontrarse en deploymentInput.tasks (formato antiguo)."""
        definition = {
            'environments': [
                {
                    'name': 'QA',
                    'deployPhases': [
                        {
                            'deploymentInput': {
                                'tasks': [
                                    {'displayName': 'DataDog', 'inputs': {'script': 'old'}},
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        rules = {'tasks': [{'name': 'DataDog'}]}
        engine = SearchEngine(definition, rules)
        matches = engine.search_tasks(rules['tasks'])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].name, 'DataDog')


if __name__ == '__main__':
    unittest.main()
