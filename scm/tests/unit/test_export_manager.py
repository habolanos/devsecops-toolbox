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
