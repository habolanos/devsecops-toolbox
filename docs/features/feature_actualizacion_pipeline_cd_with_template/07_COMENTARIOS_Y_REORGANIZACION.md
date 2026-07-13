# 📝 Comentarios y Reorganización de Stages

## 1. SISTEMA DE COMENTARIOS

### 1.1 Tipos de Comentarios

El sistema soporta dos tipos de comentarios:

#### **Comentarios Automáticos (comment)**
Se generan automáticamente basados en el tipo de cambio realizado.

```yaml
comment:
  type: "task_update"  # Tipo de cambio
  message: "Descripción automática del cambio"
```

**Tipos disponibles**:
```
- task_update          → Actualización de task
- task_removal         → Eliminación de task
- task_addition        → Adición de task
- stage_update         → Actualización de stage
- stage_removal        → Eliminación de stage
- stage_addition       → Adición de stage
- dependency_change    → Cambio de dependencias
- stage_reorder        → Reorganización de stages
- variable_update      → Actualización de variables
- approval_change      → Cambio de aprobadores
```

#### **Comentarios Personalizados (custom_comment)**
Comentarios adicionales definidos por el usuario para proporcionar contexto.

```yaml
custom_comment: "Descripción detallada del cambio"
```

---

### 1.2 Estructura Completa de Comentarios

```yaml
update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old/app"
          new_value: "gcr.io/new/app"
      
      # Comentario automático
      comment:
        type: "task_update"
        message: "Registro Docker actualizado"
      
      # Comentario personalizado (opcional)
      custom_comment: "Migración a nuevo proyecto GCP como parte de la consolidación de infraestructura"
```

---

## 2. EJEMPLOS DE COMENTARIOS POR TIPO

### 2.1 Task Update (Actualización de Task)

```yaml
metadata:
  name: "Actualizar configuración de Docker"
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
          old_value: "gcr.io/old-project/app"
          new_value: "gcr.io/new-project/app"
        - path: "inputs.tag"
          old_value: "1.0.0"
          new_value: "2.0.0"
      
      comment:
        type: "task_update"
        message: "Imagen Docker actualizada a v2.0.0 en nuevo registro"
      
      custom_comment: |
        Cambios realizados:
        - Proyecto GCP: old-project → new-project
        - Versión: 1.0.0 → 2.0.0
        - Razón: Consolidación de registros y actualización de versión
        - Aprobado por: DevOps Team
        - Fecha: 2026-07-13
```

**Salida esperada**:
```
[TASK UPDATE] Imagen Docker actualizada a v2.0.0 en nuevo registro
  → Detalle: Cambios realizados:
    - Proyecto GCP: old-project → new-project
    - Versión: 1.0.0 → 2.0.0
    - Razón: Consolidación de registros y actualización de versión
    - Aprobado por: DevOps Team
    - Fecha: 2026-07-13
```

---

### 2.2 Task Removal (Eliminación de Task)

```yaml
metadata:
  name: "Eliminar task obsoleta"
  version: "1.0"

search:
  stages:
    - name: "Staging"
  tasks:
    - name: "Old Deployment"
      type: "AzureAppServiceDeploy"

update:
  tasks:
    - name: "Old Deployment"
      action: "remove"
      
      comment:
        type: "task_removal"
        message: "Task obsoleta removida - Reemplazada por KubectlDeploy"
      
      custom_comment: |
        Razón de eliminación:
        - Azure App Service ya no se usa en producción
        - Todos los deployments ahora usan Kubernetes
        - Simplifica el pipeline y reduce complejidad
        - Migración completada el 2026-07-10
        - Contacto: devops@company.com
```

---

### 2.3 Task Addition (Adición de Task)

```yaml
metadata:
  name: "Agregar validación de seguridad"
  version: "1.0"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Deploy with Kubectl"
      type: "KubectlDeploy"

update:
  tasks:
    - name: "Security Scan"
      action: "add"
      position: "after"
      reference_task: "Deploy with Kubectl"
      
      comment:
        type: "task_addition"
        message: "Task de escaneo de seguridad agregada después del deploy"
      
      custom_comment: |
        Nueva task de validación:
        - Escanea vulnerabilidades en imágenes Docker
        - Valida políticas de seguridad de Kubernetes
        - Genera reporte de compliance
        - Requerido por: Security Team
        - Implementado: 2026-07-13
      
      definition:
        displayName: "Security Scan"
        enabled: true
        task:
          id: "6C731787-BC2C-4436-8290-A81493FFEA35"
          versionSpec: "3.*"
        inputs:
          script: |
            #!/bin/bash
            echo "Running security scan..."
            # Scan implementation
```

---

### 2.4 Stage Addition (Adición de Stage)

```yaml
metadata:
  name: "Agregar stage de validación"
  version: "1.0"

search:
  stages:
    - name: "Staging"
    - name: "Producción"

update:
  stages:
    - name: "Smoke Testing"
      action: "add"
      position: "between"
      after_stage: "Staging"
      before_stage: "Producción"
      
      comment:
        type: "stage_addition"
        message: "Nuevo stage de Smoke Testing agregado entre Staging y Producción"
      
      custom_comment: |
        Propósito del nuevo stage:
        - Validar deployment antes de producción
        - Ejecutar pruebas de humo (smoke tests)
        - Verificar endpoints críticos
        - Duración estimada: 5-10 minutos
        - Responsable: QA Team
        - Inicio: 2026-07-15
      
      definition:
        # ... definición del stage
```

---

### 2.5 Dependency Change (Cambio de Dependencias)

```yaml
metadata:
  name: "Actualizar dependencias"
  version: "1.0"

search:
  stages:
    - name: "Producción"

update:
  stages:
    - name: "Producción"
      fields:
        - path: "preDeployApprovals.approvals[0].approver.displayName"
          old_value: "QA Team"
          new_value: "DevOps Team"
      
      comment:
        type: "dependency_change"
        message: "Aprobador previo cambiado de QA Team a DevOps Team"
      
      custom_comment: |
        Cambio de dependencias:
        - Aprobador anterior: QA Team
        - Nuevo aprobador: DevOps Team
        - Razón: QA ahora está en stage separado
        - Timeout: 24 horas
        - Notificaciones: Habilitadas
        - Efectivo desde: 2026-07-13
```

---

## 3. REORGANIZACIÓN DE STAGES

### 3.1 Cambiar Orden de Ejecución (Masivo)

**Caso**: Cambiar el orden en que se ejecutan los stages

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

# Comentario global para toda la reorganización
global_comment:
  type: "stage_reorder"
  message: "Reorganización masiva de stages"
  custom_comment: |
    Nuevo orden de ejecución:
    1. Build (compilación)
    2. Deploy (despliegue a staging)
    3. Test (pruebas post-deploy)
    4. Validate (validación final)
    
    Razón: Validar deployment antes de pruebas para detectar errores temprano

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

**Resultado**:
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

---

### 3.2 Reorganizar con Cambios de Dependencias

```yaml
metadata:
  name: "Reorganizar y actualizar dependencias"
  version: "2.0"

search:
  stages:
    - name: "QA"
    - name: "Staging"
    - name: "Producción"

# Comentario global para la reorganización y cambios de dependencias
global_comment:
  type: "stage_reorder"
  message: "Reorganización masiva con actualización de dependencias"
  custom_comment: |
    Cambios realizados:
    1. Nuevo orden: Staging → QA → Producción
    2. Staging es ahora el primer ambiente de prueba
    3. Producción depende de QA en lugar de Staging
    
    Razón: QA debe validar después de Staging antes de producción

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
      # Comentario específico solo para cambio de dependencia
      comment:
        type: "dependency_change"
        message: "Dependencia de Producción actualizada a Staging"
```

---

### 3.3 Insertar Stage en Posición Específica

```yaml
metadata:
  name: "Insertar stage de seguridad"
  version: "1.0"

search:
  stages:
    - name: "Build"
    - name: "Deploy"
    - name: "Producción"

# Comentario global para la inserción de nuevo stage
global_comment:
  type: "stage_addition"
  message: "Nuevo stage de Security Check insertado en el pipeline"
  custom_comment: |
    Cambios realizados:
    1. Nuevo stage: Security Check (posición 2)
    2. Nuevo orden: Build → Security Check → Deploy → Producción
    3. Duración estimada: 10-15 minutos
    
    Razón: Validar seguridad antes de deploy para cumplir políticas de compliance

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

---

## 4. AUDITORÍA DE COMENTARIOS

### 4.1 Reporte de Comentarios

Los comentarios se incluyen en el reporte final:

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
      "changes": [
        {
          "type": "task_update",
          "task": "Docker Push",
          "field": "inputs.imageRepository",
          "old": "gcr.io/old/app",
          "new": "gcr.io/new/app",
          "comment": {
            "type": "task_update",
            "message": "Registro Docker actualizado",
            "custom_comment": "Migración a nuevo proyecto GCP"
          }
        }
      ]
    }
  ]
}
```

---

### 4.2 Reporte CSV con Comentarios

```csv
definition_id,change_type,element_name,comment_type,comment_message,custom_comment
3388,task_update,Docker Push,task_update,"Registro Docker actualizado","Migración a nuevo proyecto GCP"
3388,stage_addition,Validation,stage_addition,"Nuevo stage agregado","Smoke Testing para validación"
3389,task_removal,Old Deploy,task_removal,"Task obsoleta removida","Ya no se usa en producción"
```

---

### 4.3 Reporte HTML con Comentarios

```html
<table>
  <tr>
    <th>Pipeline</th>
    <th>Cambio</th>
    <th>Elemento</th>
    <th>Tipo de Comentario</th>
    <th>Mensaje</th>
    <th>Detalle Personalizado</th>
  </tr>
  <tr>
    <td>3388</td>
    <td>Task Update</td>
    <td>Docker Push</td>
    <td>task_update</td>
    <td>Registro Docker actualizado</td>
    <td>Migración a nuevo proyecto GCP</td>
  </tr>
</table>
```

---

## 5. MEJORES PRÁCTICAS

### ✅ DO

```yaml
# Usar comentarios descriptivos
comment:
  type: "task_update"
  message: "Descripción clara del cambio"

# Agregar contexto personalizado
custom_comment: |
  Razón: Migración a nueva infraestructura
  Aprobado por: DevOps Team
  Fecha: 2026-07-13
  Contacto: devops@company.com

# Documentar reorganizaciones
comment:
  type: "stage_reorder"
  message: "Stage movido de posición 2 a 3"
```

### ❌ DON'T

```yaml
# No usar comentarios genéricos
comment:
  type: "task_update"
  message: "Cambio"

# No omitir contexto importante
custom_comment: "Cambio realizado"

# No reorganizar sin documentar
# (sin comentarios explicando por qué)
```

---

## 6. CASOS DE USO COMPLETOS

### 6.1 Migración con Documentación Completa

```yaml
metadata:
  name: "Migración a nueva infraestructura"
  version: "1.0"

search:
  stages:
    - name: "QA"
    - name: "Staging"
    - name: "Producción"
  tasks:
    - name: "Docker Push"
      type: "DockerPush"
    - name: "Deploy"
      type: "KubectlDeploy"

update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old/app"
          new_value: "gcr.io/new/app"
      comment:
        type: "task_update"
        message: "Registro Docker actualizado"
      custom_comment: |
        Migración de registro:
        - Proyecto anterior: old-project
        - Nuevo proyecto: new-project
        - Razón: Consolidación de infraestructura
        - Aprobado por: Infrastructure Team
        - Fecha: 2026-07-13
        - Contacto: infra@company.com
  
  stages:
    - name: "Validation"
      action: "add"
      position: "between"
      after_stage: "Staging"
      before_stage: "Producción"
      comment:
        type: "stage_addition"
        message: "Stage de validación agregado"
      custom_comment: |
        Nuevo stage de Smoke Testing:
        - Valida deployment antes de producción
        - Ejecuta pruebas de humo
        - Duración: 5-10 minutos
        - Responsable: QA Team
        - Inicio: 2026-07-15
      definition:
        # ... definición del stage
    
    - name: "Producción"
      fields:
        - path: "preDeployApprovals.approvals[0].approver.displayName"
          old_value: "QA Team"
          new_value: "Validation Stage"
      comment:
        type: "dependency_change"
        message: "Dependencia actualizada a nuevo stage"
      custom_comment: |
        Cambio de dependencias:
        - Aprobador anterior: QA Team
        - Nuevo aprobador: Validation Stage
        - Razón: QA ahora es un stage separado
        - Efectivo desde: 2026-07-15
```

---

**Versión**: 1.0  
**Fecha**: 2026-07-13  
**Nivel**: 📝 AUDITORÍA Y DOCUMENTACIÓN
