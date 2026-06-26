# 🆙 Actualización: Nuevo Grupo "updatecd" en AZDO Tools

**Fecha:** 25 de Junio de 2026  
**Archivo:** `scm/azdo/tools.py`  
**Versión:** 1.6.13 (patch)

---

## 📋 Resumen de Cambios

Se agregó un nuevo grupo de herramientas `"updatecd"` para organizar mejor las herramientas de actualización y rollback de Release Pipelines en Azure DevOps.

---

## 🔧 Cambios Realizados

### 1. Nuevo Grupo en TOOL_GROUPS

```python
# Línea 92 - Agregado:
"updatecd":   {"name": "Update Release & CD","emoji": "🆙", "color": "cyan"},
```

**Características:**
- **Nombre:** Update Release & CD
- **Emoji:** 🆙 (Up arrow - actualización)
- **Color:** Cyan (para diferenciación visual)

### 2. Herramientas Asignadas al Grupo

Se reasignaron 4 herramientas del grupo `"release"` al nuevo grupo `"updatecd"`:

```
Tool 21: Pipeline CD Update BranchConfig
├─ Antes: group = "release"
└─ Ahora: group = "updatecd"

Tool 22: Pipeline CD Rollback Pipeline
├─ Antes: group = "release"
└─ Ahora: group = "updatecd"

Tool 23: Pipeline Release Rollback
├─ Antes: group = "release"
└─ Ahora: group = "updatecd"

Tool 24: Pipeline Release Restore
├─ Antes: group = "release"
└─ Ahora: group = "updatecd"
```

### 3. Ubicaciones de Cambios

```
Archivo: scm/azdo/tools.py

Línea 92:  Agregar grupo "updatecd" en TOOL_GROUPS
Línea 306: Tool 21 - cambiar group de "release" a "updatecd"
Línea 314: Tool 22 - cambiar group de "release" a "updatecd"
Línea 330: Tool 23 - cambiar group de "release" a "updatecd"
Línea 346: Tool 24 - cambiar group de "release" a "updatecd"
```

---

## 📊 Estructura de Grupos Actualizada

### Antes

```
TOOL_GROUPS = {
    "pr":         {"name": "Pull Requests",      "emoji": "📬", "color": "cyan"},
    "policy":     {"name": "Políticas de Rama",  "emoji": "🔒", "color": "yellow"},
    "release":    {"name": "Releases & CD",      "emoji": "🚀", "color": "green"},
    "drift":      {"name": "Drift & Cambios",    "emoji": "🌪️", "color": "magenta"},
    "validation": {"name": "Validación",         "emoji": "✅", "color": "blue"},
    "security":   {"name": "Seguridad",          "emoji": "🛡️", "color": "red"},
    "inventory":  {"name": "Inventario",         "emoji": "📋", "color": "bright_white"},
    "health":     {"name": "Health Score",       "emoji": "📊", "color": "bright_cyan"},
    "quality":    {"name": "Calidad Deploy",     "emoji": "🎯", "color": "pink"},
    "system":     {"name": "Sistema",            "emoji": "⚙️", "color": "white"},
}
```

### Después

```
TOOL_GROUPS = {
    "pr":         {"name": "Pull Requests",      "emoji": "📬", "color": "cyan"},
    "policy":     {"name": "Políticas de Rama",  "emoji": "🔒", "color": "yellow"},
    "release":    {"name": "Releases & CD",      "emoji": "🚀", "color": "green"},
    "updatecd":   {"name": "Update Release & CD","emoji": "🆙", "color": "cyan"},  ✨ NUEVO
    "drift":      {"name": "Drift & Cambios",    "emoji": "🌪️", "color": "magenta"},
    "validation": {"name": "Validación",         "emoji": "✅", "color": "blue"},
    "security":   {"name": "Seguridad",          "emoji": "🛡️", "color": "red"},
    "inventory":  {"name": "Inventario",         "emoji": "📋", "color": "bright_white"},
    "health":     {"name": "Health Score",       "emoji": "📊", "color": "bright_cyan"},
    "quality":    {"name": "Calidad Deploy",     "emoji": "🎯", "color": "pink"},
    "system":     {"name": "Sistema",            "emoji": "⚙️", "color": "white"},
}
```

---

## 📚 Herramientas por Grupo

### Grupo: Pull Requests (📬)
```
Tool 1:   PR Master Checker
Tool 1b:  PR Pipeline Analyzer
```

### Grupo: Políticas de Rama (🔒)
```
Tool 2:   Branch Policy Checker
Tool 2b:  Branch Lock Checker
```

### Grupo: Releases & CD (🚀)
```
Tool 3:   Release CD Health
Tool 5:   Release Deep Dive
Tool 25:  Release Explorer
```

### Grupo: Update Release & CD (🆙) ✨ NUEVO
```
Tool 21:  Pipeline CD Update BranchConfig
Tool 22:  Pipeline CD Rollback Pipeline
Tool 23:  Pipeline Release Rollback
Tool 24:  Pipeline Release Restore
```

### Grupo: Drift & Cambios (🌪️)
```
Tool 4:   Pipeline Drift
```

### Grupo: Validación (✅)
```
Tool 6:   Task Validator
```

### Grupo: Seguridad (🛡️)
```
Tool 7:   Pipeline Logs Scanner
Tool 8:   Repo Vulnerabilities Scanner
```

### Grupo: Inventario (📋)
```
Tool 9:   CICD Inventory
Tool 10:  GKE Pipelines Inventory
Tool 11:  Pending Approvals
Tool 12:  Branches Created
Tool 13:  Hotfix Branches Inventory
Tool 14:  CI Pipeline Inventory (Detailed)
Tool 15:  CD Pipeline Inventory (Detailed)
Tool 17:  Prod Deploy Inventory
```

### Grupo: Health Score (📊)
```
Tool 16:  Pipeline Health Score (DORA)
Tool 18:  Pipeline Status
```

### Grupo: Calidad Deploy (🎯)
```
(Reservado para futuras herramientas)
```

### Grupo: Sistema (⚙️)
```
Tool A:   Ejecutar Todos
Tool B:   Ejecutar Todo + JSON
```

---

## 🎯 Razón de la Separación

### Antes (Grupo "release")
```
Releases & CD (🚀)
├─ Tool 3:  Release CD Health (análisis de salud)
├─ Tool 5:  Release Deep Dive (análisis profundo)
├─ Tool 21: Pipeline CD Update (actualización)
├─ Tool 22: Pipeline CD Rollback (rollback)
├─ Tool 23: Pipeline Release Rollback (rollback)
├─ Tool 24: Pipeline Release Restore (restauración)
└─ Tool 25: Release Explorer (exploración)
```

**Problema:** Mezcla de herramientas de análisis con herramientas de actualización/rollback

### Después (Grupos separados)
```
Releases & CD (🚀)
├─ Tool 3:  Release CD Health (análisis)
├─ Tool 5:  Release Deep Dive (análisis)
└─ Tool 25: Release Explorer (exploración)

Update Release & CD (🆙)
├─ Tool 21: Pipeline CD Update (actualización)
├─ Tool 22: Pipeline CD Rollback (rollback)
├─ Tool 23: Pipeline Release Rollback (rollback)
└─ Tool 24: Pipeline Release Restore (restauración)
```

**Ventajas:**
- ✅ Separación clara de responsabilidades
- ✅ Mejor organización visual en menús
- ✅ Facilita búsqueda de herramientas
- ✅ Agrupa operaciones destructivas (rollback/restore)
- ✅ Diferencia análisis de actualización

---

## 📈 Impacto en la UI

### Menú de Herramientas AZDO

Cuando se ejecuta `python scm/main.py` → Opción 2 (AZDO), ahora se verá:

```
🚀 Releases & CD
  ├─ Tool 3:  Release CD Health
  ├─ Tool 5:  Release Deep Dive
  └─ Tool 25: Release Explorer

🆙 Update Release & CD (NUEVO)
  ├─ Tool 21: Pipeline CD Update BranchConfig
  ├─ Tool 22: Pipeline CD Rollback Pipeline
  ├─ Tool 23: Pipeline Release Rollback
  └─ Tool 24: Pipeline Release Restore
```

---

## 🔄 Compatibilidad

### Cambios Compatibles

```
✅ No afecta a opciones A y B (Ejecutar Todos)
✅ No afecta a herramientas individuales
✅ No afecta a argumentos de línea de comandos
✅ No afecta a salidas (JSON, CSV, Excel)
✅ No afecta a configuración en config.json
```

### Cambios Visuales

```
⚠️ Menú de herramientas AZDO reorganizado
⚠️ Nuevo grupo visible en listados
⚠️ Cambio de color para herramientas 21-24
```

---

## 📝 Actualización de Documentación Requerida

### Archivos a Actualizar

```
1. README.md
   ├─ Actualizar versión a 1.6.13
   ├─ Agregar entrada en historial de cambios
   └─ Documentar nuevo grupo

2. docs/AZDO_TOOLS.md (si existe)
   ├─ Reorganizar herramientas por grupo
   └─ Documentar nuevo grupo

3. docs/TOOL_GROUPS.md (si existe)
   ├─ Agregar descripción del grupo "updatecd"
   └─ Explicar razón de separación

4. config.json.template
   ├─ Agregar configuración para grupo "updatecd" (si aplica)
   └─ Documentar nuevas opciones
```

---

## 🧪 Testing

### Verificación Manual

```bash
# 1. Ejecutar menú AZDO
python scm/main.py
# Seleccionar: 2 (AZDO)

# Resultado esperado:
# - Nuevo grupo "🆙 Update Release & CD" visible
# - Herramientas 21-24 bajo nuevo grupo
# - Herramientas 3, 5, 25 bajo "🚀 Releases & CD"

# 2. Ejecutar herramientas individuales
python scm/azdo/tools.py
# Seleccionar: 21 (Pipeline CD Update)

# Resultado esperado:
# - Herramienta ejecuta correctamente
# - Grupo mostrado como "🆙 Update Release & CD"
```

### Verificación de Código

```bash
# Verificar que el grupo está definido
grep -n "updatecd" scm/azdo/tools.py

# Resultado esperado:
# 92:    "updatecd":   {"name": "Update Release & CD","emoji": "🆙", "color": "cyan"},
# 306:        "group":       "updatecd",
# 314:        "group":       "updatecd",
# 330:        "group":       "updatecd",
# 346:        "group":       "updatecd",
```

---

## 📊 Estadísticas

```
Cambios Realizados:
├─ Nuevo grupo: 1
├─ Herramientas reasignadas: 4
├─ Líneas modificadas: 5
└─ Archivos modificados: 1 (tools.py)

Grupos Totales: 11
├─ Grupos con herramientas: 9
└─ Grupos reservados: 2 (quality, system)

Herramientas por Grupo:
├─ pr:         2 herramientas
├─ policy:     2 herramientas
├─ release:    3 herramientas
├─ updatecd:   4 herramientas (NUEVO)
├─ drift:      1 herramienta
├─ validation: 1 herramienta
├─ security:   2 herramientas
├─ inventory:  8 herramientas
├─ health:     2 herramientas
└─ quality:    0 herramientas (reservado)
```

---

## ✨ Próximos Pasos

### Recomendaciones

```
1. Commit de cambios
   git add scm/azdo/tools.py
   git commit -m "feat: Agregar grupo 'updatecd' para herramientas de actualización/rollback"

2. Actualizar documentación
   - README.md (versión 1.6.13)
   - Crear AZDO_TOOLS_GROUPS.md si no existe

3. Testing
   - Verificar menú AZDO
   - Ejecutar herramientas 21-24
   - Verificar opciones A y B

4. Comunicación
   - Documentar cambio en changelog
   - Actualizar documentación de usuario
```

---

## 📚 Referencias

- **Archivo:** `scm/azdo/tools.py`
- **Líneas:** 92, 306, 314, 330, 346
- **Grupos:** 11 totales
- **Herramientas:** 27 totales (25 + A + B)

---

**Documento generado automáticamente**  
**Última actualización:** 25 de Junio de 2026
