# ARQUITECTURA TÉCNICA - Dashboard Matutino

## 🏗️ Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULER (Tool 29)                          │
│  Ejecuta diariamente a las 7:00 AM                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│           ORQUESTADOR (Tool 26)                                 │
│  Ejecuta todas las herramientas en paralelo                     │
│  Consolida outputs en dashboard_data.json                       │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬──────────────┐
        │            │            │              │
        ▼            ▼            ▼              ▼
    ┌────────┐  ┌────────┐  ┌────────┐  ┌────────────┐
    │ AZDO   │  │  GCP   │  │  AWS   │  │ PR METRICS │
    │ Tools  │  │ Tools  │  │ Tools  │  │ (Tool 28)  │
    │14,15,16│  │1,7,22  │  │4,5,13  │  └────────────┘
    └────────┘  └────────┘  └────────┘
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  dashboard_data.json       │
        │  (Datos consolidados)      │
        └────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │ DASHBOARD WEB (Tool 27)    │
        │ Lee JSON y genera HTML     │
        │ Con gráficos y alertas     │
        └────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  dashboard.html            │
        │  (Visualización web)       │
        └────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  NOTIFICACIONES            │
        │  Email / Slack / Teams     │
        └────────────────────────────┘
```

---

## 🔧 TOOL 26: Orquestador (dashboard_consolidator.py)

### Responsabilidades
1. Ejecutar herramientas en paralelo
2. Consolidar outputs JSON
3. Generar dashboard_data.json
4. Manejo de errores y timeouts

### Pseudocódigo
```python
class DashboardConsolidator:
    def __init__(self, org, project, pat, gcp_project, aws_profile):
        self.org = org
        self.project = project
        self.pat = pat
        self.gcp_project = gcp_project
        self.aws_profile = aws_profile
        self.output_dir = Path("outcome/dashboard")
        
    def run_all_tools(self):
        """Ejecuta todas las herramientas en paralelo"""
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                'ci_inventory': executor.submit(self.run_tool_14),
                'cd_inventory': executor.submit(self.run_tool_15),
                'health_score': executor.submit(self.run_tool_16),
                'branch_policy': executor.submit(self.run_tool_1),
                'gcp_monitor': executor.submit(self.run_gcp_tool_1),
                'sql_disk': executor.submit(self.run_gcp_tool_7),
                'rds_status': executor.submit(self.run_aws_tool_4),
                'pr_metrics': executor.submit(self.run_tool_28),
            }
            
            results = {}
            for key, future in futures.items():
                try:
                    results[key] = future.result(timeout=300)
                except Exception as e:
                    results[key] = {'error': str(e), 'status': 'failed'}
        
        return results
    
    def consolidate(self, results):
        """Consolida todos los resultados en un JSON único"""
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'status': 'success' if all(r.get('status') != 'failed' for r in results.values()) else 'partial',
            'data': {
                'azdo': {
                    'ci_inventory': results.get('ci_inventory'),
                    'cd_inventory': results.get('cd_inventory'),
                    'health_score': results.get('health_score'),
                    'branch_policy': results.get('branch_policy'),
                    'pr_metrics': results.get('pr_metrics'),
                },
                'gcp': {
                    'monitor': results.get('gcp_monitor'),
                    'sql_disk': results.get('sql_disk'),
                },
                'aws': {
                    'rds_status': results.get('rds_status'),
                },
            },
            'summary': self.generate_summary(results),
        }
        
        output_file = self.output_dir / f"dashboard_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        
        return dashboard_data
    
    def generate_summary(self, results):
        """Genera resumen ejecutivo"""
        return {
            'total_repos': len(results.get('ci_inventory', {}).get('repos', [])),
            'repos_without_pipeline': len([r for r in results.get('ci_inventory', {}).get('repos', []) if not r.get('ci_pipeline')]),
            'health_score': results.get('health_score', {}).get('overall_score'),
            'branch_compliance': results.get('branch_policy', {}).get('compliance_percentage'),
            'pr_avg_time_to_merge': results.get('pr_metrics', {}).get('avg_time_to_merge_hours'),
            'services_down': results.get('gcp_monitor', {}).get('services_down', []),
            'databases_down': results.get('sql_disk', {}).get('databases_down', []),
        }
```

### Ejecución
```bash
python dashboard_consolidator.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT" \
  --gcp-project "cpl-corp-cial-prod-17042024" \
  --aws-profile "default"
```

---

## 🎨 TOOL 27: Dashboard Web (dashboard_generator.py)

### Responsabilidades
1. Leer dashboard_data.json
2. Generar HTML con gráficos
3. Crear alertas visuales
4. Permitir drill-down interactivo

### Estructura HTML
```html
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Matutino - DevSecOps</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* Estilos modernos con Tailwind/Bootstrap */
    </style>
</head>
<body>
    <header>
        <h1>📊 Dashboard Matutino DevSecOps</h1>
        <p>Última actualización: {timestamp}</p>
    </header>
    
    <section id="summary">
        <h2>Resumen Ejecutivo</h2>
        <div class="kpi-grid">
            <div class="kpi-card">
                <h3>Repos Totales</h3>
                <p class="value">{total_repos}</p>
            </div>
            <div class="kpi-card alert-danger">
                <h3>Sin Pipeline</h3>
                <p class="value">{repos_without_pipeline}</p>
            </div>
            <div class="kpi-card">
                <h3>Health Score</h3>
                <p class="value">{health_score}/100</p>
            </div>
            <div class="kpi-card">
                <h3>Branch Compliance</h3>
                <p class="value">{branch_compliance}%</p>
            </div>
        </div>
    </section>
    
    <section id="repositories">
        <h2>📁 Repositorios</h2>
        <table>
            <thead>
                <tr>
                    <th>Nombre</th>
                    <th>CI Pipeline</th>
                    <th>CD Pipeline</th>
                    <th>Branch Policy</th>
                    <th>Última Actualización</th>
                </tr>
            </thead>
            <tbody>
                {repo_rows}
            </tbody>
        </table>
    </section>
    
    <section id="pipelines">
        <h2>🚀 Pipelines CI/CD</h2>
        <div class="chart-container">
            <canvas id="healthScoreChart"></canvas>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Pipeline</th>
                    <th>Health Score</th>
                    <th>Recencia</th>
                    <th>Confiabilidad</th>
                    <th>Uso</th>
                </tr>
            </thead>
            <tbody>
                {pipeline_rows}
            </tbody>
        </table>
    </section>
    
    <section id="pull-requests">
        <h2>📬 Pull Requests</h2>
        <div class="metrics">
            <p>Tiempo promedio a merge: <strong>{avg_time_to_merge_hours}h</strong></p>
            <p>PRs bloqueadas > 24h: <strong>{blocked_prs_24h}</strong></p>
            <p>SLA Compliance: <strong>{sla_compliance}%</strong></p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>PR</th>
                    <th>Repo</th>
                    <th>Tiempo en Review (h)</th>
                    <th>Autor</th>
                    <th>Estado</th>
                </tr>
            </thead>
            <tbody>
                {pr_rows}
            </tbody>
        </table>
    </section>
    
    <section id="services">
        <h2>🔴 Servicios Caídos</h2>
        {services_down_alerts}
    </section>
    
    <section id="databases">
        <h2>💾 Bases de Datos</h2>
        <div class="alert alert-warning">
            <h3>Alertas de Disco</h3>
            {database_alerts}
        </div>
    </section>
    
    <footer>
        <p>Generado automáticamente por DevSecOps Toolbox</p>
    </footer>
</body>
</html>
```

### Ejecución
```bash
python dashboard_generator.py \
  --input "outcome/dashboard/dashboard_data_*.json" \
  --output "outcome/dashboard/dashboard.html"
```

---

## 📊 TOOL 28: PR Time-to-Merge Analyzer (pr_metrics_analyzer.py)

### Responsabilidades
1. Consultar API AZDO para PRs
2. Calcular métricas de tiempo
3. Generar alertas de SLA
4. Exportar JSON con resultados

### Métricas Calculadas
```python
{
    'total_prs': 150,
    'merged_prs': 145,
    'abandoned_prs': 5,
    'active_prs': 0,
    'avg_time_to_merge_hours': 24.5,
    'median_time_to_merge_hours': 18.0,
    'p95_time_to_merge_hours': 72.0,
    'prs_blocked_24h': 3,
    'prs_blocked_48h': 1,
    'sla_compliance': 95.2,  # % de PRs merged en < 48h
    'slowest_reviewers': [
        {'reviewer': 'john.doe', 'avg_review_time_hours': 48.0, 'pr_count': 10},
        {'reviewer': 'jane.smith', 'avg_review_time_hours': 36.0, 'pr_count': 8},
    ],
    'fastest_reviewers': [
        {'reviewer': 'alice.johnson', 'avg_review_time_hours': 2.0, 'pr_count': 25},
    ],
    'slowest_authors': [
        {'author': 'bob.wilson', 'avg_time_to_merge_hours': 72.0, 'pr_count': 5},
    ],
}
```

### Ejecución
```bash
python pr_metrics_analyzer.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT" \
  --days 30 \
  --output "outcome/dashboard/pr_metrics.json"
```

---

## ⏰ TOOL 29: Scheduler (dashboard_scheduler.py)

### Responsabilidades
1. Ejecutar Tool 26 diariamente a las 7:00 AM
2. Generar Tool 27 (HTML)
3. Enviar notificaciones
4. Almacenar histórico

### Configuración
```yaml
# config.json
{
  "dashboard": {
    "enabled": true,
    "schedule": "0 7 * * *",  # 7:00 AM todos los días
    "timezone": "America/Mexico_City",
    "notifications": {
      "email": {
        "enabled": true,
        "recipients": ["team@example.com", "manager@example.com"],
        "send_on": ["critical", "warning"]
      },
      "slack": {
        "enabled": true,
        "webhook_url": "${SLACK_WEBHOOK_URL}",
        "channel": "#devops-alerts",
        "send_on": ["critical"]
      },
      "teams": {
        "enabled": true,
        "webhook_url": "${TEAMS_WEBHOOK_URL}",
        "send_on": ["critical", "warning"]
      }
    },
    "alerts": {
      "repos_without_pipeline": {
        "enabled": true,
        "threshold": 0,
        "severity": "critical"
      },
      "health_score_below": {
        "enabled": true,
        "threshold": 70,
        "severity": "warning"
      },
      "branch_compliance_below": {
        "enabled": true,
        "threshold": 80,
        "severity": "warning"
      },
      "pr_sla_below": {
        "enabled": true,
        "threshold": 90,
        "severity": "warning"
      },
      "services_down": {
        "enabled": true,
        "severity": "critical"
      },
      "databases_down": {
        "enabled": true,
        "severity": "critical"
      }
    }
  }
}
```

### Ejecución
```bash
# Ejecutar como servicio/daemon
python dashboard_scheduler.py --daemon

# O ejecutar una sola vez
python dashboard_scheduler.py --run-once
```

---

## 📁 Estructura de Archivos

```
devsecops-toolbox/
├── scm/
│   ├── azdo/
│   │   ├── dashboard_consolidator.py      (Tool 26)
│   │   └── pr_metrics_analyzer.py         (Tool 28)
│   ├── gcp/
│   │   └── (reutiliza herramientas existentes)
│   ├── aws/
│   │   └── (reutiliza herramientas existentes)
│   └── dashboard/
│       ├── dashboard_generator.py         (Tool 27)
│       ├── dashboard_scheduler.py         (Tool 29)
│       ├── templates/
│       │   └── dashboard.html.jinja2
│       └── static/
│           ├── css/
│           │   └── dashboard.css
│           └── js/
│               └── dashboard.js
├── outcome/
│   └── dashboard/
│       ├── dashboard_data_20260622_070000.json
│       ├── dashboard.html
│       ├── pr_metrics.json
│       └── history/
│           ├── 2026-06-22.json
│           ├── 2026-06-21.json
│           └── ...
└── DASHBOARD_ANALYSIS.md
```

---

## 🔄 Flujo de Ejecución Diaria

```
7:00 AM (Scheduler)
  ↓
Tool 26 (Orquestador)
  ├─ Tool 14 (CI Inventory)
  ├─ Tool 15 (CD Inventory)
  ├─ Tool 16 (Health Score)
  ├─ Tool 1 (Branch Policy)
  ├─ GCP Tool 1 (Monitor)
  ├─ GCP Tool 7 (SQL Disk)
  ├─ AWS Tool 4 (RDS)
  └─ Tool 28 (PR Metrics)
  ↓
dashboard_data.json
  ↓
Tool 27 (Dashboard Generator)
  ↓
dashboard.html
  ↓
Notificaciones
  ├─ Email con resumen
  ├─ Slack con alertas críticas
  └─ Teams con link al dashboard
  ↓
Almacenar histórico
  └─ outcome/dashboard/history/{date}.json
```

---

## 📈 Métricas Clave en el Dashboard

### Resumen Ejecutivo
- Total de repositorios
- Repos sin pipeline CI/CD
- Health Score general (0-100)
- Branch compliance (%)
- Servicios caídos
- Bases de datos con alertas

### Repositorios
- Nombre
- CI Pipeline (sí/no)
- CD Pipeline (sí/no)
- Branch policy compliance
- Última actualización

### Pipelines
- Health score por pipeline
- Recencia (últimos 30 días)
- Confiabilidad (% success)
- Uso (ejecuciones/mes)
- Freshness (actualización)

### Pull Requests
- Tiempo promedio a merge
- PRs bloqueadas > 24h
- SLA compliance (%)
- Reviewers más lentos
- Autores más lentos

### Servicios
- Estado GCP (healthy/degraded/down)
- Estado AWS (healthy/degraded/down)
- Alertas CloudWatch

### Bases de Datos
- Uso de disco (%)
- Instancias con alertas
- Backups recientes

---

## 🚀 Implementación Incremental

### Semana 1: Tool 26 + Tool 28
- Orquestador básico
- PR Metrics
- Consolidación JSON

### Semana 2: Tool 27
- Dashboard HTML
- Gráficos básicos
- Tablas interactivas

### Semana 3: Tool 29
- Scheduler
- Notificaciones email
- Histórico

### Semana 4: Refinamiento
- Notificaciones Slack/Teams
- Drill-down interactivo
- Optimización de performance

---

## 💾 Almacenamiento de Datos

### dashboard_data.json (Diario)
```json
{
  "timestamp": "2026-06-22T07:00:00Z",
  "status": "success",
  "data": {
    "azdo": {...},
    "gcp": {...},
    "aws": {...}
  },
  "summary": {...}
}
```

### Histórico (outcome/dashboard/history/)
- Un archivo JSON por día
- Permite análisis de tendencias
- Retención: 90 días

---

## 🔐 Seguridad

- PAT almacenado en config.json (no en código)
- Webhook URLs en variables de entorno
- HTML sanitizado (sin XSS)
- Acceso al dashboard con autenticación (opcional)
- Logs de auditoría de acceso

---

## 📊 Estimación de Esfuerzo

| Componente | Líneas de Código | Horas Estimadas |
|---|---|---|
| Tool 26 (Orquestador) | 300-400 | 8-10 |
| Tool 27 (Dashboard) | 500-600 | 12-15 |
| Tool 28 (PR Metrics) | 400-500 | 10-12 |
| Tool 29 (Scheduler) | 200-300 | 6-8 |
| **Total** | **1400-1800** | **36-45 horas** |

**Timeline:** 3-4 semanas (con 1 dev a tiempo completo)
