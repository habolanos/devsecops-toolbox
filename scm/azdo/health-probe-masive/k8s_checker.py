"""
K8s Checker - Valida deployments, pods y health probes en Kubernetes
"""
import logging
from typing import List, Optional

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .config import K8S_KUBECONFIG
from .models import DeploymentStatus, PodStatus, ProbeStatus

logger = logging.getLogger(__name__)


class K8sChecker:
    """Validador de Kubernetes"""
    
    def __init__(self, kubeconfig_path: Optional[str] = K8S_KUBECONFIG):
        try:
            if kubeconfig_path:
                config.load_kube_config(kubeconfig_path)
            else:
                config.load_incluster_config()
        except Exception as e:
            logger.warning(f"Failed to load kubeconfig, using default: {e}")
            config.load_kube_config()
        
        self.apps_v1 = client.AppsV1Api()
        self.v1 = client.CoreV1Api()
    
    def check_deployment(self, name: str, namespace: str) -> Optional[DeploymentStatus]:
        """
        Valida estado de deployment
        
        GET /apis/apps/v1/namespaces/{namespace}/deployments/{name}
        """
        try:
            deployment = self.apps_v1.read_namespaced_deployment(name, namespace)
            
            status = DeploymentStatus(
                name=name,
                namespace=namespace,
                replicas=deployment.spec.replicas or 0,
                ready_replicas=deployment.status.ready_replicas or 0,
                updated_replicas=deployment.status.updated_replicas or 0,
                available_replicas=deployment.status.available_replicas or 0
            )
            
            logger.info(f"Deployment {name}/{namespace}: {status.status}")
            return status
        
        except ApiException as e:
            logger.error(f"Failed to get deployment {name}/{namespace}: {e}")
            return None
    
    def check_pods(self, deployment: str, namespace: str) -> List[PodStatus]:
        """
        Valida estado de pods para un deployment
        
        GET /api/v1/namespaces/{namespace}/pods
        """
        pods = []
        
        try:
            label_selector = f"app={deployment}"
            pod_list = self.v1.list_namespaced_pod(namespace, label_selector=label_selector)
            
            for pod in pod_list.items:
                pod_status = PodStatus(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    status=pod.status.phase,
                    ready_containers=sum(
                        1 for c in pod.status.conditions or []
                        if c.type == "Ready" and c.status == "True"
                    ),
                    total_containers=len(pod.spec.containers),
                    restart_count=sum(
                        c.restart_count for c in pod.status.container_statuses or []
                    ) if pod.status.container_statuses else 0,
                    age_seconds=int((pod.metadata.creation_timestamp.timestamp()))
                    if pod.metadata.creation_timestamp else 0
                )
                pods.append(pod_status)
                logger.debug(f"Pod {pod.metadata.name}: {pod_status.status}")
            
            return pods
        
        except ApiException as e:
            logger.error(f"Failed to list pods for {deployment}/{namespace}: {e}")
            return []
    
    def check_health_probes(self, pod_name: str, namespace: str) -> Optional[ProbeStatus]:
        """
        Valida health probes configurados en un pod
        
        GET /api/v1/namespaces/{namespace}/pods/{name}
        """
        try:
            pod = self.v1.read_namespaced_pod(pod_name, namespace)
            
            # Obtener probes del primer contenedor
            if not pod.spec.containers:
                return None
            
            container = pod.spec.containers[0]
            
            liveness = container.liveness_probe
            readiness = container.readiness_probe
            startup = container.startup_probe
            
            probe_status = ProbeStatus(
                liveness_configured=liveness is not None,
                liveness_type=self._get_probe_type(liveness),
                liveness_timeout=liveness.timeout_seconds if liveness else 0,
                liveness_period=liveness.period_seconds if liveness else 0,
                readiness_configured=readiness is not None,
                readiness_type=self._get_probe_type(readiness),
                readiness_timeout=readiness.timeout_seconds if readiness else 0,
                readiness_period=readiness.period_seconds if readiness else 0,
                startup_configured=startup is not None
            )
            
            logger.info(f"Pod {pod_name}: Probes - {probe_status.status_emoji}")
            return probe_status
        
        except ApiException as e:
            logger.error(f"Failed to check probes for {pod_name}/{namespace}: {e}")
            return None
    
    def _get_probe_type(self, probe) -> Optional[str]:
        """Determina tipo de probe (HTTP, TCP, Exec)"""
        if probe is None:
            return None
        
        if probe.http_get:
            return "HTTP"
        elif probe.tcp_socket:
            return "TCP"
        elif probe.exec:
            return "Exec"
        else:
            return "Unknown"
    
    def get_pod_logs(self, pod_name: str, namespace: str, lines: int = 50) -> str:
        """
        Obtiene logs del pod
        
        GET /api/v1/namespaces/{namespace}/pods/{name}/log
        """
        try:
            logs = self.v1.read_namespaced_pod_log(
                pod_name,
                namespace,
                tail_lines=lines
            )
            logger.debug(f"Retrieved logs for {pod_name}")
            return logs
        
        except ApiException as e:
            logger.error(f"Failed to get logs for {pod_name}/{namespace}: {e}")
            return ""
    
    def get_pod_events(self, pod_name: str, namespace: str) -> List[str]:
        """
        Obtiene eventos del pod
        """
        try:
            pod = self.v1.read_namespaced_pod(pod_name, namespace)
            events = []
            
            if pod.status.conditions:
                for condition in pod.status.conditions:
                    event = f"{condition.type}: {condition.message}"
                    events.append(event)
            
            logger.debug(f"Retrieved {len(events)} events for {pod_name}")
            return events
        
        except ApiException as e:
            logger.error(f"Failed to get events for {pod_name}/{namespace}: {e}")
            return []
