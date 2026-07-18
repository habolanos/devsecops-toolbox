# 📊 GCP Infrastructure Dashboard - Guía Completa

**Versión**: 1.7.2  
**Fecha**: 18 de Julio de 2026  
**Status**: ✅ Implementado

---

## 📋 Resumen

Se ha implementado un **dashboard HTML interactivo y autocontenido** que se genera automáticamente junto con el JSON al ejecutar `gcp_monitor.py`.

### ✨ Características

- ✅ **Autocontenido**: No requiere servidor web ni conexión a Internet
- ✅ **Interactivo**: Filtros globales que actualizan todas las visualizaciones
- ✅ **Responsive**: Funciona en desktop y móvil
- ✅ **Seguro**: Redacta información sensible (IPs, certificados, claves)
- ✅ **Profesional**: Tema oscuro inspirado en consolas de observabilidad
- ✅ **Automático**: Se genera sin necesidad de parámetros adicionales

---

## 🚀 Uso

### **Opción 1: Generación Automática (Recomendado)**

```bash
python gcp_monitor.py --project=PROJECT_ID
```

**Resultado**: Se generan 3 archivos automáticamente:
```
✓ outcome/gcp_report_PROJECT_ID_20260718_153045.json
✓ outcome/gcp_infrastructure_dashboard_20260718_153045.html
✓ outcome/gcp_monitor_PROJECT_ID_20260718_150743.log
```

### **Opción 2: Generación Manual desde JSON**

```bash
python generate_gcp_dashboard.py \
  --input outcome/gcp_report_consolidated_20260718_131642.json \
  --output gcp_infrastructure_dashboard.html
```

### **Opción 3: Procesar Múltiples Snapshots**

```bash
python generate_gcp_dashboard.py \
  --input-dir ./snapshots \
  --output gcp_infrastructure_dashboard.html
```

---

## 📊 Secciones del Dashboard

### **1. Encabezado**
- Título: "GCP Infrastructure Overview"
- Fecha de generación
- Zona horaria
- Versión del reporte

### **2. Filtros Globales**
Filtros interactivos que se aplican a toda la página:
- **Proyecto**: Selecciona un proyecto específico
- **Ambiente**: dev, qa, stag, prod, desconocido
- **Tipo de Recurso**: Cloud SQL, GKE, Compute Engine, Cloud Run, Pub/Sub
- **Estado**: RUNNING, RUNNABLE, ACTIVE, STOPPED
- **Búsqueda**: Por nombre de recurso
- **Botón Restablecer**: Limpia todos los filtros

### **3. KPIs (Key Performance Indicators)**
Tarjetas con conteos filtrados:
- 📊 Proyectos
- 🔧 Recursos Totales
- ☸️ Clusters GKE
- 🗄️ Cloud SQL
- 💻 Compute Engine
- 🚀 Cloud Run
- 📨 Pub/Sub

**Interactividad**: Clic en una tarjeta aplica el filtro correspondiente

### **4. Tabla de Inventario**
Tabla interactiva y ordenable con:
- Tipo de recurso
- Nombre
- Proyecto
- Ambiente
- Región/Zona
- Estado (con badge de color)
- Postura (Conforme, Advertencia, Crítico)
- Número de hallazgos

---

## 🎨 Diseño Visual

### **Colores**
- **Fondo**: Oscuro (#0f1419)
- **Tarjetas**: Gris oscuro (#1a1f26)
- **Texto primario**: Blanco (#e2e8f0)
- **Texto secundario**: Gris (#a0aec0)
- **Verde**: Saludable/Conforme (#48bb78)
- **Amarillo/Naranja**: Advertencia (#ed8936)
- **Rojo**: Crítico (#f56565)
- **Azul**: Información (#4299e1)
- **Gris**: Desconocido/N/A (#718096)

### **Badges de Estado**
```
RUNNING/RUNNABLE/ACTIVE  → Verde (Saludable)
STOPPED/TERMINATED       → Rojo (Crítico)
Desconocido              → Gris (N/A)

Conforme                 → Verde
Advertencia              → Naranja
Crítico                  → Rojo
```

---

## 🔒 Seguridad y Sanitización

### **Información Redactada**
El dashboard **nunca muestra**:
- ❌ Certificados o claves criptográficas
- ❌ Direcciones IP (públicas o privadas)
- ❌ URLs internas completas
- ❌ Cuentas de servicio
- ❌ Tokens o credenciales
- ❌ Blobs codificados
- ❌ DNS internos

### **Valores Seguros Mostrados**
- ✅ "Configurado" / "No configurado"
- ✅ "Privado" / "Público detectado"
- ✅ "Disponible" / "No disponible"
- ✅ "***REDACTADO***" para campos sensibles

---

## 📈 Evaluación de Postura

### **Cloud SQL**
Marca como hallazgo si:
- Estado ≠ RUNNABLE
- Backups deshabilitados
- PITR deshabilitado
- Protección contra eliminación deshabilitada
- IPv4 habilitado
- SSL no exigido

### **GKE**
Marca como hallazgo si:
- Estado ≠ RUNNING
- Nodos privados deshabilitados
- Shielded Nodes deshabilitado
- Binary Authorization deshabilitado
- Cifrado de BD deshabilitado
- AutoRepair deshabilitado en algún pool
- AutoUpgrade deshabilitado en algún pool
- Telemetría no disponible (Info, no error)

### **Compute Engine**
Marca como hallazgo si:
- Estado ≠ RUNNING
- Protección contra eliminación deshabilitada

### **Cloud Run y Pub/Sub**
- Marcados como "Conforme" (sin reglas de evaluación)

---

## 🔍 Filtros Interactivos

### **Comportamiento**
- Los filtros se combinan con lógica AND
- Cada cambio actualiza la tabla en tiempo real
- Los KPIs se recalculan según los filtros aplicados
- Clic en KPI aplica el filtro correspondiente

### **Ejemplo de Flujo**
```
1. Usuario selecciona Ambiente = "prod"
   ↓
2. Tabla se actualiza mostrando solo recursos prod
   ↓
3. KPIs se recalculan para recursos prod
   ↓
4. Usuario selecciona Tipo = "GKE"
   ↓
5. Tabla muestra solo GKE en prod
   ↓
6. Usuario presiona "Restablecer"
   ↓
7. Todos los filtros se limpian
```

---

## 📊 Estructura del HTML

### **Componentes**
```html
<!DOCTYPE html>
├── <head>
│   ├── Meta tags (charset, viewport)
│   ├── Plotly.js (para gráficos)
│   └── Estilos CSS embebidos
├── <body>
│   ├── Header (título, metadata)
│   ├── Filtros globales
│   ├── KPIs
│   ├── Tabla de inventario
│   └── Footer
│   └── <script> (lógica JavaScript)
```

### **Tamaño**
- Típicamente 500KB - 2MB (según cantidad de recursos)
- Completamente autocontenido (sin CDN externo)
- Compatible con navegadores modernos

---

## 🛠️ Instalación de Dependencias

### **Para Generación Automática**
```bash
pip install -r requirements_dashboard.txt
```

### **Contenido de requirements_dashboard.txt**
```
pandas>=1.5.0
plotly>=5.0.0
```

### **Nota**
- Si `pandas` o `plotly` no están disponibles, el dashboard se genera con funcionalidad limitada
- El HTML sigue siendo funcional sin estas librerías

---

## 📝 Ejemplos de Uso

### **Ejemplo 1: Monitoreo Básico**
```bash
python gcp_monitor.py --project=cpl-cs-wms-dev-30112023
```

Genera:
- JSON con métricas
- Dashboard HTML interactivo
- Log de ejecución

### **Ejemplo 2: Múltiples Proyectos**
```bash
python gcp_monitor.py --project=proj1,proj2,proj3
```

Genera dashboard consolidado con todos los proyectos

### **Ejemplo 3: Formato Específico + HTML**
```bash
python gcp_monitor.py --project=PROJECT_ID --output=csv
```

Genera:
- CSV (formato solicitado)
- JSON (automático)
- HTML (automático)

### **Ejemplo 4: Generación Manual**
```bash
python generate_gcp_dashboard.py \
  --input outcome/gcp_report_consolidated_20260718_131642.json \
  --output mi_dashboard.html
```

---

## 🔧 Personalización

### **Cambiar Nombre del HTML**
```bash
python generate_gcp_dashboard.py \
  --input report.json \
  --output mi_dashboard_personalizado.html
```

### **Procesar Directorio Completo**
```bash
python generate_gcp_dashboard.py \
  --input-dir ./snapshots \
  --output dashboard_consolidado.html
```

---

## 📋 Archivos Generados

| Archivo | Descripción | Automático |
|---------|-------------|-----------|
| `gcp_report_*.json` | Datos consolidados con métricas | ✅ Sí |
| `gcp_infrastructure_dashboard_*.html` | Dashboard interactivo | ✅ Sí |
| `gcp_report_*.txt` | Reporte en texto | Si `--output=txt` |
| `gcp_report_*.csv` | Reporte en CSV | Si `--output=csv` |
| `gcp_monitor_*.log` | Log de ejecución | ✅ Sí |

---

## 🚀 Ventajas

### **Para DevOps/SRE**
- ✅ Visión consolidada de infraestructura
- ✅ Identificación rápida de problemas
- ✅ Evaluación de postura de seguridad
- ✅ Análisis de conformidad

### **Para Seguridad**
- ✅ Información sensible redactada
- ✅ Evaluación de hallazgos
- ✅ Severidad de problemas
- ✅ Recomendaciones de mejora

### **Para Gestión**
- ✅ Inventario completo de recursos
- ✅ Distribución por ambiente
- ✅ Conteos por tipo de recurso
- ✅ Estado de salud general

---

## 📞 Soporte

### **Si el HTML no se genera**
1. Verificar que `generate_gcp_dashboard.py` está en el mismo directorio
2. Instalar dependencias: `pip install -r requirements_dashboard.txt`
3. Revisar el log: `gcp_monitor_*.log`

### **Si el HTML no abre**
1. Usar navegador moderno (Chrome, Firefox, Safari, Edge)
2. Abrir desde disco local (no requiere servidor)
3. Verificar que el archivo no está corrupto

### **Si los filtros no funcionan**
1. Abrir consola del navegador (F12)
2. Verificar que no hay errores JavaScript
3. Recargar la página (Ctrl+R)

---

## 📚 Documentación Relacionada

- `PHASE2_IMPLEMENTATION.md` - Implementación de métricas
- `JSON_EXPORT_STRUCTURE.md` - Estructura del JSON
- `PHASE2_VALIDATION.md` - Validación de cálculos
- `README.md` - Documentación general

---

## ✅ Checklist de Funcionalidad

- ✅ Dashboard se genera automáticamente
- ✅ HTML es autocontenido y portable
- ✅ Funciona sin servidor web
- ✅ Funciona sin conexión a Internet
- ✅ Filtros globales interactivos
- ✅ KPIs con clics funcionales
- ✅ Tabla ordenable y filtrable
- ✅ Información sensible redactada
- ✅ Diseño responsive
- ✅ Tema oscuro profesional
- ✅ Compatible con navegadores modernos

---

**Status**: ✅ Completado  
**Versión**: 1.7.2  
**Listo para producción**
