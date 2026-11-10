"""
Tests para selección multi-proyecto AzDO (azdo.project + azdo.projects).

Cubre:
  - azdo/tools.py: configured_projects() y select_project()
  - azdo/cicd_inventory.py: load_projects_from_config()
"""

import importlib.util
import io
import json
import os
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


# ═══════════════════════════════════════════════════════════════════════════
# Cache scoping por proyecto
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def cd_detailed_mod():
    try:
        return _load_module("cd_detailed_test", AZDO_DIR / "cicd_inventory_cd_detailed.py")
    except ImportError:
        pytest.skip("cicd_inventory_cd_detailed.py no importable (deps faltantes)")


@pytest.fixture(scope="module")
def ci_detailed_mod():
    try:
        return _load_module("ci_detailed_test", AZDO_DIR / "cicd_inventory_ci_detailed.py")
    except ImportError:
        pytest.skip("cicd_inventory_ci_detailed.py no importable (deps faltantes)")


@pytest.fixture(scope="module")
def prod_deploy_mod():
    try:
        return _load_module("prod_deploy_test", AZDO_DIR / "cicd_inventory_prod_deploy.py")
    except ImportError:
        pytest.skip("cicd_inventory_prod_deploy.py no importable (deps faltantes)")


@pytest.fixture(scope="module")
def health_score_mod():
    try:
        return _load_module("health_score_test", AZDO_DIR / "cicd_inventory_health_score.py")
    except ImportError:
        pytest.skip("cicd_inventory_health_score.py no importable (deps faltantes)")


@pytest.fixture(scope="module")
def pipeline_status_mod():
    try:
        return _load_module("pipeline_status_test", AZDO_DIR / "cicd_pipeline_status.py")
    except ImportError:
        pytest.skip("cicd_pipeline_status.py no importable (deps faltantes)")


class TestProjectCacheKey:

    @pytest.mark.parametrize("value,expected", [
        ("Compras.RMI", "Compras.RMI"),
        ("Cadena_de_Suministros", "Cadena_de_Suministros"),
        ("My Project", "My_Project"),
        ("", "default"),
        (None, "default"),
    ])
    def test_slug(self, cd_detailed_mod, value, expected):
        assert cd_detailed_mod._project_cache_key(value) == expected


class TestCacheScoping:

    def test_save_y_find_mismo_proyecto(self, cd_detailed_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        data = {"metadata": {"project": "ProjA"}, "rows": [{"id": 1}]}
        path = cd_detailed_mod._save_cache(data, project="ProjA")
        assert f"ProjA_raw_" in path.name
        assert cd_detailed_mod._find_latest_cache("ProjA") == path

    def test_find_otro_proyecto_no_match(self, cd_detailed_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        data = {"metadata": {"project": "ProjA"}, "rows": []}
        cd_detailed_mod._save_cache(data, project="ProjA")
        assert cd_detailed_mod._find_latest_cache("ProjB") is None

    def test_find_devuelve_mas_reciente_del_proyecto(
            self, cd_detailed_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir(parents=True)
        name = cd_detailed_mod.SCRIPT_NAME
        f1 = cache_dir / f"{name}_ProjA_raw_20250101_000000.json"
        f2 = cache_dir / f"{name}_ProjA_raw_20250102_000000.json"
        f1.write_text("{}", encoding="utf-8")
        f2.write_text("{}", encoding="utf-8")
        os.utime(f1, (1000, 1000))
        os.utime(f2, (2000, 2000))
        assert cd_detailed_mod._find_latest_cache("ProjA") == f2

    def test_ci_detailed_scoped(self, ci_detailed_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        data = {"metadata": {"project": "Compras.RMI"}, "rows": []}
        path = ci_detailed_mod._save_cache(data, project="Compras.RMI")
        assert "Compras.RMI_raw_" in path.name
        assert ci_detailed_mod._find_latest_cache("Compras.RMI") == path
        assert ci_detailed_mod._find_latest_cache("Cadena_de_Suministros") is None

    def test_prod_deploy_lee_cache_cd_del_proyecto(
            self, cd_detailed_mod, prod_deploy_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        data = {"metadata": {"project": "ProjA"}, "rows": [{"id": 1}]}
        path = cd_detailed_mod._save_cache(data, project="ProjA")
        assert prod_deploy_mod._find_cd_cache("ProjA") == path
        assert prod_deploy_mod._find_cd_cache("ProjB") is None

    def test_health_score_lee_cache_ci_cd_del_proyecto(
            self, ci_detailed_mod, cd_detailed_mod, health_score_mod,
            tmp_path, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        data = {"metadata": {"project": "ProjA"}, "rows": []}
        ci_path = ci_detailed_mod._save_cache(data, project="ProjA")
        cd_path = cd_detailed_mod._save_cache(data, project="ProjA")
        assert health_score_mod._find_latest_cache(
            "cicd_inventory_ci_detailed", "ProjA") == ci_path
        assert health_score_mod._find_latest_cache(
            "cicd_inventory_cd_detailed", "ProjA") == cd_path
        assert health_score_mod._find_latest_cache(
            "cicd_inventory_ci_detailed", "ProjB") is None

    def test_pipeline_status_scoped(self, pipeline_status_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path))
        path = pipeline_status_mod._save_cache([], "Org", "ProjA", 30)
        assert "ProjA_raw_" in path.name
        assert pipeline_status_mod._find_latest_cache("ProjA") == path
        assert pipeline_status_mod._find_latest_cache("ProjB") is None

    def test_azdo_parser_cache_scoped_por_org_proyecto(self):
        src = (AZDO_DIR / "health-probe-masive" / "azdo_parser.py").read_text(
            encoding="utf-8")
        assert "_cache_slug(self.org)" in src
        assert "_cache_slug(self.project)" in src


# ═══════════════════════════════════════════════════════════════════════════
# Agentes por stage (CD Detailed Inventory)
# ═══════════════════════════════════════════════════════════════════════════

class TestStageAgents:

    def test_resuelve_queue_id_a_nombre(self, cd_detailed_mod):
        envs = [{"name": "QA", "deployPhases": [
            {"deploymentInput": {"queueId": 7}}]}]
        per_stage, unique = cd_detailed_mod._stage_agents(envs, {"7": "Pool-QA"})
        assert per_stage == [("QA", "Pool-QA")]
        assert unique == ["Pool-QA"]

    def test_queue_object_variant(self, cd_detailed_mod):
        envs = [{"name": "Prod", "deployPhases": [
            {"deploymentInput": {"queue": {"id": 3, "name": "Pool-Prod"}}}]}]
        per_stage, unique = cd_detailed_mod._stage_agents(envs, {})
        assert per_stage == [("Prod", "Pool-Prod")]
        assert unique == ["Pool-Prod"]

    def test_queue_desconocida_usa_id(self, cd_detailed_mod):
        envs = [{"name": "Dev", "deployPhases": [
            {"deploymentInput": {"queueId": 99}}]}]
        per_stage, _ = cd_detailed_mod._stage_agents(envs, {})
        assert per_stage == [("Dev", "queueId:99")]

    def test_stage_sin_agente_es_server_side(self, cd_detailed_mod):
        envs = [{"name": "Gate", "deployPhases": [{"type": "runOnServer"}]}]
        per_stage, unique = cd_detailed_mod._stage_agents(envs, {})
        assert per_stage == [("Gate", "Server-side")]
        assert unique == []

    def test_dedup_multi_fases_y_stages(self, cd_detailed_mod):
        envs = [
            {"name": "QA", "deployPhases": [
                {"deploymentInput": {"queueId": 1}},
                {"deploymentInput": {"queueId": 1}},
                {"deploymentInput": {"queueId": 2}},
            ]},
            {"name": "Prod", "deployPhases": [
                {"deploymentInput": {"queueId": 2}}]},
        ]
        qmap = {"1": "Pool-A", "2": "Pool-B"}
        per_stage, unique = cd_detailed_mod._stage_agents(envs, qmap)
        assert per_stage == [("QA", "Pool-A / Pool-B"), ("Prod", "Pool-B")]
        assert unique == ["Pool-A", "Pool-B"]

    def test_sin_deploy_phases(self, cd_detailed_mod):
        per_stage, _ = cd_detailed_mod._stage_agents([{"name": "X"}], {})
        assert per_stage == [("X", "-")]

    def test_get_queue_map(self, cd_detailed_mod):
        payload = {"value": [{"id": 7, "name": "Pool-QA"},
                             {"id": 8, "name": "Pool-Prod"}]}
        with patch.object(cd_detailed_mod, "safe_az_get", return_value=payload):
            qmap = cd_detailed_mod._get_queue_map({}, "Org", "Proj")
        assert qmap == {"7": "Pool-QA", "8": "Pool-Prod"}

    def test_fetch_row_incluye_agents(self, cd_detailed_mod):
        detail = {"environments": [
            {"name": "QA", "deployPhases": [{"deploymentInput": {"queueId": 7}}]}],
            "variables": {}}

        def fake_get(url, headers, params=None):
            if "release/definitions/" in url:
                return detail
            return {"value": []}

        with patch.object(cd_detailed_mod, "safe_az_get", side_effect=fake_get):
            row = cd_detailed_mod._fetch_cd_pipeline(
                {"id": 1, "name": "pipe"}, {}, "Org", "Proj",
                queue_map={"7": "Pool-QA"})
        assert row["agents"] == "Pool-QA"
        assert row["agentPerStage_QA"] == "Pool-QA"
