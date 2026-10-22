"""Tests para azdo_default_export (salida JSON+HTML por defecto)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "azdo"))

from azdo_default_export import write_default_reports, _resolve_outdir


@pytest.fixture
def outdir(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
    return tmp_path


class TestWriteDefaultReports:
    def test_generates_json_and_html(self, outdir):
        out = write_default_reports(
            "my_tool", "1.0.0", [{"id": 1, "name": "x"}],
            summary={"warns": 0}, organization="org", project="proj",
            title="Mi Reporte", quiet=True)
        assert Path(out["json"]).exists()
        assert Path(out["html"]).exists()
        assert out["json"].startswith(str(outdir))

    def test_json_payload(self, outdir):
        out = write_default_reports(
            "t", "2.0", [{"a": 1}], metadata={"k": "v"}, quiet=True)
        payload = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
        assert payload["metadata"]["tool"] == "t"
        assert payload["metadata"]["k"] == "v"
        assert payload["summary"]["total"] == 1
        assert payload["data"] == [{"a": 1}]

    def test_html_escapes_and_has_filter(self, outdir):
        out = write_default_reports(
            "t", "1", [{"v": "<b>x</b>"}], quiet=True)
        content = Path(out["html"]).read_text(encoding="utf-8")
        assert "&lt;b&gt;" in content
        assert "function filtrar" in content

    def test_non_serializable_values(self, outdir):
        from datetime import datetime
        out = write_default_reports(
            "t", "1", [{"when": datetime(2024, 1, 1), "s": {1, 2}}],
            quiet=True)
        payload = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
        assert payload["data"][0]["when"].startswith("2024-01-01")

    def test_empty_rows(self, outdir):
        out = write_default_reports("t", "1", [], quiet=True)
        assert Path(out["json"]).exists()
        payload = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
        assert payload["summary"]["total"] == 0

    def test_excel_when_requested(self, outdir):
        pytest.importorskip("pandas")
        pytest.importorskip("openpyxl")
        out = write_default_reports(
            "t", "1", [{"id": 1, "name": "x"}], excel=True, quiet=True)
        assert out["excel"].endswith(".xlsx")
        assert Path(out["excel"]).exists()

    def test_excel_not_generated_by_default(self, outdir):
        out = write_default_reports("t", "1", [{"id": 1}], quiet=True)
        assert "excel" not in out

    def test_dict_payload(self, outdir):
        """Un reporte dict se guarda tal cual y el HTML usa key/value."""
        out = write_default_reports(
            "t", "1", {"install": {"id": 1}, "rollback": {"id": 2}},
            quiet=True)
        payload = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
        assert payload["data"]["install"]["id"] == 1
        content = Path(out["html"]).read_text(encoding="utf-8")
        assert "<th>key</th>" in content


class TestResolveOutdir:
    def test_env_var_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        assert _resolve_outdir() == tmp_path

    def test_creates_dir(self, tmp_path, monkeypatch):
        target = tmp_path / "nuevo" / "outcome"
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(target))
        assert _resolve_outdir() == target
        assert target.exists()
