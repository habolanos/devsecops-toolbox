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

    def test_paridad_propaga_isSecret_para_var_secreta(self):
        """ksaSecretManager flaggeada por RULE_1_SECRET en un stage debe
        agregarse con isSecret en otro stage por paridad."""
        definition = {"environments": [
            {"name": "Production",
             "variables": {"ksaSecretManager": {"value": "v1"}}},
            {"name": "Develop", "variables": {}}]}
        a = rem.build_actionables(definition, [
            _v("RULE_1_SECRET", "Production", "ksaSecretManager"),
            _v("STAGE_VARIABLES", "Develop", "ksaSecretManager",
               reason="paridad",
               detail="... ksaSecretManager (de Production)")])
        add = next(r for r in a["rules"]
                   if r["action"] == "add" and r["stage"] == "Develop")
        assert add["isSecret"] is True

    def test_env_mismatch_warning_en_nota(self):
        """Copiar de Develop → Production agrega advertencia en la nota."""
        definition = {"environments": [
            {"name": "Develop",
             "variables": {"cluster_name": {"value": "gke-dev-01"}}},
            {"name": "Production", "variables": {}}]}
        a = rem.build_actionables(definition, [
            _v("STAGE_VARIABLES", "Production", "cluster_name",
               reason="paridad",
               detail="... cluster_name (de Develop)")])
        assert any("⚠" in s and "'dev'" in s for s in a["summary"])

    def test_env_mismatch_rollback_a_prod_sin_warning_de_token(self):
        """Production-Rollback → Production: mismo token 'prod', sin warning
        (el warning es por nombre de stage, no por valor)."""
        assert rem._env_mismatch("Production-Rollback", "Production") == ""
        assert rem._env_mismatch("Production", "Develop") != ""
        assert rem._env_mismatch("QA", "Staging") != ""

    def test_env_token(self):
        assert rem._env_token("Production") == "prod"
        assert rem._env_token("Develop") == "dev"
        assert rem._env_token("QA") == "qa"
        assert rem._env_token("Staging") == "stg"
        assert rem._env_token("Validator") == ""

    def test_env_mismo_ambiente_sin_warning(self):
        """Production → Production-Rollback: mismo token 'prod', sin warning."""
        definition = {"environments": [
            {"name": "Production", "variables": {"x": {"value": "v"}}},
            {"name": "Production-Rollback", "variables": {}}]}
        a = rem.build_actionables(definition, [
            _v("STAGE_VARIABLES", "Production-Rollback", "x",
               reason="paridad", detail="... x (de Production)")])
        assert a["rules"] and not any("⚠" in s for s in a["summary"])


class TestRemoves:
    def test_pipeline_level_remove(self):
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "(nivel pipeline)", "tuSecret",
               detail="SIN valor")], removes={"tuSecret"})
        r = a["rules"][0]
        assert r["action"] == "remove" and r["scope"] == "release"
        assert "value" not in r  # remove no lleva value
        assert not a["pending"]

    def test_contenido_remove_stage(self):
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "Develop", "serviceAccount",
               reason="contenido",
               detail="1 variable(s) SIN valor")],
            removes={"serviceAccount"})
        r = a["rules"][0]
        assert r["action"] == "remove" and r["stage"] == "Develop"

    def test_paridad_remove_noop(self):
        """Variable marcada para eliminar que NO existe en el stage
        (paridad = ausente) → no rule, nota manual de claridad."""
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "Develop", "x_missing",
               reason="paridad", detail="... x_missing (de Otro)")],
            removes={"x_missing"})
        assert a["rules"] == []
        assert any("ya ausente" in m for m in a["manual"])

    def test_rule1_secret_remove(self):
        a = rem.build_actionables(DEFINITION, [
            _v("RULE_1_SECRET", "Production", "ksaSecretManager")],
            removes={"ksaSecretManager"})
        r = a["rules"][0]
        assert r["action"] == "remove" and r["stage"] == "Production"

    def test_template_no_incluye_nota(self, tmp_path):
        rules = [{"name": "x", "action": "add", "scope": "environment",
                  "stage": "Dev", "value": "v", "note": "copiado de Prod"}]
        tpl = yaml.safe_load(rem.generate_template(
            rules, "1", "p", out_dir=tmp_path).read_text(encoding="utf-8"))
        assert "note" not in tpl["update"]["variables"][0]


class TestAccionReal:
    """Las reglas reflejan lo que el updater realmente hará."""

    def test_paridad_ausente_real_genera_add(self):
        """Variable realmente ausente en el destino → add con fuente externa."""
        definition = {"environments": [
            {"name": "Production", "variables": {"y": {"value": "src"}}},
            {"name": "QA", "variables": {}}]}
        a = rem.build_actionables(definition, [
            _v("STAGE_VARIABLES", "QA", "y", reason="paridad",
               detail="... y (de Production)")])
        r = a["rules"][0]
        assert r["action"] == "add" and r["value"] == "src"

    def test_add_flaggeada_pero_ya_existe(self):
        """'artifact.replacePrefixMatch' flaggeada faltante en Prod pero
        existe → update (no add)."""
        definition = {"environments": [
            {"name": "Production", "variables": {
                "artifact.replacePrefixMatch": {"value": "/api"}}},
            {"name": "Staging", "variables": {}}]}
        a = rem.build_actionables(definition, [
            _v("STAGE_VARIABLES", "Production", "artifact.replacePrefixMatch",
               reason="paridad",
               detail="... artifact.replacePrefixMatch (de Staging)")])
        # existe en Production → update + nota; pero sin fuente externa
        # (Staging no la tiene) → 'ya existe con valor — sin cambio'
        assert a["rules"] == []
        assert any("sin cambio" in m for m in a["manual"])

    def test_add_existente_mismo_valor_sin_cambio(self):
        definition = {"environments": [
            {"name": "Develop", "variables": {"x": {"value": "v"}}},
            {"name": "QA", "variables": {"x": {"value": "v"}}}]}
        a = rem.build_actionables(definition, [
            _v("STAGE_VARIABLES", "QA", "x", reason="paridad",
               detail="... x (de Develop)")])
        assert a["rules"] == []
        assert any("sin cambio" in m for m in a["manual"])

    def test_add_existente_distinto_valor_update_sobrescribe(self):
        definition = {"environments": [
            {"name": "Develop", "variables": {"x": {"value": "dev"}}},
            {"name": "QA", "variables": {"x": {"value": "viejo"}}}]}
        a = rem.build_actionables(definition, [
            _v("STAGE_VARIABLES", "QA", "x", reason="paridad",
               detail="... x (de Develop)")])
        r = a["rules"][0]
        assert r["action"] == "update" and r["value"] == "dev"
        assert "sobrescribe" in r.get("note", "")

    def test_update_sin_existir_se_omite(self):
        definition = {"environments": [
            {"name": "Develop", "variables": {"x": {"value": "v"}}},
            {"name": "QA", "variables": {}}]}
        a = rem.build_actionables(definition, [
            _v("STAGE_VARIABLES", "QA", "inexistente",
               reason="contenido", detail="SIN valor")],
            values={"inexistente": "manual"})
        # update de var inexistente → omitida, va a manual
        assert a["rules"] == []
        assert any("no está en la definición" in m for m in a["manual"])

    def test_remove_sin_existir_nota_ya_ausente(self):
        definition = {"environments": [
            {"name": "QA", "variables": {}}]}
        a = rem.build_actionables(DEFINITION, [
            _v("STAGE_VARIABLES", "QA", "fantasma", reason="contenido",
               detail="SIN valor")], removes={"fantasma"})
        assert a["rules"] == []
        assert any("ya ausente" in m for m in a["manual"])

    def test_secret_ya_secreto_sin_cambio(self):
        definition = {"environments": [
            {"name": "Prod", "variables": {
                "ksa": {"value": "v", "isSecret": True}}}]}
        a = rem.build_actionables(definition, [
            _v("RULE_1_SECRET", "Prod", "ksa")])
        assert a["rules"] == []
        assert any("sin cambio" in m for m in a["manual"])


class TestEditRulesMatch:
    def test_match_filtra_edicion_puntual(self):
        rules = [
            {"name": "a", "action": "add", "scope": "environment",
             "stage": "QA", "value": "v1"},
            {"name": "a", "action": "add", "scope": "environment",
             "stage": "Staging", "value": "v1"},
            {"name": "b", "action": "add", "scope": "environment",
             "stage": "QA", "value": "v2"},
        ]
        ans = iter(["solo-qa"])
        out = rem.edit_rules(
            rules, prompt_fn=lambda _p: next(ans),
            match=lambda r: r["name"] == "a" and r.get("stage") == "QA")
        assert out[0]["value"] == "solo-qa"      # a@QA editada
        assert out[1]["value"] == "v1"           # a@Staging intacta
        assert out[2]["value"] == "v2"           # b intacta


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
        values, removes = rem.collect_pending_values(
            a, prompt_fn=lambda _p: "")
        assert values["cluster_name"] == "TBD" and not removes

    def test_collect_valor_ingresado(self):
        a = {"pending": {"cluster_name": {"scope": "environment",
                                          "stages": ["Develop"]}}}
        values, _ = rem.collect_pending_values(
            a, prompt_fn=lambda _p: "gke-prod")
        assert values["cluster_name"] == "gke-prod"

    def test_collect_skip_deja_manual(self):
        a = {"pending": {"x": {"scope": "release", "stages": []}}}
        values, removes = rem.collect_pending_values(
            a, prompt_fn=lambda _p: "s")
        assert "x" not in values and "x" not in removes

    def test_collect_ignorar_alias_i(self):
        a = {"pending": {"x": {"scope": "release", "stages": []}}}
        values, removes = rem.collect_pending_values(
            a, prompt_fn=lambda _p: "i")
        assert "x" not in values and "x" not in removes

    def test_collect_eliminar_marca_remove(self):
        a = {"pending": {"tuSecret": {"scope": "release", "stages": []}}}
        values, removes = rem.collect_pending_values(
            a, prompt_fn=lambda _p: "e")
        assert "tuSecret" in removes and "tuSecret" not in values

    def test_collect_respeta_valores_previos(self):
        a = {"pending": {"x": {"scope": "release", "stages": []}}}
        prompts = []
        values, _ = rem.collect_pending_values(
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


class TestReviewAndMask:
    def test_mask_oculta_secretos(self):
        assert rem.mask_value("apiSecret", "valor-real") == "********"
        assert rem.mask_value({"name": "x", "isSecret": True}, "v") == "********"
        assert rem.mask_value("cluster_name", "gke-prod") == "gke-prod"
        assert rem.mask_value("apiSecret", "TBD") == "TBD"  # placeholder visible

    def test_review_enter_conserva(self):
        values, _ = rem.review_values({"x": "v1"}, ["x"],
                                      prompt_fn=lambda _p: "")
        assert values == {"x": "v1"}

    def test_review_nuevo_valor_reemplaza(self):
        values, _ = rem.review_values({"x": "TBD"}, ["x"],
                                      prompt_fn=lambda _p: "gke-prod")
        assert values == {"x": "gke-prod"}

    def test_review_skip_regresa_a_manual(self):
        values, _ = rem.review_values(
            {"x": "TBD", "y": "ok"}, ["x", "y"],
            prompt_fn=lambda p: "s" if "[bold cyan]x[/]" in p else "")
        assert values == {"y": "ok"}

    def test_review_eliminar_mueve_a_removes(self):
        values, removes = rem.review_values({"x": "TBD"}, ["x"],
                                            prompt_fn=lambda _p: "e")
        assert values == {} and removes == {"x"}

    def test_review_valor_sobre_eliminar_lo_revierte(self):
        values, removes = rem.review_values(
            {}, ["x"], removes={"x"}, prompt_fn=lambda _p: "nuevo-valor")
        assert values == {"x": "nuevo-valor"} and not removes

    def test_show_rules_no_imprime_secreto(self, capsys):
        rem.show_rules([{"name": "apiSecret", "action": "update",
                         "scope": "environment", "stage": "Prod",
                         "value": "super-secreto", "isSecret": True},
                        {"name": "region", "action": "add",
                         "scope": "environment", "stage": "QA",
                         "value": "us-east1"}])
        out = capsys.readouterr().out
        assert "super-secreto" not in out
        assert "us-east1" in out and "🔒" in out

    def test_show_rules_remove_sin_valor(self, capsys):
        rem.show_rules([{"name": "tuSecret", "action": "remove",
                         "scope": "release"}])
        out = capsys.readouterr().out
        assert "remove" in out and "tuSecret" in out


class TestEditRules:
    RULES = [
        {"name": "a", "action": "add", "scope": "environment",
         "stage": "QA", "value": "v1", "note": "n"},
        {"name": "b", "action": "update", "scope": "environment",
         "stage": "Prod", "value": "v2"},
        {"name": "c", "action": "add", "scope": "environment",
         "stage": "Dev", "value": "v3"},
        {"name": "d", "action": "remove", "scope": "release"},
    ]

    def _run(self, answers):
        it = iter(answers)
        return rem.edit_rules(list(self.RULES),
                              prompt_fn=lambda _p: next(it))

    def test_enter_conserva_todo(self):
        out = self._run(["", "", "", ""])
        assert out == self.RULES

    def test_texto_reemplaza_valor(self):
        out = self._run(["", "nuevo-v2", "", ""])
        assert out[1]["value"] == "nuevo-v2"

    def test_e_convierte_a_remove_sin_valor(self):
        out = self._run(["", "", "e", ""])
        r = out[2]
        assert r["action"] == "remove" and "value" not in r
        assert r["stage"] == "Dev"  # conserva scope/stage

    def test_i_descarta_ajuste(self):
        out = self._run(["i", "", "", ""])
        assert len(out) == 3
        assert all(r["name"] != "a" for r in out)

    def test_valor_sobre_remove_revierte_a_update(self):
        out = self._run(["", "", "", "v9"])
        assert out[3]["action"] == "update" and out[3]["value"] == "v9"

    def test_todos_descartados_lista_vacia(self):
        out = self._run(["i", "i", "i", "i"])
        assert out == []

    def test_k_marca_como_secreta(self):
        out = self._run(["k", "", "", ""])
        assert out[0]["isSecret"] is True
        assert "marcada como secreta" in out[0].get("note", "")

    def test_k_desmarca_secreta(self):
        rules = [{"name": "ksa", "action": "update", "scope": "environment",
                  "stage": "Prod", "value": "v", "isSecret": True}]
        out = rem.edit_rules(rules, prompt_fn=lambda _p: "k")
        # isSecret: false explícito → el engine desmarca el candado
        assert out[0]["isSecret"] is False
        assert "desmarcada" in out[0].get("note", "")

    def test_k_en_remove_no_aplica_y_repregunta(self):
        rules = [{"name": "d", "action": "remove", "scope": "release"}]
        ans = iter(["k", ""])
        out = rem.edit_rules(rules, prompt_fn=lambda _p: next(ans))
        assert out == rules  # k no aplicó; Enter conservó

    def test_show_rules_muestra_unsecret(self, capsys):
        rem.show_rules([{"name": "x", "action": "update",
                         "scope": "release", "value": "v",
                         "isSecret": False}])
        out = capsys.readouterr().out
        assert ("🔓" in out) or ("NO-SECRET" in out)


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

    def test_comentario_simplificado_en_yaml(self, tmp_path):
        rules = [
            {"name": "requests.cpu", "action": "add", "scope": "environment",
             "stage": "Develop", "value": "200m"},
            {"name": "ksa", "action": "update", "scope": "environment",
             "stage": "Production", "value": "s1", "isSecret": True},
            {"name": "tuSecret", "action": "remove", "scope": "release"},
            {"name": "note", "action": "update", "scope": "release",
             "value": "x", "note": "interna"},
        ]
        path = rem.generate_template(rules, "9", "p", out_dir=tmp_path)
        first = path.read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("# 4 cambio(s):")
        assert "+requests.cpu@Develop=200m" in first
        assert "~ksa@Production=" in first and "********" in first
        assert "-tuSecret@release" in first
        assert "~note@release=x" in first
        assert "interna" not in first  # la nota no se filtra al comentario
        # el resumen va en metadata.comment (→ historial AzDO al hacer PUT)
        # y description solo describe el objetivo del template
        tpl = yaml.safe_load(path.read_text(encoding="utf-8"))
        meta = tpl["metadata"]
        assert meta["comment"].startswith("4 cambio(s):")
        assert "tuSecret@release" in meta["comment"]
        assert "4 cambio(s)" not in meta["description"]
        assert "SCM Inspection" in meta["description"]
        # sin reglas → "sin cambios"
        assert rem.rules_summary([]) == "sin cambios"


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


class _FakeClient:
    """AzdoClient simulado: sirve definición, deployments, release y logs."""

    def __init__(self, definition, deployments, release, logs):
        self.base = "https://vsrm.dev.azure.com/o/p/_apis/release"
        self._definition, self._deployments = definition, deployments
        self._release, self._logs = release, logs
        self.calls = []

    def get(self, url, raw=False, params=None):
        self.calls.append(url)
        if url.endswith("/definitions/1837"):
            return self._definition
        if url.endswith("/deployments"):
            return self._deployments
        if "/releases/61141" in url and "/logs" not in url:
            return self._release
        if "/logs" in url:
            return self._logs
        raise AssertionError(f"URL inesperada: {url}")


def _fake_discovery():
    definition = {"name": "pipe-CD", "environments": [
        {"id": 1, "name": "SCM Inspection", "variables": {}},
        {"id": 2, "name": "Production",
         "variables": {"ksa": {"value": "v"}}}]}
    deployments = {"value": [{"deploymentStatus": "succeeded",
                              "release": {"id": 61141}}]}
    release = {"name": "Release-74", "id": 61141, "environments": [
        {"id": 10, "name": "SCM Inspection", "status": "rejected",
         "deploySteps": [{"attempt": 1, "releaseDeployPhases": [
             {"id": 5, "deploymentJobs": [{"tasks": [
                 {"name": "inspect", "status": "failed",
                  "logUrl": "https://x/logs"}]}]}]}]}]}
    log = ("##[error] [HIGH] RULE_1_SECRET\n##[error]   Environment: "
           "'Production'\n##[error]   Variable: 'ksa'\n"
           "##[error]   ksa not marked secret\n\n")
    return _FakeClient(definition, deployments, release, log)


class TestDiscover:
    def test_ultimo_run_y_parseo(self):
        d = rem.discover(_fake_discovery(), "1837", "SCM Inspection")
        assert d["release"]["id"] == 61141
        assert len(d["violations"]) == 1
        assert d["violations"][0]["rule"] == "RULE_1_SECRET"
        assert d["violations"][0]["environment"] == "Production"

    def test_release_explicito_salta_deployments(self):
        client = _fake_discovery()
        d = rem.discover(client, "1837", "SCM Inspection",
                         release_id="61141")
        assert not any(u.endswith("/deployments") for u in client.calls)
        assert d["release"]["id"] == 61141

    def test_salta_deployments_notDeployed(self):
        client = _fake_discovery()
        client._deployments["value"].insert(
            0, {"deploymentStatus": "notDeployed",
                "release": {"id": 99999}})
        d = rem.discover(client, "1837", "SCM Inspection")
        assert d["release"]["id"] == 61141

    def test_stage_inexistente_sale(self):
        client = _fake_discovery()
        with pytest.raises(SystemExit):
            rem.discover(client, "1837", "Stage Fantasma")

    def test_stage_nunca_corrio_sale(self):
        client = _fake_discovery()
        client._deployments = {"value": [
            {"deploymentStatus": "notDeployed", "release": {"id": 1}}]}
        with pytest.raises(SystemExit):
            rem.discover(client, "1837", "SCM Inspection")

    def test_dedup_violaciones_repetidas(self):
        client = _fake_discovery()
        rel = client._release["environments"][0]
        rel["deploySteps"][0]["releaseDeployPhases"][0][
            "deploymentJobs"][0]["tasks"].append(
            {"name": "inspect2", "status": "failed",
             "logUrl": "https://x/logs"})
        d = rem.discover(client, "1837", "SCM Inspection")
        assert len(d["violations"]) == 1  # misma violación en 2 tasks → dedup


class TestApplyTemplate:
    def test_comando_invoca_pipeline_updater(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(rem.subprocess, "run",
                            lambda cmd, cwd: calls.append((cmd, cwd))
                            or type("R", (), {"returncode": 0})())
        tpl = tmp_path / "pipe_cd_fix.yaml"
        rc = rem.apply_template(tpl, "1837", "org", "proj", "pat",
                                dry_run=True)
        assert rc == 0
        cmd, cwd = calls[0]
        assert "scm.azdo.pipeline_updater.pipeline_updater" in cmd
        assert "--dry-run" in cmd and "--template" in cmd
        assert cmd[cmd.index("--definition-ids") + 1] == "1837"

    def test_apply_sin_dry_run_flag(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(rem.subprocess, "run",
                            lambda cmd, cwd: calls.append(cmd)
                            or type("R", (), {"returncode": 0})())
        rem.apply_template(tmp_path / "t.yaml", "1", "o", "p", "pat",
                           dry_run=False)
        assert "--dry-run" not in calls[0]


class TestReleaseTemplate:
    """generate_release_template + apply_release_template (engine op. 42)."""

    def _rules(self):
        return [
            {"name": "ksa", "action": "update", "scope": "environment",
             "stage": "Production", "value": "v1", "isSecret": True},
            {"name": "nueva", "action": "add", "scope": "environment",
             "stage": "QA", "value": "n"},
            {"name": "old", "action": "remove", "scope": "environment",
             "stage": "Production"},
            {"name": "tuSecret", "action": "update", "scope": "release",
             "value": "x", "isSecret": False},
        ]

    def test_template_formato_engine(self, tmp_path):
        p = rem.generate_release_template(self._rules(), "61062", "pipe",
                                          out_dir=tmp_path)
        tpl = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert p.name.startswith("release_inspection_fix_61062_")
        assert tpl["release"]["ids"] == ["61062"]
        ev = tpl["update"]["env_vars"]
        assert ev[0] == {"stage": "Production", "name": "ksa",
                         "value": "v1", "allowOverride": False,
                         "isSecret": True}
        assert ev[1] == {"stage": "QA", "name": "nueva", "value": "n",
                         "allowOverride": False}
        assert ev[2] == {"stage": "Production", "name": "old",
                         "action": "remove"}
        gv = tpl["update"]["global_vars"]
        assert gv == [{"name": "tuSecret", "value": "x",
                       "allowOverride": False, "isSecret": False}]

    def test_apply_invoca_engine_opcion_42(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(rem.subprocess, "run",
                            lambda cmd, cwd: calls.append(cmd)
                            or type("R", (), {"returncode": 0})())
        rc = rem.apply_release_template(tmp_path / "t.yaml", "61062",
                                        "org", "proj", "pat", dry_run=True)
        assert rc == 0
        cmd = calls[0]
        assert ("scm.azdo.pipeline_cd_update_release."
                "pipeline_cd_update_release" in cmd)
        assert "--dry-run" in cmd and "--template" in cmd
        assert cmd[cmd.index("--release-id") + 1] == "61062"


class TestReleaseEngineExtras:
    """El engine (opción 42) soporta isSecret/remove en sus templates."""

    def _engine(self):
        from scm.azdo.pipeline_cd_update_release.\
            pipeline_cd_update_release import build_patch_payload
        return build_patch_payload

    def _release(self):
        return {"variables": {"g": {"value": "1"},
                              "gsec": {"value": None, "isSecret": True}},
                "environments": [
                    {"name": "QA", "variables": {
                        "v": {"value": "a"},
                        "s": {"value": None, "isSecret": True},
                        "del": {"value": "x"}}}]}

    def test_env_var_is_secret_y_remove(self):
        payload, changes = self._engine()(
            self._release(), [], ["QA,s=s3", "QA,del=", "QA,v=b2"],
            False, "", [None] * 3, [], ["*"], [], [None], "",
            env_var_extras=[{"isSecret": True}, {"action": "remove"}, {}])
        qa = payload["environments"][0]["variables"]
        assert qa["s"]["isSecret"] is True and qa["s"]["value"] == "s3"
        assert "del" not in qa
        assert qa["v"]["value"] == "b2"
        assert not any("error" in c for c in changes)

    def test_desmarcar_secret_explicito(self):
        payload, _ = self._engine()(
            self._release(), [], ["QA,s="], False, "",
            [None], [], ["*"], [], [None], "",
            env_var_extras=[{"isSecret": False}])
        assert payload["environments"][0]["variables"]["s"][
            "isSecret"] is False

    def test_update_preserva_isSecret_existente(self):
        """Bugfix: actualizar una var secreta sin isSecret en el extra
        conservaba el flag (antes lo perdía)."""
        payload, _ = self._engine()(
            self._release(), ["gsec=NEW"], ["QA,s=txt"], False, "",
            [None], [], ["*"], [], [None], "",
            env_var_extras=[{}], global_var_extras=[{}])
        assert payload["variables"]["gsec"]["isSecret"] is True
        assert payload["environments"][0]["variables"]["s"][
            "isSecret"] is True

    def test_remove_ausente_no_es_error(self):
        payload, changes = self._engine()(
            self._release(), [], ["QA,fantasma="], False, "",
            [None], [], ["*"], [], [None], "",
            env_var_extras=[{"action": "remove"}])
        assert not any("error" in c for c in changes)
        assert "ausente" in changes[0]["new"]

    def test_remove_global_var(self):
        payload, changes = self._engine()(
            self._release(), ["g="], [], False, "",
            [], [], ["*"], [], [None], "",
            global_var_extras=[{"action": "remove"}])
        assert "g" not in payload["variables"]
        assert changes[0]["new"] == "(eliminada)"


class _Args:
    definition_id = "1837"
    stage = rem.DEFAULT_STAGE
    release_id = ""
    org = project = pat = "x"
    set = None
    remove = None
    tbd = False
    apply = False
    dry_run = False
    interactive = True
    target = "definition"
    redeploy = False


class TestAllowOverride:
    """Las reglas generadas fijan allowOverride=False — las variables del
    pipeline CD no deben quedar 'settable at release time'."""

    def _def(self):
        return {"variables": {}, "environments": [
            {"name": "Develop", "variables": {}},
            {"name": "Production", "variables": {
                "ksaSecretManager": {"value": "s1"}}}]}

    def test_reglas_llevan_allowOverride_false(self):
        a = rem.build_actionables(self._def(), [
            _v("RULE_1_SECRET", "Production", "ksaSecretManager")])
        assert a["rules"]
        assert all(r.get("allowOverride") is False for r in a["rules"]
                   if r["action"] != "remove")

    def test_template_incluye_allowOverride(self, tmp_path):
        rules = [{"name": "x", "action": "add", "scope": "environment",
                  "stage": "Develop", "value": "v", "allowOverride": False}]
        p = rem.generate_template(rules, "1", "p", out_dir=tmp_path)
        tpl = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert tpl["update"]["variables"][0]["allowOverride"] is False

    def test_release_template_incluye_allowOverride(self, tmp_path):
        rules = [{"name": "x", "action": "add", "scope": "environment",
                  "stage": "QA", "value": "v", "allowOverride": False}]
        p = rem.generate_release_template(rules, "9", "p", out_dir=tmp_path)
        tpl = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert tpl["update"]["env_vars"][0]["allowOverride"] is False

    def test_remove_no_lleva_allowOverride(self):
        a = rem.build_actionables(self._def(), [
            _v("RULE_1_SECRET", "Production", "ksaSecretManager")],
            removes={"ksaSecretManager"})
        assert a["rules"]
        assert all("allowOverride" not in r for r in a["rules"])

    def test_engine_honora_allowOverride_extra(self):
        from scm.azdo.pipeline_cd_update_release.\
            pipeline_cd_update_release import build_patch_payload
        rel = {"variables": {"g": {"value": "1", "allowOverride": False}},
               "environments": [{"name": "QA", "variables": {
                   "v": {"value": "a", "allowOverride": False},
                   "w": {"value": "b", "allowOverride": False}}}]}
        payload, _ = build_patch_payload(
            rel, ["g=2"], ["QA,v=x", "QA,w=y", "QA,new=n"],
            False, "", [None] * 3, [], ["*"], [], [None], "",
            env_var_extras=[{"allowOverride": True}, {},
                            {"allowOverride": False}],
            global_var_extras=[{}])
        qa = payload["environments"][0]["variables"]
        assert payload["variables"]["g"]["allowOverride"] is False
        assert qa["v"]["allowOverride"] is True    # explícito en extras
        assert qa["w"]["allowOverride"] is False   # preservado del existente
        assert qa["new"]["allowOverride"] is False  # explícito (nueva var)


class TestReleaseFallback:
    """Variables que existen solo en la instancia del release (snapshot):
    remove/update se generan igual — el engine de release las aplica; en
    la definición son no-op."""

    def _def_vacia(self):
        return {"variables": {}, "environments": [
            {"name": "Production", "variables": {}}]}

    def test_remove_existe_solo_en_release_genera_regla(self):
        release = {"variables": {"tuSecret": {"value": "x"}},
                   "environments": []}
        a = rem.build_actionables(self._def_vacia(), [
            _v("STAGE_VARIABLES", "(nivel pipeline)", "tuSecret")],
            removes={"tuSecret"}, release=release)
        r = a["rules"][0]
        assert r["action"] == "remove" and r["scope"] == "release"
        assert "solo en el release" in r["note"]
        assert not a["manual"]

    def test_update_valor_inyectado_solo_en_release(self):
        release = {"variables": {"tuSecret": {"value": "x"}},
                   "environments": []}
        a = rem.build_actionables(self._def_vacia(), [
            _v("STAGE_VARIABLES", "(nivel pipeline)", "tuSecret")],
            values={"tuSecret": "nuevo"}, release=release)
        r = a["rules"][0]
        assert r["action"] == "update" and r["scope"] == "release"
        assert "solo en el release" in r["note"]

    def test_update_inexistente_en_ambos_va_a_manual(self):
        a = rem.build_actionables(self._def_vacia(), [
            _v("STAGE_VARIABLES", "(nivel pipeline)", "ghost")],
            values={"ghost": "x"}, release={"variables": {}})
        assert a["rules"] == [] and len(a["manual"]) == 1

    def test_secret_existe_solo_en_release_env(self):
        release = {"environments": [{"name": "Production", "variables": {
            "ksa": {"value": "v1"}}}]}
        a = rem.build_actionables(self._def_vacia(), [
            _v("RULE_1_SECRET", "Production", "ksa")], release=release)
        r = a["rules"][0]
        assert r["action"] == "update" and r["isSecret"] is True
        assert r["value"] == "v1"
        assert "solo en el release" in r["note"]

    def test_secret_valor_vacio_toma_el_del_release(self):
        definition = {"environments": [{"name": "Prod", "variables": {
            "ksa": {"value": ""}}}]}
        release = {"environments": [{"name": "Prod", "variables": {
            "ksa": {"value": "real"}}}]}
        a = rem.build_actionables(definition, [
            _v("RULE_1_SECRET", "Prod", "ksa")], release=release)
        r = a["rules"][0]
        assert r["value"] == "real" and r["isSecret"] is True

    def test_secret_inexistente_en_ambos_va_a_manual(self):
        a = rem.build_actionables(self._def_vacia(), [
            _v("RULE_1_SECRET", "Production", "ghost")],
            release={"environments": []})
        assert a["rules"] == [] and len(a["manual"]) == 1


class TestRunFlow:
    def _setup(self, monkeypatch, tmp_path):
        monkeypatch.setattr(rem, "get_azdo_params", lambda a: ("o", "p", "pat"))
        monkeypatch.setattr(rem, "AzdoClient", lambda *a: _fake_discovery())
        monkeypatch.setattr(rem, "resolve_outcome_dir", lambda: tmp_path)

    def test_solo_template_sin_aplicar(self, monkeypatch, tmp_path):
        self._setup(monkeypatch, tmp_path)
        applied = []
        monkeypatch.setattr(rem, "apply_template",
                            lambda *a, **k: applied.append(1) or 0)
        # Enter en confirmación de resumen + "1" solo template en menú final
        inputs = iter(["", "", "1"])
        monkeypatch.setattr("builtins.input", lambda p="": next(inputs))
        args = _Args()
        rc = rem.run_flow(args, interactive=True)
        assert rc == 0 and applied == []
        assert list(tmp_path.glob("pipe_cd_inspection_fix_1837_*.yaml"))

    def test_apply_invoca_updater(self, monkeypatch, tmp_path):
        self._setup(monkeypatch, tmp_path)
        applied = []
        monkeypatch.setattr(rem, "apply_template",
                            lambda *a, **k: applied.append(k) or 0)
        args = _Args()
        args.apply = True
        rc = rem.run_flow(args, interactive=False)
        assert rc == 0 and applied and applied[0]["dry_run"] is False

    def test_flujo_tbd_sin_prompts(self, monkeypatch, tmp_path):
        self._setup(monkeypatch, tmp_path)
        monkeypatch.setattr(rem, "apply_template", lambda *a, **k: 0)
        inputs = iter(["", "", "1"])
        monkeypatch.setattr("builtins.input", lambda p="": next(inputs))
        args = _Args()
        args.tbd = True
        rc = rem.run_flow(args, interactive=True)
        assert rc == 0
        tpl = list(tmp_path.glob("*.yaml"))[0]
        assert "isSecret" in tpl.read_text(encoding="utf-8")

    def test_sin_violaciones_retorna_0(self, monkeypatch, tmp_path):
        self._setup(monkeypatch, tmp_path)
        empty = _fake_discovery()
        empty._logs = "sin violaciones\n"
        monkeypatch.setattr(rem, "AzdoClient", lambda *a: empty)
        monkeypatch.setattr("builtins.input", lambda p="": "")
        args = _Args()
        assert rem.run_flow(args, interactive=True) == 0
        assert not list(tmp_path.glob("*.yaml"))

    def test_reload_restaura_ajustes(self, monkeypatch, tmp_path):
        """[r] recarga los ajustes candidatos tras una edición errónea."""
        self._setup(monkeypatch, tmp_path)
        # 2 violaciones RULE_1_SECRET → 2 reglas update
        client = _fake_discovery()
        client._definition["environments"].append(
            {"id": 3, "name": "QA",
             "variables": {"ksa": {"value": "v2"}}})
        client._logs += ("##[error] [HIGH] RULE_1_SECRET\n##[error]   "
                         "Environment: 'QA'\n##[error]   Variable: 'ksa'\n"
                         "##[error]   ksa not marked secret\n\n")
        monkeypatch.setattr(rem, "AzdoClient", lambda *a: client)
        monkeypatch.setattr(rem, "apply_template", lambda *a, **k: 0)
        # e → descarta la 1ra (i), conserva la 2da → r recarga → Enter → 1
        inputs = iter(["", "e", "i", "", "r", "", "1"])
        monkeypatch.setattr("builtins.input", lambda p="": next(inputs))
        args = _Args()
        assert rem.run_flow(args, interactive=True) == 0
        tpl = yaml.safe_load(
            list(tmp_path.glob("*.yaml"))[0].read_text(encoding="utf-8"))
        assert len(tpl["update"]["variables"]) == 2  # recargadas

    def test_target_release_usa_release_descubierto(self, monkeypatch,
                                                    tmp_path):
        self._setup(monkeypatch, tmp_path)
        calls = []
        monkeypatch.setattr(
            rem, "apply_release_template",
            lambda *a, **k: calls.append((a, k)) or 0)
        monkeypatch.setattr(rem, "apply_template", lambda *a, **k: 0)
        args = _Args()
        args.apply = True
        args.target = "release"
        assert rem.run_flow(args, interactive=False) == 0
        a, k = calls[0]
        assert a[1] == "61141"            # release descubierto por defecto
        assert k["dry_run"] is False
        assert list(tmp_path.glob("release_inspection_fix_61141_*.yaml"))

    def test_target_both_aplica_definicion_y_release(self, monkeypatch,
                                                     tmp_path):
        self._setup(monkeypatch, tmp_path)
        rel_calls, def_calls = [], []
        monkeypatch.setattr(rem, "apply_release_template",
                            lambda *a, **k: rel_calls.append(1) or 0)
        monkeypatch.setattr(rem, "apply_template",
                            lambda *a, **k: def_calls.append(1) or 0)
        args = _Args()
        args.apply = True
        args.target = "both"
        assert rem.run_flow(args, interactive=False) == 0
        assert def_calls == [1] and rel_calls == [1]

    def test_menu_opcion_5_aplica_release_default(self, monkeypatch,
                                                  tmp_path):
        self._setup(monkeypatch, tmp_path)
        calls = []
        monkeypatch.setattr(
            rem, "apply_release_template",
            lambda *a, **k: calls.append((a, k)) or 0)
        monkeypatch.setattr(rem, "redeploy_stage", lambda *a, **k: 0)
        # Enter gen. template → "5" → Enter release default → "n" sin
        # redeploy → "0" salir del bucle de aplicación
        inputs = iter(["", "", "5", "", "n", "0"])
        monkeypatch.setattr("builtins.input", lambda p="": next(inputs))
        args = _Args()
        assert rem.run_flow(args, interactive=True) == 0
        a, k = calls[0]
        assert a[1] == "61141" and k["dry_run"] is False

    def test_menu_opcion_5_release_especifico(self, monkeypatch, tmp_path):
        self._setup(monkeypatch, tmp_path)
        calls = []
        monkeypatch.setattr(
            rem, "apply_release_template",
            lambda *a, **k: calls.append((a, k)) or 0)
        monkeypatch.setattr(rem, "redeploy_stage", lambda *a, **k: 0)
        inputs = iter(["", "", "5", "99999", "n", "0"])
        monkeypatch.setattr("builtins.input", lambda p="": next(inputs))
        args = _Args()
        assert rem.run_flow(args, interactive=True) == 0
        assert calls[0][0][1] == "99999"  # release específico

    def test_menu_vuelve_tras_aplicar_definicion(self, monkeypatch,
                                                 tmp_path):
        """Tras aplicar a la definición el menú de aplicación reaparece."""
        self._setup(monkeypatch, tmp_path)
        calls = []
        monkeypatch.setattr(rem, "apply_template",
                            lambda *a, **k: calls.append(1) or 0)
        # "3" aplica definición → menú reaparece → "0" sale
        inputs = iter(["", "", "3", "0"])
        monkeypatch.setattr("builtins.input", lambda p="": next(inputs))
        args = _Args()
        assert rem.run_flow(args, interactive=True) == 0
        assert calls == [1]

    def test_redeploy_tras_aplicar_release(self, monkeypatch, tmp_path):
        """Tras aplicar al release, 's' dispara el redeploy del stage."""
        self._setup(monkeypatch, tmp_path)
        redeploys = []
        monkeypatch.setattr(rem, "apply_release_template",
                            lambda *a, **k: 0)
        monkeypatch.setattr(rem, "redeploy_stage",
                            lambda *a, **k: redeploys.append(a) or 0)
        inputs = iter(["", "", "5", "", "s", "0"])
        monkeypatch.setattr("builtins.input", lambda p="": next(inputs))
        args = _Args()
        assert rem.run_flow(args, interactive=True) == 0
        assert redeploys[0][1] == "61141"
        assert redeploys[0][2] == rem.DEFAULT_STAGE

    def test_cli_redeploy_flag(self, monkeypatch, tmp_path):
        self._setup(monkeypatch, tmp_path)
        redeploys = []
        monkeypatch.setattr(rem, "apply_release_template",
                            lambda *a, **k: 0)
        monkeypatch.setattr(rem, "redeploy_stage",
                            lambda *a, **k: redeploys.append(a) or 0)
        args = _Args()
        args.apply = True
        args.target = "release"
        args.redeploy = True
        assert rem.run_flow(args, interactive=False) == 0
        assert redeploys[0][1] == "61141"

    def test_redeploy_stage_hace_patch_environment(self):
        class C:
            base = "https://vsrm/o/p/_apis/release"

            def __init__(self):
                self.patched = None

            def get(self, url, raw=False, params=None):
                return {"environments": [
                    {"id": 7, "name": "SCM Inspection"}]}

            def patch(self, url, payload, params=None):
                self.patched = (url, payload)
                return {}
        c = C()
        assert rem.redeploy_stage(c, "61062", "SCM Inspection") == 0
        url, payload = c.patched
        assert "releases/61062/environments/7" in url
        assert payload == {"status": "inProgress"}

    def test_prompt_release_id_interactivo(self, monkeypatch, tmp_path):
        """El modo interactivo pregunta Release ID tras el Definition ID y
        lo pasa a discover(); Enter = último run."""
        self._setup(monkeypatch, tmp_path)
        seen = {}

        def fake_discover(client, did, stage, rid):
            seen["rid"] = rid
            return {"definition": {"name": "p", "environments": []},
                    "release": {"id": 1, "name": "R"},
                    "env": {"name": "SCM Inspection"}, "violations": []}
        monkeypatch.setattr(rem, "discover", fake_discover)
        inputs = iter(["61077"])
        monkeypatch.setattr("builtins.input", lambda p="": next(inputs))
        args = _Args()
        assert rem.run_flow(args, interactive=True) == 0
        assert seen["rid"] == "61077"

    def test_prompt_release_id_invalido_usa_ultimo(self, monkeypatch,
                                                   tmp_path):
        self._setup(monkeypatch, tmp_path)
        seen = {}

        def fake_discover(client, did, stage, rid):
            seen["rid"] = rid
            return {"definition": {"name": "p", "environments": []},
                    "release": {"id": 1, "name": "R"},
                    "env": {"name": "SCM Inspection"}, "violations": []}
        monkeypatch.setattr(rem, "discover", fake_discover)
        inputs = iter(["abc"])
        monkeypatch.setattr("builtins.input", lambda p="": next(inputs))
        args = _Args()
        assert rem.run_flow(args, interactive=True) == 0
        assert seen["rid"] == ""  # no numérico → último run


class TestCsvActionColumn:
    SCRIPT = Path(__file__).parent.parent.parent / "terminal" / \
        "azdo_check_scm_inspection" / "inspection_errors.sh"

    def test_header_csv_incluye_action(self):
        content = self.SCRIPT.read_text(encoding="utf-8")
        headers = [l for l in content.split("\n")
                   if "SEVERITY,RULE,ENVIRONMENT" in l]
        assert len(headers) >= 2
        assert all(",ACTION," in h for h in headers)

    def test_funcion_action_for_existe(self):
        content = self.SCRIPT.read_text(encoding="utf-8")
        assert "ACTION" in content
        assert "mark-secret" in content
        assert "add-missing" in content
        assert "define-or-remove" in content
