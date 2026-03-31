#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Repository Vulnerabilities Scanner

Escanea archivos package.json en repositorios buscando dependencias vulnerables
conocidas en las ramas críticas (develop, QA, master, main).

Uso:
    python azdo_scan_repos_vulnerabilities.py --pat <PAT> --org <ORG> --project <PROJECT>
    python azdo_scan_repos_vulnerabilities.py --pat <PAT> --targets "axios:1.14.1,plain-crypto-js"
"""

import os
import sys
import json
import base64
import argparse
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Optional, Tuple, Set

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.2.0"
__author__ = "Harold Adrian"

API_VERSION = "7.1-preview.1"
BASE_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = BASE_DIR / "config.json"
OUTCOME_DIR = BASE_DIR / "outcome"

DEFAULT_BRANCHES = ["develop", "QA", "master", "main"]
DEFAULT_TARGETS = {
    "axios": {"1.14.1", "0.30.4"},
    "plain-crypto-js": None,
}


def load_config() -> Dict:
    """Carga configuración desde config.json si existe."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def parse_targets(targets_str: str) -> Dict[str, Optional[Set[str]]]:
    """Parsea string de targets a diccionario."""
    targets = {}
    for item in targets_str.split(","):
        item = item.strip()
        if ":" in item:
            pkg, versions = item.split(":", 1)
            targets[pkg.strip()] = set(v.strip() for v in versions.split("|"))
        else:
            targets[item] = None
    return targets


def get_args():
    config = load_config()
    org_config = config.get("organization", {})
    defaults_config = config.get("defaults", {})
    tool_config = config.get("tools", {}).get("scan_repos_vulnerabilities", {})

    default_org = org_config.get("url", "").replace("https://dev.azure.com/", "")
    default_project = org_config.get("project", "")
    default_pat = org_config.get("pat", "") or os.getenv("AZDO_PAT", "")
    default_branches = tool_config.get("branches", DEFAULT_BRANCHES)
    default_targets = tool_config.get("targets", DEFAULT_TARGETS)

    parser = argparse.ArgumentParser(
        description="Azure DevOps Repo Vulnerabilities Scanner - Busca dependencias vulnerables en package.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python azdo_scan_repos_vulnerabilities.py --pat <PAT> --org Coppel-Retail --project MiProyecto
  python azdo_scan_repos_vulnerabilities.py --pat <PAT> --targets "axios:1.14.1|0.30.4,plain-crypto-js"
  python azdo_scan_repos_vulnerabilities.py --pat <PAT> --branches "master,main,develop" --output csv

Formato de targets:
  - "paquete:version1|version2" - detecta versiones específicas
  - "paquete" - detecta cualquier versión del paquete
        """
    )
    parser.add_argument("--pat", type=str, default=default_pat,
                        help="Personal Access Token de Azure DevOps")
    parser.add_argument("--org", "-g", type=str, default=default_org,
                        help=f"Organización de Azure DevOps (default: {default_org or 'desde config.json'})")
    parser.add_argument("--project", "-p", type=str, default=default_project,
                        help=f"Proyecto de Azure DevOps (default: {default_project or 'desde config.json'})")
    parser.add_argument("--branches", type=str, default=None,
                        help=f"Ramas a revisar separadas por coma (default: {','.join(default_branches)})")
    parser.add_argument("--targets", type=str, default=None,
                        help="Dependencias a buscar en formato 'pkg:v1|v2,pkg2' (default: axios, plain-crypto-js)")
    parser.add_argument("--repo", "-r", type=str, default=None,
                        help="Filtrar por nombre de repositorio (substring)")
    parser.add_argument("--output", "-o", type=str, choices=["json", "csv"],
                        help="Exportar resultados a archivo en outcome/")
    parser.add_argument("--debug", action="store_true",
                        help="Mostrar información de debug")
    parser.add_argument("--help-config", action="store_true",
                        help="Mostrar ejemplo de configuración para config.json")

    args = parser.parse_args()

    if args.help_config:
        print_config_help()
        sys.exit(0)

    if args.branches:
        args.branches = [b.strip() for b in args.branches.split(",")]
    else:
        args.branches = default_branches

    if args.targets:
        args.targets = parse_targets(args.targets)
    else:
        if isinstance(default_targets, dict):
            args.targets = {k: set(v) if isinstance(v, list) else v for k, v in default_targets.items()}
        else:
            args.targets = DEFAULT_TARGETS

    if not args.pat:
        parser.error("--pat es requerido. Puedes configurarlo en config.json o variable AZDO_PAT")
    if not args.org:
        parser.error("--org es requerido. Configúralo en config.json o pásalo como argumento")
    if not args.project:
        parser.error("--project es requerido. Configúralo en config.json o pásalo como argumento")

    return args


def print_config_help():
    """Muestra ejemplo de configuración para config.json."""
    example = '''
Añade esta sección a tu config.json bajo "tools":

"scan_repos_vulnerabilities": {
    "_info": "azdo_scan_repos_vulnerabilities.py — Escanea dependencias vulnerables en repos.",
    "branches": ["develop", "QA", "master", "main"],
    "targets": {
        "axios": ["1.14.1", "0.30.4"],
        "plain-crypto-js": null
    }
}

Nota: Si "targets[paquete]" es null, detecta cualquier versión del paquete.
'''
    print(example)


def get_headers(pat: str) -> Dict[str, str]:
    token = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def build_session(headers: Dict[str, str]) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(headers)
    return session


def get_repositories(session: requests.Session, org: str, project: str) -> List[Dict]:
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories?api-version={API_VERSION}"
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.json().get("value", [])


def branch_exists(session: requests.Session, org: str, project: str, repo_id: str, branch: str) -> bool:
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/refs"
        f"?filter=heads/{branch}&api-version={API_VERSION}"
    )
    response = session.get(url, timeout=60)
    response.raise_for_status()
    values = response.json().get("value", [])
    target_ref = f"refs/heads/{branch}"
    return any(ref.get("name") == target_ref for ref in values)


def list_repo_items(session: requests.Session, org: str, project: str, repo_id: str, branch: str) -> List[Dict]:
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/items"
        f"?scopePath=/&recursionLevel=full&includeContentMetadata=true"
        f"&versionDescriptor.versionType=branch&versionDescriptor.version={branch}"
        f"&api-version={API_VERSION}"
    )
    response = session.get(url, timeout=120)
    response.raise_for_status()
    return response.json().get("value", [])


def get_file_content(session: requests.Session, org: str, project: str, repo_id: str, path: str, branch: str) -> Optional[str]:
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}/items"
        f"?path={path}&includeContent=true"
        f"&versionDescriptor.versionType=branch&versionDescriptor.version={branch}"
        f"&api-version={API_VERSION}"
    )
    response = session.get(url, timeout=60)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.text


def normalize_version(version: str) -> str:
    return version.strip().lstrip("^~<>= ")


def analyze_package_json(content: str, targets: Dict[str, Optional[Set[str]]]) -> List[Dict]:
    try:
        package_json = json.loads(content)
    except json.JSONDecodeError:
        return []

    dependency_sections = [
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ]

    findings = []

    for section in dependency_sections:
        deps = package_json.get(section, {})
        if not isinstance(deps, dict):
            continue

        for pkg_name, allowed_versions in targets.items():
            if pkg_name in deps:
                raw_version = deps[pkg_name]
                normalized = normalize_version(raw_version)
                
                if allowed_versions is None:
                    findings.append({
                        "dependency": pkg_name,
                        "version_found": raw_version,
                        "normalized_version": normalized,
                        "dependency_section": section,
                    })
                elif normalized in allowed_versions:
                    findings.append({
                        "dependency": pkg_name,
                        "version_found": raw_version,
                        "normalized_version": normalized,
                        "dependency_section": section,
                    })

    return findings


def get_repo_url(org: str, project: str, repo_name: str) -> str:
    return f"https://dev.azure.com/{org}/{project}/_git/{repo_name}"


def print_row(row: Dict) -> None:
    print(
        f"[MATCH] project={row['project']} | repo={row['repository']} | branch={row['branch']} | "
        f"path={row['package_json_path']} | dependency={row['dependency']} | "
        f"version={row['version_found']} | section={row['dependency_section']}"
    )


def export_results(rows: List[Dict], output_format: str) -> None:
    """Exporta resultados a archivo."""
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"scan_repos_vulnerabilities_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": timestamp, "total_matches": len(rows), "results": rows}, f, indent=2)
    elif output_format == "csv":
        filepath = OUTCOME_DIR / f"scan_repos_vulnerabilities_{timestamp}.csv"
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False, encoding="utf-8")
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def collect_rows(args) -> Tuple[List[Dict], pd.DataFrame]:
    headers = get_headers(args.pat)
    session = build_session(headers)
    rows: List[Dict] = []
    console = Console() if RICH_AVAILABLE else None
    matches_count = 0

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]Azure DevOps Repo Vulnerabilities Scanner[/bold cyan]\n"
            f"Org: [yellow]{args.org}[/yellow] | Project: [yellow]{args.project}[/yellow]\n"
            f"Ramas: [green]{', '.join(args.branches)}[/green]\n"
            f"Targets: [magenta]{', '.join(args.targets.keys())}[/magenta]"
            + (f"\nFiltro repo: [blue]{args.repo}[/blue]" if args.repo else ""),
            title="🛡️ Scan Config"
        ))
    else:
        print(f"Organización: {args.org}")
        print(f"Proyecto: {args.project}")
        print(f"Ramas objetivo: {', '.join(args.branches)}")
        print(f"Dependencias a buscar: {', '.join(args.targets.keys())}")
        if args.repo:
            print(f"Filtro de repositorio: {args.repo}")
        print("Iniciando consulta...\n")

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task("[cyan]Obteniendo lista de repositorios...", total=None)
            repositories = get_repositories(session, args.org, args.project)
    else:
        repositories = get_repositories(session, args.org, args.project)
    
    if args.repo:
        repositories = [r for r in repositories if args.repo.lower() in r["name"].lower()]
    
    if RICH_AVAILABLE:
        console.print(f"✅ Repositorios a revisar: [bold green]{len(repositories)}[/bold green]")
    else:
        print(f"Total repositorios a revisar: {len(repositories)}\n")

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[green]Matches: {task.fields[matches]}[/green]"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Escaneando repositorios...", 
                total=len(repositories),
                matches=0
            )
            
            for repo in repositories:
                repo_name = repo["name"]
                repo_id = repo["id"]
                repo_url = repo.get("webUrl") or get_repo_url(args.org, args.project, repo_name)
                
                progress.update(task, description=f"[cyan]Repo: {repo_name[:35]}...")

                existing_branches = []
                for branch in args.branches:
                    try:
                        if branch_exists(session, args.org, args.project, repo_id, branch):
                            existing_branches.append(branch)
                    except Exception as e:
                        if args.debug:
                            console.print(f"[red]  Error rama {branch}: {e}[/red]")

                if not existing_branches:
                    progress.advance(task)
                    continue

                for branch in existing_branches:
                    try:
                        items = list_repo_items(session, args.org, args.project, repo_id, branch)
                    except Exception as e:
                        if args.debug:
                            console.print(f"[red]  Error listando {branch}: {e}[/red]")
                        continue

                    package_files = [
                        item["path"]
                        for item in items
                        if item.get("gitObjectType") == "blob" and item["path"].endswith("package.json")
                    ]

                    if not package_files:
                        continue

                    for package_path in package_files:
                        try:
                            content = get_file_content(session, args.org, args.project, repo_id, package_path, branch)
                            if not content:
                                continue

                            findings = analyze_package_json(content, args.targets)

                            if not findings:
                                continue

                            for finding in findings:
                                row = {
                                    "organization": args.org,
                                    "project": args.project,
                                    "repository": repo_name,
                                    "branch": branch,
                                    "package_json_path": package_path,
                                    "dependency": finding["dependency"],
                                    "version_found": finding["version_found"],
                                    "normalized_version": finding["normalized_version"],
                                    "dependency_section": finding["dependency_section"],
                                    "repository_url": repo_url,
                                }
                                rows.append(row)
                                matches_count += 1
                                progress.update(task, matches=matches_count)
                        except Exception as e:
                            if args.debug:
                                console.print(f"[red]  Error {package_path}: {e}[/red]")

                progress.advance(task)
    else:
        for repo in repositories:
            repo_name = repo["name"]
            repo_id = repo["id"]
            repo_url = repo.get("webUrl") or get_repo_url(args.org, args.project, repo_name)

            print(f"Repositorio: {repo_name}")

            existing_branches = []
            for branch in args.branches:
                try:
                    if branch_exists(session, args.org, args.project, repo_id, branch):
                        existing_branches.append(branch)
                except Exception as e:
                    if args.debug:
                        print(f"  Error consultando rama {branch}: {e}")

            if not existing_branches:
                print(f"  No existen ramas {', '.join(args.branches)} en este repo\n")
                continue

            print(f"  Ramas a revisar: {', '.join(existing_branches)}")

            for branch in existing_branches:
                if args.debug:
                    print(f"  Consultando rama: {branch}")
                try:
                    items = list_repo_items(session, args.org, args.project, repo_id, branch)
                except Exception as e:
                    if args.debug:
                        print(f"    Error listando archivos en rama {branch}: {e}")
                    continue

                package_files = [
                    item["path"]
                    for item in items
                    if item.get("gitObjectType") == "blob" and item["path"].endswith("package.json")
                ]

                if not package_files:
                    if args.debug:
                        print(f"    Sin package.json en rama {branch}")
                    continue

                if args.debug:
                    print(f"    package.json encontrados: {len(package_files)}")

                for package_path in package_files:
                    try:
                        content = get_file_content(session, args.org, args.project, repo_id, package_path, branch)
                        if not content:
                            continue

                        findings = analyze_package_json(content, args.targets)

                        if not findings:
                            continue

                        for finding in findings:
                            row = {
                                "organization": args.org,
                                "project": args.project,
                                "repository": repo_name,
                                "branch": branch,
                                "package_json_path": package_path,
                                "dependency": finding["dependency"],
                                "version_found": finding["version_found"],
                                "normalized_version": finding["normalized_version"],
                                "dependency_section": finding["dependency_section"],
                                "repository_url": repo_url,
                            }
                            rows.append(row)
                            print_row(row)
                    except Exception as e:
                        if args.debug:
                            print(f"    Error procesando {package_path} en rama {branch}: {e}")

            print()

    results_table = pd.DataFrame(rows, columns=[
        "organization",
        "project",
        "repository",
        "branch",
        "package_json_path",
        "dependency",
        "version_found",
        "normalized_version",
        "dependency_section",
        "repository_url",
    ]) if rows else pd.DataFrame()
    
    return rows, results_table, console if RICH_AVAILABLE else None


def main() -> None:
    start_time = time.time()
    args = get_args()
    result = collect_rows(args)
    rows, results_table = result[0], result[1]
    console = result[2] if len(result) > 2 else None
    
    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    if RICH_AVAILABLE and console:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total de coincidencias encontradas:[/bold] [green]{len(rows)}[/green]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print("\n=== RESUMEN ===")
        print(f"Total de registros encontrados: {len(rows)}")
        print(f"Tiempo de ejecución: {time_str}")
    
    if not results_table.empty:
        print("\n=== TABLA FINAL ===")
        print(results_table.to_string(index=False))
        
        if args.output:
            export_results(rows, args.output)
    else:
        if RICH_AVAILABLE and console:
            console.print("[yellow]Sin coincidencias[/yellow]")
        else:
            print("Sin coincidencias")


if __name__ == "__main__":
    main()

