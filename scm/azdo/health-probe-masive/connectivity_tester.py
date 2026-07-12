"""
Connectivity Tester - Prueba conectividad usando pod de verificación
"""
import logging
import subprocess
import time
from typing import List

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .config import CONNECTIVITY_POD_IMAGE, CONNECTIVITY_POD_NAME, CONNECTIVITY_NAMESPACE
from .models import TestResult

logger = logging.getLogger(__name__)


class ConnectivityTester:
    """Tester de conectividad usando pod de verificación"""
    
    def __init__(self, namespace: str = CONNECTIVITY_NAMESPACE):
        self.namespace = namespace
        self.pod_name = CONNECTIVITY_POD_NAME
        self.image = CONNECTIVITY_POD_IMAGE
        self.v1 = client.CoreV1Api()
        self.pod_created = False
    
    def create_test_pod(self) -> bool:
        """
        Crea pod de verificación de conectividad
        """
        try:
            # Verificar si pod ya existe
            try:
                self.v1.read_namespaced_pod(self.pod_name, self.namespace)
                logger.info(f"Pod {self.pod_name} already exists")
                self.pod_created = True
                return True
            except ApiException:
                pass
            
            # Crear pod
            pod_manifest = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": self.pod_name,
                    "namespace": self.namespace,
                    "labels": {"app": "health-probe-checker"}
                },
                "spec": {
                    "containers": [{
                        "name": "netshoot",
                        "image": self.image,
                        "command": ["sleep", "3600"],
                        "resources": {
                            "requests": {
                                "cpu": "100m",
                                "memory": "128Mi"
                            },
                            "limits": {
                                "cpu": "200m",
                                "memory": "256Mi"
                            }
                        },
                        "securityContext": {
                            "runAsNonRoot": False,
                            "allowPrivilegeEscalation": False
                        }
                    }],
                    "restartPolicy": "Never"
                }
            }
            
            self.v1.create_namespaced_pod(self.namespace, pod_manifest)
            logger.info(f"Created pod {self.pod_name}")
            
            # Esperar a que pod esté running
            self._wait_for_pod_ready(timeout=60)
            self.pod_created = True
            return True
        
        except Exception as e:
            logger.error(f"Failed to create test pod: {e}")
            return False
    
    def _wait_for_pod_ready(self, timeout: int = 60):
        """Espera a que el pod esté en estado Running"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                pod = self.v1.read_namespaced_pod(self.pod_name, self.namespace)
                if pod.status.phase == "Running":
                    logger.info(f"Pod {self.pod_name} is ready")
                    return
            except ApiException:
                pass
            
            time.sleep(2)
        
        logger.warning(f"Pod {self.pod_name} did not become ready within {timeout}s")
    
    def test_endpoint(self, host: str, port: int, protocol: str = "tcp") -> TestResult:
        """
        Prueba conectividad a un endpoint
        """
        start_time = time.time()
        
        try:
            if protocol.lower() in ["http", "https"]:
                return self._test_http(host, port, protocol, start_time)
            else:
                return self._test_tcp(host, port, start_time)
        
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error(f"Test failed for {host}:{port}: {e}")
            return TestResult(
                host=host,
                port=port,
                protocol=protocol,
                success=False,
                latency_ms=latency,
                timeout=False,
                error_message=str(e)
            )
    
    def _test_http(self, host: str, port: int, protocol: str, start_time: float) -> TestResult:
        """Prueba HTTP/HTTPS"""
        url = f"{protocol}://{host}:{port}"
        
        try:
            cmd = f"curl -s -o /dev/null -w '%{{http_code}}' {url}"
            result = subprocess.run(
                ["kubectl", "exec", self.pod_name, "-n", self.namespace, "--", "sh", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            latency = (time.time() - start_time) * 1000
            status_code = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            
            success = 200 <= status_code < 400
            
            return TestResult(
                host=host,
                port=port,
                protocol=protocol,
                success=success,
                latency_ms=latency,
                timeout=False,
                status_code=status_code
            )
        
        except subprocess.TimeoutExpired:
            latency = (time.time() - start_time) * 1000
            return TestResult(
                host=host,
                port=port,
                protocol=protocol,
                success=False,
                latency_ms=latency,
                timeout=True,
                error_message="Request timeout"
            )
    
    def _test_tcp(self, host: str, port: int, start_time: float) -> TestResult:
        """Prueba TCP"""
        try:
            cmd = f"nc -zv -w 5 {host} {port}"
            result = subprocess.run(
                ["kubectl", "exec", self.pod_name, "-n", self.namespace, "--", "sh", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            latency = (time.time() - start_time) * 1000
            success = result.returncode == 0
            
            return TestResult(
                host=host,
                port=port,
                protocol="tcp",
                success=success,
                latency_ms=latency,
                timeout=False,
                error_message=result.stderr if not success else ""
            )
        
        except subprocess.TimeoutExpired:
            latency = (time.time() - start_time) * 1000
            return TestResult(
                host=host,
                port=port,
                protocol="tcp",
                success=False,
                latency_ms=latency,
                timeout=True,
                error_message="Connection timeout"
            )
    
    def test_dns(self, hostname: str) -> bool:
        """Valida resolución DNS"""
        try:
            cmd = f"dig {hostname} +short"
            result = subprocess.run(
                ["kubectl", "exec", self.pod_name, "-n", self.namespace, "--", "sh", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            success = result.returncode == 0 and result.stdout.strip()
            logger.info(f"DNS resolution for {hostname}: {'OK' if success else 'FAILED'}")
            return success
        
        except Exception as e:
            logger.error(f"DNS test failed for {hostname}: {e}")
            return False
    
    def test_all_endpoints(self, endpoints: List[str], ports: List[int] = None) -> List[TestResult]:
        """Prueba múltiples endpoints"""
        if ports is None:
            ports = [8080, 443, 80]
        
        results = []
        
        for endpoint in endpoints:
            for port in ports:
                result = self.test_endpoint(endpoint, port)
                results.append(result)
                logger.debug(f"Test result: {endpoint}:{port} - {result.status}")
        
        return results
    
    def cleanup_test_pod(self) -> bool:
        """Elimina pod de verificación"""
        if not self.pod_created:
            return True
        
        try:
            self.v1.delete_namespaced_pod(
                self.pod_name,
                self.namespace,
                grace_period_seconds=5
            )
            logger.info(f"Deleted pod {self.pod_name}")
            self.pod_created = False
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete pod {self.pod_name}: {e}")
            return False
