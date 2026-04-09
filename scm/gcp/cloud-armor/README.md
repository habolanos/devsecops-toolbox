# GCP Cloud Armor Checker

Herramienta SCM para auditar y analizar Security Policies (Cloud Armor) en Google Cloud Platform.

## 📋 Contenido

| Archivo | Descripción |
|---------|-------------|
| `gcp_cloud_armor_checker.py` | Script principal de auditoría |
| `requirements.txt` | Dependencias (rich) |
| `outcome/` | Directorio de salida para exportaciones |
| `README.md` | Esta documentación |

---

## 🛡️ Características

- **Listado de Security Policies** - Nombre, tipo, reglas, adaptive protection
- **Detalle de Rules** - Prioridad, acción, match conditions, WAF rules
- **Cobertura de Backends** - Qué backends tienen/no tienen Cloud Armor
- **Modo Auditoría** - Validaciones automáticas de seguridad
- **Detección de Gaps** - Backends expuestos sin protección
- **Comparación entre proyectos** - Diferencias de configuración
- **Exportación CSV/JSON** - Reportes en carpeta `outcome/`
- **Sistema de Semáforos SCM** - Severidad de hallazgos:
  - 🔴 **CRITICAL** - Requiere acción inmediata
  - 🟡 **WARNING** - Revisar configuración
  - 🔵 **INFO** - Información relevante

---

## 🔍 Validaciones de Auditoría

### Críticas (🔴)
- Backends externos sin Security Policy
- Default rule permite todo el tráfico (action=allow)
- Backends expuestos a Internet sin WAF

### Warnings (🟡)
- Sin reglas WAF preconfiguradas (OWASP CRS)
- Rate limiting no configurado
- Adaptive Protection deshabilitado
- Backends internos sin Security Policy

### Info (🔵)
- Reglas en modo preview
- Estadísticas de cobertura

---

## 🚀 Uso

### Requisitos

```bash
pip install rich
```

### Comandos Básicos

```bash
# Ver todas las políticas y backends
python gcp_cloud_armor_checker.py --project mi-proyecto

# Solo Security Policies
python gcp_cloud_armor_checker.py --project mi-proyecto --view policies

# Solo reglas detalladas
python gcp_cloud_armor_checker.py --project mi-proyecto --view rules

# Ver cobertura de backends
python gcp_cloud_armor_checker.py --project mi-proyecto --view backends

# Ver backends sin protección (gaps)
python gcp_cloud_armor_checker.py --project mi-proyecto --view gaps

# Auditoría completa de seguridad
python gcp_cloud_armor_checker.py --project mi-proyecto --audit

# Filtrar hallazgos por severidad
python gcp_cloud_armor_checker.py --project mi-proyecto --audit --severity critical

# Comparar con otro proyecto
python gcp_cloud_armor_checker.py --project proyecto-prod --compare proyecto-dev

# Exportar a JSON
python gcp_cloud_armor_checker.py --project mi-proyecto --audit --output json

# Exportar a CSV
python gcp_cloud_armor_checker.py --project mi-proyecto --audit --output csv
```

---

## 📊 Parámetros

| Parámetro | Alias | Requerido | Descripción |
|-----------|-------|-----------|-------------|
| `--project` | `-p` | ❌ | ID del proyecto GCP (Default: cpl-xxxx-yyyy-zzzz-99999999) |
| `--view` | `-v` | ❌ | Vista: `all`, `policies`, `rules`, `backends`, `gaps` |
| `--audit` | `-a` | ❌ | Ejecuta auditoría completa con validaciones |
| `--severity` | `-s` | ❌ | Filtra hallazgos: `all`, `critical`, `warning`, `info` |
| `--compare` | `-c` | ❌ | Compara con otro proyecto GCP |
| `--output` | `-o` | ❌ | Exporta resultados: `json` o `csv` |
| `--timezone` | `-tz` | ❌ | Timezone (default: America/Mazatlan) |
| `--debug` | | ❌ | Muestra comandos gcloud ejecutados |
| `--parallel` | | ❌ | Ejecución paralela (default: activado) |
| `--no-parallel` | | ❌ | Desactiva ejecución paralela |
| `--max-workers` | | ❌ | Workers para paralelismo (default: 4) |
| `--help` | `-h` | ❌ | Muestra esta documentación |

---

## 📈 Ejemplo de Salida

### Vista de Policies

```
╭──────────────────────────────────────────────────────────────────────────────╮
│                     🛡️ Security Policies (Cloud Armor)                       │
├────┬─────────────────────┬─────────────┬───────┬──────────┬──────────┬───────┤
│ #  │ Policy Name         │ Type        │ Rules │ WAF Rules│ Default  │Backends│
├────┼─────────────────────┼─────────────┼───────┼──────────┼──────────┼───────┤
│ 1  │ policy-waf-prod     │ CLOUD_ARMOR │    12 │        5 │ deny(403)│      4 │
│ 2  │ policy-api-gateway  │ CLOUD_ARMOR │     8 │        3 │ deny(403)│      2 │
│ 3  │ policy-default      │ CLOUD_ARMOR │     2 │        0 │ allow    │      1 │
╰────┴─────────────────────┴─────────────┴───────┴──────────┴──────────┴───────╯
```

### Cobertura de Backends

```
╭──────────────────────────────────────────────────────────────────────────────╮
│              🔌 Backend Services - Cloud Armor Coverage                       │
├────┬───────────────────┬─────────┬──────────┬─────────────────┬──────────────┤
│ #  │ Backend Service   │ Scope   │ LB Scheme│ Security Policy │ Status       │
├────┼───────────────────┼─────────┼──────────┼─────────────────┼──────────────┤
│ 1  │ bs-web-frontend   │ Global  │ EXTERNAL │ policy-waf-prod │ ✅ Protected │
│ 2  │ bs-api-gateway    │ Global  │ EXTERNAL │ None            │ 🔴 EXPOSED   │
│ 3  │ bs-internal-svc   │ Regional│ INTERNAL │ None            │ ⚠️ Unprotected│
╰────┴───────────────────┴─────────┴──────────┴─────────────────┴──────────────╯
```

### Hallazgos de Auditoría

```
╭──────────────────────────────────────────────────────────────────────────────╮
│                        🔍 Security Audit Findings                             │
├─────┬─────────────────────┬─────────────────┬────────────────────────────────┤
│ Sev │ Resource            │ Type            │ Finding                        │
├─────┼─────────────────────┼─────────────────┼────────────────────────────────┤
│ 🔴  │ bs-api-gateway      │ backend_service │ Backend expuesto sin Cloud Armor│
│ 🔴  │ policy-default      │ security_policy │ Default rule: ALLOW            │
│ 🟡  │ policy-api-gateway  │ security_policy │ Sin rate limiting configurado  │
│ 🔵  │ policy-waf-prod     │ security_policy │ 2 regla(s) en modo preview     │
╰─────┴─────────────────────┴─────────────────┴────────────────────────────────╯
```

### Resumen Ejecutivo

```
╭─────────────────────────── 📈 Resumen Ejecutivo ────────────────────────────╮
│ 📊 Coverage                                                                  │
│ Backends: 6/8 (75%) con Cloud Armor                                         │
│ External: 4/5 backends externos protegidos                                  │
│                                                                              │
│ 🛡️ Policies                                                                  │
│ Total: 3 | WAF Rules: 8 | Adaptive Protection: 2/3                          │
│                                                                              │
│ 🔍 Findings                                                                  │
│ 🔴 Critical: 2 | 🟡 Warning: 3 | 🔵 Info: 1                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## 🔐 Permisos IAM Requeridos

```yaml
roles/compute.securityAdmin:
  - compute.securityPolicies.list
  - compute.securityPolicies.get

roles/compute.viewer:
  - compute.backendServices.list
  - compute.backendServices.get
  - compute.forwardingRules.list
```

O el rol predefinido: `roles/compute.networkViewer` + `roles/compute.securityAdmin`

---

## 🏗️ Arquitectura Cloud Armor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUJO DE PROTECCIÓN                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Internet                                                                    │
│     │                                                                        │
│     ▼                                                                        │
│  ┌─────────────────────────────────────────────────────┐                     │
│  │              🛡️ Cloud Armor (WAF/DDoS)               │                    │
│  │  ┌─────────────────────────────────────────────────┐│                     │
│  │  │ Security Policy                                 ││                     │
│  │  │  ├─ Rule 1000: Deny SQLi (OWASP CRS)           ││                     │
│  │  │  ├─ Rule 2000: Deny XSS (OWASP CRS)            ││                     │
│  │  │  ├─ Rule 3000: Rate Limit (100 req/min)        ││                     │
│  │  │  └─ Default: Deny(403)                         ││                     │
│  │  └─────────────────────────────────────────────────┘│                     │
│  │                                                      │                     │
│  │  🔄 Adaptive Protection (L7 DDoS)                   │                     │
│  └─────────────────────────────────────────────────────┘                     │
│     │                                                                        │
│     ▼                                                                        │
│  ┌─────────────────┐                                                         │
│  │ Load Balancer   │                                                         │
│  │ (Backend Service)│◄── Security Policy asociada                            │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │    Backends     │  ◄── GKE, Cloud Run, VMs                                │
│  └─────────────────┘                                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Exportación

### JSON

```bash
python gcp_cloud_armor_checker.py --project mi-proyecto --audit -o json
```

Archivo generado: `outcome/cloud_armor_audit_mi-proyecto_20260325_224500.json`

Estructura:
```json
{
  "metadata": {
    "project": "mi-proyecto",
    "timestamp": "2026-03-25T22:45:00-06:00",
    "timezone": "America/Mazatlan",
    "version": "1.0.0"
  },
  "security_policies": [...],
  "backend_services": {
    "global": [...],
    "regional": [...]
  },
  "audit_findings": [...],
  "summary": {
    "total_policies": 3,
    "total_backends": 8,
    "findings_critical": 2,
    "findings_warning": 3,
    "findings_info": 1
  }
}
```

### CSV

```bash
python gcp_cloud_armor_checker.py --project mi-proyecto --audit -o csv
```

Columnas: `project`, `severity`, `resource`, `resource_type`, `finding`, `recommendation`, `timestamp`

---

## 🔧 Troubleshooting

### Error: No hay sesión activa de gcloud

```bash
gcloud auth login
gcloud config set project TU_PROYECTO
```

### Error: Permission denied

Verifica que tengas los roles:
- `roles/compute.viewer`
- `roles/compute.securityAdmin`

### Error: rich no instalado

```bash
pip install rich
```

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-03-25 | 1.0.0 | Versión inicial con auditoría completa de Cloud Armor |

---

## Autor

**Harold Adrian**

---

## Licencia

Internal SCM Tool - Softtek
