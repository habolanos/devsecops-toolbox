#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EKS Deployments Off Analyzer — Tool 35

Analiza todos los deployments en estado no running en un cluster EKS,
proporcionando diagnóstico automático y recomendaciones.

Equivalente a GCP Tool: Deployments Off Analyzer
(deployments_off/gcp_deployments_off_analyzer.py).

Usa kubectl (contexto actual o `aws eks update-kubeconfig` cuando se pasa
--cluster) — no requiere la librería kubernetes.

Uso:
    python aws_eks_deployments_off_analyzer.py --profile default --region us-east-1
    python aws_eks_deployments_off_analyzer.py --cluster my-eks -o json
    python aws_eks_deployments_off_analyzer.py --cluster my-eks --namespace production
"""

import argparse
import csv
import json
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

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "DevSecOps Team"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers de proceso
# ═══════════════════════════════════════════════════════════════════════════════

def run_command(cmd: List[str], debug: bool = False,
                timeout: Optional[int] = 60) -> Tuple[int, str, str]:
    """Ejecuta un comando y retorna código, stdout, stderr."""
    if debug:
        print(f"[DEBUG] Ejecutando: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout)
        if debug and result.stderr.strip():
            print(f"[DEBUG] stderr: {result.stderr.strip()[:400]}")
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout tras {timeout}s"
    except FileNotFoundError:
        return 127, "", "Comando no encontrado"


def configure_kubectl_context(cluster: str, region: str, profile: str,
                              debug: bool = False) -> bool:
    """Configura el contexto de kubectl vía `aws eks update-kubeconfig`."""
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


def kubectl_json(args: List[str], debug: bool = False,
                 timeout: int = 60) -> Optional[Dict]:
    """Ejecuta `kubectl <args> -o json` y devuelve el JSON parseado."""
    code, stdout, _ = run_command(["kubectl"] + args + ["-o", "json"],
                                  debug, timeout=timeout)
    if code != 0 or not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Analizador
# ═══════════════════════════════════════════════════════════════════════════════

class EKSDeploymentsOffAnalyzer:
    """Analiza deployments no running en EKS (diagnóstico + recomendaciones)."""

    CLASSIFICATIONS = {
        "ImagePullBackOff": "Image Registry",
        "ImagePullError": "Image Registry",
        "ErrImagePull": "Image Registry",
        "InvalidImageName": "Image Registry",
        "CrashLoopBackOff": "Application Error",
        "BackOff": "Application Error",
        "Failed": "Application Error",
        "FailedScheduling": "Resource Constraint",
        "Insufficient": "Resource Constraint",
        "FailedCreatePodSandbox": "Infrastructure Error",
        "FailedMount": "Configuration Error",
        "ConfigError": "Configuration Error",
        "CreateContainerConfigError": "Configuration Error",
    }

    def __init__(self, cluster: str, namespace: Optional[str] = None,
                 debug: bool = False):
        self.cluster = cluster
        self.namespace = namespace
        self.debug = debug

    # ── Datos de k8s ────────────────────────────────────────────────────

    def _get_namespaces(self) -> List[str]:
        if self.namespace:
            return [self.namespace]
        data = kubectl_json(["get", "namespaces"], self.debug)
        if not data:
            return []
        return [i["metadata"]["name"] for i in data.get("items", [])]

    def _get_non_running_deployments(self, namespace: str) -> List[Dict]:
        data = kubectl_json(["get", "deployments", "-n", namespace],
                            self.debug)
        non_running = []
        for dep in (data or {}).get("items", []):
            status = dep.get("status", {})
            desired = status.get("replicas", 0)
            ready = status.get("readyReplicas", 0)
            if ready < desired or desired == 0:
                non_running.append({
                    "name": dep["metadata"]["name"],
                    "namespace": namespace,
                    "desired": desired,
                    "ready": ready,
                    "updated": status.get("updatedReplicas", 0),
                    "available": status.get("availableReplicas", 0),
                })
        return non_running

    def _get_pods(self, namespace: str) -> List[Dict]:
        data = kubectl_json(["get", "pods", "-n", namespace], self.debug)
        return (data or {}).get("items", [])

    def _get_events(self, namespace: str) -> List[Dict]:
        data = kubectl_json(["get", "events", "-n", namespace], self.debug)
        return (data or {}).get("items", [])

    # ── Análisis ────────────────────────────────────────────────────────

    @staticmethod
    def _container_state(cs: Dict) -> Dict:
        state = cs.get("state", {})
        if "running" in state:
            return {"type": "Running"}
        if "waiting" in state:
            w = state["waiting"]
            return {"type": "Waiting",
                    "reason": w.get("reason", ""),
                    "message": w.get("message", "")}
        if "terminated" in state:
            t = state["terminated"]
            return {"type": "Terminated",
                    "exit_code": t.get("exitCode"),
                    "reason": t.get("reason", ""),
                    "message": t.get("message", "")}
        return {"type": "Unknown"}

    def _analyze_pods(self, namespace: str, deployment_name: str,
                      pods: List[Dict]) -> List[Dict]:
        pods_info = []
        for pod in pods:
            if deployment_name not in pod["metadata"]["name"]:
                continue
            status = pod.get("status", {})
            info = {
                "name": pod["metadata"]["name"],
                "phase": status.get("phase", "Unknown"),
                "conditions": [{
                    "type": c.get("type"),
                    "status": c.get("status"),
                    "reason": c.get("reason"),
                    "message": c.get("message"),
                } for c in status.get("conditions", [])],
                "container_statuses": [],
                "restart_count": 0,
            }
            for cs in status.get("containerStatuses", []):
                info["container_statuses"].append({
                    "name": cs.get("name"),
                    "ready": cs.get("ready", False),
                    "restart_count": cs.get("restartCount", 0),
                    "state": self._container_state(cs),
                })
                info["restart_count"] = max(info["restart_count"],
                                            cs.get("restartCount", 0))
            pods_info.append(info)
        return pods_info

    def _deployment_events(self, namespace: str, deployment_name: str,
                           all_events: List[Dict]) -> List[Dict]:
        events = []
        for ev in all_events:
            obj = ev.get("involvedObject", {})
            if deployment_name in obj.get("name", ""):
                events.append({
                    "timestamp": ev.get("lastTimestamp")
                                 or ev.get("eventTime") or "",
                    "reason": ev.get("reason", ""),
                    "message": ev.get("message", ""),
                    "type": ev.get("type", ""),
                    "count": ev.get("count", 1),
                })
        events.sort(key=lambda e: e["timestamp"], reverse=True)
        return events[:10]

    def _classify_event(self, event: Dict) -> Optional[Dict]:
        reason = event.get("reason", "") or ""
        # Claves más largas primero: 'FailedScheduling' debe ganar a 'Failed'
        for key in sorted(self.CLASSIFICATIONS, key=len, reverse=True):
            if key in reason:
                return {"type": reason, "category":
                        self.CLASSIFICATIONS[key],
                        "message": event.get("message", ""),
                        "source": "Event"}
        return None

    def _identify_root_causes(self, pods: List[Dict],
                              events: List[Dict]) -> List[Dict]:
        causes = []
        for event in events:
            cause = self._classify_event(event)
            if cause:
                causes.append(cause)
        for pod in pods:
            for condition in pod.get("conditions", []):
                if condition["status"] != "True":
                    causes.append({
                        "type": condition["type"],
                        "reason": condition.get("reason") or "Unknown",
                        "message": condition.get("message") or "",
                        "source": "Pod Condition"})
            for cs in pod.get("container_statuses", []):
                if cs["state"]["type"] != "Running":
                    causes.append({
                        "type": cs["state"]["type"],
                        "reason": cs["state"].get("reason") or "Unknown",
                        "message": cs["state"].get("message") or "",
                        "source": "Container State"})

        unique, seen = [], set()
        for cause in causes:
            key = (cause["type"], cause.get("reason"))
            if key not in seen:
                unique.append(cause)
                seen.add(key)
        return unique

    @staticmethod
    def _generate_recommendations(causes: List[Dict]) -> List[Dict]:
        recommendations = []
        seen_types = set()
        for cause in causes:
            ctype = cause["type"]
            if ctype in seen_types:
                continue
            seen_types.add(ctype)
            if "ImagePull" in ctype or "InvalidImageName" in ctype:
                recommendations.append({
                    "action": "Verificar imagen de contenedor",
                    "priority": "HIGH",
                    "steps": [
                        "Validar que la imagen existe en ECR/registry",
                        "Verificar credenciales de acceso (imagePullSecrets)",
                        "Revisar imagePullPolicy",
                        "Confirmar que los nodos EKS tienen permisos de pull "
                        "en ECR (rol del node group)"],
                })
            elif "CrashLoop" in ctype or "BackOff" in ctype:
                recommendations.append({
                    "action": "Analizar logs de aplicación",
                    "priority": "CRITICAL",
                    "steps": [
                        "kubectl logs POD -n NAMESPACE --previous",
                        "Revisar logs del pod para errores",
                        "Validar variables de entorno y configmaps",
                        "Revisar liveness/readiness probes",
                        "Aumentar initialDelaySeconds si aplica"],
                })
            elif "FailedScheduling" in ctype or "Insufficient" in ctype:
                recommendations.append({
                    "action": "Aumentar capacidad del cluster",
                    "priority": "HIGH",
                    "steps": [
                        "Revisar requests/limits del deployment",
                        "kubectl top nodes",
                        "Escalar node groups / cluster autoscaler",
                        "Considerar Karpenter/Cluster Autoscaler en EKS",
                        "Revisar node selectors y affinities"],
                })
            elif "Mount" in ctype or "ConfigError" in ctype or \
                    "CreateContainerConfig" in ctype:
                recommendations.append({
                    "action": "Verificar configuración",
                    "priority": "HIGH",
                    "steps": [
                        "kubectl get secrets -n NAMESPACE",
                        "kubectl get configmaps -n NAMESPACE",
                        "Revisar referencias a Secrets/ConfigMaps/AWS "
                        "Secrets Manager (IRSA)",
                        "Validar rutas de mount"],
                })
        return recommendations

    @staticmethod
    def _calculate_severity(causes: List[Dict]) -> str:
        if not causes:
            return "LOW"
        for cause in causes:
            text = f"{cause.get('type', '')} {cause.get('reason', '')}"
            for kw in ("CrashLoop", "ImagePull", "ErrImagePull",
                       "FailedScheduling"):
                if kw in text:
                    return "CRITICAL"
        return "HIGH"

    def _analyze_deployment(self, namespace: str, deployment: Dict,
                            pods: List[Dict],
                            events: List[Dict]) -> Dict:
        dep_pods = self._analyze_pods(namespace, deployment["name"], pods)
        dep_events = self._deployment_events(namespace, deployment["name"],
                                             events)
        causes = self._identify_root_causes(dep_pods, dep_events)
        return {
            "namespace": namespace,
            "deployment": deployment["name"],
            "timestamp": datetime.utcnow().isoformat(),
            "replica_status": {
                "desired": deployment["desired"],
                "ready": deployment["ready"],
                "updated": deployment["updated"],
                "available": deployment["available"],
            },
            "pods": dep_pods,
            "events": dep_events,
            "root_causes": causes,
            "recommendations": self._generate_recommendations(causes),
            "severity": self._calculate_severity(causes),
        }

    def analyze_all(self) -> List[Dict]:
        results = []
        namespaces = self._get_namespaces()
        if not namespaces:
            _print("⚠ No se pudieron listar namespaces (kubectl)", "yellow")
            return results
        for ns in namespaces:
            pods = self._get_pods(ns)
            events = self._get_events(ns)
            for dep in self._get_non_running_deployments(ns):
                results.append(self._analyze_deployment(ns, dep, pods,
                                                        events))
        return results

    # ── Presentación ────────────────────────────────────────────────────

    def print_results_table(self, results: List[Dict]):
        if not results:
            _print("✓ No hay deployments no running", "green")
            return
        if console:
            table = Table(title="Deployments No Running (EKS)",
                          show_header=True, header_style="bold cyan")
            for col, st in [("Namespace", "magenta"), ("Deployment", "cyan"),
                            ("Severity", "red"), ("Desired", "yellow"),
                            ("Ready", "yellow"), ("Root Cause", "white")]:
                table.add_column(col, style=st)
            for r in results:
                sev_color = "red" if r["severity"] == "CRITICAL" else "yellow"
                causes = "; ".join(c["type"] for c in r["root_causes"]) \
                    or "Unknown"
                table.add_row(
                    r["namespace"], r["deployment"],
                    f"[{sev_color}]{r['severity']}[/{sev_color}]",
                    str(r["replica_status"]["desired"]),
                    str(r["replica_status"]["ready"]), causes[:50])
            console.print(table)
        else:
            for r in results:
                causes = "; ".join(c["type"] for c in r["root_causes"]) \
                    or "Unknown"
                print(f"{r['namespace']}/{r['deployment']} "
                      f"[{r['severity']}] "
                      f"{r['replica_status']['ready']}/"
                      f"{r['replica_status']['desired']} — {causes}")


# ═══════════════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════════════

def export_json(results: List[Dict], output_file: Path):
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_deployments": len(results),
        "critical_count": len([r for r in results
                               if r["severity"] == "CRITICAL"]),
        "high_count": len([r for r in results
                           if r["severity"] == "HIGH"]),
        "deployments": results,
    }
    output_file.write_text(json.dumps(report, indent=2, default=str),
                           encoding="utf-8")


def export_csv(results: List[Dict], output_file: Path):
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "namespace", "deployment", "severity", "desired_replicas",
            "ready_replicas", "root_causes", "recommendations"])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "namespace": r["namespace"],
                "deployment": r["deployment"],
                "severity": r["severity"],
                "desired_replicas": r["replica_status"]["desired"],
                "ready_replicas": r["replica_status"]["ready"],
                "root_causes": "; ".join(c["type"]
                                         for c in r["root_causes"]),
                "recommendations": "; ".join(x["action"]
                                             for x in r["recommendations"]),
            })


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Analiza deployments no running en AWS EKS")
    parser.add_argument("--profile", "-p", default="default",
                        help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1",
                        help="AWS region")
    parser.add_argument("--cluster", "-c", default="",
                        help="Nombre del cluster EKS (vacío = contexto "
                             "kubectl actual)")
    parser.add_argument("--namespace", "-n", default=None,
                        help="Namespace específico (opcional)")
    parser.add_argument("-o", "--output", choices=["json", "csv"],
                        default=None, help="Formato de exportación")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def main():
    start = time.time()
    args = get_args()

    if args.cluster:
        if not configure_kubectl_context(args.cluster, args.region,
                                         args.profile, args.debug):
            sys.exit(1)

    analyzer = EKSDeploymentsOffAnalyzer(
        cluster=args.cluster or "(contexto actual)",
        namespace=args.namespace, debug=args.debug)

    if console:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                      transient=True, console=console) as prog:
            prog.add_task("[cyan]Analizando deployments en EKS...",
                          total=None)
            results = analyzer.analyze_all()
    else:
        results = analyzer.analyze_all()

    analyzer.print_results_table(results)

    critical = len([r for r in results if r["severity"] == "CRITICAL"])
    high = len([r for r in results if r["severity"] == "HIGH"])
    elapsed = f"{int(time.time() - start)}s"

    if console:
        console.print(Panel.fit(
            f"[bold]Total No Running:[/bold] {len(results)}\n"
            f"[bold]Critical:[/bold] [red]{critical}[/red] | "
            f"[bold]High:[/bold] [yellow]{high}[/yellow]\n"
            f"[bold]Tiempo:[/bold] {elapsed}", title="📊 Resumen"))
    else:
        print(f"\nTotal No Running: {len(results)} | Critical: {critical} "
              f"| High: {high} | {elapsed}")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"eks_deployments_off_{ts}.{args.output}"
        if args.output == "json":
            export_json(results, out)
        else:
            export_csv(results, out)
        _print(f"✓ Reporte exportado a: {out}", "green")


if __name__ == "__main__":
    main()
