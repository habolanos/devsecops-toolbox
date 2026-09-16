#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
GCP Cloud Run VPC IP Diagnostic

Herramienta SRE para diagnosticar saturación de IPs en Cloud Run VPC Connectors
y proponer rangos CIDR óptimos por ambiente (Dev/QA/Stg/Prod).

Analiza:
- Servicios Cloud Run y sus VPC connectors
- Capacidad actual vs uso de IPs en connectors
- Subnets de Shared VPC host project
- Proyección de crecimiento por ambiente

Autor: Harold Adrian
"""

import argparse
import subprocess
import json
import sys
import os
import threading
import time
import ipaddress
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from cloudrun_base import CloudRunBase
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cloudrun_base import CloudRunBase

__version__ = "1.0.0"

# Configuración de ambientes estándar
ENVIRONMENT_CONFIG = {
    "dev": {
        "min_instances_per_service": 1,
        "max_instances_per_service": 10,
        "concurrency_per_instance": 80,
        "growth_factor": 1.5,
        "recommended_cidr": "/24",
        "reserved_ips": 4
    },
    "qa": {
        "min_instances_per_service": 2,
        "max_instances_per_service": 20,
        "concurrency_per_instance": 80,
        "growth_factor": 2.0,
        "recommended_cidr": "/24",
        "reserved_ips": 4
    },
    "stg": {
        "min_instances_per_service": 3,
        "max_instances_per_service": 30,
        "concurrency_per_instance": 100,
        "growth_factor": 2.5,
        "recommended_cidr": "/23",
        "reserved_ips": 4
    },
    "prod": {
        "min_instances_per_service": 5,
        "max_instances_per_service": 100,
        "concurrency_per_instance": 100,
        "growth_factor": 3.0,
        "recommended_cidr": "/22",
        "reserved_ips": 4
    }
}

CIDR_TO_IPS = {
    "/28": 16,
    "/27": 32,
    "/26": 64,
    "/25": 128,
    "/24": 256,
    "/23": 512,
    "/22": 1024,
    "/21": 2048,
    "/20": 4096,
}


def format_ip_usage(current_ips: int, total_ips: int) -> str:
    """Formatea el uso de IPs como cantidad actual sobre total."""
    return f"{max(0, current_ips)}/{max(0, total_ips)}"


class AnimatedSpinner:
    """Spinner compatible con terminales Linux y WSL usando una sola línea."""

    def __init__(self, message: str = "Procesando"):
        self.message = message
        self._stop_event = threading.Event()
        self._thread = None
        self._frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    def _animate(self):
        frame = 0
        while not self._stop_event.is_set():
            text = f"\r{self._frames[frame % len(self._frames)]} {self.message}"
            sys.stdout.write(text)
            sys.stdout.flush()
            frame += 1
            time.sleep(0.1)

    def start(self):
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
        return self

    def stop(self, final_message: str = ""):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        # Limpia la línea anterior y deja un resultado final estable.
        sys.stdout.write("\r\033[2K")
        if final_message:
            sys.stdout.write(final_message)
        sys.stdout.write("\n")
        sys.stdout.flush()


@dataclass
class CloudRunService:
    """Representa un servicio Cloud Run"""
    name: str
    region: str
    url: str
    vpc_connector: str
    vpc_egress: str
    vpc_network: str
    vpc_subnetwork: str
    min_instances: int
    max_instances: int
    cpu: str
    memory: str
    is_public: bool
    ingress: str
    service_account: str


@dataclass
class VPCConnectorInfo:
    """Información de un VPC Connector"""
    name: str
    region: str
    network: str
    ip_cidr_range: str
    min_instances: int
    max_instances: int
    connected_services: List[str]
    total_ips: int
    used_ips_estimate: int
    available_ips: int
    utilization_pct: float
    status: str  # OK, WARNING, CRITICAL


@dataclass
class EnvironmentDiagnostic:
    """Diagnóstico completo por ambiente"""
    environment: str
    project_id: str
    host_project_id: str
    services: List[CloudRunService]
    connectors: List[VPCConnectorInfo]
    subnet_info: Dict
    recommendations: List[Dict]
    risk_level: str
    ip_current_estimate: int = 0
    ip_total: int = 0
    ip_cidr: str = "N/A"
    ip_scope: str = "N/A"


def get_args():
    """Parsea argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description="SRE Tool: Cloud Run VPC IP Diagnostic & CIDR Planner",
        add_help=False
    )
    parser.add_argument(
        "--projects",
        type=str,
        required=True,
        help="Proyectos GCP separados por coma: dev-proj,qa-proj,stg-prod,prod-proj"
    )
    parser.add_argument(
        "--host-project",
        type=str,
        help="Proyecto host de Shared VPC (único para todos)"
    )
    parser.add_argument(
        "--host-projects",
        type=str,
        help="Proyectos host por ambiente: dev-host,qa-host,stg-host,prod-host"
    )
    parser.add_argument(
        "--auto-detect-host",
        action="store_true",
        help="Auto-detectar Host Project(s) vía Shared VPC API"
    )
    parser.add_argument(
        "--region",
        type=str,
        default="us-central1",
        help="Región a analizar (default: us-central1)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "csv", "html"],
        help="Formato de exportación"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Modo debug"
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Muestra ayuda"
    )
    parser.add_argument(
        "--timezone", "-tz",
        type=str,
        default="America/Mazatlan",
        help="Timezone (default: America/Mazatlan)"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Ejecución paralela (default: True)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Max workers paralelos (default: 4)"
    )
    return parser.parse_args()


def show_help():
    """Muestra ayuda completa"""
    help_text = """
╔══════════════════════════════════════════════════════════════════════════════╗
║         GCP CLOUD RUN VPC IP DIAGNOSTIC & CIDR PLANNER v1.0.0               ║
║         Diagnóstico de saturación IPs y planificación de rangos CIDR        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  DESCRIPCIÓN:                                                                ║
║    Analiza servicios Cloud Run en múltiples ambientes (Dev/QA/Stg/Prod)     ║
║    detecta saturación de IPs en VPC Connectors y propone rangos CIDR        ║
║    óptimos por ambiente.                                                     ║
║                                                                              ║
║  USO:                                                                        ║
║    python gcp_cloudrun_vpc_ip_diagnostic.py --projects PROYECTOS [opciones] ║
║                                                                              ║
║  OPCIONES REQUERIDAS:                                                        ║
║    --projects        Proyectos GCP separados por coma                        ║
║                      Ej: cpl-corp-cial-dev,cpl-corp-cial-qa,                ║
║                          cpl-corp-cial-stg,cpl-corp-cial-prod               ║
║                                                                              ║
║  OPCIONES OPCIONALES:                                                        ║
║    --host-project    Proyecto host Shared VPC (único para todos)             ║
║    --host-projects   Proyectos host por ambiente (separados por coma)       ║
║    --region          Región a analizar (default: us-central1)               ║
║    --output, -o      Exportar: json, csv, html                               ║
║    --debug           Modo debug                                              ║
║    --timezone, -tz   Timezone (default: America/Mazatlan)                   ║
║    --parallel        Ejecución paralela (default: True)                     ║
║    --max-workers     Workers paralelos (default: 4)                         ║
║    --help, -h        Muestra esta ayuda                                      ║
║                                                                              ║
║  EJEMPLOS:                                                                   ║
║    # Básico - 4 ambientes, mismo host project                                ║
║    python gcp_cloudrun_vpc_ip_diagnostic.py \\                               ║
║      --projects dev-proj,qa-proj,stg-proj,prod-proj \\                       ║
║      --host-project cpl-corp-host-prod                                       ║
║                                                                              ║
║    # Host projects diferentes por ambiente                                   ║
║    python gcp_cloudrun_vpc_ip_diagnostic.py \\                               ║
║      --projects dev,qa,stg,prod \\                                           ║
║      --host-projects dev-host,qa-host,stg-host,prod-host                     ║
║                                                                              ║
║    # Exportar reporte HTML                                                   ║
║    python gcp_cloudrun_vpc_ip_diagnostic.py \\                               ║
║      --projects dev,qa,stg,prod \\                                           ║
║      --host-project host-proj -o html                                        ║
║                                                                              ║
║    # Auto-detectar Host Project (recomendado si no sabes cuál es)           ║
║    python gcp_cloudrun_vpc_ip_diagnostic.py \\                               ║
║      --projects dev,qa,stg,prod --auto-detect-host                           ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(help_text)
    sys.exit(0)


def detect_shared_vpc_host_project(project_id: str, debug: bool = False) -> Optional[str]:
    """Detecta el host project de Shared VPC si el proyecto es un service project"""
    import subprocess
    cmd = f'gcloud compute shared-vpc get-host-project {project_id} --format="value(name)"'
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        if debug:
            print(f"[DEBUG] Shared VPC check: {cmd}")
            print(f"[DEBUG] Return code: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] Stderr: {result.stderr}")
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception as e:
        if debug:
            print(f"[DEBUG] Exception checking Shared VPC: {e}")
        return None


def auto_detect_host_projects(projects: List[str], debug: bool = False) -> List[str]:
    """Auto-detecta host projects para una lista de service projects"""
    host_projects = []
    for project in projects:
        host = detect_shared_vpc_host_project(project, debug)
        if host:
            host_projects.append(host)
            if debug:
                print(f"[DEBUG] {project} → Host Project: {host}")
        else:
            host_projects.append("")
            if debug:
                print(f"[DEBUG] {project} → No Shared VPC host project found")
    return host_projects


def extract_direct_vpc_network(annotations: Dict) -> tuple[str, str]:
    """Extrae red y subred de la configuración Direct VPC Egress."""
    raw_interfaces = annotations.get("run.googleapis.com/network-interfaces", "")
    if not raw_interfaces:
        return "", ""
    try:
        interfaces = json.loads(raw_interfaces) if isinstance(raw_interfaces, str) else raw_interfaces
        if isinstance(interfaces, list) and interfaces:
            interface = interfaces[0] or {}
            return (
                str(interface.get("network", "")).split("/")[-1],
                str(interface.get("subnetwork", "")).split("/")[-1],
            )
    except (TypeError, json.JSONDecodeError):
        pass
    return "", ""


class CloudRunVPCDiagnostic(CloudRunBase):
    """Diagnosticador de VPC IP para Cloud Run"""
    
    def __init__(self, project: str, host_project: str, region: str = "us-central1", 
                 debug: bool = False, tz: str = "America/Mazatlan", environment: str = "unknown"):
        super().__init__(project, region, debug, tz)
        self.host_project = host_project
        self.environment = environment
        self.env_config = ENVIRONMENT_CONFIG.get(environment, ENVIRONMENT_CONFIG["dev"])
    
    def validate_connection_silent(self) -> bool:
        """Valida conexión a GCP sin spinner (para uso en paralelo)"""
        result = self.run_gcloud_command("gcloud run services list")
        return result is not None
    
    def get_cloudrun_services(self) -> List[CloudRunService]:
        """Obtiene todos los servicios Cloud Run del proyecto"""
        if self.region == "all":
            cmd = "gcloud run services list"
        else:
            cmd = f"gcloud run services list --region={self.region}"
        
        services_data = self.run_gcloud_command(cmd) or []
        services = []
        
        for svc in services_data:
            metadata = svc.get("metadata", {})
            status = svc.get("status", {})
            spec = svc.get("spec", {}).get("template", {}).get("spec", {})
            template_meta = svc.get("spec", {}).get("template", {}).get("metadata", {})
            annotations = metadata.get("annotations", {})
            template_annotations = template_meta.get("annotations", {})
            
            # VPC Connector
            vpc_connector = (template_annotations.get("run.googleapis.com/vpc-access-connector") or 
                           annotations.get("run.googleapis.com/vpc-access-connector", ""))
            
            # VPC Egress
            vpc_egress = (template_annotations.get("run.googleapis.com/vpc-access-egress") or
                         annotations.get("run.googleapis.com/vpc-access-egress", ""))
            
            # Direct VPC Egress network interfaces
            network_annotations = {**annotations, **template_annotations}
            vpc_network, vpc_subnetwork = extract_direct_vpc_network(network_annotations)

            # Min/Max instances
            min_inst = int(template_annotations.get("autoscaling.knative.dev/minScale", "0"))
            max_inst = int(template_annotations.get("autoscaling.knative.dev/maxScale", "100"))
            
            # Resources
            container = spec.get("containers", [{}])[0] if spec.get("containers") else {}
            resources = container.get("resources", {}).get("limits", {})
            cpu = resources.get("cpu", "1")
            memory = resources.get("memory", "512Mi")
            
            # Security
            iam_policy = self.get_service_iam_policy(metadata.get("name", ""), self.region)
            is_public = False
            if iam_policy:
                for binding in iam_policy.get("bindings", []):
                    if "allUsers" in binding.get("members", []) or "allAuthenticatedUsers" in binding.get("members", []):
                        is_public = True
                        break
            
            ingress = annotations.get("run.googleapis.com/ingress", "all")
            service_account = spec.get("serviceAccountName", "default")
            
            services.append(CloudRunService(
                name=metadata.get("name", "unknown"),
                region=metadata.get("labels", {}).get("cloud.googleapis.com/location", self.region),
                url=status.get("url", "N/A"),
                vpc_connector=vpc_connector,
                vpc_egress=vpc_egress,
                vpc_network=vpc_network,
                vpc_subnetwork=vpc_subnetwork,
                min_instances=min_inst,
                max_instances=max_inst,
                cpu=cpu,
                memory=memory,
                is_public=is_public,
                ingress=ingress,
                service_account=service_account
            ))
        
        return services
    
    def get_service_iam_policy(self, service_name: str, region: str) -> Dict:
        """Obtiene política IAM de un servicio"""
        cmd = f"gcloud run services get-iam-policy {service_name} --region={region}"
        result = self.run_gcloud_command(cmd)
        return result if isinstance(result, dict) else {}
    
    def get_vpc_connectors(self) -> List[Dict]:
        """Obtiene VPC Connectors del host project"""
        cmd = f"gcloud compute networks vpc-access connectors list --project={self.host_project} --region={self.region} --format=json"
        return self.run_gcloud_command(cmd) or []
    
    def get_subnet_info(self) -> Dict:
        """Obtiene información de subnets en el host project"""
        cmd = f"gcloud compute networks subnets list --project={self.host_project} --region={self.region} --format=json"
        subnets = self.run_gcloud_command(cmd) or []
        
        subnet_info = {}
        for subnet in subnets:
            name = subnet.get("name", "unknown")
            subnet_info[name] = {
                "network": subnet.get("network", "").split("/")[-1],
                "region": subnet.get("region", "").split("/")[-1],
                "ip_cidr_range": subnet.get("ipCidrRange", ""),
                "purpose": subnet.get("purpose", "PRIVATE"),
                "secondary_ranges": subnet.get("secondaryIpRanges", [])
            }
        
        return subnet_info
    
    def analyze_connector(self, connector: Dict, services: List[CloudRunService]) -> VPCConnectorInfo:
        """Analiza un VPC Connector y su uso estimado"""
        name = connector.get("name", "unknown")
        network = connector.get("network", "").split("/")[-1]
        ip_cidr = connector.get("ipCidrRange", "")
        min_inst = connector.get("minInstances", 2)
        max_inst = connector.get("maxInstances", 10)
        
        # Calcular IPs totales
        total_ips = CIDR_TO_IPS.get(f"/{ip_cidr.split('/')[-1]}", 0) if '/' in ip_cidr else 0
        usable_ips = max(0, total_ips - 4)  # Restar 4 IPs reservadas por GCP
        
        # Servicios conectados a este connector
        connected = [s.name for s in services if s.vpc_connector and name in s.vpc_connector]
        
        # Estimar IPs usadas
        used_estimate = 0
        for svc in services:
            if svc.vpc_connector and name in svc.vpc_connector:
                # Estimar: min_instances + (max_instances * factor de concurrencia)
                # Cada instancia = 1 IP del connector
                used_estimate += svc.min_instances
                # Agregar buffer por escalado
                used_estimate += int((svc.max_instances - svc.min_instances) * 0.3)
        
        # Agregar buffer de crecimiento
        used_estimate = int(used_estimate * self.env_config["growth_factor"])
        
        available = usable_ips - used_estimate
        utilization = (used_estimate / usable_ips * 100) if usable_ips > 0 else 100
        
        # Determinar status
        if utilization >= 90:
            status = "CRITICAL"
        elif utilization >= 70:
            status = "WARNING"
        else:
            status = "OK"
        
        return VPCConnectorInfo(
            name=name,
            region=self.region,
            network=network,
            ip_cidr_range=ip_cidr,
            min_instances=min_inst,
            max_instances=max_inst,
            connected_services=connected,
            total_ips=usable_ips,
            used_ips_estimate=used_estimate,
            available_ips=max(0, available),
            utilization_pct=round(utilization, 1),
            status=status
        )
    
    def calculate_recommended_cidr(self, services: List[CloudRunService], 
                                    current_connectors: List[VPCConnectorInfo]) -> List[Dict]:
        """Calcula rangos CIDR recomendados por ambiente"""
        recommendations = []
        
        # Contar servicios que necesitan VPC
        services_needing_vpc = [s for s in services if s.vpc_connector or s.vpc_egress]
        services_without_vpc = [s for s in services if not s.vpc_connector and not s.vpc_egress]
        
        # Estimar IPs necesarias totales
        total_min_instances = sum(s.min_instances for s in services_needing_vpc)
        total_max_instances = sum(s.max_instances for s in services_needing_vpc)
        
        # Proyectar con factor de crecimiento
        projected_ips = int(total_max_instances * self.env_config["growth_factor"])
        projected_ips += self.env_config["reserved_ips"]
        
        # Encontrar CIDR mínimo que cubra la necesidad
        recommended_cidr = None
        for cidr, ips in sorted(CIDR_TO_IPS.items(), key=lambda x: x[1]):
            usable = ips - 4
            if usable >= projected_ips:
                recommended_cidr = cidr
                break
        
        if not recommended_cidr:
            recommended_cidr = "/20"  # Máximo disponible
        
        # Recomendación principal
        recommendations.append({
            "type": "vpc_connector_cidr",
            "priority": "HIGH",
            "title": f"Rango CIDR recomendado para VPC Connector ({self.environment.upper()})",
            "current": current_connectors[0].ip_cidr_range if current_connectors else "N/A",
            "recommended": recommended_cidr,
            "justification": f"Proyección: {projected_ips} IPs necesarias (max_instances={total_max_instances} × growth_factor={self.env_config['growth_factor']}). CIDR {recommended_cidr} = {CIDR_TO_IPS[recommended_cidr] - 4} IPs usables.",
            "action": f"Crear nuevo connector con --range=10.x.0.0{recommended_cidr} y migrar servicios"
        })
        
        # Servicios sin VPC
        if services_without_vpc:
            recommendations.append({
                "type": "services_without_vpc",
                "priority": "MEDIUM",
                "title": f"Servicios sin VPC Connector ({len(services_without_vpc)})",
                "current": "Direct egress / sin VPC",
                "recommended": "Asignar VPC Connector",
                "justification": f"Servicios: {', '.join([s.name for s in services_without_vpc[:5]])}{'...' if len(services_without_vpc) > 5 else ''}. Sin VPC no pueden acceder a recursos privados (Cloud SQL, Memorystore, APIs internas).",
                "action": "Actualizar cada servicio: gcloud run services update SERVICE --vpc-connector=CONNECTOR --region=REGION"
            })
        
        # Connectors en WARNING/CRITICAL
        for conn in current_connectors:
            if conn.status in ["WARNING", "CRITICAL"]:
                recommendations.append({
                    "type": "connector_saturation",
                    "priority": "CRITICAL" if conn.status == "CRITICAL" else "HIGH",
                    "title": f"Connector saturado: {conn.name}",
                    "current": f"{conn.ip_cidr_range} ({conn.utilization_pct}% usado)",
                    "recommended": f"Migrar a CIDR {recommended_cidr} o crear connector adicional",
                    "justification": f"IPs usables: {conn.total_ips}, Estimadas usadas: {conn.used_ips_estimate}, Disponibles: {conn.available_ips}. Servicios afectados: {', '.join(conn.connected_services[:3])}{'...' if len(conn.connected_services) > 3 else ''}",
                    "action": f"Crear connector nuevo con rango mayor y migrar servicios progresivamente"
                })
        
        # Verificar subnet capacity en host project
        subnet_rec = self._check_subnet_capacity()
        if subnet_rec:
            recommendations.append(subnet_rec)
        
        return recommendations
    
    def _check_subnet_capacity(self) -> Optional[Dict]:
        """Verifica capacidad de subnets en host project"""
        # Esta verificación requiere acceso al host project
        # Por ahora retornamos recomendación genérica
        return {
            "type": "subnet_capacity",
            "priority": "MEDIUM",
            "title": "Verificar capacidad de Subnet en Host Project",
            "current": "Revisar gcloud compute networks subnets list --project=HOST_PROJECT",
            "recommended": "Asegurar subnet con rango /20 o superior para Cloud Run",
            "justification": "Cloud Run VPC Connectors consumen IPs de la subnet primaria. Subnets /24 o menores pueden agotarse.",
            "action": "Crear subnet dedicada para Cloud Run con --range=10.x.0.0/20 o usar secondary IP ranges"
        }
    
    def calculate_environment_ip_capacity(
        self, services: List[CloudRunService], subnet_info: Dict
    ) -> Dict[str, Any]:
        """Calcula capacidad IP para Connectors o Direct VPC Egress."""
        grouped_services: Dict[str, List[CloudRunService]] = {}
        for service in services:
            subnet = service.vpc_subnetwork
            if subnet:
                grouped_services.setdefault(subnet, []).append(service)

        if not grouped_services:
            return {
                "current": 0,
                "total": 0,
                "cidr": "N/A",
                "scope": "No se detectó subred Direct VPC Egress",
            }

        current_total = 0
        total_ips = 0
        cidrs = []
        for subnet_name, subnet_services in grouped_services.items():
            subnet = subnet_info.get(subnet_name, {})
            cidr = subnet.get("ip_cidr_range", "")
            try:
                usable_ips = max(0, ipaddress.ip_network(cidr, strict=False).num_addresses - 4)
            except ValueError:
                usable_ips = 0
            current = sum(
                service.min_instances
                + int((service.max_instances - service.min_instances) * 0.3)
                for service in subnet_services
            )
            current = int(current * self.env_config["growth_factor"])
            current_total += current
            total_ips += usable_ips
            if cidr:
                cidrs.append(f"{subnet_name}: {cidr}")

        return {
            "current": current_total,
            "total": total_ips,
            "cidr": ", ".join(cidrs) if cidrs else "N/A",
            "scope": "Direct VPC Egress",
        }

    def diagnose_environment(self, silent: bool = False) -> EnvironmentDiagnostic:
        """Ejecuta diagnóstico completo del ambiente"""
        if not silent:
            self.print_info(f"Diagnosticando ambiente: {self.environment.upper()} (proyecto: {self.project})")
        
        # 1. Obtener servicios Cloud Run
        services = self.get_cloudrun_services()
        if not silent:
            self.print_info(f"  Servicios encontrados: {len(services)}")
        
        # 2. Obtener VPC Connectors
        connectors_data = self.get_vpc_connectors()
        connectors = [self.analyze_connector(c, services) for c in connectors_data]
        if not silent:
            self.print_info(f"  VPC Connectors encontrados: {len(connectors)}")
        
        # 3. Obtener info de subnets y capacidad Direct VPC Egress
        subnet_info = self.get_subnet_info()
        ip_capacity = self.calculate_environment_ip_capacity(services, subnet_info)
        
        # 4. Calcular recomendaciones
        recommendations = self.calculate_recommended_cidr(services, connectors)
        
        # 5. Determinar riesgo general
        critical_count = sum(1 for c in connectors if c.status == "CRITICAL")
        warning_count = sum(1 for c in connectors if c.status == "WARNING")
        
        if critical_count > 0:
            risk_level = "CRITICAL"
        elif warning_count > 0:
            risk_level = "WARNING"
        elif len(connectors) == 0 and len(services) > 0:
            risk_level = "WARNING"  # Servicios sin VPC
        else:
            risk_level = "OK"
        
        return EnvironmentDiagnostic(
            environment=self.environment,
            project_id=self.project,
            host_project_id=self.host_project,
            services=services,
            connectors=connectors,
            subnet_info=subnet_info,
            recommendations=recommendations,
            risk_level=risk_level,
            ip_current_estimate=ip_capacity["current"],
            ip_total=ip_capacity["total"],
            ip_cidr=ip_capacity["cidr"],
            ip_scope=ip_capacity["scope"]
        )
    
    def create_summary_table(self, diagnostics: List[EnvironmentDiagnostic]) -> Table:
        """Crea tabla resumen multi-ambiente"""
        table = Table(
            title="📊 Cloud Run VPC IP Diagnostic - Resumen Multi-Ambiente",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Ambiente", style="bold white")
        table.add_column("Proyecto", style="yellow")
        table.add_column("Host Project", style="blue")
        table.add_column("Servicios", justify="center")
        table.add_column("Con VPC", justify="center")
        table.add_column("Connectors", justify="center")
        table.add_column("IPs Actuales / Total", justify="center")
        table.add_column("CIDR", style="cyan")
        table.add_column("Riesgo", justify="center")
        table.add_column("Recomendaciones", justify="center")
        
        for diag in diagnostics:
            env = diag.environment.upper()
            services_total = len(diag.services)
            services_with_vpc = sum(1 for s in diag.services if s.vpc_connector)
            connectors_count = len(diag.connectors)
            rec_count = len(diag.recommendations)
            
            risk_style = {
                "CRITICAL": "[red]CRITICAL[/red]",
                "WARNING": "[yellow]WARNING[/yellow]",
                "OK": "[green]OK[/green]"
            }.get(diag.risk_level, diag.risk_level)
            
            table.add_row(
                env,
                diag.project_id,
                diag.host_project_id,
                str(services_total),
                str(services_with_vpc),
                str(connectors_count),
                format_ip_usage(diag.ip_current_estimate, diag.ip_total)
                if diag.ip_total else "N/A",
                diag.ip_cidr,
                risk_style,
                str(rec_count)
            )
        
        return table
    
    def create_connector_table(self, connectors: List[VPCConnectorInfo], env: str) -> Table:
        """Crea tabla de conectores"""
        table = Table(
            title=f"🔗 VPC Connectors - {env.upper()}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Connector", style="bold white")
        table.add_column("Red", style="yellow")
        table.add_column("CIDR", style="cyan")
        table.add_column("IPs Actuales / Total", justify="right", style="yellow")
        table.add_column("Disponibles", justify="right", style="green")
        table.add_column("Uso %", justify="right")
        table.add_column("Estado", justify="center")
        table.add_column("Servicios", style="dim", max_width=30)
        
        for conn in connectors:
            status_style = {
                "OK": "[green]OK[/green]",
                "WARNING": "[yellow]WARNING[/yellow]",
                "CRITICAL": "[red]CRITICAL[/red]"
            }.get(conn.status, conn.status)
            
            services_str = ", ".join(conn.connected_services[:3])
            if len(conn.connected_services) > 3:
                services_str += f" +{len(conn.connected_services)-3} más"
            
            table.add_row(
                conn.name,
                conn.network,
                conn.ip_cidr_range,
                format_ip_usage(conn.used_ips_estimate, conn.total_ips),
                str(conn.available_ips),
                f"{conn.utilization_pct}%",
                status_style,
                services_str
            )
        
        return table
    
    def create_recommendations_table(self, recommendations: List[Dict], env: str) -> Table:
        """Crea tabla de recomendaciones"""
        table = Table(
            title=f"💡 Recomendaciones - {env.upper()}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Prioridad", justify="center")
        table.add_column("Tipo", style="cyan")
        table.add_column("Título", style="bold white", max_width=35)
        table.add_column("Actual", style="yellow", max_width=25)
        table.add_column("Recomendado", style="green", max_width=25)
        table.add_column("Acción", style="dim", max_width=40)
        
        for rec in recommendations:
            priority_style = {
                "CRITICAL": "[red]🔴 CRITICAL[/red]",
                "HIGH": "[orange3]🟠 HIGH[/orange3]",
                "MEDIUM": "[yellow]🟡 MEDIUM[/yellow]",
                "LOW": "[green]🟢 LOW[/green]"
            }.get(rec["priority"], rec["priority"])
            
            table.add_row(
                priority_style,
                rec["type"],
                rec["title"][:35],
                str(rec["current"])[:25],
                str(rec["recommended"])[:25],
                rec["action"][:40]
            )
        
        return table
    
    def export_diagnostics(self, diagnostics: List[EnvironmentDiagnostic], format: str) -> str:
        """Exporta diagnósticos completos"""
        export_data = {
            "metadata": {
                "tool": "CloudRunVPCDiagnostic",
                "version": __version__,
                "timestamp": datetime.now(ZoneInfo(self.tz)).isoformat(),
                "region": self.region,
                "environments_analyzed": len(diagnostics)
            },
            "summary": {
                "total_services": sum(len(d.services) for d in diagnostics),
                "total_connectors": sum(len(d.connectors) for d in diagnostics),
                "critical_environments": sum(1 for d in diagnostics if d.risk_level == "CRITICAL"),
                "warning_environments": sum(1 for d in diagnostics if d.risk_level == "WARNING"),
                "ok_environments": sum(1 for d in diagnostics if d.risk_level == "OK")
            },
            "diagnostics": [asdict(d) for d in diagnostics]
        }
        
        return self.export_results(export_data, format, "cloudrun_vpc_ip_diagnostic")


def run_diagnostics(projects: List[str], host_projects: List[str], region: str, 
                    debug: bool, tz: str, parallel: bool, max_workers: int) -> List[EnvironmentDiagnostic]:
    """Ejecuta diagnósticos en paralelo para todos los ambientes"""
    # Entornos por defecto, pero se ajustan al número de proyectos
    default_environments = ["dev", "qa", "stg", "prod"]
    num_projects = len(projects)
    
    if num_projects < 1 or num_projects > 4:
        print(f"❌ Se esperan entre 1 y 4 proyectos. Recibidos: {num_projects}")
        sys.exit(1)
    
    if len(host_projects) not in [1, num_projects]:
        print(f"❌ host-projects debe ser 1 (compartido) o {num_projects} (uno por ambiente). Recibidos: {len(host_projects)}")
        sys.exit(1)
    
    # Usar solo los primeros N entornos según el número de proyectos
    environments = default_environments[:num_projects]
    
    # Expandir host_projects si es uno solo
    if len(host_projects) == 1:
        host_projects = host_projects * num_projects
    
    diagnostics = []  # Inicializar ANTES del if/else
    
    def diagnose_env(idx: int, use_silent_validation: bool = False) -> EnvironmentDiagnostic:
        env = environments[idx]
        project = projects[idx]
        host_project = host_projects[idx]
        
        diagnostic_tool = CloudRunVPCDiagnostic(
            project=project,
            host_project=host_project,
            region=region,
            debug=debug,
            tz=tz,
            environment=env
        )
        
        # Usar validación silenciosa en paralelo para evitar spam en el progress bar
        if use_silent_validation:
            connected = diagnostic_tool.validate_connection_silent()
        else:
            connected = diagnostic_tool.validate_connection()
            
        if not connected:
            if RICH_AVAILABLE:
                console = Console()
                console.print(f"[red]❌ No se pudo conectar al proyecto: {project}[/red]")
            return None
        
        # Pasar silent=True para suprimir print_info en paralelo
        return diagnostic_tool.diagnose_environment(silent=use_silent_validation)
    
    if parallel:
        spinner = AnimatedSpinner(
            f"Diagnosticando {num_projects} ambiente(s) en paralelo..."
        ).start()
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Validación y diagnóstico silenciosos para evitar salida intercalada.
                futures = {executor.submit(diagnose_env, i, True): i for i in range(num_projects)}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        diagnostics.append(result)
        finally:
            spinner.stop(
                f"Diagnóstico completado: {len(diagnostics)}/{num_projects} ambiente(s)."
            )
    else:
        spinner = AnimatedSpinner(
            f"Diagnosticando {num_projects} ambiente(s) de forma secuencial..."
        ).start()
        try:
            for i in range(num_projects):
                result = diagnose_env(i, True)
                if result:
                    diagnostics.append(result)
        finally:
            spinner.stop(
                f"Diagnóstico completado: {len(diagnostics)}/{num_projects} ambiente(s)."
            )
    
    return diagnostics


def generate_html_report(diagnostics: List[EnvironmentDiagnostic], region: str, tz: str) -> str:
    """Genera reporte HTML interactivo"""
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloud Run VPC IP Diagnostic Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #1a73e8; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card h3 {{ margin: 0 0 10px 0; color: #5f6368; font-size: 14px; text-transform: uppercase; }}
        .card .value {{ font-size: 32px; font-weight: bold; color: #202124; }}
        .critical {{ color: #ea4335; }} .warning {{ color: #fbbc04; }} .ok {{ color: #34a853; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
        th {{ background: #1a73e8; color: white; font-weight: 600; }}
        tr:hover {{ background: #f8f9fa; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .badge-critical {{ background: #fce8e6; color: #ea4335; }}
        .badge-warning {{ background: #fef7e0; color: #fbbc04; }}
        .badge-ok {{ background: #e6f4ea; color: #34a853; }}
        .badge-high {{ background: #fce8e6; color: #ea4335; }}
        .badge-medium {{ background: #fef7e0; color: #fbbc04; }}
        .badge-low {{ background: #e6f4ea; color: #34a853; }}
        .section {{ margin-bottom: 40px; }}
        .recommendation {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #1a73e8; }}
        .recommendation.critical {{ border-left-color: #ea4335; }}
        .recommendation.high {{ border-left-color: #fbbc04; }}
        .recommendation.medium {{ border-left-color: #4285f4; }}
        .meta {{ color: #5f6368; font-size: 14px; margin-bottom: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Cloud Run VPC IP Diagnostic Report</h1>
        <p class="meta">Región: {region} | Generado: {datetime.now(ZoneInfo(tz)).strftime('%Y-%m-%d %H:%M:%S')} | Zona horaria: {tz}</p>
        
        <div class="summary">
            <div class="card">
                <h3>Total Servicios</h3>
                <div class="value">{sum(len(d.services) for d in diagnostics)}</div>
            </div>
            <div class="card">
                <h3>Total Connectors</h3>
                <div class="value">{sum(len(d.connectors) for d in diagnostics)}</div>
            </div>
            <div class="card">
                <h3>Ambientes Críticos</h3>
                <div class="value critical">{sum(1 for d in diagnostics if d.risk_level == 'CRITICAL')}</div>
            </div>
            <div class="card">
                <h3>Ambientes Warning</h3>
                <div class="value warning">{sum(1 for d in diagnostics if d.risk_level == 'WARNING')}</div>
            </div>
            <div class="card">
                <h3>Ambientes OK</h3>
                <div class="value ok">{sum(1 for d in diagnostics if d.risk_level == 'OK')}</div>
            </div>
        </div>
"""
    
    # Resumen por ambiente
    html += """
        <div class="section">
            <h2>Resumen por Ambiente</h2>
            <table>
                <thead>
                    <tr>
                        <th>Ambiente</th>
                        <th>Proyecto</th>
                        <th>Host Project</th>
                        <th>Servicios</th>
                        <th>Con VPC</th>
                        <th>Connectors</th>
                        <th>IPs Actuales / Total</th>
                        <th>CIDR</th>
                        <th>Riesgo</th>
                        <th>Recomendaciones</th>
                    </tr>
                </thead>
                <tbody>
"""
    for d in diagnostics:
        env = d.environment.upper()
        services_total = len(d.services)
        services_with_vpc = sum(1 for s in d.services if s.vpc_connector)
        connectors_count = len(d.connectors)
        rec_count = len(d.recommendations)
        risk_class = d.risk_level.lower()
        
        html += f"""
                    <tr>
                        <td><strong>{env}</strong></td>
                        <td>{d.project_id}</td>
                        <td>{d.host_project_id}</td>
                        <td>{services_total}</td>
                        <td>{services_with_vpc}</td>
                        <td>{connectors_count}</td>
                        <td>{format_ip_usage(d.ip_current_estimate, d.ip_total) if d.ip_total else 'N/A'}</td>
                        <td>{d.ip_cidr}</td>
                        <td><span class="badge badge-{risk_class}">{d.risk_level}</span></td>
                        <td>{rec_count}</td>
                    </tr>
"""
    html += """
                </tbody>
            </table>
        </div>
"""
    
    # Detalle por ambiente
    for d in diagnostics:
        env = d.environment.upper()
        html += f"""
        <div class="section">
            <h2>🔍 Detalle: {env} ({d.project_id})</h2>
            
            <h3>VPC Connectors</h3>
            <table>
                <thead>
                    <tr>
                        <th>Connector</th>
                        <th>Red</th>
                        <th>CIDR</th>
                        <th>IPs Actuales / Total</th>
                        <th>Disponibles</th>
                        <th>Uso %</th>
                        <th>Estado</th>
                        <th>Servicios</th>
                    </tr>
                </thead>
                <tbody>
"""
        for conn in d.connectors:
            status_class = conn.status.lower()
            services_str = ", ".join(conn.connected_services[:3])
            if len(conn.connected_services) > 3:
                services_str += f" +{len(conn.connected_services)-3} más"
            
            html += f"""
                    <tr>
                        <td>{conn.name}</td>
                        <td>{conn.network}</td>
                        <td>{conn.ip_cidr_range}</td>
                        <td>{format_ip_usage(conn.used_ips_estimate, conn.total_ips)}</td>
                        <td>{conn.available_ips}</td>
                        <td>{conn.utilization_pct}%</td>
                        <td><span class="badge badge-{status_class}">{conn.status}</span></td>
                        <td>{services_str}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
            
            <h3>Servicios Cloud Run</h3>
            <table>
                <thead>
                    <tr>
                        <th>Servicio</th>
                        <th>Región</th>
                        <th>VPC Connector</th>
                        <th>Egress</th>
                        <th>Min/Max Inst</th>
                        <th>CPU/Mem</th>
                        <th>Ingress</th>
                        <th>Público</th>
                    </tr>
                </thead>
                <tbody>
"""
        for svc in d.services:
            vpc_display = svc.vpc_connector if svc.vpc_connector else "—"
            public_badge = "🌐 Sí" if svc.is_public else "🔒 No"
            
            html += f"""
                    <tr>
                        <td>{svc.name}</td>
                        <td>{svc.region}</td>
                        <td>{vpc_display[:40]}{'...' if len(vpc_display) > 40 else ''}</td>
                        <td>{svc.vpc_egress or '—'}</td>
                        <td>{svc.min_instances}/{svc.max_instances}</td>
                        <td>{svc.cpu}/{svc.memory}</td>
                        <td>{svc.ingress}</td>
                        <td>{public_badge}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
            
            <h3>Recomendaciones</h3>
"""
        for rec in d.recommendations:
            priority_class = rec["priority"].lower()
            html += f"""
            <div class="recommendation {priority_class}">
                <h4>{rec['title']} <span class="badge badge-{priority_class}">{rec['priority']}</span></h4>
                <p><strong>Actual:</strong> {rec['current']}</p>
                <p><strong>Recomendado:</strong> {rec['recommended']}</p>
                <p><strong>Justificación:</strong> {rec['justification']}</p>
                <p><strong>Acción:</strong> {rec['action']}</p>
            </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    return html


def main():
    args = get_args()
    
    if args.help:
        show_help()
    
    if not RICH_AVAILABLE:
        print("Error: La librería 'rich' no está instalada.")
        print("Instalar con: pip install rich")
        sys.exit(1)
    
    console = Console()
    
    # Parsear proyectos
    projects = [p.strip() for p in args.projects.split(",")]
    
    # Auto-detectar host projects si se solicita
    if args.auto_detect_host:
        console.print("[cyan]🔍 Auto-detectando Host Projects vía Shared VPC API...[/cyan]")
        host_projects = auto_detect_host_projects(projects, args.debug)
        
        # Verificar que todos se detectaron
        missing = [projects[i] for i, hp in enumerate(host_projects) if not hp]
        if missing:
            console.print(f"[yellow]⚠️ No se pudo auto-detectar host project para: {', '.join(missing)}[/yellow]")
            console.print("[yellow]   Se usará el primer host project detectado para los que falten[/yellow]")
            
            # Usar el primero detectado como fallback
            first_detected = next((hp for hp in host_projects if hp), None)
            if first_detected:
                host_projects = [hp if hp else first_detected for hp in host_projects]
            else:
                console.print("[red]❌ No se detectó ningún host project. Usa --host-project manualmente.[/red]")
                sys.exit(1)
        
        console.print(f"[green]✅ Host Projects detectados: {', '.join(host_projects)}[/green]")
    else:
        host_projects = [p.strip() for p in args.host_project.split(",")] if args.host_project else []
        if args.host_projects:
            host_projects = [p.strip() for p in args.host_projects.split(",")]
        
        if not host_projects:
            console.print("[red]❌ Se requiere --host-project, --host-projects, o --auto-detect-host[/red]")
            sys.exit(1)
    
    console.print(Panel.fit(
        f"[bold cyan]Cloud Run VPC IP Diagnostic v{__version__}[/bold cyan]\n"
        f"[yellow]Proyectos: {', '.join(projects)}[/yellow]\n"
        f"[yellow]Host Projects: {', '.join(host_projects)}[/yellow]\n"
        f"[yellow]Región: {args.region}[/yellow]",
        border_style="cyan"
    ))
    
    # Ejecutar diagnósticos
    diagnostics = run_diagnostics(
        projects=projects,
        host_projects=host_projects,
        region=args.region,
        debug=args.debug,
        tz=args.timezone,
        parallel=args.parallel,
        max_workers=args.max_workers
    )
    
    if not diagnostics:
        console.print("[red]❌ No se pudieron diagnosticar ambientes[/red]")
        sys.exit(1)
    
    # Crear instancia helper para métodos de tabla
    helper = CloudRunVPCDiagnostic(
        project=projects[0],
        host_project=host_projects[0],
        region=args.region,
        debug=args.debug,
        tz=args.timezone,
        environment=diagnostics[0].environment
    )
    
    # Mostrar resumen
    console.print()
    console.print(helper.create_summary_table(diagnostics))
    console.print()
    
    # Mostrar detalle por ambiente
    for diag in diagnostics:
        console.print(helper.create_connector_table(diag.connectors, diag.environment))
        console.print()
        console.print(helper.create_recommendations_table(diag.recommendations, diag.environment))
        console.print()
    
    # Exportar
    if args.output:
        if args.output == "html":
            html = generate_html_report(diagnostics, args.region, args.timezone)
            output_dir = console.__class__.__module__  # dummy
            from pathlib import Path
            import os
            try:
                from utils import get_output_dir
            except ImportError:
                def get_output_dir(default="."):
                    env = os.getenv("DEVSECOPS_OUTPUT_DIR")
                    if env:
                        p = Path(env)
                        p.mkdir(parents=True, exist_ok=True)
                        return p
                    p = Path(default)
                    p.mkdir(parents=True, exist_ok=True)
                    return p
            
            output_dir = Path(str(get_output_dir("outcome")))
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now(ZoneInfo(args.timezone)).strftime("%Y%m%d_%H%M%S")
            filename = output_dir / f"cloudrun_vpc_ip_diagnostic_{timestamp}.html"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)
            
            console.print(f"[green]✅ Reporte HTML exportado a: {filename}[/green]")
        else:
            filename = helper.export_diagnostics(diagnostics, args.output)
            console.print(f"[green]✅ Exportado a: {filename}[/green]")
    
    # Resumen final
    critical_envs = [d.environment.upper() for d in diagnostics if d.risk_level == "CRITICAL"]
    warning_envs = [d.environment.upper() for d in diagnostics if d.risk_level == "WARNING"]
    
    if critical_envs:
        console.print(Panel.fit(
            f"[red]🔴 ACCIÓN REQUERIDA INMEDIATA[/red]\n"
            f"Ambientes CRÍTICOS: {', '.join(critical_envs)}\n"
            f"Revisar recomendaciones y planificar migración de VPC Connectors",
            border_style="red"
        ))
    elif warning_envs:
        console.print(Panel.fit(
            f"[yellow]⚠️ ATENCIÓN REQUERIDA[/yellow]\n"
            f"Ambientes WARNING: {', '.join(warning_envs)}\n"
            f"Planificar ampliación de rangos CIDR",
            border_style="yellow"
        ))
    else:
        console.print(Panel.fit(
            f"[green]✅ TODOS LOS AMBIENTES OK[/green]\n"
            f"Capacidad de IPs suficiente en todos los VPC Connectors",
            border_style="green"
        ))


if __name__ == "__main__":
    main()