#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Cloud SQL Comparator - Herramienta SCM para comparación de instancias

Lista TODAS las instancias Cloud SQL de 2 proyectos GCP y compara sus atributos:
- Cloud SQL Edition (Enterprise, Enterprise Plus)
- Type (MySQL, PostgreSQL, SQL Server)
- Port Number
- Public IP Connectivity
- Private IP Connectivity

Características:
- Usa gcloud CLI (no requiere APIs de Python especiales)
- Lista automáticamente todas las instancias de ambos proyectos
- Compara instancias con nombres coincidentes
- Tabla comparativa con semáforos de validación (✅, 🚧, ⛔)
- Validación de conexión GCP antes de ejecutar
- Exportación a CSV y JSON

El resultado se guarda en: outcome/sql_compare_<timestamp>.<ext>

Autor: Harold Adrian
"""

import argparse
import subprocess
import json
import csv
import os
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any, Tuple

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

try:
    from rich.console import Console
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.1.0"
__author__ = "Harold Adrian"

# Puertos por defecto según tipo de base de datos
DEFAULT_PORTS = {
    "MYSQL": 3306,
    "POSTGRES": 5432,
    "SQLSERVER": 1433
}


def get_args():
    """Parsea los argumentos de línea de comandos"""
    parser = argparse.ArgumentParser(
        description="SCM Tool: Cloud SQL Instance Comparator between GCP Projects",
        add_help=False
    )
    parser.add_argument(
        "--project1", "-p1",
        type=str,
        required=True,
        help="ID del primer proyecto GCP (proyecto de referencia)"
    )
    parser.add_argument(
        "--project2", "-p2",
        type=str,
        required=True,
        help="ID del segundo proyecto GCP (proyecto a comparar)"
    )
    parser.add_argument(
        "--instance", "-i",
        type=str,
        default=None,
        help="Filtrar por nombre de instancia específica (opcional)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa modo debug para ver comandos gcloud ejecutados"
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Muestra documentación completa del script"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["csv", "json"],
        help="Exporta resultados a archivo (csv o json) en carpeta outcome/"
    )
    parser.add_argument(
        "--timezone", "-tz",
        type=str,
        default="America/Mazatlan",
        help="Zona horaria para mostrar fechas (default: America/Mazatlan)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Muestra comparación de TODOS los atributos (no solo versiones)"
    )
    parser.add_argument(
        "--attributes",
        type=str,
        nargs="+",
        choices=["edition", "type", "port", "public_ip", "private_ip"],
        help="Atributos específicos a comparar además de la versión"
    )
    return parser.parse_args()


def show_help():
    """Muestra el README.md con formato enriquecido en consola"""
    console = Console()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(script_dir, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
        console.print(Markdown(readme_content))
    else:
        console.print("[yellow]README.md no encontrado[/]")
        print_usage(console)


def print_usage(console):
    """Imprime información de uso básica"""
    usage_text = """
## Uso Básico

```bash
python gcp_sql_comparator.py --project1 <PROJECT_1> --project2 <PROJECT_2>
```

## Atributos Comparados

| Atributo | Descripción |
|----------|-------------|
| Cloud SQL Edition | Enterprise, Enterprise Plus |
| Type | MySQL, PostgreSQL, SQL Server |
| Port Number | Puerto de conexión (3306, 5432, 1433) |
| Public IP | Conectividad IP pública habilitada |
| Private IP | Conectividad IP privada habilitada |

## Semáforos

- ✅ **OK**: Los valores coinciden
- 🚧 **WARNING**: Los valores difieren pero no es crítico
- ⛔ **ERROR**: Los valores difieren y es crítico
"""
    console.print(Markdown(usage_text))


def check_gcp_connection(project_id: str, console, debug: bool = False) -> bool:
    """Valida conexión a GCP antes de ejecutar el script"""
    try:
        auth_cmd = 'gcloud auth list --filter=status:ACTIVE --format="value(account)"'
        auth_result = subprocess.run(auth_cmd, shell=True, capture_output=True, text=True)
        
        if debug:
            print(f"[DEBUG] Auth command: {auth_cmd}")
            print(f"[DEBUG] Auth result: {auth_result.stdout.strip()}")
        
        if auth_result.returncode != 0 or not auth_result.stdout.strip():
            console.print("[red]❌ No hay sesión activa de gcloud. Ejecuta: gcloud auth login[/]")
            return False
        
        project_cmd = f'gcloud projects describe {project_id} --format="value(projectId)" 2>&1'
        project_result = subprocess.run(project_cmd, shell=True, capture_output=True, text=True)
        
        if debug:
            print(f"[DEBUG] Project command: {project_cmd}")
            print(f"[DEBUG] Project result: {project_result.stdout.strip()}")
        
        if project_result.returncode != 0:
            console.print(f"[red]❌ No tienes acceso al proyecto: {project_id}[/]")
            return False
        
        return True
        
    except Exception as e:
        if debug:
            print(f"[DEBUG] Connection check exception: {e}")
        console.print(f"[red]❌ Error verificando conexión: {e}[/]")
        return False


def run_gcloud_command(command: str, debug: bool = False) -> Optional[Any]:
    """Ejecuta un comando gcloud y retorna el resultado como JSON"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        if debug:
            print(f"[DEBUG] Command: {command}")
            print(f"[DEBUG] Return code: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] Stderr: {result.stderr}")
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except (json.JSONDecodeError, Exception) as e:
        if debug:
            print(f"[DEBUG] Exception: {e}")
        return None


def get_all_sql_instances(project_id: str, debug: bool = False) -> List[Dict]:
    """Obtiene lista de todas las instancias Cloud SQL de un proyecto"""
    cmd = f'gcloud sql instances list --project={project_id} --format=json'
    result = run_gcloud_command(cmd, debug)
    return result if result else []


def extract_instance_attributes(instance_data: Dict) -> Dict[str, Any]:
    """Extrae los atributos relevantes de una instancia Cloud SQL"""
    if not instance_data:
        return {
            "name": "N/A",
            "edition": "N/A",
            "type": "N/A",
            "port": "N/A",
            "public_ip": "N/A",
            "private_ip": "N/A",
            "state": "NOT_FOUND"
        }
    
    settings = instance_data.get("settings", {})
    ip_config = settings.get("ipConfiguration", {})
    
    # Nombre de la instancia
    name = instance_data.get("name", "UNKNOWN")
    
    # Extraer tipo de base de datos
    db_version = instance_data.get("databaseVersion", "UNKNOWN")
    db_type = db_version.split("_")[0] if "_" in db_version else db_version
    
    # Extraer edición
    edition = settings.get("edition", "ENTERPRISE")
    if edition == "ENTERPRISE_PLUS":
        edition_display = "Enterprise Plus"
    else:
        edition_display = "Enterprise"
    
    # Determinar puerto según tipo de DB
    port = DEFAULT_PORTS.get(db_type, "UNKNOWN")
    
    # Verificar conectividad IP pública
    public_ip_enabled = ip_config.get("ipv4Enabled", False)
    
    # Verificar conectividad IP privada
    private_network = ip_config.get("privateNetwork", None)
    private_ip_enabled = private_network is not None and private_network != ""
    
    # Estado de la instancia
    state = instance_data.get("state", "UNKNOWN")
    
    return {
        "name": name,
        "edition": edition_display,
        "type": db_type,
        "port": port,
        "public_ip": public_ip_enabled,
        "private_ip": private_ip_enabled,
        "state": state,
        "db_version": db_version
    }


def compare_attribute(attr_name: str, value1: Any, value2: Any) -> Tuple[str, str]:
    """Compara dos valores y retorna el semáforo apropiado."""
    # Atributos críticos donde la diferencia es un error
    critical_attrs = ["type", "port"]
    
    # Atributos importantes donde la diferencia es warning
    warning_attrs = ["edition", "public_ip", "private_ip"]
    
    if value1 == value2:
        return "✅", "OK"
    
    if attr_name in critical_attrs:
        return "⛔", "MISMATCH"
    
    if attr_name in warning_attrs:
        return "🚧", "DIFFERS"
    
    return "🚧", "DIFFERS"


def format_bool_value(value: Any) -> str:
    """Formatea un valor booleano para mostrar"""
    if isinstance(value, bool):
        return "ENABLED" if value else "DISABLED"
    return str(value)


def get_overall_status(attrs1: Dict, attrs2: Dict) -> Tuple[str, str]:
    """Calcula el estado general de la comparación de una instancia"""
    attributes_to_compare = ["edition", "type", "port", "public_ip", "private_ip"]
    
    has_mismatch = False
    has_differs = False
    
    for attr in attributes_to_compare:
        val1 = attrs1.get(attr, "N/A")
        val2 = attrs2.get(attr, "N/A")
        semaphore, _ = compare_attribute(attr, val1, val2)
        
        if semaphore == "⛔":
            has_mismatch = True
        elif semaphore == "🚧":
            has_differs = True
    
    if has_mismatch:
        return "⛔", "MISMATCH"
    elif has_differs:
        return "🚧", "DIFFERS"
    else:
        return "✅", "OK"


def print_instances_list(console, instances: List[Dict], project: str):
    """Muestra la lista de instancias de un proyecto"""
    table = Table(
        title=f"📋 Instancias en {project}",
        title_style="bold cyan",
        header_style="bold white",
        border_style="dim"
    )
    
    table.add_column("#", style="dim", width=3)
    table.add_column("Instancia", style="white bold")
    table.add_column("Edition", justify="center")
    table.add_column("Type", justify="center")
    table.add_column("Port", justify="center")
    table.add_column("Public IP", justify="center")
    table.add_column("Private IP", justify="center")
    table.add_column("Estado", justify="center")
    
    for idx, inst in enumerate(instances, 1):
        attrs = extract_instance_attributes(inst)
        table.add_row(
            str(idx),
            attrs["name"],
            attrs["edition"],
            attrs["type"],
            str(attrs["port"]),
            "[green]ENABLED[/]" if attrs["public_ip"] else "[red]DISABLED[/]",
            "[green]ENABLED[/]" if attrs["private_ip"] else "[red]DISABLED[/]",
            f"[green]{attrs['state']}[/]" if attrs["state"] == "RUNNING" else f"[yellow]{attrs['state']}[/]"
        )
    
    console.print(table)


def print_version_comparison_table(console, all_comparisons: List[Dict], project1: str, project2: str):
    """Imprime tabla comparativa de versiones de DB para todas las instancias"""
    
    table = Table(
        title="📦 Comparación de Versiones de Base de Datos",
        title_style="bold blue",
        header_style="bold cyan",
        border_style="dim",
        box=box.ROUNDED
    )
    
    table.add_column("#", style="dim", width=3)
    table.add_column("Instancia", style="white bold", width=25)
    table.add_column(f"📌 {project1}", justify="center", width=20)
    table.add_column(f"📌 {project2}", justify="center", width=20)
    table.add_column("Check", justify="center", width=8)
    
    version_ok = 0
    version_differs = 0
    
    for idx, comp in enumerate(all_comparisons, 1):
        instance_name = comp["instance_name"]
        attrs1 = comp["attrs1"]
        attrs2 = comp["attrs2"]
        
        version1 = attrs1.get("db_version", "N/A") if comp["in_project1"] else "❌ NO EXISTE"
        version2 = attrs2.get("db_version", "N/A") if comp["in_project2"] else "❌ NO EXISTE"
        
        # Determinar semáforo
        if not comp["in_project1"] or not comp["in_project2"]:
            semaphore = "🚧"
            status = "MISSING"
            version_differs += 1
        elif version1 == version2:
            semaphore = "✅"
            status = "OK"
            version_ok += 1
        else:
            semaphore = "⛔"
            status = "MISMATCH"
            version_differs += 1
        
        # Colores según estado
        if semaphore == "✅":
            v1_display = f"[green]{version1}[/]"
            v2_display = f"[green]{version2}[/]"
            row_style = ""
        elif semaphore == "⛔":
            v1_display = f"[red]{version1}[/]"
            v2_display = f"[red]{version2}[/]"
            row_style = "red"
        else:
            v1_display = f"[yellow]{version1}[/]"
            v2_display = f"[yellow]{version2}[/]"
            row_style = "yellow"
        
        table.add_row(
            str(idx),
            instance_name,
            v1_display,
            v2_display,
            semaphore,
            style=row_style
        )
    
    console.print(table)
    
    # Mini resumen de versiones
    total = len(all_comparisons)
    console.print(f"[dim]   Versiones: [green]✅ Iguales: {version_ok}[/] | [red]⛔ Diferentes: {version_differs}[/] | Total: {total}[/]")


def print_comparison_table(console, all_comparisons: List[Dict], project1: str, project2: str, filter_attrs: List[str] = None):
    """Imprime la tabla de comparación con todas las instancias
    
    Args:
        filter_attrs: Lista de atributos específicos a mostrar (None = todos)
    """
    
    table = Table(
        title="🔍 Comparación de Atributos Cloud SQL",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim",
        box=box.ROUNDED
    )
    
    table.add_column("Instancia", style="white bold", width=25)
    table.add_column("Atributo", style="white", width=18)
    table.add_column(f"📌 {project1}", justify="center", width=18)
    table.add_column(f"📌 {project2}", justify="center", width=18)
    table.add_column("Check", justify="center", width=8)
    
    all_attributes = [
        ("Edition", "edition"),
        ("Type", "type"),
        ("Port", "port"),
        ("Public IP", "public_ip"),
        ("Private IP", "private_ip"),
    ]
    
    # Filtrar atributos si se especificaron
    if filter_attrs:
        attributes = [(name, key) for name, key in all_attributes if key in filter_attrs]
    else:
        attributes = all_attributes
    
    for comp in all_comparisons:
        instance_name = comp["instance_name"]
        attrs1 = comp["attrs1"]
        attrs2 = comp["attrs2"]
        
        # Primera fila con nombre de instancia
        first_row = True
        for display_name, attr_key in attributes:
            val1 = attrs1.get(attr_key, "N/A")
            val2 = attrs2.get(attr_key, "N/A")
            
            display_val1 = format_bool_value(val1)
            display_val2 = format_bool_value(val2)
            
            semaphore, _ = compare_attribute(attr_key, val1, val2)
            
            # Color según semáforo
            val_color = "green" if semaphore == "✅" else ("red" if semaphore == "⛔" else "yellow")
            
            row_style = ""
            if semaphore == "⛔":
                row_style = "red"
            elif semaphore == "🚧":
                row_style = "yellow"
            
            table.add_row(
                f"[bold]{instance_name}[/]" if first_row else "",
                display_name,
                f"[{val_color}]{display_val1}[/]",
                f"[{val_color}]{display_val2}[/]",
                semaphore,
                style=row_style
            )
            first_row = False
        
        # Separador entre instancias
        table.add_row("", "", "", "", "", style="dim")
    
    console.print(table)


def print_summary_table(console, all_comparisons: List[Dict], project1: str, project2: str):
    """Imprime tabla resumen con todas las instancias y su estado general"""
    
    table = Table(
        title="📊 Resumen de Comparación",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="dim",
        box=box.ROUNDED
    )
    
    table.add_column("Instancia", style="white bold", width=30)
    table.add_column(f"En {project1}", justify="center", width=15)
    table.add_column(f"En {project2}", justify="center", width=15)
    table.add_column("Estado", justify="center", width=12)
    table.add_column("Check", justify="center", width=10)
    
    ok_count = 0
    differs_count = 0
    mismatch_count = 0
    only_p1_count = 0
    only_p2_count = 0
    
    for comp in all_comparisons:
        instance_name = comp["instance_name"]
        in_p1 = comp["in_project1"]
        in_p2 = comp["in_project2"]
        
        if in_p1 and in_p2:
            semaphore, status = get_overall_status(comp["attrs1"], comp["attrs2"])
            p1_status = "[green]✓[/]"
            p2_status = "[green]✓[/]"
            
            if semaphore == "✅":
                ok_count += 1
            elif semaphore == "🚧":
                differs_count += 1
            else:
                mismatch_count += 1
        elif in_p1:
            semaphore = "🚧"
            status = "ONLY_P1"
            p1_status = "[green]✓[/]"
            p2_status = "[red]✗[/]"
            only_p1_count += 1
        else:
            semaphore = "🚧"
            status = "ONLY_P2"
            p1_status = "[red]✗[/]"
            p2_status = "[green]✓[/]"
            only_p2_count += 1
        
        row_style = ""
        if semaphore == "⛔":
            row_style = "red"
        elif semaphore == "🚧":
            row_style = "yellow"
        
        table.add_row(
            instance_name,
            p1_status,
            p2_status,
            status,
            semaphore,
            style=row_style
        )
    
    console.print(table)
    
    # Panel de resumen
    total = len(all_comparisons)
    summary_text = (
        f"[bold green]✅ OK: {ok_count}[/]  "
        f"[bold yellow]🚧 DIFFERS: {differs_count}[/]  "
        f"[bold red]⛔ MISMATCH: {mismatch_count}[/]  "
        f"[bold cyan]📌 Solo P1: {only_p1_count}[/]  "
        f"[bold blue]📌 Solo P2: {only_p2_count}[/]  "
        f"[dim]| Total: {total}[/]"
    )
    
    if mismatch_count > 0:
        overall = "[bold red]⛔ CRITICAL - Diferencias críticas detectadas[/]"
    elif differs_count > 0 or only_p1_count > 0 or only_p2_count > 0:
        overall = "[bold yellow]🚧 WARNING - Diferencias detectadas[/]"
    else:
        overall = "[bold green]✅ HEALTHY - Los proyectos son equivalentes[/]"
    
    console.print(Panel(
        f"{summary_text}\n\n{overall}",
        title="📊 Resumen Ejecutivo",
        border_style="blue",
        expand=False
    ))
    
    return {
        "ok": ok_count,
        "differs": differs_count,
        "mismatch": mismatch_count,
        "only_p1": only_p1_count,
        "only_p2": only_p2_count,
        "total": total
    }


def export_to_csv(data: Dict, filepath: str):
    """Exporta los datos a un archivo CSV"""
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Instance", "Attribute",
            "Project1_Value", "Project2_Value",
            "Check", "Status"
        ])
        
        attributes = ["edition", "type", "port", "public_ip", "private_ip"]
        
        for comp in data['comparisons']:
            instance_name = comp['instance_name']
            attrs1 = comp['attrs1']
            attrs2 = comp['attrs2']
            
            for attr in attributes:
                val1 = format_bool_value(attrs1.get(attr, "N/A"))
                val2 = format_bool_value(attrs2.get(attr, "N/A"))
                semaphore, status = compare_attribute(attr, attrs1.get(attr), attrs2.get(attr))
                
                writer.writerow([
                    instance_name, attr,
                    val1, val2,
                    semaphore, status
                ])


def export_to_json(data: Dict, filepath: str, tz_name: str = "America/Mazatlan"):
    """Exporta los datos a un archivo JSON con metadatos completos"""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    
    export_data = {
        "report_metadata": {
            "tool_name": "GCP Cloud SQL Comparator",
            "version": __version__,
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "projects": {
            "project1": data['project1'],
            "project2": data['project2']
        },
        "summary": data['summary'],
        "comparisons": data['comparisons']
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)


def print_execution_time(start_time: float, console, tz_name: str = "America/Mazatlan"):
    """Imprime el tiempo de ejecución del script"""
    end_time = time.time()
    duration = end_time - start_time
    
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)
    seconds = duration % 60
    
    tz = ZoneInfo(tz_name)
    start_dt = datetime.fromtimestamp(start_time, tz=tz)
    end_dt = datetime.fromtimestamp(end_time, tz=tz)
    
    time_parts = []
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    time_parts.append(f"{seconds:.2f}s")
    duration_str = " ".join(time_parts)
    
    time_table = Table(title="⏱️  Tiempo de Ejecución", title_style="bold cyan", border_style="dim")
    time_table.add_column("Métrica", style="white")
    time_table.add_column("Valor", style="green")
    time_table.add_row("🚀 Inicio", start_dt.strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})'))
    time_table.add_row("🏁 Fin", end_dt.strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})'))
    time_table.add_row("⏳ Duración", duration_str)
    
    console.print(f"\n")
    console.print(time_table)


def main():
    start_time = time.time()
    args = get_args()
    console = Console()
    
    if args.help:
        show_help()
        return
    
    tz_name = args.timezone
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        console.print(f"[red]⚠️ Zona horaria inválida: {tz_name}. Usando America/Mazatlan[/]")
        tz_name = "America/Mazatlan"
    
    revision_time = datetime.now(ZoneInfo(tz_name)).strftime(f'%Y-%m-%d %H:%M:%S ({tz_name})')
    
    # Header
    console.print(f"\n[bold blue]🔍 Cloud SQL Instance Comparator[/]")
    console.print(f"[dim]🕐 Fecha y hora de revisión: {revision_time}[/]")
    console.print(f"[dim]📌 Proyecto 1: {args.project1}[/]")
    console.print(f"[dim]📌 Proyecto 2: {args.project2}[/]")
    console.print()
    
    # Verificar conexión a ambos proyectos
    console.print(f"[dim]📡 Verificando acceso a proyecto 1...[/]")
    if not check_gcp_connection(args.project1, console, args.debug):
        print_execution_time(start_time, console, tz_name)
        return
    console.print(f"[dim]✅ Acceso verificado: {args.project1}[/]")
    
    console.print(f"[dim]📡 Verificando acceso a proyecto 2...[/]")
    if not check_gcp_connection(args.project2, console, args.debug):
        print_execution_time(start_time, console, tz_name)
        return
    console.print(f"[dim]✅ Acceso verificado: {args.project2}[/]")
    console.print()
    
    try:
        # Obtener todas las instancias de ambos proyectos
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Obteniendo instancias de {args.project1}...", total=None)
            instances1 = get_all_sql_instances(args.project1, args.debug)
            
            progress.update(task, description=f"Obteniendo instancias de {args.project2}...")
            instances2 = get_all_sql_instances(args.project2, args.debug)
        
        # Crear diccionarios por nombre de instancia
        instances1_dict = {inst.get("name"): inst for inst in instances1}
        instances2_dict = {inst.get("name"): inst for inst in instances2}
        
        # Filtrar por instancia específica si se proporcionó
        if args.instance:
            instances1_dict = {k: v for k, v in instances1_dict.items() if args.instance in k}
            instances2_dict = {k: v for k, v in instances2_dict.items() if args.instance in k}
        
        # Obtener todos los nombres únicos de instancias
        all_instance_names = sorted(set(list(instances1_dict.keys()) + list(instances2_dict.keys())))
        
        if not all_instance_names:
            console.print(f"[yellow]⚠️ No se encontraron instancias Cloud SQL en ninguno de los proyectos.[/]")
            print_execution_time(start_time, console, tz_name)
            return
        
        console.print(f"[dim]📊 Instancias encontradas: {len(instances1_dict)} en P1, {len(instances2_dict)} en P2[/]")
        console.print()
        
        # Mostrar lista de instancias por proyecto
        if instances1:
            print_instances_list(console, instances1, args.project1)
            console.print()
        
        if instances2:
            print_instances_list(console, instances2, args.project2)
            console.print()
        
        # Construir comparaciones
        all_comparisons = []
        for instance_name in all_instance_names:
            inst1 = instances1_dict.get(instance_name)
            inst2 = instances2_dict.get(instance_name)
            
            attrs1 = extract_instance_attributes(inst1) if inst1 else {"name": instance_name}
            attrs2 = extract_instance_attributes(inst2) if inst2 else {"name": instance_name}
            
            all_comparisons.append({
                "instance_name": instance_name,
                "in_project1": inst1 is not None,
                "in_project2": inst2 is not None,
                "attrs1": attrs1,
                "attrs2": attrs2
            })
        
        # Tabla comparativa de VERSIONES (siempre se muestra por defecto)
        print_version_comparison_table(console, all_comparisons, args.project1, args.project2)
        console.print()
        
        # Determinar si mostrar tablas adicionales de atributos
        show_all_attributes = getattr(args, 'all', False)
        selected_attributes = getattr(args, 'attributes', None)
        
        # Mostrar tablas adicionales solo si se solicita --all o --attributes
        if show_all_attributes or selected_attributes:
            # Filtrar solo instancias que existen en ambos proyectos para comparación detallada
            common_instances = [c for c in all_comparisons if c["in_project1"] and c["in_project2"]]
            
            if common_instances:
                # Si se especificaron atributos específicos, filtrar
                attrs_to_show = selected_attributes if selected_attributes else None
                print_comparison_table(console, common_instances, args.project1, args.project2, attrs_to_show)
                console.print()
            
            # Mostrar tabla resumen
            summary = print_summary_table(console, all_comparisons, args.project1, args.project2)
        else:
            # Solo versiones, resumen simplificado
            summary = {"version_only": True}
        
        # Exportar si se solicitó
        if args.output:
            export_data = {
                'project1': args.project1,
                'project2': args.project2,
                'comparisons': all_comparisons,
                'summary': summary
            }
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            outcome_dir = os.path.join(script_dir, 'outcome')
            os.makedirs(outcome_dir, exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"sql_compare_{timestamp}"
            
            if args.output == 'csv':
                filepath = os.path.join(outcome_dir, f"{filename}.csv")
                export_to_csv(export_data, filepath)
            elif args.output == 'json':
                filepath = os.path.join(outcome_dir, f"{filename}.json")
                export_to_json(export_data, filepath, tz_name)
            
            console.print(f"\n[bold green]📁 Archivo exportado:[/] {filepath}")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error ejecutando comparación:[/]\n{e}")
        if args.debug:
            import traceback
            traceback.print_exc()
    
    print_execution_time(start_time, console, tz_name)


if __name__ == "__main__":
    main()
