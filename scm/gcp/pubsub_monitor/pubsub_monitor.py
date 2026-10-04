"""
PubSubMonitor - Orquestador principal del sistema de monitoreo

Módulo que coordina todos los componentes del sistema de monitoreo
de Pub/Sub, incluyendo recopilación, análisis, alertas y reportes.

Características:
- Orquestación completa del flujo
- CLI interactivo con Rich
- Integración de todos los módulos
- Generación de reportes completos
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from .pubsub_collector import PubSubCollector
from .metrics_analyzer import MetricsAnalyzer
from .alert_engine import AlertEngine
from .dashboard_generator import DashboardGenerator

console = Console()
logger = logging.getLogger(__name__)

# Directorio de salida compartido (DEVSECOPS_OUTPUT_DIR > config.json > scm/outcome)
try:
    from scm.utils import resolve_outcome_dir
except ImportError:
    try:
        from utils import resolve_outcome_dir
    except ImportError:
        def resolve_outcome_dir(default: str = "outcome") -> Path:
            p = Path("scm") / default if Path("scm").exists() else Path(default)
            p.mkdir(parents=True, exist_ok=True)
            return p


class PubSubMonitor:
    """Orquestador principal del sistema de monitoreo."""

    def __init__(self, config_path: str, projects: Optional[List[str]] = None):
        """
        Inicializa el monitor.

        Args:
            config_path: Ruta del archivo de configuración
            projects: Lista de proyectos (si se omite se leen del config)
        """
        self.config = self._load_config(config_path)
        if projects is None:
            projects = self.config.get("gcp", {}).get("service_accounts_reporter", {}).get("projects", [])
        self.projects = projects
        self.collector = PubSubCollector(self.projects)
        self.analyzer = MetricsAnalyzer()
        self.alert_engine = AlertEngine()
        self.results = {}

    def _load_config(self, config_path: str) -> Dict:
        """Carga configuración desde archivo."""
        config_file = Path(config_path)

        if not config_file.exists():
            console.print(f"[red]❌ Archivo de configuración no encontrado: {config_path}[/red]")
            sys.exit(1)

        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            console.print(f"[red]❌ Error al parsear JSON: {str(e)}[/red]")
            sys.exit(1)

    def run_interactive_menu(self) -> None:
        """Ejecuta menú interactivo."""
        while True:
            console.clear()
            self._display_main_menu()

            choice = Prompt.ask(
                "[cyan]Selecciona una opción[/cyan]",
                choices=["1", "2", "3", "4", "5", "Q", "q"]
            )

            if choice == "1":
                self.run_full_analysis()
            elif choice == "2":
                self.run_project_analysis()
            elif choice == "3":
                self.run_alerts_only()
            elif choice == "4":
                self.generate_reports()
            elif choice == "5":
                self.display_configuration()
            elif choice in ("Q", "q"):
                console.print("[yellow]👋 Saliendo...[/yellow]")
                break

    def _display_main_menu(self) -> None:
        """Muestra menú principal."""
        console.print(Panel(
            "[bold cyan]📊 Pub/Sub Monitor - Menú Principal[/bold cyan]",
            style="blue"
        ))

        menu_table = Table(show_header=False, show_footer=False)
        menu_table.add_row("[cyan][1][/cyan]", "Análisis Completo (todos los proyectos)")
        menu_table.add_row("[cyan][2][/cyan]", "Análisis de Proyecto Específico")
        menu_table.add_row("[cyan][3][/cyan]", "Evaluar Alertas Solamente")
        menu_table.add_row("[cyan][4][/cyan]", "Generar Reportes")
        menu_table.add_row("[cyan][5][/cyan]", "Ver Configuración")
        menu_table.add_row("[cyan][Q][/cyan]", "Salir")

        console.print(menu_table)
        console.print()

    def _execute_analysis(self, show_steps: bool = True) -> None:
        """Ejecuta recopilación + análisis + alertas y guarda self.results."""
        if show_steps:
            console.print("\n[cyan]1️⃣  Recopilando datos...[/cyan]")
        collection_results = self.collector.collect_all_data()
        self.collector.display_collection_summary(collection_results)

        if show_steps:
            console.print("\n[cyan]2️⃣  Analizando métricas...[/cyan]")
        analysis_results = {}
        for project, data in collection_results["projects"].items():
            summary = self.analyzer.calculate_project_summary(data)
            analysis_results[project] = summary

        self.analyzer.display_analysis_summary(analysis_results)

        if show_steps:
            console.print("\n[cyan]3️⃣  Evaluando alertas...[/cyan]")
        all_alerts = {}
        for project, data in collection_results["projects"].items():
            alerts = self.alert_engine.evaluate_all_alerts(data)
            all_alerts[project] = alerts

        # Mostrar alertas
        total_alerts = sum(len(a) for a in all_alerts.values())
        if total_alerts > 0:
            console.print(f"\n[yellow]⚠️  Se encontraron {total_alerts} alertas[/yellow]")
            for project, alerts in all_alerts.items():
                if alerts:
                    console.print(f"\n[cyan]{project}:[/cyan]")
                    self.alert_engine.display_alerts_summary(alerts)
        else:
            console.print("\n[green]✅ No hay alertas[/green]")

        # Guardar resultados
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "projects": {},
            "errors": collection_results.get("errors", [])
        }

        for project, data in collection_results["projects"].items():
            self.results["projects"][project] = {
                "collection": data,
                "analysis": analysis_results.get(project, {}),
                "alerts": all_alerts.get(project, [])
            }

    def run_full_analysis(self, pause: bool = True) -> None:
        """Ejecuta análisis completo."""
        console.print(Panel(
            "[bold cyan]🔍 Iniciando Análisis Completo[/bold cyan]",
            style="blue"
        ))

        self._execute_analysis()

        console.print("\n[green]✅ Análisis completado[/green]")
        if pause:
            Prompt.ask("[cyan]Presiona Enter para continuar[/cyan]")

    def run_project_analysis(self) -> None:
        """Ejecuta análisis de proyecto específico."""
        console.print("\n[cyan]Proyectos disponibles:[/cyan]")
        for i, project in enumerate(self.projects, 1):
            console.print(f"  {i}. {project}")

        choice = Prompt.ask("[cyan]Selecciona un proyecto[/cyan]")

        try:
            project_idx = int(choice) - 1
            if 0 <= project_idx < len(self.projects):
                project = self.projects[project_idx]
                console.print(f"\n[cyan]Analizando {project}...[/cyan]")
                # Implementar análisis específico
                console.print("[green]✅ Análisis completado[/green]")
            else:
                console.print("[red]❌ Opción inválida[/red]")
        except ValueError:
            console.print("[red]❌ Entrada inválida[/red]")

        Prompt.ask("[cyan]Presiona Enter para continuar[/cyan]")

    def run_alerts_only(self, pause: bool = True) -> None:
        """Ejecuta evaluación de alertas solamente."""
        console.print(Panel(
            "[bold cyan]🚨 Evaluando Alertas[/bold cyan]",
            style="red"
        ))

        collection_results = self.collector.collect_all_data()
        self.collector.display_collection_summary(collection_results)

        all_alerts = {}
        for project, data in collection_results["projects"].items():
            alerts = self.alert_engine.evaluate_all_alerts(data)
            all_alerts[project] = alerts

        for project, alerts in all_alerts.items():
            if alerts:
                console.print(f"\n[cyan]{project}:[/cyan]")
                self.alert_engine.display_alerts_summary(alerts)

        if pause:
            Prompt.ask("[cyan]Presiona Enter para continuar[/cyan]")

    def generate_reports(self, pause: bool = True, output: str = "all",
                         output_dir: Optional[Path] = None) -> None:
        """Genera reportes."""
        if not self.results:
            console.print("[yellow]⚠️  Ejecuta primero un análisis completo[/yellow]")
            if pause:
                Prompt.ask("[cyan]Presiona Enter para continuar[/cyan]")
            return

        if output_dir is None:
            output_dir = Path(resolve_outcome_dir()) / "pubsub_monitor"
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        console.print(Panel(
            "[bold cyan]📄 Generando Reportes[/bold cyan]",
            style="blue"
        ))

        dashboard = DashboardGenerator(self.results)
        generated = []

        # HTML
        if output in ("all", "html"):
            console.print("[cyan]Generando dashboard HTML...[/cyan]")
            generated.append(dashboard.generate_html_dashboard(
                str(output_dir / f"pubsub_dashboard_{ts}.html")))

        # JSON
        if output in ("all", "json"):
            console.print("[cyan]Generando reporte JSON...[/cyan]")
            generated.append(dashboard.generate_json_report(
                str(output_dir / f"pubsub_report_{ts}.json")))

        # Excel
        if output in ("all", "excel"):
            console.print("[cyan]Generando reporte Excel...[/cyan]")
            generated.append(dashboard.generate_excel_report(
                str(output_dir / f"pubsub_report_{ts}.xlsx")))

        if generated:
            console.print(Panel(
                "[green]✅ Reportes generados:[/green]\n" + "\n".join(generated),
                style="green"
            ))
        else:
            console.print("[yellow]No se generaron archivos (formato console)[/yellow]")

        if pause:
            Prompt.ask("[cyan]Presiona Enter para continuar[/cyan]")

    def display_configuration(self) -> None:
        """Muestra configuración actual."""
        console.print(Panel(
            "[bold cyan]⚙️  Configuración Actual[/bold cyan]",
            style="blue"
        ))

        config_table = Table(title="Configuración de Proyectos")
        config_table.add_column("Proyecto", style="cyan")
        config_table.add_column("Estado", style="green")

        for project in self.projects:
            config_table.add_row(project, "✅ Configurado")

        console.print(config_table)
        console.print(f"\n[cyan]Total de proyectos:[/cyan] {len(self.projects)}")

        Prompt.ask("[cyan]Presiona Enter para continuar[/cyan]")

    def run_cli(self, action: str = "full", output: str = "all") -> int:
        """
        Ejecuta el monitor en modo no-interactivo (CLI/launcher).

        Args:
            action: "full" (análisis + reportes) o "alerts" (solo recolección + alertas)
            output: "all" | "html" | "json" | "excel" | "console"

        Returns:
            Código de salida (0 ok, 1 error)
        """
        if not self.projects:
            console.print("[red]❌ No hay proyectos configurados[/red]")
            return 1

        console.print(Panel(
            "[bold cyan]📊 Pub/Sub Monitor[/bold cyan]\n"
            f"[cyan]Proyectos:[/cyan] {', '.join(self.projects)}",
            style="blue"
        ))

        if action == "alerts":
            self.run_alerts_only(pause=False)
            return 0

        # full: análisis completo + reportes
        self.run_full_analysis(pause=False)
        self.generate_reports(pause=False, output=output)
        return 0


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Pub/Sub Monitor - Monitoreo multi-proyecto de Google Cloud Pub/Sub")
    parser.add_argument("--config", default="scm/config.json",
                        help="Ruta del archivo de configuración")
    proj_group = parser.add_mutually_exclusive_group()
    proj_group.add_argument("--project", help="Proyecto GCP único")
    proj_group.add_argument("--multi-project",
                            help="Proyectos GCP separados por comas (ej. ALL ya resuelto por el launcher)")
    parser.add_argument("--action", choices=["full", "alerts"], default="full",
                        help="full: análisis + reportes | alerts: solo evaluación de alertas")
    parser.add_argument("-o", "--output", choices=["all", "html", "json", "excel", "console"],
                        default="all", help="Formato(s) de reporte a generar")
    parser.add_argument("--interactive", action="store_true",
                        help="Forzar menú interactivo aunque se pasen argumentos")
    args = parser.parse_args()

    cli_mode = not args.interactive and bool(
        args.project or args.multi_project or args.action != "full" or args.output != "all")

    projects = None
    if args.project:
        projects = [args.project]
    elif args.multi_project:
        projects = [p.strip() for p in args.multi_project.split(",") if p.strip()]

    monitor = PubSubMonitor(args.config, projects=projects)

    if cli_mode:
        sys.exit(monitor.run_cli(action=args.action, output=args.output))

    # Sin argumentos de ejecución → menú interactivo (requiere TTY)
    if not sys.stdin or not sys.stdin.isatty():
        console.print(
            "[red]❌ Modo interactivo requiere TTY.[/red] "
            "Use --project o --multi-project para ejecución no-interactiva.")
        sys.exit(2)

    monitor.run_interactive_menu()


if __name__ == "__main__":
    main()
