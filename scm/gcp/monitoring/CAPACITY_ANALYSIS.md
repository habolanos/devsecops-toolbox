# Análisis de Columnas de Capacidad de Cómputo
## GCP Monitor - Tool 1

Documento de análisis para agregar columnas que muestren la capacidad de cómputo en las tablas de **Clusters GKE** e **Instancias Compute Engine**.

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

## 📋 Plan de Implementación

### Fase 1: Implementación Básica (RECOMENDADO)
1. **Crear diccionario de mapeo** de tipos de máquina a especificaciones
2. **GKE**: Agregar columnas `CPU Total` y `Memoria Total`
3. **Compute**: Agregar columnas `CPUs` y `Memoria (GB)`
4. **Pruebas**: Validar con datos reales de GCP

### Fase 2: Mejoras Adicionales
1. **GKE**: Agregar `Tipo de Máquina del Node Pool`
2. **Compute**: Agregar `Disco Raíz (GB)` y `GPU`
3. **Optimización**: Mejorar formato y presentación

### Fase 3: Características Avanzadas
1. **GKE**: Agregar `Número de Node Pools` y `Disco por Nodo`
2. **Compute**: Agregar `Discos Adicionales` y `Preemptible`
3. **Análisis**: Crear reportes de capacidad total

---

## 🔍 Ejemplo de Datos JSON

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

### Para Clusters GKE:
- **Prioridad**: CPU Total + Memoria Total
- **Razón**: Permite ver capacidad total del cluster de un vistazo
- **Impacto**: Alto - información crítica para planificación

### Para Compute Engine:
- **Prioridad**: CPUs + Memoria (GB)
- **Razón**: Información esencial de cada instancia
- **Impacto**: Alto - datos fundamentales

### Consideraciones:
- El mapeo de tipos de máquina debe ser mantenible
- Considerar usar API de GCP para obtener especificaciones dinámicamente
- Validar que los datos estén disponibles en todas las regiones

