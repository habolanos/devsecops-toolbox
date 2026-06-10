# 📊 KPI Analyzer — DevSecOps Toolbox

> **Versión**: 1.0.0  
> **Última actualización**: 2026-06-09

Sistema completo de análisis de KPIs DevSecOps con modelo de madurez de 6 niveles, benchmarks de industria y dashboards interactivos.

---

## 🎯 Características

- ✅ **30 KPIs** organizados en 6 dimensiones (Entrega Continua, Confiabilidad, Seguridad, Observabilidad, Cumplimiento, Eficiencia)
- ✅ **Modelo de madurez** de 6 niveles (0: Caótico → 5: Optimizado)
- ✅ **Benchmarks de industria**: DORA, Google SRE, ITIL 4, NIST CSF, ISO 20000
- ✅ **Análisis automático** desde 67 salidas JSON del toolbox
- ✅ **Reportes múltiples**: JSON, CSV, HTML
- ✅ **Dashboard estático** con Chart.js (gauges, radar, bar charts)
- ✅ **Dashboard interactivo** con Streamlit (filtros, drill-down, tiempo real)
- ✅ **Evaluación de madurez** global y por dimensión
- ✅ **Roadmap automático** de mejora basado en gaps
- ✅ **Tests unitarios** con cobertura > 80%

---

## 📦 Instalación

```bash
# Instalar dependencias
pip install -r scm/kpi_analyzer/requirements.txt

# O desde el directorio raíz
pip install -r scm/requirements.txt
```

### Dependencias

- `pyyaml>=6.0.0` — Parsing del schema YAML
- `rich>=13.0.0` — Interfaz CLI moderna
- `streamlit>=1.28.0` — Dashboard interactivo
- `plotly>=5.17.0` — Visualizaciones avanzadas
- `pandas>=2.0.0` — Procesamiento de datos

---

## 🚀 Uso

### Menú Interactivo (Recomendado) ⭐

```bash
# Lanzar menú interactivo del KPI Analyzer
python scm/kpi_analyzer/tools.py
```

**Opciones disponibles en el menú**:
1. 📊 Análisis Básico de KPIs
2. 🎯 Análisis por Plataforma (GCP, AZDO, AWS, Terminal)
3. 🎯 Evaluación de Madurez
4. 📄 Generar Reporte JSON
5. 📊 Generar Reporte CSV
6. 🌐 Generar Reporte HTML Simple
7. 📈 Dashboard Estático (HTML + Chart.js)
8. 🚀 Dashboard Interactivo (Streamlit)
9. 📦 Análisis Completo (Todos los Reportes)
10. 🧪 Ejecutar Tests Unitarios
Q. 🔙 Volver al Menú Principal

---

### 1. Análisis Básico (Línea de Comandos)

```bash
# Analizar todos los KPIs
python scm/kpi_analyzer/analyze_kpis.py

# Filtrar por plataforma
python scm/kpi_analyzer/analyze_kpis.py --platform gcp
python scm/kpi_analyzer/analyze_kpis.py --platform azdo
python scm/kpi_analyzer/analyze_kpis.py --platform aws

# Mostrar evaluación de madurez
python scm/kpi_analyzer/analyze_kpis.py --maturity
```

### 2. Generación de Reportes

```bash
# Exportar solo JSON
python scm/kpi_analyzer/analyze_kpis.py --output json

# Exportar solo CSV
python scm/kpi_analyzer/analyze_kpis.py --output csv

# Exportar todos los formatos
python scm/kpi_analyzer/analyze_kpis.py --output all
```

### 3. Dashboard Estático (HTML + Chart.js)

```bash
# Generar dashboard HTML completo
python scm/kpi_analyzer/analyze_kpis.py --dashboard

# El dashboard se genera en: outcome/kpi_dashboard_YYYYMMDD_HHMMSS.html
# Abrir en navegador para visualización interactiva
```

**Características del Dashboard Estático**:
- 📊 Gauge de nivel de madurez global
- 📈 Gráfico de barras por dimensión
- 🎯 Radar chart de dimensiones
- 📋 Tabla detallada de todos los KPIs
- 🎨 Diseño responsive y moderno
- 🚀 Sin dependencias de servidor (standalone)

### 4. Dashboard Interactivo (Streamlit)

```bash
# Lanzar dashboard interactivo
streamlit run scm/kpi_analyzer/streamlit_app.py

# Acceder en: http://localhost:8501
```

**Características del Dashboard Streamlit**:
- 🔄 Recarga automática de datos
- 🎛️ Filtros por plataforma y framework
- 📊 Visualizaciones interactivas (Plotly)
- 🔍 Drill-down por dimensión
- 📈 Tabs organizados (Madurez, Dimensiones, KPIs, Roadmap)
- 🚀 Roadmap de mejora priorizado
- 💾 Caché de datos para performance

---

## 📁 Estructura de Archivos

```
scm/kpi_analyzer/
├── __init__.py                 # Package initialization
├── tools.py                    # ⭐ Menú interactivo (launcher)
├── analyze_kpis.py             # Script principal CLI
├── analyzer.py                 # Motor de análisis de KPIs
├── benchmarks.py               # Benchmarks de industria
├── maturity_model.py           # Modelo de madurez 6 niveles
├── reporter.py                 # Generadores JSON/CSV/HTML
├── dashboard_generator.py      # Generador dashboard estático
├── streamlit_app.py            # Dashboard interactivo Streamlit
├── kpi_schema.yaml             # Schema de 30 KPIs
├── requirements.txt            # Dependencias
├── test_kpi_analyzer.py        # Tests unitarios
└── README.md                   # Este archivo
```

---

## 📊 Dimensiones y KPIs

### Dimensión 1: Entrega Continua (20%)

- **EC-001**: Deployment Frequency (deploys/día)
- **EC-002**: Change Failure Rate (%)
- **EC-003**: Lead Time for Changes (horas)
- **EC-004**: Deployment Success Rate (%)
- **EC-005**: Pipeline Execution Time (minutos)

### Dimensión 2: Confiabilidad (20%)

- **CONF-001**: Mean Time to Recovery - MTTR (minutos)
- **CONF-002**: Service Availability (%)
- **CONF-003**: Error Budget Remaining (%)
- **CONF-004**: Mean Time Between Failures - MTBF (días)
- **CONF-005**: Pod/Container Restart Rate (reinicios/pod)
- **CONF-006**: Database Connection Health (%)

### Dimensión 3: Seguridad (20%)

- **SEG-001**: MFA Coverage (%)
- **SEG-002**: Certificate Expiry Risk (%)
- **SEG-003**: Secret Rotation Coverage (%)
- **SEG-004**: IAM Over-Permissioning Rate (%)
- **SEG-005**: Vulnerability Remediation Time (días)
- **SEG-006**: WAF Coverage (%)

### Dimensión 4: Observabilidad (15%)

- **OBS-001**: Monitoring Coverage (%)
- **OBS-002**: SLO Compliance (%)
- **OBS-003**: Resource Utilization Efficiency (ratio)
- **OBS-004**: Alerting Response Time (minutos)
- **OBS-005**: Log Aggregation Coverage (%)

### Dimensión 5: Cumplimiento (15%)

- **CUMP-001**: Policy Adherence Rate (%)
- **CUMP-002**: Pipeline Drift Rate (%)
- **CUMP-003**: Approval Workflow Coverage (%)
- **CUMP-004**: Branch Lock Compliance (%)
- **CUMP-005**: Deprecated Task Usage (%)

### Dimensión 6: Eficiencia Operativa (10%)

- **EFIC-001**: Resource Utilization Rate (%)
- **EFIC-002**: Storage Utilization (%)
- **EFIC-003**: Unused Resource Rate (%)
- **EFIC-004**: Auto-Scaling Effectiveness (%)
- **EFIC-005**: Inventory Freshness (días)

---

## 🎯 Modelo de Madurez

### Nivel 0: Caótico
- Sin procesos formales
- Operaciones manuales y reactivas
- Deployment frequency < 1/mes
- Change failure rate > 50%

### Nivel 1: Inicial
- Procesos básicos documentados
- CI/CD en etapa temprana
- Deployment frequency 1-2/mes
- Change failure rate 30-50%

### Nivel 2: Gestionado
- Procesos repetibles y medibles
- CI/CD completamente automatizado
- Deployment frequency 1/semana
- Change failure rate 15-30%

### Nivel 3: Definido
- Procesos estandarizados
- Métricas DORA completas
- Deployment frequency 1/día
- Change failure rate 5-15%

### Nivel 4: Cuantificado
- Métricas avanzadas
- Error budgets activos
- Deployment on-demand
- Change failure rate < 5%

### Nivel 5: Optimizado
- Mejora continua automatizada
- AIOps / ML-driven operations
- Deployment múltiples/día
- Change failure rate < 1%

---

## 🧪 Tests

```bash
# Ejecutar tests unitarios
python scm/kpi_analyzer/test_kpi_analyzer.py

# Con pytest (si está instalado)
pytest scm/kpi_analyzer/test_kpi_analyzer.py -v
```

**Cobertura de Tests**:
- ✅ Benchmarks module (100%)
- ✅ Maturity model (95%)
- ✅ KPI Analyzer (85%)
- ✅ Reporter (90%)

---

## 📚 Documentación Completa

- **Inventario de Fuentes**: [`docs/kpi_sources_inventory.md`](../../docs/kpi_sources_inventory.md)
- **Modelo de Madurez**: [`docs/DevSecOps_Maturity_Model.md`](../../docs/DevSecOps_Maturity_Model.md)
- **Frameworks y KPIs**: [`docs/KPIs_Frameworks_DevSecOps.md`](../../docs/KPIs_Frameworks_DevSecOps.md)

---

## 🔧 Configuración Avanzada

### Variables de Entorno

```bash
# Directorio de salida personalizado
export DEVSECOPS_OUTPUT_DIR=/custom/path/outcome

# Modo debug
export DEVSECOPS_DEBUG=1

# Modo verbose
export DEVSECOPS_VERBOSE=1
```

### Schema YAML Personalizado

El archivo `kpi_schema.yaml` puede ser modificado para:
- Agregar nuevos KPIs
- Modificar fórmulas de cálculo
- Actualizar benchmarks
- Cambiar pesos de dimensiones

---

## 🤝 Contribuir

Para agregar nuevos KPIs:

1. Editar `kpi_schema.yaml` con la definición del KPI
2. Actualizar `analyzer.py` con la lógica de cálculo
3. Agregar benchmarks en `benchmarks.py`
4. Actualizar tests en `test_kpi_analyzer.py`
5. Documentar en `docs/KPIs_Frameworks_DevSecOps.md`

---

## 📝 Licencia

MIT License — Ver archivo LICENSE en el repositorio raíz

---

## 👤 Autor

**Harold Adrian Bolaños Rodríguez**  
DevSecOps Toolbox — v1.6.9

---

## 🔗 Enlaces

- **Repositorio**: (internal repo)
- **DORA Research**: https://dora.dev/research/
- **Google SRE Book**: https://sre.google/sre-book/
- **NIST CSF**: https://www.nist.gov/cyberframework
