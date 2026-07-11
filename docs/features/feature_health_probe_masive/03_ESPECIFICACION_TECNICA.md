# 🔧 Especificación Técnica - Health Probe Masivo

**Versión:** 1.0  
**Fecha:** 10 de Julio de 2026  
**Nivel de Detalle:** Profesional

---

## 📐 Arquitectura de Módulos

### 1. `models.py` - Dataclasses

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class DeploymentInput:
    """Entrada de usuario"""
    name: str
    definition_id: Optional[int] = None
    namespace: str = "default"
    cluster: str = "prod"

@dataclass
class StageInfo:
    """Información de stage en AZDO"""
    name: str
    definition_id: int
    target_deployment: str
    target_namespace: str
    endpoints: List[str]
    ports: List[int]
    environment: str  # Dev, QA, Staging, Prod

@dataclass
class DeploymentStatus:
    """Estado de deployment en K8s"""
    name: str
    namespace: str
    replicas: int
    ready_replicas: int
    updated_replicas: int
    available_replicas: int
    
    @property
    def status(self) -> str:
        if self.ready_replicas == self.replicas:
            return "Ready"
        elif self.ready_replicas > 0:
            return "Partial"
        else:
            return "NotReady"

@dataclass
class PodStatus:
    """Estado de pod individual"""
    name: str
    namespace: str
    status: str  # Running, Pending, Failed, Unknown
    ready_containers: int
    total_containers: int
    restart_count: int
    age_seconds: int

@dataclass
class ProbeStatus:
    """Estado de health probes"""
    liveness_configured: bool
    liveness_type: Optional[str]  # HTTP, TCP, Exec
    liveness_timeout: int
    liveness_period: int
    readiness_configured: bool
    readiness_type: Optional[str]
    readiness_timeout: int
    readiness_period: int
    startup_configured: bool
    
    @property
    def is_healthy(self) -> bool:
        return (
            self.liveness_configured and
            self.readiness_configured and
            self.liveness_timeout >= 5 and
            self.readiness_timeout >= 5
        )

@dataclass
class TestResult:
    """Resultado de prueba de conectividad"""
    host: str
    port: int
    protocol: str  # tcp, http, https
    success: bool
    latency_ms: float
    timeout: bool
    status_code: Optional[int] = None
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class HealthCheckResult:
    """Resultado consolidado de validación"""
    deployment: str
    stage: str
    pod_status: str  # Ready, Partial, NotReady
    pod_count: int
    ready_count: int
    liveness_probe: bool
    readiness_probe: bool
    connectivity: str  # OK, FAILED, TIMEOUT
    latency_ms: float
    last_updated: datetime
    errors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def overall_status(self) -> str:
        if self.pod_status == "Ready" and self.connectivity == "OK":
            return "✅ HEALTHY"
        elif self.pod_status == "Partial" or self.connectivity == "TIMEOUT":
            return "⚠️ WARNING"
        else:
            return "❌ CRITICAL"
```

---

## 🔌 API Specifications

### AZDO API Integration

```python
class AzDOClient:
    """Cliente para Azure DevOps REST API"""
    
    BASE_URL = "https://dev.azure.com"
    API_VERSION = "7.1"
    
    def __init__(self, org: str, project: str, pat: str):
        self.org = org
        self.project = project
        self.pat = pat
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Crea sesión autenticada"""
        session = requests.Session()
        auth = HTTPBasicAuth("", self.pat)
        session.auth = auth
        return session
    
    def get_release_definition(self, definition_id: int) -> dict:
        """
        GET /_apis/release/definitions/{definitionId}
        
        Response:
        {
            "id": 3388,
            "name": "Release-Cadena-Suministros",
            "environments": [
                {
                    "id": 1,
                    "name": "Dev",
                    "deploymentInput": {...}
                },
                {
                    "id": 2,
                    "name": "QA",
                    "deploymentInput": {...}
                }
            ]
        }
        """
        url = f"{self.BASE_URL}/{self.org}/{self.project}/_apis/release/definitions/{definition_id}"
        params = {"api-version": self.API_VERSION}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_releases(self, definition_id: int, top: int = 10) -> List[dict]:
        """
        GET /_apis/release/releases
        
        Parámetros:
        - definitionId: ID de definición
        - $top: Número de releases a retornar
        """
        url = f"{self.BASE_URL}/{self.org}/{self.project}/_apis/release/releases"
        params = {
            "api-version": self.API_VERSION,
            "definitionId": definition_id,
            "$top": top
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()["value"]
```

### Kubernetes API Integration

```python
class K8sClient:
    """Cliente para Kubernetes API"""
    
    def __init__(self, kubeconfig_path: str = None):
        config.load_kube_config(kubeconfig_path)
        self.apps_v1 = client.AppsV1Api()
        self.v1 = client.CoreV1Api()
    
    def get_deployment(self, name: str, namespace: str) -> V1Deployment:
        """
        GET /apis/apps/v1/namespaces/{namespace}/deployments/{name}
        """
        return self.apps_v1.read_namespaced_deployment(name, namespace)
    
    def list_pods(self, namespace: str, label_selector: str) -> List[V1Pod]:
        """
        GET /api/v1/namespaces/{namespace}/pods
        """
        return self.v1.list_namespaced_pod(
            namespace,
            label_selector=label_selector
        ).items
    
    def read_pod(self, name: str, namespace: str) -> V1Pod:
        """
        GET /api/v1/namespaces/{namespace}/pods/{name}
        """
        return self.v1.read_namespaced_pod(name, namespace)
    
    def read_pod_log(self, name: str, namespace: str, tail_lines: int = 50) -> str:
        """
        GET /api/v1/namespaces/{namespace}/pods/{name}/log
        """
        return self.v1.read_namespaced_pod_log(
            name,
            namespace,
            tail_lines=tail_lines
        )
```

---

## 🔄 Flujos de Procesamiento

### Flujo Principal

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INPUT: CSV de deployments/definitionIds                 │
│    "deployment-web-prod,deployment-api-prod"               │
│    o "definitionId=3388,definitionId=3389"                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 2. PARSE INPUT                                              │
│    - Validar formato                                        │
│    - Extraer nombres/IDs                                    │
│    - Normalizar                                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 3. AZDO PARSER (Paralelo, 5 workers)                        │
│    Para cada deployment/definition:                         │
│    - Obtener definición de release                          │
│    - Extraer stages (Dev, QA, Staging, Prod)               │
│    - Mapear targets de deployment                           │
│    - Obtener endpoints y puertos                            │
│    - Cachear por 24h                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 4. K8S CHECKER (Paralelo, 5 workers)                        │
│    Para cada deployment:                                    │
│    - Verificar existencia                                   │
│    - Obtener estado (replicas, ready)                       │
│    - Listar pods                                            │
│    - Validar health probes                                  │
│    - Obtener logs de errores                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 5. CONNECTIVITY TESTER (Paralelo, 5 workers)                │
│    Para cada endpoint:                                      │
│    - Crear pod de verificación                              │
│    - Probar conectividad (curl, nc)                         │
│    - Medir latencia                                         │
│    - Validar DNS                                            │
│    - Limpiar pod                                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 6. CONSOLIDATION                                            │
│    - Combinar resultados                                    │
│    - Generar recomendaciones                                │
│    - Calcular scores                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 7. REPORTER                                                 │
│    - Tabla Rich (consola)                                   │
│    - JSON (APIs)                                            │
│    - CSV (Excel)                                            │
│    - HTML (reportes)                                        │
│    - Excel (ejecutivos)                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Manejo de Errores

### Estrategia de Reintentos

```python
def retry_with_backoff(func, max_retries=3, backoff_factor=2):
    """
    Reintentos exponenciales
    
    Intento 1: Inmediato
    Intento 2: 2 segundos
    Intento 3: 4 segundos
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = backoff_factor ** attempt
            time.sleep(wait_time)
```

### Fallbacks

```python
# Si AZDO API falla, intentar kubectl
try:
    stages = azdo_parser.get_stages(definition_id)
except Exception:
    logger.warning(f"AZDO API failed, using kubectl fallback")
    stages = k8s_checker.get_stages_from_labels(deployment_name)

# Si K8s API falla, usar kubectl CLI
try:
    pods = k8s_client.list_pods(namespace, label_selector)
except Exception:
    logger.warning(f"K8s API failed, using kubectl CLI")
    pods = subprocess.run(["kubectl", "get", "pods", ...])
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Niveles:
# DEBUG: Detalles de ejecución
# INFO: Eventos importantes
# WARNING: Problemas potenciales
# ERROR: Errores que no detienen ejecución
# CRITICAL: Errores que detienen ejecución

logger.debug(f"Testing endpoint {host}:{port}")
logger.info(f"Deployment {name} is healthy")
logger.warning(f"Pod {pod_name} has high restart count: {count}")
logger.error(f"Failed to connect to {host}:{port}")
logger.critical(f"AZDO authentication failed")
```

---

## 🔐 Seguridad

### Credenciales

```python
# ✅ CORRECTO: Variables de entorno
azdo_pat = os.getenv("AZDO_PAT")
kubeconfig = os.getenv("KUBECONFIG")

# ❌ INCORRECTO: Hardcoding
azdo_pat = "abc123xyz"  # ¡NUNCA!
```

### RBAC en Kubernetes

```yaml
# Crear ServiceAccount con permisos mínimos
apiVersion: v1
kind: ServiceAccount
metadata:
  name: health-probe-validator
  namespace: default

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: health-probe-validator
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: health-probe-validator
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: health-probe-validator
subjects:
- kind: ServiceAccount
  name: health-probe-validator
  namespace: default
```

---

## 📊 Tabla de Salida

### Columnas

| Columna | Tipo | Descripción |
|---------|------|-------------|
| Deployment | str | Nombre del deployment |
| Stage | str | Nombre del stage (Dev, QA, Prod) |
| Pod Status | str | Estado de pods (Ready, Partial, NotReady) |
| Probes | str | Estado de health probes (✅, ⚠️, ❌) |
| Conectividad | str | Estado de conectividad (OK, TIMEOUT, FAILED) |
| Latencia | float | Latencia promedio en ms |
| Última Actualización | datetime | Timestamp de validación |
| Recomendaciones | str | Acciones sugeridas |

### Ejemplo de Tabla

```
┌──────────────────┬────────┬────────────┬──────────┬──────────────┬─────────┬──────────────────┬──────────────────────┐
│ Deployment       │ Stage  │ Pod Status │ Probes   │ Conectividad │ Latencia│ Última Actualiz. │ Recomendaciones      │
├──────────────────┼────────┼────────────┼──────────┼──────────────┼─────────┼──────────────────┼──────────────────────┤
│ web-prod         │ Prod   │ 3/3 Ready  │ ✅ OK    │ ✅ OK        │ 45ms    │ 2026-07-10 22:30 │ Ninguna              │
│ api-prod         │ Prod   │ 2/3 Ready  │ ⚠️ Warn  │ ⚠️ Timeout   │ 5000ms  │ 2026-07-10 22:31 │ Revisar logs         │
│ db-prod          │ Prod   │ 1/1 Ready  │ ✅ OK    │ ✅ OK        │ 12ms    │ 2026-07-10 22:32 │ Ninguna              │
│ cache-prod       │ Prod   │ 0/2 Ready  │ ❌ Error │ ❌ Failed    │ N/A     │ 2026-07-10 22:33 │ Escalar pod, revisar │
└──────────────────┴────────┴────────────┴──────────┴──────────────┴─────────┴──────────────────┴──────────────────────┘
```

---

## 🧪 Casos de Prueba

### Unit Tests

```python
# test_models.py
def test_deployment_status_ready():
    status = DeploymentStatus(name="web", namespace="prod", 
                              replicas=3, ready_replicas=3, ...)
    assert status.status == "Ready"

def test_probe_status_healthy():
    probes = ProbeStatus(liveness_configured=True, readiness_configured=True, ...)
    assert probes.is_healthy == True

# test_azdo_parser.py
def test_parse_input_csv():
    input_str = "deployment-web,deployment-api"
    result = parse_input(input_str)
    assert len(result) == 2
    assert result[0].name == "deployment-web"

def test_parse_input_definition_ids():
    input_str = "definitionId=3388,definitionId=3389"
    result = parse_input(input_str)
    assert len(result) == 2
    assert result[0].definition_id == 3388

# test_k8s_checker.py
def test_check_deployment_exists():
    checker = K8sChecker()
    status = checker.check_deployment("web", "prod")
    assert status.name == "web"

def test_check_health_probes():
    checker = K8sChecker()
    probes = checker.check_health_probes("web-abc123", "prod")
    assert probes.liveness_configured in [True, False]

# test_connectivity_tester.py
def test_test_endpoint_success():
    tester = ConnectivityTester()
    result = tester.test_endpoint("google.com", 443, "https")
    assert result.success == True
    assert result.latency_ms > 0

def test_test_endpoint_timeout():
    tester = ConnectivityTester()
    result = tester.test_endpoint("10.255.255.1", 80, "tcp")
    assert result.timeout == True
```

### Integration Tests

```python
# test_integration.py
def test_full_workflow():
    """Test completo end-to-end"""
    validator = HealthProbeValidator(azdo_pat, kubeconfig)
    results = validator.validate_deployments("deployment-web-prod")
    
    assert len(results) > 0
    assert results[0].deployment == "deployment-web-prod"
    assert results[0].overall_status in ["✅ HEALTHY", "⚠️ WARNING", "❌ CRITICAL"]
```

---

## 📈 Métricas de Rendimiento

### Objetivos

| Métrica | Objetivo | Aceptable |
|---------|----------|-----------|
| Tiempo por deployment | < 30 segundos | < 60 segundos |
| Tiempo total (10 deployments) | < 5 minutos | < 10 minutos |
| Tiempo total (100 deployments) | < 20 minutos | < 30 minutos |
| Cobertura de tests | 85%+ | 75%+ |
| Latencia de tabla | < 2 segundos | < 5 segundos |

### Monitoreo

```python
import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper

@measure_time
def validate_deployment(deployment):
    # ...
```

---

**Especificación Técnica - COMPLETA** ✅
