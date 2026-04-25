#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS IAM Users & Policies Checker

Analiza usuarios IAM, políticas adjuntas, estado de MFA y access keys.
Genera reportes detallados de seguridad IAM.

Uso:
    python aws_iam_checker.py --profile default --region us-east-1
    python aws_iam_checker.py -o json
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import time

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
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
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

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

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None


def get_args():
    parser = argparse.ArgumentParser(description="AWS IAM Users & Policies Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table", help="Output format")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        return session
    except Exception as e:
        print(f"ERROR: No se pudo crear sesión AWS: {e}")
        sys.exit(1)


def get_iam_users(iam_client) -> List[Dict]:
    users = []
    paginator = iam_client.get_paginator('list_users')
    
    for page in paginator.paginate():
        for user in page['Users']:
            users.append(user)
    
    return users


def get_user_details(iam_client, username: str) -> Dict:
    details = {
        "username": username,
        "mfa_enabled": False,
        "mfa_devices": 0,
        "access_keys": [],
        "attached_policies": [],
        "inline_policies": [],
        "groups": [],
        "password_last_used": None,
        "create_date": None
    }
    
    try:
        user_info = iam_client.get_user(UserName=username)
        details["create_date"] = user_info["User"].get("CreateDate", "").isoformat() if user_info["User"].get("CreateDate") else None
        details["password_last_used"] = user_info["User"].get("PasswordLastUsed", "").isoformat() if user_info["User"].get("PasswordLastUsed") else None
    except ClientError:
        pass
    
    try:
        mfa_devices = iam_client.list_mfa_devices(UserName=username)
        details["mfa_devices"] = len(mfa_devices.get("MFADevices", []))
        details["mfa_enabled"] = details["mfa_devices"] > 0
    except ClientError:
        pass
    
    try:
        access_keys = iam_client.list_access_keys(UserName=username)
        for key in access_keys.get("AccessKeyMetadata", []):
            key_info = {
                "access_key_id": key["AccessKeyId"],
                "status": key["Status"],
                "create_date": key["CreateDate"].isoformat() if key.get("CreateDate") else None
            }
            try:
                last_used = iam_client.get_access_key_last_used(AccessKeyId=key["AccessKeyId"])
                key_info["last_used"] = last_used.get("AccessKeyLastUsed", {}).get("LastUsedDate", "").isoformat() if last_used.get("AccessKeyLastUsed", {}).get("LastUsedDate") else "Never"
            except ClientError:
                key_info["last_used"] = "Unknown"
            details["access_keys"].append(key_info)
    except ClientError:
        pass
    
    try:
        attached = iam_client.list_attached_user_policies(UserName=username)
        details["attached_policies"] = [p["PolicyName"] for p in attached.get("AttachedPolicies", [])]
    except ClientError:
        pass
    
    try:
        inline = iam_client.list_user_policies(UserName=username)
        details["inline_policies"] = inline.get("PolicyNames", [])
    except ClientError:
        pass
    
    try:
        groups = iam_client.list_groups_for_user(UserName=username)
        details["groups"] = [g["GroupName"] for g in groups.get("Groups", [])]
    except ClientError:
        pass
    
    return details


def analyze_security_risks(user_details: Dict) -> List[str]:
    risks = []
    
    if not user_details["mfa_enabled"]:
        risks.append("MFA no habilitado")
    
    for key in user_details["access_keys"]:
        if key["status"] == "Active":
            if key.get("create_date"):
                create_date = datetime.fromisoformat(key["create_date"].replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - create_date).days
                if age_days > 90:
                    risks.append(f"Access Key {key['access_key_id'][-4:]} tiene {age_days} días (>90)")
    
    if len(user_details["access_keys"]) > 1:
        active_keys = sum(1 for k in user_details["access_keys"] if k["status"] == "Active")
        if active_keys > 1:
            risks.append(f"Múltiples access keys activas ({active_keys})")
    
    if not user_details["attached_policies"] and not user_details["inline_policies"] and not user_details["groups"]:
        risks.append("Sin políticas ni grupos asignados")
    
    return risks


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_iam_users_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_users": len(results),
                "users": results
            }, f, indent=2, default=str)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_iam_users_{timestamp}.csv"
        rows = []
        for user in results:
            rows.append({
                "username": user["username"],
                "mfa_enabled": user["mfa_enabled"],
                "access_keys_count": len(user["access_keys"]),
                "policies_count": len(user["attached_policies"]) + len(user["inline_policies"]),
                "groups": ", ".join(user["groups"]),
                "risks": ", ".join(user.get("security_risks", []))
            })
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    table = Table(title="[bold]IAM Users Analysis[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("Usuario", style="cyan")
    table.add_column("MFA", justify="center")
    table.add_column("Keys", justify="center")
    table.add_column("Políticas", justify="center")
    table.add_column("Grupos", justify="center")
    table.add_column("Riesgos", style="red")
    
    for user in results:
        mfa_status = "✅" if user["mfa_enabled"] else "❌"
        risks = user.get("security_risks", [])
        risk_text = f"⚠️ {len(risks)}" if risks else "✅"
        
        table.add_row(
            user["username"],
            mfa_status,
            str(len(user["access_keys"])),
            str(len(user["attached_policies"]) + len(user["inline_policies"])),
            str(len(user["groups"])),
            risk_text
        )
    
    console.print(table)
    
    users_with_risks = [u for u in results if u.get("security_risks")]
    if users_with_risks:
        console.print("\n[bold red]⚠️ Usuarios con riesgos de seguridad:[/bold red]")
        for user in users_with_risks:
            console.print(f"  [yellow]{user['username']}[/yellow]:")
            for risk in user["security_risks"]:
                console.print(f"    - {risk}")


def display_results_plain(results: List[Dict]):
    print("\n=== IAM Users Analysis ===\n")
    print(f"{'Usuario':<30} {'MFA':<6} {'Keys':<6} {'Políticas':<10} {'Grupos':<8} {'Riesgos':<10}")
    print("-" * 80)
    
    for user in results:
        mfa_status = "Yes" if user["mfa_enabled"] else "No"
        risks = len(user.get("security_risks", []))
        
        print(f"{user['username']:<30} {mfa_status:<6} {len(user['access_keys']):<6} "
              f"{len(user['attached_policies']) + len(user['inline_policies']):<10} "
              f"{len(user['groups']):<8} {risks:<10}")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS IAM Users & Policies Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="🔐 IAM Checker"
        ))
    else:
        print(f"AWS IAM Users & Policies Checker")
        print(f"Profile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    iam_client = session.client('iam')
    
    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task("[cyan]Obteniendo lista de usuarios IAM...", total=None)
            users = get_iam_users(iam_client)
        console.print(f"✅ Usuarios encontrados: [bold green]{len(users)}[/bold green]")
    else:
        print("Obteniendo lista de usuarios IAM...")
        users = get_iam_users(iam_client)
        print(f"Usuarios encontrados: {len(users)}")
    
    results = []
    
    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Analizando usuarios...", total=len(users))
            
            for user in users:
                username = user["UserName"]
                progress.update(task, description=f"[cyan]Analizando: {username[:30]}...")
                
                details = get_user_details(iam_client, username)
                details["security_risks"] = analyze_security_risks(details)
                results.append(details)
                
                progress.advance(task)
    else:
        for i, user in enumerate(users, 1):
            username = user["UserName"]
            print(f"[{i}/{len(users)}] Analizando: {username}")
            
            details = get_user_details(iam_client, username)
            details["security_risks"] = analyze_security_risks(details)
            results.append(details)
    
    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    if args.output == "table":
        if RICH_AVAILABLE:
            display_results_rich(results)
        else:
            display_results_plain(results)
    else:
        export_results(results, args.output)
    
    users_with_mfa = sum(1 for u in results if u["mfa_enabled"])
    users_with_risks = sum(1 for u in results if u.get("security_risks"))
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total usuarios:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]Con MFA:[/bold] [green]{users_with_mfa}[/green] | [bold]Sin MFA:[/bold] [red]{len(results) - users_with_mfa}[/red]\n"
            f"[bold]Con riesgos:[/bold] [yellow]{users_with_risks}[/yellow]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===")
        print(f"Total usuarios: {len(results)}")
        print(f"Con MFA: {users_with_mfa} | Sin MFA: {len(results) - users_with_mfa}")
        print(f"Con riesgos: {users_with_risks}")
        print(f"Tiempo de ejecución: {time_str}")


if __name__ == "__main__":
    main()
