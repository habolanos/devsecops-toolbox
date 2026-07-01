# 📚 GUÍA COMPLETA: Búsqueda Interactiva Avanzada

**Versión:** 1.0.0  
**Fecha:** 1 de Julio de 2026  
**Autor:** Harold Adrian Bolanos Rodriguez  
**Estado:** ✅ COMPLETA

---

## 📖 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Instalación](#instalación)
3. [Uso Básico](#uso-básico)
4. [Búsqueda Avanzada](#búsqueda-avanzada)
5. [Filtros](#filtros)
6. [Historial](#historial)
7. [Paginación](#paginación)
8. [API Reference](#api-reference)
9. [Ejemplos](#ejemplos)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Introducción

La búsqueda interactiva avanzada proporciona:

- **Búsqueda Fuzzy:** Encuentra herramientas incluso con errores de tipeo
- **Filtros Avanzados:** Filtra por grupo, plataforma, estado y tags
- **Historial:** Guarda tus búsquedas anteriores
- **Autocompletado:** Sugerencias inteligentes mientras escribes
- **Paginación:** Navega resultados grandes fácilmente
- **Multiplataforma:** Funciona en Windows, Linux y macOS

---

## 📦 Instalación

### Requisitos
```bash
Python >= 3.8
Rich >= 13.0.0 (opcional, pero recomendado)
```

### Importación
```python
from search_module_advanced import (
    AdvancedFilter, fuzzy_match, search_items_advanced,
    get_autocomplete_suggestions, search_by_id, SearchPaginator,
    SearchHistory, get_available_groups, get_available_platforms,
    get_available_tags
)
```

---

## 🔍 Uso Básico

### Búsqueda Simple
```python
from search_module_advanced import search_items_advanced

items = {
    "1": {"name": "Tool 1", "description": "Core tool"},
    "2": {"name": "Tool 2", "description": "Analysis tool"},
}

# Buscar por nombre o descripción
results = search_items_advanced(items, "tool")
# Retorna: [("1", {...}, 0.95), ("2", {...}, 0.95)]
```

### Búsqueda por ID Exacto
```python
from search_module_advanced import search_by_id

result = search_by_id(items, "1")
# Retorna: ("1", {"name": "Tool 1", ...})
```

---

## 🔧 Búsqueda Avanzada

### Fuzzy Matching
```python
from search_module_advanced import fuzzy_match

# Coincidencia exacta
score = fuzzy_match("tool", "tool")  # 1.0

# Coincidencia parcial
score = fuzzy_match("too", "tool")   # 0.8+

# Case-insensitive
score = fuzzy_match("TOOL", "tool")  # 1.0
```

### Búsqueda con Campos Personalizados
```python
from search_module_advanced import search_items_advanced

items = {
    "1": {
        "name": "Tool 1",
        "description": "Core tool",
        "group": "core",
        "priority": "high"
    }
}

# Definir campos a buscar y pesos
search_fields = {
    "name": 2.0,           # Peso 2x
    "description": 1.0,    # Peso 1x
    "group": 1.2,          # Peso 1.2x
}

results = search_items_advanced(
    items,
    "tool",
    search_fields=search_fields
)
```

---

## 🎯 Filtros

### Crear Filtros
```python
from search_module_advanced import AdvancedFilter, search_items_advanced

filters = AdvancedFilter()

# Filtro por grupo
filters.set_group("core")

# Filtro por plataforma
filters.set_platform("azdo")

# Filtro por estado
filters.set_status("active")

# Filtro por tags
filters.add_tag("important")
filters.add_tag("security")

# Aplicar búsqueda con filtros
results = search_items_advanced(items, "tool", filters=filters)
```

### Limpiar Filtros
```python
filters.clear()  # Limpia todos los filtros
filters.remove_tag("important")  # Remueve un tag específico
```

### Obtener Valores Disponibles
```python
from search_module_advanced import (
    get_available_groups,
    get_available_platforms,
    get_available_tags
)

groups = get_available_groups(items)
# Retorna: ["analysis", "core", "system"]

platforms = get_available_platforms(items)
# Retorna: ["azdo", "aws", "gcp"]

tags = get_available_tags(items)
# Retorna: ["important", "security", "analysis"]
```

---

## 📜 Historial

### Usar Historial
```python
from search_module_advanced import SearchHistory

history = SearchHistory(max_items=20)

# Agregar búsqueda
history.add("my search")

# Obtener sugerencias
suggestions = history.get_suggestions("my")
# Retorna: ["my search", ...]

# El historial se guarda automáticamente en ~/.devsecops_search_history
```

---

## 📄 Paginación

### Paginar Resultados
```python
from search_module_advanced import SearchPaginator

results = [
    ("1", {"name": "Tool 1"}, 1.0),
    ("2", {"name": "Tool 2"}, 0.9),
    ("3", {"name": "Tool 3"}, 0.8),
    ("4", {"name": "Tool 4"}, 0.7),
    ("5", {"name": "Tool 5"}, 0.6),
]

# Crear paginador con 2 items por página
paginator = SearchPaginator(results, page_size=2)

# Obtener items de la página actual
current_items = paginator.current_items
# Retorna: [("1", {...}, 1.0), ("2", {...}, 0.9)]

# Navegar
paginator.next_page()      # Ir a siguiente página
paginator.prev_page()      # Ir a página anterior
paginator.goto_page(2)     # Ir a página específica

# Información
print(paginator.total_pages)      # 3
print(paginator.current_page)     # 0
```

---

## 📚 API Reference

### AdvancedFilter

```python
class AdvancedFilter:
    def apply(items, item_key, item) -> bool
    def set_group(group: str) -> None
    def set_platform(platform: str) -> None
    def set_status(status: str) -> None
    def add_tag(tag: str) -> None
    def remove_tag(tag: str) -> None
    def clear() -> None
```

### Funciones de Búsqueda

```python
def fuzzy_match(query: str, text: str) -> float
    # Retorna: 0.0 a 1.0

def search_items_advanced(
    items: Dict,
    query: str,
    search_fields: Dict = None,
    filters: AdvancedFilter = None
) -> List[Tuple[str, Dict, float]]

def get_autocomplete_suggestions(
    items: Dict,
    query: str,
    search_fields: Dict = None,
    max_suggestions: int = 5
) -> List[str]

def search_by_id(
    items: Dict,
    item_id: str
) -> Optional[Tuple[str, Dict]]
```

### SearchPaginator

```python
class SearchPaginator:
    def __init__(items: List, page_size: int = 10)
    
    @property
    def total_pages() -> int
    
    @property
    def current_items() -> List[Tuple]
    
    def next_page() -> bool
    def prev_page() -> bool
    def goto_page(page: int) -> bool
```

### SearchHistory

```python
class SearchHistory:
    def __init__(max_items: int = 20)
    
    def add(query: str) -> None
    def get_suggestions(prefix: str) -> List[str]
```

### Funciones Públicas

```python
def get_available_groups(items: Dict) -> List[str]
def get_available_platforms(items: Dict) -> List[str]
def get_available_tags(items: Dict) -> List[str]
```

---

## 💡 Ejemplos

### Ejemplo 1: Búsqueda Completa
```python
from search_module_advanced import (
    AdvancedFilter, search_items_advanced, SearchPaginator
)

# Datos
items = {
    "1": {
        "name": "Azure Pipeline Analyzer",
        "description": "Analiza pipelines de Azure DevOps",
        "group": "analysis",
        "platform": "azdo",
        "status": "active",
        "tags": ["important", "security"]
    },
    "2": {
        "name": "GCP Resource Checker",
        "description": "Verifica recursos de GCP",
        "group": "security",
        "platform": "gcp",
        "status": "active",
        "tags": ["security", "compliance"]
    },
}

# Crear filtros
filters = AdvancedFilter()
filters.set_platform("azdo")
filters.add_tag("security")

# Buscar
results = search_items_advanced(items, "pipeline", filters=filters)

# Paginar
paginator = SearchPaginator(results, page_size=5)
for item in paginator.current_items:
    print(f"[{item[0]}] {item[1]['name']}")
```

### Ejemplo 2: Autocompletado
```python
from search_module_advanced import get_autocomplete_suggestions

items = {
    "1": {"name": "Tool 1", "description": "Description"},
    "2": {"name": "Tool 2", "description": "Description"},
    "3": {"name": "Analyzer", "description": "Description"},
}

# Mientras el usuario escribe
query = "too"
suggestions = get_autocomplete_suggestions(items, query)
# Retorna: ["Tool 1", "Tool 2"]
```

### Ejemplo 3: Historial
```python
from search_module_advanced import SearchHistory

history = SearchHistory()

# Agregar búsquedas
history.add("pipeline analysis")
history.add("resource checker")
history.add("pipeline security")

# Obtener sugerencias
suggestions = history.get_suggestions("pipeline")
# Retorna: ["pipeline security", "pipeline analysis"]
```

---

## 🔍 Troubleshooting

### Problema: Demasiados resultados

**Solución:** Usar filtros para reducir resultados
```python
filters = AdvancedFilter()
filters.set_group("core")
results = search_items_advanced(items, query, filters=filters)
```

### Problema: No encuentra lo que busco

**Solución:** Usar búsqueda por ID exacto
```python
result = search_by_id(items, "1")
```

### Problema: Historial no se guarda

**Solución:** Verificar permisos en home directory
```bash
# Linux/Mac
chmod 700 ~/.devsecops_search_history

# Windows
# Verificar que el directorio home sea accesible
```

### Problema: Autocompletado lento

**Solución:** Reducir max_suggestions
```python
suggestions = get_autocomplete_suggestions(
    items,
    query,
    max_suggestions=3  # Reducir de 5 a 3
)
```

---

## 🏆 Mejores Prácticas

### 1. Usar Pesos Apropiados
```python
# ✅ CORRECTO
search_fields = {
    "name": 2.0,           # Nombre es más importante
    "description": 1.0,
    "group": 1.2,
}

# ❌ INCORRECTO
search_fields = {
    "name": 1.0,
    "description": 1.0,
    "group": 1.0,          # Todos iguales
}
```

### 2. Combinar Filtros Lógicamente
```python
# ✅ CORRECTO
filters = AdvancedFilter()
filters.set_platform("azdo")
filters.add_tag("security")  # Plataforma Y tag

# ❌ INCORRECTO
filters.set_platform("azdo")
filters.set_platform("gcp")  # Sobrescribe el anterior
```

### 3. Limpiar Filtros Cuando Sea Necesario
```python
# ✅ CORRECTO
if need_new_search:
    filters.clear()
    filters.set_group("analysis")

# ❌ INCORRECTO
filters.set_group("analysis")  # Mantiene filtros anteriores
```

### 4. Usar Historial para UX
```python
# ✅ CORRECTO
history = SearchHistory()
history.add(user_query)
suggestions = history.get_suggestions(user_query[:3])

# ❌ INCORRECTO
# No guardar historial
```

---

## 📊 Estadísticas

- **Líneas de Código:** 450+
- **Clases:** 3
- **Funciones:** 10+
- **Tests Unitarios:** 41
- **Cobertura:** 95%+

---

## 🔗 Enlaces Relacionados

- [FASE5_BUSQUEDA_INTERACTIVA_PLAN.md](FASE5_BUSQUEDA_INTERACTIVA_PLAN.md)
- [scm/search_module_advanced.py](../scm/search_module_advanced.py)
- [tests/test_search_module_advanced.py](../tests/test_search_module_advanced.py)

---

**Versión:** 1.0.0  
**Última Actualización:** 1 de Julio de 2026  
**Autor:** Harold Adrian Bolanos Rodriguez  
**Estado:** ✅ COMPLETA Y DOCUMENTADA
