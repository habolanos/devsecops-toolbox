# 🔧 FIX: Habilitar Service Accounts Reporter en config.json

**Problema:** 
```
❌ Service Accounts Reporter no está habilitado en config.json
```

---

## ✅ Solución Rápida

### Paso 1: Editar tu config.json

```bash
# En Windows
notepad scm\config.json

# En Linux/Mac
nano scm/config.json
```

### Paso 2: Buscar esta línea

```json
"service_accounts_reporter": {
  "_info": "Configuración para el reporte multi-proyecto de service accounts (Tool 38)",
  "enabled": false,  ← CAMBIAR ESTO
```

### Paso 3: Cambiar a true

```json
"service_accounts_reporter": {
  "_info": "Configuración para el reporte multi-proyecto de service accounts (Tool 38)",
  "enabled": true,  ← CAMBIO REALIZADO
```

### Paso 4: Guardar el archivo

- **Windows:** Ctrl+S
- **Linux/Mac:** Ctrl+X → Y → Enter

---

## 🎯 Verificación

Después de cambiar, tu sección debe verse así:

```json
"service_accounts_reporter": {
  "_info": "Configuración para el reporte multi-proyecto de service accounts (Tool 38)",
  "enabled": true,
  "_enabled_info": "Cambiar a false para deshabilitar el reporte de service accounts",
  
  "projects": [
    "cpl-cmanager-dev-13072023",
    "cpl-cmanager-qa-13072023",
    "cpl-cmanager-stag-01052025",
    "cpl-cs-csc-dev-16112023",
    "cpl-cs-csc-qa-16112023",
    "cpl-cs-csc-stag-11042025",
    "cpl-cs-wms-dev-30112023",
    "cpl-cs-wms-qa-30112023",
    "cpl-cs-wms-stag-09042025",
    "cpl-oms-dev-08082024",
    "cpl-oms-qa-08062023",
    "cpl-oms-stag-09042025"
  ],
  ...
}
```

---

## 🚀 Ahora Ejecuta

```bash
python scm/gcp/tools.py
# Seleccionar [38]
# Elegir formato: csv
```

**Debería funcionar correctamente ahora.**

---

## 📝 Notas

- `config.json` es tu archivo personal (no se sube a git)
- `config.json.template` es el template (ya está actualizado con `enabled: true`)
- Siempre edita tu `config.json`, no el template

---

**Versión:** 1.0.0  
**Fecha:** 8 de Julio de 2026  
**Estado:** ✅ SOLUCIÓN RÁPIDA

