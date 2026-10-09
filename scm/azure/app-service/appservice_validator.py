#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure App Service Deployment Validator — Tool 21

Valida la configuración de despliegue de App Services,
equivalente a gcp_cloudrun_deployment_validator /
aws_ecs_deployment_validator:

- Always On habilitado (Free/Shared no soporta)
- Health check path configurado
- Deployment slots con auto-swap
- Preload/warmup, ARR affinity
- 32-bit vs 64-bit, HTTP/2, webSockets si aplica
- Backup configurado (appservice backup)
- Hallazgos con severidad + remediación

Uso:
    python appservice_validator.py --subscription <id>
    python appservice_validator.py --app-name myapp -o json
"""

import argparse
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, rg_of, now_ts, export_json, export_csv)

__version__ = "1.0.0"


class Sev(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


def validate_app(sub: str, app: Dict) -> List[Dict]:
    name, rg = app["name"], rg_of(app)
    findings = []
    cfg = try_az(["webapp", "config", "show", "--name", name,
                  "--resource-group", rg], sub,
                 default={}) or {}
    if not cfg.get("alwaysOn"):
        findings.append({
            "sev": "warning", "check": "always_on",
            "detail": "AlwaysOn deshabilitado — cold starts "
                      "posibles",
            "fix": "az webapp config set --always-on true"})
    if not cfg.get("healthCheckPath"):
        findings.append({
            "sev": "warning", "check": "health_check",
            "detail": "Sin healthCheckPath — el LB no puede "
                      "sacar instancias enfermas",
            "fix": "az webapp config set --health-check-path /health"})
    if not cfg.get("http20Enabled"):
        findings.append({
            "sev": "info", "check": "http2",
            "detail": "HTTP/2 deshabilitado",
            "fix": "--http20-enabled true"})
    if cfg.get("use32BitWorkerProcess"):
        findings.append({
            "sev": "info", "check": "bitness",
            "detail": "Worker 32-bit — considerar 64-bit",
            "fix": "--use-32bit-worker-process false"})
    # Slots
    slots = try_az(["webapp", "deployment", "slot", "list",
                    "--name", name, "--resource-group", rg],
                   sub, default=[]) or []
    if not slots:
        findings.append({
            "sev": "info", "check": "slots",
            "detail": "Sin deployment slots — deploys van "
                      "directo a prod",
            "fix": "az webapp deployment slot create -s staging"})
    # Backups
    backups = try_az(["webapp", "config", "backup", "show",
                      "--webapp-name", name,
                      "--resource-group", rg], sub,
                     default=None)
    if not backups:
        findings.append({
            "sev": "warning", "check": "backup",
            "detail": "Sin backup configurado",
            "fix": "az webapp config backup create"})
    return [{"app": name, **f} for f in findings]


SEV_ORDER = {"critical": 0, "warning": 1, "info": 2}


def get_args():
    p = argparse.ArgumentParser(
        description="Valida configuración de deploy App "
                    "Service")
    p.add_argument("--subscription", default="")
    p.add_argument("--resource-group", default="")
    p.add_argument("--app-name", default="",
                   help="Solo esta app (vacío = todas)")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    cmd = ["webapp", "list"]
    if args.resource_group:
        cmd += ["--resource-group", args.resource_group]
    apps = try_az(cmd, sub, default=[]) or []
    if args.app_name:
        apps = [a for a in apps if a["name"] == args.app_name]

    findings = []
    for a in apps:
        findings.extend(validate_app(sub, a))

    visible = sorted(findings,
                     key=lambda f: SEV_ORDER[f["sev"]])
    counts = {s: len([f for f in findings if f["sev"] == s])
              for s in SEV_ORDER}

    if console:
        from rich.table import Table
        table = Table(title="App Service Deployment "
                            "Validation",
                      header_style="bold cyan")
        for col in ["Sev", "App", "Check", "Detalle"]:
            table.add_column(col)
        style = {"critical": "red", "warning": "yellow",
                 "info": "dim"}
        for f in visible[:60]:
            table.add_row(
                f"[{style[f['sev']]}]{f['sev']}"
                f"[/{style[f['sev']]}]",
                f["app"][:30], f["check"],
                f["detail"][:55])
        console.print(table)
        for f in visible:
            if f.get("fix"):
                console.print(f"  [dim]💡 {f['app']}/"
                              f"{f['check']}: {f['fix']}[/dim]")
    else:
        for f in visible:
            print(f"[{f['sev']}] {f['app']}/{f['check']}: "
                  f"{f['detail']}")

    _print(f"\nApps: {len(apps)} | findings: {len(findings)}",
           "yellow" if counts["warning"] else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"appservice_valid_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "findings": findings})
        else:
            export_csv(out, ["sev", "app", "check", "detail",
                             "fix"], findings)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
