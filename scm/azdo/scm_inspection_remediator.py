#!/usr/bin/env python3
"""
SCM Inspection Remediator — AzDO

Descubre las violaciones del stage "SCM Inspection" de un pipeline CD
(misma lógica que scm/terminal/azdo_check_scm_inspection/inspection_errors.sh),
convierte cada violación accionable en una regla de variables y genera un
template pipe_cd_inspection_fix_<defId>_<ts>.yaml en outcome/.

El template se aplica con el motor existente:
    python -m scm.azdo.pipeline_updater.pipeline_updater \
        --definition-ids <id> --template <tpl> [--dry-run]

Accionables soportados:
  - RULE_1_SECRET            → isSecret: true en el stage afectado
  - STAGE_VARIABLES pipeline → valor faltante a nivel release (pide valor)
  - STAGE_VARIABLES paridad  → add con el valor copiado del stage origen
  - STAGE_VARIABLES contenido→ update con el valor hallado en otro stage

Uso:
    python scm_inspection_remediator.py --interactive
    python scm_inspection_remediator.py --definition-id 1837 --dry-run
    python scm_inspection_remediator.py --definition-id 1837 --apply
"""

import argparse
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml

BASE_DIR = Path(__file__).resolve().parent          # scm/azdo
SCM_ROOT = BASE_DIR.parent                          # scm/
REPO_ROOT = SCM_ROOT.parent                         # repo raíz
CONFIG_FILE = SCM_ROOT / "config.json"

DEFAULT_STAGE = "SCM Inspection"


# ---------------------------------------------------------------------------
# Config y outcome
# ---------------------------------------------------------------------------

def load_config() -> dict:
    import json
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def resolve_outcome_dir() -> Path:
    """DEVSECOPS_OUTPUT_DIR > config.json global.output_dir > scm/outcome."""
    import json
    import os
    env = os.environ.get("DEVSECOPS_OUTPUT_DIR")
    if env:
        out = Path(env)
    else:
        out = Path("outcome")
        if CONFIG_FILE.exists():
            try:
                out = Path(json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                           .get("global", {}).get("output_dir") or "outcome")
            except Exception:
                out = Path("outcome")
        if not out.is_absolute():
            out = SCM_ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    return out.resolve()


def get_azdo_params(args) -> tuple:
    cfg = load_config().get("azdo", {})
    org = args.org or cfg.get("organization") or \
        (cfg.get("organization_url") or "").rstrip("/").split("/")[-1]
    project = args.project or cfg.get("project", "")
    pat = args.pat or cfg.get("pat", "")
    if not org or not project or not pat:
        sys.exit("ERROR: faltan credenciales — defina azdo.organization/project/pat "
                 "en scm/config.json o use --org/--project/--pat.")
    return org, project, pat


# ---------------------------------------------------------------------------
# API Azure DevOps (Release)
# ---------------------------------------------------------------------------

class AzdoClient:
    def __init__(self, org: str, project: str, pat: str):
        self.base = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release"
        self.session = requests.Session()
        self.session.auth = ("", pat)
        self.session.headers["Accept"] = "application/json"

    def get(self, url: str, raw: bool = False, params: dict = None):
        for attempt in range(4):
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.text if raw else resp.json()
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = int(resp.headers.get("Retry-After", (attempt + 1) * 2))
                print(f"  HTTP {resp.status_code} — reintentando en {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code in (203, 401):
                sys.exit("ERROR: autenticación fallida (verifique azdo.pat, "
                         "scope 'Release (Read)').")
            sys.exit(f"ERROR: HTTP {resp.status_code} — {url}\n{resp.text[:500]}")
        sys.exit(f"ERROR: agotados los reintentos para {url}")


# ---------------------------------------------------------------------------
# Descubrimiento (equivalente a inspection_errors.sh)
# ---------------------------------------------------------------------------

_LOG_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z ?")
_LOG_LINE = re.compile(r"^##\[(warning|error)\](.*)$")
_LOG_HEAD = re.compile(r"^\s*\S*\s*\[([A-Z]+)\]\s+([A-Z][A-Z0-9_]*)\s*$")
_KV = re.compile(r"^([A-Za-z][A-Za-z_-]*):\s*(.*)$")


def parse_log(text: str, task_name: str) -> list:
    """Convierte un task log en lista de violaciones (mismo formato que
    PARSE_LOG del script bash)."""
    violations, cur = [], None

    def finish():
        nonlocal cur
        if cur:
            violations.append(cur)
            cur = None

    for raw in text.split("\n"):
        line = _LOG_TS.sub("", raw.rstrip("\r"))
        m = _LOG_LINE.match(line)
        if not m:
            finish()
            continue
        body = m.group(2)
        head = _LOG_HEAD.match(body)
        if head:
            finish()
            cur = {"severity": head.group(1), "rule": head.group(2),
                   "environment": "", "variable": "", "reason": "",
                   "detail": "", "task": task_name}
            continue
        if cur is None or not body.startswith((" ", "\t")):
            finish()
            continue
        b = body.strip()
        kv = _KV.match(b)
        if kv and kv.group(1).lower() in ("environment", "variable", "reason"):
            cur[kv.group(1).lower()] = kv.group(2).strip().strip("'")
        elif b:
            cur["detail"] = b if not cur["detail"] else cur["detail"] + " | " + b
    finish()
    return violations


def discover(client: AzdoClient, definition_id: str, stage_name: str,
             release_id: str = "") -> dict:
    """Devuelve {definition, release, env_json, violations} del último run del
    stage (o del release indicado)."""
    definition = client.get(f"{client.base}/definitions/{definition_id}",
                            params={"api-version": "7.1"})
    stage_env = next(
        (e for e in definition.get("environments", [])
         if e.get("name", "").lower() == stage_name.lower()), None)
    if not stage_env:
        stages = ", ".join(e.get("name", "?") for e in definition.get("environments", []))
        sys.exit(f"ERROR: el pipeline no tiene stage '{stage_name}'. Stages: {stages}")

    if not release_id:
        deployments = client.get(
            f"{client.base}/deployments",
            params={"api-version": "7.1", "definitionId": definition_id,
                    "definitionEnvironmentId": stage_env["id"],
                    "queryOrder": "descending", "$top": 10})
        for d in deployments.get("value", []):
            if d.get("deploymentStatus") != "notDeployed":
                release_id = str(d.get("release", {}).get("id", ""))
                break
        if not release_id:
            sys.exit(f"El stage '{stage_name}' nunca corrió en este pipeline.")

    release = client.get(f"{client.base}/releases/{release_id}",
                         params={"api-version": "7.1"})
    env_json = next(
        (e for e in release.get("environments", [])
         if e.get("name", "").lower() == stage_name.lower()), None)
    if not env_json:
        sys.exit(f"ERROR: el release {release_id} no tiene stage '{stage_name}'.")

    steps = env_json.get("deploySteps") or []
    step = max(steps, key=lambda s: s.get("attempt", 0)) if steps else {}
    tasks = []
    for ph in step.get("releaseDeployPhases", []):
        for job in ph.get("deploymentJobs", []):
            for t in job.get("tasks", []):
                if t.get("status") in ("skipped", "pending"):
                    continue
                log_url = t.get("logUrl") or (
                    f"{client.base}/releases/{release_id}/environments/"
                    f"{env_json['id']}/deployPhases/{ph.get('id')}/tasks/"
                    f"{t.get('id')}/logs?api-version=7.1")
                tasks.append((t.get("name", "task"), log_url))

    violations = []
    for name, url in tasks:
        try:
            violations.extend(parse_log(client.get(url, raw=True), name))
        except SystemExit:
            raise
        except Exception as e:
            print(f"  ⚠ No se pudo leer log de '{name}': {e}")

    # dedup + orden por severidad
    rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    seen, unique = set(), []
    for v in sorted(violations,
                    key=lambda v: (rank.get(v["severity"], 5), v["rule"],
                                   v["environment"])):
        key = (v["severity"], v["rule"], v["environment"], v["variable"],
               v["reason"], v["detail"])
        if key not in seen:
            seen.add(key)
            unique.append(v)

    return {"definition": definition, "release": release,
            "env": env_json, "violations": unique}


# ---------------------------------------------------------------------------
# Accionables → reglas de variables del template
# ---------------------------------------------------------------------------

_DETAIL_SRC = re.compile(r"([\w.\-]+) \(de ([^)]+)\)")


def build_actionables(definition: dict, violations: list,
                      values: dict = None) -> dict:
    """Convierte violaciones en reglas `update.variables` del template.

    Returns {"rules": [...], "manual": [...], "pending": {...}, "summary": [...]}
    `values` permite inyectar valores para variables 'needs-value' (no interactivo).
    `pending` = {var: {"scope": ..., "stages": [...]}} — variables que requieren
    valor (default "TBD" o capturadas con collect_pending_values/--tbd).
    """
    values = values or {}
    envs = {e["name"]: e for e in definition.get("environments", [])}

    def env_vars(stage):
        return envs.get(stage, {}).get("variables") or {}

    def find_value(var, exclude=None):
        for sname, env in envs.items():
            if exclude and sname == exclude:
                continue
            v = (env.get("variables") or {}).get(var)
            if v and v.get("value") not in (None, ""):
                return v["value"], sname
        dv = (definition.get("variables") or {}).get(var)
        if dv and dv.get("value") not in (None, ""):
            return dv["value"], "(pipeline)"
        return None, None

    rules, manual, summary, pending = [], [], [], {}

    def need_value(var, stage, scope):
        p = pending.setdefault(var, {"scope": scope, "stages": []})
        if stage and stage not in p["stages"]:
            p["stages"].append(stage)

    def add_rule(var, stage, scope, action, value, secret=False, note=""):
        rule = {"name": var, "action": action, "scope": scope, "value": value}
        if scope == "environment":
            rule["stage"] = stage
        if secret:
            rule["isSecret"] = True
        rules.append(rule)
        summary.append(f"  [{action}] {var} @ {scope}:{stage or 'release'}"
                       + (" (isSecret)" if secret else "")
                       + (f" — {note}" if note else ""))

    for v in violations:
        rule_name, env_name = v["rule"], v["environment"]
        reason, detail = v.get("reason", ""), v.get("detail", "")
        var_field = v.get("variable", "")

        if rule_name == "RULE_1_SECRET":
            var = var_field.split(",")[0].strip()
            current = env_vars(env_name).get(var, {})
            if current.get("value") not in (None, ""):
                add_rule(var, env_name, "environment", "update",
                         current["value"], secret=True, note="marcar secreta")
            else:
                manual.append(f"{var} @ {env_name}: marcar como secreta en la UI "
                              f"(valor actual no legible/ya secreto)")
            continue

        if rule_name != "STAGE_VARIABLES":
            continue

        if env_name in ("", "(nivel pipeline)"):
            for var in [x.strip() for x in var_field.split(",") if x.strip()]:
                val = values.get(var)
                if val is not None:
                    add_rule(var, "", "release", "update", val,
                             note="valor definido por usuario")
                else:
                    need_value(var, "", "release")
                    manual.append(f"{var} @ pipeline: definir valor o eliminarla")
            continue

        if "paridad" in reason:
            # detail: "...: name (de SrcStage), name2 (de SrcStage)"
            pairs = _DETAIL_SRC.findall(detail)
            for var, src in pairs:
                val, src_found = find_value(var)
                if val is not None:
                    add_rule(var, env_name, "environment", "add", val,
                             note=f"copiado de {src_found}")
                else:
                    val = values.get(var)
                    if val is not None:
                        add_rule(var, env_name, "environment", "add", val,
                                 note="valor definido por usuario")
                    else:
                        need_value(var, env_name, "environment")
                        manual.append(f"{var} @ {env_name} (de {src}): "
                                      f"sin valor fuente — definir a mano")
            continue

        if "contenido" in reason:
            for var in [x.strip() for x in var_field.split(",") if x.strip()]:
                val, src = find_value(var, exclude=env_name)
                if val is not None:
                    add_rule(var, env_name, "environment", "update", val,
                             note=f"copiado de {src}")
                elif var in values:
                    add_rule(var, env_name, "environment", "update",
                             values[var], note="valor definido por usuario")
                else:
                    need_value(var, env_name, "environment")
                    manual.append(f"{var} @ {env_name}: definir valor "
                                  f"(sin fuente en otros stages)")

    return {"rules": rules, "manual": manual,
            "pending": pending, "summary": summary}


DEFAULT_PENDING_VALUE = "TBD"


def collect_pending_values(actionables: dict, values: dict = None,
                           prompt_fn=input,
                           default: str = DEFAULT_PENDING_VALUE) -> dict:
    """Ciclo sobre todas las variables pendientes: Enter = 'TBD',
    's'/'skip'/'-' = dejar manual. Retorna dict de valores resueltos."""
    values = dict(values or {})
    pending = actionables.get("pending", {})
    if not pending:
        return values
    print("\nVariables sin valor fuente — ingrese el valor "
          f"(Enter = '{default}', 's' = dejar manual):")
    for var, info in pending.items():
        if var in values:
            continue
        scopes = ", ".join(info["stages"]) or info["scope"]
        val = prompt_fn(
            f"  Valor para '{var}' ({scopes}) [Enter={default}]: ").strip()
        if val.lower() in ("s", "skip", "-"):
            continue
        values[var] = val or default
    return values


def fill_pending_default(actionables: dict, values: dict,
                         default: str = DEFAULT_PENDING_VALUE) -> dict:
    """No interactivo: todas las pendientes toman el valor default (--tbd)."""
    values = dict(values or {})
    for var in actionables.get("pending", {}):
        values.setdefault(var, default)
    return values


# ---------------------------------------------------------------------------
# Template + aplicación
# ---------------------------------------------------------------------------

def generate_template(rules: list, definition_id: str, pipeline_name: str,
                      out_dir: Path = None) -> Path:
    out_dir = out_dir or resolve_outcome_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"pipe_cd_inspection_fix_{definition_id}_{ts}.yaml"
    template = {
        "metadata": {
            "name": f"SCM Inspection Fix — {pipeline_name} ({definition_id})",
            "version": "1.0",
            "description": "Corrige violaciones del stage SCM Inspection: "
                           "secrets, paridad de variables y valores vacíos. "
                           "Generado por scm_inspection_remediator.",
            "created_at": ts,
        },
        "search": {"stages": []},
        "update": {"variables": rules},
        "options": {"dry_run": False, "rollback_on_error": True,
                    "parallel_workers": 5},
    }
    path.write_text(yaml.safe_dump(template, allow_unicode=True,
                                   sort_keys=False), encoding="utf-8")
    return path


def apply_template(template_path: Path, definition_id: str,
                   org: str, project: str, pat: str, dry_run: bool) -> int:
    """Aplica el template llamando directamente a la opción 41
    (pipeline_updater) existente."""
    cmd = [sys.executable, "-m",
           "scm.azdo.pipeline_updater.pipeline_updater",
           "--definition-ids", str(definition_id),
           "--template", str(template_path),
           "--org", org, "--project", project, "--pat", pat]
    if dry_run:
        cmd.append("--dry-run")
    print(f"\n▶ Ejecutando: {' '.join(cmd[:3])} ...")
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------

def show_plan(discovery: dict, actionables: dict, definition_id: str):
    definition, release = discovery["definition"], discovery["release"]
    print("\n" + "=" * 70)
    print(f"Pipeline : {definition.get('name')} (ID {definition_id})")
    print(f"Release  : {release.get('name')} (ID {release.get('id')})")
    print(f"Stage    : {discovery['env'].get('name')} — "
          f"status: {discovery['env'].get('status', '-')}")
    print("=" * 70)

    violations = discovery["violations"]
    if not violations:
        print("✅ Sin violaciones en el último run del stage.")
        return
    print(f"Violaciones: {len(violations)}")
    for v in violations:
        print(f"  [{v['severity']}] {v['rule']} — {v['environment'] or 'pipeline'}"
              + (f" ({v['variable'][:60]})" if v.get("variable") else ""))

    if actionables["summary"]:
        print("\nAcciones que aplicará el template:")
        for s in actionables["summary"]:
            print(s)
    if actionables["manual"]:
        print("\n⚠ Requieren intervención manual (sin valor fuente):")
        for m in actionables["manual"]:
            print(f"  - {m}")


def run_flow(args, interactive: bool) -> int:
    org, project, pat = get_azdo_params(args)
    client = AzdoClient(org, project, pat)

    definition_id = args.definition_id
    if not definition_id:
        definition_id = input("Definition ID del pipeline CD: ").strip()
        if not definition_id:
            print("Se requiere el definition ID.")
            return 1

    values = {}
    for item in args.set or []:
        if "=" in item:
            k, _, val = item.partition("=")
            values[k.strip()] = val

    print(f"\nDescubriendo violaciones del stage '{args.stage}'...")
    discovery = discover(client, definition_id, args.stage, args.release_id)
    actionables = build_actionables(discovery["definition"],
                                    discovery["violations"], values)
    show_plan(discovery, actionables, definition_id)

    if not actionables["rules"] and not actionables["manual"]:
        return 0

    # Valores pendientes: --tbd (no interactivo) o ciclo con default TBD
    if actionables["pending"]:
        if args.tbd:
            values = fill_pending_default(actionables, values)
        elif interactive:
            values = collect_pending_values(actionables, values)
        if values:
            actionables = build_actionables(discovery["definition"],
                                            discovery["violations"], values)

    if not actionables["rules"]:
        print("\nNo hay acciones automáticas — solo pendientes manuales.")
        return 0

    template = generate_template(actionables["rules"], definition_id,
                                 discovery["definition"].get("name", ""))
    print(f"\n📄 Template generado: {template}")

    if args.apply or args.dry_run:
        rc = apply_template(template, definition_id, org, project, pat,
                            dry_run=args.dry_run and not args.apply)
        print("\n✅ Aplicado." if rc == 0 else f"\n✗ Falló (exit {rc}).")
        return rc

    print("\n[1] Solo template (aplicar luego con opción 41)")
    print("[2] Dry-run (simulación)")
    print("[3] Aplicar")
    print("[0] Salir")
    choice = input("Seleccione: ").strip()
    if choice == "2":
        rc = apply_template(template, definition_id, org, project, pat,
                            dry_run=True)
        return rc
    if choice == "3":
        rc = apply_template(template, definition_id, org, project, pat,
                            dry_run=False)
        print("\n✅ Aplicado." if rc == 0 else f"\n✗ Falló (exit {rc}).")
        return rc
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="SCM Inspection Remediator — descubre violaciones y "
                    "genera/aplica template de corrección")
    parser.add_argument("--interactive", action="store_true",
                        help="Menú interactivo (pregunta valores pendientes)")
    parser.add_argument("--definition-id", default="",
                        help="ID de la definición del pipeline CD")
    parser.add_argument("--stage", default=DEFAULT_STAGE,
                        help=f"Stage a inspeccionar (default: {DEFAULT_STAGE})")
    parser.add_argument("--release-id", default="",
                        help="Release específico (default: último run del stage)")
    parser.add_argument("--org", default=None)
    parser.add_argument("--project", default=None)
    parser.add_argument("--pat", default=None)
    parser.add_argument("--set", action="append",
                        help="Valor para variable pendiente: NAME=VALUE (repetible)")
    parser.add_argument("--tbd", action="store_true",
                        help="Rellenar todas las pendientes con 'TBD' "
                             "(no interactivo)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generar template y ejecutar en modo simulación")
    parser.add_argument("--apply", action="store_true",
                        help="Generar template y aplicar cambios")
    args = parser.parse_args()

    interactive = args.interactive or (
        sys.stdin.isatty() and not args.apply and not args.dry_run)
    sys.exit(run_flow(args, interactive))


if __name__ == "__main__":
    main()
