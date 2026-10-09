#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Lambda Cost Analyzer — Tool 31

Análisis de costos de funciones Lambda usando métricas CloudWatch:

- Invocaciones y duración promedio por función (período configurable)
- Costo estimado: requests (precio/1M) + GB-segundos de cómputo
- Top cost drivers y funciones zombie (memoria alta + 0 invocaciones)
- Recomendaciones de right-sizing (memoria alta vs duración baja)

Equivalente a GCP Tool: Cloud Run Cost Analyzer
(cloud-run/gcp_cloudrun_cost_analyzer.py).

Uso:
    python aws_lambda_cost_analyzer.py --profile p --region us-east-1
    python aws_lambda_cost_analyzer.py --period 30 -o json
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "DevSecOps Team"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None

# Precios Lambda x86 (us-east-1, referenciales)
PRICE_PER_REQUEST = 0.0000002           # $0.20 / 1M requests
PRICE_PER_GB_SECOND = 0.0000166667      # $0.0000166667 / GB-s


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# CloudWatch
# ═══════════════════════════════════════════════════════════════════════════════

def get_metric_sum(cw, function_name: str, metric: str, days: int,
                   stat: str = "Sum") -> float:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    try:
        resp = cw.get_metric_statistics(
            Namespace="AWS/Lambda", MetricName=metric,
            Dimensions=[{"Name": "FunctionName",
                         "Value": function_name}],
            StartTime=start, EndTime=end, Period=86400,
            Statistics=[stat])
        points = resp.get("Datapoints", [])
        if not points:
            return 0.0
        if stat == "Sum":
            return sum(p["Sum"] for p in points)
        return sum(p[stat] for p in points) / len(points)
    except Exception:
        return 0.0


def estimate_cost(memory_mb: int, avg_duration_ms: float,
                  invocations: float) -> Dict:
    """Estimación de costo Lambda para el período."""
    gb_s = (memory_mb / 1024.0) * (avg_duration_ms / 1000.0) * invocations
    compute = gb_s * PRICE_PER_GB_SECOND
    requests = invocations * PRICE_PER_REQUEST
    return {"gb_seconds": round(gb_s, 2),
            "compute_cost": round(compute, 4),
            "request_cost": round(requests, 4),
            "total_cost": round(compute + requests, 4)}


def cost_recommendations(fn: Dict) -> List[str]:
    recs = []
    mem = fn.get("memory_mb") or 0
    inv = fn.get("invocations", 0)
    avg_ms = fn.get("avg_duration_ms", 0)
    if inv == 0:
        recs.append("ZOMBIE: 0 invocaciones en el período — "
                    "candidata a eliminar")
    if mem >= 2048 and 0 < avg_ms < 500:
        recs.append(f"Memoria {mem}MB alta para duración {avg_ms}ms — "
                    "evaluar reducir")
    if mem <= 256 and avg_ms > 5000:
        recs.append(f"Duración {avg_ms}ms alta con {mem}MB — "
                    "más memoria puede reducir GB-s")
    if (fn.get("total_cost") or 0) > 10:
        recs.append("Costo > $10 en el período — revisar eficiencia")
    return recs


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Análisis de costos de funciones Lambda")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--function", "-f", default="")
    parser.add_argument("--period", type=int, default=7,
                        help="Días de métricas (default 7)")
    parser.add_argument("-o", "--output", choices=["json", "csv"],
                        default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = get_args()

    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)

    try:
        session = boto3.Session(profile_name=args.profile,
                                region_name=args.region)
        lam = session.client("lambda")
        cw = session.client("cloudwatch")
    except Exception as e:
        _print(f"❌ Error de sesión AWS: {e}", "red")
        sys.exit(1)

    functions = []
    try:
        for page in lam.get_paginator("list_functions").paginate():
            for fn in page.get("Functions", []):
                if args.function and args.function.lower() not in \
                        fn["FunctionName"].lower():
                    continue
                functions.append(fn)
    except Exception as e:
        _print(f"❌ list_functions: {e}", "red")
        sys.exit(1)

    results = []
    for fn in functions:
        name = fn["FunctionName"]
        inv = get_metric_sum(cw, name, "Invocations", args.period)
        avg_ms = get_metric_sum(cw, name, "Duration", args.period,
                                stat="Average")
        cost = estimate_cost(fn.get("MemorySize", 128), avg_ms, inv)
        row = {"name": name, "memory_mb": fn.get("MemorySize"),
               "timeout_s": fn.get("Timeout"),
               "invocations": int(inv),
               "avg_duration_ms": round(avg_ms, 1), **cost}
        row["recommendations"] = cost_recommendations(row)
        results.append(row)

    results.sort(key=lambda r: -r["total_cost"])
    total = round(sum(r["total_cost"] for r in results), 4)

    if console:
        table = Table(
            title=f"Lambda Cost — últimos {args.period} días",
            header_style="bold cyan")
        for col in ["Función", "Invoc.", "Avg ms", "GB-s",
                    "Est. $"]:
            table.add_column(col)
        for r in results[:30]:
            color = "red" if r["total_cost"] > 10 else \
                    "yellow" if r["total_cost"] > 1 else "green"
            table.add_row(r["name"][:40], f"{r['invocations']:,}",
                          str(r["avg_duration_ms"]),
                          f"{r['gb_seconds']:,}",
                          f"[{color}]${r['total_cost']}[/{color}]")
        console.print(table)
        for r in results:
            for rec in r["recommendations"]:
                console.print(f"  [yellow]💡 {r['name']}:[/yellow] "
                              f"[dim]{rec}[/dim]")
        console.print(f"\n[bold]Total estimado ({args.period}d): "
                      f"${total}[/bold] "
                      f"[dim](precios referenciales us-east-1 x86)[/dim]")
    else:
        for r in results:
            print(f"{r['name']}: {r['invocations']} inv, "
                  f"{r['avg_duration_ms']}ms, ${r['total_cost']}")
        print(f"TOTAL: ${total}")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"lambda_cost_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "region": args.region, "period_days": args.period,
                "total_estimated_cost": total,
                "pricing_note": "us-east-1 x86 referencial",
                "functions": results,
            }, indent=2), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "name", "memory_mb", "invocations",
                    "avg_duration_ms", "gb_seconds", "total_cost"])
                w.writeheader()
                for r in results:
                    w.writerow({k: r[k] for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
