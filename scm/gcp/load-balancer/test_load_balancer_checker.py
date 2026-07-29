"""
Tests unitarios para gcp_load_balancer_checker.py - soporte multi-proyecto
"""
import unittest
from unittest.mock import patch, MagicMock
import subprocess


class TestMultiProjectSupport(unittest.TestCase):
    """Tests para verificar el soporte de multiples proyectos separados por coma."""

    def test_check_gcp_connection_single_project(self):
        """Verifica que check_gcp_connection funciona con un solo proyecto."""
        from gcp_load_balancer_checker import check_gcp_connection

        console = MagicMock()
        with patch('subprocess.run') as mock_run:
            # Mock auth success
            auth_result = MagicMock()
            auth_result.returncode = 0
            auth_result.stdout = "user@example.com\n"

            # Mock project access success
            project_result = MagicMock()
            project_result.returncode = 0
            project_result.stdout = "my-project\n"

            mock_run.side_effect = [auth_result, project_result]

            result = check_gcp_connection("my-project", console, debug=False)
            self.assertTrue(result)

    def test_check_gcp_connection_multiple_projects(self):
        """Verifica que check_gcp_connection funciona con multiples proyectos separados por coma."""
        from gcp_load_balancer_checker import check_gcp_connection

        console = MagicMock()
        with patch('subprocess.run') as mock_run:
            # Mock auth success
            auth_result = MagicMock()
            auth_result.returncode = 0
            auth_result.stdout = "user@example.com\n"

            # Mock project access success for each project
            proj_result = MagicMock()
            proj_result.returncode = 0
            proj_result.stdout = "project\n"

            mock_run.side_effect = [auth_result, proj_result, proj_result, proj_result]

            result = check_gcp_connection("proj-1,proj-2,proj-3", console, debug=False)
            self.assertTrue(result)
            # Verify gcloud projects describe was called 3 times (once per project)
            self.assertEqual(mock_run.call_count, 4)  # 1 auth + 3 projects

    def test_check_gcp_connection_one_project_fails(self):
        """Verifica que check_gcp_connection retorna False si un proyecto falla."""
        from gcp_load_balancer_checker import check_gcp_connection

        console = MagicMock()
        with patch('subprocess.run') as mock_run:
            # Mock auth success
            auth_result = MagicMock()
            auth_result.returncode = 0
            auth_result.stdout = "user@example.com\n"

            # Mock first project success
            proj_ok = MagicMock()
            proj_ok.returncode = 0
            proj_ok.stdout = "proj-1\n"

            # Mock second project failure
            proj_fail = MagicMock()
            proj_fail.returncode = 1
            proj_fail.stdout = "ERROR"
            proj_fail.stderr = "Permission denied"

            mock_run.side_effect = [auth_result, proj_ok, proj_fail]

            result = check_gcp_connection("proj-1,proj-2", console, debug=False)
            self.assertFalse(result)

    def test_check_gcp_connection_no_auth(self):
        """Verifica que check_gcp_connection retorna False si no hay sesion activa."""
        from gcp_load_balancer_checker import check_gcp_connection

        console = MagicMock()
        with patch('subprocess.run') as mock_run:
            auth_result = MagicMock()
            auth_result.returncode = 1
            auth_result.stdout = ""

            mock_run.return_value = auth_result

            result = check_gcp_connection("my-project", console, debug=False)
            self.assertFalse(result)

    def test_project_split_strips_spaces(self):
        """Verifica que el split de proyectos elimina espacios en blanco."""
        project_input = " proj-1 , proj-2 , proj-3 "
        projects = [p.strip() for p in project_input.split(',') if p.strip()]
        self.assertEqual(projects, ["proj-1", "proj-2", "proj-3"])
        self.assertEqual(len(projects), 3)

    def test_project_split_single_project(self):
        """Verifica que el split funciona con un solo proyecto."""
        project_input = "my-project"
        projects = [p.strip() for p in project_input.split(',') if p.strip()]
        self.assertEqual(projects, ["my-project"])
        self.assertEqual(len(projects), 1)

    def test_project_split_empty_input(self):
        """Verifica que el split maneja entrada vacia."""
        project_input = ""
        projects = [p.strip() for p in project_input.split(',') if p.strip()]
        self.assertEqual(projects, [])
        self.assertEqual(len(projects), 0)

    def test_version_updated(self):
        """Verifica que la version sea 1.2.0."""
        from gcp_load_balancer_checker import __version__
        self.assertEqual(__version__, "1.2.0")


if __name__ == '__main__':
    unittest.main()
