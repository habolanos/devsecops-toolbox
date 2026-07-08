# 🔍 GCP Deployments Off Analyzer (Tool 40)

**Versión:** 1.0.0  
**Objetivo:** Analizar deployments no running en GKE con diagnóstico automático

---

## 📋 Descripción

Herramienta que identifica y diagnostica automáticamente todos los deployments en estado no running en un cluster GKE de Google Cloud Platform, proporcionando:

- ✅ Listado completo de deployments con replicas no ready
- ✅ Análisis automático de causa raíz
- ✅ Logs de eventos del cluster y pods
- ✅ Recomendaciones de remediación
- ✅ Exportación en múltiples formatos (JSON, CSV)

---

## 🚀 Uso

### Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt
```

### Ejecución Básica

```bash
# Analizar todos los deployments no running
python gcp_deployments_off_analyzer.py --project my-project --cluster my-cluster

# Analizar namespace específico
python gcp_deployments_off_analyzer.py --project my-project --cluster my-cluster --namespace production

# Exportar a JSON
python gcp_deployments_off_analyzer.py --project my-project --cluster my-cluster -o json

# Exportar a CSV
python gcp_deployments_off_analyzer.py --project my-project --cluster my-cluster -o csv

# Modo debug
python gcp_deployments_off_analyzer.py --project my-project --cluster my-cluster --debug
```

### Argumentos

```
--project PROJECT_ID          ID del proyecto GCP (requerido)
--cluster CLUSTER_NAME        Nombre del cluster GKE (requerido)
--namespace NAMESPACE         Namespace específico (opcional)
-o, --output FORMAT          Formato: json, csv (default: json)
--output-file FILE           Archivo de salida (opcional)
--debug                      Modo debug (opcional)
```

---

## 📊 Salida

### Tabla de Resultados

```
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Namespace  ┃ Deployment    ┃ Severity ┃ Des.. ┃ Rdy ┃ Root Cause         ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ production │ api-server    │ CRITICAL │ 3     │ 0   │ CrashLoopBackOff   │
│ production │ web-frontend  │ HIGH     │ 2     │ 0   │ ImagePullBackOff   │
│ default    │ test-app      │ HIGH     │ 1     │ 0   │ Pending            │
└────────────┴───────────────┴──────────┴───────┴─────┴────────────────────┘
```

### JSON Format

```json
{
  "timestamp": "2026-07-08T15:30:00",
  "total_deployments": 3,
  "critical_count": 1,
  "high_count": 2,
  "deployments": [
    {
      "namespace": "production",
      "deployment": "api-server",
      "severity": "CRITICAL",
      "replica_status": {
        "desired": 3,
        "ready": 0,
        "updated": 0,
        "available": 0
      },
      "root_causes": [
        {
          "type": "CrashLoopBackOff",
          "category": "Application Error",
          "message": "Back-off restarting failed container",
          "source": "Event"
        }
      ],
      "recommendations": [
        {
          "action": "Analizar logs de aplicación",
          "priority": "CRITICAL",
          "steps": [
            "Ejecutar: kubectl logs POD_NAME -n NAMESPACE",
            "Revisar logs del pod para errores",
            "Verificar configuración de aplicación",
            "Validar variables de entorno",
            "Revisar health checks (liveness/readiness probes)",
            "Considerar aumentar initialDelaySeconds"
          ]
        }
      ]
    }
  ]
}
```

---

## 🔍 Problemas Detectados

| Problema | Causa | Solución |
|----------|-------|----------|
| **ImagePullBackOff** | Imagen no existe o credenciales inválidas | Verificar registry y credenciales |
| **CrashLoopBackOff** | Aplicación se reinicia continuamente | Revisar logs y configuración |
| **Pending** | Recursos insuficientes | Escalar cluster o revisar requests |
| **CreateContainerConfigError** | Configuración inválida | Verificar Secrets/ConfigMaps |
| **ImagePullError** | Imagen no encontrada | Verificar nombre de imagen |
| **FailedScheduling** | No hay nodos disponibles | Escalar cluster |

---

## 📈 Casos de Uso

### Incident Response
```bash
# Cuando hay alerta de deployment no running
python gcp_deployments_off_analyzer.py --project prod --cluster prod-gke --debug
```

### Pre-Deploy Validation
```bash
# Antes de deployment
python gcp_deployments_off_analyzer.py --project prod --cluster prod-gke -o json
```

### Auditoría Semanal
```bash
# Exportar para análisis
python gcp_deployments_off_analyzer.py --project prod --cluster prod-gke -o csv --output-file weekly_audit.csv
```

---

## 🔐 Requisitos de Acceso

### RBAC Permissions
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: deployments-off-analyzer
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods", "events"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]
```

### GCP Permissions
- `container.clusters.get`
- `container.clusters.list`
- `logging.logEntries.list` (opcional)

---

## 🧪 Testing

```bash
# Test básico
python gcp_deployments_off_analyzer.py --project test-project --cluster test-cluster

# Test con namespace específico
python gcp_deployments_off_analyzer.py --project test-project --cluster test-cluster --namespace default

# Test con exportación
python gcp_deployments_off_analyzer.py --project test-project --cluster test-cluster -o json --output-file test_output.json
```

---

## 📝 Notas

- La herramienta requiere acceso a un cluster GKE válido
- Los logs se exportan a `outcome/` por defecto
- El análisis puede tomar más tiempo en clusters grandes
- Se recomienda usar namespaces específicos para análisis rápidos

---

**Tool 40: GCP Deployments Off Analyzer** ✅
