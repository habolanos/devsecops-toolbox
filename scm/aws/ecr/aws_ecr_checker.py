#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECR Repository Checker

Lista repositorios ECR, imágenes, políticas de ciclo de vida y scanning.

Uso:
    python aws_ecr_checker.py --profile default --region us-east-1
    python aws_ecr_checker.py -o json
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import time

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

BASE_DIR = Path(__file__).parent.parent.absolute()
OUTCOME_DIR = BASE_DIR / "outcome"
console = Console() if RICH_AVAILABLE else None


def get_args():
    parser = argparse.ArgumentParser(description="AWS ECR Repository Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--repo", default="", help="Filter by repository name")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def analyze_repositories(ecr_client, repo_filter: str = "") -> List[Dict]:
    results = []
    
    paginator = ecr_client.get_paginator('describe_repositories')
    
    for page in paginator.paginate():
        for repo in page['repositories']:
            repo_name = repo['repositoryName']
            
            if repo_filter and repo_filter.lower() not in repo_name.lower():
                continue
            
            repo_data = {
                "name": repo_name,
                "arn": repo.get("repositoryArn", ""),
                "uri": repo.get("repositoryUri", ""),
                "created_at": repo.get("createdAt", "").isoformat() if repo.get("createdAt") else None,
                "image_tag_mutability": repo.get("imageTagMutability", ""),
                "scan_on_push": repo.get("imageScanningConfiguration", {}).get("scanOnPush", False),
                "encryption_type": repo.get("encryptionConfiguration", {}).get("encryptionType", ""),
                "image_count": 0,
                "total_size_mb": 0,
                "latest_image": None,
                "lifecycle_policy": False,
                "repository_policy": False,
                "findings": []
            }
            
            try:
                images = ecr_client.describe_images(repositoryName=repo_name, maxResults=100)
                image_details = images.get("imageDetails", [])
                repo_data["image_count"] = len(image_details)
                
                total_bytes = sum(img.get("imageSizeInBytes", 0) for img in image_details)
                repo_data["total_size_mb"] = round(total_bytes / (1024 * 1024), 2)
                
                if image_details:
                    sorted_images = sorted(image_details, key=lambda x: x.get("imagePushedAt", datetime.min), reverse=True)
                    latest = sorted_images[0]
                    repo_data["latest_image"] = {
                        "tags": latest.get("imageTags", []),
                        "pushed_at": latest.get("imagePushedAt", "").isoformat() if latest.get("imagePushedAt") else None,
                        "size_mb": round(latest.get("imageSizeInBytes", 0) / (1024 * 1024), 2)
                    }
            except ClientError:
                pass
            
            try:
                ecr_client.get_lifecycle_policy(repositoryName=repo_name)
                repo_data["lifecycle_policy"] = True
            except ClientError:
                repo_data["findings"].append("Sin lifecycle policy configurada")
            
            try:
                ecr_client.get_repository_policy(repositoryName=repo_name)
                repo_data["repository_policy"] = True
            except ClientError:
                pass
            
            if not repo_data["scan_on_push"]:
                repo_data["findings"].append("Scan on push deshabilitado")
            
            if repo_data["image_tag_mutability"] == "MUTABLE":
                repo_data["findings"].append("Tags mutables (riesgo de sobrescritura)")
            
            results.append(repo_data)
    
    return results


def export_results(results: List[Dict], output_format: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_format == "json":
        filepath = OUTCOME_DIR / f"aws_ecr_repos_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(), "repositories": results}, f, indent=2)
    elif output_format == "csv":
        import pandas as pd
        filepath = OUTCOME_DIR / f"aws_ecr_repos_{timestamp}.csv"
        rows = [{
            "name": r["name"], "images": r["image_count"], "size_mb": r["total_size_mb"],
            "scan_on_push": r["scan_on_push"], "lifecycle": r["lifecycle_policy"],
            "findings": len(r["findings"])
        } for r in results]
        pd.DataFrame(rows).to_csv(filepath, index=False)
    
    print(f"\n✅ Resultados exportados a: {filepath}")


def display_results_rich(results: List[Dict]):
    table = Table(title="[bold]ECR Repositories Analysis[/bold]", show_header=True, header_style="bold white on blue")
    table.add_column("Repositorio", style="cyan", max_width=40)
    table.add_column("Imágenes", justify="center")
    table.add_column("Tamaño", justify="right")
    table.add_column("Scan", justify="center")
    table.add_column("Lifecycle", justify="center")
    table.add_column("Mutability", justify="center")
    table.add_column("Findings", justify="center")
    
    for repo in sorted(results, key=lambda x: x["image_count"], reverse=True):
        scan = "✅" if repo["scan_on_push"] else "❌"
        lifecycle = "✅" if repo["lifecycle_policy"] else "❌"
        mutability = "[green]IMMUTABLE[/green]" if repo["image_tag_mutability"] == "IMMUTABLE" else "[yellow]MUTABLE[/yellow]"
        findings = f"[red]⚠️ {len(repo['findings'])}[/red]" if repo["findings"] else "[green]✅[/green]"
        
        table.add_row(
            repo["name"][:40],
            str(repo["image_count"]),
            f"{repo['total_size_mb']} MB",
            scan,
            lifecycle,
            mutability,
            findings
        )
    
    console.print(table)


def display_results_plain(results: List[Dict]):
    print("\n=== ECR Repositories ===\n")
    print(f"{'Repositorio':<40} {'Imágenes':<10} {'Tamaño':<12} {'Scan':<8}")
    print("-" * 75)
    for repo in sorted(results, key=lambda x: x["image_count"], reverse=True):
        print(f"{repo['name'][:40]:<40} {repo['image_count']:<10} {repo['total_size_mb']:<12} {'Yes' if repo['scan_on_push'] else 'No':<8}")


def main():
    start_time = time.time()
    args = get_args()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS ECR Repository Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="📦 ECR Checker"
        ))
    else:
        print(f"AWS ECR Repository Checker\nProfile: {args.profile} | Region: {args.region}\n")
    
    session = get_session(args.profile, args.region)
    ecr_client = session.client('ecr')
    
    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True, console=console) as progress:
            progress.add_task("[cyan]Analizando repositorios ECR...", total=None)
            results = analyze_repositories(ecr_client, args.repo)
        console.print(f"✅ Repositorios encontrados: [bold green]{len(results)}[/bold green]")
    else:
        print("Analizando repositorios ECR...")
        results = analyze_repositories(ecr_client, args.repo)
        print(f"Repositorios encontrados: {len(results)}")
    
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
    
    total_images = sum(r["image_count"] for r in results)
    total_size = sum(r["total_size_mb"] for r in results)
    
    if RICH_AVAILABLE:
        console.print()
        console.print(Panel.fit(
            f"[bold]Total repositorios:[/bold] [green]{len(results)}[/green]\n"
            f"[bold]Total imágenes:[/bold] [cyan]{total_images}[/cyan] | [bold]Tamaño total:[/bold] [magenta]{total_size:.2f} MB[/magenta]\n"
            f"[bold]Tiempo de ejecución:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\n=== RESUMEN ===\nRepositorios: {len(results)} | Imágenes: {total_images} | Tamaño: {total_size:.2f} MB\nTiempo: {time_str}")


if __name__ == "__main__":
    main()
