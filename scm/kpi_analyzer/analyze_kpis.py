#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KPI Analyzer — DevSecOps Toolbox
Script principal para análisis de KPIs desde salidas JSON

Usage:
    python analyze_kpis.py
    python analyze_kpis.py --platform gcp
    python analyze_kpis.py --output json
    python analyze_kpis.py --dashboard

Version: 1.0.0
Author: Harold Adrian
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from kpi_analyzer.analyzer import KPIAnalyzer
from kpi_analyzer.reporter import KPIReporter
from kpi_analyzer.maturity_model import assess_maturity, get_level_name, get_level_color
from kpi_analyzer.benchmarks import get_benchmark_level, get_benchmark_emoji, get_benchmark_color

__version__ = "1.0.0"


def get_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="KPI Analyzer — Análisis de métricas DevSecOps desde salidas JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_kpis.py                    # Analizar todos los KPIs
  python analyze_kpis.py --platform gcp     # Solo KPIs de GCP
  python analyze_kpis.py --output json      # Exportar solo JSON
  python analyze_kpis.py --dashboard        # Generar dashboard HTML
  python analyze_kpis.py --maturity         # Mostrar evaluación de madurez
        """
    )
    
    parser.add_argument(
        '--platform',
        choices=['all', 'gcp', 'azdo', 'aws', 'terminal'],
        default='all',
        help='Plataforma a analizar (default: all)'
    )
    
    parser.add_argument(
        '--output',
        choices=['all', 'json', 'csv', 'html'],
        default='all',
        help='Formato de salida (default: all)'
    )
    
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Generar dashboard HTML completo'
    )
    
    parser.add_argument(
        '--maturity',
        action='store_true',
        help='Mostrar evaluación de madurez DevSecOps'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    return parser.parse_args()


def print_banner():
    """Print banner"""
    if RICH_AVAILABLE:
        console = Console()
        console.print(Panel.fit(
            "[bold cyan]KPI Analyzer[/bold cyan]\n"
            "[dim]DevSecOps Toolbox — Análisis de Métricas[/dim]\n"
            f"[dim]Version {__version__}[/dim]",
            border_style="cyan"
        ))
    else:
        print("=" * 60)
        print("KPI Analyzer — DevSecOps Toolbox")
        print(f"Version {__version__}")
        print("=" * 60)


def print_kpi_summary(results, console=None):
    """Print KPI summary table"""
    if not RICH_AVAILABLE or console is None:
        print("\n=== KPI Summary ===")
        for kpi in results.get('kpis', []):
            value = kpi.get('value')
            value_str = f"{value:.2f}" if isinstance(value, (int, float)) and value is not None else "N/A"
            print(f"{kpi.get('name')}: {value_str} {kpi.get('unit', '')}")
        return
    
    table = Table(title="📊 KPI Summary", show_header=True, header_style="bold cyan")
    table.add_column("KPI", style="cyan", width=40)
    table.add_column("Value", justify="right", style="bold")
    table.add_column("Unit", style="dim")
    table.add_column("Level", justify="center")
    table.add_column("Benchmark Elite", justify="right", style="green")
    
    for kpi in results.get('kpis', []):
        value = kpi.get('value')
        value_str = f"{value:.2f}" if isinstance(value, (int, float)) and value is not None else "N/A"
        
        # Determine benchmark level
        if value is not None and isinstance(value, (int, float)):
            level = get_benchmark_level(kpi.get('id'), value)
            emoji = get_benchmark_emoji(level)
        else:
            emoji = "⚪"
        
        benchmarks = kpi.get('benchmarks', {})
        elite_benchmark = str(benchmarks.get('elite', 'N/A'))
        
        table.add_row(
            kpi.get('name', 'N/A'),
            value_str,
            kpi.get('unit', ''),
            emoji,
            elite_benchmark
        )
    
    console.print(table)


def print_maturity_assessment(results, console=None):
    """Print maturity assessment"""
    # Extract KPI values for maturity assessment
    kpi_values = {}
    for kpi in results.get('kpis', []):
        kpi_id = kpi.get('id')
        value = kpi.get('value')
        if kpi_id and value is not None:
            # Map KPI IDs to maturity model keys
            if kpi_id == "ec_001":
                kpi_values["deployment_frequency"] = value
            elif kpi_id == "ec_002":
                kpi_values["change_failure_rate"] = value
            elif kpi_id == "ec_003":
                kpi_values["lead_time_for_changes"] = value
            elif kpi_id == "ec_004":
                kpi_values["deployment_success_rate"] = value
            elif kpi_id == "conf_001":
                kpi_values["mttr"] = value
            elif kpi_id == "conf_002":
                kpi_values["availability"] = value
            elif kpi_id == "conf_003":
                kpi_values["error_budget_remaining"] = value
            elif kpi_id == "conf_004":
                kpi_values["mtbf"] = value
            elif kpi_id == "seg_001":
                kpi_values["mfa_coverage"] = value
            elif kpi_id == "seg_002":
                kpi_values["certificate_expiry_risk"] = value
            elif kpi_id == "seg_003":
                kpi_values["secret_rotation_coverage"] = value
            elif kpi_id == "seg_004":
                kpi_values["iam_over_permissioning"] = value
            elif kpi_id == "obs_001":
                kpi_values["monitoring_coverage"] = value
            elif kpi_id == "obs_002":
                kpi_values["slo_compliance"] = value
            elif kpi_id == "cump_001":
                kpi_values["policy_adherence"] = value
            elif kpi_id == "cump_002":
                kpi_values["pipeline_drift_rate"] = value
            elif kpi_id == "efic_001":
                kpi_values["resource_utilization"] = value
    
    assessment = assess_maturity(kpi_values)
    
    if not RICH_AVAILABLE or console is None:
        print("\n=== Maturity Assessment ===")
        print(f"Global Level: {get_level_name(assessment.global_level)} ({assessment.global_level})")
        print(f"Global Score: {assessment.global_score:.2f}")
        print(f"Next Level: {get_level_name(assessment.next_level)}")
        print(f"Gap to Next: {assessment.gap_to_next:.1f}%")
        print("\nRecommended Actions:")
        for action in assessment.recommended_actions[:5]:
            print(f"  - {action['action']} (Impact: {action['impact']}, Effort: {action['effort']})")
        return
    
    # Rich output
    level_name = get_level_name(assessment.global_level)
    level_color = get_level_color(assessment.global_level)
    
    console.print(Panel.fit(
        f"[bold]Global Maturity Level:[/bold] {level_name} ({assessment.global_level}/5)\n"
        f"[bold]Global Score:[/bold] {assessment.global_score:.2f}\n"
        f"[bold]Next Level:[/bold] {get_level_name(assessment.next_level)}\n"
        f"[bold]Gap to Next:[/bold] {assessment.gap_to_next:.1f}%",
        title="🎯 Maturity Assessment",
        border_style=level_color.replace('#', '')
    ))
    
    # Dimension scores table
    table = Table(title="📈 Dimension Scores", show_header=True, header_style="bold cyan")
    table.add_column("Dimension", style="cyan")
    table.add_column("Level", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("KPIs Met", justify="center")
    table.add_column("Blocking KPIs", style="red")
    
    for dim_name, dim_score in assessment.dimension_scores.items():
        blocking_str = ", ".join(dim_score.blocking_kpis[:3]) if dim_score.blocking_kpis else "None"
        if len(dim_score.blocking_kpis) > 3:
            blocking_str += f" +{len(dim_score.blocking_kpis) - 3} more"
        
        table.add_row(
            dim_name.replace('_', ' ').title(),
            f"{dim_score.current_level}",
            f"{dim_score.score_percentage:.1f}%",
            f"{dim_score.kpis_met}/{dim_score.kpis_total}",
            blocking_str
        )
    
    console.print(table)
    
    # Recommended actions
    if assessment.recommended_actions:
        console.print("\n[bold cyan]🚀 Recommended Actions:[/bold cyan]")
        for i, action in enumerate(assessment.recommended_actions[:5], 1):
            impact_color = "red" if action['impact'] == "high" else "yellow" if action['impact'] == "medium" else "green"
            effort_color = "red" if action['effort'] == "high" else "yellow" if action['effort'] == "medium" else "green"
            console.print(
                f"  {i}. {action['action']}\n"
                f"     Impact: [{impact_color}]{action['impact']}[/{impact_color}] | "
                f"Effort: [{effort_color}]{action['effort']}[/{effort_color}]"
            )


def main():
    """Main function"""
    args = get_args()
    
    print_banner()
    
    console = Console() if RICH_AVAILABLE else None
    
    # Initialize analyzer
    if console:
        console.print("\n[cyan]Initializing KPI Analyzer...[/cyan]")
    else:
        print("\nInitializing KPI Analyzer...")
    
    analyzer = KPIAnalyzer()
    reporter = KPIReporter()
    
    # Analyze KPIs
    platform = None if args.platform == 'all' else args.platform
    
    if console:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Analyzing KPIs for {args.platform}...", total=None)
            results = analyzer.analyze_all_kpis(platform=platform)
            progress.update(task, completed=True)
    else:
        print(f"Analyzing KPIs for {args.platform}...")
        results = analyzer.analyze_all_kpis(platform=platform)
    
    # Print summary
    print_kpi_summary(results, console)
    
    # Print maturity assessment if requested
    if args.maturity:
        print_maturity_assessment(results, console)
    
    # Export results
    if console:
        console.print("\n[cyan]Exporting results...[/cyan]")
    else:
        print("\nExporting results...")
    
    exported_files = []
    
    if args.output in ['all', 'json']:
        json_file = reporter.export_json(results)
        exported_files.append(("JSON", json_file))
        
        # Save to cache for historical analysis
        cache_file = reporter.save_to_cache(results)
        exported_files.append(("Cache", cache_file))
    
    if args.output in ['all', 'csv']:
        csv_file = reporter.export_csv(results)
        exported_files.append(("CSV", csv_file))
    
    if args.output in ['all', 'html'] or args.dashboard:
        if args.dashboard:
            # Generate full interactive dashboard
            maturity_assessment = None
            if args.maturity:
                kpi_values = {}
                for kpi in results.get('kpis', []):
                    kpi_id = kpi.get('id')
                    value = kpi.get('value')
                    if kpi_id and value is not None:
                        if kpi_id == "ec_001":
                            kpi_values["deployment_frequency"] = value
                        elif kpi_id == "ec_002":
                            kpi_values["change_failure_rate"] = value
                        elif kpi_id == "conf_001":
                            kpi_values["mttr"] = value
                        elif kpi_id == "conf_002":
                            kpi_values["availability"] = value
                        elif kpi_id == "seg_001":
                            kpi_values["mfa_coverage"] = value
                        elif kpi_id == "obs_001":
                            kpi_values["monitoring_coverage"] = value
                        elif kpi_id == "cump_001":
                            kpi_values["policy_adherence"] = value
                        elif kpi_id == "efic_001":
                            kpi_values["resource_utilization"] = value
                
                assessment = assess_maturity(kpi_values)
                maturity_assessment = {
                    'global_level': assessment.global_level,
                    'global_level_name': get_level_name(assessment.global_level),
                    'global_score': assessment.global_score
                }
            
            dashboard_file = dashboard_gen.generate_dashboard(results, maturity_assessment)
            exported_files.append(("Dashboard", dashboard_file))
        else:
            html_file = reporter.export_html_simple(results)
            exported_files.append(("HTML", html_file))
    
    # Print exported files
    if console:
        console.print("\n[bold green]✅ Export Complete[/bold green]")
        for format_name, filepath in exported_files:
            console.print(f"  {format_name}: [cyan]{filepath}[/cyan]")
    else:
        print("\n✅ Export Complete")
        for format_name, filepath in exported_files:
            print(f"  {format_name}: {filepath}")
    
    if console:
        console.print(f"\n[dim]Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
    else:
        print(f"\nGenerated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
