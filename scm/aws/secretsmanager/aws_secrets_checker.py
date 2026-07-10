# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Secrets Manager & SSM Parameter Store Checker

Analiza secretos en Secrets Manager y parámetros en SSM Parameter Store:
- Lista secretos con metadatos, rotación y uso
- Lista parámetros SSM (Standard, Advanced, SecureString)
- Detecta secretos sin rotación, expirados o no utilizados
- Identifica referencias en EKS workloads (via kubectl si disponible)

Equivalente AWS de: gcp_secrets_configmaps_checker.py (GKE Secrets & ConfigMaps)

Uso:
    python aws_secrets_checker.py --profile default --region us-east-1
    python aws_secrets_checker.py --filter my-secret -o json
    python aws_secrets_checker.py --ssm-only
    python aws_secrets_checker.py --secrets-only

Autor: Harold Adrian
"""

import sys
import json
import argparse
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import time

# --- Directorio de salida centralizado ---
try:
    from utils import get_output_dir
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
# -------------------------------------------------------------------

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("ERROR: boto3 no instalado. Ejecute: pip install boto3")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.tree import Tree
    RICH_AVAILABLE = True
try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None


def get_args():
    parser = argparse.ArgumentParser(description="AWS Secrets Manager & SSM Parameter Store Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--filter", "-f", default="", help="Filtrar por nombre (substring)")
    parser.add_argument("--secrets-only", action="store_true", help="Solo Secrets Manager")
    parser.add_argument("--ssm-only", action="store_true", help="Solo SSM Parameter Store")
    parser.add_argument("--rotation-warning-days", type=int, default=30,
                        help="Días sin rotación para marcar advertencia (default: 30)")
    parser.add_argument("--debug", "-d", action="store_true", help="Modo debug")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR creando sesión AWS: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# SECRETS MANAGER
# ─────────────────────────────────────────────────────────────────────────────

def analyze_secrets(sm_client, name_filter: str = "", rotation_warning_days: int = 30) -> List[Dict]:
    """Lista y analiza secretos en AWS Secrets Manager."""
    results = []
    now = datetime.now(timezone.utc)

    paginator = sm_client.get_paginator("list_secrets")
    for page in paginator.paginate():
        for secret in page.get("SecretList", []):
            name = secret.get("Name", "")
            if name_filter and name_filter.lower() not in name.lower():
                continue

            last_changed = secret.get("LastChangedDate")
            last_accessed = secret.get("LastAccessedDate")
            rotation_enabled = secret.get("RotationEnabled", False)
            next_rotation = secret.get("NextRotationDate")

            days_since_change = (now - last_changed).days if last_changed else None
            days_since_access = (now - last_accessed).days if last_accessed else None

            findings = []
            if not rotation_enabled:
                findings.append("Sin rotación automática")
            if rotation_enabled and days_since_change and days_since_change > rotation_warning_days:
                findings.append(f"Sin rotación hace {days_since_change} días")
            if last_accessed is None:
                findings.append("Nunca accedido")
            elif days_since_access and days_since_access > 90:
                findings.append(f"Sin acceso hace {days_since_access} días")

            deleted_date = secret.get("DeletedDate")
            status = "DELETED" if deleted_date else "ACTIVE"

            results.append({
                "source": "secrets_manager",
                "name": name,
                "arn": secret.get("ARN", ""),
                "description": secret.get("Description", ""),
                "status": status,
                "rotation_enabled": rotation_enabled,
                "rotation_rules": secret.get("RotationRules", {}),
                "next_rotation": next_rotation.isoformat() if next_rotation else "",
                "last_changed": last_changed.isoformat() if last_changed else "",
                "last_accessed": last_accessed.isoformat() if last_accessed else "",
                "days_since_change": days_since_change,
                "days_since_access": days_since_access,
                "kms_key_id": secret.get("KmsKeyId", "aws/secretsmanager"),
                "tags": {t["Key"]: t["Value"] for t in secret.get("Tags", [])},
                "findings": findings,
            })

    return sorted(results, key=lambda x: x["name"])


# ─────────────────────────────────────────────────────────────────────────────
# SSM PARAMETER STORE (equivalente a ConfigMaps en GKE)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_ssm_parameters(ssm_client, name_filter: str = "") -> List[Dict]:
    """Lista y analiza parámetros en AWS SSM Parameter Store."""
    results = []
    now = datetime.now(timezone.utc)

    paginator = ssm_client.get_paginator("describe_parameters")
    for page in paginator.paginate():
        for param in page.get("Parameters", []):
            name = param.get("Name", "")
            if name_filter and name_filter.lower() not in name.lower():
                continue

            ptype = param.get("Type", "")
            last_modified = param.get("LastModifiedDate")
            days_since_modified = (now - last_modified).days if last_modified else None

            findings = []
            if ptype == "String" and "/secret" in name.lower():
                findings.append("Posible secreto como String sin cifrado")
            if ptype == "String" and "/password" in name.lower():
                findings.append("Posible contraseña como String sin cifrado")
            if days_since_modified and days_since_modified > 180:
                findings.append(f"Sin modificar hace {days_since_modified} días")

            results.append({
                "source": "ssm_parameter_store",
                "name": name,
                "arn": param.get("ARN", ""),
                "description": param.get("Description", ""),
                "type": ptype,
                "tier": param.get("Tier", "Standard"),
                "data_type": param.get("DataType", "text"),
                "version": param.get("Version", 1),
                "last_modified": last_modified.isoformat() if last_modified else "",
                "days_since_modified": days_since_modified,
                "last_modified_user": param.get("LastModifiedUser", ""),
                "kms_key_id": param.get("KeyId", "") if ptype == "SecureString" else "",
                "findings": findings,
            })

    return sorted(results, key=lambda x: x["name"])


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────────────────────────────────────

def display_secrets_rich(secrets: List[Dict], ssm_params: List[Dict]):
    """Muestra resultados con Rich."""
    if secrets:
        table = Table(
            title="🔐 AWS Secrets Manager",
            show_header=True,
            header_style="bold white on dark_red",
            show_lines=True,
        )
        table.add_column("Nombre", style="cyan", min_width=30)
        table.add_column("Estado", width=8)
        table.add_column("Rotación", width=10, justify="center")
        table.add_column("KMS Key", style="dim", width=25)
        table.add_column("Último Cambio", width=12)
        table.add_column("Último Acceso", width=12)
        table.add_column("Findings", min_width=25)

        for s in secrets:
            rot_icon = "✅" if s["rotation_enabled"] else "❌"
            status_color = "green" if s["status"] == "ACTIVE" else "red"
            changed = s["last_changed"][:10] if s["last_changed"] else "N/A"
            accessed = s["last_accessed"][:10] if s["last_accessed"] else "Nunca"
            findings_str = "; ".join(s["findings"]) if s["findings"] else "✅ OK"
            findings_style = "yellow" if s["findings"] else "green"

            table.add_row(
                s["name"],
                f"[{status_color}]{s['status']}[/{status_color}]",
                rot_icon,
                s["kms_key_id"][:25] if s["kms_key_id"] else "default",
                changed,
                accessed,
                f"[{findings_style}]{findings_str}[/{findings_style}]",
            )

        console.print(table)
        console.print()

    if ssm_params:
        table2 = Table(
            title="⚙️ SSM Parameter Store",
            show_header=True,
            header_style="bold white on blue",
            show_lines=True,
        )
        table2.add_column("Nombre", style="cyan", min_width=35)
        table2.add_column("Tipo", width=14)
        table2.add_column("Tier", width=10)
        table2.add_column("Versión", width=7, justify="right")
        table2.add_column("Último Cambio", width=12)
        table2.add_column("Findings", min_width=25)

        for p in ssm_params:
            type_color = "red" if p["type"] == "SecureString" else "yellow" if p["type"] == "StringList" else "white"
            findings_str = "; ".join(p["findings"]) if p["findings"] else "✅ OK"
            findings_style = "yellow" if p["findings"] else "green"
            modified = p["last_modified"][:10] if p["last_modified"] else "N/A"

            table2.add_row(
                p["name"],
                f"[{type_color}]{p['type']}[/{type_color}]",
                p["tier"],
                str(p["version"]),
                modified,
                f"[{findings_style}]{findings_str}[/{findings_style}]",
            )

        console.print(table2)
        console.print()


def display_results_plain(secrets: List[Dict], ssm_params: List[Dict]):
    if secrets:
        print("\n=== Secrets Manager ===")
        for s in secrets:
            print(f"  [{s['status']}] {s['name']} | Rotación: {'Sí' if s['rotation_enabled'] else 'No'} | Findings: {len(s['findings'])}")
    if ssm_params:
        print("\n=== SSM Parameter Store ===")
        for p in ssm_params:
            print(f"  {p['name']} | {p['type']} | {p['tier']} | v{p['version']} | Findings: {len(p['findings'])}")


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def export_results(results: List[Dict], output_format: str):

    """Exporta resultados usando ExportManager centralizado con fallback."""

    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual
        if output_format == "json":
            filepath = OUTCOME_DIR / f"aws_secrets_checker_{timestamp}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": results}, f, indent=2)
        elif output_format == "csv":
            try:
                import pandas as pd
                filepath = OUTCOME_DIR / f"aws_secrets_checker_{timestamp}.csv"
                pd.DataFrame(results).to_csv(filepath, index=False)
            except ImportError:
                print("ERROR: Instala pandas para exportar a CSV")
                return
        else:
            return
        
        print(f"\n✅ Resultados exportados a: {filepath}")
        return
    
    # Usar ExportManager
    manager = ExportManager("aws_secrets_checker", "1.0.0")
    
    summary = {"total_items": len(results)}
    
    if output_format == "json":
        manager.export_json(results, summary=summary)
    elif output_format == "csv":
        manager.export_csv(results)
    elif output_format == "excel":
        manager.export_excel(results, sheet_name="Results", summary=summary)

def main():
    start_time = time.time()
    args = get_args()

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS Secrets Manager & SSM Parameter Store Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="🔐 Secrets Checker"
        ))
    else:
        print(f"AWS Secrets Checker | Profile: {args.profile} | Region: {args.region}\n")

    session = get_session(args.profile, args.region)
    secrets: List[Dict] = []
    ssm_params: List[Dict] = []

    try:
        if not args.ssm_only:
            sm_client = session.client("secretsmanager")
            if RICH_AVAILABLE:
                with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"), transient=True, console=console) as p:
                    p.add_task("Analizando Secrets Manager...", total=None)
                    secrets = analyze_secrets(sm_client, args.filter, args.rotation_warning_days)
            else:
                print("Analizando Secrets Manager...")
                secrets = analyze_secrets(sm_client, args.filter, args.rotation_warning_days)

        if not args.secrets_only:
            ssm_client = session.client("ssm")
            if RICH_AVAILABLE:
                with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"), transient=True, console=console) as p:
                    p.add_task("Analizando SSM Parameter Store...", total=None)
                    ssm_params = analyze_ssm_parameters(ssm_client, args.filter)
            else:
                print("Analizando SSM Parameter Store...")
                ssm_params = analyze_ssm_parameters(ssm_client, args.filter)

    except (ClientError, NoCredentialsError) as e:
        if RICH_AVAILABLE:
            console.print(f"[red]❌ Error AWS: {e}[/red]")
        else:
            print(f"ERROR AWS: {e}")
        sys.exit(1)

    elapsed = time.time() - start_time
    m, s = divmod(int(elapsed), 60)
    time_str = f"{m}m {s}s" if m else f"{s}s"

    if args.output == "table":
        if RICH_AVAILABLE:
            display_secrets_rich(secrets, ssm_params)
        else:
            display_results_plain(secrets, ssm_params)
    else:
        export_results(secrets, ssm_params, args.output)

    # Resumen
    secrets_with_findings = sum(1 for s in secrets if s["findings"])
    ssm_with_findings = sum(1 for p in ssm_params if p["findings"])
    no_rotation = sum(1 for s in secrets if not s["rotation_enabled"])

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold]Secrets Manager:[/bold] [green]{len(secrets)}[/green] secretos "
            f"([red]{secrets_with_findings}[/red] con findings | [yellow]{no_rotation}[/yellow] sin rotación)\n"
            f"[bold]SSM Parameters:[/bold] [green]{len(ssm_params)}[/green] parámetros "
            f"([red]{ssm_with_findings}[/red] con findings)\n"
            f"[bold]Tiempo:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===")
        print(f"Secrets: {len(secrets)} ({secrets_with_findings} findings) | SSM: {len(ssm_params)} ({ssm_with_findings} findings)")
        print(f"Tiempo: {time_str}")


if __name__ == "__main__":
    main()

