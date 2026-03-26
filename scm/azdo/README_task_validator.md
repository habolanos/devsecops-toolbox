# Azure DevOps Task Validator

Herramienta DevSecOps para validación de releases en Azure DevOps, implementando controles de seguridad y verificación de integridad.

## 📋 Descripción

Este validador realiza 4 funciones principales:

| # | Función | Descripción |
|---|---------|-------------|
| 1 | **Validación de Imágenes** | Verifica existencia de imágenes Docker en Harbor/Artifact Registry |
| 2 | **Búsqueda de Rollback** | Encuentra releases anteriores por TAG para rollback |
| 3 | **Validación de Credenciales** | Compara fechas de vigencia de credenciales GIT |
| 4 | **Comparación ConfigMap** | Compara configuración K8s vs repositorio Git |

---

## 🚀 Uso Rápido

```bash
# Ejecutar todas las validaciones
python azdo_task_validator.py --all \
    --pat "$PAT" \
    --org "mi-org" \
    --project "mi-proyecto" \
    --release-id 123

# Solo validar imágenes
python azdo_task_validator.py --validate-images \
    --image-actual "us-docker.pkg.dev/proj/repo/img:v1.0" \
    --image-nueva "us-docker.pkg.dev/proj/repo/img:v1.1"

# Solo buscar release rollback
python azdo_task_validator.py --find-rollback \
    --release-id 123 \
    --tag "v1.0.0"

# Solo validar credenciales
python azdo_task_validator.py --validate-credentials \
    --group-id 456 \
    --rollback-release-id 789

# Solo comparar ConfigMap
python azdo_task_validator.py --compare-configmap \
    --artifact-name "mi-servicio" \
    --namespace "prod"
```

---

## ⚙️ Parámetros

### Azure DevOps (Requeridos)

| Parámetro | Env Variable | Descripción |
|-----------|--------------|-------------|
| `--pat` | `PAT` | Personal Access Token |
| `--org` | `ORG_NAME` | Nombre de la organización |
| `--project` | `PROJECT_NAME` | Nombre del proyecto |
| `--release-id` | `ACTUAL_RELEASE_ID` | ID del release actual |
| `--api-version` | `API_VERSION` | Versión de API (default: 7.1) |

### Validación de Imágenes

| Parámetro | Env Variable | Descripción |
|-----------|--------------|-------------|
| `--image-actual` | `IMAGE_ACTUAL` | Imagen actualmente desplegada |
| `--image-nueva` | `IMAGE_NUEVA` | Nueva imagen a desplegar |
| `--gcp-project` | `GCP_PROJECT_ID` | Proyecto GCP para auth |
| `--sa-key-file` | `SA_KEY_FILE` | Archivo de Service Account |

### Búsqueda de Rollback

| Parámetro | Env Variable | Descripción |
|-----------|--------------|-------------|
| `--tag` | - | TAG a buscar en releases anteriores |
| `--rollback-release-id` | - | ID del release rollback (si ya se conoce) |

### Validación de Credenciales

| Parámetro | Env Variable | Descripción |
|-----------|--------------|-------------|
| `--group-id` | `GROUP_ID` | ID del Variable Group de credenciales |

### Comparación ConfigMap

| Parámetro | Env Variable | Descripción |
|-----------|--------------|-------------|
| `--artifact-name` | `ARTIFACT_NAME` | Nombre del servicio/artefacto |
| `--namespace` | `ARTIFACT_NAMESPACE` | Namespace de Kubernetes |
| `--repo-name` | `REPO_NAME` | Nombre del repositorio (default: properties) |
| `--branch` | `BRANCH` | Rama del repositorio (default: master) |

### Opciones Generales

| Parámetro | Descripción |
|-----------|-------------|
| `--all` | Ejecuta todas las validaciones |
| `--validate-images` | Solo validación de imágenes |
| `--find-rollback` | Solo búsqueda de rollback |
| `--validate-credentials` | Solo validación de credenciales |
| `--compare-configmap` | Solo comparación de ConfigMap |
| `--debug` | Modo debug con logs detallados |
| `--output json\|csv` | Exporta resultados a archivo |
| `--help-full` | Muestra esta documentación |

---

## 🔧 Variables de Azure DevOps

El script establece las siguientes variables durante la ejecución:

| Variable | Descripción |
|----------|-------------|
| `TAG_ACTUAL` | TAG extraído de la imagen actual |
| `RELEASE_ID_RB` | ID del release de rollback encontrado |
| `MatchedCommitIdJob` | Commit ID que coincide con el ConfigMap |
| `ShouldRollbackJob` | `true` o `false` según si se encontró coincidencia |

---

## 📦 Requisitos

### Python
- Python 3.8+
- requests
- rich (opcional, para UI mejorada)
- PyYAML (opcional, para mejor parsing)

```bash
pip install requests rich pyyaml
```

### Herramientas externas (según uso)
- `gcloud` - Para validación de imágenes en Artifact Registry
- `crane` - Para validación de imágenes en Harbor
- `kubectl` - Para obtener ConfigMaps de Kubernetes

---

## 🔐 Permisos Requeridos

### Azure DevOps PAT
- **Release** - Read, Write, Execute
- **Build** - Read
- **Variable Groups** - Read
- **Code** - Read

### GCP (para validación de imágenes)
- `artifactregistry.repositories.get`
- `artifactregistry.dockerimages.get`
- `storage.objects.get` (si usa GCR)

### Kubernetes (para comparación ConfigMap)
- `get configmaps` en el namespace especificado

---

## 📊 Ejemplo de Salida

```
╔══════════════════════════════════════════════════════════════╗
║              Azure DevOps Task Validator                      ║
╚══════════════════════════════════════════════════════════════╝
✓ [2024-01-15T10:30:00] Organización: mi-org
✓ [2024-01-15T10:30:00] Proyecto: mi-proyecto

════════════════════════════════════════════════════════════════
  1) Validar imágenes
════════════════════════════════════════════════════════════════
✓ [2024-01-15T10:30:01] Validando existencia: us-docker.pkg.dev/.../img:v1.0
✓ [2024-01-15T10:30:02] OK: imagen existe
✓ [2024-01-15T10:30:02] Validando existencia: us-docker.pkg.dev/.../img:v1.1
✓ [2024-01-15T10:30:03] OK: imagen existe
✓ [2024-01-15T10:30:03] Nueva versión detectada

════════════════════════════════════════════════════════════════
  RESULTADO FINAL
════════════════════════════════════════════════════════════════
┌─────────────────────┬────────┬─────────────────────────────────┐
│ Paso                │ Estado │ Mensaje                         │
├─────────────────────┼────────┼─────────────────────────────────┤
│ validate_images     │   ✓    │ Imágenes validadas              │
│ find_rollback       │   ✓    │ Release rollback: 456           │
│ validate_credentials│   ✓    │ Credenciales vigentes           │
│ compare_configmap   │   ✓    │ Coincidencia: abc123...         │
└─────────────────────┴────────┴─────────────────────────────────┘
```

---

## 🔄 Integración en Pipeline

### Ejemplo de uso en Azure DevOps Pipeline

```yaml
- task: PythonScript@0
  displayName: 'Task Validator'
  inputs:
    scriptSource: 'filePath'
    scriptPath: '$(System.DefaultWorkingDirectory)/tools/azdo_task_validator.py'
    arguments: >
      --all
      --pat $(PAT)
      --org $(System.TeamFoundationCollectionUri)
      --project $(System.TeamProject)
      --release-id $(Release.ReleaseId)
      --image-actual $(IMAGE_ACTUAL)
      --image-nueva $(IMAGE_NUEVA)
      --gcp-project $(GCP_PROJECT_ID)
      --group-id $(GROUP_ID)
      --artifact-name $(ARTIFACT_NAME)
      --namespace $(ARTIFACT_NAMESPACE)
  env:
    PAT: $(PAT)
```

---

## 🐛 Troubleshooting

### Error: "No hay sesión activa de gcloud"
```bash
gcloud auth login
# O para service account:
gcloud auth activate-service-account --key-file=key.json
```

### Error: "Variable requerida faltante"
Asegúrate de que las variables de entorno estén configuradas o pásalas como argumentos CLI.

### Error: "No se encontró Release rollback"
- Verifica que el TAG exista en releases anteriores
- Aumenta el número de releases a buscar (máximo 50)
- Verifica que los builds tengan el task "Push Image"

### Error: "Credenciales vencidas"
Las credenciales del Variable Group fueron modificadas después de la fecha del release rollback. Necesitas actualizar el release o usar credenciales más recientes.

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-03-26 | 1.0.0 | Versión inicial - Port desde bash a Python |

---

## 📎 Basado en

Script original: `azdo-task-validador-optimized.sh`

## Autor

**Harold Adrian**
