#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CD Pipeline Detailed Inventory v1.0.0
Inventario detallado de pipelines CD (Release Definitions) con ambientes, estados y obsolescencia.

Uso:
    python cicd_inventory_cd_detailed.py --org Coppel-Retail --project "Compras.RMI"
    python cicd_inventory_cd_detailed.py --org Coppel-Retail --project "Compras.RMI" --force-refresh
    python cicd_inventory_cd_detailed.py --org Coppel-Retail --project "Compras.RMI" --workers 20

Cache-first: verifica cache previo < 24h para skip APIs. Genera Excel + CSV + JSON cache.
Autor: Harold Adrian Bolanos Rodriguez
"""

import os
import sys
import re
import time
import json
import glob
import requests
import pandas as pd
import argparse
from datetime import datetime, timezone
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
    _FMT_EXT = {"excel": ".xlsx", "csv": ".csv", "json": ".json", "net": ".NET", "netcore": ".NET Core"}
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

SCRIPT_NAME = "cicd_inventory_cd_detailed"
DEFAULT_ORG = "Coppel-Retail"
DEFAULT_PROJECT = "Compras.RMI"
API_VERSION = "7.1"
DEFAULT_WORKERS = 30
CACHE_TTL_HOURS = 24


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
# DETECCIÓN DE OBSOLESCENCIA
# ==========================================================

OBSOLETE_KEYWORDS = ["obsoleto", "obsolete", "_old", "legacy-", "deprecated", "deprecated_"]


def detect_obsolete(name: str) -> str:
    name_lower = name.lower()
    for kw in OBSOLETE_KEYWORDS:
        if kw in name_lower:
            return "Sí"
    return "No"


# ==========================================================
# FETCH CD PIPELINES
# ==========================================================

def _fetch_cd_pipeline(definition, headers, org, project):
    """Fetch detalles de un pipeline CD: ambientes, último release."""
    def_id = definition.get("id")
    name = definition.get("name", "")
    
    # Último release
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases"
    last_release = safe_az_get(url, headers, {"definitionId": def_id, "$top": 1})
    releases = last_release.get("value", []) if isinstance(last_release, dict) else []
    
    last_r = releases[0] if releases else {}
    last_rel_date = last_r.get("createdOn", "")
    last_rel_status = last_r.get("status", "")
    
    envs = definition.get("environments", [])
    env_names = [e.get("name", "") for e in envs]
    
    return {
        "id": def_id,
        "name": name,
        "path": definition.get("path", ""),
        "url": definition.get("url", ""),
        "createdOn": definition.get("createdOn", ""),
        "modifiedOn": definition.get("modifiedOn", ""),
        "environmentsCount": len(envs),
        "environments": " / ".join(env_names),
        "lastReleaseDate": last_rel_date,
        "lastReleaseStatus": last_rel_status,
        "isObsolete": detect_obsolete(name),
    }


def get_cd_definitions(headers, org, project):
    """Obtiene lista de release definitions."""
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions"
    data = safe_az_get(url, headers, {"$top": 5000})
    return data.get("value", []) if isinstance(data, dict) else []


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

def print_summary(total, processed, api_calls, cache_used, duration_seconds):
    if not RICH_AVAILABLE:
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN")
        print(f"   Total pipelines CD:  {total}")
        print(f"   Procesados:          {processed}")
        print(f"   Cache usado:         {'Sí' if cache_used else 'No'}")
        print(f"   Llamadas API:        {api_calls}")
        print(f"   Duración:            {duration_seconds:.1f}s")
        print(f"{'='*60}")
        return
    
    console = Console(file=sys.__stdout__)
    table = Table(title="📊 Resumen de Ejecución", show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")
    table.add_row("Total pipelines CD", str(total))
    table.add_row("Procesados", str(processed))
    table.add_row("Cache usado", "✅ Sí" if cache_used else "❌ No")
    table.add_row("Llamadas API", str(api_calls))
    table.add_row("Duración", f"{duration_seconds:.1f}s")
    console.print(table)


# ==========================================================
# MAIN
# ==========================================================

def main():
    parser = argparse.ArgumentParser(description="CD Pipeline Detailed Inventory")
    parser.add_argument("--pat", default=os.getenv("AZDO_PAT"), help="Azure DevOps PAT")
    parser.add_argument("--org", default=DEFAULT_ORG, help="Organización Azure DevOps")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Proyecto")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Hilos paralelos")
    parser.add_argument("--output", default=None, help="Directorio de salida")
    parser.add_argument("--force-refresh", action="store_true", help="Ignorar cache, consultar APIs")
    parser.add_argument("--skip-cache", action="store_true", help="Alias de --force-refresh")
    parser.add_argument("--use-cache-only", action="store_true", help="Solo cache, falla si no existe o > 24h")
    args = parser.parse_args()

    if not args.pat:
        print("❌ Se requiere --pat o env AZDO_PAT")
        sys.exit(1)

    output_dir = get_output_dir(args.output or "outcome")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    tee = setup_logging()
    start_time = time.time()
    api_calls = 0
    cache_used = False
    rows = []
    
    try:
        # Verificación previa de cache
        if not args.force_refresh and not args.skip_cache:
            cache_path = _find_latest_cache()
            if cache_path and _cache_is_fresh(cache_path):
                print(f"📦 Cache encontrado: {cache_path.name} (fresh)")
                print("⏭️  Saltando llamadas API — generando outputs desde cache...")
                data = _load_cache(cache_path)
                rows = data.get("rows", [])
                cache_used = True
            else:
                print("📭 Cache no encontrado o > 24h. Consultando APIs...")
        elif args.use_cache_only:
            cache_path = _find_latest_cache()
            if cache_path and _cache_is_fresh(cache_path):
                data = _load_cache(cache_path)
                rows = data.get("rows", [])
                cache_used = True
            else:
                print("❌ Cache no disponible para modo --use-cache-only")
                sys.exit(1)
        else:
            print("🔄 Force refresh — consultando APIs...")

        if not rows:
            headers = get_headers(args.pat)
            
            print("🔍 Cargando release definitions...")
            if RICH_AVAILABLE:
                tee.pause_terminal()
                with Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"), console=Console(file=sys.__stdout__)) as progress:
                    task = progress.add_task("Fetching CD definitions...", total=None)
                    definitions = get_cd_definitions(headers, args.org, args.project)
                    api_calls += 1
                    progress.update(task, total=1, completed=1)
                tee.resume_terminal()
            else:
                definitions = get_cd_definitions(headers, args.org, args.project)
                api_calls += 1
            
            total = len(definitions)
            print(f"📋 {total} CD definitions encontradas")
            
            if total == 0:
                print("⚠️  No se encontraron CD pipelines")
                return
            
            processed = 0
            if RICH_AVAILABLE:
                tee.pause_terminal()
                with _progress_context() as progress:
                    task = progress.add_task("Procesando CD pipelines", total=total)
                    with ThreadPoolExecutor(max_workers=args.workers) as executor:
                        futures = {executor.submit(_fetch_cd_pipeline, d, headers, args.org, args.project): d for d in definitions}
                        for future in as_completed(futures):
                            try:
                                result = future.result()
                                if result:
                                    rows.append(result)
                                    api_calls += 2
                            except Exception as e:
                                print(f"❌ Error procesando pipeline: {e}")
                            processed += 1
                            progress.update(task, advance=1)
                tee.resume_terminal()
            else:
                with ThreadPoolExecutor(max_workers=args.workers) as executor:
                    futures = {executor.submit(_fetch_cd_pipeline, d, headers, args.org, args.project): d for d in definitions}
                    for i, future in enumerate(as_completed(futures), 1):
                        try:
                            result = future.result()
                            if result:
                                rows.append(result)
                                api_calls += 2
                        except Exception as e:
                            print(f"❌ Error procesando pipeline: {e}")
                        if i % 10 == 0 or i == total:
                            print(f"  Progreso: {i}/{total} ({int(i/total*100)}%)")
            
            # Guardar cache
            cache_data = {
                "metadata": {
                    "script": SCRIPT_NAME,
                    "org": args.org,
                    "project": args.project,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "count": len(rows),
                },
                "rows": rows,
            }
            cache_path = _save_cache(cache_data)
            print(f"💾 Cache guardado: {cache_path.name}")
        
        if rows:
            export_results(rows, output_dir)
        else:
            print("⚠️  No hay datos para exportar")
        
        duration = time.time() - start_time
        print_summary(
            total=len(rows),
            processed=len(rows),
            api_calls=api_calls,
            cache_used=cache_used,
            duration_seconds=duration,
        )
        
    finally:
        teardown_logging(tee)


if __name__ == "__main__":
    main()
