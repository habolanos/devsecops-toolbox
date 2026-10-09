#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS API Gateway Checker — Tool 24

Analiza API Gateways (REST v1 + HTTP/WebSocket v2):

- Inventario de APIs: nombre, protocolo, endpoint type, stages
- Métodos y autorizaciones por recurso (REST v1)
- Authorizers configurados (JWT, Lambda, IAM, Cognito)
- Logging/metrics por stage
- Hallazgos de seguridad:
  * métodos sin autorización (NONE) en APIs no-públicas
  * stages sin logging de acceso
  * API keys no requeridas en métodos abiertos

Equivalente a GCP Tool: Gateway Services Checker
(gateway-services/gcp_gateway_checker.py).

Uso:
    python aws_api_gateway_checker.py --profile p --region us-east-1 -o json
"""

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
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


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    severity: Severity
    api_name: str
    resource: str
    message: str
    remediation: str = ""


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Análisis REST API (v1)
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_rest_api(client, api: Dict,
                     findings: List[Finding]) -> Dict:
    """Analiza una REST API: métodos, autorización, stages, logging."""
    api_id = api["id"]
    name = api.get("name", api_id)
    endpoint = (api.get("endpointConfiguration", {})
                .get("types", ["?"])[0])

    # Métodos por recurso
    methods = []
    try:
        resources = client.get_resources(restApiId=api_id,
                                         limit=500).get("items", [])
        for res in resources:
            path = res.get("path", "/")
            for method, cfg in res.get("resourceMethods", {}).items():
                auth = cfg.get("authorizationType", "NONE")
                methods.append({
                    "resource": path, "method": method,
                    "authorization": auth,
                    "api_key_required":
                        cfg.get("apiKeyRequired", False),
                })
                if auth == "NONE" and method != "OPTIONS":
                    findings.append(Finding(
                        Severity.WARNING, name, f"{method} {path}",
                        "Método sin autorización (NONE)",
                        "Configurar authorizer (IAM/JWT/Lambda/Cognito)"))
                if auth == "NONE" and not cfg.get("apiKeyRequired") \
                        and method != "OPTIONS":
                    findings.append(Finding(
                        Severity.INFO, name, f"{method} {path}",
                        "Sin API key requerida"))
    except ClientError as e:
        findings.append(Finding(Severity.WARNING, name, "-",
                                f"get_resources falló: {e}"[:120]))

    # Authorizers
    auth_types = set()
    try:
        auths = client.get_authorizers(restApiId=api_id,
                                       limit=100).get("items", [])
        auth_types = {a.get("type", "?") for a in auths}
    except ClientError:
        auths = []

    # Stages + logging
    stages = []
    for stage_name in api.get("stages", []) or []:
        try:
            st = client.get_stage(restApiId=api_id,
                                  stageName=stage_name)
            logging = (st.get("methodSettings", {})
                       .get("*/*", {})
                       .get("loggingLevel", "OFF") != "OFF")
            stages.append({"name": stage_name,
                           "logging": logging,
                           "cache": st.get("cacheClusterEnabled", False)})
            if not logging:
                findings.append(Finding(
                    Severity.WARNING, name, stage_name,
                    "Stage sin access logging",
                    "Habilitar loggingLevel en methodSettings"))
        except ClientError:
            stages.append({"name": stage_name, "logging": None})

    open_methods = [m for m in methods
                    if m["authorization"] == "NONE"
                    and m["method"] != "OPTIONS"]
    return {
        "id": api_id, "name": name, "type": "REST",
        "endpoint_type": endpoint,
        "created": str(api.get("createdDate", "")),
        "stages": stages, "methods": methods,
        "method_count": len(methods),
        "open_methods": len(open_methods),
        "authorizer_types": sorted(auth_types),
        "waf": api.get("webAclArn") is not None,
    }


def analyze_http_api(client_v2, api: Dict,
                     findings: List[Finding]) -> Dict:
    """Analiza una HTTP/WebSocket API (v2): rutas, authorizers, stages."""
    api_id = api["ApiId"]
    name = api.get("Name", api_id)
    protocol = api.get("ProtocolType", "HTTP")

    routes = []
    open_routes = 0
    try:
        paginator = client_v2.get_paginator("get_routes")
        for page in paginator.paginate(ApiId=api_id):
            for route in page.get("Items", []):
                auth = route.get("AuthorizationType", "NONE")
                routes.append({"route": route.get("RouteKey"),
                               "authorization": auth})
                if auth == "NONE" and "OPTIONS" not in \
                        route.get("RouteKey", ""):
                    open_routes += 1
                    findings.append(Finding(
                        Severity.INFO, name,
                        route.get("RouteKey", "?"),
                        "Ruta sin autorización"))
    except ClientError:
        pass

    try:
        auths = client_v2.get_authorizers(ApiId=api_id).get("Items", [])
        auth_types = {a.get("AuthorizerType", "?") for a in auths}
    except ClientError:
        auth_types = set()

    stages = []
    try:
        for st in client_v2.get_stages(ApiId=api_id).get("Items", []):
            logging = bool(st.get("AccessLogSettings"))
            stages.append({"name": st.get("StageName"),
                           "logging": logging,
                           "auto_deploy": st.get("AutoDeploy", False)})
            if not logging:
                findings.append(Finding(
                    Severity.WARNING, name, st.get("StageName", "?"),
                    "Stage sin access logging"))
    except ClientError:
        pass

    return {
        "id": api_id, "name": name, "type": protocol,
        "endpoint_type": api.get("ApiEndpoint", ""),
        "created": str(api.get("CreatedDate", "")),
        "stages": stages, "methods": routes,
        "method_count": len(routes),
        "open_methods": open_routes,
        "authorizer_types": sorted(auth_types),
        "waf": None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Analiza API Gateways (REST v1 + HTTP v2)")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--api", default="",
                        help="Filtrar por nombre de API")
    parser.add_argument("--severity", choices=["critical", "warning",
                                               "info", "all"],
                        default="all")
    parser.add_argument("-o", "--output", choices=["json", "csv"],
                        default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def main():
    args = get_args()

    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)

    try:
        session = boto3.Session(profile_name=args.profile,
                                region_name=args.region)
        gw1 = session.client("apigateway")
        gw2 = session.client("apigatewayv2")
    except Exception as e:
        _print(f"❌ Error de sesión AWS: {e}", "red")
        sys.exit(1)

    findings: List[Finding] = []
    apis: List[Dict] = []

    # REST APIs (v1)
    try:
        for api in gw1.get_rest_apis(limit=500).get("items", []):
            if args.api and args.api.lower() not in \
                    api.get("name", "").lower():
                continue
            apis.append(analyze_rest_api(gw1, api, findings))
    except ClientError as e:
        _print(f"⚠ get_rest_apis: {e}", "yellow")

    # HTTP/WebSocket APIs (v2)
    try:
        paginator = gw2.get_paginator("get_apis")
        for page in paginator.paginate():
            for api in page.get("Items", []):
                if args.api and args.api.lower() not in \
                        api.get("Name", "").lower():
                    continue
                apis.append(analyze_http_api(gw2, api, findings))
    except ClientError as e:
        _print(f"⚠ get_apis (v2): {e}", "yellow")

    # ── Reporte ──
    if console:
        table = Table(title="API Gateways", header_style="bold cyan")
        for col in ["API", "Tipo", "Endpoint", "Stages",
                    "Métodos/Rutas", "Sin auth", "Authorizers"]:
            table.add_column(col)
        for a in apis:
            color = "red" if a["open_methods"] else "green"
            table.add_row(
                a["name"][:40], a["type"], a["endpoint_type"],
                str(len(a["stages"])), str(a["method_count"]),
                f"[{color}]{a['open_methods']}[/{color}]",
                ",".join(a["authorizer_types"]) or "—")
        console.print(table)
    else:
        for a in apis:
            print(f"{a['name']} ({a['type']}): {a['method_count']} "
                  f"métodos, {a['open_methods']} sin auth")

    sev_filter = SEVERITY_ORDER.get(args.severity, 99)
    visible = [f for f in findings
               if SEVERITY_ORDER[f.severity.value] <= sev_filter]
    if console and visible:
        table = Table(title="Hallazgos", header_style="bold yellow")
        for col in ["Sev", "API", "Recurso", "Mensaje"]:
            table.add_column(col)
        for f in visible[:50]:
            color = {"critical": "red", "warning": "yellow",
                     "info": "dim"}[f.severity.value]
            table.add_row(f"[{color}]{f.severity.value}[/{color}]",
                          f.api_name, f.resource[:40], f.message)
        console.print(table)
    elif visible:
        for f in visible:
            print(f"[{f.severity.value}] {f.api_name}/{f.resource}: "
                  f"{f.message}")

    _print(f"\nAPIs: {len(apis)} | Hallazgos: {len(findings)}",
           "yellow" if findings else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"api_gateway_check_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "region": args.region,
                "apis": apis,
                "findings": [{"severity": f.severity.value,
                              "api": f.api_name,
                              "resource": f.resource,
                              "message": f.message,
                              "remediation": f.remediation}
                             for f in findings],
            }, indent=2, default=str), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "severity", "api", "resource", "message"])
                w.writeheader()
                for x in findings:
                    w.writerow({"severity": x.severity.value,
                                "api": x.api_name,
                                "resource": x.resource,
                                "message": x.message})
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
