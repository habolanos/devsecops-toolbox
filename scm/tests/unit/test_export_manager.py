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


class TestExportExcelStreaming:
    """Datasets grandes → openpyxl write-only (memoria constante)."""

    def test_streaming_genera_xlsx_valido(self, manager, monkeypatch, tmp_path):
        monkeypatch.setattr("scm.export_manager._XLSX_STREAM_CELLS", 4)
        pytest.importorskip("openpyxl")
        pytest.importorskip("pandas")
        path = manager.export_excel([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])
        assert path and Path(path).exists()
        from openpyxl import load_workbook
        ws = load_workbook(path, read_only=True)["Data"]
        rows = list(ws.iter_rows(values_only=True))
        assert rows[0] == ("a", "b")
        assert rows[1] == (1, "x") and rows[2] == (2, "y")

    def test_streaming_nan_celda_vacia(self, manager, monkeypatch):
        monkeypatch.setattr("scm.export_manager._XLSX_STREAM_CELLS", 1)
        pytest.importorskip("openpyxl")
        pytest.importorskip("pandas")
        path = manager.export_excel([{"a": 1}, {"a": 1, "extra": None}])
        from openpyxl import load_workbook
        ws = load_workbook(path, read_only=True)["Data"]
        rows = list(ws.iter_rows(values_only=True))
        assert rows[0] == ("a", "extra")
        # NaN (columna faltante en fila 1) → celda vacía
        assert rows[1][1] in (None, "")

    def test_streaming_hojas_meta_y_summary(self, manager, monkeypatch):
        monkeypatch.setattr("scm.export_manager._XLSX_STREAM_CELLS", 1)
        pytest.importorskip("openpyxl")
        pytest.importorskip("pandas")
        path = manager.export_excel(
            [{"a": 1}], metadata={"org": "x"}, summary={"total": 1})
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True)
        assert set(wb.sheetnames) == {"Data", "Metadata", "Summary"}

    def test_umbral_no_dispara_streaming(self, manager, monkeypatch):
        # umbral alto → camino normal con auto-width (sin write-only)
        monkeypatch.setattr("scm.export_manager._XLSX_STREAM_CELLS", 10**9)
        pytest.importorskip("openpyxl")
        pytest.importorskip("pandas")
        path = manager.export_excel([{"a": 1}])
        assert path and Path(path).exists()
