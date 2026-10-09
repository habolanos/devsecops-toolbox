#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS ECR Image Filter — Tool 29

Filtra imágenes de repositorios ECR y exporta a Excel/CSV/JSON:

- Lista repositorios ECR y sus imágenes (tag, digest, pushedAt, size)
- Filtro de tags por patrón semver (`N.N.N-xxx`) excluyendo
  `-master`/`latest` (comportamiento heredado del tag_filter GCP)
- Modo alternativo: filtra un CSV existente (`--csv-file`)
- Ordena por fecha de push descendente
- Export Excel (openpyxl/pandas), CSV o JSON a outcome/

Equivalente a GCP Tool: artifact-registry/tag_filter.py.

Uso:
    python aws_ecr_image_filter.py --profile p --region us-east-1
    python aws_ecr_image_filter.py --csv-file imagenes.csv -o excel
    python aws_ecr_image_filter.py --repository my-repo -o csv
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

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

# Patrón semver heredado del filtro GCP: 1.2.3-env (sin -master)
SEMVER_PATTERN = re.compile(r"^\d+(\.\d+)*-[a-zA-Z]+$")
EXCLUDE_TAG_PATTERNS = re.compile(r"(-master|^latest$)", re.IGNORECASE)


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Filtro
# ═══════════════════════════════════════════════════════════════════════════════

def keep_tag(tag: str, semver_only: bool = True,
             custom: Optional[re.Pattern] = None) -> bool:
    if EXCLUDE_TAG_PATTERNS.search(tag):
        return False
    if custom and custom.search(tag):
        return False
    if semver_only and not SEMVER_PATTERN.match(tag):
        return False
    return True


def filter_tags(tags: List[str],
                semver_only: bool = True,
                exclude_pattern: str = "") -> List[str]:
    """Filtra tags: semver N.N.N-env, excluye -master/latest/custom."""
    custom = re.compile(exclude_pattern) if exclude_pattern else None
    return [t for t in tags if keep_tag(t, semver_only, custom)]


# ═══════════════════════════════════════════════════════════════════════════════
# Origen de datos
# ═══════════════════════════════════════════════════════════════════════════════

def collect_from_ecr(session, repo_filter: str = "") -> List[Dict]:
    """Imágenes de todos los repos ECR de la región."""
    ecr = session.client("ecr")
    rows = []
    repos = []
    for page in ecr.get_paginator("describe_repositories").paginate():
        for repo in page.get("repositories", []):
            if repo_filter and repo_filter.lower() not in \
                    repo["repositoryName"].lower():
                continue
            repos.append(repo["repositoryName"])
    for repo in repos:
        for page in ecr.get_paginator("describe_images").paginate(
                repositoryName=repo,
                filter={"tagStatus": "TAGGED"}):
            for img in page.get("imageDetails", []):
                for tag in img.get("imageTags", []):
                    rows.append({
                        "repository": repo,
                        "tag": tag,
                        "digest": (img.get("imageDigest") or "")[:19],
                        "pushed_at": str(img.get("imagePushedAt", "")),
                        "size_mb": round(
                            (img.get("imageSizeInBytes") or 0)
                            / 1048576, 1),
                    })
    return rows


def collect_from_csv(csv_file: str) -> List[Dict]:
    """Lee un CSV existente (columnas flexibles: repo/image/tag/date)."""
    rows = []
    with open(csv_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = {k.strip().lower(): v
                          for k, v in row.items() if k}
            rows.append({
                "repository": (normalized.get("repository")
                               or normalized.get("repo")
                               or normalized.get("repositorio") or ""),
                "tag": (normalized.get("tag")
                        or normalized.get("version") or ""),
                "digest": normalized.get("digest", ""),
                "pushed_at": (normalized.get("pushed_at")
                              or normalized.get("fecha_creacion")
                              or normalized.get("date") or ""),
                "size_mb": normalized.get("size_mb", ""),
            })
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════════════

def export_rows(rows: List[Dict], fmt: str, base_name: str) -> Path:
    OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if fmt == "json":
        out = OUTCOME_DIR / f"{base_name}_{ts}.json"
        out.write_text(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(rows), "images": rows}, indent=2),
            encoding="utf-8")
        return out
    if fmt == "excel":
        out = OUTCOME_DIR / f"{base_name}_{ts}.xlsx"
        if PANDAS_AVAILABLE:
            df = pd.DataFrame(rows)
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Imagenes", index=False)
        else:
            _print("⚠ pandas/openpyxl no disponible — "
                   "exportando CSV", "yellow")
            out = out.with_suffix(".csv")
            _write_csv(rows, out)
        return out
    out = OUTCOME_DIR / f"{base_name}_{ts}.csv"
    _write_csv(rows, out)
    return out


def _write_csv(rows: List[Dict], out: Path):
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "repository", "tag", "digest", "pushed_at", "size_mb"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in w.fieldnames})


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Filtra imágenes ECR y exporta a Excel/CSV/JSON")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--repository", default="",
                        help="Filtrar repositorios por nombre")
    parser.add_argument("--csv-file", default="",
                        help="Filtrar un CSV existente en vez de ECR")
    parser.add_argument("--all-tags", action="store_true",
                        help="No aplicar filtro semver (todos los tags)")
    parser.add_argument("--exclude", default="",
                        help="Regex adicional de tags a excluir")
    parser.add_argument("-o", "--output",
                        choices=["excel", "csv", "json"],
                        default="excel")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = get_args()

    if args.csv_file:
        csv_path = Path(args.csv_file)
        if not csv_path.is_file():
            _print(f"❌ CSV no encontrado: {csv_path}", "red")
            sys.exit(1)
        rows = collect_from_csv(str(csv_path))
        source = f"CSV {csv_path.name}"
    else:
        if not BOTO3_AVAILABLE:
            _print("❌ boto3 no instalado (o usa --csv-file)", "red")
            sys.exit(1)
        try:
            session = boto3.Session(profile_name=args.profile,
                                    region_name=args.region)
            rows = collect_from_ecr(session, args.repository)
        except Exception as e:
            _print(f"❌ Error consultando ECR: {e}", "red")
            sys.exit(1)
        source = f"ECR {args.profile}@{args.region}"

    total = len(rows)
    custom_re = re.compile(args.exclude) if args.exclude else None
    filtered = [r for r in rows
                if keep_tag(r["tag"], not args.all_tags, custom_re)]
    filtered.sort(key=lambda r: r.get("pushed_at") or "",
                  reverse=True)

    if console:
        console.print(Panel.fit(
            f"Origen: [yellow]{source}[/yellow]\n"
            f"Tags totales: {total} → filtrados: "
            f"[green]{len(filtered)}[/green]",
            title="📦 ECR Image Filter"))
        if filtered:
            table = Table(header_style="bold cyan")
            for col in ["Repo", "Tag", "Pushed", "MB"]:
                table.add_column(col)
            for r in filtered[:30]:
                table.add_row(r["repository"][:35], r["tag"],
                              str(r.get("pushed_at", ""))[:16],
                              str(r.get("size_mb", "")))
            console.print(table)
            if len(filtered) > 30:
                console.print(f"[dim]... y {len(filtered) - 30} más "
                              f"(ver export)[/dim]")
    else:
        print(f"{source}: {total} → {len(filtered)} tags")
        for r in filtered[:20]:
            print(f"  {r['repository']}:{r['tag']}")

    out = export_rows(filtered, args.output, "ecr_images_filtered")
    _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
