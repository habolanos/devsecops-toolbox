#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EKS Deployment Validator — Tool 27

Valida un deployment de EKS de forma integral:
- ConfigMaps y Secrets referenciados: existencia, valores vacíos,
  placeholders y datos sensibles enmascarados
- Endpoints de conexión (host:puerto) extraídos de sus valores
- Conectividad TCP hacia los endpoints vía pod temporal
- IRSA (IAM Role for Service Account) del serviceAccount

Equivalente a GCP Tool: Deployment Validator
(connectivity/deployment_validator.py).

Uso:
    python aws_eks_deployment_validator.py --profile p --region us-east-1 \\
        --cluster my-eks --deployment my-app --validate all -o json
"""

import argparse
import json
import re
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "DevSecOps Team"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None

DEFAULT_PROBE_IMAGE = "busybox:1.36"
DEFAULT_TIMEOUT = 5

PLACEHOLDER_VALUES = {
    "", "changeme", "change-me", "todo", "tbd", "placeholder", "example",
    "example.com", "your-value-here", "xxx", "****", "null", "none",
    "n/a", "na", "test", "dummy", "localhost", "127.0.0.1",
    "replace-me", "fill-me", "fixme",
}

SENSITIVE_KEY_PATTERNS = [
    r"pass", r"pwd", r"secret", r"token", r"key", r"credential",
    r"auth", r"api[-_]?key", r"private", r"cert",
]

URL_PATTERN = re.compile(
    r"((?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*):\/\/"
    r"(?P<rest>[^\s'\"`<>]+))")
HOST_PORT_PATTERN = re.compile(
    r"\b((?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}|"
    r"(?:\d{1,3}\.){3}\d{1,3})[:](\d{1,5})\b")


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    severity: Severity
    resource_type: str
    resource_name: str
    key: str
    message: str
    remediation: str = ""


@dataclass
class Endpoint:
    host: str
    port: int
    raw: str
    source: str
    tcp_status: str = "PENDING"
    tcp_message: str = ""


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


def run_command(cmd: List[str], debug: bool = False,
                timeout: Optional[int] = 60) -> Tuple[int, str, str]:
    if debug:
        print(f"[DEBUG] Ejecutando: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout)
        return result.returncode, result.stdout.strip(), \
            result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout tras {timeout}s"
    except FileNotFoundError:
        return 127, "", "Comando no encontrado"


def kubectl_json(args: List[str], debug: bool = False,
                 timeout: int = 60) -> Optional[Dict]:
    code, stdout, _ = run_command(["kubectl"] + args + ["-o", "json"],
                                  debug, timeout=timeout)
    if code != 0 or not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def configure_kubectl_context(cluster: str, region: str, profile: str,
                              debug: bool = False) -> bool:
    cmd = ["aws", "eks", "update-kubeconfig",
           "--name", cluster, "--region", region]
    if profile:
        cmd += ["--profile", profile]
    code, stdout, stderr = run_command(cmd, debug, timeout=60)
    if code != 0:
        _print(f"❌ Error configurando kubectl: {stderr or stdout}", "red")
        return False
    _print(f"✅ Contexto kubectl configurado para '{cluster}'", "dim")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Análisis de valores
# ═══════════════════════════════════════════════════════════════════════════════

def is_placeholder_value(value: str) -> bool:
    if value is None:
        return True
    return value.strip().lower() in PLACEHOLDER_VALUES


def is_sensitive_key(key: str) -> bool:
    kl = key.lower()
    return any(re.search(p, kl) for p in SENSITIVE_KEY_PATTERNS)


def mask_value(value: str, visible: int = 4) -> str:
    if not value or len(value) <= visible:
        return "****"
    return value[:visible] + "*" * min(8, len(value) - visible)


def parse_endpoints(value: str, source: str) -> List[Endpoint]:
    from urllib.parse import urlparse
    endpoints = []
    for m in URL_PATTERN.finditer(value or ""):
        raw = m.group(0)
        norm = raw[5:] if raw.lower().startswith("jdbc:") else raw
        try:
            p = urlparse(norm)
            if p.hostname and p.port:
                endpoints.append(Endpoint(p.hostname, p.port, raw, source))
        except Exception:
            pass
    for m in HOST_PORT_PATTERN.finditer(value or ""):
        host, port_s = m.group(1), m.group(2)
        try:
            port = int(port_s)
        except ValueError:
            continue
        if (0 < port < 65536 and not any(
                e.host == host and e.port == port for e in endpoints)):
            endpoints.append(Endpoint(host, port, f"{host}:{port}",
                                      source))
    return endpoints


# ═══════════════════════════════════════════════════════════════════════════════
# Validaciones
# ═══════════════════════════════════════════════════════════════════════════════

def get_deployment_manifest(deployment: str, namespace: str,
                            debug: bool = False) -> Optional[Dict]:
    if namespace:
        return kubectl_json(
            ["get", "deployment", deployment, "-n", namespace], debug)
    data = kubectl_json(["get", "deployments", "-A"], debug, timeout=120)
    for item in (data or {}).get("items", []):
        if item.get("metadata", {}).get("name") == deployment:
            return item
    return None


def extract_resource_refs(deployment: Dict) -> Tuple[str, str,
                                                   Set[str], Set[str],
                                                   Optional[str]]:
    """namespace, SA, configmaps, secrets, irsa_role_arn."""
    metadata = deployment.get("metadata", {})
    namespace = metadata.get("namespace", "default")
    spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
    sa_name = spec.get("serviceAccountName", "default")

    configmaps, secrets = set(), set()
    for c in spec.get("containers", []) + spec.get("initContainers", []):
        for ef in c.get("envFrom", []):
            if r := ef.get("configMapRef", {}).get("name"):
                configmaps.add(r)
            if r := ef.get("secretRef", {}).get("name"):
                secrets.add(r)
        for env in c.get("env", []):
            vf = env.get("valueFrom", {})
            if r := vf.get("configMapKeyRef", {}).get("name"):
                configmaps.add(r)
            if r := vf.get("secretKeyRef", {}).get("name"):
                secrets.add(r)
    for v in spec.get("volumes", []):
        if r := v.get("configMap", {}).get("name"):
            configmaps.add(r)
        if r := v.get("secret", {}).get("secretName"):
            secrets.add(r)

    # IRSA: anotación eks.amazonaws.com/role-arn en el ServiceAccount
    irsa = None
    sa_obj = kubectl_json(["get", "serviceaccount", sa_name,
                           "-n", namespace])
    if sa_obj:
        irsa = (sa_obj.get("metadata", {}).get("annotations", {})
                .get("eks.amazonaws.com/role-arn"))
    return namespace, sa_name, configmaps, secrets, irsa


def validate_configmaps(names: Set[str], namespace: str,
                        findings: List[Finding],
                        endpoints: List[Endpoint], debug: bool = False):
    for name in sorted(names):
        cm = kubectl_json(["get", "configmap", name, "-n", namespace],
                          debug)
        if not cm:
            findings.append(Finding(
                Severity.CRITICAL, "configmap", name, "-",
                "ConfigMap referenciado no existe",
                f"kubectl create configmap {name} -n {namespace} ..."))
            continue
        data = cm.get("data") or {}
        if not data:
            findings.append(Finding(
                Severity.WARNING, "configmap", name, "-",
                "ConfigMap existe pero está vacío"))
        for key, value in data.items():
            if is_placeholder_value(value):
                findings.append(Finding(
                    Severity.WARNING, "configmap", name, key,
                    "Valor placeholder o vacío",
                    "Asignar un valor real"))
            else:
                endpoints.extend(parse_endpoints(
                    value, f"configmap/{name}:{key}"))


def validate_secrets(names: Set[str], namespace: str,
                     findings: List[Finding],
                     endpoints: List[Endpoint], debug: bool = False):
    import base64
    for name in sorted(names):
        sec = kubectl_json(["get", "secret", name, "-n", namespace],
                           debug)
        if not sec:
            findings.append(Finding(
                Severity.CRITICAL, "secret", name, "-",
                "Secret referenciado no existe",
                f"kubectl create secret ... -n {namespace}"))
            continue
        data = sec.get("data") or {}
        if not data:
            findings.append(Finding(
                Severity.WARNING, "secret", name, "-",
                "Secret existe pero está vacío"))
        for key, b64 in data.items():
            try:
                value = base64.b64decode(b64).decode("utf-8")
            except Exception:
                findings.append(Finding(
                    Severity.INFO, "secret", name, key,
                    "Valor binario no decodificable"))
                continue
            if is_placeholder_value(value):
                findings.append(Finding(
                    Severity.WARNING, "secret", name, key,
                    "Valor placeholder o vacío",
                    f"kubectl patch secret {name} -n {namespace}"))
            elif is_sensitive_key(key):
                # No loguear el valor — solo registrar que existe
                endpoints.extend(parse_endpoints(
                    value, f"secret/{name}:{key}"))
            else:
                endpoints.extend(parse_endpoints(
                    value, f"secret/{name}:{key}"))


def create_probe_pod(namespace: str, image: str,
                     debug: bool = False) -> Optional[str]:
    pod_name = f"validator-probe-{int(time.time())}"
    code, _, stderr = run_command(
        ["kubectl", "run", pod_name, "--image", image,
         "--restart=Never", "-n", namespace, "--", "sleep", "300"],
        debug, timeout=30)
    if code != 0:
        _print(f"⚠ No se pudo crear pod probe: {stderr}", "yellow")
        return None
    for _ in range(30):
        pod = kubectl_json(["get", "pod", pod_name, "-n", namespace],
                           debug, timeout=15)
        phase = (pod or {}).get("status", {}).get("phase")
        if phase == "Running":
            return pod_name
        if phase in ("Failed", "Succeeded"):
            break
        time.sleep(2)
    run_command(["kubectl", "delete", "pod", pod_name, "-n", namespace,
                 "--wait=false"], debug, timeout=15)
    return None


def validate_connectivity(endpoints: List[Endpoint], namespace: str,
                          probe_image: str, timeout: int,
                          debug: bool = False):
    if not endpoints:
        return
    probe = create_probe_pod(namespace, probe_image, debug)
    if not probe:
        _print("⚠ Sin pod probe — conectividad no validada", "yellow")
        return
    try:
        for ep in endpoints:
            code, _, stderr = run_command(
                ["kubectl", "exec", probe, "-n", namespace, "--",
                 "nc", "-z", "-w", str(timeout), ep.host, str(ep.port)],
                debug, timeout=timeout + 15)
            ep.tcp_status = "OK" if code == 0 else "FAIL"
            ep.tcp_message = (stderr or "")[:150]
    finally:
        run_command(["kubectl", "delete", "pod", probe, "-n", namespace,
                     "--wait=false"], debug, timeout=15)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Valida ConfigMaps, Secrets y conectividad de un "
                    "deployment EKS")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--cluster", "-c", default="",
                        help="Cluster EKS (vacío = contexto actual)")
    parser.add_argument("--deployment", "-d", required=True)
    parser.add_argument("--namespace", "-n", default="")
    parser.add_argument("--validate", choices=[
        "all", "secrets", "configmaps", "connectivity"], default="all")
    parser.add_argument("--severity", choices=[
        "critical", "warning", "info", "all"], default="all")
    parser.add_argument("--probe-image", default=DEFAULT_PROBE_IMAGE)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("-o", "--output", choices=["json", "csv"],
                        default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def main():
    args = get_args()

    if args.cluster:
        if not configure_kubectl_context(args.cluster, args.region,
                                         args.profile, args.debug):
            sys.exit(1)

    dep = get_deployment_manifest(args.deployment, args.namespace,
                                  args.debug)
    if not dep:
        _print(f"❌ Deployment '{args.deployment}' no encontrado", "red")
        sys.exit(1)

    namespace, sa, configmaps, secrets, irsa = extract_resource_refs(dep)

    if console:
        console.print(Panel.fit(
            f"[bold cyan]Deployment Validator (EKS)[/bold cyan]\n"
            f"Deployment: [yellow]{args.deployment}[/yellow] | "
            f"ns: {namespace} | SA: {sa}\n"
            f"IRSA: {irsa or '[dim]sin eks.amazonaws.com/role-arn[/dim]'}\n"
            f"ConfigMaps: {len(configmaps)} | Secrets: {len(secrets)} | "
            f"validate: {args.validate}", title="🛡 EKS Validator"))
    else:
        print(f"Deployment: {args.deployment} | ns: {namespace} | "
              f"SA: {sa} | IRSA: {irsa or '—'}")

    findings: List[Finding] = []
    endpoints: List[Endpoint] = []

    if args.validate in ("all", "configmaps"):
        validate_configmaps(configmaps, namespace, findings, endpoints,
                            args.debug)
    if args.validate in ("all", "secrets"):
        validate_secrets(secrets, namespace, findings, endpoints,
                         args.debug)
    if args.validate in ("all", "connectivity"):
        validate_connectivity(endpoints, namespace, args.probe_image,
                              args.timeout, args.debug)

    # Findings table
    sev_filter = SEVERITY_ORDER.get(args.severity, 99)
    visible = [f for f in findings
               if SEVERITY_ORDER[f.severity.value] <= sev_filter]

    if console and visible:
        table = Table(title="Hallazgos", header_style="bold cyan")
        for col in ["Sev", "Tipo", "Recurso", "Key", "Mensaje"]:
            table.add_column(col)
        for f in visible:
            color = {"critical": "red", "warning": "yellow",
                     "info": "dim"}[f.severity.value]
            table.add_row(f"[{color}]{f.severity.value}[/{color}]",
                          f.resource_type, f.resource_name,
                          f.key, f.message)
        console.print(table)
        for f in visible:
            if f.remediation:
                console.print(f"  [dim]💡 {f.resource_name}/{f.key}: "
                              f"{f.remediation}[/dim]")
    elif visible:
        for f in visible:
            print(f"[{f.severity.value}] {f.resource_type}/"
                  f"{f.resource_name}/{f.key}: {f.message}")
    else:
        _print("✓ Sin hallazgos", "green")

    # Connectivity table
    if endpoints:
        if console:
            table = Table(title="Endpoints detectados",
                          header_style="bold cyan")
            for col in ["Endpoint", "Origen", "TCP"]:
                table.add_column(col)
            for ep in endpoints:
                color = {"OK": "green", "FAIL": "red"}.get(
                    ep.tcp_status, "dim")
                table.add_row(f"{ep.host}:{ep.port}", ep.source[:45],
                              f"[{color}]{ep.tcp_status}[/{color}]")
            console.print(table)
        else:
            for ep in endpoints:
                print(f"{ep.host}:{ep.port} [{ep.tcp_status}] "
                      f"{ep.source}")

    crit = len([f for f in findings if f.severity == Severity.CRITICAL])
    warn = len([f for f in findings if f.severity == Severity.WARNING])
    _print(f"\nCritical: {crit} | Warning: {warn} | "
           f"Endpoints: {len(endpoints)}",
           "red" if crit else ("yellow" if warn else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        data = {
            "deployment": args.deployment, "namespace": namespace,
            "service_account": sa, "irsa_role": irsa,
            "timestamp": datetime.utcnow().isoformat(),
            "findings": [{"severity": f.severity.value,
                          "resource_type": f.resource_type,
                          "resource_name": f.resource_name,
                          "key": f.key, "message": f.message,
                          "remediation": f.remediation}
                         for f in findings],
            "endpoints": [{"host": e.host, "port": e.port,
                           "source": e.source,
                           "tcp_status": e.tcp_status}
                          for e in endpoints],
        }
        out = OUTCOME_DIR / f"eks_deployment_validation_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps(data, indent=2, default=str),
                           encoding="utf-8")
        else:
            import csv
            with open(out, "w", newline="", encoding="utf-8") as fo:
                w = csv.DictWriter(fo, fieldnames=[
                    "severity", "resource_type", "resource_name",
                    "key", "message"])
                w.writeheader()
                for f in data["findings"]:
                    w.writerow({k: f[k] for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
