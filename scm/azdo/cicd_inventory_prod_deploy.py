#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CD Prod Deploy Tracker v1.0.0
Rastrea el último despliegue exitoso a Producción por pipeline CD.
Lee cache CD existente y consulta APIs de releases para obtener fechas, artefactos y vigencia.

Uso:
    python cicd_inventory_prod_deploy.py --org Coppel-Retail --project "Compras.RMI" --deadline 2026-03-01
    python cicd_inventory_prod_deploy.py --org Coppel-Retail --project "Compras.RMI" --deadline 2026-03-01 --force-refresh
    python cicd_inventory_prod_deploy.py --org Coppel-Retail --project "Compras.RMI" --deadline 2026-03-01 --workers 20

Cache-first: verifica cache propio < 24h para skip APIs. Requiere cache CD previo.
Genera Excel + CSV + JSON cache.

Autor: Harold Adrian Bolanos Rodriguez
"""

import os
import sys
import time
import json
import glob
import requests
import pandas as pd
import argparse
from datetime import datetime, timezone, date
from base64 import b64encode
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *a, **k: None

try:
    from rich.progress import Progress, SpinnerColumn, BarColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from utils import get_output_dir, resolve_output_path
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
    from datetime import datetime as _dt
    _FMT_EXT = {"excel": ".xlsx", "csv": ".csv", "json": ".json"}
    def resolve_output_path(output_arg, base_name, default_format="excel"):
        output_dir = get_output_dir("outcome")
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = _FMT_EXT.get(default_format, ".xlsx")
        if not output_arg:
            return str(output_dir / f"{base_name}_{_dt.now().strftime('%Y%m%d_%H%M%S')}{ext}")
        if output_arg.lower() in _FMT_EXT:
            ext = _FMT_EXT[output_arg.lower()]
            return str(output_dir / f"{base_name}_{_dt.now().strftime('%Y%m%d_%H%M%S')}{ext}")
        p = _Path(output_arg)
        if p.suffix == "":
            p = p.with_suffix(ext)
        return str(p.resolve())

load_dotenv(Path(__file__).parent.parent / ".env")

SCRIPT_NAME = "cicd_inventory_prod_deploy"
CD_CACHE_SCRIPT = "cicd_inventory_cd_detailed"
DEFAULT_ORG = "Coppel-Retail"
DEFAULT_PROJECT = "Compras.RMI"
API_VERSION = "7.1"
DEFAULT_WORKERS = 30
CACHE_TTL_HOURS = 24

PROD_KEYWORDS = ["producción", "produccion", "production", "prod", "prd", "produc"]

OBSOLETE_KEYWORDS = ["obsoleto", "obsolete", "_old", "legacy-", "deprecated", "deprecated_"]


# ==========================================================
# UTILIDADES COMUNES
# ==========================================================

class TeeWriter:
    def __init__(self, log_path):
        self.terminal = sys.__stdout__
        self.log = open(log_path, "w", encoding="utf-8")
        self.log_path = log_path
        self._paused = False

    def write(self, message):
        self.log.write(message)
        if not self._paused:
            self.terminal.write(message)

    def flush(self):
        self.log.flush()
        if not self._paused:
            self.terminal.flush()

    def close(self):
        self.log.close()

    def pause_terminal(self):
        self._paused = True

    def resume_terminal(self):
        self._paused = False


def setup_logging():
    output_dir = get_output_dir("outcome")
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / f"{SCRIPT_NAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    tee = TeeWriter(log_path)
    sys.stdout = tee
    print(f"📝 Log: {log_path.resolve()}")
    print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    return tee


def teardown_logging(tee):
    print(f"\n📝 Log guardado: {tee.log_path.resolve()}")
    sys.stdout = tee.terminal
    tee.close()


def _progress_context():
    if RICH_AVAILABLE:
        console = Console(file=sys.__stdout__)
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            console=console,
        )
    return None


def get_headers(pat: str):
    auth = b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}


def az_get(url, headers, params=None, max_retries=5):
    params = params or {}
    params["api-version"] = API_VERSION
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
            if r.status_code >= 500:
                wait = 2 ** attempt
                print(f"⚠️  {r.status_code} en {url[:60]}... retry {attempt+1}/{max_retries} (espera {wait}s)")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError:
            raise
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt
            print(f"⚠️  Error en {url[:60]}... retry {attempt+1}/{max_retries}: {e}")
            time.sleep(wait)
    return {}


def normalize_org(org: str) -> str:
    if org.startswith("http"):
        return org.rstrip("/").split("/")[-1]
    return org


def safe_az_get(url, headers, params=None):
    try:
        return az_get(url, headers, params)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {}


# ==========================================================
# CACHE
# ==========================================================

def _find_latest_cache():
    output_dir = get_output_dir("outcome")
    cache_dir = output_dir / ".cache"
    pattern = str(cache_dir / f"{SCRIPT_NAME}_raw_*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return Path(files[0])


def _find_cd_cache():
    """Busca el cache del script CD detailed."""
    output_dir = get_output_dir("outcome")
    cache_dir = output_dir / ".cache"
    pattern = str(cache_dir / f"{CD_CACHE_SCRIPT}_raw_*.json")
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return Path(files[0])


def _cache_is_fresh(cache_path, ttl_hours=CACHE_TTL_HOURS):
    if not cache_path or not cache_path.exists():
        return False
    mtime = cache_path.stat().st_mtime
    age_hours = (time.time() - mtime) / 3600
    return age_hours < ttl_hours


def _load_cache(cache_path):
    with open(cache_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_cache(data, script_name=SCRIPT_NAME):
    output_dir = get_output_dir("outcome")
    cache_dir = output_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{script_name}_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return cache_path


# ==========================================================
# DETECCIÓN
# ==========================================================

def detect_obsolete(name: str) -> str:
    name_lower = name.lower()
    for kw in OBSOLETE_KEYWORDS:
        if kw in name_lower:
            return "Sí"
    return "No"


def _is_prod_env(env_name: str) -> bool:
    """Detecta si un environment es de producción por keywords."""
    env_lower = env_name.lower()
    return any(kw in env_lower for kw in PROD_KEYWORDS)


def _parse_iso_date(date_str):
    """Parsea una fecha ISO a datetime. Retorna None si es vacío/inválido."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        # Azure DevOps usa formato ISO 8601: 2026-04-20T14:00:00Z
        dt_str = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


# ==========================================================
# FETCH PROD DEPLOY PER PIPELINE
# ==========================================================

def _fetch_prod_deploy(cd_row, headers, org, project, deadline_date):
    """Consulta releases de un pipeline CD y extrae info del último deploy a producción."""
    def_id = cd_row.get("id") or cd_row.get("cd_pipeline_id")
    name = cd_row.get("name") or cd_row.get("cd_pipeline_name", "")
    path = cd_row.get("path") or cd_row.get("cd_pipeline_path", "")
    environments_str = cd_row.get("environments", "")
    is_obsolete = cd_row.get("isObsolete") or detect_obsolete(name)

    result = {
        "cd_pipeline_id": def_id,
        "cd_pipeline_name": name,
        "cd_pipeline_path": path,
        "environments": environments_str,
        "last_release_number": "",
        "last_release_id": "",
        "last_release_date": "",
        "last_release_status": "",
        "prod_env_name": "",
        "last_prod_deploy_date": "",
        "last_prod_deploy_status": "",
        "last_prod_release_number": "",
        "last_prod_release_id": "",
        "commit_sha": "",
        "build_id": "",
        "build_number": "",
        "deadline": str(deadline_date) if deadline_date else "",
        "deadline_status": "",
        "days_since_prod_deploy": "",
        "is_obsolete": is_obsolete,
    }

    # Consultar releases del pipeline (top 100 para buscar deploy exitoso a prod)
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases"
    releases_data = safe_az_get(url, headers, {
        "definitionId": def_id,
        "$top": 100,
        "$expand": "environments,artifacts",
    })

    releases = releases_data.get("value", []) if isinstance(releases_data, dict) else []
    if not releases:
        result["deadline_status"] = "Sin releases"
        return result

    # a) Último release global
    last_r = releases[0]
    result["last_release_number"] = last_r.get("name", "")
    result["last_release_id"] = last_r.get("id", "")
    result["last_release_date"] = last_r.get("createdOn", "")
    result["last_release_status"] = last_r.get("status", "")

    # b) Buscar último deploy exitoso a producción iterando releases
    best_prod_deploy = None  # (datetime, env_name, status, release_info)
    best_release_for_prod = None

    for rel in releases:
        envs = rel.get("environments", [])
        for env in envs:
            env_name = env.get("name", "")
            if not _is_prod_env(env_name):
                continue

            # Iterar deploy steps (attempts)
            deploy_steps = env.get("deploySteps", [])
            for step in deploy_steps:
                step_status = step.get("deploymentStatus", "")
                finished_on = step.get("finishedOn", "")
                dt_finished = _parse_iso_date(finished_on)

                if dt_finished and step_status == "succeeded":
                    if best_prod_deploy is None or dt_finished > best_prod_deploy[0]:
                        best_prod_deploy = (dt_finished, env_name, step_status, finished_on)
                        best_release_for_prod = rel

            # Si no deploySteps, check environment status directly
            if not deploy_steps:
                env_status = env.get("status", "")
                modified_on = env.get("modifiedOn", "")
                dt_modified = _parse_iso_date(modified_on)
                if dt_modified and env_status in ("succeeded", "partiallySucceeded"):
                    if best_prod_deploy is None or dt_modified > best_prod_deploy[0]:
                        best_prod_deploy = (dt_modified, env_name, env_status, modified_on)
                        best_release_for_prod = rel

    # c) Completar datos de prod deploy
    if best_prod_deploy:
        dt_prod, env_name, deploy_status, finished_on_str = best_prod_deploy
        result["prod_env_name"] = env_name
        result["last_prod_deploy_date"] = finished_on_str
        result["last_prod_deploy_status"] = deploy_status

        if best_release_for_prod:
            result["last_prod_release_number"] = best_release_for_prod.get("name", "")
            result["last_prod_release_id"] = best_release_for_prod.get("id", "")

            # d) Extraer artefactos: commit SHA, build ID
            artifacts = best_release_for_prod.get("artifacts", [])
            for art in artifacts:
                is_primary = art.get("isPrimary", False)
                art_type = art.get("type", "")
                ref = art.get("definitionReference", {})

                # Commit SHA from sourceVersion
                source_version = ref.get("sourceVersion", {})
                commit_sha = source_version.get("id", "") if isinstance(source_version, dict) else ""
                if commit_sha:
                    result["commit_sha"] = commit_sha

                # Build ID and number
                build_ref = ref.get("build", {})
                if isinstance(build_ref, dict):
                    if build_ref.get("id"):
                        result["build_id"] = str(build_ref["id"])
                    if build_ref.get("name"):
                        result["build_number"] = build_ref["name"]

                # Si es artefacto primario, priorizar
                if is_primary:
                    break

        # e) Calcular days_since_prod_deploy
        now = datetime.now(timezone.utc)
        if dt_prod.tzinfo is None:
            dt_prod = dt_prod.replace(tzinfo=timezone.utc)
        days_elapsed = (now - dt_prod).days
        result["days_since_prod_deploy"] = days_elapsed

        # f) Calcular deadline_status
        if deadline_date:
            # Comparar solo la fecha (sin hora)
            prod_date = dt_prod.date() if hasattr(dt_prod, 'date') else dt_prod
            if prod_date > deadline_date:
                result["deadline_status"] = "Vigente"
            else:
                result["deadline_status"] = "Actualizar release"
        else:
            result["deadline_status"] = ""
    else:
        # No se encontró deploy exitoso a producción
        has_prod_env = any(_is_prod_env(e.strip()) for e in environments_str.split("/") if e.strip())
        if not has_prod_env:
            result["deadline_status"] = "Sin env. Producción"
        else:
            result["deadline_status"] = "Sin deploy exitoso a prod"

    return result


# ==========================================================
# EXPORT
# ==========================================================

def export_results(rows, output_dir, script_name=SCRIPT_NAME):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    df = pd.DataFrame(rows)
    excel_path = output_dir / f"{script_name}_{ts}.xlsx"
    df.to_excel(excel_path, index=False, engine="openpyxl")
    print(f"📊 Excel: {excel_path.resolve()}")
    csv_path = output_dir / f"{script_name}_{ts}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"📄 CSV:  {csv_path.resolve()}")
    return excel_path, csv_path


# ==========================================================
# RESUMEN RICH
# ==========================================================

def print_summary(total, vigentes, actualizar, sin_prod, sin_releases, api_calls, cache_used, duration_seconds, deadline):
    if not RICH_AVAILABLE:
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN — Prod Deploy Tracker")
        print(f"   Deadline:            {deadline or 'N/A'}")
        print(f"   Total pipelines CD:  {total}")
        print(f"   Vigentes:            {vigentes}")
        print(f"   Actualizar release:  {actualizar}")
        print(f"   Sin env. Producción: {sin_prod}")
        print(f"   Sin releases:        {sin_releases}")
        print(f"   Cache usado:         {'Sí' if cache_used else 'No'}")
        print(f"   Llamadas API:        {api_calls}")
        print(f"   Duración:            {duration_seconds:.1f}s")
        print(f"{'='*60}")
        return

    console = Console(file=sys.__stdout__)
    table = Table(title="📊 Resumen — Prod Deploy Tracker", show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")
    table.add_row("Deadline", str(deadline or "N/A"))
    table.add_row("Total pipelines CD", str(total))
    table.add_row("✅ Vigentes", str(vigentes))
    table.add_row("⚠️  Actualizar release", str(actualizar))
    table.add_row("❌ Sin env. Producción", str(sin_prod))
    table.add_row("📭 Sin releases", str(sin_releases))
    table.add_row("Cache usado", "✅ Sí" if cache_used else "❌ No")
    table.add_row("Llamadas API", str(api_calls))
    table.add_row("Duración", f"{duration_seconds:.1f}s")
    console.print(table)


# ==========================================================
# MAIN
# ==========================================================

def main():
    parser = argparse.ArgumentParser(description="CD Prod Deploy Tracker — Rastrea último deploy exitoso a Producción")
    parser.add_argument("--pat", default=os.getenv("AZDO_PAT"), help="Azure DevOps PAT")
    parser.add_argument("--org", default=DEFAULT_ORG, help="Organización Azure DevOps")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Proyecto")
    parser.add_argument("--deadline", required=True, help="Fecha deadline (YYYY-MM-DD). Deploy posterior = Vigente, igual o anterior = Actualizar release")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Hilos paralelos")
    parser.add_argument("--output", default=None, help="Directorio de salida")
    parser.add_argument("--force-refresh", action="store_true", help="Ignorar cache propio, consultar APIs")
    parser.add_argument("--skip-cache", action="store_true", help="Alias de --force-refresh")
    args = parser.parse_args()
    args.org = normalize_org(args.org)

    if not args.pat:
        print("❌ Se requiere --pat o env AZDO_PAT")
        sys.exit(1)

    # Parse deadline
    try:
        deadline_date = date.fromisoformat(args.deadline)
    except ValueError:
        print(f"❌ Formato de deadline inválido: {args.deadline}. Usar YYYY-MM-DD")
        sys.exit(1)

    output_dir = get_output_dir(args.output or "outcome")
    output_dir.mkdir(parents=True, exist_ok=True)

    tee = setup_logging()
    start_time = time.time()
    api_calls = 0
    cache_used = False
    rows = []

    try:
        # ============================================
        # PASO 1: Verificar cache propio
        # ============================================
        if not args.force_refresh and not args.skip_cache:
            cache_path = _find_latest_cache()
            if cache_path and _cache_is_fresh(cache_path):
                print(f"📦 Cache encontrado: {cache_path.name} (fresh)")
                # Verificar que el deadline coincide
                data = _load_cache(cache_path)
                cached_deadline = data.get("metadata", {}).get("deadline", "")
                if cached_deadline == str(deadline_date):
                    print("⏭️  Mismo deadline — generando outputs desde cache...")
                    rows = data.get("rows", [])
                    cache_used = True
                else:
                    print(f"⚠️  Deadline diferente (cache={cached_deadline}, solicitado={deadline_date}). Re-consultando...")
            else:
                print("📭 Cache propio no encontrado o > 24h. Consultando APIs...")
        else:
            print("🔄 Force refresh — consultando APIs...")

        if not rows:
            # ============================================
            # PASO 2: Cargar datos base desde cache CD
            # ============================================
            cd_cache_path = _find_cd_cache()
            if not cd_cache_path:
                print("❌ No se encontró cache CD. Ejecutar herramienta 15 (CD Inventory) primero.")
                print("   Comando: python cicd_inventory_cd_detailed.py --org {org} --project {project}")
                sys.exit(1)

            print(f"📦 Cache CD encontrado: {cd_cache_path.name}")
            cd_data = _load_cache(cd_cache_path)
            cd_rows = cd_data.get("rows", [])

            if not cd_rows:
                print("❌ Cache CD vacío. Ejecutar herramienta 15 (CD Inventory) primero.")
                sys.exit(1)

            print(f"📋 {len(cd_rows)} pipelines CD cargados desde cache")

            # ============================================
            # PASO 3: Consultar releases por pipeline (paralelo)
            # ============================================
            headers = get_headers(args.pat)
            total = len(cd_rows)
            processed = 0

            print(f"🔍 Consultando releases con environments + artifacts ({total} pipelines)...")

            if RICH_AVAILABLE:
                tee.pause_terminal()
                with _progress_context() as progress:
                    task = progress.add_task("Rastreando deploys a Prod", total=total)
                    with ThreadPoolExecutor(max_workers=args.workers) as executor:
                        futures = {
                            executor.submit(_fetch_prod_deploy, cd_row, headers, args.org, args.project, deadline_date): cd_row
                            for cd_row in cd_rows
                        }
                        for future in as_completed(futures):
                            try:
                                result = future.result()
                                if result:
                                    rows.append(result)
                                    api_calls += 1
                            except Exception as e:
                                cd_name = futures[future].get("name", futures[future].get("cd_pipeline_name", "?"))
                                print(f"❌ Error en pipeline {cd_name}: {e}")
                            processed += 1
                            progress.update(task, advance=1)
                tee.resume_terminal()
            else:
                with ThreadPoolExecutor(max_workers=args.workers) as executor:
                    futures = {
                        executor.submit(_fetch_prod_deploy, cd_row, headers, args.org, args.project, deadline_date): cd_row
                        for cd_row in cd_rows
                    }
                    for i, future in enumerate(as_completed(futures), 1):
                        try:
                            result = future.result()
                            if result:
                                rows.append(result)
                                api_calls += 1
                        except Exception as e:
                            cd_name = futures[future].get("name", futures[future].get("cd_pipeline_name", "?"))
                            print(f"❌ Error en pipeline {cd_name}: {e}")
                        if i % 10 == 0 or i == total:
                            print(f"  Progreso: {i}/{total} ({int(i/total*100)}%)")

            # ============================================
            # PASO 4: Guardar cache propio
            # ============================================
            cache_data = {
                "metadata": {
                    "script": SCRIPT_NAME,
                    "org": args.org,
                    "project": args.project,
                    "deadline": str(deadline_date),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "count": len(rows),
                },
                "rows": rows,
            }
            cache_path = _save_cache(cache_data)
            print(f"💾 Cache guardado: {cache_path.name}")

        # ============================================
        # PASO 5: Exportar resultados
        # ============================================
        if rows:
            export_results(rows, output_dir)
        else:
            print("⚠️  No hay datos para exportar")

        # ============================================
        # PASO 6: Resumen
        # ============================================
        vigentes = sum(1 for r in rows if r.get("deadline_status") == "Vigente")
        actualizar = sum(1 for r in rows if r.get("deadline_status") == "Actualizar release")
        sin_prod = sum(1 for r in rows if r.get("deadline_status") == "Sin env. Producción")
        sin_releases = sum(1 for r in rows if r.get("deadline_status") == "Sin releases")

        duration = time.time() - start_time
        print_summary(
            total=len(rows),
            vigentes=vigentes,
            actualizar=actualizar,
            sin_prod=sin_prod,
            sin_releases=sin_releases,
            api_calls=api_calls,
            cache_used=cache_used,
            duration_seconds=duration,
            deadline=deadline_date,
        )

    finally:
        teardown_logging(tee)


if __name__ == "__main__":
    main()
