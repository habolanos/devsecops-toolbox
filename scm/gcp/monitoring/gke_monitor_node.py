#!/usr/bin/env python3
"""
GKE Node Resources Monitor v1.0.0
Muestra estado de recursos (CPU, memoria) por nodo en cada cluster GKE.
Solo lectura — no modifica ningún recurso.

Uso:
    python gke_node_monitor.py
    python gke_node_monitor.py --project mi-proyecto-id

Autor: Harold Adrian (migrado desde Comercial/scripts/3.py)
"""

import subprocess
import json
import os
import sys
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

# --- Directorio de salida centralizado + helpers GKE (KUBECONFIG aislado) ---
try:
    from utils import (get_output_dir, is_live_terminal, gke_kube_env,
                       gke_context_name, ensure_gke_cluster_credentials)
except ImportError:
    import os as _os
    import sys as _sys
    import atexit as _ax
    import shutil as _sh
    import tempfile as _tf
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
    def is_live_terminal():
        if _sys.stdout.isatty():
            return True
        return _os.environ.get("TTY_COMPATIBLE", "").strip().lower() in {
            "1", "true", "yes", "on"}
    _KCFG_DIR = _Path(_tf.mkdtemp(prefix="gke-kubeconfig-"))
    _ax.register(lambda: _sh.rmtree(_KCFG_DIR, ignore_errors=True))
    def gke_kube_env(cluster_name, project_id=""):
        env = _os.environ.copy()
        key = f"{project_id}-{cluster_name}" if project_id else cluster_name
        env["KUBECONFIG"] = str(_KCFG_DIR / f"{key}.yaml")
        return env
    def gke_context_name(project_id, location, cluster_name):
        return f"gke_{project_id}_{location}_{cluster_name}"
    def ensure_gke_cluster_credentials(project_id, cluster_name, location,
                                       timeout=60, debug=False, logger=None):
        zone_flag = f"--zone={location}" if location.count("-") == 2 else f"--region={location}"
        cmd = (f"gcloud container clusters get-credentials {cluster_name} "
               f"--project={project_id} {zone_flag} --quiet")
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               timeout=timeout, env=gke_kube_env(cluster_name, project_id))
            return r.returncode == 0
        except Exception:
            return False
# -------------------------------------------------------------------

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("⚠️  Rich no instalado. Ejecuta: pip install rich")
    sys.exit(1)

console = Console()
VERSION = "1.0.0"


class _NullProgress:
    """Fallback sin TTY: imprime las actualizaciones como líneas.
    Rich Progress requiere terminal interactiva; en pipes dibuja un
    frame por línea (el spinner 'salta')."""
    def __init__(self, console):
        self._console = console
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def add_task(self, description, total=None):
        self._console.print(description)
        return 0
    def update(self, *args, description=None, **kwargs):
        if description:
            self._console.print(description)


def _progress_ctx():
    """Progress real en TTY (o TTY_COMPATIBLE vía launcher); si no, shim de líneas."""
    if is_live_terminal():
        return Progress(SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"))
    return _NullProgress(console)



try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

def run_cmd(cmd: list[str], env: Optional[dict] = None) -> tuple[str, str, int]:
    """Ejecuta un comando y retorna (stdout, stderr, returncode)."""
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def run_json(cmd: list[str], env: Optional[dict] = None) -> Optional[dict | list]:
    """Ejecuta un comando que retorna JSON; retorna None si falla."""
    stdout, stderr, rc = run_cmd(cmd, env=env)
    if rc != 0:
        console.print(f"  ⚠️  Error: {stderr[:200]}", style="red")
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        console.print(f"  ⚠️  JSON inválido: {stdout[:200]}", style="red")
        return None


def pct_color(value_str: str) -> str:
    """Retorna el color Rich según el porcentaje."""
    try:
        val = float(value_str.replace("%", ""))
        if val > 80:
            return "red"
        elif val > 50:
            return "yellow"
        else:
            return "green"
    except (ValueError, TypeError):
        return "white"


def pct_float(value_str: str) -> float:
    """Extrae float de un string de porcentaje."""
    try:
        return float(value_str.replace("%", ""))
    except (ValueError, TypeError):
        return 0.0


def get_cluster_list(project: Optional[str] = None) -> list[dict]:
    """Lista todos los clusters GKE del proyecto."""
    cmd = ["gcloud", "container", "clusters", "list", "--format=json"]
    if project:
        cmd += ["--project", project]
    data = run_json(cmd)
    return data if data else []


def get_nodes_resources(context: str, env: Optional[dict] = None) -> list[dict]:
    """Retorna CPU y memoria de cada nodo."""
    cmd_info = [
        "kubectl", "get", "nodes", "--context", context,
        "-o", "jsonpath={range .items[*]}{.metadata.name}{'|'}"
        "{.status.allocatable.cpu}{'|'}"
        "{.status.allocatable.memory}{'|'}"
        "{.status.allocatable.pods}{'|'}"
        "{.metadata.labels.topology\\.kubernetes\\.io/zone}{'\\n'}{end}"
    ]
    stdout_info, _, rc_info = run_cmd(cmd_info, env=env)

    cmd_top = ["kubectl", "top", "nodes", "--context", context, "--no-headers"]
    stdout_top, _, rc_top = run_cmd(cmd_top, env=env)

    node_info = {}
    if rc_info == 0:
        for line in stdout_info.splitlines():
            parts = line.split("|")
            if len(parts) >= 5:
                name = parts[0].strip()
                node_info[name] = {
                    "name":       name,
                    "cpu_alloc":  parts[1].strip(),
                    "mem_alloc":  parts[2].strip(),
                    "pods_max":   parts[3].strip(),
                    "zone":       parts[4].strip(),
                    "cpu_used":   "N/A",
                    "cpu_pct":    "N/A",
                    "mem_used":   "N/A",
                    "mem_pct":    "N/A",
                }

    if rc_top == 0:
        for line in stdout_top.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                name = parts[0]
                if name in node_info:
                    node_info[name]["cpu_used"] = parts[1]
                    node_info[name]["cpu_pct"]  = parts[2]
                    node_info[name]["mem_used"] = parts[3]
                    node_info[name]["mem_pct"]  = parts[4]

    return list(node_info.values())


def show_summary_table(rows: list[dict]):
    """Tabla consolidada de nodos (multi-proyecto) con columnas Project/Cluster."""
    table = Table(
        title="Recursos por Nodo — GKE",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white on dark_blue",
        border_style="grey50",
        padding=(0, 1),
    )

    table.add_column("Project",     style="cyan", min_width=20)
    table.add_column("Cluster",     style="cyan", min_width=15)
    table.add_column("Nodo",        style="bold", min_width=20)
    table.add_column("Zona",        style="dim",  min_width=12)
    table.add_column("CPU Total",   style="white", justify="right", min_width=8)
    table.add_column("CPU Uso",     style="white", justify="right", min_width=8)
    table.add_column("CPU %",       style="white", justify="right", min_width=6)
    table.add_column("Mem Total",   style="white", justify="right", min_width=10)
    table.add_column("Mem Uso",     style="white", justify="right", min_width=10)
    table.add_column("Mem %",       style="white", justify="right", min_width=6)
    table.add_column("Pods",        style="white", justify="right", min_width=5)

    for n in rows:
        cpu_color = pct_color(n.get("cpu_pct", "0%"))
        mem_color = pct_color(n.get("mem_pct", "0%"))

        table.add_row(
            n["project"],
            n["cluster"],
            n["name"],
            n["zone"],
            n["cpu_alloc"],
            n["cpu_used"],
            Text(n["cpu_pct"], style=cpu_color),
            n["mem_alloc"],
            n["mem_used"],
            Text(n["mem_pct"], style=mem_color),
            n["pods_max"],
        )

    console.print(table)
    console.print()


_NODE_CSS = """
:root {
    --bg-dark: #0f1419;
    --bg-card: #1a1f26;
    --border: #2d3748;
    --text-primary: #e2e8f0;
    --text-secondary: #a0aec0;
    --success: #48bb78;
    --warning: #ed8936;
    --danger: #f56565;
    --info: #4299e1;
    --gray: #718096;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background-color: var(--bg-dark);
    color: var(--text-primary);
    line-height: 1.6;
}

.container { max-width: 1500px; margin: 0 auto; padding: 20px; }

header { margin-bottom: 30px; border-bottom: 1px solid var(--border); padding-bottom: 20px; }
h1 { font-size: 2.2em; margin-bottom: 10px; color: var(--info); }
.header-meta { display: flex; flex-wrap: wrap; gap: 20px; color: var(--text-secondary); font-size: 0.9em; }

.filters { background-color: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 30px; }
.filters h3 { color: var(--info); margin-bottom: 15px; font-size: 1.05em; }
.filter-group { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; }
.filter-label { display: block; margin-bottom: 5px; font-size: 0.85em; color: var(--text-secondary); }
select, input { background-color: var(--bg-dark); color: var(--text-primary); border: 1px solid var(--border); border-radius: 4px; padding: 10px; font-size: 0.9em; width: 100%; }
select:focus, input:focus { outline: none; border-color: var(--info); box-shadow: 0 0 5px rgba(66, 153, 225, 0.3); }
.btn-reset { background-color: var(--info); color: #ffffff; border: none; border-radius: 4px; padding: 10px 20px; cursor: pointer; font-size: 0.9em; transition: background-color 0.3s ease; width: 100%; }
.btn-reset:hover { background-color: #3182ce; }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr)); gap: 15px; margin-bottom: 30px; }
.kpi-card { background-color: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 18px; cursor: pointer; transition: all 0.3s ease; }
.kpi-card:hover { border-color: var(--info); box-shadow: 0 0 10px rgba(66, 153, 225, 0.2); }
.kpi-label { color: var(--text-secondary); font-size: 0.78em; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-value { font-size: 1.9em; font-weight: bold; color: var(--info); }
.kpi-value.danger { color: var(--danger); }
.kpi-value.warn { color: var(--warning); }

.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; background-color: var(--bg-card); }
table.data-table { width: 100%; border-collapse: collapse; font-size: 0.88em; }
table.data-table th { background-color: var(--bg-dark); padding: 12px; text-align: left; font-weight: 600; color: var(--info); border-bottom: 1px solid var(--border); white-space: nowrap; }
table.data-table th .th-label { cursor: pointer; user-select: none; }
table.data-table th .th-label:hover { text-decoration: underline; }
table.data-table th.sorted .th-label { color: var(--text-primary); }
.sort-indicator { margin-left: 4px; font-size: 0.8em; color: var(--info); }
table.data-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); white-space: nowrap; max-width: 340px; overflow: hidden; text-overflow: ellipsis; }
table.data-table tbody tr:hover td { background-color: rgba(66, 153, 225, 0.08); }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.empty-row { text-align: center; color: var(--text-secondary); padding: 30px !important; white-space: normal !important; }

.pct-high { background-color: rgba(245, 101, 101, 0.2); color: var(--danger); font-weight: 700; padding: 2px 8px; border-radius: 4px; }
.pct-med { background-color: rgba(237, 137, 54, 0.2); color: var(--warning); font-weight: 700; padding: 2px 8px; border-radius: 4px; }
.pct-low { color: var(--success); }

.section-title { color: var(--info); margin: 30px 0 15px 0; font-size: 1.3em; }
.row-count { color: var(--text-secondary); font-size: 0.85em; margin: 12px 0 30px 0; }
.footer { text-align: center; color: var(--text-secondary); font-size: 0.85em; margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border); }

@media (max-width: 768px) {
    .kpi-grid { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
    h1 { font-size: 1.6em; }
    .header-meta { flex-direction: column; gap: 5px; }
}
"""

# JS plano (sin f-strings) — los datos se inyectan en var REPORT del <script> previo.
_NODE_JS = r"""
var sortKey = null;
var sortDir = 1;

function esc(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function pctCell(v) {
    var n = parseFloat(String(v).replace('%', ''));
    if (isNaN(n)) return esc(v);
    if (n > 80) return '<span class="pct-high">' + esc(v) + '</span>';
    if (n > 50) return '<span class="pct-med">' + esc(v) + '</span>';
    return '<span class="pct-low">' + esc(v) + '</span>';
}

function filteredRows() {
    var p = document.getElementById('filterProject').value;
    var c = document.getElementById('filterCluster').value;
    var q = document.getElementById('filterSearch').value.toLowerCase();
    var minCpu = parseFloat(document.getElementById('filterCpu').value || '0');
    return REPORT.rows.filter(function (r) {
        if (p && r.project !== p) return false;
        if (c && r.cluster !== c) return false;
        var cpu = parseFloat(String(r.cpu_pct).replace('%', ''));
        if (minCpu > 0 && (isNaN(cpu) || cpu < minCpu)) return false;
        if (q && JSON.stringify(r).toLowerCase().indexOf(q) === -1) return false;
        return true;
    });
}

var COLS = [
    { key: 'project', label: 'Project' },
    { key: 'cluster', label: 'Cluster' },
    { key: 'name', label: 'Nodo' },
    { key: 'zone', label: 'Zona' },
    { key: 'cpu_alloc', label: 'CPU Total', right: true },
    { key: 'cpu_used', label: 'CPU Uso', right: true },
    { key: 'cpu_pct', label: 'CPU %', right: true, pct: true },
    { key: 'mem_alloc', label: 'Mem Total', right: true },
    { key: 'mem_used', label: 'Mem Uso', right: true },
    { key: 'mem_pct', label: 'Mem %', right: true, pct: true },
    { key: 'pods_max', label: 'Pods Max', right: true }
];

function sortRows(rows) {
    if (!sortKey) return rows;
    return rows.slice().sort(function (a, b) {
        var va = a[sortKey], vb = b[sortKey];
        var na = parseFloat(String(va).replace('%', ''));
        var nb = parseFloat(String(vb).replace('%', ''));
        if (!isNaN(na) && !isNaN(nb)) return (na - nb) * sortDir;
        return String(va).localeCompare(String(vb)) * sortDir;
    });
}

function sortBy(key) {
    if (sortKey === key) { sortDir = -sortDir; } else { sortKey = key; sortDir = 1; }
    render();
}

function render() {
    var head = '<tr>' + COLS.map(function (c) {
        var ind = sortKey === c.key ? '<span class="sort-indicator">' + (sortDir > 0 ? '▲' : '▼') + '</span>' : '';
        var cls = sortKey === c.key ? ' class="sorted"' : '';
        return '<th' + cls + '><span class="th-label" onclick="sortBy(\'' + c.key + '\')">' +
               c.label + ind + '</span></th>';
    }).join('') + '</tr>';

    var rows = sortRows(filteredRows());
    var body;
    if (!rows.length) {
        body = '<tr><td class="empty-row" colspan="' + COLS.length + '">Sin resultados</td></tr>';
    } else {
        body = rows.map(function (r) {
            return '<tr>' + COLS.map(function (c) {
                var cls = c.right ? ' class="num"' : '';
                if (c.pct) return '<td' + cls + '>' + pctCell(r[c.key]) + '</td>';
                return '<td' + cls + '>' + esc(r[c.key]) + '</td>';
            }).join('') + '</tr>';
        }).join('');
    }

    document.getElementById('nodesTable').innerHTML =
        '<table class="data-table"><thead>' + head + '</thead><tbody>' + body + '</tbody></table>';
    document.getElementById('rowCount').textContent =
        rows.length + ' de ' + REPORT.rows.length + ' nodos';
}

function applyFilters() { render(); }

function resetFilters() {
    document.getElementById('filterProject').value = '';
    document.getElementById('filterCluster').value = '';
    document.getElementById('filterCpu').value = '0';
    document.getElementById('filterSearch').value = '';
    render();
}

function kpiMinCpu(n) {
    document.getElementById('filterCpu').value = String(n);
    render();
}

function renderErrors() {
    var wrap = document.getElementById('errorsSection');
    if (!REPORT.errors.length) { wrap.innerHTML = ''; return; }
    var rows = REPORT.errors.map(function (e) {
        return '<tr><td>' + esc(e.project) + '</td><td>' + esc(e.cluster) + '</td><td>' +
               esc(e.location) + '</td><td>' + esc(e.error) + '</td></tr>';
    }).join('');
    wrap.innerHTML =
        '<h2 class="section-title">🔌 Clusters no accesibles (' + REPORT.errors.length + ')</h2>' +
        '<div class="table-wrap"><table class="data-table"><thead><tr>' +
        '<th>Project</th><th>Cluster</th><th>Location</th><th>Error</th>' +
        '</tr></thead><tbody>' + rows + '</tbody></table></div>';
}

renderErrors();
render();
"""


def _json_for_html(obj) -> str:
    """Serializa a JSON seguro para embeber dentro de un tag <script>."""
    return json.dumps(obj, ensure_ascii=False, default=str).replace('</', '<\\/')


def generate_html(project_ids: list[str], all_rows: list[dict],
                  cluster_errors: list[dict]) -> str:
    """HTML autocontenido, equivalente al dashboard de la opción 1."""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_nodes = len(all_rows)
    clusters_ok = len({(r.get("project"), r.get("cluster")) for r in all_rows})
    cpu_high = sum(1 for r in all_rows if pct_float(r.get("cpu_pct", "0%")) > 80)
    mem_high = sum(1 for r in all_rows if pct_float(r.get("mem_pct", "0%")) > 80)
    clusters_bad = len(cluster_errors)

    projects_sorted = sorted({r.get("project", "") for r in all_rows} | set(project_ids))
    clusters_sorted = sorted({r.get("cluster", "") for r in all_rows})
    project_options = "\n".join(
        f'                        <option value="{p}">{p}</option>' for p in projects_sorted)
    cluster_options = "\n".join(
        f'                        <option value="{c}">{c}</option>' for c in clusters_sorted)

    payload = _json_for_html({
        "generated_at": generated_at,
        "rows": all_rows,
        "errors": cluster_errors,
    })

    kpis = [
        ("📦 Proyectos", len(project_ids), "", ""),
        ("☸️ Clusters", clusters_ok, "", ""),
        ("🖥️ Nodos", total_nodes, "", ""),
        ("🔥 CPU &gt; 80%", cpu_high, "kpiMinCpu(80)", "danger" if cpu_high else ""),
        ("💾 Mem &gt; 80%", mem_high, "", "warn" if mem_high else ""),
        ("🔌 No accesibles", clusters_bad, "", "danger" if clusters_bad else ""),
    ]
    kpi_html = "\n".join(
        '                <div class="kpi-card"{action}>\n'
        '                    <div class="kpi-label">{label}</div>\n'
        '                    <div class="kpi-value {cls}">{value}</div>\n'
        '                </div>'.format(
            action=f' onclick="{action}"' if action else '',
            label=label, cls=cls, value=value)
        for label, value, action, cls in kpis)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GKE Node Resources Monitor</title>
    <style>
{_NODE_CSS}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>☸️ GKE Node Resources Monitor</h1>
            <div class="header-meta">
                <span>Generado: {generated_at}</span>
                <span>Proyectos: {len(project_ids)}</span>
                <span>Clusters consultados: {clusters_ok + clusters_bad}</span>
            </div>
        </header>

        <div class="kpi-grid">
{kpi_html}
        </div>

        <div class="filters">
            <h3>🔍 Filtros</h3>
            <div class="filter-group">
                <div>
                    <label class="filter-label" for="filterProject">Proyecto</label>
                    <select id="filterProject" onchange="applyFilters()">
                        <option value="">Todos los proyectos</option>
{project_options}
                    </select>
                </div>
                <div>
                    <label class="filter-label" for="filterCluster">Cluster</label>
                    <select id="filterCluster" onchange="applyFilters()">
                        <option value="">Todos los clusters</option>
{cluster_options}
                    </select>
                </div>
                <div>
                    <label class="filter-label" for="filterCpu">CPU % mínimo</label>
                    <select id="filterCpu" onchange="applyFilters()">
                        <option value="0">Todos</option>
                        <option value="50">&gt; 50%</option>
                        <option value="80">&gt; 80%</option>
                    </select>
                </div>
                <div>
                    <label class="filter-label" for="filterSearch">Búsqueda</label>
                    <input type="text" id="filterSearch" placeholder="Buscar en la tabla..." onkeyup="applyFilters()">
                </div>
                <div style="display: flex; align-items: flex-end;">
                    <button class="btn-reset" onclick="resetFilters()">🔄 Restablecer</button>
                </div>
            </div>
        </div>

        <h2 class="section-title">🖥️ Nodos</h2>
        <div class="table-wrap" id="nodesTable"></div>
        <div class="row-count" id="rowCount"></div>

        <div id="errorsSection"></div>

        <footer class="footer">
            <p>GKE Node Resources Monitor v{VERSION} | Generado automáticamente por DevSecOps Toolbox</p>
        </footer>
    </div>
    <script>var REPORT = {payload};</script>
    <script>{_NODE_JS}</script>
</body>
</html>
"""


def collect_cluster_nodes(project_id: str, cluster_name: str, location: str) -> list[dict]:
    """Obtiene los nodos de un cluster con KUBECONFIG aislado.

    Lanza RuntimeError si no hay credenciales — main lo colecciona como
    'cluster no accesible' sin abortar el resto.
    """
    if not ensure_gke_cluster_credentials(project_id, cluster_name, location):
        raise RuntimeError(
            f"get-credentials falló para {cluster_name} ({project_id}, {location})")

    context = gke_context_name(project_id, location, cluster_name)
    env = gke_kube_env(cluster_name, project_id)
    nodes = get_nodes_resources(context, env=env)

    if not nodes:
        raise RuntimeError(
            f"kubectl no devolvió nodos para {cluster_name} ({project_id})")

    for n in nodes:
        n["project"] = project_id
        n["cluster"] = cluster_name
    return nodes


def main():
    parser = argparse.ArgumentParser(
        description="GKE Node Resources Monitor - Uso de CPU y memoria por nodo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python gke_monitor_node.py
  python gke_monitor_node.py --project my-gcp-project
  python gke_monitor_node.py --multi-project p1,p2,p3 --output html
        """
    )
    parser.add_argument("--project", "-p", help="GCP Project ID (usa el activo si no se especifica)")
    parser.add_argument("--multi-project", dest="multi_project", default=None,
                       help="IDs de multiples proyectos GCP separados por comas")
    parser.add_argument("--output", "-o", choices=["console", "html"], default="console",
                       help="Formato de salida (default: console)")
    parser.add_argument("--html-file", default=None,
                       help="Archivo HTML de salida (default: <outcome>/gke_node_resources_<ts>.html)")
    args = parser.parse_args()

    if args.multi_project:
        project_ids = [p.strip() for p in args.multi_project.split(",") if p.strip()]
    else:
        project_ids = [args.project] if args.project else [None]

    project_label = ", ".join(p or "(configuración activa)" for p in project_ids)
    console.print(Panel(
        f"[bold cyan]GKE Node Resources Monitor v{VERSION}[/]\n"
        f"Proyecto(s) GCP: {project_label}",
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print()

    # Resolver todos los (proyecto, cluster) a consultar
    targets: list[tuple[str, str, str]] = []
    for pid in project_ids:
        clusters = get_cluster_list(pid)
        if not clusters:
            console.print(f"[yellow]⚠️  Sin clusters GKE accesibles en {pid or '(config activa)'}[/]")
            continue
        for c in clusters:
            name = c.get("name", "unknown")
            location = c.get("location") or c.get("zone") or "unknown"
            targets.append((pid, name, location))

    if not targets:
        console.print("[red]❌ No se encontraron clusters GKE en los proyectos seleccionados.[/]")
        sys.exit(1)

    console.print(f"[green]✅ {len(targets)} cluster(s) a consultar[/]\n")

    all_rows: list[dict] = []
    cluster_errors: list[dict] = []

    def _collect(fut, pid, cname, cloc):
        try:
            all_rows.extend(fut.result())
        except Exception as e:
            err = " ".join(str(e).split())[:300]
            cluster_errors.append({
                "project": pid, "cluster": cname,
                "location": cloc, "error": err,
            })

    with _progress_ctx() as progress:
        task = progress.add_task(
            f"Analizando {len(targets)} cluster(s)...", total=None)
        with ThreadPoolExecutor(max_workers=min(6, len(targets))) as executor:
            futures = {
                executor.submit(collect_cluster_nodes, pid, cname, cloc): (pid, cname, cloc)
                for pid, cname, cloc in targets
            }
            done = 0
            for fut in as_completed(futures):
                _collect(fut, *futures[fut])
                done += 1
                progress.update(task, description=f"✅ {done}/{len(targets)} cluster(s)")

    # Tabla consolidada en consola (columna Project incluida)
    if all_rows:
        all_rows.sort(key=lambda r: (r["project"], r["cluster"], r["name"]))
        show_summary_table(all_rows)
    else:
        console.print("[yellow]⚠️  No se obtuvieron datos de ningún cluster.[/]\n")

    if cluster_errors:
        err_table = Table(
            title=f"🔌 Clusters no accesibles ({len(cluster_errors)})",
            box=box.ROUNDED, show_header=True,
            header_style="bold white on dark_red", border_style="red",
            padding=(0, 1),
        )
        err_table.add_column("Project", style="cyan")
        err_table.add_column("Cluster", style="cyan")
        err_table.add_column("Location", style="dim")
        err_table.add_column("Error", style="red")
        for e in cluster_errors:
            err_table.add_row(e["project"], e["cluster"], e["location"], e["error"][:120])
        console.print(err_table)
        console.print()

    if args.output == "html":
        if args.html_file:
            html_path = args.html_file
        else:
            out_dir = get_output_dir("outcome")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = str(out_dir / f"gke_node_resources_{ts}.html")
        html_content = generate_html(project_ids, all_rows, cluster_errors)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        console.print(f"[green]✅ Reporte HTML guardado: {html_path}[/]")

    if sys.stdin is not None and sys.stdin.isatty():
        console.input("[dim]Presione Enter para continuar...[/]")


if __name__ == "__main__":
    main()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def export_results(data, output_format: str = "json", output_dir: str = "outcome"):
    """Exporta resultados usando ExportManager centralizado con fallback."""
    
    from pathlib import Path
    import json
    import csv
    from datetime import datetime
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual
        if output_format == "json":
            filepath = output_path / f"gke_monitor_node_{ts}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": data}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"gke_monitor_node_{ts}.csv"
            if isinstance(data, list) and data and isinstance(data[0], dict):
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            return None
        
        print(f"✅ Resultados exportados a: {filepath}")
        return str(filepath)
    
    # Usar ExportManager
    manager = ExportManager("gke_monitor_node", "1.0.0")
    
    summary = {"total_items": len(data) if isinstance(data, list) else 1}
    
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    
    return None
