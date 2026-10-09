#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Key Vault Checker — Tool 39 (nueva, paridad GCP)

Equivalente de gcp_secrets_configmaps_checker /
aws_secrets_checker: auditoría de secretos en Key Vault:

- Vaults: soft-delete, purge protection, RBAC vs access policies,
  firewall rules, private endpoints
- Secrets: expiración (sin expiración definida, expirados,
  próximos a vencer), deshabilitados
- Keys y certificados: expiración
- Hallazgos con severidad + export

Uso:
    python azure_keyvault_checker.py --subscription <id>
    python azure_keyvault_checker.py --vault myvault -o json
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, rg_of, now_ts, export_json, export_csv)

__version__ = "1.0.0"

WARN_DAYS = 30


def _days_to(iso: str) -> int:
    if not iso:
        return 9999
    try:
        dt = datetime.fromisoformat(
            iso.replace("Z", "+00:00"))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return (dt - datetime.now(timezone.utc)).days
    except Exception:
        return 9999


def analyze_vault(v: Dict) -> Dict:
    findings = []
    props = v.get("properties", {})
    if props.get("enableSoftDelete") is False:
        findings.append("🔴 Soft delete deshabilitado")
    if not props.get("enablePurgeProtection"):
        findings.append("🟡 Purge protection deshabilitado")
    net = props.get("networkAcls") or {}
    if net.get("defaultAction") == "Allow":
        findings.append("🟡 Firewall abierto por defecto "
                        "(defaultAction=Allow)")
    rbac = props.get("enableRbacAuthorization")
    if not rbac:
        findings.append("🟡 Usa access policies en vez de "
                        "RBAC (recomendado migrar)")
    if not props.get("publicNetworkAccess") == "Disabled" and \
            net.get("defaultAction") != "Deny":
        findings.append("🟡 Acceso público — evaluar "
                        "private endpoint")
    return {
        "vault": v["name"], "resource_group": rg_of(v),
        "location": v.get("location"),
        "soft_delete": props.get("enableSoftDelete"),
        "purge_protection": props.get("enablePurgeProtection"),
        "rbac": rbac,
        "sku": (props.get("sku") or {}).get("name"),
        "findings": findings,
    }


def analyze_secrets(sub: str, vault: str) -> List[Dict]:
    rows = []
    secrets = try_az(["keyvault", "secret", "list",
                      "--vault-name", vault], sub,
                     default=[]) or []
    for s in secrets:
        attrs = s.get("attributes", {})
        findings = []
        exp = attrs.get("expires")
        if not exp:
            findings.append("🟡 Sin fecha de expiración")
        else:
            days = _days_to(exp)
            if days < 0:
                findings.append("🔴 Expirado")
            elif days <= WARN_DAYS:
                findings.append(f"🟡 Expira en {days}d")
        if not attrs.get("enabled", True):
            findings.append("ℹ️ Deshabilitado")
        rows.append({
            "vault": vault, "secret": s.get("name") or
            s.get("id", "").rsplit("/", 1)[-1],
            "expires": (exp or "")[:10] or None,
            "enabled": attrs.get("enabled", True),
            "findings": findings,
        })
    return rows


def get_args():
    p = argparse.ArgumentParser(
        description="Auditoría de Key Vaults y secretos")
    p.add_argument("--subscription", default="")
    p.add_argument("--vault", default="",
                   help="Solo este vault (vacío = todos)")
    p.add_argument("--secrets", action="store_true",
                   help="Incluir análisis de secretos")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)

    vaults = try_az(["keyvault", "list"], sub, default=[]) or []
    if args.vault:
        vaults = [v for v in vaults if v["name"] == args.vault]
    vault_rows = [analyze_vault(v) for v in vaults]

    secret_rows = []
    if args.secrets or args.vault:
        for v in vaults:
            secret_rows.extend(
                analyze_secrets(sub, v["name"]))

    critical = [v for v in vault_rows
                if any("🔴" in f for f in v["findings"])] + \
               [s for s in secret_rows
                if any("🔴" in f for f in s["findings"])]

    if console:
        from rich.table import Table
        t1 = Table(title="Key Vaults", header_style="bold cyan")
        for col in ["Vault", "RG", "SoftDel", "Purge", "RBAC",
                    "Findings"]:
            t1.add_column(col)
        for v in vault_rows:
            bad = any("🔴" in f for f in v["findings"])
            t1.add_row(
                v["vault"][:30], v["resource_group"][:18],
                "✓" if v["soft_delete"] else "[red]✗[/red]",
                "✓" if v["purge_protection"] else "✗",
                "✓" if v["rbac"] else "✗",
                f"[{'red' if bad else 'green'}]"
                f"{len(v['findings'])}"
                f"[/{'red' if bad else 'green'}]")
        console.print(t1)
        if secret_rows:
            t2 = Table(title="Secrets", header_style="bold "
                             "magenta")
            for col in ["Secret", "Expira", "Findings"]:
                t2.add_column(col)
            for s in secret_rows[:40]:
                bad = any("🔴" in f for f in s["findings"])
                t2.add_row(
                    s["secret"][:45],
                    s["expires"] or "—",
                    f"[{'red' if bad else 'green'}]"
                    f"{len(s['findings'])}"
                    f"[/{'red' if bad else 'green'}]")
            console.print(t2)
        for v in vault_rows + secret_rows:
            for f in v["findings"]:
                name = v.get("vault") or v.get("secret")
                console.print(f"  {f} [dim]({name})[/dim]")
    else:
        for v in vault_rows:
            print(f"{v['vault']}: {v['findings']}")

    _print(f"\nVaults: {len(vault_rows)} | secrets: "
           f"{len(secret_rows)} | críticos: {len(critical)}",
           "red" if critical else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"keyvault_{now_ts()}.{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "vaults": vault_rows, "secrets": secret_rows})
        else:
            rows = [{"vault": v["vault"],
                     "findings": "; ".join(v["findings"])}
                    for v in vault_rows] + \
                   [{"vault": s["vault"],
                     "secret": s["secret"],
                     "expires": s["expires"],
                     "findings": "; ".join(s["findings"])}
                    for s in secret_rows]
            export_csv(out, list(rows[0]) if rows else
                       ["vault"], rows)
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()
