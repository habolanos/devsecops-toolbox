"""
Tests para gke_deployments_report.py — aislamiento por cluster:

- gke_kube_env clavea el KUBECONFIG por (proyecto, cluster): dos proyectos con
  cluster homónimo no comparten archivo ni se pisan en paralelo.
- Un cluster inalcanzable/fallido NO aborta el reporte multi-proyecto:
  main() colecciona el error por cluster, continua con los demas y lo
  reporta en consola/TXT (fallo distinguible de "cluster vacio").
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SCM_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCM_DIR))

import utils  # noqa: E402

REPORT_PATH = SCM_DIR / "gcp" / "monitoring" / "gke_deployments_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "gke_deployments_report_test", str(REPORT_PATH))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


try:
    report_mod = _load_module()
except Exception:
    report_mod = None

pytestmark = pytest.mark.skipif(
    report_mod is None,
    reason="gke_deployments_report requiere kubernetes/tabulate/rich")


def _fake_row(project="p2", cluster="c2"):
    return {
        "project": project, "cluster": cluster, "namespace": "ns",
        "deployment": "dep", "pods": "1/1", "pod_count": 1,
        "status": "Running", "restarts": 0, "age": "1d",
        "cpu": "N/A", "memory": "N/A",
        "request_cpu": "N/A", "request_memory": "N/A",
        "limit_cpu": "N/A", "limit_memory": "N/A",
    }


class TestKubeEnvIsolation:
    def test_scoped_by_project_and_cluster(self):
        """Mismo cluster en distintos proyectos → kubeconfigs distintos."""
        kc_p1 = utils.gke_kube_env("clus", "p1")["KUBECONFIG"]
        kc_p2 = utils.gke_kube_env("clus", "p2")["KUBECONFIG"]
        assert kc_p1 != kc_p2
        assert "p1-clus" in kc_p1
        assert "p2-clus" in kc_p2

    def test_stable_and_backwards_compatible(self):
        """La misma (proyecto, cluster) da el mismo path; sin proyecto usa
        solo el nombre del cluster (compat con callers antiguos)."""
        assert (utils.gke_kube_env("c", "p")["KUBECONFIG"]
                == utils.gke_kube_env("c", "p")["KUBECONFIG"])
        assert "c.yaml" in utils.gke_kube_env("c")["KUBECONFIG"]


class TestPerClusterFailure:
    def test_credentials_failure_raises(self, monkeypatch):
        """Sin get-credentials → RuntimeError (main lo colecciona como error)."""
        monkeypatch.setattr(report_mod, "ensure_gke_cluster_credentials",
                            lambda *a, **k: False)
        with pytest.raises(RuntimeError):
            report_mod.get_deployments_report("p1", "c1", "us-central1-a")

    def test_one_bad_cluster_does_not_abort(self, monkeypatch, tmp_path, capsys):
        """Regresion: un cluster con timeout mataba todo el reporte (exit 1).
        Ahora se registra como 'cluster no accesible' y el resto continua."""
        monkeypatch.setattr(
            report_mod, "list_gke_clusters",
            lambda pid, logger=None: [(f"clus-{pid}", "us-central1-a")])
        monkeypatch.setattr(
            report_mod, "get_output_dir", lambda *a, **k: tmp_path)

        def _fake_report(pid, cname, cloc, logger=None):
            if pid == "p-bad":
                raise RuntimeError("Connection timed out")
            return [_fake_row(project=pid, cluster=cname)]

        monkeypatch.setattr(report_mod, "get_deployments_report", _fake_report)
        monkeypatch.setattr(sys, "argv",
                            ["gke_deployments_report.py",
                             "--multi-project", "p-bad,p-ok"])

        rc = report_mod.main()

        out = capsys.readouterr().out
        assert rc == 0, "un cluster fallido no debe abortar el reporte"
        assert "no accesibles" in out
        assert "clus-p-bad" in out
        # Los archivos se generan igualmente con los datos del cluster sano
        txts = list(tmp_path.glob("gke_deployments_report_*.txt"))
        assert txts, "debe generarse el TXT aunque un cluster falle"
        assert "CLUSTERS NO ACCESIBLES" in txts[0].read_text(encoding="utf-8")
        # ... y el HTML tambien se genera
        htmls = list(tmp_path.glob("gke_deployments_report_*.html"))
        assert htmls, "debe generarse el HTML del reporte"
        assert "errorsSection" in htmls[0].read_text(encoding="utf-8")

    def test_format_cluster_errors_empty(self):
        assert report_mod.format_cluster_errors([]) == ""

    def test_format_cluster_errors_table(self):
        tbl = report_mod.format_cluster_errors([
            {"project": "p", "cluster": "c", "location": "us", "error": "boom"}])
        assert "boom" in tbl and "| p" in tbl


class TestRestartHighlight:
    """Restarts: >10 blanco/rojo, >4 negro/amarillo, resto sin estilo."""

    def test_levels(self):
        assert report_mod.restart_level(11) == "high"
        assert report_mod.restart_level(10) == "warn"   # 10 no es >10
        assert report_mod.restart_level(5) == "warn"
        assert report_mod.restart_level(4) == "ok"
        assert report_mod.restart_level("N/A") == "ok"

    def test_markup(self):
        assert report_mod.restart_markup(15) == "[white on red] 15 [/]"
        assert report_mod.restart_markup(7) == "[black on yellow] 7 [/]"
        assert report_mod.restart_markup(2) == "2"

    def test_rich_table_marks_restarts(self):
        row = _fake_row()
        row["restarts"] = 20
        table = report_mod.build_detailed_rich_table([row])
        cells = list(table.columns[6]._cells)  # columna 'Restarts'
        assert any("white on red" in str(c) for c in cells)


class TestHtmlReport:
    def test_build_html_contains_payload_and_classes(self):
        row = _fake_row()
        row["restarts"] = 15
        errors = [{"project": "pb", "cluster": "cb",
                   "location": "us", "error": "timeout"}]
        html = report_mod.build_html_report(
            [row], errors, "2026-10-04T00:00:00Z", ["p2", "pb"])
        assert "<!DOCTYPE html>" in html
        assert "restarts-high" in html          # clase CSS del resaltado
        assert "restarts-warn" in html
        assert "var REPORT =" in html           # datos embebidos
        assert "errorsSection" in html          # seccion clusters no accesibles
        assert '"timeout"' in html or "timeout" in html

    def test_write_html_creates_file(self, tmp_path):
        target = tmp_path / "report.html"
        report_mod.write_html([_fake_row()], [], str(target), "t", ["p2"])
        assert target.exists() and target.stat().st_size > 1000
