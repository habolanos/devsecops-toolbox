# Azure DevOps Pipeline Updater

## 📋 Descripción

Herramienta Python para actualizar Release Pipelines de Azure DevOps mediante la API REST. Permite modificar variables y scripts de tareas de forma programática.

## ✨ Características

- ✅ Actualiza la variable `branchConfig` en Release Pipelines
- ✅ Busca y reemplaza patrones en scripts de tareas específicas
- ✅ Modo DRY-RUN para simular cambios sin guardarlos
- ✅ Autenticación con Personal Access Token (PAT)
- ✅ Salida colorizada y detallada del proceso
- ✅ Manejo robusto de errores HTTP

## 🚀 Uso

### Desde el Menú de Terminal Tools

```bash
python scm/terminal/tools.py
# Seleccionar opción 7: Azure DevOps Pipeline Updater
```

El menú interactivo solicitará:
1. **Organización** (ej: Coppel-Retail)
2. **Proyecto** (ej: Cadena_de_Suministros)
3. **ID del Pipeline** (visible en la URL del Release Pipeline)
4. **PAT** (Personal Access Token con permisos Release: Read & Write)
5. **Opciones adicionales** (valores personalizados o usar defaults)

### Uso Directo (CLI)

**Uso más simple (modo interactivo con config.json)**:
```bash
# Lee PAT y defaults desde scm/config.json
python scm/terminal/update-pipeline-cd-branchconfig.py --interactive
```

**Uso con parámetros CLI (sin interacción)**:
```bash
# Solo requiere el PAT, usa todos los defaults
python scm/terminal/update-pipeline-cd-branchconfig.py --pat YOUR_PAT_HERE
```

**Uso completo (especificando todos los parámetros)**:
```bash
python scm/terminal/update-pipeline-cd-branchconfig.py \
  --org Coppel-Retail \
  --project Cadena_de_Suministros \
  --definition-id 123 \
  --pat YOUR_PAT_HERE
```

### Opciones Avanzadas

```bash
python scm/terminal/update-pipeline-cd-branchconfig.py \
  --org MyOrg \
  --project MyProject \
  --definition-id 456 \
  --pat TOKEN \
  --branch-config config-production \
  --task-name "deploy manifest" \
  --old-pattern "$(oldVar)" \
  --new-pattern "$(newVar)" \
  --dry-run
```

## ⚙️ Configuración (config.json)

Para usar el modo interactivo, configura `scm/config.json`:

```json
{
  "azdo": {
    "pipeline_updater": {
      "organization": "Coppel-Retail",
      "project": "Cadena_de_Suministros",
      "definition_id": 123,
      "pat": "TU_PAT_AQUI",
      "branch_config": "config-cadenaSuministro",
      "task_name": "get file k8-manifest",
      "old_pattern": "$(path_pipelineConfig)",
      "new_pattern": "$(path_pipelineConfigYml)"
    }
  }
}
```

**Pasos**:
1. Copia `scm/config.json.template` a `scm/config.json`
2. Edita la sección `azdo.pipeline_updater`
3. Agrega tu PAT
4. Ejecuta con `--interactive`

**Nota**: `scm/config.json` está en `.gitignore` y nunca se subirá al repositorio.

## 📝 Parámetros

| Parámetro | Requerido | Default | Descripción |
|-----------|-----------|---------|-------------|
| `--org` | ❌ | `Coppel-Retail` | Organización de Azure DevOps |
| `--project` | ❌ | `Cadena_de_Suministros` | Nombre del proyecto |
| `--definition-id` | ❌ | `123` | ID del Release Pipeline |
| `--pat` | ✅ | - | Personal Access Token (REQUERIDO) |
| `--branch-config` | ❌ | `config-cadenaSuministro` | Nuevo valor para variable branchConfig |
| `--task-name` | ❌ | `get file k8-manifest` | Display name de la tarea a actualizar |
| `--old-pattern` | ❌ | `$(path_pipelineConfig)` | Patrón a buscar en el script |
| `--new-pattern` | ❌ | `$(path_pipelineConfigYml)` | Patrón de reemplazo |
| `--dry-run` | ❌ | `False` | Simula cambios sin guardarlos |

**Nota**: Solo el PAT es requerido. Todos los demás parámetros tienen valores por defecto configurados según el script PowerShell original.

## 🔐 Configuración del PAT

Para crear un Personal Access Token en Azure DevOps:

1. Ve a **User Settings** → **Personal Access Tokens**
2. Click en **New Token**
3. Configura:
   - **Name**: Pipeline Updater
   - **Organization**: Selecciona tu organización
   - **Expiration**: Configura según políticas
   - **Scopes**: Selecciona **Release** (Read & Write)
4. Click **Create** y copia el token

⚠️ **Importante**: Guarda el PAT de forma segura. No lo compartas ni lo subas a repositorios.

## 📊 Ejemplo de Salida

```
======================================================================
  Azure DevOps Release Pipeline - Branch Config Updater v1.0.0
======================================================================

Configuración:
  Organización: Coppel-Retail
  Proyecto: Cadena_de_Suministros
  Pipeline ID: 123
  Modo: PRODUCCIÓN

>>> Obteniendo definición del release pipeline...
✓ Definición obtenida exitosamente
>>> Actualizando variable 'branchConfig'...
  Valor anterior: config-old
  branchConfig = config-cadenaSuministro
>>> Buscando tarea 'get file k8-manifest'...
  ✓ Tarea encontrada en environment: Production
  Script actualizado:
    ANT: $(path_pipelineConfig)
    NEW: $(path_pipelineConfigYml)
>>> Enviando definición actualizada...
>>> Pipeline actualizado exitosamente.
  Revision: 42
  URL: https://vsrm.dev.azure.com/Coppel-Retail/...

======================================================================
  ✓ Proceso completado exitosamente
======================================================================
```

## 🔍 Modo DRY-RUN

El modo `--dry-run` permite simular los cambios sin guardarlos:

```bash
python update-pipeline-cd-branchconfig.py \
  --org MyOrg --project MyProject --definition-id 123 \
  --pat TOKEN --dry-run
```

Salida:
```
>>> Modo DRY-RUN: Cambios NO guardados
  Variable branchConfig actualizada: config-cadenaSuministro
  Reemplazos en scripts: 1
```

## 🛠️ Casos de Uso

### 1. Actualizar Branch Config en Múltiples Pipelines

```bash
# Pipeline de QA
python update-pipeline-cd-branchconfig.py \
  --org MyOrg --project MyProject --definition-id 100 \
  --pat TOKEN --branch-config config-qa

# Pipeline de Producción
python update-pipeline-cd-branchconfig.py \
  --org MyOrg --project MyProject --definition-id 200 \
  --pat TOKEN --branch-config config-production
```

### 2. Migración de Variables

```bash
# Reemplazar referencias a variables antiguas
python update-pipeline-cd-branchconfig.py \
  --org MyOrg --project MyProject --definition-id 123 \
  --pat TOKEN \
  --task-name "Deploy to K8s" \
  --old-pattern "$(legacy_var)" \
  --new-pattern "$(new_var)"
```

### 3. Validación Previa (DRY-RUN)

```bash
# Verificar cambios antes de aplicarlos
python update-pipeline-cd-branchconfig.py \
  --org MyOrg --project MyProject --definition-id 123 \
  --pat TOKEN --dry-run

# Si todo está OK, ejecutar sin --dry-run
python update-pipeline-cd-branchconfig.py \
  --org MyOrg --project MyProject --definition-id 123 \
  --pat TOKEN
```

## 🐛 Troubleshooting

### Error: HTTP 401 Unauthorized

**Causa**: PAT inválido o sin permisos suficientes.

**Solución**:
- Verifica que el PAT tenga permisos **Release (Read & Write)**
- Confirma que el PAT no haya expirado
- Regenera el PAT si es necesario

### Error: No se encontró la tarea

**Causa**: El `displayName` de la tarea no coincide.

**Solución**:
1. Ve a la UI de Azure DevOps
2. Abre el Release Pipeline
3. Verifica el nombre exacto de la tarea
4. Usa `--task-name "Nombre Exacto"`

### Error: HTTP 404 Not Found

**Causa**: Organization, Project o Definition ID incorrectos.

**Solución**:
- Verifica la URL del pipeline en Azure DevOps
- Formato: `https://dev.azure.com/{org}/{project}/_release?definitionId={id}`
- Usa los valores exactos de la URL

## 📚 API de Azure DevOps

Esta herramienta usa la API REST de Azure DevOps Release Management:

- **Endpoint**: `https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{id}`
- **API Version**: 7.0
- **Autenticación**: Basic Auth con PAT
- **Métodos**: GET (obtener), PUT (actualizar)

Documentación oficial: [Azure DevOps REST API - Release Definitions](https://learn.microsoft.com/en-us/rest/api/azure/devops/release/definitions)

## 🔄 Migración desde PowerShell

Si tienes el script PowerShell original (`process-update-pipeline-cd-branchconfig.ps1`), esta herramienta Python es equivalente y ofrece:

✅ **Ventajas**:
- Multiplataforma (Windows, Linux, macOS)
- Integración con Terminal Tools menu
- Modo DRY-RUN
- Mejor manejo de errores
- Parámetros configurables vía CLI

**Equivalencia**:
```powershell
# PowerShell (antiguo)
$organization = "Coppel-Retail"
$project = "Cadena_de_Suministros"
$definitionId = 123
$pat = "TOKEN"
```

```bash
# Python (nuevo)
python update-pipeline-cd-branchconfig.py \
  --org Coppel-Retail \
  --project Cadena_de_Suministros \
  --definition-id 123 \
  --pat TOKEN
```

## 📦 Dependencias

- Python 3.7+
- Módulos estándar: `urllib`, `json`, `base64`, `argparse`
- Sin dependencias externas (no requiere `requests`)

## 🤝 Contribuciones

Para reportar bugs o sugerir mejoras, contacta al equipo de DevSecOps.

---

**Versión**: 1.0.0  
**Autor**: Harold Adrian  
**Última actualización**: Junio 2026
