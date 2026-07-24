"""
Motor de actualización para Pipeline Updater
"""

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
            # Primero aplicar reordenamiento de stages si existe
            stage_rules = self.update_rules.get('stages', [])
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
            # Obtener índices de stages que NO están siendo reordenados
            reorder_names = {name for _, _, name in stages_to_reorder}
            other_stages = [s for s in environments if s.get('name', '') not in reorder_names]
            
            # Reconstruir lista de environments
            new_environments = []
            for stage, rank, name in stages_to_reorder:
                new_environments.append(stage)
            new_environments.extend(other_stages)
            
            self.definition['environments'] = new_environments
            
            # Registrar cambios
            for stage, rank, name in stages_to_reorder:
                self.changes.append({
                    'type': 'stage_reorder',
                    'stage': name,
                    'new_rank': rank
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
