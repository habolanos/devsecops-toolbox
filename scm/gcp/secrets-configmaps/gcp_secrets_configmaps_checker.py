import argparse
import subprocess
import json
import csv
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn
import os

__version__ = "1.1.0"

def get_args():
    parser = argparse.ArgumentParser(description="SRE Tool: Secrets & ConfigMaps Reference Checker (gcloud/kubectl)", add_help=False)
    parser.add_argument(
        "--project",
        type=str,
        default="cpl-xxxx-yyyy-zzzz-99999999",
        help="ID del proyecto de GCP (Default: cpl-xxxx-yyyy-zzzz-99999999)"
    )
    parser.add_argument(
        "--cluster",
        type=str,
        help="Nombre del cluster GKE (si no se especifica, lista todos los clusters)"
    )
    parser.add_argument(
        "--namespace",
        type=str,
        default="",
        help="Namespace específico (Default: todos los namespaces)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa modo debug para ver comandos ejecutados"
    )
    parser.add_argument(
        "--help", "-h",
        action="store_true",
        help="Muestra documentación completa del script"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["csv", "json"],
        help="Exporta resultados a archivo (csv o json) en carpeta outcome/"
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Muestra en detalle los deployments que referencian cada secret/configmap"
    )
    return parser.parse_args()

def show_help():
    """Muestra el README.md con formato enriquecido en consola"""
    console = Console()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(script_dir, "README.md")
    
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
        console.print(Markdown(readme_content))
    else:
        console.print("[yellow]README.md no encontrado[/]")

def run_command(command, debug=False):
    """Ejecuta un comando y retorna el resultado"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        if debug:
            print(f"[DEBUG] Command: {command}")
            print(f"[DEBUG] Return code: {result.returncode}")
            if result.stderr:
                print(f"[DEBUG] Stderr: {result.stderr[:200]}")
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        if debug:
            print(f"[DEBUG] Exception: {e}")
        return None

def run_json_command(command, debug=False):
    """Ejecuta un comando y retorna el resultado como JSON"""
    output = run_command(command, debug)
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return None
    return None

def get_clusters(project_id, debug=False):
    """Obtiene lista de clusters GKE"""
    cmd = f'gcloud container clusters list --project={project_id} --format=json'
    return run_json_command(cmd, debug) or []

def connect_to_cluster(project_id, cluster_name, location, debug=False):
    """Conecta al cluster GKE"""
    location_flag = f'--zone={location}' if location.count('-') == 2 else f'--region={location}'
    cmd = f'gcloud container clusters get-credentials {cluster_name} --project={project_id} {location_flag} --quiet'
    result = run_command(cmd, debug)
    return result is not None or True

def get_namespaces(debug=False):
    """Obtiene lista de namespaces"""
    cmd = 'kubectl get namespaces -o json'
    data = run_json_command(cmd, debug)
    if data and 'items' in data:
        return [ns['metadata']['name'] for ns in data['items']]
    return []

def get_deployments(namespace, debug=False):
    """Obtiene deployments de un namespace"""
    ns_flag = f'-n {namespace}' if namespace else '--all-namespaces'
    cmd = f'kubectl get deployments {ns_flag} -o json'
    data = run_json_command(cmd, debug)
    if data and 'items' in data:
        return data['items']
    return []

def get_configmaps(namespace, debug=False):
    """Obtiene configmaps de un namespace"""
    ns_flag = f'-n {namespace}' if namespace else '--all-namespaces'
    cmd = f'kubectl get configmaps {ns_flag} -o json'
    data = run_json_command(cmd, debug)
    if data and 'items' in data:
        return data['items']
    return []

def get_secrets(namespace, debug=False):
    """Obtiene secrets de un namespace"""
    ns_flag = f'-n {namespace}' if namespace else '--all-namespaces'
    cmd = f'kubectl get secrets {ns_flag} -o json'
    data = run_json_command(cmd, debug)
    if data and 'items' in data:
        return data['items']
    return []

def extract_secret_refs_from_deployment(deployment):
    """Extrae referencias a secrets desde un deployment"""
    secret_refs = []
    configmap_refs = []
    
    spec = deployment.get('spec', {}).get('template', {}).get('spec', {})
    
    for container in spec.get('containers', []):
        for env in container.get('env', []):
            value_from = env.get('valueFrom', {})
            if 'secretKeyRef' in value_from:
                secret_refs.append({
                    'type': 'env',
                    'name': value_from['secretKeyRef'].get('name'),
                    'key': value_from['secretKeyRef'].get('key'),
                    'container': container.get('name')
                })
            if 'configMapKeyRef' in value_from:
                configmap_refs.append({
                    'type': 'env',
                    'name': value_from['configMapKeyRef'].get('name'),
                    'key': value_from['configMapKeyRef'].get('key'),
                    'container': container.get('name')
                })
        
        for env_from in container.get('envFrom', []):
            if 'secretRef' in env_from:
                secret_refs.append({
                    'type': 'envFrom',
                    'name': env_from['secretRef'].get('name'),
                    'key': '*',
                    'container': container.get('name')
                })
            if 'configMapRef' in env_from:
                configmap_refs.append({
                    'type': 'envFrom',
                    'name': env_from['configMapRef'].get('name'),
                    'key': '*',
                    'container': container.get('name')
                })
    
    for volume in spec.get('volumes', []):
        if 'secret' in volume:
            secret_refs.append({
                'type': 'volume',
                'name': volume['secret'].get('secretName'),
                'key': '*',
                'container': 'volume:' + volume.get('name', 'unknown')
            })
        if 'configMap' in volume:
            configmap_refs.append({
                'type': 'volume',
                'name': volume['configMap'].get('name'),
                'key': '*',
                'container': 'volume:' + volume.get('name', 'unknown')
            })
    
    return secret_refs, configmap_refs

def export_to_csv(data, filepath):
    """Exporta los datos a un archivo CSV"""
    if not data:
        return
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def export_to_json(data, filepath, project_id=None, tz_name="America/Mazatlan"):
    """Exporta los datos a un archivo JSON con metadatos completos"""
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    
    export_data = {
        "report_metadata": {
            "tool_name": "GCP Secrets & ConfigMaps Checker",
            "version": __version__,
            "project_id": project_id,
            "generated_at": now.isoformat(),
            "timezone": tz_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "summary": {
            "total_deployments": len(set(r['deployment'] for r in data)),
            "total_secrets": len(set(r['ref_name'] for r in data if r['ref_type'] == 'secret')),
            "total_configmaps": len(set(r['ref_name'] for r in data if r['ref_type'] == 'configmap')),
            "found": sum(1 for r in data if r['status'] == 'FOUND'),
            "missing": sum(1 for r in data if r['status'] == 'MISSING')
        },
        "references": data
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

def print_summary(console, results):
    """Imprime resumen ejecutivo"""
    total_deployments = len(set(r['deployment'] for r in results))
    total_secrets = len(set(r['ref_name'] for r in results if r['ref_type'] == 'secret'))
    total_configmaps = len(set(r['ref_name'] for r in results if r['ref_type'] == 'configmap'))
    missing = sum(1 for r in results if r['status'] == 'MISSING')
    found = sum(1 for r in results if r['status'] == 'FOUND')
    
    summary_text = (
        f"[bold cyan]📦 Deployments: {total_deployments}[/]  "
        f"[bold magenta]🔐 Secrets: {total_secrets}[/]  "
        f"[bold blue]📄 ConfigMaps: {total_configmaps}[/]  "
        f"[bold green]✅ Found: {found}[/]  "
        f"[bold red]❌ Missing: {missing}[/]"
    )
    
    console.print(Panel(summary_text, title="📊 Resumen Ejecutivo", border_style="blue", expand=False))

def print_reference_counts(console, results, show_details=False):
    """Imprime resumen de cantidad de referencias por secret/configmap en orden descendente"""
    from collections import Counter, defaultdict
    
    secret_counts = Counter((r['namespace'], r['ref_name']) for r in results if r['ref_type'] == 'secret')
    configmap_counts = Counter((r['namespace'], r['ref_name']) for r in results if r['ref_type'] == 'configmap')
    
    secret_refs_detail = defaultdict(list)
    configmap_refs_detail = defaultdict(list)
    
    for r in results:
        usage_type = r.get('usage_type', 'env')
        detail = f"{r['deployment']} ({usage_type})"
        key = (r['namespace'], r['ref_name'])
        if r['ref_type'] == 'secret':
            secret_refs_detail[key].append(detail)
        else:
            configmap_refs_detail[key].append(detail)
    
    def get_ref_semaphore(count):
        """Retorna semáforo basado en cantidad de referencias"""
        if count >= 5:
            return "[bold white on red] ALTO [/]"
        elif count >= 2:
            return "[bold black on yellow] MEDIO [/]"
        return "[bold white on green] BAJO [/]"
    
    if secret_counts:
        secrets_table = Table(
            title="🔐 Secrets - Cantidad de Referencias",
            title_style="bold magenta",
            header_style="bold cyan",
            border_style="dim"
        )
        secrets_table.add_column("Namespace", style="cyan")
        secrets_table.add_column("Secret", style="magenta")
        secrets_table.add_column("Refs", justify="right")
        secrets_table.add_column("Semáforo", justify="center")
        secrets_table.add_column("Barra", justify="left")
        if show_details:
            secrets_table.add_column("Referenciado por (tipo)", style="dim")
        
        max_count = max(secret_counts.values()) if secret_counts else 1
        for (namespace, name), count in sorted(secret_counts.items(), key=lambda x: x[1], reverse=True):
            bar_len = int((count / max_count) * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            key = (namespace, name)
            if show_details:
                refs = ", ".join(sorted(set(secret_refs_detail[key])))
                secrets_table.add_row(namespace, name, str(count), get_ref_semaphore(count), f"[magenta]{bar}[/]", refs)
            else:
                secrets_table.add_row(namespace, name, str(count), get_ref_semaphore(count), f"[magenta]{bar}[/]")
        
        console.print(secrets_table)
    
    if configmap_counts:
        configmaps_table = Table(
            title="📄 ConfigMaps - Cantidad de Referencias",
            title_style="bold blue",
            header_style="bold cyan",
            border_style="dim"
        )
        configmaps_table.add_column("Namespace", style="cyan")
        configmaps_table.add_column("ConfigMap", style="blue")
        configmaps_table.add_column("Refs", justify="right")
        configmaps_table.add_column("Semáforo", justify="center")
        configmaps_table.add_column("Barra", justify="left")
        if show_details:
            configmaps_table.add_column("Referenciado por (tipo)", style="dim")
        
        max_count = max(configmap_counts.values()) if configmap_counts else 1
        for (namespace, name), count in sorted(configmap_counts.items(), key=lambda x: x[1], reverse=True):
            bar_len = int((count / max_count) * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            key = (namespace, name)
            if show_details:
                refs = ", ".join(sorted(set(configmap_refs_detail[key])))
                configmaps_table.add_row(namespace, name, str(count), get_ref_semaphore(count), f"[blue]{bar}[/]", refs)
            else:
                configmaps_table.add_row(namespace, name, str(count), get_ref_semaphore(count), f"[blue]{bar}[/]")
        
        console.print(configmaps_table)

def main():
    args = get_args()
    
    if args.help:
        show_help()
        return
    
    project_id = args.project
    console = Console()
    
    revision_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    console.print(f"\n[bold blue]🔍 Iniciando análisis de Secrets y ConfigMaps en:[/] [white underline]{project_id}[/]")
    console.print(f"[dim]🕐 Fecha y hora de revisión: {revision_time}[/]\n")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Recolectando clusters y recursos...", total=None)
            if args.cluster:
                clusters = [{'name': args.cluster, 'location': ''}]
                clusters_data = get_clusters(project_id, args.debug)
                for c in clusters_data:
                    if c.get('name') == args.cluster:
                        clusters = [c]
                        break
            else:
                clusters = get_clusters(project_id, args.debug)
        
        if not clusters:
            console.print(f"[yellow]⚠️  No se detectaron clusters GKE en {project_id}.[/]")
            return

        all_results = []
        
        for cluster in clusters:
            cluster_name = cluster.get('name', 'UNKNOWN')
            location = cluster.get('location', '')
            
            console.print(f"\n[bold cyan]☸️  Procesando cluster:[/] {cluster_name}")
            
            if location:
                connect_to_cluster(project_id, cluster_name, location, args.debug)
            
            namespaces = [args.namespace] if args.namespace else get_namespaces(args.debug)
            namespaces = [ns for ns in namespaces if not ns.startswith('kube-')]
            
            for namespace in namespaces:
                deployments = get_deployments(namespace, args.debug)
                secrets = get_secrets(namespace, args.debug)
                configmaps = get_configmaps(namespace, args.debug)
                
                secret_names = {s['metadata']['name'] for s in secrets}
                configmap_names = {c['metadata']['name'] for c in configmaps}
                
                for deployment in deployments:
                    deploy_name = deployment['metadata']['name']
                    deploy_ns = deployment['metadata'].get('namespace', namespace)
                    
                    secret_refs, configmap_refs = extract_secret_refs_from_deployment(deployment)
                    
                    for ref in secret_refs:
                        status = 'FOUND' if ref['name'] in secret_names else 'MISSING'
                        all_results.append({
                            'cluster': cluster_name,
                            'namespace': deploy_ns,
                            'deployment': deploy_name,
                            'ref_type': 'secret',
                            'ref_name': ref['name'],
                            'ref_key': ref['key'],
                            'usage_type': ref['type'],
                            'container': ref['container'],
                            'status': status,
                            'revision_time': revision_time
                        })
                    
                    for ref in configmap_refs:
                        status = 'FOUND' if ref['name'] in configmap_names else 'MISSING'
                        all_results.append({
                            'cluster': cluster_name,
                            'namespace': deploy_ns,
                            'deployment': deploy_name,
                            'ref_type': 'configmap',
                            'ref_name': ref['name'],
                            'ref_key': ref['key'],
                            'usage_type': ref['type'],
                            'container': ref['container'],
                            'status': status,
                            'revision_time': revision_time
                        })

        if not all_results:
            console.print(f"\n[yellow]⚠️  No se encontraron referencias a Secrets o ConfigMaps en los deployments.[/]")
            return
        
        table = Table(
            title="🔐 Referencias de Secrets y ConfigMaps en Deployments",
            title_style="bold magenta",
            header_style="bold cyan",
            border_style="dim"
        )
        
        table.add_column("Cluster", style="white")
        table.add_column("Namespace", justify="center")
        table.add_column("Deployment", style="white")
        table.add_column("Tipo", justify="center")
        table.add_column("Nombre Ref", style="cyan")
        table.add_column("Key", justify="center")
        table.add_column("Uso", justify="center")
        table.add_column("Estado", justify="center")

        for result in sorted(all_results, key=lambda x: (x['cluster'], x['namespace'], x['deployment'])):
            ref_type_display = "[magenta]SECRET[/]" if result['ref_type'] == 'secret' else "[blue]CONFIGMAP[/]"
            status_display = "[green]FOUND[/]" if result['status'] == 'FOUND' else "[red]MISSING[/]"
            row_style = "red" if result['status'] == 'MISSING' else ""
            
            table.add_row(
                result['cluster'],
                result['namespace'],
                result['deployment'],
                ref_type_display,
                result['ref_name'],
                result['ref_key'],
                result['usage_type'],
                status_display,
                style=row_style
            )
        
        console.print(table)
        print_summary(console, all_results)
        print_reference_counts(console, all_results, args.details)
        
        if args.output and all_results:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            outcome_dir = os.path.join(script_dir, 'outcome')
            os.makedirs(outcome_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"secrets_configmaps_{project_id}_{timestamp}"
            
            if args.output == 'csv':
                filepath = os.path.join(outcome_dir, f"{filename}.csv")
                export_to_csv(all_results, filepath)
            elif args.output == 'json':
                filepath = os.path.join(outcome_dir, f"{filename}.json")
                export_to_json(all_results, filepath, project_id)
            
            console.print(f"\n[bold green]📁 Archivo exportado:[/] {filepath}")
        
        missing_refs = [r for r in all_results if r['status'] == 'MISSING']
        if missing_refs:
            console.print(f"\n[bold red]⚠️  Se encontraron {len(missing_refs)} referencias faltantes![/]")
        else:
            console.print(f"\n[bold green]✅ Todas las referencias están correctamente vinculadas.[/]")

    except Exception as e:
        console.print(f"[bold red]❌ Error:[/]\n{e}")

if __name__ == "__main__":
    main()
