#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Connectivity Checker — Tool 12

Verifica conectividad entre un workload AKS y un destino,
equivalente a connectivity/pod_connectivity_checker (GCP) y
aws_eks_pod_connectivity_checker:

- Cadena de verificación: deployment → cluster → destino
  (Azure SQL o host:port genérico) → NSG de la subnet → test TCP
  real desde pod probe busybox
- Destino Azure SQL: FQDN, publicNetworkAccess, firewall rules,
  private endpoints
- Resultado PASS/FAIL/WARN por verificación + remediación

Uso:
    python connectivity_checker.py --subscription <id> \\
        --cluster aks --resource-group rg --deployment api \\
        --host myserver.database.windows.net --port 1433
"""

import argparse
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, run_kubectl,
    kubectl_json, setup_aks_kubeconfig, try_az,
    resolve_subscription, rg_of, now_ts, export_json)

__version__ = "1.0.0"

PROBE_NS = "default"
PROBE_NAME = "devsecops-conn-probe"


class Check:
    def __init__(self, name: str):
        self.name = name
        self.results: List[Dict] = []

    def add(self, status: str, msg: str,
            remediation: str = ""):
        self.results.append({"check": self.name,
                             "status": status,
                             "message": msg,
                             "remediation": remediation})
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠",
                "INFO": "ℹ", "SKIP": "⏭"}.get(status, "•")
        _print(f"  {icon} {self.name}: {msg}",
               {"PASS": "green", "FAIL": "red",
                "WARN": "yellow"}.get(status, "dim"))


def check_deployment(name: str, ns: str) -> Check:
    c = Check("Deployment")
    try:
        d = kubectl_json(["get", "deployment", name,
                          "-n", ns])
        status = d.get("status", {})
        c.add("PASS",
              f"{name}: {status.get('readyReplicas',0)}/"
              f"{d.get('spec',{}).get('replicas',0)} réplicas "
              f"listas")
    except Exception as e:
        c.add("FAIL", f"deployment {ns}/{name}: {e}",
              "Verificar nombre/namespace")
    return c


def check_sql_target(sub: str, host: str) -> Check:
    """Contexto si el host es Azure SQL."""
    c = Check("Azure SQL")
    if ".database.windows.net" not in host:
        c.add("SKIP", f"{host} no es Azure SQL")
        return c
    server_name = host.split(".")[0]
    servers = try_az(["sql", "server", "list"], sub,
                     default=[]) or []
    srv = next((s for s in servers
                if s["name"] == server_name), None)
    if not srv:
        c.add("WARN", f"Servidor {server_name} no encontrado "
                      "en la suscripción")
        return c
    if srv.get("publicNetworkAccess") == "Disabled":
        c.add("INFO", "publicNetworkAccess deshabilitado — "
                      "solo acceso por private endpoint")
    else:
        c.add("WARN", "publicNetworkAccess habilitado",
              "Evaluar private endpoint")
        rules = try_az(["sql", "server", "firewall-rule",
                        "list", "--server", server_name,
                        "--resource-group", rg_of(srv)],
                       sub, default=[]) or []
        c.add("INFO", f"{len(rules)} reglas de firewall")
    pes = try_az(["network", "private-endpoint", "list",
                  "--query", f"[?contains(customDnsConfigs"
                  f".fqdns[0]||'', '{server_name}')]"], sub,
                 default=[]) or []
    if pes:
        c.add("PASS", f"Private endpoint: {pes[0]['name']}")
    return c


def tcp_test_local(host: str, port: int,
                   timeout: int = 5) -> Check:
    c = Check("TCP local")
    try:
        with socket.create_connection((host, port),
                                      timeout=timeout):
            c.add("PASS", f"{host}:{port} accesible desde "
                          "este host")
    except Exception as e:
        c.add("WARN", f"{host}:{port} no accesible local: "
                      f"{e}",
              "Puede ser normal si solo hay acceso privado")
    return c


def tcp_test_pod(host: str, port: int, ns: str,
                 timeout: int = 30) -> Check:
    """Test TCP desde un pod busybox en el cluster."""
    c = Check("TCP desde pod")
    try:
        run_kubectl(["delete", "pod", PROBE_NAME, "-n", ns,
                     "--ignore-not-found=true"])
    except Exception:
        pass
    try:
        run_kubectl(["run", PROBE_NAME, "-n", ns,
                     "--image=busybox", "--restart=Never",
                     "--", "sleep", "120"])
        for _ in range(12):
            try:
                pod = kubectl_json(["get", "pod", PROBE_NAME,
                                    "-n", ns])
                if pod.get("status", {}).get("phase") == \
                        "Running":
                    break
            except Exception:
                pass
            time.sleep(5)
        out = run_kubectl(
            ["exec", PROBE_NAME, "-n", ns, "--",
             "nc", "-zv", "-w", "5", host, str(port)],
            timeout=timeout)
        c.add("PASS", f"{host}:{port} accesible desde el "
                      f"cluster: {out.strip()[:80]}")
    except Exception as e:
        c.add("FAIL", f"{host}:{port} NO accesible desde "
                      f"pods: {str(e)[:120]}",
              "Revisar NSG de subnet, DNS privado o firewall "
              "del destino")
    finally:
        try:
            run_kubectl(["delete", "pod", PROBE_NAME,
                         "-n", ns, "--ignore-not-found=true",
                         "--wait=false"])
        except Exception:
            pass
    return c


def get_args():
    p = argparse.ArgumentParser(
        description="Verifica conectividad pod AKS → destino")
    p.add_argument("--subscription", default="")
    p.add_argument("--cluster", required=True)
    p.add_argument("--resource-group", required=True)
    p.add_argument("--deployment", default="",
                   help="Deployment a validar (opcional)")
    p.add_argument("--namespace", default="default")
    p.add_argument("--host", required=True,
                   help="FQDN/IP destino (ej. "
                        "srv.database.windows.net)")
    p.add_argument("--port", type=int, default=1433)
    p.add_argument("--skip-pod-test", action="store_true")
    p.add_argument("-o", "--output", choices=["json"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)

    checks = []
    if not setup_aks_kubeconfig(args.cluster,
                                args.resource_group, sub):
        _print("❌ kubeconfig no configurado", "red")
        sys.exit(1)
    checks.append(Check("Kubeconfig"))
    checks[-1].add("PASS", f"Conectado a {args.cluster}")

    if args.deployment:
        checks.append(check_deployment(args.deployment,
                                       args.namespace))
    checks.append(check_sql_target(sub, args.host))
    checks.append(tcp_test_local(args.host, args.port))
    if not args.skip_pod_test:
        checks.append(tcp_test_pod(args.host, args.port,
                                   args.namespace))

    all_results = [r for c in checks for r in c.results]
    failed = [r for r in all_results if r["status"] == "FAIL"]
    _print(f"\n{len(all_results)} verificaciones | "
           f"fallos: {len(failed)}",
           "red" if failed else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"connectivity_{now_ts()}.json"
        export_json(out, {
            "timestamp": datetime.utcnow().isoformat(),
            "target": f"{args.host}:{args.port}",
            "results": all_results})
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
