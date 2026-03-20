#!/usr/bin/env python3
"""
Cloud SQL Connectivity Checker
==============================
Valida la conectividad desde un Pod de GKE hasta una instancia de Cloud SQL,
verificando todos los elementos involucrados en la cadena de conectividad.

Modo simplificado: Solo requiere --deployment y --sql-instance
El script descubre automáticamente: cluster, namespace, service accounts, etc.

Elementos validados:
0. Deployment - información del pod y configuración
1. GKE Cluster - configuración de red
2. Cloud SQL Instance - estado y configuración de IP
3. VPC Network - red compartida
4. Private Service Connection - para IP privada
5. Firewall Rules - reglas de egress/ingress
6. IAM Permissions - permisos del Service Account
7. Workload Identity - binding KSA ↔ GSA
8. Load Balancers - servicios que median la conectividad
9. Connectivity Test - prueba de conectividad de red
"""

import subprocess
import json
import sys
import argparse
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

__version__ = "1.2.0"


class CheckStatus(Enum):
    """Estado de cada validación."""
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARN = "⚠️  WARN"
    INFO = "ℹ️  INFO"
    SKIP = "⏭️  SKIP"


@dataclass
class CheckResult:
    """Resultado de una validación."""
    name: str
    status: CheckStatus
    message: str
    details: Optional[str] = None
    remediation: Optional[str] = None


class ResultsTable:
    """Tabla de resultados que se actualiza en tiempo real."""
    
    def __init__(self):
        self.results: List[CheckResult] = []
        self.current_section = ""
        self.col_widths = {
            "num": 4,
            "section": 25,
            "check": 40,
            "status": 10,
            "message": 50
        }
    
    def _truncate(self, text: str, max_len: int) -> str:
        """Trunca texto si excede el máximo."""
        if len(text) <= max_len:
            return text
        return text[:max_len-3] + "..."
    
    def _get_status_symbol(self, status: CheckStatus) -> str:
        """Retorna solo el símbolo del estado."""
        symbols = {
            CheckStatus.PASS: "✅",
            CheckStatus.FAIL: "❌",
            CheckStatus.WARN: "⚠️ ",
            CheckStatus.INFO: "ℹ️ ",
            CheckStatus.SKIP: "⏭️ "
        }
        return symbols.get(status, "?")
    
    def _get_status_text(self, status: CheckStatus) -> str:
        """Retorna el texto del estado."""
        texts = {
            CheckStatus.PASS: "PASS",
            CheckStatus.FAIL: "FAIL",
            CheckStatus.WARN: "WARN",
            CheckStatus.INFO: "INFO",
            CheckStatus.SKIP: "SKIP"
        }
        return texts.get(status, "?")
    
    def print_header(self):
        """Imprime el encabezado de la tabla."""
        print("\n" + "="*135)
        print(f"{'#':<4} {'SECCIÓN':<25} {'VALIDACIÓN':<40} {'ESTADO':<10} {'MENSAJE':<50}")
        print("="*135)
    
    def set_section(self, section: str):
        """Establece la sección actual."""
        self.current_section = section
    
    def add_row(self, result: CheckResult):
        """Agrega una fila a la tabla y la imprime."""
        self.results.append(result)
        num = len(self.results)
        
        section = self._truncate(self.current_section, self.col_widths["section"])
        check = self._truncate(result.name, self.col_widths["check"])
        status = f"{self._get_status_symbol(result.status)} {self._get_status_text(result.status)}"
        message = self._truncate(result.message, self.col_widths["message"])
        
        print(f"{num:<4} {section:<25} {check:<40} {status:<10} {message:<50}")
        
        # Si es un error, mostrar remediación debajo
        if result.status == CheckStatus.FAIL and result.remediation:
            print(f"{'':4} {'':25} {'💡 Remediación:':<40} {self._truncate(result.remediation, 80)}")
    
    def print_separator(self):
        """Imprime un separador."""
        print("-"*135)
    
    def print_summary(self):
        """Imprime el resumen final de la tabla."""
        print("="*135)
        
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAIL)
        warnings = sum(1 for r in self.results if r.status == CheckStatus.WARN)
        info = sum(1 for r in self.results if r.status == CheckStatus.INFO)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIP)
        
        summary = f"TOTAL: {len(self.results)} | ✅ {passed} | ❌ {failed} | ⚠️  {warnings} | ℹ️  {info} | ⏭️  {skipped}"
        print(f"{summary:^135}")
        print("="*135)
        
        # Mostrar resultado final
        if failed == 0:
            print(f"{'✅ TODAS LAS VALIDACIONES CRÍTICAS PASARON':^135}")
        else:
            print(f"{'❌ HAY VALIDACIONES QUE REQUIEREN ATENCIÓN':^135}")
        print("="*135)
        
        # Mostrar acciones requeridas si hay errores
        if failed > 0:
            print("\n📋 ACCIONES REQUERIDAS:")
            print("-"*135)
            for i, r in enumerate(self.results, 1):
                if r.status == CheckStatus.FAIL and r.remediation:
                    print(f"  {i}. {r.name}")
                    print(f"     $ {r.remediation}")
                    print()
    
    def export_markdown(self) -> str:
        """Exporta la tabla en formato Markdown."""
        lines = []
        lines.append("| # | Sección | Validación | Estado | Mensaje |")
        lines.append("|---|---------|------------|--------|---------|")
        
        for i, r in enumerate(self.results, 1):
            status = f"{self._get_status_symbol(r.status)} {self._get_status_text(r.status)}"
            lines.append(f"| {i} | {self.current_section} | {r.name} | {status} | {r.message} |")
        
        return "\n".join(lines)


def check_gcp_connection(project_id, verbose=False):
    """Valida conexión a GCP antes de ejecutar el script"""
    try:
        auth_cmd = 'gcloud auth list --filter=status:ACTIVE --format="value(account)"'
        auth_result = subprocess.run(auth_cmd, shell=True, capture_output=True, text=True)
        
        if verbose:
            print(f"[DEBUG] Auth command: {auth_cmd}")
            print(f"[DEBUG] Auth result: {auth_result.stdout.strip()}")
        
        if auth_result.returncode != 0 or not auth_result.stdout.strip():
            print("❌ No hay sesión activa de gcloud. Ejecuta: gcloud auth login")
            return False
        
        active_account = auth_result.stdout.strip().split('\n')[0]
        print(f"🔐 Cuenta activa: {active_account}")
        
        if project_id:
            project_cmd = f'gcloud projects describe {project_id} --format="value(projectId)" 2>&1'
            project_result = subprocess.run(project_cmd, shell=True, capture_output=True, text=True)
            
            if verbose:
                print(f"[DEBUG] Project command: {project_cmd}")
                print(f"[DEBUG] Project result: {project_result.stdout.strip()}")
            
            if project_result.returncode != 0:
                error_msg = project_result.stderr or project_result.stdout
                if "not found" in error_msg.lower() or "permission" in error_msg.lower():
                    print(f"❌ No tienes acceso al proyecto: {project_id}")
                else:
                    print(f"❌ Error de conexión: {error_msg.strip()}")
                return False
            
            print(f"✅ Conexión verificada al proyecto: {project_id}")
        else:
            print("ℹ️  Proyecto se detectará automáticamente")
        
        return True
        
    except Exception as e:
        if verbose:
            print(f"[DEBUG] Connection check exception: {e}")
        print(f"❌ Error verificando conexión: {e}")
        return False


class ConnectivityChecker:
    """Validador de conectividad Pod → Cloud SQL."""
    
    def __init__(
        self,
        sql_instance: str,
        deployment: Optional[str] = None,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        gke_cluster: Optional[str] = None,
        gke_location: Optional[str] = None,
        namespace: str = "default",
        ksa_name: Optional[str] = None,
        gsa_email: Optional[str] = None,
        verbose: bool = False
    ):
        self.sql_instance = sql_instance
        self.deployment = deployment
        self.namespace = namespace
        self.ksa_name = ksa_name
        self.gsa_email = gsa_email
        self.verbose = verbose
        self.results: List[CheckResult] = []
        
        # Tabla de resultados en tiempo real
        self.table = ResultsTable()
        
        # Estos se pueden descubrir automáticamente
        self._provided_project_id = project_id
        self._provided_region = region
        self._provided_gke_cluster = gke_cluster
        self._provided_gke_location = gke_location
        
        # Se inicializan después del discovery
        self.project_id: Optional[str] = project_id
        self.region: Optional[str] = region
        self.gke_cluster: Optional[str] = gke_cluster
        self.gke_location: Optional[str] = gke_location
        
        # Cache para datos obtenidos
        self._sql_info: Optional[Dict] = None
        self._cluster_info: Optional[Dict] = None
        self._vpc_info: Optional[Dict] = None
        self._deployment_info: Optional[Dict] = None
        self._services: List[Dict] = []

    def run_gcloud(self, args: List[str], format_json: bool = True) -> tuple[bool, Any]:
        """Ejecuta un comando gcloud y retorna el resultado."""
        cmd = ["gcloud"] + args + ["--project", self.project_id]
        if format_json:
            cmd += ["--format", "json"]
        
        if self.verbose:
            print(f"  [CMD] {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                return False, result.stderr
            
            if format_json and result.stdout.strip():
                return True, json.loads(result.stdout)
            return True, result.stdout
        except subprocess.TimeoutExpired:
            return False, "Timeout ejecutando comando"
        except json.JSONDecodeError as e:
            return False, f"Error parseando JSON: {e}"
        except Exception as e:
            return False, str(e)

    def run_kubectl(self, args: List[str], format_json: bool = True) -> tuple[bool, Any]:
        """Ejecuta un comando kubectl y retorna el resultado."""
        cmd = ["kubectl"] + args
        if format_json:
            cmd += ["-o", "json"]
        
        if self.verbose:
            print(f"  [CMD] {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                return False, result.stderr
            
            if format_json and result.stdout.strip():
                return True, json.loads(result.stdout)
            return True, result.stdout
        except subprocess.TimeoutExpired:
            return False, "Timeout ejecutando comando"
        except json.JSONDecodeError as e:
            return False, f"Error parseando JSON: {e}"
        except Exception as e:
            return False, str(e)

    def add_result(self, result: CheckResult):
        """Agrega un resultado y lo imprime en la tabla."""
        self.results.append(result)
        self.table.add_row(result)
        
        # Si es verbose, mostrar detalles adicionales
        if result.details and self.verbose:
            for line in result.details.split("\n"):
                print(f"{'':4} {'':25} {'':40} {'':10} │ {line}")
    
    def set_section(self, section_name: str):
        """Establece la sección actual para la tabla."""
        self.table.set_section(section_name)
        self.table.print_separator()

    # =========================================================================
    # 0. DISCOVERY - DESCUBRIR INFORMACIÓN AUTOMÁTICAMENTE
    # =========================================================================
    def run_gcloud_no_project(self, args: List[str], format_json: bool = True) -> tuple[bool, Any]:
        """Ejecuta un comando gcloud sin especificar proyecto."""
        cmd = ["gcloud"] + args
        if format_json:
            cmd += ["--format", "json"]
        
        if self.verbose:
            print(f"  [CMD] {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                return False, result.stderr
            
            if format_json and result.stdout.strip():
                return True, json.loads(result.stdout)
            return True, result.stdout
        except subprocess.TimeoutExpired:
            return False, "Timeout ejecutando comando"
        except json.JSONDecodeError as e:
            return False, f"Error parseando JSON: {e}"
        except Exception as e:
            return False, str(e)

    def discover_from_current_context(self) -> bool:
        """Descubre project, cluster y location del contexto actual de kubectl/gcloud."""
        # Obtener proyecto actual de gcloud si no se especificó
        if not self.project_id:
            success, config = self.run_gcloud_no_project([
                "config", "get-value", "project"
            ], format_json=False)
            if success and config.strip():
                self.project_id = config.strip()
                self.add_result(CheckResult(
                    name="Project Discovery",
                    status=CheckStatus.INFO,
                    message=f"Proyecto detectado: {self.project_id}"
                ))
            else:
                self.add_result(CheckResult(
                    name="Project Discovery",
                    status=CheckStatus.FAIL,
                    message="No se pudo detectar el proyecto",
                    remediation="Use --project o configure: gcloud config set project PROJECT_ID"
                ))
                return False
        
        # Obtener contexto actual de kubectl
        success, context = self.run_kubectl([
            "config", "current-context"
        ], format_json=False)
        
        if success and context.strip():
            ctx = context.strip()
            self.add_result(CheckResult(
                name="Kubectl Context",
                status=CheckStatus.INFO,
                message=f"Contexto actual: {ctx}"
            ))
            
            # Extraer cluster y location del contexto GKE (formato: gke_PROJECT_LOCATION_CLUSTER)
            if ctx.startswith("gke_"):
                parts = ctx.split("_")
                if len(parts) >= 4:
                    if not self.gke_location:
                        self.gke_location = parts[2]
                    if not self.gke_cluster:
                        self.gke_cluster = "_".join(parts[3:])
                    self.add_result(CheckResult(
                        name="GKE Context Parsed",
                        status=CheckStatus.PASS,
                        message=f"Cluster: {self.gke_cluster}, Location: {self.gke_location}"
                    ))
        
        return True

    def discover_from_deployment(self) -> bool:
        """Descubre información desde el deployment especificado."""
        if not self.deployment:
            return True
        
        # Buscar el deployment en todos los namespaces si no se especificó
        if self.namespace == "default":
            success, deploys = self.run_kubectl([
                "get", "deployments", "--all-namespaces",
                "--field-selector", f"metadata.name={self.deployment}"
            ])
            
            if success and deploys.get("items"):
                self.namespace = deploys["items"][0].get("metadata", {}).get("namespace", "default")
                self.add_result(CheckResult(
                    name="Deployment Namespace Discovery",
                    status=CheckStatus.INFO,
                    message=f"Namespace detectado: {self.namespace}"
                ))
        
        # Obtener información del deployment
        success, deploy_info = self.run_kubectl([
            "get", "deployment", self.deployment,
            "-n", self.namespace
        ])
        
        if not success:
            self.add_result(CheckResult(
                name="Deployment Exists",
                status=CheckStatus.FAIL,
                message=f"No se encontró el deployment '{self.deployment}' en namespace '{self.namespace}'",
                remediation=f"kubectl get deployments -A | grep {self.deployment}"
            ))
            return False
        
        self._deployment_info = deploy_info
        
        # Extraer Service Account del deployment
        spec = deploy_info.get("spec", {}).get("template", {}).get("spec", {})
        sa_name = spec.get("serviceAccountName") or spec.get("serviceAccount")
        
        if sa_name and not self.ksa_name:
            self.ksa_name = sa_name
            self.add_result(CheckResult(
                name="Deployment Service Account",
                status=CheckStatus.INFO,
                message=f"KSA detectado: {self.ksa_name}"
            ))
        
        # Verificar replicas y estado
        replicas = deploy_info.get("status", {}).get("readyReplicas", 0)
        desired = deploy_info.get("spec", {}).get("replicas", 0)
        
        if replicas >= desired and replicas > 0:
            self.add_result(CheckResult(
                name="Deployment Status",
                status=CheckStatus.PASS,
                message=f"Deployment '{self.deployment}' activo ({replicas}/{desired} replicas)"
            ))
        else:
            self.add_result(CheckResult(
                name="Deployment Status",
                status=CheckStatus.WARN,
                message=f"Deployment tiene {replicas}/{desired} replicas listas"
            ))
        
        # Buscar GSA desde la anotación del KSA si existe
        if self.ksa_name and not self.gsa_email:
            success, ksa_info = self.run_kubectl([
                "get", "serviceaccount", self.ksa_name,
                "-n", self.namespace
            ])
            if success:
                annotations = ksa_info.get("metadata", {}).get("annotations", {})
                gsa = annotations.get("iam.gke.io/gcp-service-account")
                if gsa:
                    self.gsa_email = gsa
                    self.add_result(CheckResult(
                        name="GSA Discovery",
                        status=CheckStatus.INFO,
                        message=f"GSA detectado desde KSA: {self.gsa_email}"
                    ))
        
        # Descubrir servicios relacionados al deployment
        self._discover_related_services()
        
        return True

    def _discover_related_services(self):
        """Descubre servicios de Kubernetes relacionados al deployment."""
        if not self._deployment_info:
            return
        
        # Obtener labels del deployment para buscar servicios
        labels = self._deployment_info.get("spec", {}).get("selector", {}).get("matchLabels", {})
        
        if not labels:
            return
        
        # Obtener todos los servicios del namespace
        success, services = self.run_kubectl([
            "get", "services", "-n", self.namespace
        ])
        
        if not success or not services.get("items"):
            return
        
        # Filtrar servicios que apuntan a este deployment
        for svc in services.get("items", []):
            svc_selector = svc.get("spec", {}).get("selector", {})
            if svc_selector:
                # Verificar si los selectores coinciden
                matches = all(labels.get(k) == v for k, v in svc_selector.items() if k in labels)
                if matches:
                    self._services.append(svc)

    # =========================================================================
    # 8. VALIDACIÓN DE LOAD BALANCERS
    # =========================================================================
    def check_load_balancers(self):
        """Verifica los Load Balancers asociados al deployment."""
        if not self._services:
            # Intentar obtener servicios si no se han descubierto
            success, services = self.run_kubectl([
                "get", "services", "-n", self.namespace
            ])
            if success:
                self._services = services.get("items", [])
        
        if not self._services:
            self.add_result(CheckResult(
                name="Services Discovery",
                status=CheckStatus.INFO,
                message=f"No se encontraron servicios en namespace '{self.namespace}'"
            ))
            return
        
        lb_services = []
        nodeport_services = []
        clusterip_services = []
        
        for svc in self._services:
            svc_name = svc.get("metadata", {}).get("name", "unknown")
            svc_type = svc.get("spec", {}).get("type", "ClusterIP")
            
            if svc_type == "LoadBalancer":
                lb_services.append(svc)
            elif svc_type == "NodePort":
                nodeport_services.append(svc)
            else:
                clusterip_services.append(svc)
        
        # Validar Load Balancers
        for svc in lb_services:
            self._check_load_balancer_service(svc)
        
        # Reportar otros servicios
        if nodeport_services:
            names = [s.get("metadata", {}).get("name") for s in nodeport_services]
            self.add_result(CheckResult(
                name="NodePort Services",
                status=CheckStatus.INFO,
                message=f"{len(nodeport_services)} servicio(s) NodePort: {', '.join(names)}"
            ))
        
        if clusterip_services:
            names = [s.get("metadata", {}).get("name") for s in clusterip_services]
            self.add_result(CheckResult(
                name="ClusterIP Services",
                status=CheckStatus.INFO,
                message=f"{len(clusterip_services)} servicio(s) ClusterIP: {', '.join(names)}"
            ))
        
        if not lb_services:
            self.add_result(CheckResult(
                name="Load Balancer Services",
                status=CheckStatus.INFO,
                message="No hay servicios de tipo LoadBalancer",
                details="Para conexión a Cloud SQL, generalmente no se necesita un LB externo"
            ))

    def _check_load_balancer_service(self, svc: Dict):
        """Verifica el estado de un servicio LoadBalancer específico."""
        svc_name = svc.get("metadata", {}).get("name", "unknown")
        svc_namespace = svc.get("metadata", {}).get("namespace", "default")
        
        # Verificar si tiene IP externa asignada
        ingress = svc.get("status", {}).get("loadBalancer", {}).get("ingress", [])
        
        if ingress:
            external_ip = ingress[0].get("ip") or ingress[0].get("hostname", "pending")
            
            self.add_result(CheckResult(
                name=f"LoadBalancer: {svc_name}",
                status=CheckStatus.PASS,
                message=f"IP externa asignada: {external_ip}",
                details=f"Namespace: {svc_namespace}"
            ))
            
            # Verificar el backend en GCP
            self._check_gcp_load_balancer(svc_name, external_ip)
        else:
            self.add_result(CheckResult(
                name=f"LoadBalancer: {svc_name}",
                status=CheckStatus.WARN,
                message="LoadBalancer sin IP externa asignada (pendiente)",
                details="El LB puede estar aprovisionándose o tener un problema",
                remediation=f"kubectl describe svc {svc_name} -n {svc_namespace}"
            ))

    def _check_gcp_load_balancer(self, svc_name: str, external_ip: str):
        """Verifica el Load Balancer en GCP."""
        # Buscar forwarding rules con esta IP
        success, rules = self.run_gcloud([
            "compute", "forwarding-rules", "list",
            "--filter", f"IPAddress={external_ip}"
        ])
        
        if success and rules:
            for rule in rules:
                rule_name = rule.get("name", "unknown")
                target = rule.get("target", "").split("/")[-1] if rule.get("target") else "N/A"
                
                self.add_result(CheckResult(
                    name=f"GCP Forwarding Rule: {rule_name}",
                    status=CheckStatus.PASS,
                    message=f"Forwarding rule activa para {external_ip}",
                    details=f"Target: {target}"
                ))
                
                # Verificar backend service si existe
                backend_service = rule.get("backendService")
                if backend_service:
                    self._check_backend_service_health(backend_service.split("/")[-1])
        else:
            self.add_result(CheckResult(
                name=f"GCP Forwarding Rule for {svc_name}",
                status=CheckStatus.INFO,
                message="No se encontró forwarding rule en GCP",
                details="Puede ser un LB interno o regional"
            ))

    def _check_backend_service_health(self, backend_service_name: str):
        """Verifica la salud del backend service."""
        success, health = self.run_gcloud([
            "compute", "backend-services", "get-health", backend_service_name,
            "--global"
        ])
        
        if not success:
            # Intentar con regional
            success, health = self.run_gcloud([
                "compute", "backend-services", "get-health", backend_service_name,
                "--region", self.region or "us-central1"
            ])
        
        if success and health:
            healthy_count = 0
            unhealthy_count = 0
            
            for backend in health:
                for status in backend.get("status", {}).get("healthStatus", []):
                    if status.get("healthState") == "HEALTHY":
                        healthy_count += 1
                    else:
                        unhealthy_count += 1
            
            if unhealthy_count == 0 and healthy_count > 0:
                self.add_result(CheckResult(
                    name=f"Backend Health: {backend_service_name}",
                    status=CheckStatus.PASS,
                    message=f"Todos los backends saludables ({healthy_count} instancias)"
                ))
            elif healthy_count > 0:
                self.add_result(CheckResult(
                    name=f"Backend Health: {backend_service_name}",
                    status=CheckStatus.WARN,
                    message=f"{healthy_count} saludables, {unhealthy_count} no saludables"
                ))
            else:
                self.add_result(CheckResult(
                    name=f"Backend Health: {backend_service_name}",
                    status=CheckStatus.FAIL,
                    message=f"No hay backends saludables ({unhealthy_count} no saludables)",
                    remediation=f"gcloud compute backend-services get-health {backend_service_name} --global"
                ))

    def check_network_endpoint_groups(self):
        """Verifica los NEGs asociados al servicio."""
        if not self._services:
            return
        
        for svc in self._services:
            svc_name = svc.get("metadata", {}).get("name", "unknown")
            annotations = svc.get("metadata", {}).get("annotations", {})
            
            # Verificar si usa NEG
            neg_status = annotations.get("cloud.google.com/neg-status")
            if neg_status:
                try:
                    neg_data = json.loads(neg_status)
                    zones = neg_data.get("network_endpoint_groups", {})
                    
                    self.add_result(CheckResult(
                        name=f"NEG Status: {svc_name}",
                        status=CheckStatus.INFO,
                        message=f"NEG configurado en {len(zones)} zona(s)",
                        details=str(zones)
                    ))
                    
                    # Verificar estado de cada NEG
                    for zone, neg_name in zones.items():
                        self._check_neg_health(neg_name, zone)
                        
                except json.JSONDecodeError:
                    pass

    def _check_neg_health(self, neg_name: str, zone: str):
        """Verifica la salud de un Network Endpoint Group."""
        success, neg_info = self.run_gcloud([
            "compute", "network-endpoint-groups", "describe", neg_name,
            "--zone", zone
        ])
        
        if success and neg_info:
            size = neg_info.get("size", 0)
            self.add_result(CheckResult(
                name=f"NEG: {neg_name}",
                status=CheckStatus.PASS if size > 0 else CheckStatus.WARN,
                message=f"NEG con {size} endpoint(s) en {zone}"
            ))

    # =========================================================================
    # 1. VALIDACIÓN DE CLOUD SQL INSTANCE
    # =========================================================================
    def check_sql_instance_exists(self) -> bool:
        """Verifica que la instancia de Cloud SQL existe y está activa."""
        success, data = self.run_gcloud([
            "sql", "instances", "describe", self.sql_instance
        ])
        
        if not success:
            self.add_result(CheckResult(
                name="Cloud SQL Instance Exists",
                status=CheckStatus.FAIL,
                message=f"No se encontró la instancia '{self.sql_instance}'",
                details=str(data),
                remediation=f"gcloud sql instances create {self.sql_instance} --region={self.region}"
            ))
            return False
        
        self._sql_info = data
        state = data.get("state", "UNKNOWN")
        
        if state != "RUNNABLE":
            self.add_result(CheckResult(
                name="Cloud SQL Instance State",
                status=CheckStatus.FAIL,
                message=f"Instancia en estado '{state}', se esperaba 'RUNNABLE'",
                remediation="Verificar el estado de la instancia en Cloud Console"
            ))
            return False
        
        self.add_result(CheckResult(
            name="Cloud SQL Instance Exists",
            status=CheckStatus.PASS,
            message=f"Instancia '{self.sql_instance}' está activa (RUNNABLE)",
            details=f"Database Version: {data.get('databaseVersion', 'N/A')}"
        ))
        return True

    def check_sql_ip_configuration(self) -> Dict[str, Any]:
        """Verifica la configuración de IP de Cloud SQL."""
        if not self._sql_info:
            return {}
        
        ip_config = self._sql_info.get("settings", {}).get("ipConfiguration", {})
        ip_addresses = self._sql_info.get("ipAddresses", [])
        
        has_private_ip = ip_config.get("privateNetwork") is not None
        has_public_ip = ip_config.get("ipv4Enabled", False)
        
        private_ip = None
        public_ip = None
        
        for ip in ip_addresses:
            if ip.get("type") == "PRIVATE":
                private_ip = ip.get("ipAddress")
            elif ip.get("type") == "PRIMARY":
                public_ip = ip.get("ipAddress")
        
        details = []
        details.append(f"IP Privada habilitada: {'Sí' if has_private_ip else 'No'}")
        details.append(f"IP Pública habilitada: {'Sí' if has_public_ip else 'No'}")
        if private_ip:
            details.append(f"IP Privada: {private_ip}")
        if public_ip:
            details.append(f"IP Pública: {public_ip}")
        
        if has_private_ip:
            self.add_result(CheckResult(
                name="Cloud SQL IP Configuration",
                status=CheckStatus.PASS,
                message="IP Privada está habilitada (recomendado para conexión desde GKE)",
                details="\n".join(details)
            ))
        elif has_public_ip:
            self.add_result(CheckResult(
                name="Cloud SQL IP Configuration",
                status=CheckStatus.WARN,
                message="Solo IP Pública habilitada. Se recomienda usar IP Privada para GKE",
                details="\n".join(details),
                remediation="gcloud sql instances patch {instance} --network=VPC_NAME --no-assign-ip"
            ))
        else:
            self.add_result(CheckResult(
                name="Cloud SQL IP Configuration",
                status=CheckStatus.FAIL,
                message="No hay IP configurada",
                remediation="Habilitar IP privada o pública en la instancia"
            ))
        
        return {
            "has_private_ip": has_private_ip,
            "has_public_ip": has_public_ip,
            "private_ip": private_ip,
            "public_ip": public_ip,
            "private_network": ip_config.get("privateNetwork")
        }

    def check_sql_authorized_networks(self):
        """Verifica las redes autorizadas para conexión pública."""
        if not self._sql_info:
            return
        
        ip_config = self._sql_info.get("settings", {}).get("ipConfiguration", {})
        authorized_networks = ip_config.get("authorizedNetworks", [])
        
        if not ip_config.get("ipv4Enabled", False):
            self.add_result(CheckResult(
                name="Authorized Networks",
                status=CheckStatus.SKIP,
                message="IP pública no está habilitada, no aplica"
            ))
            return
        
        if not authorized_networks:
            self.add_result(CheckResult(
                name="Authorized Networks",
                status=CheckStatus.WARN,
                message="No hay redes autorizadas configuradas para IP pública",
                remediation="gcloud sql instances patch {instance} --authorized-networks=CIDR"
            ))
        else:
            networks = [f"{n.get('name', 'N/A')}: {n.get('value', 'N/A')}" for n in authorized_networks]
            self.add_result(CheckResult(
                name="Authorized Networks",
                status=CheckStatus.INFO,
                message=f"{len(authorized_networks)} red(es) autorizada(s)",
                details="\n".join(networks)
            ))

    # =========================================================================
    # 2. VALIDACIÓN DE GKE CLUSTER
    # =========================================================================
    def check_gke_cluster(self) -> bool:
        """Verifica el cluster GKE y su configuración de red."""
        success, data = self.run_gcloud([
            "container", "clusters", "describe", self.gke_cluster,
            "--location", self.gke_location
        ])
        
        if not success:
            self.add_result(CheckResult(
                name="GKE Cluster Exists",
                status=CheckStatus.FAIL,
                message=f"No se encontró el cluster '{self.gke_cluster}'",
                details=str(data)
            ))
            return False
        
        self._cluster_info = data
        status = data.get("status", "UNKNOWN")
        
        if status != "RUNNING":
            self.add_result(CheckResult(
                name="GKE Cluster Status",
                status=CheckStatus.FAIL,
                message=f"Cluster en estado '{status}', se esperaba 'RUNNING'"
            ))
            return False
        
        self.add_result(CheckResult(
            name="GKE Cluster Exists",
            status=CheckStatus.PASS,
            message=f"Cluster '{self.gke_cluster}' está activo",
            details=f"Location: {self.gke_location}"
        ))
        return True

    def check_gke_network_config(self) -> Optional[str]:
        """Verifica la configuración de red del cluster GKE."""
        if not self._cluster_info:
            return None
        
        network = self._cluster_info.get("network", "default")
        subnetwork = self._cluster_info.get("subnetwork", "default")
        
        # Verificar si usa VPC nativa
        ip_allocation = self._cluster_info.get("ipAllocationPolicy", {})
        vpc_native = ip_allocation.get("useIpAliases", False)
        
        # Verificar Private Google Access
        private_cluster = self._cluster_info.get("privateClusterConfig", {})
        enable_private_nodes = private_cluster.get("enablePrivateNodes", False)
        
        details = [
            f"Network: {network}",
            f"Subnetwork: {subnetwork}",
            f"VPC-native (alias IP): {'Sí' if vpc_native else 'No'}",
            f"Private Nodes: {'Sí' if enable_private_nodes else 'No'}"
        ]
        
        if vpc_native:
            self.add_result(CheckResult(
                name="GKE Network Configuration",
                status=CheckStatus.PASS,
                message="Cluster configurado con VPC-native (requerido para IP privada de Cloud SQL)",
                details="\n".join(details)
            ))
        else:
            self.add_result(CheckResult(
                name="GKE Network Configuration",
                status=CheckStatus.WARN,
                message="Cluster no usa VPC-native. Puede tener problemas con IP privada de Cloud SQL",
                details="\n".join(details)
            ))
        
        return network

    def check_workload_identity(self):
        """Verifica si Workload Identity está habilitado en el cluster."""
        if not self._cluster_info:
            return
        
        workload_identity = self._cluster_info.get("workloadIdentityConfig", {})
        wi_pool = workload_identity.get("workloadPool")
        
        if wi_pool:
            self.add_result(CheckResult(
                name="Workload Identity",
                status=CheckStatus.PASS,
                message="Workload Identity está habilitado",
                details=f"Workload Pool: {wi_pool}"
            ))
        else:
            self.add_result(CheckResult(
                name="Workload Identity",
                status=CheckStatus.WARN,
                message="Workload Identity NO está habilitado",
                details="Se recomienda usar Workload Identity para autenticación segura a Cloud SQL",
                remediation=f"gcloud container clusters update {self.gke_cluster} --workload-pool={self.project_id}.svc.id.goog"
            ))

    # =========================================================================
    # 3. VALIDACIÓN DE VPC Y PRIVATE SERVICE CONNECTION
    # =========================================================================
    def check_vpc_network(self, network_name: str):
        """Verifica la VPC y sus configuraciones."""
        # Extraer nombre de red si viene como URL
        if "/" in network_name:
            network_name = network_name.split("/")[-1]
        
        success, data = self.run_gcloud([
            "compute", "networks", "describe", network_name
        ])
        
        if not success:
            self.add_result(CheckResult(
                name="VPC Network",
                status=CheckStatus.FAIL,
                message=f"No se encontró la VPC '{network_name}'",
                details=str(data)
            ))
            return
        
        self._vpc_info = data
        
        self.add_result(CheckResult(
            name="VPC Network",
            status=CheckStatus.PASS,
            message=f"VPC '{network_name}' encontrada",
            details=f"Mode: {data.get('autoCreateSubnetworks', 'custom')}"
        ))

    def check_private_service_connection(self, network_name: str):
        """Verifica la conexión de servicios privados para Cloud SQL."""
        if "/" in network_name:
            network_name = network_name.split("/")[-1]
        
        # Verificar allocated ranges
        success, ranges = self.run_gcloud([
            "compute", "addresses", "list",
            "--filter", f"purpose=VPC_PEERING AND network~{network_name}"
        ])
        
        if success and ranges:
            range_info = [f"{r.get('name')}: {r.get('address')}/{r.get('prefixLength')}" for r in ranges]
            self.add_result(CheckResult(
                name="Private Service Connection - IP Ranges",
                status=CheckStatus.PASS,
                message=f"{len(ranges)} rango(s) de IP asignado(s) para servicios privados",
                details="\n".join(range_info)
            ))
        else:
            self.add_result(CheckResult(
                name="Private Service Connection - IP Ranges",
                status=CheckStatus.WARN,
                message="No se encontraron rangos de IP para Private Service Connection",
                remediation=(
                    f"gcloud compute addresses create google-managed-services-{network_name} "
                    f"--global --purpose=VPC_PEERING --prefix-length=16 --network={network_name}"
                )
            ))
        
        # Verificar peering connection
        success, connections = self.run_gcloud([
            "services", "vpc-peerings", "list",
            "--network", network_name
        ])
        
        if success and connections:
            self.add_result(CheckResult(
                name="Private Service Connection - VPC Peering",
                status=CheckStatus.PASS,
                message="Conexión de servicios privados establecida",
                details=f"Peerings: {len(connections)}"
            ))
        else:
            self.add_result(CheckResult(
                name="Private Service Connection - VPC Peering",
                status=CheckStatus.WARN,
                message="No se encontró VPC peering para servicios privados",
                remediation=(
                    f"gcloud services vpc-peerings connect "
                    f"--service=servicenetworking.googleapis.com "
                    f"--ranges=google-managed-services-{network_name} --network={network_name}"
                )
            ))

    # =========================================================================
    # 4. VALIDACIÓN DE FIREWALL RULES
    # =========================================================================
    def check_firewall_rules(self, network_name: str, sql_port: int = 3306):
        """Verifica las reglas de firewall para conectividad."""
        if "/" in network_name:
            network_name = network_name.split("/")[-1]
        
        # Verificar reglas de egress
        success, rules = self.run_gcloud([
            "compute", "firewall-rules", "list",
            "--filter", f"network~{network_name}"
        ])
        
        if not success:
            self.add_result(CheckResult(
                name="Firewall Rules",
                status=CheckStatus.WARN,
                message="No se pudieron obtener las reglas de firewall",
                details=str(rules)
            ))
            return
        
        egress_rules = [r for r in rules if r.get("direction") == "EGRESS"]
        ingress_rules = [r for r in rules if r.get("direction") == "INGRESS"]
        
        # Buscar reglas que permitan el puerto de SQL
        sql_egress_allowed = False
        for rule in egress_rules:
            if rule.get("disabled"):
                continue
            allowed = rule.get("allowed", [])
            for allow in allowed:
                ports = allow.get("ports", [])
                if not ports or str(sql_port) in ports or "all" in str(ports).lower():
                    sql_egress_allowed = True
                    break
        
        # Por defecto GCP permite todo egress
        if not egress_rules:
            sql_egress_allowed = True
        
        details = [
            f"Total reglas en la VPC: {len(rules)}",
            f"Reglas Egress: {len(egress_rules)}",
            f"Reglas Ingress: {len(ingress_rules)}",
            f"Puerto verificado: {sql_port}"
        ]
        
        if sql_egress_allowed:
            self.add_result(CheckResult(
                name="Firewall Egress Rules",
                status=CheckStatus.PASS,
                message=f"Egress al puerto {sql_port} está permitido",
                details="\n".join(details)
            ))
        else:
            self.add_result(CheckResult(
                name="Firewall Egress Rules",
                status=CheckStatus.FAIL,
                message=f"No se encontró regla de egress permitiendo puerto {sql_port}",
                details="\n".join(details),
                remediation=(
                    f"gcloud compute firewall-rules create allow-sql-egress "
                    f"--network={network_name} --direction=EGRESS "
                    f"--action=ALLOW --rules=tcp:{sql_port} --priority=1000"
                )
            ))

    # =========================================================================
    # 5. VALIDACIÓN DE IAM PERMISSIONS
    # =========================================================================
    def check_iam_permissions(self):
        """Verifica los permisos IAM del Service Account."""
        if not self.gsa_email:
            self.add_result(CheckResult(
                name="IAM Permissions",
                status=CheckStatus.SKIP,
                message="No se especificó un Google Service Account (GSA)",
                details="Use --gsa-email para verificar permisos IAM"
            ))
            return
        
        # Verificar que el SA existe
        success, sa_info = self.run_gcloud([
            "iam", "service-accounts", "describe", self.gsa_email
        ])
        
        if not success:
            self.add_result(CheckResult(
                name="Service Account Exists",
                status=CheckStatus.FAIL,
                message=f"No se encontró el Service Account '{self.gsa_email}'",
                remediation=f"gcloud iam service-accounts create {self.gsa_email.split('@')[0]}"
            ))
            return
        
        self.add_result(CheckResult(
            name="Service Account Exists",
            status=CheckStatus.PASS,
            message=f"Service Account '{self.gsa_email}' existe"
        ))
        
        # Verificar roles del SA
        success, policy = self.run_gcloud([
            "projects", "get-iam-policy", self.project_id,
            "--flatten", "bindings[].members",
            "--filter", f"bindings.members:serviceAccount:{self.gsa_email}"
        ])
        
        required_roles = [
            "roles/cloudsql.client",
            "roles/cloudsql.instanceUser"
        ]
        
        if success and policy:
            assigned_roles = [b.get("bindings", {}).get("role", "") for b in policy]
            
            missing_roles = []
            for role in required_roles:
                if role not in assigned_roles:
                    missing_roles.append(role)
            
            if not missing_roles:
                self.add_result(CheckResult(
                    name="Cloud SQL IAM Roles",
                    status=CheckStatus.PASS,
                    message="Service Account tiene los roles necesarios para Cloud SQL",
                    details="\n".join(assigned_roles)
                ))
            else:
                self.add_result(CheckResult(
                    name="Cloud SQL IAM Roles",
                    status=CheckStatus.FAIL,
                    message=f"Faltan roles: {', '.join(missing_roles)}",
                    remediation=f"gcloud projects add-iam-policy-binding {self.project_id} --member=serviceAccount:{self.gsa_email} --role=roles/cloudsql.client"
                ))
        else:
            self.add_result(CheckResult(
                name="Cloud SQL IAM Roles",
                status=CheckStatus.WARN,
                message="No se pudieron verificar los roles IAM",
                details="Verificar manualmente que el SA tenga roles/cloudsql.client"
            ))

    # =========================================================================
    # 6. VALIDACIÓN DE WORKLOAD IDENTITY BINDING
    # =========================================================================
    def check_workload_identity_binding(self):
        """Verifica el binding entre KSA y GSA para Workload Identity."""
        if not self.ksa_name or not self.gsa_email:
            self.add_result(CheckResult(
                name="Workload Identity Binding",
                status=CheckStatus.SKIP,
                message="No se especificó KSA o GSA",
                details="Use --ksa-name y --gsa-email para verificar el binding"
            ))
            return
        
        # Verificar la anotación en el KSA
        success, ksa_info = self.run_kubectl([
            "get", "serviceaccount", self.ksa_name,
            "-n", self.namespace
        ])
        
        if not success:
            self.add_result(CheckResult(
                name="Kubernetes Service Account",
                status=CheckStatus.FAIL,
                message=f"No se encontró el KSA '{self.ksa_name}' en namespace '{self.namespace}'",
                remediation=f"kubectl create serviceaccount {self.ksa_name} -n {self.namespace}"
            ))
            return
        
        annotations = ksa_info.get("metadata", {}).get("annotations", {})
        wi_annotation = annotations.get("iam.gke.io/gcp-service-account")
        
        if wi_annotation == self.gsa_email:
            self.add_result(CheckResult(
                name="KSA Workload Identity Annotation",
                status=CheckStatus.PASS,
                message=f"KSA '{self.ksa_name}' está anotado correctamente",
                details=f"GSA: {self.gsa_email}"
            ))
        elif wi_annotation:
            self.add_result(CheckResult(
                name="KSA Workload Identity Annotation",
                status=CheckStatus.WARN,
                message=f"KSA está anotado con un GSA diferente: {wi_annotation}"
            ))
        else:
            self.add_result(CheckResult(
                name="KSA Workload Identity Annotation",
                status=CheckStatus.FAIL,
                message="KSA no tiene la anotación de Workload Identity",
                remediation=(
                    f"kubectl annotate serviceaccount {self.ksa_name} "
                    f"--namespace {self.namespace} "
                    f"iam.gke.io/gcp-service-account={self.gsa_email}"
                )
            ))
        
        # Verificar IAM binding del GSA para Workload Identity
        success, policy = self.run_gcloud([
            "iam", "service-accounts", "get-iam-policy", self.gsa_email
        ])
        
        if success and policy:
            bindings = policy.get("bindings", [])
            expected_member = f"serviceAccount:{self.project_id}.svc.id.goog[{self.namespace}/{self.ksa_name}]"
            
            wi_binding_found = False
            for binding in bindings:
                if binding.get("role") == "roles/iam.workloadIdentityUser":
                    if expected_member in binding.get("members", []):
                        wi_binding_found = True
                        break
            
            if wi_binding_found:
                self.add_result(CheckResult(
                    name="GSA Workload Identity Binding",
                    status=CheckStatus.PASS,
                    message="GSA tiene el binding de Workload Identity configurado"
                ))
            else:
                self.add_result(CheckResult(
                    name="GSA Workload Identity Binding",
                    status=CheckStatus.FAIL,
                    message="GSA no tiene el binding de Workload Identity",
                    remediation=(
                        f"gcloud iam service-accounts add-iam-policy-binding {self.gsa_email} "
                        f"--role roles/iam.workloadIdentityUser "
                        f"--member 'serviceAccount:{self.project_id}.svc.id.goog[{self.namespace}/{self.ksa_name}]'"
                    )
                ))

    # =========================================================================
    # 7. VALIDACIÓN DE CLOUD SQL AUTH PROXY (opcional)
    # =========================================================================
    def check_sql_auth_proxy_deployment(self):
        """Verifica si hay un Cloud SQL Auth Proxy desplegado."""
        # Buscar pods con cloud-sql-proxy
        success, pods = self.run_kubectl([
            "get", "pods", "-n", self.namespace,
            "-l", "app=cloud-sql-proxy"
        ])
        
        if success and pods.get("items"):
            self.add_result(CheckResult(
                name="Cloud SQL Auth Proxy Deployment",
                status=CheckStatus.INFO,
                message=f"Se encontraron {len(pods['items'])} pod(s) de Cloud SQL Proxy"
            ))
        else:
            # Buscar como sidecar
            success, pods = self.run_kubectl([
                "get", "pods", "-n", self.namespace,
                "--field-selector", "status.phase=Running"
            ])
            
            proxy_found = False
            if success and pods.get("items"):
                for pod in pods["items"]:
                    containers = pod.get("spec", {}).get("containers", [])
                    for container in containers:
                        image = container.get("image", "")
                        if "cloud-sql-proxy" in image or "cloudsql-proxy" in image:
                            proxy_found = True
                            break
            
            if proxy_found:
                self.add_result(CheckResult(
                    name="Cloud SQL Auth Proxy Sidecar",
                    status=CheckStatus.INFO,
                    message="Se encontró Cloud SQL Proxy como sidecar en algún pod"
                ))
            else:
                self.add_result(CheckResult(
                    name="Cloud SQL Auth Proxy",
                    status=CheckStatus.INFO,
                    message="No se encontró Cloud SQL Auth Proxy",
                    details="Si usas IP privada directa, el proxy no es necesario"
                ))

    # =========================================================================
    # 8. TEST DE CONECTIVIDAD
    # =========================================================================
    def check_connectivity_test(self, sql_ip: str, sql_port: int = 3306):
        """Verifica la conectividad de red al Cloud SQL."""
        if not sql_ip:
            self.add_result(CheckResult(
                name="Network Connectivity Test",
                status=CheckStatus.SKIP,
                message="No se pudo determinar la IP de Cloud SQL"
            ))
            return
        
        # Crear test de conectividad usando gcloud
        test_name = f"test-sql-{self.sql_instance[:20]}"
        
        success, result = self.run_gcloud([
            "network-management", "connectivity-tests", "create", test_name,
            "--destination-ip-address", sql_ip,
            "--destination-port", str(sql_port),
            "--protocol", "TCP",
            "--source-network", f"projects/{self.project_id}/global/networks/default"
        ], format_json=False)
        
        if success:
            self.add_result(CheckResult(
                name="Network Connectivity Test Created",
                status=CheckStatus.INFO,
                message=f"Test de conectividad '{test_name}' creado",
                details="Ejecutar: gcloud network-management connectivity-tests describe " + test_name
            ))
        else:
            self.add_result(CheckResult(
                name="Network Connectivity Test",
                status=CheckStatus.INFO,
                message="No se pudo crear test automático de conectividad",
                details=f"Verificar manualmente: nc -zv {sql_ip} {sql_port}"
            ))

    # =========================================================================
    # EJECUCIÓN PRINCIPAL
    # =========================================================================
    def run_all_checks(self):
        """Ejecuta todas las validaciones."""
        print("\n" + "="*135)
        print(f"{'🔍 CLOUD SQL CONNECTIVITY CHECKER':^135}")
        print("="*135)
        
        # Imprimir encabezado de la tabla
        self.table.print_header()
        
        # 0. Discovery - descubrir información automáticamente
        self.set_section("0. Discovery")
        if not self.discover_from_current_context():
            self.print_summary()
            return
        
        if not self.discover_from_deployment():
            self.print_summary()
            return
        
        # Mostrar información descubierta
        self.table.print_separator()
        print(f"{'📋 CONFIGURACIÓN DETECTADA':^135}")
        config_info = f"Project: {self.project_id} | SQL: {self.sql_instance} | Cluster: {self.gke_cluster or 'N/A'} | NS: {self.namespace}"
        if self.deployment:
            config_info += f" | Deploy: {self.deployment}"
        print(f"{config_info:^135}")
        
        # 1. Cloud SQL Instance
        self.set_section("1. Cloud SQL")
        if not self.check_sql_instance_exists():
            self.print_summary()
            return
        
        ip_config = self.check_sql_ip_configuration()
        self.check_sql_authorized_networks()
        
        # Determinar puerto según tipo de DB
        db_version = self._sql_info.get("databaseVersion", "")
        sql_port = 5432 if "POSTGRES" in db_version.upper() else 3306
        
        # 2. GKE Cluster (si se detectó)
        self.set_section("2. GKE Cluster")
        network = None
        if self.gke_cluster and self.gke_location:
            if not self.check_gke_cluster():
                self.print_summary()
                return
            
            network = self.check_gke_network_config()
            self.check_workload_identity()
        else:
            self.add_result(CheckResult(
                name="GKE Cluster",
                status=CheckStatus.SKIP,
                message="No se detectó cluster GKE del contexto actual",
                details="Use --gke-cluster y --gke-location para especificar manualmente"
            ))
        
        # 3. VPC & Private Service Connection
        self.set_section("3. VPC & PSC")
        if network:
            self.check_vpc_network(network)
            if ip_config.get("has_private_ip"):
                self.check_private_service_connection(network)
        
        # 4. Firewall Rules
        self.set_section("4. Firewall")
        if network:
            self.check_firewall_rules(network, sql_port)
        
        # 5. IAM Permissions
        self.set_section("5. IAM")
        self.check_iam_permissions()
        
        # 6. Workload Identity Binding
        self.set_section("6. Workload Identity")
        self.check_workload_identity_binding()
        
        # 7. Cloud SQL Auth Proxy
        self.set_section("7. SQL Proxy")
        self.check_sql_auth_proxy_deployment()
        
        # 8. Load Balancers & Services
        self.set_section("8. Load Balancers")
        self.check_load_balancers()
        self.check_network_endpoint_groups()
        
        # 9. Connectivity Test
        self.set_section("9. Connectivity")
        sql_ip = ip_config.get("private_ip") or ip_config.get("public_ip")
        if sql_ip:
            self.check_connectivity_test(sql_ip, sql_port)
        
        self.print_summary()

    def print_summary(self):
        """Imprime el resumen final usando la tabla."""
        self.table.print_summary()


def print_execution_time(start_time, tz_name="America/Mazatlan"):
    """Imprime el tiempo de ejecución del script"""
    end_time = time.time()
    duration = end_time - start_time

    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = duration % 60

    if hours > 0:
        duration_str = f"{hours}h {minutes}m {seconds:.2f}s"
    elif minutes > 0:
        duration_str = f"{minutes}m {seconds:.2f}s"
    else:
        duration_str = f"{seconds:.2f}s"

    tz = ZoneInfo(tz_name)
    start_ts = datetime.fromtimestamp(start_time, tz=tz).strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})')
    end_ts = datetime.fromtimestamp(end_time, tz=tz).strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})')

    print("\n" + "="*60)
    print("⏱️  Tiempo de Ejecución")
    print("="*60)
    print(f"🚀 Inicio:   {start_ts}")
    print(f"🏁 Fin:      {end_ts}")
    print(f"⏳ Duración: {duration_str}")
    print("="*60)


def main():
    """Punto de entrada principal."""
    start_time = time.time()
    parser = argparse.ArgumentParser(
        description="Valida la conectividad desde un Pod de GKE hasta Cloud SQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Modo simplificado (solo deployment y database)
  # Descubre automáticamente: project, cluster, namespace, service accounts
  python connectivity-checker.py \\
    --deployment my-app \\
    --sql-instance my-database

  # Modo simplificado con proyecto específico
  python connectivity-checker.py \\
    --deployment my-app \\
    --sql-instance my-database \\
    --project my-project

  # Modo completo (especificando todos los parámetros)
  python connectivity-checker.py \\
    --sql-instance my-database \\
    --project my-project \\
    --region us-central1 \\
    --gke-cluster my-cluster \\
    --gke-location us-central1 \\
    --namespace app-ns \\
    --ksa-name app-sa \\
    --gsa-email app@my-project.iam.gserviceaccount.com \\
    --verbose

Notas:
  - Si no se especifica --project, se usa el proyecto configurado en gcloud
  - Si no se especifica --gke-cluster, se detecta del contexto actual de kubectl
  - Si se especifica --deployment, se descubre automáticamente: namespace, KSA, GSA
  - Los Load Balancers y servicios relacionados se validan automáticamente
        """
    )
    
    # Parámetros principales (simplificados)
    parser.add_argument(
        "--sql-instance", "-s",
        required=True,
        help="Nombre de la instancia de Cloud SQL (REQUERIDO)"
    )
    parser.add_argument(
        "--deployment", "-d",
        help="Nombre del deployment de Kubernetes (descubre namespace, SA automáticamente)"
    )
    
    # Parámetros opcionales (se descubren automáticamente si no se especifican)
    parser.add_argument(
        "--project", "-p",
        help="ID del proyecto de GCP (default: proyecto actual de gcloud)"
    )
    parser.add_argument(
        "--region", "-r",
        help="Región de Cloud SQL (se detecta de la instancia si no se especifica)"
    )
    parser.add_argument(
        "--gke-cluster", "-c",
        help="Nombre del cluster GKE (default: detectado del contexto kubectl)"
    )
    parser.add_argument(
        "--gke-location", "-l",
        help="Ubicación del cluster GKE (default: detectado del contexto kubectl)"
    )
    parser.add_argument(
        "--namespace", "-n",
        default="default",
        help="Namespace de Kubernetes (default: 'default' o detectado del deployment)"
    )
    parser.add_argument(
        "--ksa-name",
        help="Nombre del Kubernetes Service Account (detectado del deployment si existe)"
    )
    parser.add_argument(
        "--gsa-email",
        help="Email del Google Service Account (detectado del KSA si tiene anotación)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar detalles adicionales y comandos ejecutados"
    )
    parser.add_argument(
        "--timezone", "-tz",
        type=str,
        default="America/Mazatlan",
        help="Zona horaria para mostrar fechas (default: America/Mazatlan - Culiacán)"
    )
    
    args = parser.parse_args()
    
    tz_name = args.timezone
    try:
        ZoneInfo(tz_name)
    except Exception:
        print(f"⚠️ Zona horaria inválida: {tz_name}. Usando America/Mazatlan")
        tz_name = "America/Mazatlan"

    print(f"\n{'='*60}")
    print("🔍 Verificando conexión a GCP...")
    print(f"{'='*60}")
    
    if not check_gcp_connection(args.project, args.verbose):
        print_execution_time(start_time, tz_name)
        return

    checker = ConnectivityChecker(
        sql_instance=args.sql_instance,
        deployment=args.deployment,
        project_id=args.project,
        region=args.region,
        gke_cluster=args.gke_cluster,
        gke_location=args.gke_location,
        namespace=args.namespace,
        ksa_name=args.ksa_name,
        gsa_email=args.gsa_email,
        verbose=args.verbose
    )
    
    checker.run_all_checks()
    print_execution_time(start_time, tz_name)


if __name__ == "__main__":
    main()
