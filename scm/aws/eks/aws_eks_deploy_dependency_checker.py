#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EKS Deploy Dependency Checker — Tool 39

Analiza los ConfigMaps/Secrets referenciados por un Deployment de EKS para
identificar cadenas de conexión (host:puerto) y valida la conectividad TCP
hacia cada endpoint detectado — desde un pod temporal o localmente.

Equivalente a GCP Tool: Deploy Dependency Checker
(connectivity/deploy_dependency_checker.py).

Soporta referencias a AWS Secrets Manager para resolver credenciales:
  secretsManager:            (o awsSecretsManager:)
    secrets:
      db:
        name: "prod/db-credentials"   # secretId
        version: "AWSCURRENT"         # opcional (versionStage o versionId)

Uso:
    python aws_eks_deploy_dependency_checker.py --profile p --region us-east-1 \\
        --cluster my-eks --deployment my-app -o json
"""

import argparse
import json
import re
import socket
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

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

DB_DEFAULT_PORTS = {
    "postgresql": 5432, "postgres": 5432, "mysql": 3306, "mariadb": 3306,
    "mongodb": 27017, "redis": 6379, "sqlserver": 1433, "mssql": 1433,
    "oracle": 1521, "cassandra": 9042, "elasticsearch": 9200,
    "memcached": 11211, "kafka": 9092, "rabbitmq": 5672, "amqp": 5672,
}

URL_PATTERN = re.compile(
    r"((?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*):\/\/"
    r"(?P<rest>[^\s'\"`<>]+))")
HOST_PORT_PATTERN = re.compile(
    r"\b((?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}|"
    r"(?:\d{1,3}\.){3}\d{1,3}|[a-zA-Z0-9-]+(?::[a-zA-Z0-9-]+)*\.svc\."
    r"cluster\.local)[:](\d{1,5})\b")
ENGINE_PATTERN = re.compile(
    r"(postgres(?:ql)?|mysql|mariadb|mongodb|redis|sqlserver|mssql|"
    r"oracle|cassandra|elasticsearch|memcached|kafka|rabbitmq|amqp)",
    re.IGNORECASE)


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
        if debug and result.stderr.strip():
            print(f"[DEBUG] stderr: {result.stderr.strip()[:400]}")
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
# Parsing de conexiones
# ═══════════════════════════════════════════════════════════════════════════════

def parse_connection_values(value: str) -> List[Dict]:
    """Extrae endpoints host:puerto de un valor de ConfigMap/Secret."""
    results: List[Dict] = []
    if not value:
        return results

    for match in URL_PATTERN.finditer(value):
        raw_url = match.group(0)
        engine = match.group("scheme") or "unknown"
        normalized = raw_url
        if normalized.lower().startswith("jdbc:"):
            normalized = normalized[5:]
        try:
            parsed = urlparse(normalized)
            host = parsed.hostname
            port = parsed.port or DB_DEFAULT_PORTS.get(engine.lower())
            if host and port:
                results.append({"host": host, "port": port,
                                "raw": raw_url, "type": engine.lower(),
                                "source": "url"})
        except Exception:
            pass

    for match in HOST_PORT_PATTERN.finditer(value):
        host, port_str = match.group(1), match.group(2)
        try:
            port = int(port_str)
        except ValueError:
            continue
        if not (0 < port < 65536):
            continue
        if any(r["host"] == host and r["port"] == port for r in results):
            continue
        eng = ENGINE_PATTERN.search(value)
        results.append({"host": host, "port": port,
                        "raw": f"{host}:{port}",
                        "type": eng.group(1).lower() if eng else "unknown",
                        "source": "host:port"})
    return results


def parse_secrets_manager_references(value: str) -> List[Dict]:
    """Parsea referencias a AWS Secrets Manager embebidas en YAML.

    Formatos aceptados (equivalente al secretManager de GCP):
      secretsManager: / awsSecretsManager:
        secrets:
          db: {name: "prod/db", version: "AWSCURRENT"}
    """
    if not value or ("secretsManager" not in value
                     and "awsSecretsManager" not in value):
        return []

    try:
        import yaml
        data = yaml.safe_load(value)
        if not isinstance(data, dict):
            return []
        sm = data.get("awsSecretsManager") or data.get("secretsManager")
        if not isinstance(sm, dict):
            return []
        secrets = sm.get("secrets", {})
        if not isinstance(secrets, dict):
            return []
        return [{
            "connection_key": key,
            "secret_id": str(cfg.get("secretId")
                             or cfg.get("name", "")),
            "version": str(cfg.get("version", "AWSCURRENT")),
            "region": str(sm.get("region") or cfg.get("region", "")),
        } for key, cfg in secrets.items() if isinstance(cfg, dict)]
    except Exception:
        pass

    results = []
    pattern = re.compile(
        r"(\w+)\s*:\s*\n\s+(?:secretId|name)\s*:\s*([^\s\n]+)"
        r"\s*\n\s+version\s*:\s*([^\s\n]+)", re.MULTILINE)
    for m in pattern.finditer(value):
        results.append({"connection_key": m.group(1),
                        "secret_id": m.group(2),
                        "version": m.group(3), "region": ""})
    return results


def fetch_aws_secret(secret_id: str, version: str, session,
                     debug: bool = False) -> Optional[Dict]:
    """Obtiene un secreto de AWS Secrets Manager (boto3)."""
    if not BOTO3_AVAILABLE or not session or not secret_id:
        return None
    try:
        client = session.client("secretsmanager")
        kwargs = {"SecretId": secret_id}
        if version and version not in ("AWSCURRENT", "latest"):
            # versionId o versionStage
            if re.fullmatch(r"[0-9a-f-]{36}", version):
                kwargs["VersionId"] = version
            else:
                kwargs["VersionStage"] = version
        resp = client.get_secret_value(**kwargs)
        secret_str = resp.get("SecretString")
        if secret_str:
            try:
                return json.loads(secret_str)
            except json.JSONDecodeError:
                return {"raw": secret_str}
        return {"raw": "<binary>"}
    except Exception as e:
        if debug:
            print(f"[DEBUG] SecretsManager get_secret_value "
                  f"{secret_id}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# Kubernetes
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
                                                   List[str], List[str]]:
    """Extrae namespace, serviceAccount, configmaps y secrets referenciados."""
    metadata = deployment.get("metadata", {})
    namespace = metadata.get("namespace", "default")
    spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
    service_account = spec.get("serviceAccountName", "default")

    configmaps, secrets = set(), set()
    containers = (spec.get("containers", [])
                  + spec.get("initContainers", []))
    for container in containers:
        for env_from in container.get("envFrom", []):
            if ref := env_from.get("configMapRef", {}).get("name"):
                configmaps.add(ref)
            if ref := env_from.get("secretRef", {}).get("name"):
                secrets.add(ref)
        for env in container.get("env", []):
            vf = env.get("valueFrom", {})
            if ref := vf.get("configMapKeyRef", {}).get("name"):
                configmaps.add(ref)
            if ref := vf.get("secretKeyRef", {}).get("name"):
                secrets.add(ref)
    for volume in spec.get("volumes", []):
        if ref := volume.get("configMap", {}).get("name"):
            configmaps.add(ref)
        if ref := volume.get("secret", {}).get("secretName"):
            secrets.add(ref)
    return namespace, service_account, sorted(configmaps), sorted(secrets)


def get_configmap_data(name: str, namespace: str,
                       debug: bool = False) -> Optional[Dict[str, str]]:
    cm = kubectl_json(["get", "configmap", name, "-n", namespace], debug)
    return (cm or {}).get("data") or None


def get_secret_data(name: str, namespace: str,
                    debug: bool = False) -> Optional[Dict[str, str]]:
    import base64
    sec = kubectl_json(["get", "secret", name, "-n", namespace], debug)
    if not sec:
        return None
    decoded = {}
    for k, v in (sec.get("data") or {}).items():
        try:
            decoded[k] = base64.b64decode(v).decode("utf-8")
        except Exception:
            decoded[k] = "<binary>"
    return decoded


# ═══════════════════════════════════════════════════════════════════════════════
# Probe de conectividad
# ═══════════════════════════════════════════════════════════════════════════════

def test_tcp_local(host: str, port: int,
                   timeout: int = DEFAULT_TIMEOUT) -> Tuple[str, str, float]:
    """Prueba TCP local (socket)."""
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "OK", "conexión establecida", time.time() - start
    except socket.timeout:
        return "TIMEOUT", f"timeout tras {timeout}s", time.time() - start
    except socket.gaierror as e:
        return "DNS_ERROR", str(e), time.time() - start
    except (ConnectionRefusedError, OSError) as e:
        return "REFUSED", str(e), time.time() - start


def create_probe_pod(namespace: str, image: str,
                     debug: bool = False) -> Optional[str]:
    pod_name = f"dep-checker-probe-{int(time.time())}"
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
    _print("⚠ Pod probe no llegó a Running", "yellow")
    return None


def delete_probe_pod(pod_name: str, namespace: str, debug: bool = False):
    run_command(["kubectl", "delete", "pod", pod_name, "-n", namespace,
                 "--wait=false"], debug, timeout=15)


def test_tcp_via_pod(pod_name: str, namespace: str, host: str, port: int,
                     timeout: int = DEFAULT_TIMEOUT,
                     debug: bool = False) -> Tuple[str, str, float]:
    """nc desde un pod temporal dentro del cluster."""
    start = time.time()
    code, stdout, stderr = run_command(
        ["kubectl", "exec", pod_name, "-n", namespace, "--",
         "nc", "-z", "-w", str(timeout), host, str(port)],
        debug, timeout=timeout + 15)
    elapsed = time.time() - start
    if code == 0:
        return "OK", "nc OK", elapsed
    msg = (stderr or stdout or "nc falló").replace("\n", " ")[:200]
    return "FAIL", msg, elapsed


def build_services_map(namespace: str,
                       debug: bool = False) -> Dict[str, Dict]:
    """Mapa service-name → {clusterIP, external, type} del namespace."""
    data = kubectl_json(["get", "services", "-n", namespace], debug)
    svc_map = {}
    for svc in (data or {}).get("items", []):
        spec = svc.get("spec", {})
        ingress = (svc.get("status", {})
                   .get("loadBalancer", {}).get("ingress", []))
        external = (ingress[0].get("hostname")
                    or ingress[0].get("ip", "")) if ingress else ""
        svc_map[svc["metadata"]["name"]] = {
            "cluster_ip": spec.get("clusterIP", ""),
            "external": external,
            "type": spec.get("type", ""),
            "ports": [p.get("port") for p in spec.get("ports", [])],
        }
    return svc_map


# ═══════════════════════════════════════════════════════════════════════════════
# Núcleo
# ═══════════════════════════════════════════════════════════════════════════════

def collect_connections(configmaps: List[str], secrets: List[str],
                        namespace: str, session,
                        debug: bool = False) -> Tuple[List[Dict], List[str]]:
    """Recolecta endpoints de todos los configmaps/secrets del deployment."""
    connections: List[Dict] = []
    warnings: List[str] = []
    seen = set()

    def _add(conn, origin):
        key = (conn["host"], conn["port"])
        if key in seen:
            return
        seen.add(key)
        conn["origin"] = origin
        connections.append(conn)

    for cm_name in configmaps:
        data = get_configmap_data(cm_name, namespace, debug)
        if data is None:
            warnings.append(f"ConfigMap '{cm_name}' no encontrado")
            continue
        for key, value in data.items():
            for conn in parse_connection_values(str(value)):
                _add(conn, f"configmap/{cm_name}:{key}")
            for ref in parse_secrets_manager_references(str(value)):
                secret = fetch_aws_secret(ref["secret_id"],
                                          ref["version"], session, debug)
                if secret is None:
                    warnings.append(
                        f"Secrets Manager '{ref['secret_id']}' "
                        f"(key {ref['connection_key']}): no accesible")
                    continue
                for sk, sv in secret.items():
                    for conn in parse_connection_values(str(sv)):
                        conn["sm_key"] = ref["connection_key"]
                        _add(conn, f"secretsmanager/{ref['secret_id']}")

    for sec_name in secrets:
        data = get_secret_data(sec_name, namespace, debug)
        if data is None:
            warnings.append(f"Secret '{sec_name}' no encontrado")
            continue
        for key, value in data.items():
            for conn in parse_connection_values(str(value)):
                conn["sensitive_origin"] = True
                _add(conn, f"secret/{sec_name}:{key}")

    return connections, warnings


def get_connection_type_label(raw: str, conn_type: str) -> str:
    if conn_type and conn_type != "unknown":
        return conn_type.upper()
    if ".rds." in raw or "rds.amazonaws.com" in raw:
        return "RDS"
    if ".cluster.local" in raw:
        return "K8S-SVC"
    if re.search(r"elasticache", raw):
        return "ELASTICACHE"
    return "TCP"


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Analiza dependencias (conexiones) de un deployment EKS")
    parser.add_argument("--profile", "-p", default="default",
                        help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1",
                        help="AWS region")
    parser.add_argument("--cluster", "-c", default="",
                        help="Cluster EKS (vacío = contexto kubectl actual)")
    parser.add_argument("--deployment", "-d", required=True,
                        help="Deployment a analizar")
    parser.add_argument("--namespace", "-n", default="",
                        help="Namespace (auto-detecta si se omite)")
    parser.add_argument("--probe-mode", choices=["local", "pod"],
                        default="pod",
                        help="Origen del probe TCP (Default: pod)")
    parser.add_argument("--probe-image", default=DEFAULT_PROBE_IMAGE)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("-o", "--output", choices=["json", "csv"],
                        default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = get_args()

    if args.cluster:
        if not configure_kubectl_context(args.cluster, args.region,
                                         args.profile, args.debug):
            sys.exit(1)

    session = None
    if BOTO3_AVAILABLE:
        try:
            session = boto3.Session(profile_name=args.profile,
                                    region_name=args.region)
        except Exception as e:
            _print(f"⚠ Sesión boto3 no disponible: {e} "
                   f"(Secrets Manager deshabilitado)", "yellow")

    dep = get_deployment_manifest(args.deployment, args.namespace,
                                  args.debug)
    if not dep:
        _print(f"❌ Deployment '{args.deployment}' no encontrado", "red")
        sys.exit(1)

    namespace, sa, configmaps, secrets = extract_resource_refs(dep)
    _print(f"Deployment: {args.deployment} | ns: {namespace} | "
           f"SA: {sa}", "cyan")
    _print(f"ConfigMaps: {len(configmaps)} | Secrets: {len(secrets)}", "dim")

    connections, warnings = collect_connections(
        configmaps, secrets, namespace, session, args.debug)

    for w in warnings:
        _print(f"⚠ {w}", "yellow")

    if not connections:
        _print("No se detectaron cadenas de conexión.", "green")
        return

    # Probe
    probe_pod = None
    if args.probe_mode == "pod":
        probe_pod = create_probe_pod(namespace, args.probe_image,
                                     args.debug)
        if not probe_pod:
            _print("⚠ Probe pod no disponible — modo local", "yellow")

    svc_map = build_services_map(namespace, args.debug)

    try:
        for conn in connections:
            if probe_pod:
                status, msg, elapsed = test_tcp_via_pod(
                    probe_pod, namespace, conn["host"], conn["port"],
                    args.timeout, args.debug)
            else:
                status, msg, elapsed = test_tcp_local(
                    conn["host"], conn["port"], args.timeout)
            conn["tcp_status"] = status
            conn["tcp_message"] = msg
            conn["latency_s"] = round(elapsed, 3)
            conn["type_label"] = get_connection_type_label(
                conn["raw"], conn["type"])
            # Servicio k8s asociado (si el host es un service name)
            svc = svc_map.get(conn["host"].split(".")[0])
            if svc:
                conn["k8s_service"] = svc
    finally:
        if probe_pod:
            delete_probe_pod(probe_pod, namespace, args.debug)

    # Tabla
    if console:
        table = Table(title=f"Dependencias de {args.deployment}",
                          header_style="bold cyan")
        for col in ["Endpoint", "Tipo", "Origen", "TCP", "Latencia", "Msg"]:
            table.add_column(col)
        for c in connections:
            style = {"OK": "green", "TIMEOUT": "yellow"}.get(
                c["tcp_status"], "red")
            table.add_row(
                f"{c['host']}:{c['port']}", c["type_label"],
                c.get("origin", "")[:35],
                f"[{style}]{c['tcp_status']}[/{style}]",
                f"{c['latency_s']}s", (c["tcp_message"] or "")[:30])
        console.print(table)
    else:
        for c in connections:
            print(f"{c['host']}:{c['port']} [{c['type_label']}] "
                  f"{c['tcp_status']} ({c['latency_s']}s) — "
                  f"{c.get('origin','')}")

    ok = len([c for c in connections if c["tcp_status"] == "OK"])
    _print(f"\n{ok}/{len(connections)} endpoints alcanzables",
           "green" if ok == len(connections) else "yellow")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"eks_deploy_dependencies_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps(
                {"deployment": args.deployment, "namespace": namespace,
                 "timestamp": datetime.utcnow().isoformat(),
                 "connections": connections, "warnings": warnings},
                indent=2, default=str), encoding="utf-8")
        else:
            import csv
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "host", "port", "type_label", "origin",
                    "tcp_status", "tcp_message", "latency_s"])
                w.writeheader()
                for c in connections:
                    w.writerow({k: c.get(k) for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
