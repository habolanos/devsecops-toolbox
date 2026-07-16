"""
Integración de Pub/Sub Monitor en GCP Tools

Proporciona acceso a las herramientas de monitoreo de Pub/Sub
desde el launcher principal de GCP.
"""

import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_pubsub_monitor():
    """Ejecuta el monitor de Pub/Sub."""
    from .pubsub_monitor import PubSubMonitor

    config_path = "scm/config.json"

    try:
        monitor = PubSubMonitor(config_path)
        monitor.run_interactive_menu()
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        sys.exit(1)


def display_pubsub_menu():
    """Muestra menú de Pub/Sub Monitor."""
    console.print(Panel(
        "[bold cyan]📨 Google Cloud Pub/Sub Monitor[/bold cyan]",
        style="blue"
    ))

    menu_table = Table(show_header=False)
    menu_table.add_row("[cyan][1][/cyan]", "Análisis Completo")
    menu_table.add_row("[cyan][2][/cyan]", "Análisis de Proyecto")
    menu_table.add_row("[cyan][3][/cyan]", "Evaluar Alertas")
    menu_table.add_row("[cyan][4][/cyan]", "Generar Reportes")
    menu_table.add_row("[cyan][5][/cyan]", "Ver Configuración")
    menu_table.add_row("[cyan][Q][/cyan]", "Volver")

    console.print(menu_table)


if __name__ == "__main__":
    run_pubsub_monitor()
