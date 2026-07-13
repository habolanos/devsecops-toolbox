# 📋 Especificación del Template de Actualización

## 1. ESTRUCTURA GENERAL

```yaml
metadata:
  name: "Nombre descriptivo del template"
  version: "1.0"
  description: "Descripción de qué hace"
  author: "Tu nombre"
  created: "2026-07-13"

search:
  # Criterios de búsqueda
  stages: []
  tasks: []
  variables: []
  artifacts: []
  approvals: []

update:
  # Cambios a aplicar
  tasks: []
  variables: []
  stages: []
  artifacts: []
  approvals: []

options:
  # Opciones de ejecución
  dry_run: false
  auto_confirm: false
  rollback_on_error: true
  parallel_workers: 5
```

---

## 2. SECCIÓN METADATA

Define información del template.

```yaml
metadata:
  name: "Actualizar imagen Docker"
  version: "1.0"
  description: "Cambia la imagen Docker en todos los pipelines de producción"
  author: "DevOps Team"
  created: "2026-07-13"
  tags: ["docker", "image", "production"]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `name` | string | Sí | Nombre único del template |
| `version` | string | Sí | Versión semántica |
| `description` | string | No | Descripción detallada |
| `author` | string | No | Quién creó el template |
| `created` | date | No | Fecha de creación |
| `tags` | array | No | Tags para búsqueda |

---

## 3. SECCIÓN SEARCH

Define QUÉ BUSCAR en los pipelines.

### 3.1 Buscar Stages

```yaml
search:
  stages:
    - name: "QA"
    - name: "Producción"
    - name: "Staging"
```

**Parámetros**:
- `name`: Nombre exacto del stage
- `rank`: (Opcional) Posición del stage

**Ejemplo**:
```yaml
search:
  stages:
    - name: "Producción"
      rank: 3
```

---

### 3.2 Buscar Tasks

```yaml
search:
  tasks:
    - name: "Docker Push"
      type: "DockerPush"
    - name: "Deploy to Kubernetes"
      type: "KubernetesManifest"
```

**Parámetros**:
- `name`: Nombre exacto de la task
- `type`: Tipo de task (DockerPush, KubernetesManifest, etc.)
- `enabled`: (Opcional) Solo tareas habilitadas (true/false)

**Tipos comunes**:
```
- DockerPush
- KubernetesManifest
- AzureAppServiceDeploy
- AzureCLI
- PowerShell
- Bash
- CopyFiles
- PublishBuildArtifacts
```

**Ejemplo**:
```yaml
search:
  tasks:
    - name: "Docker Push"
      type: "DockerPush"
      enabled: true
```

---

### 3.3 Buscar Variables

```yaml
search:
  variables:
    - name: "IMAGE_REPOSITORY"
    - name: "ENVIRONMENT"
    - name: "DOCKER_TAG"
```

**Parámetros**:
- `name`: Nombre exacto de la variable
- `scope`: (Opcional) Scope de la variable (release, stage)

**Ejemplo**:
```yaml
search:
  variables:
    - name: "IMAGE_REPOSITORY"
      scope: "release"
```

---

### 3.4 Buscar Artefactos

```yaml
search:
  artifacts:
    - alias: "drop"
      type: "BuildArtifact"
    - alias: "docker-image"
      type: "Container"
```

**Parámetros**:
- `alias`: Alias del artefacto
- `type`: Tipo (BuildArtifact, Container, etc.)

---

### 3.5 Buscar Approvals

```yaml
search:
  approvals:
    - stage: "Producción"
      type: "pre-deployment"
```

**Parámetros**:
- `stage`: Stage que tiene approval
- `type`: Tipo (pre-deployment, post-deployment)

---

## 4. SECCIÓN UPDATE

Define QUÉ ACTUALIZAR.

### 4.1 Actualizar Tasks

```yaml
update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old-project/app"
          new_value: "gcr.io/new-project/app"
        - path: "inputs.tag"
          old_value: "latest"
          new_value: "v2.0.0"
```

**Parámetros**:
- `name`: Nombre de la task a actualizar
- `fields`: Lista de campos a cambiar
  - `path`: Ruta del campo (ej: inputs.imageRepository)
  - `old_value`: Valor actual (validación)
  - `new_value`: Nuevo valor

**Rutas comunes**:
```
inputs.imageRepository      # Repositorio Docker
inputs.tag                  # Tag Docker
inputs.kubernetesServiceConnection  # Conexión K8s
inputs.namespace            # Namespace K8s
inputs.manifests            # Manifiestos K8s
inputs.containerRegistryType # Tipo de registro
```

**Ejemplo completo**:
```yaml
update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/coppel-old/app"
          new_value: "gcr.io/coppel-new/app"
        - path: "inputs.containerRegistryType"
          old_value: "Container Registry"
          new_value: "Azure Container Registry"
```

---

### 4.2 Actualizar Variables

```yaml
update:
  variables:
    - name: "IMAGE_REPOSITORY"
      old_value: "gcr.io/old/app"
      new_value: "gcr.io/new/app"
    - name: "ENVIRONMENT"
      old_value: "staging"
      new_value: "production"
```

**Parámetros**:
- `name`: Nombre de la variable
- `old_value`: Valor actual (validación)
- `new_value`: Nuevo valor
- `scope`: (Opcional) Scope específico

**Ejemplo**:
```yaml
update:
  variables:
    - name: "DOCKER_TAG"
      old_value: "1.0.0"
      new_value: "2.0.0"
      scope: "release"
```

---

### 4.3 Actualizar Stages

```yaml
update:
  stages:
    - name: "Producción"
      fields:
        - path: "rank"
          old_value: 2
          new_value: 3
        - path: "preDeployApprovals.approvals[0].approver"
          old_value: "user1@company.com"
          new_value: "user2@company.com"
```

---

### 4.4 Agregar Elementos

```yaml
update:
  tasks:
    - name: "Deploy to Kubernetes"
      action: "add"
      position: "after"
      reference_task: "Docker Push"
      definition:
        displayName: "Deploy to Kubernetes"
        task:
          id: "6C731787-BC2C-4436-8290-A81493FFEA35"
          versionSpec: "0.*"
```

---

### 4.5 Eliminar Elementos

```yaml
update:
  tasks:
    - name: "Old Deploy Task"
      action: "remove"
```

---

## 5. SECCIÓN OPTIONS

Opciones de ejecución.

```yaml
options:
  dry_run: false              # Solo simular, no aplicar
  auto_confirm: false         # No pedir confirmación
  rollback_on_error: true     # Revertir si hay error
  parallel_workers: 5         # Número de workers
  timeout_per_pipeline: 30    # Timeout en segundos
  stop_on_first_error: false  # Parar si hay error
```

| Opción | Tipo | Default | Descripción |
|--------|------|---------|-------------|
| `dry_run` | bool | false | Solo simular cambios |
| `auto_confirm` | bool | false | No pedir confirmación |
| `rollback_on_error` | bool | true | Revertir si falla |
| `parallel_workers` | int | 5 | Workers paralelos |
| `timeout_per_pipeline` | int | 30 | Timeout en segundos |
| `stop_on_first_error` | bool | false | Parar en primer error |

---

## 6. EJEMPLOS PRÁCTICOS

### Ejemplo 1: Actualizar Imagen Docker

```yaml
metadata:
  name: "Actualizar imagen Docker"
  version: "1.0"
  description: "Cambia la imagen Docker en todos los pipelines"

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
          old_value: "gcr.io/coppel-old/app"
          new_value: "gcr.io/coppel-new/app"
        - path: "inputs.tag"
          old_value: "latest"
          new_value: "v2.0.0"

options:
  dry_run: false
  rollback_on_error: true
```

---

### Ejemplo 2: Actualizar Variables de Entorno

```yaml
metadata:
  name: "Actualizar variables de entorno"
  version: "1.0"

search:
  stages:
    - name: "QA"
    - name: "Producción"
  variables:
    - name: "ENVIRONMENT"
    - name: "LOG_LEVEL"

update:
  variables:
    - name: "ENVIRONMENT"
      old_value: "staging"
      new_value: "production"
    - name: "LOG_LEVEL"
      old_value: "INFO"
      new_value: "DEBUG"

options:
  dry_run: true
```

---

### Ejemplo 3: Actualizar Conexión Kubernetes

```yaml
metadata:
  name: "Actualizar conexión Kubernetes"
  version: "1.0"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Deploy to Kubernetes"
      type: "KubernetesManifest"

update:
  tasks:
    - name: "Deploy to Kubernetes"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "old-gke-cluster"
          new_value: "new-gke-cluster"
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"

options:
  rollback_on_error: true
  parallel_workers: 3
```

---

### Ejemplo 4: Actualización Compleja (Multi-stage, Multi-task)

```yaml
metadata:
  name: "Actualización completa de producción"
  version: "2.0"
  description: "Actualiza imagen, variables y conexiones"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Docker Push"
      type: "DockerPush"
    - name: "Deploy to Kubernetes"
      type: "KubernetesManifest"
  variables:
    - name: "IMAGE_REPOSITORY"
    - name: "ENVIRONMENT"
    - name: "REPLICAS"

update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old/app"
          new_value: "gcr.io/new/app"
        - path: "inputs.tag"
          old_value: "1.0.0"
          new_value: "2.0.0"
    - name: "Deploy to Kubernetes"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "old-cluster"
          new_value: "new-cluster"
        - path: "inputs.namespace"
          old_value: "staging"
          new_value: "production"
  variables:
    - name: "IMAGE_REPOSITORY"
      old_value: "gcr.io/old/app"
      new_value: "gcr.io/new/app"
    - name: "ENVIRONMENT"
      old_value: "staging"
      new_value: "production"
    - name: "REPLICAS"
      old_value: "3"
      new_value: "5"

options:
  dry_run: false
  rollback_on_error: true
  parallel_workers: 5
  timeout_per_pipeline: 60
```

---

## 7. VALIDACIÓN DE TEMPLATES

### Reglas de Validación

1. **Metadata obligatoria**:
   - `name` no puede estar vacío
   - `version` debe ser semántica (X.Y.Z)

2. **Search y Update**:
   - Al menos uno debe tener contenido
   - Los nombres deben coincidir con elementos reales

3. **Rutas de campos**:
   - Deben ser válidas (inputs.*, variables.*, etc.)
   - Validar tipos de datos

4. **Valores**:
   - `old_value` debe coincidir con valor actual
   - `new_value` no puede ser null

### Ejemplo de Validación

```bash
# Validar template
python -c "
from template_validator import TemplateValidator
validator = TemplateValidator('template.yaml')
if validator.validate():
    print('✓ Template válido')
else:
    print('✗ Errores:')
    for error in validator.errors:
        print(f'  - {error}')
"
```

---

## 8. MEJORES PRÁCTICAS

### DO ✅

```yaml
# Usar nombres descriptivos
metadata:
  name: "Actualizar imagen Docker a v2.0.0"

# Especificar valores old_value para validación
update:
  variables:
    - name: "DOCKER_TAG"
      old_value: "1.0.0"
      new_value: "2.0.0"

# Usar dry_run para probar primero
options:
  dry_run: true
```

### DON'T ❌

```yaml
# Nombres genéricos
metadata:
  name: "Update"

# Sin validación de valores anteriores
update:
  variables:
    - name: "DOCKER_TAG"
      new_value: "2.0.0"

# Aplicar directamente sin dry_run
options:
  dry_run: false
```

---

## 9. VERSIONADO DE TEMPLATES

```yaml
metadata:
  name: "Actualizar imagen Docker"
  version: "1.0"  # Versión inicial
  # version: "1.1"  # Cambios menores
  # version: "2.0"  # Cambios mayores
```

**Convención**:
- **1.0**: Versión inicial
- **1.1**: Cambios menores (campos adicionales)
- **2.0**: Cambios mayores (estructura diferente)

---

## 10. ALMACENAMIENTO DE TEMPLATES

```
templates/
├── docker-image-update.yaml
├── environment-variables.yaml
├── kubernetes-connection.yaml
├── approval-update.yaml
└── complete-production-update.yaml
```

**Recomendación**: Guardar templates en Git para auditoría y versionado.

---

**Versión**: 1.0  
**Fecha**: 2026-07-13
