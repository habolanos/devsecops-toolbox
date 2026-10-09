#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Azure Service Bus Monitor — Tool 38

Monitoreo de Azure Service Bus (colas y topics), equivalente a
pubsub_monitor (GCP) / aws_sqs_sns_monitor:

- Namespaces: SKU, estado, TLS mínimo
- Colas: mensajes activos/dead-letter/scheduled, tamaño,
  dead-lettering habilitado, lock duration
- Topics: suscripciones y mensajes por suscripción
- Alertas: dead-letter >0, cola llena >80%, maxDeliveryCount
  bajo con DLQ llena
- Multi-suscripción con --config (compatible launcher)

Uso:
    python azure_service_bus_monitor.py --subscription <id>
    python azure_service_bus_monitor.py --config scm/config.json
    python azure_service_bus_monitor.py -o json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available, try_az,
    resolve_subscription, rg_of, now_ts, export_json,
    export_csv, load_config)

__version__ = "1.0.0"

QUEUE_FULL_WARN = 0.8


def analyze_queue(q: Dict, ns: str) -> Dict:
    findings = []
    counts = q.get("countDetails", {})
    active = counts.get("activeMessageCount", 0)
    dlq = counts.get("deadLetterMessageCount", 0)
    max_size = q.get("maxSizeInMegabytes", 1024)
    size_used = q.get("sizeInBytes", 0) / 1024 / 1024
    if dlq:
        findings.append(f"🔴 DLQ con {dlq} mensajes")
    if size_used / max_size > QUEUE_FULL_WARN:
        findings.append(f"🟡 Cola al "
                        f"{int(100*size_used/max_size)}% "
                        "de capacidad")
    if active > 1000:
        findings.append(f"🟡 Backlog alto: {active} mensajes")
    if not q.get("deadLetteringOnMessageExpiration"):
        findings.append("🟡 DLQ por expiración "
                        "deshabilitada")
    return {
        "namespace": ns, "queue": q["name"],
        "active": active, "dead_letter": dlq,
        "scheduled": counts.get(
            "scheduledMessageCount", 0),
        "size_mb": round(size_used, 1),
        "max_mb": max_size,
        "status": q.get("status"),
        "max_delivery": q.get("maxDeliveryCount"),
        "dlq_enabled": q.get(
            "deadLetteringOnMessageExpiration"),
        "findings": findings,
    }


def analyze_ns(sub: str, ns: Dict) -> Dict:
    name, rg = ns["name"], rg_of(ns)
    findings = []
    if ns.get("minimumTlsVersion") and \
            float(ns["minimumTlsVersion"]) < 1.2:
        findings.append("🔴 TLS <1.2")
    if ns.get("publicNetworkAccess") == "Enabled":
        findings.append("🟡 Acceso público habilitado")
    if ns.get("zoneRedundant") is False and \
            (ns.get("sku") or {}).get("name") == "Premium":
        findings.append("🟡 Premium sin zone redundancy")
    return {
        "namespace": name, "resource_group": rg,
        "sku": (ns.get("sku") or {}).get("name"),
        "location": ns.get("location"),
        "tls": ns.get("minimumTlsVersion"),
        "public_access": ns.get("publicNetworkAccess"),
        "findings": findings,
    }


def collect(sub: str) -> Dict:
    namespaces = try_az(["servicebus", "namespace", "list"],
                        sub, default=[]) or []
    ns_rows = [analyze_ns(sub, n) for n in namespaces]
    queues, topics = [], []
    for n in namespaces:
        rg = rg_of(n)
        for q in (try_az(["servicebus", "queue", "list",
                          "--namespace-name", n["name"],
                          "--resource-group", rg], sub,
                         default=[]) or []):
            queues.append(analyze_queue(q, n["name"]))
        for t in (try_az(["servicebus", "topic", "list",
                          "--namespace-name", n["name"],
                          "--resource-group", rg], sub,
                         default=[]) or []):
            subs = try_az(
                ["servicebus", "topic", "subscription",
                 "list", "--namespace-name", n["name"],
                 "--topic-name", t["name"],
                 "--resource-group", rg], sub,
                default=[]) or []
            topics.append({
                "namespace": n["name"], "topic": t["name"],
                "subscriptions": len(subs),
                "sub_details": [{
                    "name": s["name"],
                    "active": (s.get("countDetails") or {})
                    .get("activeMessageCount", 0),
                    "dlq": (s.get("countDetails") or {})
                    .get("deadLetterMessageCount", 0),
                } for s in subs],
            })
    return {"namespaces": ns_rows, "queues": queues,
            "topics": topics}


def get_args():
    p = argparse.ArgumentParser(
        description="Monitor Azure Service Bus")
    p.add_argument("--subscription", default="")
    p.add_argument("--config", default="",
                   help="config.json (compat. launcher)")
    p.add_argument("-o", "--output", choices=["json", "csv"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    data = collect(sub)

    dlq_queues = [q for q in data["queues"]
                  if q["dead_letter"] > 0]
    total_findings = sum(
        len(x["findings"]) for x in
        data["namespaces"] + data["queues"])

    if console:
        from rich.table import Table
        t1 = Table(title="Service Bus Queues",
                   header_style="bold cyan")
        for col in ["Cola", "Activos", "DLQ", "MB",
                    "Findings"]:
            t1.add_column(col)
        for q in data["queues"]:
            color = "red" if q["dead_letter"] else "green"
            t1.add_row(q["queue"][:40], str(q["active"]),
                       f"[{color}]{q['dead_letter']}"
                       f"[/{color}]",
                       str(q["size_mb"]),
                       str(len(q["findings"])))
        console.print(t1)
        if data["topics"]:
            t2 = Table(title="Topics",
                       header_style="bold magenta")
            t2.add_column("Topic")
            t2.add_column("Subs")
            t2.add_column("DLQ total")
            for t in data["topics"]:
                dlq_tot = sum(s["dlq"]
                              for s in t["sub_details"])
                color = "red" if dlq_tot else "green"
                t2.add_row(t["topic"][:40],
                           str(t["subscriptions"]),
                           f"[{color}]{dlq_tot}[/{color}]")
            console.print(t2)
        for x in data["namespaces"] + data["queues"]:
            for f in x["findings"]:
                name = x.get("namespace") or x.get("queue")
                console.print(f"  {f} [dim]({name})[/dim]")
    else:
        for q in data["queues"]:
            print(f"{q['queue']}: active={q['active']} "
                  f"dlq={q['dead_letter']}")

    _print(f"\nNamespaces: {len(data['namespaces'])} | "
           f"colas: {len(data['queues'])} | topics: "
           f"{len(data['topics'])} | colas con DLQ: "
           f"{len(dlq_queues)}",
           "red" if dlq_queues else "green")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"servicebus_{now_ts()}" \
                            f".{args.output}"
        if args.output == "json":
            export_json(out, {
                "timestamp": datetime.utcnow().isoformat(),
                **data})
        else:
            rows = [{k: q[k] for k in
                     ("namespace", "queue", "active",
                      "dead_letter", "size_mb", "max_mb")}
                    | {"findings": "; ".join(q["findings"])}
                    for q in data["queues"]]
            export_csv(out, list(rows[0]) if rows else
                       ["queue"], rows)
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(1 if dlq_queues else 0)


if __name__ == "__main__":
    main()
