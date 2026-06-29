# 🎯 Resumen de Integración - Tools 23 y 24

## Cambios Realizados

### 1️⃣ Nuevos Scripts PowerShell

#### `scm/azdo/pipeline-cd-new-re-release.sh`
- **Líneas**: 149
- **Función**: Crear nuevo Release desde Release existente
- **Parámetros**:
  - `sourceReleaseId` (default: 987)
  - `releaseComment` (obligatorio)
  - `pat` (opcional)
  - `backupPath` (default: ./backups)

#### `scm/azdo/pipeline-cd-restore-release.sh`
- **Líneas**: 153
- **Función**: Restaurar Release desde backup versionado
- **Parámetros**:
  - `backupFile` (obligatorio)
  - `restoreComment` (obligatorio)
  - `pat` (opcional)
  - `backupPath` (default: ./backups)

---

### 2️⃣ Actualización de tools.py

**Ubicación**: `scm/azdo/tools.py` (líneas 310-337)

#### Tool 23: Pipeline Re-Release
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
}
```

#### Tool 24: Pipeline Restore Release
```python
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
}
```

---

## 📊 Parámetros por Defecto

### Tool 23 (Re-Release)

| Parámetro | Valor Default | Tipo | Obligatorio |
|-----------|---------------|------|-------------|
| `sourceReleaseId` | `987` | int | No |
| `releaseComment` | `"Re-release automático desde tools.py"` | string | No |
| `pat` | `""` | string | No |
| `backupPath` | `"./backups"` | string | No |

**Nota**: El script solicita `releaseComment` interactivamente si no se proporciona.

### Tool 24 (Restore)

| Parámetro | Valor Default | Tipo | Obligatorio |
|-----------|---------------|------|-------------|
| `backupFile` | `""` | string | **Sí** |
| `restoreComment` | `"Restore automático desde tools.py"` | string | No |
| `pat` | `""` | string | No |
| `backupPath` | `"./backups"` | string | No |

**Nota**: El script busca automáticamente en `./backups/` si se proporciona solo el nombre.

---

## 🔄 Flujo de Ejecución desde tools.py

```
┌─────────────────────────────────────────────────────────────┐
│ Usuario selecciona opción 23 o 24 en el menú               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ tools.py lee PLATFORMS["23"] o PLATFORMS["24"]             │
│ • Extrae: path, args, defaults                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Construye comando PowerShell con parámetros                │
│ Ejemplo para Tool 23:                                       │
│   & ".\scm\azdo\pipeline-cd-new-re-release.sh" `           │
│     -sourceReleaseId 987 `                                  │
│     -releaseComment "Re-release automático..." `            │
│     -pat "" `                                               │
│     -backupPath "./backups"                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Script PowerShell se ejecuta                               │
│ • Fase 1: GET (obtener release)                            │
│ • Fase 2: BACKUP (crear snapshot)                          │
│ • Fase 3: MAPEAR (construir payload)                       │
│ • Fase 4: POST (crear nuevo release)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Resultado mostrado en consola                              │
│ ✅ ÉXITO o ❌ ERROR                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 Menú de tools.py

Las nuevas opciones aparecen en el menú principal:

```
═══════════════════════════════════════════════════════════════
  AZURE DEVOPS - RELEASE PIPELINE TOOLS
═══════════════════════════════════════════════════════════════

...
21  Pipeline Updater
22  Pipeline Rollback
23  Pipeline Re-Release                    ← NUEVA
24  Pipeline Restore Release               ← NUEVA
...
A   Ejecutar Todos
B   Ejecutar Todo + JSON
Q   Salir
```

---

## 📁 Estructura de Archivos

```
devsecops-toolbox/
├── scm/
│   └── azdo/
│       ├── tools.py                              (actualizado)
│       ├── pipeline-cd-new-re-release.sh         (nuevo)
│       ├── pipeline-cd-restore-release.sh        (nuevo)
│       ├── pipeline-cd-update-branchconfig.py    (renombrado)
│       └── pipeline-cd-rollback-pipeline.py      (renombrado)
├── ANALISIS_NUEVAS_HERRAMIENTAS.md              (nuevo)
└── RESUMEN_INTEGRACION.md                       (este archivo)
```

---

## 🔗 Relación entre Herramientas

```
Tool 21: Pipeline Updater
  └─ Actualiza variables y scripts en pipelines

Tool 22: Pipeline Rollback
  └─ Revierte cambios en pipelines

Tool 23: Pipeline Re-Release ← NUEVA
  └─ Crea nuevo release desde existente
     └─ Genera backup automático
        └─ Puede ser restaurado con Tool 24

Tool 24: Pipeline Restore Release ← NUEVA
  └─ Restaura desde backup versionado
     └─ Requiere backup previo (de Tool 23 o manual)
```

---

## 💡 Casos de Uso

### Caso 1: Re-ejecutar Release Anterior
```
1. Release #987 se ejecutó hace 1 semana
2. Necesitas re-ejecutar con mismos artefactos
3. Ejecutar Tool 23 con sourceReleaseId=987
4. Se crea Release #1234 con artefactos frescos
5. Se genera backup automático
```

### Caso 2: Rollback a Versión Anterior
```
1. Release #1234 tiene problemas
2. Necesitas volver a Release #987
3. Ejecutar Tool 24 con backup de Release #987
4. Se crea Release #1235 con artefactos del backup
5. Release #1235 se ejecuta en producción
```

### Caso 3: Auditoría y Trazabilidad
```
1. Cada release creado incluye descripción con:
   - Release origen
   - Versión del backup (si aplica)
   - Motivo de la acción
   - Timestamp
2. Backups se almacenan en ./backups/ con:
   - Nombre versionado: release_backup_REL_987_20260619_123045.json
   - Metadata completa (quién, cuándo, por qué)
   - Snapshot del estado del release
```

---

## ✅ Checklist de Validación

- [x] Scripts PowerShell creados y validados
- [x] Parámetros por defecto configurados
- [x] Integración en tools.py completada
- [x] Documentación detallada creada
- [x] Commits realizados
- [x] Estructura de archivos correcta
- [x] Relación entre herramientas clara

---

## 🚀 Próximos Pasos

1. **Prueba en desarrollo**:
   ```powershell
   cd devsecops-toolbox
   python scm/azdo/tools.py
   # Seleccionar opción 23 o 24
   ```

2. **Configurar PAT** en `scm/config.json`:
   ```json
   {
     "azdo": {
       "pat": "YOUR_PAT_HERE"
     }
   }
   ```

3. **Crear backups** ejecutando Tool 23 primero
4. **Restaurar** usando Tool 24 con backups creados

---

## 📞 Contacto

Para preguntas o problemas:
- Revisar `ANALISIS_NUEVAS_HERRAMIENTAS.md` para documentación completa
- Revisar scripts en `scm/azdo/pipeline-cd-*.sh`
- Revisar configuración en `scm/azdo/tools.py`
