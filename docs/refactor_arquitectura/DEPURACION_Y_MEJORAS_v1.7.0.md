# 🔧 DEPURACIÓN Y MEJORAS: Pendientes para v1.7.1+

**Fecha:** 8 de Septiembre de 2026  
**Versión:** 1.0  
**Estado:** 📋 PENDIENTES DE IMPLEMENTACIÓN

---

## 🎯 RESUMEN EJECUTIVO

Se han identificado **5 bugs potenciales** y **5 mejoras recomendadas** que requieren implementación.

---

## 🐛 BUGS PENDIENTES (5 total)

### 1. 🔴 CRÍTICA: SearchHistory - Errores Silenciados

**Ubicación:** `scm/search_module_advanced.py:36-80`

**Problema:**
```python
def _load_from_file(self) -> None:
    try:
        history_file = Path.home() / ".devsecops_search_history"
        if history_file.exists():
            with open(history_file, 'r') as f:
                self.history = [line.strip() for line in f.readlines()][:self.max_items]
    except Exception:
        pass  # ❌ Silencia errores
```

**Impacto:** Errores de lectura/escritura se silencian, historial puede no persistir

**Solución Recomendada:**
```python
def _load_from_file(self) -> None:
    try:
        history_file = Path.home() / ".devsecops_search_history"
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                self.history = [line.strip() for line in f.readlines()][:self.max_items]
    except FileNotFoundError:
        pass  # Archivo no existe, es normal
    except PermissionError:
        print("⚠️  No hay permisos para leer historial")
    except Exception as e:
        print(f"⚠️  Error al cargar historial: {e}")
```

---

### 2. 🔴 CRÍTICA: ExportManager - Directorio No Validado

**Ubicación:** `scm/export_manager.py:41-52`

**Problema:**
```python
def __init__(self, tool_name: str, tool_version: str = "1.0.0"):
    self.tool_name = tool_name
    self.tool_version = tool_version
    self.output_dir = get_output_dir("outcome")  # ❌ No valida si es escribible
    self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
```

**Impacto:** Si el directorio no es escribible, falla silenciosamente

**Solución Recomendada:**
```python
def __init__(self, tool_name: str, tool_version: str = "1.0.0"):
    self.tool_name = tool_name
    self.tool_version = tool_version
    self.output_dir = get_output_dir("outcome")
    
    # Validar que el directorio es escribible
    try:
        test_file = self.output_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
    except (PermissionError, OSError) as e:
        raise RuntimeError(f"No se puede escribir en {self.output_dir}: {e}")
    
    self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
```

---

### 3. 🔴 CRÍTICA: RunTool - Manejo de Errores Incompleto

**Ubicación:** `scm/base_launcher.py:325-428`

**Problema:**
```python
def run_tool(tool_key: str, tools: Dict, base_dir: Path, ...):
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al ejecutar la herramienta: {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida por el usuario.{Colors.ENDC}")
    # ❌ No maneja TimeoutExpired, FileNotFoundError, etc.
```

**Impacto:** Errores de timeout y script no encontrado no se reportan bien

**Solución Recomendada:**
```python
def run_tool(tool_key: str, tools: Dict, base_dir: Path, ...):
    try:
        subprocess.run(cmd, check=True, timeout=3600)  # 1 hora timeout
    except subprocess.TimeoutExpired:
        print(f"{Colors.FAIL}Error: La herramienta tardó demasiado (timeout).{Colors.ENDC}")
    except FileNotFoundError:
        print(f"{Colors.FAIL}Error: No se encontró el script {script_path}{Colors.ENDC}")
    except PermissionError:
        print(f"{Colors.FAIL}Error: Permisos insuficientes para ejecutar {script_path}{Colors.ENDC}")
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al ejecutar la herramienta (código {e.returncode}): {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida por el usuario.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Error inesperado: {e}{Colors.ENDC}")
```

---

### 4. 🟠 ALTA: FuzzyMatch - Algoritmo No Optimizado

**Ubicación:** `scm/search_module.py:95-135`

**Problema:**
```python
def fuzzy_match(query: str, text: str) -> float:
    # ...
    matcher = SequenceMatcher(None, query, text)
    ratio = matcher.ratio()
    return ratio if ratio >= 0.5 else 0.0  # ❌ Threshold fijo
```

**Impacto:** Threshold de 0.5 es arbitrario, no funciona bien con queries cortas

**Solución Recomendada:**
```python
def fuzzy_match(query: str, text: str, min_threshold: float = 0.5) -> float:
    """Calcula similitud fuzzy entre query y text."""
    if not query:
        return 1.0
    
    query = query.lower().strip()
    text = text.lower().strip()
    
    # Coincidencia exacta
    if query == text:
        return 1.0
    
    # Coincidencia exacta como substring
    if query in text:
        return 0.95
    
    # Coincidencia al inicio
    if text.startswith(query):
        return 0.90
    
    # Coincidencia de palabra completa
    words = text.split()
    for word in words:
        if word.startswith(query):
            return 0.85
    
    # Fuzzy matching con SequenceMatcher
    matcher = SequenceMatcher(None, query, text)
    ratio = matcher.ratio()
    
    # Aplicar threshold configurable
    return ratio if ratio >= min_threshold else 0.0
```

---

### 5. 🟠 ALTA: PrintMenu - Ancho de Columnas Fijo

**Ubicación:** `scm/base_launcher.py:231-276`

**Problema:**
```python
def _print_menu_rich(tools: Dict, group_order: List[str], tool_groups: Dict):
    table = Table(...)
    table.add_column("#", justify="center", style="bold white", width=4)
    table.add_column("Grupo", justify="left", width=18)  # ❌ Ancho fijo
    table.add_column("Herramienta", justify="left", style="white")
    table.add_column("Descripción", justify="left", style="dim", min_width=40)
```

**Impacto:** Nombres largos se cortan, no se adapta a terminales pequeñas

**Solución Recomendada:**
```python
def _print_menu_rich(tools: Dict, group_order: List[str], tool_groups: Dict):
    import shutil
    terminal_width = shutil.get_terminal_size((80, 20)).columns
    
    # Calcular anchos adaptativos
    col_width = max(4, terminal_width // 4)
    
    table = Table(...)
    table.add_column("#", justify="center", style="bold white", width=4)
    table.add_column("Grupo", justify="left", width=min(18, col_width))
    table.add_column("Herramienta", justify="left", style="white", width=min(30, col_width))
    table.add_column("Descripción", justify="left", style="dim", min_width=20)
```

---

## 📈 MEJORAS RECOMENDADAS (5 total)

### 1. Logging Centralizado
**Ubicación:** Crear `scm/logger.py`  
**Propósito:** Centralizar logging en todas las herramientas  
**Esfuerzo:** Medio  
**Prioridad:** 🟠 Alta

Crear clase `DevSecOpsLogger` con handlers para archivo y consola.

---

### 2. Validación de Configuración
**Ubicación:** Crear `scm/config_validator.py`  
**Propósito:** Validar config.json antes de usar  
**Esfuerzo:** Bajo  
**Prioridad:** 🟠 Alta

Crear clase `ConfigValidator` para validar campos requeridos por plataforma.

---

### 3. Métricas de Rendimiento
**Ubicación:** Crear `scm/metrics.py`  
**Propósito:** Rastrear rendimiento de herramientas  
**Esfuerzo:** Medio  
**Prioridad:** 🟡 Media

Crear clase `PerformanceMetrics` con decorador `@metrics.track()`.

---

### 4. Modo de Prueba
**Ubicación:** Crear `scm/test_mode.py`  
**Propósito:** Ejecutar herramientas en modo de prueba  
**Esfuerzo:** Medio  
**Prioridad:** 🟡 Media

Crear clase `TestMode` con mock de llamadas API.

---

### 5. Auditoría Completa
**Ubicación:** Crear `scm/audit.py`  
**Propósito:** Rastrear todas las acciones  
**Esfuerzo:** Alto  
**Prioridad:** 🟡 Media

Crear clase `AuditLog` que registre acciones en JSONL.

---

## 📊 MATRIZ DE PRIORIDADES

| Bug/Mejora | Impacto | Esfuerzo | Prioridad | v |
|-----------|---------|----------|-----------|---|
| SearchHistory | Alto | Bajo | 🔴 Crítica | 1.7.1 |
| ExportManager | Alto | Bajo | 🔴 Crítica | 1.7.1 |
| RunTool | Alto | Medio | 🔴 Crítica | 1.7.1 |
| FuzzyMatch | Bajo | Bajo | 🟠 Alta | 1.7.2 |
| PrintMenu | Bajo | Bajo | 🟠 Alta | 1.7.2 |
| Logging | Medio | Medio | 🟠 Alta | 1.7.2 |
| Config Validator | Medio | Bajo | 🟠 Alta | 1.7.2 |
| Métricas | Bajo | Medio | 🟡 Media | 1.8.0 |
| Test Mode | Bajo | Medio | 🟡 Media | 1.8.0 |
| Auditoría | Medio | Alto | 🟡 Media | 1.8.0 |

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### v1.7.1 (Crítica - 4-6 horas)
- [ ] Fix SearchHistory - Manejo de errores
- [ ] Fix ExportManager - Validación de directorio
- [ ] Fix RunTool - Manejo de excepciones completo
- [ ] Ejecutar todos los tests
- [ ] Validar en Windows, Linux, macOS

### v1.7.2 (Alta - 8-12 horas)
- [ ] Fix FuzzyMatch - Algoritmo optimizado
- [ ] Fix PrintMenu - Ancho adaptativo
- [ ] Agregar Logging Centralizado
- [ ] Agregar Validación de Configuración
- [ ] Agregar 20+ tests nuevos

### v1.8.0 (Media - 16-24 horas)
- [ ] Agregar Métricas de Rendimiento
- [ ] Agregar Modo de Prueba
- [ ] Agregar Auditoría Completa
- [ ] Actualizar documentación
- [ ] Agregar 30+ tests nuevos

---

## 📞 REFERENCIAS

### Código Actual
- `scm/base_launcher.py` - 428 líneas
- `scm/export_manager.py` - 392 líneas
- `scm/search_module.py` - 446 líneas
- `scm/search_module_advanced.py` - 479 líneas

### Documentación Relacionada
- `docs/refactor_arquitectura/ANALISIS_IMPLEMENTACION_ACTUAL_v1.7.0.md`
- `docs/refactor_arquitectura/GUIA_BASE_LAUNCHER.md`
- `docs/refactor_arquitectura/GUIA_BUSQUEDA_INTERACTIVA.md`

---

**Documento:** DEPURACION_Y_MEJORAS_v1.7.0.md  
**Fecha:** 8 de Septiembre de 2026  
**Versión:** 1.0  
**Estado:** ✅ COMPLETO
