#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure App Service Health Analyzer — Tool 31

Análisis profundo de salud de App Services, equivalente a
gcp_cloudrun_health_analyzer / aws_lambda_health_analyzer:

- Estado de la app + plan (número de instancias, capacidad)
- Métricas vía `az monitor metrics list`: CPU%, Memory%,
  Http5xx, ResponseTime (última hora, promedio)
- Score de salud 0-100 por app + clasificación
- Recomendaciones por síntoma (errores 5xx altos, CPU saturada)

Uso:
    python appservice_health_analyzer.py --subscription <id>
    python appservice_health_analyzer.py --app-name api
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, rg_of, now_ts, export_json)

__version__ = "1.0.0"


def metric_avg(sub: str, resource_id: str,
               metric: str, hours: int = 1,
               aggregation: str = "Average") -> Optional[float]:
    """Promedio de una métrica de Azure Monitor en la ventana."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    res = try_az([
        "monitor", "metrics", "list",
        "--resource", resource_id,
        "--metric", metric,
        "--aggregation", aggregation,
        "--start-time", start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--end-time", end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--interval", "PT5M"], sub, default=None)
    try:
        points = []
        for ts in (res or {}).get("value", []):
            for serie in ts.get("timeseries", []):
                for d in serie.get("data", []):
                    v = d.get(aggregation.lower()) or \
                        d.get(aggregation.capitalize())
                    if v is not None:
                        points.append(v)
        return sum(points) / len(points) if points else None
    except Exception:
        return None


def health_score(m: Dict) -> int:
    """Score 0-100 según métricas."""
    score = 100
    if m.get("http5xx") and m["http5xx"] > 5:
        score -= 40 if m["http5xx"] > 20 else 20
    if m.get("cpu_pct") and m["cpu_pct"] > 85:
        score -= 30
    elif m.get("cpu_pct") and m["cpu_pct"] > 70:
        score -= 15
    if m.get("mem_pct") and m["mem_pct"] > 85:
        score -= 30
    elif m.get("mem_pct") and m["mem_pct"] > 70:
        score -= 15
    if m.get("response_ms") and m["response_ms"] > 2000:
        score -= 10
    return max(0, score)


def status_label(score: int) -> str:
    return "CRITICAL" if score < 50 else \
        "DEGRADED" if score < 75 else "HEALTHY"


def analyze(sub: str, app: Dict) -> Dict:
    rid = app.get("id", "")
    m = {
        "cpu_pct": metric_avg(sub, rid, "CpuPercentage"),
        "mem_pct": metric_avg(sub, rid, "MemoryPercentage"),
        "http5xx": metric_avg(sub, rid, "Http5xx", 1, "Total"),
        "response_ms": metric_avg(sub, rid,
                                  "HttpResponseTime",
                                  1, "Average"),
    }
    if m["response_ms"]:
        m["response_ms"] = round(m["response_ms"] * 1000, 0)
    score = health_score(m)
    recs = []
    if m["http5xx"] and m["http5xx"] > 5:
        recs.append("Revisar logs de aplicación — 5xx elevados")
    if m["cpu_pct"] and m["cpu_pct"] > 85:
        recs.append("Escalar el plan (más instancias o SKU "
                    "mayor)")
    if m["response_ms"] and m["response_ms"] > 2000:
        recs.append("Latencia >2s — perfilar endpoints")
    return {
        "app": app["name"], "resource_group": rg_of(app),
        "state": app.get("state"), "metrics": m,
        "score": score, "status": status_label(score),
        "recommendations": recs,
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Análisis de salud de App Services")
    p.add_argument("--subscription", default="")
    p.add_argument("--resource-group", default="")
    p.add_argument("--app-name", default="")
    p.add_argument("--output", choices=["json", "table"],
                   default="table")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--timezone", default="")
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

    results = [analyze(sub, a) for a in apps]
    unhealthy = [r for r in results
                 if r["status"] != "HEALTHY"]

    if console:
        from rich.table import Table
        table = Table(title="App Service Health",
                      header_style="bold cyan")
        for col in ["App", "Score", "CPU%", "MEM%", "5xx",
                    "Resp ms", "Estado"]:
            table.add_column(col)
        style = {"HEALTHY": "green", "DEGRADED": "yellow",
                 "CRITICAL": "red"}
        for r in results:
            m = r["metrics"]
            table.add_row(
                r["app"][:35], str(r["score"]),
                f"{m['cpu_pct']:.0f}" if m["cpu_pct"]
                else "—",
                f"{m['mem_pct']:.0f}" if m["mem_pct"]
                else "—",
                f"{m['http5xx']:.0f}" if m["http5xx"]
                else "0",
                f"{m['response_ms']:.0f}"
                if m["response_ms"] else "—",
                f"[{style[r['status']]}]{r['status']}"
                f"[/{style[r['status']]}]")
        console.print(table)
        for r in results:
            for rec in r["recommendations"]:
                console.print(f"  💡 {r['app']}: "
                              f"[dim]{rec}[/dim]")
    else:
        for r in results:
            print(f"{r['app']}: {r['status']} "
                  f"score={r['score']}")

    _print(f"\nApps: {len(results)} | no healthy: "
           f"{len(unhealthy)}",
           "red" if unhealthy else "green")

    if args.output == "json":
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"appservice_health_{now_ts()}.json"
        export_json(out, {
            "timestamp": datetime.utcnow().isoformat(),
            "apps": results})
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if unhealthy else 0)


if __name__ == "__main__":
    main()
