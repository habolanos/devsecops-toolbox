# 📊 Análisis de Límites de Recursos Kubernetes

Sistema automatizado para analizar y recomendar límites de CPU y memoria en clústeres GKE basado en métricas históricas de **90 días**.

---

## 📋 Componentes

### 1. **config.env** - Configuración
Define los clústeres GKE a analizar.

```bash
CLUSTERS=(
  "gke_cpl-cs-wms-qa-30112023_us-central1_gke-cs-wms-qa-01"
  "gke_cpl-cs-wms-qa-30112023_us-central1_gke-cs-wms-qa-02"
)
```

**Formato:** `gke_<PROJECT_ID>_<REGION>_<CLUSTER_NAME>`

### 2. **deployments_info.sh** - Orquestador
Script principal que:
- Itera sobre cada clúster
- Obtiene credenciales
- Cambia contexto kubectl
- Ejecuta análisis Python
- Registra logs detallados

### 3. **history_limits_v3.py** - Motor de Análisis
Analiza métricas Kubernetes para:
- **CPU:** promedio, min, max, p95, p99
- **Memoria:** total, evictable, non-evictable
- **Recomendaciones:** basadas en percentiles + margen de seguridad

---

## 🚀 Instalación de Dependencias

### Python
```bash
pip install pandas google-cloud-monitoring kubernetes openpyxl
```

### CLI Tools
```bash
# gcloud (si no está instalado)
curl https://sdk.cloud.google.com | bash

# kubectl
gcloud components install kubectl

# kubectx (recomendado)
git clone https://github.com/ahmetb/kubectx /opt/kubectx
sudo ln -s /opt/kubectx/kubectx /usr/local/bin/kubectx
```

---

## 🎯 Uso

### Ejecución Completa
```bash
cd ~/repos-publics/devsecops-toolbox/scm/terminal/limits

bash deployments_info.sh
```

### Ver Logs en Tiempo Real
```bash
tail -f limits_analysis.log
```

### Ejecución Manual por Clúster
```bash
# 1. Obtener credenciales
gcloud container clusters get-credentials gke-cs-wms-qa-01 \
  --zone us-central1 \
  --project cpl-cs-wms-qa-30112023

# 2. Cambiar contexto
kubectx gke_cpl-cs-wms-qa-30112023_us-central1_gke-cs-wms-qa-01

# 3. Ejecutar análisis
python3 history_limits_v3.py cpl-cs-wms-qa-30112023 gke-cs-wms-qa-01
```

### Análisis Personalizado
```bash
# Analizar últimos 30 días (en lugar de 90)
python3 history_limits_v3.py cpl-cs-wms-qa-30112023 gke-cs-wms-qa-01 30
```

---

## 📊 Salida

### Archivo Excel
```
reporte_recursos_gke-cs-wms-qa-01.xlsx
```

### Columnas Incluidas

#### Identificación
- `namespace` - Namespace del contenedor
- `deployment` - Nombre del Deployment
- `container` - Nombre del contenedor
- `request_cpu`, `limit_cpu` - Valores actuales de CPU
- `request_mem`, `limit_mem` - Valores actuales de memoria
- `hpa_min`, `hpa_max`, `hpa_target_cpu` - Configuración HPA

#### Métricas Actuales (90 días)
- `cpu_avg_m` - CPU promedio (millicores)
- `cpu_min_m` - CPU mínimo
- `cpu_max_m` - CPU máximo
- `cpu_p95_m` - Percentil 95
- `cpu_p99_m` - Percentil 99
- `mem_avg_Mi` - Memoria promedio (MiB)
- `mem_min_Mi` - Memoria mínima
- `mem_max_Mi` - Memoria máxima
- `mem_p95_Mi` - Percentil 95
- `mem_p99_Mi` - Percentil 99
- `mem_non_evict_avg_Mi` - Memoria no evictable
- `mem_evict_avg_Mi` - Memoria evictable

#### Recomendaciones
- `cpu_request_sugerido_m` - CPU request recomendado
- `cpu_limit_sugerido_m` - CPU limit recomendado
- `mem_request_sugerido_Mi` - Memoria request recomendada
- `mem_limit_sugerido_Mi` - Memoria limit recomendada

---

## 📈 Algoritmo de Recomendaciones

### CPU Request
```
sugerido = max(promedio × 1.2, p95) redondeado a 10m
```

### CPU Limit
```
sugerido = p99 × 1.5 redondeado a 10m
```

### Memoria Request
```
sugerido = max(promedio × 1.2, p95) redondeado a 50Mi
```

### Memoria Limit
```
sugerido = p99 × 1.4 redondeado a 50Mi
```

---

## ⏱️ Tiempo Estimado

| Métrica | Tiempo |
|---------|--------|
| Por clúster | 3-5 minutos |
| 3 clústeres | 9-15 minutos |
| Timeout máximo | 60 minutos |

---

## 🔧 Configuración Ajustable

En `history_limits_v3.py` (líneas 14-21):

```python
DIAS_A_ANALIZAR = 90      # Período de análisis
MAX_TRABAJADORES = 10     # Paralelismo de consultas
CPU_STEP = 10             # Redondeo de CPU (millicores)
MEM_STEP = 50             # Redondeo de memoria (MiB)
```

En `deployments_info.sh` (línea 66):

```bash
timeout 48000 python3 ...  # Timeout en segundos (48000 = 13.3 horas)
```

---

## 🔍 Troubleshooting

### Error: "No cluster named..."
**Causa:** Comas en el array CLUSTERS en config.env
**Solución:** Remover comas finales

```bash
# ❌ Incorrecto
CLUSTERS=(
  "gke_..._01",
  "gke_..._02",
)

# ✅ Correcto
CLUSTERS=(
  "gke_..._01"
  "gke_..._02"
)
```

### Error: "failed to switch context"
**Causa:** Contexto kubectl no existe
**Solución:** Ejecutar `gcloud container clusters get-credentials` primero

### Script se cuelga
**Causa:** Consulta lenta de métricas o timeout insuficiente
**Solución:** Aumentar timeout en deployments_info.sh (línea 66)

```bash
timeout 48000 python3 ...  # Aumentar este valor
```

### No se encuentran contenedores
**Causa:** Clúster sin Deployments
**Solución:** Verificar que el clúster tiene aplicaciones desplegadas

```bash
kubectl get deployments --all-namespaces
```

---

## 📝 Logs

### Archivo de Log
```
limits_analysis.log
```

Contiene:
- Cada paso del proceso
- Errores y advertencias
- Timestamps
- Detalles de ejecución

---

## 📊 Ejemplo de Salida

```
[INFO] [1/1] Procesando: gke_cpl-cs-wms-qa-30112023_us-central1_gke-cs-wms-qa-01
[INFO]   Proyecto: cpl-cs-wms-qa-30112023
[INFO]   Región: us-central1
[INFO]   Clúster: gke-cs-wms-qa-01
[INFO]   Obteniendo credenciales...
[INFO]   Cambiando contexto kubectl...
[INFO]   Iniciando análisis de límites (esto puede tomar 3-5 minutos)...
[PASO 1/5] Configurando Kubernetes...
[PASO 2/5] Obteniendo HPAs...
  → 5 HPAs encontrados
[PASO 3/5] Obteniendo contenedores...
  → 23 contenedores encontrados
[PASO 4/5] Analizando métricas (23 contenedores)...
[23/23] ██████████████████████████████ 100.0% | ETA: 0m 00s | namespace/deployment/container
✅ Completado en 4m 32s
[PASO 5/5] Generando reporte Excel...
✅ Reporte generado: reporte_recursos_gke-cs-wms-qa-01.xlsx
[INFO] ✅ Análisis completado para gke-cs-wms-qa-01
[INFO] ✅ Procesamiento completado. Ver limits_analysis.log para detalles.
```

---

## 🎯 Próximos Pasos

1. **Revisar reporte Excel** - Analizar recomendaciones
2. **Aplicar cambios** - Actualizar requests/limits en Deployments
3. **Monitorear** - Verificar impacto en performance
4. **Iterar** - Ejecutar análisis periódicamente (mensual)

---

**Versión:** 1.0  
**Última actualización:** 22 de Julio de 2026
