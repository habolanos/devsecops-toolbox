# Pipeline Updater - Actualización Masiva de Pipelines CD

Herramienta para actualizar múltiples pipelines CD de Azure DevOps de forma masiva, segura y eficiente usando templates YAML.

## Características

- ✅ **Actualización Masiva**: Actualizar 50+ pipelines en < 10 segundos
- ✅ **Templates YAML**: Definir cambios de forma declarativa
- ✅ **Validación Estricta**: Validar templates antes de ejecutar
- ✅ **Ejecución Paralela**: ThreadPoolExecutor con 5 workers
- ✅ **Snapshots Automáticos**: Rollback automático en caso de error
- ✅ **Reportería Completa**: JSON, CSV, HTML
- ✅ **Modo Dry-Run**: Simular cambios sin aplicarlos
- ✅ **Auditoría**: Logging completo de todas las operaciones

## Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt
```

## Uso

### Opción 1: Desde línea de comandos

```bash
python pipeline_updater.py \
  --definition-ids 2758,2759,2760 \
  --template example_template.yaml \
  --org Coppel-Retail \
  --project Cadena_de_Suministros \
  --pat <token> \
  --dry-run
```

### Opción 2: Desde Python

```python
from scm.azdo.pipeline_updater import PipelineUpdater

updater = PipelineUpdater(
    pat="<token>",
    org="Coppel-Retail",
    project="Cadena_de_Suministros"
)

result = updater.update_pipelines(
    definition_ids=[2758, 2759, 2760],
    template_path="example_template.yaml",
    dry_run=False,
    max_workers=5
)

print(result)
```

## Estructura de Template

### Metadata

```yaml
metadata:
  name: "Nombre del template"
  version: "1.0"
  description: "Descripción"
  comment: |
    Comentario multilínea que se registra como comentario de la revisión
    en el historial de Azure DevOps al guardar la definición.
  author: "Autor"
```

**Nota**: El campo `metadata.comment` se envía como el `comment` de la revisión del release en Azure DevOps, por lo que aparece en el historial de cambios de la definición. Si se omite, no se modifica el comentario.

### Search (Búsqueda)

Define qué elementos buscar en los pipelines:

```yaml
search:
  stages:
    - "Producción"
    - "QA"
  tasks:
    - name: "Docker Push"
      type: "DockerPush"
  variables:
    - "DOCKER_IMAGE"
  artifacts:
    - alias: "drop"
      type: "BuildArtifact"
```

**Patrones de búsqueda**:
- Exacto: `"name"`
- Contiene: `"*name*"`
- Comienza con: `"name*"`
- Termina con: `"*name"`

### Update (Actualización)

Define qué cambios aplicar:

```yaml
update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          new_value: "myregistry.azurecr.io/myapp"
  variables:
    - name: "DOCKER_IMAGE"
      new_value: "myregistry.azurecr.io/myapp"
  stages:
    - name: "Producción"
      properties:
        - path: "queueId"
          new_value: 123
```

#### Acciones de Stage: `copy`, `add` y `rename`

El Pipeline Updater soporta tres acciones especiales para modificar stages:

**`action: copy`** - Clona un stage existente y lo inserta con un nuevo nombre:

```yaml
update:
  stages:
    - action: "copy"
      source_stage: "QA"          # Stage existente a clonar
      new_name: "QA-Copia"        # Nombre del nuevo stage
      position: "after"            # after | before | start | end
      reference_stage: "QA"       # Stage ancla (default: source_stage)
      task_updates:               # Opcional: modificar tasks del stage copiado
        - task_name: "Deploy to QA"
          fields:
            - path: "inputs.namespace"
              new_value: "qa-copia"
```

**`action: add`** - Inserta un stage nuevo desde una definición embebida:

```yaml
update:
  stages:
    - action: "add"
      name: "Security Check"
      definition:                  # Definición completa del stage
        id: 99
        name: "Security Check"
        rank: 2
        deployPhases:
          - deploymentInput:
              tasks:
                - displayName: "Run Security Scan"
                  enabled: true
      position: "between"          # after | before | between | start | end
      after_stage: "Build"
      before_stage: "Deploy"
```

**`action: rename`** - Renombra un stage existente:

```yaml
update:
  stages:
    - action: "rename"
      source_stage: "QA"          # Stage existente a renombrar
      new_name: "QA-Testing"       # Nuevo nombre del stage
```

**Posiciones de inserción**:
- `after`: después del stage de referencia (default)
- `before`: antes del stage de referencia
- `between`: entre `after_stage` y `before_stage` (requiere ambos)
- `start`: al inicio del pipeline
- `end`: al final del pipeline

**Notas**:
- Al insertar stages, los `rank` se reasignan automáticamente (1, 2, 3...) según el orden del array, ya que Azure DevOps ordena por `rank`.
- Los IDs de los nuevos stages se asignan automáticamente (max existente + 1).

### Options (Opciones)

```yaml
options:
  dry_run: false
  rollback_on_error: true
  ignore_variable_groups: [186, 196]  # IDs de variable groups a ignorar/remover
```

**Opciones disponibles:**

- **`dry_run`** (bool, default: false): Si es true, no aplica cambios reales, solo simula.
- **`rollback_on_error`** (bool, default: true): Si es true, crea snapshot antes de actualizar y hace rollback si hay error.
- **`ignore_variable_groups`** (list[int], default: []): Lista de IDs de variable groups que deben removirse antes de actualizar. Útil cuando los pipelines referencian grupos que ya no existen en Azure DevOps.

**Variable Groups Faltantes:**

Cuando un pipeline tiene referencias a variable groups que fueron eliminados o movidos, la actualización falla con HTTP 400. Use `ignore_variable_groups` para especificar qué IDs remover automáticamente:

```yaml
options:
  ignore_variable_groups: [186, 196]  # Estos grupos se removerán
```

**Niveles de Remoción:**

Los variable groups se remueven de dos niveles en la definición del pipeline:

1. **Nivel Global** (`definition.variableGroups`): Referencias a nivel del pipeline completo
2. **Nivel de Environments** (`environments[].variableGroups`): Referencias específicas a cada stage

Los grupos removidos se registran en el reporte de cambios con tipo `variable_groups_removed`, indicando el nivel (Global o nombre del environment).

## Ejemplos

### Ejemplo 1: Actualizar imagen Docker

```yaml
metadata:
  name: "Update Docker Image"
  version: "1.0"

search:
  tasks:
    - name: "Docker Push"

update:
  tasks:
    - name: "Docker Push"
      fields:
        - path: "inputs.imageRepository"
          new_value: "myregistry.azurecr.io/app:v2.0"
```

### Ejemplo 2: Actualizar variables de entorno

```yaml
metadata:
  name: "Update Environment Variables"
  version: "1.0"

search:
  variables:
    - "API_URL"
    - "API_KEY"

update:
  variables:
    - name: "API_URL"
      new_value: "https://api.prod.example.com"
    - name: "API_KEY"
      new_value: "new-secret-key"
```

### Ejemplo 3: Actualizar múltiples elementos

```yaml
metadata:
  name: "Complete Pipeline Update"
  version: "1.0"

search:
  stages:
    - "Producción"
  tasks:
    - name: "*Deploy*"
  variables:
    - "*IMAGE*"

update:
  tasks:
    - name: "Deploy to AKS"
      fields:
        - path: "inputs.kubernetesCluster"
          new_value: "prod-cluster"
  variables:
    - name: "DOCKER_IMAGE"
      new_value: "myregistry.azurecr.io/app:latest"
```

## Salida y Reportes

Los reportes se generan en `outcome/pipeline_updates/`:

- **report_YYYYMMDD_HHMMSS.json**: Datos completos en JSON
- **report_YYYYMMDD_HHMMSS.csv**: Resumen en CSV
- **report_YYYYMMDD_HHMMSS.html**: Reporte visual en HTML

### Estructura JSON

```json
{
  "timestamp": "2026-07-13T10:00:00",
  "summary": {
    "total": 3,
    "success": 3,
    "failed": 0,
    "total_matches": 9,
    "total_changes": 9
  },
  "details": [
    {
      "definition_id": 2758,
      "success": true,
      "snapshot_id": "snapshot_2758_1689241200",
      "matches_found": 3,
      "changes_applied": 3,
      "changes": [
        {
          "type": "task_field",
          "stage": "Producción",
          "task": "Docker Push",
          "field": "inputs.imageRepository",
          "old": "old-image",
          "new": "new-image"
        }
      ],
      "duration": 2.34
    }
  ],
  "errors": []
}
```

## Snapshots y Rollback

Los snapshots se guardan automáticamente en `outcome/snapshots/`:

```bash
# Restaurar desde snapshot
python -c "
from scm.azdo.pipeline_updater import AzureDevOpsClient

client = AzureDevOpsClient('<pat>', 'org', 'project')
client.rollback(2758, 'snapshot_2758_1689241200')
"
```

## Validación

El template se valida automáticamente:

```python
from scm.azdo.pipeline_updater import TemplateValidator

validator = TemplateValidator(template_dict)
if validator.validate():
    print("Template válido")
else:
    print("Errores:", validator.get_errors())
    print("Advertencias:", validator.get_warnings())
```

## Manejo de Errores

La herramienta maneja automáticamente:

- Pipelines no encontrados
- Permisos insuficientes
- Errores de conexión
- Validación de templates
- Rollback automático en caso de error

## Seguridad

- ✅ Validación de permisos
- ✅ Snapshots automáticos para rollback
- ✅ Confirmación del usuario antes de ejecutar
- ✅ Auditoría completa en logs
- ✅ Modo dry-run para preview

## Performance

- **Tiempo de actualización**: ~2-5 segundos por pipeline
- **Paralelismo**: 5 workers por defecto (configurable)
- **50 pipelines**: < 10 segundos
- **100 pipelines**: < 20 segundos

## Troubleshooting

### Error: "Template inválido"
Verificar que el template contiene las secciones requeridas: `metadata`, `search`, `update`

### Error: "Pipeline no encontrado"
Verificar que el definition-id es correcto usando:
```bash
python -c "
from scm.azdo.pipeline_updater import AzureDevOpsClient
client = AzureDevOpsClient('<pat>', 'org', 'project')
defs = client.list_release_definitions()
print(defs)
"
```

### Error: "Permiso denegado"
Verificar que el PAT tiene permisos para editar Release Pipelines

### Error: "You are using an old copy of the release pipeline" (HTTP 400)
Azure DevOps usa el campo `revision` de la definición como mecanismo de
**concurrencia optimista**. Al hacer `PUT` se debe enviar la **misma** revisión
que devolvió el `GET`; el servidor la incrementa internamente. **No** se debe
incrementar la revisión manualmente ni enviar una copia desactualizada. Si otro
usuario modifica el pipeline entre el `GET` y el `PUT`, vuelve a descargar la
definición y reintenta.

### Error: HTTP 400 al guardar (campos de solo lectura)
La API rechaza definiciones que incluyan campos de solo lectura a nivel raíz.
El cliente elimina automáticamente: `_links`, `url`, `projectReference`,
`createdBy`, `createdOn`, `modifiedBy`, `modifiedOn`, `isDeleted`, `isDisabled`,
`currentRelease`, `badgeUrl` y `lastRelease` antes del `PUT`.

## Documentación

- [Plan de Implementación](../../../docs/features/feature_actualizacion_pipeline_cd_with_template/03_PLAN_IMPLEMENTACION.md)
- [Especificación de Template](../../../docs/features/feature_actualizacion_pipeline_cd_with_template/02_ESPECIFICACION_TEMPLATE.md)
- [Ejemplos Prácticos](../../../docs/features/feature_actualizacion_pipeline_cd_with_template/04_EJEMPLOS_PRACTICOS.md)

## Versión

- **Versión**: 1.0.5
- **Autor**: Harold Adrian
- **Fecha**: 2026-07-25

## Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0.5 | 2026-07-25 | **Acción de Stage: rename**: Implementación para renombrar stages existentes. (1) **action: rename**: cambia el nombre de un stage existente (`source_stage`) a un nuevo nombre (`new_name`). (2) **Preservación**: mantiene el ID, rank y configuración del stage original; solo modifica el campo `name`. (3) **Pruebas**: 4 tests nuevos en `test_copy_stage.py` (cambio de nombre, preservación de ID/rank, validación de source_stage, registro de cambios). (4) **Template**: `pipe_cd_rename_stage.yaml` como ejemplo de uso. (5) **Documentación**: README actualizado con ejemplo de `action: rename`. Suite del módulo: 34 tests en verde (14 nuevos + 20 existentes). |
| 1.0.4 | 2026-07-24 | **Acciones de Stage: copy y add**: Implementación completa para insertar nuevos stages en pipelines. (1) **action: copy**: clona un stage existente (`source_stage`) y lo inserta con un nuevo nombre (`new_name`). Soporta modificación de atributos de tasks dentro del stage copiado (`task_updates`). (2) **action: add**: inserta un stage nuevo desde una definición embebida (`definition`). (3) **Posiciones de inserción**: `after`, `before`, `between`, `start`, `end`. `between` requiere `after_stage` y `before_stage`. (4) **Ranks automáticos**: al insertar stages, los `rank` se reasignan secuencialmente (1, 2, 3...) según el orden del array, ya que Azure DevOps ordena por `rank`. (5) **IDs automáticos**: los IDs de nuevos stages se asignan como max existente + 1. (6) **Pruebas**: `test_copy_stage.py` con 10 tests (copy, add, task_updates, between, validaciones). Documentación actualizada en README. |
| 1.0.3 | 2026-07-24 | El campo `metadata.comment` del template ahora se envía como comentario de la revisión del release en Azure DevOps (visible en el historial). Se agregó `comment` a `TemplateMetadata` y al parser; `update_release_definition()` acepta el parámetro opcional `comment`. Pruebas añadidas en `test_update_release_definition.py`. |
| 1.0.2 | 2026-07-24 | Corregido el reordenamiento de stages: ahora se asigna el campo `rank` a cada environment. En Azure DevOps el orden de los stages lo determina `rank`, no la posición en el array; antes solo se reordenaba el array y el cambio no se reflejaba. Validado contra el pipeline `2016` (Develop→QA→Staging→Production). Se añadieron pruebas de unidad en `test_reorder_stages.py`. |
| 1.0.1 | 2026-07-24 | Corregida la persistencia del `PUT` a Azure DevOps: se dejó de incrementar `revision` manualmente (causa del error HTTP 400 "You are using an old copy"); se usa `deepcopy` para no mutar la definición original; se agregó `lastRelease` a los campos de solo lectura removidos; el cuerpo del error de la API ahora se incluye en la excepción; logging de progreso simplificado. |
| 1.0.0 | 2026-07-13 | Versión inicial: actualización masiva de pipelines CD con templates YAML, búsqueda con `exact_match`, snapshots automáticos, ejecución paralela y reportería JSON/CSV/HTML. |
