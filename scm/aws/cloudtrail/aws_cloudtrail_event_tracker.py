#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS CloudTrail Event Tracker — Tool 42

Rastreo de eventos de un componente/recurso AWS vía CloudTrail +
CloudWatch Logs, equivalente al Event Tracker de GCP:

- LookupEvents de CloudTrail filtrando por usuario, recurso,
  evento o ventana de tiempo
- Normalización de eventos (timestamp, actor, acción, recurso, IP)
- Clasificación de severidad: eventos de escritura/seguridad/errores
- Correlación básica por usuario + ventana
- Reporte JSON/CSV/HTML en outcome/

Uso:
    python aws_cloudtrail_event_tracker.py --profile p --region us-east-1
    python aws_cloudtrail_event_tracker.py --resource-name my-db \\
        --hours 48 -o html
    python aws_cloudtrail_event_tracker.py --username deploy-role \\
        --event-name Delete
"""

import argparse
import csv
import html as html_mod
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
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
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "DevSecOps Team"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None

# Acciones que elevan severidad del evento
DESTRUCTIVE_PREFIXES = ("Delete", "Terminate", "Stop", "Disable",
                        "Remove", "Revoke", "Put", "Update",
                        "Modify", "Create", "Attach", "Detach")
SECURITY_SERVICES = {"iam.amazonaws.com", "sts.amazonaws.com",
                     "kms.amazonaws.com", "secretsmanager.amazonaws.com"}
ERROR_PREFIXES = ("AccessDenied", "UnauthorizedOperation",
                  "Client.", "Error")


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Eventos
# ═══════════════════════════════════════════════════════════════════════════════

def classify_severity(event: Dict) -> str:
    """critical/warning/info según acción, servicio y errores."""
    name = event.get("event_name", "")
    if event.get("error"):
        return "critical"
    src = event.get("event_source", "")
    if name.startswith(ERROR_PREFIXES):
        return "critical"
    if src in SECURITY_SERVICES:
        return "warning"
    if name.startswith(DESTRUCTIVE_PREFIXES):
        return "warning"
    return "info"


def normalize_event(raw: Dict) -> Dict:
    """Normaliza un CloudTrail LookupEvent a campos planos."""
    detail = {}
    try:
        detail = json.loads(raw.get("CloudTrailEvent", "{}"))
    except (json.JSONDecodeError, TypeError):
        pass
    resources = ", ".join(
        f"{r.get('ResourceType', '')}:{r.get('ResourceName', '')}"
        for r in raw.get("Resources", []))
    event = {
        "timestamp": str(raw.get("EventTime", "")),
        "event_name": raw.get("EventName", ""),
        "event_source": raw.get("EventSource", ""),
        "username": raw.get("Username", ""),
        "resources": resources,
        "source_ip": detail.get("sourceIPAddress", ""),
        "user_agent": (detail.get("userAgent") or "")[:60],
        "error": detail.get("errorCode", ""),
        "region": detail.get("awsRegion", ""),
        "read_only": detail.get("readOnly", True),
    }
    event["severity"] = classify_severity(event)
    return event


def lookup_events(client, start: datetime, end: datetime,
                  username: str = "", resource_name: str = "",
                  event_name: str = "", max_events: int = 200
                  ) -> List[Dict]:
    """LookupEvents con filtros AttributeKey opcionales."""
    attrs = []
    if username:
        attrs.append({"AttributeKey": "Username",
                      "AttributeValue": username})
    if resource_name:
        attrs.append({"AttributeKey": "ResourceName",
                      "AttributeValue": resource_name})
    if event_name:
        attrs.append({"AttributeKey": "EventName",
                      "AttributeValue": event_name})

    events, token = [], None
    kwargs = {"StartTime": start, "EndTime": end, "MaxResults": 50}
    if attrs:
        kwargs["LookupAttributes"] = attrs
    while len(events) < max_events:
        if token:
            kwargs["NextToken"] = token
        try:
            resp = client.lookup_events(**kwargs)
        except ClientError as e:
            _print(f"⚠ lookup_events: {e}", "yellow")
            break
        for raw in resp.get("Events", []):
            events.append(normalize_event(raw))
            if len(events) >= max_events:
                break
        token = resp.get("NextToken")
        if not token:
            break
    return events


def correlate(events: List[Dict]) -> Dict[str, List[Dict]]:
    """Agrupa por username para vista de actividad por actor."""
    by_user: Dict[str, List[Dict]] = {}
    for e in events:
        by_user.setdefault(e["username"] or "unknown", []).append(e)
    return by_user


# ═══════════════════════════════════════════════════════════════════════════════
# Reportes
# ═══════════════════════════════════════════════════════════════════════════════

def export_json(events: List[Dict], meta: Dict, path: Path):
    path.write_text(json.dumps({
        **meta, "count": len(events), "events": events},
        indent=2, default=str), encoding="utf-8")


def export_csv(events: List[Dict], path: Path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "timestamp", "severity", "event_name", "event_source",
            "username", "resources", "source_ip", "error"])
        w.writeheader()
        for e in events:
            w.writerow({k: e.get(k, "") for k in w.fieldnames})


HTML = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>AWS Event Tracker</title>
<style>body{{font-family:system-ui;background:#0f1419;color:#e6e6e6;
margin:2em}}h1{{color:#58a6ff}}table{{border-collapse:collapse;
width:100%}}td,th{{border-bottom:1px solid #30363d;padding:6px;
text-align:left;font-size:.85em}}
.critical{{color:#ff7b72}}.warning{{color:#f2cc60}}
.info{{color:#79c0ff}}</style></head><body>
<h1>🔍 AWS CloudTrail Event Tracker</h1>
<p>Generado: {ts} | Eventos: {count} | Ventana: {window}</p>
<table><tr><th>Timestamp</th><th>Sev</th><th>Evento</th>
<th>Servicio</th><th>Usuario</th><th>Recursos</th><th>IP</th>
<th>Error</th></tr>
{rows}
</table></body></html>"""


def export_html(events: List[Dict], meta: Dict, path: Path):
    rows = "".join(
        f"<tr><td>{html_mod.escape(e['timestamp'][:19])}</td>"
        f"<td class='{e['severity']}'>{e['severity']}</td>"
        f"<td>{html_mod.escape(e['event_name'])}</td>"
        f"<td>{html_mod.escape(e['event_source'])}</td>"
        f"<td>{html_mod.escape(e['username'])}</td>"
        f"<td>{html_mod.escape(e['resources'][:50])}</td>"
        f"<td>{html_mod.escape(e['source_ip'])}</td>"
        f"<td>{html_mod.escape(e['error'])}</td></tr>"
        for e in events[:500])
    path.write_text(HTML.format(
        ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
        count=len(events), window=meta.get("window", ""),
        rows=rows), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Rastreo de eventos CloudTrail de un componente AWS")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--username", "-u", default="",
                        help="Filtrar por usuario/rol IAM")
    parser.add_argument("--resource-name", "-R", default="",
                        help="Filtrar por nombre de recurso")
    parser.add_argument("--event-name", "-e", default="",
                        help="Filtrar por nombre de evento")
    parser.add_argument("--hours", type=int, default=24,
                        help="Ventana hacia atrás en horas")
    parser.add_argument("--start-time", default="",
                        help="ISO 8601 (anula --hours)")
    parser.add_argument("--end-time", default="")
    parser.add_argument("--max-events", type=int, default=200)
    parser.add_argument("-o", "--output",
                        choices=["json", "csv", "html"], default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)

    end = datetime.now(timezone.utc)
    if args.start_time:
        start = datetime.fromisoformat(
            args.start_time.replace("Z", "+00:00"))
    else:
        start = end - timedelta(hours=args.hours)
    if args.end_time:
        end = datetime.fromisoformat(
            args.end_time.replace("Z", "+00:00"))

    try:
        session = boto3.Session(profile_name=args.profile,
                                region_name=args.region)
        client = session.client("cloudtrail")
    except Exception as e:
        _print(f"❌ Error de sesión AWS: {e}", "red")
        sys.exit(1)

    events = lookup_events(
        client, start, end, username=args.username,
        resource_name=args.resource_name,
        event_name=args.event_name, max_events=args.max_events)

    sev_count = Counter(e["severity"] for e in events)

    if console:
        console.print(Panel.fit(
            f"Ventana: {start:%Y-%m-%d %H:%M} → {end:%Y-%m-%d %H:%M} UTC\n"
            f"Eventos: [bold]{len(events)}[/bold] | "
            f"🔴 {sev_count.get('critical', 0)} "
            f"🟡 {sev_count.get('warning', 0)} "
            f"🔵 {sev_count.get('info', 0)}",
            title="🔍 Event Tracker"))
        if events:
            table = Table(header_style="bold cyan")
            for col in ["Timestamp", "Sev", "Evento", "Usuario",
                        "IP"]:
                table.add_column(col)
            for e in events[:40]:
                color = {"critical": "red", "warning": "yellow"}.get(
                    e["severity"], "dim")
                table.add_row(e["timestamp"][:19],
                              f"[{color}]{e['severity'][:4]}[/{color}]",
                              e["event_name"], e["username"][:25],
                              e["source_ip"])
            console.print(table)
            # Actividad por actor
            by_user = correlate(events)
            top = sorted(by_user.items(),
                         key=lambda kv: -len(kv[1]))[:5]
            console.print("[dim]Top actores: " + ", ".join(
                f"{u}({len(ev)})" for u, ev in top) + "[/dim]")
    else:
        for e in events:
            print(f"{e['timestamp'][:19]} [{e['severity']}] "
                  f"{e['event_name']} {e['username']} {e['error']}")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"event_tracker_{ts}.{args.output}"
        meta = {"timestamp": datetime.now().isoformat(),
                "window": f"{start.isoformat()} → {end.isoformat()}",
                "filters": {"username": args.username,
                            "resource_name": args.resource_name,
                            "event_name": args.event_name}}
        {"json": lambda: export_json(events, meta, out),
         "csv": lambda: export_csv(events, out),
         "html": lambda: export_html(events, meta, out)}[args.output]()
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
