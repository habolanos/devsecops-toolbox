# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS EBS Volume Checker

Analiza volúmenes EBS: estado, tipo, tamaño, cifrado, snapshots y uso.
Detecta volúmenes sin adjuntar, sin cifrar o con snapshots desactualizados.

Equivalente AWS de: gcp_disk_checker.py (GCP Persistent Disk Checker)

Uso:
    python aws_ebs_checker.py --profile default --region us-east-1
    python aws_ebs_checker.py --unattached-only -o csv
    python aws_ebs_checker.py --volume-id vol-12345678

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
    parser = argparse.ArgumentParser(description="AWS EBS Volume Checker")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region")
    parser.add_argument("--output", "-o", choices=["json", "csv", "table"], default="table")
    parser.add_argument("--volume-id", default="", help="Filtrar por Volume ID")
    parser.add_argument("--unattached-only", action="store_true", help="Solo volúmenes no adjuntados")
    parser.add_argument("--unencrypted-only", action="store_true", help="Solo volúmenes sin cifrar")
    parser.add_argument("--snapshot-days", type=int, default=7,
                        help="Días sin snapshot para marcar advertencia (default: 7)")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def get_latest_snapshot(ec2_client, volume_id: str) -> Optional[Dict]:
    """Obtiene el snapshot más reciente de un volumen."""
    try:
        resp = ec2_client.describe_snapshots(
            Filters=[{"Name": "volume-id", "Values": [volume_id]}],
            OwnerIds=["self"]
        )
        snaps = sorted(resp.get("Snapshots", []),
                       key=lambda x: x.get("StartTime", datetime.min.replace(tzinfo=timezone.utc)),
                       reverse=True)
        return snaps[0] if snaps else None
    except ClientError:
        return None


def analyze_volumes(ec2_client, volume_id_filter: str = "", unattached_only: bool = False,
                    unencrypted_only: bool = False, snapshot_days: int = 7) -> List[Dict]:
    now = datetime.now(timezone.utc)
    results = []

    filters = []
    if volume_id_filter:
        filters.append({"Name": "volume-id", "Values": [volume_id_filter]})
    if unattached_only:
        filters.append({"Name": "status", "Values": ["available"]})
    if unencrypted_only:
        filters.append({"Name": "encrypted", "Values": ["false"]})

    paginator = ec2_client.get_paginator("describe_volumes")
    for page in paginator.paginate(Filters=filters):
        for vol in page.get("Volumes", []):
            vol_id = vol.get("VolumeId", "")
            state = vol.get("State", "")
            attachments = vol.get("Attachments", [])
            attached = bool(attachments)
            instance_id = attachments[0].get("InstanceId", "") if attached else ""
            device = attachments[0].get("Device", "") if attached else ""

            create_time = vol.get("CreateTime")
            age_days = (now - create_time).days if create_time else None

            # Snapshot más reciente
            latest_snap = get_latest_snapshot(ec2_client, vol_id)
            snap_age_days = None
            if latest_snap:
                snap_time = latest_snap.get("StartTime")
                if snap_time:
                    snap_age_days = (now - snap_time).days

            tags = {t["Key"]: t["Value"] for t in vol.get("Tags", [])}
            name = tags.get("Name", "")

            findings = []
            if not vol.get("Encrypted", False):
                findings.append("Sin cifrado KMS")
            if not attached:
                findings.append("Volumen no adjuntado")
            if snap_age_days is None:
                findings.append("Sin snapshots")
            elif snap_age_days > snapshot_days:
                findings.append(f"Snapshot hace {snap_age_days} días")
            if not tags.get("Environment") and not tags.get("Env"):
                findings.append("Sin tag Environment")

            results.append({
                "volume_id": vol_id,
                "name": name,
                "state": state,
                "volume_type": vol.get("VolumeType", ""),
                "size_gb": vol.get("Size", 0),
                "iops": vol.get("Iops", 0),
                "throughput": vol.get("Throughput", 0),
                "encrypted": vol.get("Encrypted", False),
                "kms_key_id": vol.get("KmsKeyId", ""),
                "availability_zone": vol.get("AvailabilityZone", ""),
                "attached": attached,
                "instance_id": instance_id,
                "device": device,
                "multi_attach": vol.get("MultiAttachEnabled", False),
                "age_days": age_days,
                "latest_snapshot_id": latest_snap.get("SnapshotId", "") if latest_snap else "",
                "latest_snapshot_age_days": snap_age_days,
                "snapshot_count": 0,
                "tags": tags,
                "findings": findings,
            })

    return sorted(results, key=lambda x: (not x["attached"], x["volume_id"]))


def display_table_rich(volumes: List[Dict]):
    table = Table(
        title=f"💾 EBS Volumes ({len(volumes)} volúmenes)",
        header_style="bold white on purple4",
        show_lines=True,
    )
    table.add_column("Volume ID", style="cyan", width=22)
    table.add_column("Nombre", width=25)
    table.add_column("Estado", width=10)
    table.add_column("Tipo", width=10)
    table.add_column("Tamaño", justify="right", width=8)
    table.add_column("AZ", style="dim", width=16)
    table.add_column("Cifrado", width=8, justify="center")
    table.add_column("Adjunto a", width=22)
    table.add_column("Snap (días)", justify="right", width=11)
    table.add_column("Findings", min_width=25)

    for v in volumes:
        state_color = "green" if v["state"] == "in-use" else "yellow" if v["state"] == "available" else "red"
        enc_icon = "✅" if v["encrypted"] else "❌"
        size_str = f"{v['size_gb']} GiB"
        attached_to = v["instance_id"] if v["attached"] else "[dim]—[/dim]"
        snap_str = str(v["latest_snapshot_age_days"]) if v["latest_snapshot_age_days"] is not None else "—"
        snap_color = "red" if (v["latest_snapshot_age_days"] is None or v["latest_snapshot_age_days"] > 7) else "green"
        findings_str = "; ".join(v["findings"]) if v["findings"] else "✅ OK"
        findings_color = "yellow" if v["findings"] else "green"

        table.add_row(
            v["volume_id"],
            v["name"][:25],
            f"[{state_color}]{v['state']}[/{state_color}]",
            v["volume_type"],
            size_str,
            v["availability_zone"],
            enc_icon,
            attached_to,
            f"[{snap_color}]{snap_str}[/{snap_color}]",
            f"[{findings_color}]{findings_str}[/{findings_color}]",
        )

    console.print(table)


def display_table_plain(volumes: List[Dict]):
    print(f"\n{'VOLUME ID':<25} {'TIPO':<12} {'GiB':>5} {'ESTADO':<12} {'CIFRADO':<8} {'FINDINGS'}")
    print("-" * 100)
    for v in volumes:
        print(f"{v['volume_id']:<25} {v['volume_type']:<12} {v['size_gb']:>5} "
              f"{v['state']:<12} {'Sí' if v['encrypted'] else 'No':<8} "
              f"{'; '.join(v['findings']) or 'OK'}")


def export_results(results: List[Dict], output_format: str):

    """Exporta resultados usando ExportManager centralizado con fallback."""

    OUTCOME_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual
        if output_format == "json":
            filepath = OUTCOME_DIR / f"aws_ebs_checker_{timestamp}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": results}, f, indent=2)
        elif output_format == "csv":
            try:
                import pandas as pd
                filepath = OUTCOME_DIR / f"aws_ebs_checker_{timestamp}.csv"
                pd.DataFrame(results).to_csv(filepath, index=False)
            except ImportError:
                print("ERROR: Instala pandas para exportar a CSV")
                return
        else:
            return
        
        print(f"\n✅ Resultados exportados a: {filepath}")
        return
    
    # Usar ExportManager
    manager = ExportManager("aws_ebs_checker", "1.0.0")
    
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
            f"[bold cyan]AWS EBS Volume Checker[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow]",
            title="💾 EBS Checker"
        ))
    else:
        print(f"AWS EBS Volume Checker | Profile: {args.profile} | Region: {args.region}")

    session = get_session(args.profile, args.region)
    ec2_client = session.client("ec2")

    try:
        if RICH_AVAILABLE:
            with Progress(SpinnerColumn(), TextColumn("[cyan]{task.description}"), transient=True, console=console) as p:
                p.add_task("Analizando volúmenes EBS...", total=None)
                volumes = analyze_volumes(
                    ec2_client, args.volume_id, args.unattached_only,
                    args.unencrypted_only, args.snapshot_days
                )
        else:
            print("Analizando volúmenes EBS...")
            volumes = analyze_volumes(
                ec2_client, args.volume_id, args.unattached_only,
                args.unencrypted_only, args.snapshot_days
            )
    except ClientError as e:
        if RICH_AVAILABLE:
            console.print(f"[red]❌ Error AWS: {e}[/red]")
        else:
            print(f"ERROR: {e}")
        sys.exit(1)

    elapsed = time.time() - start_time
    m, s = divmod(int(elapsed), 60)
    time_str = f"{m}m {s}s" if m else f"{s}s"

    if args.output == "table":
        if RICH_AVAILABLE:
            display_table_rich(volumes)
        else:
            display_table_plain(volumes)
    else:
        export_results(volumes, args.output)

    unattached = sum(1 for v in volumes if not v["attached"])
    unencrypted = sum(1 for v in volumes if not v["encrypted"])
    with_findings = sum(1 for v in volumes if v["findings"])
    total_gib = sum(v["size_gb"] for v in volumes)

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold]Total volúmenes:[/bold] [green]{len(volumes)}[/green] ({total_gib:,} GiB)\n"
            f"[bold]Sin adjuntar:[/bold] [yellow]{unattached}[/yellow] | [bold]Sin cifrar:[/bold] [red]{unencrypted}[/red] | "
            f"[bold]Con findings:[/bold] [yellow]{with_findings}[/yellow]\n"
            f"[bold]Tiempo:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen"
        ))
    else:
        print(f"\nVolúmenes: {len(volumes)} ({total_gib:,} GiB) | Sin adjuntar: {unattached} | Sin cifrar: {unencrypted} | {time_str}")


if __name__ == "__main__":
    main()

