#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure DevOps Pipeline Logs Scanner

Escanea los logs de pipelines CI buscando términos específicos relacionados
con vulnerabilidades de dependencias (axios, plain-crypto-js, etc.).

Uso:
    python azdo_scan_pipeline_logs.py --pat <PAT> --org <ORG> --project <PROJECT>
    python azdo_scan_pipeline_logs.py --pat <PAT> --search-terms "axios@1.14.1,plain-crypto-js"
"""

import os
import re
import sys
import json
import base64
import argparse
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.2.0"
__author__ = "Harold Adrian"

API_VERSION = "7.1-preview.7"
BASE_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = BASE_DIR / "config.json"
OUTCOME_DIR = BASE_DIR / "outcome"

DEFAULT_SEARCH_TERMS = [
    "axios@1.14.1",
    "axios@0.30.4",
    "plain-crypto-js",
]
DEFAULT_CONTEXT_TERMS = [
    "vulnerab",
    "npm audit",
    "critical",
    "high",
    "package.json",
    "dependency",
]


def load_config() -> Dict:
    """Carga configuración desde config.json si existe."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def get_args():
    config = load_config()
    org_config = config.get("organization", {})
    defaults_config = config.get("defaults", {})
    tool_config = config.get("tools", {}).get("scan_pipeline_logs", {})

    default_org = org_config.get("url", "").replace("https://dev.azure.com/", "")
    default_project = org_config.get("project", "")
    default_pat = org_config.get("pat", "") or os.getenv("AZDO_PAT", "")
    default_threads = tool_config.get("threads", defaults_config.get("threads", 10))
    default_top_runs = tool_config.get("top_runs", 50)
    default_search_terms = tool_config.get("search_terms", DEFAULT_SEARCH_TERMS)
    default_context_terms = tool_config.get("context_terms", DEFAULT_CONTEXT_TERMS)

    parser = argparse.ArgumentParser(
        description="Azure DevOps Pipeline Logs Scanner - Busca vulnerabilidades en logs de CI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python azdo_scan_pipeline_logs.py --pat <PAT> --org Coppel-Retail --project MiProyecto
  python azdo_scan_pipeline_logs.py --pat <PAT> --search-terms "axios@1.14.1,plain-crypto-js"
  python azdo_scan_pipeline_logs.py --pat <PAT> --top-runs 100 --threads 15 --output csv
        """
    )
    parser.add_argument("--pat", type=str, default=default_pat,
                        help="Personal Access Token de Azure DevOps")
    parser.add_argument("--org", "-g", type=str, default=default_org,
                        help=f"Organización de Azure DevOps (default: {default_org or 'desde config.json'})")
    parser.add_argument("--project", "-p", type=str, default=default_project,
                        help=f"Proyecto de Azure DevOps (default: {default_project or 'desde config.json'})")
    parser.add_argument("--search-terms", type=str, default=None,
                        help=f"Términos a buscar separados por coma (default: {','.join(default_search_terms)})")
    parser.add_argument("--context-terms", type=str, default=None,
                        help="Términos de contexto separados por coma")
    parser.add_argument("--top-runs", type=int, default=default_top_runs,
                        help=f"Últimas N ejecuciones por pipeline (default: {default_top_runs})")
    parser.add_argument("--threads", type=int, default=default_threads,
                        help=f"Hilos paralelos (default: {default_threads})")
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

    if args.search_terms:
        args.search_terms = [t.strip() for t in args.search_terms.split(",")]
    else:
        args.search_terms = default_search_terms

    if args.context_terms:
        args.context_terms = [t.strip() for t in args.context_terms.split(",")]
    else:
        args.context_terms = default_context_terms

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

"scan_pipeline_logs": {
    "_info": "azdo_scan_pipeline_logs.py — Escanea logs de pipelines CI.",
    "top_runs": 50,
    "threads": 10,
    "search_terms": ["axios@1.14.1", "axios@0.30.4", "plain-crypto-js"],
    "context_terms": ["vulnerab", "npm audit", "critical", "high"]
}
'''
    print(example)


def get_headers(pat: str) -> Dict[str, str]:
    token = base64.b64encode(f":{pat}".encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def build_session(pat: str, max_workers: int) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=max_workers, pool_maxsize=max_workers)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(get_headers(pat))
    return session


def get_build_definitions(session: requests.Session, org: str, project: str) -> List[Dict]:
    definitions = []
    continuation_token = None

    while True:
        url = f"https://dev.azure.com/{org}/{project}/_apis/build/definitions?api-version={API_VERSION}&$top=100"
        headers = {}
        if continuation_token:
            headers["x-ms-continuationtoken"] = continuation_token

        response = session.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        definitions.extend(data.get("value", []))
        continuation_token = response.headers.get("x-ms-continuationtoken")
        if not continuation_token:
            break

    return definitions


def get_build_runs(session: requests.Session, org: str, project: str, definition_id: int, top: int) -> List[Dict]:
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/build/builds"
        f"?definitions={definition_id}&$top={top}&queryOrder=queueTimeDescending&api-version={API_VERSION}"
    )
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.json().get("value", [])


def get_build_logs_metadata(session: requests.Session, org: str, project: str, build_id: int) -> List[Dict]:
    url = f"https://dev.azure.com/{org}/{project}/_apis/build/builds/{build_id}/logs?api-version={API_VERSION}"
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.json().get("value", [])


def get_log_content(session: requests.Session, org: str, project: str, build_id: int, log_id: int) -> str:
    url = f"https://dev.azure.com/{org}/{project}/_apis/build/builds/{build_id}/logs/{log_id}?api-version={API_VERSION}"
    response = session.get(url, timeout=120)
    response.raise_for_status()
    return response.text


def line_matches(line: str, search_terms: List[str]) -> List[str]:
    lowered = line.lower()
    matches = []
    for term in search_terms:
        if term.lower() in lowered:
            matches.append(term)
    return matches


def has_context(line: str, context_terms: List[str]) -> bool:
    lowered = line.lower()
    return any(ctx in lowered for ctx in context_terms)


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def get_build_web_url(org: str, project: str, build_id: int) -> str:
    return f"https://dev.azure.com/{org}/{project}/_build/results?buildId={build_id}"


def analyze_single_run(args, definition: Dict, run: Dict) -> List[Dict]:
    session = build_session(args.pat, args.threads)
    rows: List[Dict] = []

    pipeline_name = definition.get("name", "")
    pipeline_id = definition.get("id", "")
    build_id = run.get("id")
    build_number = run.get("buildNumber", "")
    source_branch = run.get("sourceBranch", "")
    status = run.get("status", "")
    result = run.get("result", "")
    web_url = run.get("_links", {}).get("web", {}).get("href") or get_build_web_url(args.org, args.project, build_id)

    if args.debug:
        print(f"[RUN] pipeline={pipeline_name} | build_id={build_id} | branch={source_branch} | status={status} | result={result}")

    try:
        logs_metadata = get_build_logs_metadata(session, args.org, args.project, build_id)
    except Exception as e:
        if args.debug:
            print(f"  [ERROR] No fue posible obtener logs de build_id={build_id}: {e}")
        return rows

    for log_info in logs_metadata:
        log_id = log_info.get("id")
        try:
            content = get_log_content(session, args.org, args.project, build_id, log_id)
        except Exception as e:
            if args.debug:
                print(f"  [ERROR] build_id={build_id} log_id={log_id}: {e}")
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            found_terms = line_matches(line, args.search_terms)
            if not found_terms:
                continue

            normalized_line = clean_line(line)
            contextual = has_context(normalized_line, args.context_terms)

            for term in found_terms:
                row = {
                    "organization": args.org,
                    "project": args.project,
                    "pipeline_name": pipeline_name,
                    "pipeline_id": pipeline_id,
                    "run_id": build_id,
                    "run_name": build_number,
                    "source_branch": source_branch,
                    "status": status,
                    "result": result,
                    "log_id": log_id,
                    "line_number": line_number,
                    "match_term": term,
                    "context_detected": contextual,
                    "matched_line": normalized_line[:1000],
                    "web_url": web_url,
                }
                rows.append(row)
                print(
                    f"  [MATCH] pipeline={pipeline_name} | run_id={build_id} | log_id={log_id} | "
                    f"line={line_number} | term={term} | context={contextual}"
                )

    return rows


def export_results(rows: List[Dict], output_format: str) -> None:
    """Exporta resultados a archivo."""
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"scan_pipeline_logs_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": timestamp, "total_matches": len(rows), "results": rows}, f, indent=2)
    elif output_format == "csv":
        filepath = OUTCOME_DIR / f"scan_pipeline_logs_{timestamp}.csv"
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False, encoding="utf-8")
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def main() -> None:
    start_time = time.time()
    args = get_args()
    base_session = build_session(args.pat, args.threads)
    all_rows: List[Dict] = []
    console = Console() if RICH_AVAILABLE else None
    matches_count = 0

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]Azure DevOps Pipeline Logs Scanner[/bold cyan]\n"
            f"Org: [yellow]{args.org}[/yellow] | Project: [yellow]{args.project}[/yellow]\n"
            f"Top runs: [green]{args.top_runs}[/green] | Threads: [green]{args.threads}[/green]\n"
            f"Términos: [magenta]{', '.join(args.search_terms)}[/magenta]",
            title="🔍 Scan Config"
        ))
    else:
        print(f"Organización: {args.org}")
        print(f"Proyecto: {args.project}")
        print(f"Top runs por pipeline: {args.top_runs}")
        print(f"Máximo de hilos: {args.threads}")
        print(f"Términos de búsqueda: {', '.join(args.search_terms)}")
        print("Iniciando consulta de pipelines CI...\n")

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task("[cyan]Obteniendo definiciones de pipelines...", total=None)
            definitions = get_build_definitions(base_session, args.org, args.project)
        console.print(f"✅ Pipelines encontrados: [bold green]{len(definitions)}[/bold green]")
    else:
        definitions = get_build_definitions(base_session, args.org, args.project)
        print(f"Total pipelines encontrados: {len(definitions)}\n")

    work_items = []
    
    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Consultando ejecuciones de pipelines...", total=len(definitions))
            for definition in definitions:
                pipeline_name = definition.get("name", "")
                definition_id = definition.get("id")
                progress.update(task, description=f"[cyan]Pipeline: {pipeline_name[:40]}...")
                try:
                    runs = get_build_runs(base_session, args.org, args.project, definition_id, args.top_runs)
                    for run in runs:
                        work_items.append((definition, run))
                except Exception as e:
                    if args.debug:
                        console.print(f"[red]  ERROR: {pipeline_name}: {e}[/red]")
                progress.advance(task)
        console.print(f"✅ Ejecuciones a procesar: [bold green]{len(work_items)}[/bold green]")
    else:
        for definition in definitions:
            pipeline_name = definition.get("name", "")
            definition_id = definition.get("id")
            if args.debug:
                print(f"[PIPELINE] Consultando ejecuciones de: {pipeline_name} (id={definition_id})")
            try:
                runs = get_build_runs(base_session, args.org, args.project, definition_id, args.top_runs)
                if args.debug:
                    print(f"  Ejecuciones encontradas: {len(runs)}")
                for run in runs:
                    work_items.append((definition, run))
            except Exception as e:
                if args.debug:
                    print(f"  [ERROR] No fue posible obtener runs del pipeline {pipeline_name}: {e}")
        print(f"Total de ejecuciones a procesar: {len(work_items)}\n")

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
                "[cyan]Analizando logs de ejecuciones...", 
                total=len(work_items),
                matches=0
            )
            
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                future_map = {
                    executor.submit(analyze_single_run, args, definition, run): (definition.get("name", ""), run.get("id"))
                    for definition, run in work_items
                }

                for future in as_completed(future_map):
                    pipeline_name, run_id = future_map[future]
                    try:
                        rows = future.result()
                        all_rows.extend(rows)
                        matches_count += len(rows)
                        progress.update(task, matches=matches_count)
                    except Exception as e:
                        if args.debug:
                            console.print(f"[red]ERROR: {pipeline_name} | run_id={run_id} | {e}[/red]")
                    progress.advance(task)
    else:
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            future_map = {
                executor.submit(analyze_single_run, args, definition, run): (definition.get("name", ""), run.get("id"))
                for definition, run in work_items
            }

            for future in as_completed(future_map):
                pipeline_name, run_id = future_map[future]
                try:
                    rows = future.result()
                    all_rows.extend(rows)
                    if args.debug:
                        print(f"[DONE] pipeline={pipeline_name} | run_id={run_id} | matches={len(rows)}")
                except Exception as e:
                    if args.debug:
                        print(f"[ERROR] pipeline={pipeline_name} | run_id={run_id} | error={e}")

    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total de coincidencias encontradas:[/bold] [green]{len(all_rows)}[/green]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print("\n=== RESUMEN ===")
        print(f"Total de registros encontrados: {len(all_rows)}")
        print(f"Tiempo de ejecución: {time_str}")
    
    if all_rows:
        results_table = pd.DataFrame(all_rows)
        print("\n=== TABLA FINAL ===")
        print(results_table.to_string(index=False))
        
        if args.output:
            export_results(all_rows, args.output)
    else:
        if RICH_AVAILABLE:
            console.print("[yellow]Sin coincidencias en logs[/yellow]")
        else:
            print("Sin coincidencias en logs")


if __name__ == "__main__":
    main()

