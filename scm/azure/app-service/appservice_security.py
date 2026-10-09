#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure App Service Security Auditor — Tool 20

Auditoría de seguridad de App Services, equivalente a
aws_lambda_security_auditor / gcp_cloudrun_security_auditor:

- httpsOnly, TLS mínimo (<1.2 critical), FTPS state
- Easy Auth (auth settings) deshabilitado en apps expuestas
- Managed identity ausente
- Remote debugging habilitado, CORS con *, VNet integration
- Client certificates, IP restrictions (sin restricción = público)

Uso:
    python appservice_security.py --subscription <id>
    python appservice_security.py --severity critical -o json
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
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def audit_app(sub: str, app: Dict) -> List[Dict]:
    name, rg = app["name"], rg_of(app)
    findings = []

    cfg = try_az(["webapp", "config", "show", "--name", name,
                  "--resource-group", rg], sub,
                 default={}) or {}
    auth = try_az(["webapp", "auth", "show", "--name", name,
                   "--resource-group", rg], sub,
                  default={}) or {}

    if not app.get("httpsOnly"):
        findings.append({"sev": "critical", "check": "https",
                         "detail": "httpsOnly=false"})
    tls = cfg.get("minTlsVersion")
    if tls and float(tls) < 1.2:
        findings.append({"sev": "critical", "check": "tls",
                         "detail": f"minTlsVersion={tls} <1.2"})
    if cfg.get("ftpsState") not in ("Disabled", "FtpsOnly"):
        findings.append({"sev": "high", "check": "ftps",
                         "detail": f"ftpsState="
                                   f"{cfg.get('ftpsState')}"})
    if cfg.get("remoteDebuggingEnabled"):
        findings.append({"sev": "high", "check": "remote_debug",
                         "detail": "Remote debugging "
                                   "habilitado"})
    cors = cfg.get("cors", {})
    if "*" in (cors.get("allowedOrigins") or []):
        findings.append({"sev": "high", "check": "cors",
                         "detail": "CORS permite *"})
    if not auth.get("enabled"):
        findings.append({"sev": "medium", "check": "auth",
                         "detail": "Easy Auth deshabilitado — "
                                   "app accesible sin auth "
                                   "(si no es pública "
                                   "intencional)"})
    if not app.get("identity"):
        findings.append({"sev": "low", "check": "identity",
                         "detail": "Sin managed identity"})
    if not cfg.get("vnetRouteAllEnabled"):
        findings.append({"sev": "low", "check": "vnet",
                         "detail": "Sin VNet integration "
                                   "(todo el tráfico sale "
                                   "público)"})
    ip_restrictions = cfg.get("ipSecurityRestrictions", [])
    if not ip_restrictions:
        findings.append({"sev": "medium",
                         "check": "ip_restriction",
                         "detail": "Sin restricciones IP — "
                                   "expuesto a internet"})
    return [{"app": name, **f} for f in findings]


SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def get_args():
    p = argparse.ArgumentParser(
        description="Auditoría de seguridad App Service")
    p.add_argument("--subscription", default="")
    p.add_argument("--resource-group", default="")
    p.add_argument("--severity",
                   choices=["all", "critical", "high",
                            "medium", "low"], default="all")
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

    findings = []
    for a in apps:
        findings.extend(audit_app(sub, a))

    sev = SEV_ORDER.get(args.severity, 99)
    visible = sorted(
        [f for f in findings if SEV_ORDER[f["sev"]] <= sev],
        key=lambda f: SEV_ORDER[f["sev"]])
    counts = {s: len([f for f in findings if f["sev"] == s])
              for s in SEV_ORDER}

    if console:
        from rich.table import Table
        table = Table(title="App Service Security",
                      header_style="bold red")
        for col in ["Sev", "App", "Check", "Detalle"]:
            table.add_column(col)
        style = {"critical": "red bold", "high": "red",
                 "medium": "yellow", "low": "dim"}
        for f in visible[:60]:
            table.add_row(
                f"[{style[f['sev']]}]{f['sev']}"
                f"[/{style[f['sev']]}]",
                f["app"][:30], f["check"],
                f["detail"][:55])
        console.print(table)
    else:
        for f in visible:
            print(f"[{f['sev']}] {f['app']}/{f['check']}: "
                  f"{f['detail']}")

    _print(f"\nApps: {len(apps)} | findings: {len(findings)} "
           f"(critical: {counts['critical']})",
           "red" if counts["critical"] else
           ("yellow" if findings else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"appservice_security_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "summary": counts, "findings": findings})
        else:
            export_csv(out, ["sev", "app", "check", "detail"],
                       findings)
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if counts["critical"] else 0)


if __name__ == "__main__":
    main()
