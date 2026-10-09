#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure ACR Image Filter — Tool 28

Filtra y exporta imágenes de Azure Container Registry,
equivalente a artifact-registry/tag_filter (GCP) /
aws_ecr_image_filter:

- Repositorios de un ACR → tags con metadatos
- Filtro semver ('>=1.2.0', '<2.0.0', '=1.4.2') o regex libre
- Entrada alternativa: CSV local con columna `tag`
- Export CSV/JSON/Excel (si pandas+openpyxl disponibles)

Uso:
    python azure_acr_image_filter.py --registry myacr --filter ">=1.2.0"
    python azure_acr_image_filter.py --csv-file images.csv -o csv
"""

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, now_ts, export_json, export_csv)

__version__ = "1.0.0"

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+).*$")
OPS = (">=", "<=", "!=", "=", ">", "<")


def parse_semver(tag: str):
    m = SEMVER_RE.match(tag)
    if not m:
        return None
    return tuple(int(g) for g in m.groups())


def _split_filter(flt: str):
    """'>=1.2.0' → ('>=', '1.2.0'); 'prod.*' → (None, 'prod.*')."""
    flt = flt.strip()
    for op in OPS:
        if flt.startswith(op):
            return op, flt[len(op):].strip()
    return None, flt


def matches_filter(tag: str, flt: str) -> bool:
    op, val = _split_filter(flt)
    if op is None:
        try:
            return bool(re.search(val, tag))
        except re.error:
            return val in tag
    tv, vv = parse_semver(tag), parse_semver(val)
    if tv is None or vv is None:
        return False
    return {">=": tv >= vv, "<=": tv <= vv,
            ">": tv > vv, "<": tv < vv,
            "=": tv == vv, "!=": tv != vv}[op]


def list_images(sub: str, registry: str) -> List[Dict]:
    """Repos y tags del ACR vía az."""
    repos = try_az(["acr", "repository", "list",
                    "--name", registry], sub, default=[]) or []
    images = []
    for repo in repos:
        tags = try_az(["acr", "repository", "show-tags",
                       "--name", registry, "--repository",
                       repo, "--detail",
                       "--orderby", "time_desc"], sub,
                      default=[]) or []
        for t in tags:
            images.append({
                "registry": registry, "repository": repo,
                "tag": t.get("name"),
                "digest": (t.get("digest") or "")[:19],
                "created": (t.get("createdTime") or "")[:19],
                "last_update": (t.get(
                    "lastUpdateTime") or "")[:19],
                "size_mb": round((t.get("imageSize") or 0)
                                 / 1024 / 1024, 1)
                if t.get("imageSize") else None,
            })
    return images


def load_csv_tags(path: str) -> List[Dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tag = r.get("tag") or r.get("Tag") or \
                r.get("name") or ""
            rows.append({"registry": r.get("registry", ""),
                         "repository": r.get(
                             "repository") or
                             r.get("Repository") or "",
                         "tag": tag,
                         "created": r.get("created") or
                         r.get("Created") or "",
                         "size_mb": r.get("size_mb") or
                         r.get("size") or ""})
    return rows


def export_excel(path: Path, rows: List[Dict]) -> bool:
    try:
        import pandas as pd
        pd.DataFrame(rows).to_excel(path, index=False)
        return True
    except Exception:
        return False


def get_args():
    p = argparse.ArgumentParser(
        description="Filtra imágenes ACR por tag")
    p.add_argument("--subscription", default="")
    p.add_argument("--registry", "-r", default="")
    p.add_argument("--filter", "-f", default="",
                   help="Filtro semver ('>=1.2.0') o regex")
    p.add_argument("--csv-file", default="",
                   help="CSV de entrada alternativo")
    p.add_argument("-o", "--output",
                   choices=["json", "csv", "excel"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if args.csv_file:
        images = load_csv_tags(args.csv_file)
    else:
        if not az_available():
            _print("❌ az CLI no disponible o sin login",
                   "red")
            sys.exit(1)
        if not args.registry:
            _print("❌ --registry requerido (o --csv-file)",
                   "red")
            sys.exit(1)
        sub = resolve_subscription(args.subscription)
        images = list_images(sub, args.registry)

    filtered = [i for i in images
                if not args.filter or
                matches_filter(i.get("tag") or "", args.filter)]
    filtered.sort(key=lambda i: (
        i["repository"], -(parse_semver(i["tag"] or "")
                           or (0,))[0]
        if parse_semver(i["tag"] or "") else 0,
        i["tag"] or ""))

    if console:
        from rich.table import Table
        table = Table(title=f"ACR Images — "
                            f"{args.filter or 'all'}",
                      header_style="bold cyan")
        for col in ["Repo", "Tag", "Creado", "MB"]:
            table.add_column(col)
        for i in filtered[:50]:
            table.add_row(i["repository"][:35],
                          i["tag"][:30],
                          (i.get("created") or "")[:10],
                          str(i.get("size_mb") or "—"))
        console.print(table)
    else:
        for i in filtered[:50]:
            print(f"{i['repository']}:{i['tag']}")

    _print(f"\nImágenes: {len(images)} | filtradas: "
           f"{len(filtered)}", "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ext = "xlsx" if args.output == "excel" else args.output
        out = OUTCOME_DIR / f"acr_images_{now_ts()}.{ext}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                "filter": args.filter, "images": filtered})
        elif args.output == "excel":
            if not export_excel(out, filtered):
                out = out.with_suffix(".csv")
                export_csv(out, ["registry", "repository",
                                 "tag", "created", "size_mb"],
                           filtered)
                _print("⚠ pandas/openpyxl no disponibles — "
                       "exportado como CSV", "yellow")
        else:
            export_csv(out, ["registry", "repository", "tag",
                             "digest", "created", "size_mb"],
                       filtered)
        _print(f"✓ Exportado a: {out}", "green")


if __name__ == "__main__":
    main()
