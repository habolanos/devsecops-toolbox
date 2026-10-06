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
  - STAGE_VARIABLES pipeline → valor a nivel release (pide valor / TBD / remove)
  - STAGE_VARIABLES paridad  → add con el valor copiado del stage origen
  - STAGE_VARIABLES contenido→ update con el valor hallado en otro stage
  - Pendientes               → valor | 'TBD' | eliminar (e) | ignorar (i)

Uso:
    python scm_inspection_remediator.py --interactive
    python scm_inspection_remediator.py --definition-id 1837 --dry-run
    python scm_inspection_remediator.py --definition-id 1837 --apply
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

    def get(self, url: str, raw: bool = False, params: dict = None):
        for attempt in range(4):
            resp = self.session.get(url, params=params, timeout=30)
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
                      values: dict = None, removes: set = None) -> dict:
    """Convierte violaciones en reglas `update.variables` del template.

    Returns {"rules": [...], "manual": [...], "pending": {...}, "summary": [...]}
    `values` permite inyectar valores para variables pendientes.
    `removes` = set de variables a eliminar (action: remove) donde existan.
    `pending` = {var: {"scope": ..., "stages": [...]}} — variables que requieren
    valor (default "TBD" o capturadas con collect_pending_values/--tbd).
    """
    values = values or {}
    removes = set(removes or ())
    envs = {e["name"]: e for e in definition.get("environments", [])}
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

    def add_rule(var, stage, scope, action, value=None, secret=False, note=""):
        # Ajustar la acción a lo que el updater realmente hará
        vars_map = env_vars(stage) if scope == "environment" \
            else (definition.get("variables") or {})
        exists = var in vars_map
        cur = vars_map.get(var) or {}
        loc = stage or "release"

        if action == "remove" and not exists:
            manual.append(f"{var} @ {loc}: ya ausente — nada que eliminar")
            return
        if action == "add" and exists:
            action = "update"
            note = (note + " | " if note else "") + "ya existe — se actualiza"
        elif action == "update" and not exists:
            manual.append(f"{var} @ {loc}: la violación indica variable "
                          f"existente pero no está en la definición — omitida")
            return
        if action == "update" and exists and cur.get("value") == value \
                and not (secret and not cur.get("isSecret")):
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


def generate_template(rules: list, definition_id: str, pipeline_name: str,
                      out_dir: Path = None) -> Path:
    out_dir = out_dir or resolve_outcome_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"pipe_cd_inspection_fix_{definition_id}_{ts}.yaml"
    clean_rules = [{k: v for k, v in r.items() if k in _RULE_KEYS}
                   for r in rules]
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
        "update": {"variables": clean_rules},
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
    console.print(f"\n[cyan]{ICON_RUN} Ejecutando:[/] "
                  f"[dim]{' '.join(cmd[:3])} ...[/]")
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


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
                                    discovery["violations"], values, removes)
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
                                            values, removes)

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
                                            values, removes)
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
                                            values, removes)
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

    if args.apply or args.dry_run:
        rc = apply_template(template, definition_id, org, project, pat,
                            dry_run=args.dry_run and not args.apply)
        console.print(f"\n[bold green]{ICON_OK} Aplicado.[/]" if rc == 0
                      else f"\n[bold red]X Falló (exit {rc}).[/]")
        return rc

    console.print("\n[bold][1][/] Solo template (aplicar luego con opción 41)")
    console.print("[bold][2][/] Dry-run (simulación)")
    console.print("[bold][3][/] Aplicar")
    console.print("[bold][0][/] Salir")
    choice = _rich_input("[bold]Seleccione:[/] ").strip()
    if choice == "2":
        return apply_template(template, definition_id, org, project, pat,
                              dry_run=True)
    if choice == "3":
        rc = apply_template(template, definition_id, org, project, pat,
                            dry_run=False)
        console.print(f"\n[bold green]{ICON_OK} Aplicado.[/]" if rc == 0
                      else f"\n[bold red]X Falló (exit {rc}).[/]")
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
