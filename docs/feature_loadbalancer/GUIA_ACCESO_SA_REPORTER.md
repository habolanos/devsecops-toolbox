# 📖 Guía de Acceso y Configuración - Service Accounts Reporter

**Fecha:** 8 de Julio de 2026  
**Versión:** 1.0.0  
**Estado:** ✅ IMPLEMENTADO

---

## 🎯 Tabla de Contenidos

1. [Acceso a la Herramienta](#acceso-a-la-herramienta)
2. [Configuración en config.json](#configuración-en-configjson)
3. [Uso desde CLI](#uso-desde-cli)
4. [Ejemplos Prácticos](#ejemplos-prácticos)
5. [Troubleshooting](#troubleshooting)

---

## 🚀 Acceso a la Herramienta

### Opción 1: Desde el Menú Principal (Recomendado)

```bash
# 1. Navegar a la carpeta del toolbox
cd devsecops-toolbox

# 2. Ejecutar el launcher GCP
python scm/gcp/tools.py

# 3. Seleccionar Tool 38: Service Accounts Reporter
# (Cuando esté integrado en tools.py)
```

### Opción 2: Ejecución Directa

```bash
# Ejecutar directamente el script
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py
```

### Opción 3: Desde Python

```python
from scm.gcp.service_accounts import (
    ConfigLoader,
    ServiceAccountExtractor,
    RolesAndPermissionsAnalyzer,
    JSONReportGenerator
)

# Cargar configuración
config_loader = ConfigLoader('config.json')
projects = config_loader.get_projects()

# Extraer datos
extractor = ServiceAccountExtractor(projects[0])
data = extractor.extract_all()

# Generar reporte
generator = JSONReportGenerator()
report_path = generator.generate(data)
```

---

## ⚙️ Configuración en config.json

### Paso 1: Copiar Template

```bash
cp scm/config.json.template scm/config.json
```

### Paso 2: Agregar Sección de Service Accounts

Edita `scm/config.json` y agrega esta sección dentro de `"gcp"`:

```json
{
  "gcp": {
    "service_accounts_reporter": {
      "enabled": true,
      "projects": [
        "proyecto-produccion-001",
        "proyecto-staging-002",
        "proyecto-desarrollo-003",
        "proyecto-qa-004"
      ],
      "defaults": {
        "mode": "all",
        "output_format": "json",
        "include_activity": true,
        "activity_days": 30,
        "key_rotation_policy_days": 90,
        "parallel_workers": 5,
        "timeout_seconds": 300,
        "cache_enabled": true,
        "cache_ttl_minutes": 60
      },
      "security": {
        "dangerous_roles": [
          "roles/editor",
          "roles/owner",
          "roles/compute.admin",
          "roles/iam.securityAdmin",
          "roles/resourcemanager.organizationAdmin"
        ],
        "alert_on_risk_level": ["HIGH", "CRITICAL"],
        "encrypt_reports": false
      },
      "compliance": {
        "policies": [
          {
            "name": "key_rotation_90days",
            "description": "Rotación de claves cada 90 días",
            "enabled": true,
            "threshold_days": 90
          },
          {
            "name": "no_excessive_permissions",
            "description": "No permitir roles peligrosos",
            "enabled": true
          }
        ]
      },
      "notifications": {
        "enabled": true,
        "on_high_risk": true,
        "on_compliance_violation": true,
        "webhook_url": "https://outlook.webhook.office.com/webhookb2/..."
      }
    }
  }
}
```

### Paso 3: Configurar Proyectos

Reemplaza los nombres de proyectos en el array `"projects"`:

```json
"projects": [
  "mi-proyecto-prod",
  "mi-proyecto-staging",
  "mi-proyecto-dev"
]
```

### Paso 4: Configurar Roles Peligrosos (Opcional)

Personaliza la lista de roles considerados peligrosos:

```json
"dangerous_roles": [
  "roles/editor",
  "roles/owner",
  "roles/compute.admin",
  "roles/iam.securityAdmin"
]
```

### Paso 5: Configurar Notificaciones (Opcional)

Para recibir alertas en Teams:

```json
"notifications": {
  "enabled": true,
  "on_high_risk": true,
  "webhook_url": "https://outlook.webhook.office.com/webhookb2/..."
}
```

**Cómo obtener Teams Webhook URL:**
1. Ir a Teams → Equipo → Connectors
2. Buscar "Incoming Webhook"
3. Configurar y copiar URL

---

## 💻 Uso desde CLI

### Sintaxis Básica

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py [opciones]
```

### Opciones Disponibles

```
--projects PROYECTOS      Proyectos a analizar (separados por coma)
--mode MODO              Modo: all, security, compliance, usage (default: all)
--output FORMATO         Formato: json, csv, excel, html (default: json)
--config RUTA            Ruta a config.json (default: config.json)
--output-dir DIRECTORIO  Directorio de salida (default: outcome)
--debug                  Modo debug
--help                   Mostrar ayuda
```

---

## 📋 Ejemplos Prácticos

### Ejemplo 1: Usar Configuración por Defecto

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py
```

**Resultado:**
- Usa proyectos de `config.json`
- Genera reporte JSON
- Guarda en `outcome/sa_report_YYYYMMDD_HHMMSS.json`

---

### Ejemplo 2: Analizar Proyectos Específicos

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --projects=proyecto-prod,proyecto-staging
```

**Resultado:**
- Analiza solo los 2 proyectos especificados
- Ignora configuración de `config.json`

---

### Ejemplo 3: Reporte de Seguridad en Excel

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --mode=security \
  --output=excel
```

**Resultado:**
- Enfoque en análisis de seguridad
- Genera archivo Excel con múltiples tabs
- Archivo: `outcome/sa_report_YYYYMMDD_HHMMSS.xlsx`

---

### Ejemplo 4: Reporte de Cumplimiento en CSV

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --mode=compliance \
  --output=csv
```

**Resultado:**
- Enfoque en cumplimiento de políticas
- Genera archivo CSV para análisis
- Archivo: `outcome/sa_report_YYYYMMDD_HHMMSS.csv`

---

### Ejemplo 5: Debug Mode

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --debug
```

**Resultado:**
- Muestra logs detallados de ejecución
- Útil para troubleshooting

---

### Ejemplo 6: Salida HTML Interactiva

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --output=html
```

**Resultado:**
- Genera HTML interactivo
- Abre en navegador
- Archivo: `outcome/sa_report_YYYYMMDD_HHMMSS.html`

---

## 📊 Estructura de Salida

### JSON

```json
{
  "metadata": {
    "generated_at": "2026-07-08T11:00:00",
    "format": "json",
    "version": "1.0.0"
  },
  "data": {
    "summary": {
      "total_projects": 4,
      "total_service_accounts": 45,
      "total_roles": 120
    },
    "by_project": {
      "proyecto-prod": {
        "project_id": "proyecto-prod",
        "service_accounts": [...]
      }
    }
  }
}
```

### CSV

```csv
proyecto,service_account,rol,titulo_rol,permisos,otorgado_en,duracion_dias,fecha_expiracion,dias_restantes,nivel_riesgo
proyecto-prod,app-sa@proyecto-prod.iam.gserviceaccount.com,roles/compute.admin,Compute Admin,127,2024-01-15T10:30:00Z,90,2024-04-15T10:30:00Z,45,HIGH
```

### Excel

**Tabs:**
1. **Resumen Ejecutivo** - Métricas generales
2. **Roles por SA** - Detalle de cada rol
3. **Expirando Pronto** - Alertas críticas
4. **Riesgos** - Análisis de riesgos

### HTML

- Tabla interactiva
- Colores por nivel de riesgo
- Filtros dinámicos
- Responsive design

---

## 🔐 Permisos Requeridos

El usuario o service account debe tener estos permisos:

```yaml
Permisos Mínimos:
  - iam.serviceAccounts.list
  - iam.serviceAccounts.get
  - iam.serviceAccountKeys.list
  - resourcemanager.projects.getIamPolicy

Roles Recomendados:
  - roles/iam.securityReviewer
  - roles/resourcemanager.organizationViewer
```

**Crear rol personalizado:**

```bash
gcloud iam roles create saReporter \
  --project=mi-proyecto \
  --title="SA Reporter" \
  --permissions=iam.serviceAccounts.list,iam.serviceAccounts.get,iam.serviceAccountKeys.list,resourcemanager.projects.getIamPolicy
```

---

## 🐛 Troubleshooting

### Problema 1: "config.json no encontrado"

**Solución:**
```bash
cp scm/config.json.template scm/config.json
# Editar y completar valores
```

---

### Problema 2: "No hay proyectos para analizar"

**Solución:**
```bash
# Opción 1: Especificar desde CLI
python ... --projects=proyecto1,proyecto2

# Opción 2: Agregar a config.json
"projects": ["proyecto1", "proyecto2"]
```

---

### Problema 3: "Error de permisos"

**Solución:**
```bash
# Verificar sesión gcloud
gcloud auth list

# Verificar permisos
gcloud projects get-iam-policy mi-proyecto \
  --flatten="bindings[].members" \
  --filter="bindings.members:$(gcloud config get-value account)"
```

---

### Problema 4: "Timeout en gcloud"

**Solución:**
```bash
# Aumentar timeout en config.json
"timeout_seconds": 600

# O ejecutar con debug
python ... --debug
```

---

## 📈 Casos de Uso

### Auditoría de Seguridad

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --mode=security \
  --output=excel
```

Genera reporte con:
- Roles administrativos
- Claves antiguas
- Permisos excesivos

---

### Cumplimiento Normativo

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --mode=compliance \
  --output=csv
```

Genera reporte con:
- Cumplimiento de rotación
- Violaciones de políticas
- Recomendaciones

---

### Análisis de Uso

```bash
python scm/gcp/service-accounts/gcp_sa_multi_project_reporter.py \
  --mode=usage \
  --output=json
```

Genera reporte con:
- Actividad reciente
- Servicios utilizados
- Service accounts inactivos

---

## 📞 Soporte

Para más información:
- Documentación: `docs/analysis/ANALISIS_REPORTE_SERVICE_ACCOUNTS_MULTI_PROYECTO.md`
- Código: `scm/gcp/service-accounts/`
- Issues: Reportar en el repositorio

---

**Versión:** 1.0.0  
**Fecha:** 8 de Julio de 2026  
**Estado:** ✅ COMPLETADO

