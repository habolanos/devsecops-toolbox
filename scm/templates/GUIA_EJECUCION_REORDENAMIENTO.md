# 🚀 Guía de Ejecución: Reordenamiento de Stages con Rank

**Fecha:** 23 de Julio de 2026  
**Versión:** 1.0  
**Status:** ✅ Listos para usar

---

## 📋 Resumen

Esta guía te muestra cómo usar los 3 nuevos templates para reordenar stages en pipelines CD de Azure DevOps.

---

## 🎯 Templates Disponibles

| Template | Propósito | Complejidad |
|----------|-----------|------------|
| **pipe_cd_reorder_stages_basic.yaml** | Reordenar stages existentes | 🟢 Baja |
| **pipe_cd_reorder_stages_with_dependencies.yaml** | Reordenar + actualizar dependencias | 🟡 Media |
| **pipe_cd_insert_security_stage.yaml** | Insertar nuevo stage + reordenar | 🔴 Alta |

---

## 🚀 Paso a Paso: Cómo Ejecutar

### **Paso 1: Abrir el Menú Principal**

```bash
cd c:\Users\harold.bolanos\repos-publics\devsecops-toolbox
python scm/main.py
```

**Salida esperada:**
```
╔════════════════════════════════════════════════════════════════╗
║          🚀 DEVSECOPS TOOLBOX - MAIN LAUNCHER 1.0.0           ║
╚════════════════════════════════════════════════════════════════╝

[1] 📊 Monitoreo       │ Monitoreo de Recursos GCP
[2] ☁️  Google Cloud   │ Herramientas de GCP
[3] 🔷 Azure DevOps    │ Herramientas de Azure DevOps
[4] 🟦 Azure Cloud     │ Herramientas de Azure Cloud
[5] 🟠 AWS             │ Herramientas de AWS
[6] 🔧 Terminal Tools  │ Scripts de Terminal
[7] 📈 KPI Analyzer    │ Analizador de KPIs
[Q] 👋 Salir           │ Salir del programa

Seleccione una opción: 
```

---

### **Paso 2: Seleccionar Azure DevOps**

```
Seleccione una opción: 3
```

**Salida esperada:**
```
🚀 Lanzando 🔷 Azure DevOps...

╔════════════════════════════════════════════════════════════════╗
║              AZURE DEVOPS TOOLS - LAUNCHER 1.9.4              ║
╚════════════════════════════════════════════════════════════════╝

[1] ... (otras opciones)
[21] 🔄 Pipeline Updater - Actualizar pipelines con templates
[22] ... (otras opciones)

Seleccione una opción: 
```

---

### **Paso 3: Seleccionar Pipeline Updater (Tool 21)**

```
Seleccione una opción: 21
```

**Salida esperada:**
```
🚀 Lanzando 🔄 Pipeline Updater...

╔════════════════════════════════════════════════════════════════╗
║                    PIPELINE UPDATER v1.0.0                    ║
╚════════════════════════════════════════════════════════════════╝

Ingrese los parámetros:
```

---

### **Paso 4: Ingresar Organización**

```
Organización Azure DevOps: myorganization
```

---

### **Paso 5: Ingresar Proyecto**

```
Proyecto: myproject
```

---

### **Paso 6: Ingresar Definition IDs**

Ingresa los IDs de los pipelines que deseas actualizar:

```
Definition IDs (separados por coma): 3388,3389,3390
```

**Nota:** Puedes obtener los IDs de:
- URL del pipeline: `https://dev.azure.com/org/project/_release?definitionId=3388`
- Herramienta: `scm/azdo/azdo_release_cd_health.py`

---

### **Paso 7: Ingresar Ruta del Template**

Ingresa la ruta del template que deseas usar:

```
Ruta del template: scm/templates/pipe_cd_reorder_stages_basic.yaml
```

**Opciones disponibles:**
- `scm/templates/pipe_cd_reorder_stages_basic.yaml`
- `scm/templates/pipe_cd_reorder_stages_with_dependencies.yaml`
- `scm/templates/pipe_cd_insert_security_stage.yaml`

---

### **Paso 8: Confirmar Ejecución**

El programa mostrará un resumen de los cambios:

```
╔════════════════════════════════════════════════════════════════╗
║                    RESUMEN DE CAMBIOS                         ║
╚════════════════════════════════════════════════════════════════╝

Template: Reordenar stages - Orden básico
Pipelines: 3388, 3389, 3390
Cambios:
  - Build: rank 1
  - Deploy: rank 2
  - Test: rank 3
  - Validate: rank 4

¿Deseas continuar? (S/N): 
```

Ingresa `S` para confirmar:

```
¿Deseas continuar? (S/N): S
```

---

### **Paso 9: Esperar Ejecución**

El programa procesará los cambios:

```
Procesando pipeline 3388...
  ✓ Stage Build: rank 1
  ✓ Stage Deploy: rank 2
  ✓ Stage Test: rank 3
  ✓ Stage Validate: rank 4
  ✓ Cambios aplicados

Procesando pipeline 3389...
  ✓ Stage Build: rank 1
  ✓ Stage Deploy: rank 2
  ✓ Stage Test: rank 3
  ✓ Stage Validate: rank 4
  ✓ Cambios aplicados

Procesando pipeline 3390...
  ✓ Stage Build: rank 1
  ✓ Stage Deploy: rank 2
  ✓ Stage Test: rank 3
  ✓ Stage Validate: rank 4
  ✓ Cambios aplicados

✓ Ejecución completada
```

---

### **Paso 10: Revisar Resultados**

El programa generará un reporte:

```
Reporte guardado en: outcome/pipeline_update_20260723_143022.json
```

**Contenido del reporte:**
```json
{
  "timestamp": "2026-07-23T14:30:22Z",
  "template": "Reordenar stages - Orden básico",
  "summary": {
    "total": 3,
    "success": 3,
    "failed": 0
  },
  "details": [
    {
      "definition_id": 3388,
      "success": true,
      "changes": [
        {
          "type": "stage_reorder",
          "stage": "Build",
          "rank": 1
        },
        {
          "type": "stage_reorder",
          "stage": "Deploy",
          "rank": 2
        }
      ]
    }
  ]
}
```

---

## 📍 Ubicación del Template en la Ejecución

### **Estructura de Directorios**

```
devsecops-toolbox/
├── scm/
│   ├── main.py                          ← Punto de entrada
│   ├── azdo/
│   │   ├── tools.py                     ← Menú de Azure DevOps
│   │   └── ... (otras herramientas)
│   └── templates/                       ← 📍 AQUÍ VAN LOS TEMPLATES
│       ├── README.md
│       ├── pipe_cd_update_docker.yaml
│       ├── pipe_cd_update_kubernetes.yaml
│       ├── pipe_cd_reorder_stages_basic.yaml          ← Template 1
│       ├── pipe_cd_reorder_stages_with_dependencies.yaml  ← Template 2
│       └── pipe_cd_insert_security_stage.yaml         ← Template 3
└── docs/
    └── features/
        └── feature_actualizacion_pipeline_cd_with_template/
            └── 08_VALIDACION_REORDENAMIENTO_RANK.md
```

### **Flujo de Ejecución**

```
main.py
  ↓
Seleccionar Azure DevOps (opción 3)
  ↓
azdo/tools.py
  ↓
Seleccionar Pipeline Updater (opción 21)
  ↓
azdo/pipeline_updater.py (o similar)
  ↓
Lee template desde: scm/templates/pipe_cd_reorder_stages_basic.yaml
  ↓
Procesa cambios en Azure DevOps
  ↓
Genera reporte en: outcome/pipeline_update_*.json
```

---

## 🎯 Ejemplos de Uso

### **Ejemplo 1: Reordenar Stages Básico**

**Comando:**
```bash
python scm/main.py
# → Seleccionar 3 (Azure DevOps)
# → Seleccionar 21 (Pipeline Updater)
# → Ingresar: myorganization
# → Ingresar: myproject
# → Ingresar: 3388,3389
# → Ingresar: scm/templates/pipe_cd_reorder_stages_basic.yaml
# → Confirmar: S
```

**Resultado:**
```
Antes:  Build → Test → Deploy → Validate
Después: Build → Deploy → Test → Validate
```

---

### **Ejemplo 2: Reordenar con Cambio de Dependencias**

**Comando:**
```bash
python scm/main.py
# → Seleccionar 3 (Azure DevOps)
# → Seleccionar 21 (Pipeline Updater)
# → Ingresar: myorganization
# → Ingresar: myproject
# → Ingresar: 3390,3391,3392
# → Ingresar: scm/templates/pipe_cd_reorder_stages_with_dependencies.yaml
# → Confirmar: S
```

**Resultado:**
```
Antes:  QA → Staging → Producción
Después: Staging → QA → Producción
(Producción ahora depende de QA)
```

---

### **Ejemplo 3: Insertar Nuevo Stage de Seguridad**

**Comando:**
```bash
python scm/main.py
# → Seleccionar 3 (Azure DevOps)
# → Seleccionar 21 (Pipeline Updater)
# → Ingresar: myorganization
# → Ingresar: myproject
# → Ingresar: 3393,3394
# → Ingresar: scm/templates/pipe_cd_insert_security_stage.yaml
# → Confirmar: S
```

**Resultado:**
```
Antes:  Build → Deploy → Producción
Después: Build → Security Check → Deploy → Producción
```

---

## ✅ Checklist Antes de Ejecutar

- [ ] Identifiqué los definition IDs de los pipelines
- [ ] Seleccioné el template correcto
- [ ] Revisé el comentario en el template
- [ ] Tengo acceso a Azure DevOps
- [ ] Estoy en la rama correcta
- [ ] Hice backup de los pipelines (opcional)

---

## 🔒 Seguridad y Validación

**El Pipeline Updater automáticamente:**

✅ Valida la estructura del template  
✅ Verifica que los stages existan  
✅ Confirma antes de aplicar cambios  
✅ Crea snapshots antes de modificar  
✅ Genera auditoría completa  
✅ Permite rollback si algo falla  

---

## 📊 Monitoreo de Ejecución

### **Archivo de Reporte**

```
outcome/pipeline_update_20260723_143022.json
```

**Contenido:**
```json
{
  "timestamp": "2026-07-23T14:30:22Z",
  "template": "Reordenar stages - Orden básico",
  "organization": "myorganization",
  "project": "myproject",
  "definition_ids": [3388, 3389, 3390],
  "summary": {
    "total": 3,
    "success": 3,
    "failed": 0
  },
  "details": [
    {
      "definition_id": 3388,
      "success": true,
      "changes": [...]
    }
  ]
}
```

---

## 🆘 Solución de Problemas

### **Problema: "Template no encontrado"**

**Solución:**
```bash
# Verifica que el archivo existe
ls scm/templates/pipe_cd_reorder_stages_basic.yaml

# Usa la ruta correcta
scm/templates/pipe_cd_reorder_stages_basic.yaml
```

---

### **Problema: "Stage no encontrado"**

**Solución:**
```bash
# Verifica los nombres exactos de los stages
python scm/azdo/azdo_release_cd_health.py

# Busca el pipeline y revisa los nombres de stages
# Actualiza el template con los nombres correctos
```

---

### **Problema: "Error de autenticación"**

**Solución:**
```bash
# Verifica que tengas credenciales de Azure DevOps
# Configura PAT (Personal Access Token) si es necesario
# Verifica permisos en el proyecto
```

---

## 📚 Referencias

- `docs/features/feature_actualizacion_pipeline_cd_with_template/08_VALIDACION_REORDENAMIENTO_RANK.md`
- `docs/features/feature_actualizacion_pipeline_cd_with_template/06_EJEMPLOS_AVANZADOS.md`
- `docs/features/feature_actualizacion_pipeline_cd_with_template/07_COMENTARIOS_Y_REORGANIZACION.md`

---

**Status:** ✅ Guía Completa  
**Versión:** 1.0  
**Última actualización:** 2026-07-23
