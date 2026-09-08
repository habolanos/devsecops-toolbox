# 📊 Dashboard Matutino DevSecOps

**Versión:** 2.0.0  
**Autor:** Harold Adrian  
**Fecha:** 15 de Julio de 2026

---

## 📋 Descripción

El Dashboard Matutino DevSecOps es un sistema automatizado que consolida métricas de Azure DevOps (DORA, PR, branch compliance, security, approvals, prod deploy, CI/CD inventory) en un dashboard interactivo. Se ejecuta automáticamente cada mañana a las 7:00 AM y envía notificaciones a Microsoft Teams.

### **Nota Importante sobre Configuración**

A partir de v2.0.0, la configuración del Dashboard está **centralizada en `scm/config.json`** (sección "dashboard"). 

**Cambios:**
- ✅ Eliminado: `scm/dashboard/config_dashboard.json` (duplicado)
- ✅ Consolidado: Toda la configuración en `scm/config.json.template`
- ✅ Reutilización: Credenciales AZDO se obtienen automáticamente
- ✅ Simplificado: Usuario solo necesita editar un archivo de configuración

---

## 🎯 Componentes

### **Tool 26: Dashboard Consolidator**
Orquesta la ejecución de múltiples herramientas AZDO y consolida datos en `dashboard_data.json`.

```bash
python dashboard_consolidator.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT"
```

**Funcionalidades:**
- Lee JSON de 9 herramientas AZDO (ver tabla abajo)
- Consolida datos en estructura JSON
- Gestiona histórico de 90 días
- Detecta alertas críticas dinámicamente (security, approvals, prod deploy overdue, health score)

**Herramientas AZDO integradas (9 fuentes):**

| Fuente | JSON Pattern | Métrica |
|-------|-------------|--------|
| `azdo_pr_master_checker.py` | `pr_master_*.json` | PR Metrics |
| `azdo_branch_policy_checker.py` | `branch_policies_*.json` | Branch Compliance |
| `cicd_inventory_health_score.py` | `pipeline_health_score_*.json` | Health Score (DORA) |
| `cicd_pipeline_status.py` | `pipeline_status_*.json` | Pipeline Status |
| `azdo_scan_pipeline_logs.py` | `azdo_scan_pipeline_logs_*.json` | Security: Logs Scanner |
| `azdo_scan_repos_vulnerabilities.py` | `azdo_scan_repos_vulnerabilities_*.json` | Security: Repo Vulnerabilities |
| `cicd_inventory_pending_approvals.py` | `cicd_inventory_pending_approvals_*.json` | Pending Approvals |
| `cicd_inventory.py` | `cicd_inventory_*.json` | CI/CD Inventory |
| `cicd_inventory_prod_deploy.py` | `cicd_inventory_prod_deploy_*.json` | Prod Deploy Tracking |

---

### **Tool 27: Dashboard Generator**
Genera dashboard HTML interactivo a partir de `dashboard_data.json`.

```bash
python dashboard_generator.py \
  --input "outcome/dashboard/dashboard_data.json" \
  --output "outcome/dashboard/dashboard.html"
```

**Funcionalidades:**
- Genera HTML responsivo con secciones organizadas
- Tarjetas de métricas con colores dinámicos según estado
- 4 gráficos Chart.js (radar, doughnut, bar, bar)
- Tablas de datos (CI/CD Inventory, Prod Deploy Tracking)
- Alertas visuales dinámicas
- Secciones: DORA, PR & Branch, Security & Approvals, Charts, Inventory, Prod Deploy

---

### **Tool 29: Dashboard Scheduler**
Ejecuta el dashboard automáticamente y envía notificaciones a Teams.

```bash
# Ejecutar una sola vez
python dashboard_scheduler.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT" \
  --webhook "$TEAMS_WEBHOOK_URL" \
  --run-once

# Iniciar scheduler (7:00 AM diariamente)
python dashboard_scheduler.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT" \
  --webhook "$TEAMS_WEBHOOK_URL" \
  --cron "0 7 * * *"
```

**Funcionalidades:**
- Scheduling con APScheduler
- Notificaciones a Microsoft Teams
- Reintentos automáticos
- Logging completo

---

## 📊 Métricas Incluidas

### **Health Score (DORA Metrics)**
```
- Deployment Frequency
- Lead Time for Changes
- Mean Time to Recovery (MTTR)
- Change Failure Rate
- System Uptime
- Health Score Breakdown (radar chart)
```

### **PR Metrics**
```
- Total PRs
- Average Review Time
- Approval Rate
- PR Size
- Merge Conflicts
- Awaiting Review/Changes
```

### **Branch Compliance**
```
- Total Repositories
- Protected Branches
- Compliance Percentage
- Repos Without Pipeline
```

### **Pipeline Status**
```
- Total Pipelines
- Success Rate
- Failed Pipelines
- In Progress
- Average Duration
- Doughnut chart (success/failed/in_progress)
```

### **Security: Pipeline Logs Scanner**
```
- Total matches en logs de CI
- Pipelines affected
- Context detected (vulnerab, npm audit, critical, high)
```

### **Security: Repo Vulnerabilities Scanner**
```
- Total findings en package.json
- Repos affected
- Dependencies detected (axios, plain-crypto-js)
- Branches scanned (develop, QA, master, main)
```

### **Pending Approvals**
```
- Total releases con aprobaciones pendientes
- Stage Validador status
- Approver details
- Pending since date
```

### **CI/CD Inventory**
```
- Total repos
- Total CI pipelines (YAML builds)
- Total CD pipelines (classic releases)
- Repo ↔ CI ↔ CD relationship
- Bar chart (repos, CI, CD)
```

### **Prod Deploy Tracking**
```
- Total pipelines tracked
- Pipelines within deadline
- Pipelines overdue
- Last prod deploy date & status
- Days since last deploy
- Deadline status (vencido / al día)
```

---

## 🚨 Alertas Críticas

### **Condiciones Críticas**
```
- Health Score < 60
- Repo Vulnerabilities > 0
- Prod Deploy Overdue > 0
- Deployment Failure Rate > 15%
- MTTR > 4 horas
- System Uptime < 99%
```

### **Condiciones de Advertencia**
```
- Health Score 60-75
- Pipeline Log Alerts > 0
- Pending Approvals > 5
- System Uptime 99-99.5%
```

---

## 📁 Estructura de Archivos

```
scm/dashboard/
├── __init__.py
├── dashboard_consolidator.py (Tool 26)
├── dashboard_generator.py (Tool 27)
├── dashboard_scheduler.py (Tool 29)
├── run_dashboard.py (Tool 28 - Launcher)
├── tests/
│   ├── __init__.py
│   ├── test_dashboard_consolidator.py
│   └── test_dashboard_generator.py
└── README.md

outcome/dashboard/
├── dashboard_data.json (datos consolidados)
├── dashboard.html (dashboard interactivo)
└── history/
    ├── 2026-07-15/
    │   ├── dashboard_data_2026-07-15_070000.json
    │   └── metrics_summary_2026-07-15.json
    └── ... (90 días de histórico)
```

---

## 🔧 Instalación

### **Dependencias**
```bash
pip install apscheduler requests
```

### **Configuración**

**Ubicación:** `scm/config.json` (copiar de `scm/config.json.template`)

```json
{
  "azdo": {
    "organization": "Coppel-Retail",
    "project": "Cadena_de_Suministros",
    "pat": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  },
  "dashboard": {
    "enabled": true,
    "webhook_url": "https://outlook.webhook.office.com/webhookb2/..."
  }
}
```

**Nota:** Las credenciales (org, project, pat) se obtienen automáticamente de la sección `azdo`. Solo es necesario agregar `webhook_url` en la sección `dashboard` si se desean notificaciones a Teams.

### **Variables de Entorno (Alternativa)**
```bash
export AZDO_ORG="Coppel-Retail"
export AZDO_PROJECT="Cadena_de_Suministros"
export AZDO_PAT="your_personal_access_token"
export TEAMS_WEBHOOK_URL="https://outlook.webhook.office.com/..."
```

---

## 🚀 Uso

### **Ejecución Manual**
```bash
# Consolidar datos
python scm/dashboard/dashboard_consolidator.py \
  --org "$AZDO_ORG" \
  --project "$AZDO_PROJECT" \
  --pat "$AZDO_PAT"

# Generar dashboard
python scm/dashboard/dashboard_generator.py

# Enviar notificación
python scm/dashboard/dashboard_scheduler.py \
  --org "$AZDO_ORG" \
  --project "$AZDO_PROJECT" \
  --pat "$AZDO_PAT" \
  --webhook "$TEAMS_WEBHOOK_URL" \
  --run-once
```

### **Ejecución Automática**
```bash
# Iniciar scheduler (7:00 AM diariamente)
python scm/dashboard/dashboard_scheduler.py \
  --org "$AZDO_ORG" \
  --project "$AZDO_PROJECT" \
  --pat "$AZDO_PAT" \
  --webhook "$TEAMS_WEBHOOK_URL"
```

---

## 📊 Salida

### **dashboard_data.json**
```json
{
  "timestamp": "2026-07-15T07:00:00Z",
  "status": "success",
  "metrics": {
    "health_score": {
      "overall_score": 75,
      "deployment_frequency": 2.5,
      "lead_time_days": 2.3,
      "mttr_hours": 1.5,
      "change_failure_rate": 8.5,
      "system_uptime": 99.8,
      "breakdown": {
        "deployment_frequency_score": 75,
        "lead_time_score": 75,
        "mttr_score": 100,
        "cfr_score": 100,
        "uptime_score": 100
      }
    },
    "pr_metrics": {
      "total_prs": 150,
      "approval_rate_percentage": 92
    },
    "branch_compliance": {
      "total_repos": 50,
      "compliance_percentage": 96
    },
    "pipeline_status": {
      "total_pipelines": 95,
      "successful": 85,
      "failed": 5,
      "in_progress": 5,
      "success_rate": 94.4
    },
    "security": {
      "pipeline_logs": {
        "total_matches": 3
      },
      "repo_vulnerabilities": {
        "total_findings": 2
      }
    },
    "pending_approvals": {
      "total": 4
    },
    "cicd_inventory": {
      "total_repos": 50,
      "total_ci_pipelines": 45,
      "total_cd_pipelines": 40
    },
    "prod_deploy": {
      "total_pipelines": 40,
      "pipelines_within_deadline": 38,
      "pipelines_overdue": 2
    }
  },
  "alerts": {
    "critical": [
      "2 vulnerabilidades detectadas en repositorios",
      "2 pipelines con despliegue a producción vencido"
    ],
    "warning": [
      "3 coincidencias de vulnerabilidades en logs de pipelines"
    ],
    "info": []
  },
  "summary": {
    "total_repos": 50,
    "health_score": 75,
    "branch_compliance": 96,
    "pipeline_success_rate": 94.4,
    "security_vulnerabilities": 2,
    "security_log_alerts": 3,
    "pending_approvals": 4,
    "prod_deploy_overdue": 2
  }
}
```

### **dashboard.html**
Dashboard interactivo con:
- Sección DORA Metrics & Health Score (5 tarjetas)
- Sección PR & Branch Policies (4 tarjetas)
- Sección Security & Approvals (4 tarjetas)
- 4 gráficos Chart.js (radar, doughnut, bar, bar)
- Alertas dinámicas
- Tabla CI/CD Inventory (Top 20 repos)
- Tabla Prod Deploy Tracking (Top 20 pipelines)

---

## 🔍 Logging

El sistema genera logs detallados:

```
2026-07-15 07:00:00 - dashboard_consolidator - INFO - Consolidator inicializado
2026-07-15 07:00:01 - dashboard_consolidator - INFO - Ejecutando herramientas en paralelo...
2026-07-15 07:00:15 - dashboard_consolidator - INFO - ✅ health_score cargado
2026-07-15 07:00:16 - dashboard_consolidator - INFO - ✅ pr_metrics cargado
2026-07-15 07:00:17 - dashboard_consolidator - INFO - ✅ security_logs cargado
2026-07-15 07:00:18 - dashboard_consolidator - INFO - ✅ pending_approvals cargado
2026-07-15 07:00:19 - dashboard_consolidator - INFO - ✅ prod_deploy cargado
2026-07-15 07:00:20 - dashboard_consolidator - INFO - Consolidando datos...
2026-07-15 07:00:21 - dashboard_consolidator - INFO - ✅ Consolidación completada exitosamente
```

---

## 📈 Próximas Mejoras

- [ ] Integración con cloud providers (GCP, AWS, Azure) para métricas de monitoreo
- [ ] Gráficos de tendencias (90 días de histórico)
- [ ] Análisis de volatilidad y estabilidad
- [ ] Drill-down interactivo
- [ ] Exportación a Excel
- [ ] Análisis de impacto de cambios

---

## 📜 Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|--------|
| **2.0.0** | 2026-07-15 | Integración de 5 nuevas herramientas AZDO (security logs, repo vulnerabilities, pending approvals, CI/CD inventory, prod deploy). Eliminación de Code Coverage (sin tool generadora). Alertas dinámicas. 4 gráficos Chart.js. Tablas de inventario y prod deploy. |
| 1.0.0 | 2026-06-22 | Versión inicial: Health Score, Code Coverage, PR Metrics, Branch Compliance, Pipeline Status. Scheduler con Teams. |

---

## 📞 Soporte

Para problemas o preguntas, contactar a:
- **DevOps Lead:** Harold Adrian
- **Arquitecto:** Harold Adrian

---

**Versión:** 2.0.0  
**Última actualización:** 15 de Julio de 2026  
**Estado:** ✅ PRODUCCIÓN
