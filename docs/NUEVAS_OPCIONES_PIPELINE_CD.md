# 🆙 Nuevas Opciones de Actualización de Pipeline CD

## 📍 Ubicación en el Menú

Las nuevas opciones de actualización de Pipeline CD están en el grupo **"Update Pipeline"** (🆙) del menú de Azure DevOps.

```
🆙 Update Pipeline
├── 21 - Pipeline Updater
├── 22 - Pipeline Rollback  
├── 23 - Refresh Release
└── 24 - Pipeline Restore Release
```

---

## 🔧 Herramientas Disponibles

### **21 - Pipeline Updater** (Actualización con Template)

**Descripción**: Actualiza variable branchConfig y scripts de tareas en Release Pipelines vía API REST. Modo interactivo con config.json.

**Archivo**: `scm/azdo/pipeline-cd-update-branchconfig.py`

**Características**:
- ✅ Actualización de variables branchConfig
- ✅ Actualización de scripts de tareas
- ✅ Modo interactivo con config.json
- ✅ Validación de cambios
- ✅ Soporte para múltiples pipelines
- ✅ Exportación JSON de resultados

**Uso**:
```bash
python scm/azdo/pipeline-cd-update-branchconfig.py --interactive
```

---

### **22 - Pipeline Rollback** (Reversión de Cambios)

**Descripción**: Revierte cambios en Release Pipelines con 3 métodos diferentes.

**Archivo**: `scm/azdo/pipeline-cd-rollback-pipeline.py`

**Métodos de Rollback**:

1. **Full Backup Restore** (Máxima Seguridad)
   - Restaura backup completo del pipeline
   - Mejor para cambios críticos
   
2. **Hybrid Rollback** (Revisión del Backup)
   - Obtiene revisión anterior desde Azure DevOps
   - Balance entre seguridad y flexibilidad
   
3. **Manual Revision** (Rollback a Revisión Específica)
   - Rollback a una revisión específica
   - Mayor control granular

**Características**:
- ✅ Listado de backups disponibles
- ✅ Listado de revisiones del pipeline
- ✅ Validación antes de rollback
- ✅ Modo dry-run para preview
- ✅ Logging completo de operaciones

**Uso**:
```bash
# Opción 1: Full Backup Restore
python scm/azdo/pipeline-cd-rollback-pipeline.py --list-backups

# Opción 2: Hybrid Rollback
python scm/azdo/pipeline-cd-rollback-pipeline.py --list-revisions --pipeline-id 123

# Opción 3: Manual Revision
python scm/azdo/pipeline-cd-rollback-pipeline.py --to-revision 44 --pipeline-id 123
```

---

### **23 - Refresh Release** (Crear Nuevo Release)

**Descripción**: Crea Nuevo Release desde uno existente con backup automático versionado. Ideal para renovar variables de grupo y actualizar credenciales Git.

**Archivo**: `scm/azdo/pipeline_cd_new_re_release.py`

**Características**:
- ✅ Copia de Release existente
- ✅ Backup automático versionado
- ✅ Renovación de variables de grupo
- ✅ Actualización de credenciales Git
- ✅ Trazabilidad completa

**Uso**:
```bash
python scm/azdo/pipeline_cd_new_re_release.py \
  --org Coppel-Retail \
  --project Cadena_de_Suministros \
  --source-release-id 123 \
  --release-comment "Renovación de credenciales" \
  --pat <token>
```

---

### **24 - Pipeline Restore Release** (Restaurar desde Backup)

**Descripción**: Restaura un Release desde un backup versionado. Permite rollback completo con trazabilidad y confirmación interactiva.

**Archivo**: `scm/azdo/pipeline_cd_restore_release.py`

**Características**:
- ✅ Restauración desde backup versionado
- ✅ Rollback completo con trazabilidad
- ✅ Confirmación interactiva
- ✅ Validación de integridad
- ✅ Logging de operaciones

**Uso**:
```bash
python scm/azdo/pipeline_cd_restore_release.py \
  --org Coppel-Retail \
  --project Cadena_de_Suministros \
  --backup-file outcome/backups/release_123_20260713_100000.json \
  --restore-comment "Restauración de backup" \
  --pat <token>
```

---

## 🚀 Acceso desde el Menú Principal

### Opción 1: Desde el Menú de Azure DevOps

```bash
python scm/main.py
# Seleccionar: [1] 🔷 AZDO (Azure DevOps)
# Luego seleccionar: [21], [22], [23] o [24]
```

### Opción 2: Desde el Menú de AZDO Directamente

```bash
python scm/azdo/tools.py
# Seleccionar: [21], [22], [23] o [24]
```

---

## 📋 Comparación de Opciones

| Opción | Propósito | Método | Seguridad | Velocidad |
|--------|-----------|--------|-----------|-----------|
| **21** | Actualizar variables | API REST | Alta | Rápida |
| **22** | Revertir cambios | Backup/Revisión | Muy Alta | Media |
| **23** | Crear nuevo release | Copia + Backup | Alta | Media |
| **24** | Restaurar desde backup | Backup versionado | Muy Alta | Rápida |

---

## 💡 Casos de Uso

### Caso 1: Actualizar branchConfig en múltiples pipelines
```
Usar: Opción 21 (Pipeline Updater)
Pasos:
1. Ejecutar con --interactive
2. Seleccionar pipelines
3. Actualizar variables
4. Confirmar cambios
```

### Caso 2: Revertir cambios críticos
```
Usar: Opción 22 (Pipeline Rollback)
Pasos:
1. Listar backups disponibles
2. Seleccionar backup o revisión
3. Ejecutar dry-run para preview
4. Confirmar rollback
```

### Caso 3: Renovar credenciales Git
```
Usar: Opción 23 (Refresh Release)
Pasos:
1. Seleccionar release existente
2. Crear nuevo release con backup
3. Actualizar variables de grupo
4. Validar nuevo release
```

### Caso 4: Restaurar desde backup versionado
```
Usar: Opción 24 (Pipeline Restore Release)
Pasos:
1. Listar backups disponibles
2. Seleccionar backup
3. Confirmar restauración
4. Validar integridad
```

---

## 🔐 Configuración Requerida

Todas las herramientas requieren:

1. **config.json** con:
   - `pat`: Personal Access Token de Azure DevOps
   - `org`: Organización (ej: Coppel-Retail)
   - `project`: Proyecto (ej: Cadena_de_Suministros)

2. **Permisos en Azure DevOps**:
   - Release Pipelines: Editar
   - Versioning: Ver y crear revisiones
   - Backups: Crear y restaurar

---

## 📊 Salida y Reportes

Todas las herramientas generan:

- **Consola**: Salida formateada con Rich
- **JSON**: `outcome/results_*.json` para integración
- **Logs**: `outcome/*_*.log` para auditoría
- **Backups**: `outcome/backups/` para recuperación

---

## 🆘 Troubleshooting

### Error: "Módulo no encontrado"
```bash
# Asegúrate de estar en la raíz del proyecto
cd devsecops-toolbox
python scm/main.py
```

### Error: "PAT inválido"
```bash
# Verifica config.json
cat config.json
# O reconfigura
python scm/main.py
# Selecciona opción para configurar
```

### Error: "Pipeline no encontrado"
```bash
# Verifica el definition-id
# Usa la herramienta de inventario (opción 9) para listar pipelines
```

---

## 📚 Documentación Adicional

- [Pipeline Rollback Detallado](../docs/features/feature_actualizacion_pipeline_cd_with_template/)
- [Azure DevOps API Reference](https://learn.microsoft.com/en-us/rest/api/azure/devops/)
- [README Principal](../README.md)

---

**Última Actualización**: 13 de Julio de 2026  
**Versión**: 1.6.20+
