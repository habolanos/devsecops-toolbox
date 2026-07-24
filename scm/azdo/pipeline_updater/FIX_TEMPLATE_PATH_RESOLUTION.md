# 🔧 Fix: Resolución Correcta de Ruta del Template

**Fecha:** 24 de Julio de 2026  
**Versión:** 1.0  
**Status:** ✅ COMPLETADO

---

## 🐛 Problema

Cuando se ejecutaba la herramienta 41 (Pipeline Updater) con una ruta de template relativa, se duplicaba la ruta:

```
❌ Template no encontrado: /mnt/c/Users/harold.bolanos/repos-publics/devsecops-toolbox/scm/azdo/scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
                                                                                          ↑ DUPLICADO
```

**Causa:** El script se ejecutaba desde `BASE_DIR` (que es `scm/azdo`), pero la ruta del template se pasaba como relativa desde la raíz del proyecto, sin resolver correctamente.

---

## ✅ Solución

Se agregó lógica en `pipeline_updater.py` para resolver correctamente la ruta del template desde la raíz del proyecto:

```python
# Resolver ruta del template desde la raíz del proyecto
# El script se ejecuta desde scm/azdo (cwd=BASE_DIR), así que necesitamos subir 2 niveles
template_path = Path(args.template)
if not template_path.is_absolute():
    # Obtener la raíz del proyecto (2 niveles arriba de scm/azdo)
    # __file__ = /ruta/scm/azdo/pipeline_updater/pipeline_updater.py
    # .parent = /ruta/scm/azdo/pipeline_updater/
    # .parent = /ruta/scm/azdo/
    # .parent = /ruta/scm/
    # .parent = /ruta/ (raíz)
    script_dir = Path(__file__).parent.parent.parent.parent  # scm/azdo/pipeline_updater -> raíz
    template_path = script_dir / args.template
```

**Explicación:**

1. **`Path(__file__)`** - Obtiene la ruta del script actual (`pipeline_updater.py`)
2. **`.parent.parent.parent.parent`** - Sube 4 niveles:
   - `.parent` → `scm/azdo/pipeline_updater/` → `scm/azdo/`
   - `.parent` → `scm/azdo/` → `scm/`
   - `.parent` → `scm/` → raíz del proyecto
   - `.parent` → raíz del proyecto (confirmación)
3. **`script_dir / args.template`** - Resuelve la ruta relativa desde la raíz

---

## 📊 Antes vs Después

### ❌ ANTES (Problema)

```
Entrada: scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
Ejecución desde: scm/azdo/
Ruta resultante: scm/azdo/scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
                 ↑ DUPLICADO
```

### ✅ DESPUÉS (Solución)

```
Entrada: scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
Ejecución desde: scm/azdo/
Ruta resuelta: /ruta/completa/devsecops-toolbox/scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
               ✅ CORRECTA
```

---

## 🧪 Casos de Uso

### Caso 1: Ruta Relativa (Recomendado)

```bash
# Entrada
--template scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml

# Resolución
script_dir = /ruta/raíz/devsecops-toolbox
template_path = /ruta/raíz/devsecops-toolbox/scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
✅ CORRECTO
```

### Caso 2: Ruta Absoluta

```bash
# Entrada
--template /ruta/completa/scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml

# Resolución
template_path.is_absolute() = True
template_path = /ruta/completa/scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
✅ CORRECTO (sin cambios)
```

### Caso 3: Ruta Relativa Corta

```bash
# Entrada
--template templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml

# Resolución
script_dir = /ruta/raíz/devsecops-toolbox
template_path = /ruta/raíz/devsecops-toolbox/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
❌ NO ENCONTRADO (porque está en scm/templates, no templates/)
```

---

## 🎯 Cómo Usar

### Opción 1: Ruta Relativa desde Raíz (Recomendado)

```bash
# En la herramienta 41, ingresar:
Ruta del template YAML: scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
```

### Opción 2: Ruta Absoluta

```bash
# En la herramienta 41, ingresar:
Ruta del template YAML: /ruta/completa/devsecops-toolbox/scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
```

---

## 📝 Cambios Realizados

**Archivo:** `scm/azdo/pipeline_updater/pipeline_updater.py`

**Líneas modificadas:** 308-314

**Cambios:**
- Agregada lógica para resolver ruta relativa desde la raíz del proyecto
- Soporta rutas absolutas sin cambios
- Evita duplicación de rutas

---

## ✅ Validación

**Test realizado:**

```bash
# Entrada
Definition IDs: 2758,2759,2760
Template: scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml

# Resultado
✅ Template encontrado correctamente
✅ Actualización ejecutada sin errores
```

---

## 🔗 Referencias

- `scm/azdo/pipeline_updater/pipeline_updater.py` - Script corregido
- `scm/templates/` - Ubicación de templates
- Tool 41 - Pipeline Updater (herramienta que usa este fix)

---

## 📚 Documentación Relacionada

- `IMPLEMENTACION_EXACT_MATCH.md` - Implementación del parámetro exact_match
- `VALIDACION_EXACTA_STAGES.md` - Especificación del parámetro exact_match
- `operation/pipeline_cd_updating/README.md` - Guía de actualización de pipelines

---

**Status:** ✅ FIX COMPLETADO  
**Commit:** e7476e3  
**Versión:** 1.0
