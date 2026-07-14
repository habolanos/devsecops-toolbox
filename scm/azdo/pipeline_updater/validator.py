"""
Validador de templates para Pipeline Updater
"""

from typing import Dict, List


class TemplateValidator:
    """Validador de estructura de templates"""
    
    def __init__(self, template: Dict):
        """
        Inicializar validador
        
        Args:
            template: Diccionario del template a validar
        """
        self.template = template
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self) -> bool:
        """
        Validar template completo
        
        Returns:
            True si el template es válido, False en caso contrario
        """
        self.errors = []
        self.warnings = []
        
        self._validate_metadata()
        self._validate_search()
        self._validate_update()
        self._validate_options()
        
        return len(self.errors) == 0
    
    def _validate_metadata(self):
        """Validar sección metadata"""
        meta = self.template.get('metadata', {})
        
        if not meta:
            self.errors.append("metadata es obligatorio")
            return
        
        if not meta.get('name'):
            self.errors.append("metadata.name es obligatorio")
        
        if not meta.get('version'):
            self.errors.append("metadata.version es obligatorio")
        
        if not isinstance(meta.get('name'), str):
            self.errors.append("metadata.name debe ser string")
        
        if not isinstance(meta.get('version'), str):
            self.errors.append("metadata.version debe ser string")
    
    def _validate_search(self):
        """Validar sección search"""
        search = self.template.get('search', {})
        
        if not search:
            self.errors.append("search no puede estar vacío")
            return
        
        if not isinstance(search, dict):
            self.errors.append("search debe ser un diccionario")
            return
        
        # Validar que al menos hay una regla de búsqueda
        has_rules = any([
            search.get('stages'),
            search.get('tasks'),
            search.get('variables'),
            search.get('artifacts')
        ])
        
        if not has_rules:
            self.warnings.append("search no contiene ninguna regla de búsqueda")
    
    def _validate_update(self):
        """Validar sección update"""
        update = self.template.get('update', {})
        
        if not update:
            self.errors.append("update no puede estar vacío")
            return
        
        if not isinstance(update, dict):
            self.errors.append("update debe ser un diccionario")
            return
        
        # Validar que al menos hay una regla de actualización
        has_rules = any([
            update.get('stages'),
            update.get('tasks'),
            update.get('variables')
        ])
        
        if not has_rules:
            self.warnings.append("update no contiene ninguna regla de actualización")
    
    def _validate_options(self):
        """Validar sección options"""
        options = self.template.get('options', {})
        
        if not isinstance(options, dict):
            self.errors.append("options debe ser un diccionario")
            return
        
        # Validar tipos de opciones
        if 'dry_run' in options and not isinstance(options['dry_run'], bool):
            self.errors.append("options.dry_run debe ser booleano")
        
        if 'rollback_on_error' in options and not isinstance(options['rollback_on_error'], bool):
            self.errors.append("options.rollback_on_error debe ser booleano")
    
    def get_errors(self) -> List[str]:
        """Obtener lista de errores"""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """Obtener lista de advertencias"""
        return self.warnings
    
    def is_valid(self) -> bool:
        """Verificar si el template es válido"""
        return len(self.errors) == 0
