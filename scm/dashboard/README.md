# 📊 Dashboard Matutino DevSecOps

**Versión:** 1.0.0  
**Autor:** Harold Adrian  
**Fecha:** 22 de Junio de 2026

---

## 📋 Descripción

El Dashboard Matutino DevSecOps es un sistema automatizado que consolida métricas de salud, cobertura de código y desempeño de CI/CD en un dashboard interactivo. Se ejecuta automáticamente cada mañana a las 7:00 AM y envía notificaciones a Microsoft Teams.

### **Nota Importante sobre Configuración**

A partir de v1.0.0, la configuración del Dashboard está **centralizada en `scm/config.json`** (sección "dashboard"). 

**Cambios:**
- ✅ Eliminado: `scm/dashboard/config_dashboard.json` (duplicado)
- ✅ Consolidado: Toda la configuración en `scm/config.json.template`
- ✅ Reutilización: Credenciales AZDO se obtienen automáticamente
- ✅ Simplificado: Usuario solo necesita editar un archivo de configuración

---

## 🎯 Componentes

### **Tool 26: Dashboard Consolidator**
Orquesta la ejecución de múltiples herramientas y consolida datos en `dashboard_data.json`.

```bash
python dashboard_consolidator.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT"
```

**Funcionalidades:**
- Ejecuta herramientas en paralelo (ThreadPoolExecutor)
- Consolida datos en estructura JSON
- Gestiona histórico de 90 días
- Detecta alertas críticas

---

### **Tool 27: Dashboard Generator**
Genera dashboard HTML interactivo a partir de `dashboard_data.json`.

```bash
python dashboard_generator.py \
  --input "outcome/dashboard/dashboard_data.json" \
  --output "outcome/dashboard/dashboard.html"
```

**Funcionalidades:**
- Genera HTML responsivo
- Visualización de métricas clave
- Gráficos interactivos (Chart.js)
- Alertas visuales

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
```

### **Code Coverage (ISO 29119)**
```
- Overall Coverage
- Line Coverage
- Branch Coverage
- Function Coverage
- Test Execution Rate
```

### **PR Metrics**
```
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
- Average Duration
```

---

## 🚨 Alertas Críticas

### **Condiciones Críticas**
```
- Health Score < 40
- Code Coverage < 60%
- Deployment Failure Rate > 15%
- MTTR > 4 horas
- System Uptime < 99%
- Review Time > 120 minutos
- Approval Rate < 70%
```

### **Condiciones de Advertencia**
```
- Health Score 40-60
- Code Coverage 60-75%
- System Uptime 99-99.5%
- Review Time 60-120 minutos
- Approval Rate 70-80%
```

---

## 📁 Estructura de Archivos

```
scm/dashboard/
├── __init__.py
├── dashboard_consolidator.py (Tool 26)
├── dashboard_generator.py (Tool 27)
├── dashboard_scheduler.py (Tool 29)
├── config_dashboard.json
└── README.md

outcome/dashboard/
├── dashboard_data.json (datos consolidados)
├── dashboard.html (dashboard interactivo)
└── history/
    ├── 2026-06-22/
    │   ├── dashboard_data_2026-06-22_070000.json
    │   └── metrics_summary_2026-06-22.json
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
  "timestamp": "2026-06-22T07:00:00Z",
  "status": "success",
  "metrics": {
    "health_score": {
      "overall_score": 75,
      "deployment_frequency": 2.5,
      "lead_time_days": 2.3,
      "mttr_hours": 1.5,
      "change_failure_rate": 8.5,
      "system_uptime": 99.8
    },
    "code_coverage": {
      "overall_coverage": 82,
      "line_coverage": 85,
      "branch_coverage": 78,
      "function_coverage": 88,
      "test_execution_rate": 95
    }
  },
  "alerts": {
    "critical": [],
    "warning": [],
    "info": []
  },
  "summary": {
    "total_repos": 50,
    "health_score": 75,
    "code_coverage": 82,
    "branch_compliance": 96
  }
}
```

### **dashboard.html**
Dashboard interactivo con:
- Métricas clave en tarjetas
- Gráficos interactivos
- Alertas visuales
- Información de estado

---

## 🔍 Logging

El sistema genera logs detallados:

```
2026-06-22 07:00:00 - dashboard_consolidator - INFO - Consolidator inicializado
2026-06-22 07:00:01 - dashboard_consolidator - INFO - Ejecutando herramientas en paralelo...
2026-06-22 07:00:15 - dashboard_consolidator - INFO - ✅ health_score completado
2026-06-22 07:00:20 - dashboard_consolidator - INFO - ✅ code_coverage completado
2026-06-22 07:00:25 - dashboard_consolidator - INFO - Consolidando datos...
2026-06-22 07:00:26 - dashboard_consolidator - INFO - ✅ Consolidación completada exitosamente
```

---

## 📈 Próximas Mejoras

- [ ] Integración con Jira para métricas de velocidad
- [ ] Gráficos de tendencias (90 días)
- [ ] Análisis de volatilidad y estabilidad
- [ ] Pronósticos de problemas
- [ ] Drill-down interactivo
- [ ] Exportación a Excel
- [ ] Integración con Slack
- [ ] Análisis de impacto de cambios

---

## 📞 Soporte

Para problemas o preguntas, contactar a:
- **DevOps Lead:** Harold Adrian
- **Arquitecto:** Harold Adrian

---

**Versión:** 1.0.0  
**Última actualización:** 22 de Junio de 2026  
**Estado:** ✅ PRODUCCIÓN
