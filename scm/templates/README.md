# 📋 Templates para Pipeline Updater

Esta carpeta contiene templates YAML de ejemplo para actualizar masivamente pipelines CD en Azure DevOps.

---

## 📁 Templates Disponibles

### **01_cambiar-docker.yaml**
Cambiar imagen Docker en pipelines de producción.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 21
# Ingresar: scm/templates/01_cambiar-docker.yaml
```

---

### **02_cambiar-k8s.yaml**
Cambiar cluster Kubernetes y namespace.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 21
# Ingresar: scm/templates/02_cambiar-k8s.yaml
```

---

### **03_cambiar-variables.yaml**
Cambiar variables de entorno (ENVIRONMENT, etc).

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 21
# Ingresar: scm/templates/03_cambiar-variables.yaml
```

---

### **04_cambiar-azure.yaml**
Cambiar suscripción Azure en tasks.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 21
# Ingresar: scm/templates/04_cambiar-azure.yaml
```

---

### **05_cambiar-script.yaml**
Cambiar contenido de scripts PowerShell.

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 21
# Ingresar: scm/templates/05_cambiar-script.yaml
```

---

### **06_migracion-completa.yaml**
Realizar múltiples cambios simultáneamente (imagen, cluster, variables).

**Uso**:
```bash
python scm/main.py
# Seleccionar: Azure DevOps → Tool 21
# Ingresar: scm/templates/06_migracion-completa.yaml
```

---

## 🚀 Cómo Usar

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
2. Selecciona: **Tool 21 (Pipeline Updater)**
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

**Versión**: 1.0  
**Última actualización**: 2026-07-13  
**Estado**: ✅ Listos para usar
