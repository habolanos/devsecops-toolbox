"""Tests para SCM Inspection Remediator (opción 44 azdo) + columna ACTION del CSV."""
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import scm.azdo.tools as azdo_tools
from scm.azdo import scm_inspection_remediator as rem


LOG_SAMPLE = """2026-10-06T00:14:51.033Z ##[error]  🔴 [HIGH] STAGE_VARIABLES
2026-10-06T00:14:51.033Z ##[error]     Environment: 'Develop'
2026-10-06T00:14:51.033Z ##[error]     Variable: 'cluster_name'
2026-10-06T00:14:51.033Z ##[error]     Reason: 'paridad (variable existe en otros stages pero falta en este)'
2026-10-06T00:14:51.033Z ##[error]     El stage 'Develop' no define 1 variable(s): cluster_name (de Production)
2026-10-06T00:14:51.033Z
2026-10-06T00:14:51.033Z ##[warning]  🔴 [HIGH] RULE_1_SECRET
2026-10-06T00:14:51.033Z ##[warning]     Environment: 'Production'
2026-10-06T00:14:51.033Z ##[warning]     Variable: 'ksaSecretManager'
2026-10-06T00:14:51.033Z ##[warning]     ksaSecretManager not marked secret
"""


DEFINITION = {
    "name": "ps-test-pipeline-CD",
    "variables": {"tuSecret": {"value": ""}},
    "environments": [
        {"id": 1, "name": "Develop", "variables": {
            "serviceAccount": {"value": ""}}},
        {"id": 2, "name": "Production", "variables": {
            "cluster_name": {"value": "gke-prod"},
            "ksaSecretManager": {"value": "secret-val"},
            "serviceAccount": {"value": "sa@prod"}}},
        {"id": 3, "name": "Production-Rollback", "variables": {
            "cluster_name": {"value": ""}}},
        {"id": 4, "name": "SCM Inspection", "variables": {}},
    ],
}


def _v(rule, env="", variable="", reason="", detail="", sev="HIGH"):
    return {"severity": sev, "rule": rule, "environment": env,
            "variable": variable, "reason": reason, "detail": detail,
            "task": "t"}


class TestParseLog:
    def test_parsea_bloques_violacion(self):
        vs = rem.parse_log(LOG_SAMPLE, "inspect")
        assert len(vs) == 2
        assert vs[0]["severity"] == "HIGH"
        assert vs[0]["rule"] == "STAGE_VARIABLES"
        assert vs[0]["environment"] == "Develop"
        assert vs[0]["variable"] == "cluster_name"
        assert "paridad" in vs[0]["reason"]
        assert vs[1]["rule"] == "RULE_1_SECRET"
        assert vs[1]["task"] == "inspect"

    def test_lineas_sin_marcador_cierran_bloque(self):
        vs = rem.parse_log(
            "##[error] [HIGH] STAGE_VARIABLES\n##[error]   Environment: 'Dev'\n"
            "texto libre fuera del bloque\n", "t")
        assert len(vs) == 1


class TestBuildActionables:
    def test_secret_genera_update_con_isSecret(self):
        a = rem.build_actionables(DEFINITION, [
            _v("RULE_1_SECRET", "Production", "ksaSecretManager",
               detail="ksaSecretManager not marked secret")])
        r = a["rules"][0]
        assert r["action"] == "update" and r["scope"] == "environment"
        assert r["stage"] == "Production" and r["isSecret"] is True
        assert r["value"] == "secret-val"  # preserva el valor actual

    def test_paridad_agrega_con_valor_del_origen(self):
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "Develop", "cluster_name",
               reason="paridad (variable existe en otros stages pero falta en este)",
               detail="El stage 'Develop' no define 1 variable(s) presentes en "
                      "otros stages: cluster_name (de Production)")])
        r = a["rules"][0]
        assert r["action"] == "add" and r["stage"] == "Develop"
        assert r["value"] == "gke-prod"

    def test_paridad_sin_valor_fuente_va_a_manual(self):
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "Develop", "x_missing",
               reason="paridad",
               detail="El stage 'Develop' no define: x_missing (de Otro)")])
        assert a["rules"] == []
        assert len(a["manual"]) == 1

    def test_contenido_update_con_valor_de_otro_stage(self):
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "Develop", "serviceAccount",
               reason="contenido (variable definida pero sin valor)",
               detail="El stage 'Develop' tiene 1 variable(s) SIN valor: serviceAccount")])
        r = a["rules"][0]
        assert r["action"] == "update" and r["value"] == "sa@prod"

    def test_nivel_pipeline_manual_sin_valor(self):
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "(nivel pipeline)", "tuSecret",
               detail="tiene 1 variable(s) SIN valor")])
        assert a["rules"] == []
        assert any("tuSecret" in m for m in a["manual"])

    def test_nivel_pipeline_con_valor_inyectado(self):
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "(nivel pipeline)", "tuSecret",
               detail="tiene 1 variable(s) SIN valor")],
            values={"tuSecret": "mi-valor"})
        r = a["rules"][0]
        assert r["action"] == "update" and r["scope"] == "release"
        assert r["value"] == "mi-valor"

    def test_secret_ya_secreto_va_a_manual(self):
        definition = {"environments": [
            {"name": "Prod", "variables": {"ksa": {"value": None, "isSecret": True}}}]}
        a = rem.build_actionables(definition, [
            _v("RULE_1_SECRET", "Prod", "ksa")])
        assert a["rules"] == []
        assert len(a["manual"]) == 1


class TestPendingValues:
    def test_pending_registra_var_y_scopes(self):
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "(nivel pipeline)", "tuSecret",
               detail="SIN valor"),
            _v("STAGE_VARIABLES", "Develop", "x_missing",
               reason="paridad", detail="... x_missing (de Otro)")])
        assert "tuSecret" in a["pending"]
        assert a["pending"]["tuSecret"]["scope"] == "release"
        assert a["pending"]["x_missing"]["scope"] == "environment"
        assert a["pending"]["x_missing"]["stages"] == ["Develop"]

    def test_collect_enter_usa_tbd(self):
        a = {"pending": {"cluster_name": {"scope": "environment",
                                          "stages": ["Develop"]}}}
        values = rem.collect_pending_values(a, prompt_fn=lambda _p: "")
        assert values["cluster_name"] == "TBD"

    def test_collect_valor_ingresado(self):
        a = {"pending": {"cluster_name": {"scope": "environment",
                                          "stages": ["Develop"]}}}
        values = rem.collect_pending_values(a, prompt_fn=lambda _p: "gke-prod")
        assert values["cluster_name"] == "gke-prod"

    def test_collect_skip_deja_manual(self):
        a = {"pending": {"x": {"scope": "release", "stages": []}}}
        values = rem.collect_pending_values(a, prompt_fn=lambda _p: "s")
        assert "x" not in values

    def test_collect_respeta_valores_previos(self):
        a = {"pending": {"x": {"scope": "release", "stages": []}}}
        prompts = []
        values = rem.collect_pending_values(
            a, values={"x": "ya-definido"},
            prompt_fn=lambda p: prompts.append(p) or "otro")
        assert values["x"] == "ya-definido" and prompts == []

    def test_fill_pending_default_cubre_todas(self):
        a = {"pending": {"a1": {"scope": "release", "stages": []},
                         "b2": {"scope": "environment", "stages": ["QA"]}}}
        values = rem.fill_pending_default(a, {"a1": "custom"})
        assert values == {"a1": "custom", "b2": "TBD"}

    def test_rebuild_con_tbd_genera_reglas(self):
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "(nivel pipeline)", "tuSecret",
               detail="SIN valor")])
        values = rem.fill_pending_default(a, {})
        a2 = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "(nivel pipeline)", "tuSecret",
               detail="SIN valor")], values=values)
        assert a2["rules"][0]["value"] == "TBD"
        assert a2["pending"] == {}


class TestGenerateTemplate:
    def test_genera_yaml_valido_en_outcome(self, tmp_path):
        rules = [{"name": "x", "action": "add", "scope": "environment",
                  "stage": "Develop", "value": "v"}]
        path = rem.generate_template(rules, "1837", "pipe-test", out_dir=tmp_path)
        assert path.exists() and "pipe_cd_inspection_fix_1837" in path.name
        tpl = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert tpl["update"]["variables"] == rules
        assert tpl["metadata"]["name"].startswith("SCM Inspection Fix")
        assert tpl["options"]["rollback_on_error"] is True


class TestOutcomeResolution:
    def test_env_tiene_prioridad(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DEVSECOPS_OUTPUT_DIR", str(tmp_path / "custom"))
        assert rem.resolve_outcome_dir() == (tmp_path / "custom").resolve()

    def test_fallback_scm_outcome(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DEVSECOPS_OUTPUT_DIR", raising=False)
        monkeypatch.setattr(rem, "CONFIG_FILE", tmp_path / "inexistente.json")
        monkeypatch.setattr(rem, "SCM_ROOT", tmp_path / "scm")
        resolved = rem.resolve_outcome_dir()
        assert resolved == (tmp_path / "scm" / "outcome").resolve()
        assert resolved.exists()


class TestLauncherWiring:
    def test_opcion_44_registrada(self):
        tool = azdo_tools.TOOLS["44"]
        assert tool["path"] == "scm_inspection_remediator.py"
        assert tool["group"] == "updatepipe"
        assert "--interactive" in tool["args"]

    def test_script_existe(self):
        assert (azdo_tools.BASE_DIR / azdo_tools.TOOLS["44"]["path"]).exists()
