"""
Orquestador principal de Pipeline Updater
"""

import argparse
import json
import sys
from typing import Dict, List, Optional
from pathlib import Path

from .template_parser import TemplateParser
from .validator import TemplateValidator
from .azdo_client import AzureDevOpsClient, AzureDevOpsError
from .parallel_executor import ParallelExecutor
from .reporter import Reporter


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
        
        print("\n" + "="*70)
        print("  Pipeline Updater - Actualización Masiva de Pipelines CD")
        print("="*70 + "\n")
        
        # 1. Cargar y validar template
        print(f"[1/5] Cargando template: {template_path}")
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
            print(f"  ✓ Template cargado: {metadata.name} v{metadata.version}")
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Error al cargar template: {str(e)}'
            }
        
        # 2. Análisis previo
        print(f"\n[2/5] Analizando {len(definition_ids)} pipelines...")
        analysis_results = self._analyze_pipelines(definition_ids, parser)
        
        print(f"  ✓ Análisis completado")
        print(f"    - Pipelines analizados: {analysis_results['analyzed']}")
        print(f"    - Pipelines con coincidencias: {analysis_results['with_matches']}")
        print(f"    - Total de coincidencias: {analysis_results['total_matches']}")
        
        # 3. Confirmación
        if not dry_run:
            print(f"\n[3/5] Confirmación requerida")
            print(f"  ⚠  Se procederá a actualizar {len(definition_ids)} pipelines")
            print(f"  ⚠  Los cambios serán PERMANENTES")
            print(f"  ℹ  Se crearán snapshots automáticos para rollback")
            
            response = input("\n  ¿Deseas continuar? (SI/S/Y/YES para confirmar): ").strip()
            
            if response.upper() not in ('SI', 'S', 'Y', 'YES'):
                print(f"\n  ✗ Operación cancelada por el usuario\n")
                return {
                    'success': False,
                    'error': 'Operación cancelada',
                    'cancelled': True
                }
        else:
            print(f"\n[3/5] Modo DRY-RUN (sin cambios)")
        
        # 4. Ejecutar actualización
        print(f"\n[4/5] Ejecutando actualización en paralelo...")
        
        executor = ParallelExecutor(max_workers=max_workers)
        
        def progress_callback(completed, total, result):
            status = "✓" if result and result.success else "✗"
            print(f"  {status} [{completed}/{total}] Pipeline {result.definition_id if result else 'Error'}")
        
        execution_results = executor.execute(
            definition_ids,
            parser,
            self.azdo_client,
            on_progress=progress_callback
        )
        
        # 5. Generar reportes
        print(f"\n[5/5] Generando reportes...")
        
        reporter = Reporter(execution_results['results'], execution_results['errors'])
        json_file = reporter.generate_json()
        csv_file = reporter.generate_csv()
        html_file = reporter.generate_html()
        
        print(f"  ✓ Reportes generados:")
        print(f"    - JSON: {json_file}")
        print(f"    - CSV: {csv_file}")
        print(f"    - HTML: {html_file}")
        
        # Resumen final
        print(f"\n" + "="*70)
        print(f"  RESUMEN DE EJECUCIÓN")
        print(f"="*70)
        print(f"  Total pipelines: {execution_results['total']}")
        print(f"  Exitosos: {execution_results['success']}")
        print(f"  Fallidos: {execution_results['failed']}")
        print(f"  Tasa de éxito: {execution_results['success']/execution_results['total']*100:.1f}%")
        print(f"="*70 + "\n")
        
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
        required=True,
        help='Personal Access Token de Azure DevOps'
    )
    parser.add_argument(
        '--org',
        required=True,
        help='Organización de Azure DevOps'
    )
    parser.add_argument(
        '--project',
        required=True,
        help='Proyecto de Azure DevOps'
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
        
        updater = PipelineUpdater(args.pat, args.org, args.project)
        
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
    updater = PipelineUpdater(args.pat, args.org, args.project)
    result = updater.update_pipelines(
        definition_ids,
        args.template,
        dry_run=args.dry_run,
        max_workers=args.workers
    )
    
    # Mostrar resultado en JSON
    print(json.dumps(result, indent=2, default=str))
    
    # Salir con código apropiado
    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    main()
