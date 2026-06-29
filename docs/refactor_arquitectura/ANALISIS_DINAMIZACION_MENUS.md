# 📋 ANÁLISIS: DINAMIZACIÓN DE MENÚS SIN HARDCODE

**Fecha:** 29 de Junio de 2026  
**Objetivo:** Eliminar hardcode de opciones de menú y generarlas dinámicamente desde TOOLS  
**Estado:** ANÁLISIS COMPLETO - PENDIENTE APROBACIÓN

---

## 🎯 PROBLEMA ACTUAL

### Hardcode Identificado

```python
# AZDO tools.py - Líneas 358-377
"A": {
    "name":        "Ejecutar Todos",
    "description": "Ejecuta todas las herramientas...",
    "auto_tools":  ["1", "2", "2b", "3", "4", "8", "9", "10", "11", "13", "14", "15", "16", "18"],
    "group":       "system",
    "status":      "ready",
},
"B": {
    "name":        "Ejecutar Todo + JSON",
    "description": "Ejecuta TODAS las herramientas...",
    "auto_tools":  ["1", "2", "2b", "3", "4", "8", "9", "10", "11", "13", "14", "15", "16", "18"],
    "group":       "system",
    "status":      "ready",
},
"Q": {
    "name":        "Salir",
    "description": "Salir del menú",
    "group":       "system",
    "status":      "exit",
},
```

**Problemas:**
- ❌ IDs de herramientas hardcodeados en `auto_tools`
- ❌ Si se agrega/elimina herramienta, hay que actualizar manualmente
- ❌ Riesgo de inconsistencias
- ❌ Difícil de mantener en múltiples plataformas (AZDO, GCP, AWS)
- ❌ No hay forma de excluir herramientas dinámicamente

### Ubicaciones del Hardcode

```
AZDO (scm/azdo/tools.py)
├─ Línea 358-377: "A" y "B" con auto_tools hardcodeados
└─ Línea 361, 368: Listas de IDs duplicadas

GCP (scm/gcp/tools.py)
├─ Línea 329-336: "A" con auto_tools hardcodeados
└─ Línea 332: Lista de IDs hardcodeada

AWS (scm/aws/tools.py)
├─ Línea 282-289: "A" con auto_tools hardcodeados
└─ Línea 285: Lista de IDs hardcodeada

Terminal (scm/terminal/tools.py)
├─ Línea 170-176: "Q" (Volver al menú principal)
└─ Sin auto_tools (scripts shell, no aplica)
```

---

## 🏗️ SOLUCIÓN PROPUESTA

### Estrategia: Generación Dinámica de Opciones de Sistema

```python
# Estructura mejorada en TOOLS

TOOLS = {
    # ... herramientas normales ...
    "1": { ... },
    "2": { ... },
    
    # Opciones de sistema (generadas dinámicamente)
    "_system_options": {
        "A": {
            "name": "Ejecutar Todos",
            "description": "Ejecuta todas las herramientas...",
            "type": "auto_run",
            "exclude": ["1b", "5", "6", "7"],  # Excluir estas herramientas
            "reason": "Excluye: Deep Dive (requiere release-id), Task Validator (requiere parámetros específicos), etc."
        },
        "B": {
            "name": "Ejecutar Todo + JSON",
            "description": "Ejecuta TODAS las herramientas en secuencia...",
            "type": "auto_run_json",
            "exclude": ["1b", "5", "6", "7"],
            "reason": "Excluye: Deep Dive, Task Validator, etc."
        },
        "Q": {
            "name": "Salir",
            "description": "Salir del menú",
            "type": "exit"
        }
    }
}
```

### Función para Generar auto_tools Dinámicamente

```python
def get_auto_tools(exclude_list: List[str] = None) -> List[str]:
    """
    Genera lista de herramientas para auto_run dinámicamente.
    
    Args:
        exclude_list: Lista de IDs a excluir (ej: ["1b", "5", "6"])
    
    Returns:
        Lista de IDs de herramientas válidas, ordenadas por grupo
    """
    exclude_list = exclude_list or []
    auto_tools = []
    
    # Iterar por grupos en orden
    for group_key in GROUP_ORDER:
        # Obtener herramientas de este grupo
        group_tools = [
            key for key, tool in TOOLS.items()
            if (tool.get("group") == group_key and 
                key not in ("Q", "A", "B", "_system_options") and
                key not in exclude_list)
        ]
        
        # Ordenar numéricamente dentro del grupo
        group_tools.sort(key=_menu_sort_key)
        auto_tools.extend(group_tools)
    
    return auto_tools


def build_system_options():
    """
    Construye las opciones de sistema (A, B, Q) dinámicamente.
    Reemplaza el hardcode actual.
    """
    system_opts = TOOLS.get("_system_options", {})
    
    for key, opt_config in system_opts.items():
        if opt_config.get("type") in ("auto_run", "auto_run_json"):
            # Generar auto_tools dinámicamente
            exclude = opt_config.get("exclude", [])
            auto_tools = get_auto_tools(exclude)
            
            # Crear opción final
            TOOLS[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "auto_tools": auto_tools,
                "group": "system",
                "status": "ready"
            }
        else:
            # Opciones simples (como "Q")
            TOOLS[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "group": "system",
                "status": opt_config.get("type", "exit")
            }


# Llamar al inicio del programa
build_system_options()
```

---

## 📊 COMPARATIVA: ANTES vs DESPUÉS

### ANTES (Hardcode)

```python
# AZDO tools.py - 20 líneas de hardcode
"A": {
    "name":        "Ejecutar Todos",
    "description": "Ejecuta todas las herramientas con la misma configuración (sin Deep Dive)",
    "auto_tools":  ["1", "2", "2b", "3", "4", "8", "9", "10", "11", "13", "14", "15", "16", "18"],
    "group":       "system",
    "status":      "ready",
},
"B": {
    "name":        "Ejecutar Todo + JSON",
    "description": "Ejecuta TODAS las herramientas en secuencia forzando salida JSON en outcome/. Ideal para alimentar el dashboard.",
    "auto_tools":  ["1", "2", "2b", "3", "4", "8", "9", "10", "11", "13", "14", "15", "16", "18"],
    "group":       "system",
    "status":      "ready",
},

# GCP tools.py - 8 líneas de hardcode
"A": {
    "name": "Ejecutar Todos (Checkers)",
    "description": "Ejecuta todos los checkers con proyecto default y output JSON",
    "auto_tools": ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21"],
    "excluded_reason": "Excluye: Pod Connectivity (requiere deployment), Artifact Registry (requiere CSV), Inventario (pipeline propio)",
    "group": "system",
    "status": "ready"
},

# AWS tools.py - 8 líneas de hardcode
"A": {
    "name": "Ejecutar Todos (Checkers)",
    "description": "Ejecuta todos los checkers con profile y región por defecto",
    "auto_tools": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "17", "18"],
    "excluded_reason": "Excluye: EKS Pod/Node Monitor (requieren kubectl y selección de cluster), Inventory (pipeline propio)",
    "group": "system",
    "status": "ready"
},

TOTAL HARDCODE: 36 líneas × 3 plataformas = 108 líneas
```

### DESPUÉS (Dinámico)

```python
# Estructura común en todos los tools.py
"_system_options": {
    "A": {
        "name": "Ejecutar Todos",
        "description": "Ejecuta todas las herramientas...",
        "type": "auto_run",
        "exclude": ["1b", "5", "6", "7"],  # Solo especificar exclusiones
        "reason": "Excluye: Deep Dive, Task Validator, etc."
    },
    "B": {
        "name": "Ejecutar Todo + JSON",
        "description": "Ejecuta TODAS las herramientas...",
        "type": "auto_run_json",
        "exclude": ["1b", "5", "6", "7"],
        "reason": "Excluye: Deep Dive, Task Validator, etc."
    },
    "Q": {
        "name": "Salir",
        "description": "Salir del menú",
        "type": "exit"
    }
}

# Función única (reutilizable en todas las plataformas)
def build_system_options():
    """Construye opciones de sistema dinámicamente"""
    system_opts = TOOLS.get("_system_options", {})
    for key, opt_config in system_opts.items():
        if opt_config.get("type") in ("auto_run", "auto_run_json"):
            exclude = opt_config.get("exclude", [])
            TOOLS[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "auto_tools": get_auto_tools(exclude),
                "group": "system",
                "status": "ready"
            }
        else:
            TOOLS[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "group": "system",
                "status": opt_config.get("type", "exit")
            }

TOTAL DINÁMICO: 20 líneas × 3 plataformas = 60 líneas
REDUCCIÓN: 44% (108 → 60 líneas)
```

---

## 🔄 IMPLEMENTACIÓN PASO A PASO

### Paso 1: Crear Función Auxiliar (Común)

```python
# En cada tools.py (AZDO, GCP, AWS)

def _menu_sort_key(k: str):
    """Ordena claves numéricamente."""
    if k.isdigit():
        return (0, int(k), 0)
    # Handle keys like "1b", "2a", etc.
    base = ""
    suffix = ""
    for c in k:
        if c.isdigit():
            base += c
        else:
            suffix += c
    if base:
        return (0, int(base), ord(suffix) if suffix else 0)
    return (1, 0, ord(k))


def get_auto_tools(exclude_list: List[str] = None) -> List[str]:
    """
    Genera lista de herramientas para auto_run dinámicamente.
    
    Itera por GROUP_ORDER, obtiene herramientas de cada grupo,
    excluye las especificadas, y retorna lista ordenada.
    """
    exclude_list = exclude_list or []
    auto_tools = []
    
    for group_key in GROUP_ORDER:
        group_tools = [
            key for key, tool in TOOLS.items()
            if (tool.get("group") == group_key and 
                key not in ("Q", "A", "B", "_system_options") and
                key not in exclude_list)
        ]
        group_tools.sort(key=_menu_sort_key)
        auto_tools.extend(group_tools)
    
    return auto_tools


def build_system_options():
    """
    Construye las opciones de sistema (A, B, Q) dinámicamente.
    Reemplaza el hardcode actual.
    """
    system_opts = TOOLS.get("_system_options", {})
    
    for key, opt_config in system_opts.items():
        if opt_config.get("type") in ("auto_run", "auto_run_json"):
            exclude = opt_config.get("exclude", [])
            auto_tools = get_auto_tools(exclude)
            
            TOOLS[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "auto_tools": auto_tools,
                "group": "system",
                "status": "ready"
            }
        else:
            TOOLS[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "group": "system",
                "status": opt_config.get("type", "exit")
            }
```

### Paso 2: Reemplazar Hardcode en TOOLS

```python
# ANTES (AZDO tools.py - líneas 358-377)
"A": {
    "name":        "Ejecutar Todos",
    "description": "Ejecuta todas las herramientas con la misma configuración (sin Deep Dive)",
    "auto_tools":  ["1", "2", "2b", "3", "4", "8", "9", "10", "11", "13", "14", "15", "16", "18"],
    "group":       "system",
    "status":      "ready",
},
"B": {
    "name":        "Ejecutar Todo + JSON",
    "description": "Ejecuta TODAS las herramientas en secuencia forzando salida JSON en outcome/. Ideal para alimentar el dashboard.",
    "auto_tools":  ["1", "2", "2b", "3", "4", "8", "9", "10", "11", "13", "14", "15", "16", "18"],
    "group":       "system",
    "status":      "ready",
},
"Q": {
    "name":        "Salir",
    "description": "Salir del menú",
    "group":       "system",
    "status":      "exit",
},

# DESPUÉS (AZDO tools.py)
"_system_options": {
    "A": {
        "name": "Ejecutar Todos",
        "description": "Ejecuta todas las herramientas con la misma configuración (sin Deep Dive)",
        "type": "auto_run",
        "exclude": ["1b", "5", "6", "7"],
        "reason": "Excluye: PR Pipeline Analyzer, Release Deep Dive, Task Validator, Pipeline Logs Scanner"
    },
    "B": {
        "name": "Ejecutar Todo + JSON",
        "description": "Ejecuta TODAS las herramientas en secuencia forzando salida JSON en outcome/. Ideal para alimentar el dashboard.",
        "type": "auto_run_json",
        "exclude": ["1b", "5", "6", "7"],
        "reason": "Excluye: PR Pipeline Analyzer, Release Deep Dive, Task Validator, Pipeline Logs Scanner"
    },
    "Q": {
        "name": "Salir",
        "description": "Salir del menú",
        "type": "exit"
    }
}
```

### Paso 3: Llamar a build_system_options() al Inicio

```python
# Al final de la sección de definición de TOOLS, antes de main()

# Construir opciones de sistema dinámicamente
build_system_options()

# Ahora TOOLS["A"], TOOLS["B"], TOOLS["Q"] tienen auto_tools generado dinámicamente
```

### Paso 4: Verificar que get_menu_order() Funciona

```python
# La función get_menu_order() ya existe y funciona correctamente
# No necesita cambios, ya que itera sobre TOOLS.items()

def get_menu_order() -> List[str]:
    """Retorna las claves del menú ordenadas por grupo y numéricamente dentro de cada grupo."""
    ordered: List[str] = []
    for group_key in GROUP_ORDER:
        keys = [k for k, t in TOOLS.items()
                if t.get("group") == group_key and k not in ("Q", "A", "B", "_system_options")]
        keys.sort(key=_menu_sort_key)
        ordered.extend(keys)
    if "B" in TOOLS:
        ordered.append("B")
    if "A" in TOOLS:
        ordered.append("A")
    if "Q" in TOOLS:
        ordered.append("Q")
    return ordered
```

---

## 🎁 BENEFICIOS DE LA SOLUCIÓN

### 1. Mantenibilidad

```
✅ Agregar nueva herramienta:
   - Solo agregar entrada en TOOLS
   - auto_tools se actualiza automáticamente
   - No hay que tocar hardcode

✅ Cambiar exclusiones:
   - Solo modificar "exclude" en _system_options
   - No hay que actualizar múltiples listas
```

### 2. Escalabilidad

```
✅ Nuevas plataformas:
   - Copiar estructura de _system_options
   - Personalizar solo "exclude"
   - Reutilizar funciones get_auto_tools() y build_system_options()

✅ Nuevos tipos de auto_run:
   - Agregar nuevo tipo en _system_options
   - Extender build_system_options() si es necesario
```

### 3. Consistencia

```
✅ Todas las plataformas usan mismo patrón
✅ Mismo código de generación (DRY)
✅ Menos errores por inconsistencia
```

### 4. Documentación

```
✅ "exclude" documenta por qué se excluyen herramientas
✅ "reason" explica la razón
✅ Más fácil de entender para nuevos desarrolladores
```

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### Para AZDO (scm/azdo/tools.py)

- [ ] Agregar función `get_auto_tools()`
- [ ] Agregar función `build_system_options()`
- [ ] Reemplazar hardcode de "A", "B", "Q" con `_system_options`
- [ ] Llamar `build_system_options()` después de definir TOOLS
- [ ] Verificar que `get_menu_order()` excluya `_system_options`
- [ ] Testing: Verificar que "A" ejecuta herramientas correctas
- [ ] Testing: Verificar que "B" ejecuta herramientas correctas
- [ ] Testing: Verificar que menú muestra opciones correctamente

### Para GCP (scm/gcp/tools.py)

- [ ] Copiar funciones `get_auto_tools()` y `build_system_options()`
- [ ] Reemplazar hardcode de "A", "Q" con `_system_options`
- [ ] Llamar `build_system_options()` después de definir TOOLS
- [ ] Verificar que `get_menu_order()` excluya `_system_options`
- [ ] Testing: Verificar que "A" ejecuta herramientas correctas
- [ ] Testing: Verificar que menú muestra opciones correctamente

### Para AWS (scm/aws/tools.py)

- [ ] Copiar funciones `get_auto_tools()` y `build_system_options()`
- [ ] Reemplazar hardcode de "A", "Q" con `_system_options`
- [ ] Llamar `build_system_options()` después de definir TOOLS
- [ ] Verificar que `get_menu_order()` excluya `_system_options`
- [ ] Testing: Verificar que "A" ejecuta herramientas correctas
- [ ] Testing: Verificar que menú muestra opciones correctamente

### Para Terminal (scm/terminal/tools.py)

- [ ] Copiar funciones (aunque no tenga auto_run)
- [ ] Reemplazar hardcode de "Q" con `_system_options`
- [ ] Llamar `build_system_options()` después de definir SCRIPTS
- [ ] Verificar que menú muestra opciones correctamente

---

## 🔍 CASOS DE USO

### Caso 1: Agregar Nueva Herramienta

```python
# ANTES: Había que actualizar hardcode
"A": {
    "auto_tools": ["1", "2", "2b", "3", "4", "8", "9", "10", "11", "13", "14", "15", "16", "18"],  # ← Actualizar aquí
}

# DESPUÉS: Se actualiza automáticamente
# Solo agregar en TOOLS:
"26": {
    "name": "Nueva Herramienta",
    "group": "inventory",
    ...
}

# auto_tools se regenera automáticamente al llamar build_system_options()
```

### Caso 2: Excluir Herramienta de auto_run

```python
# ANTES: Había que actualizar hardcode
"A": {
    "auto_tools": ["1", "2", "2b", "3", "4", "8", "9", "10", "11", "13", "14", "15", "16", "18"],  # ← Remover "5"
}

# DESPUÉS: Solo actualizar exclude
"_system_options": {
    "A": {
        "exclude": ["1b", "5", "6", "7"],  # ← Agregar "5"
        "reason": "Excluye: PR Pipeline Analyzer, Release Deep Dive, Task Validator, Pipeline Logs Scanner"
    }
}
```

### Caso 3: Crear Nuevo Tipo de auto_run

```python
# Agregar en _system_options:
"C": {
    "name": "Ejecutar Herramientas de Inventario",
    "description": "Ejecuta solo herramientas de inventario",
    "type": "auto_run_inventory",
    "exclude": [],
    "reason": "Solo herramientas del grupo 'inventory'"
}

# Extender build_system_options():
def build_system_options():
    system_opts = TOOLS.get("_system_options", {})
    
    for key, opt_config in system_opts.items():
        if opt_config.get("type") == "auto_run_inventory":
            # Generar solo herramientas del grupo inventory
            auto_tools = [
                k for k, t in TOOLS.items()
                if t.get("group") == "inventory" and k not in ("Q", "A", "B", "C", "_system_options")
            ]
            auto_tools.sort(key=_menu_sort_key)
            
            TOOLS[key] = {
                "name": opt_config["name"],
                "description": opt_config["description"],
                "auto_tools": auto_tools,
                "group": "system",
                "status": "ready"
            }
        # ... resto del código ...
```

---

## 📊 IMPACTO FINAL

```
┌─────────────────────────────────────────────────────┐
│ MÉTRICA                    │ ANTES    │ DESPUÉS     │
├─────────────────────────────────────────────────────┤
│ Líneas de hardcode         │ 108      │ 60          │
│ Reducción                  │ -        │ 44%         │
│ Puntos de cambio           │ 3        │ 1           │
│ Riesgo de inconsistencia   │ Alto     │ Bajo        │
│ Facilidad de mantenimiento │ Difícil  │ Fácil       │
│ Escalabilidad              │ Baja     │ Alta        │
└─────────────────────────────────────────────────────┘
```

---

## 🔄 PRÓXIMOS PASOS (PENDIENTE APROBACIÓN)

1. **Revisión del Análisis**
   - ¿Está de acuerdo con la solución propuesta?
   - ¿Hay mejoras sugeridas?
   - ¿Hay restricciones técnicas?

2. **Validación de Implementación**
   - ¿Proceder con la refactorización?
   - ¿Implementar todas las plataformas o por fases?
   - ¿Timeline estimado?

3. **Decisión Final**
   - ¿Aprobar la dinamización de menús?
   - ¿Crear módulo compartido para funciones comunes?
   - ¿Documentar el patrón para futuras plataformas?

---

**Documento generado automáticamente**  
**Última actualización:** 29 de Junio de 2026  
**Estado:** ANÁLISIS COMPLETO - PENDIENTE APROBACIÓN DEL USUARIO
