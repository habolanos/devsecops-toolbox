#!/usr/bin/env python3
"""Diagnóstico rápido: llama las 3 APIs para un definitionId y muestra la estructura real."""
import os, sys, json, requests, argparse
from base64 import b64encode
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--pat", required=True)
parser.add_argument("--org", default="Coppel-Retail")
parser.add_argument("--project", default="Compras.RMI")
parser.add_argument("--def-id", default="930", help="Release definition ID to test")
args = parser.parse_args()

PAT = args.pat
ORG = args.org
PROJECT = args.project
DEF_ID = args.def_id

auth = b64encode(f":{PAT}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

print(f"🔍 Testing APIs for definitionId={DEF_ID} org={ORG} project={PROJECT}\n")

# 1) Definition detail
print("=" * 60)
print("1) GET /release/definitions/{id}")
url1 = f"https://vsrm.dev.azure.com/{ORG}/{PROJECT}/_apis/release/definitions/{DEF_ID}?api-version=7.1"
r1 = requests.get(url1, headers=headers, timeout=30)
print(f"   Status: {r1.status_code}")
if r1.ok:
    d = r1.json()
    envs = d.get("environments", [])
    print(f"   Environments ({len(envs)}):")
    for e in envs:
        print(f"     - {e.get('name', '?')} (id={e.get('id', '?')})")
else:
    print(f"   Error: {r1.text[:200]}")

# 2) Deployments
print("\n" + "=" * 60)
print("2) GET /release/deployments?definitionId={id}&$top=5")
url2 = f"https://vsrm.dev.azure.com/{ORG}/{PROJECT}/_apis/release/deployments"
r2 = requests.get(url2, headers=headers, params={"definitionId": DEF_ID, "$top": 5, "api-version": "7.1"}, timeout=30)
print(f"   Status: {r2.status_code}")
if r2.ok:
    deps = r2.json().get("value", [])
    print(f"   Deployments count: {len(deps)}")
    if deps:
        print(f"   First record keys: {list(deps[0].keys())}")
        print(f"   First record (pretty):")
        print(json.dumps(deps[0], indent=2, ensure_ascii=False, default=str)[:2000])
    else:
        print("   ⚠️  NO deployments returned!")
else:
    print(f"   Error: {r2.text[:200]}")

# 3) Releases with $expand=environments
print("\n" + "=" * 60)
print("3) GET /releases?definitionId={id}&$expand=environments&$top=2")
url3 = f"https://vsrm.dev.azure.com/{ORG}/{PROJECT}/_apis/release/releases"
r3 = requests.get(url3, headers=headers, params={"definitionId": DEF_ID, "$expand": "environments", "$top": 2, "api-version": "7.1"}, timeout=30)
print(f"   Status: {r3.status_code}")
if r3.ok:
    rels = r3.json().get("value", [])
    print(f"   Releases count: {len(rels)}")
    if rels:
        rel = rels[0]
        print(f"   Release: {rel.get('name', '?')} (id={rel.get('id', '?')})")
        envs = rel.get("environments", [])
        print(f"   Environments in release ({len(envs)}):")
        for e in envs:
            print(f"     - name={e.get('name', '?')} status={e.get('status', '?')} modifiedOn={e.get('modifiedOn', '?')}")
            steps = e.get("deploySteps", [])
            print(f"       deploySteps ({len(steps)}):")
            for s in steps[:3]:
                print(f"         status={s.get('deploymentStatus', '?')} finishedOn={s.get('finishedOn', '?')}")
    else:
        print("   ⚠️  NO releases returned!")
else:
    print(f"   Error: {r3.text[:200]}")

# 4) Release detail (artifacts)
if r3.ok:
    rels = r3.json().get("value", [])
    if rels:
        rel_id = rels[0].get("id", "")
        print("\n" + "=" * 60)
        print(f"4) GET /releases/{rel_id} (artifacts)")
        url4 = f"https://vsrm.dev.azure.com/{ORG}/{PROJECT}/_apis/release/releases/{rel_id}?api-version=7.1"
        r4 = requests.get(url4, headers=headers, timeout=30)
        print(f"   Status: {r4.status_code}")
        if r4.ok:
            rd = r4.json()
            arts = rd.get("artifacts", [])
            print(f"   Artifacts ({len(arts)}):")
            for a in arts:
                print(f"     - type={a.get('type', '?')} isPrimary={a.get('isPrimary', '?')} alias={a.get('alias', '?')}")
                ref = a.get("definitionReference", {})
                print(f"       definitionReference keys: {list(ref.keys())}")
                sv = ref.get("sourceVersion", {})
                ver = ref.get("version", {})
                br = ref.get("build", {})
                print(f"       sourceVersion={sv}")
                print(f"       version={ver}")
                print(f"       build={br}")
