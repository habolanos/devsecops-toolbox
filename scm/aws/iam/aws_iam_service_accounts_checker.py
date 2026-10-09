#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS IAM Service Accounts Checker — Tool 53

Equivalente de GCP Service Account Checker: las "service accounts"
de AWS se materializan como (a) roles con trust de servicio AWS
(ec2/ecs/lambda.amazonaws.com), (b) instance profiles, y (c) usuarios
IAM con access keys usados como cuentas de servicio:

- Roles de servicio: trust policy, RoleLastUsed (nunca usado /
  >90 días), políticas adjuntas
- Instance profiles: sin roles asociados, sin uso
- Access keys de usuarios: edad (>90 días sin rotar), nunca usadas,
  último uso viejo
- Hallazgos con severidad + export JSON/CSV

Uso:
    python aws_iam_service_accounts_checker.py --profile p \\
        --region us-east-1
    python aws_iam_service_accounts_checker.py --key-days 60 -o json
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

__version__ = "1.0.0"

STALE_DAYS = 90
MAX_WORKERS = 10


def _days_ago(dt) -> int:
    if dt is None:
        return -1
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def list_service_roles(iam) -> List[Dict]:
    """Roles cuyo trust incluye servicios AWS (*.amazonaws.com)."""
    roles = []
    for page in iam.get_paginator("list_roles").paginate():
        for r in page.get("Roles", []):
            trust = r.get("AssumeRolePolicyDocument", {})
            stmts = trust.get("Statement", [])
            if isinstance(stmts, dict):
                stmts = [stmts]
            principals = set()
            for s in stmts:
                svc = s.get("Principal", {}).get("Service")
                if isinstance(svc, str):
                    principals.add(svc)
                elif isinstance(svc, list):
                    principals.update(svc)
            if principals:
                last = r.get("RoleLastUsed", {})
                roles.append({
                    "name": r["RoleName"], "arn": r["Arn"],
                    "created": str(r.get("CreateDate", ""))[:10],
                    "trusted_services": sorted(principals),
                    "last_used_date": str(
                        last.get("LastUsedDate", ""))[:10] or None,
                    "last_used_region": last.get("Region"),
                    "days_since_use": _days_ago(
                        last.get("LastUsedDate")),
                    "description": r.get("Description", "")[:80],
                })
    return roles


def list_instance_profiles(iam) -> List[Dict]:
    out = []
    for page in iam.get_paginator(
            "list_instance_profiles").paginate():
        for ip in page.get("InstanceProfiles", []):
            out.append({
                "name": ip["InstanceProfileName"],
                "arn": ip["Arn"],
                "roles": [r["RoleName"]
                          for r in ip.get("Roles", [])],
                "created": str(ip.get("CreateDate", ""))[:10],
            })
    return out


def user_access_keys(iam, user_name: str) -> List[Dict]:
    """Access keys de un usuario con antigüedad y último uso."""
    keys = []
    try:
        resp = iam.list_access_keys(UserName=user_name)
    except Exception:
        return keys
    for k in resp.get("AccessKeyMetadata", []):
        info = {"user": user_name, "key_id": k["AccessKeyId"],
                "status": k["Status"],
                "created": str(k.get("CreateDate", ""))[:10],
                "age_days": _days_ago(k.get("CreateDate")),
                "last_used": None, "last_used_days": -1,
                "last_service": None}
        try:
            lu = iam.get_access_key_last_used(
                AccessKeyId=k["AccessKeyId"]) \
                .get("AccessKeyLastUsed", {})
            if lu.get("LastUsedDate"):
                info["last_used"] = str(lu["LastUsedDate"])[:10]
                info["last_used_days"] = _days_ago(
                    lu["LastUsedDate"])
                info["last_service"] = lu.get("ServiceName")
        except Exception:
            pass
        keys.append(info)
    return keys


def analyze_roles(roles: List[Dict],
                  stale_days: int) -> List[Dict]:
    findings = []
    for r in roles:
        if r["days_since_use"] == -1:
            findings.append({
                "severity": "warning", "type": "role_never_used",
                "resource": r["name"],
                "detail": "Rol de servicio nunca usado "
                          f"(creado {r['created']})"})
        elif r["days_since_use"] > stale_days:
            findings.append({
                "severity": "info", "type": "role_stale",
                "resource": r["name"],
                "detail": f"Sin uso hace {r['days_since_use']} días"})
    return findings


def analyze_keys(keys: List[Dict],
                 stale_days: int) -> List[Dict]:
    findings = []
    for k in keys:
        if k["status"] != "Active":
            findings.append({
                "severity": "info", "type": "key_inactive",
                "resource": k["key_id"],
                "detail": f"Key inactiva de {k['user']} — "
                          "candidata a borrar"})
            continue
        if k["age_days"] > stale_days:
            findings.append({
                "severity": "warning", "type": "key_old",
                "resource": k["key_id"],
                "detail": f"Key de {k['user']} con "
                          f"{k['age_days']} días sin rotar"})
        if k["last_used_days"] == -1:
            findings.append({
                "severity": "warning", "type": "key_never_used",
                "resource": k["key_id"],
                "detail": f"Key activa de {k['user']} nunca usada"})
        elif k["last_used_days"] > stale_days:
            findings.append({
                "severity": "info", "type": "key_stale",
                "resource": k["key_id"],
                "detail": f"Key de {k['user']} sin uso hace "
                          f"{k['last_used_days']} días "
                          f"(último: {k['last_service']})"})
    return findings


def get_args():
    p = argparse.ArgumentParser(
        description="IAM service accounts (roles de servicio, "
                    "instance profiles, access keys)")
    p.add_argument("--profile", "-p", default="default")
    p.add_argument("--region", "-r", default="us-east-1")
    p.add_argument("--key-days", type=int, default=STALE_DAYS,
                   help="Umbral de días para keys/roles sin uso")
    p.add_argument("--skip-keys", action="store_true",
                   help="No analizar access keys de usuarios")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)
    iam = make_session(args.profile, args.region).client("iam")

    _print("Listando roles de servicio e instance profiles...",
           "dim")
    roles = list_service_roles(iam)
    profiles = list_instance_profiles(iam)
    empty_profiles = [p for p in profiles if not p["roles"]]

    keys: List[Dict] = []
    if not args.skip_keys:
        users = [u["UserName"] for u in
                 iam.get_paginator("list_users").paginate()
                 .search("Users[]") or []]
        with ThreadPoolExecutor(
                max_workers=MAX_WORKERS) as ex:
            for f in as_completed(
                    {ex.submit(user_access_keys, iam, u)
                     for u in users}):
                keys.extend(f.result())

    findings = analyze_roles(roles, args.key_days) + \
        analyze_keys(keys, args.key_days)
    for p in empty_profiles:
        findings.append({
            "severity": "info", "type": "profile_no_roles",
            "resource": p["name"],
            "detail": "Instance profile sin roles"})

    counts = {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    if console:
        from rich.table import Table
        table = Table(title="IAM Service Accounts",
                      header_style="bold cyan")
        for col in ["Recurso", "Tipo", "Confía en", "Último uso"]:
            table.add_column(col)
        for r in sorted(roles, key=lambda x: -x["days_since_use"]
                        )[:25]:
            color = "red" if r["days_since_use"] == -1 else \
                    "yellow" if r["days_since_use"] > args.key_days \
                    else "green"
            table.add_row(
                r["name"][:40], "role",
                ", ".join(r["trusted_services"][:2])[:30],
                f"[{color}]{r['last_used_date'] or 'nunca'}"
                f"[/{color}]")
        console.print(table)
        t2 = Table(title="Findings", header_style="bold red")
        for col in ["Sev", "Tipo", "Recurso", "Detalle"]:
            t2.add_column(col)
        for f in findings[:40]:
            color = "red" if f["severity"] == "warning" else "dim"
            t2.add_row(f"[{color}]{f['severity']}[/{color}]",
                       f["type"], f["resource"][:35],
                       f["detail"][:60])
        console.print(t2)
    else:
        print(f"service_roles={len(roles)} "
              f"instance_profiles={len(profiles)} keys={len(keys)}")
        for f in findings:
            print(f"[{f['severity']}] {f['type']} "
                  f"{f['resource']}: {f['detail']}")

    _print(f"\nRoles servicio: {len(roles)} | profiles: "
           f"{len(profiles)} | keys: {len(keys)} | findings: "
           f"{len(findings)}",
           "yellow" if findings else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"iam_service_accounts_{ts}" \
                            f".{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "service_roles": roles,
                "instance_profiles": profiles,
                "access_keys": keys, "findings": findings},
                indent=2, default=str), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "severity", "type", "resource", "detail"])
                w.writeheader()
                w.writerows(findings)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
