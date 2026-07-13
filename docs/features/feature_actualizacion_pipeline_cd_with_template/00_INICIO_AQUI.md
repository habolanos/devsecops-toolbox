# 🚀 Actualización Masiva de Pipelines CD con Template

## 📌 Resumen Ejecutivo

Este documento describe una solución profesional para **actualizar masivamente pipelines CD (Release Definitions) en Azure DevOps** usando un sistema de templates que especifica:

- **QUÉ BUSCAR**: Criterios de búsqueda (stages, tasks, variables, artefactos)
- **QUÉ ACTUALIZAR**: Cambios a aplicar (reemplazos, adiciones, eliminaciones)
- **CÓMO HACERLO**: Procesamiento paralelo y seguro

**Entrada**: Lista de `definitionId` separados por comas  
**Salida**: Reporte de cambios, rollback automático si falla

---

## 🎯 Objetivo

Permitir a DevOps Engineers actualizar **múltiples pipelines CD simultáneamente** sin:
- ❌ Editar manualmente cada pipeline
- ❌ Riesgo de inconsistencias
- ❌ Pérdida de configuración
- ❌ Downtime

---

## 📚 Documentos en esta Carpeta

| Documento | Descripción |
|-----------|-------------|
| **00_INICIO_AQUI.md** | Este archivo - Punto de entrada |
| **01_ANALISIS_ARQUITECTURA.md** | Análisis técnico detallado (PRO level) |
| **02_ESPECIFICACION_TEMPLATE.md** | Especificación del formato de template |
| **03_PLAN_IMPLEMENTACION.md** | Plan paso a paso de implementación |
| **04_EJEMPLOS_PRACTICOS.md** | Casos de uso reales |
| **05_GUIA_USO.md** | Cómo usar la herramienta |

---

## 🔑 Conceptos Clave

### 1. **Template de Actualización**
Archivo YAML/JSON que define:
```yaml
metadata:
  name: "Actualizar imagen Docker"
  version: "1.0"
  
search:
  stages: ["QA", "Producción"]
  tasks:
    - name: "Docker Push"
      type: "DockerPush"
  
update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old-project/app"
          new_value: "gcr.io/new-project/app"
```

### 2. **Procesamiento Masivo**
- Recibe: `definitionId1,definitionId2,definitionId3`
- Procesa: En paralelo (5 workers)
- Valida: Antes de aplicar cambios
- Revierte: Si algo falla

### 3. **Seguridad**
- ✅ Validación de cambios antes de aplicar
- ✅ Rollback automático
- ✅ Auditoría completa
- ✅ Confirmación del usuario

---

## 🚀 Inicio Rápido

```bash
# 1. Crear template
cat > template_update.yaml << 'EOF'
metadata:
  name: "Actualizar imagen"
search:
  stages: ["Producción"]
  tasks:
    - name: "Docker Push"
update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old/app"
          new_value: "gcr.io/new/app"
EOF

# 2. Ejecutar actualización
python scm/azdo/pipeline_updater_template.py \
  --definition-ids "3388,3389,3390" \
  --template template_update.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros"

# 3. Revisar cambios
cat outcome/pipeline_updates/report.json
```

---

## 📊 Flujo General

```
┌─────────────────────────────────────────────────────────────┐
│ Usuario proporciona:                                         │
│ - definition-ids: "3388,3389,3390"                          │
│ - template: template_update.yaml                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. VALIDACIÓN                                                │
│ - Verificar IDs válidos                                     │
│ - Validar template                                          │
│ - Verificar permisos                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. ANÁLISIS (DRY RUN)                                        │
│ - Descargar pipelines                                       │
│ - Buscar coincidencias                                      │
│ - Simular cambios                                           │
│ - Mostrar preview                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CONFIRMACIÓN                                              │
│ - Mostrar resumen de cambios                                │
│ - Pedir confirmación del usuario                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. APLICACIÓN (PARALELO)                                     │
│ - 5 workers procesando simultáneamente                      │
│ - Guardar cambios en AZDO                                   │
│ - Crear snapshots para rollback                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. REPORTE                                                   │
│ - JSON con cambios realizados                               │
│ - CSV con resumen                                           │
│ - HTML con visualización                                    │
│ - Logs de auditoría                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 💡 Casos de Uso

### Caso 1: Actualizar Imagen Docker
Cambiar versión de imagen en múltiples pipelines

### Caso 2: Actualizar Variables
Cambiar valores de variables de entorno

### Caso 3: Actualizar Artefactos
Cambiar alias o ruta de artefactos

### Caso 4: Actualizar Approvals
Cambiar aprobadores en stages

### Caso 5: Actualizar Tasks
Reemplazar tareas completas

---

## ⚡ Características Principales

| Característica | Descripción |
|---|---|
| 🎯 **Masivo** | Actualizar 100+ pipelines en minutos |
| 📋 **Template** | Reutilizable, versionable, auditable |
| ⚡ **Paralelo** | 5 workers simultáneos |
| 🔄 **Rollback** | Revertir cambios automáticamente |
| 📊 **Reportería** | JSON, CSV, HTML, Excel |
| 🔐 **Seguro** | Validación, confirmación, auditoría |
| 🔍 **Flexible** | Buscar por stage, task, variable, etc. |

---

## 📖 Próximos Pasos

1. **Leer**: `01_ANALISIS_ARQUITECTURA.md` - Entender la arquitectura
2. **Entender**: `02_ESPECIFICACION_TEMPLATE.md` - Formato del template
3. **Planificar**: `03_PLAN_IMPLEMENTACION.md` - Cómo implementar
4. **Aprender**: `04_EJEMPLOS_PRACTICOS.md` - Casos reales
5. **Usar**: `05_GUIA_USO.md` - Cómo ejecutar

---

## 🤝 Soporte

Para preguntas o sugerencias, contacta al equipo DevOps.

**Versión**: 1.0  
**Última actualización**: 2026-07-13  
**Estado**: 📋 Análisis Completo
