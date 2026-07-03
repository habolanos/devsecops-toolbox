#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud Run Deployment Validator

Validación de configuración pre-deploy para Cloud Run.

Autor: Harold Adrian
"""

import argparse
import sys
from typing import List, Dict, Optional

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


class CloudRunDeploymentValidator(CloudRunBase):
    """Validador de despliegues de Cloud Run"""
    
    def __init__(self, project: str, debug: bool = False, tz: str = "America/Mazatlan"):
        super().__init__(project, "all", debug, tz)
        self.validation_results = []
    
    def validate_config(self, config: Dict, strict: bool = False) -> Dict:
        """Valida configuración de despliegue"""
        errors = []
        warnings = []
        
        # Validar nombre del servicio
        service_name = config.get("name", "")
        if not service_name:
            errors.append("Nombre del servicio es requerido")
        elif len(service_name) > 63:
            errors.append("Nombre del servicio no puede exceder 63 caracteres")
        
        # Validar imagen
        image = config.get("image", "")
        if not image:
            errors.append("Imagen del contenedor es requerida")
        elif not image.startswith("gcr.io/") and not image.startswith("us.gcr.io/"):
            warnings.append("Considere usar Google Container Registry (gcr.io)")
        
        # Validar recursos
        cpu = config.get("cpu", "1")
        memory = config.get("memory", "512Mi")
        
        valid_cpus = ["0.08", "0.25", "0.5", "1", "2", "4"]
        if cpu not in valid_cpus:
            errors.append(f"CPU inválida. Valores válidos: {', '.join(valid_cpus)}")
        
        # Validar timeout
        timeout = config.get("timeout", 300)
        if timeout < 1 or timeout > 3600:
            errors.append("Timeout debe estar entre 1 y 3600 segundos")
        
        # Validar min/max instances
        min_instances = config.get("min_instances", 0)
        max_instances = config.get("max_instances", 100)
        
        if min_instances < 0:
            errors.append("min_instances no puede ser negativo")
        if max_instances < min_instances:
            errors.append("max_instances debe ser mayor que min_instances")
        
        # Validar health check
        if not config.get("health_check"):
            warnings.append("Se recomienda configurar health check")
        
        # Validar variables de entorno
        env_vars = config.get("env", {})
        if any(key in env_vars for key in ["PASSWORD", "SECRET", "TOKEN", "KEY"]):
            errors.append("No almacene secretos en variables de entorno. Use Secret Manager")
        
        # Validar VPC connector
        if not config.get("vpc_connector"):
            warnings.append("Considere usar VPC connector para acceso a recursos privados")
        
        return {
            "service_name": service_name,
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "strict_mode": strict,
            "config": config
        }
    
    def create_validation_table(self, validation: Dict) -> Table:
        """Crea tabla de validación"""
        table = Table(
            title="✅ Deployment Validation",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Validación", style="bold white")
        table.add_column("Estado", justify="center")
        table.add_column("Detalles", style="yellow")
        
        # Validar nombre
        table.add_row(
            "Nombre del Servicio",
            "[green]✓[/green]" if validation["config"].get("name") else "[red]✗[/red]",
            validation["config"].get("name", "No especificado")
        )
        
        # Validar imagen
        table.add_row(
            "Imagen del Contenedor",
            "[green]✓[/green]" if validation["config"].get("image") else "[red]✗[/red]",
            validation["config"].get("image", "No especificada")
        )
        
        # Validar recursos
        table.add_row(
            "Recursos (CPU/Memory)",
            "[green]✓[/green]",
            f"{validation['config'].get('cpu', '1')}/{validation['config'].get('memory', '512Mi')}"
        )
        
        # Validar timeout
        table.add_row(
            "Timeout",
            "[green]✓[/green]",
            f"{validation['config'].get('timeout', 300)}s"
        )
        
        # Validar scaling
        table.add_row(
            "Scaling (min/max)",
            "[green]✓[/green]",
            f"{validation['config'].get('min_instances', 0)}/{validation['config'].get('max_instances', 100)}"
        )
        
        return table
    
    def export_validation(self, validation: Dict, format: str = "json") -> str:
        """Exporta validación"""
        export_data = {
            "metadata": {
                "tool": "CloudRunDeploymentValidator",
                "version": __version__,
                "project": self.project
            },
            "validation": validation
        }
        
        return self.export_results(export_data, format, "cloudrun_deployment_validation")


def get_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Cloud Run Deployment Validator", add_help=False)
    parser.add_argument("--project", "-p", type=str, required=True, help="ID del proyecto GCP")
    parser.add_argument("--config", type=str, help="Archivo de configuración YAML")
    parser.add_argument("--strict", action="store_true", help="Modo estricto")
    parser.add_argument("--output", "-o", type=str, choices=["json", "csv", "excel"], help="Formato de exportación")
    parser.add_argument("--debug", action="store_true", help="Modo debug")
    parser.add_argument("--help", "-h", action="store_true", help="Muestra ayuda")
    
    return parser.parse_args()


def main():
    """Función principal"""
    args = get_args()
    
    if args.help:
        print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║              GCP CLOUD RUN DEPLOYMENT VALIDATOR v1.0.0                       ║
║                    Validación Pre-Deploy de Cloud Run                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  DESCRIPCIÓN:                                                                ║
║    Valida configuración de despliegue antes de enviar a Cloud Run.          ║
║                                                                              ║
║  USO:                                                                        ║
║    python gcp_cloudrun_deployment_validator.py --project <PROJECT_ID>        ║
║                                                                              ║
║  OPCIONES:                                                                   ║
║    --project, -p    ID del proyecto GCP (requerido)                          ║
║    --config         Archivo de configuración YAML                           ║
║    --strict         Modo estricto (falla en warnings)                        ║
║    --output, -o     Exportar a json, csv o excel                             ║
║    --debug          Modo debug                                              ║
║    --help, -h       Muestra esta ayuda                                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """)
        sys.exit(0)
    
    if not RICH_AVAILABLE:
        print("Error: La librería 'rich' no está instalada.")
        sys.exit(1)
    
    validator = CloudRunDeploymentValidator(project=args.project, debug=args.debug)
    
    validator.print_header(
        title="Cloud Run Deployment Validator",
        subtitle=f"v{__version__}",
        description=f"Proyecto: {args.project}"
    )
    
    # Ejemplo de configuración
    test_config = {
        "name": "my-service",
        "image": "gcr.io/my-project/my-service:latest",
        "cpu": "1",
        "memory": "512Mi",
        "timeout": 300,
        "min_instances": 0,
        "max_instances": 100,
        "env": {"LOG_LEVEL": "INFO"},
        "vpc_connector": "my-vpc-connector"
    }
    
    validation = validator.validate_config(test_config, args.strict)
    
    validator.console.print()
    validator.console.print(validator.create_validation_table(validation))
    validator.console.print()
    
    if validation["errors"]:
        validator.print_error(f"Encontrados {len(validation['errors'])} errores:")
        for error in validation["errors"]:
            print(f"  • {error}")
    
    if validation["warnings"]:
        validator.print_warning(f"Encontrados {len(validation['warnings'])} warnings:")
        for warning in validation["warnings"]:
            print(f"  • {warning}")
    
    if validation["valid"]:
        validator.print_success("Configuración válida para despliegue")
    
    if args.output:
        filename = validator.export_validation(validation, args.output)
        validator.print_success(f"Exportado a: {filename}")


if __name__ == "__main__":
    main()
