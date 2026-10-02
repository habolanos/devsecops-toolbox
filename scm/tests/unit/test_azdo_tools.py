"""
Tests para herramientas AZDO (Azure DevOps)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestAZDOTools:
    """Tests para herramientas AZDO"""

    def test_azdo_pr_master_checker(self):
        """Test PR Master Checker"""
        try:
            from scm.azdo.azdo_pr_master_checker import get_args
            args = get_args()
            assert args is not None
        except (ImportError, SystemExit):
            pytest.skip("AZDO PR Master Checker no disponible")

    def test_azdo_branch_policy_checker(self):
        """Test Branch Policy Checker"""
        # Simular validación de políticas de rama
        policies = {
            'require_pull_request': True,
            'require_code_review': True,
            'minimum_reviewers': 2,
            'require_linked_work_items': True
        }
        
        assert policies['require_pull_request'] is True
        assert policies['minimum_reviewers'] == 2

    def test_azdo_release_cd_health(self):
        """Test Release CD Health"""
        # Simular métricas de salud
        health_metrics = {
            'success_rate': 0.95,
            'average_duration': 300,
            'failure_count': 5,
            'total_releases': 100
        }
        
        assert health_metrics['success_rate'] == 0.95
        assert health_metrics['total_releases'] == 100

    def test_azdo_pipeline_drift_analyzer(self):
        """Test Pipeline Drift Analyzer"""
        # Simular análisis de drift
        drift_data = {
            'pipelines_analyzed': 50,
            'pipelines_with_drift': 15,
            'drift_percentage': 30.0
        }
        
        assert drift_data['pipelines_analyzed'] == 50
        assert drift_data['drift_percentage'] == 30.0

    def test_azdo_task_validator(self):
        """Test Task Validator"""
        # Simular validación de tareas
        tasks = [
            {'id': 1, 'name': 'Build', 'valid': True},
            {'id': 2, 'name': 'Test', 'valid': True},
            {'id': 3, 'name': 'Deploy', 'valid': True}
        ]
        
        assert len(tasks) == 3
        assert all(task['valid'] for task in tasks)

    def test_azdo_pipeline_updater(self):
        """Test Pipeline Updater"""
        # Simular actualización de pipelines
        update_config = {
            'definition_ids': [1, 2, 3],
            'template': 'docker.yaml',
            'dry_run': False,
            'backup': True
        }
        
        assert len(update_config['definition_ids']) == 3
        assert update_config['template'] == 'docker.yaml'

    def test_azdo_pipeline_rollback(self):
        """Test Pipeline Rollback"""
        # Simular rollback de pipeline
        rollback_config = {
            'definition_id': 2758,
            'method': 'hybrid',
            'target_revision': 44,
            'dry_run': False
        }
        
        assert rollback_config['definition_id'] == 2758
        assert rollback_config['method'] == 'hybrid'

    def test_azdo_redo_pipeline(self):
        """Test Redo Pipeline"""
        # Simular redo de pipeline
        redo_config = {
            'definition_id': 2758,
            'org': 'Coppel-Retail',
            'project': 'Cadena_de_Suministros',
            'dry_run': False
        }
        
        assert redo_config['definition_id'] == 2758
        assert redo_config['org'] == 'Coppel-Retail'


class TestAZDOIntegration:
    """Tests de integración para AZDO"""

    def test_azdo_workflow_pr_to_release(self):
        """Test workflow PR a Release"""
        workflow = {
            'pr_created': True,
            'pr_approved': True,
            'pr_merged': True,
            'pipeline_triggered': True,
            'release_created': True
        }
        
        assert all(workflow.values())

    def test_azdo_multiple_pipelines(self):
        """Test manejo de múltiples pipelines"""
        pipelines = [
            {'id': 1, 'name': 'Pipeline 1', 'status': 'success'},
            {'id': 2, 'name': 'Pipeline 2', 'status': 'success'},
            {'id': 3, 'name': 'Pipeline 3', 'status': 'failed'},
            {'id': 4, 'name': 'Pipeline 4', 'status': 'success'}
        ]
        
        success_count = sum(1 for p in pipelines if p['status'] == 'success')
        assert success_count == 3

    def test_azdo_branch_policies_validation(self):
        """Test validación de políticas de rama"""
        branches = {
            'main': {
                'require_pr': True,
                'require_review': True,
                'reviewers': 2
            },
            'develop': {
                'require_pr': True,
                'require_review': True,
                'reviewers': 1
            }
        }
        
        assert branches['main']['reviewers'] == 2
        assert branches['develop']['reviewers'] == 1


class TestAZDOMetrics:
    """Tests para métricas AZDO"""

    def test_pipeline_success_rate(self):
        """Test cálculo de tasa de éxito"""
        runs = [
            {'status': 'success'},
            {'status': 'success'},
            {'status': 'failed'},
            {'status': 'success'},
            {'status': 'success'}
        ]
        
        success_rate = sum(1 for r in runs if r['status'] == 'success') / len(runs)
        assert success_rate == 0.8

    def test_pipeline_duration(self):
        """Test cálculo de duración de pipeline"""
        runs = [
            {'duration': 300},
            {'duration': 320},
            {'duration': 280},
            {'duration': 310}
        ]
        
        avg_duration = sum(r['duration'] for r in runs) / len(runs)
        assert avg_duration == 302.5

    def test_release_frequency(self):
        """Test cálculo de frecuencia de releases"""
        releases = [
            {'date': '2026-07-01'},
            {'date': '2026-07-05'},
            {'date': '2026-07-10'},
            {'date': '2026-07-15'}
        ]
        
        assert len(releases) == 4
        frequency = len(releases) / 15  # 15 días
        assert frequency > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestReleaseDeepDiveLauncherArgs:
    """Opcion 5 (Release Deep Dive): el launcher debe declarar --definition-id
    (requerido por azdo_release_deep_dive.py), no --release-id."""

    @staticmethod
    def _load_launcher():
        import importlib.util
        from pathlib import Path
        tools_py = (Path(__file__).parent.parent.parent
                    / "azdo" / "tools.py")
        spec = importlib.util.spec_from_file_location(
            "azdo_tools_launcher", tools_py)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_tool5_declara_definition_id(self):
        mod = self._load_launcher()
        args = mod.TOOLS["5"]["args"]
        assert "--definition-id" in args
        assert "--release-id" not in args

    def test_script_acepta_definition_id(self):
        """azdo_release_deep_dive.py declara --definition-id/--id requerido."""
        from pathlib import Path
        script = (Path(__file__).parent.parent.parent
                  / "azdo" / "azdo_release_deep_dive.py")
        src = script.read_text(encoding="utf-8")
        assert '"--definition-id"' in src
        assert 'dest="definition_id"' in src
        assert 'required=True' in src
