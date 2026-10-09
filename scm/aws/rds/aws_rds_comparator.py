#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS RDS Comparator — Tool 23

Compara instancias RDS entre dos regiones (o cuentas vía profiles):

- Lista todas las instancias de ambos orígenes
- Las empareja por DBInstanceIdentifier
- Compara atributos clave: engine, versión, clase, storage, Multi-AZ,
  backups, cifrado, acceso público
- Tabla comparativa con semáforos (✅ igual / ⛔ difiere / 🚧 solo en un lado)

Equivalente a GCP Tool: Cloud SQL Comparator (cloud-sql/gcp_sql_comparator.py).

Uso:
    python aws_rds_comparator.py --profile p --region1 us-east-1 \\
        --region2 us-west-2 -o json
    python aws_rds_comparator.py --region1 us-east-1 --region2 us-west-2 \\
        --instance my-db --all-attributes
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Consolas Windows (cp1252): permitir salida Unicode
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p
# -------------------------------------------------------------------

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "DevSecOps Team"

OUTCOME_DIR = get_output_dir("outcome")
console = Console() if RICH_AVAILABLE else None

# Atributos comparados por defecto (con --all-attributes se usa todo)
DEFAULT_ATTRIBUTES = [
    "engine", "engine_version", "instance_class", "allocated_storage",
    "multi_az", "backup_retention", "encrypted", "publicly_accessible",
    "auto_minor_upgrade", "deletion_protection",
]

ALL_ATTRIBUTES = DEFAULT_ATTRIBUTES + [
    "storage_type", "storage_encrypted", "iops", "port",
    "preferred_backup_window", "preferred_maintenance_window",
    "vpc_id", "db_subnet_group", "parameter_group",
    "performance_insights", "monitoring_interval", "copy_tags_to_snapshot",
]


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Extracción
# ═══════════════════════════════════════════════════════════════════════════════

def make_session(profile: str, region: str):
    if not BOTO3_AVAILABLE:
        raise RuntimeError("boto3 no instalado")
    return boto3.Session(profile_name=profile, region_name=region)


def list_db_instances(profile: str, region: str) -> Dict[str, Dict]:
    """{DBInstanceIdentifier: raw_instance} para una región/profile."""
    rds = make_session(profile, region).client("rds")
    instances = {}
    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for inst in page.get("DBInstances", []):
            instances[inst["DBInstanceIdentifier"]] = inst
    return instances


def extract_attributes(inst: Dict) -> Dict[str, Any]:
    """Normaliza una instancia RDS a atributos comparables."""
    pg = inst.get("DBParameterGroups", [{}])
    return {
        "engine": inst.get("Engine"),
        "engine_version": inst.get("EngineVersion"),
        "instance_class": inst.get("DBInstanceClass"),
        "allocated_storage": inst.get("AllocatedStorage"),
        "storage_type": inst.get("StorageType"),
        "iops": inst.get("Iops"),
        "multi_az": inst.get("MultiAZ"),
        "publicly_accessible": inst.get("PubliclyAccessible"),
        "encrypted": inst.get("StorageEncrypted"),
        "storage_encrypted": inst.get("StorageEncrypted"),
        "backup_retention": inst.get("BackupRetentionPeriod"),
        "auto_minor_upgrade": inst.get("AutoMinorVersionUpgrade"),
        "deletion_protection": inst.get("DeletionProtection"),
        "port": (inst.get("Endpoint") or {}).get("Port"),
        "preferred_backup_window": inst.get("PreferredBackupWindow"),
        "preferred_maintenance_window":
            inst.get("PreferredMaintenanceWindow"),
        "vpc_id": (inst.get("DBSubnetGroup") or {}).get("VpcId"),
        "db_subnet_group": (inst.get("DBSubnetGroup") or {})
            .get("DBSubnetGroupName"),
        "parameter_group": pg[0].get("DBParameterGroupName") if pg else None,
        "performance_insights":
            inst.get("PerformanceInsightsEnabled", False),
        "monitoring_interval": inst.get("MonitoringInterval", 0),
        "copy_tags_to_snapshot": inst.get("CopyTagsToSnapshot", False),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Comparación
# ═══════════════════════════════════════════════════════════════════════════════

def compare_instance(attrs1: Dict, attrs2: Dict,
                     attributes: List[str]) -> Dict:
    """Compara atributo a atributo. Retorna detalle + estado."""
    diffs, matches = [], []
    for attr in attributes:
        v1, v2 = attrs1.get(attr), attrs2.get(attr)
        if v1 == v2:
            matches.append({"attribute": attr, "value": v1})
        else:
            diffs.append({"attribute": attr, "region1": v1,
                          "region2": v2})
    if not diffs:
        status = "MATCH"
    elif any(d["attribute"] == "engine_version" for d in diffs):
        status = "VERSION_DIFFERS"
    else:
        status = "DIFFERS"
    return {"status": status, "differences": diffs, "matches": matches}


def compare_all(instances1: Dict[str, Dict], instances2: Dict[str, Dict],
                attributes: List[str],
                only_instance: Optional[str] = None) -> List[Dict]:
    """Empareja por DBInstanceIdentifier y compara."""
    names = sorted(set(instances1) | set(instances2))
    if only_instance:
        names = [n for n in names if n == only_instance]
    results = []
    for name in names:
        i1, i2 = instances1.get(name), instances2.get(name)
        row = {"instance": name}
        if i1 and i2:
            comp = compare_instance(extract_attributes(i1),
                                    extract_attributes(i2), attributes)
            row.update({
                "presence": "BOTH",
                "status": comp["status"],
                "differences": comp["differences"],
                "matches": comp["matches"],
                "engine1": i1.get("Engine"),
                "version1": i1.get("EngineVersion"),
                "engine2": i2.get("Engine"),
                "version2": i2.get("EngineVersion"),
            })
        else:
            row.update({
                "presence": "ONLY_REGION1" if i1 else "ONLY_REGION2",
                "status": "MISSING",
                "differences": [],
                "matches": [],
                "engine1": (i1 or {}).get("Engine"),
                "version1": (i1 or {}).get("EngineVersion"),
                "engine2": (i2 or {}).get("Engine"),
                "version2": (i2 or {}).get("EngineVersion"),
            })
        results.append(row)
    return results


STATUS_EMOJI = {"MATCH": "✅", "DIFFERS": "⛔", "VERSION_DIFFERS": "🚧",
                "MISSING": "⚠️"}


def print_results(results: List[Dict], label1: str, label2: str,
                  show_diffs: bool = True):
    if console:
        table = Table(title="Comparación de instancias RDS",
                      header_style="bold cyan")
        for col in ["Instancia", "Presencia", f"Versión {label1}",
                    f"Versión {label2}", "Estado", "Diffs"]:
            table.add_column(col)
        for r in results:
            status = r["status"]
            table.add_row(
                r["instance"], r["presence"],
                str(r.get("version1") or "—"),
                str(r.get("version2") or "—"),
                f"{STATUS_EMOJI.get(status, '?')} {status}",
                str(len(r["differences"])))
        console.print(table)

        if show_diffs:
            for r in results:
                if r["differences"]:
                    console.print(f"\n[bold]{r['instance']}[/bold] "
                                  "— diferencias:")
                    for d in r["differences"]:
                        console.print(
                            f"  [yellow]{d['attribute']}[/yellow]: "
                            f"{d['region1']!r} ↔ {d['region2']!r}")
        match = len([r for r in results if r["status"] == "MATCH"])
        diff = len([r for r in results if r["status"] != "MATCH"])
        console.print(f"\n✅ Iguales: {match} | ⛔/⚠️ Diferentes: {diff}")
    else:
        for r in results:
            print(f"{r['instance']}: {r['presence']} {r['status']} "
                  f"({len(r['differences'])} diffs)")
            for d in r["differences"]:
                print(f"   {d['attribute']}: {d['region1']!r} "
                      f"↔ {d['region2']!r}")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Compara instancias RDS entre regiones/cuentas")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--profile2", default="",
                        help="Profile del segundo origen (vacío = mismo)")
    parser.add_argument("--region1", default="us-east-1")
    parser.add_argument("--region2", default="us-west-2")
    parser.add_argument("--instance", "-i", default="",
                        help="Comparar solo esta instancia")
    parser.add_argument("--all-attributes", action="store_true",
                        help="Comparar todos los atributos")
    parser.add_argument("--attributes", default="",
                        help="CSV de atributos específicos")
    parser.add_argument("-o", "--output", choices=["json", "csv"],
                        default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = get_args()
    profile2 = args.profile2 or args.profile

    attributes = DEFAULT_ATTRIBUTES
    if args.all_attributes:
        attributes = ALL_ATTRIBUTES
    if args.attributes:
        attributes = [a.strip() for a in args.attributes.split(",")
                      if a.strip()]

    label1 = f"{args.profile}@{args.region1}"
    label2 = f"{profile2}@{args.region2}"

    if console:
        console.print(Panel.fit(
            f"[bold cyan]RDS Comparator[/bold cyan]\n"
            f"Origen 1: [yellow]{label1}[/yellow]\n"
            f"Origen 2: [yellow]{label2}[/yellow]",
            title="💾 Comparación"))
    else:
        print(f"RDS Comparator: {label1} ↔ {label2}")

    try:
        with console.status("[cyan]Consultando origen 1...") \
                if console else _nullctx():
            instances1 = list_db_instances(args.profile, args.region1)
        with console.status("[cyan]Consultando origen 2...") \
                if console else _nullctx():
            instances2 = list_db_instances(profile2, args.region2)
    except Exception as e:
        _print(f"❌ Error consultando AWS: {e}", "red")
        sys.exit(1)

    _print(f"Origen 1: {len(instances1)} instancias | "
           f"Origen 2: {len(instances2)} instancias", "dim")

    results = compare_all(instances1, instances2, attributes,
                          args.instance or None)
    if not results:
        _print("⚠ Sin instancias para comparar", "yellow")
        sys.exit(0)

    print_results(results, label1, label2)

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"rds_comparison_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "source1": label1, "source2": label2,
                "timestamp": datetime.utcnow().isoformat(),
                "results": results,
            }, indent=2, default=str), encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "instance", "presence", "status", "version1",
                    "version2", "diff_count", "diff_attributes"])
                w.writeheader()
                for r in results:
                    w.writerow({
                        "instance": r["instance"],
                        "presence": r["presence"],
                        "status": r["status"],
                        "version1": r.get("version1"),
                        "version2": r.get("version2"),
                        "diff_count": len(r["differences"]),
                        "diff_attributes": ";".join(
                            d["attribute"] for d in r["differences"]),
                    })
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if any(r["status"] != "MATCH" for r in results) else 0)


from contextlib import contextmanager


@contextmanager
def _nullctx():
    yield


if __name__ == "__main__":
    main()
