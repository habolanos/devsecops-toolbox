"""
Tests unitarios para soporte de pattern regex y old_value opcional en release updater.
"""

import unittest
from scm.azdo.pipeline_cd_update_release.pipeline_cd_update_release import build_patch_payload


def _make_release():
    return {
        'environments': [
            {
                'name': 'Develop',
                'deployPhases': [
                    {'workflowTasks': [
                        {'displayName': 'Ejecutar Deployment Script', 'inputs': {'script': 'old script'}}
                    ]}
                ]
            },
            {
                'name': '01-Culiacan',
                'deployPhases': [
                    {'workflowTasks': [
                        {'displayName': 'Ejecutar Deployment Script', 'inputs': {'script': 'old script'}}
                    ]}
                ]
            },
            {
                'name': 'Other',
                'deployPhases': [
                    {'workflowTasks': [
                        {'displayName': 'Ejecutar Deployment Script', 'inputs': {'script': 'old script'}}
                    ]}
                ]
            }
        ]
    }


class TestReleasePatternAndOverwrite(unittest.TestCase):

    def test_pattern_stages_matched(self):
        release = _make_release()
        task_updates = [
            {'name': 'Ejecutar Deployment Script',
             'fields': [{'path': 'inputs.script', 'new_value': 'new script'}]}
        ]
        payload, changes = build_patch_payload(
            release, [], [], False, '',
            task_updates=task_updates,
            search_stages=['Develop'],
            search_stage_patterns=[r'^\d{2}-.*']
        )
        envs = {e['name']: e for e in payload['environments']}
        develop_script = envs['Develop']['deployPhases'][0]['workflowTasks'][0]['inputs']['script']
        culiacan_script = envs['01-Culiacan']['deployPhases'][0]['workflowTasks'][0]['inputs']['script']
        other_script = envs['Other']['deployPhases'][0]['workflowTasks'][0]['inputs']['script']
        self.assertEqual(develop_script, 'new script')
        self.assertEqual(culiacan_script, 'new script')
        self.assertEqual(other_script, 'old script')

    def test_old_value_star_overwrites_full_field(self):
        release = _make_release()
        task_updates = [
            {'name': 'Ejecutar Deployment Script',
             'fields': [{'path': 'inputs.script', 'old_value': '*', 'new_value': 'full overwrite'}]}
        ]
        payload, changes = build_patch_payload(
            release, [], [], False, '',
            task_updates=task_updates,
            search_stages=['*']
        )
        for env in payload['environments']:
            script = env['deployPhases'][0]['workflowTasks'][0]['inputs']['script']
            self.assertEqual(script, 'full overwrite')

    def test_old_value_omitted_overwrites_full_field(self):
        release = _make_release()
        task_updates = [
            {'name': 'Ejecutar Deployment Script',
             'fields': [{'path': 'inputs.script', 'new_value': 'no old value'}]}
        ]
        payload, changes = build_patch_payload(
            release, [], [], False, '',
            task_updates=task_updates,
            search_stages=['*']
        )
        for env in payload['environments']:
            script = env['deployPhases'][0]['workflowTasks'][0]['inputs']['script']
            self.assertEqual(script, 'no old value')

    def test_old_value_partial_replace_still_works(self):
        release = _make_release()
        task_updates = [
            {'name': 'Ejecutar Deployment Script',
             'fields': [{'path': 'inputs.script', 'old_value': 'old', 'new_value': 'new'}]}
        ]
        payload, changes = build_patch_payload(
            release, [], [], False, '',
            task_updates=task_updates,
            search_stages=['*']
        )
        for env in payload['environments']:
            script = env['deployPhases'][0]['workflowTasks'][0]['inputs']['script']
            self.assertEqual(script, 'new script')


if __name__ == '__main__':
    unittest.main()
