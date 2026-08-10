"""
Parser de templates YAML para Pipeline Updater
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Optional
from .models import TemplateMetadata, SearchRule, UpdateRule, TemplateOptions, IgnoreVariableGroups, ReplaceAgentPools


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
    
    def get_pipeline_action(self) -> Optional[str]:
        """
        Obtener acción a nivel de pipeline (no stage).
        
        Soporta:
          - None: actualización normal (default)
          - "disable": eliminar (soft-delete) el pipeline
          - "move": mover el pipeline a otra carpeta (cambiar path)
        
        Returns:
            Acción del pipeline o None
        """
        pipeline = self.update_rules.get('pipeline', {})
        if isinstance(pipeline, dict):
            return pipeline.get('action')
        return None
    
    def get_pipeline_path(self) -> Optional[str]:
        """
        Obtener el path destino para la acción "move".
        
        Returns:
            Path destino o None si no se especifica
        """
        pipeline = self.update_rules.get('pipeline', {})
        if isinstance(pipeline, dict):
            return pipeline.get('path')
        return None
    
    def get_pipeline_sort_config(self) -> Dict:
        r"""
        Obtener configuracion para la accion 'autosort_stages'.

        Acepta dos formatos para fixed_stages:

        1. Lista simple de strings (orden = orden de la lista):
           fixed_stages:
             - "Develop"
             - "QA"
             - "Production"

        2. Lista de dicts con name y rank (orden = por rank ascendente):
           fixed_stages:
             - name: "SCM Inspection"
               rank: 1
             - name: "Develop"
               rank: 2

        Returns:
            Diccionario con:
              - fixed_stages: lista de dicts [{'name': str, 'rank': int}, ...]
                ordenados por rank. Si no hay rank, se asigna por posicion.
              - fixed_stage_names: set de nombres de stages fijos
              - sort_pattern: regex para identificar stages a ordenar (default: r'^\d+')
              - sort_order: 'asc' o 'desc' (default: 'asc')
        """
        pipeline = self.update_rules.get('pipeline', {})
        if not isinstance(pipeline, dict):
            return {}

        raw_fixed = pipeline.get('fixed_stages', [])
        fixed_stages = []
        for idx, item in enumerate(raw_fixed):
            if isinstance(item, str):
                fixed_stages.append({'name': item, 'rank': idx + 1})
            elif isinstance(item, dict):
                name = item.get('name', '')
                rank = item.get('rank', idx + 1)
                fixed_stages.append({'name': name, 'rank': rank})

        fixed_stages.sort(key=lambda x: x['rank'])

        return {
            'fixed_stages': fixed_stages,
            'fixed_stage_names': {fs['name'] for fs in fixed_stages},
            'sort_pattern': pipeline.get('sort_pattern', r'^\d+'),
            'sort_order': pipeline.get('sort_order', 'asc')
        }

    def get_template_options(self) -> TemplateOptions:
        """Obtener opciones como objeto TemplateOptions"""
        raw_ignore = self.options.get('ignore_variable_groups', [])
        ignore_vg = self._parse_ignore_variable_groups(raw_ignore)
        raw_replace_pools = self.options.get('replace_agent_pools', {})
        replace_pools = self._parse_replace_agent_pools(raw_replace_pools)
        return TemplateOptions(
            dry_run=self.options.get('dry_run', False),
            rollback_on_error=self.options.get('rollback_on_error', True),
            ignore_variable_groups=ignore_vg,
            replace_agent_pools=replace_pools
        )

    @staticmethod
    def _parse_ignore_variable_groups(raw) -> IgnoreVariableGroups:
        """
        Parsear ignore_variable_groups desde el template.
        
        Acepta dos formatos:
        
        1. Lista simple (remueve de ambos niveles):
           ignore_variable_groups: [186, 196]
        
        2. Diferenciado por scope:
           ignore_variable_groups:
             global: [186]         # Solo nivel global del pipeline
             environments: [196]   # Solo nivel de environments/stages
             all: [200]            # Ambos niveles
        """
        if not raw:
            return IgnoreVariableGroups()
        
        if isinstance(raw, list):
            return IgnoreVariableGroups(all_ids=raw)
        
        if isinstance(raw, dict):
            return IgnoreVariableGroups(
                global_ids=raw.get('global', []),
                environment_ids=raw.get('environments', []),
                all_ids=raw.get('all', [])
            )
        
        return IgnoreVariableGroups()

    @staticmethod
    def _parse_replace_agent_pools(raw) -> ReplaceAgentPools:
        """
        Parsear replace_agent_pools desde el template.

        Formato:
          replace_agent_pools:
            1751: 100    # Reemplazar pool 1751 con pool 100
            2722: 200    # Reemplazar pool 2722 con pool 200
        """
        if not raw or not isinstance(raw, dict):
            return ReplaceAgentPools()

        mappings = {}
        for old_id, new_id in raw.items():
            try:
                mappings[int(old_id)] = int(new_id)
            except (ValueError, TypeError):
                continue

        return ReplaceAgentPools(mappings=mappings)

    def to_dict(self) -> Dict:
        """Convertir template a diccionario"""
        return self.template
    
    def to_json(self) -> str:
        """Convertir template a JSON"""
        return json.dumps(self.template, indent=2)
