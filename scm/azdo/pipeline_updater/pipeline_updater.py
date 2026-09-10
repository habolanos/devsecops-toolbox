"""
Orquestador principal de Pipeline Updater
"""

import argparse
import sys
from typing import Dict, List, Optional
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from .template_parser import TemplateParser
from .validator import TemplateValidator
from .azdo_client import AzureDevOpsClient, AzureDevOpsError
from .parallel_executor import ParallelExecutor
from .reporter import Reporter
from .config import load_config

console = Console()


class PipelineUpdater:
    """Orquestador principal de actualización de pipelines"""
    
    def __init__(self, pat: str, org: str, project: str):
        """
        Inicializar actualizador
        
        Args:
            pat: Personal Access Token
            org: Organización
            project: Proyecto
        """
        self.pat = pat
        self.org = org
        self.project = project
        self.azdo_client = AzureDevOpsClient(pat, org, project)
    
    def update_pipelines(
        self,
        definition_ids: List[int],
        template_path: str,
        dry_run: bool = False,
        max_workers: int = 5
    ) -> Dict:
        """
        Actualizar múltiples pipelines
        
        Args:
            definition_ids: Lista de IDs de definiciones
            template_path: Ruta al archivo de template
            dry_run: Modo simulación
            max_workers: Número de workers paralelos
            
        Returns:
            Diccionario con resultados
        """
        
        console.print(Panel(
            f"[bold]🆙 Pipeline Updater[/bold]\n"
            f"Actualización masiva de definiciones de CD\n"
            f"Total de pipelines: {len(definition_ids)}",
            title="Pipeline Updater",
            border_style="cyan"
        ))
        console.print()

        # 1. Cargar y validar template
        console.print(f"[bold cyan][1/5] Cargando template:[/bold cyan] {template_path}")
        try:
            parser = TemplateParser(template_path)
            
            if not parser.validate():
                return {
                    'success': False,
                    'error': 'Template inválido',
                    'details': 'El template no contiene las secciones requeridas'
                }
            
            validator = TemplateValidator(parser.to_dict())
            if not validator.validate():
                return {
                    'success': False,
                    'error': 'Template inválido',
                    'details': validator.get_errors()
                }
            
            metadata = parser.get_metadata()
            console.print(f"  [green]✓[/green] Template cargado: {metadata.name} v{metadata.version}")
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Error al cargar template: {str(e)}'
            }
        
        # 2. Análisis previo
        console.print(f"\n[bold cyan][2/5] Analizando {len(definition_ids)} pipelines...[/bold cyan]")
        analysis_results = self._analyze_pipelines(definition_ids, parser)

        console.print(f"  [green]✓[/green] Análisis completado")
        console.print(f"    - Pipelines analizados: [cyan]{analysis_results['analyzed']}[/cyan]")
        console.print(f"    - Pipelines con coincidencias: [cyan]{analysis_results['with_matches']}[/cyan]")
        console.print(f"    - Total de coincidencias: [cyan]{analysis_results['total_matches']}[/cyan]")
        
        # 3. Confirmación
        if not dry_run:
            console.print("\n[bold cyan][3/5] Confirmación requerida[/bold cyan]")
            console.print(f"  [yellow]⚠[/yellow] Se procederá a actualizar [cyan]{len(definition_ids)}[/cyan] pipelines")
            console.print("  [yellow]⚠[/yellow] Los cambios serán [red]PERMANENTES[/red]")
            console.print("  [blue]ℹ[/blue] Se crearán snapshots automáticos para rollback")
            
            response = Prompt.ask(
                "\n  ¿Deseas continuar?",
                default="n",
                console=console
            )
            
            if response.strip().upper() not in ('SI', 'S', 'Y', 'YES'):
                console.print("\n  [red]✗[/red] Operación cancelada por el usuario\n")
                return {
                    'success': False,
                    'error': 'Operación cancelada',
                    'cancelled': True
                }
        else:
            console.print("\n[bold yellow][3/5] Modo DRY-RUN (sin cambios)[/bold yellow]")
        
        # Merge dry_run: CLI flag OR template option
        template_options = parser.get_template_options()
        if template_options.dry_run:
            dry_run = True

        # 4. Ejecutar actualización
        console.print(f"\n[bold cyan][4/5] Ejecutando actualización en paralelo...[/bold cyan]")

        executor = ParallelExecutor(max_workers=max_workers)

        def progress_callback(completed, total, result):
            if result:
                status = "[green]✅ Success[/green]" if result.success else "[red]❌ Error[/red]"
                detail = f"cambios: [cyan]{result.changes_applied}[/cyan]"
            else:
                status = "[red]❌ Error[/red]"
                detail = "error desconocido"
            def_id = result.definition_id if result else '?'
            console.print(f"  [{completed}/{total}] Pipeline [cyan]#{def_id}[/cyan] | {status} | {detail}")

        execution_results = executor.execute(
            definition_ids,
            parser,
            self.azdo_client,
            on_progress=progress_callback,
            dry_run=dry_run
        )
        
        # 5. Generar reportes
        console.print(f"\n[bold cyan][5/5] Generando reportes...[/bold cyan]")

        reporter = Reporter(execution_results['results'], execution_results['errors'])
        json_file = reporter.generate_json()
        csv_file = reporter.generate_csv()
        html_file = reporter.generate_html()

        console.print("  [green]✓[/green] Reportes generados:")
        console.print(f"    - JSON: [cyan]{json_file}[/cyan]")
        console.print(f"    - CSV:  [cyan]{csv_file}[/cyan]")
        console.print(f"    - HTML: [cyan]{html_file}[/cyan]")

        # ─── Resumen final estilo Release Updater ───
        console.print(f"\n[bold]{'='*70}[/]")
        console.print("[bold]  RESUMEN DE EJECUCIÓN[/bold]")
        console.print(f"[bold]{'='*70}[/]\n")

        all_results: list = list(execution_results.get('results', []))
        all_errors: list = list(execution_results.get('errors', []))

        summary_table = Table(title="Resultados por Pipeline", show_lines=True)
        summary_table.add_column("#", style="dim", width=4)
        summary_table.add_column("Definition ID", style="cyan", width=16)
        summary_table.add_column("Status", width=12)
        summary_table.add_column("Cambios", justify="right", width=8)
        summary_table.add_column("Detalle", no_wrap=False)

        status_styles = {
            'success': '[green]✅ Success[/green]',
            'error': '[red]❌ Error[/red]',
            'dry_run': '[cyan]🔍 Dry-run[/cyan]',
            'no_changes': '[yellow]⏭ Sin cambios[/yellow]',
        }

        row_index = 1
        # Filas exitosas / simuladas
        for r in all_results:
            if r.success and r.changes_applied == 0 and not dry_run:
                status_key = 'no_changes'
            elif dry_run and r.success:
                status_key = 'dry_run'
            elif r.success:
                status_key = 'success'
            else:
                status_key = 'error'

            status_str = status_styles.get(status_key, r.success)
            changes = str(r.changes_applied)

            if status_key == 'success':
                detail = f"snapshot: {r.snapshot_id} | matches: {r.matches_found}"
            elif status_key == 'dry_run':
                detail = f"{r.changes_applied} cambios simulados | matches: {r.matches_found}"
            elif status_key == 'no_changes':
                detail = f"matches: {r.matches_found}"
            else:
                detail = f"error: {r.error or 'N/A'}"

            summary_table.add_row(str(row_index), f"#{r.definition_id}", status_str, changes, detail)
            row_index += 1

        # Filas de errores capturados fuera del resultado
        for err in all_errors:
            status_str = status_styles['error']
            detail = f"error: {err.get('error', 'N/A')}"
            summary_table.add_row(str(row_index), f"#{err.get('definition_id', '?')}", status_str, "0", detail)
            row_index += 1

        console.print(summary_table)

        console.print()
        console.print(f"[green]✅ Exitosos: {execution_results['success']}/{execution_results['total']}[/green]")
        if dry_run:
            console.print(f"[cyan]🔍 Dry-run: {execution_results['success']}/{execution_results['total']}[/cyan]")
        if execution_results['failed']:
            console.print(f"[red]❌ Errores: {execution_results['failed']}/{execution_results['total']}[/red]")
        if execution_results['total'] > 0:
            rate = execution_results['success'] / execution_results['total'] * 100
            console.print(f"[cyan]Tasa de éxito: {rate:.1f}%[/cyan]")

        console.print(f"\n[bold]{'='*70}[/]\n")
        
        return {
            'success': execution_results['failed'] == 0,
            'execution_results': execution_results,
            'analysis_results': analysis_results,
            'reports': {
                'json': json_file,
                'csv': csv_file,
                'html': html_file
            }
        }
    
    def _analyze_pipelines(self, definition_ids: List[int], parser: TemplateParser) -> Dict:
        """
        Analizar pipelines antes de actualizar
        
        Args:
            definition_ids: Lista de IDs
            parser: Parser de templates
            
        Returns:
            Diccionario con resultados del análisis
        """
        from .search_engine import SearchEngine
        
        analyzed = 0
        with_matches = 0
        total_matches = 0
        
        for def_id in definition_ids[:5]:  # Analizar primeros 5 como muestra
            try:
                definition = self.azdo_client.get_release_definition(def_id)
                search_engine = SearchEngine(definition, parser.get_search_rules())
                matches = search_engine.search_all()
                
                analyzed += 1
                if matches:
                    with_matches += 1
                    total_matches += len(matches)
            
            except AzureDevOpsError:
                pass
        
        return {
            'analyzed': analyzed,
            'with_matches': with_matches,
            'total_matches': total_matches
        }


def main():
    """Función principal CLI"""
    parser = argparse.ArgumentParser(
        description='Pipeline Updater - Actualización masiva de pipelines CD'
    )
    
    # Argumentos para actualización
    parser.add_argument(
        '--definition-ids',
        help='IDs de definiciones separados por coma (ej: 2758,2759,2760)'
    )
    parser.add_argument(
        '--template',
        help='Ruta al archivo de template YAML'
    )
    parser.add_argument(
        '--pat',
        default=None,
        help='Personal Access Token de Azure DevOps (default: desde config.json)'
    )
    parser.add_argument(
        '--org',
        default=None,
        help='Organización de Azure DevOps (default: desde config.json)'
    )
    parser.add_argument(
        '--project',
        default=None,
        help='Proyecto de Azure DevOps (default: desde config.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Modo simulación (sin cambios)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Número de workers paralelos (default: 5)'
    )
    
    # Argumentos para rollback
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Ejecutar rollback desde snapshot'
    )
    parser.add_argument(
        '--definition-id',
        help='ID de definición para rollback'
    )
    parser.add_argument(
        '--snapshot-id',
        help='ID del snapshot para rollback'
    )
    
    args = parser.parse_args()
    
    # Cargar configuración desde scm/config.json
    cfg = load_config()
    pat = args.pat or cfg.get('pat', '')
    org = args.org or cfg.get('organization', '')
    project = args.project or cfg.get('project', '')
    
    if not pat:
        print("Error: --pat es requerido (no encontrado en config.json ni CLI)")
        sys.exit(1)
    if not org:
        print("Error: --org es requerido (no encontrado en config.json ni CLI)")
        sys.exit(1)
    if not project:
        print("Error: --project es requerido (no encontrado en config.json ni CLI)")
        sys.exit(1)
    
    # Ejecutar rollback si se especifica
    if args.rollback:
        if not args.definition_id or not args.snapshot_id:
            print("Error: --definition-id y --snapshot-id son requeridos para rollback")
            sys.exit(1)
        
        try:
            definition_id = int(args.definition_id)
        except ValueError:
            print("Error: definition-id debe ser un número")
            sys.exit(1)
        
        updater = PipelineUpdater(pat, org, project)
        
        print("\n" + "="*70)
        print("  Pipeline Updater - Rollback desde Snapshot")
        print("="*70 + "\n")
        
        try:
            success = updater.azdo_client.rollback(definition_id, args.snapshot_id)
            
            if success:
                print(f"\n✅ Rollback completado exitosamente")
                print(f"   Pipeline: {definition_id}")
                print(f"   Snapshot: {args.snapshot_id}\n")
                sys.exit(0)
            else:
                print(f"\n❌ Rollback falló")
                sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error durante rollback: {str(e)}\n")
            sys.exit(1)
    
    # Ejecutar actualización normal
    if not args.definition_ids or not args.template:
        print("Error: --definition-ids y --template son requeridos para actualización")
        sys.exit(1)
    
    # Parsear definition IDs
    try:
        definition_ids = [int(x.strip()) for x in args.definition_ids.split(',')]
    except ValueError:
        print("Error: definition-ids debe contener números separados por coma")
        sys.exit(1)
    
    # Ejecutar actualización
    # La ruta del template se pasa como absoluta desde tools.py
    updater = PipelineUpdater(pat, org, project)
    result = updater.update_pipelines(
        definition_ids,
        args.template,
        dry_run=args.dry_run,
        max_workers=args.workers
    )
    
    # Salir con código apropiado
    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    main()
