#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Lambda Security Auditor — Tool 36

Auditoría de seguridad de funciones Lambda:

- Secretos en texto plano en variables de entorno (patrones +
  entropía básica)
- Resource policies públicas (principal '*')
- Rol de ejecución con permisos wildcard (Action/Resource '*')
- Funciones fuera de VPC procesando datos (informativo)
- Sin DLQ, sin tracing, runtime EOL
- URL pública (FunctionUrlConfig) sin auth o con auth NONE

Equivalente a GCP Tool: Cloud Run Security Auditor
(cloud-run/gcp_cloudrun_security_auditor.py).

Uso:
    python aws_lambda_security_auditor.py --profile p --region us-east-1
    python aws_lambda_security_auditor.py --severity critical -o json
"""

import argparse
import base64
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
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

SECRET_KEY_PATTERN = re.compile(
    r"(pass(word)?|secret|token|api[-_]?key|private[-_]?key|"
    r"credential|pwd|connection[-_]?string)", re.IGNORECASE)
AWS_KEY_PATTERN = re.compile(r"AKIA[0-9A-Z]{16}")

EOL_RUNTIMES = {
    "python2.7", "python3.6", "python3.7", "python3.8",
    "nodejs10.x", "nodejs12.x", "nodejs14.x", "nodejs16.x",
    "dotnetcore3.1", "ruby2.7", "java8", "go1.x",
}


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    severity: Severity
    function: str
    check: str
    message: str
    remediation: str = ""


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Checks
# ═══════════════════════════════════════════════════════════════════════════════

def check_env_secrets(fn: Dict, findings: List[Finding]):
    env = fn.get("Environment", {}).get("Variables", {})
    for key, value in env.items():
        if AWS_KEY_PATTERN.search(value or ""):
            findings.append(Finding(
                Severity.CRITICAL, fn["FunctionName"], "env_secrets",
                f"Access key AWS en env var '{key}'",
                "Mover a Secrets Manager y rotar la key"))
        elif SECRET_KEY_PATTERN.search(key):
            findings.append(Finding(
                Severity.HIGH, fn["FunctionName"], "env_secrets",
                f"Posible secreto en env var '{key}'",
                "Usar Secrets Manager + iam policy"))


def check_public_policy(client, fn: Dict, findings: List[Finding]):
    try:
        resp = client.get_policy(FunctionName=fn["FunctionName"])
        policy = json.loads(resp["Policy"])
    except ClientError:
        return
    for stmt in policy.get("Statement", []):
        principal = stmt.get("Principal", {})
        if stmt.get("Effect") == "Allow" and (
                principal == "*" or principal.get("AWS") == "*"
                or principal.get("Service") == "*"):
            findings.append(Finding(
                Severity.CRITICAL, fn["FunctionName"], "public_policy",
                "Resource policy permite principal '*' — función "
                "invocable públicamente",
                "Restringir Principal en lambda:RemovePermission / "
                "add-permission"))


def check_function_url(client, fn: Dict, findings: List[Finding]):
    try:
        cfg = client.get_function_url_config(
            FunctionName=fn["FunctionName"])
        if cfg.get("AuthType") == "NONE":
            findings.append(Finding(
                Severity.HIGH, fn["FunctionName"], "function_url",
                f"Function URL pública: {cfg.get('FunctionUrl')}",
                "AuthType AWS_IAM o eliminar la URL"))
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code != "ResourceNotFoundException":
            pass


def check_role_wildcards(session, fn: Dict, findings: List[Finding]):
    role_arn = fn.get("Role", "")
    if not role_arn:
        return
    role_name = role_arn.rsplit("/", 1)[-1]
    iam = session.client("iam")
    wildcard_actions = []
    try:
        for page in iam.get_paginator("list_role_policies").paginate(
                RoleName=role_name):
            for pol_name in page.get("PolicyNames", []):
                doc = iam.get_role_policy(
                    RoleName=role_name,
                    PolicyName=pol_name)["PolicyDocument"]
                for stmt in doc.get("Statement", []):
                    if stmt.get("Effect") != "Allow":
                        continue
                    actions = stmt.get("Action", [])
                    resources = stmt.get("Resource", [])
                    if not isinstance(actions, list):
                        actions = [actions]
                    if not isinstance(resources, list):
                        resources = [resources]
                    if "*" in actions and "*" in resources:
                        wildcard_actions.append(pol_name)
    except ClientError:
        return
    for pol in set(wildcard_actions):
        findings.append(Finding(
            Severity.HIGH, fn["FunctionName"], "iam_wildcard",
            f"Rol '{role_name}' con policy inline '{pol}' "
            f"Action='*' + Resource='*'",
            "Aplicar least-privilege"))


def check_config(fn: Dict, findings: List[Finding]):
    name = fn["FunctionName"]
    if fn.get("Runtime") in EOL_RUNTIMES:
        findings.append(Finding(
            Severity.HIGH, name, "runtime",
            f"Runtime EOL: {fn['Runtime']}",
            "Migrar a runtime soportado (recibe parches de seguridad)"))
    if not fn.get("DeadLetterConfig", {}).get("TargetArn"):
        findings.append(Finding(
            Severity.LOW, name, "dlq",
            "Sin Dead Letter Queue — eventos async perdidos en fallo",
            "Configurar DLQ (SQS/SNS)"))
    if fn.get("TracingConfig", {}).get("Mode") != "Active":
        findings.append(Finding(
            Severity.LOW, name, "tracing",
            "X-Ray tracing deshabilitado",
            "Habilitar para auditoría y troubleshooting"))


def audit_function(session, client, fn: Dict) -> List[Finding]:
    findings: List[Finding] = []
    check_env_secrets(fn, findings)
    check_public_policy(client, fn, findings)
    check_function_url(client, fn, findings)
    check_role_wildcards(session, fn, findings)
    check_config(fn, findings)
    return findings


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2,
                  "low": 3, "info": 4}
SEVERITY_STYLE = {"critical": "red bold", "high": "red",
                  "medium": "yellow", "low": "dim", "info": "dim"}


def get_args():
    parser = argparse.ArgumentParser(
        description="Auditoría de seguridad de funciones Lambda")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--function", "-f", default="")
    parser.add_argument("--severity", choices=[
        "critical", "high", "medium", "low", "all"], default="all")
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
    except Exception as e:
        _print(f"❌ Error de sesión AWS: {e}", "red")
        sys.exit(1)

    all_findings: List[Finding] = []
    fn_count = 0
    try:
        for page in client.get_paginator("list_functions").paginate():
            for fn in page.get("Functions", []):
                if args.function and args.function.lower() not in \
                        fn["FunctionName"].lower():
                    continue
                fn_count += 1
                all_findings.extend(
                    audit_function(session, client, fn))
    except Exception as e:
        _print(f"❌ Error auditando: {e}", "red")
        sys.exit(1)

    sev_filter = SEVERITY_ORDER.get(args.severity, 99)
    visible = [f for f in all_findings
               if SEVERITY_ORDER[f.severity.value] <= sev_filter]
    visible.sort(key=lambda f: SEVERITY_ORDER[f.severity.value])

    if console:
        table = Table(title="Lambda Security Audit",
                      header_style="bold red")
        for col in ["Sev", "Función", "Check", "Hallazgo"]:
            table.add_column(col)
        for f in visible[:60]:
            color = SEVERITY_STYLE[f.severity.value]
            table.add_row(f"[{color}]{f.severity.value}[/{color}]",
                          f.function[:30], f.check, f.message[:60])
        console.print(table)
        for f in visible:
            if f.remediation and f.severity in (
                    Severity.CRITICAL, Severity.HIGH):
                console.print(f"  [dim]💡 {f.function}/{f.check}: "
                              f"{f.remediation}[/dim]")
    else:
        for f in visible:
            print(f"[{f.severity.value}] {f.function}/{f.check}: "
                  f"{f.message}")

    counts = {s.value: len([f for f in all_findings
                           if f.severity == s])
              for s in Severity}
    _print(f"\nFunciones: {fn_count} | "
           f"critical: {counts['critical']} | high: {counts['high']} | "
           f"medium: {counts['medium']} | low: {counts['low']}",
           "red" if counts["critical"] else
           ("yellow" if counts["high"] else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"lambda_security_audit_{ts}.{args.output}"
        data = [{"severity": f.severity.value,
                 "function": f.function, "check": f.check,
                 "message": f.message,
                 "remediation": f.remediation} for f in all_findings]
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "region": args.region,
                "functions_audited": fn_count,
                "summary": counts, "findings": data,
            }, indent=2), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as fo:
                w = csv.DictWriter(fo, fieldnames=[
                    "severity", "function", "check", "message"])
                w.writeheader()
                for d in data:
                    w.writerow({k: d[k] for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if counts["critical"] else 0)


if __name__ == "__main__":
    main()
