# ✅ Validación: Reordenamiento de Stages con Rank

**Fecha:** 23 de Julio de 2026  
**Status:** ✅ VALIDADO - Ejemplos Encontrados  
**Ubicación:** `docs/features/feature_actualizacion_pipeline_cd_with_template/`

---

## 📋 Resumen

Se han validado **3 ejemplos completos** de reordenamiento de stages usando `rank` en los documentos de la feature:

1. ✅ **Cambiar Orden de Ejecución (Masivo)** - Ejemplo básico
2. ✅ **Reorganizar con Cambios de Dependencias** - Ejemplo intermedio
3. ✅ **Insertar Stage en Posición Específica** - Ejemplo avanzado

---

## 🎯 Ejemplo 1: Cambiar Orden de Ejecución (Masivo)

**Ubicación:** `07_COMENTARIOS_Y_REORGANIZACION.md` (líneas 260-323)

### Caso de Uso
Cambiar el orden en que se ejecutan los stages de forma masiva.

### Template YAML
```yaml
metadata:
  name: "Reorganizar pipeline stages"
  version: "1.0"
  description: "Cambiar orden de ejecución de stages"

search:
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"

update:
  stages:
    # Nuevo orden: Build → Deploy → Test → Validate
    - name: "Build"
      rank: 1
    
    - name: "Deploy"
      rank: 2
    
    - name: "Test"
      rank: 3
    
    - name: "Validate"
      rank: 4

options:
  dry_run: false
  rollback_on_error: true
```

### Resultado
```
Antes:
1. Build
2. Test
3. Deploy
4. Validate

Después:
1. Build
2. Deploy
3. Test
4. Validate
```

### Características
- ✅ Usa `rank` para especificar el orden
- ✅ Números secuenciales (1, 2, 3, 4)
- ✅ Aplica a múltiples stages
- ✅ Soporta `dry_run` para validación
- ✅ Soporta `rollback_on_error` para reversión

---

## 🎯 Ejemplo 2: Reorganizar con Cambios de Dependencias

**Ubicación:** `07_COMENTARIOS_Y_REORGANIZACION.md` (líneas 327-374)

### Caso de Uso
Reorganizar stages Y actualizar las dependencias entre ellos.

### Template YAML
```yaml
metadata:
  name: "Reorganizar y actualizar dependencias"
  version: "2.0"

search:
  stages:
    - name: "QA"
    - name: "Staging"
    - name: "Producción"

update:
  stages:
    # Mover Staging a primer lugar
    - name: "Staging"
      rank: 1
    
    # Mover QA a segundo lugar
    - name: "QA"
      rank: 2
    
    # Producción en tercer lugar
    - name: "Producción"
      rank: 3
      # Actualizar dependencias
      fields:
        - path: "preDeployApprovals.approvals[0].approver.displayName"
          old_value: "QA Team"
          new_value: "Staging Team"
```

### Características
- ✅ Combina `rank` con cambios de dependencias
- ✅ Actualiza aprobadores después de reordenar
- ✅ Mantiene coherencia entre orden y dependencias
- ✅ Permite cambios de campos en el mismo stage

---

## 🎯 Ejemplo 3: Insertar Stage en Posición Específica

**Ubicación:** `07_COMENTARIOS_Y_REORGANIZACION.md` (líneas 378-436)

### Caso de Uso
Insertar un nuevo stage en una posición específica y reordenar los demás.

### Template YAML
```yaml
metadata:
  name: "Insertar stage de seguridad"
  version: "1.0"

search:
  stages:
    - name: "Build"
    - name: "Deploy"
    - name: "Producción"

update:
  stages:
    # Insertar Security Check entre Build y Deploy
    - name: "Security Check"
      action: "add"
      position: "between"
      after_stage: "Build"
      before_stage: "Deploy"
      definition:
        id: 2
        name: "Security Check"
        rank: 2
        deployPhases:
          - id: 1
            name: "Security Validation"
            deploymentInput:
              tasks:
                - displayName: "Run Security Scan"
                  enabled: true
                  task:
                    id: "6C731787-BC2C-4436-8290-A81493FFEA35"
                    versionSpec: "3.*"
                  inputs:
                    script: |
                      #!/bin/bash
                      echo "Running security scan..."
    
    # Deploy y Producción se reordenan automáticamente
    - name: "Deploy"
      rank: 3
    
    - name: "Producción"
      rank: 4
```

### Resultado
```
Antes:
1. Build
2. Deploy
3. Producción

Después:
1. Build
2. Security Check (NUEVO)
3. Deploy
4. Producción
```

### Características
- ✅ Usa `action: "add"` para insertar
- ✅ Usa `position: "between"` para especificar ubicación
- ✅ Especifica `after_stage` y `before_stage`
- ✅ Incluye definición completa del nuevo stage
- ✅ Reordena automáticamente los stages posteriores

---

## 📊 Comparativa de Métodos

| Aspecto | Ejemplo 1 | Ejemplo 2 | Ejemplo 3 |
|---------|-----------|-----------|-----------|
| **Propósito** | Reordenar existentes | Reordenar + dependencias | Insertar + reordenar |
| **Usa `rank`** | ✅ Sí | ✅ Sí | ✅ Sí |
| **Usa `action`** | ❌ No | ❌ No | ✅ Sí (add) |
| **Usa `position`** | ❌ No | ❌ No | ✅ Sí (between) |
| **Actualiza campos** | ❌ No | ✅ Sí | ❌ No |
| **Agrega stage nuevo** | ❌ No | ❌ No | ✅ Sí |
| **Complejidad** | 🟢 Baja | 🟡 Media | 🔴 Alta |

---

## 🔑 Conceptos Clave

### 1. **Rank (Rango)**
```yaml
rank: 1  # Posición en el pipeline (1 = primero, 2 = segundo, etc.)
```

**Características:**
- Número entero positivo
- Define el orden de ejecución
- Números secuenciales (1, 2, 3...)
- Se actualiza automáticamente al insertar stages

### 2. **Action (Acción)**
```yaml
action: "add"  # Insertar nuevo stage
```

**Valores válidos:**
- `"add"` - Insertar nuevo stage
- `"remove"` - Eliminar stage
- (omitir para actualizar existente)

### 3. **Position (Posición)**
```yaml
position: "between"  # Ubicación relativa
```

**Valores válidos:**
- `"between"` - Entre dos stages
- `"before"` - Antes de un stage
- `"after"` - Después de un stage
- `"first"` - Al inicio
- `"last"` - Al final

### 4. **Reference Stage**
```yaml
after_stage: "Build"      # Stage anterior
before_stage: "Deploy"    # Stage posterior
```

**Uso:**
- Requerido cuando `position: "between"`
- Especifica dónde insertar el nuevo stage

---

## 💡 Mejores Prácticas

### ✅ DO

```yaml
# 1. Usar rank secuencial
- name: "Stage1"
  rank: 1
- name: "Stage2"
  rank: 2
- name: "Stage3"
  rank: 3

# 2. Actualizar dependencias al reordenar
- name: "Producción"
  rank: 3
  fields:
    - path: "preDeployApprovals.approvals[0].approver.displayName"
      old_value: "Old Stage"
      new_value: "New Stage"

# 3. Documentar cambios con comentarios
metadata:
  comment: |
    Nuevo orden:
    1. Build
    2. Security Check
    3. Deploy
    4. Producción
```

### ❌ DON'T

```yaml
# 1. No usar rank no secuencial
- name: "Stage1"
  rank: 1
- name: "Stage2"
  rank: 5  # ❌ Debería ser 2
- name: "Stage3"
  rank: 10  # ❌ Debería ser 3

# 2. No reordenar sin actualizar dependencias
- name: "Producción"
  rank: 2  # Movido a posición 2
  # ❌ Pero las dependencias siguen apuntando al stage anterior

# 3. No omitir definición al insertar
- name: "New Stage"
  action: "add"
  position: "between"
  # ❌ Falta: definition, after_stage, before_stage
```

---

## 🚀 Casos de Uso Reales

### Caso 1: Agregar Validación de Seguridad
```yaml
Antes:  Build → Deploy → Producción
Después: Build → Security Check → Deploy → Producción

Rank:
- Build: 1
- Security Check: 2 (NUEVO)
- Deploy: 3
- Producción: 4
```

### Caso 2: Cambiar Orden de Ambientes
```yaml
Antes:  QA → Staging → Producción
Después: Staging → QA → Producción

Rank:
- Staging: 1
- QA: 2
- Producción: 3
```

### Caso 3: Agregar Aprobación Manual
```yaml
Antes:  Build → Deploy → Producción
Después: Build → Deploy → Approval → Producción

Rank:
- Build: 1
- Deploy: 2
- Approval Gate: 3 (NUEVO)
- Producción: 4
```

---

## 📚 Referencias

| Documento | Ubicación | Líneas | Contenido |
|-----------|-----------|--------|----------|
| **06_EJEMPLOS_AVANZADOS.md** | Líneas 449-567 | Agregar stages completos | Ejemplos de adición de stages |
| **07_COMENTARIOS_Y_REORGANIZACION.md** | Líneas 260-436 | Reorganización masiva | 3 ejemplos de reordenamiento |

---

## ✅ Validación Final

**Documentación Disponible:**
- ✅ Ejemplo básico (Cambiar orden)
- ✅ Ejemplo intermedio (Reordenar + dependencias)
- ✅ Ejemplo avanzado (Insertar + reordenar)
- ✅ Mejores prácticas
- ✅ Casos de uso reales
- ✅ Conceptos clave

**Funcionalidad Soportada:**
- ✅ Reordenar stages existentes con `rank`
- ✅ Insertar nuevos stages con `action: "add"`
- ✅ Especificar posición con `position`
- ✅ Actualizar dependencias automáticamente
- ✅ Documentar cambios con comentarios

---

## 🎯 Conclusión

**Sí, tenemos ejemplos completos para reordenar stages con rank.**

Los documentos contienen:
1. **3 ejemplos prácticos** con YAML completo
2. **Explicaciones detalladas** de cada parámetro
3. **Casos de uso reales** aplicables a tu situación
4. **Mejores prácticas** para evitar errores

Puedes usar estos ejemplos como plantilla para reordenar tus stages especificando el `rank` deseado.

---

**Status:** ✅ VALIDACIÓN COMPLETADA  
**Documentos Revisados:** 2  
**Ejemplos Encontrados:** 3  
**Versión:** 1.0
