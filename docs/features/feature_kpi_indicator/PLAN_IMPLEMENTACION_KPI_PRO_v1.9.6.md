# Plan de Implementación: KPI Analyzer Pro v1.9.6

**Fecha:** 9 de Julio de 2026  
**Versión:** 1.9.6  
**Estado:** 📋 PLAN DETALLADO

---

## 🎯 Objetivo

Integrar los componentes de **Dashboard Matutino (Opción 6)** en **KPI Analyzer (Opción 5)** para crear una **plataforma unificada profesional nivel PRO** con análisis de KPIs, Health Score DORA y dashboards consolidados.

---

## 📋 Fases de Implementación

### Fase 1: Preparación (2 horas)

#### 1.1 Crear Estructura de Directorios
```bash
scm/kpi_analyzer/
├── __init__.py
├── tools.py (MODIFICAR)
├── analyze_kpis.py (EXISTENTE)
├── streamlit_app.py (EXISTENTE)
├── test_kpi_analyzer.py (EXISTENTE)
├── consolidator.py (NUEVO - de dashboard)
├── generator.py (NUEVO - de dashboard)
├── scheduler.py (NUEVO - de dashboard)
├── health_score.py (NUEVO)
├── exporter.py (NUEVO)
└── requirements.txt (ACTUALIZAR)
```

#### 1.2 Refactorizar Módulos de Dashboard
**Archivos a Copiar y Refactorizar:**
- `dashboard/dashboard_consolidator.py` → `kpi_analyzer/consolidator.py`
- `dashboard/dashboard_generator.py` → `kpi_analyzer/generator.py`
- `dashboard/dashboard_scheduler.py` → `kpi_analyzer/scheduler.py`

**Cambios:**
- Actualizar imports
- Cambiar rutas de salida
- Unificar configuración

#### 1.3 Crear Nuevos Módulos
**health_score.py:**
```python
class HealthScoreDORA:
    """Calcula Health Score usando métricas DORA"""
    def __init__(self, org, project, pat):
        pass
    
    def calculate_deployment_frequency(self):
        """Calcula frecuencia de despliegue"""
        pass
    
    def calculate_lead_time(self):
        """Calcula tiempo de entrega"""
        pass
    
    def calculate_mttr(self):
        """Calcula tiempo de recuperación"""
        pass
    
    def calculate_change_failure_rate(self):
        """Calcula tasa de fallos"""
        pass
    
    def get_overall_score(self):
        """Retorna puntuación general"""
        pass
```

**exporter.py:**
```python
class ExporterPro:
    """Exporta datos a múltiples formatos"""
    def __init__(self, data):
        pass
    
    def to_json(self, filepath):
        """Exportar a JSON"""
        pass
    
    def to_csv(self, filepath):
        """Exportar a CSV"""
        pass
    
    def to_html(self, filepath):
        """Exportar a HTML"""
        pass
    
    def to_excel(self, filepath):
        """Exportar a Excel con formatos"""
        pass
```

---

### Fase 2: Integración (4 horas)

#### 2.1 Actualizar tools.py

**Estructura Nueva:**
```python
TOOLS = {
    # ═══════════════════════════════════════════════════════════
    # ANÁLISIS DE KPIs (1-5)
    # ═══════════════════════════════════════════════════════════
    "1": {
        "name": "Análisis Básico de KPIs",
        "emoji": "📊",
        "script": "analyze_kpis.py",
        "args": [],
        "group": "analysis",
        "description": "Analizar todos los KPIs desde salidas JSON"
    },
    "2": {
        "name": "Análisis por Plataforma",
        "emoji": "🎯",
        "script": "analyze_kpis.py",
        "args": None,
        "group": "analysis",
        "description": "Filtrar análisis por plataforma (GCP, AZDO, AWS, Terminal)"
    },
    "3": {
        "name": "Evaluación de Madurez",
        "emoji": "📈",
        "script": "analyze_kpis.py",
        "args": ["--maturity"],
        "group": "analysis",
        "description": "Mostrar evaluación de madurez DevSecOps (6 niveles)"
    },
    "4": {
        "name": "Análisis Completo",
        "emoji": "📦",
        "script": "analyze_kpis.py",
        "args": ["--output", "all", "--maturity", "--dashboard"],
        "group": "analysis",
        "description": "Generar todos los reportes y dashboard"
    },
    "5": {
        "name": "Tests Unitarios",
        "emoji": "🧪",
        "script": "test_kpi_analyzer.py",
        "args": [],
        "group": "analysis",
        "description": "Ejecutar suite de tests del KPI Analyzer"
    },
    
    # ═══════════════════════════════════════════════════════════
    # HEALTH SCORE & DASHBOARDS (6-12)
    # ═══════════════════════════════════════════════════════════
    "6": {
        "name": "Health Score DORA",
        "emoji": "💪",
        "script": "health_score.py",
        "args": None,
        "group": "dashboard",
        "description": "Calcular Health Score usando métricas DORA"
    },
    "7": {
        "name": "Dashboard Estático (HTML + Chart.js)",
        "emoji": "📈",
        "script": "analyze_kpis.py",
        "args": ["--dashboard", "--maturity"],
        "group": "dashboard",
        "description": "Generar dashboard HTML interactivo con gráficos"
    },
    "8": {
        "name": "Dashboard Interactivo (Streamlit)",
        "emoji": "🚀",
        "script": "streamlit_app.py",
        "args": None,
        "group": "dashboard",
        "description": "Lanzar dashboard web interactivo con Streamlit"
    },
    "9": {
        "name": "Dashboard Matutino AZDO",
        "emoji": "🌅",
        "script": "dashboard_matutino.py",
        "args": None,
        "group": "dashboard",
        "description": "Dashboard consolidado AZDO con Health Score DORA"
    },
    "10": {
        "name": "Consolidador de Datos",
        "emoji": "🔄",
        "script": "consolidator.py",
        "args": None,
        "group": "dashboard",
        "description": "Consolidar datos de múltiples fuentes"
    },
    "11": {
        "name": "Planificador Automático",
        "emoji": "⏰",
        "script": "scheduler.py",
        "args": None,
        "group": "dashboard",
        "description": "Planificar ejecución automática de análisis"
    },
    "12": {
        "name": "Generador Dashboard Pro",
        "emoji": "🎨",
        "script": "generator.py",
        "args": None,
        "group": "dashboard",
        "description": "Generar dashboard profesional con formatos avanzados"
    },
    
    # ═══════════════════════════════════════════════════════════
    # EXPORTACIÓN & REPORTES (13-16)
    # ═══════════════════════════════════════════════════════════
    "13": {
        "name": "Exportar a JSON",
        "emoji": "📄",
        "script": "analyze_kpis.py",
        "args": ["--output", "json"],
        "group": "export",
        "description": "Exportar resultados en formato JSON"
    },
    "14": {
        "name": "Exportar a CSV",
        "emoji": "📊",
        "script": "analyze_kpis.py",
        "args": ["--output", "csv"],
        "group": "export",
        "description": "Exportar resultados en formato CSV"
    },
    "15": {
        "name": "Exportar a HTML",
        "emoji": "🌐",
        "script": "analyze_kpis.py",
        "args": ["--output", "html"],
        "group": "export",
        "description": "Exportar reporte HTML con estilos profesionales"
    },
    "16": {
        "name": "Exportar a Excel Pro",
        "emoji": "📑",
        "script": "exporter.py",
        "args": ["--format", "excel"],
        "group": "export",
        "description": "Exportar a Excel con formatos, gráficos y tablas"
    },
    
    # ═══════════════════════════════════════════════════════════
    # OPCIONES DE SISTEMA
    # ═══════════════════════════════════════════════════════════
    "_system_options": {
        "Q": {
            "name": "Volver al Menú Principal",
            "emoji": "🔙",
            "description": "Regresar al launcher principal",
            "type": "exit"
        }
    }
}
```

#### 2.2 Integrar Consolidador
**Cambios en consolidator.py:**
```python
# Antes
from dashboard.dashboard_consolidator import DashboardConsolidator

# Después
class DataConsolidator:
    """Consolida datos de múltiples fuentes"""
    def __init__(self, org=None, project=None, pat=None):
        self.org = org
        self.project = project
        self.pat = pat
    
    def consolidate_azdo_data(self):
        """Consolida datos de AZDO"""
        pass
    
    def consolidate_kpi_data(self):
        """Consolida datos de KPIs"""
        pass
    
    def consolidate_all(self):
        """Consolida todos los datos"""
        pass
```

#### 2.3 Integrar Generador
**Cambios en generator.py:**
```python
class DashboardGeneratorPro:
    """Genera dashboards profesionales"""
    def __init__(self, data, output_dir=None):
        self.data = data
        self.output_dir = output_dir or "outcome/kpi_analyzer"
    
    def generate_html(self):
        """Genera HTML profesional"""
        pass
    
    def generate_with_charts(self):
        """Genera con Chart.js"""
        pass
    
    def generate_responsive(self):
        """Genera responsive design"""
        pass
```

#### 2.4 Integrar Scheduler
**Cambios en scheduler.py:**
```python
class AutoScheduler:
    """Planifica ejecución automática"""
    def __init__(self, config=None):
        self.config = config or {}
    
    def schedule_daily(self):
        """Planifica ejecución diaria"""
        pass
    
    def schedule_weekly(self):
        """Planifica ejecución semanal"""
        pass
    
    def schedule_on_demand(self):
        """Ejecución bajo demanda"""
        pass
```

---

### Fase 3: Mejoras (3 horas)

#### 3.1 Mejorar Dashboards
- Agregar temas personalizables
- Mejorar responsividad
- Agregar exportación de gráficos
- Mejorar rendimiento

#### 3.2 Agregar Exportación Excel
- Crear módulo exporter.py
- Implementar formatos profesionales
- Agregar gráficos embebidos
- Agregar tablas dinámicas

#### 3.3 Optimizar Rendimiento
- Cachear datos
- Paralelizar cálculos
- Optimizar consultas
- Mejorar tiempos de generación

---

### Fase 4: Testing (2 horas)

#### 4.1 Tests Unitarios
```python
# test_kpi_analyzer.py
class TestHealthScore(unittest.TestCase):
    def test_calculate_deployment_frequency(self):
        pass
    
    def test_calculate_lead_time(self):
        pass
    
    def test_overall_score(self):
        pass

class TestExporter(unittest.TestCase):
    def test_export_json(self):
        pass
    
    def test_export_excel(self):
        pass
    
    def test_export_html(self):
        pass
```

#### 4.2 Tests de Integración
- Validar consolidación de datos
- Validar generación de dashboards
- Validar exportación
- Validar planificación

#### 4.3 Validación de Salidas
- Verificar formato JSON
- Verificar formato Excel
- Verificar HTML responsivo
- Verificar gráficos

---

### Fase 5: Limpieza (1 hora)

#### 5.1 Remover Opción 6 de main.py
```python
# ANTES
PLATFORMS = {
    "1": { "name": "Google Cloud Platform", ... },
    "2": { "name": "Azure DevOps", ... },
    "3": { "name": "Amazon Web Services", ... },
    "4": { "name": "Terminal Scripts", ... },
    "5": { "name": "KPI Analyzer", ... },
    "6": { "name": "Dashboard Matutino", ... },  # ❌ REMOVER
    "Q": { "name": "Salir", ... },
}

# DESPUÉS
PLATFORMS = {
    "1": { "name": "Google Cloud Platform", ... },
    "2": { "name": "Azure DevOps", ... },
    "3": { "name": "Amazon Web Services", ... },
    "4": { "name": "Terminal Scripts", ... },
    "5": { "name": "KPI Analyzer Pro", ... },  # ✅ ACTUALIZAR
    "Q": { "name": "Salir", ... },
}
```

#### 5.2 Actualizar Documentación
- Actualizar README.md
- Crear guía de uso KPI Analyzer Pro
- Documentar nuevas herramientas
- Actualizar API docs

#### 5.3 Commit Final
```bash
git add -A
git commit -m "feat: Integrar Dashboard Matutino en KPI Analyzer Pro v1.9.6 - Opción 6 removida"
git push origin master
```

---

## 📊 Matriz de Cambios

| Archivo | Acción | Líneas | Descripción |
|---------|--------|--------|-------------|
| `kpi_analyzer/tools.py` | MODIFICAR | 200+ | Agregar 12 nuevas herramientas |
| `kpi_analyzer/consolidator.py` | CREAR | 150 | Refactorizar de dashboard |
| `kpi_analyzer/generator.py` | CREAR | 200 | Refactorizar de dashboard |
| `kpi_analyzer/scheduler.py` | CREAR | 100 | Refactorizar de dashboard |
| `kpi_analyzer/health_score.py` | CREAR | 150 | Nuevo módulo DORA |
| `kpi_analyzer/exporter.py` | CREAR | 200 | Nuevo módulo exportación |
| `scm/main.py` | MODIFICAR | 20 | Remover opción 6 |
| `README.md` | ACTUALIZAR | 50 | Documentar cambios |

---

## ✅ Checklist de Implementación

### Preparación
- [ ] Crear estructura de directorios
- [ ] Refactorizar módulos de dashboard
- [ ] Crear nuevos módulos
- [ ] Actualizar requirements.txt

### Integración
- [ ] Actualizar tools.py
- [ ] Integrar consolidador
- [ ] Integrar generador
- [ ] Integrar scheduler
- [ ] Integrar health score

### Mejoras
- [ ] Mejorar dashboards
- [ ] Agregar exportación Excel
- [ ] Optimizar rendimiento
- [ ] Agregar caché

### Testing
- [ ] Tests unitarios
- [ ] Tests de integración
- [ ] Validación de salidas
- [ ] Tests de rendimiento

### Limpieza
- [ ] Remover opción 6
- [ ] Actualizar documentación
- [ ] Commit final
- [ ] Push a GitHub

---

## 📈 Impacto Esperado

| Métrica | Antes | Después | Cambio |
|---------|-------|---------|--------|
| **Opciones en main.py** | 6 | 5 | -1 |
| **Herramientas KPI** | 10 | 16 | +6 |
| **Dashboards** | 2 | 3 | +1 |
| **Exportación** | 3 | 4 | +1 |
| **Health Score** | No | Sí | ✅ |
| **Consolidación** | Parcial | Completa | ✅ |

---

## 🎯 Conclusión

Este plan detallado proporciona una **hoja de ruta clara** para integrar Dashboard Matutino en KPI Analyzer Pro, creando una **plataforma unificada profesional nivel PRO** con:

- ✅ 16 herramientas integradas
- ✅ Health Score DORA
- ✅ Dashboards profesionales
- ✅ Consolidación automática
- ✅ Múltiples formatos de exportación

**Duración Total:** 12 horas  
**Complejidad:** Media  
**Riesgo:** Bajo (módulos independientes)

---

**Plan de Implementación KPI Analyzer Pro v1.9.6 - COMPLETADO** ✅
