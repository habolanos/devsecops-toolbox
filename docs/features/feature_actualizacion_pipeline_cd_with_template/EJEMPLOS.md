# 📚 Ejemplos Prácticos

## Caso 1: Cambiar Imagen Docker

**Escenario**: Actualizar imagen Docker en 50 pipelines de producción

**Template:**
```yaml
metadata:
  name: "Actualizar imagen Docker"
  version: "1.0"
  comment: |
    Cambios: myapp:v1.5 → myapp:v2.0
    Razón: Bugfix crítico de seguridad
    Aprobado por: Security Team
    Fecha: 2026-07-13

search:
  stages: ["Producción"]
  tasks:
    - name: "Push Docker"
    # type: "Docker"              # Opcional

update:
  tasks:
    - name: "Push Docker"
      fields:
        - path: "inputs.repository"
          old_value: "myapp:v1.5"
          new_value: "myapp:v2.0"
```

**Ejecución:**
```
Pipelines encontrados: 50
Cambios a aplicar: 50
Tiempo estimado: 30 segundos
¿Continuar? Y
✅ 50 pipelines actualizados
```

---

## Caso 2: Cambiar Cluster Kubernetes

**Escenario**: Migrar de GKE old-cluster a new-cluster

**Template:**
```yaml
metadata:
  name: "Migrar a nuevo cluster GKE"
  version: "1.0"
  comment: |
    Cambios: old-gke-cluster → new-gke-cluster
    Región: us-central1 → us-east1
    Razón: Mejora de latencia
    Aprobado por: Infrastructure Team

search:
  stages: ["Producción", "Staging"]
  tasks:
    - name: "Deploy"
    # type: "KubectlDeploy"       # Opcional

update:
  tasks:
    - name: "Deploy"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "old-gke-cluster"
          new_value: "new-gke-cluster"
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"
```

---

## Caso 3: Actualizar Variables de Entorno

**Escenario**: Cambiar ambiente de staging a production en 30 pipelines

**Template:**
```yaml
metadata:
  name: "Cambiar ambiente a production"
  version: "1.0"
  comment: |
    Cambios: ENVIRONMENT staging → production
    Razón: Promoción a producción
    Aprobado por: DevOps Lead

search:
  variables:
    - name: "ENVIRONMENT"

update:
  variables:
    - name: "ENVIRONMENT"
      old_value: "staging"
      new_value: "production"
```

---

## Caso 4: Cambiar Conexión Azure

**Escenario**: Cambiar suscripción Azure en pipelines

**Template:**
```yaml
metadata:
  name: "Cambiar suscripción Azure"
  version: "1.0"
  comment: |
    Cambios: old-subscription → new-subscription
    Razón: Consolidación de suscripciones
    Aprobado por: Cloud Ops Team

search:
  stages: ["Deploy"]
  tasks:
    - name: "Deploy"
    # type: "AzureCLI"            # Opcional

update:
  tasks:
    - name: "Deploy"
      fields:
        - path: "inputs.azureSubscription"
          old_value: "old-subscription"
          new_value: "new-subscription"
```

---

## Caso 5: Cambiar Script PowerShell

**Escenario**: Actualizar URL de base de datos en script

**Template:**
```yaml
metadata:
  name: "Actualizar conexión BD"
  version: "1.0"
  comment: |
    Cambios: old-db.company.com → new-db.company.com
    Puerto: 5432 → 5433
    Razón: Migración a nuevo servidor
    Aprobado por: Database Team

search:
  stages: ["Staging", "Producción"]
  tasks:
    - name: "Initialize Database"
    # type: "PowerShell"          # Opcional

update:
  tasks:
    - name: "Initialize Database"
      fields:
        - path: "inputs.script"
          old_value: "Server=old-db.company.com;Port=5432"
          new_value: "Server=new-db.company.com;Port=5433"
        - path: "inputs.script"
          old_value: "User=dbuser_old"
          new_value: "User=dbuser_new"
```

---

## Caso 6: Reorganizar Stages

**Escenario**: Cambiar orden de stages en pipeline

**Template:**
```yaml
metadata:
  name: "Reorganizar stages"
  version: "1.0"
  comment: |
    Nuevo orden: Deploy → Test → Build
    Razón: Optimizar pipeline
    Aprobado por: DevOps Team

search:
  stages: ["Build", "Test", "Deploy"]

update:
  stages:
    - name: "Deploy"
      rank: 1
    - name: "Test"
      rank: 2
    - name: "Build"
      rank: 3
```

---

## Caso 7: Múltiples Cambios Simultáneos

**Escenario**: Migración completa (imagen, cluster, variables)

**Template:**
```yaml
metadata:
  name: "Migración completa a v2.0"
  version: "1.0"
  comment: |
    Cambios:
    - Imagen: myapp:v1.0 → myapp:v2.0
    - Cluster: old-gke → new-gke
    - Ambiente: staging → production
    Razón: Lanzamiento de v2.0
    Aprobado por: Release Manager

search:
  stages: ["Producción"]
  tasks:
    - name: "Push Docker"
    # type: "Docker"              # Opcional
    - name: "Deploy"
    # type: "KubectlDeploy"       # Opcional
  variables:
    - name: "ENVIRONMENT"

update:
  tasks:
    - name: "Push Docker"
      fields:
        - path: "inputs.repository"
          old_value: "myapp:v1.0"
          new_value: "myapp:v2.0"
    - name: "Deploy"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "old-gke"
          new_value: "new-gke"
  variables:
    - name: "ENVIRONMENT"
      old_value: "staging"
      new_value: "production"
```

---

## Caso 8: Cambio Selectivo por Stage

**Escenario**: Cambiar solo en stage de producción, no en staging

**Template:**
```yaml
metadata:
  name: "Cambiar solo en producción"
  version: "1.0"
  comment: "Actualizar imagen solo en producción"

search:
  stages: ["Producción"]    # Solo buscar en Producción
  tasks:
    - name: "Push Docker"
    # type: "Docker"              # Opcional

update:
  tasks:
    - name: "Push Docker"
      fields:
        - path: "inputs.repository"
          old_value: "myapp:v1.0"
          new_value: "myapp:v2.0"
```

---

## Caso 9: Cambio Selectivo por Tipo de Task

**Escenario**: Cambiar solo en tasks de Kubernetes, no en Docker

**Template:**
```yaml
metadata:
  name: "Cambiar solo Kubernetes"
  version: "1.0"
  comment: "Actualizar namespace solo en KubectlDeploy"

search:
  tasks:
    - name: "Deploy"
    # type: "KubectlDeploy"       # Opcional (solo este tipo)

update:
  tasks:
    - name: "Deploy"
      fields:
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"
```

---

## Caso 10: Cambio Selectivo por Nombre

**Escenario**: Cambiar solo en task específica

**Template:**
```yaml
metadata:
  name: "Cambiar task específica"
  version: "1.0"
  comment: "Cambiar solo en 'Deploy Production'"

search:
  tasks:
    - name: "Deploy Production"   # Nombre exacto

update:
  tasks:
    - name: "Deploy Production"
      fields:
        - path: "inputs.image"
          old_value: "v1.0"
          new_value: "v2.0"
```

---

## Cómo Usar Estos Ejemplos

1. **Copiar template** del ejemplo que aplique
2. **Ajustar valores** según tu caso
3. **Guardar como archivo** (ej: cambiar-docker.yaml)
4. **Ejecutar en Tool 21** (Pipeline Updater)
5. **Confirmar cambios** cuando se solicite
6. **Revisar reporte** de cambios aplicados

---

## Validación Antes de Ejecutar

```bash
# Opción 1: Dry-run (simular sin cambios)
options:
  dry_run: true

# Opción 2: Revisar reporte
# El tool muestra cambios antes de confirmar
```

---

## Rollback si Algo Falla

```bash
# Automático: Si falla, revierte automáticamente
# Manual: Usar Tool 22 (Pipeline Rollback)
```

---

**Versión**: 1.0  
**Última actualización**: 2026-07-13
