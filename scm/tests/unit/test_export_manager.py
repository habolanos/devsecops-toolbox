"""Tests para ExportManager (exportación centralizada)."""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scm.export_manager import ExportManager


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
    return ExportManager("test_tool", "1.0.0")


class TestExportCsvHeterogeneousRows:
    """Regresión: rows con keys distintas no deben perder columnas."""

    def test_csv_unions_keys_from_all_rows(self, manager):
        rows = [
            {"id": 1, "tasksPerStage_Dev": 2},
            {"id": 2, "tasksPerStage_Dev": 3, "tasksPerStage_QA": 1},
        ]
        path = manager.export_csv(rows)
        with open(path, newline="", encoding="utf-8") as f:
            read = list(csv.DictReader(f))
        assert "tasksPerStage_QA" in read[0]          # header incluye la key
        assert read[1]["tasksPerStage_QA"] == "1"
        assert read[0]["tasksPerStage_QA"] == ""      # fila sin la key → vacío

    def test_csv_explicit_fieldnames_respected(self, manager):
        path = manager.export_csv([{"a": 1, "b": 2}], fieldnames=["b", "a"])
        header = Path(path).read_text(encoding="utf-8").splitlines()[0]
        assert header == "b,a"

    def test_csv_empty_data(self, manager):
        assert manager.export_csv([]) is None


class TestExportHtml:
    """HTML genérico auto-contenido."""

    def test_html_generates_table_with_all_columns(self, manager):
        rows = [
            {"id": 1, "name": "a"},
            {"id": 2, "name": "b", "extra": "x"},
        ]
        path = manager.export_html(rows, summary={"criticos": 1})
        content = Path(path).read_text(encoding="utf-8")
        assert path.endswith(".html")
        assert "<th>id</th>" in content and "<th>extra</th>" in content
        assert "<td>a</td>" in content and "criticos" in content

    def test_html_escapes_values(self, manager):
        path = manager.export_html([{"v": "<script>alert(1)</script>"}])
        content = Path(path).read_text(encoding="utf-8")
        assert "<script>alert(1)</script>" not in content
        assert "&lt;script&gt;" in content

    def test_html_empty_data(self, manager):
        path = manager.export_html([])
        content = Path(path).read_text(encoding="utf-8")
        assert "total" in content


class TestExportDefault:
    """export_default genera siempre JSON + HTML."""

    def test_generates_both_files(self, manager):
        out = manager.export_default([{"id": 1}], summary={"k": "v"})
        assert out["json"].endswith(".json")
        assert out["html"].endswith(".html")
        assert Path(out["json"]).exists() and Path(out["html"]).exists()

    def test_json_payload_structure(self, manager):
        import json
        out = manager.export_default(
            [{"id": 1}], metadata={"m": 1}, summary={"s": 2},
            organization="org", project="proj")
        payload = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
        assert payload["metadata"]["tool"] == "test_tool"
        assert payload["metadata"]["organization"] == "org"
        assert payload["metadata"]["m"] == 1
        assert payload["summary"]["s"] == 2
        assert payload["summary"]["total"] == 1
        assert payload["data"] == [{"id": 1}]
