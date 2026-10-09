#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EKS Pod Connectivity Checker — Tool 26

Valida la conectividad desde un Pod de EKS hasta una instancia RDS,
verificando todos los elementos de la cadena de conectividad:

 0. Deployment      — pods, serviceAccount, IRSA
 1. EKS Cluster     — estado, VPC, security groups del control plane
 2. RDS Instance    — estado, endpoint, puerto, publiclyAccessible
 3. VPC             — misma VPC o peering entre cluster y RDS
 4. Security Groups — reglas ingress en los SGs de RDS (puerto/origen)
 5. IAM / IRSA      — rol asociado al serviceAccount (si aplica)
 6. Load Balancers  — servicios k8s tipo LoadBalancer relacionados
 7. TCP Test        — prueba real desde un pod temporal (nc)

Equivalente a GCP Tool: Pod Connectivity Checker
(connectivity/pod_connectivity_checker.py — GKE → Cloud SQL).

Uso:
    python aws_eks_pod_connectivity_checker.py --profile p --region us-east-1 \\
        --cluster my-eks --deployment my-app --rds-instance my-db -o json
"""

import argparse
import json
import subprocess
import sys
import time

# Consolas Windows (cp1252): permitir salida Unicode
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

DEFAULT_PROBE_IMAGE = "busybox:1.36"
DEFAULT_TIMEOUT = 5


class CheckStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    INFO = "INFO"
    SKIP = "SKIP"


STATUS_EMOJI = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️",
                "INFO": "ℹ️", "SKIP": "⏭️"}


@dataclass
class CheckResult:
    section: str
    name: str
    status: CheckStatus
    message: str
    remediation: str = ""

    def as_dict(self) -> Dict:
        return {"section": self.section, "check": self.name,
                "status": self.status.value, "message": self.message,
                "remediation": self.remediation}


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
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Checker
# ═══════════════════════════════════════════════════════════════════════════════

class EKSConnectivityChecker:
    def __init__(self, profile: str, region: str, cluster_name: str,
                 deployment: str, namespace: str, rds_instance: str,
                 timeout: int = DEFAULT_TIMEOUT, probe_image: str =
                 DEFAULT_PROBE_IMAGE, debug: bool = False):
        self.profile = profile
        self.region = region
        self.cluster_name = cluster_name
        self.deployment_name = deployment
        self.namespace = namespace or "default"
        self.rds_instance_id = rds_instance
        self.timeout = timeout
        self.probe_image = probe_image
        self.debug = debug
        self.results: List[CheckResult] = []

        self.session = None
        if BOTO3_AVAILABLE:
            try:
                self.session = boto3.Session(profile_name=profile,
                                             region_name=region)
            except Exception as e:
                self.results.append(CheckResult(
                    "AWS", "Sesión boto3", CheckStatus.FAIL, str(e),
                    "Verificar credenciales/profile"))

        # Datos descubiertos
        self.deployment: Optional[Dict] = None
        self.cluster: Optional[Dict] = None
        self.rds: Optional[Dict] = None
        self.irsa_role: Optional[str] = None

    def _aws(self, service: str):
        return self.session.client(service) if self.session else None

    def add(self, section: str, name: str, status: CheckStatus,
            message: str, remediation: str = ""):
        r = CheckResult(section, name, status, message, remediation)
        self.results.append(r)
        if console:
            color = {"PASS": "green", "FAIL": "red", "WARN": "yellow",
                     "INFO": "cyan", "SKIP": "dim"}[status.value]
            console.print(f"{STATUS_EMOJI[status.value]} "
                          f"[{color}]{section}/{name}:[/{color}] {message}")
            if status == CheckStatus.FAIL and remediation:
                console.print(f"   [dim]💡 {remediation}[/dim]")
        else:
            print(f"{STATUS_EMOJI[status.value]} {section}/{name}: "
                  f"{message}")
            if status == CheckStatus.FAIL and remediation:
                print(f"   💡 {remediation}")

    # ── 0. Deployment ────────────────────────────────────────────────────

    def check_deployment(self):
        section = "0. Deployment"
        if not self.deployment_name:
            self.add(section, "deployment", CheckStatus.SKIP,
                     "No se especificó deployment")
            return
        dep = kubectl_json(["get", "deployment", self.deployment_name,
                            "-n", self.namespace], self.debug)
        if not dep:
            # Buscar en todos los namespaces
            data = kubectl_json(["get", "deployments", "-A"], self.debug,
                                timeout=120)
            for item in (data or {}).get("items", []):
                if item.get("metadata", {}).get("name") == \
                        self.deployment_name:
                    dep = item
                    self.namespace = item["metadata"]["namespace"]
                    break
        if not dep:
            self.add(section, "deployment", CheckStatus.FAIL,
                     f"'{self.deployment_name}' no encontrado",
                     "Verificar nombre/namespace con kubectl get deploy -A")
            return
        self.deployment = dep
        spec = dep.get("spec", {}).get("template", {}).get("spec", {})
        sa = spec.get("serviceAccountName", "default")
        replicas = dep.get("status", {})
        ready = replicas.get("readyReplicas", 0)
        desired = replicas.get("replicas", 0)
        self.add(section, "deployment", CheckStatus.PASS,
                 f"{self.deployment_name} en ns {self.namespace} "
                 f"({ready}/{desired} ready, SA: {sa})")
        if ready < desired:
            self.add(section, "replicas", CheckStatus.WARN,
                     f"Solo {ready}/{desired} réplicas ready — "
                     f"los probes pueden no reflejar el estado real")

        # IRSA del serviceAccount
        sa_obj = kubectl_json(["get", "serviceaccount", sa,
                               "-n", self.namespace], self.debug)
        if sa_obj:
            self.irsa_role = (sa_obj.get("metadata", {})
                              .get("annotations", {})
                              .get("eks.amazonaws.com/role-arn"))
            if self.irsa_role:
                self.add(section, "IRSA", CheckStatus.PASS,
                         f"SA '{sa}' con IRSA → {self.irsa_role}")
            else:
                self.add(section, "IRSA", CheckStatus.INFO,
                         f"SA '{sa}' sin eks.amazonaws.com/role-arn")

    # ── 1. EKS Cluster ───────────────────────────────────────────────────

    def check_cluster(self):
        section = "1. EKS Cluster"
        eks = self._aws("eks")
        if not eks or not self.cluster_name:
            self.add(section, "cluster", CheckStatus.SKIP,
                     "Sin sesión AWS o sin --cluster")
            return
        try:
            self.cluster = eks.describe_cluster(
                name=self.cluster_name)["cluster"]
        except ClientError as e:
            self.add(section, "cluster", CheckStatus.FAIL, str(e)[:120],
                     f"aws eks describe-cluster --name "
                     f"{self.cluster_name}")
            return
        status = self.cluster.get("status")
        self.add(section, "cluster", CheckStatus.PASS
                 if status == "ACTIVE" else CheckStatus.WARN,
                 f"{self.cluster_name} — {status} "
                 f"v{self.cluster.get('version')}")
        vpc_cfg = self.cluster.get("resourcesVpcConfig", {})
        self.add(section, "endpoint access",
                 CheckStatus.PASS if vpc_cfg.get(
                     "endpointPrivateAccess") else CheckStatus.WARN,
                 f"public={vpc_cfg.get('endpointPublicAccess')} "
                 f"private={vpc_cfg.get('endpointPrivateAccess')}")

    # ── 2. RDS ───────────────────────────────────────────────────────────

    def check_rds(self):
        section = "2. RDS Instance"
        rds = self._aws("rds")
        if not rds or not self.rds_instance_id:
            self.add(section, "instance", CheckStatus.SKIP,
                     "Sin sesión AWS o sin --rds-instance")
            return
        try:
            resp = rds.describe_db_instances(
                DBInstanceIdentifier=self.rds_instance_id)
            self.rds = resp["DBInstances"][0]
        except ClientError as e:
            self.add(section, "instance", CheckStatus.FAIL, str(e)[:120],
                     f"aws rds describe-db-instances "
                     f"--db-instance-identifier {self.rds_instance_id}")
            return
        status = self.rds.get("DBInstanceStatus")
        ep = self.rds.get("Endpoint", {})
        self.add(section, "instance", CheckStatus.PASS
                 if status == "available" else CheckStatus.WARN,
                 f"{self.rds_instance_id} — {status} "
                 f"{self.rds.get('Engine')} "
                 f"{self.rds.get('DBInstanceClass')}")
        self.add(section, "endpoint", CheckStatus.INFO,
                 f"{ep.get('Address')}:{ep.get('Port')}")
        if self.rds.get("PubliclyAccessible"):
            self.add(section, "public access", CheckStatus.WARN,
                     "RDS es públicamente accesible")

    # ── 3. VPC ───────────────────────────────────────────────────────────

    def check_vpc(self):
        section = "3. VPC"
        if not self.cluster or not self.rds:
            self.add(section, "vpc", CheckStatus.SKIP,
                     "Requiere cluster y RDS resueltos")
            return
        cluster_vpc = (self.cluster.get("resourcesVpcConfig", {})
                       .get("vpcId"))
        rds_vpc = (self.rds.get("DBSubnetGroup", {}) or {}).get("VpcId")
        if cluster_vpc == rds_vpc:
            self.add(section, "vpc", CheckStatus.PASS,
                     f"Cluster y RDS en la misma VPC {cluster_vpc}")
        else:
            self.add(section, "vpc", CheckStatus.WARN,
                     f"Cluster VPC {cluster_vpc} ≠ RDS VPC {rds_vpc} — "
                     f"requiere VPC peering/transit gateway",
                     "aws ec2 describe-vpc-peering-connections")

    # ── 4. Security Groups ───────────────────────────────────────────────

    def check_security_groups(self):
        section = "4. Security Groups"
        ec2 = self._aws("ec2")
        if not ec2 or not self.rds:
            self.add(section, "sgs", CheckStatus.SKIP,
                     "Requiere sesión AWS y RDS resuelto")
            return
        port = (self.rds.get("Endpoint", {}) or {}).get("Port") or 0
        rds_sgs = [sg["VpcSecurityGroupId"] for sg in
                   self.rds.get("VpcSecurityGroups", [])
                   if sg.get("Status") == "active"]
        cluster_sgs = set()
        if self.cluster:
            vc = self.cluster.get("resourcesVpcConfig", {})
            cluster_sgs = set(vc.get("securityGroupIds", []))
            if vc.get("clusterSecurityGroupId"):
                cluster_sgs.add(vc["clusterSecurityGroupId"])

        open_to_cluster, open_all = False, False
        for sg_id in rds_sgs:
            try:
                sg = ec2.describe_security_groups(
                    GroupIds=[sg_id])["SecurityGroups"][0]
            except ClientError as e:
                self.add(section, sg_id, CheckStatus.WARN,
                         f"No se pudo leer: {e}"[:100])
                continue
            for rule in sg.get("IpPermissions", []):
                from_p = rule.get("FromPort", 0)
                to_p = rule.get("ToPort", 65535)
                if not (from_p <= port <= to_p):
                    continue
                for pair in rule.get("UserIdGroupPairs", []):
                    if pair.get("GroupId") in cluster_sgs:
                        open_to_cluster = True
                for ipr in rule.get("IpRanges", []):
                    if ipr.get("CidrIp") == "0.0.0.0/0":
                        open_all = True
        if open_all:
            self.add(section, "ingress", CheckStatus.WARN,
                     f"SGs de RDS abren :{port} a 0.0.0.0/0 — "
                     f"conectividad OK pero riesgo de seguridad")
        elif open_to_cluster:
            self.add(section, "ingress", CheckStatus.PASS,
                     f"SGs de RDS permiten :{port} desde SG del cluster")
        else:
            self.add(section, "ingress", CheckStatus.FAIL,
                     f"Ningún SG de RDS permite :{port} desde SGs del "
                     f"cluster {sorted(cluster_sgs)}",
                     f"aws ec2 authorize-security-group-ingress "
                     f"--group-id <rds-sg> --protocol tcp --port {port} "
                     f"--source-group <cluster-sg>")

    # ── 5. IAM / IRSA ────────────────────────────────────────────────────

    def check_iam(self):
        section = "5. IAM / IRSA"
        iam = self._aws("iam")
        if not self.irsa_role:
            self.add(section, "irsa", CheckStatus.INFO,
                     "Sin IRSA — la app usa credenciales de nodo o "
                     "secretos k8s")
            return
        if not iam:
            self.add(section, "irsa", CheckStatus.SKIP, "Sin sesión AWS")
            return
        role_name = self.irsa_role.rsplit("/", 1)[-1]
        try:
            role = iam.get_role(RoleName=role_name)["Role"]
            self.add(section, "irsa", CheckStatus.PASS,
                     f"Rol {role_name} existe "
                     f"(creado {role['CreateDate'].date()})")
        except ClientError as e:
            self.add(section, "irsa", CheckStatus.FAIL, str(e)[:120])
        # Simular permisos comunes (rds-db:connect / secretsmanager)
        try:
            resp = iam.simulate_principal_policy(
                PolicySourceArn=self.irsa_role,
                ActionNames=["rds-db:connect",
                             "secretsmanager:GetSecretValue"],
                ResourceArns=["*"])
            for ev in resp.get("EvaluationResults", []):
                dec = ev.get("EvalDecision")
                self.add(section, ev["EvalActionName"],
                         CheckStatus.PASS if dec == "allowed"
                         else CheckStatus.WARN,
                         f"simulación: {dec}")
        except ClientError:
            self.add(section, "simulate", CheckStatus.INFO,
                     "Sin permiso iam:SimulatePrincipalPolicy")

    # ── 6. Load Balancers ────────────────────────────────────────────────

    def check_load_balancers(self):
        section = "6. Load Balancers"
        data = kubectl_json(["get", "services", "-n", self.namespace],
                            self.debug)
        lbs = []
        for svc in (data or {}).get("items", []):
            if svc.get("spec", {}).get("type") == "LoadBalancer":
                ing = (svc.get("status", {}).get("loadBalancer", {})
                       .get("ingress", []))
                host = (ing[0].get("hostname") or ing[0].get("ip")
                        if ing else "pending")
                lbs.append((svc["metadata"]["name"], host))
        if not lbs:
            self.add(section, "services", CheckStatus.INFO,
                     "Sin services tipo LoadBalancer en el namespace")
        for name, host in lbs:
            self.add(section, name, CheckStatus.PASS,
                     f"LoadBalancer → {host}")

    # ── 7. TCP test ──────────────────────────────────────────────────────

    def check_connectivity(self):
        section = "7. TCP Test"
        if not self.rds:
            self.add(section, "test", CheckStatus.SKIP,
                     "Sin RDS resuelto")
            return
        ep = self.rds.get("Endpoint", {})
        host, port = ep.get("Address"), ep.get("Port")
        pod_name = f"conn-probe-{int(time.time())}"
        code, _, stderr = run_command(
            ["kubectl", "run", pod_name, "--image", self.probe_image,
             "--restart=Never", "-n", self.namespace, "--",
             "sleep", "120"], self.debug, timeout=30)
        if code != 0:
            self.add(section, "test", CheckStatus.WARN,
                     f"No se pudo crear pod probe: {stderr[:100]}",
                     "Verificar permisos kubectl run en el namespace")
            return
        try:
            for _ in range(30):
                pod = kubectl_json(["get", "pod", pod_name,
                                    "-n", self.namespace],
                                   self.debug, timeout=15)
                phase = (pod or {}).get("status", {}).get("phase")
                if phase == "Running":
                    break
                time.sleep(2)
            else:
                self.add(section, "test", CheckStatus.WARN,
                         "Pod probe no llegó a Running")
                return
            code, _, stderr = run_command(
                ["kubectl", "exec", pod_name, "-n", self.namespace,
                 "--", "nc", "-z", "-w", str(self.timeout),
                 host, str(port)], self.debug,
                timeout=self.timeout + 15)
            if code == 0:
                self.add(section, "test", CheckStatus.PASS,
                         f"nc {host}:{port} OK desde pod en "
                         f"{self.namespace}")
            else:
                self.add(section, "test", CheckStatus.FAIL,
                         f"nc {host}:{port} falló — "
                         f"{(stderr or 'timeout')[:100]}",
                         "Revisar Security Groups de RDS (sección 4)")
        finally:
            run_command(["kubectl", "delete", "pod", pod_name,
                         "-n", self.namespace, "--wait=false"],
                        self.debug, timeout=15)

    # ── Orquestación ─────────────────────────────────────────────────────

    def run_all(self) -> List[CheckResult]:
        self.check_deployment()
        self.check_cluster()
        self.check_rds()
        self.check_vpc()
        self.check_security_groups()
        self.check_iam()
        self.check_load_balancers()
        self.check_connectivity()
        return self.results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Valida conectividad pod EKS → RDS")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--cluster", "-c", default="",
                        help="Cluster EKS (vacío = contexto actual)")
    parser.add_argument("--deployment", "-d", default="",
                        help="Deployment origen (auto-descubre ns/SA/IRSA)")
    parser.add_argument("--namespace", "-n", default="")
    parser.add_argument("--rds-instance", "-s", required=True,
                        help="DBInstanceIdentifier de RDS")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--probe-image", default=DEFAULT_PROBE_IMAGE)
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

    checker = EKSConnectivityChecker(
        profile=args.profile, region=args.region,
        cluster_name=args.cluster, deployment=args.deployment,
        namespace=args.namespace, rds_instance=args.rds_instance,
        timeout=args.timeout, probe_image=args.probe_image,
        debug=args.debug)

    if console:
        console.print(Panel.fit(
            f"[bold cyan]EKS Pod Connectivity Checker[/bold cyan]\n"
            f"RDS: [yellow]{args.rds_instance}[/yellow] | "
            f"Deployment: {args.deployment or '—'} | "
            f"Cluster: {args.cluster or 'contexto actual'}",
            title="🔌 Connectivity"))
    results = checker.run_all()

    fails = [r for r in results if r.status == CheckStatus.FAIL]
    warns = [r for r in results if r.status == CheckStatus.WARN]
    passed = [r for r in results if r.status == CheckStatus.PASS]

    if console:
        console.print(Panel.fit(
            f"✅ PASS: {len(passed)} | ❌ FAIL: [red]{len(fails)}[/red] | "
            f"⚠️ WARN: [yellow]{len(warns)}[/yellow]",
            title="📊 Resumen"))
    else:
        print(f"\nPASS: {len(passed)} | FAIL: {len(fails)} | "
              f"WARN: {len(warns)}")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"eks_connectivity_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "rds_instance": args.rds_instance,
                "deployment": args.deployment,
                "cluster": args.cluster,
                "timestamp": datetime.utcnow().isoformat(),
                "results": [r.as_dict() for r in results],
            }, indent=2, default=str), encoding="utf-8")
        else:
            import csv
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "section", "check", "status", "message",
                    "remediation"])
                w.writeheader()
                for r in results:
                    w.writerow(r.as_dict())
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
