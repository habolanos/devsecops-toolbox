# 💡 Ejemplos Prácticos - Casos Reales

## 1. EJEMPLO 1: Actualizar Imagen Docker

### Caso de Uso
Cambiar la imagen Docker en 50 pipelines de producción de `gcr.io/coppel-old/app:1.0.0` a `gcr.io/coppel-new/app:2.0.0`.

### Template: `update_docker_image.yaml`

```yaml
metadata:
  name: "Actualizar imagen Docker a v2.0.0"
  version: "1.0"
  description: "Cambiar imagen Docker en todos los pipelines de producción"
  author: "DevOps Team"
  created: "2026-07-13"

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
          old_value: "1.0.0"
          new_value: "2.0.0"

options:
  dry_run: false
  rollback_on_error: true
  parallel_workers: 5
  timeout_per_pipeline: 30
```

### Ejecución

```bash
# 1. Obtener IDs de pipelines
python scm/azdo/tools.py
# Seleccionar: 15 (CD Detailed Inventory)
# Filtrar por "Producción"
# Copiar IDs: 3388,3389,3390,...

# 2. Crear template
cat > templates/update_docker_image.yaml << 'EOF'
[contenido del template arriba]
EOF

# 3. Ejecutar actualización
python scm/main.py
# Seleccionar: 1 (AZDO)
# Seleccionar: 41 (Pipeline Updater Template)
# Ingresar: --definition-ids "3388,3389,3390,..." --template templates/update_docker_image.yaml

# O directamente:
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "3388,3389,3390,3391,3392" \
  --template templates/update_docker_image.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros"
```

### Salida Esperada

```
╔════════════════════════════════════════════════════════════════╗
║              Pipeline Updater - Análisis Previo                ║
╚════════════════════════════════════════════════════════════════╝

Template: update_docker_image.yaml
Pipelines a actualizar: 5
Cambios por pipeline: 2

PREVIEW DE CAMBIOS:
┌─────────────────────────────────────────────────────────────┐
│ Pipeline 3388 - "Deploy Web App"                            │
│                                                             │
│ Task: Docker Push                                           │
│   • inputs.imageRepository                                  │
│     OLD: gcr.io/coppel-old/app                             │
│     NEW: gcr.io/coppel-new/app                             │
│   • inputs.tag                                              │
│     OLD: 1.0.0                                              │
│     NEW: 2.0.0                                              │
└─────────────────────────────────────────────────────────────┘

[Similar para pipelines 3389, 3390, 3391, 3392]

¿Continuar con la actualización? (s/n): s

╔════════════════════════════════════════════════════════════════╗
║                    Ejecutando Actualización                    ║
╚════════════════════════════════════════════════════════════════╝

⚙️  Pipeline 3388 - Deploy Web App ... ✓ (2 cambios)
⚙️  Pipeline 3389 - Deploy API ... ✓ (2 cambios)
⚙️  Pipeline 3390 - Deploy Worker ... ✓ (2 cambios)
⚙️  Pipeline 3391 - Deploy Cache ... ✓ (2 cambios)
⚙️  Pipeline 3392 - Deploy Queue ... ✓ (2 cambios)

╔════════════════════════════════════════════════════════════════╗
║                      Resumen de Ejecución                      ║
╚════════════════════════════════════════════════════════════════╝

✓ Exitosos: 5
✗ Errores: 0
📊 Cambios totales: 10
⏱️  Duración: 3.2 segundos
💾 Snapshots: 5 (disponibles para rollback)

Reportes generados:
  • outcome/pipeline_updates/report.json
  • outcome/pipeline_updates/report.csv
  • outcome/pipeline_updates/report.html
```

### Reporte JSON

```json
{
  "timestamp": "2026-07-13T14:30:00Z",
  "summary": {
    "total": 5,
    "success": 5,
    "failed": 0
  },
  "details": [
    {
      "definition_id": 3388,
      "success": true,
      "snapshot_id": "snapshot_3388_1689254400",
      "matches_found": 1,
      "changes_applied": 2,
      "changes": [
        {
          "type": "task_field",
          "task": "Docker Push",
          "field": "inputs.imageRepository",
          "old": "gcr.io/coppel-old/app",
          "new": "gcr.io/coppel-new/app"
        },
        {
          "type": "task_field",
          "task": "Docker Push",
          "field": "inputs.tag",
          "old": "1.0.0",
          "new": "2.0.0"
        }
      ]
    }
  ],
  "errors": []
}
```

---

## 2. EJEMPLO 2: Actualizar Variables de Entorno

### Caso de Uso
Cambiar variables de entorno en 10 pipelines de QA de `staging` a `qa-final`.

### Template: `update_environment_variables.yaml`

```yaml
metadata:
  name: "Actualizar variables de entorno QA"
  version: "1.0"
  description: "Cambiar ENVIRONMENT de staging a qa-final"

search:
  stages:
    - name: "QA"
  variables:
    - name: "ENVIRONMENT"
    - name: "LOG_LEVEL"

update:
  variables:
    - name: "ENVIRONMENT"
      old_value: "staging"
      new_value: "qa-final"
    - name: "LOG_LEVEL"
      old_value: "INFO"
      new_value: "DEBUG"

options:
  dry_run: true  # Primero en dry-run
  rollback_on_error: true
```

### Ejecución

```bash
# Primero: Dry-run para ver cambios
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "3400,3401,3402,3403,3404,3405,3406,3407,3408,3409" \
  --template templates/update_environment_variables.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --dry-run

# Si todo está bien, ejecutar sin dry-run
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "3400,3401,3402,3403,3404,3405,3406,3407,3408,3409" \
  --template templates/update_environment_variables.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros"
```

### Salida

```
✓ Exitosos: 10
✗ Errores: 0
📊 Cambios totales: 20 (2 variables × 10 pipelines)
⏱️  Duración: 2.1 segundos
```

---

## 3. EJEMPLO 3: Actualizar Conexión Kubernetes

### Caso de Uso
Cambiar conexión de Kubernetes de `old-gke-cluster` a `new-gke-cluster` en 15 pipelines de producción.

### Template: `update_k8s_connection.yaml`

```yaml
metadata:
  name: "Actualizar conexión Kubernetes"
  version: "1.0"
  description: "Cambiar cluster de GKE en pipelines de producción"

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
        - path: "inputs.strategy"
          old_value: "canary"
          new_value: "rolling"

options:
  dry_run: false
  rollback_on_error: true
  parallel_workers: 3
  timeout_per_pipeline: 45
```

### Ejecución

```bash
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "3500,3501,3502,3503,3504,3505,3506,3507,3508,3509,3510,3511,3512,3513,3514" \
  --template templates/update_k8s_connection.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros"
```

---

## 4. EJEMPLO 4: Actualización Compleja (Multi-stage, Multi-task)

### Caso de Uso
Migración completa de infraestructura:
- Cambiar imagen Docker
- Actualizar conexión K8s
- Cambiar variables de entorno
- Actualizar aprobadores

### Template: `complete_migration.yaml`

```yaml
metadata:
  name: "Migración completa de infraestructura"
  version: "2.0"
  description: "Actualiza imagen, K8s, variables y aprobadores"

search:
  stages:
    - name: "QA"
    - name: "Staging"
    - name: "Producción"
  tasks:
    - name: "Docker Push"
      type: "DockerPush"
    - name: "Deploy to Kubernetes"
      type: "KubernetesManifest"
  variables:
    - name: "IMAGE_REPOSITORY"
    - name: "ENVIRONMENT"
    - name: "K8S_CLUSTER"
    - name: "REPLICAS"

update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          old_value: "gcr.io/old-project/app"
          new_value: "gcr.io/new-project/app"
        - path: "inputs.containerRegistryType"
          old_value: "Container Registry"
          new_value: "Azure Container Registry"
    - name: "Deploy to Kubernetes"
      fields:
        - path: "inputs.kubernetesServiceConnection"
          old_value: "gke-old"
          new_value: "gke-new"
        - path: "inputs.namespace"
          old_value: "default"
          new_value: "production"
  variables:
    - name: "IMAGE_REPOSITORY"
      old_value: "gcr.io/old-project/app"
      new_value: "gcr.io/new-project/app"
    - name: "ENVIRONMENT"
      old_value: "old-env"
      new_value: "new-env"
    - name: "K8S_CLUSTER"
      old_value: "gke-old"
      new_value: "gke-new"
    - name: "REPLICAS"
      old_value: "3"
      new_value: "5"

options:
  dry_run: false
  rollback_on_error: true
  parallel_workers: 5
  timeout_per_pipeline: 60
  stop_on_first_error: false
```

### Ejecución

```bash
# Obtener todos los IDs de pipelines
PIPELINE_IDS=$(python scm/azdo/tools.py --list-all-pipelines | grep -E "^\d+" | cut -d' ' -f1 | paste -sd ',' -)

# Ejecutar
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --definition-ids "$PIPELINE_IDS" \
  --template templates/complete_migration.yaml \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros"
```

---

## 5. EJEMPLO 5: Rollback Automático

### Escenario
Se ejecutó una actualización pero algo salió mal. Usar rollback automático.

### Comando de Rollback

```bash
# Ver snapshots disponibles
ls -la outcome/snapshots/

# Rollback manual de un pipeline específico
python scm/azdo/pipeline-updater/pipeline_updater.py \
  --rollback \
  --definition-id 3388 \
  --snapshot-id "snapshot_3388_1689254400" \
  --pat "$AZDO_PAT" \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros"
```

### Salida

```
╔════════════════════════════════════════════════════════════════╗
║                    Ejecutando Rollback                         ║
╚════════════════════════════════════════════════════════════════╝

Restaurando snapshot: snapshot_3388_1689254400
Pipeline: 3388 - Deploy Web App

✓ Rollback completado exitosamente
  • Cambios revertidos: 2
  • Duración: 1.2 segundos
```

---

## 6. EJEMPLO 6: Validación de Template

### Comando

```bash
# Validar template antes de ejecutar
python scm/azdo/pipeline-updater/template_validator.py \
  --template templates/update_docker_image.yaml
```

### Salida Válida

```
✓ Template válido
  • Metadata: OK
  • Search rules: OK
  • Update rules: OK
  • Options: OK

Resumen:
  • Stages a buscar: 1 (Producción)
  • Tasks a buscar: 1 (Docker Push)
  • Variables a buscar: 0
  • Cambios a aplicar: 2
```

### Salida Inválida

```
✗ Template inválido

Errores encontrados:
  1. metadata.name es obligatorio
  2. search.stages está vacío
  3. update.tasks[0].fields[0].old_value no coincide con valor actual

Por favor, corrija los errores y vuelva a intentar.
```

---

## 7. COMPARATIVA: Manual vs Template

### Actualizar 50 pipelines manualmente

```
Tiempo: 50 × 3 minutos = 150 minutos (2.5 horas)
Errores: ~25% (12-13 pipelines con errores)
Reversión: Otro 2.5 horas
Auditoría: Manual, incompleta
Total: 5+ horas
```

### Actualizar 50 pipelines con template

```
Tiempo: 5 min (setup) + 2 min (ejecución) = 7 minutos
Errores: 0% (validación automática)
Reversión: 30 segundos (rollback automático)
Auditoría: Automática, completa
Total: 7 minutos
```

**Mejora**: 43x más rápido, 0% errores, auditoría completa

---

## 8. MEJORES PRÁCTICAS

### ✅ DO

1. **Usar dry-run primero**
   ```bash
   --dry-run  # Simular antes de aplicar
   ```

2. **Validar templates**
   ```bash
   template_validator.py --template template.yaml
   ```

3. **Usar snapshots**
   ```yaml
   options:
     rollback_on_error: true
   ```

4. **Documentar cambios**
   ```yaml
   metadata:
     description: "Descripción clara de qué cambia"
   ```

5. **Versionar templates**
   ```yaml
   metadata:
     version: "1.0"  # Incrementar con cambios
   ```

### ❌ DON'T

1. **No usar sin validación**
   ```bash
   # ❌ Evitar
   --definition-ids "3388,3389,3390" --template template.yaml
   
   # ✅ Hacer
   --dry-run --definition-ids "3388,3389,3390" --template template.yaml
   ```

2. **No cambiar valores sin validación**
   ```yaml
   # ❌ Evitar
   update:
     variables:
       - name: "DOCKER_TAG"
         new_value: "2.0.0"  # Sin old_value
   
   # ✅ Hacer
   update:
     variables:
       - name: "DOCKER_TAG"
         old_value: "1.0.0"
         new_value: "2.0.0"
   ```

3. **No ejecutar sin snapshots**
   ```yaml
   # ❌ Evitar
   options:
     rollback_on_error: false
   
   # ✅ Hacer
   options:
     rollback_on_error: true
   ```

---

**Versión**: 1.0  
**Fecha**: 2026-07-13
