# Análisis de Columnas: Capacidad + Uso Actual de Cómputo
## GCP Monitor - Tool 1

Documento de análisis para agregar columnas que muestren tanto la **capacidad disponible** como el **uso actual** de recursos en las tablas de **Clusters GKE** e **Instancias Compute Engine**.

---

## 📊 Tabla: Clusters GKE (☸️)

### Columnas Actuales
| Columna | Contenido | Ejemplo |
|---------|-----------|---------|
| Proyecto | ID del proyecto GCP | `cpl-cmanager-dev-13072023` |
| Nombre | Nombre del cluster | `gke-cluster-prod` |
| Ubicación | Región/Zona | `us-central1-a` |
| Estado | Estado del cluster | `RUNNING` |
| Versión | Versión de Kubernetes | `1.27.0` |
| Nodos | Cantidad de nodos | `6` |

### Columnas Recomendadas para Capacidad de Cómputo

#### 1. **CPU Total (vCPUs)** ⭐⭐⭐ ALTA PRIORIDAD
- **Descripción**: Suma total de CPUs disponibles en todos los nodos del cluster
- **Campo GCP**: `nodePools[].config.machineType` + `nodePools[].initialNodeCount`
- **Cálculo**: Especificación de máquina × cantidad de nodos
- **Ejemplo**: `24 vCPU` (6 nodos × 4 vCPU c/u)
- **Utilidad**: Ver capacidad total de procesamiento del cluster
- **Implementación**: Requiere mapeo de tipos de máquina a especificaciones

#### 2. **Memoria Total (GB)** ⭐⭐⭐ ALTA PRIORIDAD
- **Descripción**: Suma total de RAM disponible en todos los nodos
- **Campo GCP**: `nodePools[].config.machineType` + `nodePools[].initialNodeCount`
- **Cálculo**: Especificación de máquina × cantidad de nodos
- **Ejemplo**: `96 GB` (6 nodos × 16 GB c/u)
- **Utilidad**: Ver capacidad de memoria disponible
- **Implementación**: Mismo mapeo que CPU Total

#### 3. **Tipo de Máquina del Node Pool** ⭐⭐ MEDIA PRIORIDAD
- **Descripción**: Tipo de máquina usado en los nodos
- **Campo GCP**: `nodePools[].config.machineType`
- **Ejemplo**: `n1-standard-4` o `e2-medium`
- **Utilidad**: Entender configuración de hardware del cluster
- **Implementación**: Extraer último segmento del path completo

#### 4. **Número de Node Pools** ⭐ BAJA PRIORIDAD
- **Descripción**: Cantidad de pools de nodos diferentes
- **Campo GCP**: `nodePools.length`
- **Ejemplo**: `2 pools`
- **Utilidad**: Identificar clusters con múltiples configuraciones
- **Implementación**: Simple conteo

#### 5. **Disco por Nodo (GB)** ⭐ BAJA PRIORIDAD
- **Descripción**: Tamaño de disco local por nodo
- **Campo GCP**: `nodePools[].config.diskSizeGb`
- **Ejemplo**: `100 GB`
- **Utilidad**: Capacidad de almacenamiento local
- **Implementación**: Lectura directa del campo

### Columnas Recomendadas - USO ACTUAL ⭐⭐⭐ NUEVA PRIORIDAD

#### 1. **CPU Usado (%)** ⭐⭐⭐ ALTA PRIORIDAD
- **Descripción**: Porcentaje de CPU utilizado en el cluster
- **Campo GCP**: Cloud Monitoring API - `kubernetes.io/container/cpu/core_usage_time`
- **Ejemplo**: `45%`
- **Utilidad**: Ver carga actual de procesamiento
- **Implementación**: Consultar Monitoring API para últimas 5 minutos
- **Nota**: Requiere Monitoring API habilitada

#### 2. **Memoria Usada (%)** ⭐⭐⭐ ALTA PRIORIDAD
- **Descripción**: Porcentaje de memoria utilizada
- **Campo GCP**: Cloud Monitoring API - `kubernetes.io/container/memory/used_bytes`
- **Ejemplo**: `62%`
- **Utilidad**: Ver presión de memoria
- **Implementación**: Consultar Monitoring API para últimas 5 minutos
- **Nota**: Requiere Monitoring API habilitada

#### 3. **Pods Activos** ⭐⭐ MEDIA PRIORIDAD
- **Descripción**: Cantidad de pods corriendo en el cluster
- **Campo GCP**: Cloud Monitoring API o `kubectl get pods`
- **Ejemplo**: `45 pods`
- **Utilidad**: Carga de trabajo actual
- **Implementación**: Contar pods en ejecución

---

## 💻 Tabla: Instancias Compute Engine

### Columnas Actuales
| Columna | Contenido | Ejemplo |
|---------|-----------|---------|
| Proyecto | ID del proyecto GCP | `cpl-cmanager-dev-13072023` |
| Nombre | Nombre de la instancia | `web-server-01` |
| Estado | Estado de la VM | `RUNNING` |
| Tipo | Tipo de máquina | `n1-standard-4` |
| Zona | Zona de disponibilidad | `us-central1-a` |

### Columnas Recomendadas para Capacidad de Cómputo

#### 1. **CPUs** ⭐⭐⭐ ALTA PRIORIDAD
- **Descripción**: Número de CPUs de la máquina
- **Campo GCP**: `machineType` (extraer especificación)
- **Ejemplo**: `4` o `8`
- **Utilidad**: Capacidad de procesamiento individual
- **Implementación**: Mapeo de tipo de máquina a especificación

#### 2. **Memoria (GB)** ⭐⭐⭐ ALTA PRIORIDAD
- **Descripción**: RAM disponible en la máquina
- **Campo GCP**: `machineType` (extraer especificación)
- **Ejemplo**: `16 GB` o `32 GB`
- **Utilidad**: Capacidad de memoria individual
- **Implementación**: Mapeo de tipo de máquina a especificación

#### 3. **Disco Raíz (GB)** ⭐⭐ MEDIA PRIORIDAD
- **Descripción**: Tamaño del disco de arranque
- **Campo GCP**: `disks[0].sizeGb` (disco de arranque)
- **Ejemplo**: `100 GB`
- **Utilidad**: Espacio disponible en el sistema
- **Implementación**: Lectura directa del primer disco

#### 4. **Discos Adicionales** ⭐ BAJA PRIORIDAD
- **Descripción**: Cantidad de discos adicionales adjuntos
- **Campo GCP**: `disks.length - 1`
- **Ejemplo**: `2 discos`
- **Utilidad**: Almacenamiento adicional
- **Implementación**: Conteo de discos

#### 5. **GPU** ⭐⭐ MEDIA PRIORIDAD
- **Descripción**: Tipo y cantidad de GPUs
- **Campo GCP**: `guestAccelerators[].acceleratorType`
- **Ejemplo**: `1x NVIDIA Tesla K80` o `N/A`
- **Utilidad**: Capacidad de aceleración
- **Implementación**: Lectura y formateo de aceleradores

#### 6. **Preemptible** ⭐ BAJA PRIORIDAD
- **Descripción**: Si es instancia preemptible
- **Campo GCP**: `scheduling.preemptible`
- **Ejemplo**: `Sí` o `No`
- **Utilidad**: Tipo de instancia y costo
- **Implementación**: Lectura booleana

### Columnas Recomendadas - USO ACTUAL ⭐⭐⭐ NUEVA PRIORIDAD

#### 1. **CPU Usado (%)** ⭐⭐⭐ ALTA PRIORIDAD
- **Descripción**: Porcentaje de CPU utilizado
- **Campo GCP**: Cloud Monitoring API - `compute.googleapis.com/instance/cpu/utilization`
- **Ejemplo**: `35%`
- **Utilidad**: Ver carga de procesamiento actual
- **Implementación**: Consultar Monitoring API para últimas 5 minutos
- **Nota**: Requiere Monitoring API habilitada

#### 2. **Memoria Usada (%)** ⭐⭐⭐ ALTA PRIORIDAD
- **Descripción**: Porcentaje de memoria utilizada
- **Campo GCP**: Cloud Monitoring API - `agent.googleapis.com/memory/percent_used`
- **Ejemplo**: `58%`
- **Utilidad**: Ver presión de memoria
- **Implementación**: Consultar Monitoring API para últimas 5 minutos
- **Nota**: Requiere Google Cloud Ops Agent instalado en la VM

#### 3. **Disco Usado (%)** ⭐⭐⭐ ALTA PRIORIDAD
- **Descripción**: Porcentaje de disco utilizado
- **Campo GCP**: Cloud Monitoring API - `agent.googleapis.com/disk/percent_used`
- **Ejemplo**: `72%`
- **Utilidad**: Ver espacio disponible en el disco
- **Implementación**: Consultar Monitoring API para últimas 5 minutos
- **Nota**: Requiere Google Cloud Ops Agent instalado en la VM

---

## 🔧 Especificaciones de Máquinas GCP

### Tipos Comunes de Máquinas

#### Familia N1 (General Purpose)
| Tipo | vCPU | RAM | Disco |
|------|------|-----|-------|
| `n1-standard-1` | 1 | 3.75 GB | - |
| `n1-standard-2` | 2 | 7.5 GB | - |
| `n1-standard-4` | 4 | 15 GB | - |
| `n1-standard-8` | 8 | 30 GB | - |
| `n1-standard-16` | 16 | 60 GB | - |
| `n1-standard-32` | 32 | 120 GB | - |
| `n1-standard-64` | 64 | 240 GB | - |
| `n1-standard-96` | 96 | 360 GB | - |

#### Familia E2 (Cost-Optimized)
| Tipo | vCPU | RAM | Disco |
|------|------|-----|-------|
| `e2-micro` | 0.25 | 1 GB | - |
| `e2-small` | 0.5 | 2 GB | - |
| `e2-medium` | 1 | 4 GB | - |
| `e2-standard-2` | 2 | 8 GB | - |
| `e2-standard-4` | 4 | 16 GB | - |
| `e2-standard-8` | 8 | 32 GB | - |
| `e2-standard-16` | 16 | 64 GB | - |
| `e2-standard-32` | 32 | 128 GB | - |

#### Familia C2 (Compute-Optimized)
| Tipo | vCPU | RAM | Disco |
|------|------|-----|-------|
| `c2-standard-4` | 4 | 16 GB | - |
| `c2-standard-8` | 8 | 32 GB | - |
| `c2-standard-16` | 16 | 64 GB | - |
| `c2-standard-30` | 30 | 120 GB | - |
| `c2-standard-60` | 60 | 240 GB | - |

#### Familia M1 (Memory-Optimized)
| Tipo | vCPU | RAM | Disco |
|------|------|-----|-------|
| `m1-megamem-96` | 96 | 1433.6 GB | - |
| `m1-ultramem-40` | 40 | 961 GB | - |
| `m1-ultramem-80` | 80 | 1922 GB | - |
| `m1-ultramem-160` | 160 | 3844 GB | - |

---

## 📋 Plan de Implementación Actualizado

### Fase 1: Capacidad Básica (INMEDIATO - 2-3 horas)
1. **Crear diccionario de mapeo** de tipos de máquina a especificaciones
2. **GKE**: Agregar columnas `CPU Total` y `Memoria Total`
3. **Compute**: Agregar columnas `CPUs`, `Memoria (GB)` y `Disco Raíz (GB)`
4. **Pruebas**: Validar con datos reales de GCP

### Fase 2: Uso Actual (SIGUIENTE - 4-6 horas)
1. **Integración con Cloud Monitoring API**
   - Crear función para consultar métricas
   - Configurar autenticación y permisos
   
2. **GKE**: Agregar columnas `CPU Usado (%)` y `Memoria Usada (%)`
   - Consultar últimas 5 minutos de datos
   - Mostrar promedio de utilización
   
3. **Compute**: Agregar columnas `CPU Usado (%)`, `Memoria Usada (%)` y `Disco Usado (%)`
   - Consultar últimas 5 minutos de datos
   - Mostrar promedio de utilización

4. **Manejo de errores**: Si Monitoring API no está disponible, mostrar "N/A"

### Fase 3: Características Avanzadas (FUTURO)
1. **GKE**: Agregar `Pods Activos`, `Tipo de Máquina del Node Pool`
2. **Compute**: Agregar `GPU`, `Discos Adicionales`, `Preemptible`
3. **Análisis**: Crear reportes de capacidad vs uso
4. **Alertas**: Identificar recursos con alta utilización

---

## � Integración con Cloud Monitoring API

### Requisitos Previos
1. **API habilitada**: `monitoring.googleapis.com`
2. **Permisos**: `monitoring.timeSeries.list`
3. **Autenticación**: Usar credenciales de GCP (gcloud auth)

### Ejemplo de Consulta para GKE CPU

```bash
gcloud monitoring time-series list \
  --filter='resource.type="k8s_cluster" AND metric.type="kubernetes.io/container/cpu/core_usage_time"' \
  --format=json \
  --project=PROJECT_ID
```

### Ejemplo de Consulta para Compute Engine CPU

```bash
gcloud monitoring time-series list \
  --filter='resource.type="gce_instance" AND metric.type="compute.googleapis.com/instance/cpu/utilization"' \
  --format=json \
  --project=PROJECT_ID
```

### Ejemplo de Consulta para Compute Engine Memoria (requiere Ops Agent)

```bash
gcloud monitoring time-series list \
  --filter='resource.type="gce_instance" AND metric.type="agent.googleapis.com/memory/percent_used"' \
  --format=json \
  --project=PROJECT_ID
```

### Ejemplo de Consulta para Compute Engine Disco (requiere Ops Agent)

```bash
gcloud monitoring time-series list \
  --filter='resource.type="gce_instance" AND metric.type="agent.googleapis.com/disk/percent_used"' \
  --format=json \
  --project=PROJECT_ID
```

---

## �🔍 Ejemplo de Datos JSON

### GKE Cluster
```json
{
  "name": "gke-cluster-prod",
  "nodePools": [
    {
      "name": "default-pool",
      "initialNodeCount": 6,
      "config": {
        "machineType": "zones/us-central1-a/machineTypes/n1-standard-4",
        "diskSizeGb": 100
      }
    }
  ]
}
```

### Compute Instance
```json
{
  "name": "web-server-01",
  "machineType": "zones/us-central1-a/machineTypes/n1-standard-4",
  "disks": [
    {
      "sizeGb": "100",
      "boot": true
    },
    {
      "sizeGb": "500",
      "boot": false
    }
  ],
  "guestAccelerators": [
    {
      "acceleratorType": "nvidia-tesla-k80",
      "acceleratorCount": 1
    }
  ],
  "scheduling": {
    "preemptible": false
  }
}
```

---

## 💡 Recomendaciones Finales

### Columnas Prioritarias por Tabla

#### Clusters GKE (☸️)
**Fase 1 (Capacidad)**:
- CPU Total (vCPUs)
- Memoria Total (GB)

**Fase 2 (Uso Actual)**:
- CPU Usado (%)
- Memoria Usada (%)

**Resultado**: Visión completa de capacidad vs uso del cluster

#### Instancias Compute Engine (💻)
**Fase 1 (Capacidad)**:
- CPUs
- Memoria (GB)
- Disco Raíz (GB)

**Fase 2 (Uso Actual)**:
- CPU Usado (%)
- Memoria Usada (%)
- Disco Usado (%)

**Resultado**: Visión completa de capacidad vs uso de cada VM

### Consideraciones Técnicas
1. **Mapeo de tipos de máquina**: Debe ser mantenible y actualizable
2. **Cloud Monitoring API**: Requiere permisos y API habilitada
3. **Google Cloud Ops Agent**: Necesario para métricas de memoria y disco en Compute
4. **Manejo de errores**: Si las métricas no están disponibles, mostrar "N/A"
5. **Performance**: Cachear datos de capacidad (estáticos), actualizar uso cada 5 min

### Beneficios Esperados
- **Planificación**: Saber capacidad disponible
- **Optimización**: Identificar recursos subutilizados
- **Alertas**: Detectar recursos con alta utilización
- **Reportes**: Análisis de capacidad vs demanda
- **Decisiones**: Información para escalado y ajustes

