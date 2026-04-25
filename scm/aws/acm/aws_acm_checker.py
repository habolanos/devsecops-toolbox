#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ACM Certificate Checker

Monitorea certificados SSL/TLS en AWS Certificate Manager, expiración y estado.

Uso:
    python aws_acm_checker.py --profile default --region us-east-1
    python aws_acm_checker.py --days 30 -o json
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
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
    from botocore.exceptions import ClientError
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
    parser = argparse.ArgumentParser(description="AWS ACM Certificate Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--days", "-D", type=int, default=30, help="Days threshold for expiration warning")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def analyze_certificates(acm_client, days_threshold: int) -> List[Dict]:
    results = []
    now = datetime.now(timezone.utc)
    
    paginator = acm_client.get_paginator('list_certificates')
    
    for page in paginator.paginate():
        for cert_summary in page['CertificateSummaryList']:
            cert_arn = cert_summary['CertificateArn']
            
            try:
                cert_details = acm_client.describe_certificate(CertificateArn=cert_arn)['Certificate']
                
                not_after = cert_details.get('NotAfter')
                days_remaining = None
                expiration_status = "ok"
                
                if not_after:
                    days_remaining = (not_after - now).days
                    if days_remaining < 0:
                        expiration_status = "expired"
                    elif days_remaining <= 7:
                        expiration_status = "critical"
                    elif days_remaining <= days_threshold:
                        expiration_status = "warning"
                
                cert_data = {
                    "domain_name": cert_details.get("DomainName", ""),
                    "arn": cert_arn,
                    "status": cert_details.get("Status", ""),
                    "type": cert_details.get("Type", ""),
                    "issuer": cert_details.get("Issuer", ""),
                    "key_algorithm": cert_details.get("KeyAlgorithm", ""),
                    "not_before": cert_details.get("NotBefore", "").isoformat() if cert_details.get("NotBefore") else None,
                    "not_after": not_after.isoformat() if not_after else None,
                    "days_remaining": days_remaining,
                    "expiration_status": expiration_status,
                    "in_use_by": cert_details.get("InUseBy", []),
                    "subject_alternative_names": cert_details.get("SubjectAlternativeNames", []),
                    "renewal_eligibility": cert_details.get("RenewalEligibility", ""),
                    "failure_reason": cert_details.get("FailureReason", ""),
                    "domain_validation_options": []
                }
                
                for dvo in cert_details.get("DomainValidationOptions", []):
                    cert_data["domain_validation_options"].append({
                        "domain": dvo.get("DomainName", ""),
                        "status": dvo.get("ValidationStatus", ""),
                        "method": dvo.get("ValidationMethod", "")
                    })
                
                results.append(cert_data)
            except ClientError as e:
                results.append({
                    "arn": cert_arn,
                    "error": str(e)
                })
    
    return results


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_acm_certificates_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "certificates": results}, f, indent=2)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_acm_certificates_{timestamp}.csv"
        rows = [{
            "domain": c.get("domain_name", ""), "status": c.get("status", ""),
            "type": c.get("type", ""), "days_remaining": c.get("days_remaining", ""),
            "expiration_status": c.get("expiration_status", ""), "in_use": len(c.get("in_use_by", []))
        } for c in results if "error" not in c]
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    table = Table(title="[bold]ACM Certificates Analysis[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("Dominio", style="cyan", max_width=40)
    table.add_column("Tipo", justify="center")
    table.add_column("Estado", justify="center")
    table.add_column("Días Rest.", justify="center")
    table.add_column("Expiración", justify="center")
    table.add_column("En Uso", justify="center")
    
    sorted_results = sorted([c for c in results if "error" not in c], key=lambda x: x.get("days_remaining") or 9999)
    
    for cert in sorted_results:
        status_color = "green" if cert["status"] == "ISSUED" else "yellow"
        
        exp_status = cert.get("expiration_status", "ok")
        if exp_status == "expired":
            exp_display = "[bold red]🔴 EXPIRADO[/bold red]"
        elif exp_status == "critical":
            exp_display = "[red]🔴 CRÍTICO[/red]"
        elif exp_status == "warning":
            exp_display = "[yellow]🟡 PRONTO[/yellow]"
        else:
            exp_display = "[green]🟢 OK[/green]"
        
        days = cert.get("days_remaining")
        days_display = f"{days}d" if days is not None else "-"
        
        in_use = len(cert.get("in_use_by", []))
        in_use_display = f"[green]{in_use}[/green]" if in_use > 0 else "[dim]0[/dim]"
        
        table.add_row(
            cert["domain_name"][:40],
            cert["type"][:10],
            f"[{status_color}]{cert['status']}[/{status_color}]",
            days_display,
            exp_display,
            in_use_display
        )
    
    console.print(table)


def display_results_plain(results: List[Dict]):
    print("\n=== ACM Certificates ===\n")
    print(f"{'Dominio':<40} {'Estado':<12} {'Días':<8} {'En Uso'}")
    print("-" * 70)
    for cert in sorted([c for c in results if "error" not in c], key=lambda x: x.get("days_remaining") or 9999):
        days = cert.get("days_remaining", "-")
        print(f"{cert['domain_name'][:40]:<40} {cert['status']:<12} {days:<8} {len(cert.get('in_use_by', []))}")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS ACM Certificate Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]\n"
            f"Alerta expiración: [magenta]{args.days} días[/magenta]",
            title="🔐 ACM Checker"
        ))
    else:
        print(f"AWS ACM Certificate Checker\nProfile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    acm_client = session.client('acm')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Analizando certificados ACM...", total=None)
            results = analyze_certificates(acm_client, args.days)
        console.print(f"✅ Certificados encontrados: [bold green]{len(results)}[/bold green]")
    else:
        print("Analizando certificados ACM...")
        results = analyze_certificates(acm_client, args.days)
        print(f"Certificados encontrados: {len(results)}")
    
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
    
    valid_certs = [c for c in results if "error" not in c]
    expiring = sum(1 for c in valid_certs if c.get("expiration_status") in ["warning", "critical"])
    expired = sum(1 for c in valid_certs if c.get("expiration_status") == "expired")
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total certificados:[/bold] [green]{len(valid_certs)}[/green]\n"
            f"[bold]Por expirar (<{args.days}d):[/bold] [yellow]{expiring}[/yellow] | [bold]Expirados:[/bold] [red]{expired}[/red]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nTotal: {len(valid_certs)} | Por expirar: {expiring} | Expirados: {expired}\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
