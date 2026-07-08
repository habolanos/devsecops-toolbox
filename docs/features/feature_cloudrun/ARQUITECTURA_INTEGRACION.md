# 🏗️ ARQUITECTURA DE INTEGRACIÓN: Cloud Run con Arquitectura Actual

**Fecha:** 2 de Julio de 2026  
**Versión:** 1.0.0  
**Estado:** 📋 ESPECIFICACIÓN TÉCNICA

---

## 📊 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                      CAPA DE PRESENTACIÓN                        │
│  (base_launcher.py - print_header, print_menu, run_tool)        │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   CAPA DE BÚSQUEDA                               │
│  (search_module_advanced.py - filtros, autocompletado)          │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│              CAPA DE HERRAMIENTAS CLOUD RUN                      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  cloudrun_base.py (Clase Base Compartida)               │  │
│  │  ├─ CloudRunBase                                        │  │
│  │  ├─ run_gcloud_command()                                │  │
│  │  ├─ validate_connection()                               │  │
│  │  └─ export_results()                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  cloudrun_metrics.py (Cálculo de Métricas)              │  │
│  │  ├─ calculate_health_score()                            │  │
│  │  ├─ analyze_performance()                               │  │
│  │  ├─ calculate_costs()                                   │  │
│  │  └─ detect_anomalies()                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  cloudrun_alerts.py (Sistema de Alertas)                │  │
│  │  ├─ AlertManager                                        │  │
│  │  ├─ create_alert()                                      │  │
│  │  ├─ evaluate_thresholds()                               │  │
│  │  └─ format_alert()                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Herramientas Específicas (Tool 19-25)                  │  │
│  │  ├─ gcp_cloudrun_health_analyzer.py                     │  │
│  │  ├─ gcp_cloudrun_security_auditor.py                    │  │
│  │  ├─ gcp_cloudrun_cost_analyzer.py                       │  │
│  │  ├─ gcp_cloudrun_deployment_validator.py                │  │
│  │  ├─ gcp_cloudrun_traffic_analyzer.py                    │  │
│  │  ├─ gcp_cloudrun_dependency_mapper.py                   │  │
│  │  └─ gcp_cloudrun_executive_dashboard.py                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   CAPA DE EXPORTACIÓN                            │
│  (export_manager.py - JSON, CSV, Excel)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   CAPA DE ALMACENAMIENTO                         │
│  (outcome/ - Directorio centralizado de salida)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Puntos de Integración

### 1. Integración con base_launcher.py

**Uso en cada herramienta:**
```python
from base_launcher import (
    clear_screen,
    print_header,
    print_menu,
    Colors,
    log_command,
    run_tool
)

class CloudRunHealthAnalyzer(CloudRunBase):
    def __init__(self, project: str, region: str = "all"):
        super().__init__(project, region)
        self.colors = Colors
    
    def display_results(self):
        # Usar print_header para encabezado consistente
        print_header(
            title="Cloud Run Health Analyzer",
            subtitle="v1.0.0",
            description="Análisis de salud de servicios Cloud Run",
            platform_name="GCP"
        )
        
        # Usar Colors para colores consistentes
        print(f"{self.colors.HEADER}=== Resultados ==={self.colors.ENDC}")
        
        # Usar log_command para auditoría
        log_command(
            ["gcloud", "run", "services", "list"],
            status="EXEC",
            platform="gcp"
        )
```

### 2. Integración con search_module_advanced.py

**Uso para búsqueda de servicios:**
```python
from search_module_advanced import (
    AdvancedFilter,
    search_items_advanced,
    get_autocomplete_suggestions,
    SearchPaginator
)

class CloudRunHealthAnalyzer(CloudRunBase):
    def search_services(self, query: str):
        # Obtener servicios
        services = self.get_services()
        
        # Crear filtros
        filters = AdvancedFilter()
        filters.set_group("cloud-run")
        
        # Buscar
        results = search_items_advanced(
            services,
            query,
            filters=filters
        )
        
        # Paginar resultados
        paginator = SearchPaginator(results, page_size=10)
        return paginator
```

### 3. Integración con export_manager.py

**Uso para exportación estándar:**
```python
from export_manager import ExportManager

class CloudRunHealthAnalyzer(CloudRunBase):
    def export_results(self, data: Dict, format: str = "json"):
        """Exporta resultados usando ExportManager"""
        
        exporter = ExportManager(
            tool_name="cloudrun_health_analyzer",
            version="1.0.0"
        )
        
        # Exportar a JSON
        if format == "json":
            exporter.to_json(data)
        
        # Exportar a CSV
        elif format == "csv":
            exporter.to_csv(data)
        
        # Exportar a Excel
        elif format == "excel":
            exporter.to_excel(data)
        
        return exporter.get_output_path()
```

### 4. Integración en tools.py

**Estructura en scm/gcp/tools.py:**
```python
# Importar base_launcher
try:
    from base_launcher import (
        clear_screen, print_header, print_menu,
        get_menu_order, get_auto_tools, build_system_options,
        log_command, run_tool, Colors
    )
    BASE_LAUNCHER_AVAILABLE = True
except ImportError:
    BASE_LAUNCHER_AVAILABLE = False

# Agregar herramientas Cloud Run
TOOLS = {
    # ... herramientas existentes ...
    
    "19": {
        "name": "Cloud Run Health Analyzer",
        "description": "Análisis profundo de salud y rendimiento",
        "path": "cloud-run/gcp_cloudrun_health_analyzer.py",
        "args": ["--project", "--region", "--service", "--metric"],
        "group": "kubernetes",
        "status": "ready"
    },
    # ... más herramientas ...
}

# Usar run_tool de base_launcher
def run_tool(tool_key: str):
    if BASE_LAUNCHER_AVAILABLE:
        # Usar función centralizada
        from base_launcher import run_tool as base_run_tool
        return base_run_tool(tool_key, TOOLS, BASE_DIR)
    else:
        # Fallback local
        # ... implementación local ...
```

---

## 📦 Estructura de Módulos

### cloudrun_base.py
```python
#!/usr/bin/env python3
"""
Módulo base para todas las herramientas Cloud Run.
Proporciona funcionalidad común y reutilizable.
"""

import subprocess
import json
from typing import List, Dict, Optional
from pathlib import Path

class CloudRunBase:
    """Clase base para herramientas Cloud Run"""
    
    def __init__(self, project: str, region: str = "all", debug: bool = False):
        self.project = project
        self.region = region
        self.debug = debug
        self.gcp_client = None
    
    def run_gcloud_command(self, command: str) -> Optional[List[Dict]]:
        """
        Ejecuta comando gcloud y retorna JSON.
        
        Args:
            command: Comando gcloud a ejecutar
        
        Returns:
            Lista de diccionarios con resultado o None
        """
        full_command = f"{command} --project={self.project} --format=json"
        
        try:
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                if self.debug:
                    print(f"Error: {result.stderr}")
                return []
            
            if result.stdout.strip():
                return json.loads(result.stdout)
            return []
        
        except Exception as e:
            if self.debug:
                print(f"Exception: {e}")
            return []
    
    def validate_connection(self) -> bool:
        """Valida conexión a GCP"""
        result = self.run_gcloud_command("gcloud run services list")
        return result is not None
    
    def export_results(self, data: Dict, format: str = "json"):
        """
        Exporta resultados usando ExportManager.
        
        Args:
            data: Datos a exportar
            format: Formato (json, csv, excel)
        """
        try:
            from export_manager import ExportManager
            
            exporter = ExportManager(
                tool_name=self.__class__.__name__,
                version="1.0.0"
            )
            
            if format == "json":
                return exporter.to_json(data)
            elif format == "csv":
                return exporter.to_csv(data)
            elif format == "excel":
                return exporter.to_excel(data)
        
        except ImportError:
            # Fallback: exportar manualmente
            return self._export_fallback(data, format)
    
    def _export_fallback(self, data: Dict, format: str):
        """Fallback si ExportManager no está disponible"""
        from datetime import datetime
        from pathlib import Path
        
        output_dir = Path("outcome")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"{self.__class__.__name__}_{timestamp}.{format}"
        
        if format == "json":
            import json
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
        
        return str(filename)
```

### cloudrun_metrics.py
```python
#!/usr/bin/env python3
"""
Módulo de cálculo de métricas para Cloud Run.
Proporciona funciones para análisis de rendimiento, costos, etc.
"""

from typing import Dict, List
from datetime import datetime, timedelta

class CloudRunMetrics:
    """Cálculo de métricas para Cloud Run"""
    
    @staticmethod
    def calculate_health_score(
        service: Dict,
        metrics: Dict
    ) -> int:
        """
        Calcula score de salud (0-100).
        
        Factores:
        - Availability (30%)
        - Performance (30%)
        - Error Rate (20%)
        - Resource Usage (20%)
        """
        availability = metrics.get("availability", 100)
        performance = metrics.get("performance", 100)
        error_rate = metrics.get("error_rate", 0)
        resource_usage = metrics.get("resource_usage", 50)
        
        score = (
            availability * 0.30 +
            performance * 0.30 +
            (100 - error_rate) * 0.20 +
            (100 - resource_usage) * 0.20
        )
        
        return int(score)
    
    @staticmethod
    def calculate_costs(
        service: Dict,
        region: str,
        period_days: int = 30
    ) -> Dict:
        """
        Calcula costos estimados.
        
        Basado en:
        - CPU allocation
        - Memory allocation
        - Invocations
        - Outbound traffic
        """
        # Implementación de cálculo de costos
        pass
    
    @staticmethod
    def detect_anomalies(
        metrics_history: List[Dict]
    ) -> List[Dict]:
        """
        Detecta anomalías en métricas.
        
        Usa desviación estándar para identificar valores anómalos.
        """
        # Implementación de detección de anomalías
        pass
```

### cloudrun_alerts.py
```python
#!/usr/bin/env python3
"""
Sistema de alertas para Cloud Run.
Gestiona creación, evaluación y formato de alertas.
"""

from typing import Dict, List
from enum import Enum

class AlertSeverity(Enum):
    """Niveles de severidad de alertas"""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

class AlertManager:
    """Gestor de alertas"""
    
    def __init__(self):
        self.alerts: List[Dict] = []
    
    def create_alert(
        self,
        service: str,
        severity: AlertSeverity,
        message: str,
        metric: str,
        threshold: float,
        current_value: float
    ) -> Dict:
        """
        Crea una alerta.
        
        Args:
            service: Nombre del servicio
            severity: Nivel de severidad
            message: Mensaje de alerta
            metric: Métrica que disparó la alerta
            threshold: Umbral configurado
            current_value: Valor actual
        
        Returns:
            Diccionario con detalles de la alerta
        """
        alert = {
            "service": service,
            "severity": severity.value,
            "message": message,
            "metric": metric,
            "threshold": threshold,
            "current_value": current_value,
            "timestamp": datetime.now().isoformat()
        }
        
        self.alerts.append(alert)
        return alert
    
    def evaluate_thresholds(
        self,
        service: Dict,
        metrics: Dict,
        thresholds: Dict
    ) -> List[Dict]:
        """
        Evalúa métricas contra umbrales.
        
        Args:
            service: Datos del servicio
            metrics: Métricas calculadas
            thresholds: Umbrales configurados
        
        Returns:
            Lista de alertas generadas
        """
        alerts = []
        
        for metric_name, threshold in thresholds.items():
            current_value = metrics.get(metric_name, 0)
            
            if current_value > threshold:
                severity = AlertSeverity.CRITICAL if current_value > threshold * 1.5 else AlertSeverity.WARNING
                
                alert = self.create_alert(
                    service=service.get("name", "unknown"),
                    severity=severity,
                    message=f"{metric_name} excedió umbral",
                    metric=metric_name,
                    threshold=threshold,
                    current_value=current_value
                )
                
                alerts.append(alert)
        
        return alerts
```

---

## 🔄 Flujo de Ejecución

### Flujo Típico de una Herramienta Cloud Run

```
1. Inicialización
   ├─ Parsear argumentos CLI
   ├─ Validar proyecto GCP
   └─ Inicializar CloudRunBase

2. Recolección de Datos
   ├─ Ejecutar comandos gcloud
   ├─ Parsear respuestas JSON
   └─ Validar datos

3. Análisis
   ├─ Calcular métricas (cloudrun_metrics.py)
   ├─ Detectar anomalías
   └─ Evaluar umbrales (cloudrun_alerts.py)

4. Visualización
   ├─ Usar base_launcher.print_header()
   ├─ Crear tablas con Rich
   └─ Mostrar alertas

5. Exportación
   ├─ Usar export_manager.py
   ├─ Generar JSON/CSV/Excel
   └─ Guardar en outcome/

6. Logging
   ├─ Usar base_launcher.log_command()
   └─ Registrar en auditoría
```

---

## 🧪 Testing

### Estructura de Tests
```
tests/
├── test_cloudrun_base.py
│   ├─ TestCloudRunBase
│   │  ├─ test_init()
│   │  ├─ test_validate_connection()
│   │  └─ test_export_results()
│   └─ TestCloudRunMetrics
│      ├─ test_calculate_health_score()
│      ├─ test_calculate_costs()
│      └─ test_detect_anomalies()
│
├── test_cloudrun_health_analyzer.py
│   ├─ TestHealthAnalyzer
│   │  ├─ test_get_metrics()
│   │  ├─ test_analyze_performance()
│   │  └─ test_generate_report()
│
└── ... (más tests para otras herramientas)
```

### Mocking de GCP
```python
from unittest.mock import patch, MagicMock

@patch('cloudrun_base.subprocess.run')
def test_run_gcloud_command(mock_run):
    """Test de ejecución de comando gcloud"""
    
    # Mock respuesta
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='[{"name": "service-1"}]'
    )
    
    # Ejecutar
    analyzer = CloudRunHealthAnalyzer("test-project")
    result = analyzer.run_gcloud_command("gcloud run services list")
    
    # Verificar
    assert len(result) == 1
    assert result[0]["name"] == "service-1"
```

---

## 📊 Configuración de Umbrales

### Archivo de Configuración (cloudrun_config.yaml)
```yaml
health_analyzer:
  thresholds:
    error_rate: 5.0  # %
    latency_p99: 1000  # ms
    availability: 99.9  # %
    cpu_usage: 80  # %
    memory_usage: 85  # %

security_auditor:
  checks:
    - iam_policies
    - ingress_settings
    - vpc_connector
    - service_accounts
    - secrets
    - binary_authorization

cost_analyzer:
  alerts:
    daily_increase: 10  # %
    monthly_projection: 1000  # USD
    per_service_limit: 500  # USD

deployment_validator:
  strict_mode: false
  checks:
    - config_validation
    - dependency_check
    - resource_limits
    - health_checks
```

---

## 🔐 Seguridad

### Consideraciones de Seguridad

1. **Autenticación**
   ```python
   # Usar gcloud para autenticación
   # No guardar credenciales en código
   # Validar permisos del usuario
   ```

2. **Autorización**
   ```python
   # Verificar permisos necesarios
   # Usar service accounts cuando sea posible
   # Auditar acceso con log_command()
   ```

3. **Datos Sensibles**
   ```python
   # No loguear secrets
   # Enmascarar información sensible
   # Usar variables de entorno
   ```

---

## 📈 Performance

### Optimizaciones

1. **Ejecución Paralela**
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   with ThreadPoolExecutor(max_workers=6) as executor:
       futures = [
           executor.submit(get_services, project, region),
           executor.submit(get_jobs, project, region),
           executor.submit(get_domain_mappings, project, region)
       ]
   ```

2. **Cacheo**
   ```python
   # Cachear resultados de gcloud por 5 minutos
   # Usar TTL para invalidar cache
   # Permitir --no-cache para forzar refresh
   ```

3. **Paginación**
   ```python
   # Usar SearchPaginator para resultados grandes
   # Limitar resultados con --top
   # Implementar lazy loading
   ```

---

## 🔗 Referencias

### Documentación Relacionada
- [base_launcher.py](../../scm/base_launcher.py)
- [search_module_advanced.py](../../scm/search_module_advanced.py)
- [export_manager.py](../../scm/export_manager.py)
- [gcp_cloudrun_checker.py](../../scm/gcp/cloud-run/gcp_cloudrun_checker.py)

### Estándares
- [PLAN_INTEGRAL_CLOUDRUN.md](PLAN_INTEGRAL_CLOUDRUN.md)
- [SESION_FINAL_COMPLETA_FASE2_FASE3_FASE4.md](../SESION_FINAL_COMPLETA_FASE2_FASE3_FASE4.md)

---

**Estado:** 📋 ESPECIFICACIÓN TÉCNICA COMPLETA  
**Versión:** 1.0.0  
**Próximo Paso:** Implementar cloudrun_base.py

---

*Creado: 2 de Julio de 2026*  
*Autor: Harold Adrian Bolanos Rodriguez*  
*Proyecto: DevSecOps Toolbox - Cloud Run Feature*
