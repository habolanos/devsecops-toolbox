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
        
        return {
            'success': len(self.results),
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
            # 1. Descargar definición
            definition = azdo_client.get_release_definition(definition_id)
            
            # 2. Crear snapshot
            snapshot_id = azdo_client.create_snapshot(definition_id, definition)
            
            # 3. Buscar coincidencias
            search_engine = SearchEngine(
                definition,
                template_parser.get_search_rules()
            )
            matches = search_engine.search_all()
            
            # 4. Aplicar actualizaciones
            update_engine = UpdateEngine(
                definition,
                matches,
                template_parser.get_update_rules()
            )
            update_engine.apply_updates()
            
            # 5. Guardar cambios
            success = azdo_client.update_release_definition(definition_id, definition)
            
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
        
        return {
            'total_pipelines': len(self.results) + len(self.errors),
            'successful': len(self.results),
            'failed': len(self.errors),
            'total_matches': total_matches,
            'total_changes': total_changes,
            'total_duration': total_duration,
            'average_duration': total_duration / len(self.results) if self.results else 0
        }
