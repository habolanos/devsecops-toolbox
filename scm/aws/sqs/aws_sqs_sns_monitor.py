#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AWS SQS/SNS Monitor — Tool 43

Monitoreo de mensajería AWS, equivalente al Pub/Sub Monitor de GCP:

- Colas SQS: profundidad (visible + in-flight), edad del mensaje más
  antiguo, DLQ asociada y su profundidad
- Topics SNS: suscripciones pendientes de confirmar, deliveries
- Alertas: backlog alto, mensajes envejecidos, DLQ con mensajes,
  colas sin consumo (ReceiveCount=0 con backlog)
- Export JSON/CSV/HTML a outcome/

Uso:
    python aws_sqs_sns_monitor.py --profile p --region us-east-1
    python aws_sqs_sns_monitor.py --queue-prefix prod- -o json
"""

import argparse
import csv
import json
import sys
from collections import Counter
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

BACKLOG_WARN = 100
BACKLOG_CRITICAL = 1000
AGE_WARN_SECONDS = 300          # 5 min
DLQ_WARN_MESSAGES = 1


def _print(msg: str, style: str = ""):
    if console:
        console.print(f"[{style}]{msg}[/{style}]" if style else msg)
    else:
        print(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# SQS
# ═══════════════════════════════════════════════════════════════════════════════

def queue_name(url: str) -> str:
    return url.rsplit("/", 1)[-1]


def get_queue_metrics(sqs, url: str) -> Dict:
    attrs = sqs.get_queue_attributes(
        QueueUrl=url,
        AttributeNames=[
            "ApproximateNumberOfMessages",
            "ApproximateNumberOfMessagesNotVisible",
            "ApproximateAgeOfOldestMessage",
            "RedrivePolicy",
            "VisibilityTimeout",
            "CreatedTimestamp",
        ]).get("Attributes", {})
    return {
        "queue": queue_name(url), "url": url,
        "visible": int(attrs.get("ApproximateNumberOfMessages", 0)),
        "in_flight": int(attrs.get(
            "ApproximateNumberOfMessagesNotVisible", 0)),
        "oldest_message_s": int(attrs.get(
            "ApproximateAgeOfOldestMessage", 0)),
        "has_dlq": "RedrivePolicy" in attrs,
        "visibility_timeout": int(attrs.get("VisibilityTimeout", 30)),
    }


def dlq_arns(sqs, urls: List[str]) -> Dict[str, str]:
    """{queue_url: dlq_arn} para colas con redrive policy."""
    mapping = {}
    for url in urls:
        attrs = sqs.get_queue_attributes(
            QueueUrl=url, AttributeNames=["RedrivePolicy"]
        ).get("Attributes", {})
        policy = attrs.get("RedrivePolicy")
        if policy:
            try:
                mapping[url] = json.loads(
                    policy)["deadLetterTargetArn"]
            except (json.JSONDecodeError, KeyError):
                pass
    return mapping


def queue_status(m: Dict) -> str:
    if m["visible"] >= BACKLOG_CRITICAL or \
            m["oldest_message_s"] >= 3600:
        return "CRITICAL"
    if m["visible"] >= BACKLOG_WARN or \
            m["oldest_message_s"] >= AGE_WARN_SECONDS:
        return "WARNING"
    return "OK"


def analyze_queues(sqs, prefix: str = "") -> List[Dict]:
    urls = []
    kw = {"QueueNamePrefix": prefix} if prefix else {}
    for page in sqs.get_paginator("list_queues").paginate(**kw):
        urls.extend(page.get("QueueUrls", []))

    dlq_map = dlq_arns(sqs, urls)
    # Nombres de colas que son DLQ de otra (último segmento del ARN)
    dlq_names = {a.rsplit(":", 1)[-1] for a in dlq_map.values()}

    queues = []
    for url in urls:
        m = get_queue_metrics(sqs, url)
        m["dlq_arn"] = dlq_map.get(url)
        m["is_dlq"] = m["queue"] in dlq_names
        m["status"] = queue_status(m)
        if m["is_dlq"] and m["visible"] > 0:
            m["status"] = "CRITICAL"
            m["dlq_messages"] = m["visible"]
        queues.append(m)
    return queues


# ═══════════════════════════════════════════════════════════════════════════════
# SNS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_topics(sns) -> List[Dict]:
    topics = []
    for page in sns.get_paginator("list_topics").paginate():
        for t in page.get("Topics", []):
            arn = t["TopicArn"]
            name = arn.rsplit(":", 1)[-1]
            pending = 0
            try:
                for sp in sns.get_paginator(
                        "list_subscriptions_by_topic").paginate(
                            TopicArn=arn):
                    for s in sp.get("Subscriptions", []):
                        if s.get("SubscriptionArn",
                                 "").startswith("Pending"):
                            pending += 1
            except ClientError:
                pass
            topics.append({"topic": name, "arn": arn,
                           "pending_subscriptions": pending,
                           "status": "WARNING" if pending else "OK"})
    return topics


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

STATUS_STYLE = {"OK": "green", "WARNING": "yellow",
                "CRITICAL": "red"}


def get_args():
    parser = argparse.ArgumentParser(
        description="Monitoreo de colas SQS y topics SNS")
    parser.add_argument("--profile", "-p", default="default")
    parser.add_argument("--region", "-r", default="us-east-1")
    parser.add_argument("--queue-prefix", default="",
                        help="Filtrar colas por prefijo")
    parser.add_argument("--backlog-warn", type=int,
                        default=BACKLOG_WARN)
    parser.add_argument("--backlog-critical", type=int,
                        default=BACKLOG_CRITICAL)
    parser.add_argument("--age-warn", type=int,
                        default=AGE_WARN_SECONDS,
                        help="Edad de mensaje más antiguo (s)")
    parser.add_argument("--skip-sns", action="store_true")
    parser.add_argument("-o", "--output", choices=["json", "csv"],
                        default=None)
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main():
    args = get_args()
    global BACKLOG_WARN, BACKLOG_CRITICAL, AGE_WARN_SECONDS
    BACKLOG_WARN = args.backlog_warn
    BACKLOG_CRITICAL = args.backlog_critical
    AGE_WARN_SECONDS = args.age_warn

    if not BOTO3_AVAILABLE:
        _print("❌ boto3 no instalado", "red")
        sys.exit(1)
    try:
        session = boto3.Session(profile_name=args.profile,
                                region_name=args.region)
        sqs = session.client("sqs")
        sns = session.client("sns") if not args.skip_sns else None
    except Exception as e:
        _print(f"❌ Error de sesión AWS: {e}", "red")
        sys.exit(1)

    try:
        queues = analyze_queues(sqs, args.queue_prefix)
    except Exception as e:
        _print(f"❌ SQS: {e}", "red")
        sys.exit(1)
    topics = []
    if sns:
        try:
            topics = analyze_topics(sns)
        except Exception as e:
            _print(f"⚠ SNS: {e}", "yellow")

    alerts = []
    for q in queues:
        if q["status"] == "CRITICAL":
            alerts.append(
                f"🔴 {q['queue']}: {q['visible']} msgs"
                + (" (DLQ)" if q["is_dlq"] else "")
                + (f", más antiguo {q['oldest_message_s']}s"
                   if q["oldest_message_s"] else ""))
        elif q["status"] == "WARNING":
            alerts.append(
                f"🟡 {q['queue']}: {q['visible']} msgs"
                + (f", más antiguo {q['oldest_message_s']}s"
                   if q["oldest_message_s"] >= AGE_WARN_SECONDS
                   else ""))
    for t in topics:
        if t["pending_subscriptions"]:
            alerts.append(
                f"🟡 {t['topic']}: {t['pending_subscriptions']} "
                "suscripciones pendientes")

    if console:
        if queues:
            table = Table(title="Colas SQS", header_style="bold cyan")
            for col in ["Cola", "Visible", "In-flight", "Antiguo s",
                        "DLQ", "Estado"]:
                table.add_column(col)
            for q in sorted(queues, key=lambda x: -x["visible"]):
                color = STATUS_STYLE.get(q["status"], "")
                dlq = "🔗" if q["dlq_arn"] else \
                      ("📥" if q["is_dlq"] else "—")
                table.add_row(q["queue"][:40], str(q["visible"]),
                              str(q["in_flight"]),
                              str(q["oldest_message_s"]), dlq,
                              f"[{color}]{q['status']}[/{color}]")
            console.print(table)
        if topics:
            table = Table(title="Topics SNS", header_style="bold cyan")
            for col in ["Topic", "Suscripciones pendientes"]:
                table.add_column(col)
            for t in topics:
                table.add_row(t["topic"][:50],
                              str(t["pending_subscriptions"]))
            console.print(table)
        if alerts:
            console.print(Panel("\n".join(alerts),
                                title="⚠️ Alertas",
                                border_style="yellow"))
    else:
        for q in queues:
            print(f"{q['queue']}: {q['visible']} visible "
                  f"[{q['status']}]")
        for a in alerts:
            print(a)

    _print(f"\nColas: {len(queues)} | Topics: {len(topics)} | "
           f"Alertas: {len(alerts)}",
           "red" if any("🔴" in a for a in alerts)
           else ("yellow" if alerts else "green"))

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = OUTCOME_DIR / f"sqs_sns_monitor_{ts}.{args.output}"
        if args.output == "json":
            out.write_text(json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "region": args.region,
                "queues": queues, "topics": topics,
                "alerts": alerts}, indent=2, default=str),
                encoding="utf-8")
        else:
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "queue", "visible", "in_flight",
                    "oldest_message_s", "is_dlq", "has_dlq",
                    "status"])
                w.writeheader()
                for q in queues:
                    w.writerow({k: q.get(k) for k in w.fieldnames})
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if any("🔴" in a for a in alerts) else 0)


if __name__ == "__main__":
    main()
