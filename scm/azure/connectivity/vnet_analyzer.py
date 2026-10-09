#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure VNet Analyzer — Tool 9

Análisis de Virtual Networks, equivalente a
gcp_vpc_networks_checker / aws_vpc_checker:

- VNets: address space, subnets, peerings, DDoS protection
- Subnets: prefijos, NSG asociado, delegaciones, endpoints
- Hallazgos: subnets sin NSG, VNet sin DDoS, address space
  casi lleno (count IPs disponibles vs usadas aproximado)

Uso:
    python vnet_analyzer.py --subscription <id>
    python vnet_analyzer.py --resource-group rg -o json
"""

import argparse
import ipaddress
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, rg_of, now_ts, export_json, export_csv)

__version__ = "1.0.0"

AZURE_RESERVED_IPS = 5


def analyze_vnet(v: Dict) -> Dict:
    findings = []
    prefixes = (v.get("addressSpace") or {}) \
        .get("addressPrefixes", [])
    total_ips = sum(ipaddress.ip_network(p, strict=False)
                    .num_addresses for p in prefixes)
    subnets = v.get("subnets", [])
    used_ips = 0
    subnet_rows = []
    for s in subnets:
        pfx = s.get("addressPrefix") or \
            (s.get("addressPrefixes") or [None])[0]
        size = ipaddress.ip_network(
            pfx, strict=False).num_addresses if pfx else 0
        nsg = (s.get("networkSecurityGroup") or {}).get("id")
        if not nsg and s.get("name") != "GatewaySubnet":
            findings.append(f"🟡 Subnet {s['name']} sin NSG")
        if (s.get("delegations")):
            findings.append(f"ℹ️ Subnet {s['name']} delegada: "
                            f"{s['delegations'][0].get('name', '?')}")
        used_ips += size
        subnet_rows.append({
            "name": s["name"], "prefix": pfx, "ips": size,
            "nsg": bool(nsg),
            "delegated": bool(s.get("delegations")),
            "private_endpoints": len(
                s.get("privateEndpoints", [])),
        })
    if not v.get("enableDdosProtection"):
        findings.append("ℹ️ DDoS protection plan deshabilitado")
    if used_ips and total_ips and used_ips / total_ips > 0.9:
        findings.append(f"🟡 Address space ~"
                        f"{int(100*used_ips/total_ips)}% asignado "
                        "a subnets")
    return {
        "vnet": v["name"], "resource_group": rg_of(v),
        "location": v.get("location"),
        "address_space": prefixes, "total_ips": total_ips,
        "subnets": subnet_rows,
        "peerings": len(v.get("virtualNetworkPeerings", [])),
        "ddos": v.get("enableDdosProtection", False),
        "findings": findings,
    }


def get_args():
    p = argparse.ArgumentParser(description="VNet analyzer")
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
    cmd = ["network", "vnet", "list"]
    if args.resource_group:
        cmd += ["--resource-group", args.resource_group]
    vnets = [analyze_vnet(v)
             for v in (try_az(cmd, sub, default=[]) or [])]
    no_nsg = [s for v in vnets for s in v["subnets"]
              if not s["nsg"] and s["name"] != "GatewaySubnet"]

    if console:
        from rich.table import Table
        t1 = Table(title="Virtual Networks",
                   header_style="bold cyan")
        for col in ["VNet", "RG", "Address space", "Subnets",
                    "Peerings", "Findings"]:
            t1.add_column(col)
        for v in vnets:
            bad = any("🟡" in f or "🔴" in f
                      for f in v["findings"])
            t1.add_row(
                v["vnet"][:25], v["resource_group"][:18],
                ",".join(v["address_space"])[:25],
                str(len(v["subnets"])),
                str(v["peerings"]),
                f"[{'yellow' if bad else 'green'}]"
                f"{len(v['findings'])}"
                f"[/{'yellow' if bad else 'green'}]")
        console.print(t1)
        for v in vnets:
            for f in v["findings"]:
                console.print(f"  {f} [dim]({v['vnet']})[/dim]")
    else:
        for v in vnets:
            print(f"{v['vnet']}: {v['address_space']} "
                  f"subnets={len(v['subnets'])}")

    _print(f"\nVNets: {len(vnets)} | subnets sin NSG: "
           f"{len(no_nsg)}",
           "yellow" if no_nsg else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"vnets_{now_ts()}.{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "vnets": vnets})
        else:
            rows = [{"vnet": v["vnet"],
                     "rg": v["resource_group"],
                     "subnet": s["name"], "prefix": s["prefix"],
                     "nsg": s["nsg"]}
                    for v in vnets for s in v["subnets"]]
            export_csv(out, ["vnet", "rg", "subnet", "prefix",
                             "nsg"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
