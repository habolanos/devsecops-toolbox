# 📋 Templates para Pipeline Updater

Esta carpeta contiene templates YAML de ejemplo para actualizar masivamente pipelines CD en Azure DevOps.

---

## 📁 Templates Disponibles

### **pipe_cd_update_docker.yaml**
Cambiar imagen Docker en pipelines de producción.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_update_docker.yaml
```

---

### **pipe_cd_update_kubernetes.yaml**
Cambiar cluster Kubernetes y namespace.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_update_kubernetes.yaml
```

---

### **pipe_cd_update_variables.yaml**
Cambiar variables de entorno (ENVIRONMENT, etc).

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_update_variables.yaml
```

---

### **pipe_cd_update_azure.yaml**
Cambiar suscripción Azure en tasks.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_update_azure.yaml
```

---

### **pipe_cd_update_script.yaml**
Cambiar contenido de scripts PowerShell.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_update_script.yaml
```

---

### **pipe_cd_update_migracion.yaml**
Realizar múltiples cambios simultáneamente (imagen, cluster, variables).

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_update_migracion.yaml
```

---

### **pipe_cd_reorder_stages_basic.yaml** 🆕
Reordenar stages usando `rank` - Cambio de orden básico.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_reorder_stages_basic.yaml
```

**Ejemplo**:
```
Antes:  Build → Test → Deploy → Validate
Después: Build → Deploy → Test → Validate
```

---

### **pipe_cd_reorder_stages_with_dependencies.yaml** 🆕
Reordenar stages Y actualizar dependencias automáticamente.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_reorder_stages_with_dependencies.yaml
```

**Ejemplo**:
```
Antes:  QA → Staging → Producción
Después: Staging → QA → Producción
(Producción ahora depende de QA)
```

---

### **pipe_cd_insert_security_stage.yaml** 🆕
Insertar nuevo stage de seguridad en posición específica.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_insert_security_stage.yaml
```

**Ejemplo**:
```
Antes:  Build → Deploy → Producción
Después: Build → Security Check → Deploy → Producción
```

---

### **pipe_cd_insert_stage_with_n_tasks.yaml** 🆕
Insertar un nuevo stage con N tasks, configurar triggers y artifact branch filters, actualizar dependencias y reordenar por rank.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_insert_stage_with_n_tasks.yaml
```

**Ejemplo**:
```
Antes:  Staging → Producción
Después: Staging → Pre Deploy Validation → Producción

- Pre Deploy Validation contiene 3 tasks (Unit Tests, Security Scan, Smoke Tests)
- Producción depende de Pre Deploy Validation (no de Staging)
- Artifact trigger configurado con branch filter: refs/heads/main
- Artifact branch filter actualizado a "main"
```

**Características**:
- Stage con N tasks escalable (copiar y pegar bloques de task)
- Triggers: `action: add` / `update` / `remove` con `branchFilters`
- Artifact filters: actualizar `definitionReference.branch.id` y `.name`
- Reordenamiento por `rank`
- Dependencias entre stages actualizadas automáticamente

---

### **pipe_cd_move_to_folder.yaml** 🆕
Mover pipelines CD a otra carpeta dentro del proyecto de Azure DevOps.

Soporta el placeholder `{current}` para mover preservando el path relativo.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_move_to_folder.yaml
```

**Ejemplo**:
```
path: '\Decomiso{current}'
# Si el path actual es \GCP\Proyecto WMS
# Resultado: \Decomiso\GCP\Proyecto WMS
```

---

### **pipe_cd_autosort_stages.yaml** 🆕
Auto-ordenar stages numericos alfanumericamente, manteniendo fijos los stages no numericos.

**Comportamiento**:
1. Los stages en `fixed_stages` mantienen su posicion original
2. Los stages que coinciden con `sort_pattern` (default: empiezan con numero) se ordenan alfanumericamente
3. Todos los ranks se renumeran consecutivamente (1..N)

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 41
# Ingresar: scm/templates/pipe_cd_autosort_stages.yaml
```

**Ejemplo**:
```
Antes:  Develop → QA → Production → 03-Laguna → 01-Culiacan → 02-Leon
Después: Develop → QA → Production → 01-Culiacan → 02-Leon → 03-Laguna
```

**Opciones configurables**:
- `fixed_stages`: lista de stages que no se reordenan (default: Develop, QA, Production)
- `sort_pattern`: regex para identificar stages a ordenar (default: `^\d+`)
- `sort_order`: `asc` (ascendente) o `desc` (descendente)

---

## 🚀 Cómo Usar

### **Templates para Tool 41 (Pipeline Updater Template)**

Estos templates modifican **definiciones** de pipelines CD (Release Definitions).

### **Templates para Tool 42 (Release Updater Template)** 🆕

Estos templates modifican **releases existentes** (por releaseId) via PATCH API.

#### **release_update_git_credentials.yaml**
Renueva credenciales Git (GIT_USER, GIT_PASS) en releases existentes.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 42
# Ingresar: --template scm/templates/release_update_git_credentials.yaml --release-id 987 --pat TOKEN
```

#### **release_update_node_version.yaml**
Actualiza NODE_VERSION por environment (QA=18, PROD=20).

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 42
# Ingresar: --template scm/templates/release_update_node_version.yaml --release-id 987 --pat TOKEN
```

#### **release_abandon_stale.yaml**
Marca releases como abandoned para limpieza trimestral.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 42
# Ingresar: --template scm/templates/release_abandon_stale.yaml --release-id 987,988 --pat TOKEN
```

### **Estructura de Templates Tool 42**

```yaml
metadata:
  name: "Nombre del template"
  version: "1.0"
  description: "Descripcion"

release:
  ids: []  # IDs de releases, o vacio para usar --release-id

update:
  global_vars:
    - name: "VAR_NAME"
      value: "new_value"
  env_vars:
    - stage: "QA"
      name: "NODE_VERSION"
      value: "18"
  abandon: false
  description: "Nueva descripcion"

options:
  dry_run: true
  backup_path: "./outcome/backups"
```

**Notas**:
- Los flags CLI (`--set-var`, `--abandon`, etc.) sobrescriben los valores del template
- `--release-id` es requerido si el template no tiene `release.ids`
- `--pat` es siempre requerido (via CLI o config.json)

---

### **Paso 1: Personalizar Template**

Copia uno de los templates y personaliza los valores:

```yaml
metadata:
  name: "Tu nombre"
  comment: "Tu comentario"

search:
  stages: ["Tu stage"]
  tasks:
    - name: "Tu task"

update:
  tasks:
    - name: "Tu task"
      fields:
        - path: "inputs.tuPropiedad"
          old_value: "valor_actual"
          new_value: "valor_nuevo"
```

### **Paso 2: Guardar Template**

Guarda con un nombre descriptivo:
```
scm/templates/mi-cambio.yaml
```

### **Paso 3: Ejecutar**

```bash
python scm/main.py
```

Luego:
1. Selecciona: **Azure DevOps**
2. Selecciona: **Tool 41 (Pipeline Updater Template)**
3. Ingresa: **definition-ids** (ej: 3388,3389,3390)
4. Ingresa: **ruta del template** (ej: scm/templates/mi-cambio.yaml)
5. Confirma: **Y**

### **Paso 4: Revisar Resultados**

El programa generará un reporte JSON con los cambios aplicados.

---

## 📖 Documentación

Para más información sobre el formato de templates, consulta:

- `docs/features/feature_actualizacion_pipeline_cd_with_template/README.md`
- `docs/features/feature_actualizacion_pipeline_cd_with_template/ESPECIFICACION.md`
- `docs/features/feature_actualizacion_pipeline_cd_with_template/EJEMPLOS.md`

---

## ✅ Checklist Antes de Ejecutar

- [ ] Personalicé el template
- [ ] Verifiqué nombres exactos de stages/tasks
- [ ] Preparé lista de definition-ids
- [ ] Guardé el archivo en `scm/templates/`
- [ ] Leí la documentación
- [ ] Estoy listo para ejecutar

---

## 🔒 Seguridad

✅ Validación automática de estructura  
✅ Confirmación del usuario antes de ejecutar  
✅ Snapshots automáticos antes de cambios  
✅ Rollback automático si algo falla  
✅ Auditoría completa en cada pipeline  

---

**Versión**: 1.2  
**Última actualización**: 2026-08-09  
**Estado**: ✅ Listos para usar
