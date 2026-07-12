"""
Health Probe Masivo Validator - Orquestador principal
"""
import argparse
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List

from rich.console import Console

from .azdo_parser import AzDOParser, parse_input
from .config import (
    AZDO_ORG, AZDO_PAT, AZDO_PROJECT, K8S_KUBECONFIG, LOG_FILE,
    LOG_LEVEL, MAX_WORKERS, OUTPUT_DIR, TIMEOUT
)
from .connectivity_tester import ConnectivityTester
from .k8s_checker import K8sChecker
from .models import DeploymentInput, HealthCheckResult
from .reporter import HealthProbeReporter

# Configurar logging
os.makedirs(OUTPUT_DIR, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
console = Console()


class HealthProbeValidator:
    """Orquestador principal de validación"""
    
    def __init__(self, azdo_pat: str = AZDO_PAT, kubeconfig: str = K8S_KUBECONFIG,
                 workers: int = MAX_WORKERS, timeout: int = TIMEOUT):
        self.azdo_parser = AzDOParser(AZDO_ORG, AZDO_PROJECT, azdo_pat)
        self.k8s_checker = K8sChecker(kubeconfig)
        self.connectivity_tester = ConnectivityTester()
        self.workers = workers
        self.timeout = timeout
    
    def validate_deployments(self, input_str: str) -> List[HealthCheckResult]:
        """
        Flujo principal de validación
        """
        console.print("[bold cyan]🏥 Health Probe Masivo Validator[/bold cyan]\n")
        
        # 1. Parsear entrada
        console.print("[bold]1. Parsing input...[/bold]")
        deployments = parse_input(input_str)
        console.print(f"   ✅ Parsed {len(deployments)} deployment(s)\n")
        
        # 2. Crear pod de verificación
        console.print("[bold]2. Creating connectivity test pod...[/bold]")
        if not self.connectivity_tester.create_test_pod():
            console.print("   ⚠️ Failed to create test pod, continuing without connectivity tests\n")
        else:
            console.print("   ✅ Test pod created\n")
        
        # 3. Validar deployments en paralelo
        console.print(f"[bold]3. Validating {len(deployments)} deployment(s) (workers={self.workers})...[/bold]")
        results = []
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self._validate_single, dep): dep
                for dep in deployments
            }
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                deployment = futures[future]
                try:
                    result = future.result(timeout=self.timeout)
                    if result:
                        results.append(result)
                        console.print(f"   [{completed}/{len(deployments)}] {result.deployment}: {result.overall_status}")
                except Exception as e:
                    logger.error(f"Failed to validate {deployment.name}: {e}")
                    console.print(f"   [{completed}/{len(deployments)}] {deployment.name}: ❌ ERROR")
        
        console.print()
        
        # 4. Limpiar pod de verificación
        console.print("[bold]4. Cleaning up...[/bold]")
        self.connectivity_tester.cleanup_test_pod()
        console.print("   ✅ Cleanup complete\n")
        
        return results
    
    def _validate_single(self, deployment: DeploymentInput) -> HealthCheckResult:
        """Valida un deployment individual"""
        try:
            # Obtener info de AZDO
            if deployment.definition_id:
                stages = self.azdo_parser.get_stages(deployment.definition_id)
                stage = stages[0] if stages else None
            else:
                stage = None
            
            # Validar K8s
            namespace = deployment.namespace
            pod_status = self.k8s_checker.check_deployment(deployment.name, namespace)
            
            if not pod_status:
                return HealthCheckResult(
                    deployment=deployment.name,
                    stage=stage.name if stage else "Unknown",
                    pod_status="NotReady",
                    pod_count=0,
                    ready_count=0,
                    liveness_probe=False,
                    readiness_probe=False,
                    connectivity="FAILED",
                    latency_ms=0,
                    errors=[f"Deployment {deployment.name} not found"],
                    recommendations=["Create deployment or check namespace"]
                )
            
            # Validar probes
            pods = self.k8s_checker.check_pods(deployment.name, namespace)
            probes = None
            if pods:
                probes = self.k8s_checker.check_health_probes(pods[0].name, namespace)
            
            # Pruebas de conectividad
            connectivity = "OK"
            latency_ms = 0
            
            if stage and self.connectivity_tester.pod_created:
                test_results = self.connectivity_tester.test_all_endpoints(
                    stage.endpoints,
                    stage.ports
                )
                
                if test_results:
                    success_count = sum(1 for t in test_results if t.success)
                    connectivity = "OK" if success_count == len(test_results) else "FAILED"
                    latency_ms = sum(t.latency_ms for t in test_results) / len(test_results)
            
            # Generar recomendaciones
            recommendations = self._generate_recommendations(
                pod_status, probes, connectivity
            )
            
            return HealthCheckResult(
                deployment=deployment.name,
                stage=stage.name if stage else "Unknown",
                pod_status=pod_status.status,
                pod_count=pod_status.replicas,
                ready_count=pod_status.ready_replicas,
                liveness_probe=probes.liveness_configured if probes else False,
                readiness_probe=probes.readiness_configured if probes else False,
                connectivity=connectivity,
                latency_ms=latency_ms,
                recommendations=recommendations
            )
        
        except Exception as e:
            logger.error(f"Error validating {deployment.name}: {e}")
            return HealthCheckResult(
                deployment=deployment.name,
                stage="Unknown",
                pod_status="Unknown",
                pod_count=0,
                ready_count=0,
                liveness_probe=False,
                readiness_probe=False,
                connectivity="FAILED",
                latency_ms=0,
                errors=[str(e)],
                recommendations=["Check logs for details"]
            )
    
    def _generate_recommendations(self, pod_status, probes, connectivity) -> List[str]:
        """Genera recomendaciones basadas en estado"""
        recommendations = []
        
        if pod_status.status != "Ready":
            recommendations.append("Scale up deployment or check pod logs")
        
        if probes and not probes.is_healthy:
            recommendations.append("Configure or fix health probes")
        
        if connectivity == "FAILED":
            recommendations.append("Check network connectivity and firewall rules")
        
        if not recommendations:
            recommendations.append("Deployment is healthy")
        
        return recommendations


def main():
    """Punto de entrada principal"""
    parser = argparse.ArgumentParser(
        description="Health Probe Masivo Validator - Validación masiva de health probes en K8s"
    )
    
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input: deployments CSV o definition IDs (e.g., 'web-prod,api-prod' o 'definitionId=3388')"
    )
    parser.add_argument(
        "-o", "--output",
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "-n", "--namespace",
        default="default",
        help="Kubernetes namespace (default: default)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"Number of parallel workers (default: {MAX_WORKERS})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT,
        help=f"Timeout per deployment in seconds (default: {TIMEOUT})"
    )
    parser.add_argument(
        "--format",
        default="json,csv,html,excel",
        help="Export formats: json,csv,html,excel (default: all)"
    )
    parser.add_argument(
        "--skip-connectivity",
        action="store_true",
        help="Skip connectivity tests"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging"
    )
    
    args = parser.parse_args()
    
    try:
        # Crear validador
        validator = HealthProbeValidator(
            workers=args.workers,
            timeout=args.timeout
        )
        
        # Validar deployments
        results = validator.validate_deployments(args.input)
        
        if not results:
            console.print("[red]❌ No results to report[/red]")
            return 1
        
        # Generar reportes
        reporter = HealthProbeReporter(results, console)
        
        # Mostrar tabla
        console.print("[bold cyan]📊 Summary Table:[/bold cyan]\n")
        reporter.print_summary_table()
        
        # Exportar
        console.print("\n[bold cyan]📤 Exporting reports...[/bold cyan]\n")
        formats = [f.strip() for f in args.format.split(",")]
        
        if "json" in formats:
            reporter.to_json(os.path.join(args.output, "health_probe_report.json"))
        if "csv" in formats:
            reporter.to_csv(os.path.join(args.output, "health_probe_report.csv"))
        if "html" in formats:
            reporter.to_html(os.path.join(args.output, "health_probe_report.html"))
        if "excel" in formats:
            reporter.to_excel(os.path.join(args.output, "health_probe_report.xlsx"))
        
        # Mostrar recomendaciones
        recommendations = reporter.generate_recommendations()
        console.print("\n[bold cyan]💡 Recommendations:[/bold cyan]")
        for rec in recommendations:
            console.print(f"  {rec}")
        
        console.print(f"\n[green]✅ Validation complete[/green]")
        return 0
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        console.print(f"[red]❌ Error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
