#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
azdo_permission_audit.py — Permission & Access Auditor (Azure DevOps)

Auditoría de SOLO LECTURA de permisos efectivos a nivel
organización/proyecto/usuario sobre los recursos securizables:

  CD  — Release Pipelines   (namespace ReleaseManagement)
  CI  — Build Pipelines     (namespace Build)
  REP — Repositorios Git    (namespace Git Repositories)
  PRO — Nivel Proyecto      (namespace Project)

Para cada permiso efectivo se reporta su ORIGEN (ACE directa o grupo
heredante con su nombre) — responde "¿por qué este usuario aún puede
editar CDs aunque ya no pertenece al proyecto?".

Modos:
  - Masivo (default): vista por USUARIO + vista por RECURSO + anomalías.
  - --user <email>    deep dive de 1 usuario (cadena de herencia).
  - --compare A B     diff de permisos efectivos entre dos usuarios.
  - --expected-users  marca los que tienen acceso sin estar en la lista.

Salida por defecto: JSON + HTML + Excel en outcome/ (rutas al final).

Autor: Harold Adrian
"""

import argparse
import base64
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote
from typing import Any, Dict, List, Optional, Set, Tuple

# --- Directorio de salida centralizado (DEVSECOPS_OUTPUT_DIR) ---
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
    from rich.console import Console
    from rich.progress import (BarColumn, Progress, SpinnerColumn,
                               TaskProgressColumn, TextColumn)
    from rich.table import Table
    from rich import box
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None

try:
    import requests
except ImportError:
    requests = None

__version__ = "1.0.0"
__author__ = "Harold Adrian"

API_VERSION = "7.1"
API_VERSION_GRAPH = "7.1-preview.1"
MAX_LIST_PAGES = 100
GRAPH_DEPTH = 0  # 0 = transitivo completo en memberships

# namespaces a auditar: clave → nombre en securitynamespaces + tokens
NAMESPACES = {
    "release": {
        "ns_name": "ReleaseManagement",
        "ns_id_fallback": "c788c23e-1b46-4162-8f76-99428ed13bce",
        "kind": "CD",
        "root_token": "{pid}",
        "res_kind": "cd",
    },
    "build": {
        "ns_name": "Build",
        "ns_id_fallback": "33344d9c-fc72-4d6f-bf44-14e94696ab48",
        "kind": "CI",
        "root_token": "{pid}",
        "res_kind": "ci",
    },
    "git": {
        "ns_name": "Git Repositories",
        "ns_id_fallback": "2e9eb7ed-3c0a-47d4-87c1-0ffdd275fd87",
        "kind": "REPO",
        "root_token": "repoV2/{pid}",
        "res_kind": "repo",
    },
    "project": {
        "ns_name": "Project",
        "ns_id_fallback": "52d39943-cb85-4d7f-8fa8-c6baac873819",
        "kind": "PROYECTO",
        "root_token": "$PROJECT:vstfs:///Classification/"
                      "TeamProject/{pid}",
        "res_kind": "project",
    },
}

# acciones "sensibles" (edición/administración) — substring match
SENSITIVE = ("edit", "delete", "manage", "administer", "create",
             "contribute", "forcepush", "policyexempt", "queue")


def get_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="azdo_permission_audit",
        description="Audita permisos efectivos (solo lectura) sobre CD, "
                    "CI, repos y proyecto en Azure DevOps.")
    p.add_argument("--pat", required=True)
    p.add_argument("--org",
                   default="https://dev.azure.com/Coppel-Retail")
    p.add_argument("--project", default="Cadena_de_Suministros")
    p.add_argument("--user", default="",
                   help="Deep dive de un usuario (email/nombre/descriptor)")
    p.add_argument("--compare", default="", metavar="A,B",
                   help="Diff de permisos entre dos usuarios "
                        "'correoA,correoB'")
    p.add_argument("--expected-users", default="",
                   help="Archivo (un email por línea) o lista separada por "
                        "comas — los que SÍ deberían tener acceso")
    p.add_argument("--namespaces", default="release,build,git,project",
                   help="release|build|git|project (default: todos)")
    p.add_argument("--definition-id", type=int, default=0,
                   help="Acotar a un pipeline CD/CI puntual")
    p.add_argument("--repo", default="",
                   help="Acotar a un repositorio (substring del nombre)")
    p.add_argument("--threads", type=int, default=10,
                   help="Workers paralelos (default: 10)")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP helpers (convención del toolbox)
# ═══════════════════════════════════════════════════════════════════════════════
def make_headers(pat: str) -> Dict[str, str]:
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}",
            "Accept": "application/json"}


def vssps(org_url: str) -> str:
    if "vssps.dev.azure.com" in org_url:
        return org_url
    return org_url.replace("dev.azure.com", "vssps.dev.azure.com")


def vsrm(org_url: str) -> str:
    if "vsrm.dev.azure.com" in org_url:
        return org_url
    return org_url.replace("dev.azure.com", "vsrm.dev.azure.com")


def api_get(url: str, headers: Dict, params: Dict = None,
            debug: bool = False) -> Optional[Any]:
    try:
        r = requests.get(url, headers=headers, params=params, timeout=40)
        if r.status_code >= 400 and debug:
            print(f"[DEBUG] HTTP {r.status_code} {url}\n{r.text[:300]}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if debug:
            print(f"[DEBUG] {url}: {e}")
        return None


def api_get_page(url: str, headers: Dict, params: Dict = None,
                 debug: bool = False) -> Tuple[Optional[Any], Optional[str]]:
    """api_get + continuationToken (header x-ms-continuationtoken o
    campo del body para Graph)."""
    try:
        r = requests.get(url, headers=headers, params=params, timeout=40)
        if r.status_code >= 400 and debug:
            print(f"[DEBUG] HTTP {r.status_code} {url}\n{r.text[:300]}")
        r.raise_for_status()
        data = r.json()
        token = r.headers.get("x-ms-continuationtoken") \
            or (data or {}).get("continuationToken")
        return data, token
    except Exception as e:
        if debug:
            print(f"[DEBUG] {url}: {e}")
        return None, None


def _print(msg: str = "") -> None:
    if RICH and console:
        console.print(msg)
    else:
        print(re.sub(r"\[/?[a-zA-Z0-9_# =]+\]", "", str(msg)))


# ═══════════════════════════════════════════════════════════════════════════════
# Graph API: proyecto, usuarios, grupos, membresías, descriptores
# ═══════════════════════════════════════════════════════════════════════════════
def get_project_id(org: str, project: str, headers: Dict,
                   debug: bool) -> str:
    data = api_get(f"{org}/_apis/projects/{quote(project, safe='')}",
                   headers, {"api-version": API_VERSION}, debug)
    return (data or {}).get("id", "")


def get_scope_descriptor(org: str, project_id: str, headers: Dict,
                         debug: bool) -> str:
    """Descriptor del scope del proyecto (scp.*) para filtrar grupos."""
    url = f"{vssps(org)}/_apis/graph/descriptors/{project_id}"
    data = api_get(url, headers, {"api-version": API_VERSION_GRAPH},
                   debug)
    return (data or {}).get("value", "")


def graph_list(org: str, kind: str, scope_desc: str, headers: Dict,
               debug: bool) -> List[Dict]:
    """Pagina graph/users|groups?scopeDescriptor=…"""
    url = f"{vssps(org)}/_apis/graph/{kind}"
    params = {"api-version": API_VERSION_GRAPH}
    if scope_desc:
        params["scopeDescriptor"] = scope_desc
    out: List[Dict] = []
    for _ in range(MAX_LIST_PAGES):
        data, token = api_get_page(url, headers, params, debug)
        if not data:
            break
        out.extend(data.get("value", []) or [])
        if not token:
            break
        params["continuationToken"] = token
    return out


def get_memberships(org: str, subject_desc: str, direction: str,
                    headers: Dict, debug: bool,
                    depth: int = GRAPH_DEPTH) -> List[str]:
    """Descriptores contenedores/miembros de un sujeto.
    direction='up' → grupos a los que pertenece;
    direction='down' → miembros del grupo."""
    url = f"{vssps(org)}/_apis/graph/memberships/" \
          f"{quote(subject_desc, safe='')}"
    params = {"api-version": API_VERSION_GRAPH,
              "direction": direction}
    if depth:
        params["depth"] = depth
    out: List[str] = []
    for _ in range(MAX_LIST_PAGES):
        data, token = api_get_page(url, headers, params, debug)
        if not data:
            break
        out.extend(data.get("value", []) or [])
        if not token:
            break
        params["continuationToken"] = token
    key = "containerDescriptor" if direction == "up" \
        else "memberDescriptor"
    return [m.get(key, "") for m in out if m.get(key)]


def resolve_descriptors(org: str, id_descriptors: List[str],
                        headers: Dict, debug: bool) -> Dict[str, str]:
    """identityDescriptor (ACE) → subjectDescriptor (graph)."""
    url = f"{vssps(org)}/_apis/graph/subjectdescriptors"
    out: Dict[str, str] = {}
    # batch de a 50
    for i in range(0, len(id_descriptors), 50):
        batch = id_descriptors[i:i + 50]
        data = api_get(url, headers,
                       {"api-version": API_VERSION_GRAPH,
                        "subjectDescriptors": ",".join(batch)}, debug)
        for entry in (data or {}).get("value", []) or []:
            # la API devuelve pares descriptor→subjectDescriptor
            for k, v in (entry or {}).items():
                if isinstance(v, str):
                    out[k] = v
    return out


def get_graph_subject(org: str, desc: str, headers: Dict,
                      debug: bool) -> Optional[Dict]:
    """graph/users/{desc} o graph/groups/{desc} — datos del sujeto."""
    for kind in ("users", "groups"):
        data = api_get(f"{vssps(org)}/_apis/graph/{kind}/"
                       f"{quote(desc, safe='')}",
                       headers, {"api-version": API_VERSION_GRAPH}, debug)
        if data and data.get("descriptor"):
            return data
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Security API: namespaces y ACLs
# ═══════════════════════════════════════════════════════════════════════════════
def get_security_namespaces(org: str, headers: Dict,
                            debug: bool) -> Dict[str, Dict]:
    """name → {id, actions{bit:name}} — resolución dinámica."""
    data = api_get(f"{org}/_apis/securitynamespaces", headers,
                   {"api-version": API_VERSION}, debug)
    out: Dict[str, Dict] = {}
    for ns in (data or {}).get("value", []) or []:
        actions = {}
        for a in ns.get("actions", []) or []:
            try:
                actions[int(a["bit"])] = a.get("name", "")
            except (KeyError, TypeError, ValueError):
                pass
        out[ns.get("name", "")] = {"id": ns.get("namespaceId", ""),
                                   "actions": actions}
    return out


def get_acls(org: str, ns_id: str, token: str, headers: Dict,
             debug: bool, recurse: bool = True) -> List[Dict]:
    """ACLs de un token (y sus hijos con recurse=True)."""
    url = f"{org}/_apis/accesscontrollists/{ns_id}"
    data = api_get(url, headers,
                   {"api-version": API_VERSION, "token": token,
                    "includeExtendedInfo": "true",
                    "recurse": "true" if recurse else "false"}, debug)
    return (data or {}).get("value", []) or []


# ═══════════════════════════════════════════════════════════════════════════════
# Datos de soporte (nombres amigables de recursos)
# ═══════════════════════════════════════════════════════════════════════════════
def get_release_defs(org: str, project: str, headers: Dict,
                     debug: bool) -> Dict[int, str]:
    url = f"{vsrm(org)}/{quote(project, safe='')}/_apis/release/definitions"
    out: Dict[int, str] = {}
    params = {"api-version": "7.1-preview.4", "$top": 500}
    for _ in range(MAX_LIST_PAGES):
        data, token = api_get_page(url, headers, params, debug)
        if not data:
            break
        for d in data.get("value", []) or []:
            out[d.get("id")] = d.get("name", "")
        if not token:
            break
        params["continuationToken"] = token
    return out


def get_build_defs(org: str, project: str, headers: Dict,
                   debug: bool) -> Dict[int, str]:
    url = f"{org}/{quote(project, safe='')}/_apis/build/definitions"
    data = api_get(url, headers, {"api-version": API_VERSION,
                                  "$top": 500}, debug)
    return {d.get("id"): d.get("name", "")
            for d in (data or {}).get("value", []) or []}


def get_repos(org: str, project: str, headers: Dict,
              debug: bool) -> Dict[str, str]:
    url = f"{org}/{quote(project, safe='')}/_apis/git/repositories"
    data = api_get(url, headers, {"api-version": API_VERSION}, debug)
    return {r.get("id"): r.get("name", "")
            for r in (data or {}).get("value", []) or []}


# ═══════════════════════════════════════════════════════════════════════════════
# Modelo: decodificación de bits, identidades, matriz efectiva
# ═══════════════════════════════════════════════════════════════════════════════
def decode_bits(bits: int, actions: Dict[int, str]) -> List[str]:
    """bitmask → [nombres de acciones]."""
    if not actions:
        return [f"bit:{b}" for b in _bit_positions(bits)]
    return [actions.get(b, f"bit:{b}")
            for b in _bit_positions(bits)]


def _bit_positions(bits: int) -> List[int]:
    out, b = [], 1
    while b <= bits and b <= (1 << 63):
        if bits & b:
            out.append(b)
        b <<= 1
    return out


def is_sensitive(action_name: str) -> bool:
    n = (action_name or "").lower().replace(" ", "")
    return any(s in n for s in SENSITIVE)


def ace_bits(ace: Dict) -> Tuple[int, int]:
    """(allow, deny) efectivos de una ACE (extendedInfo tiene prioridad)."""
    ext = ace.get("extendedInfo") or {}
    allow = ext.get("effectiveAllow", ace.get("allow", 0)) or 0
    deny = ext.get("effectiveDeny", ace.get("deny", 0)) or 0
    return int(allow), int(deny)


class Identity:
    """Usuario o grupo resuelto de un descriptor."""
    def __init__(self, descriptor: str, kind: str, name: str,
                 mail: str = "", subject: str = ""):
        self.descriptor = descriptor
        self.kind = kind          # 'user' | 'group' | 'service' | 'other'
        self.name = name
        self.mail = mail
        self.subject = subject

    def __repr__(self):
        return f"<{self.kind}:{self.name}>"


def aces_to_subjects(aces: Dict[str, Dict],
                     sub_map: Dict[str, str]) -> Dict[str, Dict]:
    """Traduce las ACEs (identityDescriptor) a espacio de SUBJECT
    descriptors (vssgp/aad) uniendo bits de identidades que mapean al
    mismo sujeto."""
    out: Dict[str, Dict] = {}
    for idesc, ace in aces.items():
        s = sub_map.get(idesc, idesc)
        a_bits, d_bits = ace_bits(ace)
        cur = out.setdefault(s, {"extendedInfo": {}})
        ca, cd = ace_bits(cur)
        cur["extendedInfo"]["effectiveAllow"] = ca | a_bits
        cur["extendedInfo"]["effectiveDeny"] = cd | d_bits
    return out


def build_effective_map(
        aces_subj: Dict[str, Dict],
        groups_of_user: Dict[str, Set[str]],
        group_names: Dict[str, str],
        actions: Dict[int, str],
) -> Dict[str, Dict[int, str]]:
    """subjectDescriptor → {bit: origen} de permisos efectivos.
    `aces_subj` y `groups_of_user` están ambos en espacio de sujetos
    (vssgp/aad). origin: 'directa' | 'grupo:<nombre>'; deny precede."""
    users = set(groups_of_user.keys())
    out: Dict[str, Dict[int, str]] = {}
    for u in users:
        allow = 0
        deny = 0
        origin: Dict[int, str] = {}
        for desc, ace in aces_subj.items():
            a_bits, d_bits = ace_bits(ace)
            if desc == u:
                allow |= a_bits
                deny |= d_bits
                for b in _bit_positions(a_bits):
                    origin.setdefault(b, "directa")
            elif desc in groups_of_user.get(u, set()):
                gname = group_names.get(desc, desc)
                allow |= a_bits
                deny |= d_bits
                for b in _bit_positions(a_bits):
                    origin.setdefault(b, f"grupo:{gname}")
        eff = allow & ~deny
        if eff:
            out[u] = {b: origin.get(b, "directa")
                      for b in _bit_positions(eff)}
    return out


def sensitive_names(bit_map: Dict[int, str],
                    actions: Dict[int, str]) -> List[str]:
    """Nombres de acciones sensibles presentes en el mapa de bits."""
    names = [actions.get(b, f"bit:{b}") for b in bit_map]
    sens = [n for n in names if is_sensitive(n)]
    return sorted(sens)


def load_expected_users(src: str) -> Set[str]:
    """--expected-users: archivo (un email/línea) o lista separada por
    comas. Normaliza a minúsculas."""
    out: Set[str] = set()
    if not src:
        return out
    p = Path(src)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            e = line.strip().lower()
            if e and not e.startswith("#"):
                out.add(e)
    else:
        for e in src.split(","):
            e = e.strip().lower()
            if e:
                out.add(e)
    return out


def find_user(users: List[Identity], term: str) -> Optional[Identity]:
    """--user/--compare: match por email (prioridad), nombre o
    descriptor, case-insensitive."""
    t = (term or "").strip().lower()
    if not t:
        return None
    for u in users:
        if u.mail.lower() == t:
            return u
    for u in users:
        if t in u.name.lower() or t == u.descriptor.lower() \
                or t == (u.subject or "").lower():
            return u
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Recursos por namespace → nombre amigable
# ═══════════════════════════════════════════════════════════════════════════════
def token_resource_name(ns_key: str, token: str,
                        names: Dict[str, Dict]) -> Tuple[str, str]:
    """Token → (recurso_nombre, recurso_id). El último segmento del token
    es el id del recurso; la raíz del proyecto se marca como nivel proyecto."""
    if "/" not in token.strip("/"):
        return f"(nivel {NAMESPACES[ns_key]['kind']})", ""
    rid = token.split("/")[-1]
    m = names.get(NAMESPACES[ns_key]["res_kind"], {})
    try:
        nm = m.get(int(rid)) or m.get(rid)
    except (TypeError, ValueError):
        nm = m.get(rid)
    return (nm or f"{NAMESPACES[ns_key]['kind']} #{rid}"), rid


def collect_acls(org: str, project_id: str, ns_keys: List[str],
                 namespaces: Dict[str, Dict], headers: Dict,
                 debug: bool) -> Dict[str, List[Dict]]:
    """{ns_key: [ACLs]} — raíz de proyecto + recurse para cada namespace."""
    out: Dict[str, List[Dict]] = {}

    def _one(k):
        cfg = NAMESPACES[k]
        ns = namespaces.get(cfg["ns_name"]) \
            or {"id": cfg["ns_id_fallback"], "actions": {}}
        token = cfg["root_token"].format(pid=project_id)
        return k, ns, get_acls(org, ns["id"], token, headers, debug)

    with ThreadPoolExecutor(max_workers=min(4, len(ns_keys) or 1)) as ex:
        for k, ns, acls in ex.map(_one, ns_keys):
            out[k] = acls
            namespaces[k] = ns  # propagar actions resueltas
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# Vistas
# ═══════════════════════════════════════════════════════════════════════════════
def _rich_table(title: str, cols: List[str]) -> "Table":
    t = Table(title=title, box=box.ROUNDED)
    for c in cols:
        t.add_column(c)
    return t


def print_user_view(rows: List[Dict]) -> None:
    """USUARIO | EMAIL | GRUPOS | CD | CI | REPO | PROYECTO | PERMISOS |
    ¿ESPERADO?"""
    if RICH and console:
        t = _rich_table("Vista por USUARIO — permisos efectivos",
                        ["USUARIO", "EMAIL", "GRUPOS", "CD", "CI",
                         "REPO", "PROYECTO", "PERMISOS CLAVE",
                         "¿ESPERADO?"])
        for r in rows:
            flag = {"yes": "[green]SÍ[/]", "no": "[red]⚠ NO[/]",
                    "na": "[dim]?[/]"}[r["expected"]]
            t.add_row(r["name"], r["mail"], r["groups_str"],
                      r["cd"], r["ci"], r["repo"], r["proj"],
                      r["sens"], flag)
        console.print(t)
    else:
        for r in rows:
            print(f"{r['name']} <{r['mail']}> | grupos:{r['groups_str']} "
                  f"| CD:{r['cd']} CI:{r['ci']} REPO:{r['repo']} "
                  f"PRO:{r['proj']} | {r['sens']} | {r['expected']}")


def print_resource_view(rows: List[Dict]) -> None:
    """RECURSO | TIPO | USUARIOS | PERMISOS | VÍA | ALERTA."""
    if RICH and console:
        t = _rich_table("Vista por RECURSO — quién puede tocarlo",
                        ["RECURSO", "TIPO", "USUARIOS", "PERMISOS CLAVE",
                         "VÍA", "ALERTA"])
        for r in rows:
            t.add_row(r["resource"], r["kind"], str(r["n_users"]),
                      r["sens"], r["via"], r["alert"])
        console.print(t)
    else:
        for r in rows:
            print(f"{r['resource']} [{r['kind']}] | {r['n_users']} usuarios "
                  f"| {r['sens']} | {r['via']} | {r['alert']}")


def print_user_deep_dive(u: Identity, chain: List[str],
                         detail: List[Dict]) -> None:
    """Cadena de herencia + tabla recurso×permiso×origen."""
    _print(f"\n[bold cyan]═══ Deep dive: {u.name} "
           f"{'<' + u.mail + '>' if u.mail else ''} ═══[/]")
    _print(f"  Descriptor: {u.descriptor}")
    _print(f"  Cadena de herencia ({len(chain)} grupo(s)):")
    for g in chain:
        _print(f"    └─ {g}")
    if RICH and console:
        t = _rich_table("Permisos efectivos por recurso",
                        ["RECURSO", "TIPO", "PERMISO", "ORIGEN",
                         "¿SENSIBLE?"])
        for d in detail:
            t.add_row(d["resource"], d["kind"], d["perm"],
                      d["origin"], "⚠" if d["sensitive"] else "")
        console.print(t)
    else:
        for d in detail:
            print(f"  {d['resource']} [{d['kind']}] {d['perm']} "
                  f"← {d['origin']}")


def print_compare(a: "Identity", b: "Identity", diff: List[Dict]) -> None:
    """Diff de permisos efectivos A vs B."""
    _print(f"\n[bold cyan]═══ Compare: {a.name}  vs  {b.name} ═══[/]")
    if RICH and console:
        t = _rich_table("Diferencias de permisos",
                        ["RECURSO", "PERMISO", f"{a.name[:22]}",
                         f"{b.name[:22]}", "ORIGEN DEL ACCESO"])
        for d in diff:
            va = "✔" if d["a"] else "—"
            vb = "✔" if d["b"] else "—"
            if not d["a"]:
                va = "[dim]—[/]"
            if not d["b"]:
                vb = "[dim]—[/]"
            t.add_row(d["resource"], d["perm"], va, vb, d["origin"])
        console.print(t)
    else:
        for d in diff:
            print(f"  {d['resource']} | {d['perm']} | "
                  f"A={'✔' if d['a'] else '—'} B={'✔' if d['b'] else '—'} "
                  f"| {d['origin']}")


# ═══════════════════════════════════════════════════════════════════════════════
# Exportación por defecto
# ═══════════════════════════════════════════════════════════════════════════════
def export_row_user(r: Dict) -> Dict:
    return {"usuario": r["name"], "email": r["mail"],
            "grupos": r["groups_str"], "cd": r["cd"], "ci": r["ci"],
            "repo": r["repo"], "proyecto": r["proj"],
            "permisos_clave": r["sens"], "esperado": r["expected"]}


def export_row_resource(r: Dict) -> Dict:
    return {"recurso": r["resource"], "tipo": r["kind"],
            "usuarios_con_acceso": r["n_users"],
            "permisos_clave": r["sens"], "via": r["via"],
            "alerta": r["alert"]}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> int:
    if requests is None:
        print("❌ Falta 'requests' (pip install requests)")
        return 2
    args = get_args()
    org = args.org.rstrip("/")
    project = args.project
    headers = make_headers(args.pat)
    ns_keys = [k.strip() for k in args.namespaces.split(",")
               if k.strip() in NAMESPACES]

    # ── FASE 1: contexto ──
    if RICH and console:
        with Progress(SpinnerColumn(),
                      TextColumn("[progress.description]{task.description}"),
                      console=console) as p:
            t = p.add_task("Contexto del proyecto…", total=None)
            pid = get_project_id(org, project, headers, args.debug)
            sdesc = get_scope_descriptor(org, pid, headers, args.debug)
            users_g = graph_list(org, "users", sdesc, headers, args.debug)
            groups_g = graph_list(org, "groups", sdesc, headers,
                                  args.debug)
            namespaces = get_security_namespaces(org, headers, args.debug)
            p.update(t, description="✅ Contexto")
    else:
        pid = get_project_id(org, project, headers, args.debug)
        sdesc = get_scope_descriptor(org, pid, headers, args.debug)
        users_g = graph_list(org, "users", sdesc, headers, args.debug)
        groups_g = graph_list(org, "groups", sdesc, headers, args.debug)
        namespaces = get_security_namespaces(org, headers, args.debug)
        print("Contexto listo")

    if not pid:
        _print("[red]❌ No se pudo resolver el projectId.[/]")
        return 1

    # ── FASE 2: membresías (user→grupos, group→miembros) ──
    groups_by_desc = {g["descriptor"]: g for g in groups_g
                      if g.get("descriptor")}
    group_names = {d: g.get("displayName", "") or g.get("principalName", "")
                   for d, g in groups_by_desc.items()}
    groups_of_user: Dict[str, Set[str]] = {}
    members_of_group: Dict[str, Set[str]] = {}

    def _up(u):
        return u["descriptor"], set(get_memberships(
            org, u["descriptor"], "up", headers, args.debug))

    def _down(g):
        return g["descriptor"], set(get_memberships(
            org, g["descriptor"], "down", headers, args.debug))

    targets_u = [u for u in users_g if u.get("descriptor")]
    targets_g = [g for g in groups_g if g.get("descriptor")]
    if RICH and console:
        with Progress(SpinnerColumn(),
                      TextColumn("[progress.description]{task.description}"),
                      BarColumn(), TaskProgressColumn(),
                      console=console) as p:
            t = p.add_task("Membresías (usuarios/grupos)…",
                           total=len(targets_u) + len(targets_g))
            with ThreadPoolExecutor(
                    max_workers=max(1, args.threads)) as ex:
                futs = [ex.submit(_up, u) for u in targets_u]
                futs += [ex.submit(_down, g) for g in targets_g]
                for fut in as_completed(futs):
                    d, s = fut.result()
                    if d in groups_by_desc:
                        members_of_group[d] = s
                    else:
                        groups_of_user[d] = s
                    p.advance(t)
    else:
        for u in targets_u:
            d, s = _up(u)
            groups_of_user[d] = s
        for g in targets_g:
            d, s = _down(g)
            members_of_group[d] = s
        print("Membresías listas")

    # ── FASE 3: ACLs por namespace ──
    if RICH and console:
        with Progress(SpinnerColumn(),
                      TextColumn("[progress.description]{task.description}"),
                      console=console) as p:
            t = p.add_task("ACLs por namespace…", total=None)
            acls_by_ns = collect_acls(org, pid, ns_keys, namespaces,
                                      headers, args.debug)
            p.update(t, description="✅ ACLs")
    else:
        acls_by_ns = collect_acls(org, pid, ns_keys, namespaces,
                                  headers, args.debug)
        print("ACLs listas")

    # ── FASE 4: identidades de las ACEs (usuarios + grupos en tokens) ──
    all_ace_descs: Set[str] = set()
    for acls in acls_by_ns.values():
        for acl in acls:
            for d in (acl.get("acesDictionary") or {}).keys():
                all_ace_descs.add(d)
    sub_map = resolve_descriptors(org, sorted(all_ace_descs), headers,
                                  args.debug)

    # resolver sujetos (paralelo) → datos Graph
    subjects: Dict[str, Dict] = {}

    def _resolve(desc):
        return desc, get_graph_subject(org, desc, headers, args.debug)

    # sujetos: descriptores de ACEs + miembros de grupos (subject descs)
    member_descs = {m for mems in members_of_group.values() for m in mems}
    sub_descs = sorted({*sub_map.values(), *member_descs} - {""})
    with ThreadPoolExecutor(max_workers=max(1, args.threads)) as ex:
        for desc, subj in ex.map(_resolve, sub_descs):
            if subj:
                subjects[desc] = subj

    # usuarios = usuarios del proyecto + users que aparecen en ACEs
    users: List[Identity] = []
    seen = set()
    for u in users_g:
        d = u.get("descriptor")
        if not d or d in seen:
            continue
        seen.add(d)
        users.append(Identity(d, "user",
                              u.get("displayName", "") or
                              u.get("principalName", ""),
                              u.get("mailAddress", "") or
                              u.get("mail", ""),
                              u.get("descriptor", "")))
    for sdesc_, subj in subjects.items():
        if (subj.get("subjectKind") == "user"
                or subj.get("mailAddress")) and sdesc_ not in seen:
            seen.add(sdesc_)
            users.append(Identity(sdesc_, "user",
                                  subj.get("displayName", ""),
                                  subj.get("mailAddress", ""),
                                  sdesc_))

    # identityDescriptor (ACE) → user Identity (vía subjectDescriptor)
    desc_to_user: Dict[str, Identity] = {}
    by_desc = {u.descriptor: u for u in users}
    for idesc, sdesc_ in sub_map.items():
        u = by_desc.get(sdesc_)
        if u:
            desc_to_user[idesc] = u

    # completar user→grupos: grupos que contienen al usuario vía su
    # identityDescriptor en las ACEs
    for g_desc, mems in members_of_group.items():
        for m in mems:
            su = desc_to_user.get(m) or by_desc.get(m)
            if su:
                groups_of_user.setdefault(su.descriptor, set()).add(g_desc)

    # completar group_names con grupos resueltos de las ACEs
    # (pueden ser de colección, fuera del scope del proyecto)
    for sdesc_, subj in subjects.items():
        if subj.get("subjectKind") == "group" or subj.get("principalName"):
            if sdesc_ not in group_names:
                group_names[sdesc_] = subj.get("displayName", "") or \
                    subj.get("principalName", "")

    # ── FASE 5: matriz efectiva ──
    names = {"cd": get_release_defs(org, project, headers, args.debug),
             "ci": get_build_defs(org, project, headers, args.debug),
             "repo": get_repos(org, project, headers, args.debug)}
    expected = load_expected_users(args.expected_users)

    # grupos de CADA usuario conocido (espacio de sujetos) — incluye a
    # quien no aparece como ACE directa: hereda vía sus grupos
    all_user_groups = {u.descriptor: groups_of_user.get(u.descriptor,
                                                       set())
                       for u in users}
    # también incluir miembros de grupos aunque no estén en graph/users
    # del proyecto (usuario 'fantasma' con acceso residual)
    for g_desc, mems in members_of_group.items():
        for m in mems:
            if m in by_desc or m in all_user_groups:
                continue
            su = desc_to_user.get(m) or by_desc.get(m)
            if su:
                all_user_groups.setdefault(
                    su.descriptor, set()).add(g_desc)

    # {ns_key: {token: {user_subject_desc: {bit: origen}}}}
    matrix: Dict[str, Dict[str, Dict[str, Dict[int, str]]]] = {}
    for k in ns_keys:
        actions = namespaces.get(k, {}).get("actions", {})
        matrix[k] = {}
        for acl in acls_by_ns.get(k, []):
            token = acl.get("token", "")
            aces = acl.get("acesDictionary") or {}
            if not aces:
                continue
            aces_subj = aces_to_subjects(aces, sub_map)
            matrix[k][token] = build_effective_map(
                aces_subj, all_user_groups, group_names, actions)

    # ── Filtros de alcance ──
    def _res_ok(ns_key, token, rid):
        if args.definition_id:
            try:
                if int(rid or -1) != args.definition_id:
                    return False
            except (TypeError, ValueError):
                return False
        if args.repo and ns_key == "git":
            nm = names["repo"].get(rid, "")
            return args.repo.lower() in nm.lower()
        return True

    def _user_map(u: Identity) -> Dict[str, Dict[int, str]]:
        """ns_key → {token: {bit: origen}} para un usuario (espacio
        de sujetos — las claves de matrix ya son subjectDescriptors)."""
        out: Dict[str, Dict[int, str]] = {}
        for k in ns_keys:
            out[k] = {}
            for token, umap in matrix.get(k, {}).items():
                bit_map = umap.get(u.descriptor)
                if bit_map:
                    out[k][token] = bit_map
        return out

    # ── VISTA POR USUARIO ──
    user_rows = []
    for u in users:
        per_kind = {"release": [], "build": [], "git": [],
                    "project": []}
        origins: Set[str] = set()
        umap = _user_map(u)
        for k in ns_keys:
            actions = namespaces.get(k, {}).get("actions", {})
            for token, bit_map in umap.get(k, {}).items():
                rname, rid = token_resource_name(k, token, names)
                if not _res_ok(k, token, rid):
                    continue
                sens = sensitive_names(bit_map, actions)
                per_kind[k].append((rname, sens, bit_map))
                origins.update(bit_map.values())
        kind_str = {k: ("—" if not per_kind[k]
                        else f"{len(per_kind[k])} res")
                    for k in per_kind}
        all_sens = sorted({s for _, sens, _ in
                           [x for v in per_kind.values() for x in v]
                           for s in sens})
        exp = "na" if not expected else (
            "yes" if u.mail.lower() in expected or
            u.name.lower() in expected else "no")
        user_rows.append({
            "name": u.name, "mail": u.mail, "descriptor": u.descriptor,
            "groups_str": ",".join(sorted(
                group_names.get(g, g) for g in
                groups_of_user.get(u.descriptor, set())))[:60],
            "cd": kind_str["release"], "ci": kind_str["build"],
            "repo": kind_str["git"], "proj": kind_str["project"],
            "sens": ",".join(all_sens[:6]), "expected": exp,
            "origins": ";".join(sorted(origins))[:80]})

    # ── VISTA POR RECURSO ──
    res_rows = []
    for k in ns_keys:
        actions = namespaces.get(k, {}).get("actions", {})
        for token, umap in matrix.get(k, {}).items():
            rname, rid = token_resource_name(k, token, names)
            if not _res_ok(k, token, rid):
                continue
            users_acc = []
            sens_all = set()
            vias = set()
            alerts = []
            for idesc, bit_map in umap.items():
                u = by_desc.get(idesc)
                if not u:
                    continue
                users_acc.append(u.name)
                sens_all.update(sensitive_names(bit_map, actions))
                vias.update(bit_map.values())
                if expected and (
                        u.mail.lower() not in expected and
                        u.name.lower() not in expected):
                    alerts.append(u.mail or u.name)
            if not users_acc:
                continue
            res_rows.append({
                "resource": rname, "kind": NAMESPACES[k]["kind"],
                "n_users": len(set(users_acc)),
                "sens": ",".join(sorted(sens_all)[:6]),
                "via": ";".join(sorted(vias))[:60],
                "alert": ("⚠ " + ",".join(sorted(set(alerts))[:4])
                          if alerts else "")})

    # ── SALIDA ──
    _print(f"\n[bold]═══ Permission & Access Auditor — "
           f"{project} ═══[/]")
    _print(f"  Usuarios: {len(users)} | Grupos: {len(groups_g)} | "
           f"Namespaces: {','.join(ns_keys)} | "
           f"Recursos auditados: {sum(len(m) for m in matrix.values())}")

    compare_pair = [t.strip() for t in (args.compare or "").split(",")
                    if t.strip()]

    if args.user or compare_pair:
        for term in ([args.user] if args.user else compare_pair):
            u = find_user(users, term)
            if not u:
                _print(f"[red]❌ '{term}' no encontrado.[/]")
                continue
            chain = [group_names.get(g, g)
                     for g in sorted(groups_of_user.get(u.descriptor,
                                                        set()))]
            detail = []
            umap = _user_map(u)
            for k in ns_keys:
                actions = namespaces.get(k, {}).get("actions", {})
                for token, bit_map in umap.get(k, {}).items():
                    rname, rid = token_resource_name(k, token, names)
                    if not _res_ok(k, token, rid):
                        continue
                    for b, orig in bit_map.items():
                        perm = actions.get(b, f"bit:{b}")
                        detail.append({"resource": rname,
                                       "kind": NAMESPACES[k]["kind"],
                                       "perm": perm, "origin": orig,
                                       "sensitive": is_sensitive(perm)})
            print_user_deep_dive(u, chain, detail)

        if compare_pair and len(compare_pair) >= 2:
            ua = find_user(users, compare_pair[0])
            ub = find_user(users, compare_pair[1])
            if ua and ub:
                ma = _user_map(ua)
                mb = _user_map(ub)
                diff = []
                for k in ns_keys:
                    actions = namespaces.get(k, {}).get("actions", {})
                    for token in set(ma.get(k, {})) | set(mb.get(k, {})):
                        rname, rid = token_resource_name(k, token, names)
                        if not _res_ok(k, token, rid):
                            continue
                        bits_a = ma[k].get(token, {})
                        bits_b = mb[k].get(token, {})
                        for b in set(bits_a) | set(bits_b):
                            diff.append({
                                "resource": rname,
                                "perm": actions.get(b, f"bit:{b}"),
                                "a": b in bits_a, "b": b in bits_b,
                                "origin": bits_a.get(b, bits_b.get(b, ""))})
                print_compare(ua, ub, diff)
    else:
        print_user_view(user_rows)
        print_resource_view(res_rows)

    # ── Exportación al final ──
    try:
        from azdo_default_export import write_default_reports
        out_rows = ([export_row_user(r) for r in user_rows] +
                    [export_row_resource(r) for r in res_rows])
        write_default_reports(
            "permission_audit", __version__, out_rows,
            metadata={"organization": org, "project": project,
                      "namespaces": ",".join(ns_keys),
                      "mode": "compare" if compare_pair else
                              ("user" if args.user else "audit")},
            summary={"usuarios": len(users), "grupos": len(groups_g),
                     "recursos": sum(len(m) for m in matrix.values()),
                     "no_esperados": sum(1 for r in user_rows
                                        if r["expected"] == "no")},
            organization=org, project=project,
            title="Permission & Access Auditor", excel=True)
    except Exception as e:
        if args.debug:
            print(f"[DEBUG] export: {e}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(130)
