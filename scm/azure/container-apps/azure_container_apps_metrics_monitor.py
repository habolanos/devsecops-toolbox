#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Container Apps Metrics Monitor - Tool 3

Obtiene información y métricas de uso de Azure Container Apps:
- Request count (últimos 5 min)
- Latencia p95 (ms)
- CPU utilization (%)
- Memory utilization (%)
- Error rate (%)

Homologación de GCP Cloud Run Monitoring y AWS ECS Fargate.

Uso:
    python azure_container_apps_metrics_monitor.py --subscription <id> --resource-group <rg>
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional


def _is_tty() -> bool:
    """Retorna True si stdout es un terminal interactivo."""
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.resource import ResourceManagementClient
    from azure.mgmt.appcontainers import ContainerAppsAPIClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE and _is_tty() else (Console(force_terminal=False, no_color=True) if RICH_AVAILABLE else None)

__version__ = "1.0.0"
__description__ = "Monitorea métricas de Azure Container Apps"


def get_container_apps(subscription_id: str, resource_group: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lista las Container Apps de una suscripción y/o grupo de recursos."""
    if not AZURE_AVAILABLE:
        return []
    
    try:
        credential = DefaultAzureCredential()
        client = ContainerAppsAPIClient(credential, subscription_id)
        
        apps = []
        if resource_group:
            containers = client.container_apps.list_by_resource_group(resource_group)
        else:
            containers = client.container_apps.list_by_subscription()
        
        for app in containers:
            apps.append({
                "name": app.name,
                "resource_id": app.id,
                "resource_group": app.resource_group,
                "location": app.location,
                "revisions_mode": app.configuration.revisions_mode if app.configuration else "N/A",
                "ingress": app.configuration.ingress.external if (app.configuration and app.configuration.ingress) else False
            })
        
        return apps
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ Error al listar Container Apps: {e}[/red]")
        else:
            print(f"❌ Error al listar Container Apps: {e}")
        return []


def get_app_info(subscription_id: str, resource_group: str, app_name: str) -> Dict[str, Any]:
    """Obtiene información básica de una Container App."""
    if not AZURE_AVAILABLE:
        return {"name": app_name}
    
    try:
        credential = DefaultAzureCredential()
        client = ContainerAppsAPIClient(credential, subscription_id)
        app = client.container_apps.get(resource_group, app_name)
        
        return {
            "name": app.name,
            "resource_group": app.resource_group,
            "location": app.location,
            "replicas": app.properties.get("revisions", [])
        }
    except Exception:
        return {"name": app_name}


def print_table(apps_info: Dict[str, Any], metrics: Dict[str, Any]):
    """Imprime la tabla de métricas."""
    if RICH_AVAILABLE and console:
        table = Table(
            title="Azure Container Apps Metrics",
            title_style="bold cyan"
        )
        table.add_column("App", style="bold")
        table.add_column("RG")
        table.add_column("Location")
        table.add_column("Requests")
        table.add_column("Lat p95", justify="right")
        table.add_column("CPU%", justify="right")
        table.add_column("Mem%", justify="right")
        table.add_column("Errores%", justify="right")
        
        for name, info in apps_info.items():
            m = metrics.get(name, {})
            table.add_row(
                info.get("name", name),
                info.get("resource_group", "N/A"),
                info.get("location", "N/A"),
                str(m.get("request_count", "N/A")),
                f"{m.get('latency_p95_ms', 'N/A')} ms" if m.get('latency_p95_ms') is not None else "N/A",
                f"{m.get('cpu_percent', 'N/A')}%" if m.get('cpu_percent') is not None else "N/A",
                f"{m.get('memory_percent', 'N/A')}%" if m.get('memory_percent') is not None else "N/A",
                f"{m.get('error_rate_percent', 'N/A')}%" if m.get('error_rate_percent') is not None else "N/A"
            )
        
        console.print(table)
    else:
        print("\nAzure Container Apps Metrics")
        print("-" * 80)
        for name, info in apps_info.items():
            m = metrics.get(name, {})
            print(f"{info.get('name', name):30} | "
                  f"CPU:{m.get('cpu_percent', 'N/A'):<7} "
                  f"Mem:{m.get('memory_percent', 'N/A'):<7} "
                  f"Req:{m.get('request_count', 'N/A'):<6}")


def main():
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--subscription", required=True, help="Azure subscription ID")
    parser.add_argument("--resource-group", help="Azure resource group")
    parser.add_argument("-o", "--output", choices=["json", "table"], default="table", help="Output format")
    
    args = parser.parse_args()
    
    apps = get_container_apps(args.subscription, args.resource_group)
    if not apps:
        print("No se encontraron Container Apps.")
        sys.exit(0)
    
    # Importar aquí para evitar circular y mantener el módulo usable sin Azure
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from monitoring.azure_monitor_metrics import get_container_app_metrics_parallel
    except ImportError:
        print("❌ No se pudo importar azure_monitor_metrics")
        sys.exit(1)
    
    metrics = get_container_app_metrics_parallel(apps)
    
    apps_info = {app["name"]: app for app in apps}
    
    if args.output == "json":
        output = {
            "subscription": args.subscription,
            "apps": [
                {**apps_info.get(app["name"], {}), "metrics": metrics.get(app["name"], {})}
                for app in apps
            ]
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print_table(apps_info, metrics)


if __name__ == "__main__":
    main()
