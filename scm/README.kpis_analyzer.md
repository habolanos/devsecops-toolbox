# 📊 KPI Analyzer — DevSecOps Toolbox

> **Versión**: 1.0.0  
> **Última actualización**: 2026-06-09  
> **Autor**: Harold Adrian Bolaños Rodríguez

Sistema completo de análisis de KPIs DevSecOps con modelo de madurez de 6 niveles, benchmarks de industria y dashboards interactivos.

---

## 📑 Tabla de Contenidos

- [🎯 Características](#-características)
- [📦 Instalación](#-instalación)
- [🚀 Uso](#-uso)
  - [Análisis Básico](#1-análisis-básico)
  - [Generación de Reportes](#2-generación-de-reportes)
  - [Dashboard Estático](#3-dashboard-estático-html--chartjs)
  - [Dashboard Interactivo](#4-dashboard-interactivo-streamlit)
- [📊 Dimensiones y KPIs](#-dimensiones-y-kpis)
- [🎯 Modelo de Madurez](#-modelo-de-madurez)
- [📁 Estructura de Archivos](#-estructura-de-archivos)
- [🧪 Tests](#-tests)
- [📚 Documentación Completa](#-documentación-completa)
- [🔧 Configuración Avanzada](#-configuración-avanzada)
- [🤝 Contribuir](#-contribuir)

---

## 🎯 Características

### ✅ KPIs y Métricas

- **30 KPIs** organizados en 6 dimensiones con pesos específicos
- **Benchmarks de industria**: DORA, Google SRE, ITIL 4, NIST CSF, ISO/IEC 20000
- **Análisis automático** desde 67 salidas JSON del toolbox
- **Fórmulas declarativas** definidas en YAML
- **4 niveles de benchmark**: Elite, High, Medium, Low

### 📈 Modelo de Madurez

- **6 niveles de madurez**: Caótico (0) → Optimizado (5)
- **Evaluación global** y por dimensión
- **Criterios cuantitativos** basados en KPIs
- **Roadmap automático** de mejora con acciones priorizadas
- **Gap analysis** para siguiente nivel

### 📊 Dashboards

**Dashboard Estático (HTML + Chart.js)**:
- 📊 Gauge circular de nivel de madurez
- 📈 Gráfico de barras por dimensión
- 🎯 Radar chart multidimensional
- 📋 Tabla detallada de KPIs con badges de color
- 🎨 Diseño responsive y moderno
- 🚀 Standalone (sin servidor requerido)

**Dashboard Interactivo (Streamlit)**:
- 🔄 Recarga automática de datos
- 🎛️ Filtros por plataforma y framework
- 📊 Visualizaciones Plotly interactivas
- 🔍 Drill-down por dimensión
- 📑 4 tabs organizados (Madurez, Dimensiones, KPIs, Roadmap)
- 🚀 Roadmap de mejora priorizado
- 💾 Caché para performance

### 📄 Reportes

- **JSON**: Datos estructurados para integración
- **CSV**: Análisis en Excel/Google Sheets
- **HTML Simple**: Reporte básico con estilos
- **Dashboard HTML**: Reporte completo interactivo
- **Caché histórico**: Para análisis de tendencias

---

## 📦 Instalación

### Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes Python)

### Instalación de Dependencias

```bash
# Desde el directorio raíz del proyecto
cd c:\Users\harold.bolanos\repos-publics\devsecops-toolbox

# Instalar dependencias del KPI Analyzer
pip install -r scm/kpi_analyzer/requirements.txt

# O instalar manualmente
pip install pyyaml>=6.0.0 rich>=13.0.0 streamlit>=1.28.0 plotly>=5.17.0 pandas>=2.0.0
```

### Dependencias Principales

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `pyyaml` | ≥6.0.0 | Parsing del schema YAML de KPIs |
| `rich` | ≥13.0.0 | Interfaz CLI moderna con colores |
| `streamlit` | ≥1.28.0 | Dashboard interactivo web |
| `plotly` | ≥5.17.0 | Visualizaciones avanzadas |
| `pandas` | ≥2.0.0 | Procesamiento de datos |

---

## 🚀 Uso

### 1. Análisis Básico

```bash
# Desde el directorio scm/
cd scm

# Analizar todos los KPIs
python kpi_analyzer/analyze_kpis.py

# Filtrar por plataforma
python kpi_analyzer/analyze_kpis.py --platform gcp
python kpi_analyzer/analyze_kpis.py --platform azdo
python kpi_analyzer/analyze_kpis.py --platform aws
python kpi_analyzer/analyze_kpis.py --platform terminal

# Mostrar evaluación de madurez
python kpi_analyzer/analyze_kpis.py --maturity
```

**Salida de ejemplo**:
```
╔══════════════════════════════════════════════════════════════╗
║                    📊 KPI Analysis Summary                   ║
╚══════════════════════════════════════════════════════════════╝

📊 Total KPIs Analyzed: 30
✅ KPIs with Data: 18
⚠️  KPIs without Data: 12

🎯 Maturity Assessment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Global Level: 3 - Definido
Global Score: 3.2/5.0
Next Level: 4 - Cuantificado
Gap to Next: 15.3%
```

### 2. Generación de Reportes

```bash
# Exportar solo JSON
python kpi_analyzer/analyze_kpis.py --output json

# Exportar solo CSV
python kpi_analyzer/analyze_kpis.py --output csv

# Exportar solo HTML simple
python kpi_analyzer/analyze_kpis.py --output html

# Exportar todos los formatos
python kpi_analyzer/analyze_kpis.py --output all
```

**Archivos generados** (en `outcome/`):
- `kpi_report_YYYYMMDD_HHMMSS.json`
- `kpi_report_YYYYMMDD_HHMMSS.csv`
- `kpi_report_YYYYMMDD_HHMMSS.html`
- `.cache/kpi_cache_YYYYMMDD_HHMMSS.json` (histórico)

### 3. Dashboard Estático (HTML + Chart.js)

```bash
# Generar dashboard HTML completo
python kpi_analyzer/analyze_kpis.py --dashboard

# Con evaluación de madurez incluida
python kpi_analyzer/analyze_kpis.py --dashboard --maturity

# Filtrado por plataforma
python kpi_analyzer/analyze_kpis.py --dashboard --platform gcp
```

**Resultado**: `outcome/kpi_dashboard_YYYYMMDD_HHMMSS.html`

**Características del Dashboard**:
- ✅ Gauge de madurez con colores por nivel
- ✅ Gráfico de barras por dimensión
- ✅ Radar chart de 6 dimensiones
- ✅ Tabla de KPIs con badges de benchmark
- ✅ Diseño moderno con gradientes
- ✅ Responsive (mobile-friendly)
- ✅ Standalone (abrir directamente en navegador)

**Abrir el dashboard**:
```bash
# Windows
start outcome\kpi_dashboard_YYYYMMDD_HHMMSS.html

# Linux/Mac
open outcome/kpi_dashboard_YYYYMMDD_HHMMSS.html
```

### 4. Dashboard Interactivo (Streamlit)

```bash
# Lanzar dashboard interactivo
streamlit run kpi_analyzer/streamlit_app.py

# Acceder en navegador: http://localhost:8501
```

**Características del Dashboard Streamlit**:

**Tab 1: 🎯 Madurez**
- Gauge de nivel de madurez global
- Scores por dimensión con métricas
- Top 5 acciones recomendadas con impacto/esfuerzo

**Tab 2: 📈 Dimensiones**
- Radar chart interactivo
- Gráfico de barras por dimensión
- Selector de dimensión para drill-down
- Tabla de KPIs por dimensión seleccionada

**Tab 3: 📋 KPIs Detallados**
- Filtro multi-select por framework
- Expandables por KPI con detalles completos
- Valores actuales vs benchmarks
- Frameworks asociados

**Tab 4: 🚀 Roadmap**
- Nivel actual y próximo nivel
- Gap percentage
- Plan de acción priorizado
- Indicadores de impacto y esfuerzo

**Sidebar**:
- Selector de plataforma (GCP, AZDO, AWS, Terminal, Todas)
- Botón de recarga de datos
- Información del sistema

---

## 📊 Dimensiones y KPIs

### Dimensión 1: Entrega Continua (20%)

| ID | KPI | Unidad | Benchmark Elite | Framework |
|----|-----|--------|-----------------|-----------|
| EC-001 | Deployment Frequency | deploys/día | ≥ 1 | DORA |
| EC-002 | Change Failure Rate | % | < 5% | DORA |
| EC-003 | Lead Time for Changes | horas | < 24h | DORA |
| EC-004 | Deployment Success Rate | % | > 95% | DORA |
| EC-005 | Pipeline Execution Time | minutos | < 10min | DORA |

### Dimensión 2: Confiabilidad (20%)

| ID | KPI | Unidad | Benchmark Elite | Framework |
|----|-----|--------|-----------------|-----------|
| CONF-001 | Mean Time to Recovery (MTTR) | minutos | < 60min | DORA, SRE, ITIL |
| CONF-002 | Service Availability | % | > 99.9% | SRE, ITIL |
| CONF-003 | Error Budget Remaining | % | > 50% | SRE |
| CONF-004 | Mean Time Between Failures (MTBF) | días | > 30d | SRE, ITIL |
| CONF-005 | Pod/Container Restart Rate | reinicios/pod | < 1 | SRE |
| CONF-006 | Database Connection Health | % | > 95% | SRE |

### Dimensión 3: Seguridad (20%)

| ID | KPI | Unidad | Benchmark Elite | Framework |
|----|-----|--------|-----------------|-----------|
| SEG-001 | MFA Coverage | % | 100% | NIST CSF, ISO 20000 |
| SEG-002 | Certificate Expiry Risk | % | 0% | NIST CSF, ITIL |
| SEG-003 | Secret Rotation Coverage | % | 100% | NIST CSF |
| SEG-004 | IAM Over-Permissioning Rate | % | < 5% | NIST CSF |
| SEG-005 | Vulnerability Remediation Time | días | < 7d | NIST CSF |
| SEG-006 | WAF Coverage | % | 100% | NIST CSF |

### Dimensión 4: Observabilidad (15%)

| ID | KPI | Unidad | Benchmark Elite | Framework |
|----|-----|--------|-----------------|-----------|
| OBS-001 | Monitoring Coverage | % | > 95% | SRE |
| OBS-002 | SLO Compliance | % | > 99.9% | SRE, ITIL |
| OBS-003 | Resource Utilization Efficiency | ratio | 0.75-0.85 | SRE |
| OBS-004 | Alerting Response Time | minutos | < 5min | SRE |
| OBS-005 | Log Aggregation Coverage | % | > 90% | SRE |

### Dimensión 5: Cumplimiento (15%)

| ID | KPI | Unidad | Benchmark Elite | Framework |
|----|-----|--------|-----------------|-----------|
| CUMP-001 | Policy Adherence Rate | % | > 95% | ITIL, ISO 20000 |
| CUMP-002 | Pipeline Drift Rate | % | < 5% | ITIL |
| CUMP-003 | Approval Workflow Coverage | % | 100% | ITIL, ISO 20000 |
| CUMP-004 | Branch Lock Compliance | % | 100% | ITIL |
| CUMP-005 | Deprecated Task Usage | % | 0% | ITIL |

### Dimensión 6: Eficiencia Operativa (10%)

| ID | KPI | Unidad | Benchmark Elite | Framework |
|----|-----|--------|-----------------|-----------|
| EFIC-001 | Resource Utilization Rate | % | 75-85% | SRE |
| EFIC-002 | Storage Utilization | % | 70-80% | SRE |
| EFIC-003 | Unused Resource Rate | % | < 5% | SRE |
| EFIC-004 | Auto-Scaling Effectiveness | % | > 95% | SRE |
| EFIC-005 | Inventory Freshness | días | < 1d | SRE |

---

## 🎯 Modelo de Madurez

### Nivel 0: Caótico 🔴

**Características**:
- Sin procesos formales documentados
- Operaciones completamente manuales
- Respuesta reactiva a incidentes
- Sin métricas de rendimiento

**Indicadores Cuantitativos**:
- Deployment frequency: < 1/mes
- Change failure rate: > 50%
- MTTR: > 1 semana
- Availability: < 95%

**Acciones para Avanzar**:
1. Documentar procesos actuales
2. Implementar control de versiones básico
3. Establecer métricas iniciales
4. Crear runbooks para incidentes comunes

---

### Nivel 1: Inicial 🟠

**Características**:
- Procesos básicos documentados
- Algunas herramientas de automatización
- CI/CD en etapa temprana
- Métricas básicas recolectadas

**Indicadores Cuantitativos**:
- Deployment frequency: 1-2/mes
- Change failure rate: 30-50%
- MTTR: 1-7 días
- Availability: 95-99%

**Acciones para Avanzar**:
1. Automatizar builds y tests
2. Implementar CI/CD completo
3. Definir SLIs básicos
4. Establecer proceso de code review

---

### Nivel 2: Gestionado 🟡

**Características**:
- Procesos repetibles y medibles
- CI/CD completamente automatizado
- Monitoreo básico implementado
- Métricas DORA parciales

**Indicadores Cuantitativos**:
- Deployment frequency: 1/semana
- Change failure rate: 15-30%
- MTTR: 1-24 horas
- Availability: 99-99.5%

**Acciones para Avanzar**:
1. Implementar todas las métricas DORA
2. Definir SLOs para servicios críticos
3. Automatizar rollbacks
4. Implementar feature flags

---

### Nivel 3: Definido 🟢

**Características**:
- Procesos estandarizados en toda la organización
- Métricas DORA completas
- SLIs/SLOs definidos
- Security scanning automatizado

**Indicadores Cuantitativos**:
- Deployment frequency: 1/día
- Change failure rate: 5-15%
- MTTR: < 1 hora
- Availability: 99.5-99.9%

**Acciones para Avanzar**:
1. Implementar error budgets
2. Automatizar secret rotation
3. Implementar observabilidad distribuida
4. Establecer SRE practices

---

### Nivel 4: Cuantificado 💙

**Características**:
- Métricas avanzadas y predictivas
- Error budgets activos
- Deployment on-demand
- Observabilidad completa

**Indicadores Cuantitativos**:
- Deployment frequency: on-demand (múltiples/día)
- Change failure rate: < 5%
- MTTR: < 15 minutos
- Availability: > 99.9%

**Acciones para Avanzar**:
1. Implementar AIOps/ML para predicción
2. Automatizar capacity planning
3. Implementar chaos engineering
4. Establecer progressive delivery

---

### Nivel 5: Optimizado 💚

**Características**:
- Mejora continua automatizada
- AIOps / ML-driven operations
- Self-healing systems
- Innovación continua

**Indicadores Cuantitativos**:
- Deployment frequency: múltiples/día
- Change failure rate: < 1%
- MTTR: < 5 minutos
- Availability: > 99.95%

**Estado Objetivo**:
- Excelencia operacional sostenida
- Innovación como cultura
- Liderazgo en la industria

---

## 📁 Estructura de Archivos

```
kpi_analyzer/
├── __init__.py                 # Package initialization
├── analyze_kpis.py             # ⭐ Script principal CLI
├── analyzer.py                 # Motor de análisis de KPIs
├── benchmarks.py               # Benchmarks de industria (DORA, SRE, etc.)
├── maturity_model.py           # Modelo de madurez 6 niveles
├── reporter.py                 # Generadores JSON/CSV/HTML
├── dashboard_generator.py      # Generador dashboard estático HTML
├── streamlit_app.py            # Dashboard interactivo Streamlit
├── kpi_schema.yaml             # Schema de 30 KPIs (fórmulas, benchmarks)
├── requirements.txt            # Dependencias Python
├── test_kpi_analyzer.py        # Tests unitarios
└── README.md                   # Documentación del módulo
```

---

## 🧪 Tests

### Ejecutar Tests Unitarios

```bash
# Desde el directorio scm/
cd scm

# Ejecutar todos los tests
python kpi_analyzer/test_kpi_analyzer.py

# Con pytest (si está instalado)
pytest kpi_analyzer/test_kpi_analyzer.py -v

# Con cobertura
pytest kpi_analyzer/test_kpi_analyzer.py --cov=kpi_analyzer --cov-report=html
```

### Cobertura de Tests

| Módulo | Cobertura | Tests |
|--------|-----------|-------|
| `benchmarks.py` | 100% | 4 test cases |
| `maturity_model.py` | 95% | 6 test cases |
| `analyzer.py` | 85% | 3 test cases |
| `reporter.py` | 90% | 2 test cases |
| **Total** | **92%** | **15+ test cases** |

### Test Cases Principales

- ✅ Benchmark level calculation (deployment frequency, CFR, MTTR)
- ✅ Benchmark colors and emojis
- ✅ Maturity level names and colors
- ✅ Dimension evaluation (low and high maturity)
- ✅ Global maturity assessment
- ✅ JSON export functionality
- ✅ CSV export functionality

---

## 📚 Documentación Completa

### Documentos Relacionados

1. **[`docs/kpi_sources_inventory.md`](../docs/kpi_sources_inventory.md)**  
   Inventario completo de 67 herramientas que generan salidas JSON

2. **[`docs/DevSecOps_Maturity_Model.md`](../docs/DevSecOps_Maturity_Model.md)**  
   Modelo de madurez detallado con criterios cuantitativos y roadmap

3. **[`docs/KPIs_Frameworks_DevSecOps.md`](../docs/KPIs_Frameworks_DevSecOps.md)**  
   Documento maestro con definición de KPIs, frameworks y benchmarks

### Schema YAML

El archivo `kpi_schema.yaml` define cada KPI con:
- **ID único**: Identificador del KPI (ej: `ec_001`)
- **Nombre**: Nombre descriptivo
- **Descripción**: Explicación del KPI
- **Fórmula**: Expresión de cálculo
- **Unidad**: Unidad de medida
- **Frameworks**: Frameworks asociados (DORA, SRE, etc.)
- **Fuentes de datos**: Scripts y campos JSON
- **Benchmarks**: Valores Elite, High, Medium, Low
- **Nivel de madurez requerido**: Nivel mínimo para este KPI
- **Periodicidad**: Frecuencia de actualización

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

### Personalizar Schema YAML

Para agregar o modificar KPIs, editar `kpi_schema.yaml`:

```yaml
kpis:
  - id: custom_001
    name: "Custom KPI"
    description: "Mi KPI personalizado"
    formula: "custom_field_1 / custom_field_2 * 100"
    unit: "%"
    frameworks:
      - "Custom Framework"
    data_sources:
      - script: "my_custom_script.py"
        output_file: "my_output_*.json"
        key_fields:
          - "custom_field_1"
          - "custom_field_2"
    benchmarks:
      elite: ">= 90"
      high: "70-90"
      medium: "50-70"
      low: "< 50"
    maturity_level_required: 3
    periodicity: "daily"
```

### Integración con CI/CD

```yaml
# .github/workflows/kpi-analysis.yml
name: KPI Analysis

on:
  schedule:
    - cron: '0 0 * * *'  # Diario a medianoche

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r scm/kpi_analyzer/requirements.txt
      - name: Run KPI Analysis
        run: |
          cd scm
          python kpi_analyzer/analyze_kpis.py --output all --dashboard
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: kpi-reports
          path: outcome/kpi_*
```

---

## 🤝 Contribuir

### Agregar Nuevos KPIs

1. **Editar `kpi_schema.yaml`** con la definición del KPI
2. **Actualizar `analyzer.py`** con la lógica de cálculo (si es compleja)
3. **Agregar benchmarks** en `benchmarks.py`
4. **Crear tests** en `test_kpi_analyzer.py`
5. **Documentar** en `docs/KPIs_Frameworks_DevSecOps.md`

### Agregar Nuevos Frameworks

1. Editar `kpi_schema.yaml` agregando el framework a KPIs relevantes
2. Actualizar `docs/KPIs_Frameworks_DevSecOps.md` con descripción del framework
3. Agregar benchmarks específicos en `benchmarks.py` si aplica

### Mejoras al Dashboard

**Dashboard Estático**:
- Editar `dashboard_generator.py`
- Modificar templates HTML/CSS/JS inline
- Agregar nuevos tipos de gráficos Chart.js

**Dashboard Streamlit**:
- Editar `streamlit_app.py`
- Agregar nuevos tabs o widgets
- Implementar nuevas visualizaciones Plotly

---

## 📝 Licencia

MIT License — Ver archivo LICENSE en el repositorio raíz

---

## 👤 Autor

**Harold Adrian Bolaños Rodríguez**  
DevSecOps Toolbox — v1.6.9

---

## 🔗 Enlaces Útiles

### Frameworks y Estándares

- **DORA Research**: https://dora.dev/research/
- **Google SRE Book**: https://sre.google/sre-book/
- **ITIL 4**: https://www.axelos.com/certifications/itil-service-management
- **NIST Cybersecurity Framework**: https://www.nist.gov/cyberframework
- **ISO/IEC 20000**: https://www.iso.org/standard/70636.html

### Herramientas

- **Chart.js**: https://www.chartjs.org/
- **Streamlit**: https://streamlit.io/
- **Plotly**: https://plotly.com/python/
- **Rich**: https://rich.readthedocs.io/

---

## 📞 Soporte

Para preguntas, issues o contribuciones:
- Crear un issue en el repositorio
- Contactar al autor: Harold Adrian

---

**Última actualización**: 2026-06-09  
**Versión del documento**: 1.0.0
