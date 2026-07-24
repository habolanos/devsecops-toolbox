# 📋 Resumen: Templates para Reordenamiento de Stages

**Fecha:** 23 de Julio de 2026  
**Versión:** 1.0  
**Status:** ✅ Completado

---

## 🎯 Qué se Creó

Se crearon **3 templates YAML completos** para reordenar stages en pipelines CD de Azure DevOps, basados en la documentación de validación.

---

## 📁 Archivos Creados

### **1. Templates YAML**

| Archivo | Propósito | Complejidad |
|---------|-----------|------------|
| `pipe_cd_reorder_stages_basic.yaml` | Reordenar stages existentes | 🟢 Baja |
| `pipe_cd_reorder_stages_with_dependencies.yaml` | Reordenar + actualizar dependencias | 🟡 Media |
| `pipe_cd_insert_security_stage.yaml` | Insertar nuevo stage + reordenar | 🔴 Alta |

### **2. Documentación**

| Archivo | Contenido |
|---------|----------|
| `GUIA_EJECUCION_REORDENAMIENTO.md` | Paso a paso completo de cómo ejecutar |
| `README.md` (actualizado) | Descripción de todos los templates |

---

## 🎯 Template 1: Reordenar Stages Básico

**Archivo:** `pipe_cd_reorder_stages_basic.yaml`

**Propósito:** Cambiar el orden de ejecución de stages

**Ejemplo:**
```
Antes:  Build → Test → Deploy → Validate
Después: Build → Deploy → Test → Validate
```

**Estructura:**
```yaml
metadata:
  name: "Reordenar stages - Orden básico"
  comment: "Documentación completa..."

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

**Características:**
- ✅ Usa `rank` para especificar orden
- ✅ Números secuenciales (1, 2, 3, 4)
- ✅ Aplica a múltiples stages
- ✅ Comentario descriptivo incluido

---

## 🎯 Template 2: Reordenar con Cambios de Dependencias

**Archivo:** `pipe_cd_reorder_stages_with_dependencies.yaml`

**Propósito:** Reordenar stages Y actualizar sus dependencias

**Ejemplo:**
```
Antes:  QA → Staging → Producción
Después: Staging → QA → Producción
(Producción ahora depende de QA)
```

**Estructura:**
```yaml
metadata:
  name: "Reordenar stages con cambio de dependencias"
  comment: "Documentación completa..."

search:
  stages:
    - name: "QA"
    - name: "Staging"
    - name: "Producción"

update:
  stages:
    - name: "Staging"
      rank: 1
    
    - name: "QA"
      rank: 2
    
    - name: "Producción"
      rank: 3
      fields:
        - path: "preDeployApprovals.approvals[0].approver.displayName"
          old_value: "Staging"
          new_value: "QA"
        - path: "preDeployApprovals.approvals[0].timeoutInMinutes"
          old_value: "60"
          new_value: "120"
```

**Características:**
- ✅ Combina `rank` con cambios de dependencias
- ✅ Actualiza aprobadores automáticamente
- ✅ Mantiene coherencia entre orden y dependencias
- ✅ Permite cambios de campos en el mismo stage

---

## 🎯 Template 3: Insertar Nuevo Stage

**Archivo:** `pipe_cd_insert_security_stage.yaml`

**Propósito:** Insertar nuevo stage en posición específica

**Ejemplo:**
```
Antes:  Build → Deploy → Producción
Después: Build → Security Check → Deploy → Producción
```

**Estructura:**
```yaml
metadata:
  name: "Insertar stage de seguridad en el pipeline"
  comment: "Documentación completa..."

search:
  stages:
    - name: "Build"
    - name: "Deploy"
    - name: "Producción"

update:
  stages:
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
    
    - name: "Deploy"
      rank: 3
    
    - name: "Producción"
      rank: 4
```

**Características:**
- ✅ Usa `action: "add"` para insertar
- ✅ Usa `position: "between"` para especificar ubicación
- ✅ Especifica `after_stage` y `before_stage`
- ✅ Incluye definición completa del nuevo stage
- ✅ Reordena automáticamente los stages posteriores

---

## 🚀 Cómo Usar los Templates

### **Paso 1: Abrir Menú Principal**

```bash
cd c:\Users\harold.bolanos\repos-publics\devsecops-toolbox
python scm/main.py
```

### **Paso 2: Seleccionar Azure DevOps**

```
Seleccione una opción: 3
```

### **Paso 3: Seleccionar Pipeline Updater**

```
Seleccione una opción: 21
```

### **Paso 4: Ingresar Parámetros**

```
Organización: myorganization
Proyecto: myproject
Definition IDs: 3388,3389,3390
Ruta del template: scm/templates/pipe_cd_reorder_stages_basic.yaml
```

### **Paso 5: Confirmar**

```
¿Deseas continuar? (S/N): S
```

### **Paso 6: Revisar Resultados**

```
Reporte guardado en: outcome/pipeline_update_20260723_143022.json
```

---

## 📍 Ubicación de los Templates

```
devsecops-toolbox/
├── scm/
│   ├── main.py                          ← Punto de entrada
│   ├── azdo/
│   │   ├── tools.py                     ← Menú de Azure DevOps
│   │   └── pipeline_updater.py          ← Lee templates desde aquí
│   └── templates/                       ← 📍 TEMPLATES AQUÍ
│       ├── README.md
│       ├── pipe_cd_update_docker.yaml
│       ├── pipe_cd_update_kubernetes.yaml
│       ├── pipe_cd_reorder_stages_basic.yaml          ← Template 1
│       ├── pipe_cd_reorder_stages_with_dependencies.yaml  ← Template 2
│       ├── pipe_cd_insert_security_stage.yaml         ← Template 3
│       ├── GUIA_EJECUCION_REORDENAMIENTO.md           ← Guía paso a paso
│       └── RESUMEN_TEMPLATES_REORDENAMIENTO.md        ← Este archivo
└── docs/
    └── features/
        └── feature_actualizacion_pipeline_cd_with_template/
            └── 08_VALIDACION_REORDENAMIENTO_RANK.md   ← Documentación original
```

---

## 🔄 Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────┐
│ 1. main.py - Menú Principal                                 │
│    Seleccionar: Azure DevOps (opción 3)                     │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. azdo/tools.py - Menú de Azure DevOps                     │
│    Seleccionar: Pipeline Updater (opción 21)                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Pipeline Updater - Solicita Parámetros                   │
│    - Organización                                            │
│    - Proyecto                                                │
│    - Definition IDs                                          │
│    - Ruta del template ← 📍 AQUÍ INGRESAS EL TEMPLATE       │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Lee Template desde: scm/templates/pipe_cd_*.yaml          │
│    - Valida estructura                                       │
│    - Verifica stages                                         │
│    - Confirma cambios                                        │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Aplica Cambios en Azure DevOps                           │
│    - Reordena stages                                         │
│    - Actualiza dependencias                                  │
│    - Inserta nuevos stages                                   │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Genera Reporte en: outcome/pipeline_update_*.json         │
│    - Resumen de cambios                                      │
│    - Detalles por pipeline                                   │
│    - Auditoría completa                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Comparativa de Templates

| Aspecto | Template 1 | Template 2 | Template 3 |
|---------|-----------|-----------|-----------|
| **Propósito** | Reordenar | Reordenar + Deps | Insertar |
| **Usa `rank`** | ✅ Sí | ✅ Sí | ✅ Sí |
| **Usa `action`** | ❌ No | ❌ No | ✅ Sí |
| **Usa `position`** | ❌ No | ❌ No | ✅ Sí |
| **Actualiza campos** | ❌ No | ✅ Sí | ❌ No |
| **Agrega stage** | ❌ No | ❌ No | ✅ Sí |
| **Complejidad** | 🟢 Baja | 🟡 Media | 🔴 Alta |
| **Tiempo setup** | 5 min | 10 min | 15 min |

---

## 💡 Casos de Uso Reales

### **Caso 1: Validar Antes de Desplegar**

**Problema:** Queremos que Deploy se ejecute antes que Test

**Solución:** Usar `pipe_cd_reorder_stages_basic.yaml`

```
Antes:  Build → Test → Deploy → Validate
Después: Build → Deploy → Test → Validate
```

---

### **Caso 2: Cambiar Orden de Ambientes**

**Problema:** Queremos que QA valide después de Staging

**Solución:** Usar `pipe_cd_reorder_stages_with_dependencies.yaml`

```
Antes:  QA → Staging → Producción
Después: Staging → QA → Producción
(Producción depende de QA)
```

---

### **Caso 3: Agregar Validación de Seguridad**

**Problema:** Queremos escanear seguridad antes de Deploy

**Solución:** Usar `pipe_cd_insert_security_stage.yaml`

```
Antes:  Build → Deploy → Producción
Después: Build → Security Check → Deploy → Producción
```

---

## ✅ Checklist de Uso

- [ ] Identifiqué los definition IDs de los pipelines
- [ ] Seleccioné el template correcto para mi caso
- [ ] Revisé el comentario en el template
- [ ] Personalicé los valores si es necesario
- [ ] Tengo acceso a Azure DevOps
- [ ] Leí la guía de ejecución
- [ ] Estoy listo para ejecutar

---

## 📚 Documentación Relacionada

| Documento | Ubicación | Contenido |
|-----------|-----------|----------|
| **Validación** | `docs/features/.../08_VALIDACION_REORDENAMIENTO_RANK.md` | Ejemplos y conceptos |
| **Guía Ejecución** | `scm/templates/GUIA_EJECUCION_REORDENAMIENTO.md` | Paso a paso completo |
| **README Templates** | `scm/templates/README.md` | Descripción de templates |
| **Ejemplos Avanzados** | `docs/features/.../06_EJEMPLOS_AVANZADOS.md` | Casos complejos |

---

## 🔒 Seguridad

**El Pipeline Updater automáticamente:**

✅ Valida la estructura del template  
✅ Verifica que los stages existan  
✅ Confirma antes de aplicar cambios  
✅ Crea snapshots antes de modificar  
✅ Genera auditoría completa  
✅ Permite rollback si algo falla  

---

## 📝 Commits Realizados

```
672dd81 - docs: Agregar validación de ejemplos de reordenamiento de stages con rank
[nuevo] - feat: Agregar 3 templates para reordenamiento de stages con rank + guía
```

---

## 🎯 Próximos Pasos

1. ✅ Identificar definition IDs de tus pipelines
2. ✅ Seleccionar el template que necesitas
3. ✅ Ejecutar desde `python scm/main.py`
4. ✅ Revisar el reporte de cambios
5. ✅ Validar en Azure DevOps

---

## 📞 Soporte

**Documentación:**
- `GUIA_EJECUCION_REORDENAMIENTO.md` - Paso a paso
- `08_VALIDACION_REORDENAMIENTO_RANK.md` - Conceptos
- `README.md` - Descripción de templates

**Problemas:**
- Template no encontrado → Verifica la ruta
- Stage no encontrado → Verifica nombres exactos
- Error de autenticación → Verifica credenciales de Azure DevOps

---

**Status:** ✅ Completado  
**Versión:** 1.0  
**Fecha:** 23 de Julio de 2026  
**Listo para usar:** Sí ✅
