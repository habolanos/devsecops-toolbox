"""
Motor de actualización para Pipeline Updater
"""

import copy
import fnmatch
from typing import Dict, List, Any
from .models import Match


class UpdateEngine:
    """Motor de actualización de definiciones de release"""
    
    def __init__(self, definition: Dict, matches: List[Match], update_rules: Dict):
        """
        Inicializar motor de actualización
        
        Args:
            definition: Definición de release
            matches: Coincidencias encontradas
            update_rules: Reglas de actualización
        """
        self.definition = definition
        self.matches = matches
        self.update_rules = update_rules
        self.changes: List[Dict] = []
    
    def apply_updates(self) -> bool:
        """
        Aplicar todas las actualizaciones
        
        Returns:
            True si todas las actualizaciones fueron exitosas
        """
        try:
            stage_rules = self.update_rules.get('stages', [])
            
            # Primero procesar acciones de stage (copy/add/rename) que modifican stages
            if stage_rules and any(rule.get('action') in ('copy', 'add', 'rename') for rule in stage_rules):
                self._process_stage_actions(stage_rules)
            
            # Luego aplicar reordenamiento de stages si existe
            if stage_rules and any(rule.get('rank') for rule in stage_rules):
                self._reorder_stages(stage_rules)
            
            # Luego aplicar otras actualizaciones
            for match in self.matches:
                if match.type == 'task':
                    self._update_task(match)
                elif match.type == 'variable':
                    self._update_variable(match)
                elif match.type == 'stage':
                    self._update_stage(match)
                elif match.type == 'artifact':
                    self._update_artifact(match)
            
            return True
        except Exception as e:
            print(f"Error al aplicar actualizaciones: {e}")
            return False
    
    def _reorder_stages(self, stage_rules: List[Dict]):
        """
        Reordenar stages según las reglas
        
        Args:
            stage_rules: Reglas de actualización de stages con rank
        """
        environments = self.definition.get('environments', [])
        
        # Crear mapeo de nombre -> stage y rank
        stage_map = {}
        for rule in stage_rules:
            stage_name = rule.get('name', '')
            rank = rule.get('rank')
            if stage_name and rank is not None:
                stage_map[stage_name] = rank
        
        # Encontrar stages que necesitan reordenamiento
        stages_to_reorder = []
        for stage in environments:
            stage_name = stage.get('name', '')
            if stage_name in stage_map:
                stages_to_reorder.append((stage, stage_map[stage_name], stage_name))
        
        # Ordenar por rank
        stages_to_reorder.sort(key=lambda x: x[1])
        
        # Reordenar en la definición
        if stages_to_reorder:
            # IMPORTANTE: En Azure DevOps el orden de los stages lo determina el
            # campo 'rank' de cada environment, NO la posición en el array. Por eso
            # se DEBE asignar el nuevo rank a cada stage; reordenar solo el array no
            # tiene efecto porque el servidor reordena por 'rank'.
            for stage, rank, name in stages_to_reorder:
                old_rank = stage.get('rank')
                stage['rank'] = rank
                
                self.changes.append({
                    'type': 'stage_reorder',
                    'stage': name,
                    'old_rank': old_rank,
                    'new_rank': rank
                })
            
            # Reordenar también el array por rank (por consistencia/legibilidad)
            reorder_names = {name for _, _, name in stages_to_reorder}
            other_stages = [s for s in environments if s.get('name', '') not in reorder_names]
            
            new_environments = [stage for stage, _, _ in stages_to_reorder]
            new_environments.extend(other_stages)
            
            self.definition['environments'] = new_environments
    
    def _process_stage_actions(self, stage_rules: List[Dict]):
        """
        Procesar acciones de stage que modifican o insertan environments.
        
        Soporta:
          - action: "copy"  -> Copia un stage existente (source_stage) y lo inserta
                               con un nuevo nombre (new_name).
          - action: "add"   -> Inserta un stage nuevo desde una definición embebida.
          - action: "rename" -> Renombra un stage existente (source_stage) a new_name.
        
        Parámetros de la regla:
          - action: "copy"
          - source_stage: nombre del stage a copiar (obligatorio)
          - new_name: nombre del nuevo stage insertado (obligatorio)
          - position: "after" | "before" | "start" | "end" (default: "after")
          - reference_stage: stage ancla para after/before (default: source_stage)
          - task_updates: lista opcional de modificaciones a tasks del stage copiado:
                - task_name: displayName de la task (soporta comodines)
                  fields:
                    - path: "inputs.namespace"
                      new_value: "..."
        
          - action: "add"
          - name: nombre del nuevo stage (obligatorio)
          - definition: definición completa del stage (obligatorio)
          - position: "after" | "before" | "between" | "start" | "end"
          - after_stage / before_stage: para position "between"
        
          - action: "rename"
          - source_stage: nombre del stage a renombrar (obligatorio)
          - new_name: nuevo nombre del stage (obligatorio)
        
        Args:
            stage_rules: Reglas de actualización de stages
        """
        for rule in stage_rules:
            action = rule.get('action')
            if action == 'copy':
                self._copy_stage(rule)
            elif action == 'add':
                self._add_stage(rule)
            elif action == 'rename':
                self._rename_stage(rule)
    
    def _copy_stage(self, rule: Dict):
        """Copiar un stage existente e insertarlo con un nuevo nombre."""
        environments = self.definition.get('environments', [])
        
        source_name = rule.get('source_stage')
        new_name = rule.get('new_name') or rule.get('name')
        
        if not source_name or not new_name:
            raise ValueError("action 'copy' requiere 'source_stage' y 'new_name'")
        
        # Localizar el stage origen
        source_stage = None
        for stage in environments:
            if stage.get('name', '') == source_name:
                source_stage = stage
                break
        
        if source_stage is None:
            raise ValueError(f"source_stage '{source_name}' no encontrado en el pipeline")
        
        # Clonar y renombrar
        new_stage = copy.deepcopy(source_stage)
        new_stage['name'] = new_name
        new_stage['id'] = self._next_environment_id(environments)
        
        # Aplicar modificaciones de tasks al stage copiado
        task_updates = rule.get('task_updates', [])
        if task_updates:
            self._apply_task_updates_to_stage(new_stage, task_updates, new_name)
        
        # Determinar posición de inserción
        insert_index = self._resolve_insert_index(environments, rule, source_name)
        environments.insert(insert_index, new_stage)
        
        # Reasignar ranks según el orden del array (rank gobierna el orden en AzDO)
        self._resequence_ranks(environments)
        
        self.definition['environments'] = environments
        
        self.changes.append({
            'type': 'stage_copy',
            'source_stage': source_name,
            'new_stage': new_name,
            'position_index': insert_index,
            'new_rank': new_stage.get('rank')
        })
    
    def _add_stage(self, rule: Dict):
        """Insertar un stage nuevo a partir de una definición embebida."""
        environments = self.definition.get('environments', [])
        
        definition = rule.get('definition')
        new_name = rule.get('name') or (definition.get('name') if definition else None)
        
        if not definition or not new_name:
            raise ValueError("action 'add' requiere 'definition' y 'name'")
        
        new_stage = copy.deepcopy(definition)
        new_stage['name'] = new_name
        new_stage['id'] = self._next_environment_id(environments)
        
        insert_index = self._resolve_insert_index(
            environments, rule, rule.get('after_stage')
        )
        environments.insert(insert_index, new_stage)
        
        self._resequence_ranks(environments)
        self.definition['environments'] = environments
        
        self.changes.append({
            'type': 'stage_add',
            'new_stage': new_name,
            'position_index': insert_index,
            'new_rank': new_stage.get('rank')
        })
    
    def _rename_stage(self, rule: Dict):
        """Renombrar un stage existente."""
        environments = self.definition.get('environments', [])
        
        source_name = rule.get('source_stage')
        new_name = rule.get('new_name')
        
        if not source_name or not new_name:
            raise ValueError("action 'rename' requiere 'source_stage' y 'new_name'")
        
        # Localizar el stage a renombrar
        stage_found = False
        for stage in environments:
            if stage.get('name', '') == source_name:
                old_name = stage['name']
                stage['name'] = new_name
                stage_found = True
                
                self.changes.append({
                    'type': 'stage_rename',
                    'old_name': old_name,
                    'new_name': new_name
                })
                break
        
        if not stage_found:
            raise ValueError(f"source_stage '{source_name}' no encontrado en el pipeline")
        
        self.definition['environments'] = environments
    
    def _resolve_insert_index(self, environments: List[Dict], rule: Dict, default_ref: str) -> int:
        """
        Resolver el índice de inserción en el array de environments.
        
        position: "after" (default) | "before" | "between" | "start" | "end"
        reference_stage / after_stage / before_stage: stage ancla.
        
        Para "between": requiere after_stage y before_stage.
        """
        position = (rule.get('position') or 'after').lower()
        
        if position == 'start':
            return 0
        if position == 'end':
            return len(environments)
        
        if position == 'between':
            after_stage = rule.get('after_stage')
            before_stage = rule.get('before_stage')
            if not after_stage or not before_stage:
                raise ValueError("position 'between' requiere 'after_stage' y 'before_stage'")
            
            after_index = None
            before_index = None
            for idx, stage in enumerate(environments):
                name = stage.get('name', '')
                if name == after_stage:
                    after_index = idx
                if name == before_stage:
                    before_index = idx
            
            # Si no se encuentran ambos, insertar al final
            if after_index is None or before_index is None:
                return len(environments)
            
            # Insertar justo después de after_stage (antes de before_stage)
            return after_index + 1
        
        reference = (
            rule.get('reference_stage')
            or rule.get('after_stage')
            or rule.get('before_stage')
            or default_ref
        )
        
        ref_index = None
        for idx, stage in enumerate(environments):
            if stage.get('name', '') == reference:
                ref_index = idx
                break
        
        # Si no se encuentra la referencia, insertar al final
        if ref_index is None:
            return len(environments)
        
        if position == 'before':
            return ref_index
        # default: after
        return ref_index + 1
    
    def _next_environment_id(self, environments: List[Dict]) -> int:
        """Obtener un id único para un nuevo environment (max existente + 1)."""
        max_id = 0
        for stage in environments:
            sid = stage.get('id')
            if isinstance(sid, int) and sid > max_id:
                max_id = sid
        return max_id + 1
    
    def _resequence_ranks(self, environments: List[Dict]):
        """Reasignar ranks secuenciales (1..N) según el orden actual del array."""
        for idx, stage in enumerate(environments):
            stage['rank'] = idx + 1
    
    def _apply_task_updates_to_stage(self, stage: Dict, task_updates: List[Dict], stage_name: str):
        """
        Aplicar modificaciones de atributos a tasks dentro de un stage.
        
        Args:
            stage: Stage (environment) sobre el que aplicar cambios
            task_updates: Lista de reglas {task_name, fields:[{path, new_value}]}
            stage_name: Nombre del stage (para el registro de cambios)
        """
        for phase in stage.get('deployPhases', []):
            tasks = phase.get('deploymentInput', {}).get('tasks', [])
            for task in tasks:
                display_name = task.get('displayName', '')
                for tu in task_updates:
                    task_name = tu.get('task_name', tu.get('name', ''))
                    if task_name and not fnmatch.fnmatch(display_name, task_name):
                        continue
                    for field_update in tu.get('fields', []):
                        path = field_update.get('path')
                        new_value = field_update.get('new_value')
                        old_value = self._get_nested_value(task, path)
                        self._set_nested_value(task, path, new_value)
                        
                        self.changes.append({
                            'type': 'copied_task_field',
                            'stage': stage_name,
                            'task': display_name,
                            'field': path,
                            'old': old_value,
                            'new': new_value
                        })
    
    def _update_task(self, match: Match):
        """
        Actualizar una task
        
        Args:
            match: Coincidencia de task
        """
        task = match.object
        task_rules = self.update_rules.get('tasks', [])
        
        for rule in task_rules:
            if self._rule_matches_match(rule, match):
                # Actualizar campos
                for field_update in rule.get('fields', []):
                    path = field_update.get('path')
                    new_value = field_update.get('new_value')
                    old_value = self._get_nested_value(task, path)
                    
                    self._set_nested_value(task, path, new_value)
                    
                    self.changes.append({
                        'type': 'task_field',
                        'stage': match.stage_name,
                        'task': match.name,
                        'field': path,
                        'old': old_value,
                        'new': new_value
                    })
    
    def _update_variable(self, match: Match):
        """
        Actualizar una variable
        
        Args:
            match: Coincidencia de variable
        """
        var = match.object
        var_rules = self.update_rules.get('variables', [])
        
        for rule in var_rules:
            if self._rule_matches_match(rule, match):
                old_value = var.get('value')
                new_value = rule.get('new_value')
                
                var['value'] = new_value
                
                self.changes.append({
                    'type': 'variable',
                    'name': match.name,
                    'old': old_value,
                    'new': new_value
                })
    
    def _update_stage(self, match: Match):
        """
        Actualizar un stage
        
        Args:
            match: Coincidencia de stage
        """
        stage = match.object
        stage_rules = self.update_rules.get('stages', [])
        
        for rule in stage_rules:
            if self._rule_matches_match(rule, match):
                # Actualizar propiedades del stage
                for prop_update in rule.get('properties', []):
                    path = prop_update.get('path')
                    new_value = prop_update.get('new_value')
                    old_value = self._get_nested_value(stage, path)
                    
                    self._set_nested_value(stage, path, new_value)
                    
                    self.changes.append({
                        'type': 'stage_property',
                        'stage': match.name,
                        'property': path,
                        'old': old_value,
                        'new': new_value
                    })
    
    def _update_artifact(self, match: Match):
        """
        Actualizar un artifact
        
        Args:
            match: Coincidencia de artifact
        """
        artifact = match.object
        artifact_rules = self.update_rules.get('artifacts', [])
        
        for rule in artifact_rules:
            if self._rule_matches_match(rule, match):
                # Actualizar propiedades del artifact
                for prop_update in rule.get('properties', []):
                    path = prop_update.get('path')
                    new_value = prop_update.get('new_value')
                    old_value = self._get_nested_value(artifact, path)
                    
                    self._set_nested_value(artifact, path, new_value)
                    
                    self.changes.append({
                        'type': 'artifact_property',
                        'artifact': match.name,
                        'property': path,
                        'old': old_value,
                        'new': new_value
                    })
    
    def _rule_matches_match(self, rule: Dict, match: Match) -> bool:
        """
        Verificar si una regla coincide con un match
        
        Args:
            rule: Regla de actualización
            match: Coincidencia
            
        Returns:
            True si la regla aplica al match
        """
        rule_name = rule.get('name', '')
        
        if rule_name and rule_name != match.name:
            return False
        
        return True
    
    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """
        Obtener valor en ruta anidada
        
        Args:
            obj: Diccionario
            path: Ruta (ej: "inputs.imageRepository")
            
        Returns:
            Valor en la ruta
        """
        keys = path.split('.')
        current = obj
        
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        
        return current
    
    def _set_nested_value(self, obj: Dict, path: str, value: Any):
        """
        Establecer valor en ruta anidada
        
        Args:
            obj: Diccionario
            path: Ruta (ej: "inputs.imageRepository")
            value: Nuevo valor
        """
        keys = path.split('.')
        current = obj
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def get_changes(self) -> List[Dict]:
        """Obtener lista de cambios realizados"""
        return self.changes
    
    def get_changes_count(self) -> int:
        """Obtener cantidad de cambios realizados"""
        return len(self.changes)
