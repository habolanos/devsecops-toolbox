#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Event Tracker — Tool 24

Rastreo de eventos e interrupciones en Azure, equivalente a
event-tracker (GCP) / aws_cloudtrail_event_tracker:

- Activity Log: operaciones por usuario/recurso/acción
- Filtros: --component-name, --start-time/--end-time (o --hours)
- Clasificación por severidad: Write/Delete/Action =
  high, Read = low, ServiceHealth = critical
- Correlación por correlationId y recurso
- Export JSON/CSV/Markdown

Uso:
    python event_tracker.py --subscription <id> --hours 24
    python event_tracker.py --component-name myapp \\
        --output-format markdown
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, now_ts, export_json, export_csv)

__version__ = "1.0.0"


def severity_of(event: Dict) -> str:
    cat = (event.get("category") or {}).get("value", "")
    level = event.get("level", "")
    op_raw = event.get("operationName") or ""
    op = op_raw.get("localizedValue", "") \
        if isinstance(op_raw, dict) else op_raw
    if "ServiceHealth" in cat or level == "Critical":
        return "critical"
    if any(k in str(op).lower() for k in
           ("delete", "write", "action")):
        return "high"
    if level in ("Error", "Warning"):
        return "medium"
    return "low"


def collect(sub: str, hours: int, component: str,
            start: str, end: str) -> List[Dict]:
    if not start:
        start = (datetime.now(timezone.utc) -
                 timedelta(hours=hours)) \
            .strftime("%Y-%m-%dT%H:%M:%SZ")
    if not end:
        end = datetime.now(timezone.utc) \
            .strftime("%Y-%m-%dT%H:%M:%SZ")
    events = try_az(
        ["monitor", "activity-log", "list",
         "--start-time", start, "--end-time", end],
        sub, default=[]) or []
    out = []
    for e in events:
        res_name = (e.get("resourceId") or "") \
            .rsplit("/", 1)[-1]
        if component and component.lower() not in \
                res_name.lower() and \
                component.lower() not in \
                (e.get("resourceId") or "").lower():
            continue
        out.append({
            "time": str(e.get("eventTimestamp"))[:19],
            "operation": (e.get("operationName") or {})
            .get("localizedValue", "?") if isinstance(
                e.get("operationName"), dict)
            else (e.get("operationName") or "?"),
            "caller": e.get("caller"),
            "resource": res_name,
            "resource_type": (e.get("resourceType") or {})
            .get("value", "?") if isinstance(
                e.get("resourceType"), dict)
            else e.get("resourceType"),
            "level": e.get("level"),
            "status": (e.get("status") or {}).get("value")
            if isinstance(e.get("status"), dict)
            else e.get("status"),
            "correlation_id": e.get("correlationId"),
            "severity": severity_of(e),
        })
    return out


def summarize(events: List[Dict]) -> Dict:
    return {
        "total": len(events),
        "by_severity": dict(Counter(e["severity"]
                                    for e in events)),
        "by_caller": dict(Counter(e.get("caller") or "?"
                                  for e in events)
                          .most_common(10)),
        "by_operation": dict(Counter(e["operation"]
                                     for e in events)
                             .most_common(10)),
        "failed": len([e for e in events
                       if e.get("status") == "Failed"]),
    }


def get_args():
    p = argparse.ArgumentParser(
        description="Rastreo de eventos Azure (Activity Log)")
    p.add_argument("--subscription", default="")
    p.add_argument("--component-name", default="")
    p.add_argument("--hours", type=int, default=24)
    p.add_argument("--start-time", default="")
    p.add_argument("--end-time", default="")
    p.add_argument("--output-format",
                   choices=["json", "csv", "markdown", "table"],
                   default="table")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    events = collect(sub, args.hours, args.component_name,
                     args.start_time, args.end_time)
    summary = summarize(events)

    if console:
        from rich.table import Table
        t = Table(title=f"Activity Log ({args.hours}h)",
                  header_style="bold cyan")
        for col in ["Hora", "Operación", "Caller", "Recurso",
                    "Sev"]:
            t.add_column(col)
        style = {"critical": "red bold", "high": "red",
                 "medium": "yellow", "low": "dim"}
        for e in sorted(events, key=lambda x: x["time"],
                        reverse=True)[:40]:
            t.add_row(
                e["time"], e["operation"][:30],
                str(e.get("caller") or "?")[:25],
                e["resource"][:25],
                f"[{style[e['severity']]}]{e['severity']}"
                f"[/{style[e['severity']]}]")
        console.print(t)
        console.print(f"[dim]{summary}[/dim]")
    else:
        for e in events[:50]:
            print(f"[{e['severity']}] {e['time']} "
                  f"{e['operation']} {e['resource']}")

    _print(f"\nEventos: {summary['total']} | "
           f"fallidos: {summary['failed']}",
           "red" if summary["failed"] else "green")

    if args.output_format != "table":
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"azure_events_{now_ts()}." \
                            f"{args.output_format}"
        if args.output_format == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "summary": summary, "events": events})
        elif args.output_format == "csv":
            export_csv(out, ["time", "operation", "caller",
                             "resource", "status", "severity"],
                       events)
        else:  # markdown
            lines = [f"# Azure Event Report — {sub}",
                     f"Generado: {datetime.now()}",
                     f"Eventos: {summary['total']} | "
                     f"Fallidos: {summary['failed']}", "",
                     "| Hora | Operación | Caller | Recurso | "
                     "Sev |", "|---|---|---|---|---|"]
            for e in events[:200]:
                lines.append(
                    f"| {e['time']} | {e['operation']} | "
                    f"{e.get('caller') or '?'} | "
                    f"{e['resource']} | {e['severity']} |")
            out.write_text("\n".join(lines),
                           encoding="utf-8")
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
