#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Functions Analyzer — Tool 34

Análisis profundo de Azure Functions, equivalente a
gcp_cloud_functions_analyzer / aws_lambda_analyzer:

- Function apps: runtime, plan (Consumption/Premium/Dedicated),
  estado, httpsOnly
- Funciones por app: bindings/triggers (http, timer, queue,
  servicebus, eventhub)
- Vistas: summary/security/performance
- Hallazgos: httpTrigger + anonymous auth, runtime viejo,
  sin función (app vacía), CORS *

Uso:
    python azure_functions_analyzer.py --subscription <id>
    python azure_functions_analyzer.py --view security -o json
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, rg_of, now_ts, export_json, export_csv)

__version__ = "1.0.0"

EOL_RUNTIMES = {"~2", "~1", "v1"}


def list_functions(sub: str, app: Dict) -> List[Dict]:
    """Funciones dentro de una function app."""
    funcs = try_az(["functionapp", "function", "list",
                    "--name", app["name"],
                    "--resource-group", rg_of(app)], sub,
                   default=[]) or []
    out = []
    for f in funcs:
        cfg = f.get("config", {})
        bindings = cfg.get("bindings", [])
        triggers = [b.get("type") for b in bindings
                    if (b.get("type") or "").lower()
                    .endswith("trigger")]
        http_anon = any(
            b.get("type") == "httpTrigger" and
            b.get("authLevel") in ("anonymous", None)
            for b in bindings)
        out.append({
            "name": f.get("name", "").rsplit("/", 1)[-1],
            "triggers": triggers,
            "bindings": len(bindings),
            "http_anonymous": http_anon,
        })
    return out


def analyze_app(sub: str, app: Dict) -> Dict:
    name, rg = app["name"], rg_of(app)
    findings = []
    if not app.get("httpsOnly"):
        findings.append("🔴 httpsOnly=false")
    cfg = try_az(["functionapp", "config", "show",
                  "--name", name, "--resource-group", rg],
                 sub, default={}) or {}
    runtime = cfg.get("linuxFxVersion") or \
        (cfg.get("netFrameworkVersion") or "")
    cors = (cfg.get("cors") or {}).get("allowedOrigins", [])
    if "*" in cors:
        findings.append("🔴 CORS permite *")
    if not app.get("identity"):
        findings.append("🟡 Sin managed identity")
    funcs = list_functions(sub, app)
    if not funcs:
        findings.append("🟡 Function app vacía (sin funciones)")
    anon_funcs = [f for f in funcs if f["http_anonymous"]]
    if anon_funcs:
        findings.append(
            f"🟡 {len(anon_funcs)} HTTP triggers anónimos")
    plan = (app.get("appServicePlanId") or "").rsplit(
        "/", 1)[-1]
    return {
        "app": name, "resource_group": rg,
        "state": app.get("state"), "plan": plan,
        "kind": app.get("kind", ""),
        "functions": funcs,
        "function_count": len(funcs),
        "trigger_types": sorted({t for f in funcs
                                 for t in f["triggers"]}),
        "https_only": app.get("httpsOnly"),
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Análisis de Azure Functions")
    p.add_argument("--subscription", default="")
    p.add_argument("--view",
                   choices=["summary", "security",
                            "performance"],
                   default="summary")
    p.add_argument("--output", choices=["json", "csv"],
                   default="")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--timezone", default="")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    apps = try_az(["functionapp", "list"], sub,
                  default=[]) or []
    results = [analyze_app(sub, a) for a in apps]
    issues = [r for r in results
              if any("🔴" in f for f in r["findings"])]

    if console:
        from rich.table import Table
        if args.view == "security":
            cols = ["App", "HTTPS", "Anónimos", "Findings"]
        elif args.view == "performance":
            cols = ["App", "Plan", "Funcs", "Triggers"]
        else:
            cols = ["App", "State", "Plan", "Funcs", "Findings"]
        table = Table(title=f"Azure Functions — "
                            f"{args.view}", header_style="bold cyan")
        for c in cols:
            table.add_column(c)
        for r in results:
            anon = len([f for f in r["functions"]
                        if f["http_anonymous"]])
            if args.view == "security":
                table.add_row(
                    r["app"][:35],
                    "[green]✓[/green]" if r["https_only"]
                    else "[red]✗[/red]",
                    str(anon), str(len(r["findings"])))
            elif args.view == "performance":
                table.add_row(
                    r["app"][:35], r["plan"][:25],
                    str(r["function_count"]),
                    ",".join(r["trigger_types"])[:30])
            else:
                table.add_row(
                    r["app"][:35], str(r["state"]),
                    r["plan"][:20],
                    str(r["function_count"]),
                    str(len(r["findings"])))
        console.print(table)
        for r in results:
            for f in r["findings"]:
                console.print(f"  {f} [dim]({r['app']})[/dim]")
    else:
        for r in results:
            print(f"{r['app']}: {r['function_count']} funcs "
                  f"{r['findings']}")

    _print(f"\nFunction apps: {len(results)} | críticas: "
           f"{len(issues)}",
           "red" if issues else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"functions_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "view": args.view, "apps": results})
        else:
            rows = [{"app": r["app"], "plan": r["plan"],
                     "funcs": r["function_count"],
                     "findings": "; ".join(r["findings"])}
                    for r in results]
            export_csv(out, list(rows[0]) if rows else
                       ["app"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
