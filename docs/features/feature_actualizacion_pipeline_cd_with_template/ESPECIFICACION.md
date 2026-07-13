# 📋 Especificación del Template

## Estructura Base

```yaml
metadata:
  name: string              # Nombre del template
  version: string           # Versión (ej: 1.0)
  description: string       # Descripción (opcional)
  comment: string           # Comentario único para auditoría

search:                     # QUÉ BUSCAR
  stages: [string]          # Nombres de stages
  tasks: [object]           # Criterios de búsqueda de tasks
  variables: [object]       # Criterios de búsqueda de variables

update:                     # QUÉ CAMBIAR
  tasks: [object]           # Cambios en tasks
  variables: [object]       # Cambios en variables
  stages: [object]          # Cambios en stages

options:                    # OPCIONES (opcional)
  dry_run: boolean          # Solo simular (default: false)
  rollback_on_error: bool   # Revertir si falla (default: true)
```

---

## Sección: metadata

```yaml
metadata:
  name: "Nombre descriptivo del template"
  version: "1.0"
  description: "Descripción opcional"
  comment: |
    Comentario único que se registra en cada pipeline.
    Puede ser multilinea.
    Se usa para auditoría y trazabilidad.
```

**Notas:**
- `name`: Identificador único del template
- `version`: Seguimiento de cambios (ej: 1.0, 1.1, 2.0)
- `comment`: Aparece en historial de cambios del pipeline

---

## Sección: search

### Buscar Stages

```yaml
search:
  stages: ["Producción", "Staging"]
```

Busca stages cuyo nombre coincida exactamente.

### Buscar Tasks

```yaml
search:
  tasks:
    - name: "Deploy"              # Requerido: Nombre exacto
    # - type: "KubectlDeploy"     # Opcional: Tipo de task (más específico)
    - name: "Build"
    # - type: "Docker"
```

**Notas:**
- `name`: Requerido - Nombre exacto de la tarea
- `type`: Opcional - Tipo de tarea (para más precisión)

**Tipos de Tasks Comunes (referencia):**
- `KubectlDeploy` - Desplegar en Kubernetes
- `Docker` - Construir/empujar imagen Docker
- `PowerShell` - Ejecutar script PowerShell
- `BashScript` - Ejecutar script Bash
- `AzureCLI` - Ejecutar comando Azure CLI
- `ServiceFabricDeploy` - Desplegar en Service Fabric
- `AzureAppServiceDeploy` - Desplegar en App Service
- `CmdLine` - Ejecutar comando línea
- `VSTest` - Ejecutar tests Visual Studio

### Buscar Variables

```yaml
search:
  variables:
    - name: "IMAGE_TAG"
      scope: "Release"            # Release, Stage (opcional)
```

---

## Sección: update

### Actualizar Tasks

```yaml
update:
  tasks:
    - name: "Deploy"
      fields:
        - path: "inputs.image"
          old_value: "myapp:v1.0"
          new_value: "myapp:v2.0"
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"
```

**Estructura de field:**
- `path`: Ruta a la propiedad (inputs.*, properties.*)
- `old_value`: Valor actual a buscar
- `new_value`: Valor nuevo a reemplazar

### Actualizar Variables

```yaml
update:
  variables:
    - name: "IMAGE_TAG"
      old_value: "v1.0"
      new_value: "v2.0"
    - name: "ENVIRONMENT"
      old_value: "staging"
      new_value: "production"
```

### Reorganizar Stages

```yaml
update:
  stages:
    - name: "Deploy"
      rank: 1
    - name: "Test"
      rank: 2
    - name: "Build"
      rank: 3
```

**Notas:**
- `rank`: Posición en el pipeline (1 = primero)
- No se necesita `old_value`

---

## Sección: options (Opcional)

```yaml
options:
  dry_run: false              # true = simular, false = ejecutar
  rollback_on_error: true     # true = revertir si falla
```

---

## Ejemplos Rápidos

### Ejemplo 1: Cambiar Imagen Docker

```yaml
metadata:
  name: "Actualizar Docker"
  version: "1.0"
  comment: "Cambiar imagen de v1.0 a v2.0"

search:
  stages: ["Producción"]
  tasks:
    - name: "Push Docker"
      type: "Docker"

update:
  tasks:
    - name: "Push Docker"
      fields:
        - path: "inputs.repository"
          old_value: "myapp:v1.0"
          new_value: "myapp:v2.0"
```

### Ejemplo 2: Cambiar Variable

```yaml
metadata:
  name: "Cambiar ambiente"
  version: "1.0"
  comment: "Cambiar de staging a production"

search:
  variables:
    - name: "ENVIRONMENT"

update:
  variables:
    - name: "ENVIRONMENT"
      old_value: "staging"
      new_value: "production"
```

### Ejemplo 3: Cambiar Conexión Kubernetes

```yaml
metadata:
  name: "Cambiar cluster K8s"
  version: "1.0"
  comment: "Migrar a nuevo cluster"

search:
  stages: ["Deploy"]
  tasks:
    - type: "KubectlDeploy"

update:
  tasks:
    - name: "Deploy"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "old-cluster"
          new_value: "new-cluster"
```

### Ejemplo 4: Múltiples Cambios

```yaml
metadata:
  name: "Migración completa"
  version: "1.0"
  comment: "Cambiar cluster, imagen y variables"

search:
  stages: ["Producción"]
  tasks:
    - type: "KubectlDeploy"
    - type: "Docker"
  variables:
    - name: "ENVIRONMENT"

update:
  tasks:
    - name: "Deploy"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "old-cluster"
          new_value: "new-cluster"
    - name: "Push Docker"
      fields:
        - path: "inputs.repository"
          old_value: "myapp:v1.0"
          new_value: "myapp:v2.0"
  variables:
    - name: "ENVIRONMENT"
      old_value: "staging"
      new_value: "production"
```

---

## Validación

El template se valida automáticamente:

✅ Estructura YAML válida  
✅ Secciones requeridas presentes  
✅ Tipos de datos correctos  
✅ Rutas de búsqueda válidas  
✅ Valores no vacíos  

---

## Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `Invalid YAML` | Sintaxis incorrecta | Revisar indentación |
| `Missing metadata` | Falta sección metadata | Agregar metadata |
| `Invalid path` | Ruta incorrecta | Usar `inputs.*` o `properties.*` |
| `Stage not found` | Stage no existe | Verificar nombre exacto |
| `Task not found` | Task no existe | Verificar nombre y tipo |

---

## Mejores Prácticas

1. **Nombres exactos**: Usar nombres exactos de stages y tasks
2. **Valores precisos**: `old_value` debe coincidir exactamente
3. **Comentarios claros**: Explicar razón del cambio
4. **Versiones**: Incrementar versión con cada cambio
5. **Dry-run**: Probar con `dry_run: true` primero
6. **Backup**: Hacer snapshot antes de ejecutar

---

**Versión**: 1.0  
**Última actualización**: 2026-07-13
