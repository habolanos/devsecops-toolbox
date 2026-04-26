#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline Health Score Report v1.0.0
Orquestador de salud de pipelines CI/CD con scoring multi-dimensional basado en DORA/SRE.

Genera 1 Excel con 3 pestañas:
  1. CI Inventory — datos consolidados de pipelines CI
  2. CD Inventory — datos consolidados de pipelines CD
  3. Health Score — scoring DORA/SRE + recomendaciones

Uso:
    python azdo_pipeline_health_score.py --org Coppel-Retail --project "Compras.RMI"
    python azdo_pipeline_health_score.py --org Coppel-Retail --project "Compras.RMI" --offline
    python azdo_pipeline_health_score.py --org Coppel-Retail --project "Compras.RMI" --skip-incremental

Autor: Harold Adrian Bolanos Rodriguez
"""

import os
import sys
import re
import time
import json
import glob
import math
import subprocess
import requests
import pandas as pd
import argparse
from datetime import datetime, timezone, timedelta
from base64 import b64encode
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, Future

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

SCRIPT_NAME = "azdo_pipeline_health_score"
DEFAULT_ORG = "Coppel-Retail"
DEFAULT_PROJECT = "Compras.RMI"
API_VERSION = "7.1"
DEFAULT_WORKERS = 30
CACHE_TTL_HOURS = 24

# ==========================================================
# UTILIDADES
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
            SpinnerColumn(), TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40), TaskProgressColumn(),
            TextColumn("({task.completed}/{task.total})"), TimeElapsedColumn(),
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
                print(f"⚠️  {r.status_code} en {url[:60]}... retry {attempt+1}/{max_retries}")
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


def _find_latest_cache(pattern_key: str):
    """Busca archivo cache más reciente por patrón de nombre."""
    output_dir = get_output_dir("outcome")
    cache_dir = output_dir / ".cache"
    pattern = str(cache_dir / f"{pattern_key}_raw_*.json")
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


def _save_cache(data, prefix):
    output_dir = get_output_dir("outcome")
    cache_dir = output_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{prefix}_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return cache_path


# ==========================================================
# FETCH BASE DATA (CI/CD definitions)
# ==========================================================

def fetch_ci_definitions(headers, org, project):
    url = f"https://dev.azure.com/{org}/{project}/_apis/build/definitions"
    data = safe_az_get(url, headers, {"$top": 5000})
    return data.get("value", []) if isinstance(data, dict) else []


def fetch_cd_definitions(headers, org, project):
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions"
    data = safe_az_get(url, headers, {"$top": 5000})
    return data.get("value", []) if isinstance(data, dict) else []


# ==========================================================
# FETCH INCREMENTAL: Last 20 executions per pipeline
# ==========================================================

def fetch_ci_builds(def_id, headers, org, project, top=20):
    url = f"https://dev.azure.com/{org}/{project}/_apis/build/builds"
    data = safe_az_get(url, headers, {"definitions": def_id, "$top": top})
    return data.get("value", []) if isinstance(data, dict) else []


def fetch_cd_releases(def_id, headers, org, project, top=20):
    url = f"https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases"
    data = safe_az_get(url, headers, {"definitionId": def_id, "$top": top})
    return data.get("value", []) if isinstance(data, dict) else []


# ==========================================================
# TECNOLOGÍA Y CICLO DE VIDA
# ==========================================================

TECH_VERSION_PATTERNS = [
    (r"springboot[\s_-]?3", "Spring Boot", "3.x", "Moderna"),
    (r"springboot[\s_-]?2", "Spring Boot", "2.x", "Mantenimiento"),
    (r"spring[\s_-]?boot", "Spring Boot", "", "Desconocido"),
    (r"angular[\s_-]?(19|2[0-9])", "Angular", "19+", "Moderna"),
    (r"angular[\s_-]?(14|15|16|17|18)", "Angular", "14-18", "Mantenimiento"),
    (r"angular", "Angular", "<14", "EOL"),
    (r"react", "React", "", "Moderna"),
    (r"dotnet[\s_-]?(8|9)", ".NET", "8/9", "Moderna"),
    (r"dotnet[\s_-]?6", ".NET", "6", "Mantenimiento"),
    (r"dotnet[\s_-]?(core|5|7)", ".NET Core", "", "Mantenimiento"),
    (r"\.net[\s_-]?framework", ".NET Framework", "4.x", "EOL"),
    (r"net[\s_-]?framework", ".NET Framework", "4.x", "EOL"),
    (r"php[\s_-]?(8\.[2-9])", "PHP", "8.2+", "Moderna"),
    (r"php[\s_-]?8\.1", "PHP", "8.1", "Mantenimiento"),
    (r"php[\s_-]?(7|8\.0|5)", "PHP", "7/8.0/5", "EOL"),
    (r"php", "PHP", "", "Desconocido"),
    (r"java[\s_-]?(21|17)", "Java", "21/17", "Moderna"),
    (r"java[\s_-]?11", "Java", "11", "Mantenimiento"),
    (r"java[\s_-]?8", "Java", "8", "EOL"),
    (r"java", "Java", "", "Desconocido"),
    (r"kotlin", "Kotlin", "", "Moderna"),
    (r"android", "Android", "", "Moderna"),
    (r"nodejs[\s_-]?(20|22)", "Node.js", "20/22", "Moderna"),
    (r"nodejs[\s_-]?18", "Node.js", "18", "Mantenimiento"),
    (r"nodejs[\s_-]?(16|14)", "Node.js", "16/14", "EOL"),
    (r"node[\s_-]?(20|22)", "Node.js", "20/22", "Moderna"),
    (r"node[\s_-]?18", "Node.js", "18", "Mantenimiento"),
    (r"node", "Node.js", "", "Desconocido"),
    (r"python[\s_-]?(3\.(11|12))", "Python", "3.11/3.12", "Moderna"),
    (r"python[\s_-]?(3\.(9|10))", "Python", "3.9/3.10", "Mantenimiento"),
    (r"python[\s_-]?(3\.[0-8]|2)", "Python", "3.8-/2.x", "EOL"),
    (r"python", "Python", "", "Desconocido"),
    (r"gke|k8s|kubernetes", "Kubernetes", "", "Moderna"),
    (r"docker", "Docker", "", "Moderna"),
    (r"aws", "AWS", "", "Moderna"),
]


def detect_technology_status(name: str):
    name_lower = name.lower()
    for pattern, tech, version, status in TECH_VERSION_PATTERNS:
        if re.search(pattern, name_lower):
            return tech, version, status
    return "Desconocido", "", "Desconocido"


# ==========================================================
# SCORING FUNCTIONS
# ==========================================================

def days_since(dt_str):
    if not dt_str:
        return 9999
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return 9999


def calculate_recency_score(last_exec_str):
    days = days_since(last_exec_str)
    if days <= 1: return 20
    if days <= 7: return 17
    if days <= 14: return 13
    if days <= 30: return 9
    if days <= 60: return 5
    if days <= 90: return 2
    return 0


def calculate_reliability_score(builds):
    if not builds:
        return 0, 0, 5  # no data, no mttr, 5 pts neutral
    total = len(builds)
    successes = sum(1 for b in builds if b.get("result") == "succeeded")
    failures = total - successes
    success_rate = successes / total if total > 0 else 0
    
    # Success rate pts
    if success_rate >= 1.0: sr_pts = 15
    elif success_rate >= 0.95: sr_pts = 12
    elif success_rate >= 0.90: sr_pts = 9
    elif success_rate >= 0.80: sr_pts = 6
    elif success_rate >= 0.60: sr_pts = 3
    else: sr_pts = 0
    
    # MTTR calculation
    mttr_minutes = 0
    if failures > 0 and total >= 2:
        recovery_times = []
        for i in range(len(builds) - 1):
            if builds[i].get("result") != "succeeded":
                # Look ahead for next success
                for j in range(i + 1, len(builds)):
                    if builds[j].get("result") == "succeeded":
                        t1 = datetime.fromisoformat(builds[i].get("finishTime", "").replace("Z", "+00:00")) if builds[i].get("finishTime") else None
                        t2 = datetime.fromisoformat(builds[j].get("finishTime", "").replace("Z", "+00:00")) if builds[j].get("finishTime") else None
                        if t1 and t2:
                            recovery_times.append((t2 - t1).total_seconds() / 60)
                        break
        if recovery_times:
            mttr_minutes = sum(recovery_times) / len(recovery_times)
    
    # MTTR pts
    if mttr_minutes == 0:
        if failures == 0:
            mttr_pts = 10
        else:
            mttr_pts = 5
    elif mttr_minutes <= 15: mttr_pts = 10
    elif mttr_minutes <= 60: mttr_pts = 8
    elif mttr_minutes <= 240: mttr_pts = 6
    elif mttr_minutes <= 1440: mttr_pts = 3
    else: mttr_pts = 0
    
    return min(sr_pts + mttr_pts, 25), mttr_minutes, sr_pts


def calculate_usage_score(count_30d):
    if count_30d is None: count_30d = 0
    if count_30d > 200: return 20
    if count_30d >= 50: return 17
    if count_30d >= 20: return 13
    if count_30d >= 5: return 8
    if count_30d >= 1: return 3
    return 0


def calculate_freshness_score(modified_str):
    days = days_since(modified_str)
    if days <= 7: return 15
    if days <= 30: return 12
    if days <= 90: return 9
    if days <= 180: return 5
    if days <= 365: return 2
    return 0


def calculate_tech_debt_score(process_type, has_yaml, repo_name, tech_status, pipeline_name):
    penalties = 0
    if process_type == "designerJson":
        penalties += 8
    if tech_status == "EOL":
        penalties += 7
    elif tech_status == "Mantenimiento":
        penalties += 4
    if not has_yaml and process_type != "designerJson":
        penalties += 5
    if not repo_name:
        penalties += 3
    name_lower = pipeline_name.lower()
    for kw in ["obsoleto", "obsolete", "_old", "legacy-", "deprecated"]:
        if kw in name_lower:
            penalties += 2
            break
    return max(0, 20 - penalties)


def calculate_dora_profile(count_30d, failure_rate, mttr_minutes):
    if count_30d > 200 and failure_rate < 0.05 and mttr_minutes < 60:
        return "Elite"
    if count_30d >= 50 and failure_rate < 0.15 and mttr_minutes < 1440:
        return "High"
    if count_30d >= 10 and failure_rate < 0.30 and mttr_minutes < 10080:
        return "Medium"
    return "Low"


def generate_recommendation(score, tech_debt, recency_score, dora_profile, count_30d):
    if score >= 75 and dora_profile in ("Elite", "High"):
        return "Mantener"
    if 50 <= score < 75 and tech_debt < 10:
        return "Evolucionar"
    if 25 <= score < 50 and count_30d < 5:
        return "Consolidar"
    if score < 25 and recency_score == 0:
        return "Deprecar"
    if score < 10 and count_30d == 0:
        return "Eliminar"
    if score >= 75:
        return "Mantener"
    if score >= 50:
        return "Evolucionar"
    return "Consolidar"


def demand_level_text(count_30d):
    if count_30d > 200: return "Elite"
    if count_30d >= 50: return "Alto"
    if count_30d >= 10: return "Medio"
    if count_30d >= 1: return "Bajo"
    return "Nulo"


def rating_text(score):
    if score >= 90: return "Excelente"
    if score >= 75: return "Bueno"
    if score >= 50: return "Regular"
    if score >= 25: return "Bajo"
    return "Crítico"


# ==========================================================
# ENRICH CI PIPELINE WITH INCREMENTAL DATA
# ==========================================================

def enrich_ci_pipeline(base_data, headers, org, project, skip_incremental=False):
    def_id = base_data.get("id")
    if skip_incremental:
        return {**base_data, "builds20": [], "failureRate": 0.0, "mttrMinutes": 0}
    
    builds = fetch_ci_builds(def_id, headers, org, project, top=20)
    total = len(builds)
    failures = sum(1 for b in builds if b.get("result") != "succeeded")
    failure_rate = failures / total if total > 0 else 0.0
    
    rel_score, mttr_min, _ = calculate_reliability_score(builds)
    
    return {
        **base_data,
        "builds20": builds,
        "failureRate": failure_rate,
        "mttrMinutes": mttr_min,
        "reliabilityScore": rel_score,
    }


def enrich_cd_pipeline(base_data, headers, org, project, skip_incremental=False):
    def_id = base_data.get("id")
    if skip_incremental:
        return {**base_data, "releases20": [], "failureRate": 0.0, "mttrMinutes": 0}
    
    releases = fetch_cd_releases(def_id, headers, org, project, top=20)
    # CD releases don't have simple result field like CI builds; use status approximation
    total = len(releases)
    failures = sum(1 for r in releases if r.get("status") in ("rejected", "abandoned", "canceled"))
    failure_rate = failures / total if total > 0 else 0.0
    
    # Simplified MTTR for CD (less granular API)
    mttr_min = 0
    if failures > 0 and total >= 2:
        recovery_times = []
        for i in range(len(releases) - 1):
            if releases[i].get("status") in ("rejected", "abandoned", "canceled"):
                for j in range(i + 1, len(releases)):
                    if releases[j].get("status") in ("succeeded", "active"):
                        t1_str = releases[i].get("createdOn", "")
                        t2_str = releases[j].get("createdOn", "")
                        try:
                            t1 = datetime.fromisoformat(t1_str.replace("Z", "+00:00")) if t1_str else None
                            t2 = datetime.fromisoformat(t2_str.replace("Z", "+00:00")) if t2_str else None
                            if t1 and t2:
                                recovery_times.append((t2 - t1).total_seconds() / 60)
                        except Exception:
                            pass
                        break
        if recovery_times:
            mttr_min = sum(recovery_times) / len(recovery_times)
    
    # Reliability score for CD (simplified, no detailed build-level results)
    if failure_rate == 0: sr_pts = 15
    elif failure_rate < 0.05: sr_pts = 12
    elif failure_rate < 0.10: sr_pts = 9
    elif failure_rate < 0.20: sr_pts = 6
    elif failure_rate < 0.40: sr_pts = 3
    else: sr_pts = 0
    
    if mttr_min == 0:
        mttr_pts = 10 if failures == 0 else 5
    elif mttr_min <= 15: mttr_pts = 10
    elif mttr_min <= 60: mttr_pts = 8
    elif mttr_min <= 240: mttr_pts = 6
    elif mttr_min <= 1440: mttr_pts = 3
    else: mttr_pts = 0
    
    rel_score = min(sr_pts + mttr_pts, 25)
    
    return {
        **base_data,
        "releases20": releases,
        "failureRate": failure_rate,
        "mttrMinutes": mttr_min,
        "reliabilityScore": rel_score,
    }


# ==========================================================
# BUILD INVENTORY ROWS
# ==========================================================

def build_ci_row(data, headers, org, project, skip_incremental=False):
    enriched = enrich_ci_pipeline(data, headers, org, project, skip_incremental)
    tech, version, tech_status = detect_technology_status(enriched.get("name", ""))
    
    last_exec = enriched.get("lastExecution", "")
    modified = enriched.get("modifiedDate", "")
    count_30d = enriched.get("totalExecutions30d", 0) or 0
    
    recency = calculate_recency_score(last_exec)
    reliability = enriched.get("reliabilityScore", 0)
    usage = calculate_usage_score(count_30d)
    freshness = calculate_freshness_score(modified)
    tech_debt = calculate_tech_debt_score(
        enriched.get("processType", ""),
        bool(enriched.get("yamlFilename", "")),
        enriched.get("repositoryName", ""),
        tech_status,
        enriched.get("name", "")
    )
    
    health = recency + reliability + usage + freshness + tech_debt
    dora = calculate_dora_profile(count_30d, enriched.get("failureRate", 0), enriched.get("mttrMinutes", 0))
    rec = generate_recommendation(health, tech_debt, recency, dora, count_30d)
    
    return {
        "pipeline_name": enriched.get("name", ""),
        "pipeline_type": "CI",
        "pipeline_path": enriched.get("path", ""),
        "technology": tech,
        "technology_version": version,
        "technology_status": tech_status,
        "health_score": health,
        "rating": rating_text(health),
        "recency_score": recency,
        "reliability_score": reliability,
        "usage_score": usage,
        "freshness_score": freshness,
        "tech_debt_score": tech_debt,
        "last_execution": last_exec,
        "last_execution_status": enriched.get("lastExecutionState", ""),
        "last_execution_result": enriched.get("lastExecutionResult", ""),
        "total_executions_30d": count_30d,
        "total_executions_90d": enriched.get("totalExecutions90d", 0) or 0,
        "total_failures_30d": int((enriched.get("failureRate", 0) or 0) * max(count_30d, 1)),
        "mttr_minutes": round(enriched.get("mttrMinutes", 0) or 0, 1),
        "last_modified": modified,
        "created_date": enriched.get("createdDate", ""),
        "days_since_creation": days_since(enriched.get("createdDate", "")),
        "demand_level": demand_level_text(count_30d),
        "dora_profile": dora,
        "recommendation": rec,
        "process_type": enriched.get("processType", ""),
        "repository_name": enriched.get("repositoryName", ""),
        "yaml_filename": enriched.get("yamlFilename", ""),
    }


def build_cd_row(data, headers, org, project, skip_incremental=False):
    enriched = enrich_cd_pipeline(data, headers, org, project, skip_incremental)
    tech, version, tech_status = detect_technology_status(enriched.get("name", ""))
    
    last_exec = enriched.get("lastReleaseDate", "")
    modified = enriched.get("modifiedOn", "")
    # For CD, estimate count_30d from last release recency (less granular API)
    # Use a placeholder since CD API doesn't provide direct counts easily
    days = days_since(last_exec)
    if days <= 1: count_30d = 30
    elif days <= 7: count_30d = 4
    elif days <= 30: count_30d = 1
    else: count_30d = 0
    
    recency = calculate_recency_score(last_exec)
    reliability = enriched.get("reliabilityScore", 0)
    usage = calculate_usage_score(count_30d)
    freshness = calculate_freshness_score(modified)
    tech_debt = calculate_tech_debt_score(
        "releaseDefinition",  # CD classic releases are like designerJson
        False,
        "",  # CD doesn't always have direct repo
        tech_status,
        enriched.get("name", "")
    )
    
    health = recency + reliability + usage + freshness + tech_debt
    dora = calculate_dora_profile(count_30d, enriched.get("failureRate", 0), enriched.get("mttrMinutes", 0))
    rec = generate_recommendation(health, tech_debt, recency, dora, count_30d)
    
    return {
        "pipeline_name": enriched.get("name", ""),
        "pipeline_type": "CD",
        "pipeline_path": enriched.get("path", ""),
        "technology": tech,
        "technology_version": version,
        "technology_status": tech_status,
        "health_score": health,
        "rating": rating_text(health),
        "recency_score": recency,
        "reliability_score": reliability,
        "usage_score": usage,
        "freshness_score": freshness,
        "tech_debt_score": tech_debt,
        "last_execution": last_exec,
        "last_execution_status": enriched.get("lastReleaseStatus", ""),
        "last_execution_result": "",
        "total_executions_30d": count_30d,
        "total_executions_90d": 0,
        "total_failures_30d": int((enriched.get("failureRate", 0) or 0) * max(count_30d, 1)),
        "mttr_minutes": round(enriched.get("mttrMinutes", 0) or 0, 1),
        "last_modified": modified,
        "created_date": enriched.get("createdOn", ""),
        "days_since_creation": days_since(enriched.get("createdOn", "")),
        "demand_level": demand_level_text(count_30d),
        "dora_profile": dora,
        "recommendation": rec,
        "environments_count": enriched.get("environmentsCount", 0),
        "environments": enriched.get("environments", ""),
        "is_obsolete": enriched.get("isObsolete", "No"),
    }


# ==========================================================
# EXPORT 3-SHEET EXCEL
# ==========================================================

def export_three_sheet_excel(ci_rows, cd_rows, health_rows, output_dir):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_path = output_dir / f"{SCRIPT_NAME}_{ts}.xlsx"
    
    df_ci = pd.DataFrame(ci_rows) if ci_rows else pd.DataFrame()
    df_cd = pd.DataFrame(cd_rows) if cd_rows else pd.DataFrame()
    df_health = pd.DataFrame(health_rows) if health_rows else pd.DataFrame()
    
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        if not df_ci.empty:
            df_ci.to_excel(writer, sheet_name="CI Inventory", index=False)
        if not df_cd.empty:
            df_cd.to_excel(writer, sheet_name="CD Inventory", index=False)
        if not df_health.empty:
            df_health.to_excel(writer, sheet_name="Health Score", index=False)
    
    print(f"📊 Excel generado: {excel_path.resolve()}")
    print(f"   📋 Hoja 1 — CI Inventory:     {len(df_ci)} filas")
    print(f"   📋 Hoja 2 — CD Inventory:     {len(df_cd)} filas")
    print(f"   📊 Hoja 3 — Health Score:     {len(df_health)} filas")
    return excel_path


# ==========================================================
# RESUMEN RICH
# ==========================================================

def print_summary(ci_count, cd_count, cache_ci, cache_cd, api_calls, health_rows, duration):
    ratings = {"Excelente": 0, "Bueno": 0, "Regular": 0, "Bajo": 0, "Crítico": 0}
    for row in health_rows:
        r = row.get("rating", "")
        if r in ratings:
            ratings[r] += 1
    
    if not RICH_AVAILABLE:
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN PIPELINE HEALTH SCORE")
        print(f"   Pipelines CI:        {ci_count}")
        print(f"   Pipelines CD:        {cd_count}")
        print(f"   Cache CI usado:      {'Sí' if cache_ci else 'No'}")
        print(f"   Cache CD usado:      {'Sí' if cache_cd else 'No'}")
        print(f"   Llamadas API:        {api_calls}")
        print(f"   Duración:            {duration:.1f}s")
        print(f"   Distribución:")
        for k, v in ratings.items():
            print(f"      {k}: {v}")
        print(f"{'='*60}")
        return
    
    console = Console(file=sys.__stdout__)
    table = Table(title="📊 Resumen Pipeline Health Score", show_header=True, header_style="bold magenta")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="green")
    table.add_row("Pipelines CI", str(ci_count))
    table.add_row("Pipelines CD", str(cd_count))
    table.add_row("Cache CI usado", "✅ Sí" if cache_ci else "❌ No")
    table.add_row("Cache CD usado", "✅ Sí" if cache_cd else "❌ No")
    table.add_row("Llamadas API", str(api_calls))
    table.add_row("Duración", f"{duration:.1f}s")
    for k, v in ratings.items():
        table.add_row(f"Rating {k}", str(v))
    console.print(table)


# ==========================================================
# MAIN
# ==========================================================

def _launch_proc(label, cmd, env):
    """Lanza un subprocess Popen y retorna el proceso."""
    return subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _fmt_elapsed(seconds):
    """Formatea segundos como Xm Ys."""
    m, s = divmod(int(seconds), 60)
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def _run_inventory_scripts(args, tee):
    """Lanza cicd_inventory_ci_detailed.py y cicd_inventory_cd_detailed.py en paralelo con spinner dinámico."""
    script_dir = Path(__file__).parent
    python_exe = sys.executable
    
    common_env = os.environ.copy()
    common_env["AZDO_PAT"] = args.pat
    
    ci_cmd = [
        python_exe, str(script_dir / "cicd_inventory_ci_detailed.py"),
        "--pat", args.pat,
        "--org", args.org,
        "--project", args.project,
        "--workers", str(args.workers),
    ]
    cd_cmd = [
        python_exe, str(script_dir / "cicd_inventory_cd_detailed.py"),
        "--pat", args.pat,
        "--org", args.org,
        "--project", args.project,
        "--workers", str(args.workers),
    ]
    
    print("\n🔄 Ejecutando inventory CI y CD en paralelo...")
    print(f"   CI: cicd_inventory_ci_detailed.py --org {args.org} --project {args.project}")
    print(f"   CD: cicd_inventory_cd_detailed.py --org {args.org} --project {args.project}")
    
    ci_proc = _launch_proc("CI-Inventory", ci_cmd, common_env)
    cd_proc = _launch_proc("CD-Inventory", cd_cmd, common_env)
    procs = {"CI-Inventory": ci_proc, "CD-Inventory": cd_proc}
    results = {}
    start = time.time()
    
    # Spinner frames
    spinner_frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    frame_idx = 0
    
    if RICH_AVAILABLE:
        tee.pause_terminal()
        console = Console(file=sys.__stdout__)
        from rich.live import Live
        from rich.text import Text
        
        with Live(console=console, refresh_per_second=4, transient=True) as live:
            while procs:
                elapsed = time.time() - start
                frame = spinner_frames[frame_idx % len(spinner_frames)]
                frame_idx += 1
                
                lines = [f"{frame} [bold blue]Inventory en progreso[/] ({_fmt_elapsed(elapsed)})"]
                for label, proc in list(procs.items()):
                    if proc.poll() is not None:
                        rc = proc.returncode
                        icon = "✅" if rc == 0 else "⚠️"
                        lines.append(f"  {icon} {label}: terminado (código {rc})")
                        results[label] = rc
                        del procs[label]
                    else:
                        lines.append(f"  🔄 {label}: ejecutándose...")
                
                live.update(Text.from_markup("\n".join(lines)))
                time.sleep(0.25)
        
        tee.resume_terminal()
    else:
        # Fallback sin Rich: imprimir líneas con \r
        last_print = 0
        while procs:
            elapsed = time.time() - start
            if elapsed - last_print >= 2:
                status_parts = []
                for label, proc in procs.items():
                    status_parts.append(f"{label}: ejecutándose")
                print(f"   ⏳ {_fmt_elapsed(elapsed)} — {', '.join(status_parts)}")
                last_print = elapsed
            
            for label, proc in list(procs.items()):
                if proc.poll() is not None:
                    rc = proc.returncode
                    icon = "✅" if rc == 0 else "⚠️"
                    print(f"   {icon} {label}: terminado (código {rc})")
                    results[label] = rc
                    del procs[label]
            time.sleep(0.5)
    
    # Capturar stderr de procesos terminados para diagnóstico
    for label, rc in results.items():
        proc = ci_proc if label == "CI-Inventory" else cd_proc
        if proc.stderr:
            err_lines = proc.stderr.read().strip().split("\n")[-3:]
            if err_lines and any(l.strip() for l in err_lines):
                print(f"   [{label}] stderr (últimas líneas):")
                for l in err_lines:
                    if l.strip():
                        print(f"      {l.strip()}")
    
    ci_rc = results.get("CI-Inventory", -1)
    cd_rc = results.get("CD-Inventory", -1)
    print(f"   CI-Inventory: código {ci_rc}")
    print(f"   CD-Inventory: código {cd_rc}")
    print("✅ Inventory completado. Continuando con Health Score...\n")


def main():
    parser = argparse.ArgumentParser(description="Pipeline Health Score Report")
    parser.add_argument("--pat", default=os.getenv("AZDO_PAT"), help="Azure DevOps PAT")
    parser.add_argument("--org", default=DEFAULT_ORG, help="Organización")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Proyecto")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Hilos paralelos")
    parser.add_argument("--output", default=None, help="Directorio de salida")
    parser.add_argument("--force-refresh", action="store_true", help="Ignorar cache, re-consultar todo")
    parser.add_argument("--offline", action="store_true", help="Solo usar cache, fallar si no existe")
    parser.add_argument("--skip-incremental", action="store_true", help="No consultar últimas 20 ejecuciones")
    parser.add_argument("--run-inventory", action="store_true", help="Ejecutar CI y CD inventory en hilos paralelos antes de procesar")
    args = parser.parse_args()
    args.org = normalize_org(args.org)

    if not args.pat and not args.offline:
        print("❌ Se requiere --pat o env AZDO_PAT (o usar --offline)")
        sys.exit(1)

    output_dir = get_output_dir(args.output or "outcome")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    tee = setup_logging()
    start_time = time.time()
    api_calls = 0
    ci_rows = []
    cd_rows = []
    health_rows = []
    cache_ci_used = False
    cache_cd_used = False
    
    try:
        # ============================================
        # PASO 0: EJECUTAR INVENTORY EN SEGUNDO PLANO
        # ============================================
        if args.run_inventory and not args.offline:
            _run_inventory_scripts(args, tee)
        
        # ============================================
        # PASO 1: OBTENER DATOS BASE CI
        # ============================================
        ci_base_data = []
        if not args.force_refresh:
            cache_path = _find_latest_cache("cicd_inventory_ci_detailed")
            if cache_path and _cache_is_fresh(cache_path):
                print(f"📦 CI Cache encontrado: {cache_path.name}")
                data = _load_cache(cache_path)
                ci_base_data = data.get("rows", [])
                cache_ci_used = True
            else:
                print("📭 CI Cache no encontrado o > 24h")
        
        if not ci_base_data:
            if args.offline:
                print("❌ Modo offline pero no hay cache CI disponible")
                sys.exit(1)
            print("🔍 Consultando CI definitions...")
            if RICH_AVAILABLE:
                tee.pause_terminal()
                with Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"), console=Console(file=sys.__stdout__)) as progress:
                    task = progress.add_task("Fetching CI definitions...", total=None)
                    headers = get_headers(args.pat)
                    definitions = fetch_ci_definitions(headers, args.org, args.project)
                    api_calls += 1
                    progress.update(task, total=1, completed=1)
                tee.resume_terminal()
            else:
                headers = get_headers(args.pat)
                definitions = fetch_ci_definitions(headers, args.org, args.project)
                api_calls += 1
            
            print(f"📋 {len(definitions)} CI definitions encontradas")
            
            # Simplified base extraction for cache-less mode
            for d in definitions:
                ci_base_data.append({
                    "id": d.get("id"),
                    "name": d.get("name", ""),
                    "path": d.get("path", ""),
                    "url": d.get("url", ""),
                    "createdDate": d.get("createdDate", ""),
                    "modifiedDate": d.get("modifiedDate", ""),
                    "processType": d.get("process", {}).get("type", ""),
                    "yamlFilename": d.get("process", {}).get("yamlFilename", ""),
                    "repositoryName": d.get("repository", {}).get("name", ""),
                    "repositoryUrl": d.get("repository", {}).get("url", ""),
                    "defaultBranch": d.get("repository", {}).get("defaultBranch", ""),
                    "lastPipelineModifier": d.get("authoredBy", {}).get("displayName", ""),
                    "lastExecution": "",
                    "lastExecutionState": "",
                    "lastExecutionResult": "",
                    "totalExecutions30d": 0,
                    "totalExecutions90d": 0,
                })
            
            # Save cache for future
            _save_cache({
                "metadata": {"script": "azdo_pipeline_health_score_ci", "org": args.org, "project": args.project, "generated_at": datetime.now(timezone.utc).isoformat(), "count": len(ci_base_data)},
                "rows": ci_base_data,
            }, "azdo_pipeline_health_score_ci")
            print("💾 CI cache guardado")
        
        # ============================================
        # PASO 2: OBTENER DATOS BASE CD
        # ============================================
        cd_base_data = []
        if not args.force_refresh:
            cache_path = _find_latest_cache("cicd_inventory_cd_detailed")
            if cache_path and _cache_is_fresh(cache_path):
                print(f"📦 CD Cache encontrado: {cache_path.name}")
                data = _load_cache(cache_path)
                cd_base_data = data.get("rows", [])
                cache_cd_used = True
            else:
                print("📭 CD Cache no encontrado o > 24h")
        
        if not cd_base_data:
            if args.offline:
                print("❌ Modo offline pero no hay cache CD disponible")
                sys.exit(1)
            print("🔍 Consultando CD definitions...")
            if RICH_AVAILABLE:
                tee.pause_terminal()
                with Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"), console=Console(file=sys.__stdout__)) as progress:
                    task = progress.add_task("Fetching CD definitions...", total=None)
                    headers = get_headers(args.pat)
                    definitions = fetch_cd_definitions(headers, args.org, args.project)
                    api_calls += 1
                    progress.update(task, total=1, completed=1)
                tee.resume_terminal()
            else:
                headers = get_headers(args.pat)
                definitions = fetch_cd_definitions(headers, args.org, args.project)
                api_calls += 1
            
            print(f"📋 {len(definitions)} CD definitions encontradas")
            
            for d in definitions:
                envs = d.get("environments", [])
                cd_base_data.append({
                    "id": d.get("id"),
                    "name": d.get("name", ""),
                    "path": d.get("path", ""),
                    "url": d.get("url", ""),
                    "createdOn": d.get("createdOn", ""),
                    "modifiedOn": d.get("modifiedOn", ""),
                    "environmentsCount": len(envs),
                    "environments": " / ".join([e.get("name", "") for e in envs]),
                    "lastReleaseDate": "",
                    "lastReleaseStatus": "",
                    "isObsolete": "Sí" if any(kw in d.get("name", "").lower() for kw in ["obsoleto", "obsolete", "_old", "legacy-", "deprecated"]) else "No",
                })
            
            _save_cache({
                "metadata": {"script": "azdo_pipeline_health_score_cd", "org": args.org, "project": args.project, "generated_at": datetime.now(timezone.utc).isoformat(), "count": len(cd_base_data)},
                "rows": cd_base_data,
            }, "azdo_pipeline_health_score_cd")
            print("💾 CD cache guardado")
        
        # ============================================
        # PASO 3: ENRIQUECER CI CON INCREMENTAL
        # ============================================
        print(f"🔧 Enriqueciendo {len(ci_base_data)} CI pipelines...")
        headers = get_headers(args.pat) if args.pat else {}
        
        if RICH_AVAILABLE and ci_base_data:
            tee.pause_terminal()
            with _progress_context() as progress:
                task = progress.add_task("Enriqueciendo CI pipelines", total=len(ci_base_data))
                with ThreadPoolExecutor(max_workers=args.workers) as executor:
                    futures = {executor.submit(build_ci_row, d, headers, args.org, args.project, args.skip_incremental): d for d in ci_base_data}
                    for future in as_completed(futures):
                        try:
                            row = future.result()
                            if row:
                                ci_rows.append(row)
                                health_rows.append(row)
                                api_calls += 1
                        except Exception as e:
                            print(f"❌ Error CI pipeline: {e}")
                        progress.update(task, advance=1)
            tee.resume_terminal()
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {executor.submit(build_ci_row, d, headers, args.org, args.project, args.skip_incremental): d for d in ci_base_data}
                for i, future in enumerate(as_completed(futures), 1):
                    try:
                        row = future.result()
                        if row:
                            ci_rows.append(row)
                            health_rows.append(row)
                            api_calls += 1
                    except Exception as e:
                        print(f"❌ Error CI pipeline: {e}")
                    if i % 10 == 0 or i == len(ci_base_data):
                        print(f"  CI Progreso: {i}/{len(ci_base_data)}")
        
        # ============================================
        # PASO 4: ENRIQUECER CD CON INCREMENTAL
        # ============================================
        print(f"🔧 Enriqueciendo {len(cd_base_data)} CD pipelines...")
        
        if RICH_AVAILABLE and cd_base_data:
            tee.pause_terminal()
            with _progress_context() as progress:
                task = progress.add_task("Enriqueciendo CD pipelines", total=len(cd_base_data))
                with ThreadPoolExecutor(max_workers=args.workers) as executor:
                    futures = {executor.submit(build_cd_row, d, headers, args.org, args.project, args.skip_incremental): d for d in cd_base_data}
                    for future in as_completed(futures):
                        try:
                            row = future.result()
                            if row:
                                cd_rows.append(row)
                                health_rows.append(row)
                                api_calls += 1
                        except Exception as e:
                            print(f"❌ Error CD pipeline: {e}")
                        progress.update(task, advance=1)
            tee.resume_terminal()
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {executor.submit(build_cd_row, d, headers, args.org, args.project, args.skip_incremental): d for d in cd_base_data}
                for i, future in enumerate(as_completed(futures), 1):
                    try:
                        row = future.result()
                        if row:
                            cd_rows.append(row)
                            health_rows.append(row)
                            api_calls += 1
                    except Exception as e:
                        print(f"❌ Error CD pipeline: {e}")
                    if i % 10 == 0 or i == len(cd_base_data):
                        print(f"  CD Progreso: {i}/{len(cd_base_data)}")
        
        # ============================================
        # PASO 5: EXPORTAR
        # ============================================
        if health_rows:
            export_three_sheet_excel(ci_rows, cd_rows, health_rows, output_dir)
        else:
            print("⚠️  No hay datos para exportar")
        
        duration = time.time() - start_time
        print_summary(len(ci_rows), len(cd_rows), cache_ci_used, cache_cd_used, api_calls, health_rows, duration)
        
    finally:
        teardown_logging(tee)


if __name__ == "__main__":
    main()
