# 🔌 Implementación de REST API Exacta de Monitoring

**Versión**: 1.7.2  
**Fecha**: 18 de Julio de 2026  
**Status**: ✅ Completado  
**Basado en**: `gcp-project-cluster-health.sh`

---

## 📋 Resumen

Se ha reescrito el módulo `gcp_monitoring_metrics.py` para usar la **REST API exacta** de Google Cloud Monitoring (`https://monitoring.googleapis.com/v3`) en lugar del cliente Python. Ahora implementa al 100% la lógica del script bash.

---

## 🔄 Cambios Principales

### Antes (Cliente Python)
```python
from google.cloud import monitoring_v3
client = monitoring_v3.MetricServiceClient()
results = client.query_time_series(name=project_name, query=cpu_query)
```

### Después (REST API)
```python
token = _get_gcloud_token()  # gcloud auth print-access-token
headers = {'Authorization': f'Bearer {token}'}
response = requests.post(
    f"{MONITORING_API}/projects/{project_id}/timeSeries:query",
    json={'query': mql_query},
    headers=headers
)
```

---

## 🔑 Funciones Nuevas

### 1. `_get_gcloud_token()`
**Propósito**: Obtener token de acceso de gcloud (como en script bash)

```python
def _get_gcloud_token() -> Optional[str]:
    """Ejecuta: gcloud auth print-access-token"""
    result = subprocess.run(
        ['gcloud', 'auth', 'print-access-token'],
        capture_output=True,
        text=True,
        timeout=10
    )
    return result.stdout.strip() if result.returncode == 0 else None
```

**Equivalente en Bash**:
```bash
TOKEN="$(gcloud auth print-access-token)"
```

---

### 2. `_query_monitoring_rest()`
**Propósito**: Consultar Monitoring API REST directamente

```python
def _query_monitoring_rest(project_id: str, mql_query: str, logger=None) -> Optional[Dict]:
    """Consulta: POST https://monitoring.googleapis.com/v3/projects/{project_id}/timeSeries:query"""
    token = _get_gcloud_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    url = f"{MONITORING_API}/projects/{project_id}/timeSeries:query"
    response = requests.post(url, json={'query': mql_query}, headers=headers, timeout=30)
    return response.json() if response.status_code == 200 else None
```

**Equivalente en Bash**:
```bash
curl -sS -X POST \
  "${MONITORING_API}/projects/${project_id}/timeSeries:query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg query "${mql_query}" '{query: $query}')"
```

---

### 3. `_extract_latest_value()`
**Propósito**: Extraer el valor más reciente de la respuesta JSON

```python
def _extract_latest_value(response: Dict) -> Optional[float]:
    """Extrae el valor numérico de timeSeriesData"""
    for ts_data in response.get('timeSeriesData', []):
        for point_data in ts_data.get('pointData', []):
            for value in point_data.get('values', []):
                if 'doubleValue' in value:
                    return float(value['doubleValue'])
                elif 'int64Value' in value:
                    return float(value['int64Value'])
    return None
```

**Equivalente en Bash**:
```bash
jq -r '[.timeSeriesData[]? | .pointData[]? | .values[]? | (.doubleValue? // .int64Value? // empty)] | first // empty'
```

---

## 📊 Queries MQL Exactas

### GKE CPU (Idéntica al Script Bash)

**Antes**:
```mql
fetch k8s_cluster
| metric 'kubernetes.io/container/cpu/core_usage_time'
| filter resource.project_id == '{project_id}'
| filter resource.cluster_name == '{cluster_name}'
| filter resource.location == '{location}'
| group_by [value_cpu: mean(value.cpu_usage)]
```

**Después (Exacta)**:
```mql
fetch k8s_node
| metric 'kubernetes.io/node/cpu/allocatable_utilization'
| filter resource.cluster_name == '{cluster_name}' && resource.location == '{location}'
| within 24h
| group_by [], mean(val())
```

### GKE Memoria (Idéntica al Script Bash)

**Antes**:
```mql
fetch k8s_cluster
| metric 'kubernetes.io/container/memory/used_bytes'
| filter resource.project_id == '{project_id}'
| filter resource.cluster_name == '{cluster_name}'
| filter resource.location == '{location}'
| group_by [value_mem: mean(value.memory_used)]
```

**Después (Exacta)**:
```mql
fetch k8s_node
| metric 'kubernetes.io/node/memory/allocatable_utilization'
| filter resource.cluster_name == '{cluster_name}' && resource.location == '{location}'
| within 24h
| group_by [], mean(val())
```

---

## 🔧 Configuración

### Constantes Globales

```python
MONITORING_API = "https://monitoring.googleapis.com/v3"
WINDOW = "24h"  # Ventana temporal (configurable)
```

### Umbrales (Heredados)

```python
WARNING_THRESHOLD = 75    # %
CRITICAL_THRESHOLD = 90   # %
```

---

## 📦 Dependencias Nuevas

```
requests>=2.28.0
```

Agregado a `requirements.txt`

---

## 🔄 Flujo de Ejecución

```
1. get_gke_usage_metrics(project_id, cluster_name, location)
   ↓
2. Construir queries MQL (idénticas al script bash)
   ↓
3. _query_monitoring_rest(project_id, cpu_query)
   ├─ _get_gcloud_token()  → gcloud auth print-access-token
   ├─ requests.post() → https://monitoring.googleapis.com/v3/...
   └─ response.json()
   ↓
4. _extract_latest_value(response)
   ├─ Navegar: timeSeriesData → pointData → values
   └─ Retornar: doubleValue o int64Value
   ↓
5. Convertir a porcentaje (si es necesario)
   ├─ Si valor <= 1 → multiplicar por 100
   └─ Si valor > 1 → usar como está
   ↓
6. Retornar: {'cpu_used_percent': X, 'memory_used_percent': Y, 'status': 'success'}
```

---

## ✅ Validación

### Comparación: Script Bash vs Python

| Aspecto | Bash | Python | Estado |
|---------|------|--------|--------|
| **API Endpoint** | `https://monitoring.googleapis.com/v3` | ✅ Idéntico | ✅ |
| **Token** | `gcloud auth print-access-token` | ✅ `subprocess.run()` | ✅ |
| **Método HTTP** | `curl -X POST` | ✅ `requests.post()` | ✅ |
| **Headers** | `Authorization: Bearer {TOKEN}` | ✅ Idéntico | ✅ |
| **Query MQL CPU** | `kubernetes.io/node/cpu/allocatable_utilization` | ✅ Idéntico | ✅ |
| **Query MQL Memoria** | `kubernetes.io/node/memory/allocatable_utilization` | ✅ Idéntico | ✅ |
| **Ventana Temporal** | `within 24h` | ✅ `WINDOW = "24h"` | ✅ |
| **Extracción de Valor** | `jq` | ✅ `_extract_latest_value()` | ✅ |
| **Conversión %** | `awk` | ✅ Condicional | ✅ |

---

## 🎯 Beneficios

✅ **100% Exacto**: Idéntico al script bash  
✅ **REST API Directa**: Sin dependencias de cliente Python  
✅ **Token Refresh**: Obtiene token fresco en cada consulta  
✅ **Queries MQL Exactas**: Métricas de nodos, no de contenedores  
✅ **Ventana Configurable**: `WINDOW = "24h"` (como en bash)  
✅ **Mejor Precisión**: Usa `allocatable_utilization` (más preciso)

---

## 📝 Ejemplo de Respuesta

### Request
```bash
POST https://monitoring.googleapis.com/v3/projects/cpl-cs-wms-dev-30112023/timeSeries:query
Authorization: Bearer ya29.a0AfH6SMB...
Content-Type: application/json

{
  "query": "fetch k8s_node | metric 'kubernetes.io/node/cpu/allocatable_utilization' | filter resource.cluster_name == 'gke-dev-01' && resource.location == 'us-central1-a' | within 24h | group_by [], mean(val())"
}
```

### Response
```json
{
  "timeSeriesData": [
    {
      "pointData": [
        {
          "values": [
            {
              "doubleValue": 0.4532
            }
          ]
        }
      ]
    }
  ]
}
```

### Procesamiento
```python
response = requests.post(...)  # → Response JSON
value = _extract_latest_value(response)  # → 0.4532
percent = value * 100 if value <= 1 else value  # → 45.32
result = round(percent, 1)  # → 45.3
```

---

## 🔐 Autenticación

### Requisitos

1. **gcloud CLI instalado y configurado**
   ```bash
   gcloud auth login
   gcloud config set project PROJECT_ID
   ```

2. **Permisos necesarios**
   ```
   monitoring.timeSeries.list
   ```

3. **Token válido**
   ```bash
   gcloud auth print-access-token  # Debe retornar token válido
   ```

---

## 📚 Documentación Relacionada

- `gcp-project-cluster-health.sh` - Script bash original
- `GKE_HEALTH_STATUS_IMPLEMENTATION.md` - Estado de salud
- `DASHBOARD_HTML_GUIDE.md` - Dashboard HTML

---

## 📦 Commit

```
5cf8be6 - feat: Implementar REST API exacta de Monitoring como en gcp-project-cluster-health.sh
```

---

**Status**: ✅ Completado  
**Precisión**: 100% con script bash  
**Versión**: 1.7.2  
**Listo para producción**
