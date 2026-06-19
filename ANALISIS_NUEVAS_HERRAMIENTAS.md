# 📊 Análisis de Nuevas Herramientas de Release Pipeline

## Resumen Ejecutivo

Se han agregado **2 nuevas herramientas** al sistema de Azure DevOps para gestionar releases con backup y restore automáticos:

- **Tool 23**: Pipeline Re-Release (`pipeline-cd-new-re-release.sh`)
- **Tool 24**: Pipeline Restore Release (`pipeline-cd-restore-release.sh`)

Ambas herramientas están integradas en `tools.py` con parámetros por defecto y opciones de configuración.

---

## 📋 Tool 23: Pipeline Re-Release

### Propósito
Crea un nuevo Release desde un Release existente con **backup automático versionado**. Permite re-ejecutar un release anterior con artefactos frescos sin perder el historial.

### Parámetros

| Parámetro | Tipo | Obligatorio | Default | Descripción |
|-----------|------|-------------|---------|-------------|
| `sourceReleaseId` | int | No | 987 | ID del Release origen a re-ejecutar |
| `releaseComment` | string | **Sí** | N/A | Comentario explicando el motivo del re-release |
| `pat` | string | No | "" | Personal Access Token (si no se proporciona, solicita interactivamente) |
| `backupPath` | string | No | `./backups` | Carpeta donde guardar backups versionados |

### Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: GET - Obtener Release Origen                        │
│ • Consulta Azure DevOps VSRM API                            │
│ • Valida que el Release existe                              │
│ • Extrae artefactos, variables y configuración              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: BACKUP - Crear Snapshot Versionado                  │
│ • Genera label: REL_{releaseId}_{timestamp}                 │
│ • Guarda JSON con metadata completa                         │
│ • Almacena en ./backups/release_backup_*.json               │
│ • Incluye: definitionId, artefactos, variables, status      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: MAPEAR - Construir Payload del Nuevo Release        │
│ • Extrae artefactos exactos del release origen              │
│ • Crea descripción con trazabilidad:                        │
│   "Re-release desde #987 [Backup: REL_987_20260619_123045]" │
│ • Prepara payload JSON para POST                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 4: POST - Crear Nuevo Release                          │
│ • Envía POST a VSRM API /releases                           │
│ • Crea release FRESH con artefactos nuevos                  │
│ • Retorna ID del nuevo release                              │
│ • Muestra URL directa en Azure DevOps                       │
└─────────────────────────────────────────────────────────────┘
```

### Ejemplo de Uso

```powershell
# Desde tools.py (automático)
# Seleccionar opción 23 en el menú

# Parámetros que se pasan:
# --sourceReleaseId 987
# --releaseComment "Re-release automático desde tools.py"
# --pat "TU_PAT_AQUI"
# --backupPath "./backups"

# Salida esperada:
# ✅ ÉXITO: Nuevo Release creado!
#    ID         : 1234
#    Nombre     : Release-1234
#    Comentario : Re-release automático desde tools.py
#    Backup Ref : REL_987_20260619_123045
#    Pipeline   : Cadena_de_Suministros
#    URL        : https://dev.azure.com/Coppel-Retail/Cadena_de_Suministros/_releaseProgress?...
```

### Backup Versionado

Cada re-release crea un backup con estructura:

```json
{
  "metadata": {
    "versionLabel": "REL_987_20260619_123045",
    "sourceReleaseId": 987,
    "backupDate": "2026-06-19 12:30:45",
    "backedUpBy": "harold.bolanos",
    "comment": "Re-release automático desde tools.py"
  },
  "releaseSnapshot": {
    "releaseDefinitionId": 42,
    "releaseDefinitionName": "Cadena_de_Suministros",
    "originalDescription": "...",
    "originalStatus": "active",
    "createdOn": "2026-06-19T12:30:45.123Z",
    "artifacts": [...],
    "variables": {...},
    "environments": [...]
  }
}
```

---

## 🔄 Tool 24: Pipeline Restore Release

### Propósito
Restaura un Release desde un **backup versionado** con trazabilidad completa. Permite rollback seguro con confirmación interactiva y auditoría.

### Parámetros

| Parámetro | Tipo | Obligatorio | Default | Descripción |
|-----------|------|-------------|---------|-------------|
| `backupFile` | string | **Sí** | "" | Ruta o nombre del archivo de backup a restaurar |
| `restoreComment` | string | **Sí** | N/A | Comentario explicando el motivo del restore |
| `pat` | string | No | "" | Personal Access Token |
| `backupPath` | string | No | `./backups` | Carpeta donde buscar backups si no se proporciona ruta completa |

### Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: LECTURA - Cargar y Validar Backup                   │
│ • Busca archivo en ruta completa o en ./backups/            │
│ • Valida que sea JSON válido                                │
│ • Extrae metadata y snapshot                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: VALIDACIÓN - Mostrar Info del Backup                │
│ • Muestra tabla con:                                        │
│   - Versión Label (REL_987_20260619_123045)                 │
│   - Release Origen (#987)                                   │
│   - Fecha del Backup                                        │
│   - Usuario que creó el backup                              │
│   - Pipeline afectado                                       │
│   - Cantidad de artefactos                                  │
│ • Solicita confirmación interactiva: ¿Confirmas RESTORE?    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: CONSTRUIR - Reconstruir Payload desde Snapshot      │
│ • Mapea artefactos exactos del backup                       │
│ • Crea descripción con trazabilidad:                        │
│   "🔄 RESTORE desde backup [REL_987_...] - Release #987"    │
│ • Agrega motivo del restore                                 │
│ • Prepara payload JSON para POST                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 4: POST - Crear Release de Restore                     │
│ • Envía POST a VSRM API /releases                           │
│ • Crea release NUEVO con artefactos del backup              │
│ • Retorna ID del release restaurado                         │
│ • Muestra URL directa en Azure DevOps                       │
└─────────────────────────────────────────────────────────────┘
```

### Ejemplo de Uso

```powershell
# Desde tools.py (automático)
# Seleccionar opción 24 en el menú

# Parámetros que se pasan:
# --backupFile "release_backup_REL_987_20260619_123045.json"
# --restoreComment "Restore automático desde tools.py"
# --pat "TU_PAT_AQUI"
# --backupPath "./backups"

# Flujo interactivo:
# 1. Carga backup
# 2. Muestra tabla con información
# 3. Solicita confirmación: "¿Confirmas el RESTORE desde este backup? (S/N)"
# 4. Si confirma: crea nuevo release
# 5. Muestra resultado

# Salida esperada:
# ✅ RESTORE EXITOSO!
#    Nuevo Release ID  : 1235
#    Nombre            : Release-1235
#    Backup Origen     : REL_987_20260619_123045
#    Release Origen    : #987
#    Motivo Restore    : Restore automático desde tools.py
#    URL               : https://dev.azure.com/Coppel-Retail/...
```

### Búsqueda Inteligente de Backups

Si no se proporciona ruta completa, busca automáticamente:

```powershell
# Ejemplo: si pasas solo "REL_987"
# El script busca en ./backups/ archivos que contengan "REL_987"
# Selecciona el más reciente (LastWriteTime descendente)

Get-ChildItem -Path "./backups" -Filter "*REL_987*" | 
  Sort-Object LastWriteTime -Descending | 
  Select-Object -First 1
```

---

## 🔗 Integración en tools.py

### Entrada en PLATFORMS

```python
"23": {
    "name":        "Pipeline Re-Release",
    "description": "Crea un nuevo Release desde un Release existente con backup automático versionado...",
    "path":        "pipeline-cd-new-re-release.sh",
    "args":        ["--sourceReleaseId", "--releaseComment", "--pat", "--backupPath"],
    "defaults":    {
        "sourceReleaseId": 987,
        "releaseComment": "Re-release automático desde tools.py",
        "pat": "",
        "backupPath": "./backups"
    },
    "group":       "release",
    "status":      "ready",
},

"24": {
    "name":        "Pipeline Restore Release",
    "description": "Restaura un Release desde un backup versionado...",
    "path":        "pipeline-cd-restore-release.sh",
    "args":        ["--backupFile", "--restoreComment", "--pat", "--backupPath"],
    "defaults":    {
        "backupFile": "",
        "restoreComment": "Restore automático desde tools.py",
        "pat": "",
        "backupPath": "./backups"
    },
    "group":       "release",
    "status":      "ready",
},
```

### Cómo se Ejecutan desde tools.py

1. Usuario selecciona opción 23 o 24 en el menú
2. tools.py lee la configuración desde `PLATFORMS[tool_id]`
3. Extrae `path` y `defaults`
4. Construye comando PowerShell:
   ```powershell
   & ".\scm\azdo\pipeline-cd-new-re-release.sh" `
     -sourceReleaseId 987 `
     -releaseComment "Re-release automático desde tools.py" `
     -pat "" `
     -backupPath "./backups"
   ```
5. Ejecuta el script con los parámetros
6. Captura salida y muestra resultados

---

## 📊 Comparativa: Re-Release vs Restore

| Aspecto | Re-Release (Tool 23) | Restore (Tool 24) |
|--------|---------------------|-------------------|
| **Propósito** | Crear nuevo release desde existente | Restaurar desde backup |
| **Entrada** | Release ID origen | Archivo de backup |
| **Backup** | Automático (crea nuevo) | Requiere backup previo |
| **Confirmación** | Automática | Interactiva (requiere confirmación) |
| **Artefactos** | Frescos (nuevos) | Del backup (históricos) |
| **Caso de Uso** | Re-ejecutar release anterior | Rollback a versión anterior |
| **Riesgo** | Bajo (crea nuevo) | Medio (restaura histórico) |
| **Auditoría** | Backup versionado | Trazabilidad completa |

---

## 🔐 Seguridad y Auditoría

### Backup Versionado
- **Label único**: `REL_{releaseId}_{timestamp}`
- **Metadata completa**: quién, cuándo, por qué
- **Snapshot JSON**: estado completo del release
- **Almacenamiento**: `./backups/release_backup_*.json`

### Confirmación Interactiva
- Tool 24 requiere confirmación antes de restaurar
- Muestra tabla con información del backup
- Solicita entrada explícita: "¿Confirmas el RESTORE?"

### Trazabilidad
- Descripción del nuevo release incluye:
  - Release origen
  - Versión del backup
  - Motivo de la acción
  - Timestamp de ejecución

---

## 🚀 Flujo Completo: Re-Release + Restore

### Escenario: Problema en Producción

```
1. Release #987 se ejecuta en producción
   ↓
2. Se detecta problema
   ↓
3. Ejecutar Tool 23 (Re-Release)
   • Crea backup automático: REL_987_20260619_123045
   • Crea nuevo release #1234 con artefactos frescos
   ↓
4. Si el nuevo release también falla:
   ↓
5. Ejecutar Tool 24 (Restore)
   • Carga backup: REL_987_20260619_123045
   • Muestra información
   • Solicita confirmación
   • Crea release #1235 con artefactos del backup
   ↓
6. Release #1235 se ejecuta con configuración anterior
```

---

## 📝 Notas Técnicas

### Requisitos
- PowerShell 5.0+
- Acceso a Azure DevOps VSRM API
- Personal Access Token (PAT) con permisos Release (Read & Write)
- Carpeta `./backups` con permisos de escritura

### Configuración en config.json
```json
{
  "azdo": {
    "organization_url": "https://dev.azure.com/Coppel-Retail",
    "project": "Cadena_de_Suministros",
    "pat": "YOUR_PAT_HERE",
    "pipeline_updater": {
      "definition_id": 123,
      "branch_config": "config-cadenaSuministro"
    }
  }
}
```

### Errores Comunes
1. **PAT inválido**: "Error HTTP 401: Unauthorized"
2. **Release no existe**: "Error HTTP 404: Not Found"
3. **Backup no encontrado**: "No se encontró ningún backup con ese nombre"
4. **Permisos insuficientes**: "Error HTTP 403: Forbidden"

---

## ✅ Checklist de Implementación

- [x] Script `pipeline-cd-new-re-release.sh` creado
- [x] Script `pipeline-cd-restore-release.sh` creado
- [x] Entrada Tool 23 en `tools.py`
- [x] Entrada Tool 24 en `tools.py`
- [x] Parámetros por defecto configurados
- [x] Documentación completa
- [x] Commit realizado

---

## 📞 Soporte

Para más información:
- Revisar scripts: `scm/azdo/pipeline-cd-*.sh`
- Revisar configuración: `scm/azdo/tools.py` (líneas 310-337)
- Revisar backups: `./backups/` (después de ejecutar)
