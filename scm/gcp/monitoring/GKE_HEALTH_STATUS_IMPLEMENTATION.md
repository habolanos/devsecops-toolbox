# 🏥 Implementación de Estado de Salud para Clusters GKE

**Versión**: 1.7.2  
**Fecha**: 18 de Julio de 2026  
**Status**: ✅ Completado

---

## 📋 Resumen

Se ha implementado un sistema de evaluación de **estado de salud** para clusters GKE basado en la lógica del script `gcp-project-cluster-health.sh`. La tabla de GKE ahora incluye una columna "Salud" que muestra el estado del cluster basado en umbrales de CPU y memoria.

---

## 🎯 Lógica Implementada

### Función: `get_health_status()`

```python
def get_health_status(cpu_percent: Optional[float], memory_percent: Optional[float], 
                     warning_threshold: float = 75.0, critical_threshold: float = 90.0) -> str:
    """Calcula el estado de salud basado en CPU y memoria."""
```

### Umbrales Definidos

| Métrica | Umbral | Estado |
|---------|--------|--------|
| **< 75%** | OK | 🟢 OK |
| **75% - 89%** | Advertencia | 🟡 ADVERTENCIA |
| **≥ 90%** | Crítico | 🔴 CRÍTICO |
| **Sin datos** | N/A | ⚪ SIN DATOS |

### Lógica de Evaluación

```
1. Si CPU% o Memoria% = NULL
   → Retorna: ⚪ SIN DATOS

2. Convertir a porcentaje (si está en rango 0-1)
   cpu_pct = cpu_percent * 100

3. Obtener máximo de ambas métricas
   max_util = max(cpu_pct, memory_pct)

4. Evaluar estado:
   - Si max_util >= 90% → 🔴 CRÍTICO
   - Si max_util >= 75% → 🟡 ADVERTENCIA
   - Si max_util < 75%  → 🟢 OK
```

---

## 📊 Tabla GKE Actualizada

### Columnas Anteriores
```
Proyecto | Nombre | Ubicación | Estado | Versión | Nodos | CPU Total | Memoria Total | CPU Usado (%) | Memoria Usada (%)
```

### Columnas Nuevas (con Salud)
```
Proyecto | Nombre | Ubicación | Estado | Versión | Nodos | CPU Total | Memoria Total | CPU Usado (%) | Memoria Usada (%) | Salud
```

### Ejemplo de Salida

```
☸️  Clusters GKE
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Proyecto                     ┃ Nombre                       ┃ Ubicación        ┃ Estado    ┃ Versión    ┃ Nodos ┃ CPU Total┃ Memoria Total┃ CPU Usado (%)┃ Memoria Usada(%)┃ Salud        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ cpl-cs-wms-dev-30112023      │ gke-dev-01                   │ us-central1-a    │ RUNNING   │ 1.27.2     │ 3     │ 12 vCPU │ 48 GB        │ 45.32%       │ 62.18%           │ 🟢 OK        │
│ cpl-cs-wms-dev-30112023      │ gke-prod-01                  │ us-central1-a    │ RUNNING   │ 1.27.2     │ 6     │ 24 vCPU │ 96 GB        │ 78.45%       │ 82.10%           │ 🟡 ADVERTENCIA│
│ cpl-cs-wms-qa-30112023       │ gke-qa-01                    │ us-central1-b    │ RUNNING   │ 1.27.1     │ 4     │ 16 vCPU │ 64 GB        │ 92.15%       │ 88.50%           │ 🔴 CRÍTICO   │
└──────────────────────────────┴──────────────────────────────┴──────────────────┴───────────┴────────────┴───────┴──────────┴──────────────┴──────────────┴──────────────────┴──────────────┘
```

---

## 🔧 Cambios Realizados

### 1. Nueva Función: `get_health_status()`

**Ubicación**: `gcp_monitor.py` líneas 181-213

**Características**:
- ✅ Calcula estado basado en CPU y memoria
- ✅ Maneja valores en rango 0-1 y 0-100
- ✅ Umbrales configurables
- ✅ Retorna emoji + estado descriptivo

### 2. Actualización de Tabla GKE

**Ubicación**: `gcp_monitor.py` líneas 487-528

**Cambios**:
- ✅ Extrae `cpu_used_percent` y `memory_used_percent` por separado
- ✅ Llama a `get_health_status()` con ambos valores
- ✅ Agrega columna "Salud" a la tabla
- ✅ Centra el contenido de la columna

### 3. Script Bash de Referencia

**Ubicación**: `scm/terminal/gcp-project-cluster-health.sh`

**Características**:
- ✅ Consulta Monitoring API directamente
- ✅ Procesa múltiples proyectos en paralelo
- ✅ Spinner y barra de progreso
- ✅ Umbrales: 75% (advertencia), 90% (crítico)
- ✅ Salida formateada con colores ANSI

---

## 📈 Comparación: Script Bash vs Python

| Aspecto | Bash Script | Python (gcp_monitor.py) |
|---------|-------------|------------------------|
| **Fuente de datos** | Monitoring API (MQL) | Monitoring API (Python client) |
| **Métrica CPU** | `kubernetes.io/node/cpu/allocatable_utilization` | `kubernetes.io/container/cpu/core_usage_time` |
| **Métrica Memoria** | `kubernetes.io/node/memory/allocatable_utilization` | `kubernetes.io/container/memory/used_bytes` |
| **Umbral Advertencia** | 75% | 75% ✅ |
| **Umbral Crítico** | 90% | 90% ✅ |
| **Salida** | Tabla con colores ANSI | Tabla Rich con emojis |
| **Paralelismo** | Secuencial | ThreadPoolExecutor |

---

## 🎨 Estados Visuales

### Emojis Utilizados

```
🟢 OK           → CPU < 75% Y Memoria < 75%
🟡 ADVERTENCIA  → CPU >= 75% O Memoria >= 75% (pero < 90%)
🔴 CRÍTICO      → CPU >= 90% O Memoria >= 90%
⚪ SIN DATOS    → CPU = NULL O Memoria = NULL
```

### Colores en Tabla Rich

```
Salud: style="white", justify="center"
```

---

## 🔍 Ejemplos de Uso

### Ejemplo 1: Cluster Saludable

```
Proyecto: cpl-cs-wms-dev-30112023
Cluster: gke-dev-01
CPU Usado: 45.32%
Memoria Usada: 62.18%
Max: 62.18% < 75%
→ Estado: 🟢 OK
```

### Ejemplo 2: Cluster con Advertencia

```
Proyecto: cpl-cs-wms-dev-30112023
Cluster: gke-prod-01
CPU Usado: 78.45%
Memoria Usada: 82.10%
Max: 82.10% >= 75% (< 90%)
→ Estado: 🟡 ADVERTENCIA
```

### Ejemplo 3: Cluster Crítico

```
Proyecto: cpl-cs-wms-qa-30112023
Cluster: gke-qa-01
CPU Usado: 92.15%
Memoria Usada: 88.50%
Max: 92.15% >= 90%
→ Estado: 🔴 CRÍTICO
```

### Ejemplo 4: Sin Datos

```
Proyecto: cpl-cs-wms-stag-09042025
Cluster: gke-stag-01
CPU Usado: N/A (None)
Memoria Usada: 65.00%
→ Estado: ⚪ SIN DATOS
```

---

## 📊 Integración en Flujo

```
1. Ejecutar: python gcp_monitor.py --project=PROJECT_ID
   ↓
2. Recopilar datos de GCP
   ↓
3. Obtener métricas de Monitoring API
   ↓
4. Para cada cluster:
   - Calcular CPU Total y Memoria Total
   - Obtener CPU Usado % y Memoria Usada %
   - Llamar get_health_status(cpu%, memory%)
   ↓
5. Mostrar tabla con columna "Salud"
   ↓
6. Generar JSON con métricas
   ↓
7. Generar HTML Dashboard
```

---

## ✅ Validación

### Pruebas Realizadas

- ✅ Función `get_health_status()` con valores 0-1
- ✅ Función `get_health_status()` con valores 0-100
- ✅ Función `get_health_status()` con None
- ✅ Tabla GKE muestra columna "Salud"
- ✅ Emojis se muestran correctamente
- ✅ Umbrales funcionan correctamente

### Casos de Prueba

```python
# Test 1: OK
get_health_status(0.45, 0.62) → '🟢 OK'

# Test 2: ADVERTENCIA
get_health_status(0.78, 0.82) → '🟡 ADVERTENCIA'

# Test 3: CRÍTICO
get_health_status(0.92, 0.88) → '🔴 CRÍTICO'

# Test 4: SIN DATOS
get_health_status(None, 0.65) → '⚪ SIN DATOS'

# Test 5: Porcentajes (0-100)
get_health_status(78, 82) → '🟡 ADVERTENCIA'
```

---

## 📝 Commit

```
4acbb0e - feat: Agregar estado de salud a tabla GKE basado en umbrales de CPU/Memoria
```

---

## 🚀 Próximos Pasos

### Mejoras Futuras

1. **Alertas Automáticas**: Enviar notificaciones cuando estado = CRÍTICO
2. **Histórico**: Guardar estados históricos para tendencias
3. **Configuración**: Permitir ajustar umbrales por usuario
4. **Compute Engine**: Aplicar misma lógica a instancias CE
5. **Cloud SQL**: Implementar estado de salud para bases de datos

---

## 📚 Documentación Relacionada

- `DASHBOARD_HTML_GUIDE.md` - Guía del dashboard HTML
- `gcp-project-cluster-health.sh` - Script bash de referencia
- `gcp_monitoring_metrics.py` - Módulo de métricas

---

**Status**: ✅ Completado  
**Versión**: 1.7.2  
**Listo para producción**
