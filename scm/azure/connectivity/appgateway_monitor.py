#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Application Gateway Monitor — Tool 11

Monitorea Application Gateways, equivalente a
gcp_load_balancer_checker / aws_load_balancer_checker:

- Gateways: SKU (tier/capacidad), estado operacional
- Listeners HTTP/HTTPS y certificados
- Backend pools y salud (backendhealth)
- WAF: firewall mode/policy asociada
- Hallazgos: listeners HTTP sin SSL, backends unhealthy,
  WAF en Detection en vez de Prevention

Uso:
    python appgateway_monitor.py --subscription <id>
    python appgateway_monitor.py -o json
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


def backend_health(sub: str, gw: Dict) -> Dict:
    """az network application-gateway show-backend-health."""
    return try_az(
        ["network", "application-gateway",
         "show-backend-health", "--name", gw["name"],
         "--resource-group", rg_of(gw)], sub,
        default={}) or {}


def analyze(sub: str, gw: Dict) -> Dict:
    findings = []
    listeners = gw.get("httpListeners", [])
    http_only = [l["name"] for l in listeners
                 if l.get("protocol") == "Http"]
    if http_only:
        findings.append(f"🟡 Listeners HTTP sin TLS: "
                        f"{', '.join(http_only[:3])}")
    waf_cfg = gw.get("webApplicationFirewallConfiguration", {})
    if waf_cfg and not waf_cfg.get("enabled"):
        findings.append("🟡 WAF configurado pero deshabilitado")
    if waf_cfg.get("firewallMode") == "Detection":
        findings.append("🟡 WAF en modo Detection (no "
                        "Prevention)")
    sku = gw.get("sku", {})
    health = backend_health(sub, gw)
    unhealthy = []
    for pool in health.get("backendAddressPools", []):
        for h in pool.get("backendHttpSettingsCollection",
                          []):
            for srv in h.get("servers", []):
                if srv.get("health") not in ("Up", "Healthy",
                                             None):
                    unhealthy.append(
                        srv.get("address", "?"))
    if unhealthy:
        findings.append(f"🔴 Backends unhealthy: "
                        f"{len(unhealthy)}")
    return {
        "gateway": gw["name"], "resource_group": rg_of(gw),
        "sku": f"{sku.get('tier','?')}/"
               f"{sku.get('name','?')}x{sku.get('capacity','?')}",
        "state": gw.get("operationalState"),
        "listeners": len(listeners),
        "backend_pools": len(gw.get("backendAddressPools",
                                    [])),
        "unhealthy_backends": unhealthy,
        "waf_enabled": waf_cfg.get("enabled"),
        "waf_mode": waf_cfg.get("firewallMode"),
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Application Gateway monitor")
    p.add_argument("--subscription", default="")
    p.add_argument("--resource-group", default="")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    cmd = ["network", "application-gateway", "list"]
    if args.resource_group:
        cmd += ["--resource-group", args.resource_group]
    gws = [analyze(sub, g)
           for g in (try_az(cmd, sub, default=[]) or [])]
    issues = [g for g in gws
              if any("🔴" in f for f in g["findings"])]

    if console:
        from rich.table import Table
        table = Table(title="Application Gateways",
                      header_style="bold cyan")
        for col in ["Gateway", "SKU", "Listeners", "Backends",
                    "Estado", "Findings"]:
            table.add_column(col)
        for g in gws:
            bad = any("🔴" in f for f in g["findings"])
            table.add_row(
                g["gateway"][:30], g["sku"][:20],
                str(g["listeners"]),
                str(g["backend_pools"]),
                str(g["state"]),
                f"[{'red' if bad else 'green'}]"
                f"{len(g['findings'])}"
                f"[/{'red' if bad else 'green'}]")
        console.print(table)
        for g in gws:
            for f in g["findings"]:
                console.print(f"  {f} [dim]({g['gateway']})"
                              f"[/dim]")
    else:
        for g in gws:
            print(f"{g['gateway']}: {g['state']} "
                  f"{g['findings']}")

    _print(f"\nGateways: {len(gws)} | con issues "
           f"críticos: {len(issues)}",
           "red" if issues else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"appgateways_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "gateways": gws})
        else:
            rows = [{k: g[k] for k in
                     ("gateway", "resource_group", "sku",
                      "listeners", "backend_pools", "state")}
                    | {"unhealthy": ";".join(
                        g["unhealthy_backends"]),
                       "findings": "; ".join(g["findings"])}
                    for g in gws]
            export_csv(out, list(rows[0]) if rows else
                       ["gateway"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
