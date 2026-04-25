#!/usr/bin/env python3
"""
GKE Node Resources Monitor v1.0.0
Muestra estado de recursos (CPU, memoria) por nodo en cada cluster GKE.
Solo lectura — no modifica ningún recurso.

Uso:
    python gke_node_monitor.py
    python gke_node_monitor.py --project mi-proyecto-id

Autor: Harold Adrian (migrado desde Comercial/scripts/3.py)
"""

import subprocess
import json
import sys
import argparse
import time
from datetime import datetime
from typing import Optional

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
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("⚠️  Rich no instalado. Ejecuta: pip install rich")
    sys.exit(1)

console = Console()
VERSION = "1.0.0"


def run_cmd(cmd: list[str]) -> tuple[str, str, int]:
    """Ejecuta un comando y retorna (stdout, stderr, returncode)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def run_json(cmd: list[str]) -> Optional[dict | list]:
    """Ejecuta un comando que retorna JSON; retorna None si falla."""
    stdout, stderr, rc = run_cmd(cmd)
    if rc != 0:
        console.print(f"  ⚠️  Error: {stderr[:200]}", style="red")
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        console.print(f"  ⚠️  JSON inválido: {stdout[:200]}", style="red")
        return None


def pct_color(value_str: str) -> str:
    """Retorna el color Rich según el porcentaje."""
    try:
        val = float(value_str.replace("%", ""))
        if val > 80:
            return "red"
        elif val > 50:
            return "yellow"
        else:
            return "green"
    except (ValueError, TypeError):
        return "white"


def pct_float(value_str: str) -> float:
    """Extrae float de un string de porcentaje."""
    try:
        return float(value_str.replace("%", ""))
    except (ValueError, TypeError):
        return 0.0


def get_cluster_list(project: Optional[str] = None) -> list[dict]:
    """Lista todos los clusters GKE del proyecto."""
    cmd = ["gcloud", "container", "clusters", "list", "--format=json"]
    if project:
        cmd += ["--project", project]
    data = run_json(cmd)
    return data if data else []


def get_credentials(cluster_name: str, location: str, project: Optional[str] = None) -> bool:
    """Obtiene credenciales kubectl para un cluster."""
    cmd = [
        "gcloud", "container", "clusters", "get-credentials",
        cluster_name, "--zone", location, "--quiet"
    ]
    if project:
        cmd += ["--project", project]
    _, stderr, rc = run_cmd(cmd)
    if rc != 0:
        console.print(f"  ⚠️  No se pudieron obtener credenciales: {stderr[:150]}", style="red")
    return rc == 0


def get_nodes_resources(context: str) -> list[dict]:
    """Retorna CPU y memoria de cada nodo."""
    cmd_info = [
        "kubectl", "get", "nodes", "--context", context,
        "-o", "jsonpath={range .items[*]}{.metadata.name}{'|'}"
        "{.status.allocatable.cpu}{'|'}"
        "{.status.allocatable.memory}{'|'}"
        "{.status.allocatable.pods}{'|'}"
        "{.metadata.labels.topology\\.kubernetes\\.io/zone}{'\\n'}{end}"
    ]
    stdout_info, _, rc_info = run_cmd(cmd_info)

    cmd_top = ["kubectl", "top", "nodes", "--context", context, "--no-headers"]
    stdout_top, _, rc_top = run_cmd(cmd_top)

    node_info = {}
    if rc_info == 0:
        for line in stdout_info.splitlines():
            parts = line.split("|")
            if len(parts) >= 5:
                name = parts[0].strip()
                node_info[name] = {
                    "name":       name,
                    "cpu_alloc":  parts[1].strip(),
                    "mem_alloc":  parts[2].strip(),
                    "pods_max":   parts[3].strip(),
                    "zone":       parts[4].strip(),
                    "cpu_used":   "N/A",
                    "cpu_pct":    "N/A",
                    "mem_used":   "N/A",
                    "mem_pct":    "N/A",
                }

    if rc_top == 0:
        for line in stdout_top.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                name = parts[0]
                if name in node_info:
                    node_info[name]["cpu_used"] = parts[1]
                    node_info[name]["cpu_pct"]  = parts[2]
                    node_info[name]["mem_used"] = parts[3]
                    node_info[name]["mem_pct"]  = parts[4]

    return list(node_info.values())


def show_summary_table(cluster_name: str, nodes: list[dict]):
    """Muestra tabla resumen de nodos."""
    table = Table(
        title=f"Recursos por Nodo — {cluster_name}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white on dark_blue",
        border_style="grey50",
        padding=(0, 1),
    )

    table.add_column("Nodo",        style="bold", min_width=20)
    table.add_column("Zona",        style="dim",  min_width=12)
    table.add_column("CPU Total",   style="white", justify="right", min_width=8)
    table.add_column("CPU Uso",     style="white", justify="right", min_width=8)
    table.add_column("CPU %",       style="white", justify="right", min_width=6)
    table.add_column("Mem Total",   style="white", justify="right", min_width=10)
    table.add_column("Mem Uso",     style="white", justify="right", min_width=10)
    table.add_column("Mem %",       style="white", justify="right", min_width=6)
    table.add_column("Pods",        style="white", justify="right", min_width=5)

    for n in nodes:
        cpu_color = pct_color(n.get("cpu_pct", "0%"))
        mem_color = pct_color(n.get("mem_pct", "0%"))

        table.add_row(
            n["name"],
            n["zone"],
            n["cpu_alloc"],
            n["cpu_used"],
            Text(n["cpu_pct"], style=cpu_color),
            n["mem_alloc"],
            n["mem_used"],
            Text(n["mem_pct"], style=mem_color),
            n["pods_max"],
        )

    console.print(table)
    console.print()


def generate_html(project: Optional[str], all_data: list[tuple[str, list[dict]]]) -> str:
    """Genera reporte HTML con los datos de todos los clusters."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    project_str = project or "(gcloud config)"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GKE Node Resources Monitor</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 24px; }}
        .header p {{ margin: 0; opacity: 0.9; font-size: 14px; }}
        .cluster {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .cluster h2 {{
            margin: 0 0 15px 0;
            color: #333;
            font-size: 18px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 8px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .cpu-high {{ color: #dc3545; font-weight: bold; }}
        .cpu-med {{ color: #ffc107; font-weight: bold; }}
        .cpu-low {{ color: #28a745; font-weight: bold; }}
        .mem-high {{ color: #dc3545; font-weight: bold; }}
        .mem-med {{ color: #ffc107; font-weight: bold; }}
        .mem-low {{ color: #28a745; font-weight: bold; }}
        .no-data {{
            text-align: center;
            color: #6c757d;
            font-style: italic;
            padding: 40px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>☸️ GKE Node Resources Monitor</h1>
        <p>Proyecto: <strong>{project_str}</strong> | Generado: {timestamp}</p>
    </div>
"""

    for cluster_name, nodes in all_data:
        html += f'    <div class="cluster">\n        <h2>Cluster: {cluster_name}</h2>\n'

        if not nodes:
            html += '        <p class="no-data">No se pudieron obtener datos de este cluster</p>\n'
        else:
            html += """        <table>
            <thead>
                <tr>
                    <th>Nodo</th>
                    <th>Zona</th>
                    <th>CPU Total</th>
                    <th>CPU Uso</th>
                    <th>CPU %</th>
                    <th>Mem Total</th>
                    <th>Mem Uso</th>
                    <th>Mem %</th>
                    <th>Pods Max</th>
                </tr>
            </thead>
            <tbody>
"""
            for n in nodes:
                cpu_class = "cpu-low"
                mem_class = "mem-low"
                try:
                    cpu_val = float(n.get("cpu_pct", "0%").replace("%", ""))
                    mem_val = float(n.get("mem_pct", "0%").replace("%", ""))
                    if cpu_val > 80: cpu_class = "cpu-high"
                    elif cpu_val > 50: cpu_class = "cpu-med"
                    if mem_val > 80: mem_class = "mem-high"
                    elif mem_val > 50: mem_class = "mem-med"
                except:
                    pass

                html += f"""                <tr>
                    <td><strong>{n['name']}</strong></td>
                    <td>{n['zone']}</td>
                    <td>{n['cpu_alloc']}</td>
                    <td>{n['cpu_used']}</td>
                    <td class="{cpu_class}">{n['cpu_pct']}</td>
                    <td>{n['mem_alloc']}</td>
                    <td>{n['mem_used']}</td>
                    <td class="{mem_class}">{n['mem_pct']}</td>
                    <td>{n['pods_max']}</td>
                </tr>
"""
            html += "            </tbody>\n        </table>\n"

        html += "    </div>\n"

    html += """</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(
        description="GKE Node Resources Monitor - Uso de CPU y memoria por nodo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python gke_node_monitor.py
  python gke_node_monitor.py --project my-gcp-project
  python gke_node_monitor.py --project my-gcp-project --output html
        """
    )
    parser.add_argument("--project", "-p", help="GCP Project ID (usa el activo si no se especifica)")
    parser.add_argument("--output", "-o", choices=["console", "html"], default="html",
                       help="Formato de salida (default: html)")
    parser.add_argument("--html-file", default="gke_node_resources.html",
                       help="Nombre del archivo HTML (default: gke_node_resources.html)")
    args = parser.parse_args()

    console.print(Panel(
        f"[bold cyan]GKE Node Resources Monitor v{VERSION}[/]\n"
        f"Proyecto GCP: {args.project or '(configuración activa)'}",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()

    clusters = get_cluster_list(args.project)
    if not clusters:
        console.print("[red]❌ No se encontraron clusters GKE en este proyecto.[/]")
        sys.exit(1)

    console.print(f"[green]✅ {len(clusters)} cluster(s) encontrado(s)[/]\n")

    all_data: list[tuple[str, list[dict]]] = []

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        for c in clusters:
            name = c.get("name", "unknown")
            location = c.get("zone") or c.get("location", "unknown")

            task = progress.add_task(f"Analizando {name}...", total=None)

            if not get_credentials(name, location, args.project):
                all_data.append((name, []))
                continue

            nodes = get_nodes_resources(name)
            all_data.append((name, nodes))

            progress.update(task, description=f"✅ {name} - {len(nodes)} nodos")
            time.sleep(0.3)

    if args.output == "html":
        html_content = generate_html(args.project, all_data)
        with open(args.html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        console.print(f"\n[green]✅ Reporte HTML guardado: {args.html_file}[/]")

        # Mostrar también en consola
        for cluster_name, nodes in all_data:
            show_summary_table(cluster_name, nodes)
    else:
        for cluster_name, nodes in all_data:
            show_summary_table(cluster_name, nodes)

    console.input("[dim]Presione Enter para continuar...[/]")


if __name__ == "__main__":
    main()
