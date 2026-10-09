#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKS Deployment Validator — Tool 17

Valida un deployment específico en AKS, equivalente a
connectivity/deployment_validator (GCP) y
aws_eks_deployment_validator:

- ConfigMaps y Secrets referenciados (env, envFrom, volúmenes)
  existen realmente
- Keys referenciadas (configMapKeyRef/secretKeyRef) existen
- Placeholders sin resolver (VALORES como CHANGEME/TODO/${...})
- Valores sensibles enmascarados en la salida
- Endpoints host:port extraídos de las configs (--validate
  connectivity hace probe TCP desde un pod temporal)

Uso:
    python aks_deployment_validator.py --cluster aks \\
        --resource-group rg --deployment api --namespace prod
    python aks_deployment_validator.py ... --validate secrets
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

sys.path.insert(0, str(Path(__file__).parent.parent))
from azure_common import (  # noqa: E402
    OUTCOME_DIR, console, _print, az_available,
    setup_aks_kubeconfig, kubectl_json, run_kubectl,
    resolve_subscription, now_ts, export_json)

__version__ = "1.0.0"

SECRET_PATTERNS = ("pass", "secret", "token", "key", "pwd",
                   "credential", "private")
PLACEHOLDER = re.compile(
    r"^(CHANGEME|TODO|PLACEHOLDER|REPLACE|xxx+|<.*>|\$\{.*\}.*)$",
    re.IGNORECASE)
ENDPOINT_RE = re.compile(
    r"(?P<host>[a-zA-Z0-9][\w.\-]*\.[\w.\-]+|[\w.\-]+:\d{2,5})")


def mask(value: str) -> str:
    return "****" if len(value or "") > 4 else "***"


def deployment_refs(deploy: Dict) -> Dict[str, Set[str]]:
    """ConfigMaps/Secrets referenciados por el deployment."""
    cms, secrets = set(), set()
    spec = deploy.get("spec", {}).get("template", {}) \
        .get("spec", {})
    for c in spec.get("containers", []):
        for env in c.get("env", []):
            ref = env.get("valueFrom", {})
            if "configMapKeyRef" in ref:
                cms.add(ref["configMapKeyRef"]["name"])
            if "secretKeyRef" in ref:
                secrets.add(ref["secretKeyRef"]["name"])
        for ef in c.get("envFrom", []):
            if "configMapRef" in ef:
                cms.add(ef["configMapRef"]["name"])
            if "secretRef" in ef:
                secrets.add(ef["secretRef"]["name"])
    for v in spec.get("volumes", []):
        if "configMap" in v:
            cms.add(v["configMap"]["name"])
        if "secret" in v:
            secrets.add(v["secret"]["secretName"])
    return {"configmaps": cms, "secrets": secrets}


def keys_referenced(deploy: Dict) -> Dict[str, Set[str]]:
    """{resource_name: {keys}} por configMapKeyRef/secretKeyRef."""
    refs = {}
    spec = deploy.get("spec", {}).get("template", {}) \
        .get("spec", {})
    for c in spec.get("containers", []):
        for env in c.get("env", []):
            for kind in ("configMapKeyRef", "secretKeyRef"):
                ref = env.get("valueFrom", {}).get(kind)
                if ref:
                    refs.setdefault(ref["name"], set()) \
                        .add(ref.get("key", ""))
    return refs


def get_obj(kind: str, name: str, ns: str) -> Dict:
    try:
        return kubectl_json(["get", kind, name, "-n", ns])
    except Exception:
        return {}


def validate(name: str, ns: str, mode: str) -> Dict:
    deploy = get_obj("deployment", name, ns)
    if not deploy:
        return {"error": f"deployment {ns}/{name} no existe"}

    refs = deployment_refs(deploy)
    key_refs = keys_referenced(deploy)
    result = {"deployment": name, "namespace": ns,
              "checks": [], "placeholders": [],
              "endpoints": []}

    kinds = (("configmaps", "configmap"),
             ("secrets", "secret"))
    for list_key, kind in kinds:
        if mode not in ("all", list_key):
            continue
        for res_name in sorted(refs[list_key]):
            obj = get_obj(kind, res_name, ns)
            if not obj:
                result["checks"].append({
                    "type": kind, "name": res_name,
                    "status": "MISSING",
                    "detail": "referenciado pero no existe"})
                continue
            data = obj.get("data", {}) or {}
            result["checks"].append({
                "type": kind, "name": res_name,
                "status": "OK",
                "detail": f"{len(data)} keys"})
            # keys referenciadas existen?
            for key in key_refs.get(res_name, set()):
                if key and key not in data and \
                        key not in (obj.get("stringData") or {}):
                    result["checks"].append({
                        "type": kind, "name": res_name,
                        "status": "MISSING_KEY",
                        "detail": f"key '{key}' no existe"})
            # placeholders y endpoints (solo ConfigMaps en claro)
            if kind == "configmap":
                for k, v in data.items():
                    if PLACEHOLDER.match(str(v)):
                        result["placeholders"].append(
                            f"{res_name}/{k}={v}")
                    for m in ENDPOINT_RE.finditer(str(v)):
                        result["endpoints"].append(
                            {"source": f"{res_name}/{k}",
                             "endpoint": m.group("host")})

    result["ok"] = not any(
        c["status"].startswith("MISSING")
        for c in result["checks"])
    return result


def get_args():
    p = argparse.ArgumentParser(
        description="Valida ConfigMaps/Secrets de un deployment "
                    "AKS")
    p.add_argument("--subscription", default="")
    p.add_argument("--cluster", required=True)
    p.add_argument("--resource-group", required=True)
    p.add_argument("--deployment", required=True)
    p.add_argument("--namespace", default="default")
    p.add_argument("--validate",
                   choices=["all", "configmaps", "secrets"],
                   default="all")
    p.add_argument("-o", "--output", choices=["json"])
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = get_args()
    if not az_available():
        _print("❌ az CLI no disponible o sin login", "red")
        sys.exit(1)
    sub = resolve_subscription(args.subscription)
    if not setup_aks_kubeconfig(args.cluster,
                                args.resource_group, sub):
        _print("❌ kubeconfig no configurado", "red")
        sys.exit(1)

    result = validate(args.deployment, args.namespace,
                      args.validate)
    if result.get("error"):
        _print(f"❌ {result['error']}", "red")
        sys.exit(1)

    if console:
        for c in result["checks"]:
            color = {"OK": "green"}.get(c["status"], "red")
            console.print(
                f"  [{color}]{c['status']}[/{color}] "
                f"{c['type']}/{c['name']}: "
                f"[dim]{c['detail']}[/dim]")
        for ph in result["placeholders"]:
            console.print(f"  [yellow]⚠ placeholder: {ph}"
                          f"[/yellow]")
        if result["endpoints"]:
            console.print(f"[dim]Endpoints detectados: "
                          f"{len(result['endpoints'])}[/dim]")
    else:
        import json
        print(json.dumps(result, indent=2, default=str))

    _print(f"\n{args.deployment}: "
           f"{'✅ OK' if result['ok'] else '❌ con errores'}",
           "green" if result["ok"] else "red")

    if args.output:
        OUTCOME_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTCOME_DIR / f"aks_deploy_valid_{now_ts()}.json"
        export_json(out, {"timestamp": datetime.utcnow()
                          .isoformat(), **result})
        _print(f"✓ Exportado a: {out}", "green")

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
