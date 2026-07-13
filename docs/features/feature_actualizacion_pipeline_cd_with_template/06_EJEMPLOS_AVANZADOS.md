# 🚀 Ejemplos Avanzados - Casos Complejos

## 1. BUSCAR Y CAMBIAR EN TASKS DE LÍNEA DE COMANDOS

### 1.1 PowerShell - Cambiar Variables de Entorno

**Caso**: Cambiar el ambiente de `staging` a `production` en un script PowerShell

```yaml
metadata:
  name: "Actualizar ambiente en PowerShell"
  version: "1.0"
  description: "Cambiar variables de entorno en script PowerShell"

search:
  stages:
    - name: "Staging"
    - name: "Producción"
  tasks:
    - name: "Deploy Application"
      type: "PowerShell"

update:
  tasks:
    - name: "Deploy Application"
      fields:
        # Cambiar variable en el script
        - path: "inputs.script"
          old_value: "$env:ENVIRONMENT = 'staging'"
          new_value: "$env:ENVIRONMENT = 'production'"
        
        # Cambiar número de replicas
        - path: "inputs.script"
          old_value: "$replicas = 3"
          new_value: "$replicas = 5"
        
        # Cambiar endpoint
        - path: "inputs.script"
          old_value: "$apiUrl = 'https://api-staging.company.com'"
          new_value: "$apiUrl = 'https://api-prod.company.com'"
        
        # Cambiar argumentos
        - path: "inputs.arguments"
          old_value: "-Environment staging -Verbose"
          new_value: "-Environment production -Verbose"
```

**Explicación**:
- `inputs.script`: El contenido del script PowerShell
- `inputs.arguments`: Argumentos pasados al script
- Busca cadenas exactas y las reemplaza

---

### 1.2 Bash - Actualizar Rutas y Comandos

**Caso**: Cambiar rutas de manifiestos y registros en script Bash

```yaml
metadata:
  name: "Actualizar rutas en Bash"
  version: "1.0"

search:
  stages:
    - name: "Deploy"
  tasks:
    - name: "Deploy Kubernetes"
      type: "BashScript"

update:
  tasks:
    - name: "Deploy Kubernetes"
      fields:
        # Cambiar ruta de manifiestos
        - path: "inputs.script"
          old_value: "kubectl apply -f ./manifests/old/"
          new_value: "kubectl apply -f ./manifests/new/"
        
        # Cambiar registro Docker
        - path: "inputs.script"
          old_value: "export DOCKER_REGISTRY=gcr.io/old-project"
          new_value: "export DOCKER_REGISTRY=gcr.io/new-project"
        
        # Cambiar namespace
        - path: "inputs.script"
          old_value: "kubectl set image deployment/app app=gcr.io/old-project/app:1.0 -n default"
          new_value: "kubectl set image deployment/app app=gcr.io/new-project/app:2.0 -n production"
        
        # Cambiar variable de entorno
        - path: "inputs.script"
          old_value: "export LOG_LEVEL=INFO"
          new_value: "export LOG_LEVEL=DEBUG"
```

**Explicación**:
- Busca y reemplaza comandos completos
- Útil para cambiar rutas, variables, registros
- Soporta multi-línea

---

### 1.3 Command Line - Actualizar Parámetros

**Caso**: Cambiar parámetros en comando de línea

```yaml
metadata:
  name: "Actualizar comando CLI"
  version: "1.0"

search:
  stages:
    - name: "Build"
  tasks:
    - name: "Run Build Command"
      type: "CmdLine"

update:
  tasks:
    - name: "Run Build Command"
      fields:
        # Cambiar comando completo
        - path: "inputs.script"
          old_value: "dotnet build -c Release --output ./bin/old"
          new_value: "dotnet build -c Release --output ./bin/new"
        
        # Cambiar parámetros
        - path: "inputs.script"
          old_value: "npm run build:staging"
          new_value: "npm run build:production"
```

---

## 2. CAMBIAR PROPIEDADES EN TASKS KUBECTL

### 2.1 Actualizar Conexión y Namespace

**Caso**: Migrar de un cluster GKE a otro

```yaml
metadata:
  name: "Migrar cluster Kubernetes"
  version: "1.0"
  description: "Cambiar conexión y namespace en KubectlDeploy"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Deploy with Kubectl"
      type: "KubectlDeploy"

update:
  tasks:
    - name: "Deploy with Kubectl"
      fields:
        # Cambiar conexión al cluster
        - path: "inputs.kubernetesServiceConnection"
          old_value: "gke-old-cluster"
          new_value: "gke-new-cluster"
        
        # Cambiar namespace
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"
        
        # Cambiar manifiestos
        - path: "inputs.manifests"
          old_value: "k8s/old-manifests/*.yaml"
          new_value: "k8s/new-manifests/*.yaml"
        
        # Cambiar estrategia de deploy
        - path: "inputs.strategy"
          old_value: "canary"
          new_value: "rolling"
        
        # Cambiar timeout
        - path: "inputs.rolloutStatusTimeout"
          old_value: "300"
          new_value: "600"
```

**Propiedades comunes de KubectlDeploy**:
- `kubernetesServiceConnection`: Conexión al cluster
- `namespace`: Namespace K8s
- `manifests`: Ruta de manifiestos
- `strategy`: Estrategia de deploy (canary, rolling, blue-green)
- `rolloutStatusTimeout`: Timeout en segundos

---

### 2.2 Cambiar Configuración de Secrets y ConfigMaps

```yaml
metadata:
  name: "Actualizar secrets en Kubectl"
  version: "1.0"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Deploy with Kubectl"
      type: "KubectlDeploy"

update:
  tasks:
    - name: "Deploy with Kubectl"
      fields:
        # Cambiar secret a usar
        - path: "inputs.secretsFilePath"
          old_value: "k8s/secrets/old-secrets.yaml"
          new_value: "k8s/secrets/new-secrets.yaml"
        
        # Cambiar configmap
        - path: "inputs.configMapFilePath"
          old_value: "k8s/config/old-config.yaml"
          new_value: "k8s/config/new-config.yaml"
```

---

### 2.3 Cambiar Imagen en Deployment

```yaml
metadata:
  name: "Actualizar imagen en Kubectl"
  version: "1.0"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Deploy with Kubectl"
      type: "KubectlDeploy"

update:
  tasks:
    - name: "Deploy with Kubectl"
      fields:
        # Cambiar imagen en el manifesto
        - path: "inputs.manifests"
          old_value: "image: gcr.io/old-project/app:1.0"
          new_value: "image: gcr.io/new-project/app:2.0"
        
        # O cambiar parámetro de imagen
        - path: "inputs.imageNameOverride"
          old_value: "gcr.io/old-project/app:1.0"
          new_value: "gcr.io/new-project/app:2.0"
```

---

## 3. ELIMINAR UNA TASK

### 3.1 Eliminar Task Obsoleta

**Caso**: Remover una task que ya no se usa

```yaml
metadata:
  name: "Eliminar task obsoleta"
  version: "1.0"
  description: "Remover Azure App Service Deploy que fue reemplazado por Kubectl"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Deploy to App Service"
      type: "AzureAppServiceDeploy"

update:
  tasks:
    - name: "Deploy to App Service"
      action: "remove"
```

**Explicación**:
- `action: "remove"` elimina la task
- Se busca por nombre y tipo
- Útil para limpiar pipelines

---

### 3.2 Eliminar Múltiples Tasks

```yaml
metadata:
  name: "Limpiar tasks obsoletas"
  version: "1.0"

search:
  stages:
    - name: "QA"
    - name: "Staging"
  tasks:
    - name: "Old Test Task"
      type: "VSTest"
    - name: "Legacy Deploy"
      type: "AzureAppServiceDeploy"
    - name: "Deprecated Validation"
      type: "PowerShell"

update:
  tasks:
    - name: "Old Test Task"
      action: "remove"
    
    - name: "Legacy Deploy"
      action: "remove"
    
    - name: "Deprecated Validation"
      action: "remove"
```

---

## 4. AGREGAR UNA NUEVA TASK

### 4.1 Agregar Task de Validación

**Caso**: Agregar health check después del deploy

```yaml
metadata:
  name: "Agregar validación de salud"
  version: "1.0"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Deploy with Kubectl"
      type: "KubectlDeploy"

update:
  tasks:
    # Agregar nueva task DESPUÉS de Kubectl
    - name: "Health Check"
      action: "add"
      position: "after"
      reference_task: "Deploy with Kubectl"
      definition:
        displayName: "Health Check"
        enabled: true
        task:
          id: "6C731787-BC2C-4436-8290-A81493FFEA35"  # BashScript
          versionSpec: "3.*"
        inputs:
          script: |
            #!/bin/bash
            echo "Checking deployment health..."
            
            # Esperar a que los pods estén listos
            kubectl wait --for=condition=ready pod -l app=myapp -n production --timeout=300s
            
            # Verificar servicios
            kubectl get services -n production
            
            # Hacer health check
            curl -f https://api.production.com/health || exit 1
            
            echo "Health check passed!"
```

**Propiedades**:
- `position`: "before", "after", "first", "last"
- `reference_task`: Task de referencia (si position es "before" o "after")
- `definition`: Definición completa de la task

---

### 4.2 Agregar Task de Notificación

```yaml
metadata:
  name: "Agregar notificación de deploy"
  version: "1.0"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Deploy with Kubectl"
      type: "KubectlDeploy"

update:
  tasks:
    - name: "Send Notification"
      action: "add"
      position: "after"
      reference_task: "Deploy with Kubectl"
      definition:
        displayName: "Notify Slack"
        enabled: true
        task:
          id: "71575882-25B1-4E65-99C6-C32C4B46A14A"  # Slack Notification
          versionSpec: "0.*"
        inputs:
          webhookUrl: "$(SlackWebhook)"
          message: "Deployment to production completed successfully"
          color: "good"
```

---

### 4.3 Agregar Task de Rollback

```yaml
metadata:
  name: "Agregar rollback automático"
  version: "1.0"

search:
  stages:
    - name: "Producción"
  tasks:
    - name: "Deploy with Kubectl"
      type: "KubectlDeploy"

update:
  tasks:
    - name: "Rollback on Failure"
      action: "add"
      position: "after"
      reference_task: "Health Check"
      definition:
        displayName: "Rollback Deployment"
        enabled: true
        continueOnError: true
        task:
          id: "6C731787-BC2C-4436-8290-A81493FFEA35"  # BashScript
          versionSpec: "3.*"
        inputs:
          script: |
            #!/bin/bash
            if [ $? -ne 0 ]; then
              echo "Deployment failed, rolling back..."
              kubectl rollout undo deployment/myapp -n production
              exit 1
            fi
```

---

## 5. AGREGAR UN STAGE COMPLETO

### 5.1 Agregar Stage de Smoke Testing

**Caso**: Agregar stage de validación entre Staging y Producción

```yaml
metadata:
  name: "Agregar stage de Smoke Testing"
  version: "2.0"
  description: "Nuevo stage que valida deployment antes de producción"

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
      definition:
        id: 3
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
                      
                      # Test API endpoints
                      curl -f https://api.production.com/health
                      curl -f https://api.production.com/version
                      
                      # Test web endpoints
                      curl -f https://web.production.com/
                      curl -f https://web.production.com/login
                      
                      # Test database connectivity
                      curl -f https://api.production.com/db-check
                      
                      echo "All smoke tests passed!"
        
        # Pre-deployment: Aprobación automática de Staging
        preDeployApprovals:
          approvals:
            - rank: 1
              isAutomated: true
              isNotificationOn: false
              approver:
                displayName: "Automated"
        
        # Post-deployment: Sin aprobaciones adicionales
        postDeployApprovals:
          approvals: []
```

---

### 5.2 Agregar Stage con Aprobación Manual

```yaml
metadata:
  name: "Agregar stage de aprobación"
  version: "1.0"

search:
  stages:
    - name: "Staging"
    - name: "Producción"

update:
  stages:
    - name: "Approval Gate"
      action: "add"
      position: "between"
      after_stage: "Staging"
      before_stage: "Producción"
      definition:
        id: 3
        name: "Approval Gate"
        rank: 2
        deployPhases:
          - id: 1
            name: "Manual Approval"
            deploymentInput:
              tasks:
                - displayName: "Wait for Approval"
                  enabled: true
                  task:
                    id: "E8B84330-3B1B-11E5-8612-FB35E6C3CE77"  # Manual Intervention
                    versionSpec: "0.*"
                  inputs:
                    notifyUsers: "devops@company.com"
                    instructions: "Please review and approve deployment to production"
        
        # Requiere aprobación manual
        preDeployApprovals:
          approvals:
            - rank: 1
              isAutomated: false
              isNotificationOn: true
              approver:
                displayName: "DevOps Team"
              timeoutInMinutes: 1440  # 24 horas
```

---

## 6. CONFIGURAR DEPENDENCIAS ENTRE STAGES

### 6.1 Hacer que un Stage Dependa de Otro

**Caso**: Cambiar que Producción dependa de Smoke Testing en lugar de Staging

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
        # Cambiar aprobador previo (dependencia)
        - path: "preDeployApprovals.approvals[0].approver.displayName"
          old_value: "Staging"
          new_value: "Smoke Testing"
        
        # Cambiar timeout de aprobación
        - path: "preDeployApprovals.approvals[0].timeoutInMinutes"
          old_value: "60"
          new_value: "120"
        
        # Cambiar si es automático o manual
        - path: "preDeployApprovals.approvals[0].isAutomated"
          old_value: "false"
          new_value: "true"
```

---

### 6.2 Agregar Aprobadores Adicionales

```yaml
metadata:
  name: "Agregar aprobadores a stage"
  version: "1.0"

search:
  stages:
    - name: "Producción"

update:
  stages:
    - name: "Producción"
      fields:
        # Agregar segundo aprobador
        - path: "preDeployApprovals.approvals"
          action: "add"
          definition:
            - rank: 1
              isAutomated: false
              isNotificationOn: true
              approver:
                displayName: "DevOps Lead"
              timeoutInMinutes: 1440
            
            - rank: 2
              isAutomated: false
              isNotificationOn: true
              approver:
                displayName: "Security Team"
              timeoutInMinutes: 1440
```

---

## 7. EJEMPLO COMPLETO: MIGRACIÓN INTEGRAL

**Caso**: Migración completa de infraestructura con nuevo stage

```yaml
metadata:
  name: "Migración integral de infraestructura"
  version: "3.0"
  description: "Cambiar imagen, cluster K8s, agregar validación y actualizar dependencias"

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
    - name: "Old App Service Deploy"
      type: "AzureAppServiceDeploy"
    - name: "Run Tests"
      type: "VSTest"

update:
  # 1. ELIMINAR TASKS OBSOLETAS
  tasks:
    - name: "Old App Service Deploy"
      action: "remove"
    
    # 2. ACTUALIZAR DOCKER PUSH
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old-project/app"
          new_value: "gcr.io/new-project/app"
        - path: "inputs.containerRegistryType"
          old_value: "Container Registry"
          new_value: "Azure Container Registry"
    
    # 3. ACTUALIZAR KUBECTL
    - name: "Deploy with Kubectl"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "gke-old"
          new_value: "gke-new"
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"
        - path: "inputs.manifests"
          old_value: "k8s/old/"
          new_value: "k8s/new/"
    
    # 4. AGREGAR HEALTH CHECK
    - name: "Health Check"
      action: "add"
      position: "after"
      reference_task: "Deploy with Kubectl"
      definition:
        displayName: "Health Check"
        enabled: true
        task:
          id: "6C731787-BC2C-4436-8290-A81493FFEA35"
          versionSpec: "3.*"
        inputs:
          script: |
            #!/bin/bash
            kubectl wait --for=condition=ready pod -l app=myapp -n production --timeout=300s
            curl -f https://api.production.com/health
  
  # 5. AGREGAR STAGE DE VALIDACIÓN
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
            name: "Smoke Tests"
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
        preDeployApprovals:
          approvals:
            - rank: 1
              isAutomated: true
              approver:
                displayName: "Automated"
    
    # 6. ACTUALIZAR DEPENDENCIAS DE PRODUCCIÓN
    - name: "Producción"
      fields:
        - path: "preDeployApprovals.approvals[0].approver.displayName"
          old_value: "Staging"
          new_value: "Validation"

options:
  dry_run: false
  rollback_on_error: true
  parallel_workers: 5
```

---

**Versión**: 1.0  
**Fecha**: 2026-07-13  
**Nivel**: 🚀 AVANZADO
