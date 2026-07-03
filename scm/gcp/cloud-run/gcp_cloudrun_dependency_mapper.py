#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud Run Dependency Mapper

Mapeo de dependencias y conectividad entre servicios.

Autor: Harold Adrian
"""

import argparse
import sys
from typing import List, Dict

from cloudrun_base import CloudRunBase

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"


class CloudRunDependencyMapper(CloudRunBase):
    """Mapeador de dependencias de Cloud Run"""
    
    def __init__(self, project: str, region: str = "all", debug: bool = False, tz: str = "America/Mazatlan"):
        super().__init__(project, region, debug, tz)
        self.services = []
        self.dependencies = {}
    
    def get_services(self) -> List[Dict]:
        """Obtiene lista de servicios"""
        if self.region == "all":
            command = "gcloud run services list"
        else:
            command = f"gcloud run services list --region={self.region}"
        return self.run_gcloud_command(command) or []
    
    def map_service_dependencies(self, service: Dict) -> Dict:
        """Mapea dependencias de un servicio"""
        metadata = service.get("metadata", {})
        spec = service.get("spec", {}).get("template", {}).get("spec", {})
        
        service_name = metadata.get("name", "unknown")
        region = metadata.get("labels", {}).get("cloud.googleapis.com/location", "unknown")
        
        # Extraer variables de entorno que podrían indicar dependencias
        container_spec = spec.get("containers", [{}])[0] if spec.get("containers") else {}
        env_vars = container_spec.get("env", [])
        
        dependencies = []
        for var in env_vars:
            name = var.get("name", "")
            if any(x in name.upper() for x in ["HOST", "URL", "ENDPOINT", "SERVICE"]):
                dependencies.append({
                    "type": "environment_variable",
                    "name": name,
                    "value": var.get("value", "")
                })
        
        # Analizar VPC connector
        annotations = metadata.get("annotations", {})
        vpc_connector = annotations.get("run.googleapis.com/vpc-access-connector", "")
        
        vpc_dependencies = []
        if vpc_connector:
            vpc_dependencies.append({
                "type": "vpc_connector",
                "name": vpc_connector,
                "connectivity": "Private Network"
            })
        
        return {
            "service_name": service_name,
            "region": region,
            "environment_dependencies": dependencies,
            "vpc_dependencies": vpc_dependencies,
            "total_dependencies": len(dependencies) + len(vpc_dependencies),
            "connectivity_status": "Connected" if vpc_connector else "Public Only"
        }
    
    def create_dependency_table(self, mappings: List[Dict]) -> Table:
        """Crea tabla de dependencias"""
        table = Table(title="🔗 Dependency Map", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Servicio", style="bold white")
        table.add_column("Región", style="yellow")
        table.add_column("Dependencias", justify="center")
        table.add_column("VPC", justify="center")
        table.add_column("Conectividad", style="cyan")
        
        for mapping in mappings:
            vpc_status = "✓" if mapping["vpc_dependencies"] else "✗"
            table.add_row(
                mapping["service_name"],
                mapping["region"],
                str(mapping["total_dependencies"]),
                vpc_status,
                mapping["connectivity_status"]
            )
        
        return table
    
    def export_mapping(self, mappings: List[Dict], format: str = "json") -> str:
        """Exporta mapeo"""
        export_data = {
            "metadata": {
                "tool": "CloudRunDependencyMapper",
                "version": __version__,
                "project": self.project
            },
            "dependency_mappings": mappings
        }
        return self.export_results(export_data, format, "cloudrun_dependency_map")


def get_args():
    parser = argparse.ArgumentParser(description="Cloud Run Dependency Mapper", add_help=False)
    parser.add_argument("--project", "-p", type=str, required=True, help="ID del proyecto GCP")
    parser.add_argument("--region", "-r", type=str, default="all", help="Región específica o 'all'")
    parser.add_argument("--service", "-s", type=str, help="Servicio específico")
    parser.add_argument("--depth", type=int, default=1, help="Profundidad del mapeo")
    parser.add_argument("--output", "-o", type=str, choices=["json", "csv", "excel"], help="Formato de exportación")
    parser.add_argument("--debug", action="store_true", help="Modo debug")
    parser.add_argument("--help", "-h", action="store_true", help="Muestra ayuda")
    return parser.parse_args()


def main():
    args = get_args()
    
    if args.help:
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║             GCP CLOUD RUN DEPENDENCY MAPPER v1.0.0                           ║
║                    Mapeo de Dependencias de Cloud Run                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  USO:                                                                        ║
║    python gcp_cloudrun_dependency_mapper.py --project <PROJECT_ID>           ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        sys.exit(0)
    
    if not RICH_AVAILABLE:
        print("Error: La librería 'rich' no está instalada.")
        sys.exit(1)
    
    mapper = CloudRunDependencyMapper(project=args.project, region=args.region, debug=args.debug)
    mapper.print_header("Cloud Run Dependency Mapper", f"v{__version__}")
    
    if not mapper.validate_connection():
        mapper.print_error("No se pudo conectar a GCP")
        sys.exit(1)
    
    services = mapper.get_services()
    if not services:
        mapper.print_warning("No hay servicios para mapear")
        sys.exit(0)
    
    mappings = [mapper.map_service_dependencies(s) for s in services]
    
    mapper.console.print()
    mapper.console.print(mapper.create_dependency_table(mappings))
    mapper.console.print()
    
    if args.output:
        filename = mapper.export_mapping(mappings, args.output)
        mapper.print_success(f"Exportado a: {filename}")


if __name__ == "__main__":
    main()
