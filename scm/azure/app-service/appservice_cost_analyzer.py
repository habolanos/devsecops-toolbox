#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure App Service Cost Analyzer — Tool 32

Análisis de costos y optimización de App Service Plans,
equivalente a gcp_cloudrun_cost_analyzer /
aws_lambda_cost_analyzer:

- Planes: SKU, capacidad (workers), # apps alojadas
- Estimación mensual por precio de lista aproximado
- Planes vacíos (sin apps), planes sobredimensionados
  (apps pocas en SKU grande), SKU Free/Shared con apps prod
- Recomendaciones de right-sizing + export

Uso:
    python appservice_cost_analyzer.py --subscription <id>
    python appservice_cost_analyzer.py --period 30 -o json
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

# Precios mensuales aproximados por worker (USD, referencia
# East US Linux — informativo, no exacto)
SKU_PRICE = {
    "F1": 0, "D1": 9.49, "B1": 13.14, "B2": 26.28,
    "B3": 52.56, "S1": 69.35, "S2": 138.7, "S3": 277.4,
    "P1v2": 81.03, "P2v2": 162.06, "P3v2": 324.12,
    "P1v3": 97.09, "P2v3": 194.18, "P3v3": 388.36,
    "I1v2": 306.6, "I2v2": 613.2, "I3v2": 1226.4,
}


def plan_analysis(sub: str, plan: Dict) -> Dict:
    name, rg = plan["name"], rg_of(plan)
    sku = (plan.get("sku") or {}).get("name", "?")
    capacity = (plan.get("sku") or {}).get("capacity", 1)
    apps = try_az(["webapp", "list",
                   "--query", f"[?contains(appServicePlanId,"
                   f"'{name}')]"], sub, default=[]) or []
    price_unit = SKU_PRICE.get(sku.upper(), 0)
    monthly = price_unit * capacity
    recs = []
    if not apps:
        recs.append("Plan vacío — eliminar o consolidar")
    if sku.upper() in ("F1", "D1") and apps:
        recs.append("SKU Free/Shared en uso — limitaciones "
                    "serias para prod")
    if sku.upper().startswith("P") and len(apps) <= 1:
        recs.append("Premium con ≤1 app — evaluar SKU menor "
                    "o consolidar")
    if capacity > 3 and len(apps) <= 2:
        recs.append(f"{capacity} workers para {len(apps)} "
                    "app(s) — posible sobredimensionamiento")
    return {
        "plan": name, "resource_group": rg,
        "sku": sku, "workers": capacity,
        "apps": len(apps), "app_names": [a["name"] for a in
                                         apps][:10],
        "monthly_est": round(monthly, 2),
        "recommendations": recs,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Análisis de costos App Service Plans")
    p.add_argument("--subscription", default="")
    p.add_argument("--resource-group", default="")
    p.add_argument("--compare", action="store_true",
                   help="Ordena por costo desc.")
    p.add_argument("--period", type=int, default=30,
                   help="Días del período (informativo)")
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
    cmd = ["appservice", "plan", "list"]
    if args.resource_group:
        cmd += ["--resource-group", args.resource_group]
    plans = try_az(cmd, sub, default=[]) or []
    results = [plan_analysis(sub, p) for p in plans]
    results.sort(key=lambda r: -r["monthly_est"]
                 if args.compare else -r["monthly_est"])
    total = round(sum(r["monthly_est"] for r in results), 2)
    with_recs = [r for r in results if r["recommendations"]]

    if console:
        from rich.table import Table
        table = Table(title="App Service Plan Costs "
                            "(mensual est.)",
                      header_style="bold cyan")
        for col in ["Plan", "SKU", "Workers", "Apps",
                    "$/mes"]:
            table.add_column(col)
        for r in results[:30]:
            color = "red" if r["monthly_est"] > 200 else \
                "yellow" if r["monthly_est"] > 50 else "green"
            table.add_row(r["plan"][:30], r["sku"],
                          str(r["workers"]), str(r["apps"]),
                          f"[{color}]${r['monthly_est']}"
                          f"[/{color}]")
        console.print(table)
        console.print(f"[bold]Total estimado: ${total}/mes"
                      f"[/bold] [dim](precios de lista "
                      f"aprox.)[/dim]")
        for r in with_recs:
            for rec in r["recommendations"]:
                console.print(f"  [yellow]💡 {r['plan']}:[/"
                              f"yellow] [dim]{rec}[/dim]")
    else:
        for r in results:
            print(f"{r['plan']}: {r['sku']}x{r['workers']} "
                  f"${r['monthly_est']}/mes {r['recommendations']}")
        print(f"TOTAL: ${total}/mes")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"appservice_cost_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "total_monthly": total, "plans": results})
        else:
            rows = [{k: r[k] for k in
                     ("plan", "resource_group", "sku",
                      "workers", "apps", "monthly_est")}
                    | {"recommendations": "; ".join(
                        r["recommendations"])}
                    for r in results]
            export_csv(out, list(rows[0]) if rows else
                       ["plan"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
