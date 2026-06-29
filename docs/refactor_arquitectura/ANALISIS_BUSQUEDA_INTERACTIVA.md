# 🔍 ANÁLISIS: BÚSQUEDA INTERACTIVA CON `/`

**Fecha:** 29 de Junio de 2026  
**Objetivo:** Analizar la funcionalidad de búsqueda interactiva con `/` en los menús  
**Estado:** ANÁLISIS EXHAUSTIVO COMPLETADO

---

## 📍 UBICACIÓN DE LA FUNCIONALIDAD

### Archivo Principal: `scm/azdo/interactive_search.py`

```
c:\Users\harold.bolanos\repos-publics\devsecops-toolbox\scm\azdo\
├─ interactive_search.py          ← MÓDULO DE BÚSQUEDA (328 líneas)
└─ tools.py                        ← INTEGRACIÓN (Línea 1849)
```

---

## 🔧 COMPONENTES DE LA BÚSQUEDA INTERACTIVA

### 1. Módulo: `interactive_search.py`

**Características principales:**

```python
# Línea 4-14: Descripción
"""
Búsqueda Interactiva en Vivo para Azure DevOps Tools

Proporciona una interfaz de búsqueda con captura de teclas en tiempo real,
permitiendo filtrado visual mientras el usuario escribe.

Características:
- Búsqueda en vivo (se actualiza con cada tecla)
- Fuzzy matching en ID, nombre, descripción y grupo
- Navegación con flechas arriba/abajo
- Selección rápida por número
- Compatible con Windows, Linux y macOS
"""
```

---

## 🎯 FUNCIONALIDADES IMPLEMENTADAS

### 1. Captura de Teclas (Multiplataforma)

```python
# Línea 38-77: Funciones de captura de teclas

def get_char_windows() -> Optional[str]:
    """Captura una tecla en Windows usando msvcrt."""
    # Implementación para Windows

def get_char_unix() -> Optional[str]:
    """Captura una tecla en Unix/Linux/macOS usando termios."""
    # Implementación para Unix/Linux/macOS

def get_single_char() -> Optional[str]:
    """Captura una tecla según la plataforma."""
    if sys.platform == "win32":
        return get_char_windows()
    else:
        return get_char_unix()
```

**Soporta:**
- ✅ Windows (msvcrt)
- ✅ Linux/macOS (termios)

---

### 2. Búsqueda Fuzzy (Línea 84-144)

```python
def fuzzy_match(query: str, text: str) -> float:
    """
    Calcula similitud fuzzy entre query y text.
    Retorna valor entre 0 y 1 (1 = coincidencia perfecta).
    """
    # Coincidencia exacta: 1.0
    # Coincidencia al inicio: 0.9
    # Fuzzy matching: SequenceMatcher.ratio()

def search_tools(tools: Dict, query: str, tool_groups: Dict) -> List[Tuple[str, Dict, float]]:
    """
    Filtra herramientas por query.
    Busca en: ID, nombre, descripción, grupo.
    
    Pesos de búsqueda:
    - ID: 2.0x (máxima prioridad)
    - Nombre: 1.5x
    - Grupo: 1.2x
    - Descripción: 1.0x
    """
```

**Algoritmo de búsqueda:**
1. Busca en 4 campos: ID, nombre, descripción, grupo
2. Aplica pesos diferentes a cada campo
3. Ordena por relevancia (puntuación descendente)
4. Filtra resultados con score > 0.3

---

### 3. Visualización (Línea 156-248)

```python
def print_search_interface(query: str, results: List[Tuple[str, Dict, float]], 
                          tool_groups: Dict, selected_idx: int = 0):
    """Imprime la interfaz de búsqueda con resultados."""
    
    # Con Rich:
    # - Panel de búsqueda
    # - Tabla de resultados con colores
    # - Fila seleccionada destacada
    # - Instrucciones de navegación
    
    # Sin Rich (fallback):
    # - Texto plano
    # - Listado simple
    # - Instrucciones básicas
```

**Interfaz Rich:**
```
┌─────────────────────────────────────────────────────┐
│ 🔍 BÚSQUEDA EN VIVO                                 │
├─────────────────────────────────────────────────────┤
│ Búsqueda: [query]                                   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Coincidencias: N/M                                  │
├─────────────────────────────────────────────────────┤
│ # │ Grupo │ Herramienta │ Descripción             │
├─────────────────────────────────────────────────────┤
│ 1 │ PR    │ PR Master   │ Lista PRs hacia master  │
│ 2 │ PR    │ PR Pipeline │ Analiza PRs múltiples  │
└─────────────────────────────────────────────────────┘

⬆️  ⬇️  Navegar  │  ENTER Seleccionar  │  BACKSPACE Borrar  │  ESC Cancelar
```

---

### 4. Interfaz Interactiva (Línea 255-315)

```python
def interactive_search(tools: Dict, tool_groups: Dict) -> Optional[str]:
    """
    Interfaz interactiva de búsqueda en vivo.
    Retorna el ID de la herramienta seleccionada o None si se cancela.
    """
    
    # Bucle principal que:
    # 1. Captura teclas
    # 2. Procesa comandos (ESC, ENTER, BACKSPACE, flechas)
    # 3. Actualiza búsqueda en vivo
    # 4. Redibuja interfaz
```

**Teclas soportadas:**
- ✅ **ESC (27)**: Cancelar búsqueda
- ✅ **ENTER (13)**: Seleccionar herramienta
- ✅ **BACKSPACE (8/127)**: Borrar último carácter
- ✅ **ARRIBA (↑)**: Navegar arriba
- ✅ **ABAJO (↓)**: Navegar abajo
- ✅ **Caracteres normales**: Escribir búsqueda

---

## 🔌 INTEGRACIÓN EN `tools.py`

### Ubicación: Línea 1849-1854

```python
# En azdo/tools.py - Función main()

while True:
    try:
        print_header()
        print_menu()
        
        # Tip
        if RICH_AVAILABLE and console:
            console.print("[dim]💡 Tip: Presione '/' para búsqueda interactiva[/dim]\n")
            choice = Prompt.ask("[bold cyan]Seleccione una opción[/]", default="Q").strip().upper()
        else:
            choice = input(f"{Colors.BOLD}Seleccione una opción: {Colors.ENDC}").strip().upper()
        
        # ← AQUÍ ESTÁ LA BÚSQUEDA
        if choice == "/":
            if SEARCH_AVAILABLE:
                choice = search_and_select(TOOLS, TOOL_GROUPS)
                if choice is None:
                    continue
            else:
                console.print("[yellow]⚠️  Búsqueda interactiva no disponible[/yellow]")
                continue
        
        # Procesar opción seleccionada
        if choice in TOOLS:
            run_tool(choice)
        # ... resto del código
```

---

## 📊 ANÁLISIS DE DISPONIBILIDAD

### ¿Dónde está implementada?

```
✅ AZDO (scm/azdo/tools.py)
   ├─ Módulo: interactive_search.py
   ├─ Integración: Línea 1849
   └─ Estado: IMPLEMENTADO

❌ GCP (scm/gcp/tools.py)
   ├─ Módulo: NO EXISTE
   └─ Estado: NO IMPLEMENTADO

❌ AWS (scm/aws/tools.py)
   ├─ Módulo: NO EXISTE
   └─ Estado: NO IMPLEMENTADO

❌ Terminal (scm/terminal/tools.py)
   ├─ Módulo: NO EXISTE
   └─ Estado: NO IMPLEMENTADO

❌ KPI Analyzer (scm/kpi_analyzer/tools.py)
   ├─ Módulo: NO EXISTE
   └─ Estado: NO IMPLEMENTADO

❌ Main (scm/main.py)
   ├─ Módulo: NO EXISTE
   └─ Estado: NO IMPLEMENTADO
```

---

## 🎯 CÓMO USAR LA BÚSQUEDA

### En AZDO Tools

```
1. Ejecutar: python scm/azdo/tools.py
2. Ver menú principal
3. Presionar: /
4. Escribir: nombre de herramienta (ej: "pr", "release", "validator")
5. Navegar: ↑ ↓ (flechas)
6. Seleccionar: ENTER
7. Cancelar: ESC
```

### Ejemplo de búsqueda:

```
Búsqueda: "pr"
Coincidencias: 3

[1] PR Master Checker          (PR)
[2] PR Pipeline Analyzer       (PR)
[3] Properties Branch Diff     (Quality)
```

---

## 🏗️ ARQUITECTURA DE LA BÚSQUEDA

```
┌─────────────────────────────────────────────────────┐
│ tools.py (main loop)                                │
├─────────────────────────────────────────────────────┤
│ if choice == "/":                                   │
│   choice = search_and_select(TOOLS, TOOL_GROUPS)   │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ interactive_search.py                               │
├─────────────────────────────────────────────────────┤
│ def search_and_select()                             │
│   └─ def interactive_search()                       │
│       ├─ Captura de teclas (get_single_char)       │
│       ├─ Búsqueda fuzzy (search_tools)             │
│       ├─ Visualización (print_search_interface)    │
│       └─ Navegación (flechas, ENTER, ESC)          │
└─────────────────────────────────────────────────────┘
```

---

## ⚠️ PROBLEMAS IDENTIFICADOS

### 1. No está documentado en el menú

```python
# Línea 1848-1849 en azdo/tools.py
if RICH_AVAILABLE and console:
    console.print("[dim]💡 Tip: Presione '/' para búsqueda interactiva[/dim]\n")
    # ↑ Solo muestra el tip si RICH está disponible
```

**Problema:**
- ❌ Si RICH no está disponible, el usuario no sabe que existe `/`
- ❌ El tip aparece después de mostrar el menú (puede no verse)

### 2. Solo implementado en AZDO

```
✅ AZDO: Implementado
❌ GCP: No implementado
❌ AWS: No implementado
❌ Terminal: No implementado
❌ KPI: No implementado
❌ Main: No implementado
```

**Problema:**
- ❌ Inconsistencia entre plataformas
- ❌ Usuarios de GCP/AWS no pueden usar búsqueda

### 3. Captura de teclas puede fallar

```python
# Línea 38-77: Captura de teclas
def get_char_windows() -> Optional[str]:
    try:
        import msvcrt
        # ... código
    except Exception:
        pass
    return None  # ← Retorna None si falla
```

**Problema:**
- ⚠️ Si falla la captura, el usuario queda atrapado en el bucle
- ⚠️ No hay manejo de errores explícito

### 4. Búsqueda fuzzy puede ser lenta

```python
# Línea 104: SequenceMatcher
matcher = SequenceMatcher(None, query, text)
return matcher.ratio()
```

**Problema:**
- ⚠️ Con muchas herramientas, puede ser lento
- ⚠️ No hay optimización para búsquedas largas

---

## 📋 CHECKLIST: EXPANDIR BÚSQUEDA A TODAS LAS PLATAFORMAS

### Paso 1: Crear módulo compartido

- [ ] Copiar `interactive_search.py` a `scm/` (nivel raíz)
- [ ] Hacer que sea importable desde todas las plataformas
- [ ] Actualizar imports en todos los `tools.py`

### Paso 2: Integrar en GCP

- [ ] Importar `search_and_select` en `scm/gcp/tools.py`
- [ ] Agregar lógica `if choice == "/"` en main loop
- [ ] Agregar tip en menú
- [ ] Testing

### Paso 3: Integrar en AWS

- [ ] Importar `search_and_select` en `scm/aws/tools.py`
- [ ] Agregar lógica `if choice == "/"` en main loop
- [ ] Agregar tip en menú
- [ ] Testing

### Paso 4: Integrar en Terminal

- [ ] Adaptar para scripts shell (si aplica)
- [ ] O implementar búsqueda de scripts
- [ ] Testing

### Paso 5: Integrar en KPI Analyzer

- [ ] Importar `search_and_select` en `scm/kpi_analyzer/tools.py`
- [ ] Agregar lógica `if choice == "/"` en main loop
- [ ] Agregar tip en menú
- [ ] Testing

### Paso 6: Integrar en Main

- [ ] Crear búsqueda de plataformas (no herramientas)
- [ ] Agregar lógica `if choice == "/"` en main loop
- [ ] Agregar tip en menú
- [ ] Testing

### Paso 7: Mejorar búsqueda

- [ ] Optimizar SequenceMatcher para búsquedas largas
- [ ] Agregar caché de resultados
- [ ] Mejorar manejo de errores
- [ ] Agregar documentación

---

## 🎯 PROPUESTA DE MEJORA

### Crear módulo centralizado: `scm/search_module.py`

```python
# scm/search_module.py

def search_and_select_tools(tools: Dict, tool_groups: Dict) -> Optional[str]:
    """Búsqueda de herramientas (para tools.py)"""
    # Implementación

def search_and_select_platforms(platforms: Dict) -> Optional[str]:
    """Búsqueda de plataformas (para main.py)"""
    # Implementación

def search_and_select_scripts(scripts: Dict) -> Optional[str]:
    """Búsqueda de scripts (para terminal/tools.py)"""
    # Implementación
```

### Beneficios:

```
✅ Código centralizado (DRY)
✅ Reutilizable en todas las plataformas
✅ Fácil de mantener
✅ Fácil de mejorar
✅ Consistencia entre plataformas
```

---

## 📊 IMPACTO ACTUAL

```
┌─────────────────────────────────────────────────────┐
│ PLATAFORMA          │ BÚSQUEDA │ ESTADO            │
├─────────────────────────────────────────────────────┤
│ AZDO                │ ✅ SÍ    │ Implementado      │
│ GCP                 │ ❌ NO    │ No implementado   │
│ AWS                 │ ❌ NO    │ No implementado   │
│ Terminal            │ ❌ NO    │ No implementado   │
│ KPI Analyzer        │ ❌ NO    │ No implementado   │
│ Main (Plataformas)  │ ❌ NO    │ No implementado   │
├─────────────────────────────────────────────────────┤
│ COBERTURA           │ 17%      │ 1 de 6            │
└─────────────────────────────────────────────────────┘
```

---

## 🔄 PRÓXIMOS PASOS

**PENDIENTE TU APROBACIÓN:**

1. ✅ ¿Desea expandir búsqueda a todas las plataformas?
2. ✅ ¿Crear módulo centralizado?
3. ✅ ¿Mejorar la búsqueda fuzzy?
4. ✅ ¿Agregar búsqueda en main.py?

**Una vez aprobado, procederemos con:**
- Crear `scm/search_module.py` centralizado
- Integrar en GCP, AWS, Terminal, KPI, Main
- Mejorar algoritmo de búsqueda
- Testing exhaustivo
- Documentación actualizada

---

**Documento generado automáticamente**  
**Última actualización:** 29 de Junio de 2026  
**Estado:** ANÁLISIS EXHAUSTIVO COMPLETO - PENDIENTE APROBACIÓN DEL USUARIO
