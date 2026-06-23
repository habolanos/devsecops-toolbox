# PLAN DE ACCIÓN - Dashboard Matutino

## 🎯 Objetivo General

Implementar un dashboard matutino automatizado que consolide el estado de:
- Repositorios y cumplimiento de branching
- Pipelines CI/CD y health scores
- Pull requests y tiempo de atención
- Servicios e infraestructura (GCP/AWS)
- Bases de datos y alertas

**Timeline:** 3-4 semanas
**Esfuerzo:** 36-45 horas
**Equipo:** 1 developer

---

## 📋 FASE 1: Orquestador + PR Metrics (Semana 1)

### Objetivo
Crear la base para consolidar datos de todas las herramientas existentes.

### Tareas

#### 1.1 Crear Tool 26: Dashboard Consolidator
**Archivo:** `scm/azdo/dashboard_consolidator.py`
**Responsabilidades:**
- Ejecutar herramientas en paralelo (ThreadPoolExecutor)
- Consolidar outputs en JSON único
- Manejo de errores y timeouts
- Generar resumen ejecutivo

**Checklist:**
- [ ] Crear estructura base de clase `DashboardConsolidator`
- [ ] Implementar métodos para ejecutar cada herramienta
- [ ] Consolidar outputs en `dashboard_data.json`
- [ ] Generar resumen ejecutivo
- [ ] Manejo de errores y logging
- [ ] Tests unitarios básicos
- [ ] Documentación en docstrings

**Tiempo estimado:** 8-10 horas

---

#### 1.2 Crear Tool 28: PR Metrics Analyzer
**Archivo:** `scm/azdo/pr_metrics_analyzer.py`
**Responsabilidades:**
- Consultar API AZDO para PRs
- Calcular métricas de tiempo (avg, median, p95)
- Identificar PRs bloqueadas
- Calcular SLA compliance
- Identificar reviewers/autores lentos

**Checklist:**
- [ ] Crear estructura base de clase `PRMetricsAnalyzer`
- [ ] Implementar consulta de PRs por rama
- [ ] Calcular métricas de tiempo
- [ ] Generar alertas de SLA
- [ ] Exportar JSON con resultados
- [ ] Tests unitarios
- [ ] Documentación

**Tiempo estimado:** 10-12 horas

---

#### 1.3 Integrar Tool 26 en tools.py
**Archivo:** `scm/azdo/tools.py`
**Cambios:**
- Agregar entrada en TOOLS dict para Tool 26
- Agregar en GROUP_ORDER
- Crear menú interactivo para parámetros

**Checklist:**
- [ ] Agregar Tool 26 en TOOLS dict
- [ ] Agregar en TOOL_GROUPS si es necesario
- [ ] Implementar run_tool_26() en run_tool()
- [ ] Probar ejecución desde menú

**Tiempo estimado:** 2-3 horas

---

#### 1.4 Integrar Tool 28 en tools.py
**Archivo:** `scm/azdo/tools.py`
**Cambios:**
- Agregar entrada en TOOLS dict para Tool 28
- Crear menú interactivo

**Checklist:**
- [ ] Agregar Tool 28 en TOOLS dict
- [ ] Implementar run_tool_28() en run_tool()
- [ ] Probar ejecución desde menú

**Tiempo estimado:** 1-2 horas

---

#### 1.5 Crear outcome/dashboard/ directory
**Estructura:**
```
outcome/
└── dashboard/
    ├── dashboard_data_20260622_070000.json
    ├── pr_metrics_20260622_070000.json
    └── history/
        ├── 2026-06-22.json
        └── ...
```

**Checklist:**
- [ ] Crear directorio
- [ ] Crear .gitignore para archivos generados
- [ ] Documentar estructura

**Tiempo estimado:** 0.5 horas

---

#### 1.6 Pruebas de Fase 1
**Checklist:**
- [ ] Ejecutar Tool 26 manualmente
- [ ] Verificar dashboard_data.json
- [ ] Ejecutar Tool 28 manualmente
- [ ] Verificar pr_metrics.json
- [ ] Validar consolidación correcta
- [ ] Pruebas de error handling

**Tiempo estimado:** 3-4 horas

---

### Entregables Fase 1
- ✅ `dashboard_consolidator.py` (Tool 26)
- ✅ `pr_metrics_analyzer.py` (Tool 28)
- ✅ `dashboard_data.json` (ejemplo)
- ✅ `pr_metrics.json` (ejemplo)
- ✅ Actualización de `tools.py`
- ✅ README con instrucciones

---

## 📊 FASE 2: Dashboard Web (Semana 2)

### Objetivo
Crear visualización web interactiva del dashboard_data.json.

### Tareas

#### 2.1 Crear Tool 27: Dashboard Generator
**Archivo:** `scm/dashboard/dashboard_generator.py`
**Responsabilidades:**
- Leer dashboard_data.json
- Generar HTML con gráficos
- Crear alertas visuales
- Permitir drill-down interactivo

**Checklist:**
- [ ] Crear estructura base de clase `DashboardGenerator`
- [ ] Implementar lectura de dashboard_data.json
- [ ] Crear template HTML base
- [ ] Implementar secciones:
  - [ ] Resumen ejecutivo (KPIs)
  - [ ] Repositorios (tabla)
  - [ ] Pipelines (gráficos + tabla)
  - [ ] Pull requests (métricas + tabla)
  - [ ] Servicios (alertas)
  - [ ] Bases de datos (alertas)
- [ ] Agregar gráficos con Chart.js
- [ ] Estilos CSS (Tailwind/Bootstrap)
- [ ] Responsivo para mobile
- [ ] Tests

**Tiempo estimado:** 12-15 horas

---

#### 2.2 Crear estructura de templates
**Archivos:**
- `scm/dashboard/templates/dashboard.html.jinja2`
- `scm/dashboard/static/css/dashboard.css`
- `scm/dashboard/static/js/dashboard.js`

**Checklist:**
- [ ] Crear template base con Jinja2
- [ ] Crear estilos CSS
- [ ] Crear scripts JavaScript para interactividad
- [ ] Agregar Chart.js para gráficos

**Tiempo estimado:** 4-5 horas

---

#### 2.3 Integrar Tool 27 en tools.py
**Archivo:** `scm/azdo/tools.py` o `scm/dashboard/tools.py`
**Cambios:**
- Agregar entrada en TOOLS dict para Tool 27
- Crear menú interactivo

**Checklist:**
- [ ] Agregar Tool 27 en TOOLS dict
- [ ] Implementar run_tool_27() en run_tool()
- [ ] Probar ejecución desde menú

**Tiempo estimado:** 1-2 horas

---

#### 2.4 Pruebas de Fase 2
**Checklist:**
- [ ] Ejecutar Tool 27 con dashboard_data.json de Fase 1
- [ ] Verificar dashboard.html generado
- [ ] Validar gráficos se renderizan correctamente
- [ ] Probar responsividad en mobile
- [ ] Validar alertas se muestran correctamente
- [ ] Pruebas de drill-down

**Tiempo estimado:** 2-3 horas

---

### Entregables Fase 2
- ✅ `dashboard_generator.py` (Tool 27)
- ✅ `templates/dashboard.html.jinja2`
- ✅ `static/css/dashboard.css`
- ✅ `static/js/dashboard.js`
- ✅ `dashboard.html` (ejemplo)
- ✅ Actualización de `tools.py`
- ✅ README con instrucciones

---

## ⏰ FASE 3: Scheduler + Notificaciones (Semana 3)

### Objetivo
Automatizar ejecución diaria y enviar notificaciones.

### Tareas

#### 3.1 Crear Tool 29: Dashboard Scheduler
**Archivo:** `scm/dashboard/dashboard_scheduler.py`
**Responsabilidades:**
- Ejecutar Tool 26 diariamente a las 7:00 AM
- Generar Tool 27 (HTML)
- Enviar notificaciones
- Almacenar histórico

**Checklist:**
- [ ] Crear estructura base de clase `DashboardScheduler`
- [ ] Implementar scheduler con APScheduler
- [ ] Implementar notificaciones por email
- [ ] Implementar notificaciones por Slack
- [ ] Implementar notificaciones por Teams
- [ ] Almacenar histórico en outcome/dashboard/history/
- [ ] Logging de ejecuciones
- [ ] Tests

**Tiempo estimado:** 6-8 horas

---

#### 3.2 Configurar notificaciones en config.json
**Cambios en config.json:**
```json
{
  "dashboard": {
    "enabled": true,
    "schedule": "0 7 * * *",
    "timezone": "America/Mexico_City",
    "notifications": {
      "email": {
        "enabled": true,
        "recipients": ["team@example.com"],
        "send_on": ["critical", "warning"]
      },
      "slack": {
        "enabled": true,
        "webhook_url": "${SLACK_WEBHOOK_URL}",
        "send_on": ["critical"]
      },
      "teams": {
        "enabled": true,
        "webhook_url": "${TEAMS_WEBHOOK_URL}",
        "send_on": ["critical"]
      }
    },
    "alerts": {
      "repos_without_pipeline": {
        "enabled": true,
        "threshold": 0,
        "severity": "critical"
      }
    }
  }
}
```

**Checklist:**
- [ ] Actualizar config.json.template
- [ ] Documentar variables de entorno necesarias
- [ ] Crear ejemplo de configuración

**Tiempo estimado:** 1-2 horas

---

#### 3.3 Implementar almacenamiento de histórico
**Estructura:**
```
outcome/dashboard/history/
├── 2026-06-22.json
├── 2026-06-21.json
└── ...
```

**Checklist:**
- [ ] Crear directorio history/
- [ ] Implementar guardado diario
- [ ] Implementar rotación (retener 90 días)
- [ ] Documentar formato

**Tiempo estimado:** 1-2 horas

---

#### 3.4 Integrar Tool 29 en tools.py
**Archivo:** `scm/azdo/tools.py` o `scm/dashboard/tools.py`
**Cambios:**
- Agregar entrada en TOOLS dict para Tool 29
- Crear menú interactivo

**Checklist:**
- [ ] Agregar Tool 29 en TOOLS dict
- [ ] Implementar run_tool_29() en run_tool()
- [ ] Probar ejecución desde menú
- [ ] Probar modo daemon

**Tiempo estimado:** 1-2 horas

---

#### 3.5 Pruebas de Fase 3
**Checklist:**
- [ ] Ejecutar Tool 29 en modo --run-once
- [ ] Verificar ejecución de Tool 26
- [ ] Verificar generación de Tool 27
- [ ] Verificar notificaciones email
- [ ] Verificar notificaciones Slack
- [ ] Verificar notificaciones Teams
- [ ] Verificar almacenamiento de histórico
- [ ] Probar modo daemon

**Tiempo estimado:** 3-4 horas

---

### Entregables Fase 3
- ✅ `dashboard_scheduler.py` (Tool 29)
- ✅ Actualización de `config.json.template`
- ✅ Actualización de `tools.py`
- ✅ Documentación de configuración
- ✅ README con instrucciones

---

## 🎨 FASE 4: Refinamiento (Semana 4)

### Objetivo
Optimizar, mejorar UX y agregar funcionalidades avanzadas.

### Tareas

#### 4.1 Optimización de Performance
**Checklist:**
- [ ] Perfilar Tool 26 (tiempo de ejecución)
- [ ] Optimizar consultas a APIs
- [ ] Implementar caché adicional si es necesario
- [ ] Reducir tamaño de dashboard_data.json
- [ ] Minificar CSS/JS

**Tiempo estimado:** 2-3 horas

---

#### 4.2 Mejoras de UX
**Checklist:**
- [ ] Agregar drill-down interactivo
- [ ] Agregar filtros en tablas
- [ ] Agregar búsqueda de repositorios
- [ ] Agregar exportación a Excel
- [ ] Agregar modo oscuro (opcional)
- [ ] Mejorar accesibilidad (WCAG)

**Tiempo estimado:** 3-4 horas

---

#### 4.3 Análisis de Tendencias
**Checklist:**
- [ ] Implementar gráficos de tendencias (últimos 30 días)
- [ ] Comparar con semana anterior
- [ ] Mostrar deltas (mejora/empeoramiento)
- [ ] Agregar predicciones (opcional)

**Tiempo estimado:** 2-3 horas

---

#### 4.4 Documentación Completa
**Checklist:**
- [ ] Documentar arquitectura
- [ ] Documentar APIs
- [ ] Documentar configuración
- [ ] Crear guía de troubleshooting
- [ ] Crear guía de extensión

**Tiempo estimado:** 2-3 horas

---

#### 4.5 Tests Completos
**Checklist:**
- [ ] Unit tests para Tool 26
- [ ] Unit tests para Tool 27
- [ ] Unit tests para Tool 28
- [ ] Unit tests para Tool 29
- [ ] Integration tests
- [ ] Tests de carga

**Tiempo estimado:** 3-4 horas

---

### Entregables Fase 4
- ✅ Código optimizado
- ✅ UX mejorada
- ✅ Análisis de tendencias
- ✅ Documentación completa
- ✅ Tests completos

---

## 📅 CRONOGRAMA DETALLADO

### Semana 1: Orquestador + PR Metrics
| Día | Tarea | Horas | Status |
|---|---|---|---|
| Lunes | 1.1 Tool 26 base | 4 | ⏳ |
| Martes | 1.1 Tool 26 consolidación | 4 | ⏳ |
| Miércoles | 1.2 Tool 28 base | 4 | ⏳ |
| Jueves | 1.2 Tool 28 métricas | 4 | ⏳ |
| Viernes | 1.3-1.6 Integración + Pruebas | 6 | ⏳ |
| **Total** | | **22 horas** | |

### Semana 2: Dashboard Web
| Día | Tarea | Horas | Status |
|---|---|---|---|
| Lunes | 2.1 Tool 27 base | 4 | ⏳ |
| Martes | 2.1 Tool 27 secciones | 4 | ⏳ |
| Miércoles | 2.2 Templates + CSS | 4 | ⏳ |
| Jueves | 2.2 JavaScript + Gráficos | 4 | ⏳ |
| Viernes | 2.3-2.4 Integración + Pruebas | 5 | ⏳ |
| **Total** | | **21 horas** | |

### Semana 3: Scheduler + Notificaciones
| Día | Tarea | Horas | Status |
|---|---|---|---|
| Lunes | 3.1 Tool 29 base | 3 | ⏳ |
| Martes | 3.1 Notificaciones | 3 | ⏳ |
| Miércoles | 3.2-3.3 Configuración | 3 | ⏳ |
| Jueves | 3.4 Integración | 2 | ⏳ |
| Viernes | 3.5 Pruebas | 4 | ⏳ |
| **Total** | | **15 horas** | |

### Semana 4: Refinamiento
| Día | Tarea | Horas | Status |
|---|---|---|---|
| Lunes | 4.1 Performance | 3 | ⏳ |
| Martes | 4.2 UX | 4 | ⏳ |
| Miércoles | 4.3 Tendencias | 3 | ⏳ |
| Jueves | 4.4 Documentación | 3 | ⏳ |
| Viernes | 4.5 Tests | 4 | ⏳ |
| **Total** | | **17 horas** | |

---

## 🎯 CRITERIOS DE ACEPTACIÓN

### Por Fase

#### Fase 1: Orquestador + PR Metrics
- ✅ Tool 26 ejecuta todas las herramientas en paralelo
- ✅ dashboard_data.json se genera correctamente
- ✅ Tool 28 calcula métricas de PR correctamente
- ✅ Manejo de errores funciona
- ✅ Logging es informativo

#### Fase 2: Dashboard Web
- ✅ dashboard.html se genera desde dashboard_data.json
- ✅ Todos los gráficos se renderizan correctamente
- ✅ Tablas son interactivas y responsivas
- ✅ Alertas se muestran correctamente
- ✅ Funciona en desktop y mobile

#### Fase 3: Scheduler + Notificaciones
- ✅ Tool 29 ejecuta Tool 26 diariamente
- ✅ Notificaciones email se envían correctamente
- ✅ Notificaciones Slack se envían correctamente
- ✅ Notificaciones Teams se envían correctamente
- ✅ Histórico se almacena correctamente

#### Fase 4: Refinamiento
- ✅ Performance < 5 minutos para ejecución completa
- ✅ UX mejorada con drill-down y filtros
- ✅ Tendencias visibles en gráficos
- ✅ Documentación completa
- ✅ Tests con cobertura > 80%

---

## 🚀 CÓMO EMPEZAR

### Paso 1: Preparar Entorno
```bash
cd c:\Users\harold.bolanos\repos-publics\devsecops-toolbox
git checkout -b feature/dashboard-matutino
mkdir -p scm/dashboard/templates scm/dashboard/static/{css,js}
mkdir -p outcome/dashboard/history
```

### Paso 2: Crear Tool 26
```bash
# Crear archivo base
touch scm/azdo/dashboard_consolidator.py

# Copiar estructura de otra herramienta como referencia
# Implementar clase DashboardConsolidator
```

### Paso 3: Crear Tool 28
```bash
# Crear archivo base
touch scm/azdo/pr_metrics_analyzer.py

# Implementar clase PRMetricsAnalyzer
```

### Paso 4: Actualizar tools.py
```bash
# Agregar Tools 26 y 28 en TOOLS dict
# Agregar en GROUP_ORDER
# Implementar run_tool_26() y run_tool_28()
```

### Paso 5: Pruebas Iniciales
```bash
# Ejecutar Tool 26
python scm/azdo/tools.py

# Seleccionar opción 26
# Verificar dashboard_data.json
```

---

## 📞 CONTACTOS Y ESCALACIÓN

### Preguntas sobre Requerimientos
- **Equipo Comercial/CDS:** ¿Qué métricas exactas necesitan?
- **Operaciones:** ¿Qué alertas son críticas?
- **Arquitectura:** ¿Qué servicios deben monitorearse?

### Escalación
- **Bloqueador de API:** Contactar a Azure DevOps team
- **Bloqueador de Infraestructura:** Contactar a DevOps team
- **Bloqueador de Notificaciones:** Contactar a IT team

---

## 📝 NOTAS IMPORTANTES

1. **Cache 24h:** Reutilizar cache existente de Tools 14, 15, 16
2. **Parallelización:** Usar ThreadPoolExecutor para ejecutar herramientas en paralelo
3. **Error Handling:** Continuar con otras herramientas si una falla
4. **Logging:** Registrar todas las ejecuciones para debugging
5. **Histórico:** Guardar un JSON por día para análisis de tendencias
6. **Notificaciones:** Configurables por severidad (critical, warning, info)
7. **Seguridad:** No guardar PATs en código, usar config.json
8. **Documentación:** Actualizar README.md después de cada fase

---

## ✅ CHECKLIST FINAL

- [ ] Fase 1 completada y testeada
- [ ] Fase 2 completada y testeada
- [ ] Fase 3 completada y testeada
- [ ] Fase 4 completada y testeada
- [ ] Documentación actualizada
- [ ] README.md actualizado con v1.7.0
- [ ] Commits realizados (sin push)
- [ ] Code review completado
- [ ] Demostración a equipo Comercial/CDS
- [ ] Feedback incorporado
- [ ] Listo para producción

---

## 📊 MÉTRICAS DE ÉXITO

- ✅ Dashboard disponible todos los días a las 7:00 AM
- ✅ Tiempo de ejecución < 5 minutos
- ✅ Cobertura de tests > 80%
- ✅ Cero errores en notificaciones
- ✅ Equipo Comercial/CDS satisfecho con visualización
- ✅ Reducción de tiempo de respuesta operacional
