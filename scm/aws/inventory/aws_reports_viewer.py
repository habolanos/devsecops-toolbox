#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Reports Viewer — Tool 30

Genera un dashboard HTML interactivo (Chart.js vía CDN, sin deps de
gráficos) a partir de los reportes JSON generados por las demás
herramientas AWS en outcome/:

- Escanea outcome/ buscando *.json con estructura de reporte
- Agrupa por herramienta: items, severidades, status
- Gráficos: doughnut de severidades, barras por herramienta,
  tabla de hallazgos recientes

Equivalente a GCP Tool: Reports Viewer
(reports-viewer/gcp_reports_viewer.py).

Uso:
    python aws_reports_viewer.py
    python aws_reports_viewer.py --input outcome --output reporte.html
"""

import argparse
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "DevSecOps Team"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None

SEVERITY_KEYS = ("critical", "high", "warning", "medium", "low",
                 "info", "fail", "warn")


def _print(msg: str):
    console.print(msg) if console else print(
        re.sub(r"\[/?[a-z_ ]*\]", "", msg))


# ═══════════════════════════════════════════════════════════════════════════════
# Extracción de hallazgos de un JSON de reporte
# ═══════════════════════════════════════════════════════════════════════════════

def extract_findings(data: Dict) -> List[Dict]:
    """Saca hallazgos de cualquier estructura de reporte AWS."""
    for key in ("findings", "issues", "results", "checks",
                "deployments", "functions", "instances"):
        items = data.get(key)
        if isinstance(items, list):
            return items
    # reportes anidados por recurso
    collected = []
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(
                value.get("findings"), list):
            collected.extend(value["findings"])
    return collected


def severity_of(item: Dict) -> str:
    for key in ("severity", "status", "grade", "level"):
        val = str(item.get(key, "")).lower()
        if val in SEVERITY_KEYS or val in ("pass", "ok", "match",
                                           "healthy"):
            return val
    return "info"


def scan_reports(input_dir: Path) -> List[Dict]:
    """Carga todos los JSON de reporte del directorio."""
    reports = []
    for path in sorted(input_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        findings = extract_findings(data)
        reports.append({
            "file": path.name,
            "tool": path.stem.rsplit("_", 1)[0],
            "timestamp": data.get("timestamp", ""),
            "item_count": len(findings),
            "findings": findings[:200],
        })
    return reports


# ═══════════════════════════════════════════════════════════════════════════════
# HTML
# ═══════════════════════════════════════════════════════════════════════════════

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<title>AWS Reports Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{{font-family:system-ui;background:#0f1419;color:#e6e6e6;margin:2em}}
h1{{color:#58a6ff}} .card{{background:#1c2128;border-radius:8px;
padding:1em;margin:1em 0}}
canvas{{max-height:300px}} table{{border-collapse:collapse;width:100%}}
td,th{{border-bottom:1px solid #30363d;padding:6px 10px;text-align:left;
font-size:.9em}}
.sev-critical,.sev-fail{{color:#ff7b72}} .sev-high,.sev-warning,.sev-warn
{{color:#f2cc60}} .sev-info,.sev-low{{color:#79c0ff}}
.sev-pass,.sev-ok,.sev-healthy,.sev-match{{color:#56d364}}
</style></head><body>
<h1>☁️ AWS Reports Dashboard</h1>
<p>Generado: {generated} | Reportes: {n_reports} | Items: {n_items}</p>
<div class="card"><h2>Severidades</h2><canvas id="sevChart"></canvas></div>
<div class="card"><h2>Items por reporte</h2>
<canvas id="toolChart"></canvas></div>
<div class="card"><h2>Reportes cargados</h2><table>
<tr><th>Archivo</th><th>Tool</th><th>Fecha</th><th>Items</th></tr>
{report_rows}
</table></div>
<div class="card"><h2>Hallazgos destacados</h2><table>
<tr><th>Reporte</th><th>Severidad</th><th>Detalle</th></tr>
{finding_rows}
</table></div>
<script>
new Chart(document.getElementById('sevChart'),{{type:'doughnut',
data:{{labels:{sev_labels},datasets:[{{data:{sev_data},
backgroundColor:['#ff7b72','#f85149','#f2cc60','#d29922','#79c0ff',
'#56d364','#8b949e']}}]}} }});
new Chart(document.getElementById('toolChart'),{{type:'bar',
data:{{labels:{tool_labels},datasets:[{{label:'Items',data:{tool_data},
backgroundColor:'#58a6ff'}}]}} }});
</script></body></html>"""


def render_html(reports: List[Dict]) -> str:
    sev_counter: Counter = Counter()
    finding_rows = []
    for rep in reports:
        for item in rep["findings"]:
            sev = severity_of(item)
            sev_counter[sev] += 1
            detail = (item.get("message") or item.get("name")
                      or item.get("check") or str(item))[:100]
            if sev in ("critical", "fail", "high", "warning", "warn"):
                finding_rows.append(
                    f"<tr><td>{html.escape(rep['file'][:40])}</td>"
                    f"<td class='sev-{sev}'>{sev}</td>"
                    f"<td>{html.escape(str(detail))}</td></tr>")

    labels = list(sev_counter.keys()) or ["sin datos"]
    data_vals = [sev_counter[k] for k in sev_counter] or [0]
    report_rows = "".join(
        f"<tr><td>{html.escape(r['file'])}</td><td>{r['tool']}</td>"
        f"<td>{str(r['timestamp'])[:19]}</td>"
        f"<td>{r['item_count']}</td></tr>" for r in reports)

    return HTML_TEMPLATE.format(
        generated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        n_reports=len(reports),
        n_items=sum(r["item_count"] for r in reports),
        sev_labels=json.dumps(labels),
        sev_data=json.dumps(data_vals),
        tool_labels=json.dumps([r["tool"][:25] for r in reports]),
        tool_data=json.dumps([r["item_count"] for r in reports]),
        report_rows=report_rows,
        finding_rows="".join(finding_rows[:100]))


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Dashboard HTML de reportes JSON en outcome/")
    parser.add_argument("--input", "-i", default=str(OUTCOME_DIR),
                        help="Directorio con reportes JSON")
    parser.add_argument("--output", "-o", default="",
                        help="Archivo HTML de salida")
    return parser.parse_args()


def main():
    args = get_args()
    input_dir = Path(args.input)
    if not input_dir.is_dir():
        _print(f"[red]❌ Directorio no encontrado: {input_dir}[/red]")
        sys.exit(1)

    reports = scan_reports(input_dir)
    if not reports:
        _print(f"[yellow]⚠ Sin reportes JSON en {input_dir}[/yellow]")
        sys.exit(0)

    out = Path(args.output) if args.output else \
        OUTCOME_DIR / f"aws_reports_dashboard_" \
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(reports), encoding="utf-8")

    _print(f"[green]✓ Dashboard generado: {out}[/green]")
    _print(f"[dim]  {len(reports)} reportes, "
           f"{sum(r['item_count'] for r in reports)} items[/dim]")


if __name__ == "__main__":
    main()
