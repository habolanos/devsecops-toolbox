# 📨 Pub/Sub Monitor - Sistema Profesional de Monitoreo

**Versión**: 1.0.0  
**Estado**: ✅ Implementación Completa  
**Fecha**: 16 de Julio de 2026

---

## 🎯 Descripción

Sistema profesional de monitoreo para **Google Cloud Pub/Sub** con capacidad de:

- ✅ **Multi-proyecto GCP**: Monitoreo simultáneo de 12 proyectos
- ✅ **Estado Actual**: Visualización en tiempo real de topics y subscriptions
- ✅ **Alertas Preventivas**: 5 categorías, 25+ reglas de alerta
- ✅ **Dashboards**: HTML interactivo, JSON, Excel
- ✅ **Menú Interactivo**: Interfaz profesional con Rich

---

## 📦 Instalación

### Requisitos

- Python 3.11+
- Acceso a Google Cloud Platform
- Credenciales GCP configuradas

### Dependencias

```bash
pip install -r requirements.txt
```

**Paquetes principales**:
- `google-cloud-pubsub` - API de Pub/Sub
- `google-cloud-monitoring` - Cloud Monitoring API
- `google-cloud-logging` - Cloud Logging API
- `rich` - Interfaz profesional
- `openpyxl` - Exportación Excel

---

## 🚀 Uso

### Desde el Launcher GCP

```bash
python scm/gcp/tools.py
# Seleccionar opción [41] - Pub/Sub Monitor
```

### Ejecución Directa

```bash
python scm/gcp/pubsub_monitor/pubsub_monitor.py
```

### Menú Interactivo

```
📊 Pub/Sub Monitor - Menú Principal

[1] Análisis Completo (todos los proyectos)
[2] Análisis de Proyecto Específico
[3] Evaluar Alertas Solamente
[4] Generar Reportes
[5] Ver Configuración
[Q] Salir
```

---

## 📊 Proyectos Soportados

El monitor soporta **12 proyectos GCP** de CPL:

### CPL-CMANAGER (Customer Manager)
- `cpl-cmanager-dev-13072023`
- `cpl-cmanager-qa-13072023`
- `cpl-cmanager-stag-01052025`

### CPL-CS-CSC (Customer Service Center)
- `cpl-cs-csc-dev-16112023`
- `cpl-cs-csc-qa-16112023`
- `cpl-cs-csc-stag-11042025`

### CPL-CS-WMS (Warehouse Management System)
- `cpl-cs-wms-dev-30112023`
- `cpl-cs-wms-qa-30112023`
- `cpl-cs-wms-stag-09042025`

### CPL-OMS (Order Management System)
- `cpl-oms-dev-08082024`
- `cpl-oms-qa-08062023`
- `cpl-oms-stag-09042025`

---

## 🚨 Alertas Preventivas

### 5 Categorías de Alertas

#### 1. **Capacidad** 🔴
- Backlog Crítico (> 100k mensajes)
- Backlog Elevado (> 50k mensajes)
- Retraso de Entrega (> 60 segundos)
- Tasa de Error Crítica (> 5%)

#### 2. **Rendimiento** 🟡
- Latencia P95 Elevada (> 5 segundos)
- Throughput Bajo (< 50% baseline)
- Tasa de Descarte Elevada (> 1%)

#### 3. **Configuración** 🟠
- Sin Dead-Letter Policy
- TTL de Mensajes Bajo (< 1 hora)
- Sin Retry Policy
- Encriptación No Habilitada

#### 4. **Seguridad** 🔐
- Acceso Público Detectado
- Cambios en IAM Sin Auditoría

#### 5. **Costo** 💰
- Incremento Significativo (> 20%)
- Subscription Inactiva (> 30 días)
- Topic Sin Consumidores

---

## 📈 Módulos Implementados

### 1. **PubSubCollector** (~400 líneas)
Recopilación de datos de Pub/Sub
- Multi-proyecto paralelo
- Caché de 1 hora
- Manejo de errores robusto

### 2. **MetricsAnalyzer** (~350 líneas)
Análisis de métricas y cálculo de KPIs
- Health scores (0-100)
- Detección de anomalías
- Análisis de tendencias

### 3. **AlertEngine** (~300 líneas)
Evaluación de alertas
- 5 categorías de alertas
- Deduplicación automática
- Escalado progresivo

### 4. **DashboardGenerator** (~400 líneas)
Generación de reportes
- Dashboard HTML interactivo
- Reportes JSON
- Exportación Excel

### 5. **PubSubMonitor** (~300 líneas)
Orquestador principal
- Menú interactivo
- Integración de módulos
- Gestión de flujo

---

## 📊 Salida Generada

### Dashboard HTML
```
outcome/pubsub_monitor/dashboard.html
```
- Interfaz profesional
- Gráficos interactivos
- Resumen ejecutivo

### Reporte JSON
```
outcome/pubsub_monitor/report.json
```
- Datos estructurados
- Completo y detallado
- Fácil de procesar

### Reporte Excel
```
outcome/pubsub_monitor/report.xlsx
```
- 3 hojas: Resumen, Proyectos, Alertas
- Formato profesional
- Listo para presentar

---

## ⚙️ Configuración

### config.json

```json
{
  "gcp": {
    "service_accounts_reporter": {
      "enabled": true,
      "projects": [
        "cpl-cmanager-dev-13072023",
        "cpl-cmanager-qa-13072023",
        ...
      ]
    }
  }
}
```

---

## 🔐 Permisos Requeridos

```yaml
Roles Necesarios:
  - roles/pubsub.viewer (Lectura de Pub/Sub)
  - roles/monitoring.metricReader (Lectura de métricas)
  - roles/logging.viewer (Lectura de logs)
  - roles/resourcemanager.organizationViewer (Multi-proyecto)
```

---

## 📚 Documentación Adicional

- `docs/features/feat_monitoreo_pubsub/README.md` - Visión general
- `docs/features/feat_monitoreo_pubsub/ESPECIFICACION.md` - Especificación técnica
- `docs/features/feat_monitoreo_pubsub/ALERTAS.md` - Sistema de alertas
- `docs/features/feat_monitoreo_pubsub/ARQUITECTURA.md` - Arquitectura
- `docs/features/feat_monitoreo_pubsub/EJEMPLOS.md` - Casos de uso
- `docs/features/feat_monitoreo_pubsub/INTEGRACION_PROYECTOS.md` - Integración

---

## 🐛 Troubleshooting

### Error: "No se pueden recopilar métricas"
**Causa**: Permisos insuficientes  
**Solución**: Verificar roles IAM en GCP

### Error: "Proyecto no encontrado"
**Causa**: Proyecto no existe o no está configurado  
**Solución**: Verificar `config.json`

### Error: "Módulo no encontrado"
**Causa**: Dependencias no instaladas  
**Solución**: `pip install -r requirements.txt`

---

## 📞 Soporte

Para reportar problemas o sugerencias:
1. Revisar documentación en `docs/features/feat_monitoreo_pubsub/`
2. Verificar logs en `outcome/pubsub_monitor/`
3. Contactar al equipo DevSecOps

---

**Versión**: 1.0.0  
**Última actualización**: 16 de Julio de 2026  
**Estado**: ✅ Implementación Completa

