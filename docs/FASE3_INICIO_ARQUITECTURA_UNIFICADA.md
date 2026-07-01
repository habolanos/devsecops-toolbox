# 🚀 FASE 3: ARQUITECTURA UNIFICADA - INICIADA

**Fecha:** 1 de Julio de 2026  
**Estado:** ✅ INICIADA  
**Estimado:** 40 horas  
**Progreso:** 1/5 componentes completados (20%)

---

## 📋 Objetivo

Consolidar funciones duplicadas en un módulo centralizado `base_launcher.py` para:
- Eliminar ~1,080 líneas de código duplicado
- Mejorar mantenibilidad
- Facilitar futuras actualizaciones
- Reducir tiempo de desarrollo

---

## 🎯 Componentes de Fase 3

### 1. ✅ Módulo Base Launcher (COMPLETADO)

**Archivo:** `scm/base_launcher.py`  
**Líneas:** 427  
**Funciones Consolidadas:**

- ✅ `clear_screen()` - Limpia pantalla (Windows/Linux)
- ✅ `print_header()` - Encabezado consistente con Rich/fallback
- ✅ `print_menu()` - Menú principal con Rich/fallback
- ✅ `get_menu_order()` - Ordena menú por grupo y numéricamente
- ✅ `get_auto_tools()` - Genera lista de herramientas para auto_run
- ✅ `build_system_options()` - Construye opciones de sistema dinámicamente
- ✅ `log_command()` - Registra comandos en log global
- ✅ `run_tool()` - Ejecuta herramientas de forma consistente
- ✅ `Colors` - Clase con códigos ANSI

**Beneficios:**
- Código DRY (Don't Repeat Yourself)
- Consistencia en todas las plataformas
- Fácil de mantener y actualizar
- Reutilizable en nuevas plataformas

---

### 2. ⏳ Refactorización de AZDO (PENDIENTE)

**Archivo:** `scm/azdo/tools.py`  
**Líneas Actuales:** ~1,970  
**Líneas Después:** ~1,200 (reducción: 39%)  
**Tiempo Estimado:** 8 horas

**Cambios:**
- Importar `base_launcher`
- Reemplazar `clear_screen()` con `base_launcher.clear_screen()`
- Reemplazar `print_header()` con `base_launcher.print_header()`
- Reemplazar `print_menu()` con `base_launcher.print_menu()`
- Reemplazar `get_menu_order()` con `base_launcher.get_menu_order()`
- Reemplazar `get_auto_tools()` con `base_launcher.get_auto_tools()`
- Reemplazar `build_system_options()` con `base_launcher.build_system_options()`
- Reemplazar `log_command()` con `base_launcher.log_command()`
- Reemplazar `run_tool()` con `base_launcher.run_tool()`

---

### 3. ⏳ Refactorización de AWS (PENDIENTE)

**Archivo:** `scm/aws/tools.py`  
**Líneas Actuales:** ~1,059  
**Líneas Después:** ~600 (reducción: 43%)  
**Tiempo Estimado:** 6 horas

**Cambios:** Idénticos a AZDO

---

### 4. ⏳ Refactorización de GCP (PENDIENTE)

**Archivo:** `scm/gcp/tools.py`  
**Líneas Actuales:** ~1,257  
**Líneas Después:** ~750 (reducción: 40%)  
**Tiempo Estimado:** 8 horas

**Cambios:** Idénticos a AZDO

---

### 5. ⏳ Refactorización de KPI Analyzer (PENDIENTE)

**Archivo:** `scm/kpi_analyzer/tools.py`  
**Líneas Actuales:** ~480  
**Líneas Después:** ~300 (reducción: 37%)  
**Tiempo Estimado:** 6 horas

**Cambios:** Idénticos a AZDO

---

## 📊 Impacto Estimado

| Archivo | Líneas Actuales | Líneas Después | Reducción | % Reducción |
|---------|-----------------|----------------|-----------|------------|
| azdo/tools.py | 1,970 | 1,200 | 770 | 39% |
| aws/tools.py | 1,059 | 600 | 459 | 43% |
| gcp/tools.py | 1,257 | 750 | 507 | 40% |
| kpi_analyzer/tools.py | 480 | 300 | 180 | 37% |
| **TOTAL** | **4,766** | **2,850** | **1,916** | **40%** |

---

## 🔧 Cómo Usar base_launcher.py

### Ejemplo 1: Imprimir Encabezado

```python
from base_launcher import print_header

print_header(
    title="Azure DevOps Tools",
    subtitle="v1.6.14 | by Harold Adrian",
    description="Herramientas para Azure DevOps",
    emoji="🔷",
    border_color="cyan",
    platform_name="AZURE DEVOPS TOOLS"
)
```

### Ejemplo 2: Mostrar Menú

```python
from base_launcher import print_menu

print_menu(
    tools=TOOLS,
    group_order=GROUP_ORDER,
    tool_groups=TOOL_GROUPS,
    status_indicators=STATUS_INDICATORS
)
```

### Ejemplo 3: Obtener Orden del Menú

```python
from base_launcher import get_menu_order

sorted_keys = get_menu_order(
    tools=TOOLS,
    group_order=GROUP_ORDER,
    system_keys=["A", "Q"]
)
```

### Ejemplo 4: Construir Opciones de Sistema

```python
from base_launcher import build_system_options

build_system_options(
    tools=TOOLS,
    group_order=GROUP_ORDER
)
```

### Ejemplo 5: Ejecutar Herramienta

```python
from base_launcher import run_tool

run_tool(
    tool_key="1",
    tools=TOOLS,
    base_dir=BASE_DIR,
    venv_python=venv_python,
    install_requirements_fn=install_requirements,
    get_venv_python_fn=get_venv_python
)
```

---

## 📈 Progreso Fase 3

```
✅ 1. Módulo base_launcher.py          COMPLETADO (427 líneas)
⏳ 2. Refactorización AZDO             PENDIENTE (8 horas)
⏳ 3. Refactorización AWS              PENDIENTE (6 horas)
⏳ 4. Refactorización GCP              PENDIENTE (8 horas)
⏳ 5. Refactorización KPI Analyzer     PENDIENTE (6 horas)

PROGRESO: 1/5 (20%)
TIEMPO ESTIMADO RESTANTE: 28 horas
```

---

## 🎓 Lecciones Aprendidas

1. **Consolidación de Código**
   - Identificar patrones duplicados
   - Crear abstracciones genéricas
   - Mantener flexibilidad con parámetros

2. **Diseño de Módulos**
   - Funciones pequeñas y reutilizables
   - Parámetros claros y documentados
   - Fallbacks para compatibilidad

3. **Mantenibilidad**
   - Código centralizado = actualizaciones más fáciles
   - Menos bugs por cambios inconsistentes
   - Mejor documentación

---

## 🚀 Próximos Pasos

1. **Refactorizar AZDO** (8 horas)
   - Importar base_launcher
   - Reemplazar funciones duplicadas
   - Validar que funcione correctamente

2. **Refactorizar AWS** (6 horas)
   - Mismo proceso que AZDO

3. **Refactorizar GCP** (8 horas)
   - Mismo proceso que AZDO

4. **Refactorizar KPI Analyzer** (6 horas)
   - Mismo proceso que AZDO

5. **Testing Exhaustivo** (12 horas)
   - Verificar que todos los menús funcionen
   - Verificar que todas las herramientas se ejecuten
   - Verificar que los logs se registren correctamente

---

## 📝 Commits Realizados

```
db98857 feat: Crear módulo base_launcher.py para consolidar código duplicado
```

---

## 💡 Notas Importantes

✅ **Módulo base_launcher.py creado**
- 427 líneas de código reutilizable
- 9 funciones consolidadas
- Totalmente documentado
- Compatible con Rich y fallback

⏳ **Refactorización de plataformas pendiente**
- AZDO: 8 horas
- AWS: 6 horas
- GCP: 8 horas
- KPI Analyzer: 6 horas
- Total: 28 horas

📊 **Impacto esperado**
- Reducción de ~1,916 líneas de código (40%)
- Mejora de mantenibilidad
- Consistencia en todas las plataformas

---

**Estado Final:** ✅ **FASE 3 INICIADA - MÓDULO BASE CREADO**  
**Progreso:** 1/5 componentes (20%)  
**Estimado de Finalización:** 28 horas (3-4 días tiempo completo)  
**Próxima Acción:** Refactorizar AZDO tools.py

---

*Creado: 1 de Julio de 2026*  
*Autor: Harold Adrian Bolanos Rodriguez*  
*Proyecto: DevSecOps Toolbox - Refactorización v1.6.14*
