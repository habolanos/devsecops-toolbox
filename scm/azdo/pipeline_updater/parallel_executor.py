"""
Ejecutor paralelo para Pipeline Updater
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Callable
from .models import UpdateResult
from .search_engine import SearchEngine
from .update_engine import UpdateEngine


class ParallelExecutor:
    """Ejecutor paralelo de actualizaciones"""
    
    def __init__(self, max_workers: int = 5):
        """
        Inicializar ejecutor
        
        Args:
            max_workers: Número máximo de workers
        """
        self.max_workers = max_workers
        self.results: List[UpdateResult] = []
        self.errors: List[Dict] = []
    
    def execute(
        self,
        definition_ids: List[int],
        template_parser,
        azdo_client,
        on_progress: Callable = None
    ) -> Dict:
        """
        Ejecutar actualización en paralelo
        
        Args:
            definition_ids: Lista de IDs de definiciones
            template_parser: Parser de templates
            azdo_client: Cliente de Azure DevOps
            on_progress: Callback para progreso
            
        Returns:
            Diccionario con resultados
        """
        self.results = []
        self.errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._process_pipeline,
                    def_id,
                    template_parser,
                    azdo_client
                ): def_id
                for def_id in definition_ids
            }
            
            completed = 0
            total = len(futures)
            
            for future in as_completed(futures):
                def_id = futures[future]
                completed += 1
                
                try:
                    result = future.result()
                    self.results.append(result)
                    
                    if on_progress:
                        on_progress(completed, total, result)
                
                except Exception as e:
                    self.errors.append({
                        'definition_id': def_id,
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    
                    if on_progress:
                        on_progress(completed, total, None)
        
        # Contar solo resultados exitosos
        successful_count = sum(1 for r in self.results if r.success)
        
        return {
            'success': successful_count,
            'failed': len(self.errors),
            'total': len(definition_ids),
            'results': self.results,
            'errors': self.errors
        }
    
    def _process_pipeline(
        self,
        definition_id: int,
        template_parser,
        azdo_client
    ) -> UpdateResult:
        """
        Procesar un pipeline
        
        Args:
            definition_id: ID de la definición
            template_parser: Parser de templates
            azdo_client: Cliente de Azure DevOps
            
        Returns:
            Resultado de la actualización
        """
        start_time = time.time()
        
        try:
            print(f"\n  [Pipeline {definition_id}] Iniciando procesamiento...")
            
            # 1. Descargar definición
            print(f"  [Pipeline {definition_id}] 1/5 Descargando definición...")
            definition = azdo_client.get_release_definition(definition_id)
            print(f"  [Pipeline {definition_id}]   ✓ Definición descargada (revision: {definition.get('revision', 'N/A')})")
            
            # 2. Crear snapshot
            print(f"  [Pipeline {definition_id}] 2/5 Creando snapshot...")
            snapshot_id = azdo_client.create_snapshot(definition_id, definition)
            print(f"  [Pipeline {definition_id}]   ✓ Snapshot creado: {snapshot_id}")
            
            # 3. Buscar coincidencias
            print(f"  [Pipeline {definition_id}] 3/5 Buscando coincidencias...")
            search_rules = template_parser.get_search_rules()
            
            search_engine = SearchEngine(
                definition,
                search_rules
            )
            matches = search_engine.search_all()
            print(f"  [Pipeline {definition_id}]   ✓ Coincidencias encontradas: {len(matches)}")
            
            # Verificar si el template tiene una acción a nivel de pipeline
            pipeline_action = template_parser.get_pipeline_action()
            
            if pipeline_action == 'disable':
                # Flujo de deshabilitación: PUT con isDisabled=true
                # El pipeline permanece visible en la UI pero no permite crear releases.
                # Es reversible: un PUT con isDisabled=false lo re-habilita.
                print(f"  [Pipeline {definition_id}] 4/5 Deshabilitando pipeline (isDisabled=true)...")
                metadata = template_parser.get_metadata()
                success = azdo_client.update_release_definition(
                    definition_id, definition,
                    comment=metadata.comment,
                    disable=True
                )
                print(f"  [Pipeline {definition_id}]   ✓ Pipeline deshabilitado exitosamente")
                
                duration = time.time() - start_time
                
                return UpdateResult(
                    definition_id=definition_id,
                    success=success,
                    snapshot_id=snapshot_id,
                    matches_found=len(matches),
                    changes_applied=1,
                    changes=[{
                        'type': 'pipeline_disable',
                        'definition_id': definition_id,
                        'snapshot_id': snapshot_id
                    }],
                    error=None,
                    duration=duration
                )
            
            # 4. Aplicar actualizaciones (flujo normal)
            print(f"  [Pipeline {definition_id}] 4/5 Aplicando actualizaciones...")
            update_rules = template_parser.get_update_rules()
            template_options = template_parser.get_template_options()
            
            update_engine = UpdateEngine(
                definition,
                matches,
                update_rules,
                template_options
            )
            update_engine.apply_updates()
            changes_count = update_engine.get_changes_count()
            print(f"  [Pipeline {definition_id}]   ✓ Cambios aplicados: {changes_count}")
            
            # 5. Guardar cambios
            print(f"  [Pipeline {definition_id}] 5/5 Guardando cambios en Azure DevOps...")
            metadata = template_parser.get_metadata()
            success = azdo_client.update_release_definition(
                definition_id, definition, comment=metadata.comment
            )
            print(f"  [Pipeline {definition_id}]   ✓ Cambios guardados exitosamente")
            
            duration = time.time() - start_time
            
            return UpdateResult(
                definition_id=definition_id,
                success=success,
                snapshot_id=snapshot_id,
                matches_found=len(matches),
                changes_applied=update_engine.get_changes_count(),
                changes=update_engine.get_changes(),
                error=None,
                duration=duration
            )
        
        except Exception as e:
            duration = time.time() - start_time
            print(f"  [Pipeline {definition_id}] ✗ ERROR: {str(e)}")
            
            return UpdateResult(
                definition_id=definition_id,
                success=False,
                snapshot_id='',
                matches_found=0,
                changes_applied=0,
                changes=[],
                error=str(e),
                duration=duration
            )
    
    def get_results(self) -> List[UpdateResult]:
        """Obtener resultados"""
        return self.results
    
    def get_errors(self) -> List[Dict]:
        """Obtener errores"""
        return self.errors
    
    def get_summary(self) -> Dict:
        """Obtener resumen de ejecución"""
        total_duration = sum(r.duration for r in self.results)
        total_matches = sum(r.matches_found for r in self.results)
        total_changes = sum(r.changes_applied for r in self.results)
        successful_count = sum(1 for r in self.results if r.success)
        
        return {
            'total_pipelines': len(self.results) + len(self.errors),
            'successful': successful_count,
            'failed': len(self.errors),
            'total_matches': total_matches,
            'total_changes': total_changes,
            'total_duration': total_duration,
            'average_duration': total_duration / len(self.results) if self.results else 0
        }
