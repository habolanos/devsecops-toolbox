"""
Motor de búsqueda para Pipeline Updater
"""

from typing import Dict, List, Optional
from .models import Match


class SearchEngine:
    """Motor de búsqueda en definiciones de release"""
    
    def __init__(self, definition: Dict, search_rules: Dict):
        """
        Inicializar motor de búsqueda
        
        Args:
            definition: Definición de release
            search_rules: Reglas de búsqueda
        """
        self.definition = definition
        self.search_rules = search_rules
        self.matches: List[Match] = []
    
    def search_all(self) -> List[Match]:
        """
        Ejecutar todas las búsquedas
        
        Returns:
            Lista de coincidencias encontradas
        """
        self.matches = []
        
        # Validar exact_match si está habilitado
        if self.search_rules.get('exact_match', False):
            if not self._validate_exact_match():
                return []  # No hay coincidencias si exact_match falla
        
        self.matches.extend(self.search_stages(self.search_rules.get('stages', [])))
        self.matches.extend(self.search_tasks(self.search_rules.get('tasks', [])))
        self.matches.extend(self.search_variables(self.search_rules.get('variables', [])))
        self.matches.extend(self.search_artifacts(self.search_rules.get('artifacts', [])))
        
        return self.matches
    
    def search_stages(self, stage_names: List[str]) -> List[Match]:
        """
        Buscar stages por nombre
        
        Args:
            stage_names: Lista de nombres de stages a buscar
            
        Returns:
            Lista de coincidencias
        """
        matches = []
        
        for stage in self.definition.get('environments', []):
            stage_name = stage.get('name', '')
            
            for search_name in stage_names:
                if self._matches_pattern(stage_name, search_name):
                    matches.append(Match(
                        type='stage',
                        name=stage_name,
                        location=f"environments[{stage.get('id')}]",
                        object=stage,
                        stage_name=stage_name
                    ))
                    break
        
        return matches
    
    def search_tasks(self, task_criteria: List[Dict]) -> List[Match]:
        """
        Buscar tasks por criterios
        
        Args:
            task_criteria: Lista de criterios de búsqueda
            
        Returns:
            Lista de coincidencias
        """
        matches = []
        
        for env_idx, stage in enumerate(self.definition.get('environments', [])):
            stage_name = stage.get('name', '')
            
            for phase_idx, phase in enumerate(stage.get('deployPhases', [])):
                for task_idx, task in enumerate(phase.get('deploymentInput', {}).get('tasks', [])):
                    task_name = task.get('displayName', '')
                    
                    for criteria in task_criteria:
                        if self._task_matches(task, criteria):
                            matches.append(Match(
                                type='task',
                                name=task_name,
                                location=f"environments[{env_idx}].deployPhases[{phase_idx}].deploymentInput.tasks[{task_idx}]",
                                object=task,
                                stage_name=stage_name
                            ))
                            break
        
        return matches
    
    def search_variables(self, var_names: List[str]) -> List[Match]:
        """
        Buscar variables por nombre
        
        Args:
            var_names: Lista de nombres de variables a buscar
            
        Returns:
            Lista de coincidencias
        """
        matches = []
        
        variables = self.definition.get('variables', {})
        
        for var_name, var_obj in variables.items():
            for search_name in var_names:
                if self._matches_pattern(var_name, search_name):
                    matches.append(Match(
                        type='variable',
                        name=var_name,
                        location=f"variables.{var_name}",
                        object=var_obj
                    ))
                    break
        
        return matches
    
    def search_artifacts(self, artifact_criteria: List[Dict]) -> List[Match]:
        """
        Buscar artifacts por criterios
        
        Args:
            artifact_criteria: Lista de criterios de búsqueda
            
        Returns:
            Lista de coincidencias
        """
        matches = []
        
        artifacts = self.definition.get('artifacts', [])
        
        for art_idx, artifact in enumerate(artifacts):
            artifact_name = artifact.get('alias', '')
            
            for criteria in artifact_criteria:
                if self._artifact_matches(artifact, criteria):
                    matches.append(Match(
                        type='artifact',
                        name=artifact_name,
                        location=f"artifacts[{art_idx}]",
                        object=artifact
                    ))
                    break
        
        return matches
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """
        Verificar si texto coincide con patrón
        
        Soporta:
        - Coincidencia exacta: "name"
        - Contiene: "*name*"
        - Comienza con: "name*"
        - Termina con: "*name"
        
        Args:
            text: Texto a verificar
            pattern: Patrón de búsqueda
            
        Returns:
            True si coincide
        """
        if pattern == text:
            return True
        
        if pattern.startswith('*') and pattern.endswith('*'):
            return pattern[1:-1] in text
        elif pattern.startswith('*'):
            return text.endswith(pattern[1:])
        elif pattern.endswith('*'):
            return text.startswith(pattern[:-1])
        
        return False
    
    def _task_matches(self, task: Dict, criteria: Dict) -> bool:
        """
        Verificar si task coincide con criterios
        
        Args:
            task: Objeto task
            criteria: Criterios de búsqueda
            
        Returns:
            True si coincide
        """
        # Verificar nombre
        task_name = task.get('displayName', '')
        criteria_name = criteria.get('name', '')
        
        if criteria_name and not self._matches_pattern(task_name, criteria_name):
            return False
        
        # Verificar tipo
        task_type = task.get('task', {}).get('definitionType', '')
        criteria_type = criteria.get('type', '')
        
        if criteria_type and task_type != criteria_type:
            return False
        
        return True
    
    def _artifact_matches(self, artifact: Dict, criteria: Dict) -> bool:
        """
        Verificar si artifact coincide con criterios
        
        Args:
            artifact: Objeto artifact
            criteria: Criterios de búsqueda
            
        Returns:
            True si coincide
        """
        # Verificar alias
        artifact_alias = artifact.get('alias', '')
        criteria_alias = criteria.get('alias', '')
        
        if criteria_alias and not self._matches_pattern(artifact_alias, criteria_alias):
            return False
        
        # Verificar tipo
        artifact_type = artifact.get('type', '')
        criteria_type = criteria.get('type', '')
        
        if criteria_type and artifact_type != criteria_type:
            return False
        
        return True
    
    def get_matches(self) -> List[Match]:
        """Obtener todas las coincidencias"""
        return self.matches
    
    def get_matches_by_type(self, match_type: str) -> List[Match]:
        """
        Obtener coincidencias por tipo
        
        Args:
            match_type: Tipo de coincidencia (stage, task, variable, artifact)
            
        Returns:
            Lista de coincidencias del tipo especificado
        """
        return [m for m in self.matches if m.type == match_type]
    
    def _validate_exact_match(self) -> bool:
        """
        Validar que el pipeline tenga EXACTAMENTE los stages especificados
        
        Returns:
            True si el pipeline tiene exactamente los stages, False si no
        """
        search_stages = self.search_rules.get('stages', [])
        
        # Si no hay stages en search, no validar exact_match
        if not search_stages:
            return True
        
        # Obtener stages del pipeline
        pipeline_stages = [stage.get('name', '') for stage in self.definition.get('environments', [])]
        
        # Verificar que el pipeline tiene EXACTAMENTE los stages buscados
        if len(pipeline_stages) != len(search_stages):
            return False
        
        # Verificar que todos los stages buscados existen en el pipeline
        for search_stage in search_stages:
            found = False
            for pipeline_stage in pipeline_stages:
                if self._matches_pattern(pipeline_stage, search_stage):
                    found = True
                    break
            if not found:
                return False
        
        # Verificar que NO hay stages adicionales
        for pipeline_stage in pipeline_stages:
            found = False
            for search_stage in search_stages:
                if self._matches_pattern(pipeline_stage, search_stage):
                    found = True
                    break
            if not found:
                return False
        
        return True
