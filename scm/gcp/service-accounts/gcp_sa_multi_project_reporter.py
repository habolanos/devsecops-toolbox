#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Service Accounts Multi-Project Reporter
Extrae, analiza y reporta service accounts de múltiples proyectos GCP

Uso:
    python gcp_sa_multi_project_reporter.py --projects=p1,p2,p3 --mode=all --output=json
    python gcp_sa_multi_project_reporter.py  # Usa config.json
"""

import argparse
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
from datetime import datetime

# Agregar parent directory al path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from sa_config_loader import ConfigLoader
from sa_extractors import ServiceAccountExtractor
from sa_analyzers import RolesAndPermissionsAnalyzer, SecurityAnalyzer
from sa_report_generators import (
    JSONReportGenerator, CSVReportGenerator, ExcelReportGenerator, HTMLReportGenerator
)

# Rich imports para visualización profesional
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.box import ROUNDED, HEAVY
    from rich.align import Align
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


class MultiProjectOrchestrator:
    """Orquesta extracción y análisis de múltiples proyectos."""
    
    def __init__(self, projects: List[str], config: Dict, debug: bool = False):
        self.projects = projects
        self.config = config
        self.debug = debug
        self.max_workers = config.get('parallel_workers', 5)
        self.results_summary = []
    
    def extract_all(self) -> Dict:
        """Extrae datos de todos los proyectos en paralelo con visualización."""
        results = {}
        
        if RICH_AVAILABLE and console:
            console.print(f"\n🚀 Iniciando análisis de {len(self.projects)} proyecto(s)...\n")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task(
                    "[cyan]Extrayendo datos de proyectos...",
                    total=len(self.projects)
                )
                
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(self._extract_project, proj): proj
                        for proj in self.projects
                    }
                    
                    for future in as_completed(futures):
                        project = futures[future]
                        try:
                            results[project] = future.result()
                            self.results_summary.append({
                                'project': project,
                                'status': '✅',
                                'sas': len(results[project].get('service_accounts', []))
                            })
                            progress.update(task, advance=1)
                        except Exception as e:
                            results[project] = {'error': str(e)}
                            self.results_summary.append({
                                'project': project,
                                'status': '❌',
                                'sas': 0
                            })
                            progress.update(task, advance=1)
        else:
            # Fallback sin Rich
            print(f"\n🚀 Iniciando análisis de {len(self.projects)} proyecto(s)...\n")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self._extract_project, proj): proj
                    for proj in self.projects
                }
                
                for i, future in enumerate(as_completed(futures), 1):
                    project = futures[future]
                    try:
                        results[project] = future.result()
                        print(f"[{i}/{len(self.projects)}] ✅ {project}")
                    except Exception as e:
                        results[project] = {'error': str(e)}
                        print(f"[{i}/{len(self.projects)}] ❌ {project}: {e}")
        
        return results
    
    def _extract_project(self, project_id: str) -> Dict:
        """Extrae datos de un proyecto específico."""
        extractor = ServiceAccountExtractor(project_id, self.debug)
        data = extractor.extract_all()
        
        # Analizar roles
        roles_analyzer = RolesAndPermissionsAnalyzer(self.debug)
        iam_bindings = data.get('iam_bindings', [])
        
        for sa in data.get('service_accounts', []):
            sa['roles_analysis'] = roles_analyzer.analyze_roles(sa['email'], iam_bindings)
            
            # Analizar seguridad
            security_analyzer = SecurityAnalyzer(self.debug)
            sa['security'] = security_analyzer.analyze(sa)
        
        return data
    
    def consolidate(self, data: Dict) -> Dict:
        """Consolida datos de múltiples proyectos."""
        return {
            'summary': self._generate_summary(data),
            'by_project': data,
            'cross_project_analysis': self._cross_project_analysis(data)
        }
    
    def _generate_summary(self, data: Dict) -> Dict:
        """Genera resumen general."""
        total_sa = sum(len(proj.get('service_accounts', []))
                      for proj in data.values() if isinstance(proj, dict))
        total_roles = sum(len(sa.get('roles_analysis', {}).get('iam_bindings', []))
                         for proj in data.values() if isinstance(proj, dict)
                         for sa in proj.get('service_accounts', []))
        
        return {
            'total_projects': len(data),
            'total_service_accounts': total_sa,
            'total_roles': total_roles,
            'generated_at': __import__('datetime').datetime.now().isoformat()
        }
    
    def _cross_project_analysis(self, data: Dict) -> Dict:
        """Análisis cruzado entre proyectos."""
        high_risk_sas = []
        
        for proj_name, proj_data in data.items():
            if isinstance(proj_data, dict) and 'error' not in proj_data:
                for sa in proj_data.get('service_accounts', []):
                    if sa.get('security', {}).get('risk_level') in ['HIGH', 'CRITICAL']:
                        high_risk_sas.append({
                            'project': proj_name,
                            'service_account': sa.get('email'),
                            'risk_level': sa.get('security', {}).get('risk_level')
                        })
        
        return {
            'high_risk_service_accounts': high_risk_sas,
            'projects_with_issues': len([p for p in data.values() 
                                        if isinstance(p, dict) and 'error' not in p])
        }
    
    def print_results_table(self):
        """Imprime tabla de resultados con Rich."""
        if not RICH_AVAILABLE or not console:
            return
        
        table = Table(
            title="📊 Resumen de Extracción por Proyecto",
            box=ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Proyecto", style="cyan", width=40)
        table.add_column("Estado", style="green", justify="center", width=10)
        table.add_column("Service Accounts", style="yellow", justify="right", width=15)
        
        for result in self.results_summary:
            table.add_row(
                result['project'],
                result['status'],
                str(result['sas'])
            )
        
        console.print(table)


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='GCP Service Accounts Multi-Project Reporter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Usar configuración desde config.json
  python gcp_sa_multi_project_reporter.py
  
  # Override de proyectos
  python gcp_sa_multi_project_reporter.py --projects=p1,p2,p3
  
  # Modo seguridad con salida Excel
  python gcp_sa_multi_project_reporter.py --mode=security --output=excel
  
  # Debug mode
  python gcp_sa_multi_project_reporter.py --debug
        """
    )
    
    parser.add_argument('--projects', 
                       help='Proyectos a analizar (separados por coma)')
    parser.add_argument('--mode', 
                       choices=['all', 'security', 'compliance', 'usage'],
                       default='all',
                       help='Modo de reporte (default: all)')
    parser.add_argument('-o', '--output', 
                       choices=['json', 'csv', 'excel', 'html'],
                       default='json',
                       help='Formato de salida (default: json)')
    parser.add_argument('--config', 
                       default='config.json',
                       help='Ruta a config.json (default: config.json)')
    parser.add_argument('--output-dir', 
                       default='outcome',
                       help='Directorio de salida (default: outcome)')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='Modo debug')
    
    args = parser.parse_args()
    
    # Cargar configuración
    config_loader = ConfigLoader(args.config, args.debug)
    
    # Validar configuración
    is_valid, errors = config_loader.validate()
    if not is_valid and not args.projects:
        print("❌ Errores de configuración:")
        for error in errors:
            print(f"   - {error}")
        print("\n💡 Solución: Especifica --projects o configura config.json")
        sys.exit(1)
    
    # Obtener proyectos
    projects = args.projects.split(',') if args.projects else config_loader.get_projects()
    
    if not projects:
        print("❌ No hay proyectos para analizar")
        sys.exit(1)
    
    # Obtener configuración
    defaults = config_loader.get_defaults()
    
    # Mostrar información inicial con Rich
    if RICH_AVAILABLE and console:
        console.print(f"\n[bold cyan]Proyectos:[/bold cyan] {', '.join(projects)}")
        console.print(f"[bold cyan]Modo:[/bold cyan] {args.mode}")
        console.print(f"[bold cyan]Salida:[/bold cyan] {args.output}")
    else:
        print(f"🚀 Iniciando análisis de {len(projects)} proyecto(s)...")
        print(f"   Proyectos: {', '.join(projects)}")
        print(f"   Modo: {args.mode}")
        print(f"   Salida: {args.output}")
    
    # Extraer datos
    start_time = datetime.now()
    orchestrator = MultiProjectOrchestrator(projects, defaults, args.debug)
    extracted_data = orchestrator.extract_all()
    
    # Mostrar tabla de resultados
    orchestrator.print_results_table()
    
    # Consolidar datos
    consolidated_data = orchestrator.consolidate(extracted_data)
    
    # Generar reporte
    if RICH_AVAILABLE and console:
        console.print(f"\n[bold cyan]📊 Generando reporte {args.output}...[/bold cyan]")
    else:
        print(f"\n📊 Generando reporte {args.output}...")
    
    generators = {
        'json': JSONReportGenerator,
        'csv': CSVReportGenerator,
        'excel': ExcelReportGenerator,
        'html': HTMLReportGenerator
    }
    
    generator_class = generators.get(args.output, JSONReportGenerator)
    generator = generator_class(args.output_dir, args.debug)
    report_path = generator.generate(consolidated_data)
    
    if report_path:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if RICH_AVAILABLE and console:
            console.print(f"\n[bold green]✅ Reporte generado:[/bold green] {report_path}")
            
            # Tabla de resumen
            summary = consolidated_data.get('summary', {})
            summary_table = Table(
                title="📈 Resumen de Ejecución",
                box=ROUNDED,
                show_header=True,
                header_style="bold cyan"
            )
            summary_table.add_column("Métrica", style="cyan")
            summary_table.add_column("Valor", style="green", justify="right")
            
            summary_table.add_row("Proyectos", str(summary.get('total_projects', 0)))
            summary_table.add_row("Service Accounts", str(summary.get('total_service_accounts', 0)))
            summary_table.add_row("Roles", str(summary.get('total_roles', 0)))
            summary_table.add_row("Duración", f"{duration:.2f}s")
            
            console.print(summary_table)
        else:
            print(f"✅ Reporte generado: {report_path}")
            print(f"\n📈 Resumen:")
            summary = consolidated_data.get('summary', {})
            print(f"   - Proyectos: {summary.get('total_projects', 0)}")
            print(f"   - Service Accounts: {summary.get('total_service_accounts', 0)}")
            print(f"   - Roles: {summary.get('total_roles', 0)}")
            print(f"   - Duración: {duration:.2f}s")
    else:
        if RICH_AVAILABLE and console:
            console.print("[bold red]❌ Error generando reporte[/bold red]")
        else:
            print("❌ Error generando reporte")
        sys.exit(1)


if __name__ == '__main__':
    main()
