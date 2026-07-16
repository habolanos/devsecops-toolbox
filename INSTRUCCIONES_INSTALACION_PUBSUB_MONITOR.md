# 📦 Instrucciones de Instalación - Pub/Sub Monitor v1.0.0

**Fecha**: 16 de Julio de 2026  
**Versión**: 1.0.0  
**Estado**: ✅ LISTO PARA INSTALAR

---

## 🚀 Instalación Rápida

### Paso 1: Verificar Python
```bash
python --version
# Debe ser Python 3.11 o superior
```

### Paso 2: Instalar Dependencias
```bash
# Desde el directorio raíz del proyecto
pip install -r scm/gcp/pubsub_monitor/requirements.txt
```

### Paso 3: Ejecutar el Monitor
```bash
# Opción 1: Desde el launcher GCP
python scm/gcp/tools.py
# Seleccionar opción [41]

# Opción 2: Ejecución directa
python scm/gcp/pubsub_monitor/pubsub_monitor.py
```

---

## 📋 Dependencias Requeridas

```
google-cloud-pubsub>=2.18.0
google-cloud-monitoring>=2.15.0
google-cloud-logging>=3.5.0
rich>=13.0.0
numpy>=1.24.0
openpyxl>=3.0.0
```

### Notas Importantes

- **openpyxl**: Versión máxima disponible es 3.1.5 (no 3.10.0)
- **google-cloud-pubsub**: Versión 2.39.0 es la más reciente
- **rich**: Versión 15.0.0 es la más reciente
- Todas las dependencias son compatibles con Python 3.11+

---

## 🔐 Requisitos de Autenticación GCP

### Configurar Credenciales
```bash
# Opción 1: Usar gcloud CLI
gcloud auth application-default login

# Opción 2: Usar archivo de credenciales
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Permisos Requeridos
```yaml
Roles Necesarios:
  - roles/pubsub.viewer (Lectura de Pub/Sub)
  - roles/monitoring.metricReader (Lectura de métricas)
  - roles/logging.viewer (Lectura de logs)
  - roles/resourcemanager.organizationViewer (Multi-proyecto)
```

---

## ⚙️ Configuración

### Archivo: `scm/config.json`

```json
{
  "gcp": {
    "service_accounts_reporter": {
      "enabled": true,
      "projects": [
        "cpl-cmanager-dev-13072023",
        "cpl-cmanager-qa-13072023",
        "cpl-cmanager-stag-01052025",
        "cpl-cs-csc-dev-16112023",
        "cpl-cs-csc-qa-16112023",
        "cpl-cs-csc-stag-11042025",
        "cpl-cs-wms-dev-30112023",
        "cpl-cs-wms-qa-30112023",
        "cpl-cs-wms-stag-09042025",
        "cpl-oms-dev-08082024",
        "cpl-oms-qa-08062023",
        "cpl-oms-stag-09042025"
      ]
    }
  }
}
```

---

## 🎯 Uso del Monitor

### Menú Principal
```
[1] Análisis Completo (todos los proyectos)
[2] Análisis de Proyecto Específico
[3] Evaluar Alertas Solamente
[4] Generar Reportes
[5] Ver Configuración
[Q] Salir
```

### Opción 1: Análisis Completo
- Recopila datos de todos los 12 proyectos
- Analiza métricas
- Evalúa alertas
- Genera reportes (HTML, JSON, Excel)

### Opción 2: Análisis de Proyecto
- Selecciona un proyecto específico
- Realiza análisis detallado
- Muestra health score

### Opción 3: Evaluar Alertas
- Recopila datos
- Evalúa todas las alertas
- Muestra resumen de alertas activas

### Opción 4: Generar Reportes
- Genera dashboard HTML interactivo
- Genera reporte JSON estructurado
- Genera reporte Excel (3 hojas)

### Opción 5: Ver Configuración
- Muestra proyectos configurados
- Verifica estado de conexión

---

## 📊 Reportes Generados

### Ubicación
```
outcome/pubsub_monitor/
├── dashboard.html (Dashboard interactivo)
├── report.json (Datos estructurados)
└── report.xlsx (3 hojas: Resumen, Proyectos, Alertas)
```

### Contenido

**dashboard.html**:
- Interfaz profesional con CSS
- Resumen ejecutivo
- Métricas por proyecto
- Alertas activas

**report.json**:
- Estructura completa
- Todos los datos recopilados
- Análisis y alertas

**report.xlsx**:
- Hoja 1: Resumen (proyectos, topics, subscriptions, alertas)
- Hoja 2: Proyectos (detalle por proyecto)
- Hoja 3: Alertas (lista completa)

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'google.cloud'"
**Solución**: Instalar dependencias
```bash
pip install -r scm/gcp/pubsub_monitor/requirements.txt
```

### Error: "No se pueden recopilar métricas"
**Causa**: Permisos insuficientes  
**Solución**: Verificar roles IAM en GCP

### Error: "Proyecto no encontrado"
**Causa**: Proyecto no existe o no está configurado  
**Solución**: Verificar `scm/config.json`

### Error: "openpyxl no instalado"
**Solución**: Instalar openpyxl
```bash
pip install openpyxl>=3.0.0
```

---

## 📚 Documentación Adicional

- `scm/gcp/pubsub_monitor/README.md` - Documentación del módulo
- `docs/features/feat_monitoreo_pubsub/README.md` - Visión general
- `docs/features/feat_monitoreo_pubsub/ESPECIFICACION.md` - Especificación técnica
- `docs/features/feat_monitoreo_pubsub/ALERTAS.md` - Sistema de alertas
- `docs/features/feat_monitoreo_pubsub/ARQUITECTURA.md` - Diseño de arquitectura
- `docs/features/feat_monitoreo_pubsub/EJEMPLOS.md` - Casos de uso
- `docs/features/feat_monitoreo_pubsub/INTEGRACION_PROYECTOS.md` - Integración con proyectos

---

## ✅ Verificación de Instalación

### Paso 1: Verificar archivos
```bash
ls -la scm/gcp/pubsub_monitor/
# Debe mostrar:
# - __init__.py
# - pubsub_collector.py
# - metrics_analyzer.py
# - alert_engine.py
# - dashboard_generator.py
# - pubsub_monitor.py
# - tools.py
# - requirements.txt
# - README.md
```

### Paso 2: Verificar dependencias
```bash
pip list | grep -E "google-cloud|rich|numpy|openpyxl"
# Debe mostrar todas las dependencias instaladas
```

### Paso 3: Verificar integración en GCP Tools
```bash
grep -n "Pub/Sub Monitor" scm/gcp/tools.py
# Debe mostrar la herramienta registrada como Tool 41
```

### Paso 4: Verificar configuración
```bash
python -c "import json; print(json.load(open('scm/config.json'))['gcp']['service_accounts_reporter']['projects'])"
# Debe mostrar los 12 proyectos
```

---

## 🚀 Próximos Pasos

1. ✅ Instalar dependencias
2. ✅ Configurar credenciales GCP
3. ✅ Ejecutar el monitor
4. ✅ Generar reportes
5. ✅ Revisar alertas

---

## 📞 Soporte

Para reportar problemas o sugerencias:
1. Revisar documentación en `docs/features/feat_monitoreo_pubsub/`
2. Verificar logs en `outcome/pubsub_monitor/`
3. Contactar al equipo DevSecOps

---

**Versión**: 1.0.0  
**Última actualización**: 16 de Julio de 2026  
**Estado**: ✅ LISTO PARA INSTALAR

