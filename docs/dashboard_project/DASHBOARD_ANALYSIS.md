# REQUERIMIENTO: Dashboard Matutino de Repositorios y Servicios

## 📋 Requerimientos Solicitados

El equipo Comercial/CDS necesita un dashboard diario que muestre:

1. **Estado de Repositorios**
   - Cumplimiento con estrategia de branching
   - Repos sin pipelines CI/CD
   - Ramas y su alineación con estrategia

2. **Pull Requests**
   - PRs con tiempo de atención
   - Estado y métricas

3. **Servicios e Infraestructura**
   - Servicios caídos en servidores
   - Bases de datos caídas
   - Estado general de salud

---

## ✅ QUÉ YA TENEMOS (Reutilizable)

### AZDO Tools (25 herramientas)

**Repositorios & Branching:**
- Tool 1: `azdo_branch_policy_checker.py` - Audita políticas de rama
- Tool 2b: `azdo_branch_lock_checker.py` - Lista ramas con lock
- Tool 12: `cicd_inventory_branches_created.py` - Ramas creadas desde fecha
- Tool 13: `cicd_inventory_hotfix_branches.py` - Inventario hotfix branches

**Pipelines CI/CD:**
- Tool 9: `cicd_inventory.py` - Inventario completo repos ↔ CI ↔ CD
- Tool 14: `cicd_inventory_ci_detailed.py` - Inventario detallado CI (cache 24h)
- Tool 15: `cicd_inventory_cd_detailed.py` - Inventario detallado CD (cache 24h)
- Tool 16: `cicd_inventory_health_score.py` - Health Score DORA/SRE
- Tool 18: `cicd_pipeline_status.py` - Estado consolidado CI+CD

**PRs y Calidad:**
- Tool 20: `azdo_repo_branch_diff.py` - Análisis impacto entre ramas
- Tool 8: `azdo_scan_repos_vulnerabilities.py` - Escanea vulnerabilidades

**Release Management:**
- Tool 3: `azdo_release_cd_health.py` - Score de salud Release CD
- Tool 25: `azdo_release_explorer_rich.py` - Explorador interactivo releases

### GCP Tools (25 herramientas)

**Monitoreo de Servicios:**
- Tool 1: `gcp_monitor.py` - Monitorea recursos GCP
- Tool 2: `gke_deployments_report.py` - Reporte despliegues GKE
- Tool 24: `gke_monitor_node.py` - CPU/memoria por nodo
- Tool 25: `gke_monitor_pod.py` - CPU/memoria por pod

**Bases de Datos:**
- Tool 7: `gcp_disk_checker.py` - Monitorea disco Cloud SQL
- Tool 8: `gcp_database_checker.py` - Lista bases de datos
- Tool 9: `gcp_sql_comparator.py` - Compara instancias Cloud SQL

**Conectividad:**
- Tool 16: `pod_connectivity_checker.py` - Valida conectividad Pod → BD
- Tool 17: `deploy_dependency_checker.py` - Analiza ConfigMaps y conexiones
- Tool 19: `deployment_validator.py` - Valida ConfigMaps y Secrets

**Reportes:**
- Tool 21: `gcp_reports_viewer.py` - Genera gráficos HTML
- Tool 22: `run_inventory.py` - Inventario consolidado GCP

### AWS Tools (19 herramientas)

**Monitoreo:**
- Tool 13: `aws_cloudwatch_checker.py` - Monitorea alarmas
- Tool 4: `aws_rds_checker.py` - Analiza instancias RDS
- Tool 5: `aws_rds_storage_checker.py` - Monitorea almacenamiento RDS

**Infraestructura:**
- Tool 11: `aws_ec2_checker.py` - Analiza instancias EC2
- Tool 9: `aws_eks_checker.py` - Monitorea clusters EKS
- Tool 15: `aws_eks_pod_checker.py` - CPU/memoria por pod
- Tool 16: `aws_eks_node_checker.py` - Estado nodos EKS

### KPI Analyzer

- Análisis consolidado de KPIs
- Modelo de madurez DevSecOps (6 niveles)
- Benchmarks de industria
- Salida: JSON, CSV, HTML, Dashboard interactivo

---

## ❌ GAPS IDENTIFICADOS

### 1. **Falta: Agregación en Dashboard Único**
   - Herramientas individuales pero sin dashboard consolidado
   - No hay orquestación de múltiples fuentes (AZDO + GCP + AWS)
   - No hay visualización unificada matutina

### 2. **Falta: Monitoreo de Servicios Caídos**
   - No hay herramienta que verifique estado de servicios en producción
   - No hay health checks consolidados
   - No hay alertas de servicios down

### 3. **Falta: Análisis de PRs con Tiempo de Atención**
   - Tool 20 hace diff pero no análisis de tiempo de PR
   - Falta métrica de "time-to-merge"
   - Falta SLA de atención de PRs

### 4. **Falta: Automatización Diaria**
   - No hay scheduler/cron para ejecutar diariamente
   - No hay notificaciones (email, Slack, Teams)
   - No hay almacenamiento histórico de métricas

### 5. **Falta: Visualización Web Moderna**
   - Reportes JSON/Excel pero no dashboard web interactivo
   - No hay gráficos en tiempo real
   - No hay drill-down interactivo

---

## 🎯 PLAN DE IMPLEMENTACIÓN (Reutilizando Máximo)

### FASE 1: Crear Orquestador Principal (Tool 26)
**Objetivo:** Ejecutar todas las herramientas necesarias y consolidar outputs

```
Tool 26: "Dashboard Consolidado Matutino"
├── Ejecuta Tool 14 (CI Inventory) → ci_raw.json
├── Ejecuta Tool 15 (CD Inventory) → cd_raw.json
├── Ejecuta Tool 16 (Health Score) → health_score.xlsx
├── Ejecuta Tool 1 (Branch Policy) → branch_policy.json
├── Ejecuta GCP Tool 1 (Monitor) → gcp_monitor.json
├── Ejecuta GCP Tool 7 (SQL Disk) → sql_disk.json
├── Ejecuta AWS Tool 4 (RDS) → rds_status.json
└── Consolida todo en: dashboard_data.json
```

### FASE 2: Crear Dashboard Web Interactivo (Tool 27)
**Objetivo:** Visualizar datos consolidados en HTML/Web

```
Tool 27: "Dashboard Web Matutino"
├── Lee dashboard_data.json
├── Genera HTML con:
│   ├── Resumen ejecutivo (KPIs principales)
│   ├── Repositorios (branching compliance %)
│   ├── Pipelines (CI/CD health score)
│   ├── PRs (tiempo de atención)
│   ├── Servicios (estado GCP/AWS)
│   ├── Bases de datos (salud)
│   └── Alertas (servicios caídos)
└── Salida: dashboard.html
```

### FASE 3: Crear Herramienta de PRs con Tiempo de Atención (Tool 28)
**Objetivo:** Analizar tiempo de atención de PRs

```
Tool 28: "PR Time-to-Merge Analyzer"
├── Consulta API AZDO
├── Calcula:
│   ├── Tiempo promedio en review
│   ├── Tiempo promedio para merge
│   ├── PRs bloqueadas > X horas
│   ├── SLA compliance
│   └── Autores/reviewers más lentos
└── Salida: pr_metrics.json
```

### FASE 4: Crear Scheduler/Notificador (Tool 29)
**Objetivo:** Automatizar ejecución diaria y notificaciones

```
Tool 29: "Dashboard Scheduler"
├── Ejecuta Tool 26 (Orquestador) diariamente a las 7am
├── Genera Tool 27 (Dashboard Web)
├── Envía notificaciones:
│   ├── Email con resumen
│   ├── Slack con alertas críticas
│   └── Teams con dashboard link
└── Almacena histórico en outcome/dashboard_history/
```

---

## 📊 MATRIZ DE REUTILIZACIÓN

| Requerimiento | Herramienta Existente | Reutilización | Gap |
|---|---|---|---|
| Estado repos | Tool 1, 2b, 12, 13 | 100% | Agregación |
| Pipelines sin repos | Tool 9 | 100% | Agregación |
| Ramas en estrategia | Tool 1, 2b | 100% | Agregación |
| PRs con tiempo | - | 0% | **NUEVA Tool 28** |
| Servicios caídos | GCP Tool 1, AWS Tool 13 | 70% | Consolidación |
| BD caídas | GCP Tool 7, AWS Tool 4 | 100% | Agregación |
| Dashboard visual | KPI Analyzer | 50% | **NUEVA Tool 27** |
| Automatización diaria | - | 0% | **NUEVA Tool 29** |

---

## 🚀 PRÓXIMOS PASOS

1. **Validar con equipo:** ¿Cuál es la prioridad? (Orquestador → Dashboard → PRs → Scheduler)
2. **Definir scope:** ¿Qué métricas exactas en el dashboard matutino?
3. **Definir notificaciones:** ¿Email, Slack, Teams? ¿A quién?
4. **Definir horario:** ¿7am? ¿Qué zona horaria?
5. **Definir alertas:** ¿Qué es "crítico"? ¿Umbrales?

---

## 💡 VENTAJAS DE ESTE ENFOQUE

✅ Reutiliza 80% del código existente
✅ Minimiza desarrollo nuevo (solo 4 nuevas herramientas)
✅ Aprovecha cache 24h existente (sin sobrecargar APIs)
✅ Mantiene modularidad (cada tool independiente)
✅ Permite evolución incremental
✅ Usa infraestructura existente (outcome/, config.json, etc.)

---

## 📝 RESUMEN EJECUTIVO

**Situación Actual:**
- ✅ Tenemos 69 herramientas individuales (AZDO 25 + GCP 25 + AWS 19)
- ✅ Cada una genera reportes en JSON/Excel/HTML
- ❌ No hay orquestación centralizada
- ❌ No hay dashboard unificado
- ❌ No hay automatización diaria

**Propuesta:**
- Crear 4 nuevas herramientas (Tools 26-29)
- Reutilizar 80% del código existente
- Implementar en 4 fases incrementales
- Tiempo estimado: 3-4 semanas (dependiendo de prioridades)

**Impacto:**
- Dashboard matutino automático
- Visibilidad centralizada de repos, pipelines, servicios
- Alertas proactivas de problemas
- Reducción de tiempo de respuesta operacional
