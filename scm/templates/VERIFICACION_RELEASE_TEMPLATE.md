# Verificación Completa: Template Release Update Task Script and Contents

**Fecha:** 7 de Septiembre de 2026  
**Template:** `release_update_task_script_and_contents.yaml`  
**Versión:** 1.0  
**Status:** ✅ VERIFICADO

---

## 1. Verificación de Estructura YAML

### ✅ Secciones Requeridas
- [x] `metadata` - Información del template
- [x] `release` - Configuración de releases (ids vacío para modo interactivo)
- [x] `search` - Criterios de búsqueda (stages y tasks)
- [x] `update` - Reglas de actualización
- [x] `options` - Opciones de ejecución

### ✅ Campos de Metadata
- [x] `name` - Descripción clara del template
- [x] `version` - Versión 1.0
- [x] `description` - Descripción técnica
- [x] `comment` - Caso de uso y notas
- [x] `author` - DevOps Team
- [x] `created_at` - Fecha de creación

### ✅ Configuración Release
```yaml
release:
  ids: []  # Vacío: se especifica vía --release-id o modo interactivo
```

### ✅ Búsqueda (Search)
```yaml
search:
  stages:
    - name: "Develop"
    - name: "QA"
    - pattern: "^\\d{2}-"  # Regex: 01-*, 02-*, etc.
  
  tasks:
    - name: "DataDog"
    - name: "SFTP Properties $(host)"
```

**Validación:**
- ✅ Stages: 2 fixed + 1 pattern = hasta 34+ stages
- ✅ Tasks: 2 tasks específicas
- ✅ Patrón regex válido: `^\\d{2}-` (2 dígitos + guion)

### ✅ Actualización (Update)
```yaml
update:
  global_vars: []
  env_vars: []
  
  tasks:
    - name: "DataDog"
      fields:
        - path: "inputs.script"
          new_value: |
            [script bash/powershell]
    
    - name: "SFTP Properties $(host)"
      fields:
        - path: "inputs.contents"
          new_value: |
            [contenido de archivos]
```

**Validación:**
- ✅ 2 tasks a actualizar
- ✅ Paths correctos: `inputs.script` y `inputs.contents`
- ✅ new_value con contenido válido
- ✅ `abandon: false` (no abandonar releases)

### ✅ Opciones (Options)
```yaml
options:
  dry_run: true  # Inicialmente en true para verificación
  backup_path: "./outcome/backups"
```

**Validación:**
- ✅ `dry_run: true` para modo seguro
- ✅ `backup_path` especificado

---

## 2. Compatibilidad con Release Updater (Tool 42)

### ✅ Verificación de Compatibilidad

**Archivo:** `pipeline_cd_update_release.py`

**Características soportadas:**
- ✅ Búsqueda por nombre exacto de stage
- ✅ Búsqueda por patrón regex de stage
- ✅ Búsqueda de tasks por nombre
- ✅ Actualización de campos de task (inputs.*)
- ✅ Modo dry-run
- ✅ Backup automático
- ✅ Modo interactivo (release-id vacío)

**Campos soportados:**
- ✅ `metadata.*` - Cargado correctamente
- ✅ `release.ids` - Vacío para modo interactivo
- ✅ `search.stages[].name` - Fixed stages
- ✅ `search.stages[].pattern` - Pattern stages
- ✅ `search.tasks[].name` - Task names
- ✅ `update.tasks[].fields[].path` - Nested paths
- ✅ `update.tasks[].fields[].new_value` - Valores nuevos
- ✅ `options.dry_run` - Modo simulación
- ✅ `options.backup_path` - Ruta de backup

---

## 3. Escenarios de Prueba

### Escenario 1: Búsqueda de Stages
**Esperado:** Encontrar stages Develop, QA, 01-Culiacan, 02-Leon, ... 31-IMPTecamac

```
Stages encontrados:
- Develop (fixed)
- QA (fixed)
- 01-Culiacan (pattern)
- 02-Leon (pattern)
- ... (hasta 31-IMPTecamac)
Total: ~34 stages
```

### Escenario 2: Búsqueda de Tasks
**Esperado:** Encontrar 2 tasks por stage

```
Tasks encontradas por stage:
- DataDog (inputs.script)
- SFTP Properties $(host) (inputs.contents)
Total: 2 tasks × 34 stages = 68 matches
```

### Escenario 3: Actualización de Fields
**Esperado:** Actualizar inputs.script e inputs.contents

```
Cambios aplicados:
- DataDog: inputs.script → [nuevo script]
- SFTP Properties: inputs.contents → [nuevo contenido]
Total: 2 cambios × 34 stages = 68 cambios
```

---

## 4. Checklist de Validación

### Pre-ejecución
- [x] Template YAML válido (sintaxis correcta)
- [x] Metadata completa
- [x] Stages configurados (fixed + pattern)
- [x] Tasks configuradas
- [x] Paths de actualización válidos
- [x] new_value con contenido
- [x] dry_run: true (seguro)
- [x] backup_path especificado

### Ejecución Dry-Run
- [ ] Release cargado correctamente
- [ ] Stages encontrados: ~34
- [ ] Tasks encontradas: ~68
- [ ] Cambios a aplicar: ~68
- [ ] Sin errores de sintaxis
- [ ] Sin errores de búsqueda
- [ ] Sin errores de actualización

### Post-ejecución
- [ ] Reportes generados (JSON, CSV, HTML)
- [ ] Backup creado
- [ ] Cambios verificables en reporte
- [ ] Sin cambios reales (dry-run)

---

## 5. Diferencias con Template CD

| Aspecto | CD (pipe_cd_update_task_script_and_contents.yaml) | Release (release_update_task_script_and_contents.yaml) |
|--------|--------------------------------------------------|-----------------------------------------------------|
| Tipo | Pipeline Definition | Release Definition |
| Tool | Pipeline Updater | Release Updater (Tool 42) |
| Entrada | Pipeline ID | Release ID |
| Stages | Environments | Environments |
| Tasks | workflowTasks / deploymentInput.tasks | tasks |
| Búsqueda | search.stages + search.tasks | search.stages + search.tasks |
| Actualización | update.tasks | update.tasks |
| Contenido | Idéntico | Idéntico |

---

## 6. Próximos Pasos

### Fase 1: Verificación (ACTUAL)
1. ✅ Estructura YAML validada
2. ✅ Compatibilidad verificada
3. ⏳ Ejecutar dry-run con release existente

### Fase 2: Ejecución
1. Ejecutar dry-run
2. Verificar matches encontrados
3. Ejecutar actualización real
4. Verificar cambios aplicados

### Fase 3: Documentación
1. Actualizar README.md
2. Crear ejemplos de uso
3. Documentar troubleshooting

---

## 7. Notas Importantes

- **Compatibilidad:** Template es idéntico al de CD pero para releases
- **Seguridad:** dry_run: true por defecto (cambiar a false para actualizar)
- **Backup:** Automático en ./outcome/backups
- **Patrón Regex:** `^\\d{2}-` coincide con 01-*, 02-*, ... 99-*
- **Release ID:** Vacío para modo interactivo (seleccionar release en menú)

---

**Status:** ✅ VERIFICACIÓN COMPLETADA - LISTO PARA TESTING

