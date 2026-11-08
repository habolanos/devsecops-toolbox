"""
Tests para selección multi-proyecto AzDO (azdo.project + azdo.projects).

Cubre:
  - azdo/tools.py: configured_projects() y select_project()
  - azdo/cicd_inventory.py: load_projects_from_config()
"""

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCM_ROOT = Path(__file__).resolve().parents[2]
AZDO_DIR = SCM_ROOT / "azdo"


def _load_module(name: str, path: Path):
    sys.path.insert(0, str(SCM_ROOT))
    sys.path.insert(0, str(AZDO_DIR))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tools_mod():
    return _load_module("azdo_tools_launcher", AZDO_DIR / "tools.py")


@pytest.fixture(scope="module")
def inventory_mod():
    try:
        return _load_module("cicd_inventory_test", AZDO_DIR / "cicd_inventory.py")
    except ImportError:
        pytest.skip("cicd_inventory.py no importable (deps faltantes)")


# ═══════════════════════════════════════════════════════════════════════════
# configured_projects
# ═══════════════════════════════════════════════════════════════════════════

class TestConfiguredProjects:

    def test_sin_config(self, tools_mod):
        assert tools_mod.configured_projects({}) == []

    def test_solo_project(self, tools_mod):
        cfg = {"azdo": {"project": "ProjA"}}
        assert tools_mod.configured_projects(cfg) == ["ProjA"]

    def test_solo_projects_list(self, tools_mod):
        cfg = {"azdo": {"projects": ["ProjB", "ProjC"]}}
        assert tools_mod.configured_projects(cfg) == ["ProjB", "ProjC"]

    def test_project_default_antepuesto(self, tools_mod):
        cfg = {"azdo": {"project": "ProjA", "projects": ["ProjB", "ProjC"]}}
        assert tools_mod.configured_projects(cfg) == ["ProjA", "ProjB", "ProjC"]

    def test_project_ya_en_lista_no_duplica(self, tools_mod):
        cfg = {"azdo": {"project": "ProjA", "projects": ["ProjA", "ProjB"]}}
        assert tools_mod.configured_projects(cfg) == ["ProjA", "ProjB"]

    def test_sanitiza_entradas_invalidas(self, tools_mod):
        cfg = {"azdo": {"projects": ["ProjA", "", "  ", None, 42, "ProjB"]}}
        assert tools_mod.configured_projects(cfg) == ["ProjA", "ProjB"]

    def test_projects_no_lista_ignorado(self, tools_mod):
        cfg = {"azdo": {"project": "ProjA", "projects": "ProjB"}}
        assert tools_mod.configured_projects(cfg) == ["ProjA"]


# ═══════════════════════════════════════════════════════════════════════════
# select_project
# ═══════════════════════════════════════════════════════════════════════════

class TestSelectProject:

    def test_sin_config_retorna_vacio(self, tools_mod):
        assert tools_mod.select_project({}) == ""

    def test_un_proyecto_sin_prompt(self, tools_mod):
        cfg = {"azdo": {"project": "ProjA"}}
        with patch("builtins.input", side_effect=AssertionError("no debe preguntar")):
            assert tools_mod.select_project(cfg) == "ProjA"

    def test_multi_enter_usa_default(self, tools_mod):
        cfg = {"azdo": {"project": "ProjA", "projects": ["ProjA", "ProjB"]}}
        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", return_value=""):
            assert tools_mod.select_project(cfg) == "ProjA"

    def test_multi_seleccion_numerada(self, tools_mod):
        cfg = {"azdo": {"project": "ProjA", "projects": ["ProjA", "ProjB"]}}
        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", return_value="2"):
            assert tools_mod.select_project(cfg) == "ProjB"

    def test_multi_texto_libre(self, tools_mod):
        cfg = {"azdo": {"project": "ProjA", "projects": ["ProjA", "ProjB"]}}
        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", return_value="Otro_Proyecto"):
            assert tools_mod.select_project(cfg) == "Otro_Proyecto"

    def test_multi_numero_fuera_de_rango_es_nombre(self, tools_mod):
        cfg = {"azdo": {"project": "ProjA", "projects": ["ProjA", "ProjB"]}}
        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", return_value="99"):
            assert tools_mod.select_project(cfg) == "99"

    def test_multi_sin_tty_usa_default(self, tools_mod):
        cfg = {"azdo": {"project": "ProjA", "projects": ["ProjA", "ProjB"]}}
        with patch.object(sys.stdin, "isatty", return_value=False), \
             patch("builtins.input", side_effect=AssertionError("no debe preguntar")):
            assert tools_mod.select_project(cfg) == "ProjA"


# ═══════════════════════════════════════════════════════════════════════════
# ask_common_params con multi-proyecto
# ═══════════════════════════════════════════════════════════════════════════

class TestAskCommonParamsProjects:

    def test_seleccion_se_refleja_en_params(self, tools_mod):
        cfg = {"azdo": {
            "organization_url": "https://dev.azure.com/Org",
            "project": "ProjA",
            "projects": ["ProjA", "ProjB"],
            "pat": "token",
        }}
        with patch.object(sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", return_value="2"):
            params = tools_mod.ask_common_params(cfg)
        assert params["project"] == "ProjB"
        assert params["org"] == "https://dev.azure.com/Org"
        assert params["pat"] == "token"

    def test_un_proyecto_fast_path(self, tools_mod):
        cfg = {"azdo": {
            "organization_url": "https://dev.azure.com/Org",
            "project": "ProjA",
            "pat": "token",
        }}
        with patch("builtins.input", side_effect=AssertionError("no debe preguntar")):
            params = tools_mod.ask_common_params(cfg)
        assert params["project"] == "ProjA"


# ═══════════════════════════════════════════════════════════════════════════
# cicd_inventory.load_projects_from_config
# ═══════════════════════════════════════════════════════════════════════════

class TestLoadProjectsFromConfig:

    def _write_cfg(self, tmp_path, azdo):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"azdo": azdo}), encoding="utf-8")
        return cfg_file

    def test_projects_list(self, inventory_mod, tmp_path):
        cfg = self._write_cfg(tmp_path, {"projects": ["P1", "P2"]})
        assert inventory_mod.load_projects_from_config(cfg) == ["P1", "P2"]

    def test_fallback_project_scalar(self, inventory_mod, tmp_path):
        cfg = self._write_cfg(tmp_path, {"project": "ProjA"})
        assert inventory_mod.load_projects_from_config(cfg) == ["ProjA"]

    def test_fallback_default_projects(self, inventory_mod, tmp_path):
        cfg = tmp_path / "inexistente.json"
        assert inventory_mod.load_projects_from_config(cfg) == \
            list(inventory_mod.DEFAULT_PROJECTS)

    def test_azdo_vacio_fallback(self, inventory_mod, tmp_path):
        cfg = self._write_cfg(tmp_path, {})
        assert inventory_mod.load_projects_from_config(cfg) == \
            list(inventory_mod.DEFAULT_PROJECTS)

    def test_json_malformado_fallback(self, inventory_mod, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text("{no es json", encoding="utf-8")
        assert inventory_mod.load_projects_from_config(cfg) == \
            list(inventory_mod.DEFAULT_PROJECTS)

    def test_sanitiza_lista(self, inventory_mod, tmp_path):
        cfg = self._write_cfg(tmp_path, {"projects": ["P1", "", "  ", "P2"]})
        assert inventory_mod.load_projects_from_config(cfg) == ["P1", "P2"]
