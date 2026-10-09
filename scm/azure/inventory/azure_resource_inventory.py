#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Resource Inventory — Tool 22

Inventario completo de recursos de la suscripción, equivalente a
generar-inventario-csv (GCP) / aws_inventory_generator:

- `az resource list` completo: tipo, RG, location, nombre
- Conteos por tipo/RG/location
- Export CSV/JSON con el inventario completo

Uso:
    python azure_resource_inventory.py --subscription <id>
    python azure_resource_inventory.py -o csv
"""

import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, now_ts, export_json, export_csv)

__version__ = "1.0.0"


def collect(sub: str) -> Dict:
    resources = try_az(
        ["resource", "list",
         "--query", "[].{name:name,type:type,rg:resourceGroup,"
         "location:location,kind:kind}"], sub,
        default=[]) or []
    by_type = Counter(r["type"].split("/")[-1]
                      for r in resources)
    by_rg = Counter(r["rg"] for r in resources)
    by_loc = Counter(r["location"] for r in resources)
    return {
        "resources": resources,
        "total": len(resources),
        "by_type": dict(by_type.most_common()),
        "by_rg": dict(by_rg.most_common()),
        "by_location": dict(by_loc.most_common()),
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Inventario completo de recursos Azure")
    p.add_argument("--subscription", default="")
    p.add_argument("-o", "--output", choices=["json", "csv"],
                   default="csv")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    data = collect(sub)

    if console:
        from rich.table import Table
        t1 = Table(title=f"Top tipos ({data['total']} "
                         f"recursos)", header_style="bold cyan")
        t1.add_column("Tipo")
        t1.add_column("Count", justify="right")
        for t, c in list(data["by_type"].items())[:15]:
            t1.add_row(t, str(c))
        console.print(t1)
        t2 = Table(title="Por location",
                   header_style="bold magenta")
        t2.add_column("Location")
        t2.add_column("Count", justify="right")
        for loc, c in list(data["by_location"].items())[:10]:
            t2.add_row(loc, str(c))
        console.print(t2)
    else:
        print(f"total={data['total']} "
              f"types={len(data['by_type'])} "
              f"rgs={len(data['by_rg'])}")

    OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTCOME_DIR / f"azure_inventory_{now_ts()}" \
                        f".{args.output}"
    if args.output == "json":
        export_json(out, {
            "timestamp": datetime.utcnow().isoformat(),
            "subscription": sub, **data})
    else:
        export_csv(out, ["name", "type", "rg", "location",
                         "kind"], data["resources"])
    _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
