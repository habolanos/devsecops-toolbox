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

Además de la definición, los ajustes pueden aplicarse sobre un Release
(instancia) — el descubierto por defecto o uno específico — generando un
template release_inspection_fix_<relId>_<ts>.yaml y aplicándolo con el
engine existente de Update Release (opción 42, templates release_*):
--target release|both. Tras aplicar puede dispararse el redeploy del
stage inspeccionado (--redeploy).

Accionables soportados:
  - RULE_1_SECRET            → isSecret: true en el stage afectado
  - STAGE_VARIABLES pipeline → valor a nivel release (pide valor / TBD / remove)
  - STAGE_VARIABLES paridad  → add con el valor copiado del stage origen
  - STAGE_VARIABLES contenido→ update con el valor hallado en otro stage
  - Pendientes               → valor | 'TBD' | eliminar (e) | ignorar (i)

Uso:
    python scm_inspection_remediator.py --interactive
    python scm_inspection_remediator.py --definition-id 1837 --dry-run
    python scm_inspection_remediator.py --definition-id 1837 --apply
    python scm_inspection_remediator.py --definition-id 1837 --apply --target both
    python scm_inspection_remediator.py --definition-id 1837 --apply \
        --target release --release-id 61062
    python scm_inspection_remediator.py --definition-id 1837 --tbd
    python scm_inspection_remediator.py --definition-id 1837 --remove tuSecret
    python scm_inspection_remediator.py --definition-id 1837 --set region=us-central1
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
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

BASE_DIR = Path(__file__).resolve().parent          # scm/azdo
SCM_ROOT = BASE_DIR.parent                          # scm/
REPO_ROOT = SCM_ROOT.parent                         # repo raíz
CONFIG_FILE = SCM_ROOT / "config.json"

DEFAULT_STAGE = "SCM Inspection"
DEFAULT_PENDING_VALUE = "TBD"

console = Console()

# Fallback ASCII en consolas legacy Windows (cp1252 no soporta emoji/≠/→)
_UTF8 = "utf" in ((getattr(sys.stdout, "encoding", "") or "").lower())
ICON_SECRET = "🔒" if _UTF8 else "[SECRET]"
ICON_UNSECRET = "🔓" if _UTF8 else "[NO-SECRET]"
ICON_WARN = "⚠" if _UTF8 else "!"
ICON_OK = "✅" if _UTF8 else "[OK]"
ICON_DOC = "📄" if _UTF8 else ">>"
ICON_RUN = "▶" if _UTF8 else ">"

SEV_STYLE = {"CRITICAL": "bold white on red", "HIGH": "bold red",
             "MEDIUM": "yellow", "LOW": "cyan", "INFO": "dim"}
ACTION_STYLE = {"add": "bold green", "update": "bold yellow",
                "remove": "bold red"}


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
        console.print("[bold red]ERROR: faltan credenciales[/] — defina "
                      "azdo.organization/project/pat en scm/config.json "
                      "o use --org/--project/--pat.")
        sys.exit(1)
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

    def _send(self, method: str, url: str, params: dict = None,
              payload: dict = None, raw: bool = False, timeout: int = 60):
        for attempt in range(4):
            resp = self.session.request(method, url, params=params,
                                        json=payload, timeout=timeout)
            if resp.status_code == 200:
                return resp.text if raw else resp.json()
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = int(resp.headers.get("Retry-After", (attempt + 1) * 2))
                console.print(f"  [yellow]HTTP {resp.status_code} — "
                              f"reintentando en {wait}s...[/]")
                time.sleep(wait)
                continue
            if resp.status_code in (203, 401):
                sys.exit("ERROR: autenticación fallida (verifique azdo.pat, "
                         "scope 'Release (Read, write & execute)').")
            sys.exit(f"ERROR: HTTP {resp.status_code} — {url}\n"
                     f"{resp.text[:500]}")
        sys.exit(f"ERROR: agotados los reintentos para {url}")

    def get(self, url: str, raw: bool = False, params: dict = None):
        return self._send("GET", url, params=params, raw=raw, timeout=30)

    def patch(self, url: str, payload: dict, params: dict = None):
        """PATCH con la misma política de reintentos que get()."""
        return self._send("PATCH", url, params=params, payload=payload)


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
            console.print(f"  [yellow]{ICON_WARN} No se pudo leer log de "
                          f"'{name}': {e}[/]")

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


def _env_token(name: str) -> str:
    """Normaliza el ambiente implícito en el nombre del stage."""
    n = name.lower()
    if "prod" in n:
        return "prod"
    if "stg" in n or "stag" in n:
        return "stg"
    if "qa" in n:
        return "qa"
    if "dev" in n or "develop" in n:
        return "dev"
    return ""


def _env_mismatch(src_stage: str, dst_stage: str) -> str:
    """Advierte si el valor se copia entre ambientes distintos
    (ej. dev → Production). Retorna texto de warning o ''."""
    a, b = _env_token(src_stage), _env_token(dst_stage)
    if a and b and a != b:
        return f"{ICON_WARN} origen '{src_stage}' es ambiente '{a}' " \
               f"!= destino '{b}'"
    return ""


def build_actionables(definition: dict, violations: list,
                      values: dict = None, removes: set = None,
                      release: dict = None) -> dict:
    """Convierte violaciones en reglas `update.variables` del template.

    Returns {"rules": [...], "manual": [...], "pending": {...}, "summary": [...]}
    `values` permite inyectar valores para variables pendientes.
    `removes` = set de variables a eliminar (action: remove) donde existan.
    `release` = instancia inspeccionada — sus variables son la fuente real del
    inspector: una variable puede existir solo en el release (snapshot) aunque
    falte en la definición; remove/update sobre ella aplica al release
    (engine opción 42) y es no-op en la definición.
    `pending` = {var: {"scope": ..., "stages": [...]}} — variables que requieren
    valor (default "TBD" o capturadas con collect_pending_values/--tbd).
    """
    values = values or {}
    removes = set(removes or ())
    envs = {e["name"]: e for e in definition.get("environments", [])}
    rel_envs = {e.get("name", ""): e
                for e in (release or {}).get("environments", [])}
    rel_vars = (release or {}).get("variables") or {}
    # Variables que el reporte marcó como secretas en cualquier stage:
    # si las agregamos por paridad en otro stage, deben ir con isSecret.
    secret_vars = {v.get("variable", "").split(",")[0].strip()
                   for v in violations if v.get("rule") == "RULE_1_SECRET"}

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

    def rel_var(stage, scope, var):
        """Entry de la variable en la instancia del release (o None)."""
        if scope == "environment":
            return (rel_envs.get(stage, {}).get("variables") or {}).get(var)
        return rel_vars.get(var)

    def add_rule(var, stage, scope, action, value=None, secret=False, note=""):
        # Ajustar la acción a lo que el updater realmente hará
        vars_map = env_vars(stage) if scope == "environment" \
            else (definition.get("variables") or {})
        exists = var in vars_map
        cur = vars_map.get(var) or {}
        rel_cur = rel_var(stage, scope, var)
        in_release = rel_cur is not None
        loc = stage or "release"

        if action == "remove" and not exists:
            if in_release:
                # Existe solo en la instancia: el engine de release la
                # elimina; en la definición es no-op.
                note = ((note + " | ") if note else "") + \
                    "existe solo en el release — se elimina ahí"
                rule = {"name": var, "action": "remove", "scope": scope}
                if scope == "environment":
                    rule["stage"] = stage
                rule["note"] = note
                rules.append(rule)
                summary.append(f"  [remove] {var} @ {scope}:{loc} — {note}")
                return
            manual.append(f"{var} @ {loc}: ya ausente — nada que eliminar")
            return
        if action == "add" and exists:
            action = "update"
            note = (note + " | " if note else "") + "ya existe — se actualiza"
        elif action == "update" and not exists:
            if in_release:
                note = (note + " | " if note else "") + \
                    "no está en la definición — se actualiza solo " \
                    "en el release"
            else:
                manual.append(f"{var} @ {loc}: la violación indica variable "
                              f"existente pero no está en la definición "
                              f"— omitida")
                return
        if action == "update" and exists and cur.get("value") == value \
                and not (secret and not cur.get("isSecret")) \
                and not (secret and in_release
                         and not (rel_cur or {}).get("isSecret")):
            manual.append(f"{var} @ {loc}: ya tiene el valor correcto — "
                          f"sin cambio")
            return
        if action == "update" and exists and cur.get("value") != value:
            note = (note + " | " if note else "") + (
                "sobrescribe valor actual" if cur.get("value") not in (None, "")
                else "existía vacía — se rellena")

        rule = {"name": var, "action": action, "scope": scope}
        if action != "remove":
            rule["value"] = value
            # Las variables del pipeline CD no deben quedar "settable at
            # release time": ambos engines defaultan allowOverride=true
            rule["allowOverride"] = False
        if scope == "environment":
            rule["stage"] = stage
        if secret:
            rule["isSecret"] = True
        if note:
            rule["note"] = note
        rules.append(rule)
        summary.append(f"  [{action}] {var} @ {scope}:{loc}"
                       + (" (isSecret)" if secret else "")
                       + (f" — {note}" if note else ""))

    for v in violations:
        rule_name, env_name = v["rule"], v["environment"]
        reason, detail = v.get("reason", ""), v.get("detail", "")
        var_field = v.get("variable", "")

        if rule_name == "RULE_1_SECRET":
            var = var_field.split(",")[0].strip()
            if var in removes:
                add_rule(var, env_name, "environment", "remove",
                         note="eliminada a petición")
                continue
            current = env_vars(env_name).get(var) or {}
            rel_current = rel_var(env_name, "environment", var) or {}
            if not current and not rel_current:
                manual.append(f"{var} @ {env_name}: no está en la definición "
                              f"ni en el release — omitida")
                continue
            val = current.get("value")
            if val in (None, ""):
                val = rel_current.get("value")
            add_rule(var, env_name, "environment", "update", val,
                     secret=True, note="marcar secreta")
            continue

        if rule_name != "STAGE_VARIABLES":
            continue

        if env_name in ("", "(nivel pipeline)"):
            for var in [x.strip() for x in var_field.split(",") if x.strip()]:
                val = values.get(var)
                if var in removes:
                    add_rule(var, "", "release", "remove",
                             note="eliminada a petición")
                elif val is not None:
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
                if var in removes:
                    add_rule(var, env_name, "environment", "remove",
                             note="eliminada a petición")
                    continue
                # Buscar fuente EXTERNA al stage destino (evita "copiado de sí
                # mismo"); si la var ya existe en el destino, add_rule la
                # convierte en update o la marca sin cambio.
                val, src_found = find_value(var, exclude=env_name)
                if val is not None:
                    warn = _env_mismatch(src_found, env_name)
                    note = f"copiado de {src_found}"
                    if warn:
                        note += f" | {warn}"
                    add_rule(var, env_name, "environment", "add", val,
                             secret=var in secret_vars,
                             note=note)
                elif var in values:
                    add_rule(var, env_name, "environment", "add",
                             values[var], secret=var in secret_vars,
                             note="valor definido por usuario")
                else:
                    cur = env_vars(env_name).get(var) or {}
                    if cur.get("value") not in (None, ""):
                        manual.append(f"{var} @ {env_name}: ya existe con "
                                      f"valor — sin cambio necesario")
                    else:
                        need_value(var, env_name, "environment")
                        manual.append(f"{var} @ {env_name} (de {src}): "
                                      f"sin valor fuente — definir a mano")
            continue

        if "contenido" in reason:
            for var in [x.strip() for x in var_field.split(",") if x.strip()]:
                if var in removes:
                    add_rule(var, env_name, "environment", "remove",
                             note="eliminada a petición")
                    continue
                val, src = find_value(var, exclude=env_name)
                if val is not None:
                    warn = _env_mismatch(src, env_name)
                    note = f"copiado de {src}"
                    if warn:
                        note += f" | {warn}"
                    add_rule(var, env_name, "environment", "update", val,
                             secret=var in secret_vars,
                             note=note)
                elif var in values:
                    add_rule(var, env_name, "environment", "update",
                             values[var],
                             secret=var in secret_vars,
                             note="valor definido por usuario")
                else:
                    need_value(var, env_name, "environment")
                    manual.append(f"{var} @ {env_name}: definir valor "
                                  f"(sin fuente en otros stages)")

    return {"rules": rules, "manual": manual,
            "pending": pending, "summary": summary}


# ---------------------------------------------------------------------------
# Captura de valores pendientes
# ---------------------------------------------------------------------------

_REMOVE_CMDS = ("e", "eliminar", "remove", "d", "delete", "r")
_IGNORE_CMDS = ("i", "ignorar", "s", "skip", "-")
_SECRET_CMDS = ("k", "secreto", "secret", "lock")


def _rich_input(prompt: str) -> str:
    console.print(prompt, end="", markup=True)
    return input()


def collect_pending_values(actionables: dict, values: dict = None,
                           removes: set = None,
                           prompt_fn=None,
                           default: str = DEFAULT_PENDING_VALUE):
    """Ciclo sobre las variables pendientes.

    Por cada una: Enter = 'TBD', texto = valor, 'e' = eliminar la variable,
    'i'/'s' = ignorar (queda manual).
    Retorna (values, removes)."""
    prompt_fn = prompt_fn or _rich_input
    values = dict(values or {})
    removes = set(removes or ())
    pending = actionables.get("pending", {})
    if not pending:
        return values, removes
    console.print(Panel(
        "[bold]Variables sin valor fuente[/]\n\n"
        f"  [cyan bold]Enter[/]   = valor '{default}' (placeholder)\n"
        "  [green bold]texto[/]  = ese valor en todos los scopes pendientes\n"
        "  [red bold]e[/]      = eliminar la variable donde exista\n"
        "  [yellow]i[/]      = ignorar (queda pendiente manual)",
        title="Captura de valores", border_style="cyan"))
    for var, info in pending.items():
        if var in values or var in removes:
            continue
        scopes = ", ".join(info["stages"]) or info["scope"]
        val = prompt_fn(
            f"  Valor para [bold white]{var}[/] ([magenta]{scopes}[/]) "
            f"\\[[cyan bold]Enter={default}[/] | [red bold]e[/]=eliminar | "
            f"[yellow]i[/]=ignorar]: ").strip()
        low = val.lower()
        if low in _REMOVE_CMDS:
            removes.add(var)
        elif low in _IGNORE_CMDS:
            continue
        else:
            values[var] = val or default
    return values, removes


def fill_pending_default(actionables: dict, values: dict,
                         default: str = DEFAULT_PENDING_VALUE) -> dict:
    """No interactivo: todas las pendientes toman el valor default (--tbd)."""
    values = dict(values or {})
    for var in actionables.get("pending", {}):
        values.setdefault(var, default)
    return values


_SECRET_NAME = re.compile(r"secret|token|passw|pwd|key|cred", re.I)


def mask_value(rule_or_name, value) -> str:
    """Oculta valores sensibles en el resumen; muestra 'TBD' tal cual."""
    name = rule_or_name.get("name", "") if isinstance(rule_or_name, dict) \
        else str(rule_or_name)
    is_secret = isinstance(rule_or_name, dict) and rule_or_name.get("isSecret")
    if value == DEFAULT_PENDING_VALUE:
        return DEFAULT_PENDING_VALUE
    if is_secret or _SECRET_NAME.search(name):
        return "********"
    s = str(value)
    return s if len(s) <= 60 else s[:57] + "..."


def rules_table(rules: list, title: str) -> Table:
    """Tabla de ajustes con acción coloreada y valores enmascarados."""
    table = Table(title=title, box=box.SIMPLE_HEAD, header_style="bold cyan")
    table.add_column("Acción", no_wrap=True)
    table.add_column("Variable", style="bold")
    table.add_column("Scope")
    table.add_column("Valor")
    table.add_column("Nota", style="dim")
    for r in rules:
        action = r.get("action", "")
        style = ACTION_STYLE.get(action, "")
        loc = r.get("stage") if r.get("scope") == "environment" \
            else "pipeline (release)"
        value = "(eliminar)" if action == "remove" \
            else mask_value(r, r.get("value"))
        val_style = "dim" if value in ("********", "(eliminar)") \
            else ("bold cyan" if value == DEFAULT_PENDING_VALUE else "")
        if r.get("isSecret"):
            var_cell = r["name"] + f"  [magenta]{ICON_SECRET}[/]"
        elif r.get("isSecret") is False:
            var_cell = r["name"] + f"  [dim]{ICON_UNSECRET}[/]"
        else:
            var_cell = r["name"]
        table.add_row(f"[{style}]{action}[/]" if style else action,
                      var_cell, loc,
                      f"[{val_style}]{value}[/]" if val_style else str(value),
                      r.get("note", ""))
    return table


def show_rules(rules: list,
               title: str = "Resumen FINAL de cambios (lo que se "
                            "escribirá en el pipeline)"):
    """Resumen de reglas con sus valores (sensibles enmascarados)."""
    console.print(rules_table(rules, title))


def edit_rules(rules: list, prompt_fn=None, match=None) -> list:
    """Recorre los ajustes candidatos (todos o solo los que cumplan `match`).

    Por regla: Enter = conservar, texto = nuevo valor (en remove revierte
    a update), 'e' = convertir a remove (eliminar la variable),
    'i' = descartar el ajuste (no se toca la variable)."""
    prompt_fn = prompt_fn or _rich_input
    console.print(Panel(
        "[bold]Edición de ajustes candidatos[/]\n\n"
        "  [cyan bold]Enter[/]   = conservar tal cual\n"
        "  [green bold]texto[/]  = reemplazar el valor "
        "(en remove: revierte a update)\n"
        "  [magenta bold]k[/]      = marcar/desmarcar como secreta "
        "(isSecret)\n"
        "  [red bold]e[/]      = eliminar la variable (action: remove)\n"
        "  [yellow]i[/]      = descartar el ajuste (no modificar)",
        title="Editor de ajustes", border_style="magenta"))
    edited, dropped = [], 0
    total = len(rules)
    for i, r in enumerate(rules, 1):
        if match and not match(r):
            edited.append(r)
            continue
        action = r["action"]
        loc = r.get("stage") if r.get("scope") == "environment" else "release"
        cur = "(eliminar)" if action == "remove" \
            else mask_value(r, r.get("value"))
        style = ACTION_STYLE.get(action, "")
        lock = f" [magenta]{ICON_SECRET}[/]" if r.get("isSecret") else ""
        console.print(
            f"  [cyan]{i}/{total}[/] [{style}]{action}[/] "
            f"[bold white]{r['name']}[/]{lock} @ [magenta]{loc}[/] "
            f"= [bold]{cur}[/]")
        while True:
            val = prompt_fn(
                "    [cyan bold]Enter[/]=conservar | [green bold]texto[/]"
                "=valor | [magenta bold]k[/]=secret on/off | "
                "[red bold]e[/]=eliminar | [yellow]i[/]=ignorar: ").strip()
            low = val.lower()
            if low in _IGNORE_CMDS:
                dropped += 1
                r = None
                break
            if low in _SECRET_CMDS:
                if action == "remove":
                    console.print("    [yellow](no aplica a remove)[/]")
                    continue
                nr = dict(r)
                if nr.get("isSecret"):
                    nr["isSecret"] = False
                    nr["note"] = ((nr.get("note") or "") +
                                  " | desmarcada como secreta").lstrip(" |")
                else:
                    nr["isSecret"] = True
                    nr["note"] = ((nr.get("note") or "") +
                                  " | marcada como secreta").lstrip(" |")
                edited.append(nr)
                break
            if low in _REMOVE_CMDS:
                edited.append({"name": r["name"], "action": "remove",
                               "scope": r["scope"],
                               **({"stage": r["stage"]}
                                  if r.get("stage") else {}),
                               "note": "eliminada a petición "
                                       "(edición manual)"})
                break
            if val:
                nr = dict(r)
                if action == "remove":
                    nr["action"] = "update"
                    nr["note"] = "valor definido por usuario (edición manual)"
                    nr.setdefault("allowOverride", False)
                nr["value"] = val
                edited.append(nr)
                break
            edited.append(r)
            break
    if dropped:
        console.print(f"  [yellow]{dropped} ajuste(s) descartados.[/]")
    return edited


def review_values(values: dict, var_names, removes: set = None,
                  prompt_fn=None):
    """Corregir/eliminar valores capturados: Enter conserva, texto reemplaza,
    'e' marca la variable para eliminación, 'i'/'s' la regresa a manual."""
    prompt_fn = prompt_fn or _rich_input
    removes = removes if removes is not None else set()
    console.print("\n[bold]Corregir valores[/] "
                  "([cyan]Enter[/] = conservar, [red]e[/] = eliminar, "
                  "[yellow]i[/] = manual)")
    for var in list(var_names):
        if var in values:
            current = mask_value(var, values[var])
            new = prompt_fn(
                f"  [bold cyan]{var}[/] actual='{current}' -> nuevo: "
            ).strip()
            low = new.lower()
            if low in _REMOVE_CMDS:
                values.pop(var, None)
                removes.add(var)
            elif low in _IGNORE_CMDS:
                values.pop(var, None)
            elif new:
                values[var] = new
        elif var in removes:
            new = prompt_fn(
                f"  [bold cyan]{var}[/] actual='(eliminar)' -> nuevo: "
            ).strip()
            low = new.lower()
            if low in _IGNORE_CMDS:
                removes.discard(var)
            elif new and low not in _REMOVE_CMDS:
                removes.discard(var)
                values[var] = new
    return values, removes


# ---------------------------------------------------------------------------
# Template + aplicación
# ---------------------------------------------------------------------------

_RULE_KEYS = {"name", "action", "scope", "stage", "value",
              "allowOverride", "isSecret"}
_ACTION_GLYPH = {"add": "+", "update": "~", "remove": "-"}


def rules_summary(rules: list) -> str:
    """Comentario simplificado de todos los cambios de una regla:
    '3 cambio(s): +cpu@Develop=200m, ~ksa@Prod=******** 🔒, -tuSecret@release'.
    Va en metadata.comment (→ historial de revisiones de AzDO) y como
    comentario '#' al inicio del YAML."""
    parts = []
    for r in rules:
        glyph = _ACTION_GLYPH.get(r.get("action"), "?")
        loc = r.get("stage") if r.get("scope") == "environment" else "release"
        s = f"{glyph}{r.get('name')}@{loc}"
        if r.get("action") != "remove":
            s += f"={mask_value(r, r.get('value'))}"
        if r.get("isSecret") is True:
            s += f" {ICON_SECRET}"
        elif r.get("isSecret") is False:
            s += f" {ICON_UNSECRET}"
        parts.append(s)
    if not parts:
        return "sin cambios"
    return f"{len(parts)} cambio(s): " + ", ".join(parts)


def _write_template(path: Path, template: dict, comment: str) -> Path:
    """Escribe el YAML precedido por '# <comentario simplificado>'."""
    text = yaml.safe_dump(template, allow_unicode=True, sort_keys=False)
    path.write_text(f"# {comment}\n{text}", encoding="utf-8")
    return path


def generate_template(rules: list, definition_id: str, pipeline_name: str,
                      out_dir: Path = None) -> Path:
    out_dir = out_dir or resolve_outcome_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"pipe_cd_inspection_fix_{definition_id}_{ts}.yaml"
    clean_rules = [{k: v for k, v in r.items() if k in _RULE_KEYS}
                   for r in rules]
    comment = rules_summary(clean_rules)
    template = {
        "metadata": {
            "name": f"SCM Inspection Fix — {pipeline_name} ({definition_id})",
            "version": "1.0",
            "description": "Corrige violaciones del stage SCM Inspection "
                           "del pipeline CD: secrets, paridad de variables "
                           "y valores vacíos. Generado por "
                           "scm_inspection_remediator.",
            # 'comment' viaja en el PUT de la definición → historial AzDO
            "comment": comment,
            "created_at": ts,
        },
        "search": {"stages": []},
        "update": {"variables": clean_rules},
        "options": {"dry_run": False, "rollback_on_error": True,
                    "parallel_workers": 5},
    }
    return _write_template(path, template, comment)


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
    console.print(f"\n[cyan]{ICON_RUN} Ejecutando:[/] "
                  f"[dim]{' '.join(cmd[:3])} ...[/]")
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


# ---------------------------------------------------------------------------
# Aplicación sobre un Release (instancia) — engine existente (opción 42)
# ---------------------------------------------------------------------------

def generate_release_template(rules: list, release_id: str,
                              pipeline_name: str = "",
                              out_dir: Path = None) -> Path:
    """Genera template formato pipeline_cd_update_release (opción 42):
    reglas scope=release → update.global_vars; scope=environment →
    update.env_vars con stage. Soporta action: remove e isSecret."""
    out_dir = out_dir or resolve_outcome_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"release_inspection_fix_{release_id}_{ts}.yaml"
    gvars, evars = [], []
    for r in rules:
        if r.get("scope") == "environment":
            v = {"stage": r.get("stage"), "name": r["name"]}
            target = evars
        else:
            v = {"name": r["name"]}
            target = gvars
        if r["action"] == "remove":
            v["action"] = "remove"
        else:
            v["value"] = r.get("value")
            v["allowOverride"] = r.get("allowOverride", False)
        if "isSecret" in r:
            v["isSecret"] = r["isSecret"]
        target.append(v)
    comment = rules_summary(rules)
    template = {
        "metadata": {
            "name": f"SCM Inspection Fix — Release #{release_id} "
                    f"({pipeline_name})",
            "version": "1.0",
            "description": "Corrige violaciones del stage SCM Inspection "
                           "sobre el snapshot de variables del release. "
                           "Generado por scm_inspection_remediator.",
            # 'comment' viaja en el PUT del release → historial AzDO
            "comment": comment,
            "created_at": ts,
        },
        "release": {"ids": [str(release_id)]},
        "update": {"global_vars": gvars, "env_vars": evars},
        "options": {"dry_run": False},
    }
    return _write_template(path, template, comment)


def apply_release_template(template_path: Path, release_id: str,
                           org: str, project: str, pat: str,
                           dry_run: bool) -> int:
    """Aplica el template de release con el engine existente
    (pipeline_cd_update_release — opción 42): GET → cambios → backup → PUT."""
    cmd = [sys.executable, "-m",
           "scm.azdo.pipeline_cd_update_release.pipeline_cd_update_release",
           "--release-id", str(release_id),
           "--template", str(template_path),
           "--org", org, "--project", project, "--pat", pat]
    if dry_run:
        cmd.append("--dry-run")
    console.print(f"\n[cyan]{ICON_RUN} Ejecutando:[/] "
                  f"[dim]{' '.join(cmd[:3])} ...[/]")
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def redeploy_stage(client: AzdoClient, release_id: str,
                   stage_name: str) -> int:
    """Dispara el deploy de un environment del release: PATCH
    releases/{id}/environments/{envId} con status inProgress. Usado para
    Ejecutar el stage 'SCM Inspection' tras remediar el release."""
    release = client.get(f"{client.base}/releases/{release_id}",
                         params={"api-version": "7.1"})
    env = next((e for e in release.get("environments", [])
                if e.get("name", "").lower() == stage_name.lower()), None)
    if not env:
        console.print(f"[red]El release #{release_id} no tiene stage "
                      f"'{stage_name}'.[/]")
        return 1
    client.patch(
        f"{client.base}/releases/{release_id}/environments/{env['id']}",
        {"status": "inProgress"}, params={"api-version": "7.1"})
    console.print(f"[bold green]{ICON_OK} Deploy de '{stage_name}' "
                  f"disparado en release #{release_id}.[/]")
    return 0


def _offer_redeploy(client: AzdoClient, release_id: str, stage_name: str,
                    prompt_fn=None, auto: bool = False) -> int:
    """Tras aplicar al release, ofrece/ejecuta el redeploy del stage
    inspeccionado (default Sí en interactivo; `auto` para CLI)."""
    if auto:
        return redeploy_stage(client, release_id, stage_name)
    if not prompt_fn:
        return 0
    ans = prompt_fn(
        f"  [bold]Ejecutar deploy de '{stage_name}' en release "
        f"#{release_id}?[/] \\[[cyan]S/n[/]]: ").strip().lower()
    if ans in ("n", "no"):
        return 0
    return redeploy_stage(client, release_id, stage_name)


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------

def show_plan(discovery: dict, actionables: dict, definition_id: str):
    definition, release = discovery["definition"], discovery["release"]
    console.print(Panel(
        f"[bold]Pipeline :[/] {definition.get('name')} (ID {definition_id})\n"
        f"[bold]Release  :[/] {release.get('name')} "
        f"(ID {release.get('id')})\n"
        f"[bold]Stage    :[/] {discovery['env'].get('name')} — "
        f"status: {discovery['env'].get('status', '-')}",
        title="Descubrimiento", border_style="blue"))

    violations = discovery["violations"]
    if not violations:
        console.print(f"[bold green]{ICON_OK} Sin violaciones en el "
                      f"último run del stage.[/]")
        return

    table = Table(title=f"Violaciones: {len(violations)}",
                  box=box.SIMPLE_HEAD, header_style="bold")
    table.add_column("Sev", no_wrap=True)
    table.add_column("Regla")
    table.add_column("Stage")
    table.add_column("Variables", style="dim", max_width=60)
    for v in violations:
        sev = v["severity"]
        table.add_row(f"[{SEV_STYLE.get(sev, '')}]{sev}[/]",
                      v["rule"], v["environment"] or "pipeline",
                      (v.get("variable") or "")[:80])
    console.print(table)

    if actionables["rules"]:
        console.print("\n[bold]Ajustes candidatos[/] [dim](se escribirán en "
                      "un template pipe_cd_*.yaml y se aplicarán al pipeline "
                      "CD via Pipeline Updater — opción 41; aún puedes "
                      "editarlos)[/]")
        console.print(rules_table(actionables["rules"],
                                  "Ajustes candidatos"))
    if actionables["manual"]:
        console.print(f"\n[yellow]{ICON_WARN} Requieren intervención "
                      f"manual (sin valor fuente):[/]")
        for m in actionables["manual"]:
            console.print(f"  [yellow]-[/] {m}")


def run_flow(args, interactive: bool) -> int:
    org, project, pat = get_azdo_params(args)
    client = AzdoClient(org, project, pat)

    definition_id = args.definition_id
    if not definition_id:
        definition_id = _rich_input(
            "[bold]Definition ID del pipeline CD:[/] ").strip()
        if not definition_id:
            console.print("[red]Se requiere el definition ID.[/]")
            return 1

    if interactive and not args.release_id:
        rel = _rich_input(
            "[bold]Release ID a inspeccionar[/] "
            "[dim]\\[Enter = último run del stage][/]: ").strip()
        if rel and not rel.isdigit():
            console.print(f"[yellow]{ICON_WARN} '{rel}' no es numérico — "
                          f"se usa el último run.[/]")
            rel = ""
        args.release_id = rel

    values = {}
    removes = set(args.remove or [])
    for item in args.set or []:
        if "=" in item:
            k, _, val = item.partition("=")
            values[k.strip()] = val

    console.print(f"\n[cyan]Descubriendo violaciones del stage "
                  f"'{args.stage}'...[/]")
    discovery = discover(client, definition_id, args.stage, args.release_id)
    actionables = build_actionables(discovery["definition"],
                                    discovery["violations"], values, removes,
                                    release=discovery["release"])
    show_plan(discovery, actionables, definition_id)

    if not actionables["rules"] and not actionables["manual"]:
        return 0

    # Valores pendientes: --tbd (no interactivo) o ciclo con default TBD
    pending_vars = set(actionables["pending"])
    if pending_vars:
        if args.tbd:
            values = fill_pending_default(actionables, values)
        elif interactive:
            values, removes = collect_pending_values(
                actionables, values, removes)
        if values or removes:
            actionables = build_actionables(discovery["definition"],
                                            discovery["violations"],
                                            values, removes,
                                            release=discovery[
                                                "release"])

    if not actionables["rules"]:
        console.print("\n[yellow]No hay acciones automáticas — solo "
                      "pendientes manuales.[/]")
        return 0

    # Resumen final con valores; permite corregir antes de generar/aplicar
    rules_edited = False
    while True:
        show_rules(actionables["rules"])
        if actionables["manual"]:
            console.print(f"\n[yellow]{ICON_WARN} Quedarán manuales:[/]")
            for m in actionables["manual"]:
                console.print(f"  [yellow]-[/] {m}")
        if not interactive:
            break
        opts = "[bold cyan][Enter][/] Generar template"
        if pending_vars:
            opts += " [dim]|[/] [bold cyan]\\[c][/] Corregir valores pendientes"
        opts += (" [dim]|[/] [bold cyan]\\[e][/] Editar ajustes uno a uno"
                 " [dim]|[/] [bold cyan]\\[v][/] Editar variable puntual"
                 " [dim]|[/] [bold cyan]\\[r][/] Recargar ajustes"
                 " [dim]|[/] [bold cyan]\\[0][/] Salir")
        console.print("\n" + opts)
        choice = _rich_input("[bold cyan]Seleccione:[/] ").strip().lower()
        if choice == "0":
            return 0
        if choice == "r":
            actionables = build_actionables(discovery["definition"],
                                            discovery["violations"],
                                            values, removes,
                                            release=discovery[
                                                "release"])
            rules_edited = False
            console.print("[cyan]Ajustes recargados desde las "
                          "violaciones (ediciones manuales descartadas; "
                          "los valores pendientes capturados se "
                          "conservan).[/]")
            continue
        if choice == "v":
            target = _rich_input(
                "[bold]Variable a editar[/] ([white]nombre[/] o "
                "[white]nombre@stage[/]): ").strip()
            if not target:
                continue
            name, _, stg = target.partition("@")
            name, stg = name.strip(), stg.strip()

            def _mt(r, _n=name, _s=stg):
                return r["name"] == _n and (not _s or r.get("stage") == _s)
            if not any(_mt(r) for r in actionables["rules"]):
                console.print(f"[yellow]Sin ajustes para '{target}' — "
                              f"verifique nombre/stage.[/]")
                continue
            actionables["rules"] = edit_rules(
                actionables["rules"], match=_mt)
            rules_edited = True
            continue
        if choice == "e":
            actionables["rules"] = edit_rules(actionables["rules"])
            rules_edited = True
            if not actionables["rules"]:
                console.print("\n[yellow]Todos los ajustes fueron "
                              "descartados.[/]")
                return 0
            continue
        if choice == "c" and pending_vars:
            if rules_edited:
                console.print("[yellow]Los ajustes editados a mano se "
                              "recalcularán desde las violaciones.[/]")
            values, removes = review_values(values, pending_vars, removes)
            actionables = build_actionables(discovery["definition"],
                                            discovery["violations"],
                                            values, removes,
                                            release=discovery[
                                                "release"])
            rules_edited = False
            if not actionables["rules"]:
                console.print("\n[yellow]Sin reglas restantes — solo "
                              "pendientes manuales.[/]")
                return 0
            continue
        break

    template = generate_template(actionables["rules"], definition_id,
                                 discovery["definition"].get("name", ""))
    console.print(f"\n[green]{ICON_DOC} Template generado:[/] "
                  f"[bold]{template}[/]")

    release_target = args.release_id or \
        str(discovery["release"].get("id", ""))

    if args.apply or args.dry_run:
        dry = args.dry_run and not args.apply
        target = getattr(args, "target", None) or "definition"
        rc = 0
        if target in ("definition", "both"):
            rc = apply_template(template, definition_id, org, project, pat,
                                dry_run=dry)
            console.print(f"\n[bold green]{ICON_OK} Definición "
                          f"actualizada.[/]" if rc == 0 else
                          f"\n[bold red]X Definición falló (exit {rc}).[/]")
        if target in ("release", "both"):
            if rc != 0:
                console.print(f"[yellow]{ICON_WARN} Release omitido — "
                              f"falló la definición.[/]")
            else:
                rel_tpl = generate_release_template(
                    actionables["rules"], release_target,
                    discovery["definition"].get("name", ""))
                console.print(f"[green]{ICON_DOC} Template release:[/] "
                              f"[bold]{rel_tpl}[/]")
                rc = apply_release_template(rel_tpl, release_target,
                                            org, project, pat, dry_run=dry)
                if rc == 0 and not dry and getattr(args, "redeploy", False):
                    _offer_redeploy(client, release_target, args.stage,
                                    auto=True)
        return rc

    console.print("\n[dim]Definición: template pipe_cd_*.yaml (opción 41); "
                  "Release: template release_*.yaml aplicado con el engine "
                  "de Update Release (opción 42).[/]")
    while True:
        console.print("\n[bold][1][/] Solo template (definición — aplicar "
                      "luego con opción 41)")
        console.print("[bold][2][/] Definición: dry-run")
        console.print("[bold][3][/] Definición: aplicar")
        console.print(f"[bold][4][/] Release: dry-run "
                      f"(default #{release_target})")
        console.print(f"[bold][5][/] Release: aplicar "
                      f"(default #{release_target})")
        console.print("[bold][6][/] Ambos: definición + release")
        console.print("[bold][0][/] Salir")
        choice = _rich_input("[bold]Seleccione:[/] ").strip()
        if choice in ("0", "1"):
            return 0
        if choice == "2":
            apply_template(template, definition_id, org, project, pat,
                           dry_run=True)
            continue
        if choice == "3":
            rc = apply_template(template, definition_id, org, project, pat,
                                dry_run=False)
            console.print(f"\n[bold green]{ICON_OK} Aplicado.[/]"
                          if rc == 0
                          else f"\n[bold red]X Falló (exit {rc}).[/]")
            continue
        if choice in ("4", "5", "6"):
            rel = _rich_input(
                f"  [bold]Release ID[/] "
                f"\\[[cyan]{release_target}[/]]: ").strip() or release_target
            rel_tpl = generate_release_template(
                actionables["rules"], rel,
                discovery["definition"].get("name", ""))
            console.print(f"[green]{ICON_DOC} Template release:[/] "
                          f"[bold]{rel_tpl}[/]")
            if choice == "4":
                apply_release_template(rel_tpl, rel, org, project, pat,
                                       dry_run=True)
                continue
            if choice == "5":
                rc = apply_release_template(rel_tpl, rel, org, project,
                                            pat, dry_run=False)
                if rc == 0:
                    _offer_redeploy(client, rel, args.stage,
                                    prompt_fn=_rich_input)
                continue
            rc = apply_template(template, definition_id, org, project, pat,
                                dry_run=False)
            if rc != 0:
                console.print(f"\n[bold red]X Definición falló "
                              f"(exit {rc}) — release omitido.[/]")
                continue
            rc = apply_release_template(rel_tpl, rel, org, project, pat,
                                        dry_run=False)
            if rc == 0:
                _offer_redeploy(client, rel, args.stage,
                                prompt_fn=_rich_input)
            continue
        console.print("[red]Opción no válida.[/]")


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
                        help="Release específico (default: último run del "
                             "stage; también es el release destino por "
                             "defecto con --target release|both)")
    parser.add_argument("--target",
                        choices=["definition", "release", "both"],
                        default="definition",
                        help="Destino de --apply/--dry-run: definición del "
                             "pipeline, release (instancia) o ambos")
    parser.add_argument("--redeploy", action="store_true",
                        help="Tras aplicar al release (--target release|both "
                             "--apply), dispara el deploy del stage "
                             "inspeccionado en ese release")
    parser.add_argument("--org", default=None)
    parser.add_argument("--project", default=None)
    parser.add_argument("--pat", default=None)
    parser.add_argument("--set", action="append",
                        help="Valor para variable pendiente: NAME=VALUE (repetible)")
    parser.add_argument("--remove", action="append",
                        help="Eliminar variable: NAME (repetible)")
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
