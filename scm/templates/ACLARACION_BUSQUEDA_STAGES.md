# 🔍 Aclaración: Comportamiento de Búsqueda en Templates

**Fecha:** 24 de Julio de 2026  
**Versión:** 1.0  
**Status:** ✅ Aclaración Completa

---

## ❓ Pregunta

Cuando la búsqueda coincide con todos los criterios pero el pipeline tiene más stages, ¿qué pasa?

**Ejemplo:**
```yaml
search:
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"
```

**Pregunta:** Si el pipeline tiene 5 stages (Build, Test, Deploy, Validate + **Security**), ¿se actualiza solo los 4 buscados o también el 5to?

---

## ✅ Respuesta: SOLO se actualizan los que coinciden

**El comportamiento es:**

1. **Búsqueda:** Busca stages que coincidan CON LOS CRITERIOS
2. **Coincidencia:** Si encuentra los 4 stages especificados
3. **Actualización:** SOLO actualiza esos 4 stages
4. **Stages adicionales:** Se ignoran completamente

---

## 📊 Ejemplo Visual

### **Escenario: Pipeline con 5 Stages**

**Pipeline Original:**
```
1. Build
2. Test
3. Deploy
4. Validate
5. Security ← Stage adicional (NO en search)
```

**Template:**
```yaml
search:
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
1. Build       ← Actualizado (rank: 1)
2. Deploy      ← Actualizado (rank: 2)
3. Test        ← Actualizado (rank: 3)
4. Validate    ← Actualizado (rank: 4)
5. Security    ← ❌ NO ACTUALIZADO (no está en search)
```

---

## 🔑 Conceptos Clave

### **1. Search (Búsqueda)**

Define QUÉ stages buscar:

```yaml
search:
  stages:
    - name: "Build"      ← Busca este
    - name: "Test"       ← Busca este
    - name: "Deploy"     ← Busca este
    - name: "Validate"   ← Busca este
```

**Comportamiento:**
- ✅ Busca stages que coincidan con estos nombres
- ✅ Si encuentra todos → Continúa
- ❌ Si falta alguno → Error (no aplica cambios)
- ❌ Stages adicionales → Se ignoran

---

### **2. Update (Actualización)**

Define QUÉ cambios hacer:

```yaml
update:
  stages:
    - name: "Build"
      rank: 1      ← Cambio a aplicar
    - name: "Deploy"
      rank: 2      ← Cambio a aplicar
    - name: "Test"
      rank: 3      ← Cambio a aplicar
    - name: "Validate"
      rank: 4      ← Cambio a aplicar
```

**Comportamiento:**
- ✅ Solo aplica cambios a stages en update
- ✅ Ignora stages no mencionados
- ✅ No afecta stages adicionales

---

## 📋 Casos de Uso

### **Caso 1: Pipeline con Exactamente los 4 Stages**

**Pipeline:**
```
1. Build
2. Test
3. Deploy
4. Validate
```

**Template:**
```yaml
search:
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

**Resultado:** ✅ Éxito
```
1. Build
2. Deploy
3. Test
4. Validate
```

---

### **Caso 2: Pipeline con 5 Stages (1 adicional)**

**Pipeline:**
```
1. Build
2. Test
3. Deploy
4. Validate
5. Security ← Adicional
```

**Template:**
```yaml
search:
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

**Resultado:** ✅ Éxito (Security se ignora)
```
1. Build
2. Deploy
3. Test
4. Validate
5. Security ← Sin cambios
```

---

### **Caso 3: Pipeline con 3 Stages (falta uno)**

**Pipeline:**
```
1. Build
2. Test
3. Deploy
(Falta: Validate)
```

**Template:**
```yaml
search:
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"  ← No existe

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

**Resultado:** ❌ Error
```
Error: Stage "Validate" no encontrado en el pipeline
No se aplican cambios
```

---

### **Caso 4: Pipeline con 6 Stages (2 adicionales)**

**Pipeline:**
```
1. Build
2. Test
3. Deploy
4. Validate
5. Security ← Adicional 1
6. Approval ← Adicional 2
```

**Template:**
```yaml
search:
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

**Resultado:** ✅ Éxito (Security y Approval se ignoran)
```
1. Build
2. Deploy
3. Test
4. Validate
5. Security ← Sin cambios
6. Approval ← Sin cambios
```

---

## 🎯 Regla General

```
┌─────────────────────────────────────────────────────────┐
│ REGLA: Búsqueda Exacta, Actualización Selectiva         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ 1. SEARCH busca EXACTAMENTE los stages especificados    │
│    - Todos deben existir                                │
│    - Stages adicionales se ignoran en la búsqueda       │
│                                                          │
│ 2. UPDATE solo modifica los stages en la sección        │
│    - Stages no mencionados NO se tocan                  │
│    - Stages adicionales permanecen sin cambios          │
│                                                          │
│ 3. Resultado:                                           │
│    - Si SEARCH encuentra todos → Se aplican cambios     │
│    - Si SEARCH no encuentra alguno → Error              │
│    - Stages adicionales → Siempre ignorados             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🔍 Cómo Funciona Internamente

### **Paso 1: Validar Búsqueda**

```python
# Buscar stages en el pipeline
stages_encontrados = []
for stage_buscado in search.stages:
    if stage_buscado.name en pipeline.stages:
        stages_encontrados.append(stage_buscado)
    else:
        ERROR: "Stage no encontrado"
        return

# Verificar que se encontraron TODOS
if len(stages_encontrados) != len(search.stages):
    ERROR: "No se encontraron todos los stages"
    return
```

### **Paso 2: Aplicar Cambios**

```python
# Solo actualizar stages en update
for stage_actualizar in update.stages:
    if stage_actualizar.name en pipeline.stages:
        aplicar_cambios(stage_actualizar)
    # Si no existe, se ignora (no error)

# Stages no mencionados → No se tocan
```

---

## 📝 Ejemplos Prácticos

### **Ejemplo 1: Reordenar 4 de 5 Stages**

**Quiero:** Reordenar Build, Deploy, Test, Validate (ignorar Security)

**Template:**
```yaml
search:
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
Antes:  Build → Test → Deploy → Validate → Security
Después: Build → Deploy → Test → Validate → Security
         (Security permanece en su posición)
```

---

### **Ejemplo 2: Actualizar Solo Algunos Stages**

**Quiero:** Cambiar solo Deploy y Validate, ignorar Build y Test

**Template:**
```yaml
search:
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"

update:
  stages:
    # Solo actualizar estos dos
    - name: "Deploy"
      fields:
        - path: "preDeployApprovals.approvals[0].approver.displayName"
          old_value: "QA"
          new_value: "DevOps"
    
    - name: "Validate"
      fields:
        - path: "preDeployApprovals.approvals[0].timeoutInMinutes"
          old_value: "60"
          new_value: "120"
```

**Resultado:**
```
- Build: Sin cambios
- Test: Sin cambios
- Deploy: Aprobador actualizado
- Validate: Timeout actualizado
- Security: Sin cambios (si existe)
```

---

## ⚠️ Casos Especiales

### **Caso: ¿Qué pasa si hay duplicados?**

**Pipeline:**
```
1. Build
2. Build ← Duplicado
3. Test
4. Deploy
5. Validate
```

**Comportamiento:**
- ✅ Busca "Build" → Encuentra el primero
- ✅ Busca "Test" → Encuentra
- ✅ Busca "Deploy" → Encuentra
- ✅ Busca "Validate" → Encuentra
- ✅ Actualiza el primer "Build" encontrado

**Nota:** Generalmente Azure DevOps no permite duplicados, pero si ocurre, se actualiza el primero encontrado.

---

### **Caso: ¿Qué pasa si el orden es diferente?**

**Pipeline:**
```
1. Validate
2. Deploy
3. Test
4. Build
```

**Search:**
```yaml
search:
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"
```

**Comportamiento:**
- ✅ El ORDEN en search NO importa
- ✅ Solo importa que EXISTAN todos los stages
- ✅ Se actualizan según el update

---

## 🎓 Resumen

| Pregunta | Respuesta |
|----------|-----------|
| **¿Se actualiza el stage adicional?** | ❌ No, se ignora |
| **¿Se requieren TODOS los stages en search?** | ✅ Sí, o error |
| **¿Importa el orden en search?** | ❌ No |
| **¿Puedo actualizar solo algunos?** | ✅ Sí, en update |
| **¿Se tocan stages no mencionados?** | ❌ No |

---

## 💡 Mejores Prácticas

### ✅ DO

```yaml
# 1. Ser específico en search
search:
  stages:
    - name: "Build"
    - name: "Test"
    - name: "Deploy"
    - name: "Validate"

# 2. Actualizar solo lo necesario
update:
  stages:
    - name: "Build"
      rank: 1
    - name: "Deploy"
      rank: 2
    # Test y Validate sin cambios

# 3. Documentar qué se ignora
metadata:
  comment: |
    Actualiza Build y Deploy
    Ignora: Test, Validate, y cualquier stage adicional
```

### ❌ DON'T

```yaml
# 1. No incluir stages que no existen
search:
  stages:
    - name: "Build"
    - name: "NonExistent"  # ❌ Error

# 2. No asumir que se actualizan stages adicionales
# Si hay Security en el pipeline, NO se actualiza

# 3. No olvidar que search es validación
# Si falta un stage en search, falla todo
```

---

## 📞 Preguntas Frecuentes

### **P: Si tengo 10 stages y busco 4, ¿se actualizan los 6 restantes?**

**R:** No. Solo se actualizan los 4 que especifiques en `update`. Los 6 restantes se ignoran.

---

### **P: ¿Qué pasa si un stage en search no existe?**

**R:** Error. No se aplican cambios. Debes verificar que TODOS los stages en search existan.

---

### **P: ¿Puedo actualizar un stage que no está en search?**

**R:** No. Si está en `update` pero no en `search`, se ignora. Primero debe estar en `search`.

---

### **P: ¿El orden en search importa?**

**R:** No. Solo importa que existan. El orden en `update` es lo que define los cambios.

---

## 🎯 Conclusión

**La búsqueda es EXACTA pero SELECTIVA:**

1. **Search:** Valida que existan EXACTAMENTE esos stages
2. **Update:** Aplica cambios SOLO a los stages mencionados
3. **Stages adicionales:** Se ignoran completamente
4. **Resultado:** Control preciso sobre qué se actualiza

---

**Status:** ✅ Aclaración Completa  
**Versión:** 1.0  
**Fecha:** 24 de Julio de 2026
