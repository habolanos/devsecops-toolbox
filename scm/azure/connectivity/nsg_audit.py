#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure NSG Audit — Tool 10

Auditoría de Network Security Groups, equivalente a
aws_security_groups_checker / reglas cloud-armor:

- Reglas inbound permitidas desde 0.0.0.0/0 / Internet / *
- Puertos sensibles abiertos: SSH(22), RDP(3389), DBs
  (1433/3306/5432/27017), Kubernetes (6443)
- Reglas Any(*) en protocolo/puerto
- NSGs sin subnets asociadas (huérfanos)

Uso:
    python nsg_audit.py --subscription <id>
    python nsg_audit.py -o csv
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

RISKY_PORTS = {22: "SSH", 3389: "RDP", 1433: "SQL",
               3306: "MySQL", 5432: "PostgreSQL",
               27017: "MongoDB", 6379: "Redis",
               6443: "Kubernetes API", 9200: "Elasticsearch"}
OPEN_SOURCES = ("*", "0.0.0.0/0", "internet", "any")


def port_range(rule: Dict) -> List[int]:
    """Puertos destino de una regla (rango → representativos)."""
    port = rule.get("destinationPortRange") or ""
    if port == "*":
        return sorted(RISKY_PORTS)
    if "-" in port:
        lo, hi = port.split("-", 1)
        try:
            lo, hi = int(lo), int(hi)
            return [p for p in RISKY_PORTS if lo <= p <= hi]
        except ValueError:
            return []
    try:
        return [int(port)]
    except (TypeError, ValueError):
        return []


def audit_rule(nsg: str, rule: Dict) -> List[Dict]:
    findings = []
    if rule.get("direction") != "Inbound" or \
            rule.get("access") != "Allow":
        return findings
    src = (rule.get("sourceAddressPrefix") or "").lower()
    srcs = rule.get("sourceAddressPrefixes") or []
    sources = [src] + [s.lower() for s in srcs]
    open_src = any(s in OPEN_SOURCES or s.endswith("/0")
                   for s in sources)
    if not open_src:
        return findings
    ports = port_range(rule)
    proto = rule.get("protocol", "*")
    if rule.get("destinationPortRange") == "*":
        findings.append({
            "sev": "critical", "nsg": nsg,
            "rule": rule["name"],
            "detail": "Inbound Allow * → TODOS los puertos "
                      "desde internet"})
    for p in ports:
        if p in RISKY_PORTS:
            findings.append({
                "sev": "high", "nsg": nsg,
                "rule": rule["name"],
                "detail": f"Puerto {RISKY_PORTS[p]}({p}) "
                          f"abierto a internet ({proto})"})
    return findings


def get_args():
    p = argparse.ArgumentParser(
        description="Auditoría de NSGs")
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
    cmd = ["network", "nsg", "list"]
    if args.resource_group:
        cmd += ["--resource-group", args.resource_group]
    nsgs = try_az(cmd, sub, default=[]) or []

    findings, orphan = [], []
    for n in nsgs:
        rules = n.get("securityRules", []) + \
            n.get("defaultSecurityRules", [])
        if not n.get("subnets") and not n.get(
                "networkInterfaces"):
            orphan.append(n["name"])
        for r in rules:
            findings.extend(audit_rule(n["name"], r))

    counts = {"critical": 0, "high": 0}
    for f in findings:
        counts[f["sev"]] = counts.get(f["sev"], 0) + 1

    if console:
        from rich.table import Table
        table = Table(title="NSG Audit", header_style="bold red")
        for col in ["Sev", "NSG", "Regla", "Detalle"]:
            table.add_column(col)
        for f in sorted(findings,
                        key=lambda x: x["sev"] != "critical"):
            color = "red" if f["sev"] == "critical" else "yellow"
            table.add_row(f"[{color}]{f['sev']}[/{color}]",
                          f["nsg"][:25], f["rule"][:25],
                          f["detail"][:60])
        console.print(table)
        if orphan:
            console.print(f"[dim]NSGs sin asociar: "
                          f"{', '.join(orphan[:8])}[/dim]")
    else:
        for f in findings:
            print(f"[{f['sev']}] {f['nsg']}/{f['rule']}: "
                  f"{f['detail']}")

    _print(f"\nNSGs: {len(nsgs)} | findings: {len(findings)} "
           f"| huérfanos: {len(orphan)}",
           "red" if counts["critical"] else
           ("yellow" if findings else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"nsg_audit_{now_ts()}.{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "nsgs": len(nsgs), "orphan_nsgs": orphan,
                "findings": findings})
        else:
            export_csv(out, ["sev", "nsg", "rule", "detail"],
                       findings)
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if counts["critical"] else 0)


if __name__ == "__main__":
    main()
