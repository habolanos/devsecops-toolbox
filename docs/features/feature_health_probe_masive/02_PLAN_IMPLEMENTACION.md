# 📋 Plan de Implementación - Health Probe Masivo

**Versión:** 1.0  
**Fecha:** 10 de Julio de 2026  
**Duración Estimada:** 40 horas (5 días, tiempo completo)  
**Equipo:** 1 DevOps Engineer

---

## 🎯 Objetivos

1. ✅ Crear herramienta de validación masiva de health probes
2. ✅ Integrar con Azure DevOps para mapeo de stages
3. ✅ Validar conectividad usando pod de verificación
4. ✅ Generar reportería ejecutiva
5. ✅ Documentar y testear completamente

---

## 📅 Cronograma (5 Fases)

### Fase 1: Preparación (4 horas)
**Días 1-2 (Mañana)**

#### 1.1 Estructura de Directorios
```bash
scm/azdo/health-probe-masive/
├── __init__.py
├── health_probe_validator.py      # Orquestador principal
├── azdo_parser.py                 # Parser de AZDO
├── k8s_checker.py                 # Validador de K8s
├── connectivity_tester.py         # Tester de conectividad
├── reporter.py                    # Generador de reportes
├── models.py                      # Dataclasses
├── config.py                      # Configuración
└── requirements.txt
```

#### 1.2 Dependencias
```
azure-devops==7.1.0
kubernetes==28.0.0
requests==2.31.0
pandas==2.0.0
openpyxl==3.1.0
rich==13.5.0
pyyaml==6.0
```

#### 1.3 Configuración Inicial
```python
# config.py
AZDO_ORG = "Coppel-Retail"
AZDO_PROJECT = "Cadena_de_Suministros"
AZDO_API_VERSION = "7.1"
K8S_NAMESPACES = ["default", "production", "staging"]
CONNECTIVITY_POD_IMAGE = "nicolaka/netshoot:latest"
CACHE_TTL = 86400  # 24 horas
MAX_WORKERS = 5
TIMEOUT = 30  # segundos
```

---

### Fase 2: Desarrollo - AZDO Parser (8 horas)
**Días 2-3 (Tarde - Día 3 Mañana)**

#### 2.1 AzDO Parser (`azdo_parser.py`)
```python
class AzDOParser:
    """
    Extrae información de releases y stages desde AZDO
    """
    
    def __init__(self, org, project, pat):
        self.client = DevOpsClient(org, project, pat)
    
    def get_release_definition(self, definition_id: int) -> ReleaseDefinition:
        """Obtiene definición de release"""
        # GET /_apis/release/definitions/{id}
        # Retorna: nombre, stages, artifacts
    
    def get_stages(self, definition_id: int) -> List[StageInfo]:
        """Extrae stages y sus targets"""
        # Para cada stage:
        #   - Nombre (Dev, QA, Staging, Prod)
        #   - Deployment target
        #   - Namespace K8s
        #   - Endpoints
        #   - Puertos
    
    def get_stage_deployments(self, stage_name: str) -> List[str]:
        """Obtiene deployments de un stage"""
        # Parsea la definición para encontrar
        # qué deployments se usan en cada stage
    
    def cache_definition(self, definition_id: int):
        """Cachea definición por 24h"""
        # Almacenar en outcome/cache/azdo_{id}.json
```

#### 2.2 Entrada de Datos
```python
def parse_input(input_str: str) -> List[DeploymentInput]:
    """
    Parsea entrada CSV
    
    Ejemplos:
      "deployment-web-prod,deployment-api-prod"
      "definitionId=3388,definitionId=3389"
      "3388,3389,3390"
    """
    items = input_str.split(",")
    results = []
    
    for item in items:
        if item.startswith("definitionId="):
            def_id = int(item.split("=")[1])
            results.append(DeploymentInput(
                definition_id=def_id,
                name=f"release_{def_id}"
            ))
        else:
            results.append(DeploymentInput(name=item.strip()))
    
    return results
```

#### 2.3 Tests
```python
# test_azdo_parser.py
def test_get_release_definition():
    """Valida extracción de definición"""
    
def test_get_stages():
    """Valida extracción de stages"""
    
def test_parse_input():
    """Valida parsing de entrada"""
```

---

### Fase 3: Desarrollo - K8s Checker (10 horas)
**Días 3-4 (Tarde - Día 4 Completo)**

#### 3.1 K8s Checker (`k8s_checker.py`)
```python
class K8sChecker:
    """
    Valida deployments en Kubernetes
    """
    
    def __init__(self, kubeconfig_path: str = None):
        self.client = kubernetes.client.AppsV1Api()
        self.v1 = kubernetes.client.CoreV1Api()
    
    def check_deployment(self, name: str, namespace: str) -> DeploymentStatus:
        """Valida estado de deployment"""
        # kubectl get deployment {name} -n {namespace}
        # Retorna: replicas, ready, updated, available
    
    def check_pods(self, deployment: str, namespace: str) -> List[PodStatus]:
        """Valida estado de pods"""
        # kubectl get pods -l app={deployment} -n {namespace}
        # Para cada pod:
        #   - Estado (Running, Pending, Failed)
        #   - Ready containers
        #   - Restart count
    
    def check_health_probes(self, pod: str, namespace: str) -> ProbeStatus:
        """Valida health probes configurados"""
        # kubectl describe pod {pod} -n {namespace}
        # Extrae:
        #   - Liveness probe (tipo, timeout, period)
        #   - Readiness probe (tipo, timeout, period)
        #   - Startup probe (si existe)
    
    def get_pod_logs(self, pod: str, namespace: str, lines: int = 50) -> str:
        """Obtiene logs del pod"""
        # kubectl logs {pod} -n {namespace} --tail={lines}
    
    def get_pod_events(self, pod: str, namespace: str) -> List[Event]:
        """Obtiene eventos del pod"""
        # kubectl describe pod {pod} -n {namespace}
        # Extrae sección Events
```

#### 3.2 Validación de Probes
```python
@dataclass
class ProbeStatus:
    liveness_configured: bool
    liveness_type: str  # HTTP, TCP, Exec
    liveness_timeout: int
    readiness_configured: bool
    readiness_type: str
    readiness_timeout: int
    startup_configured: bool
    
    @property
    def is_healthy(self) -> bool:
        """Determina si probes están bien configurados"""
        return (
            self.liveness_configured and
            self.readiness_configured and
            self.liveness_timeout >= 5 and
            self.readiness_timeout >= 5
        )
```

#### 3.3 Tests
```python
# test_k8s_checker.py
def test_check_deployment():
    """Valida estado de deployment"""
    
def test_check_pods():
    """Valida estado de pods"""
    
def test_check_health_probes():
    """Valida extracción de probes"""
```

---

### Fase 4: Desarrollo - Connectivity Tester (12 horas)
**Días 4-5 (Tarde - Día 5 Completo)**

#### 4.1 Connectivity Tester (`connectivity_tester.py`)
```python
class ConnectivityTester:
    """
    Prueba conectividad usando pod de verificación
    """
    
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.pod_name = "connectivity-checker"
        self.image = "nicolaka/netshoot:latest"
    
    def create_test_pod(self) -> bool:
        """Crea pod de verificación"""
        # kubectl run connectivity-checker --image=nicolaka/netshoot
        # Espera a que esté Running
    
    def test_endpoint(self, host: str, port: int, protocol: str = "tcp") -> TestResult:
        """Prueba conectividad a endpoint"""
        # kubectl exec {pod} -- curl -v http://{host}:{port}
        # kubectl exec {pod} -- nc -zv {host} {port}
        # Mide latencia y timeout
    
    def test_dns(self, hostname: str) -> bool:
        """Valida resolución DNS"""
        # kubectl exec {pod} -- dig {hostname}
    
    def test_routing(self, host: str) -> List[str]:
        """Prueba routing"""
        # kubectl exec {pod} -- traceroute {host}
    
    def cleanup_test_pod(self):
        """Elimina pod de verificación"""
        # kubectl delete pod connectivity-checker
```

#### 4.2 Medición de Latencia
```python
@dataclass
class TestResult:
    host: str
    port: int
    protocol: str
    success: bool
    latency_ms: float
    timeout: bool
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def status(self) -> str:
        if self.timeout:
            return "TIMEOUT"
        elif self.success:
            return "OK"
        else:
            return "FAILED"
```

#### 4.3 Procesamiento Paralelo
```python
def test_all_endpoints(endpoints: List[Endpoint]) -> List[TestResult]:
    """Prueba múltiples endpoints en paralelo"""
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(test_endpoint, ep.host, ep.port)
            for ep in endpoints
        ]
        return [f.result() for f in futures]
```

#### 4.4 Tests
```python
# test_connectivity_tester.py
def test_create_test_pod():
    """Valida creación de pod"""
    
def test_endpoint_connectivity():
    """Valida prueba de conectividad"""
    
def test_latency_measurement():
    """Valida medición de latencia"""
```

---

### Fase 5: Reportería y Finalización (6 horas)
**Día 5 (Tarde)**

#### 5.1 Reporter (`reporter.py`)
```python
class HealthProbeReporter:
    """
    Genera reportes de validación
    """
    
    def __init__(self, results: List[HealthCheckResult]):
        self.results = results
    
    def generate_table(self) -> Table:
        """Genera tabla Rich"""
        # Columnas:
        # - Deployment
        # - Stage
        # - Pod Status
        # - Probes
        # - Conectividad
        # - Latencia
        # - Recomendaciones
    
    def to_json(self, filepath: str):
        """Exporta a JSON"""
    
    def to_csv(self, filepath: str):
        """Exporta a CSV"""
    
    def to_html(self, filepath: str):
        """Exporta a HTML con estilos"""
    
    def to_excel(self, filepath: str):
        """Exporta a Excel con gráficos"""
    
    def generate_recommendations(self) -> List[str]:
        """Genera recomendaciones basadas en resultados"""
```

#### 5.2 Tabla Ejecutiva
```python
def print_summary_table(results: List[HealthCheckResult]):
    """
    ┌──────────────────┬────────┬────────────┬──────────┬──────────────┬─────────┐
    │ Deployment       │ Stage  │ Pod Status │ Probes   │ Conectividad │ Latencia│
    ├──────────────────┼────────┼────────────┼──────────┼──────────────┼─────────┤
    │ web-prod         │ Prod   │ 3/3 Ready  │ ✅ OK    │ ✅ OK        │ 45ms    │
    │ api-prod         │ Prod   │ 2/3 Ready  │ ⚠️ Warn  │ ⚠️ Timeout   │ 5000ms  │
    │ db-prod          │ Prod   │ 1/1 Ready  │ ✅ OK    │ ✅ OK        │ 12ms    │
    └──────────────────┴────────┴────────────┴──────────┴──────────────┴─────────┘
    """
```

#### 5.3 Orquestador Principal (`health_probe_validator.py`)
```python
class HealthProbeValidator:
    """
    Orquestador principal
    """
    
    def __init__(self, azdo_pat: str, kubeconfig: str = None):
        self.azdo_parser = AzDOParser(azdo_pat)
        self.k8s_checker = K8sChecker(kubeconfig)
        self.connectivity_tester = ConnectivityTester()
    
    def validate_deployments(self, input_str: str) -> List[HealthCheckResult]:
        """
        Flujo principal:
        1. Parsear entrada
        2. Obtener info de AZDO
        3. Validar K8s
        4. Probar conectividad
        5. Consolidar resultados
        """
        deployments = parse_input(input_str)
        results = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self._validate_single, dep)
                for dep in deployments
            ]
            results = [f.result() for f in futures]
        
        return results
    
    def _validate_single(self, deployment: DeploymentInput) -> HealthCheckResult:
        """Valida un deployment individual"""
        # 1. AZDO: Obtener stages
        stages = self.azdo_parser.get_stages(deployment.definition_id)
        
        # 2. K8s: Validar pods
        pod_status = self.k8s_checker.check_deployment(
            deployment.name,
            deployment.namespace
        )
        
        # 3. Probes: Validar health checks
        probes = self.k8s_checker.check_health_probes(
            deployment.name,
            deployment.namespace
        )
        
        # 4. Conectividad: Probar endpoints
        connectivity = self.connectivity_tester.test_all_endpoints(
            stages[0].endpoints  # Endpoints del primer stage
        )
        
        # 5. Consolidar
        return HealthCheckResult(
            deployment=deployment.name,
            stage=stages[0].name if stages else "Unknown",
            pod_status=pod_status.status,
            pod_count=pod_status.replicas,
            ready_count=pod_status.ready_replicas,
            liveness_probe=probes.liveness_configured,
            readiness_probe=probes.readiness_configured,
            connectivity="OK" if all(c.success for c in connectivity) else "FAILED",
            latency_ms=sum(c.latency_ms for c in connectivity) / len(connectivity),
            last_updated=datetime.now(),
            errors=[],
            recommendations=[]
        )
```

#### 5.4 Integración en tools.py
```python
# scm/azdo/tools.py
TOOLS = {
    # ... herramientas existentes ...
    "40": {
        "name": "Health Probe Masivo Validator",
        "short": "HEALTH",
        "emoji": "🏥",
        "group": "monitoring",
        "description": "Validación masiva de health probes en K8s desde AZDO",
        "path": "health-probe-masive/health_probe_validator.py",
        "args": ["-i", "-o"],
        "status": "ready"
    }
}
```

---

## 🧪 Testing (4 horas)

### Cobertura de Tests
```
- Unit tests: 30+ tests
- Integration tests: 10+ tests
- E2E tests: 5+ tests
- Coverage objetivo: 85%+
```

### Casos de Prueba
```
1. Parsing de entrada
   - CSV válido
   - DefinitionIds válidos
   - Entrada mixta
   - Entrada inválida

2. AZDO Parser
   - Obtener definición
   - Extraer stages
   - Cacheo
   - Fallback

3. K8s Checker
   - Deployment existente
   - Deployment no existente
   - Pods en diferentes estados
   - Probes configurados/no configurados

4. Connectivity Tester
   - Endpoint accesible
   - Endpoint no accesible
   - Timeout
   - DNS resolution

5. Reporter
   - Generación de tabla
   - Exportación JSON/CSV/HTML/Excel
   - Recomendaciones
```

---

## 📦 Entregables

### Código
- ✅ 5 módulos Python (~2,000 líneas)
- ✅ 45+ tests unitarios
- ✅ Documentación inline
- ✅ Integración en tools.py

### Documentación
- ✅ Análisis arquitectónico
- ✅ Plan de implementación
- ✅ Guía de uso
- ✅ Troubleshooting

### Reportería
- ✅ Tabla ejecutiva (Rich)
- ✅ Exportación JSON
- ✅ Exportación CSV
- ✅ Exportación HTML
- ✅ Exportación Excel

---

## 🎯 Criterios de Aceptación

- ✅ Procesa 100+ deployments en < 5 minutos
- ✅ Tabla ejecutiva clara y legible
- ✅ Exportación a 4 formatos
- ✅ Recomendaciones automáticas
- ✅ 85%+ cobertura de tests
- ✅ Documentación completa
- ✅ Sin hardcoding de credenciales
- ✅ Manejo de errores robusto

---

## 📊 Estimación de Esfuerzo

| Fase | Horas | Días |
|------|-------|------|
| Preparación | 4 | 0.5 |
| AZDO Parser | 8 | 1 |
| K8s Checker | 10 | 1.25 |
| Connectivity Tester | 12 | 1.5 |
| Reportería | 6 | 0.75 |
| **TOTAL** | **40** | **5** |

---

## ✅ Próximos Pasos

1. ✅ Revisar y aprobar plan
2. ⏳ Iniciar Fase 1 (Preparación)
3. ⏳ Implementar módulos secuencialmente
4. ⏳ Testing exhaustivo
5. ⏳ Documentación final
6. ⏳ Integración en toolbox

---

**Plan de Implementación - LISTO PARA REVISIÓN** ✅
