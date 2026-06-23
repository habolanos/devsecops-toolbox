#!/usr/bin/env python3
"""
Wrapper para ejecutar Dashboard desde el launcher
Ejecuta todas las herramientas AZDO necesarias y consolida datos
"""

import sys
import subprocess
import argparse
import json
import os
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

# Número de workers paralelos (ajusta según tu máquina)
MAX_WORKERS = 4

# Cargar configuración
def load_config():
    """Carga config.json si existe"""
    config_path = Path(__file__).parent.parent / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            if RICH_AVAILABLE and console:
                console.print(f"[yellow]⚠️ Error cargando config.json: {e}[/yellow]")
            else:
                print(f"⚠️ Error cargando config.json: {e}")
    return {}

# Obtener directorio de salida desde config
def get_output_dir():
    """Obtiene directorio de salida desde config.json o usa default"""
    config = load_config()
    
    # Intentar obtener de dashboard.output.directory
    dashboard_output = config.get("dashboard", {}).get("output", {}).get("directory")
    if dashboard_output:
        return dashboard_output
    
    # Intentar obtener de global.output_dir
    global_output = config.get("global", {}).get("output_dir")
    if global_output:
        return f"{global_output}/dashboard"
    
    # Default
    return "outcome/dashboard"

OUTPUT_DIR = get_output_dir()

def execute_azdo_tools(org, project, pat):
    """Ejecuta opción B (Ejecutar Todo + JSON) de azdo/tools.py"""
    azdo_tools_path = Path(__file__).parent.parent / "azdo" / "tools.py"
    
    if not azdo_tools_path.exists():
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ No se encontró: {azdo_tools_path}[/red]")
        else:
            print(f"❌ No se encontró: {azdo_tools_path}")
        return False
    
    if RICH_AVAILABLE and console:
        console.print()
        console.print("[bold cyan]Paso 1:[/bold cyan] [white]Ejecutando todas las herramientas AZDO con JSON...[/white]")
        console.print()
    else:
        print(f"\n🚀 Paso 1: Ejecutando todas las herramientas AZDO con JSON...")
    
    # Ejecutar opción B: Ejecutar Todo + JSON
    cmd = [
        sys.executable,
        str(azdo_tools_path),
        "--option", "B",
        "--org", org,
        "--project", project,
        "--pat", pat
    ]
    
    try:
        if RICH_AVAILABLE and console:
            console.print(f"[dim]Ejecutando: {' '.join(cmd[:3])} ... (esto puede tardar varios minutos)[/dim]\n")
        else:
            print(f"Ejecutando: {' '.join(cmd[:3])} ... (esto puede tardar varios minutos)\n")
        
        # Preparar variables de entorno
        env = os.environ.copy()
        
        # Pasar OUTPUT_DIR como variable de entorno para que azdo/tools.py lo use
        # Convertir a ruta absoluta si es relativa
        output_path = Path(OUTPUT_DIR)
        if not output_path.is_absolute():
            output_path = Path(__file__).parent.parent / OUTPUT_DIR
        
        env["DEVSECOPS_OUTPUT_DIR"] = str(output_path)
        
        if RICH_AVAILABLE and console:
            console.print(f"[dim]Directorio de salida: {env['DEVSECOPS_OUTPUT_DIR']}[/dim]")
        
        # Ejecutar sin capturar salida para que el usuario vea el progreso
        result = subprocess.run(cmd, timeout=3600, env=env)  # 1 hora de timeout
        
        if result.returncode == 0:
            if RICH_AVAILABLE and console:
                console.print()
                console.print("[green]✅ Todas las herramientas ejecutadas exitosamente[/green]")
            else:
                print(f"\n✅ Todas las herramientas ejecutadas exitosamente")
            return True
        else:
            if RICH_AVAILABLE and console:
                console.print(f"\n[yellow]⚠️ Algunas herramientas retornaron código: {result.returncode}[/yellow]")
            else:
                print(f"\n⚠️ Algunas herramientas retornaron código: {result.returncode}")
            return True  # Continuar aunque haya errores
            
    except subprocess.TimeoutExpired:
        if RICH_AVAILABLE and console:
            console.print(f"\n[red]❌ Tiempo excedido (3600s)[/red]")
        else:
            print(f"\n❌ Tiempo excedido (3600s)")
        return False
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"\n[red]❌ Error: {str(e)}[/red]")
        else:
            print(f"\n❌ Error: {str(e)}")
        return False

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Dashboard Matutino DevSecOps')
    parser.add_argument('--org', required=True, help='Organización Azure DevOps')
    parser.add_argument('--project', required=True, help='Proyecto Azure DevOps')
    parser.add_argument('--pat', required=True, help='Personal Access Token')
    parser.add_argument('--webhook', default='', help='Webhook Teams (opcional)')
    
    args = parser.parse_args()
    
    # Header
    if RICH_AVAILABLE and console:
        console.print()
        header_text = Text("📈 Dashboard Matutino DevSecOps", justify="center", style="bold cyan")
        console.print(Panel(header_text, border_style="cyan", expand=False))
        
        # Parámetros
        params_table = Table(title="⚙️ Parámetros", show_header=False, box=None)
        params_table.add_row("Organización:", f"[cyan]{args.org}[/cyan]")
        params_table.add_row("Proyecto:", f"[cyan]{args.project}[/cyan]")
        params_table.add_row("PAT:", f"[green]Configurado[/green]" if args.pat else "[red]No configurado[/red]")
        params_table.add_row("Webhook:", f"[green]Configurado[/green]" if args.webhook else "[yellow]No configurado[/yellow]")
        console.print(params_table)
    else:
        print("\n" + "=" * 60)
        print("📈 Dashboard Matutino DevSecOps")
        print("=" * 60)
        print(f"\n✅ Parámetros recibidos:")
        print(f"   Organización: {args.org}")
        print(f"   Proyecto: {args.project}")
        print(f"   PAT: {'Configurado' if args.pat else 'No configurado'}")
        print(f"   Webhook: {'Configurado' if args.webhook else 'No configurado'}")
    
    # Paso 1: Ejecutar todas las herramientas AZDO
    if RICH_AVAILABLE and console:
        console.print()
        console.print("[bold cyan]Paso 1:[/bold cyan] [white]Ejecutando herramientas AZDO para generar reportes...[/white]")
    else:
        print(f"\n🚀 Paso 1: Ejecutando herramientas AZDO para generar reportes...")
    
    if not execute_azdo_tools(args.org, args.project, args.pat):
        if RICH_AVAILABLE and console:
            console.print("[yellow]⚠️ Algunas herramientas fallaron, continuando...[/yellow]")
        else:
            print(f"⚠️ Algunas herramientas fallaron, continuando...")
    
    if RICH_AVAILABLE and console:
        console.print(f"[green]✅ Reportes generados en {OUTPUT_DIR}[/green]")
    else:
        print(f"\n✅ Reportes generados en {OUTPUT_DIR}")
    
    # Importar y ejecutar consolidator
    try:
        from dashboard_consolidator import DashboardConsolidator
        
        # Paso 2: Consolidación
        if RICH_AVAILABLE and console:
            console.print()
            console.print("[bold cyan]Paso 2:[/bold cyan] [white]Consolidando datos...[/white]")
        else:
            print(f"\n🚀 Paso 2: Consolidando datos...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console if RICH_AVAILABLE else None,
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Consolidando...", total=None)
            
            consolidator = DashboardConsolidator(
                org=args.org,
                project=args.project,
                pat=args.pat,
                output_dir=OUTPUT_DIR
            )
            
            dashboard_data = consolidator.run()
            progress.stop()
        
        # Mostrar resultados
        if RICH_AVAILABLE and console:
            console.print()
            metrics_table = Table(title="📊 Métricas Consolidadas", show_header=False, box=None)
            metrics_table.add_row("Health Score:", f"[cyan]{dashboard_data['summary']['health_score']}/100[/cyan]")
            metrics_table.add_row("Code Coverage:", f"[cyan]{dashboard_data['summary']['code_coverage']}%[/cyan]")
            metrics_table.add_row("Branch Compliance:", f"[cyan]{dashboard_data['summary']['branch_compliance']}%[/cyan]")
            console.print(metrics_table)
        else:
            print(f"\n✅ Dashboard consolidado exitosamente")
            print(f"   Health Score: {dashboard_data['summary']['health_score']}/100")
            print(f"   Code Coverage: {dashboard_data['summary']['code_coverage']}%")
            print(f"   Branch Compliance: {dashboard_data['summary']['branch_compliance']}%")
        
        # Paso 3: Generar HTML
        if RICH_AVAILABLE and console:
            console.print()
            console.print("[bold cyan]Paso 3:[/bold cyan] [white]Generando HTML...[/white]")
        else:
            print(f"\n📊 Paso 3: Generando HTML...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console if RICH_AVAILABLE else None,
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Generando HTML...", total=None)
            
            from dashboard_generator import DashboardGenerator
            
            generator = DashboardGenerator(
                input_file=f'{OUTPUT_DIR}/dashboard_data.json',
                output_file=f'{OUTPUT_DIR}/dashboard.html'
            )
            generator.generate()
            progress.stop()
        
        if RICH_AVAILABLE and console:
            console.print(f"[green]✅ Dashboard HTML generado: {OUTPUT_DIR}/dashboard.html[/green]")
        else:
            print(f"✅ Dashboard HTML generado: {OUTPUT_DIR}/dashboard.html")
        
        # Paso 4: Notificar a Teams si hay webhook
        if args.webhook and args.webhook != "<TU_TEAMS_WEBHOOK_URL>":
            if RICH_AVAILABLE and console:
                console.print()
                console.print("[bold cyan]Paso 4:[/bold cyan] [white]Enviando notificación a Teams...[/white]")
            else:
                print(f"\n📢 Paso 4: Enviando notificación a Teams...")
            
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console if RICH_AVAILABLE else None,
                    transient=True
                ) as progress:
                    task = progress.add_task("[cyan]Enviando...", total=None)
                    
                    from dashboard_scheduler import TeamsNotifier
                    notifier = TeamsNotifier(webhook_url=args.webhook)
                    notifier.send_notification(dashboard_data)
                    progress.stop()
                
                if RICH_AVAILABLE and console:
                    console.print("[green]✅ Notificación enviada a Teams[/green]")
                else:
                    print(f"✅ Notificación enviada a Teams")
            except Exception as e:
                if RICH_AVAILABLE and console:
                    console.print(f"[yellow]⚠️ No se pudo enviar notificación: {e}[/yellow]")
                else:
                    print(f"⚠️ No se pudo enviar notificación: {e}")
        
        # Resumen final
        if RICH_AVAILABLE and console:
            console.print()
            final_text = Text("✅ Dashboard ejecutado exitosamente", justify="center", style="bold green")
            console.print(Panel(final_text, border_style="green", expand=False))
            
            summary_table = Table(title="📁 Archivos Generados", show_header=False, box=None)
            summary_table.add_row("Datos:", f"[cyan]{OUTPUT_DIR}/dashboard_data.json[/cyan]")
            summary_table.add_row("HTML:", f"[cyan]{OUTPUT_DIR}/dashboard.html[/cyan]")
            summary_table.add_row("Histórico:", f"[cyan]{OUTPUT_DIR}/history/[/cyan]")
            console.print(summary_table)
        else:
            print("\n" + "=" * 60)
            print("✅ Dashboard ejecutado exitosamente")
            print("=" * 60)
            print("Archivos generados:")
            print(f"  - {OUTPUT_DIR}/dashboard_data.json")
            print(f"  - {OUTPUT_DIR}/dashboard.html")
            print(f"  - {OUTPUT_DIR}/history/")
        
        return 0
        
    except ImportError as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ Error de importación: {e}[/red]")
            console.print(f"[yellow]   Asegúrate de que los módulos están en el mismo directorio[/yellow]")
        else:
            print(f"\n❌ Error de importación: {e}")
            print(f"   Asegúrate de que los módulos están en el mismo directorio")
        return 1
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]❌ Error: {str(e)}[/red]")
        else:
            print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = main()
    # No usar sys.exit() para permitir que el launcher continúe
    # sys.exit(exit_code)
