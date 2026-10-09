#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Lambda Functions Analyzer — Tool 28

Análisis profundo de funciones Lambda:

- Inventario completo: runtime, memoria, timeout, arquitectura,
  última modificación
- Vistas: summary (default), security (env vars sensibles, políticas
  públicas, VPC), performance (memoria vs timeout, runtimes EOL)
- Detección de secretos en variables de entorno (patrones)
- Funciones sin VPC, sin DLQ, sin tracing, con runtime deprecado

Equivalente a GCP Tool: Cloud Functions Analyzer /
Cloud Run Health Analyzer.

Uso:
    python aws_lambda_analyzer.py --profile p --region us-east-1 -o json
    python aws_lambda_analyzer.py --function my-fn --view security
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
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
    from botocore.exceptions import ClientError
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

# Runtimes EOL o próximos (deprecados por AWS)
EOL_RUNTIMES = {
    "python2.7", "python3.6", "python3.7", "python3.8",
    "nodejs10.x", "nodejs12.x", "nodejs14.x", "nodejs16.x",
    "nodejs18.x",  # EOL anunciado 2025
    "dotnetcore3.1", "dotnet6", "ruby2.7", "java8", "go1.x",
    "provided",   # AL1 deprecated
}

SECRET_PATTERN = re.compile(
    r"(pass(word)?|secret|token|api[-_]?key|private[-_]?key|"
    r"credential|auth|pwd)", re.IGNORECASE)


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Recolección
# ═══════════════════════════════════════════════════════════════════════════════

def list_functions(client, name_filter: str = "") -> List[Dict]:
    functions = []
    paginator = client.get_paginator("list_functions")
    for page in paginator.paginate():
        for fn in page.get("Functions", []):
            if name_filter and name_filter.lower() not in \
                    fn["FunctionName"].lower():
                continue
            functions.append(fn)
    return functions


def get_function_policy(client, function_name: str) -> Optional[Dict]:
    try:
        resp = client.get_policy(FunctionName=function_name)
        return json.loads(resp["Policy"])
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return None
        return None


def policy_is_public(policy: Optional[Dict]) -> bool:
    if not policy:
        return False
    for stmt in policy.get("Statement", []):
        principal = stmt.get("Principal", {})
        if stmt.get("Effect") == "Allow" and (
                principal == "*" or principal.get("AWS") == "*"):
            return True
    return False


def analyze_function(client, fn: Dict) -> Dict:
    env = fn.get("Environment", {}).get("Variables", {})
    sensitive_env = [k for k in env if SECRET_PATTERN.search(k)]
    runtime = fn.get("Runtime", "")
    policy = get_function_policy(client, fn["FunctionName"])

    issues = []
    if runtime in EOL_RUNTIMES:
        issues.append("runtime EOL/deprecado")
    if sensitive_env:
        issues.append(f"{len(sensitive_env)} var(s) sensibles en env")
    if not fn.get("VpcConfig", {}).get("SubnetIds"):
        issues.append("sin VPC")
    if not fn.get("DeadLetterConfig", {}).get("TargetArn"):
        issues.append("sin DLQ")
    if fn.get("TracingConfig", {}).get("Mode") != "Active":
        issues.append("tracing deshabilitado")
    if policy_is_public(policy):
        issues.append("policy permite principal '*' (pública)")

    last_mod = fn.get("LastModified", "")
    age_days = None
    if last_mod:
        try:
            dt = datetime.fromisoformat(last_mod.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - dt).days
        except ValueError:
            pass

    return {
        "name": fn["FunctionName"],
        "runtime": runtime,
        "memory_mb": fn.get("MemorySize"),
        "timeout_s": fn.get("Timeout"),
        "architectures": fn.get("Architectures", []),
        "code_size": fn.get("CodeSize"),
        "last_modified": last_mod,
        "age_days": age_days,
        "vpc": bool(fn.get("VpcConfig", {}).get("SubnetIds")),
        "dlq": bool(fn.get("DeadLetterConfig", {}).get("TargetArn")),
        "tracing": fn.get("TracingConfig", {}).get("Mode"),
        "layers": len(fn.get("Layers", [])),
        "env_var_count": len(env),
        "sensitive_env_vars": sensitive_env,
        "public_policy": policy_is_public(policy),
        "ephemeral_storage_mb": (fn.get("EphemeralStorage") or {})
            .get("Size"),
        "reserved_concurrency": fn.get("ReservedConcurrentExecutions"),
        "issues": issues,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Análisis profundo de funciones Lambda")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--function", "-f", default="",
                        help="Filtrar por nombre")
    parser.add_argument("--view", choices=["summary", "security",
                                           "performance"],
                        default="summary")
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
        client = session.client("lambda")
        functions = list_functions(client, args.function)
        results = [analyze_function(client, fn) for fn in functions]
    except Exception as e:
        _print(f"❌ Error: {e}", "red")
        sys.exit(1)

    if console:
        cols = ["Función", "Runtime", "Mem", "TO", "Issues"]
        if args.view == "security":
            cols = ["Función", "Env sensibles", "VPC", "DLQ",
                    "Pública", "Issues"]
        elif args.view == "performance":
            cols = ["Función", "Runtime", "Mem", "TO", "Layers",
                    "Edad (días)"]
        table = Table(title=f"Lambda Functions — {args.view}",
                      header_style="bold cyan")
        for c in cols:
            table.add_column(c)
        for r in results:
            if args.view == "security":
                table.add_row(
                    r["name"][:35],
                    f"[red]{len(r['sensitive_env_vars'])}[/red]"
                    if r["sensitive_env_vars"] else "0",
                    "✓" if r["vpc"] else "[yellow]✗[/yellow]",
                    "✓" if r["dlq"] else "[yellow]✗[/yellow]",
                    "[red]SÍ[/red]" if r["public_policy"] else "—",
                    str(len(r["issues"])))
            elif args.view == "performance":
                eol = r["runtime"] in EOL_RUNTIMES
                table.add_row(
                    r["name"][:35],
                    f"[red]{r['runtime']}[/red]" if eol else r["runtime"],
                    str(r["memory_mb"]), str(r["timeout_s"]),
                    str(r["layers"]), str(r["age_days"] or "—"))
            else:
                n = len(r["issues"])
                table.add_row(
                    r["name"][:35], r["runtime"], str(r["memory_mb"]),
                    str(r["timeout_s"]),
                    f"[{'red' if n > 2 else 'yellow' if n else 'green'}]"
                    f"{n}[/{'red' if n > 2 else 'yellow' if n else 'green'}]")
        console.print(table)
        for r in results:
            if r["issues"]:
                console.print(f"  [dim]⚠ {r['name']}: "
                              f"{', '.join(r['issues'])}[/dim]")
    else:
        for r in results:
            print(f"{r['name']}: {r['runtime']} {r['memory_mb']}MB "
                  f"issues={len(r['issues'])} {r['issues']}")

    _print(f"\nFunciones: {len(results)} | "
           f"con issues: {len([r for r in results if r['issues']])}",
           "cyan")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"lambda_analysis_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "region": args.region, "view": args.view,
                "functions": results,
            }, indent=2, default=str), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "name", "runtime", "memory_mb", "timeout_s",
                    "vpc", "dlq", "sensitive_env_count", "issues"])
                w.writeheader()
                for r in results:
                    w.writerow({
                        "name": r["name"], "runtime": r["runtime"],
                        "memory_mb": r["memory_mb"],
                        "timeout_s": r["timeout_s"],
                        "vpc": r["vpc"], "dlq": r["dlq"],
                        "sensitive_env_count":
                            len(r["sensitive_env_vars"]),
                        "issues": "; ".join(r["issues"])})
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
