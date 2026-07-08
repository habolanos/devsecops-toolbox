# ⚡ Configuración Rápida - Service Accounts Reporter

**Fecha:** 8 de Julio de 2026  
**Estado:** ✅ GUÍA RÁPIDA

---

## 🎯 El Problema

```
❌ Errores de configuración:
   - No hay proyectos configurados en config.json

💡 Solución: Especifica --projects o configura config.json
```

---

## ✅ Solución Rápida (2 minutos)

### Opción 1: Configurar en config.json (Recomendado)

#### Paso 1: Abrir config.json

```bash
# Si no existe, copiar del template
cp scm/config.json.template scm/config.json

# Luego editar
nano scm/config.json
# o en Windows
notepad scm\config.json
```

#### Paso 2: Buscar la sección GCP

Encuentra esta sección:
```json
"gcp": {
  "enabled": true,
  "project_id": "<TU_PROJECT_ID>",
  "region": "us-central1",
  ...
```

#### Paso 3: Agregar proyectos

Dentro de `"gcp"`, busca `"service_accounts_reporter"` y actualiza:

```json
"service_accounts_reporter": {
  "enabled": true,
  "projects": [
    "tu-proyecto-1",
    "tu-proyecto-2",
    "tu-proyecto-3"
  ],
  ...
}
```

**Ejemplo Real:**
```json
"service_accounts_reporter": {
  "enabled": true,
  "projects": [
    "proyecto-produccion",
    "proyecto-staging",
    "proyecto-desarrollo"
  ],
  "defaults": {
    "mode": "all",
    "output_format": "json"
  }
}
```

#### Paso 4: Guardar y ejecutar

```bash
# Ejecutar nuevamente
python scm/gcp/tools.py

# Seleccionar [38]
# Seleccionar formato: csv
```

---

### Opción 2: Especificar desde CLI (Rápido)

Si no quieres editar `config.json`, puedes pasar los proyectos directamente:

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --projects=proyecto-prod,proyecto-staging \
  -o csv
```

---

## 📋 Checklist de Configuración

- [ ] Copiar `config.json.template` a `config.json`
- [ ] Editar `config.json`
- [ ] Buscar sección `"gcp"` → `"service_accounts_reporter"`
- [ ] Cambiar `"enabled": false` a `"enabled": true`
- [ ] Agregar tus proyectos en el array `"projects"`
- [ ] Guardar el archivo
- [ ] Ejecutar `python scm/gcp/tools.py`
- [ ] Seleccionar `[38]`
- [ ] Seleccionar formato de salida

---

## 🔍 Cómo Encontrar tus Proyectos GCP

### Opción 1: Desde gcloud CLI

```bash
gcloud projects list --format="value(project_id)"
```

**Salida:**
```
proyecto-produccion
proyecto-staging
proyecto-desarrollo
```

### Opción 2: Desde Google Cloud Console

1. Ir a: https://console.cloud.google.com/
2. Hacer clic en el selector de proyecto (arriba a la izquierda)
3. Ver lista de proyectos disponibles

---

## 📝 Estructura de config.json

```json
{
  "gcp": {
    "enabled": true,
    "project_id": "mi-proyecto-default",
    "region": "us-central1",
    
    "service_accounts_reporter": {
      "enabled": true,
      "projects": [
        "proyecto-1",
        "proyecto-2",
        "proyecto-3"
      ],
      "defaults": {
        "mode": "all",
        "output_format": "json",
        "parallel_workers": 5,
        "timeout_seconds": 300
      },
      "security": {
        "dangerous_roles": [
          "roles/editor",
          "roles/owner",
          "roles/compute.admin"
        ],
        "alert_on_risk_level": ["HIGH", "CRITICAL"]
      }
    }
  }
}
```

---

## 🚀 Después de Configurar

### Ejecutar desde Menú

```bash
python scm/gcp/tools.py
# Seleccionar [38]
# Seleccionar formato
```

### Ejecutar Directamente

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py
```

### Resultado

```
🚀 Iniciando análisis de 3 proyecto(s)...
   Proyectos: proyecto-prod, proyecto-staging, proyecto-dev
   Modo: all
   Salida: csv

✅ Proyecto extraído: proyecto-prod
✅ Proyecto extraído: proyecto-staging
✅ Proyecto extraído: proyecto-dev

📊 Generando reporte csv...
✅ Reporte generado: outcome/sa_report_20260708_120700.csv

📈 Resumen:
   - Proyectos: 3
   - Service Accounts: 45
   - Roles: 120
```

---

## 🆘 Troubleshooting

### Error: "No hay proyectos configurados"

**Solución:**
```bash
# Opción 1: Editar config.json
nano scm/config.json
# Agregar proyectos en "projects": [...]

# Opción 2: Usar CLI
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --projects=proyecto1,proyecto2
```

### Error: "Permiso denegado"

**Solución:**
```bash
# Verificar autenticación
gcloud auth list

# Si no hay sesión activa
gcloud auth application-default login
```

### Error: "Timeout"

**Solución:**
```json
"defaults": {
  "timeout_seconds": 600  # Aumentar a 10 minutos
}
```

---

## 📊 Formatos de Salida

```bash
# JSON (default)
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py -o json

# CSV
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py -o csv

# Excel
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py -o excel

# HTML
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py -o html
```

---

## 📁 Archivos Generados

```
outcome/
├── sa_report_20260708_120700.csv
├── sa_report_20260708_120700.json
├── sa_report_20260708_120700.xlsx
└── sa_report_20260708_120700.html
```

---

## 🎯 Próximos Pasos

1. ✅ Configurar `config.json` con tus proyectos
2. ✅ Ejecutar herramienta
3. ✅ Revisar reporte generado
4. ✅ Configurar notificaciones (opcional)
5. ✅ Automatizar ejecución (opcional)

---

**Versión:** 1.0.0  
**Fecha:** 8 de Julio de 2026  
**Estado:** ✅ LISTO

