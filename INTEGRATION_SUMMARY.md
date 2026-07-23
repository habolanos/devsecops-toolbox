# 📋 Integración: GKE Cluster Memory & CPU Limits Analyzer

**Fecha:** 22 de Julio de 2026  
**Versión:** 1.7.2  
**Status:** ✅ COMPLETADO

---

## 🎯 Objetivo

Integrar el programa de análisis de límites de recursos Kubernetes en el menú principal de `terminal/tools.py` para facilitar su ejecución desde la interfaz centralizada.

---

## 📊 Cambios Realizados

### 1. **Refactorización de Directorio**
```
Antes:  scm/terminal/limits/
Después: scm/terminal/check_cluster_memory_cpu_limits/
```

**Razón:** Nombre más descriptivo y consistente con la función del programa.

### 2. **Integración en terminal/tools.py**

Agregada opción **7** al menú de scripts:

```python
"7": {
    "name": "GKE Cluster Memory & CPU Limits Analyzer",
    "description": "Analiza y recomienda límites de CPU y memoria en clústeres GKE basado en métricas de 90 días. Genera reporte Excel con recomendaciones. IMPORTANTE: Configurar clústeres en check_cluster_memory_cpu_limits/config.env antes de ejecutar.",
    "path": "check_cluster_memory_cpu_limits/deployments_info.sh",
    "args": [],
    "status": "ready",
    "type": "shell"
}
```

### 3. **Características de la Integración**

✅ **Menú Interactivo**
- Opción 7 visible en el menú principal
- Descripción clara con instrucciones
- Indicador de estado: 🟢 (ready)

✅ **Validación Automática**
- Verifica existencia del script
- Detecta plataforma (Windows/Linux)
- Muestra advertencia en Windows

✅ **Documentación Integrada**
- Descripción menciona el archivo `config.env`
- Instrucciones claras en la opción

---

## 📁 Estructura Final

```
scm/terminal/
├── tools.py                          (Menú principal)
├── check_cluster_memory_cpu_limits/  (Nueva carpeta)
│   ├── README.md                     (Documentación)
│   ├── config.env                    (Configuración - EDITAR ANTES)
│   ├── config.env.template           (Plantilla)
│   ├── deployments_info.sh           (Script orquestador)
│   └── history_limits_v3.py          (Motor de análisis)
├── check-certificate-report.sh
├── db-connections-checker.sh
├── deployments-last-news.sh
├── deployments-last-update.sh
├── deployments-recent-events.sh
└── k8s-deploy-manifest-diff.sh
```

---

## 🚀 Cómo Usar

### **Desde el Menú Principal**

```bash
cd ~/repos-publics/devsecops-toolbox

# Ejecutar el launcher
python scm/main.py

# Seleccionar opción: terminal/tools.py
# Luego seleccionar opción: 7
```

### **Paso a Paso**

1. **Ejecutar menú:**
   ```bash
   python scm/main.py
   ```

2. **Seleccionar "Terminal Tools"** (opción del menú principal)

3. **Ver menú de scripts:**
   ```
   [7] 🟢 GKE Cluster Memory & CPU Limits Analyzer
       Analiza y recomienda límites de CPU y memoria...
   ```

4. **Seleccionar opción 7**

5. **Configurar clústeres** (si no está hecho):
   - Editar: `scm/terminal/check_cluster_memory_cpu_limits/config.env`
   - Agregar clústeres GKE a analizar

6. **Ejecutar análisis:**
   - El script se ejecutará automáticamente
   - Mostrará barra de progreso
   - Generará reportes Excel

---

## 📝 Configuración Requerida

Antes de ejecutar, editar:
```bash
scm/terminal/check_cluster_memory_cpu_limits/config.env
```

Agregar clústeres GKE:
```bash
CLUSTERS=(
  "gke_PROJECT_ID_REGION_CLUSTER_NAME"
  "gke_PROJECT_ID_REGION_CLUSTER_NAME"
)
```

**Ejemplo:**
```bash
CLUSTERS=(
  "gke_cpl-cs-wms-qa-30112023_us-central1_gke-cs-wms-qa-01"
  "gke_cpl-cs-wms-qa-30112023_us-central1_gke-cs-wms-qa-02"
)
```

---

## 📊 Características del Programa

### **Análisis**
- ✅ Período: 90 días de métricas
- ✅ Métricas: CPU (millicores), Memoria (MiB)
- ✅ Percentiles: p95, p99, promedio, min, max
- ✅ Desglose: Memoria evictable vs non-evictable

### **Recomendaciones**
- ✅ CPU request: max(promedio × 1.2, p95)
- ✅ CPU limit: p99 × 1.5
- ✅ Memoria request: max(promedio × 1.2, p95)
- ✅ Memoria limit: p99 × 1.4

### **Salida**
- ✅ Reporte Excel: `reporte_recursos_<CLUSTER>.xlsx`
- ✅ Barra de progreso en tiempo real
- ✅ Logging detallado
- ✅ ETA de ejecución

---

## ⏱️ Tiempo Estimado

| Métrica | Tiempo |
|---------|--------|
| Por clúster | 3-5 minutos |
| 3 clústeres | 9-15 minutos |
| Timeout máximo | 60 minutos |

---

## 📋 Commits Realizados

```
a993fa3 - refactor: Renombrar directorio limits a check_cluster_memory_cpu_limits
7d8af01 - feat: Agregar opción 7 - GKE Cluster Memory & CPU Limits Analyzer a terminal/tools.py
```

---

## 🔍 Validación

✅ **Script existe:** `check_cluster_memory_cpu_limits/deployments_info.sh`  
✅ **Configuración:** `config.env` presente  
✅ **Documentación:** README.md completo  
✅ **Integración:** Opción 7 en terminal/tools.py  
✅ **Descripción:** Menciona archivo config.env  
✅ **Status:** Ready (🟢)

---

## 📚 Documentación Relacionada

- `scm/terminal/check_cluster_memory_cpu_limits/README.md` - Guía completa
- `scm/terminal/tools.py` - Menú principal
- `scm/main.py` - Launcher principal

---

## 🎯 Próximos Pasos

1. ✅ Usuario edita `config.env` con sus clústeres
2. ✅ Usuario ejecuta desde menú principal
3. ✅ Sistema genera reportes Excel
4. ✅ Usuario revisa recomendaciones
5. ✅ Usuario aplica cambios en Deployments

---

**Status:** ✅ INTEGRACIÓN COMPLETADA  
**Listo para:** Uso inmediato  
**Versión:** 1.7.2
