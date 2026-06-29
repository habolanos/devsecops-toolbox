# 🐍 Implementación Python - Tools 23 y 24

## Resumen de Cambios

Se han convertido los scripts PowerShell a **Python puro** siguiendo el patrón de trabajo establecido en el proyecto.

### Archivos Creados

#### 1. `scm/azdo/pipeline_cd_new_re_release.py` (422 líneas)
- **Propósito**: Crear nuevo Release desde uno existente con backup automático
- **Patrón**: Idéntico a `pipeline-cd-update-branchconfig.py`
- **Características**:
  - ✅ Carga config desde `scm/config.json`
  - ✅ Modo interactivo con `--interactive`
  - ✅ Colores ANSI para terminal
  - ✅ Argumentos con defaults
  - ✅ Exporta reporte JSON a `outcome/`
  - ✅ Confirmación antes de ejecutar
  - ✅ Manejo de errores completo

#### 2. `scm/azdo/pipeline_cd_restore_release.py` (418 líneas)
- **Propósito**: Restaurar Release desde backup versionado
- **Patrón**: Idéntico a otros scripts del proyecto
- **Características**:
  - ✅ Carga config desde `scm/config.json`
  - ✅ Modo interactivo con `--interactive`
  - ✅ Búsqueda automática de backups
  - ✅ Confirmación interactiva antes de restore
  - ✅ Tabla de información del backup
  - ✅ Exporta reporte JSON a `outcome/`
  - ✅ Manejo de errores completo

### Actualización de tools.py

```python
"23": {
    "name":        "Pipeline Re-Release",
    "description": "Crea Nuevo Release desde uno existente con backup automático versionado...",
    "path":        "pipeline_cd_new_re_release.py",  # ← Cambio de .sh a .py
    "args":        ["--org", "--project", "--source-release-id", "--release-comment", "--pat", "--backup-path"],
    "defaults":    {
        "org": "Coppel-Retail",
        "project": "Cadena_de_Suministros",
        "source_release_id": 999999,
        "release_comment": "Renovacion de Credenciales Git",
        "pat": "",
        "backup_path": "./outcome/backups"  # ← Cambio a outcome/
    },
    "group":       "release",
    "status":      "ready",
},

"24": {
    "name":        "Pipeline Restore Release",
    "description": "Restaura un Release desde un backup versionado...",
    "path":        "pipeline_cd_restore_release.py",  # ← Cambio de .sh a .py
    "args":        ["--org", "--project", "--backup-file", "--restore-comment", "--pat", "--backup-path"],
    "defaults":    {
        "org": "Coppel-Retail",
        "project": "Cadena_de_Suministros",
        "backup_file": "",
        "restore_comment": "Restore automático desde tools.py",
        "pat": "",
        "backup_path": "./outcome/backups"  # ← Cambio a outcome/
    },
    "group":       "release",
    "status":      "ready",
},
```

---

## 📊 Comparativa: PowerShell vs Python

| Aspecto | PowerShell | Python |
|---------|-----------|--------|
| **Lenguaje** | .sh (PowerShell) | .py (Python 3) |
| **Dependencias** | PowerShell 5.0+ | Python 3.8+ |
| **Config** | Hardcoded | Carga desde config.json |
| **Modo Interactivo** | Manual | `--interactive` automático |
| **Colores** | Write-Host | ANSI codes |
| **Reportes** | Consola | JSON a outcome/ |
| **Patrón** | Único | Consistente con proyecto |
| **Mantenibilidad** | Media | Alta |
| **Testing** | Difícil | Fácil (pytest) |

---

## 🚀 Uso desde tools.py

### Tool 23: Pipeline Re-Release

```bash
# Modo interactivo (recomendado)
python scm/azdo/pipeline_cd_new_re_release.py --interactive

# Modo directo con parámetros
python scm/azdo/pipeline_cd_new_re_release.py \
  --org Coppel-Retail \
  --project Cadena_de_Suministros \
  --source-release-id 987 \
  --release-comment "Motivo del re-release" \
  --pat YOUR_PAT_HERE \
  --backup-path ./outcome/backups
```

**Salida esperada**:
```
═══════════════════════════════════════════════════════════════
  Azure DevOps Pipeline Re-Release v1.0.0
═══════════════════════════════════════════════════════════════

Configuración:
  Organización: Coppel-Retail
  Proyecto: Cadena_de_Suministros
  Release origen: #987
  Comentario: Motivo del re-release
  Carpeta backups: ./outcome/backups

─────────────────────────────────────────────────────────────
FASE 1: Obtener Release Origen
─────────────────────────────────────────────────────────────
>>> Obteniendo Release #987...
✓ Release obtenido: Release-987

─────────────────────────────────────────────────────────────
FASE 2: Crear Backup Versionado
─────────────────────────────────────────────────────────────
✓ Backup guardado: ./outcome/backups/release_backup_REL_987_20260619_140530.json
  Versión: REL_987_20260619_140530

─────────────────────────────────────────────────────────────
FASE 3: Crear Nuevo Release
─────────────────────────────────────────────────────────────
>>> Creando nuevo Release...
  Descripción: Re-release desde #987 [Backup: REL_987_20260619_140530]...
✓ Release creado exitosamente

═══════════════════════════════════════════════════════════════
  ✅ RE-RELEASE EXITOSO
═══════════════════════════════════════════════════════════════
Release origen:     #987
Nuevo Release:      #1234
Nombre:             Release-1234
Backup:             REL_987_20260619_140530
Comentario:         Motivo del re-release
URL:                https://dev.azure.com/Coppel-Retail/...
═══════════════════════════════════════════════════════════════

📄 Reporte exportado: outcome/re_release_report_20260619_140530.json
```

### Tool 24: Pipeline Restore Release

```bash
# Modo interactivo (recomendado)
python scm/azdo/pipeline_cd_restore_release.py --interactive

# Modo directo con parámetros
python scm/azdo/pipeline_cd_restore_release.py \
  --org Coppel-Retail \
  --project Cadena_de_Suministros \
  --backup-file release_backup_REL_987_20260619_140530.json \
  --restore-comment "Motivo del restore" \
  --pat YOUR_PAT_HERE \
  --backup-path ./outcome/backups
```

**Salida esperada**:
```
═══════════════════════════════════════════════════════════════
  Azure DevOps Pipeline Restore v1.0.0
═══════════════════════════════════════════════════════════════

─────────────────────────────────────────────────────────────
FASE 1: Cargar Backup
─────────────────────────────────────────────────────────────
>>> Cargando backup desde: release_backup_REL_987_20260619_140530.json
✓ Backup cargado correctamente

─────────────────────────────────────────────────────────────
FASE 2: Validación del Backup
─────────────────────────────────────────────────────────────

╔══════════════════════════════════════════════════╗
║           INFORMACIÓN DEL BACKUP                ║
╠══════════════════════════════════════════════════╣
║  Versión Label  : REL_987_20260619_140530
║  Release Origen : #987
║  Fecha Backup   : 2026-06-19 14:05:30
║  Generado por   : pipeline_cd_new_re_release.py
║  Pipeline       : Cadena_de_Suministros
║  Artefactos     : 3
╚══════════════════════════════════════════════════╝

¿Confirmas el RESTORE desde este backup? (S/N): S

─────────────────────────────────────────────────────────────
FASE 3: Crear Release de Restore
─────────────────────────────────────────────────────────────

>>> Creando Release de Restore...
✓ Release de Restore creado exitosamente

═══════════════════════════════════════════════════════════════
  ✅ RESTORE EXITOSO
═══════════════════════════════════════════════════════════════
Backup Origen:      REL_987_20260619_140530
Release Origen:     #987
Nuevo Release:      #1235
Nombre:             Release-1235
Comentario:         Motivo del restore
URL:                https://dev.azure.com/Coppel-Retail/...
═══════════════════════════════════════════════════════════════

📄 Reporte exportado: outcome/restore_release_report_20260619_140545.json
```

---

## 📁 Estructura de Archivos

```
devsecops-toolbox/
├── scm/
│   ├── config.json                              (carga config)
│   └── azdo/
│       ├── tools.py                             (actualizado)
│       ├── pipeline_cd_new_re_release.py        (nuevo)
│       ├── pipeline_cd_restore_release.py       (nuevo)
│       ├── pipeline-cd-new-re-release.sh        (legacy)
│       └── pipeline-cd-restore-release.sh       (legacy)
├── outcome/
│   ├── backups/                                 (backups versionados)
│   │   ├── release_backup_REL_987_*.json
│   │   └── ...
│   ├── re_release_report_*.json                 (reportes)
│   └── restore_release_report_*.json            (reportes)
└── IMPLEMENTACION_PYTHON_TOOLS.md               (este archivo)
```

---

## 🔄 Flujo de Ejecución desde tools.py

```
┌─────────────────────────────────────────────────────────────┐
│ Usuario selecciona opción 23 o 24 en tools.py              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ tools.py lee PLATFORMS["23"] o PLATFORMS["24"]             │
│ • Extrae: path, args, defaults                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Construye comando Python con parámetros                    │
│ Ejemplo para Tool 23:                                       │
│   python scm/azdo/pipeline_cd_new_re_release.py \          │
│     --org Coppel-Retail \                                   │
│     --project Cadena_de_Suministros \                       │
│     --source-release-id 999999 \                            │
│     --release-comment "Renovacion de Credenciales Git" \    │
│     --pat "" \                                              │
│     --backup-path ./outcome/backups                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Script Python se ejecuta                                   │
│ • Carga config.json si existe                              │
│ • Solicita parámetros faltantes interactivamente           │
│ • Ejecuta 3-4 fases de procesamiento                       │
│ • Exporta reporte JSON a outcome/                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Resultado mostrado en consola                              │
│ ✅ ÉXITO o ❌ ERROR                                         │
│ 📄 Reporte en outcome/                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Características de Seguridad

### Tool 23 (Re-Release)
- ✅ Confirmación antes de crear release
- ✅ Backup automático versionado
- ✅ Trazabilidad completa en descripción
- ✅ Reporte JSON exportado
- ✅ Manejo de errores HTTP

### Tool 24 (Restore)
- ✅ Confirmación interactiva antes de restore
- ✅ Tabla de información del backup
- ✅ Búsqueda automática de archivos
- ✅ Validación de JSON
- ✅ Trazabilidad en descripción del release
- ✅ Reporte JSON exportado

---

## 📝 Configuración en config.json

```json
{
  "azdo": {
    "organization_url": "https://dev.azure.com/Coppel-Retail",
    "project": "Cadena_de_Suministros",
    "pat": "YOUR_PAT_HERE",
    "pipeline_re_release": {
      "source_release_id": 999999,
      "release_comment": "Renovacion de Credenciales Git",
      "backup_path": "./outcome/backups"
    },
    "pipeline_restore_release": {
      "backup_file": "",
      "restore_comment": "Restore automático desde tools.py",
      "backup_path": "./outcome/backups"
    }
  }
}
```

---

## ✅ Checklist de Validación

- [x] Scripts Python creados con patrón consistente
- [x] Carga de config.json implementada
- [x] Modo interactivo con `--interactive`
- [x] Colores ANSI para terminal
- [x] Argumentos con defaults configurados
- [x] Exportación de reportes JSON
- [x] Confirmación antes de ejecutar
- [x] Manejo de errores completo
- [x] tools.py actualizado
- [x] Commits realizados

---

## 🚀 Próximos Pasos

1. **Prueba en desarrollo**:
   ```bash
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

3. **Crear backups** ejecutando Tool 23
4. **Restaurar** usando Tool 24 con backups creados

---

## 📊 Estadísticas

| Métrica | Valor |
|---------|-------|
| Líneas Tool 23 | 422 |
| Líneas Tool 24 | 418 |
| Total líneas | 840 |
| Funciones Tool 23 | 8 |
| Funciones Tool 24 | 8 |
| Parámetros Tool 23 | 6 |
| Parámetros Tool 24 | 6 |
| Fases Tool 23 | 3 |
| Fases Tool 24 | 3 |

---

## 📞 Contacto

Para preguntas o problemas:
- Revisar scripts en `scm/azdo/pipeline_cd_*.py`
- Revisar configuración en `scm/azdo/tools.py`
- Revisar reportes en `outcome/`
