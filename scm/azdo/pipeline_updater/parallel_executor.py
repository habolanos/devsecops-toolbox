"""
Ejecutor paralelo para Pipeline Updater
"""

import copy
import re
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
        
        # Contar resultados exitosos y fallidos
        successful_count = sum(1 for r in self.results if r.success)
        failed_count = sum(1 for r in self.results if not r.success) + len(self.errors)
        
        return {
            'success': successful_count,
            'failed': failed_count,
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
            
            if pipeline_action == 'move':
                # Flujo de movimiento: cambiar el campo "path" de la definición
                # y enviar via PUT. El pipeline se reubica dentro de la estructura
                # de carpetas del proyecto en Azure DevOps.
                #
                # Soporta el placeholder {current} en el path destino:
                #   path: '\Decomiso{current}'
                # Si el path actual es '\GCP\Proyecto WMS', el resultado es
                # '\Decomiso\GCP\Proyecto WMS'.
                target_path = template_parser.get_pipeline_path()
                if not target_path:
                    raise ValueError("action 'move' requiere 'path' en update.pipeline")
                
                old_path = definition.get('path', '')
                
                # Resolver placeholder {current}
                if '{current}' in target_path:
                    target_path = target_path.replace('{current}', old_path)
                
                print(f"  [Pipeline {definition_id}] 4/5 Moviendo pipeline de '{old_path}' a '{target_path}'...")
                
                definition['path'] = target_path
                metadata = template_parser.get_metadata()
                success = azdo_client.update_release_definition(
                    definition_id, definition,
                    comment=metadata.comment
                )
                print(f"  [Pipeline {definition_id}]   ✓ Pipeline movido exitosamente")
                
                duration = time.time() - start_time
                
                return UpdateResult(
                    definition_id=definition_id,
                    success=success,
                    snapshot_id=snapshot_id,
                    matches_found=len(matches),
                    changes_applied=1,
                    changes=[{
                        'type': 'pipeline_move',
                        'definition_id': definition_id,
                        'old_path': old_path,
                        'new_path': target_path,
                        'snapshot_id': snapshot_id
                    }],
                    error=None,
                    duration=duration
                )
            
            if pipeline_action == 'autosort_stages':
                # Flujo de auto-ordenamiento: ordenar los stages fijos segun
                # el orden declarado en fixed_stages (por rank), ordenar los
                # stages numericos alfanumericamente, y renumerar todos los
                # ranks consecutivamente.
                sort_config = template_parser.get_pipeline_sort_config()
                fixed_stages = sort_config.get('fixed_stages', [])
                fixed_stage_names = sort_config.get('fixed_stage_names', set())
                sort_pattern = sort_config.get('sort_pattern', r'^\d+')
                sort_order = sort_config.get('sort_order', 'asc')
                
                environments = definition.get('environments', [])
                
                # Mapear stages por nombre para busqueda rapida
                env_map = {}
                for stage in environments:
                    env_map[stage.get('name', '')] = stage
                
                # Construir lista de stages fijos en el orden declarado (por rank)
                fixed = []
                for fs in fixed_stages:
                    name = fs['name']
                    if name in env_map:
                        fixed.append(env_map[name])
                
                # Separar stages ordenables y otros (excluyendo los fijos)
                sortable = []
                others = []
                compiled_pattern = re.compile(sort_pattern)
                
                for stage in environments:
                    name = stage.get('name', '')
                    if name in fixed_stage_names:
                        continue
                    elif compiled_pattern.search(name):
                        sortable.append(stage)
                    else:
                        others.append(stage)
                
                # Ordenar stages numericos alfanumericamente
                reverse = (sort_order == 'desc')
                sortable.sort(key=lambda s: s.get('name', ''), reverse=reverse)
                
                # Construir nuevo orden: fijos (en orden declarado) +
                # ordenables (sorted) + otros (en su orden original)
                new_environments = fixed + sortable + others
                
                # Renumerar ranks consecutivamente
                changes = []
                for i, stage in enumerate(new_environments):
                    old_rank = stage.get('rank')
                    new_rank = i + 1
                    if old_rank != new_rank:
                        stage['rank'] = new_rank
                        changes.append({
                            'type': 'stage_autosort',
                            'stage': stage.get('name', ''),
                            'old_rank': old_rank,
                            'new_rank': new_rank
                        })
                
                print(f"  [Pipeline {definition_id}] 4/5 Auto-ordenando {len(sortable)} stages numericos...")
                if changes:
                    print(f"  [Pipeline {definition_id}]   ✓ {len(changes)} stages reordenados")
                else:
                    print(f"  [Pipeline {definition_id}]   ✓ Sin cambios de orden necesarios")
                
                definition['environments'] = new_environments
                metadata = template_parser.get_metadata()
                success = azdo_client.update_release_definition(
                    definition_id, definition,
                    comment=metadata.comment
                )
                print(f"  [Pipeline {definition_id}]   ✓ Definicion guardada exitosamente")
                
                duration = time.time() - start_time
                
                return UpdateResult(
                    definition_id=definition_id,
                    success=success,
                    snapshot_id=snapshot_id,
                    matches_found=len(matches),
                    changes_applied=len(changes),
                    changes=changes,
                    error=None,
                    duration=duration
                )
            
            # 4. Aplicar actualizaciones (flujo normal)
            print(f"  [Pipeline {definition_id}] 4/5 Aplicando actualizaciones...")
            update_rules = template_parser.get_update_rules()
            template_options = template_parser.get_template_options()
            
            # Pre-procesar reglas copy_from: descargar pipeline origen y
            # convertir a action:add con definition embebida
            update_rules = self._resolve_copy_from_rules(
                update_rules, azdo_client, definition_id
            )
            
            update_engine = UpdateEngine(
                definition,
                matches,
                update_rules,
                template_options
            )
            success = update_engine.apply_updates()
            if not success:
                duration = time.time() - start_time
                return UpdateResult(
                    definition_id=definition_id,
                    success=False,
                    snapshot_id=snapshot_id,
                    matches_found=len(matches),
                    changes_applied=0,
                    changes=[],
                    error='apply_updates failed (ver logs arriba)',
                    duration=duration
                )
            changes_count = update_engine.get_changes_count()
            print(f"  [Pipeline {definition_id}]   ✓ Cambios aplicados: {changes_count}")
            
            # 5. Guardar cambios (skip si no hubo cambios)
            if changes_count == 0:
                print(f"  [Pipeline {definition_id}] 5/5 Sin cambios - omitiendo PUT a Azure DevOps")
                duration = time.time() - start_time
                return UpdateResult(
                    definition_id=definition_id,
                    success=True,
                    snapshot_id=snapshot_id,
                    matches_found=len(matches),
                    changes_applied=0,
                    changes=[],
                    error=None,
                    duration=duration
                )
            
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
    
    def _resolve_copy_from_rules(
        self,
        update_rules: Dict,
        azdo_client,
        target_definition_id: int
    ) -> Dict:
        """
        Pre-procesar reglas de stage con action: 'copy_from'.
        
        Descarga el pipeline origen (source_definition_id), extrae el stage
        fuente (source_stage), y lo convierte en una regla action:'add' con
        la definicion embebida. Asi el UpdateEngine lo procesa normalmente.
        
        Formato de regla copy_from en el template:
          - action: "copy_from"
            source_definition_id: 2758
            source_stage: "QA"
            new_name: "QA-Copia"
            position: "after"
            reference_stage: "Production"
            task_updates:
              - task_name: "Deploy to QA"
                fields:
                  - path: "inputs.namespace"
                    new_value: "qa-copia"
        
        Args:
            update_rules: Reglas de actualizacion del template
            azdo_client: Cliente de Azure DevOps
            target_definition_id: ID del pipeline destino (para logging)
        
        Returns:
            Reglas de actualizacion con copy_from resueltas como add
        """
        stage_rules = update_rules.get('stages', [])
        if not stage_rules:
            return update_rules
        
        new_stage_rules = []
        for rule in stage_rules:
            if rule.get('action') != 'copy_from':
                new_stage_rules.append(rule)
                continue
            
            source_def_id = rule.get('source_definition_id')
            source_stage_name = rule.get('source_stage')
            new_name = rule.get('new_name') or rule.get('name')
            
            if not source_def_id or not source_stage_name or not new_name:
                raise ValueError(
                    "action 'copy_from' requiere 'source_definition_id', "
                    "'source_stage' y 'new_name'"
                )
            
            print(f"  [Pipeline {target_definition_id}]   "
                  f"Descargando pipeline origen {source_def_id}...")
            
            source_definition = azdo_client.get_release_definition(source_def_id)
            source_environments = source_definition.get('environments', [])
            
            source_stage = None
            for stage in source_environments:
                if stage.get('name', '') == source_stage_name:
                    source_stage = stage
                    break
            
            if source_stage is None:
                raise ValueError(
                    f"source_stage '{source_stage_name}' no encontrado en "
                    f"pipeline {source_def_id}"
                )
            
            stage_def = copy.deepcopy(source_stage)
            
            new_rule = {
                'action': 'add',
                'name': new_name,
                'definition': stage_def,
                'position': rule.get('position', 'after'),
            }
            
            if rule.get('reference_stage'):
                new_rule['reference_stage'] = rule['reference_stage']
            if rule.get('after_stage'):
                new_rule['after_stage'] = rule['after_stage']
            if rule.get('before_stage'):
                new_rule['before_stage'] = rule['before_stage']
            if rule.get('task_updates'):
                new_rule['task_updates'] = rule['task_updates']
            if rule.get('trigger') is not None:
                new_rule['trigger'] = rule['trigger']
            if rule.get('make_dependents'):
                new_rule['make_dependents'] = rule['make_dependents']
            
            new_stage_rules.append(new_rule)
            
            print(f"  [Pipeline {target_definition_id}]   "
                  f"✓ Stage '{source_stage_name}' copiado desde pipeline "
                  f"{source_def_id} como '{new_name}'")
        
        update_rules = dict(update_rules)
        update_rules['stages'] = new_stage_rules
        return update_rules
    
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
