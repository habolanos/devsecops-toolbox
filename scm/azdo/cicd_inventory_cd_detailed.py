#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CD Pipeline Detailed Inventory v1.0.5
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
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

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
DEFAULT_WORKERS = 10
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


def normalize_org(org: str) -> str:
    """Extrae nombre de organización desde URL o nombre simple."""
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

def _extract_variables(definition_detail):
    """Extrae variables del detalle de un release definition.
    
    Azure DevOps retorna variables como:
        {"branchConfig": {"value": "cadenaSuministro", "allowOverride": false}, ...}
    """
    variables = definition_detail.get("variables", {}) or {}
    var_list = []
    for var_name, var_data in variables.items():
        val = var_data.get("value", "") if isinstance(var_data, dict) else str(var_data)
        var_list.append({"name": var_name, "value": val})
    return var_list


def _variables_to_string(var_list):
    """Convierte lista de variables a string legible para reporte."""
    if not var_list:
        return ""
    return "; ".join(f"{v['name']}={v['value']}" for v in var_list)


def _count_stage_tasks(envs):
    """Cuenta tareas por stage: environments[].deployPhases[].workflowTasks[].

    Retorna (lista [(nombre_stage, n_tareas)], total). Cubre todas las fases
    del stage (agent job, agentless, deployment group) pues cada una es un
    deployPhase con sus propias workflowTasks.
    """
    per_stage = []
    total = 0
    for env in envs or []:
        phases = env.get("deployPhases") or []
        n = sum(len(p.get("workflowTasks") or []) for p in phases)
        per_stage.append((env.get("name", "?"), n))
        total += n
    return per_stage, total


# ==========================================================
# RELEASE STATS POR STAGE (conteo, frecuencia, tiempo entre stages)
# ==========================================================

_RELEASE_OK = {"succeeded", "partiallysucceeded"}


def _parse_dt(value):
    """Parsea timestamp ISO 8601 de Azure DevOps ('Z' u offset) a datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _env_key(env):
    """Clave estable de un environment: definitionEnvironmentId > id > nombre."""
    return (env.get("definitionEnvironmentId") or env.get("id")
            or (env.get("name") or "").strip().lower())


def _first_deploy_ts(release_env):
    """Primer deploy exitoso del env dentro del release (deploySteps status ok)."""
    times = []
    for step in release_env.get("deploySteps") or []:
        if (step.get("status") or "").lower() in _RELEASE_OK:
            dt = _parse_dt(step.get("lastDeployedOn") or step.get("completedOn")
                           or step.get("lastModifiedOn") or step.get("requestedOn"))
            if dt:
                times.append(dt)
    return min(times) if times else None


def _release_stage_stats(def_envs, releases):
    """Estadísticas por stage desde el historial de releases.

    Retorna lista por stage (orden de la definición, por rank):
      {stage, releases, avg_days, avg_gap_hours}
    - releases: nº de releases que llegaron exitosamente al stage.
    - avg_days: días promedio entre deploys exitosos al stage (None si <2).
    - avg_gap_hours: horas promedio desde el deploy del stage anterior dentro
      del mismo release (None si el stage es el primero o sin pares medibles).
    Matcheo por definitionEnvironmentId (sobrevive renombres de stage).
    """
    envs_sorted = sorted(def_envs or [],
                         key=lambda e: e.get("rank", 10 ** 9))
    rel_env_times = []
    for rel in releases or []:
        times_map = {}
        for rel_env in rel.get("environments") or []:
            t = _first_deploy_ts(rel_env)
            if t is not None:
                times_map[_env_key(rel_env)] = t
        rel_env_times.append(times_map)

    stats = []
    prev_key = None
    for env in envs_sorted:
        key = _env_key(env)
        deploy_times = []
        gaps_h = []
        for times_map in rel_env_times:
            t = times_map.get(key)
            if t is None:
                continue
            deploy_times.append(t)
            if prev_key is not None and prev_key in times_map:
                gap = (t - times_map[prev_key]).total_seconds() / 3600.0
                if gap >= 0:
                    gaps_h.append(gap)
        deploy_times.sort()
        count = len(deploy_times)
        avg_days = (round((deploy_times[-1] - deploy_times[0]).total_seconds()
                          / 86400.0 / (count - 1), 1)
                    if count >= 2 else None)
        avg_gap = round(sum(gaps_h) / len(gaps_h), 1) if gaps_h else None
        stats.append({
            "stage": env.get("name", "?"),
            "releases": count,
            "avg_days": avg_days,
            "avg_gap_hours": avg_gap,
        })
        prev_key = key
    return stats


def _fetch_cd_pipeline(definition, headers, org, project, max_releases=100):
    """Fetch detalles de un pipeline CD: ambientes, releases, variables."""
    def_id = definition.get("id")
    name = definition.get("name", "")

    # Fetch full definition detail (incluye variables)
    detail_url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions/{def_id}"
    full_detail = safe_az_get(detail_url, headers)

    # Últimos N releases con environments (para stats por stage + último release)
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases"
    last_release = safe_az_get(
        url, headers,
        {"definitionId": def_id, "$top": max_releases, "$expand": "environments"})
    releases = last_release.get("value", []) if isinstance(last_release, dict) else []
    
    last_r = releases[0] if releases else {}
    last_rel_date = last_r.get("createdOn", "")
    last_rel_status = last_r.get("status", "")
    
    # Usar full_detail si está disponible, sino fallback al definition básico
    source = full_detail if full_detail else definition
    envs = source.get("environments", [])
    env_names = [e.get("name", "") for e in envs]
    
    # Extraer variables del full detail
    var_list = _extract_variables(source)
    var_names = [v["name"] for v in var_list]
    var_string = _variables_to_string(var_list)

    stage_tasks, total_tasks = _count_stage_tasks(envs)
    stage_stats = _release_stage_stats(envs, releases)

    result = {
        "id": def_id,
        "name": name,
        "path": definition.get("path", ""),
        "url": definition.get("url", ""),
        "createdOn": definition.get("createdOn", ""),
        "modifiedOn": definition.get("modifiedOn", ""),
        "stagesCount": len(envs),
        "stages": " / ".join(env_names),
        "totalTasks": total_tasks,
        "totalReleasesAnalyzed": len(releases),
        "lastReleaseDate": last_rel_date,
        "lastReleaseStatus": last_rel_status,
        "isObsolete": detect_obsolete(name),
        "variableCount": len(var_list),
        "variableNames": ", ".join(var_names),
        "variables": var_string,
    }
    
    # Agregar cada variable como columna individual (var_<name>)
    for v in var_list:
        result[f"var_{v['name']}"] = v["value"]

    # Agregar conteo de tareas por stage como columna individual (tasksPerStage_<stage>)
    for stage_name, n_tasks in stage_tasks:
        result[f"tasksPerStage_{stage_name}"] = n_tasks

    # Stats de releases por stage como columnas individuales
    for st in stage_stats:
        stage_name = st["stage"]
        result[f"releasesPerStage_{stage_name}"] = st["releases"]
        result[f"avgDaysPerStage_{stage_name}"] = (
            st["avg_days"] if st["avg_days"] is not None else "")
        result[f"avgHrsFromPrev_{stage_name}"] = (
            st["avg_gap_hours"] if st["avg_gap_hours"] is not None else "")

    return result


def get_cd_definitions(headers, org, project):
    """Obtiene lista de release definitions."""
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions"
    data = safe_az_get(url, headers, {"$top": 5000})
    return data.get("value", []) if isinstance(data, dict) else []


# ==========================================================
# GRÁFICOS EXCEL — pestaña Charts (openpyxl nativo)
# ==========================================================

def _hist_bins(values, bin_count=12):
    """Histograma de una serie numérica → [(etiqueta_rango, count)]."""
    vals = [v for v in values if isinstance(v, (int, float))]
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if lo == hi:
        return [(f"{lo}", len(vals))]
    step = (hi - lo) / bin_count
    bins = [0] * bin_count
    for v in vals:
        bins[min(int((v - lo) / step), bin_count - 1)] += 1
    return [(f"{lo + i * step:g}–{lo + (i + 1) * step:g}", bins[i])
            for i in range(bin_count) if bins[i]]


def _stage_metric_agg(rows, prefix):
    """Agrega columnas dinámicas prefix_<stage> → [(stage, promedio, suma, n)]."""
    acc = {}
    for row in rows:
        for key, val in row.items():
            if key.startswith(prefix) and isinstance(val, (int, float)):
                stage = key[len(prefix):]
                tot, n = acc.get(stage, (0.0, 0))
                acc[stage] = (tot + val, n + 1)
    return [(s, round(t / n, 1), t, n) for s, (t, n) in acc.items()]


def _add_charts_sheet(excel_path, rows):
    """Post-procesa el xlsx: hoja 'Charts' con gráficos nativos + hojas _data_* ocultas."""
    try:
        from openpyxl import load_workbook
        from openpyxl.chart import BarChart, LineChart, PieChart, Reference, ScatterChart, Series
        from openpyxl.chart.label import DataLabelList
    except ImportError:
        print("⚠️  openpyxl no disponible — pestaña Charts omitida")
        return
    if not rows:
        return

    wb = load_workbook(excel_path)

    def _ds(name, header, data_rows):
        if not data_rows:
            return None, 0
        ws = wb.create_sheet(name)
        ws.sheet_state = "hidden"
        ws.append(header)
        for r in data_rows:
            ws.append(list(r))
        return ws, len(data_rows)

    def _bar(ws, n, title, cat_title, val_title, horizontal=False):
        c = BarChart()
        c.type = "bar" if horizontal else "col"
        c.title = title
        c.style = 10
        c.add_data(Reference(ws, min_col=2, min_row=1, max_row=1 + n),
                   titles_from_data=True)
        c.set_categories(Reference(ws, min_col=1, min_row=2, max_row=1 + n))
        (c.y_axis if horizontal else c.x_axis).title = cat_title
        (c.x_axis if horizontal else c.y_axis).title = val_title
        c.legend = None
        c.width, c.height = 22, 11
        return c

    def _donut(ws, n, title):
        c = PieChart()
        c.title = title
        c.style = 10
        c.add_data(Reference(ws, min_col=2, min_row=1, max_row=1 + n),
                   titles_from_data=True)
        c.set_categories(Reference(ws, min_col=1, min_row=2, max_row=1 + n))
        c.dataLabels = DataLabelList()
        c.dataLabels.showPercent = True
        c.width, c.height = 16, 11
        return c

    charts = []

    # G1 Histograma: stages por pipeline
    ws, n = _ds("_data_hist_stages", ["Rango stages", "Pipelines"],
                _hist_bins([r.get("stagesCount") for r in rows]))
    if n:
        charts.append(_bar(ws, n, "P1 — Distribución de stages por pipeline",
                           "Stages", "Pipelines"))
    # G2 Histograma: tasks por pipeline
    ws, n = _ds("_data_hist_tasks", ["Rango tasks", "Pipelines"],
                _hist_bins([r.get("totalTasks") for r in rows]))
    if n:
        charts.append(_bar(ws, n, "P2 — Distribución de tasks por pipeline",
                           "Tasks", "Pipelines"))
    # G3 Scatter: stages vs tasks (complejidad vs alcance)
    scatter_rows = [(r["stagesCount"], r["totalTasks"]) for r in rows
                    if isinstance(r.get("stagesCount"), (int, float))
                    and isinstance(r.get("totalTasks"), (int, float))]
    ws, n = _ds("_data_scatter", ["Stages", "Tasks"], scatter_rows)
    if n:
        c = ScatterChart()
        c.title = "P3 — Stages vs Tasks (complejidad)"
        c.style = 13
        c.x_axis.title, c.y_axis.title = "Stages", "Tasks"
        c.x_axis.delete = c.y_axis.delete = False
        c.add_data(Reference(ws, min_col=1, min_row=1, max_col=2,
                             max_row=1 + n), titles_from_data=True)
        c.legend = None
        c.width, c.height = 22, 11
        charts.append(c)
    # G4 Pareto: releases por stage (top 20, barra + % acumulado)
    rel_stats = sorted(_stage_metric_agg(rows, "releasesPerStage_"),
                       key=lambda t: -t[2])[:20]
    total_rel = sum(t[2] for t in rel_stats) or 1
    cum = 0.0
    pareto = []
    for s, _avg, tot, _n in rel_stats:
        cum += tot
        pareto.append((s, tot, round(cum / total_rel * 100, 1)))
    ws, n = _ds("_data_pareto", ["Stage", "Releases", "% Acumulado"], pareto)
    if n:
        c = _bar(ws, n, "P4 — Pareto: releases por stage (top 20)",
                 "Stage", "Releases")
        c.y_axis.majorGridlines = None
        line = LineChart()
        line.add_data(Reference(ws, min_col=3, min_row=1, max_row=1 + n),
                      titles_from_data=True)
        line.y_axis.axId = 200
        line.y_axis.title = "% acumulado"
        line.y_axis.crosses = "max"
        line.y_axis.scaling.max = 100
        c += line
        charts.append(c)
    # G5 Cuellos de botella: horas promedio de tránsito por stage (top 15)
    transit = sorted(_stage_metric_agg(rows, "avgHrsFromPrev_"),
                     key=lambda t: -t[1])[:15]
    ws, n = _ds("_data_bottleneck", ["Stage", "Hrs prom. desde stage previo"],
                [(s, avg) for s, avg, _t, _n in transit])
    if n:
        charts.append(_bar(ws, n, "P5 — Cuellos de botella: tránsito "
                                  "promedio por stage (hrs)",
                           "Hrs", "Stage", horizontal=True))
    # G6 Donut: estado del último release
    status = {}
    for r in rows:
        s = str(r.get("lastReleaseStatus") or "Sin releases")
        status[s] = status.get(s, 0) + 1
    ws, n = _ds("_data_status", ["Estado", "Pipelines"],
                sorted(status.items(), key=lambda kv: -kv[1]))
    if n:
        charts.append(_donut(ws, n, "P6 — Estado del último release"))
    # G7 Donut: obsoletos vs activos
    obs = {}
    for r in rows:
        k = "Obsoleto" if r.get("isObsolete") == "Sí" else "Activo"
        obs[k] = obs.get(k, 0) + 1
    ws, n = _ds("_data_obsolete", ["Estado", "Pipelines"], sorted(obs.items()))
    if n:
        charts.append(_donut(ws, n, "P7 — Pipelines obsoletos vs activos"))
    # G8 Cadencia: días promedio entre deploys por stage (top 20 más usados)
    cad = sorted(_stage_metric_agg(rows, "avgDaysPerStage_"),
                 key=lambda t: -t[3])[:20]
    ws, n = _ds("_data_cadence", ["Stage", "Días prom. entre deploys"],
                [(s, avg) for s, avg, _t, _n in cad])
    if n:
        charts.append(_bar(ws, n, "P8 — Cadencia de deploy por stage "
                                  "(días prom., top 20 por volumen)",
                           "Stage", "Días"))

    if not charts:
        return
    cs = wb.create_sheet("Charts", 0)
    for i, ch in enumerate(charts):
        cs.add_chart(ch, f"{'A' if i % 2 == 0 else 'N'}{1 + (i // 2) * 24}")
    wb.save(excel_path)
    print(f"   📊 Hoja Charts: {len(charts)} gráficos nativos Excel")


# ==========================================================
# EXPORT
# ==========================================================

def export_results(rows, output_dir, script_name=SCRIPT_NAME):

    """Exporta resultados usando ExportManager centralizado con fallback."""

    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual con pandas
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        df = pd.DataFrame(rows)
        excel_path = output_dir / f"{script_name}_{ts}.xlsx"
        df.to_excel(excel_path, index=False, engine="openpyxl")
        print(f"📊 Excel: {excel_path.resolve()}")
        _add_charts_sheet(str(excel_path), rows)
        csv_path = output_dir / f"{script_name}_{ts}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"📄 CSV:  {csv_path.resolve()}")
        return excel_path, csv_path
    
    # Usar ExportManager
    manager = ExportManager(script_name, "1.0.5")
    
    summary = {
        "total_pipelines": len(rows),
    }
    
    # Exportar a JSON
    json_path = manager.export_json(rows, summary=summary)
    if json_path:
        print(f"📋 JSON: {json_path}")
    
    # Exportar a CSV
    csv_path = manager.export_csv(rows)
    if csv_path:
        print(f"📄 CSV:  {csv_path}")
    
    # Exportar a Excel
    excel_path = manager.export_excel(rows, sheet_name="CD Pipelines", summary=summary)
    if excel_path:
        _add_charts_sheet(str(excel_path), rows)
        print(f"📊 Excel: {excel_path}")

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
    parser.add_argument("--var-name", default=None, help="Filtrar pipelines que tienen esta variable (ej: branchConfig)")
    parser.add_argument("--var-value", default=None, help="Filtrar pipelines donde la variable --var-name tiene este valor (ej: cadenaSuministro)")
    parser.add_argument("--max-releases", type=int, default=100, help="Releases por pipeline para stats por stage (default 100)")
    parser.add_argument("--force-refresh", action="store_true", help="Ignorar cache, consultar APIs")
    parser.add_argument("--skip-cache", action="store_true", help="Alias de --force-refresh")
    parser.add_argument("--use-cache-only", action="store_true", help="Solo cache, falla si no existe o > 24h")
    args = parser.parse_args()
    args.org = normalize_org(args.org)

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
                        futures = {executor.submit(_fetch_cd_pipeline, d, headers, args.org, args.project, args.max_releases): d for d in definitions}
                        for future in as_completed(futures):
                            try:
                                result = future.result()
                                if result:
                                    rows.append(result)
                                    api_calls += 3
                            except Exception as e:
                                print(f"❌ Error procesando pipeline: {e}")
                            processed += 1
                            progress.update(task, advance=1)
                tee.resume_terminal()
            else:
                with ThreadPoolExecutor(max_workers=args.workers) as executor:
                    futures = {executor.submit(_fetch_cd_pipeline, d, headers, args.org, args.project, args.max_releases): d for d in definitions}
                    for i, future in enumerate(as_completed(futures), 1):
                        try:
                            result = future.result()
                            if result:
                                rows.append(result)
                                api_calls += 3
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
        
        # Filtrar por variable si se especificó
        if args.var_name and rows:
            var_key = f"var_{args.var_name}"
            before_count = len(rows)
            if args.var_value:
                rows = [r for r in rows if r.get(var_key) is not None and str(r.get(var_key)) == args.var_value]
                print(f"🔍 Filtro: var '{args.var_name}' = '{args.var_value}' → {len(rows)}/{before_count} pipelines")
            else:
                rows = [r for r in rows if r.get(var_key) is not None]
                print(f"🔍 Filtro: var '{args.var_name}' existe → {len(rows)}/{before_count} pipelines")
            
            if not rows:
                print("⚠️  Ningún pipeline coincide con el filtro de variable")
                return
        
        if rows:
            export_results(rows, output_dir)
            try:
                from azdo_default_export import write_default_reports
                write_default_reports(
                    "cd_detailed_inventory", globals().get("__version__", "1.0.0"), rows,
                    organization=args.org, project=args.project,
                    title="CD Detailed Inventory")
            except Exception:
                pass
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
