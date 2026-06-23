# 🔧 Guía de Implementación - Teams + Métricas Específicas

**Fecha:** 22 de Junio de 2026  
**Versión:** 1.0  
**Objetivo:** Implementar notificaciones a Teams con Health Score y Coverage

---

## 📱 Integración con Microsoft Teams

### Paso 1: Crear Webhook en Teams

```bash
1. Abrir Microsoft Teams
2. Ir al grupo: [Equipo Comercial/CDS]
3. Click en "..." (More options)
4. Seleccionar "Connectors"
5. Buscar "Incoming Webhook"
6. Click "Configure"
7. Nombre: "Dashboard Matutino DevSecOps"
8. Imagen: [Logo DevSecOps]
9. Click "Create"
10. Copiar URL del webhook
```

### Paso 2: Guardar Webhook en config.json

```json
{
  "dashboard": {
    "enabled": true,
    "schedule": "0 7 * * *",
    "notifications": {
      "teams": {
        "enabled": true,
        "webhook_url": "https://outlook.webhook.office.com/webhookb2/...",
        "group_name": "Equipo Comercial/CDS",
        "mention_on_critical": true,
        "retry_attempts": 3,
        "timeout_seconds": 30
      },
      "email": {
        "enabled": false
      },
      "slack": {
        "enabled": false
      }
    }
  }
}
```

### Paso 3: Formato de Mensaje Teams

```python
# En Tool 29 (Scheduler)

def send_teams_notification(webhook_url, dashboard_data):
    """Envía notificación a Teams con formato adaptativo."""
    
    summary = dashboard_data['summary']
    alerts = dashboard_data['alerts']
    
    # Determinar color según estado
    if alerts['critical']:
        color = "ff0000"  # Rojo
        status = "🔴 CRÍTICO"
    elif alerts['warning']:
        color = "ffcc00"  # Amarillo
        status = "🟡 ADVERTENCIA"
    else:
        color = "00cc00"  # Verde
        status = "🟢 SALUDABLE"
    
    # Construir mensaje adaptativo
    message = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": f"Dashboard Matutino - {status}",
        "themeColor": color,
        "sections": [
            {
                "activityTitle": "📊 Dashboard Matutino DevSecOps",
                "activitySubtitle": f"Ejecución: {dashboard_data['timestamp']}",
                "activityImage": "https://...",
                "facts": [
                    {
                        "name": "Estado",
                        "value": status
                    },
                    {
                        "name": "Health Score",
                        "value": f"{summary['health_score']}/100"
                    },
                    {
                        "name": "Code Coverage",
                        "value": f"{summary['code_coverage']}%"
                    },
                    {
                        "name": "Deployment Frequency",
                        "value": f"{summary['deployment_frequency']}/semana"
                    },
                    {
                        "name": "MTTR",
                        "value": f"{summary['mttr']} horas"
                    },
                    {
                        "name": "System Uptime",
                        "value": f"{summary['system_uptime']}%"
                    }
                ]
            }
        ]
    }
    
    # Agregar alertas si las hay
    if alerts['critical']:
        message['sections'].append({
            "activityTitle": "🔴 ALERTAS CRÍTICAS",
            "text": "\n".join([f"• {alert}" for alert in alerts['critical']])
        })
    
    if alerts['warning']:
        message['sections'].append({
            "activityTitle": "🟡 ADVERTENCIAS",
            "text": "\n".join([f"• {alert}" for alert in alerts['warning']])
        })
    
    # Agregar link al dashboard
    message['potentialAction'] = [
        {
            "@type": "OpenUri",
            "name": "Ver Dashboard Completo",
            "targets": [
                {
                    "os": "default",
                    "uri": "file:///outcome/dashboard/dashboard.html"
                }
            ]
        }
    ]
    
    # Enviar
    response = requests.post(webhook_url, json=message)
    return response.status_code == 200
```

---

## 📊 Implementación de Métricas

### 1. Health Score (DORA Metrics)

```python
# En Tool 26 (Consolidator)

class HealthScoreCalculator:
    """Calcula Health Score basado en DORA Metrics."""
    
    def __init__(self, ci_data, cd_data, service_data):
        self.ci_data = ci_data
        self.cd_data = cd_data
        self.service_data = service_data
    
    def calculate(self):
        """Calcula Health Score (0-100)."""
        
        # 1. Deployment Frequency (20%)
        deployment_freq = self._calculate_deployment_frequency()
        deployment_score = self._score_deployment_frequency(deployment_freq)
        
        # 2. Lead Time for Changes (20%)
        lead_time = self._calculate_lead_time()
        lead_time_score = self._score_lead_time(lead_time)
        
        # 3. Mean Time to Recovery (25%)
        mttr = self._calculate_mttr()
        mttr_score = self._score_mttr(mttr)
        
        # 4. Change Failure Rate (20%)
        cfr = self._calculate_change_failure_rate()
        cfr_score = self._score_cfr(cfr)
        
        # 5. System Uptime (15%)
        uptime = self._calculate_system_uptime()
        uptime_score = self._score_uptime(uptime)
        
        # Calcular score final ponderado
        health_score = (
            deployment_score * 0.20 +
            lead_time_score * 0.20 +
            mttr_score * 0.25 +
            cfr_score * 0.20 +
            uptime_score * 0.15
        )
        
        return {
            'health_score': round(health_score, 2),
            'deployment_frequency': deployment_freq,
            'lead_time_days': lead_time,
            'mttr_hours': mttr,
            'change_failure_rate': cfr,
            'system_uptime': uptime,
            'breakdown': {
                'deployment_frequency_score': deployment_score,
                'lead_time_score': lead_time_score,
                'mttr_score': mttr_score,
                'cfr_score': cfr_score,
                'uptime_score': uptime_score
            }
        }
    
    def _calculate_deployment_frequency(self):
        """Calcula deploys por semana."""
        # Contar deploys en los últimos 7 días
        deploys = len([d for d in self.cd_data 
                      if d['last_deployment_date'] > 7_days_ago])
        return deploys
    
    def _score_deployment_frequency(self, freq):
        """Puntúa deployment frequency."""
        if freq >= 3:
            return 100  # Elite
        elif freq >= 1:
            return 75   # High
        elif freq >= 0.5:
            return 50   # Medium
        else:
            return 25   # Low
    
    def _calculate_lead_time(self):
        """Calcula lead time promedio en días."""
        lead_times = []
        for repo in self.ci_data:
            if repo.get('last_build_date') and repo.get('last_commit_date'):
                days = (repo['last_build_date'] - repo['last_commit_date']).days
                lead_times.append(days)
        return sum(lead_times) / len(lead_times) if lead_times else 0
    
    def _score_lead_time(self, days):
        """Puntúa lead time."""
        if days < 1:
            return 100  # Elite
        elif days < 3:
            return 75   # High
        elif days < 7:
            return 50   # Medium
        else:
            return 25   # Low
    
    def _calculate_mttr(self):
        """Calcula Mean Time to Recovery en horas."""
        # Basado en histórico de incidentes
        incidents = self.service_data.get('incidents', [])
        recovery_times = []
        for incident in incidents:
            if incident.get('resolved_at') and incident.get('created_at'):
                hours = (incident['resolved_at'] - incident['created_at']).total_seconds() / 3600
                recovery_times.append(hours)
        return sum(recovery_times) / len(recovery_times) if recovery_times else 0
    
    def _score_mttr(self, hours):
        """Puntúa MTTR."""
        if hours < 1:
            return 100  # Elite
        elif hours < 4:
            return 75   # High
        elif hours < 24:
            return 50   # Medium
        else:
            return 25   # Low
    
    def _calculate_change_failure_rate(self):
        """Calcula % de cambios que fallan."""
        total_changes = len(self.cd_data)
        failed_changes = len([d for d in self.cd_data if d.get('status') == 'failed'])
        return (failed_changes / total_changes * 100) if total_changes > 0 else 0
    
    def _score_cfr(self, percentage):
        """Puntúa Change Failure Rate."""
        if percentage < 10:
            return 100  # Elite
        elif percentage < 20:
            return 75   # High
        elif percentage < 30:
            return 50   # Medium
        else:
            return 25   # Low
    
    def _calculate_system_uptime(self):
        """Calcula uptime del sistema."""
        # Basado en monitoreo de servicios
        services = self.service_data.get('services', [])
        uptimes = [s.get('uptime_percentage', 100) for s in services]
        return sum(uptimes) / len(uptimes) if uptimes else 100
    
    def _score_uptime(self, percentage):
        """Puntúa System Uptime."""
        if percentage >= 99.9:
            return 100  # Elite
        elif percentage >= 99:
            return 75   # High
        elif percentage >= 95:
            return 50   # Medium
        else:
            return 25   # Low
```

### 2. Code Coverage (ISO 29119)

```python
# En Tool 28 (PR Metrics) o Tool 26 (Consolidator)

class CodeCoverageAnalyzer:
    """Analiza cobertura de código basado en ISO 29119."""
    
    def __init__(self, test_data):
        self.test_data = test_data
    
    def calculate(self):
        """Calcula métricas de cobertura."""
        
        repos = self.test_data.get('repositories', [])
        
        coverage_metrics = {
            'overall_coverage': self._calculate_overall_coverage(repos),
            'line_coverage': self._calculate_line_coverage(repos),
            'branch_coverage': self._calculate_branch_coverage(repos),
            'function_coverage': self._calculate_function_coverage(repos),
            'test_execution_rate': self._calculate_test_execution_rate(repos),
            'repos_by_coverage': self._categorize_repos(repos),
            'trend': self._calculate_trend(repos)
        }
        
        return coverage_metrics
    
    def _calculate_overall_coverage(self, repos):
        """Calcula cobertura general."""
        coverages = [r.get('coverage_percentage', 0) for r in repos]
        return round(sum(coverages) / len(coverages), 2) if coverages else 0
    
    def _calculate_line_coverage(self, repos):
        """Calcula cobertura de líneas."""
        line_coverages = [r.get('line_coverage', 0) for r in repos]
        return round(sum(line_coverages) / len(line_coverages), 2) if line_coverages else 0
    
    def _calculate_branch_coverage(self, repos):
        """Calcula cobertura de ramas."""
        branch_coverages = [r.get('branch_coverage', 0) for r in repos]
        return round(sum(branch_coverages) / len(branch_coverages), 2) if branch_coverages else 0
    
    def _calculate_function_coverage(self, repos):
        """Calcula cobertura de funciones."""
        function_coverages = [r.get('function_coverage', 0) for r in repos]
        return round(sum(function_coverages) / len(function_coverages), 2) if function_coverages else 0
    
    def _calculate_test_execution_rate(self, repos):
        """Calcula % de tests ejecutados."""
        total_tests = sum([r.get('total_tests', 0) for r in repos])
        executed_tests = sum([r.get('executed_tests', 0) for r in repos])
        return round((executed_tests / total_tests * 100), 2) if total_tests > 0 else 0
    
    def _categorize_repos(self, repos):
        """Categoriza repos por nivel de cobertura."""
        categories = {
            'critical': [],      # < 60%
            'acceptable': [],    # 60-75%
            'good': [],          # 75-85%
            'excellent': []      # > 85%
        }
        
        for repo in repos:
            coverage = repo.get('coverage_percentage', 0)
            if coverage < 60:
                categories['critical'].append(repo['name'])
            elif coverage < 75:
                categories['acceptable'].append(repo['name'])
            elif coverage < 85:
                categories['good'].append(repo['name'])
            else:
                categories['excellent'].append(repo['name'])
        
        return categories
    
    def _calculate_trend(self, repos):
        """Calcula tendencia de cobertura."""
        current = self._calculate_overall_coverage(repos)
        # Comparar con semana anterior (requiere histórico)
        previous = repos[0].get('previous_week_coverage', current)
        trend = current - previous
        return {
            'current': current,
            'previous': previous,
            'change': round(trend, 2),
            'direction': 'up' if trend > 0 else 'down' if trend < 0 else 'stable'
        }
```

---

## 🚨 Evaluación de Alertas Críticas

```python
# En Tool 26 o Tool 29

class AlertEvaluator:
    """Evalúa condiciones críticas."""
    
    def __init__(self, health_score, coverage, service_data):
        self.health_score = health_score
        self.coverage = coverage
        self.service_data = service_data
    
    def evaluate(self):
        """Evalúa todas las condiciones críticas."""
        
        alerts = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        # 1. Fallos en Producción
        if self.health_score['change_failure_rate'] > 15:
            alerts['critical'].append(
                f"🔴 Deployment Failure Rate: {self.health_score['change_failure_rate']}% (> 15%)"
            )
        
        if self.health_score['mttr_hours'] > 4:
            alerts['critical'].append(
                f"🔴 MTTR: {self.health_score['mttr_hours']} horas (> 4h)"
            )
        
        if self.health_score['system_uptime'] < 99:
            alerts['critical'].append(
                f"🔴 System Uptime: {self.health_score['system_uptime']}% (< 99%)"
            )
        
        # 2. Baja Cobertura
        if self.coverage['overall_coverage'] < 60:
            alerts['critical'].append(
                f"🔴 Code Coverage: {self.coverage['overall_coverage']}% (< 60%)"
            )
        
        if self.coverage['test_execution_rate'] < 80:
            alerts['critical'].append(
                f"🔴 Test Execution Rate: {self.coverage['test_execution_rate']}% (< 80%)"
            )
        
        if len(self.coverage['repos_by_coverage']['critical']) > 0:
            alerts['critical'].append(
                f"🔴 {len(self.coverage['repos_by_coverage']['critical'])} repos con cobertura < 60%"
            )
        
        # 3. Pérdida de Estabilidad
        if self.health_score['health_score'] < 40:
            alerts['critical'].append(
                f"🔴 Health Score: {self.health_score['health_score']}/100 (Crítico)"
            )
        
        # Advertencias
        if self.health_score['health_score'] < 60:
            alerts['warning'].append(
                f"🟡 Health Score: {self.health_score['health_score']}/100 (Aceptable)"
            )
        
        if self.coverage['overall_coverage'] < 75:
            alerts['warning'].append(
                f"🟡 Code Coverage: {self.coverage['overall_coverage']}% (Aceptable)"
            )
        
        return alerts
```

---

## 📋 Configuración en config.json

```json
{
  "dashboard": {
    "enabled": true,
    "schedule": "0 7 * * *",
    "timezone": "America/Mexico_City",
    "timeout_seconds": 1800,
    
    "metrics": {
      "health_score": {
        "enabled": true,
        "weights": {
          "deployment_frequency": 0.20,
          "lead_time": 0.20,
          "mttr": 0.25,
          "change_failure_rate": 0.20,
          "system_uptime": 0.15
        }
      },
      "code_coverage": {
        "enabled": true,
        "thresholds": {
          "critical": 60,
          "acceptable": 75,
          "good": 85,
          "excellent": 95
        }
      }
    },
    
    "alerts": {
      "critical": {
        "deployment_failure_rate": 15,
        "mttr_hours": 4,
        "change_failure_rate": 20,
        "system_uptime": 99,
        "code_coverage": 60,
        "test_execution_rate": 80
      },
      "warning": {
        "health_score": 60,
        "code_coverage": 75,
        "system_uptime": 99.5
      }
    },
    
    "notifications": {
      "teams": {
        "enabled": true,
        "webhook_url": "https://outlook.webhook.office.com/webhookb2/...",
        "group_name": "Equipo Comercial/CDS",
        "mention_on_critical": true,
        "retry_attempts": 3,
        "timeout_seconds": 30
      }
    },
    
    "output": {
      "directory": "outcome/dashboard",
      "history_directory": "outcome/dashboard/history",
      "retention_days": 90,
      "formats": ["json", "html"]
    }
  }
}
```

---

## 🧪 Pruebas de Implementación

```bash
# 1. Probar Health Score
python -m pytest tests/unit/test_health_score.py -v

# 2. Probar Code Coverage
python -m pytest tests/unit/test_code_coverage.py -v

# 3. Probar Alertas
python -m pytest tests/unit/test_alerts.py -v

# 4. Probar Notificación Teams
python -m pytest tests/integration/test_teams_notification.py -v

# 5. Probar flujo completo
python scm/azdo/dashboard_consolidator.py \
  --org "Coppel-Retail" \
  --project "Cadena_de_Suministros" \
  --pat "$AZDO_PAT"
```

---

## 📊 Ejemplo de dashboard_data.json

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
      "system_uptime": 99.8,
      "breakdown": {
        "deployment_frequency_score": 75,
        "lead_time_score": 75,
        "mttr_score": 100,
        "cfr_score": 100,
        "uptime_score": 100
      }
    },
    "code_coverage": {
      "overall_coverage": 82,
      "line_coverage": 85,
      "branch_coverage": 78,
      "function_coverage": 88,
      "test_execution_rate": 95,
      "repos_by_coverage": {
        "critical": [],
        "acceptable": ["repo-3"],
        "good": ["repo-1", "repo-2"],
        "excellent": ["repo-4", "repo-5"]
      },
      "trend": {
        "current": 82,
        "previous": 80,
        "change": 2,
        "direction": "up"
      }
    }
  },
  "alerts": {
    "critical": [],
    "warning": [
      "Code Coverage en repo-3: 72% (< 75%)"
    ],
    "info": []
  },
  "summary": {
    "total_repos": 50,
    "repos_with_ci": 48,
    "repos_with_cd": 45,
    "repos_without_pipeline": 2,
    "health_score": 75,
    "code_coverage": 82,
    "branch_compliance": 92
  }
}
```

---

**Preparado por:** Harold Adrian  
**Fecha:** 22 de Junio de 2026  
**Versión:** 1.0
