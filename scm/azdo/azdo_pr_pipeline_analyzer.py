#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
azdo_pr_pipeline_analyzer.py

Analiza Pull Requests de múltiples ramas destino (dev/QA/master/release*)
y cruza la información con pipelines CD y últimos releases.

Pasos:
  1. Descargar PRs de ramas seleccionadas (dev, QA, master, release*)
  2. Organizar por fecha descendente y mostrar en tabla
  3. Agrupar por repositorio y mostrar
  4. Descargar pipelines CD para los repositorios con PRs
  5. Descargar último release por cada repositorio
  6. Mostrar tiempos de ejecución de cada paso

Autor: Harold Adrian
Versión: 1.0.0
"""

import argparse
import base64
import csv
import json
import os
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
    from rich.table import Table
    from rich import box
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════════
DEFAULT_ORG_URL = "https://dev.azure.com/Coppel-Retail"
DEFAULT_PROJECT = "Cadena_de_Suministros"
DEFAULT_TIMEZONE = "America/Mazatlan"
DEFAULT_TOP = 500
DEFAULT_THREADS = 20
API_VERSION = "7.1"

# Ramas soportadas para filtrado
SUPPORTED_BRANCHES = ["dev", "QA", "master", "release"]


# ═══════════════════════════════════════════════════════════════════════════════
# ARGS
# ═══════════════════════════════════════════════════════════════════════════════
def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analiza PRs de múltiples ramas y cruza con CD/releases"
    )
    parser.add_argument(
        "--org", "-g",
        default=DEFAULT_ORG_URL,
        help=f"URL de la organización AzDO (default: {DEFAULT_ORG_URL})"
    )
    parser.add_argument(
        "--project", "-p",
        default=DEFAULT_PROJECT,
        help=f"Nombre del proyecto (default: {DEFAULT_PROJECT})"
    )
    parser.add_argument(
        "--pat",
        required=True,
        help="Personal Access Token con permisos: Code (Read), Release (Read)"
    )
    parser.add_argument(
        "--branches", "-b",
        nargs="+",
        choices=SUPPORTED_BRANCHES + ["all"],
        default=["master"],
        help="Ramas destino a analizar: dev, QA, master, release, o all (default: master)"
    )
    parser.add_argument(
        "--status", "-s",
        choices=["active", "completed", "abandoned", "all"],
        default="active",
        help="Estado de los PRs a descargar (default: active)"
    )
    parser.add_argument(
        "--timezone", "-tz",
        default=DEFAULT_TIMEZONE,
        help=f"Zona horaria para fechas (default: {DEFAULT_TIMEZONE})"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_TOP,
        help=f"Máximo de PRs por consulta (default: {DEFAULT_TOP})"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=DEFAULT_THREADS,
        help=f"Hilos paralelos (default: {DEFAULT_THREADS})"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["json", "csv", "excel"],
        default=None,
        help="Exportar resultados (json / csv / excel)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mostrar detalles de debug"
    )
    parser.add_argument(
        "--list-cds",
        action="store_true",
        help="Listar todos los pipelines CD disponibles y salir (diagnóstico)"
    )
    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def get_auth_headers(pat: str) -> Dict[str, str]:
    encoded = base64.b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }


def http_get(url: str, headers: Dict[str, str], params: Dict = None, debug: bool = False, silent: bool = True) -> Optional[Dict]:
    """
    Realiza GET request a la API de Azure DevOps.
    
    Args:
        url: URL completa de la API
        headers: Headers HTTP (incluye auth)
        params: Parámetros de query (opcional)
        debug: Si True, muestra mensajes de debug
        silent: Si False, siempre muestra errores (útil para operaciones críticas)
    """
    if not REQUESTS_AVAILABLE:
        print("[ERROR] Librería 'requests' no instalada. Ejecuta: pip install requests")
        return None
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code >= 400:
            _label = url.split("/_apis")[0].split("/")[-1] if "/_apis" in url else url
            if not silent or debug:
                print(f"  ⚠  HTTP {resp.status_code} ({_label})")
                if debug:
                    print(f"[DEBUG] URL: {url}")
                    print(f"[DEBUG] Body: {resp.text[:400]}")
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        if not silent or debug:
            if e.response.status_code == 401:
                print("        Token de autenticación inválido o expirado")
            elif e.response.status_code == 403:
                print("        Permisos insuficientes para acceder a este recurso")
            elif e.response.status_code == 404:
                print("        Recurso no encontrado")
        return None
    except Exception as e:
        if not silent or debug:
            print(f"\n[ERROR] {type(e).__name__}: {e}")
        return None


def vsrm_base(org_url: str) -> str:
    """Transforma dev.azure.com/{org} → vsrm.dev.azure.com/{org} para Release APIs."""
    return org_url.replace("dev.azure.com", "vsrm.dev.azure.com")


# ═══════════════════════════════════════════════════════════════════════════════
# API FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def get_repositories(org: str, project: str, headers: Dict[str, str], debug: bool = False) -> List[Dict]:
    """Obtiene todos los repositorios del proyecto."""
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories"
    data = http_get(url, headers, params={"api-version": API_VERSION}, debug=debug)
    return data.get("value", []) if data else []


def get_pull_requests_for_branch(
    org: str, 
    project: str, 
    branch: str, 
    headers: Dict[str, str],
    top: int = DEFAULT_TOP,
    status: str = "active",
    debug: bool = False
) -> List[Dict]:
    """Obtiene PRs hacia una rama destino específica."""
    # Normalizar nombre de rama para AzDO
    target_ref = f"refs/heads/{branch}"
    encoded_ref = quote(target_ref, safe="")
    
    # Usar el estado especificado (all para traer todos)
    status_param = status if status != "all" else "all"
    
    url = (
        f"{org}/{quote(project, safe='')}/_apis/git/pullrequests"
        f"?searchCriteria.status={status_param}"
        f"&searchCriteria.targetRefName={encoded_ref}"
        f"&$top={top}"
        f"&api-version={API_VERSION}"
    )
    
    data = http_get(url, headers, params=None, debug=debug)
    return data.get("value", []) if data else []


def search_release_definitions(
    org: str, project: str, search_text: str, headers: Dict[str, str], debug: bool = False
) -> List[Dict]:
    """Busca release definitions por nombre usando searchText de la API.
    Retorna lista resumida (ID + nombre) que contienen search_text.
    """
    base = vsrm_base(org)
    url = f"{base}/{quote(project, safe='')}/_apis/release/definitions"
    params = {
        "api-version": "7.2-preview.4",
        "searchText": search_text,
        "$top": 50,
    }
    data = http_get(url, headers, params=params, debug=debug)
    return data.get("value", []) if data else []


def search_cds_for_repos(
    org: str, project: str, repo_names: List[str],
    headers: Dict[str, str], threads: int, debug: bool = False,
) -> Dict[str, List[Dict]]:
    """Busca CDs candidatos para cada repo en paralelo usando searchText.
    Retorna {repo_name: [release_def_summary, ...]}.
    """
    results: Dict[str, List[Dict]] = {}

    def _search_one(name: str) -> Tuple[str, List[Dict]]:
        # Buscar por nombre exacto y por nombre normalizado (sin guiones)
        found = search_release_definitions(org, project, name, headers, debug)
        # También buscar variaciones del nombre
        name_parts = re.split(r'[-_]', name)
        extra_searches = set()
        if len(name_parts) > 1:
            # Buscar por cada parte significativa (>=3 chars)
            for part in name_parts:
                if len(part) >= 3:
                    extra_searches.add(part)
        for term in extra_searches:
            extra = search_release_definitions(org, project, term, headers, debug)
            # Deduplicar por ID
            existing_ids = {rd["id"] for rd in found}
            for rd in extra:
                if rd["id"] not in existing_ids:
                    found.append(rd)
                    existing_ids.add(rd["id"])
        return (name, found)

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futs = {executor.submit(_search_one, name): name for name in repo_names}
        for fut in as_completed(futs):
            try:
                name, found = fut.result()
                results[name] = found
            except Exception:
                results[futs[fut]] = []

    return results


def _get_release_definitions_paginated(
    org: str, project: str, headers: Dict[str, str], debug: bool = False
) -> List[Dict]:
    """Lista paginada de release definitions (solo para --list-cds diagnóstico).
    ADVERTENCIA: Puede tardar mucho si hay miles de definitions.
    """
    base = vsrm_base(org)
    url = f"{base}/{quote(project, safe='')}/_apis/release/definitions"
    all_defs: List[Dict] = []
    skip = 0
    page_size = 500
    while True:
        params = {"api-version": "7.2-preview.4", "$top": page_size, "$skip": skip}
        data = http_get(url, headers, params=params, debug=debug, silent=False)
        if not data:
            break
        batch = data.get("value", [])
        all_defs.extend(batch)
        if len(batch) < page_size:
            break
        skip += page_size
        print(f"   ... {len(all_defs)} definitions cargadas", flush=True)
    return all_defs


def get_release_definition_detail(
    org: str,
    project: str,
    definition_id: int,
    headers: Dict[str, str],
    debug: bool = False
) -> Optional[Dict]:
    """Obtiene detalles de una release definition específica usando VSRM endpoint."""
    base = vsrm_base(org)
    return http_get(
        f"{base}/{quote(project, safe='')}/_apis/release/definitions/{definition_id}",
        headers,
        params={"api-version": "7.2-preview.4"},
        debug=debug
    )


def get_latest_release(
    org: str,
    project: str,
    definition_id: int,
    headers: Dict[str, str],
    debug: bool = False
) -> Optional[Dict]:
    """Obtiene el último release de una definition usando VSRM endpoint."""
    base = vsrm_base(org)
    data = http_get(
        f"{base}/{quote(project, safe='')}/_apis/release/releases",
        headers,
        params={
            "definitionId": definition_id,
            "$top": 1,
            "queryOrder": "descending",
            "api-version": "7.2-preview.8"
        },
        debug=debug
    )
    if data and data.get("value"):
        return data["value"][0]
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# DATA PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════
def format_datetime(iso_str: str, tz_str: str) -> str:
    """Formatea fecha ISO a formato local."""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        local_tz = ZoneInfo(tz_str)
        dt_local = dt.astimezone(local_tz)
        return dt_local.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_str[:19] if len(iso_str) > 19 else iso_str


def get_pr_date(pr: Dict) -> datetime:
    """Obtiene la fecha relevante del PR para ordenamiento."""
    # Usar fecha de cierre si está completado, sino fecha de creación
    closed_date = pr.get("closedDate")
    creation_date = pr.get("creationDate")
    
    date_str = closed_date if closed_date else creation_date
    if date_str:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


def get_pr_display_date(pr: Dict, tz_str: str) -> str:
    """Obtiene fecha formateada para mostrar."""
    closed_date = pr.get("closedDate")
    creation_date = pr.get("creationDate")
    
    date_str = closed_date if closed_date else creation_date
    prefix = "Cerrado: " if closed_date else "Creado: "
    return prefix + format_datetime(date_str, tz_str)


def get_pr_status(pr: Dict) -> str:
    """Obtiene estado del PR con emoji."""
    status = pr.get("status", "unknown")
    mapping = {
        "active": "🟢 Activo",
        "completed": "✅ Completado",
        "abandoned": "❌ Abandonado"
    }
    return mapping.get(status, f"⚪ {status}")


def normalize_name(name: str) -> str:
    """Normaliza un nombre para comparación."""
    return re.sub(r'[-_\s\.]+', '', name.lower())


def find_cd_candidates_for_repo(repo_name: str, release_defs: List[Dict], debug: bool = False) -> List[Tuple[int, int]]:
    """
    Busca CDs candidatos para un repositorio por nombre (sin descargar detalles).
    Retorna lista de (cd_id, score) ordenada por score descendente.
    Solo se descargarán los detalles de estos candidatos posteriormente.
    """
    repo_lower = repo_name.lower()
    repo_normalized = normalize_name(repo_name)
    
    candidates = []
    
    for rd in release_defs:
        cd_name = rd.get("name", "").lower()
        cd_normalized = normalize_name(cd_name)
        score = 0
        
        # Heurística 1: Match exacto o contiene
        if cd_name == repo_lower:
            score = 100
        elif cd_name.startswith(repo_lower):
            score = 90
        elif repo_lower in cd_name:
            score = 70
        elif repo_normalized in cd_normalized or cd_normalized in repo_normalized:
            score = 60
        
        # Heurística 2: Palabras compartidas (3+ caracteres)
        if score < 50:
            repo_words = set(w for w in re.split(r'[-_\s\.]+', repo_lower) if len(w) >= 3)
            cd_words = set(w for w in re.split(r'[-_\s\.]+', cd_name) if len(w) >= 3)
            shared = repo_words & cd_words
            generic = {'api', 'svc', 'service', 'web', 'app', 'frontend', 'backend', 'legacy', 'uc', 'wm', 'wms', 'tms', 'iwms'}
            specific_shared = shared - generic
            if len(specific_shared) >= 1:
                score = 40 + len(specific_shared) * 10
            elif len(shared) >= 2:
                score = 30
        
        if score > 0:
            candidates.append((rd["id"], score))
    
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    if debug and candidates:
        cd_names = {rd["id"]: rd["name"] for rd in release_defs}
        print(f"\n[DEBUG] CD candidates for '{repo_name}' ({len(candidates)}):")
        for i, (cd_id, score) in enumerate(candidates[:5], 1):
            marker = " ✅ TOP" if i == 1 else ""
            print(f"  {i}. '{cd_names.get(cd_id, '?')}' (score: {score}){marker}")
    
    return candidates


def find_cd_by_artifact_source(repo_name: str, cd_details_map: Dict[int, Dict], debug: bool = False) -> Optional[Dict]:
    """
    Busca CD por nombre exacto del repositorio en artifact source.
    Esta es la forma más precisa de detectar relación repo-CD.
    """
    repo_lower = repo_name.lower()
    
    for cd_id, cd_detail in cd_details_map.items():
        if not cd_detail:
            continue
        for artifact in cd_detail.get("artifacts", []):
            if artifact.get("type") == "Git":
                artifact_repo_name = (
                    artifact.get("definitionReference", {})
                    .get("definition", {})
                    .get("name", "")
                    .lower()
                )
                if artifact_repo_name == repo_lower:
                    if debug:
                        print(f"[DEBUG] ✅ Match por artifact source: '{cd_detail.get('name')}' (ID: {cd_id})")
                    return cd_detail
    
    return None


def find_cd_for_repo_with_details(
    repo_name: str,
    release_defs: List[Dict],
    cd_details_map: Dict[int, Dict],
    debug: bool = False
) -> Optional[Dict]:
    """
    Busca CD pipeline para un repositorio usando detalles descargados:
    1. Artifact source (más preciso)
    2. Nombre del CD (fallback con scoring)
    """
    if debug:
        print(f"\n[DEBUG] Buscando CD para repo: '{repo_name}'")
    
    # PASO 1: Artifact source (más preciso)
    cd_match = find_cd_by_artifact_source(repo_name, cd_details_map, debug)
    if cd_match:
        return cd_match
    
    # PASO 2: Fallback por nombre con scoring
    if debug:
        print(f"[DEBUG] No match por artifact, buscando por nombre...")
    
    repo_lower = repo_name.lower()
    best_match = None
    best_score = 0
    
    for rd in release_defs:
        cd_id = rd.get("id")
        # Solo considerar CDs cuyos detalles fueron descargados
        if cd_id not in cd_details_map:
            continue
        
        cd_name = rd.get("name", "").lower()
        score = 0
        
        if cd_name == repo_lower:
            score = 100
        elif cd_name.startswith(repo_lower):
            score = 90
        elif repo_lower in cd_name:
            score = 70
        elif normalize_name(repo_name) in normalize_name(cd_name):
            score = 60
        else:
            repo_words = set(w for w in re.split(r'[-_\s\.]+', repo_lower) if len(w) >= 3)
            cd_words = set(w for w in re.split(r'[-_\s\.]+', cd_name) if len(w) >= 3)
            shared = repo_words & cd_words
            generic = {'api', 'svc', 'service', 'web', 'app', 'frontend', 'backend', 'legacy', 'uc', 'wm', 'wms', 'tms', 'iwms'}
            specific_shared = shared - generic
            if len(specific_shared) >= 1:
                score = 40 + len(specific_shared) * 10
            elif len(shared) >= 2:
                score = 30
        
        if score > best_score:
            best_score = score
            best_match = rd
    
    if best_match and best_score >= 30:
        cd_id = best_match.get("id")
        cd_detail = cd_details_map.get(cd_id, best_match)
        if debug:
            print(f"[DEBUG] ✅ Match por nombre: '{best_match.get('name')}' (score: {best_score})")
        return cd_detail
    
    if debug:
        print(f"[DEBUG] ❌ No se encontró CD para '{repo_name}'")
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# DISPLAY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def print_pr_table(prs: List[Dict], tz_str: str, console: Optional[Any] = None):
    """Muestra tabla de PRs ordenados por fecha."""
    if not prs:
        msg = "⚠️ No se encontraron PRs"
        if console:
            console.print(f"[yellow]{msg}[/]")
        else:
            print(msg)
        return
    
    if RICH_AVAILABLE and console:
        table = Table(
            title=f"📋 Pull Requests ({len(prs)} total)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Fecha", style="dim", width=20)
        table.add_column("Repositorio", style="bold", width=25)
        table.add_column("PR #", justify="right", width=6)
        table.add_column("Título", width=35)
        table.add_column("Autor", width=15)
        table.add_column("Rama Origen", width=20)
        table.add_column("Estado", width=12)
        table.add_column("Rama Destino", width=15)
        
        for pr in prs:
            repo = pr.get("repository", {})
            table.add_row(
                get_pr_display_date(pr, tz_str),
                repo.get("name", "—")[:24],
                str(pr.get("pullRequestId", "—")),
                pr.get("title", "—")[:34],
                pr.get("createdBy", {}).get("displayName", "—")[:14],
                pr.get("sourceRefName", "—").replace("refs/heads/", "")[:19],
                get_pr_status(pr),
                pr.get("targetRefName", "—").replace("refs/heads/", "")[:14]
            )
        
        console.print(table)
    else:
        # Modo texto simple
        print(f"\n{'='*120}")
        print(f"Pull Requests ({len(prs)} total)")
        print(f"{'='*120}")
        print(f"{'Fecha':<22} {'Repo':<25} {'PR':<6} {'Título':<35} {'Autor':<15} {'Origen':<20} {'Estado':<12} {'Destino':<15}")
        print(f"{'-'*120}")
        for pr in prs:
            repo = pr.get("repository", {})
            print(f"{get_pr_display_date(pr, tz_str):<22} "
                  f"{repo.get('name', '—')[:24]:<25} "
                  f"{str(pr.get('pullRequestId', '—')):<6} "
                  f"{pr.get('title', '—')[:34]:<35} "
                  f"{pr.get('createdBy', {}).get('displayName', '—')[:14]:<15} "
                  f"{pr.get('sourceRefName', '—').replace('refs/heads/', '')[:19]:<20} "
                  f"{get_pr_status(pr):<12} "
                  f"{pr.get('targetRefName', '—').replace('refs/heads/', '')[:14]:<15}")


def print_repo_grouped(prs: List[Dict], tz_str: str, console: Optional[Any] = None):
    """Muestra tabla única con PRs agrupados por repositorio y conteos por estado."""
    if not prs:
        return
    
    # Agrupar por repo y contar por estado
    repo_stats: Dict[str, Dict[str, int]] = {}
    for pr in prs:
        repo_name = pr.get("repository", {}).get("name", "Unknown")
        status = pr.get("status", "unknown")
        
        if repo_name not in repo_stats:
            repo_stats[repo_name] = {"total": 0, "active": 0, "completed": 0, "abandoned": 0, "other": 0}
        
        repo_stats[repo_name]["total"] += 1
        if status in repo_stats[repo_name]:
            repo_stats[repo_name][status] += 1
        else:
            repo_stats[repo_name]["other"] += 1
    
    if RICH_AVAILABLE and console:
        console.print(Panel.fit(
            f"📁 Resumen por Repositorio ({len(repo_stats)} repos)",
            style="bold green"
        ))
        
        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold blue"
        )
        table.add_column("Repositorio", style="bold", width=35)
        table.add_column("Total", justify="right", width=6)
        table.add_column("🟢 Activos", justify="right", width=10)
        table.add_column("✅ Completados", justify="right", width=14)
        table.add_column("❌ Abandonados", justify="right", width=14)
        
        # Calcular totales
        total_active = sum(s["active"] for s in repo_stats.values())
        total_completed = sum(s["completed"] for s in repo_stats.values())
        total_abandoned = sum(s["abandoned"] for s in repo_stats.values())
        total_prs = sum(s["total"] for s in repo_stats.values())
        
        # Ordenar por total descendente
        sorted_repos = sorted(repo_stats.items(), key=lambda x: x[1]["total"], reverse=True)
        
        for repo_name, stats in sorted_repos:
            table.add_row(
                repo_name[:34],
                str(stats["total"]),
                str(stats["active"]) if stats["active"] > 0 else "—",
                str(stats["completed"]) if stats["completed"] > 0 else "—",
                str(stats["abandoned"]) if stats["abandoned"] > 0 else "—"
            )
        
        # Fila de totales
        table.add_row(
            "—" * 30,
            "—",
            "—" * 8,
            "—" * 12,
            "—" * 12,
            style="dim"
        )
        table.add_row(
            "TOTAL",
            str(total_prs),
            str(total_active),
            str(total_completed),
            str(total_abandoned),
            style="bold cyan"
        )
        
        console.print(table)
    else:
        print(f"\n{'='*100}")
        print(f"📁 Resumen por Repositorio ({len(repo_stats)} repos)")
        print(f"{'='*100}")
        print(f"{'Repositorio':<35} {'Total':>6} {'Activos':>10} {'Completados':>14} {'Abandonados':>14}")
        print(f"{'-'*100}")
        
        # Calcular totales
        total_active = sum(s["active"] for s in repo_stats.values())
        total_completed = sum(s["completed"] for s in repo_stats.values())
        total_abandoned = sum(s["abandoned"] for s in repo_stats.values())
        total_prs = sum(s["total"] for s in repo_stats.values())
        
        # Ordenar por total descendente
        sorted_repos = sorted(repo_stats.items(), key=lambda x: x[1]["total"], reverse=True)
        
        for repo_name, stats in sorted_repos:
            print(f"{repo_name:<35} {stats['total']:>6} {stats['active']:>10} {stats['completed']:>14} {stats['abandoned']:>14}")
        
        print(f"{'-'*100}")
        print(f"{'TOTAL':<35} {total_prs:>6} {total_active:>10} {total_completed:>14} {total_abandoned:>14}")


def print_cd_info(
    repo_cds: Dict[str, Optional[Dict]], 
    repo_releases: Dict[str, Optional[Dict]],
    prs: List[Dict],
    console: Optional[Any] = None
):
    """Muestra información de CDs y releases por repositorio, ordenado por cantidad de PRs."""
    # Calcular cantidad de PRs por repositorio para ordenamiento
    pr_count_by_repo: Dict[str, int] = {}
    for pr in prs:
        repo_name = pr.get("repository", {}).get("name", "Unknown")
        if repo_name != "Unknown":
            pr_count_by_repo[repo_name] = pr_count_by_repo.get(repo_name, 0) + 1
    
    # Ordenar repos por cantidad de PRs (descendente)
    sorted_repos = sorted(
        repo_cds.keys(),
        key=lambda r: pr_count_by_repo.get(r, 0),
        reverse=True
    )
    
    if RICH_AVAILABLE and console:
        table = Table(
            title="🚀 Pipelines CD y Últimos Releases",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("Repositorio", style="bold", width=30)
        table.add_column("# PRs", justify="right", width=5)
        table.add_column("Pipeline CD", width=38)
        table.add_column("Último Release", width=22)
        table.add_column("Estado", width=10)
        
        for repo_name in sorted_repos:
            cd = repo_cds.get(repo_name)
            release = repo_releases.get(repo_name)
            pr_count = pr_count_by_repo.get(repo_name, 0)
            
            cd_name = cd.get("name", "—") if cd else "[dim]—[/]"
            
            if release:
                rel_name = release.get("name", "—")
                rel_status = release.get("status", "—")
                if rel_status == "active":
                    status_emoji = "🟢"
                    status_style = "green"
                elif rel_status == "abandoned":
                    status_emoji = "🔴"
                    status_style = "red"
                else:
                    status_emoji = "⚪"
                    status_style = "white"
                status_text = f"[{status_style}]{status_emoji} {rel_status}[/{status_style}]"
            else:
                rel_name = "—"
                status_text = "[dim]—[/]"
            
            table.add_row(
                repo_name[:29],
                str(pr_count),
                cd_name[:37] if cd else cd_name,
                rel_name[:21],
                status_text
            )
        
        console.print(table)
    else:
        print(f"\n{'='*115}")
        print(f"Pipelines CD y Últimos Releases")
        print(f"{'='*115}")
        print(f"{'Repositorio':<30} {'# PRs':>5} {'Pipeline CD':<40} {'Último Release':<25} {'Estado':<12}")
        print(f"{'-'*115}")
        for repo_name in sorted_repos:
            cd = repo_cds.get(repo_name)
            release = repo_releases.get(repo_name)
            pr_count = pr_count_by_repo.get(repo_name, 0)
            
            cd_name = cd.get("name", "—") if cd else "—"
            
            if release:
                rel_name = release.get("name", "—")
                rel_status = release.get("status", "—")
            else:
                rel_name = "—"
                rel_status = "—"
            
            print(f"{repo_name[:29]:<30} {pr_count:>5} {cd_name[:39]:<40} {rel_name[:24]:<25} {rel_status:<12}")


def print_timing_report(step_times: List[Tuple[str, float]], total_time: float, console: Optional[Any] = None):
    """Muestra reporte de tiempos."""
    if RICH_AVAILABLE and console:
        table = Table(
            title="⏱️ Tiempos de Ejecución",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold yellow"
        )
        table.add_column("Paso", style="bold")
        table.add_column("Tiempo (s)", justify="right")
        table.add_column("% del Total", justify="right")
        
        for step_name, step_time in step_times:
            pct = (step_time / total_time * 100) if total_time > 0 else 0
            table.add_row(
                step_name,
                f"{step_time:.2f}s",
                f"{pct:.1f}%"
            )
        
        table.add_row("—" * 20, "—" * 12, "—" * 10)
        table.add_row(
            "TOTAL",
            f"{total_time:.2f}s",
            "100.0%",
            style="bold green"
        )
        
        console.print(table)
    else:
        print(f"\n{'='*50}")
        print(f"Tiempos de Ejecución")
        print(f"{'='*50}")
        print(f"{'Paso':<35} {'Tiempo':<12} {'%':<8}")
        print(f"{'-'*50}")
        for step_name, step_time in step_times:
            pct = (step_time / total_time * 100) if total_time > 0 else 0
            print(f"{step_name:<35} {step_time:>6.2f}s     {pct:>5.1f}%")
        print(f"{'-'*50}")
        print(f"{'TOTAL':<35} {total_time:>6.2f}s     100.0%")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def export_results(
    prs: List[Dict],
    repo_cds: Dict[str, Optional[Dict]],
    repo_releases: Dict[str, Optional[Dict]],
    step_times: List[Tuple[str, float]],
    total_time: float,
    output_format: str,
    org: str,
    project: str
):
    """Exporta resultados a archivo."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"pr_pipeline_analysis_{timestamp}"
    
    # Preparar datos
    data = {
        "metadata": {
            "org": org,
            "project": project,
            "timestamp": timestamp,
            "total_time_seconds": round(total_time, 2),
            "step_times": {name: round(t, 2) for name, t in step_times}
        },
        "pull_requests": [
            {
                "pr_id": pr.get("pullRequestId"),
                "title": pr.get("title"),
                "repository": pr.get("repository", {}).get("name"),
                "source_branch": pr.get("sourceRefName", "").replace("refs/heads/", ""),
                "target_branch": pr.get("targetRefName", "").replace("refs/heads/", ""),
                "status": pr.get("status"),
                "created_by": pr.get("createdBy", {}).get("displayName"),
                "creation_date": pr.get("creationDate"),
                "closed_date": pr.get("closedDate")
            }
            for pr in prs
        ],
        "repositories": {
            repo_name: {
                "cd_pipeline": repo_cds.get(repo_name, {}).get("name") if repo_cds.get(repo_name) else None,
                "latest_release": repo_releases.get(repo_name, {}).get("name") if repo_releases.get(repo_name) else None,
                "release_status": repo_releases.get(repo_name, {}).get("status") if repo_releases.get(repo_name) else None
            }
            for repo_name in sorted(repo_cds.keys())
        }
    }
    
    if output_format == "json":
        filename = f"outcome/{base_name}.json"
        os.makedirs("outcome", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n📁 Exportado a: {filename}")
    
    elif output_format == "csv":
        filename = f"outcome/{base_name}_prs.csv"
        os.makedirs("outcome", exist_ok=True)
        with open(filename, "w", newline="", encoding="utf-8") as f:
            if data["pull_requests"]:
                writer = csv.DictWriter(f, fieldnames=data["pull_requests"][0].keys())
                writer.writeheader()
                writer.writerows(data["pull_requests"])
        print(f"\n📁 Exportado a: {filename}")
    
    elif output_format == "excel":
        try:
            import pandas as pd
            filename = f"outcome/{base_name}.xlsx"
            os.makedirs("outcome", exist_ok=True)
            
            with pd.ExcelWriter(filename, engine="openpyxl") as writer:
                # PRs
                df_prs = pd.DataFrame(data["pull_requests"])
                df_prs.to_excel(writer, sheet_name="Pull Requests", index=False)
                
                # Repos with CD/Releases
                repos_data = []
                for repo_name, info in data["repositories"].items():
                    repos_data.append({
                        "Repository": repo_name,
                        "CD Pipeline": info["cd_pipeline"] or "—",
                        "Latest Release": info["latest_release"] or "—",
                        "Release Status": info["release_status"] or "—"
                    })
                df_repos = pd.DataFrame(repos_data)
                df_repos.to_excel(writer, sheet_name="Repositories", index=False)
                
                # Metadata
                meta_data = {
                    "Property": list(data["metadata"].keys()),
                    "Value": [str(v) for v in data["metadata"].values()]
                }
                df_meta = pd.DataFrame(meta_data)
                df_meta.to_excel(writer, sheet_name="Metadata", index=False)
            
            print(f"\n📁 Exportado a: {filename}")
        except ImportError:
            print("[WARN] pandas y openpyxl requeridos para Excel. Instala: pip install pandas openpyxl")
            print("[INFO] Exportando como CSV en su lugar...")
            export_results(prs, repo_cds, repo_releases, step_times, total_time, "csv", org, project)


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def list_all_cds(
    org: str,
    project: str,
    headers: Dict[str, str],
    console: Optional[Any] = None,
    debug: bool = False
):
    """Lista todos los pipelines CD disponibles para diagnóstico."""
    print(f"\n📋 Listando todos los Pipelines CD en {project}...")
    print(f"   Org: {org}")
    print()
    
    release_defs = _get_release_definitions_paginated(org, project, headers, debug)
    
    if not release_defs:
        print("⚠️ No se encontraron pipelines CD.")
        return
    
    print(f"✅ Total de CDs encontrados: {len(release_defs)}\n")
    
    # Ordenar alfabéticamente
    sorted_cds = sorted(release_defs, key=lambda x: x.get("name", "").lower())
    
    if RICH_AVAILABLE and console:
        table = Table(
            title=f"🚀 Pipelines CD Disponibles ({len(release_defs)})",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("#", justify="right", width=4)
        table.add_column("ID", justify="right", width=6)
        table.add_column("Nombre del Pipeline CD", width=60)
        table.add_column("Url", width=30)
        
        for i, rd in enumerate(sorted_cds, 1):
            cd_id = rd.get("id", "—")
            cd_name = rd.get("name", "—")
            url = rd.get("url", "—")
            # Truncar URL para mostrar
            url_short = url[:27] + "..." if len(url) > 30 else url
            
            table.add_row(
                str(i),
                str(cd_id),
                cd_name[:59],
                url_short
            )
        
        console.print(table)
    else:
        print(f"{'='*100}")
        print(f"{'#':<4} {'ID':<6} {'Nombre del Pipeline CD':<60} {'Url':<30}")
        print(f"{'-'*100}")
        for i, rd in enumerate(sorted_cds, 1):
            cd_id = rd.get("id", "—")
            cd_name = rd.get("name", "—")
            url = rd.get("url", "—")[:27]
            print(f"{i:<4} {cd_id:<6} {cd_name[:59]:<60} {url:<30}")
        print(f"{'='*100}")
    
    print(f"\n💡 Usa estos nombres para configurar mapeos manuales en repo_cd_mapping.json")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    args = get_args()
    
    # Setup
    headers = get_auth_headers(args.pat)
    console = Console() if RICH_AVAILABLE else None
    
    if not REQUESTS_AVAILABLE:
        print("[ERROR] Requiere 'requests'. Instala: pip install requests")
        return
    
    # Modo diagnóstico: listar CDs y salir
    if args.list_cds:
        list_all_cds(args.org, args.project, headers, console, args.debug)
        return
    
    # Determinar ramas a consultar
    if "all" in args.branches:
        branches_to_query = ["dev", "QA", "master", "release"]
    else:
        branches_to_query = args.branches
    
    print(f"\n🔧 Configuración:")
    print(f"   Org: {args.org}")
    print(f"   Project: {args.project}")
    print(f"   Ramas: {', '.join(branches_to_query)}")
    print(f"   Estado PRs: {args.status}")
    print(f"   Zona horaria: {args.timezone}")
    print()
    
    step_times: List[Tuple[str, float]] = []
    total_start = time.time()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PASO 1: Descargar PRs de todas las ramas
    # ═══════════════════════════════════════════════════════════════════════════
    step_start = time.time()
    print("📥 Paso 1: Descargando PRs...")
    
    all_prs: List[Dict] = []
    for branch in branches_to_query:
        if console:
            with console.status(f"[bold green]Consultando rama '{branch}'..."):
                prs = get_pull_requests_for_branch(
                    args.org, args.project, branch, headers, args.top, args.status, args.debug
                )
        else:
            print(f"   Consultando rama '{branch}'...", end="", flush=True)
            prs = get_pull_requests_for_branch(
                args.org, args.project, branch, headers, args.top, args.status, args.debug
            )
            print(f" {len(prs)} PRs")
        
        # Agregar info de rama destino para referencia
        for pr in prs:
            pr["_queried_target_branch"] = branch
        
        all_prs.extend(prs)
    
    # Eliminar duplicados (un PR puede aparecer en múltiples consultas)
    seen_ids = set()
    unique_prs = []
    for pr in all_prs:
        pr_id = pr.get("pullRequestId")
        if pr_id and pr_id not in seen_ids:
            seen_ids.add(pr_id)
            unique_prs.append(pr)
    
    all_prs = unique_prs
    
    # Ordenar por fecha descendente
    all_prs.sort(key=get_pr_date, reverse=True)
    
    step_times.append(("1. Descargar PRs", time.time() - step_start))
    print(f"   ✅ {len(all_prs)} PRs únicos encontrados")
    
    if not all_prs:
        print("\n⚠️ No se encontraron PRs en las ramas seleccionadas.")
        return
    
    # Mostrar tabla de PRs
    print_pr_table(all_prs, args.timezone, console)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PASO 2: Agrupar por repositorio y mostrar
    # ═══════════════════════════════════════════════════════════════════════════
    step_start = time.time()
    print("\n📁 Paso 2: Agrupando por repositorio...")
    
    # Agrupar por repositorio
    repos_with_prs = {pr.get("repository", {}).get("name", "Unknown") for pr in all_prs}
    repos_with_prs = {r for r in repos_with_prs if r != "Unknown"}
    
    step_times.append(("2. Agrupar por repo", time.time() - step_start))
    print(f"   ✅ {len(repos_with_prs)} repositorios con PRs")
    
    # Mostrar agrupado
    print_repo_grouped(all_prs, args.timezone, console)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PASO 3: Buscar pipelines CD para repositorios con PRs
    # ═══════════════════════════════════════════════════════════════════════════
    step_start = time.time()
    print("\n🚀 Paso 3: Buscando pipelines CD...")
    
    # 1. Buscar CDs por repo usando searchText API (paralelo)
    if console:
        with console.status("[bold green]Buscando pipelines CD por repositorio..."):
            repo_cds_map = search_cds_for_repos(
                args.org, args.project, list(repos_with_prs), headers, args.threads, args.debug
            )
    else:
        print(f"   Buscando CDs para {len(repos_with_prs)} repos...", end="", flush=True)
        repo_cds_map = search_cds_for_repos(
            args.org, args.project, list(repos_with_prs), headers, args.threads, args.debug
        )
        total_cds = sum(len(v) for v in repo_cds_map.values())
        print(f" {total_cds} candidatos encontrados")

    total_cds = sum(len(v) for v in repo_cds_map.values())
    if total_cds == 0:
        print("   ⚠️ No hay pipelines CD disponibles")
        repo_cds = {repo: None for repo in repos_with_prs}
        repo_releases = {repo: None for repo in repos_with_prs}
    else:
        # 2. Scoring local sobre los resultados de searchText
        print(f"   Scoring de candidatos para {len(repos_with_prs)} repos...")
        candidate_ids_per_repo: Dict[str, List[Tuple[int, int]]] = {}
        all_candidate_ids: Set[int] = set()

        for repo_name in repos_with_prs:
            candidates = find_cd_candidates_for_repo(repo_name, repo_cds_map.get(repo_name, []), args.debug)
            candidate_ids_per_repo[repo_name] = candidates
            for cd_id, score in candidates:
                all_candidate_ids.add(cd_id)

        print(f"   CDs con score >= 30: {len(all_candidate_ids)} únicos")
        
        # 3. Descargar detalles solo de los candidatos en paralelo
        cd_details_map: Dict[int, Dict] = {}
        if all_candidate_ids:
            if console:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task("Descargando detalles de CDs candidatos...", total=len(all_candidate_ids))
                    
                    with ThreadPoolExecutor(max_workers=args.threads) as executor:
                        futures = {
                            executor.submit(
                                get_release_definition_detail,
                                args.org, args.project,
                                cd_id, headers, args.debug
                            ): cd_id
                            for cd_id in all_candidate_ids
                        }
                        
                        for future in as_completed(futures):
                            cd_id = futures[future]
                            try:
                                cd_detail = future.result()
                                if cd_detail:
                                    cd_details_map[cd_id] = cd_detail
                            except Exception as e:
                                if args.debug:
                                    print(f"\n[DEBUG] Error descargando CD {cd_id}: {e}")
                            progress.advance(task)
            else:
                print(f"   Descargando detalles de {len(all_candidate_ids)} CDs...", end="", flush=True)
                with ThreadPoolExecutor(max_workers=args.threads) as executor:
                    futures = {
                        executor.submit(
                            get_release_definition_detail,
                            args.org, args.project,
                            cd_id, headers, args.debug
                        ): cd_id
                        for cd_id in all_candidate_ids
                    }
                    
                    for future in as_completed(futures):
                        cd_id = futures[future]
                        try:
                            cd_detail = future.result()
                            if cd_detail:
                                cd_details_map[cd_id] = cd_detail
                        except Exception:
                            pass
                print(f" ✓ ({len(cd_details_map)} cargados)")
        
        # 4. Matching final: artifact source + nombre fallback
        repo_cds: Dict[str, Optional[Dict]] = {}
        for repo_name in repos_with_prs:
            # Solo considerar CDs candidatos para este repo
            repo_candidate_ids = {cd_id for cd_id, _ in candidate_ids_per_repo.get(repo_name, [])}
            repo_cd_details = {k: v for k, v in cd_details_map.items() if k in repo_candidate_ids}
            repo_release_defs = [rd for rd in repo_cds_map.get(repo_name, []) if rd["id"] in repo_candidate_ids]
            
            cd = find_cd_for_repo_with_details(repo_name, repo_release_defs, repo_cd_details, args.debug)
            repo_cds[repo_name] = cd
        
        # Diagnóstico
        matched_count = sum(1 for cd in repo_cds.values() if cd is not None)
        if args.debug:
            print(f"\n[DEBUG] Total CDs candidatos: {total_cds}")
            print(f"[DEBUG] CDs candidatos descargados: {len(cd_details_map)}")
            print(f"[DEBUG] CDs encontrados para repos: {matched_count}/{len(repos_with_prs)}")
    
    cd_found_count = sum(1 for cd in repo_cds.values() if cd is not None)
    step_times.append(("3. Buscar CD pipelines", time.time() - step_start))
    print(f"   ✅ CD encontrados: {cd_found_count}/{len(repos_with_prs)}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PASO 4: Descargar últimos releases
    # ═══════════════════════════════════════════════════════════════════════════
    step_start = time.time()
    print("\n📦 Paso 4: Descargando últimos releases...")
    
    repo_releases: Dict[str, Optional[Dict]] = {}
    cds_with_releases = [(repo, cd) for repo, cd in repo_cds.items() if cd is not None]
    
    if cds_with_releases:
        if console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Consultando releases...", total=len(cds_with_releases))
                
                with ThreadPoolExecutor(max_workers=args.threads) as executor:
                    futures = {
                        executor.submit(
                            get_latest_release,
                            args.org, args.project,
                            cd["id"], headers, args.debug
                        ): repo_name
                        for repo_name, cd in cds_with_releases
                    }
                    
                    for future in as_completed(futures):
                        repo_name = futures[future]
                        try:
                            release = future.result()
                            repo_releases[repo_name] = release
                        except Exception:
                            repo_releases[repo_name] = None
                        progress.advance(task)
        else:
            print("   Consultando releases...", end="", flush=True)
            with ThreadPoolExecutor(max_workers=args.threads) as executor:
                futures = {
                    executor.submit(
                        get_latest_release,
                        args.org, args.project,
                        cd["id"], headers, args.debug
                    ): repo_name
                    for repo_name, cd in cds_with_releases
                }
                
                for future in as_completed(futures):
                    repo_name = futures[future]
                    try:
                        release = future.result()
                        repo_releases[repo_name] = release
                    except Exception:
                        repo_releases[repo_name] = None
            print(f" {len([r for r in repo_releases.values() if r])} encontrados")
    
    releases_found = len([r for r in repo_releases.values() if r is not None])
    step_times.append(("4. Descargar releases", time.time() - step_start))
    print(f"   ✅ Releases encontrados: {releases_found}/{len(cds_with_releases)}")
    
    # Mostrar info de CDs y releases
    print_cd_info(repo_cds, repo_releases, all_prs, console)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # REPORTE DE TIEMPOS
    # ═══════════════════════════════════════════════════════════════════════════
    total_time = time.time() - total_start
    
    print("\n")
    print_timing_report(step_times, total_time, console)
    
    # Exportar si se solicitó
    if args.output:
        export_results(
            all_prs, repo_cds, repo_releases,
            step_times, total_time, args.output,
            args.org, args.project
        )
    
    print(f"\n✨ Análisis completado en {total_time:.2f} segundos")


if __name__ == "__main__":
    main()
