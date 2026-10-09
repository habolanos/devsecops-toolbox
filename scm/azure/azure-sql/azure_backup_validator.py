#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Database Backup Validator — Tool 8

Valida la configuración de backups/retención de bases de datos Azure:

- Azure SQL: retención PITR (short-term) y políticas LTR por DB
- Cosmos DB: tipo de backup y retención
- Hallazgos: retención mínima (<7 días), sin LTR, backup
  deshabilitado

Uso:
    python azure_backup_validator.py --subscription <id>
    python azure_backup_validator.py -o json
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, rg_of, now_ts, export_json, export_csv)

__version__ = "1.0.0"

MIN_PITR_DAYS = 7


def validate_sql_dbs(sub: str) -> List[Dict]:
    out = []
    servers = try_az(["sql", "server", "list"], sub,
                     default=[]) or []
    for s in servers:
        rg = rg_of(s)
        dbs = try_az(["sql", "db", "list", "--server",
                      s["name"], "--resource-group", rg],
                     sub, default=[]) or []
        for d in dbs:
            if d["name"] == "master":
                continue
            findings = []
            # PITR
            st = try_az(["sql", "db", "str-policy", "show",
                         "--name", d["name"], "--server",
                         s["name"], "--resource-group", rg],
                        sub, default=None)
            pitr_days = (st or {}).get("retentionDays")
            if pitr_days is None:
                findings.append("🟡 Sin política PITR visible")
            elif pitr_days < MIN_PITR_DAYS:
                findings.append(f"🔴 PITR {pitr_days}d < "
                                f"{MIN_PITR_DAYS}d")
            # LTR
            ltr = try_az(["sql", "db", "ltr-policy", "show",
                          "--name", d["name"], "--server",
                          s["name"], "--resource-group", rg],
                         sub, default=None)
            if not ltr or not ltr.get("weeklyRetention"):
                findings.append("🟡 Sin LTR semanal")
            out.append({
                "type": "sql", "resource": f"{s['name']}/"
                                           f"{d['name']}",
                "pitr_days": pitr_days,
                "ltr_weekly": (ltr or {}).get(
                    "weeklyRetention"),
                "findings": findings,
            })
    return out


def validate_cosmos(sub: str) -> List[Dict]:
    out = []
    for a in (try_az(["cosmosdb", "list"], sub, default=[])
              or []):
        findings = []
        backup = a.get("backupPolicy", {})
        btype = backup.get("type", "?")
        if btype == "Periodic":
            interval = (backup.get("periodicModeProperties")
                        or {}).get("backupIntervalInMinutes")
            retention = (backup.get("periodicModeProperties")
                         or {}).get("backupRetentionIntervalInHours")
            if retention and retention < 24:
                findings.append(f"🟡 Retención backup "
                                f"{retention}h <24h")
            if interval and interval > 1440:
                findings.append(f"🟡 Intervalo backup "
                                f"{interval}min >24h")
        elif btype not in ("Continuous", "Periodic"):
            findings.append("🟡 Tipo de backup "
                            f"desconocido: {btype}")
        out.append({
            "type": "cosmos", "resource": a["name"],
            "backup_type": btype, "findings": findings,
        })
    return out


def get_args():
    p = argparse.ArgumentParser(
        description="Valida backups/retención de bases Azure")
    p.add_argument("--subscription", default="")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    results = validate_sql_dbs(sub) + validate_cosmos(sub)
    issues = [r for r in results
              if any("🔴" in f for f in r["findings"])]

    if console:
        from rich.table import Table
        table = Table(title="Backup Validation",
                      header_style="bold cyan")
        for col in ["Tipo", "Recurso", "PITR", "LTR/Type",
                    "Findings"]:
            table.add_column(col)
        for r in results:
            bad = any("🔴" in f for f in r["findings"])
            table.add_row(
                r["type"], r["resource"][:40],
                str(r.get("pitr_days", "-")),
                str(r.get("ltr_weekly") or r.get("backup_type",
                                                 "-"))[:15],
                f"[{'red' if bad else 'green'}]"
                f"{len(r['findings'])}"
                f"[/{'red' if bad else 'green'}]")
        console.print(table)
        for r in results:
            for f in r["findings"]:
                console.print(f"  {f} [dim]({r['resource']})"
                              f"[/dim]")
    else:
        for r in results:
            print(f"{r['resource']}: {r['findings']}")

    _print(f"\nRecursos: {len(results)} | con issues: "
           f"{len(issues)}",
           "red" if issues else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"backup_validation_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "resources": results})
        else:
            rows = [{k: r.get(k, "") for k in
                     ("type", "resource", "pitr_days",
                      "backup_type")}
                    | {"findings": "; ".join(r["findings"])}
                    for r in results]
            export_csv(out, list(rows[0]) if rows else
                       ["resource"], rows)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
