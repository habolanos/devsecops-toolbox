"""
Tests para Release Explorer Diff (azdo_release_explorer_rich.py)
Verifica que la comparación de releases maneja valores None,
tasks con inputs nulos y caracteres especiales de Rich markup.
"""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "azdo"))

try:
    import azdo_release_explorer_rich as explorer
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


pytestmark = pytest.mark.skipif(not RICH_AVAILABLE, reason="rich o modulo explorer no disponible")


def _console():
    buf = io.StringIO()
    return buf, Console(file=buf, width=140)


class TestSafeStr:
    def test_none_returns_default(self):
        assert explorer.safe_str(None) == "N/A"
        assert explorer.safe_str(None, "?") == "?"

    def test_dict_serializes_json(self):
        result = explorer.safe_str({"b": 2, "a": 1})
        assert result == '{"a": 1, "b": 2}'

    def test_list_serializes_json(self):
        assert explorer.safe_str([1, "x"]) == '[1, "x"]'

    def test_scalar_to_str(self):
        assert explorer.safe_str(True) == "True"
        assert explorer.safe_str(42) == "42"
        assert explorer.safe_str("texto") == "texto"


class TestCell:
    def test_equal_values_green(self):
        a, b = explorer.cell("x", "x")
        assert "[green]" in a and "[green]" in b

    def test_diff_values_red(self):
        a, b = explorer.cell("x", "y")
        assert "[red]" in a and "[red]" in b

    def test_none_values_no_crash(self):
        a, b = explorer.cell(None, "y")
        assert a == "[red]N/A[/red]"
        assert b == "[red]y[/red]"

    def test_markup_escaped(self):
        a, _ = explorer.cell("va[red]lue", "otro")
        assert "va\\[red]lue" in a
        # corchetes que no forman tag se dejan literal
        a, _ = explorer.cell("va[0]lue", "otro")
        assert "va[0]lue" in a


class TestPrintDiff:
    """print_diff no debe fallar con campos None en ninguna sección."""

    def _releases_con_none(self):
        release_a = {
            "id": 41727, "name": "Release-45", "status": "active",
            "createdBy": {"displayName": "User A"}, "createdOn": "2026-01-23",
            "modifiedOn": None, "description": None,
            "artifacts": [
                {"alias": "_repo", "definitionReference": {"version": {"id": "abc", "name": "v1"}}},
                {"alias": None, "definitionReference": None},
            ],
            "environments": [
                {"name": "Dev", "status": "succeeded",
                 "preDeployApprovals": [{"status": "approved"}, {"status": None}],
                 "postDeployApprovals": [],
                 # release A usa la clave de la definición del pipeline
                 "deployPhases": [
                     {"name": "Deploy", "phaseType": "agent",
                      "workflowTasks": [
                          {"name": "Azure CLI", "task": {"id": "t1"}, "version": "2.*",
                           "enabled": True,
                           "inputs": {"script": "echo hi", "nested": {"a": 1}, "nullable": None}},
                          {"name": "Task[brackets]", "task": None, "version": None,
                           "enabled": None, "inputs": None},
                      ]},
                 ]},
                {"name": "QA", "status": None,
                 "preDeployApprovals": None, "postDeployApprovals": None,
                 "deployPhases": None},
            ],
            "variables": {"v1": {"value": "x"}, "v2": {"value": None}},
        }
        release_b = {
            "id": 59806, "name": "Release-61", "status": "active",
            "createdBy": None, "createdOn": "2026-09-19",
            "modifiedOn": "2026-09-21", "description": "desc",
            "artifacts": [
                {"alias": "_repo", "definitionReference": {"version": {"id": "abc", "name": "v1"}}},
            ],
            "environments": [
                {"name": "Dev", "status": "succeeded",
                 "preDeployApprovals": [{"status": "approved"}],
                 "postDeployApprovals": [{"status": "approved"}],
                 # release B usa la clave real de la API de releases
                 "deployPhasesSnapshot": [
                     {"name": "Deploy", "phaseType": "agent",
                      "workflowTasks": [
                          {"name": "Azure CLI", "task": {"id": "t1"}, "version": "2.*",
                           "enabled": False,
                           "inputs": {"script": "echo bye", "extra": "new[0]"}},
                          {"name": "NewTask", "task": {"id": "t3"}, "version": "1.*",
                           "enabled": True, "inputs": {"k": "v"}},
                      ]},
                 ]},
                {"name": "Stg", "status": "notStarted",
                 "preDeployApprovals": [], "postDeployApprovals": [],
                 "deployPhases": []},
            ],
            "variables": {"v1": {"value": "y"}, "v3": "plain"},
        }
        return release_a, release_b

    def test_print_diff_con_none_no_falla(self):
        release_a, release_b = self._releases_con_none()
        buf, console = _console()
        original = explorer.console
        explorer.console = console
        try:
            explorer.print_diff(release_a, release_b)
        finally:
            explorer.console = original
        out = buf.getvalue()
        assert "DIFF" in out
        assert "Stages" in out
        assert "Tasks - Stage: Dev" in out

    def test_print_diff_tasks_muestran_inputs(self):
        release_a, release_b = self._releases_con_none()
        buf, console = _console()
        original = explorer.console
        explorer.console = console
        try:
            explorer.print_diff(release_a, release_b)
        finally:
            explorer.console = original
        out = buf.getvalue()
        # inputs comparados
        assert "script=echo" in out
        assert "no definido" in out
        # valor con corchetes renderizado literal
        assert "new[0]" in out
        # input None -> N/A
        assert "nullable=N/A" in out

    def test_print_diff_releases_vacios(self):
        buf, console = _console()
        original = explorer.console
        explorer.console = console
        try:
            explorer.print_diff({"id": 1}, {"id": 2})
        finally:
            explorer.console = original
        assert "DIFF" in buf.getvalue()

    def test_print_diff_sin_tasks_muestra_aviso(self):
        release_a = {"id": 1, "environments": [{"name": "Dev", "status": "ok"}]}
        release_b = {"id": 2, "environments": [{"name": "Dev", "status": "ok"}]}
        buf, console = _console()
        original = explorer.console
        explorer.console = console
        try:
            explorer.print_diff(release_a, release_b)
        finally:
            explorer.console = original
        out = buf.getvalue()
        assert "No se encontraron tasks" in out

    def test_print_diff_muestra_resumen(self):
        release_a, release_b = self._releases_con_none()
        buf, console = _console()
        original = explorer.console
        explorer.console = console
        try:
            explorer.print_diff(release_a, release_b)
        finally:
            explorer.console = original
        out = buf.getvalue()
        assert "Resumen de Cambios" in out
        assert "TOTAL" in out
        assert "Diferentes" in out

    def test_print_diff_exporta_txt_y_html(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        release_a, release_b = self._releases_con_none()
        buf, console = _console()
        original = explorer.console
        explorer.console = console
        try:
            explorer.print_diff(release_a, release_b)
        finally:
            explorer.console = original
        out_dir = tmp_path / "outcome"
        txts = list(out_dir.glob("release_diff_41727_vs_59806_*.txt"))
        htmls = list(out_dir.glob("release_diff_41727_vs_59806_*.html"))
        assert txts, "no se generó el TXT"
        assert htmls, "no se generó el HTML"
        txt = txts[0].read_text(encoding="utf-8")
        html = htmls[0].read_text(encoding="utf-8")
        assert "Resumen de Cambios" in txt
        assert "<" in html and "Resumen" in html
