#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure App Service Traffic Analyzer — Tool 33

Análisis de tráfico y distribución entre App Services,
equivalente a gcp_cloudrun_traffic_analyzer:

- Requests por app (métrica Requests de Azure Monitor)
- Distribution entre deployment slots (traffic-routing)
- Errores 4xx/5xx rate, latencia promedio
- Detección de apps sin tráfico (zombies) y desbalanceo

Uso:
    python appservice_traffic_analyzer.py --subscription <id>
    python appservice_traffic_analyzer.py --period 24
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, rg_of, now_ts, export_json, export_csv)

__version__ = "1.0.0"


def metric(sub: str, rid: str, name: str, hours: int,
           aggregation: str = "Total") -> Optional[float]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    res = try_az([
        "monitor", "metrics", "list", "--resource", rid,
        "--metric", name, "--aggregation", aggregation,
        "--start-time", start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--end-time", end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--interval", "PT1H"], sub, default=None)
    try:
        total = 0.0
        for ts in (res or {}).get("value", []):
            for serie in ts.get("timeseries", []):
                for d in serie.get("data", []):
                    total += d.get("total") or d.get(
                        "average") or 0
        return total
    except Exception:
        return None


def slot_traffic(sub: str, app: Dict) -> Dict:
    """Distribución % entre slots (az webapp traffic-routing)."""
    routing = try_az(["webapp", "traffic-routing", "show",
                      "--name", app["name"],
                      "--resource-group", rg_of(app)], sub,
                     default=[]) or []
    return {r.get("actionHostName", "?").split(".")[0]:
            r.get("reroutePercentage", 0) for r in routing}


def analyze(sub: str, app: Dict, hours: int) -> Dict:
    rid = app.get("id", "")
    requests = metric(sub, rid, "Requests", hours)
    err5 = metric(sub, rid, "Http5xx", hours) or 0
    err4 = metric(sub, rid, "Http4xx", hours) or 0
    resp = metric(sub, rid, "HttpResponseTime", hours,
                  "Average")
    error_rate = (err5 / requests * 100) if requests else 0
    return {
        "app": app["name"], "resource_group": rg_of(app),
        "state": app.get("state"),
        "requests": requests, "http5xx": err5,
        "http4xx": err4,
        "error_rate": round(error_rate, 2),
        "avg_response_s": round(resp, 3) if resp else None,
        "slot_traffic": slot_traffic(sub, app),
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Análisis de tráfico App Services")
    p.add_argument("--subscription", default="")
    p.add_argument("--resource-group", default="")
    p.add_argument("--app-name", default="")
    p.add_argument("--period", type=int, default=24,
                   help="Horas de la ventana")
    p.add_argument("--output", choices=["json", "csv"],
                   default="")
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

    results = [analyze(sub, a, args.period) for a in apps]
    results.sort(key=lambda r: -(r["requests"] or 0))
    zombies = [r for r in results
               if r["state"] == "Running" and
               not r["requests"]]
    high_err = [r for r in results if r["error_rate"] > 5]

    if console:
        from rich.table import Table
        table = Table(title=f"App Service Traffic "
                            f"({args.period}h)",
                      header_style="bold cyan")
        for col in ["App", "Requests", "5xx", "Err%",
                    "Resp s", "Slots"]:
            table.add_column(col)
        for r in results[:40]:
            color = "red" if r["error_rate"] > 5 else \
                "yellow" if r["error_rate"] > 1 else "green"
            slots = "; ".join(f"{k}:{v}%"
                              for k, v in
                              r["slot_traffic"].items()) or "—"
            table.add_row(
                r["app"][:35],
                f"{r['requests']:.0f}"
                if r["requests"] else "0",
                f"{r['http5xx']:.0f}",
                f"[{color}]{r['error_rate']}%[/{color}]",
                str(r["avg_response_s"] or "—"), slots)
        console.print(table)
        if zombies:
            console.print(f"[dim]Zombies (running sin "
                          f"tráfico): {', '.join(z['app'] for z in zombies[:8])}[/dim]")
    else:
        for r in results:
            print(f"{r['app']}: req={r['requests']} "
                  f"err={r['error_rate']}%")

    _print(f"\nApps: {len(results)} | zombies: "
           f"{len(zombies)} | err>5%: {len(high_err)}",
           "red" if high_err else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"appservice_traffic_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "period_hours": args.period,
                "apps": results})
        else:
            rows = [{"app": r["app"], "requests": r["requests"],
                     "http5xx": r["http5xx"],
                     "error_rate": r["error_rate"],
                     "avg_response_s": r["avg_response_s"]}
                    for r in results]
            export_csv(out, list(rows[0]) if rows else
                       ["app"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
