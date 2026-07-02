# Fix: NameError en tools.py (AZDO, GCP, AWS)

**Fecha:** 29 de Junio de 2026  
**Versión:** v1.6.13-dev  
**Commit:** d048494

---

## 🔴 PROBLEMA IDENTIFICADO

Cuando se intentaba acceder a **GCP**, **AZDO** o **AWS** desde el menú principal, se lanzaba un error:

```
NameError: name 'build_system_options' is not defined
```

### Causa Raíz

En los archivos `tools.py` de las tres plataformas (AZDO, GCP, AWS), la función `_init_system_options()` se llamaba **antes** de que la función `build_system_options()` estuviera definida.

**Estructura del problema:**

```python
# Línea ~390-395 (AZDO), ~363-367 (GCP), ~316-320 (AWS)
def _init_system_options():
    """Inicializa las opciones de sistema."""
    build_system_options()  # ❌ build_system_options aún no está definida

_init_system_options()  # ❌ Se llama inmediatamente

# ... mucho código ...

# Línea ~671 (AZDO), ~470 (GCP), ~421 (AWS)
def build_system_options():  # ✅ Se define aquí, pero ya es demasiado tarde
    """Construye las opciones de sistema dinámicamente."""
    # ...
```

---

## ✅ SOLUCIÓN IMPLEMENTADA

Se movió la llamada a `_init_system_options()` al **final del archivo**, después de que todas las funciones necesarias estén definidas.

### Cambios Realizados

**Antes:**
```python
# Línea ~390-395
def _init_system_options():
    build_system_options()

_init_system_options()  # ❌ Llamada inmediata (error)
```

**Después:**
```python
# Línea ~390-395
def _init_system_options():
    build_system_options()

# NOTA: _init_system_options() se llama al final del archivo

# ... todas las funciones se definen ...

# Línea ~1950 (AZDO), ~1240 (GCP), ~1040 (AWS)
# ═══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
# Inicializar opciones de sistema después de que todas las funciones estén definidas
_init_system_options()  # ✅ Llamada al final (correcto)
```

### Archivos Modificados

1. `scm/azdo/tools.py` (líneas 389-395, 1952-1956)
2. `scm/gcp/tools.py` (líneas 362-368, 1241-1245)
3. `scm/aws/tools.py` (líneas 315-321, 1042-1046)

---

## 🧪 VERIFICACIÓN

Se creó un script de diagnóstico (`scripts/diagnose_import_error.py`) que verifica:

```bash
python scripts/diagnose_import_error.py
```

**Resultado después del fix:**
```
✅ Módulo azdo/tools.py cargado exitosamente
✅ Módulo gcp/tools.py cargado exitosamente
✅ Módulo aws/tools.py cargado exitosamente
```

---

## 📋 CHECKLIST

- ✅ Problema identificado
- ✅ Causa raíz encontrada
- ✅ Solución implementada en AZDO
- ✅ Solución implementada en GCP
- ✅ Solución implementada en AWS
- ✅ Script de diagnóstico creado
- ✅ Verificación exitosa
- ✅ Commit realizado (d048494)
- ✅ Documentación creada

---

## 🔗 ARCHIVOS MODIFICADOS

```
scm/azdo/tools.py (líneas 389-395, 1952-1956)
scm/gcp/tools.py (líneas 362-368, 1241-1245)
scm/aws/tools.py (líneas 315-321, 1042-1046)
scripts/diagnose_import_error.py (nuevo)
```

---

## 💡 LECCIONES APRENDIDAS

1. **Orden de definición importa** - Las funciones deben estar definidas antes de ser llamadas
2. **Inicialización tardía** - Es mejor inicializar al final del archivo cuando todo está listo
3. **Diagnóstico es clave** - Un buen script de diagnóstico ayuda a identificar problemas rápidamente
4. **Consistencia** - El mismo patrón se aplicó a los tres archivos para mantener consistencia

---

## 🚀 PRÓXIMOS PASOS

1. ✅ Probar acceso a AZDO desde el menú principal
2. ✅ Probar acceso a GCP desde el menú principal
3. ✅ Probar acceso a AWS desde el menú principal
4. ✅ Confirmar que no hay errores de NameError

---

**Estado:** ✅ COMPLETADO  
**Impacto:** Alto - Afecta a AZDO, GCP y AWS  
**Riesgo:** Bajo - Solo reordena código, no cambia lógica  
**Retrocompatibilidad:** 100% - No cambia comportamiento, solo lo corrige

---

**Creado:** 29 de Junio de 2026  
**Autor:** Harold Adrian  
**Versión:** v1.6.13-dev
