# 🔧 Fix: Resolución Correcta de Ruta del Template

**Fecha:** 24 de Julio de 2026  
**Versión:** 2.0  
**Status:** ✅ COMPLETADO

---

## 🐛 Problema

Cuando se ejecutaba la herramienta 41 (Pipeline Updater) con una ruta de template relativa, se duplicaba la ruta:

```
❌ Template no encontrado: /mnt/c/Users/harold.bolanos/repos-publics/devsecops-toolbox/scm/azdo/scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
                                                                                          ↑ DUPLICADO
```

**Causa Raíz:** El script se ejecuta con `cwd=BASE_DIR` (que es `scm/azdo`), así que cuando se pasaba una ruta relativa como `scm/templates/...`, se interpretaba como relativa a `scm/azdo`, resultando en `scm/azdo/scm/templates/...`.

---

## ✅ Solución (v2.0)

Se cambió la estrategia: **resolver la ruta en `tools.py` (antes de ejecutar el script) y pasar la ruta absoluta**.

### En `tools.py`:

```python
# Resolver ruta del template desde la raíz del proyecto
template_path_obj = Path(template_path_input)
if template_path_obj.is_absolute():
    template_full_path = template_path_obj
else:
    # BASE_DIR es scm/azdo, necesitamos subir 2 niveles para llegar a la raíz
    project_root = BASE_DIR.parent.parent
    template_full_path = project_root / template_path_input

# Verificar que el template existe
if not template_full_path.exists():
    print(f"❌ Template no encontrado: {template_full_path}")
    continue

# Pasar la ruta absoluta al script
template_path = str(template_full_path)
```

### En `pipeline_updater.py`:

```python
# La ruta del template se pasa como absoluta desde tools.py
updater = PipelineUpdater(args.pat, args.org, args.project)
result = updater.update_pipelines(
    definition_ids,
    args.template,  # Ya es absoluta
    dry_run=args.dry_run,
    max_workers=args.workers
)
```

**Ventajas:**

1. **Validación temprana:** Se verifica que el template existe antes de ejecutar el script
2. **Ruta absoluta:** El script recibe una ruta absoluta, sin ambigüedades
3. **Más simple:** No hay lógica de resolución en el script

---

## 📊 Antes vs Después

### ❌ ANTES (Problema)

```
Entrada: scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
tools.py: Pasa como relativa
cwd: scm/azdo/
Interpretación: scm/azdo/ + scm/templates/... = scm/azdo/scm/templates/...
                                                 ↑ DUPLICADO
```

### ✅ DESPUÉS (Solución v2.0)

```
Entrada: scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
tools.py: Resuelve a absoluta
         project_root = scm/azdo/../.. = /ruta/devsecops-toolbox/
         template_path = /ruta/devsecops-toolbox/scm/templates/...
Pasa al script: /ruta/completa/devsecops-toolbox/scm/templates/pipe_cd_reorder_stages_exact_match_20260724-T0-0.yaml
                ✅ CORRECTO (absoluta, sin ambigüedades)
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
