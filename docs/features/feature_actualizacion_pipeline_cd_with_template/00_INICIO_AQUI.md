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
Archivo YAML/JSON que define QUÉ BUSCAR y QUÉ ACTUALIZAR:

#### Ejemplo 1: Buscar y Cambiar Propiedad en Task Kubectl
```yaml
metadata:
  name: "Actualizar namespace en Kubectl"
  version: "1.0"
  description: "Migración de cluster GKE y namespace"
  comment: |
    Cambios realizados:
    - Cluster: old-gke-cluster → new-gke-cluster
    - Namespace: default → production
    - Manifiestos: k8s/old-manifest.yaml → k8s/new-manifest.yaml
    
    Razón: Migración a nuevo cluster GKE en us-central1
    Aprobado por: Infrastructure Team
    Fecha: 2026-07-13
  
search:
  stages: ["Producción"]
  tasks:
    - name: "Deploy with Kubectl"
      type: "KubectlDeploy"
  
update:
  tasks:
    - name: "Deploy with Kubectl"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "old-gke-cluster"
          new_value: "new-gke-cluster"
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"
        - path: "inputs.manifests"
          old_value: "k8s/old-manifest.yaml"
          new_value: "k8s/new-manifest.yaml"
```

#### Ejemplo 2: Buscar Cadena en Task Command Line
```yaml
metadata:
  name: "Buscar y reemplazar en PowerShell"
  version: "1.0"
  
search:
  stages: ["QA", "Staging"]
  tasks:
    - name: "Run PowerShell Script"
      type: "PowerShell"
  
update:
  tasks:
    - name: "Run PowerShell Script"
      fields:
        # Buscar cadena en el script y reemplazarla
        - path: "inputs.script"
          old_value: "Write-Host 'Environment: staging'"
          new_value: "Write-Host 'Environment: production'"
        # O cambiar parámetros
        - path: "inputs.arguments"
          old_value: "-Environment staging -Replicas 3"
          new_value: "-Environment production -Replicas 5"
```

#### Ejemplo 3: Buscar y Cambiar en Task Bash/Shell
```yaml
metadata:
  name: "Actualizar variables en Bash"
  version: "1.0"
  
search:
  stages: ["Deploy"]
  tasks:
    - name: "Execute Bash Script"
      type: "BashScript"
  
update:
  tasks:
    - name: "Execute Bash Script"
      fields:
        - path: "inputs.script"
          old_value: "export DOCKER_REGISTRY=gcr.io/old-project"
          new_value: "export DOCKER_REGISTRY=gcr.io/new-project"
        - path: "inputs.script"
          old_value: "kubectl apply -f manifests/old/"
          new_value: "kubectl apply -f manifests/new/"
```

#### Ejemplo 3b: Buscar y Cambiar Cadena en Script (Inline Script Task)
```yaml
metadata:
  name: "Actualizar cadena en script inline"
  version: "1.0"
  description: "Cambiar URL de base de datos en script inline"
  comment: |
    Actualización de cadena en script
    
    Cambios realizados:
    - URL de BD: old-db.company.com → new-db.company.com
    - Puerto: 5432 → 5433
    - Razón: Migración a nuevo servidor de base de datos
    - Aprobado por: Database Team
    - Fecha: 2026-07-13

search:
  stages: ["Staging", "Producción"]
  tasks:
    - name: "Initialize Database"
      type: "PowerShell"

update:
  tasks:
    - name: "Initialize Database"
      fields:
        # Buscar y reemplazar URL de base de datos
        - path: "inputs.script"
          old_value: "Server=old-db.company.com;Port=5432"
          new_value: "Server=new-db.company.com;Port=5433"
        
        # Buscar y reemplazar credencial
        - path: "inputs.script"
          old_value: "User=dbuser_old;Password=$(OLD_DB_PASSWORD)"
          new_value: "User=dbuser_new;Password=$(NEW_DB_PASSWORD)"
        
        # Buscar y reemplazar nombre de base de datos
        - path: "inputs.script"
          old_value: "Database=production_old"
          new_value: "Database=production_new"
```

**Ejemplo de script original**:
```powershell
$connectionString = "Server=old-db.company.com;Port=5432;User=dbuser_old;Password=$(OLD_DB_PASSWORD);Database=production_old"
$connection = New-Object System.Data.SqlClient.SqlConnection
$connection.ConnectionString = $connectionString
$connection.Open()
Write-Host "Connected to old-db.company.com"
```

**Resultado después de la actualización**:
```powershell
$connectionString = "Server=new-db.company.com;Port=5433;User=dbuser_new;Password=$(NEW_DB_PASSWORD);Database=production_new"
$connection = New-Object System.Data.SqlClient.SqlConnection
$connection.ConnectionString = $connectionString
$connection.Open()
Write-Host "Connected to new-db.company.com"
```

#### Ejemplo 4: Eliminar una Task
```yaml
metadata:
  name: "Eliminar task obsoleta"
  version: "1.0"
  
search:
  stages: ["QA"]
  tasks:
    - name: "Old Deployment Task"
      type: "AzureAppServiceDeploy"
  
update:
  tasks:
    - name: "Old Deployment Task"
      action: "remove"  # Eliminar esta task
```

#### Ejemplo 5: Agregar una Nueva Task
```yaml
metadata:
  name: "Agregar task de validación"
  version: "1.0"
  
search:
  stages: ["Staging"]
  tasks:
    - name: "Deploy to Kubernetes"
      type: "KubernetesManifest"
  
update:
  tasks:
    # Agregar nueva task DESPUÉS de "Deploy to Kubernetes"
    - name: "Health Check Validation"
      action: "add"
      position: "after"
      reference_task: "Deploy to Kubernetes"
      definition:
        displayName: "Health Check Validation"
        enabled: true
        task:
          id: "6C731787-BC2C-4436-8290-A81493FFEA35"  # BashScript
          versionSpec: "3.*"
        inputs:
          script: |
            #!/bin/bash
            echo "Validating deployment health..."
            kubectl get pods -n production
            kubectl get services -n production
```

#### Ejemplo 6: Agregar Stage Completo con Dependencias
```yaml
metadata:
  name: "Agregar stage de validación"
  version: "2.0"
  description: "Agregar stage de Smoke Testing que depende de Staging"
  
search:
  stages:
    - name: "Staging"
    - name: "Producción"
  
update:
  stages:
    # Agregar nuevo stage entre Staging y Producción
    - name: "Smoke Testing"
      action: "add"
      position: "between"
      before_stage: "Producción"
      after_stage: "Staging"
      definition:
        id: 4
        name: "Smoke Testing"
        rank: 2
        deployPhases:
          - id: 1
            name: "Run Smoke Tests"
            deploymentInput:
              tasks:
                - displayName: "Run Smoke Tests"
                  enabled: true
                  task:
                    id: "6C731787-BC2C-4436-8290-A81493FFEA35"
                    versionSpec: "3.*"
                  inputs:
                    script: |
                      #!/bin/bash
                      echo "Running smoke tests..."
                      curl -f https://api.production.com/health
                      curl -f https://web.production.com/
        # Hacer que este stage dependa de Staging
        preDeployApprovals:
          approvals:
            - rank: 1
              isAutomated: true
              isNotificationOn: false
              approver:
                displayName: "Automated"
        # Hacer que Producción dependa de este stage
        postDeployApprovals:
          approvals: []
```

#### Ejemplo 7: Cambiar Dependencias Entre Stages
```yaml
metadata:
  name: "Cambiar dependencias de stages"
  version: "1.0"
  
search:
  stages:
    - name: "Producción"
  
update:
  stages:
    - name: "Producción"
      fields:
        # Cambiar el stage del que depende
        - path: "preDeployApprovals.approvals[0].approver.displayName"
          old_value: "QA Team"
          new_value: "DevOps Team"
        # Cambiar rank (posición en el pipeline)
        - path: "rank"
          old_value: 3
          new_value: 4
      
      # Comentario automático basado en el tipo de cambio
      comment:
        type: "dependency_change"  # Tipos: dependency_change, stage_reorder, task_update, etc.
        message: "Actualización de dependencias: Ahora requiere aprobación de DevOps Team"
      
      # Comentario personalizado adicional (opcional)
      custom_comment: "Cambio realizado como parte de la migración a nuevo cluster GKE"
```

---

#### Ejemplo 7b: Reorganizar Orden de Stages
```yaml
metadata:
  name: "Reorganizar orden de stages"
  version: "1.0"
  description: "Cambiar el orden de ejecución de los stages en el pipeline"
  comment: |
    Reorganización masiva de stages
    
    Nuevo orden de ejecución:
    1. Staging (ambiente de prueba inicial)
    2. Producción (deploy a producción)
    3. QA (validación post-deploy)
    
    Razón: Validar en staging antes de producción, y QA después para auditoría
    Aprobado por: DevOps Team
    Efectivo desde: 2026-07-13
  
search:
  stages:
    - name: "QA"
    - name: "Staging"
    - name: "Producción"

update:
  stages:
    # Mover Staging a la primera posición
    - name: "Staging"
      rank: 1
    
    # Mover Producción a la segunda posición
    - name: "Producción"
      rank: 2
    
    # Mover QA al final
    - name: "QA"
      rank: 3
```

**Resultado esperado**:
```
Antes:
1. QA
2. Staging
3. Producción

Después:
1. Staging
2. Producción
3. QA
```

#### Ejemplo 8: Actualización Compleja (Multi-stage, Multi-task)
```yaml
metadata:
  name: "Migración completa con nuevo stage"
  version: "3.0"
  description: "Agregar stage de validación, cambiar tasks y actualizar dependencias"
  comment: |
    Migración integral de infraestructura
    
    Cambios realizados:
    1. Eliminar: Azure App Service Deploy (obsoleta)
    2. Actualizar: Docker Push → nuevo proyecto GCP (old-project → new-project)
    3. Actualizar: Kubectl → nuevo cluster GKE (old-gke → new-gke)
    4. Agregar: Stage de Validation (Smoke Testing)
    
    Razón: Consolidación de infraestructura y modernización de deployments
    Aprobado por: Infrastructure & DevOps Team
    Fecha: 2026-07-13
    Contacto: devops@company.com
  
search:
  stages:
    - name: "QA"
    - name: "Staging"
    - name: "Producción"
  tasks:
    - name: "Docker Push"
      type: "DockerPush"
    - name: "Deploy with Kubectl"
      type: "KubectlDeploy"
    - name: "Old Legacy Task"
      type: "AzureAppServiceDeploy"
  
update:
  # 1. Eliminar task obsoleta
  tasks:
    - name: "Old Legacy Task"
      action: "remove"
    
    # 2. Cambiar Docker Push
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old-project/app"
          new_value: "gcr.io/new-project/app"
    
    # 3. Cambiar Kubectl
    - name: "Deploy with Kubectl"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "old-gke"
          new_value: "new-gke"
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"
  
  # 4. Agregar nuevo stage de validación
  stages:
    - name: "Validation"
      action: "add"
      position: "between"
      after_stage: "Staging"
      before_stage: "Producción"
      definition:
        id: 3
        name: "Validation"
        rank: 2
        deployPhases:
          - id: 1
            name: "Health Checks"
            deploymentInput:
              tasks:
                - displayName: "Validate Deployment"
                  enabled: true
                  task:
                    id: "6C731787-BC2C-4436-8290-A81493FFEA35"
                    versionSpec: "3.*"
                  inputs:
                    script: |
                      #!/bin/bash
                      echo "Validating..."
                      kubectl get pods -n production
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
