#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS IAM Multi-Account Reporter — Tool 54

Equivalente de GCP Service Accounts Multi-Project Reporter: recorre
varios perfiles AWS (≈ cuentas/proyectos) y consolida la postura IAM:

- Por perfil: usuarios, roles, políticas, % MFA, access keys,
  account alias / ID
- Matriz comparativa de postura entre cuentas
- Errores de acceso por perfil (expired token, sin permisos)
- Ejecución paralela con ThreadPoolExecutor
- Export JSON/CSV

Uso:
    python aws_iam_multi_account_reporter.py --profiles p1,p2
    python aws_iam_multi_account_reporter.py --profiles ALL
    python aws_iam_multi_account_reporter.py --profiles ALL -o json
"""

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent / "ecs"))
from aws_ecs_common import (  # noqa: E402
    BOTO3_AVAILABLE, OUTCOME_DIR, console, _print, make_session)

if BOTO3_AVAILABLE:
    import boto3

__version__ = "1.0.0"

MAX_WORKERS = 10


def available_profiles() -> List[str]:
    """Perfiles AWS configurados (boto3 session store)."""
    try:
        return sorted(boto3.Session().available_profiles)
    except Exception:
        return ["default"]


def _count(iam, op: str, key: str) -> int:
    try:
        total = 0
        for page in iam.get_paginator(op).paginate():
            total += len(page.get(key, []))
        return total
    except Exception:
        return -1


def account_summary(profile: str, region: str) -> Dict:
    """Postura IAM de una cuenta (profile)."""
    out = {"profile": profile, "account": None,
           "users": -1, "roles": -1, "policies": -1,
           "groups": -1, "mfa_pct": None,
           "access_keys": -1, "error": None}
    try:
        session = make_session(profile, region)
        iam = session.client("iam")
        sts = session.client("sts")
        try:
            out["account"] = sts.get_caller_identity()["Account"]
        except Exception:
            pass
        try:
            aliases = iam.list_account_aliases() \
                .get("AccountAliases", [])
            if aliases:
                out["alias"] = aliases[0]
        except Exception:
            pass

        out["users"] = _count(iam, "list_users", "Users")
        out["roles"] = _count(iam, "list_roles", "Roles")
        out["policies"] = _count(iam, "list_policies",
                                 "Policies")
        out["groups"] = _count(iam, "list_groups", "Groups")

        # MFA coverage + access keys (solo si hay pocos usuarios)
        users = []
        try:
            for page in iam.get_paginator("list_users").paginate():
                users.extend(page.get("Users", []))
        except Exception:
            pass
        if users and len(users) <= 200:
            mfa_ok = 0
            keys_total = 0
            for u in users:
                try:
                    if iam.list_mfa_devices(
                            UserName=u["UserName"]) \
                            .get("MFADevices"):
                        mfa_ok += 1
                    keys_total += len(iam.list_access_keys(
                        UserName=u["UserName"])
                        .get("AccessKeyMetadata", []))
                except Exception:
                    pass
            out["mfa_pct"] = round(100 * mfa_ok / len(users), 1)
            out["access_keys"] = keys_total
    except Exception as e:
        out["error"] = str(e)[:120]
    return out


def get_args():
    p = argparse.ArgumentParser(
        description="IAM multi-account reporter (por profiles)")
    p.add_argument("--profiles", default="ALL",
                   help="Profiles separados por coma o ALL")
    p.add_argument("--region", "-r", default="us-east-1")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)

    if args.profiles.strip().lower() in ("", "all"):
        profiles = available_profiles()
    else:
        profiles = [p.strip() for p in args.profiles.split(",")
                    if p.strip()]

    _print(f"Analizando {len(profiles)} perfiles...", "dim")
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(account_summary, p, args.region):
                   p for p in profiles}
        for f in as_completed(futures):
            results.append(f.result())
    results.sort(key=lambda r: r["profile"])

    errors = [r for r in results if r["error"]]

    if console:
        from rich.table import Table
        table = Table(title="IAM Multi-Account Report",
                      header_style="bold cyan")
        for col in ["Perfil", "Cuenta", "Users", "Roles",
                    "MFA%", "Keys"]:
            table.add_column(col)
        for r in results:
            if r["error"]:
                table.add_row(r["profile"], "[red]ERROR[/red]",
                              "-", "-", "-", "-")
                continue
            mfa = r["mfa_pct"]
            color = "green" if mfa is not None and mfa >= 80 \
                else "yellow" if mfa is not None and mfa >= 50 \
                else "red"
            table.add_row(
                r["profile"], r.get("account") or "-",
                str(r["users"]), str(r["roles"]),
                f"[{color}]{mfa}%[/{color}]"
                if mfa is not None else "-",
                str(r["access_keys"]) if r["access_keys"] >= 0
                else "-")
        console.print(table)
        for r in errors:
            console.print(f"  [red]✗ {r['profile']}:[/red] "
                          f"[dim]{r['error']}[/dim]")
    else:
        for r in results:
            print(f"{r['profile']}: account={r.get('account')} "
                  f"users={r['users']} roles={r['roles']} "
                  f"mfa={r['mfa_pct']} err={r['error']}")

    _print(f"\nPerfiles: {len(results)} | con error: "
           f"{len(errors)}",
           "yellow" if errors else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"iam_multi_account_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "accounts": results}, indent=2, default=str),
                encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "profile", "account", "users", "roles",
                    "policies", "groups", "mfa_pct",
                    "access_keys", "error"])
                w.writeheader()
                w.writerows(
                    [{k: r.get(k) for k in w.fieldnames}
                     for r in results])
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
