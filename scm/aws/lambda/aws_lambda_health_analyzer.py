#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Lambda Health Analyzer — Tool 34

Análisis de salud y rendimiento de funciones Lambda (CloudWatch):

- Error rate, throttles, duración avg/p95, concurrent executions
- Health score por función (0-100) con semáforo
- Funciones con errores sostenidos, throttling o latencia degradada
- Timeout risk: duración p95 vs timeout configurado

Equivalente a GCP Tool: Cloud Run Health Analyzer
(cloud-run/gcp_cloudrun_health_analyzer.py).

Uso:
    python aws_lambda_health_analyzer.py --profile p --region us-east-1
    python aws_lambda_health_analyzer.py --function my-fn -o json
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

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

DEFAULT_PERIOD_DAYS = 7


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Métricas
# ═══════════════════════════════════════════════════════════════════════════════

def get_metric(cw, function_name: str, metric: str, days: int,
               stat: str = "Sum") -> float:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    try:
        resp = cw.get_metric_statistics(
            Namespace="AWS/Lambda", MetricName=metric,
            Dimensions=[{"Name": "FunctionName",
                         "Value": function_name}],
            StartTime=start, EndTime=end, Period=3600,
            Statistics=[stat])
        points = resp.get("Datapoints", [])
        if not points:
            return 0.0
        if stat == "Sum":
            return sum(p["Sum"] for p in points)
        if stat == "Maximum":
            return max(p["Maximum"] for p in points)
        return sum(p[stat] for p in points) / len(points)
    except Exception:
        return 0.0


def get_duration_p95(cw, function_name: str, days: int) -> float:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    try:
        resp = cw.get_metric_statistics(
            Namespace="AWS/Lambda", MetricName="Duration",
            Dimensions=[{"Name": "FunctionName",
                         "Value": function_name}],
            StartTime=start, EndTime=end, Period=3600,
            ExtendedStatistics=["p95"])
        points = resp.get("Datapoints", [])
        if not points:
            return 0.0
        return max(p.get("ExtendedStatistics", {}).get("p95", 0)
                   for p in points)
    except Exception:
        return 0.0


def compute_health(m: Dict) -> Dict:
    """Score 0-100 basado en error rate, throttles y timeout risk."""
    score = 100.0
    issues = []
    inv = m.get("invocations", 0)
    if inv == 0:
        return {"score": None, "grade": "IDLE",
                "issues": ["sin invocaciones en el período"]}

    error_rate = m.get("errors", 0) / inv * 100
    if error_rate >= 5:
        score -= 40; issues.append(f"error rate {error_rate:.1f}%")
    elif error_rate >= 1:
        score -= 20; issues.append(f"error rate {error_rate:.1f}%")
    elif error_rate > 0:
        score -= 5; issues.append(f"error rate {error_rate:.2f}%")

    if m.get("throttles", 0) > 0:
        score -= 25
        issues.append(f"{int(m['throttles'])} throttles")

    timeout_ms = (m.get("timeout_s") or 0) * 1000
    p95 = m.get("duration_p95_ms", 0)
    if timeout_ms and p95 > timeout_ms * 0.9:
        score -= 25
        issues.append(f"p95 {p95:.0f}ms ≈ timeout {timeout_ms}ms")
    elif timeout_ms and p95 > timeout_ms * 0.7:
        score -= 10
        issues.append(f"p95 {p95:.0f}ms cerca del timeout")

    score = max(0.0, round(score, 1))
    grade = ("HEALTHY" if score >= 90 else
             "WARNING" if score >= 70 else
             "CRITICAL" if score >= 40 else "FAILING")
    return {"score": score, "grade": grade, "issues": issues,
            "error_rate_pct": round(error_rate, 2)}


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

GRADE_STYLE = {"HEALTHY": "green", "WARNING": "yellow",
               "CRITICAL": "red", "FAILING": "red bold",
               "IDLE": "dim"}


def get_args():
    parser = argparse.ArgumentParser(
        description="Análisis de salud de funciones Lambda")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--function", "-f", default="")
    parser.add_argument("--period", type=int,
                        default=DEFAULT_PERIOD_DAYS)
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
        m = {
            "name": name,
            "runtime": fn.get("Runtime"),
            "timeout_s": fn.get("Timeout"),
            "memory_mb": fn.get("MemorySize"),
            "invocations": int(get_metric(
                cw, name, "Invocations", args.period)),
            "errors": int(get_metric(cw, name, "Errors", args.period)),
            "throttles": int(get_metric(
                cw, name, "Throttles", args.period)),
            "duration_p95_ms": round(
                get_duration_p95(cw, name, args.period), 1),
            "concurrent_max": int(get_metric(
                cw, name, "ConcurrentExecutions", args.period,
                stat="Maximum")),
        }
        m.update(compute_health(m))
        results.append(m)

    results.sort(key=lambda r: (r["score"] is None,
                                r["score"] or 0))

    if console:
        table = Table(
            title=f"Lambda Health — últimos {args.period} días",
            header_style="bold cyan")
        for col in ["Función", "Invoc.", "Err%", "Throt.",
                    "p95 ms", "Score", "Estado"]:
            table.add_column(col)
        for r in results:
            color = GRADE_STYLE.get(r["grade"], "")
            table.add_row(
                r["name"][:38], f"{r['invocations']:,}",
                str(r.get("error_rate_pct", 0)),
                str(r["throttles"]), str(r["duration_p95_ms"]),
                str(r["score"]) if r["score"] is not None else "—",
                f"[{color}]{r['grade']}[/{color}]")
        console.print(table)
        for r in results:
            if r["grade"] in ("CRITICAL", "FAILING"):
                console.print(f"  [red]⚠ {r['name']}:[/red] "
                              f"[dim]{', '.join(r['issues'])}[/dim]")
    else:
        for r in results:
            print(f"{r['name']}: {r['grade']} "
                  f"score={r['score']} issues={r['issues']}")

    unhealthy = len([r for r in results
                     if r["grade"] in ("CRITICAL", "FAILING")])
    _print(f"\nFunciones: {len(results)} | "
           f"unhealthy: {unhealthy}",
           "red" if unhealthy else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"lambda_health_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "region": args.region, "period_days": args.period,
                "functions": results,
            }, indent=2), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "name", "invocations", "errors", "throttles",
                    "duration_p95_ms", "score", "grade"])
                w.writeheader()
                for r in results:
                    w.writerow({k: r.get(k) for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
