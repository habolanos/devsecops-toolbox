#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure WAF / Front Door Checker — Tool 27

Auditoría de Web Application Firewall en Azure Front Door,
equivalente a aws_waf_checker / gcp cloud-armor:

- Políticas WAF: modo (Detection vs Prevention), estado,
  managed rulesets habilitados, custom rules
- Front Doors: WAF asociado a frontend endpoints o sin WAF
- Hallazgos: WAF en Detection, sin managed rules, endpoints
  sin protección

Uso:
    python azure_waf_checker.py --subscription <id>
    python azure_waf_checker.py --view policies|frontdoors
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


def analyze_policy(p: Dict) -> Dict:
    findings = []
    settings = p.get("policySettings", {})
    if settings.get("mode") != "Prevention":
        findings.append("🔴 Modo Detection — no bloquea")
    if settings.get("state") != "Enabled":
        findings.append("🔴 Política deshabilitada")
    managed = (p.get("managedRules") or {}) \
        .get("managedRuleSets", [])
    if not managed:
        findings.append("🟡 Sin managed rulesets")
    custom = p.get("customRules", {})
    rules = custom.get("rules", [])
    disabled = [r["name"] for r in rules
                if not r.get("enabled", True)]
    if disabled:
        findings.append(f"🟡 Custom rules deshabilitadas: "
                        f"{', '.join(disabled[:3])}")
    return {
        "policy": p["name"], "resource_group": rg_of(p),
        "mode": settings.get("mode"),
        "state": settings.get("state"),
        "managed_rulesets": len(managed),
        "custom_rules": len(rules),
        "redirect_https": settings.get(
            "redirectEnabled", False),
        "findings": findings,
    }


def analyze_frontdoor(fd: Dict, policies: List[Dict]
                      ) -> Dict:
    findings = []
    waf_link = (fd.get("frontendEndpoints", [{}])[0]
                .get("webApplicationFirewallPolicyLink") or {})
    policy_id = waf_link.get("id", "")
    https_endpoints = [fe for fe in
                       fd.get("frontendEndpoints", [])
                       if (fe.get(
                           "frontendEndpointType") or
                           fe.get("hostName"))]
    for fe in fd.get("frontendEndpoints", []):
        link = (fe.get(
            "webApplicationFirewallPolicyLink") or {})
        if not link.get("id"):
            findings.append(
                f"🔴 Endpoint {fe.get('hostName','?')[:40]} "
                "sin WAF")
    if not https_endpoints:
        findings.append("ℹ️ Sin frontend endpoints")
    https_only = all(
        fe.get("sessionAffinityEnabledState") is not None or
        True for fe in https_endpoints)
    return {
        "frontdoor": fd["name"], "resource_group": rg_of(fd),
        "state": fd.get("enabledState"),
        "endpoints": len(fd.get("frontendEndpoints", [])),
        "backend_pools": len(fd.get("backendPools", [])),
        "waf_policy": policy_id.rsplit("/", 1)[-1]
        if policy_id else None,
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Auditoría WAF / Front Door")
    p.add_argument("--subscription", default="")
    p.add_argument("--view",
                   choices=["all", "policies", "frontdoors"],
                   default="all")
    p.add_argument("--severity",
                   choices=["all", "critical", "warning"],
                   default="all")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)

    policies = []
    if args.view in ("all", "policies"):
        policies = [analyze_policy(p) for p in
                    (try_az(["network", "front-door",
                             "waf-policy", "list"], sub,
                            default=[]) or [])]
    frontdoors = []
    if args.view in ("all", "frontdoors"):
        fds = try_az(["network", "front-door", "list"], sub,
                     default=[]) or []
        frontdoors = [analyze_frontdoor(fd, policies)
                      for fd in fds]

    if args.severity == "critical":
        for coll in (policies, frontdoors):
            for item in coll:
                item["findings"] = [f for f in item["findings"]
                                    if "🔴" in f]
    elif args.severity == "warning":
        for coll in (policies, frontdoors):
            for item in coll:
                item["findings"] = [f for f in item["findings"]
                                    if "ℹ" not in f]

    issues = sum(1 for coll in (policies, frontdoors)
                 for i in coll
                 if any("🔴" in f for f in i["findings"]))

    if console:
        from rich.table import Table
        if policies:
            t = Table(title="WAF Policies",
                      header_style="bold cyan")
            for col in ["Policy", "Mode", "State", "Rules",
                        "Findings"]:
                t.add_column(col)
            for p in policies:
                color = "green" if p["mode"] == "Prevention" \
                    and p["state"] == "Enabled" else "red"
                t.add_row(p["policy"][:30],
                          f"[{color}]{p['mode']}[/{color}]",
                          str(p["state"]),
                          f"{p['managed_rulesets']}m/"
                          f"{p['custom_rules']}c",
                          str(len(p["findings"])))
            console.print(t)
        if frontdoors:
            t2 = Table(title="Front Doors",
                       header_style="bold magenta")
            for col in ["FrontDoor", "Endpoints", "WAF",
                        "Findings"]:
                t2.add_column(col)
            for fd in frontdoors:
                t2.add_row(fd["frontdoor"][:30],
                           str(fd["endpoints"]),
                           fd["waf_policy"] or "[red]✗[/red]",
                           str(len(fd["findings"])))
            console.print(t2)
        for coll in (policies, frontdoors):
            for item in coll:
                name = item.get("policy") or item["frontdoor"]
                for f in item["findings"]:
                    console.print(f"  {f} [dim]({name})[/dim]")
    else:
        for coll in (policies, frontdoors):
            for i in coll:
                print(i)

    _print(f"\nWAF policies: {len(policies)} | Front Doors: "
           f"{len(frontdoors)} | críticos: {issues}",
           "red" if issues else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"waf_check_{now_ts()}.{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "policies": policies,
                "frontdoors": frontdoors})
        else:
            rows = [{"type": "policy", "name": p["policy"],
                     "findings": "; ".join(p["findings"])}
                    for p in policies] + \
                   [{"type": "frontdoor", "name": f["frontdoor"],
                     "findings": "; ".join(f["findings"])}
                    for f in frontdoors]
            export_csv(out, ["type", "name", "findings"], rows)
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
