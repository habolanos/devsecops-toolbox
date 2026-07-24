# 🔒 Validación Exacta de Stages - Parámetro `exact_match`

**Fecha:** 24 de Julio de 2026  
**Versión:** 1.0  
**Status:** ✅ Especificación Completa

---

## ❓ Pregunta

¿Cómo garantizar que SOLO se actualicen pipelines que tengan EXACTAMENTE los 4 stages buscados, sin stages adicionales?

---

## ✅ Solución: Parámetro `exact_match`

Agregar un parámetro `exact_match` en la sección `search` para validar que el pipeline tenga EXACTAMENTE los stages especificados.

---

## 📋 Especificación

### **Parámetro: `exact_match`**

```yaml
search:
  exact_match: true  # ← Nuevo parámetro
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"
```

**Valores:**
- `true` - Pipeline debe tener EXACTAMENTE estos 4 stages (no más, no menos)
- `false` (default) - Pipeline puede tener estos 4 + otros adicionales

---

## 🎯 Comportamiento

### **Con `exact_match: true`**

```yaml
search:
  exact_match: true
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"
```

**Validación:**
```
Pipeline 1: Build, Test, Deploy, Validate
            ✅ EXACTAMENTE 4 → Se actualiza

Pipeline 2: Build, Test, Deploy, Validate, Security
            ❌ 5 stages (tiene 1 extra) → Se IGNORA

Pipeline 3: Build, Test, Deploy
            ❌ 3 stages (falta 1) → Se IGNORA
```

---

### **Con `exact_match: false` (default)**

```yaml
search:
  exact_match: false  # o simplemente omitir
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"
```

**Validación:**
```
Pipeline 1: Build, Test, Deploy, Validate
            ✅ Tiene los 4 → Se actualiza

Pipeline 2: Build, Test, Deploy, Validate, Security
            ✅ Tiene los 4 + 1 extra → Se actualiza

Pipeline 3: Build, Test, Deploy
            ❌ Falta 1 → Se IGNORA
```

---

## 📊 Comparativa

| Escenario | `exact_match: true` | `exact_match: false` |
|-----------|-------------------|-------------------|
| **Exactamente 4 stages** | ✅ Se actualiza | ✅ Se actualiza |
| **4 + 1 adicional** | ❌ Se ignora | ✅ Se actualiza |
| **4 + 2 adicionales** | ❌ Se ignora | ✅ Se actualiza |
| **3 stages (falta 1)** | ❌ Se ignora | ❌ Se ignora |
| **Garantiza integridad** | ✅ Sí | ❌ No |

---

## 💡 Ejemplos Prácticos

### **Ejemplo 1: Validación Exacta (Recomendado)**

**Template:**
```yaml
metadata:
  name: "Reordenar stages - Validación exacta"
  version: "1.0"
  comment: |
    Solo actualiza pipelines con EXACTAMENTE 4 stages
    Garantiza integridad del pipeline

search:
  exact_match: true  # ← Validación exacta
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"

update:
  stages:
    - name: "Build"
      rank: 1
    - name: "Deploy"
      rank: 2
    - name: "Test"
      rank: 3
    - name: "Validate"
      rank: 4
```

**Resultado:**
```
Pipeline A: Build, Test, Deploy, Validate
            ✅ ACTUALIZADO

Pipeline B: Build, Test, Deploy, Validate, Security
            ❌ IGNORADO (tiene 5 stages)

Pipeline C: Build, Test, Deploy, Validate, Approval, Security
            ❌ IGNORADO (tiene 6 stages)
```

---

### **Ejemplo 2: Validación Flexible (Default)**

**Template:**
```yaml
metadata:
  name: "Reordenar stages - Validación flexible"
  version: "1.0"

search:
  # exact_match: false (default, se puede omitir)
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"

update:
  stages:
    - name: "Build"
      rank: 1
    - name: "Deploy"
      rank: 2
    - name: "Test"
      rank: 3
    - name: "Validate"
      rank: 4
```

**Resultado:**
```
Pipeline A: Build, Test, Deploy, Validate
            ✅ ACTUALIZADO

Pipeline B: Build, Test, Deploy, Validate, Security
            ✅ ACTUALIZADO (ignora Security)

Pipeline C: Build, Test, Deploy, Validate, Approval, Security
            ✅ ACTUALIZADO (ignora Approval y Security)
```

---

## 🔍 Cómo Funciona Internamente

### **Paso 1: Validar Search**

```python
# Buscar stages
stages_encontrados = []
for stage_buscado in search.stages:
    if stage_buscado.name en pipeline.stages:
        stages_encontrados.append(stage_buscado)

# Verificar que se encontraron TODOS
if len(stages_encontrados) != len(search.stages):
    ERROR: "No se encontraron todos los stages"
    return False
```

### **Paso 2: Validar Exactitud (NUEVO)**

```python
# Si exact_match está habilitado
if search.exact_match == True:
    # Verificar que el pipeline tiene EXACTAMENTE los stages
    if len(pipeline.stages) != len(search.stages):
        ERROR: "Pipeline no tiene exactamente los stages buscados"
        return False
    
    # Verificar que NO hay stages adicionales
    for stage_pipeline in pipeline.stages:
        if stage_pipeline.name no en search.stages:
            ERROR: "Pipeline tiene stages adicionales"
            return False
```

### **Paso 3: Aplicar Cambios**

```python
# Si todas las validaciones pasaron
aplicar_cambios(pipeline, update)
```

---

## 📝 Casos de Uso

### **Caso 1: Migración Crítica (Usar `exact_match: true`)**

**Escenario:** Migración de infraestructura donde necesitas garantizar que SOLO los pipelines con estructura exacta se actualicen.

```yaml
search:
  exact_match: true
  stages:
    - name: "Build"
    - name: "Deploy"
    - name: "Producción"
```

**Razón:** Evitar actualizar pipelines con stages adicionales que podrían tener lógica especial.

---

### **Caso 2: Actualización Masiva (Usar `exact_match: false`)**

**Escenario:** Actualizar imagen Docker en todos los pipelines, sin importar si tienen stages adicionales.

```yaml
search:
  exact_match: false
  stages:
    - name: "Build"
    - name: "Deploy"
```

**Razón:** Flexibilidad para actualizar múltiples variantes de pipelines.

---

### **Caso 3: Reordenamiento Controlado (Usar `exact_match: true`)**

**Escenario:** Reordenar stages en pipelines específicos con estructura exacta.

```yaml
search:
  exact_match: true
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"
```

**Razón:** Garantizar que solo se reordenan pipelines con la estructura esperada.

---

## ✅ Mejores Prácticas

### ✅ DO

```yaml
# 1. Usar exact_match: true para migraciones críticas
search:
  exact_match: true
  stages:
    - name: "Build"
    - name: "Deploy"
    - name: "Producción"

# 2. Documentar por qué se usa exact_match
metadata:
  comment: |
    Usa exact_match: true para garantizar integridad
    Solo actualiza pipelines con EXACTAMENTE 3 stages

# 3. Validar el resultado
# Revisar reporte para confirmar que se actualizaron
# los pipelines esperados
```

### ❌ DON'T

```yaml
# 1. No omitir exact_match sin pensar
# Si necesitas validación exacta, especifícalo

# 2. No asumir que exact_match es default
# Siempre especificar si lo necesitas

# 3. No usar exact_match: true sin revisar
# Primero hacer dry_run para ver qué se actualiza
```

---

## 🔒 Validación de Integridad

### **Checklist de Integridad**

```yaml
metadata:
  name: "Actualización con validación exacta"
  version: "1.0"

search:
  exact_match: true  # ← Garantiza integridad
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"

options:
  dry_run: true  # ← Primero validar
  rollback_on_error: true  # ← Poder revertir
```

**Proceso:**
1. ✅ Especificar `exact_match: true`
2. ✅ Usar `dry_run: true` primero
3. ✅ Revisar reporte de qué se actualiza
4. ✅ Confirmar que son los pipelines esperados
5. ✅ Cambiar a `dry_run: false` y ejecutar

---

## 📊 Reporte de Validación

### **Con `exact_match: true`**

```json
{
  "timestamp": "2026-07-24T00:33:00Z",
  "template": "Reordenar stages - Validación exacta",
  "search": {
    "exact_match": true,
    "stages": ["Build", "Test", "Deploy", "Validate"]
  },
  "summary": {
    "total_pipelines": 10,
    "matched": 4,
    "ignored_exact_mismatch": 6,
    "success": 4,
    "failed": 0
  },
  "details": [
    {
      "definition_id": 3388,
      "name": "Pipeline A",
      "stage_count": 4,
      "exact_match": true,
      "status": "updated"
    },
    {
      "definition_id": 3389,
      "name": "Pipeline B",
      "stage_count": 5,
      "exact_match": false,
      "status": "ignored",
      "reason": "Pipeline has 5 stages, expected exactly 4"
    }
  ]
}
```

---

## 🎯 Sintaxis Completa

### **Template con `exact_match`**

```yaml
metadata:
  name: "Nombre del template"
  version: "1.0"
  description: "Descripción"
  comment: |
    Comentario con contexto
    Explica por qué se usa exact_match

search:
  exact_match: true  # ← NUEVO PARÁMETRO
  stages:
    - name: "Stage1"
    - name: "Stage2"
    - name: "Stage3"
    - name: "Stage4"

update:
  stages:
    - name: "Stage1"
      rank: 1
    - name: "Stage2"
      rank: 2
    - name: "Stage3"
      rank: 3
    - name: "Stage4"
      rank: 4

options:
  dry_run: false
  rollback_on_error: true
```

---

## 📚 Parámetros Disponibles

| Parámetro | Ubicación | Tipo | Default | Descripción |
|-----------|-----------|------|---------|------------|
| **exact_match** | `search` | boolean | `false` | Validar exactitud de stages |
| **dry_run** | `options` | boolean | `false` | Simular sin aplicar cambios |
| **rollback_on_error** | `options` | boolean | `true` | Revertir si hay error |

---

## 🆚 Comparativa: Con vs Sin `exact_match`

### **Sin `exact_match` (Flexible)**

```yaml
search:
  stages:
    - name: "Build"
    - name: "Deploy"
```

**Resultado:**
```
Pipeline: Build, Deploy, Security, Approval
          ✅ Se actualiza (tiene los 2 buscados)
```

---

### **Con `exact_match: true` (Estricto)**

```yaml
search:
  exact_match: true
  stages:
    - name: "Build"
    - name: "Deploy"
```

**Resultado:**
```
Pipeline: Build, Deploy, Security, Approval
          ❌ Se ignora (tiene 4, se esperan 2)
```

---

## 🔐 Garantía de Integridad

**Con `exact_match: true`, garantizas:**

✅ Solo se actualizan pipelines con estructura exacta  
✅ No hay actualizaciones inesperadas  
✅ Integridad del pipeline garantizada  
✅ Fácil auditoría de qué se actualizó  
✅ Reversión segura si es necesario  

---

## 💡 Recomendaciones

### **Usar `exact_match: true` cuando:**

- ✅ Migración crítica de infraestructura
- ✅ Cambios en estructura de stages
- ✅ Reordenamiento de stages
- ✅ Necesitas garantizar integridad
- ✅ Pipelines tienen variantes

### **Usar `exact_match: false` cuando:**

- ✅ Actualización de imagen Docker
- ✅ Cambio de variables de entorno
- ✅ Actualización de conexiones
- ✅ Cambios que aplican a cualquier pipeline
- ✅ Actualización masiva flexible

---

## 🎓 Conclusión

**Para garantizar integridad, usa:**

```yaml
search:
  exact_match: true
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"
```

**Esto asegura que SOLO se actualicen pipelines con EXACTAMENTE estos 4 stages.**

---

**Status:** ✅ Especificación Completa  
**Versión:** 1.0  
**Fecha:** 24 de Julio de 2026
