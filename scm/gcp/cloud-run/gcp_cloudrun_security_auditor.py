#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud Run Security Auditor

Herramienta SRE para auditoría completa de seguridad en Cloud Run.

Autor: Harold Adrian
"""

import argparse
import sys
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from cloudrun_base import CloudRunBase
from cloudrun_alerts import SecurityAlertManager, AlertSeverity, AlertType

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"


class CloudRunSecurityAuditor(CloudRunBase):
    """Auditor de seguridad de Cloud Run"""
    
    def __init__(self, project: str, region: str = "all", debug: bool = False, tz: str = "America/Mazatlan"):
        super().__init__(project, region, debug, tz)
        self.alert_manager = SecurityAlertManager()
        self.services = []
        self.audit_results = {}
    
    def get_services(self) -> List[Dict]:
        """Obtiene lista de servicios Cloud Run"""
        if self.region == "all":
            command = "gcloud run services list"
        else:
            command = f"gcloud run services list --region={self.region}"
        
        return self.run_gcloud_command(command) or []
    
    def get_service_iam_policy(self, service_name: str, region: str) -> Dict:
        """Obtiene política IAM de un servicio"""
        command = f"gcloud run services get-iam-policy {service_name} --region={region}"
        result = self.run_gcloud_command(command)
        return result if isinstance(result, dict) else {}
    
    def analyze_iam_policy(self, service: Dict, iam_policy: Dict) -> Dict:
        """Analiza política IAM"""
        metadata = service.get("metadata", {})
        service_name = metadata.get("name", "unknown")
        
        is_public = False
        public_members = []
        
        if iam_policy:
            bindings = iam_policy.get("bindings", [])
            for binding in bindings:
                members = binding.get("members", [])
                role = binding.get("role", "")
                
                if "allUsers" in members or "allAuthenticatedUsers" in members:
                    is_public = True
                    public_members.append({
                        "role": role,
                        "members": members
                    })
        
        return {
            "is_public": is_public,
            "public_members": public_members,
            "policy_count": len(iam_policy.get("bindings", []))
        }
    
    def analyze_ingress_settings(self, service: Dict) -> Dict:
        """Analiza configuración de ingress"""
        metadata = service.get("metadata", {})
        annotations = metadata.get("annotations", {})
        
        ingress = annotations.get("run.googleapis.com/ingress", "all")
        
        risk_level = "HIGH" if ingress == "all" else "LOW"
        
        return {
            "ingress_setting": ingress,
            "risk_level": risk_level,
            "description": {
                "all": "Permite tráfico desde cualquier lugar",
                "internal": "Solo tráfico interno a Google Cloud",
                "internal-and-cloud-load-balancing": "Tráfico interno y desde Cloud Load Balancing"
            }.get(ingress, "Desconocido")
        }
    
    def analyze_vpc_configuration(self, service: Dict) -> Dict:
        """Analiza configuración de VPC"""
        metadata = service.get("metadata", {})
        annotations = metadata.get("annotations", {})
        spec = service.get("spec", {}).get("template", {}).get("spec", {})
        
        vpc_connector = annotations.get("run.googleapis.com/vpc-access-connector", "")
        vpc_egress = annotations.get("run.googleapis.com/vpc-access-egress", "")
        
        return {
            "vpc_connector": vpc_connector if vpc_connector else "None",
            "vpc_egress": vpc_egress if vpc_egress else "None",
            "has_vpc_access": bool(vpc_connector),
            "recommendation": "Configurar VPC connector para acceso a recursos privados" if not vpc_connector else "VPC configurado"
        }
    
    def analyze_service_account(self, service: Dict) -> Dict:
        """Analiza configuración de service account"""
        spec = service.get("spec", {}).get("template", {}).get("spec", {})
        service_account = spec.get("serviceAccountName", "default")
        
        is_default = service_account == "default" or service_account.endswith("@appspot.gserviceaccount.com")
        
        return {
            "service_account": service_account,
            "is_default": is_default,
            "risk_level": "MEDIUM" if is_default else "LOW",
            "recommendation": "Usar service account personalizado con permisos mínimos" if is_default else "Service account personalizado configurado"
        }
    
    def analyze_binary_authorization(self, service: Dict) -> Dict:
        """Analiza configuración de binary authorization"""
        metadata = service.get("metadata", {})
        annotations = metadata.get("annotations", {})
        
        binary_auth = annotations.get("run.googleapis.com/binary-authorization", "")
        
        return {
            "binary_authorization": binary_auth if binary_auth else "Disabled",
            "enabled": bool(binary_auth),
            "recommendation": "Habilitar binary authorization para mayor seguridad" if not binary_auth else "Binary authorization habilitado"
        }
    
    def analyze_secrets(self, service: Dict) -> Dict:
        """Analiza uso de secrets"""
        spec = service.get("spec", {}).get("template", {}).get("spec", {})
        containers = spec.get("containers", [])
        
        secrets_count = 0
        env_vars_count = 0
        
        for container in containers:
            env = container.get("env", [])
            env_vars_count += len(env)
            
            for var in env:
                if "valueFrom" in var and "secretKeyRef" in var.get("valueFrom", {}):
                    secrets_count += 1
        
        return {
            "secrets_count": secrets_count,
            "env_vars_count": env_vars_count,
            "has_secrets": secrets_count > 0,
            "recommendation": "Usar Secret Manager para almacenar credenciales" if env_vars_count > 0 else "No se detectan variables de entorno"
        }
    
    def audit_service(self, service: Dict) -> Dict:
        """Audita un servicio completo"""
        metadata = service.get("metadata", {})
        service_name = metadata.get("name", "unknown")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "unknown")
        
        # Obtener política IAM
        iam_policy = self.get_service_iam_policy(service_name, region)
        
        # Realizar análisis
        iam_analysis = self.analyze_iam_policy(service, iam_policy)
        ingress_analysis = self.analyze_ingress_settings(service)
        vpc_analysis = self.analyze_vpc_configuration(service)
        sa_analysis = self.analyze_service_account(service)
        binary_auth_analysis = self.analyze_binary_authorization(service)
        secrets_analysis = self.analyze_secrets(service)
        
        # Crear alertas
        alerts = []
        
        if iam_analysis["is_public"]:
            alert = self.alert_manager.check_iam_policy(service_name, iam_policy, True)
            if alert:
                alerts.append(alert)
        
        if not vpc_analysis["has_vpc_access"]:
            alert = self.alert_manager.check_vpc_connector(service_name, "")
            if alert:
                alerts.append(alert)
        
        if not binary_auth_analysis["enabled"]:
            alert = self.alert_manager.check_binary_authorization(service_name, "")
            if alert:
                alerts.append(alert)
        
        # Calcular security score
        security_score = self._calculate_security_score(
            iam_analysis, ingress_analysis, vpc_analysis, sa_analysis, binary_auth_analysis
        )
        
        return {
            "service_name": service_name,
            "region": region,
            "security_score": security_score,
            "iam_analysis": iam_analysis,
            "ingress_analysis": ingress_analysis,
            "vpc_analysis": vpc_analysis,
            "service_account_analysis": sa_analysis,
            "binary_authorization_analysis": binary_auth_analysis,
            "secrets_analysis": secrets_analysis,
            "alerts": alerts
        }
    
    def _calculate_security_score(self, iam: Dict, ingress: Dict, vpc: Dict, sa: Dict, binary_auth: Dict) -> int:
        """Calcula score de seguridad (0-100)"""
        score = 100
        
        # IAM
        if iam["is_public"]:
            score -= 30
        
        # Ingress
        if ingress["risk_level"] == "HIGH":
            score -= 20
        
        # VPC
        if not vpc["has_vpc_access"]:
            score -= 15
        
        # Service Account
        if sa["is_default"]:
            score -= 15
        
        # Binary Authorization
        if not binary_auth["enabled"]:
            score -= 10
        
        return max(0, score)
    
    def audit_all_services(self) -> Dict:
        """Audita todos los servicios"""
        self.services = self.get_services()
        
        if not self.services:
            self.print_warning("No se encontraron servicios Cloud Run")
            return {}
        
        audit_results = {}
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Auditando servicios...", total=len(self.services))
                
                for service in self.services:
                    service_name = service.get("metadata", {}).get("name", "unknown")
                    audit = self.audit_service(service)
                    audit_results[service_name] = audit
                    progress.advance(task)
        else:
            for service in self.services:
                service_name = service.get("metadata", {}).get("name", "unknown")
                audit = self.audit_service(service)
                audit_results[service_name] = audit
        
        return audit_results
    
    def create_security_table(self, audit_results: Dict) -> Table:
        """Crea tabla de seguridad"""
        table = Table(
            title="🔐 Cloud Run Security Audit",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Servicio", style="bold white")
        table.add_column("Región", style="yellow")
        table.add_column("Security Score", justify="center")
        table.add_column("Público", justify="center")
        table.add_column("VPC", justify="center")
        table.add_column("Ingress", justify="center")
        table.add_column("Alertas", justify="center")
        
        for service_name, audit in audit_results.items():
            score = audit["security_score"]
            is_public = audit["iam_analysis"]["is_public"]
            has_vpc = audit["vpc_analysis"]["has_vpc_access"]
            ingress = audit["ingress_analysis"]["ingress_setting"]
            alerts_count = len(audit["alerts"])
            
            # Colorear score
            if score >= 80:
                score_display = f"[green]{score}[/green]"
            elif score >= 60:
                score_display = f"[yellow]{score}[/yellow]"
            else:
                score_display = f"[red]{score}[/red]"
            
            # Colorear público
            public_display = f"[red]SÍ[/red]" if is_public else f"[green]NO[/green]"
            
            # Colorear VPC
            vpc_display = f"[green]SÍ[/green]" if has_vpc else f"[yellow]NO[/yellow]"
            
            # Colorear alertas
            alerts_display = f"[red]{alerts_count}[/red]" if alerts_count > 0 else f"[green]0[/green]"
            
            table.add_row(
                service_name,
                audit["region"],
                score_display,
                public_display,
                vpc_display,
                ingress,
                alerts_display
            )
        
        return table
    
    def export_audit(self, audit_results: Dict, format: str = "json") -> str:
        """Exporta auditoría"""
        export_data = {
            "metadata": {
                "tool": "CloudRunSecurityAuditor",
                "version": __version__,
                "project": self.project,
                "region": self.region
            },
            "audit_results": audit_results,
            "summary": {
                "total_services": len(audit_results),
                "average_security_score": sum(a["security_score"] for a in audit_results.values()) / len(audit_results) if audit_results else 0,
                "public_services": sum(1 for a in audit_results.values() if a["iam_analysis"]["is_public"]),
                "total_alerts": sum(len(a["alerts"]) for a in audit_results.values())
            }
        }
        
        return self.export_results(export_data, format, "cloudrun_security_audit")


def get_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Cloud Run Security Auditor",
        add_help=False
    )
    parser.add_argument("--project", "-p", type=str, required=True, help="ID del proyecto GCP")
    parser.add_argument("--region", "-r", type=str, default="all", help="Región específica o 'all'")
    parser.add_argument("--service", "-s", type=str, help="Servicio específico a auditar")
    parser.add_argument("--severity", type=str, choices=["CRITICAL", "WARNING", "INFO"], help="Filtrar por severidad")
    parser.add_argument("--output", "-o", type=str, choices=["json", "csv", "excel"], help="Formato de exportación")
    parser.add_argument("--debug", action="store_true", help="Modo debug")
    parser.add_argument("--help", "-h", action="store_true", help="Muestra ayuda")
    parser.add_argument("--timezone", "-tz", type=str, default="America/Mazatlan", help="Timezone")
    
    return parser.parse_args()


def main():
    """Función principal"""
    args = get_args()
    
    if args.help:
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  GCP CLOUD RUN SECURITY AUDITOR v1.0.0                       ║
║                    Auditoría de Seguridad de Cloud Run                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  DESCRIPCIÓN:                                                                ║
║    Realiza auditoría completa de seguridad en servicios Cloud Run.          ║
║                                                                              ║
║  USO:                                                                        ║
║    python gcp_cloudrun_security_auditor.py --project <PROJECT_ID>            ║
║                                                                              ║
║  OPCIONES:                                                                   ║
║    --project, -p    ID del proyecto GCP (requerido)                          ║
║    --region, -r     Región específica o 'all' (default: all)                 ║
║    --service, -s    Servicio específico a auditar                            ║
║    --severity       Filtrar por CRITICAL, WARNING, INFO                      ║
║    --output, -o     Exportar a json, csv o excel                             ║
║    --debug          Modo debug                                              ║
║    --timezone, -tz  Timezone (default: America/Mazatlan)                     ║
║    --help, -h       Muestra esta ayuda                                       ║
║                                                                              ║
║  EJEMPLOS:                                                                   ║
║    python gcp_cloudrun_security_auditor.py -p mi-proyecto                    ║
║    python gcp_cloudrun_security_auditor.py -p mi-proyecto -r us-central1     ║
║    python gcp_cloudrun_security_auditor.py -p mi-proyecto -s mi-servicio     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        sys.exit(0)
    
    if not RICH_AVAILABLE:
        print("Error: La librería 'rich' no está instalada.")
        print("Instalar con: pip install rich")
        sys.exit(1)
    
    # Crear auditor
    auditor = CloudRunSecurityAuditor(
        project=args.project,
        region=args.region,
        debug=args.debug,
        tz=args.timezone
    )
    
    # Mostrar encabezado
    auditor.print_header(
        title="Cloud Run Security Auditor",
        subtitle=f"v{__version__}",
        description=f"Proyecto: {args.project} | Región: {args.region}"
    )
    
    # Validar conexión
    if not auditor.validate_connection():
        auditor.print_error("No se pudo conectar a GCP o no hay permisos suficientes")
        sys.exit(1)
    
    # Auditar servicios
    audit_results = auditor.audit_all_services()
    
    if not audit_results:
        auditor.print_warning("No hay servicios para auditar")
        sys.exit(0)
    
    # Mostrar tabla de seguridad
    auditor.console.print()
    auditor.console.print(auditor.create_security_table(audit_results))
    auditor.console.print()
    
    # Exportar si se solicitó
    if args.output:
        filename = auditor.export_audit(audit_results, args.output)
        auditor.print_success(f"Exportado a: {filename}")


if __name__ == "__main__":
    main()
