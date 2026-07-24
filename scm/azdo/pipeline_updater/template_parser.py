"""
Parser de templates YAML para Pipeline Updater
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Optional
from .models import TemplateMetadata, SearchRule, UpdateRule


class TemplateParser:
    """Parser de templates YAML/JSON"""
    
    def __init__(self, template_path: str):
        """
        Inicializar parser
        
        Args:
            template_path: Ruta al archivo de template
        """
        self.template_path = Path(template_path)
        self.template = self._load_template()
        self.metadata = self.template.get('metadata', {})
        self.search_rules = self.template.get('search', {})
        self.update_rules = self.template.get('update', {})
        self.options = self.template.get('options', {})
    
    def _load_template(self) -> Dict:
        """Cargar template desde archivo YAML o JSON"""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template no encontrado: {self.template_path}")
        
        content = self.template_path.read_text(encoding='utf-8')
        
        if self.template_path.suffix in ['.yaml', '.yml']:
            return yaml.safe_load(content)
        elif self.template_path.suffix == '.json':
            return json.loads(content)
        else:
            raise ValueError(f"Formato no soportado: {self.template_path.suffix}")
    
    def validate(self) -> bool:
        """Validar estructura del template"""
        required = ['metadata', 'search', 'update']
        return all(k in self.template for k in required)
    
    def get_metadata(self) -> TemplateMetadata:
        """Obtener metadata del template"""
        meta = self.metadata
        return TemplateMetadata(
            name=meta.get('name', 'Unknown'),
            version=meta.get('version', '1.0'),
            description=meta.get('description'),
            comment=meta.get('comment'),
            author=meta.get('author'),
            created_at=meta.get('created_at'),
            updated_at=meta.get('updated_at')
        )
    
    def get_search_rules(self) -> Dict:
        """Obtener reglas de búsqueda"""
        return self.search_rules
    
    def get_update_rules(self) -> Dict:
        """Obtener reglas de actualización"""
        return self.update_rules
    
    def get_options(self) -> Dict:
        """Obtener opciones"""
        return self.options
    
    def get_dry_run(self) -> bool:
        """Obtener opción dry_run"""
        return self.options.get('dry_run', False)
    
    def get_rollback_on_error(self) -> bool:
        """Obtener opción rollback_on_error"""
        return self.options.get('rollback_on_error', True)
    
    def to_dict(self) -> Dict:
        """Convertir template a diccionario"""
        return self.template
    
    def to_json(self) -> str:
        """Convertir template a JSON"""
        return json.dumps(self.template, indent=2)
