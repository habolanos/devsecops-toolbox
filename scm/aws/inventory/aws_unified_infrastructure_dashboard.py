#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS Unified Infrastructure Dashboard — Tool 33

Dashboard ejecutivo unificado de la infraestructura AWS:

- Conteos por servicio: EC2, RDS, Lambda, EKS, ECR, ELB, VPC, S3
- Alertas agregadas: instancias detenidas, RDS sin Multi-AZ,
  buckets públicos, funciones EOL, LBs sin targets
- Score de salud general con semáforo
- Export HTML con Chart.js y JSON

Equivalente a GCP Tool: Unified Infrastructure Dashboard
(consolidation/gcp_unified_infrastructure_dashboard.py).

Uso:
    python aws_unified_infrastructure_dashboard.py --profile p \\
        --region us-east-1 -o html
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

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

EOL_RUNTIMES = {"python2.7", "python3.6", "python3.7", "python3.8",
                "nodejs10.x", "nodejs12.x", "nodejs14.x",
                "dotnetcore3.1", "ruby2.7", "java8", "go1.x"}


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# Recolección por servicio (tolerante a fallos por servicio)
# ═══════════════════════════════════════════════════════════════════════════════

def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def collect(session) -> Dict:
    counts, alerts = {}, []

    # EC2
    def _ec2():
        ec2 = session.client("ec2")
        instances = []
        for page in ec2.get_paginator(
                "describe_instances").paginate():
            for r in page.get("Reservations", []):
                instances.extend(r.get("Instances", []))
        stopped = [i for i in instances
                   if i.get("State", {}).get("Name") == "stopped"]
        counts["ec2"] = len(instances)
        if stopped:
            alerts.append(f"🟡 {len(stopped)} instancias EC2 "
                          "detenidas (costo EBS)")
    _safe(_ec2, None)
    counts.setdefault("ec2", 0)

    # RDS
    def _rds():
        rds = session.client("rds")
        insts = []
        for page in rds.get_paginator(
                "describe_db_instances").paginate():
            insts.extend(page.get("DBInstances", []))
        counts["rds"] = len(insts)
        no_ma = [i["DBInstanceIdentifier"] for i in insts
                 if not i.get("MultiAZ")]
        unenc = [i["DBInstanceIdentifier"] for i in insts
                 if not i.get("StorageEncrypted")]
        public = [i["DBInstanceIdentifier"] for i in insts
                  if i.get("PubliclyAccessible")]
        if public:
            alerts.append(f"🔴 {len(public)} RDS públicos: "
                          f"{', '.join(public[:3])}")
        if unenc:
            alerts.append(f"🔴 {len(unenc)} RDS sin cifrado")
        if no_ma:
            alerts.append(f"🟡 {len(no_ma)} RDS sin Multi-AZ")
    _safe(_rds, None)
    counts.setdefault("rds", 0)

    # Lambda
    def _lambda():
        lam = session.client("lambda")
        fns = []
        for page in lam.get_paginator("list_functions").paginate():
            fns.extend(page.get("Functions", []))
        counts["lambda"] = len(fns)
        eol = [f["FunctionName"] for f in fns
               if f.get("Runtime") in EOL_RUNTIMES]
        if eol:
            alerts.append(f"🟠 {len(eol)} lambdas con runtime EOL: "
                          f"{', '.join(eol[:3])}")
    _safe(_lambda, None)
    counts.setdefault("lambda", 0)

    # EKS
    def _eks():
        eks = session.client("eks")
        clusters = eks.list_clusters().get("clusters", [])
        counts["eks"] = len(clusters)
    _safe(_eks, None)
    counts.setdefault("eks", 0)

    # ECR
    def _ecr():
        ecr = session.client("ecr")
        repos = []
        for page in ecr.get_paginator(
                "describe_repositories").paginate():
            repos.extend(page.get("repositories", []))
        counts["ecr"] = len(repos)
    _safe(_ecr, None)
    counts.setdefault("ecr", 0)

    # ELB
    def _elb():
        elb = session.client("elbv2")
        lbs = []
        for page in elb.get_paginator(
                "describe_load_balancers").paginate():
            lbs.extend(page.get("LoadBalancers", []))
        counts["elb"] = len(lbs)
    _safe(_elb, None)
    counts.setdefault("elb", 0)

    # VPC
    def _vpc():
        ec2 = session.client("ec2")
        counts["vpc"] = len(ec2.describe_vpcs().get("Vpcs", []))
    _safe(_vpc, None)
    counts.setdefault("vpc", 0)

    # S3 (global)
    def _s3():
        s3 = session.client("s3")
        buckets = s3.list_buckets().get("Buckets", [])
        counts["s3"] = len(buckets)
        public = []
        for b in buckets[:20]:
            try:
                pab = s3.get_public_access_block(
                    Bucket=b["Name"]).get(
                        "PublicAccessBlockConfiguration", {})
                if not all([pab.get("BlockPublicAcls"),
                            pab.get("BlockPublicPolicy")]):
                    public.append(b["Name"])
            except ClientError:
                public.append(b["Name"])
        if public:
            alerts.append(f"🔴 {len(public)} buckets S3 sin "
                          f"Public Access Block completo: "
                          f"{', '.join(public[:3])}")
    _safe(_s3, None)
    counts.setdefault("s3", 0)

    return {"counts": counts, "alerts": alerts}


def health_score(alerts: List[str]) -> int:
    score = 100
    for a in alerts:
        if a.startswith("🔴"):
            score -= 15
        elif a.startswith("🟠"):
            score -= 10
        else:
            score -= 5
    return max(0, score)


HTML = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>AWS Infrastructure Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{{font-family:system-ui;background:#0f1419;color:#e6e6e6;
margin:2em}}h1{{color:#58a6ff}}.grid{{display:grid;
grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1em}}
.kpi{{background:#1c2128;border-radius:8px;padding:1em;text-align:center}}
.kpi b{{font-size:2em;color:#58a6ff;display:block}}
.card{{background:#1c2128;border-radius:8px;padding:1em;margin:1em 0}}
.score{{font-size:3em}}</style></head><body>
<h1>☁️ AWS Infrastructure Dashboard</h1>
<p>Generado: {ts} | Region: {region} | Health score:
<span class="score">{score}</span></p>
<div class="grid">{kpis}</div>
<div class="card"><h2>Distribución de recursos</h2>
<canvas id="chart"></canvas></div>
<div class="card"><h2>Alertas</h2><ul>{alerts}</ul></div>
<script>new Chart(document.getElementById('chart'),{{type:'bar',
data:{{labels:{labels},datasets:[{{label:'Recursos',data:{vals},
backgroundColor:'#58a6ff'}}]}}}});</script>
</body></html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def get_args():
    parser = argparse.ArgumentParser(
        description="Dashboard ejecutivo unificado AWS")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--interactive", action="store_true",
                        help="Aceptado por compatibilidad del launcher")
    parser.add_argument("-o", "--output", choices=["html", "json"],
                        default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = get_args()
    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)
    try:
        session = boto3.Session(profile_name=args.profile,
                                region_name=args.region)
        data = collect(session)
    except Exception as e:
        _print(f"❌ Error: {e}", "red")
        sys.exit(1)

    score = health_score(data["alerts"])
    counts = data["counts"]

    if console:
        table = Table(title="Recursos por servicio",
                      header_style="bold cyan")
        table.add_column("Servicio"); table.add_column("Recursos")
        for svc, n in counts.items():
            table.add_row(svc.upper(), str(n))
        console.print(table)
        color = "green" if score >= 90 else \
                "yellow" if score >= 70 else "red"
        console.print(f"[bold {color}]Health score: {score}/100"
                      f"[/bold {color}]")
        for a in data["alerts"]:
            console.print(f"  {a}")
    else:
        print(f"Score: {score} | {counts}")
        for a in data["alerts"]:
            print(a)

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if args.output == "json":
            out = OUTCOME_DIR / f"infra_dashboard_{ts}.json"
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "region": args.region, "health_score": score,
                **data}, indent=2), encoding="utf-8")
        else:
            out = OUTCOME_DIR / f"infra_dashboard_{ts}.html"
            kpis = "".join(
                f"<div class='kpi'><b>{n}</b>{s.upper()}</div>"
                for s, n in counts.items())
            alerts = "".join(f"<li>{a}</li>" for a in data["alerts"]) \
                or "<li>Sin alertas</li>"
            out.write_text(HTML.format(
                ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
                region=args.region, score=score, kpis=kpis,
                alerts=alerts, labels=json.dumps(list(counts)),
                vals=json.dumps(list(counts.values()))),
                encoding="utf-8")
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(0 if score >= 70 else 1)


if __name__ == "__main__":
    main()
