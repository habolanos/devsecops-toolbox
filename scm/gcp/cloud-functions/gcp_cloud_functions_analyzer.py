#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud Functions Analyzer v1.0.0

Herramienta SRE para analizar y monitorear Cloud Functions en Google Cloud Platform.
Proporciona análisis de seguridad, costos, triggers y relaciones con Load Balancers.

Uso:
    python gcp_cloud_functions_analyzer.py --project mi-proyecto
    python gcp_cloud_functions_analyzer.py --project mi-proyecto --view security
    python gcp_cloud_functions_analyzer.py --project mi-proyecto --output json

Autor: Harold Adrian
"""

import sys
import os
import argparse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

from cf_base import CloudFunctionsBase, run_gcloud_command, get_output_dir
from cf_metrics import CloudFunctionsMetrics

__version__ = "1.0.0"
__author__ = "Harold Adrian"


def get_args():
    parser = argparse.ArgumentParser(
        description="SRE Tool: GCP Cloud Functions Analyzer",
        add_help=False
    )
    parser.add_argument(
        "--project", "-p",
        type=str,
        default="cpl-corp-cial-prod-17042024",
        help="ID del proyecto de GCP"
    )
    parser.add_argument(
        "--view", "-v",
        type=str,
        choices=["all", "overview", "security", "cost", "triggers", "performance"],
        default="all",
        help="Vista específica a mostrar"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["json", "csv", "excel"],
        help="Exportar resultados"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Modo debug"
    )
    parser.add_argument(
        "--timezone", "-tz",
        type=str,
        default="America/Mazatlan",
        help="Timezone para timestamps"
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Muestra ayuda"
    )
    return parser.parse_args()


def check_gcp_connection(project_id: str, console, debug: bool = False) -> bool:
    """Verifica conexión a GCP."""
    try:
        import subprocess
        
        # Verificar sesión activa
        auth_cmd = 'gcloud auth list --filter=status:ACTIVE --format="value(account)"'
        auth_result = subprocess.run(auth_cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if auth_result.returncode != 0 or not auth_result.stdout.strip():
            console.print("[red]❌ No hay sesión activa de gcloud[/red]")
            return False
        
        console.print(f"[green]✓[/green] Sesión activa")
        
        # Verificar acceso al proyecto
        project_cmd = f'gcloud projects describe {project_id} --format="value(projectId)" 2>&1'
        project_result = subprocess.run(project_cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if project_result.returncode != 0:
            console.print(f"[red]❌ No tienes acceso al proyecto: {project_id}[/red]")
            return False
        
        console.print(f"[green]✓[/green] Proyecto accesible: [cyan]{project_id}[/cyan]")
        return True
    except Exception as e:
        console.print(f"[red]❌ Error verificando conexión: {e}[/red]")
        return False


def create_overview_table(functions: List[Dict], console) -> Table:
    """Crea tabla de resumen general."""
    table = Table(
        title="📊 Cloud Functions Overview",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Nombre", style="white", no_wrap=True)
    table.add_column("Runtime", style="yellow")
    table.add_column("Región", style="blue")
    table.add_column("Tipo", style="green")
    table.add_column("Estado", style="magenta")
    table.add_column("Salud", style="cyan")
    
    for func in functions:
        name = func.get('name', 'N/A').split('/')[-1]
        runtime = func.get('runtime', 'N/A')
        region = func.get('serviceConfig', {}).get('region', 'N/A')
        func_type = CloudFunctionsMetrics.categorize_function(func)
        state = CloudFunctionsMetrics.get_runtime_status(func)
        health = CloudFunctionsMetrics.calculate_health_score(func)
        
        health_color = "green" if health >= 80 else "yellow" if health >= 60 else "red"
        health_str = f"[{health_color}]{health}[/{health_color}]"
        
        table.add_row(name, runtime, region, func_type, state, health_str)
    
    return table


def create_security_table(functions: List[Dict], console) -> Table:
    """Crea tabla de análisis de seguridad."""
    table = Table(
        title="🔒 Security Analysis",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Nombre", style="white", no_wrap=True)
    table.add_column("Público", style="red")
    table.add_column("Auth", style="green")
    table.add_column("Service Account", style="blue")
    table.add_column("Env Vars", style="yellow")
    table.add_column("Score", style="magenta")
    
    for func in functions:
        name = func.get('name', 'N/A').split('/')[-1]
        security = CloudFunctionsBase(project_id="").analyze_function_security(func)
        
        is_public = "[red]✓ PUBLIC[/red]" if security['is_public'] else "[green]✗ Private[/green]"
        requires_auth = "[green]✓[/green]" if security['requires_authentication'] else "[red]✗[/red]"
        sa = security['service_account'].split('@')[0] if '@' in security['service_account'] else security['service_account']
        env_count = security['environment_variables_count']
        score = CloudFunctionsMetrics.calculate_security_score(func)
        
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
        score_str = f"[{score_color}]{score}[/{score_color}]"
        
        table.add_row(name, is_public, requires_auth, sa, str(env_count), score_str)
    
    return table


def create_cost_table(functions: List[Dict], console) -> Table:
    """Crea tabla de análisis de costos."""
    table = Table(
        title="💰 Cost Analysis",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Nombre", style="white", no_wrap=True)
    table.add_column("Memory (MB)", style="yellow", justify="right")
    table.add_column("Timeout (s)", style="blue", justify="right")
    table.add_column("Min Instances", style="green", justify="right")
    table.add_column("Est. Costo/mes", style="magenta", justify="right")
    table.add_column("Eficiencia", style="cyan", justify="right")
    
    for func in functions:
        name = func.get('name', 'N/A').split('/')[-1]
        perf = CloudFunctionsBase(project_id="").analyze_function_performance(func)
        cost = CloudFunctionsMetrics.estimate_monthly_cost(func)
        efficiency = CloudFunctionsMetrics.calculate_cost_efficiency_score(func)
        
        efficiency_color = "green" if efficiency >= 80 else "yellow" if efficiency >= 60 else "red"
        efficiency_str = f"[{efficiency_color}]{efficiency}[/{efficiency_color}]"
        
        table.add_row(
            name,
            str(perf['memory_mb']),
            str(perf['timeout_seconds']),
            str(perf['min_instances']),
            f"${cost}",
            efficiency_str
        )
    
    return table


def create_triggers_table(functions: List[Dict], console) -> Table:
    """Crea tabla de triggers."""
    table = Table(
        title="⚡ Triggers",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Nombre", style="white", no_wrap=True)
    table.add_column("Tipo", style="yellow")
    table.add_column("Detalles", style="blue")
    table.add_column("Servicio", style="green")
    
    for func in functions:
        name = func.get('name', 'N/A').split('/')[-1]
        base = CloudFunctionsBase(project_id="")
        triggers = base.analyze_function_triggers(func)
        
        trigger_type = triggers.get('type', 'UNKNOWN')
        
        if trigger_type == 'HTTP':
            details = triggers.get('uri', 'N/A')[:50]
            service = "HTTP"
        elif trigger_type == 'EVENT':
            details = triggers.get('eventType', 'N/A')
            service = triggers.get('service', 'N/A')
        else:
            details = "N/A"
            service = "N/A"
        
        table.add_row(name, trigger_type, details, service)
    
    return table


def create_summary_table(functions: List[Dict], console) -> Table:
    """Crea tabla de resumen."""
    table = Table(
        title="📈 Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Métrica", style="white")
    table.add_column("Valor", style="cyan", justify="right")
    
    comparison = CloudFunctionsMetrics.compare_functions(functions)
    
    table.add_row("Total Functions", str(comparison.get('total_functions', 0)))
    table.add_row("Public Functions", str(sum(
        1 for f in functions
        if f.get('serviceConfig', {}).get('ingressSettings') == 'ALLOW_ALL'
    )))
    table.add_row("Avg Memory (MB)", str(comparison.get('avg_memory_mb', 0)))
    table.add_row("Avg Timeout (s)", str(comparison.get('avg_timeout_seconds', 0)))
    table.add_row("Est. Monthly Cost", f"${comparison.get('total_estimated_cost', 0)}")
    
    # Runtimes
    for runtime, count in comparison.get('by_runtime', {}).items():
        table.add_row(f"  {runtime}", str(count))
    
    return table


def export_results(functions: List[Dict], project_id: str, output_format: str, tz_name: str):
    """Exporta resultados."""
    output_dir = get_output_dir()
    tz = ZoneInfo(tz_name)
    timestamp = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback manual
        import json
        filepath = output_dir / f"cf_analyzer_{project_id}_{timestamp}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "generated_at": datetime.now(tz).isoformat(),
                "functions": functions,
                "summary": CloudFunctionsMetrics.compare_functions(functions)
            }, f, indent=2, default=str)
        return str(filepath)
    
    # Usar ExportManager
    manager = ExportManager("gcp_cloud_functions_analyzer", __version__)
    
    summary = {
        "total_functions": len(functions),
        "public_functions": sum(1 for f in functions if f.get('serviceConfig', {}).get('ingressSettings') == 'ALLOW_ALL'),
        "total_estimated_cost": CloudFunctionsMetrics.compare_functions(functions).get('total_estimated_cost', 0)
    }
    
    if output_format == "json":
        return manager.export_json(functions, summary=summary)
    elif output_format == "csv":
        return manager.export_csv(functions)
    elif output_format == "excel":
        return manager.export_excel(functions, sheet_name="Functions", summary=summary)


def main():
    """Función principal."""
    if not RICH_AVAILABLE:
        print("❌ Se requiere 'rich'. Instala con: pip install rich")
        sys.exit(1)
    
    console = Console()
    args = get_args()
    
    if args.help:
        console.print(Panel(
            "[bold cyan]GCP Cloud Functions Analyzer[/bold cyan]\n\n"
            "Analiza y monitorea Cloud Functions en Google Cloud Platform.\n\n"
            "[yellow]Uso:[/yellow]\n"
            "  python gcp_cloud_functions_analyzer.py --project mi-proyecto\n"
            "  python gcp_cloud_functions_analyzer.py --project mi-proyecto --view security\n"
            "  python gcp_cloud_functions_analyzer.py --project mi-proyecto --output json\n\n"
            "[yellow]Vistas:[/yellow]\n"
            "  all - Todas las vistas\n"
            "  overview - Resumen general\n"
            "  security - Análisis de seguridad\n"
            "  cost - Análisis de costos\n"
            "  triggers - Análisis de triggers\n"
            "  performance - Análisis de performance",
            border_style="blue"
        ))
        return
    
    project_id = args.project
    view = args.view
    debug = args.debug
    tz_name = args.timezone
    
    console.print(Panel(
        f"[bold cyan]GCP Cloud Functions Analyzer v{__version__}[/bold cyan]\n"
        f"Proyecto: [yellow]{project_id}[/yellow]",
        border_style="blue"
    ))
    
    # Verificar conexión
    if not check_gcp_connection(project_id, console, debug):
        return
    
    console.print()
    
    # Recolectar datos
    base = CloudFunctionsBase(project_id, debug)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Recolectando Cloud Functions...", total=None)
        functions = base.get_functions()
    
    if not functions:
        console.print("[yellow]⚠️  No se encontraron Cloud Functions[/yellow]")
        return
    
    console.print()
    
    # Mostrar tablas según vista
    if view in ['all', 'overview']:
        console.print(create_overview_table(functions, console))
        console.print()
    
    if view in ['all', 'security']:
        console.print(create_security_table(functions, console))
        console.print()
    
    if view in ['all', 'cost']:
        console.print(create_cost_table(functions, console))
        console.print()
    
    if view in ['all', 'triggers']:
        console.print(create_triggers_table(functions, console))
        console.print()
    
    # Siempre mostrar resumen
    console.print(create_summary_table(functions, console))
    console.print()
    
    # Exportar si se especificó
    if args.output:
        filepath = export_results(functions, project_id, args.output, tz_name)
        console.print(f"[green]✓ Exportado a:[/green] {filepath}")
    
    console.print(f"[dim]⏱️  Completado[/dim]")


if __name__ == "__main__":
    main()
