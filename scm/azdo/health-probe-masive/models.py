"""
Dataclasses para Health Probe Masivo Validator
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class DeploymentInput:
    """Entrada de usuario - deployment o definition ID"""
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
    endpoints: List[str] = field(default_factory=list)
    ports: List[int] = field(default_factory=list)
    environment: str = "Unknown"  # Dev, QA, Staging, Prod


@dataclass
class DeploymentStatus:
    """Estado de deployment en Kubernetes"""
    name: str
    namespace: str
    replicas: int
    ready_replicas: int
    updated_replicas: int
    available_replicas: int
    
    @property
    def status(self) -> str:
        if self.ready_replicas == self.replicas and self.replicas > 0:
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
    liveness_type: Optional[str] = None  # HTTP, TCP, Exec
    liveness_timeout: int = 0
    liveness_period: int = 0
    readiness_configured: bool = False
    readiness_type: Optional[str] = None
    readiness_timeout: int = 0
    readiness_period: int = 0
    startup_configured: bool = False
    
    @property
    def is_healthy(self) -> bool:
        return (
            self.liveness_configured and
            self.readiness_configured and
            self.liveness_timeout >= 5 and
            self.readiness_timeout >= 5
        )
    
    @property
    def status_emoji(self) -> str:
        if self.is_healthy:
            return "✅"
        elif self.liveness_configured or self.readiness_configured:
            return "⚠️"
        else:
            return "❌"


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
    
    @property
    def status(self) -> str:
        if self.timeout:
            return "TIMEOUT"
        elif self.success:
            return "OK"
        else:
            return "FAILED"


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
    last_updated: datetime = field(default_factory=datetime.now)
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
    
    @property
    def pod_status_emoji(self) -> str:
        if self.pod_status == "Ready":
            return "✅"
        elif self.pod_status == "Partial":
            return "⚠️"
        else:
            return "❌"
    
    @property
    def connectivity_emoji(self) -> str:
        if self.connectivity == "OK":
            return "✅"
        elif self.connectivity == "TIMEOUT":
            return "⚠️"
        else:
            return "❌"
