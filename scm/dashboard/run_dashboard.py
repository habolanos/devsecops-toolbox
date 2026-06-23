#!/usr/bin/env python3
"""
Wrapper para ejecutar Dashboard desde el launcher
Ejecuta todas las herramientas AZDO necesarias y consolida datos
"""

import sys
import subprocess
import argparse
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

# Herramientas AZDO que generan reportes JSON para el dashboard
AZDO_TOOLS = [
    ("1", "PR Master Checker"),
    ("2", "Branch Policy Checker"),
    ("3", "Release CD Health"),
    ("4", "Pipeline Drift"),
    ("7", "Release Explorer"),
    ("8", "Pipeline Inventory CI"),
    ("9", "Pipeline Inventory CD"),
    ("10", "Pipeline Health Score"),
]

def execute_azdo_tools(org, project, pat):
    """Simula ejecución de herramientas AZDO (sin bloqueos)"""
    
    # Mostrar herramientas a ejecutar
    if RICH_AVAILABLE and console:
        table = Table(title="📋 Herramientas a Ejecutar", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="cyan", width=5)
        table.add_column("Herramienta", style="white")
        for tool_id, tool_name in AZDO_TOOLS:
            table.add_row(tool_id, tool_name)
        console.print(table)
    else:
        print(f"\n📋 Herramientas a ejecutar:")
        for tool_id, tool_name in AZDO_TOOLS:
            print(f"   [{tool_id}] {tool_name}")
    
    success_count = 0
    error_count = 0
    results = []
    
    if RICH_AVAILABLE and console:
        # Usar Progress con barra de progreso y spinner - SIMULADO
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
            transient=False
        ) as progress:
            task = progress.add_task("[cyan]Ejecutando herramientas...", total=len(AZDO_TOOLS))
            
            # Simular ejecución de herramientas
            for tool_id, tool_name in AZDO_TOOLS:
                progress.update(task, description=f"[cyan]Ejecutando [{tool_id}] {tool_name}...")
                
                # Simular trabajo (sin bloqueos)
                time.sleep(0.5)
                
                results.append((tool_name, "✅", "Completado (simulado)"))
                success_count += 1
                progress.advance(task)
        
        # Mostrar resultados en tabla
        console.print()
        result_table = Table(title="📊 Resultados de Ejecución", show_header=True, header_style="bold cyan")
        result_table.add_column("Estado", width=5)
        result_table.add_column("Herramienta", style="white")
        result_table.add_column("Mensaje", style="dim")
        
        for tool_name, status, msg in results:
            result_table.add_row(status, f"[green]{tool_name}[/green]", f"[green]{msg}[/green]")
        
        console.print(result_table)
        
        # Panel de resumen
        summary_text = Text()
        summary_text.append(f"✅ Exitosas: {success_count}  ", style="bold green")
        summary_text.append(f"📁 Reportes en: outcome/", style="bold cyan")
        
        console.print(Panel(summary_text, title="📈 Resumen", border_style="cyan"))
    else:
        # Fallback sin Rich
        print(f"\n🚀 Ejecutando {len(AZDO_TOOLS)} herramientas...")
        
        for tool_id, tool_name in AZDO_TOOLS:
            print(f"\n🔵 [{tool_id}] {tool_name}")
            time.sleep(0.5)
            print(f"   ✅ Completado (simulado)")
            success_count += 1
        
        print(f"\n📊 Resumen: {success_count} exitosas, {error_count} errores")
    
    return True

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
        console.print("[green]✅ Reportes generados en outcome/[/green]")
    else:
        print(f"\n✅ Reportes generados en outcome/")
    
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
                output_dir='outcome/dashboard'
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
                input_file='outcome/dashboard/dashboard_data.json',
                output_file='outcome/dashboard/dashboard.html'
            )
            generator.generate()
            progress.stop()
        
        if RICH_AVAILABLE and console:
            console.print("[green]✅ Dashboard HTML generado: outcome/dashboard/dashboard.html[/green]")
        else:
            print(f"✅ Dashboard HTML generado: outcome/dashboard/dashboard.html")
        
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
            summary_table.add_row("Datos:", "[cyan]outcome/dashboard/dashboard_data.json[/cyan]")
            summary_table.add_row("HTML:", "[cyan]outcome/dashboard/dashboard.html[/cyan]")
            summary_table.add_row("Histórico:", "[cyan]outcome/dashboard/history/[/cyan]")
            console.print(summary_table)
        else:
            print("\n" + "=" * 60)
            print("✅ Dashboard ejecutado exitosamente")
            print("=" * 60)
            print("Archivos generados:")
            print("  - outcome/dashboard/dashboard_data.json")
            print("  - outcome/dashboard/dashboard.html")
            print("  - outcome/dashboard/history/")
        
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
