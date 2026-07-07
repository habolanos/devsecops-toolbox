# 🏗️ Arquitectura Técnica: Consolidador de Infraestructura GCP

**Versión:** 1.0.0  
**Nivel:** Arquitectura Técnica Detallada  
**Fecha:** 3 de Julio de 2026

---

## 📐 Diseño de Componentes

### 1. Load Balancer Extractor

**Responsabilidad:** Extraer datos de Load Balancers

```python
class LoadBalancerExtractor:
    def __init__(self, project_id: str, debug: bool = False):
        self.project_id = project_id
        self.debug = debug
    
    def extract_all(self) -> Dict:
        """Extrae todos los datos de LB"""
        return {
            'forwarding_rules': self.get_forwarding_rules(),
            'backend_services': self.get_backend_services(),
            'url_maps': self.get_url_maps(),
            'health_checks': self.get_health_checks(),
            'ssl_certificates': self.get_ssl_certificates(),
            'security_policies': self.get_security_policies(),
            'network_endpoint_groups': self.get_negs()
        }
    
    def get_negs(self) -> List[Dict]:
        """Obtiene Network Endpoint Groups"""
        cmd = f'gcloud compute network-endpoint-groups list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd) or []
```

### 2. Cloud Run Extractor

**Responsabilidad:** Extraer datos de Cloud Run

```python
class CloudRunExtractor:
    def __init__(self, project_id: str, debug: bool = False):
        self.project_id = project_id
        self.debug = debug
    
    def extract_all(self) -> Dict:
        """Extrae todos los datos de Cloud Run"""
        return {
            'services': self.get_services(),
            'service_details': self.get_service_details(),
            'traffic_metrics': self.get_traffic_metrics(),
            'security_config': self.get_security_config()
        }
    
    def get_services(self) -> List[Dict]:
        """Obtiene servicios Cloud Run"""
        cmd = f'gcloud run services list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd) or []
```

### 3. Cloud Functions Extractor

**Responsabilidad:** Extraer datos de Cloud Functions

```python
class CloudFunctionsExtractor:
    def __init__(self, project_id: str, debug: bool = False):
        self.project_id = project_id
        self.debug = debug
    
    def extract_all(self) -> Dict:
        """Extrae todos los datos de Cloud Functions"""
        return {
            'functions': self.get_functions(),
            'function_details': self.get_function_details(),
            'triggers': self.get_triggers(),
            'security_config': self.get_security_config()
        }
    
    def get_functions(self) -> List[Dict]:
        """Obtiene funciones Cloud Functions"""
        cmd = f'gcloud functions list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd) or []
```

### 4. Relationship Mapper

**Responsabilidad:** Mapear relaciones entre componentes

```python
class RelationshipMapper:
    def __init__(self, lb_data: Dict, cr_data: Dict, cf_data: Dict):
        self.lb_data = lb_data
        self.cr_data = cr_data
        self.cf_data = cf_data
    
    def map_all_relationships(self) -> Dict:
        """Mapea todas las relaciones"""
        return {
            'lb_to_cr': self.map_lb_to_cloud_run(),
            'lb_to_cf': self.map_lb_to_cloud_functions(),
            'lb_to_instances': self.map_lb_to_instances(),
            'orphaned_cr': self.find_orphaned_cloud_run(),
            'orphaned_cf': self.find_orphaned_cloud_functions(),
            'uncovered_backends': self.find_uncovered_backends()
        }
    
    def map_lb_to_cloud_run(self) -> List[Dict]:
        """Mapea Load Balancers a Cloud Run"""
        relationships = []
        
        for bs in self.lb_data.get('backend_services', []):
            for backend in bs.get('backends', []):
                group_url = backend.get('group', '')
                
                # Verificar si es NEG de Cloud Run
                if self._is_cloud_run_neg(group_url):
                    cr_service = self._find_cloud_run_service(group_url)
                    if cr_service:
                        relationships.append({
                            'lb_name': self._get_lb_name(bs),
                            'backend_service': bs.get('name'),
                            'neg_url': group_url,
                            'cloud_run_service': cr_service.get('name'),
                            'region': cr_service.get('location'),
                            'health_status': backend.get('balancingMode'),
                            'max_rate': backend.get('maxRatePerEndpoint')
                        })
        
        return relationships
    
    def _is_cloud_run_neg(self, url: str) -> bool:
        """Verifica si es NEG de Cloud Run"""
        return 'networkEndpointGroups' in url and 'cloudrun' in url.lower()
    
    def find_orphaned_cloud_run(self) -> List[Dict]:
        """Encuentra servicios Cloud Run sin LB"""
        lb_services = {rel['cloud_run_service'] for rel in self.map_lb_to_cloud_run()}
        all_services = {s.get('name') for s in self.cr_data.get('services', [])}
        
        return [
            s for s in self.cr_data.get('services', [])
            if s.get('name') not in lb_services
        ]
```

### 5. Consolidation Engine

**Responsabilidad:** Generar consolidado final

```python
class ConsolidationEngine:
    def __init__(self, extractors: Dict, mapper: RelationshipMapper):
        self.extractors = extractors
        self.mapper = mapper
    
    def generate_consolidation(self) -> Dict:
        """Genera consolidado completo"""
        return {
            'metadata': self._generate_metadata(),
            'summary': self._generate_summary(),
            'load_balancers': self._process_load_balancers(),
            'cloud_run': self._process_cloud_run(),
            'cloud_functions': self._process_cloud_functions(),
            'relationships': self.mapper.map_all_relationships(),
            'health_status': self._analyze_health(),
            'security_posture': self._analyze_security(),
            'cost_analysis': self._analyze_costs(),
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_summary(self) -> Dict:
        """Genera resumen ejecutivo"""
        return {
            'total_load_balancers': len(self.extractors['lb'].extract_all().get('forwarding_rules', [])),
            'total_cloud_run_services': len(self.extractors['cr'].extract_all().get('services', [])),
            'total_cloud_functions': len(self.extractors['cf'].extract_all().get('functions', [])),
            'total_relationships': len(self.mapper.map_all_relationships().get('lb_to_cr', [])),
            'orphaned_services': len(self.mapper.find_orphaned_cloud_run()),
            'health_score': self._calculate_health_score()
        }
    
    def _analyze_health(self) -> Dict:
        """Analiza salud de todas las relaciones"""
        relationships = self.mapper.map_all_relationships()
        
        health_status = {
            'healthy': 0,
            'degraded': 0,
            'unhealthy': 0,
            'unknown': 0
        }
        
        for rel in relationships.get('lb_to_cr', []):
            status = self._check_relationship_health(rel)
            health_status[status] += 1
        
        return health_status
    
    def _analyze_security(self) -> Dict:
        """Analiza postura de seguridad"""
        return {
            'cloud_armor_enabled': self._count_cloud_armor(),
            'ssl_configured': self._count_ssl(),
            'iap_enabled': self._count_iap(),
            'security_score': self._calculate_security_score()
        }
    
    def _analyze_costs(self) -> Dict:
        """Analiza costos consolidados"""
        return {
            'lb_cost_estimate': self._estimate_lb_costs(),
            'cloud_run_cost_estimate': self._estimate_cr_costs(),
            'cloud_functions_cost_estimate': self._estimate_cf_costs(),
            'total_monthly_estimate': self._estimate_total_costs()
        }
    
    def _generate_recommendations(self) -> List[Dict]:
        """Genera recomendaciones automáticas"""
        recommendations = []
        
        # Recomendación 1: Servicios huérfanos
        orphaned = self.mapper.find_orphaned_cloud_run()
        if orphaned:
            recommendations.append({
                'type': 'ORPHANED_SERVICES',
                'severity': 'MEDIUM',
                'count': len(orphaned),
                'message': f'{len(orphaned)} servicios Cloud Run sin Load Balancer',
                'action': 'Considerar agregar a LB o eliminar si no se usan'
            })
        
        # Recomendación 2: Cloud Armor no configurado
        if self._count_cloud_armor() == 0:
            recommendations.append({
                'type': 'SECURITY_MISSING',
                'severity': 'HIGH',
                'message': 'Cloud Armor no configurado en ningún backend',
                'action': 'Habilitar Cloud Armor en backends públicos'
            })
        
        # Recomendación 3: SSL no configurado
        if self._count_ssl() == 0:
            recommendations.append({
                'type': 'SSL_MISSING',
                'severity': 'CRITICAL',
                'message': 'SSL/TLS no configurado',
                'action': 'Configurar certificados SSL en todos los LB'
            })
        
        return recommendations
```

---

## 🔄 Flujo de Datos

```
┌──────────────────────────────────────────────────────────────────┐
│                    CONSOLIDATION PIPELINE                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. EXTRACTION PHASE                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ LoadBalancerExtractor → LB Data                         │    │
│  │ CloudRunExtractor     → CR Data                         │    │
│  │ CloudFunctionsExtractor → CF Data                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                        │
│  2. MAPPING PHASE                                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ RelationshipMapper                                      │    │
│  │ - Map LB → Cloud Run                                   │    │
│  │ - Map LB → Cloud Functions                             │    │
│  │ - Find Orphaned Services                               │    │
│  │ - Find Uncovered Backends                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                        │
│  3. ANALYSIS PHASE                                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ConsolidationEngine                                     │    │
│  │ - Health Analysis                                       │    │
│  │ - Security Analysis                                     │    │
│  │ - Cost Analysis                                         │    │
│  │ - Generate Recommendations                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                        │
│  4. OUTPUT PHASE                                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ExportManager                                           │    │
│  │ - JSON Export                                           │    │
│  │ - CSV Export                                            │    │
│  │ - Excel Export                                          │    │
│  │ - Rich Console Output                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📊 Estructura de Datos

### Consolidation Output

```json
{
  "consolidation": {
    "metadata": {
      "tool_name": "GCP Infrastructure Consolidator",
      "version": "1.0.0",
      "project_id": "my-project",
      "generated_at": "2026-07-03T12:00:00Z",
      "timezone": "America/Mazatlan"
    },
    "summary": {
      "total_load_balancers": 5,
      "total_cloud_run_services": 12,
      "total_cloud_functions": 8,
      "total_relationships": 15,
      "orphaned_services": 3,
      "health_score": 85
    },
    "relationships": [
      {
        "lb_name": "web-frontend",
        "backend_service": "api-backend",
        "neg_url": "projects/my-project/global/networkEndpointGroups/api-neg",
        "cloud_run_service": "api-service",
        "region": "us-central1",
        "health_status": "HEALTHY",
        "max_rate": 1000,
        "traffic_percentage": 100,
        "latency_p99_ms": 45,
        "error_rate": 0.01
      }
    ],
    "orphaned_services": [
      {
        "name": "internal-service",
        "region": "us-east1",
        "status": "ACTIVE",
        "reason": "No Load Balancer configured"
      }
    ],
    "health_status": {
      "healthy": 15,
      "degraded": 2,
      "unhealthy": 0,
      "unknown": 1
    },
    "security_posture": {
      "cloud_armor_enabled": 3,
      "ssl_configured": 5,
      "iap_enabled": 2,
      "security_score": 75
    },
    "cost_analysis": {
      "lb_cost_estimate": 150.00,
      "cloud_run_cost_estimate": 450.00,
      "cloud_functions_cost_estimate": 120.00,
      "total_monthly_estimate": 720.00
    },
    "recommendations": [
      {
        "type": "ORPHANED_SERVICES",
        "severity": "MEDIUM",
        "count": 3,
        "message": "3 servicios Cloud Run sin Load Balancer",
        "action": "Considerar agregar a LB o eliminar si no se usan"
      }
    ]
  }
}
```

---

## 🔌 Integración con Herramientas Existentes

### Con Tool 12 (Load Balancer Checker)

```python
# Reutilizar funciones de LB Checker
from load_balancer.gcp_load_balancer_checker import (
    get_forwarding_rules_global,
    get_backend_services_global,
    get_health_checks,
    get_security_policies
)

class LoadBalancerExtractor:
    def get_backend_services(self):
        # Usar función existente
        return get_backend_services_global(self.project_id, self.debug, self.console)
```

### Con Tools 28-34 (Cloud Run)

```python
# Reutilizar módulos de Cloud Run
from cloud_run.cloudrun_base import CloudRunBase
from cloud_run.cloudrun_metrics import CloudRunMetrics

class CloudRunExtractor(CloudRunBase):
    def get_services(self):
        # Usar métodos heredados
        return self.run_gcloud_command(
            'gcloud run services list --format=json'
        )
```

---

## 🧪 Testing Strategy

### Unit Tests

```python
def test_load_balancer_extractor():
    extractor = LoadBalancerExtractor('test-project')
    data = extractor.extract_all()
    assert 'forwarding_rules' in data
    assert 'backend_services' in data

def test_relationship_mapper():
    mapper = RelationshipMapper(lb_data, cr_data, cf_data)
    relationships = mapper.map_lb_to_cloud_run()
    assert len(relationships) > 0
    assert 'cloud_run_service' in relationships[0]

def test_consolidation_engine():
    engine = ConsolidationEngine(extractors, mapper)
    consolidation = engine.generate_consolidation()
    assert 'summary' in consolidation
    assert 'relationships' in consolidation
    assert 'recommendations' in consolidation
```

### Integration Tests

```python
def test_full_consolidation_pipeline():
    # Test completo end-to-end
    project = 'test-project'
    
    # Extract
    lb_extractor = LoadBalancerExtractor(project)
    cr_extractor = CloudRunExtractor(project)
    cf_extractor = CloudFunctionsExtractor(project)
    
    # Map
    mapper = RelationshipMapper(
        lb_extractor.extract_all(),
        cr_extractor.extract_all(),
        cf_extractor.extract_all()
    )
    
    # Consolidate
    engine = ConsolidationEngine(
        {'lb': lb_extractor, 'cr': cr_extractor, 'cf': cf_extractor},
        mapper
    )
    
    consolidation = engine.generate_consolidation()
    
    # Verify
    assert consolidation['summary']['total_load_balancers'] >= 0
    assert consolidation['summary']['total_cloud_run_services'] >= 0
```

---

## 📈 Performance Considerations

### Parallelization

```python
from concurrent.futures import ThreadPoolExecutor

def extract_all_parallel(project_id):
    with ThreadPoolExecutor(max_workers=3) as executor:
        lb_future = executor.submit(LoadBalancerExtractor(project_id).extract_all)
        cr_future = executor.submit(CloudRunExtractor(project_id).extract_all)
        cf_future = executor.submit(CloudFunctionsExtractor(project_id).extract_all)
        
        return {
            'lb': lb_future.result(),
            'cr': cr_future.result(),
            'cf': cf_future.result()
        }
```

### Caching

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedExtractor:
    def __init__(self, ttl_minutes=60):
        self.ttl = timedelta(minutes=ttl_minutes)
        self.cache = {}
        self.cache_time = {}
    
    def get_with_cache(self, key, fetch_func):
        if key in self.cache:
            if datetime.now() - self.cache_time[key] < self.ttl:
                return self.cache[key]
        
        result = fetch_func()
        self.cache[key] = result
        self.cache_time[key] = datetime.now()
        return result
```

---

## 🚀 Deployment

### As Tool 36

```python
# scm/gcp/tools.py
TOOLS = {
    ...
    "36": {
        "name": "Infrastructure Consolidator",
        "description": "Consolidado de LB + Cloud Run + Cloud Functions",
        "path": "consolidation/gcp_infrastructure_consolidator.py",
        "args": ["--project", "--output", "--debug"],
        "requirements": None,
        "group": "consolidation",
        "status": "ready"
    }
}
```

---

## 📝 Conclusión

Esta arquitectura proporciona:

1. **Modularidad**: Componentes independientes y reutilizables
2. **Escalabilidad**: Fácil agregar nuevos extractores
3. **Mantenibilidad**: Código limpio y bien estructurado
4. **Performance**: Ejecución paralela y caching
5. **Extensibilidad**: Fácil agregar nuevas análisis

