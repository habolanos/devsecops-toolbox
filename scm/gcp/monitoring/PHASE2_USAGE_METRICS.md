# 📊 Fase 2 - Métricas de Uso Actual (Cloud Monitoring API)

**Versión**: 1.7.1  
**Fecha**: 18 de Julio de 2026  
**Estado**: 📋 PLANIFICADO (No Implementado)

---

## 📋 Resumen Ejecutivo

La **Fase 2** implementará métricas de uso actual (CPU usado %, Memoria usada %, Disco usado %) usando la **Cloud Monitoring API de GCP**.

**Columnas a llenar**:
- GKE: CPU Usado (%), Memoria Usada (%)
- Compute Engine: CPU Usado (%), Memoria Usada (%), Disco Usado (%)

---

## 🔄 Estado Actual vs Fase 2

### **Fase 1 (✅ COMPLETADA)**
```
Columnas de Capacidad:
├─ GKE: CPU Total, Memoria Total
├─ Compute: CPUs, Memoria, Disco Raíz
└─ Fuente: Datos estáticos de GCP API
```

### **Fase 2 (📋 PLANIFICADA)**
```
Columnas de Uso Actual:
├─ GKE: CPU Usado (%), Memoria Usada (%)
├─ Compute: CPU Usado (%), Memoria Usada (%), Disco Usado (%)
└─ Fuente: Cloud Monitoring API (últimas 5 minutos)
```

---

## 🏗️ Arquitectura de Fase 2

### **Flujo de Datos**

```
GCP Cloud Monitoring API
    ↓
Métricas disponibles:
├─ kubernetes.io/container/cpu/core_usage_time (GKE)
├─ kubernetes.io/container/memory/used_bytes (GKE)
├─ compute.googleapis.com/instance/cpu/utilization (Compute)
├─ agent.googleapis.com/memory/percent_used (Compute)
└─ agent.googleapis.com/disk/percent_used (Compute)
    ↓
Procesamiento paralelo (ThreadPoolExecutor)
    ↓
Cálculo de promedios (últimas 5 minutos)
    ↓
Llenado de columnas en tablas
```

---

## 📊 Métricas por Servicio

### **GKE - Clusters**

#### **1. CPU Usado (%)**
```
Métrica GCP: kubernetes.io/container/cpu/core_usage_time
Descripción: Tiempo de uso de CPU en el cluster
Cálculo: (cpu_usage / cpu_capacity) × 100
Ejemplo: 45%
Unidad: Porcentaje
Período: Últimas 5 minutos (promedio)
```

#### **2. Memoria Usada (%)**
```
Métrica GCP: kubernetes.io/container/memory/used_bytes
Descripción: Bytes de memoria utilizada
Cálculo: (memory_used / memory_capacity) × 100
Ejemplo: 62%
Unidad: Porcentaje
Período: Últimas 5 minutos (promedio)
```

### **Compute Engine - Instancias**

#### **1. CPU Usado (%)**
```
Métrica GCP: compute.googleapis.com/instance/cpu/utilization
Descripción: Utilización de CPU
Ejemplo: 35%
Unidad: Porcentaje (0-100)
Período: Últimas 5 minutos (promedio)
Requisito: Monitoring Agent habilitado
```

#### **2. Memoria Usada (%)**
```
Métrica GCP: agent.googleapis.com/memory/percent_used
Descripción: Porcentaje de memoria utilizada
Ejemplo: 58%
Unidad: Porcentaje (0-100)
Período: Últimas 5 minutos (promedio)
Requisito: Google Cloud Ops Agent instalado
```

#### **3. Disco Usado (%)**
```
Métrica GCP: agent.googleapis.com/disk/percent_used
Descripción: Porcentaje de disco utilizado
Ejemplo: 72%
Unidad: Porcentaje (0-100)
Período: Últimas 5 minutos (promedio)
Requisito: Google Cloud Ops Agent instalado
```

---

## 💻 Implementación Técnica

### **Función: `get_gke_usage_metrics()`**

```python
def get_gke_usage_metrics(
    project_id: str,
    cluster_name: str,
    location: str,
    debug: bool = False,
    console = None,
    logger = None
) -> Dict[str, Any]:
    """Obtiene métricas de uso actual de un cluster GKE.
    
    Args:
        project_id: ID del proyecto GCP
        cluster_name: Nombre del cluster
        location: Ubicación del cluster
        debug: Modo debug
        console: Console de Rich
        logger: Logger
        
    Returns:
        {
            'cpu_used_percent': 45.2,
            'memory_used_percent': 62.1
        }
    """
    try:
        # Inicializar cliente de Monitoring
        monitoring_client = monitoring_v3.MetricServiceClient()
        
        # Construir query de MQL (Monitoring Query Language)
        query = f"""
        fetch k8s_cluster
        | metric 'kubernetes.io/container/cpu/core_usage_time'
        | filter resource.project_id == '{project_id}'
        | filter resource.cluster_name == '{cluster_name}'
        | filter resource.location == '{location}'
        | group_by [value_cpu: mean(value.cpu_usage)]
        | within 5m, d'1m'
        """
        
        # Ejecutar query
        result = monitoring_client.query_time_series(
            name=f"projects/{project_id}",
            query=query
        )
        
        # Procesar resultado
        cpu_used = extract_metric_value(result)
        
        # Repetir para memoria
        query_memory = f"""
        fetch k8s_cluster
        | metric 'kubernetes.io/container/memory/used_bytes'
        | filter resource.project_id == '{project_id}'
        | filter resource.cluster_name == '{cluster_name}'
        | filter resource.location == '{location}'
        | group_by [value_mem: mean(value.memory_used)]
        | within 5m, d'1m'
        """
        
        result_memory = monitoring_client.query_time_series(
            name=f"projects/{project_id}",
            query=query_memory
        )
        
        memory_used = extract_metric_value(result_memory)
        
        return {
            'cpu_used_percent': round(cpu_used, 1),
            'memory_used_percent': round(memory_used, 1)
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de uso para {cluster_name}: {e}")
        return {
            'cpu_used_percent': None,
            'memory_used_percent': None
        }
```

### **Función: `get_compute_usage_metrics()`**

```python
def get_compute_usage_metrics(
    project_id: str,
    instance_name: str,
    zone: str,
    debug: bool = False,
    console = None,
    logger = None
) -> Dict[str, Any]:
    """Obtiene métricas de uso actual de una instancia Compute Engine.
    
    Args:
        project_id: ID del proyecto GCP
        instance_name: Nombre de la instancia
        zone: Zona de la instancia
        debug: Modo debug
        console: Console de Rich
        logger: Logger
        
    Returns:
        {
            'cpu_used_percent': 35.2,
            'memory_used_percent': 58.1,
            'disk_used_percent': 72.3
        }
    """
    try:
        # Inicializar cliente de Monitoring
        monitoring_client = monitoring_v3.MetricServiceClient()
        
        # Query para CPU
        query_cpu = f"""
        fetch gce_instance
        | metric 'compute.googleapis.com/instance/cpu/utilization'
        | filter resource.project_id == '{project_id}'
        | filter resource.instance_id == '{instance_name}'
        | filter resource.zone == '{zone}'
        | group_by [value_cpu: mean(value.utilization)]
        | within 5m, d'1m'
        """
        
        result_cpu = monitoring_client.query_time_series(
            name=f"projects/{project_id}",
            query=query_cpu
        )
        
        cpu_used = extract_metric_value(result_cpu) * 100  # Convertir a porcentaje
        
        # Query para Memoria
        query_memory = f"""
        fetch gce_instance
        | metric 'agent.googleapis.com/memory/percent_used'
        | filter resource.project_id == '{project_id}'
        | filter resource.instance_id == '{instance_name}'
        | filter resource.zone == '{zone}'
        | group_by [value_mem: mean(value.percent_used)]
        | within 5m, d'1m'
        """
        
        result_memory = monitoring_client.query_time_series(
            name=f"projects/{project_id}",
            query=query_memory
        )
        
        memory_used = extract_metric_value(result_memory)
        
        # Query para Disco
        query_disk = f"""
        fetch gce_instance
        | metric 'agent.googleapis.com/disk/percent_used'
        | filter resource.project_id == '{project_id}'
        | filter resource.instance_id == '{instance_name}'
        | filter resource.zone == '{zone}'
        | group_by [value_disk: mean(value.percent_used)]
        | within 5m, d'1m'
        """
        
        result_disk = monitoring_client.query_time_series(
            name=f"projects/{project_id}",
            query=query_disk
        )
        
        disk_used = extract_metric_value(result_disk)
        
        return {
            'cpu_used_percent': round(cpu_used, 1),
            'memory_used_percent': round(memory_used, 1),
            'disk_used_percent': round(disk_used, 1)
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas de uso para {instance_name}: {e}")
        return {
            'cpu_used_percent': None,
            'memory_used_percent': None,
            'disk_used_percent': None
        }
```

---

## 🔄 Integración en Tablas

### **Tabla GKE - Actualización**

```python
# En create_consolidated_detailed_tables()

for cluster in clusters:
    # Obtener capacidad (Fase 1)
    cpu_total = calculate_total_cpu(cluster)
    memory_total = calculate_total_memory(cluster)
    
    # Obtener uso (Fase 2)
    usage_metrics = get_gke_usage_metrics(
        project_id, 
        cluster['name'], 
        cluster['location']
    )
    
    cpu_used = usage_metrics.get('cpu_used_percent', 'N/A')
    memory_used = usage_metrics.get('memory_used_percent', 'N/A')
    
    table.add_row(
        project_id,
        cluster['name'],
        cluster['location'],
        cluster['status'],
        cluster['currentMasterVersion'],
        str(cluster['currentNodeCount']),
        cpu_total,
        memory_total,
        f"{cpu_used}%" if cpu_used != 'N/A' else 'N/A',
        f"{memory_used}%" if memory_used != 'N/A' else 'N/A'
    )
```

### **Tabla Compute - Actualización**

```python
# En create_consolidated_detailed_tables()

for vm in compute_instances:
    # Obtener capacidad (Fase 1)
    machine_type = vm['machineType'].split('/')[-1]
    specs = get_machine_specs(machine_type)
    cpu = specs.get('cpu', 'N/A')
    memory = specs.get('memory', 'N/A')
    disk = get_boot_disk_size(vm)
    
    # Obtener uso (Fase 2)
    usage_metrics = get_compute_usage_metrics(
        project_id,
        vm['name'],
        vm['zone']
    )
    
    cpu_used = usage_metrics.get('cpu_used_percent', 'N/A')
    memory_used = usage_metrics.get('memory_used_percent', 'N/A')
    disk_used = usage_metrics.get('disk_used_percent', 'N/A')
    
    table.add_row(
        project_id,
        vm['name'],
        vm['status'],
        machine_type,
        vm['zone'],
        cpu,
        memory,
        disk,
        f"{cpu_used}%" if cpu_used != 'N/A' else 'N/A',
        f"{memory_used}%" if memory_used != 'N/A' else 'N/A',
        f"{disk_used}%" if disk_used != 'N/A' else 'N/A'
    )
```

---

## ⚙️ Configuración Requerida

### **1. Habilitar Cloud Monitoring API**

```bash
gcloud services enable monitoring.googleapis.com --project=PROJECT_ID
```

### **2. Permisos Requeridos**

```
roles/monitoring.metricReader
```

### **3. Instalar Google Cloud Ops Agent** (para Compute Engine)

```bash
# En cada instancia Compute Engine
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
sudo bash add-google-cloud-ops-agent-repo.sh --also-install
```

### **4. Configurar Monitoring en GKE**

```bash
# Habilitar Monitoring en cluster existente
gcloud container clusters update CLUSTER_NAME \
  --enable-cloud-logging \
  --enable-cloud-monitoring \
  --project=PROJECT_ID
```

---

## 📈 Análisis de Rendimiento

### **Tiempo de Ejecución Estimado**

```
Por cluster GKE: 2-3 segundos (2 métricas)
Por instancia Compute: 3-4 segundos (3 métricas)

Ejemplo: 20 clusters + 100 instancias
├─ Clusters: 20 × 2.5s = 50s
├─ Instancias: 100 × 3.5s = 350s
└─ Total secuencial: 400s

Con paralelismo (max_workers=6):
├─ Clusters paralelos: 50s / 6 ≈ 10s
├─ Instancias paralelos: 350s / 6 ≈ 60s
└─ Total paralelo: ~70s (5.7x más rápido)
```

### **Optimizaciones**

1. **Batch Queries**: Agrupar múltiples métricas en una sola query
2. **Caching**: Cachear resultados por 5 minutos
3. **Paralelismo**: Usar ThreadPoolExecutor con 6 workers
4. **Timeout**: 30 segundos por métrica

---

## 🛡️ Manejo de Errores

### **Casos de Error Comunes**

```python
# 1. Métrica no disponible
if result is None or len(result) == 0:
    return 'N/A'

# 2. Monitoring API no habilitada
except PermissionDenied:
    logger.error("Cloud Monitoring API no habilitada")
    return 'N/A'

# 3. Ops Agent no instalado (Compute)
except NotFound:
    logger.warning(f"Ops Agent no instalado en {instance_name}")
    return 'N/A'

# 4. Timeout
except DeadlineExceeded:
    logger.error(f"Timeout obteniendo métricas de {resource_name}")
    return 'N/A'
```

---

## 📋 Plan de Implementación

### **Fase 2 - Estimado: 6-8 horas**

#### **Paso 1: Crear módulo de Monitoring** (1-2 horas)
- [ ] Crear `gcp_monitoring_metrics.py`
- [ ] Implementar `get_gke_usage_metrics()`
- [ ] Implementar `get_compute_usage_metrics()`
- [ ] Implementar `extract_metric_value()`
- [ ] Agregar manejo de errores

#### **Paso 2: Integración en gcp_monitor.py** (1-2 horas)
- [ ] Importar funciones de métricas
- [ ] Actualizar `get_gke_clusters()` para incluir uso
- [ ] Actualizar `get_compute_instances()` para incluir uso
- [ ] Agregar paralelismo para métricas

#### **Paso 3: Actualizar tablas** (1 hora)
- [ ] Actualizar tabla GKE con columnas de uso
- [ ] Actualizar tabla Compute con columnas de uso
- [ ] Ajustar ancho de columnas
- [ ] Validar formato de salida

#### **Paso 4: Testing y Validación** (1-2 horas)
- [ ] Tests unitarios para funciones de métricas
- [ ] Validación con datos reales
- [ ] Prueba de manejo de errores
- [ ] Documentación de resultados

#### **Paso 5: Documentación** (1 hora)
- [ ] Actualizar README.md
- [ ] Crear PHASE2_IMPLEMENTATION.md
- [ ] Actualizar VERSION a 1.7.2
- [ ] Actualizar README.version.md

---

## 📊 Ejemplo de Salida Esperada

### **Tabla GKE con Fase 2**
```
☸️  Clusters GKE
┌────────────────────┬──────────────────┬──────────┬─────────┬──────────┬──────────────┬───────────────┬───────────────┬───────────────┬───────────────────┐
│ Proyecto           │ Nombre           │ Ubicación│ Estado  │ Versión  │ Nodos │ CPU Total │ Memoria Total │ CPU Usado (%) │ Memoria Usada (%) │
├────────────────────┼──────────────────┼──────────┼─────────┼──────────┼──────────────┼───────────────┼───────────────┼───────────────┼───────────────────┤
│ cpl-cs-wms-dev     │ gke-cs-wms-dev-01│ us-cent-1│ RUNNING │ 1.34.8   │    16 │  64 vCPU  │    256 GB     │      45.2%    │       62.1%       │
│ cpl-cs-wms-qa      │ gke-cs-wms-qa-01 │ us-cent-1│ RUNNING │ 1.34.8   │    15 │  60 vCPU  │    240 GB     │      38.7%    │       51.3%       │
└────────────────────┴──────────────────┴──────────┴─────────┴──────────┴──────────────┴───────────────┴───────────────┴───────────────┴───────────────────┘
```

### **Tabla Compute con Fase 2**
```
💻 Instancias Compute Engine
┌────────────────────┬──────────────────┬─────────┬──────────────┬──────┬─────────┬────────────┬───────────────┬───────────────────┬─────────────────┐
│ Proyecto           │ Nombre           │ Estado  │ Tipo         │ CPUs │ Memoria │ Disco Raíz │ CPU Usado (%) │ Memoria Usada (%) │ Disco Usado (%) │
├────────────────────┼──────────────────┼─────────┼──────────────┼──────┼─────────┼────────────┼───────────────┼───────────────────┼─────────────────┤
│ cpl-cs-wms-dev     │ instance-01      │ RUNNING │ n2d-std-4    │    4 │  16 GB  │   100 GB   │      35.2%    │       58.1%       │      72.3%      │
│ cpl-cs-wms-qa      │ instance-02      │ RUNNING │ n2d-std-8    │    8 │  32 GB  │   200 GB   │      42.1%    │       65.4%       │      81.2%      │
└────────────────────┴──────────────────┴─────────┴──────────────┴──────┴─────────┴────────────┴───────────────┴───────────────────┴─────────────────┘
```

---

## ✅ Checklist de Implementación

- [ ] Cloud Monitoring API habilitada en todos los proyectos
- [ ] Google Cloud Ops Agent instalado en instancias Compute
- [ ] Módulo `gcp_monitoring_metrics.py` creado
- [ ] Funciones de métricas implementadas
- [ ] Integración en `gcp_monitor.py` completada
- [ ] Tablas actualizadas con columnas de uso
- [ ] Tests unitarios creados
- [ ] Validación con datos reales
- [ ] Documentación actualizada
- [ ] Versión actualizada a 1.7.2
- [ ] Commits realizados

---

## 📝 Notas Importantes

1. **Requisitos Previos**:
   - Cloud Monitoring API debe estar habilitada
   - Ops Agent debe estar instalado en Compute Engine
   - Permisos de lectura en Monitoring

2. **Limitaciones**:
   - Las métricas pueden no estar disponibles inmediatamente después de crear recursos
   - Algunos tipos de máquinas personalizadas pueden no reportar todas las métricas
   - Datos históricos limitados a 30 días

3. **Optimizaciones Futuras**:
   - Implementar caching de 5 minutos
   - Agregar alertas automáticas
   - Crear gráficos de tendencias
   - Integración con BigQuery para análisis histórico

---

**Fase 2 - Estado**: 📋 PLANIFICADA  
**Estimado**: 6-8 horas  
**Prioridad**: ALTA (mejora significativa en visibilidad operacional)
