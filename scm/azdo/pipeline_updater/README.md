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
  author: "Autor"
```

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

### Options (Opciones)

```yaml
options:
  dry_run: false
  rollback_on_error: true
```

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

- **Versión**: 1.0.1
- **Autor**: Harold Adrian
- **Fecha**: 2026-07-24

## Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0.1 | 2026-07-24 | Corregida la persistencia del `PUT` a Azure DevOps: se dejó de incrementar `revision` manualmente (causa del error HTTP 400 "You are using an old copy"); se usa `deepcopy` para no mutar la definición original; se agregó `lastRelease` a los campos de solo lectura removidos; el cuerpo del error de la API ahora se incluye en la excepción; logging de progreso simplificado. |
| 1.0.0 | 2026-07-13 | Versión inicial: actualización masiva de pipelines CD con templates YAML, búsqueda con `exact_match`, snapshots automáticos, ejecución paralela y reportería JSON/CSV/HTML. |
