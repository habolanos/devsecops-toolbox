# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Inventory Generator

Genera un inventario completo de recursos AWS en múltiples regiones:
- Clusters EKS y node groups
- Instancias RDS y Aurora clusters
- Instancias EC2
- Load Balancers (ALB/NLB)
- Funciones Lambda
- Tablas DynamoDB
- Buckets S3 (resumen)

Exporta a CSV por servicio y opcionalmente combina todo en un Excel con tabs.

Equivalente AWS de: generar-inventario-csv.py / generar-inventario-csv-combinar-a-excel.py

Uso:
    python aws_inventory_generator.py --profile default --region us-east-1
    python aws_inventory_generator.py --all-regions
    python aws_inventory_generator.py --services eks,rds,ec2 -o excel
    python aws_inventory_generator.py -o csv

Autor: Harold Adrian
"""

import sys
import json
import argparse
import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
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
except ImportError:
    RICH_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "Harold Adrian"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None

SUPPORTED_SERVICES = ["eks", "rds", "ec2", "elb", "lambda", "dynamodb", "s3"]



try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

def get_args():
    parser = argparse.ArgumentParser(description="AWS Inventory Generator")
    parser.add_argument("--profile", "-p", default="default", help="AWS CLI profile")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region (o 'all')")
    parser.add_argument("--all-regions", action="store_true", help="Inventario en todas las regiones disponibles")
    parser.add_argument("--services", default=",".join(SUPPORTED_SERVICES),
                        help=f"Servicios separados por coma (default: todos). Opciones: {','.join(SUPPORTED_SERVICES)}")
    parser.add_argument("--output", "-o", choices=["csv", "excel", "json"], default="csv",
                        help="Formato de salida (default: csv)")
    parser.add_argument("--workers", type=int, default=4, help="Threads paralelos (default: 4)")
    parser.add_argument("--debug", "-d", action="store_true")
    return parser.parse_args()


def get_session(profile: str, region: str):
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def get_all_regions(session) -> List[str]:
    ec2 = session.client("ec2", region_name="us-east-1")
    try:
        resp = ec2.describe_regions(Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}])
        return [r["RegionName"] for r in resp.get("Regions", [])]
    except ClientError:
        return ["us-east-1", "us-west-2", "eu-west-1"]


# ─────────────────────────────────────────────────────────────────────────────
# COLLECTORS
# ─────────────────────────────────────────────────────────────────────────────

def collect_eks(session, region: str) -> List[Dict]:
    rows = []
    try:
        eks = session.client("eks", region_name=region)
        clusters = eks.list_clusters().get("clusters", [])
        for cname in clusters:
            c = eks.describe_cluster(name=cname).get("cluster", {})
            ngs = eks.list_nodegroups(clusterName=cname).get("nodegroups", [])
            node_count = 0
            for ng in ngs:
                ng_detail = eks.describe_nodegroup(clusterName=cname, nodegroupName=ng).get("nodegroup", {})
                node_count += ng_detail.get("scalingConfig", {}).get("desiredSize", 0)
            rows.append({
                "service": "EKS",
                "region": region,
                "name": cname,
                "version": c.get("version", ""),
                "status": c.get("status", ""),
                "node_groups": len(ngs),
                "nodes": node_count,
                "endpoint_public": c.get("resourcesVpcConfig", {}).get("endpointPublicAccess", False),
                "vpc_id": c.get("resourcesVpcConfig", {}).get("vpcId", ""),
                "created_at": c.get("createdAt", "").isoformat() if c.get("createdAt") else "",
                "tags": json.dumps(c.get("tags", {})),
            })
    except ClientError:
        pass
    return rows


def collect_rds(session, region: str) -> List[Dict]:
    rows = []
    try:
        rds = session.client("rds", region_name=region)
        paginator = rds.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                rows.append({
                    "service": "RDS",
                    "region": region,
                    "name": db.get("DBInstanceIdentifier", ""),
                    "engine": db.get("Engine", "") + " " + db.get("EngineVersion", ""),
                    "instance_class": db.get("DBInstanceClass", ""),
                    "status": db.get("DBInstanceStatus", ""),
                    "storage_gb": db.get("AllocatedStorage", 0),
                    "multi_az": db.get("MultiAZ", False),
                    "encrypted": db.get("StorageEncrypted", False),
                    "backup_retention": db.get("BackupRetentionPeriod", 0),
                    "endpoint": db.get("Endpoint", {}).get("Address", ""),
                    "vpc_id": db.get("DBSubnetGroup", {}).get("VpcId", ""),
                    "created_at": db.get("InstanceCreateTime", "").isoformat() if db.get("InstanceCreateTime") else "",
                })
    except ClientError:
        pass
    return rows


def collect_ec2(session, region: str) -> List[Dict]:
    rows = []
    try:
        ec2 = session.client("ec2", region_name=region)
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                    rows.append({
                        "service": "EC2",
                        "region": region,
                        "name": tags.get("Name", ""),
                        "instance_id": inst.get("InstanceId", ""),
                        "instance_type": inst.get("InstanceType", ""),
                        "state": inst.get("State", {}).get("Name", ""),
                        "platform": inst.get("Platform", "linux"),
                        "public_ip": inst.get("PublicIpAddress", ""),
                        "private_ip": inst.get("PrivateIpAddress", ""),
                        "vpc_id": inst.get("VpcId", ""),
                        "az": inst.get("Placement", {}).get("AvailabilityZone", ""),
                        "launch_time": inst.get("LaunchTime", "").isoformat() if inst.get("LaunchTime") else "",
                        "environment": tags.get("Environment", tags.get("Env", "")),
                    })
    except ClientError:
        pass
    return rows


def collect_elb(session, region: str) -> List[Dict]:
    rows = []
    try:
        elb = session.client("elbv2", region_name=region)
        paginator = elb.get_paginator("describe_load_balancers")
        for page in paginator.paginate():
            for lb in page.get("LoadBalancers", []):
                rows.append({
                    "service": "ELB",
                    "region": region,
                    "name": lb.get("LoadBalancerName", ""),
                    "dns_name": lb.get("DNSName", ""),
                    "type": lb.get("Type", ""),
                    "scheme": lb.get("Scheme", ""),
                    "state": lb.get("State", {}).get("Code", ""),
                    "vpc_id": lb.get("VpcId", ""),
                    "created_time": lb.get("CreatedTime", "").isoformat() if lb.get("CreatedTime") else "",
                })
    except ClientError:
        pass
    return rows


def collect_lambda(session, region: str) -> List[Dict]:
    rows = []
    try:
        lmbd = session.client("lambda", region_name=region)
        paginator = lmbd.get_paginator("list_functions")
        for page in paginator.paginate():
            for fn in page.get("Functions", []):
                rows.append({
                    "service": "Lambda",
                    "region": region,
                    "name": fn.get("FunctionName", ""),
                    "runtime": fn.get("Runtime", ""),
                    "memory_mb": fn.get("MemorySize", 0),
                    "timeout_s": fn.get("Timeout", 0),
                    "handler": fn.get("Handler", ""),
                    "code_size_bytes": fn.get("CodeSize", 0),
                    "last_modified": fn.get("LastModified", ""),
                    "description": fn.get("Description", ""),
                })
    except ClientError:
        pass
    return rows


def collect_dynamodb(session, region: str) -> List[Dict]:
    rows = []
    try:
        ddb = session.client("dynamodb", region_name=region)
        paginator = ddb.get_paginator("list_tables")
        for page in paginator.paginate():
            for table_name in page.get("TableNames", []):
                try:
                    t = ddb.describe_table(TableName=table_name).get("Table", {})
                    rows.append({
                        "service": "DynamoDB",
                        "region": region,
                        "name": table_name,
                        "status": t.get("TableStatus", ""),
                        "item_count": t.get("ItemCount", 0),
                        "size_bytes": t.get("TableSizeBytes", 0),
                        "billing_mode": t.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED"),
                        "encryption": t.get("SSEDescription", {}).get("Status", "DISABLED"),
                        "created_at": t.get("CreationDateTime", "").isoformat() if t.get("CreationDateTime") else "",
                    })
                except ClientError:
                    pass
    except ClientError:
        pass
    return rows


def collect_s3(session, region: str) -> List[Dict]:
    rows = []
    if region != "us-east-1":
        return rows
    try:
        s3 = session.client("s3")
        buckets = s3.list_buckets().get("Buckets", [])
        for bucket in buckets:
            name = bucket.get("Name", "")
            bucket_region = "unknown"
            try:
                loc = s3.get_bucket_location(Bucket=name).get("LocationConstraint")
                bucket_region = loc if loc else "us-east-1"
            except ClientError:
                pass

            versioning = "disabled"
            try:
                ver = s3.get_bucket_versioning(Bucket=name)
                versioning = ver.get("Status", "disabled")
            except ClientError:
                pass

            encryption = False
            try:
                s3.get_bucket_encryption(Bucket=name)
                encryption = True
            except ClientError:
                pass

            rows.append({
                "service": "S3",
                "region": bucket_region,
                "name": name,
                "versioning": versioning,
                "encryption": encryption,
                "created_at": bucket.get("CreationDate", "").isoformat() if bucket.get("CreationDate") else "",
            })
    except ClientError:
        pass
    return rows


COLLECTORS = {
    "eks": collect_eks,
    "rds": collect_rds,
    "ec2": collect_ec2,
    "elb": collect_elb,
    "lambda": collect_lambda,
    "dynamodb": collect_dynamodb,
    "s3": collect_s3,
}


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────

def export_csv(inventory: Dict[str, List[Dict]], ts: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    files = []
    for service, rows in inventory.items():
        if not rows:
            continue
        fp = OUTCOME_DIR / f"aws_inventory_{service}_{ts}.csv"
        with open(fp, "w", newline="", encoding="utf-8") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys(), extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
        files.append(fp)
        print(f"  ✅ {service.upper()}: {fp} ({len(rows)} recursos)")
    return files


def export_excel(inventory: Dict[str, List[Dict]], ts: str):
    if not PANDAS_AVAILABLE:
        print("ERROR: pandas y openpyxl son necesarios para Excel. Ejecute: pip install pandas openpyxl")
        export_csv(inventory, ts)
        return

    OUTCOME_DIR.mkdir(exist_ok=True)
    fp = OUTCOME_DIR / f"aws_inventory_{ts}.xlsx"

    with pd.ExcelWriter(fp, engine="openpyxl") as writer:
        summary_rows = []
        for service, rows in inventory.items():
            if rows:
                df = pd.DataFrame(rows)
                sheet_name = service.upper()[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                summary_rows.append({
                    "Servicio": service.upper(),
                    "Recursos": len(rows),
                    "Regiones": df["region"].nunique() if "region" in df.columns else 1,
                })
                print(f"  ✅ {service.upper()}: {len(rows)} recursos → tab '{sheet_name}'")

        if summary_rows:
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="RESUMEN", index=False)

    print(f"\n✅ Excel exportado: {fp}")


def export_json(inventory: Dict[str, List[Dict]], ts: str):
    OUTCOME_DIR.mkdir(exist_ok=True)
    fp = OUTCOME_DIR / f"aws_inventory_{ts}.json"
    with open(fp, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "inventory": inventory,
        }, f, indent=2, default=str)
    print(f"\n✅ JSON exportado: {fp}")


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def display_summary_rich(inventory: Dict[str, List[Dict]]):
    table = Table(
        title="📦 AWS Inventory Summary",
        header_style="bold white on blue",
        show_lines=True,
    )
    table.add_column("Servicio", style="cyan", width=12)
    table.add_column("Total", justify="right", width=8)
    table.add_column("Regiones", justify="right", width=10)
    table.add_column("Desglose", min_width=30)

    for service, rows in inventory.items():
        count = len(rows)
        if count == 0:
            continue
        regions = set(r.get("region", "—") for r in rows)
        region_str = ", ".join(sorted(regions)) if len(regions) <= 3 else f"{len(regions)} regiones"
        table.add_row(service.upper(), str(count), str(len(regions)), region_str)

    console.print(table)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    start_time = time.time()
    args = get_args()

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold cyan]AWS Inventory Generator[/bold cyan]\n"
            f"Profile: [yellow]{args.profile}[/yellow] | Region: [yellow]{args.region}[/yellow] | "
            f"Output: [yellow]{args.output}[/yellow]",
            title="📦 Inventory"
        ))
    else:
        print(f"AWS Inventory Generator | Profile: {args.profile} | Region: {args.region}")

    session = get_session(args.profile, args.region)
    services = [s.strip().lower() for s in args.services.split(",") if s.strip() in COLLECTORS]

    if not services:
        print(f"ERROR: Servicios inválidos. Use: {', '.join(SUPPORTED_SERVICES)}")
        sys.exit(1)

    regions = get_all_regions(session) if args.all_regions else [args.region]

    if RICH_AVAILABLE:
        console.print(f"[dim]Servicios: {', '.join(services)} | Regiones: {', '.join(regions[:5])}{'...' if len(regions) > 5 else ''}[/dim]\n")

    inventory: Dict[str, List[Dict]] = {s: [] for s in services}

    tasks = [(service, region) for service in services for region in regions]

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task(f"Recopilando inventario...", total=len(tasks))
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {
                    executor.submit(COLLECTORS[svc], session, reg): (svc, reg)
                    for svc, reg in tasks
                }
                for future in as_completed(futures):
                    svc, reg = futures[future]
                    try:
                        rows = future.result()
                        inventory[svc].extend(rows)
                    except Exception as e:
                        if args.debug:
                            console.print(f"[red]  ✗ {svc}/{reg}: {e}[/red]")
                    progress.advance(task)
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(COLLECTORS[svc], session, reg): (svc, reg)
                for svc, reg in tasks
            }
            for future in as_completed(futures):
                svc, reg = futures[future]
                try:
                    rows = future.result()
                    inventory[svc].extend(rows)
                    print(f"  ✓ {svc}/{reg}: {len(rows)} recursos")
                except Exception as e:
                    pass

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if RICH_AVAILABLE:
        display_summary_rich(inventory)

    if args.output == "csv":
        export_csv(inventory, ts)
    elif args.output == "excel":
        export_excel(inventory, ts)
    elif args.output == "json":
        export_json(inventory, ts)

    elapsed = time.time() - start_time
    m, s = divmod(int(elapsed), 60)
    time_str = f"{m}m {s}s" if m else f"{s}s"
    total = sum(len(v) for v in inventory.values())

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold]Total recursos:[/bold] [green]{total}[/green]\n"
            f"[bold]Servicios:[/bold] [cyan]{len([s for s in inventory if inventory[s]])}[/cyan] | "
            f"[bold]Regiones:[/bold] [cyan]{len(regions)}[/cyan]\n"
            f"[bold]Tiempo:[/bold] [cyan]{time_str}[/cyan]",
            title="📊 Resumen Final"
        ))
    else:
        print(f"\nTotal: {total} recursos | {time_str}")


if __name__ == "__main__":
    main()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def export_results(data, output_format: str = "json", output_dir: str = "outcome"):
    """Exporta resultados usando ExportManager centralizado con fallback."""
    
    from pathlib import Path
    import json
    import csv
    from datetime import datetime
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual
        if output_format == "json":
            filepath = output_path / f"aws_inventory_generator_{ts}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": data}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"aws_inventory_generator_{ts}.csv"
            if isinstance(data, list) and data and isinstance(data[0], dict):
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            return None
        
        print(f"✅ Resultados exportados a: {filepath}")
        return str(filepath)
    
    # Usar ExportManager
    manager = ExportManager("aws_inventory_generator", "1.0.0")
    
    summary = {"total_items": len(data) if isinstance(data, list) else 1}
    
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    
    return None

