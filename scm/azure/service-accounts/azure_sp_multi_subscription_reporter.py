#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure SP Multi-Subscription Reporter — Tool 36

Equivalente de gcp_sa_multi_project_reporter /
aws_iam_multi_account_reporter: consolida service principals y
postura RBAC a través de todas las suscripciones accesibles:

- Suscripciones: `az account list` (o las dadas con --subs)
- Por suscripción: # SPs, credenciales vencidas, Owners/
  Contributors, asignaciones totales
- Ejecución paralela (cada sub en su propio `az` con
  --subscription)
- Export JSON/CSV

Uso:
    python azure_sp_multi_subscription_reporter.py
    python azure_sp_multi_subscription_reporter.py \\
        --subs sub1,sub2 -o json
    python azure_sp_multi_subscription_reporter.py \\
        --config scm/config.json
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, now_ts, export_json, export_csv)

__version__ = "1.0.0"

MAX_WORKERS = 8


def _days_to(iso: str) -> int:
    if not iso:
        return 9999
    try:
        dt = datetime.fromisoformat(
            iso.replace("Z", "+00:00"))
        return (dt - datetime.now(timezone.utc)).days
    except Exception:
        return 9999


def list_subscriptions(config_path: str = "") -> List[Dict]:
    """Suscripciones activas: --subs > config.json > az."""
    subs = try_az(["account", "list",
                   "--query",
                   "[?state=='Enabled'].{id:id,name:name}"],
                  default=[]) or []
    return subs


def subscription_summary(sub: Dict) -> Dict:
    sid = sub["id"] if isinstance(sub, dict) else sub
    name = sub.get("name", "") if isinstance(sub, dict) else ""
    out = {"subscription": sid, "name": name,
           "sps": -1, "expired_creds": 0,
           "expiring_30d": 0, "owners": -1,
           "assignments": -1, "error": None}
    try:
        sps = try_az(["ad", "sp", "list", "--all"], sid,
                     default=[]) or []
        out["sps"] = len(sps)
        for sp in sps:
            creds = list(sp.get("passwordCredentials") or []) \
                + list(sp.get("keyCredentials") or [])
            for c in creds:
                d = _days_to(c.get("endDateTime") or
                             c.get("endDate"))
                if d < 0:
                    out["expired_creds"] += 1
                elif d <= 30:
                    out["expiring_30d"] += 1
        assigns = try_az(["role", "assignment", "list",
                          "--all"], sid, default=[]) or []
        out["assignments"] = len(assigns)
        out["owners"] = len([a for a in assigns
                             if a.get("roleDefinitionName")
                             == "Owner"])
    except Exception as e:
        out["error"] = str(e)[:120]
    return out


def get_args():
    p = argparse.ArgumentParser(
        description="Reporter multi-suscripción de service "
                    "principals")
    p.add_argument("--subs", default="",
                   help="IDs separados por coma (vacío=todas)")
    p.add_argument("--config", default="",
                   help="config.json (comp. con launcher)")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)

    if args.subs:
        subs = [{"id": s.strip(), "name": s.strip()}
                for s in args.subs.split(",") if s.strip()]
    else:
        subs = list_subscriptions()
    _print(f"Analizando {len(subs)} suscripciones...", "dim")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(subscription_summary, s): s
                   for s in subs}
        for f in as_completed(futures):
            results.append(f.result())
    results.sort(key=lambda r: r.get("name", ""))

    errors = [r for r in results if r["error"]]
    with_expired = [r for r in results
                    if r["expired_creds"] > 0]

    if console:
        from rich.table import Table
        table = Table(title="SP Multi-Subscription Report",
                      header_style="bold cyan")
        for col in ["Suscripción", "SPs", "Creds vencidas",
                    "Vencen ≤30d", "Owners", "Asignaciones"]:
            table.add_column(col)
        for r in results:
            if r["error"]:
                table.add_row(r["name"] or r["subscription"],
                              "[red]ERROR[/red]", "", "", "",
                              r["error"][:25])
                continue
            color = "red" if r["expired_creds"] else \
                "yellow" if r["expiring_30d"] else "green"
            table.add_row(
                (r["name"] or r["subscription"])[:35],
                str(r["sps"]),
                f"[{color}]{r['expired_creds']}[/{color}]",
                str(r["expiring_30d"]),
                str(r["owners"]),
                str(r["assignments"]))
        console.print(table)
        for r in errors:
            console.print(f"  [red]✗ {r['name']}:[/red] "
                          f"[dim]{r['error']}[/dim]")
    else:
        for r in results:
            print(f"{r['name']}: sps={r['sps']} "
                  f"expired={r['expired_creds']} "
                  f"owners={r['owners']} err={r['error']}")

    _print(f"\nSuscripciones: {len(results)} | con creds "
           f"vencidas: {len(with_expired)} | errores: "
           f"{len(errors)}",
           "red" if with_expired else
           ("yellow" if errors else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"sp_multi_sub_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "subscriptions": results})
        else:
            export_csv(out, ["subscription", "name", "sps",
                             "expired_creds", "expiring_30d",
                             "owners", "assignments",
                             "error"], results)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
