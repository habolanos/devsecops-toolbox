"""
Tests para gke_monitor_node.py (opcion 24) — multi-proyecto + HTML:

- La tool declara --multi-project y el stem esta en MULTI_PROJECT_PARAM_SCRIPTS
  (misma seleccion por equipo/ALL que la opcion 1/2, ejecucion consolidada).
- El prompt de export usa las opciones del tool (console/html/ninguno, default
  html) en vez del generico json/csv que el script no acepta.
- Un cluster sin credenciales/inaccesible lanza RuntimeError que main()
  colecciona sin abortar el resto.
- generate_html produce el dashboard autocontenido con columnas
  Project/Cluster y la seccion de clusters no accesibles.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

SCM_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCM_DIR))

GCP_DIR = SCM_DIR / "gcp"
NODE_PATH = GCP_DIR / "monitoring" / "gke_monitor_node.py"
TOOLS_PATH = GCP_DIR / "tools.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


try:
    node_mod = _load("gke_monitor_node_test", NODE_PATH)
except Exception:
    node_mod = None

gcp_tools = _load("gcp_tools_node_test", TOOLS_PATH)

requires_node = pytest.mark.skipif(
    node_mod is None, reason="gke_monitor_node requiere rich")


class TestTool24Registration:
    """Regresion: -o json rompia el script (solo acepta console|html)
    y la opcion no soportaba seleccion multi-proyecto."""

    def test_multi_project_arg_and_stem(self):
        tool = gcp_tools.TOOLS["24"]
        assert "--multi-project" in tool["args"]
        assert "gke_monitor_node" in gcp_tools.MULTI_PROJECT_PARAM_SCRIPTS

    def test_export_choices_match_script(self):
        """Las opciones del prompt deben ser las que el script acepta."""
        tool = gcp_tools.TOOLS["24"]
        assert "json" not in tool["export_choices"]
        assert set(tool["export_choices"]) == {"console", "html", "ninguno"}
        assert tool["export_default"] == "html"


@requires_node
class TestCollectClusterNodes:
    def test_credentials_failure_raises(self, monkeypatch):
        monkeypatch.setattr(node_mod, "ensure_gke_cluster_credentials",
                            lambda *a, **k: False)
        with pytest.raises(RuntimeError):
            node_mod.collect_cluster_nodes("p1", "c1", "us-central1-a")

    def test_empty_nodes_raises(self, monkeypatch):
        """kubectl sin nodos != cluster vacio: se trata como no accesible."""
        monkeypatch.setattr(node_mod, "ensure_gke_cluster_credentials",
                            lambda *a, **k: True)
        monkeypatch.setattr(node_mod, "get_nodes_resources",
                            lambda ctx, env=None: [])
        with pytest.raises(RuntimeError):
            node_mod.collect_cluster_nodes("p1", "c1", "us-central1-a")

    def test_rows_carry_project_and_cluster(self, monkeypatch):
        monkeypatch.setattr(node_mod, "ensure_gke_cluster_credentials",
                            lambda *a, **k: True)
        fake = [{"name": "n1", "zone": "z", "cpu_alloc": "4",
                 "cpu_used": "1", "cpu_pct": "50%", "mem_alloc": "16Gi",
                 "mem_used": "8Gi", "mem_pct": "55%", "pods_max": "110"}]
        monkeypatch.setattr(node_mod, "get_nodes_resources",
                            lambda ctx, env=None: [dict(fake[0])])
        rows = node_mod.collect_cluster_nodes("p1", "c1", "us-central1-a")
        assert rows[0]["project"] == "p1" and rows[0]["cluster"] == "c1"


@requires_node
class TestNodeHtml:
    def _row(self):
        return {"project": "p1", "cluster": "c1", "name": "n1", "zone": "z",
                "cpu_alloc": "4", "cpu_used": "1", "cpu_pct": "90%",
                "mem_alloc": "16Gi", "mem_used": "8Gi", "mem_pct": "55%",
                "pods_max": "110"}

    def test_html_contains_dashboard_parts(self):
        errors = [{"project": "pb", "cluster": "cb",
                   "location": "us", "error": "timeout"}]
        html = node_mod.generate_html(["p1", "pb"], [self._row()], errors)
        assert "<!DOCTYPE html>" in html
        assert "nodesTable" in html          # tabla consolidada JS
        assert "errorsSection" in html       # clusters no accesibles
        assert "pct-high" in html            # clases de resaltado de %
        assert "var REPORT" in html          # datos embebidos
        assert "Project" in html             # columna proyecto
        assert "filterProject" in html       # filtro por proyecto

    def test_html_no_errors_empty_section(self):
        html = node_mod.generate_html(["p1"], [self._row()], [])
        assert '"errors": []' in html
