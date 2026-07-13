# 📖 Guía de Uso - Pipeline Updater Template

## 1. INSTALACIÓN

### Requisitos
- Python 3.11+
- Azure DevOps PAT (Personal Access Token)
- Acceso a pipelines CD

### Instalación de Dependencias

```bash
# Navegar al directorio
cd scm/azdo/pipeline-updater

# Instalar dependencias
pip install -r requirements.txt
```

### requirements.txt

```
requests>=2.28.0
pyyaml>=6.0
pandas>=1.5.0
openpyxl>=3.9.0
rich>=13.0.0
```

---

## 2. CONFIGURACIÓN INICIAL

### 2.1 Obtener PAT de Azure DevOps

1. Ir a https://dev.azure.com/Coppel-Retail
2. Hacer clic en perfil → Personal access tokens
3. Crear nuevo token con permisos:
   - Release (read, write)
   - Code (read)
4. Copiar el token

### 2.2 Configurar Variables de Entorno

```bash
# Windows
set AZDO_PAT=tu_token_aqui
set AZDO_ORG=Coppel-Retail
set AZDO_PROJECT=Cadena_de_Suministros

# Linux/Mac
export AZDO_PAT=tu_token_aqui
export AZDO_ORG=Coppel-Retail
export AZDO_PROJECT=Cadena_de_Suministros
```

### 2.3 Crear Directorio de Templates

```bash
mkdir -p templates
mkdir -p outcome/pipeline_updates
mkdir -p outcome/snapshots
```

---

## 3. CREAR UN TEMPLATE

### 3.1 Template Básico

```bash
cat > templates/mi_template.yaml << 'EOF'
metadata:
  name: "Mi actualización"
  version: "1.0"
  description: "Descripción de qué hace"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Docker Push"
      type: "DockerPush"

update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old/app"
          new_value: "gcr.io/new/app"

options:
  dry_run: false
  rollback_on_error: true
EOF
```

### 3.2 Validar Template

```bash
python scm/azdo/pipeline-updater/template_validator.py \
  --template templates/mi_template.yaml
```

---

## 4. OBTENER IDs DE PIPELINES

### Opción 1: Desde el Launcher

```bash
python scm/main.py
# Seleccionar: 1 (AZDO)
# Seleccionar: 15 (CD Detailed Inventory)
# Filtrar por nombre o stage
# Copiar IDs
```

### Opción 2: Desde Azure DevOps

1. Ir a https://dev.azure.com/Coppel-Retail/Cadena_de_Suministros/_release
2. Ver URL: `definitionId=3388`
3. El número es el ID

### Opción 3: Script Python

```python
from scm.azdo.pipeline_updater import AzureDevOpsClient

client = AzureDevOpsClient(
    pat="tu_pat",
    org="Coppel-Retail",
    project="Cadena_de_Suministros"
)

# Obtener todos los pipelines
definitions = client.list_release_definitions()
for d in definitions:
    print(f"{d['id']} - {d['name']}")
```

---

## 5. EJECUTAR ACTUALIZACIÓN

### 5.1 Desde el Launcher

```bash
python scm/main.py
# Seleccionar: 1 (AZDO)
# Seleccionar: 41 (Pipeline Updater Template)
# Seguir instrucciones interactivas
```

### 5.2 Desde Línea de Comandos

```bash
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "3388,3389,3390" \
  --template templates/mi_template.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros"
```

### 5.3 Con Opciones Avanzadas

```bash
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "3388,3389,3390" \
  --template templates/mi_template.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --dry-run \
  --workers 3 \
  --timeout 60 \
  --verbose
```

---

## 6. FLUJO TÍPICO DE USO

### Paso 1: Preparar Template

```bash
# Crear template
cat > templates/update.yaml << 'EOF'
metadata:
  name: "Actualizar imagen"
  version: "1.0"
search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Docker Push"
      type: "DockerPush"
update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old/app"
          new_value: "gcr.io/new/app"
options:
  dry_run: false
  rollback_on_error: true
EOF

# Validar
python scm/azdo/pipeline-updater/template_validator.py --template templates/update.yaml
```

### Paso 2: Obtener IDs

```bash
# Desde AZDO o script
# Copiar: 3388,3389,3390
```

### Paso 3: Ejecutar en Dry-Run

```bash
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "3388,3389,3390" \
  --template templates/update.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --dry-run
```

### Paso 4: Revisar Preview

```
╔════════════════════════════════════════════════════════════════╗
║              Pipeline Updater - Análisis Previo                ║
╚════════════════════════════════════════════════════════════════╝

Template: update.yaml
Pipelines: 3
Cambios por pipeline: 1

PREVIEW:
┌─────────────────────────────────────────────────────────────┐
│ Pipeline 3388 - Deploy Web App                              │
│ Task: Docker Push                                           │
│   inputs.imageRepository: gcr.io/old/app → gcr.io/new/app  │
└─────────────────────────────────────────────────────────────┘
```

### Paso 5: Ejecutar Actualización

```bash
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "3388,3389,3390" \
  --template templates/update.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros"

# Responder: ¿Continuar? (s/n): s
```

### Paso 6: Revisar Resultados

```bash
# Ver reporte JSON
cat outcome/pipeline_updates/report.json

# Ver reporte CSV
cat outcome/pipeline_updates/report.csv

# Abrir reporte HTML
open outcome/pipeline_updates/report.html
```

---

## 7. OPCIONES DE LÍNEA DE COMANDOS

```
Uso: pipeline_updater.py [opciones]

Opciones obligatorias:
  --definition-ids IDS        IDs separados por comas (3388,3389,3390)
  --template ARCHIVO          Ruta del template YAML
  --pat TOKEN                 Azure DevOps PAT
  --org ORGANIZACIÓN          Organización AZDO
  --project PROYECTO          Proyecto AZDO

Opciones opcionales:
  --dry-run                   Solo simular, no aplicar
  --workers N                 Número de workers paralelos (default: 5)
  --timeout N                 Timeout por pipeline en segundos (default: 30)
  --verbose                   Mostrar logs detallados
  --rollback ID               Revertir a snapshot específico
  --snapshot-id ID            ID del snapshot para rollback
  --help                      Mostrar esta ayuda
```

---

## 8. INTERPRETACIÓN DE RESULTADOS

### Ejecución Exitosa

```
✓ Exitosos: 3
✗ Errores: 0
📊 Cambios totales: 3
⏱️  Duración: 2.1 segundos
💾 Snapshots: 3 (disponibles para rollback)
```

### Con Errores

```
✓ Exitosos: 2
✗ Errores: 1
📊 Cambios totales: 2
⏱️  Duración: 3.5 segundos
💾 Snapshots: 3

Error en Pipeline 3390:
  • Razón: Task "Docker Push" no encontrada
  • Snapshot disponible para rollback
```

### Reporte JSON

```json
{
  "timestamp": "2026-07-13T14:30:00Z",
  "summary": {
    "total": 3,
    "success": 3,
    "failed": 0
  },
  "details": [
    {
      "definition_id": 3388,
      "success": true,
      "snapshot_id": "snapshot_3388_1689254400",
      "matches_found": 1,
      "changes_applied": 1,
      "changes": [
        {
          "type": "task_field",
          "task": "Docker Push",
          "field": "inputs.imageRepository",
          "old": "gcr.io/old/app",
          "new": "gcr.io/new/app"
        }
      ]
    }
  ],
  "errors": []
}
```

---

## 9. ROLLBACK

### Rollback Automático

Si ocurre un error durante la ejecución, se revierte automáticamente:

```
❌ Error en Pipeline 3390
🔄 Ejecutando rollback automático...
✓ Rollback completado
```

### Rollback Manual

```bash
# Ver snapshots disponibles
ls -la outcome/snapshots/

# Revertir un pipeline específico
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --rollback \
  --definition-id 3388 \
  --snapshot-id "snapshot_3388_1689254400" \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros"
```

---

## 10. SOLUCIÓN DE PROBLEMAS

### Problema: "Template inválido"

**Causa**: Estructura incorrecta del YAML

**Solución**:
```bash
# Validar template
python scm/azdo/pipeline-updater/template_validator.py --template templates/mi_template.yaml

# Ver errores específicos
# Corregir según los errores reportados
```

### Problema: "Pipeline no encontrado"

**Causa**: ID incorrecto o pipeline eliminado

**Solución**:
```bash
# Verificar ID
python scm/main.py
# Seleccionar: 1 (AZDO)
# Seleccionar: 15 (CD Detailed Inventory)
# Buscar el pipeline correcto
```

### Problema: "Permiso denegado"

**Causa**: PAT sin permisos suficientes

**Solución**:
```bash
# Crear nuevo PAT con permisos:
# - Release (read, write)
# - Code (read)
# Ir a: https://dev.azure.com/Coppel-Retail/_usersSettings/tokens
```

### Problema: "Task no encontrada"

**Causa**: Nombre o tipo de task incorrecto

**Solución**:
```bash
# Verificar nombre exacto en AZDO
# Ir a pipeline → Edit → Ver nombre exacto de task
# Actualizar template con nombre correcto
```

### Problema: "Timeout"

**Causa**: Operación toma demasiado tiempo

**Solución**:
```bash
# Aumentar timeout
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "3388" \
  --template templates/update.yaml \
  --timeout 60  # Aumentar de 30 a 60 segundos
```

---

## 11. MEJORES PRÁCTICAS

### ✅ Recomendaciones

1. **Siempre usar dry-run primero**
   ```bash
   --dry-run
   ```

2. **Validar templates antes de ejecutar**
   ```bash
   template_validator.py --template template.yaml
   ```

3. **Usar snapshots para rollback**
   ```yaml
   options:
     rollback_on_error: true
   ```

4. **Documentar cambios en el template**
   ```yaml
   metadata:
     description: "Descripción clara"
   ```

5. **Versionar templates**
   ```yaml
   metadata:
     version: "1.0"
   ```

6. **Revisar reportes después de ejecutar**
   ```bash
   cat outcome/pipeline_updates/report.json
   ```

### ❌ Evitar

1. No ejecutar sin validación
2. No cambiar múltiples cosas a la vez
3. No ignorar errores
4. No perder snapshots
5. No ejecutar en horarios críticos

---

## 12. CASOS DE USO COMUNES

### Actualizar Imagen Docker

```bash
# 1. Crear template
cat > templates/docker.yaml << 'EOF'
metadata:
  name: "Actualizar imagen Docker"
  version: "1.0"
search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Docker Push"
      type: "DockerPush"
update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old/app"
          new_value: "gcr.io/new/app"
options:
  dry_run: false
EOF

# 2. Ejecutar
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "3388,3389,3390" \
  --template templates/docker.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros"
```

### Actualizar Variables

```bash
# Template similar, pero con variables en lugar de tasks
```

### Cambiar Conexión Kubernetes

```bash
# Template con KubernetesManifest task
```

---

## 13. INTEGRACIÓN CON CI/CD

### Ejecutar desde Pipeline

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.11'

- script: |
    pip install -r scm/azdo/pipeline-updater/requirements.txt
    python scm/azdo/pipeline-updater/pipeline_updater.py \
      --definition-ids "$(PIPELINE_IDS)" \
      --template "$(TEMPLATE_PATH)" \
      --pat "$(AZDO_PAT)" \
      --org "Coppel-Retail" \
      --project "Cadena_de_Suministros"
  displayName: 'Update Pipelines'
```

---

## 14. SOPORTE Y AYUDA

### Documentación

- `00_INICIO_AQUI.md` - Punto de entrada
- `01_ANALISIS_ARQUITECTURA.md` - Arquitectura técnica
- `02_ESPECIFICACION_TEMPLATE.md` - Formato de templates
- `03_PLAN_IMPLEMENTACION.md` - Plan de implementación
- `04_EJEMPLOS_PRACTICOS.md` - Casos reales
- `05_GUIA_USO.md` - Esta guía

### Contacto

Para preguntas o problemas:
- Contactar al equipo DevOps
- Crear issue en el repositorio
- Revisar logs en `outcome/pipeline_updates/`

---

**Versión**: 1.0  
**Última actualización**: 2026-07-13  
**Estado**: 📖 Guía Completa
