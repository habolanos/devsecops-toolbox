#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo Avanzado de Búsqueda Interactiva

Extensión de search_module.py con:
- Filtros avanzados (grupo, plataforma, estado)
- Historial de búsquedas
- Autocompletado
- Sugerencias inteligentes
- Paginación de resultados
"""

import sys
import os
from typing import Dict, List, Optional, Tuple, Set
from difflib import SequenceMatcher
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.box import ROUNDED
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

# ═══════════════════════════════════════════════════════════════════════════════
# HISTORIAL Y CACHÉ
# ═══════════════════════════════════════════════════════════════════════════════

class SearchHistory:
    """Gestiona el historial de búsquedas."""
    
    def __init__(self, max_items: int = 20):
        """
        Inicializa el historial.
        
        Args:
            max_items: Número máximo de items a guardar
        """
        self.max_items = max_items
        self.history: List[str] = []
        self._load_from_file()
    
    def add(self, query: str) -> None:
        """Agrega una búsqueda al historial."""
        if query and query not in self.history:
            self.history.insert(0, query)
            if len(self.history) > self.max_items:
                self.history.pop()
            self._save_to_file()
    
    def get_suggestions(self, prefix: str) -> List[str]:
        """Retorna sugerencias basadas en el prefijo."""
        return [q for q in self.history if q.lower().startswith(prefix.lower())]
    
    def _load_from_file(self) -> None:
        """Carga el historial desde archivo."""
        try:
            history_file = Path.home() / ".devsecops_search_history"
            if history_file.exists():
                with open(history_file, 'r') as f:
                    self.history = [line.strip() for line in f.readlines()][:self.max_items]
        except Exception:
            pass
    
    def _save_to_file(self) -> None:
        """Guarda el historial en archivo."""
        try:
            history_file = Path.home() / ".devsecops_search_history"
            with open(history_file, 'w') as f:
                for query in self.history:
                    f.write(f"{query}\n")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# FILTROS AVANZADOS
# ═══════════════════════════════════════════════════════════════════════════════

class AdvancedFilter:
    """Filtros avanzados para búsqueda."""
    
    def __init__(self):
        """Inicializa los filtros."""
        self.group_filter: Optional[str] = None
        self.platform_filter: Optional[str] = None
        self.status_filter: Optional[str] = None
        self.tags_filter: Set[str] = set()
    
    def apply(self, items: Dict, item_key: str, item: Dict) -> bool:
        """
        Aplica los filtros a un item.
        
        Args:
            items: Diccionario de items
            item_key: Clave del item
            item: Item a filtrar
        
        Returns:
            True si el item pasa los filtros
        """
        # Filtro por grupo
        if self.group_filter:
            if item.get("group", "").lower() != self.group_filter.lower():
                return False
        
        # Filtro por plataforma
        if self.platform_filter:
            if item.get("platform", "").lower() != self.platform_filter.lower():
                return False
        
        # Filtro por estado
        if self.status_filter:
            if item.get("status", "").lower() != self.status_filter.lower():
                return False
        
        # Filtro por tags
        if self.tags_filter:
            item_tags = set(item.get("tags", []))
            if not self.tags_filter.issubset(item_tags):
                return False
        
        return True
    
    def set_group(self, group: Optional[str]) -> None:
        """Establece el filtro de grupo."""
        self.group_filter = group
    
    def set_platform(self, platform: Optional[str]) -> None:
        """Establece el filtro de plataforma."""
        self.platform_filter = platform
    
    def set_status(self, status: Optional[str]) -> None:
        """Establece el filtro de estado."""
        self.status_filter = status
    
    def add_tag(self, tag: str) -> None:
        """Agrega un tag al filtro."""
        self.tags_filter.add(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remueve un tag del filtro."""
        self.tags_filter.discard(tag)
    
    def clear(self) -> None:
        """Limpia todos los filtros."""
        self.group_filter = None
        self.platform_filter = None
        self.status_filter = None
        self.tags_filter.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# BÚSQUEDA AVANZADA
# ═══════════════════════════════════════════════════════════════════════════════

def fuzzy_match(query: str, text: str) -> float:
    """
    Calcula similitud fuzzy entre query y text.
    Retorna valor entre 0 y 1 (1 = coincidencia perfecta).
    """
    if not query:
        return 1.0
    
    query = query.lower()
    text = text.lower()
    
    # Coincidencia exacta
    if query in text:
        return 1.0
    
    # Coincidencia al inicio
    if text.startswith(query):
        return 0.9
    
    # Fuzzy matching
    matcher = SequenceMatcher(None, query, text)
    return matcher.ratio()


def search_items_advanced(
    items: Dict,
    query: str,
    search_fields: Dict = None,
    filters: AdvancedFilter = None
) -> List[Tuple[str, Dict, float]]:
    """
    Filtra items por query con filtros avanzados.
    
    Args:
        items: Diccionario de items
        query: Texto a buscar
        search_fields: Campos a buscar y pesos
        filters: Filtros avanzados
    
    Returns:
        Lista de (key, item, score) ordenada por relevancia
    """
    if search_fields is None:
        search_fields = {"name": 2.0, "description": 1.0}
    
    if filters is None:
        filters = AdvancedFilter()
    
    results = []
    query_lower = query.lower()
    
    for key, item in items.items():
        # Aplicar filtros avanzados
        if not filters.apply(items, key, item):
            continue
        
        scores = []
        
        # Calcular puntuaciones para cada campo
        for field, weight in search_fields.items():
            field_value = item.get(field, "")
            if isinstance(field_value, str):
                score = fuzzy_match(query_lower, field_value) * weight
                scores.append(score)
        
        if scores:
            max_score = max(scores)
            
            # Solo incluir si hay alguna coincidencia
            if max_score > 0.3:
                results.append((key, item, max_score))
    
    # Ordenar por puntuación descendente
    results.sort(key=lambda x: x[2], reverse=True)
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# AUTOCOMPLETADO
# ═══════════════════════════════════════════════════════════════════════════════

def get_autocomplete_suggestions(
    items: Dict,
    query: str,
    search_fields: Dict = None,
    max_suggestions: int = 5
) -> List[str]:
    """
    Retorna sugerencias de autocompletado.
    
    Args:
        items: Diccionario de items
        query: Texto actual
        search_fields: Campos a buscar
        max_suggestions: Número máximo de sugerencias
    
    Returns:
        Lista de sugerencias
    """
    if not query:
        return []
    
    if search_fields is None:
        search_fields = {"name": 2.0, "description": 1.0}
    
    results = search_items_advanced(items, query, search_fields)
    
    suggestions = []
    for key, item, score in results[:max_suggestions]:
        name = item.get("name", "")
        if name and name not in suggestions:
            suggestions.append(name)
    
    return suggestions


# ═══════════════════════════════════════════════════════════════════════════════
# BÚSQUEDA POR ID EXACTO
# ═══════════════════════════════════════════════════════════════════════════════

def search_by_id(items: Dict, item_id: str) -> Optional[Tuple[str, Dict]]:
    """
    Busca un item por ID exacto.
    
    Args:
        items: Diccionario de items
        item_id: ID a buscar
    
    Returns:
        Tupla (key, item) o None si no se encuentra
    """
    if item_id in items:
        return (item_id, items[item_id])
    
    # Búsqueda case-insensitive
    for key, item in items.items():
        if key.lower() == item_id.lower():
            return (key, item)
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# PAGINACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

class SearchPaginator:
    """Gestiona la paginación de resultados de búsqueda."""
    
    def __init__(self, items: List[Tuple[str, Dict, float]], page_size: int = 10):
        """
        Inicializa el paginador.
        
        Args:
            items: Lista de items a paginar
            page_size: Número de items por página
        """
        self.items = items
        self.page_size = page_size
        self.current_page = 0
    
    @property
    def total_pages(self) -> int:
        """Retorna el número total de páginas."""
        if not self.items:
            return 1
        return (len(self.items) + self.page_size - 1) // self.page_size
    
    @property
    def current_items(self) -> List[Tuple[str, Dict, float]]:
        """Retorna los items de la página actual."""
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.items[start:end]
    
    def next_page(self) -> bool:
        """Avanza a la siguiente página."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            return True
        return False
    
    def prev_page(self) -> bool:
        """Retrocede a la página anterior."""
        if self.current_page > 0:
            self.current_page -= 1
            return True
        return False
    
    def goto_page(self, page: int) -> bool:
        """Va a una página específica."""
        if 0 <= page < self.total_pages:
            self.current_page = page
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PÚBLICAS
# ═══════════════════════════════════════════════════════════════════════════════

def search_and_select_with_filters(
    tools: Dict,
    tool_groups: Dict = None,
    filters: AdvancedFilter = None
) -> Optional[str]:
    """
    Búsqueda interactiva con filtros avanzados.
    
    Args:
        tools: Diccionario de herramientas
        tool_groups: Diccionario de grupos
        filters: Filtros avanzados
    
    Returns:
        ID de la herramienta seleccionada o None
    """
    if filters is None:
        filters = AdvancedFilter()
    
    search_fields = {
        "name": 2.0,
        "description": 1.0,
        "group": 1.2
    }
    
    # Implementar búsqueda interactiva con filtros
    # (Usar search_items_advanced en lugar de search_items)
    from search_module import search_and_select_tools
    return search_and_select_tools(tools, tool_groups)


def get_available_groups(items: Dict) -> List[str]:
    """
    Retorna lista de grupos disponibles.
    
    Args:
        items: Diccionario de items
    
    Returns:
        Lista de grupos únicos
    """
    groups = set()
    for item in items.values():
        group = item.get("group", "")
        if group:
            groups.add(group)
    return sorted(list(groups))


def get_available_platforms(items: Dict) -> List[str]:
    """
    Retorna lista de plataformas disponibles.
    
    Args:
        items: Diccionario de items
    
    Returns:
        Lista de plataformas únicas
    """
    platforms = set()
    for item in items.values():
        platform = item.get("platform", "")
        if platform:
            platforms.add(platform)
    return sorted(list(platforms))


def get_available_tags(items: Dict) -> List[str]:
    """
    Retorna lista de tags disponibles.
    
    Args:
        items: Diccionario de items
    
    Returns:
        Lista de tags únicos
    """
    tags = set()
    for item in items.values():
        item_tags = item.get("tags", [])
        if isinstance(item_tags, list):
            tags.update(item_tags)
    return sorted(list(tags))


if __name__ == "__main__":
    # Ejemplo de uso
    test_items = {
        "1": {"name": "Tool 1", "description": "Description 1", "group": "core", "tags": ["important"]},
        "2": {"name": "Tool 2", "description": "Description 2", "group": "analysis", "tags": ["analysis"]},
        "3": {"name": "Tool 3", "description": "Description 3", "group": "core", "tags": ["important", "security"]},
    }
    
    # Búsqueda simple
    results = search_items_advanced(test_items, "tool")
    print(f"Resultados de búsqueda: {len(results)}")
    
    # Búsqueda con filtros
    filters = AdvancedFilter()
    filters.set_group("core")
    results_filtered = search_items_advanced(test_items, "tool", filters=filters)
    print(f"Resultados filtrados: {len(results_filtered)}")
    
    # Autocompletado
    suggestions = get_autocomplete_suggestions(test_items, "too")
    print(f"Sugerencias: {suggestions}")
    
    # Búsqueda por ID
    result = search_by_id(test_items, "1")
    print(f"Búsqueda por ID: {result}")
    
    # Grupos disponibles
    groups = get_available_groups(test_items)
    print(f"Grupos: {groups}")
