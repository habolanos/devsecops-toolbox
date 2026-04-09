#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gcp_iam_roles_report.py

Genera un reporte de los ROLES y PERMISOS asignados a un proyecto GCP.

Qué hace:
- Lee la política IAM del proyecto (Project IAM Policy) usando la API Cloud Resource Manager.
- Identifica todos los roles usados en ese proyecto.
- Para cada rol, obtiene:
  - Título.
  - Lista de permisos (includedPermissions) usando la API IAM.
- Clasifica los roles por "jerarquía":
  - basic          -> roles/owner, roles/editor, roles/viewer
  - predefined     -> roles/...
  - custom-project -> projects/{PROJECT_ID}/roles/...
  - custom-org     -> organizations/{ORG_ID}/roles/...

Salida:
- Consola:
  - Tabla resumen de roles.
  - Resumen final con métricas.
- Archivos (en --output-dir, por defecto: outcome):
  - TXT: tabla resumen + metadatos + resumen global.
  - CSV: tabla resumen (una fila por rol).
  - CSV: detalle de permisos (una fila por (rol, permiso)).
  - JSON: detalle completo (roles y permisos).
  - LOG: todos los warnings y mensajes relevantes.

Uso:
    python3 gcp_iam_roles_report.py --project-id TU_PROYECTO_ID [--output-dir CARPETA]

Autenticación:
    Usa Application Default Credentials (ADC):
    gcloud auth application-default login

Permisos requeridos:
    - resourcemanager.projects.get
    - resourcemanager.projects.getIamPolicy
    - iam.roles.get (para ver detalle de permisos de cada rol)
"""

import argparse
import csv
import json
import os
import warnings
from datetime import datetime, timezone
from collections import defaultdict, Counter

import google.auth
from google.auth.exceptions import DefaultCredentialsError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tabulate import tabulate


# Silenciar el warning de "quota project" de google.auth en consola
warnings.filterwarnings(
    "ignore",
    message="Your application has authenticated using end user credentials.*",
)

# Variables globales para controlar warnings y estadísticas
WARNED_ORG_ROLES = False
LOG_MESSAGES = []  # aquí guardamos todos los warnings / avisos importantes


def log(msg: str):
    """Guarda mensaje en memoria para el archivo .log y lo imprime en consola."""
    LOG_MESSAGES.append(msg)
    print(msg)


# ---------------------------------------------------------------------------
# Utilidades de clasificación
# ---------------------------------------------------------------------------

def classify_role(role_name: str) -> str:
    """
    Clasifica el rol según su 'jerarquía' / origen.
    """
    if role_name in ("roles/owner", "roles/editor", "roles/viewer"):
        return "basic"
    if role_name.startswith("roles/"):
        return "predefined"
    if role_name.startswith("projects/"):
        return "custom-project"
    if role_name.startswith("organizations/"):
        return "custom-org"
    return "unknown"


def role_type_sort_key(role_type: str) -> int:
    """
    Asigna una prioridad de orden a cada tipo de rol.
    """
    order = {
        "basic": 0,
        "predefined": 1,
        "custom-project": 2,
        "custom-org": 3,
        "unknown": 4,
    }
    return order.get(role_type, 99)


# ---------------------------------------------------------------------------
# Clientes de APIs (Resource Manager + IAM)
# ---------------------------------------------------------------------------

def build_crm_client():
    """
    Crea cliente para la API Cloud Resource Manager (v1) usando ADC.
    """
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return build("cloudresourcemanager", "v1", credentials=creds, cache_discovery=False)


def build_iam_client():
    """
    Crea cliente para la API IAM (v1) usando ADC.
    """
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return build("iam", "v1", credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------------------
# Funciones para obtener proyecto e IAM Policy
# ---------------------------------------------------------------------------

def get_project_info_and_policy(project_id: str):
    """
    Usa Cloud Resource Manager v1 para:
      - Obtener info del proyecto (incluye projectNumber).
      - Obtener IAM Policy del proyecto.

    Requiere permisos:
      - resourcemanager.projects.get
      - resourcemanager.projects.getIamPolicy
    """
    crm = build_crm_client()

    # 1) Info del proyecto
    try:
        proj = crm.projects().get(projectId=project_id).execute()
    except HttpError as e:
        raise RuntimeError(f"No se pudo obtener la información del proyecto {project_id}: {e}")

    project_number = proj.get("projectNumber")
    project_id_real = proj.get("projectId", project_id)

    # 2) IAM Policy
    try:
        policy = crm.projects().getIamPolicy(
            resource=project_id_real,
            body={}
        ).execute()
    except HttpError as e:
        raise RuntimeError(f"No se pudo obtener el IAM Policy del proyecto {project_id_real}: {e}")

    # La policy viene como dict con 'bindings'
    bindings = policy.get("bindings", [])

    return {
        "project_id": project_id_real,
        "project_number": project_number,
        "bindings": bindings,
    }


# ---------------------------------------------------------------------------
# IAM Roles (definición)
# ---------------------------------------------------------------------------

def fetch_role_definition(iam, role_name: str):
    """
    Obtiene la definición del rol desde la API IAM:
      - roles/...                -> iam.roles.get
      - projects/{ID}/roles/...  -> iam.projects.roles.get
      - organizations/{ID}/roles/... -> iam.organizations.roles.get
    """
    global WARNED_ORG_ROLES

    try:
        if role_name.startswith("roles/"):
            req = iam.roles().get(name=role_name)
        elif role_name.startswith("projects/"):
            req = iam.projects().roles().get(name=role_name)
        elif role_name.startswith("organizations/"):
            req = iam.organizations().roles().get(name=role_name)
        else:
            log(f"[WARN] Formato de rol no reconocido para consulta IAM: {role_name}")
            return None

        resp = req.execute()
        return resp

    except HttpError as e:
        # Si es un rol de organización y 403, no spameamos uno por cada rol
        if role_name.startswith("organizations/") and e.resp.status == 403:
            if not WARNED_ORG_ROLES:
                WARNED_ORG_ROLES_MSG = (
                    "[AVISO] No tienes permiso 'iam.roles.get' sobre roles de ORGANIZACIÓN.\n"
                    "        Esos roles aparecerán en el reporte pero SIN detalle de permisos.\n"
                    "        Para ver permisos de roles org-level, pide el rol\n"
                    "        'roles/iam.securityReviewer' o similar a nivel de organización."
                )
                print()  # separación visual en consola
                print("=" * 80)
                log(WARNED_ORG_ROLES_MSG)
                print("=" * 80)
                print()
                WARNED_ORG_ROLES = True
            # Guardamos en log cada rol que falló (sin imprimir en consola)
            LOG_MESSAGES.append(f"[WARN] Sin permisos para rol: {role_name}")
            return None

        # Para otros casos, mostramos el warning completo
        log(f"[WARN] No se pudo obtener definición IAM para rol {role_name}: {e}")
        return None


# ---------------------------------------------------------------------------
# Construcción del reporte
# ---------------------------------------------------------------------------

def build_roles_report(project_id: str):
    """
    Construye el reporte de roles del proyecto.

    Retorna un dict con:
      - project_id
      - project_number
      - summary_rows: lista de dicts con info resumida por rol
      - roles_detail: lista de dicts con info detallada (incluye permisos y miembros)
    """
    info = get_project_info_and_policy(project_id)
    project_id_real = info["project_id"]
    project_number = info["project_number"]
    bindings = info["bindings"]

    iam = build_iam_client()

    # role -> set(members)
    role_to_members = defaultdict(set)

    for b in bindings:
        role = b.get("role")
        members = b.get("members", [])
        if not role:
            continue
        for m in members:
            role_to_members[role].add(m)

    distinct_roles = sorted(role_to_members.keys())
    log(f"[INFO] Encontrados {len(distinct_roles)} roles distintos en el IAM Policy del proyecto.")
    print()

    roles_detail = []
    summary_rows = []

    for role_name in distinct_roles:
        role_type = classify_role(role_name)
        members = sorted(role_to_members[role_name])
        members_count = len(members)

        role_def = fetch_role_definition(iam, role_name)
        if role_def:
            title = role_def.get("title", "")
            description = role_def.get("description", "")
            included_permissions = role_def.get("includedPermissions", []) or []
            stage = role_def.get("stage", "")
            permissions_count = len(included_permissions)
        else:
            title = ""
            description = ""
            included_permissions = []
            stage = ""
            permissions_count = None

        roles_detail.append(
            {
                "project_id": project_id_real,
                "project_number": project_number,
                "role_name": role_name,
                "role_type": role_type,
                "title": title,
                "description": description,
                "stage": stage,
                "permissions": included_permissions,
                "permissions_count": permissions_count,
                "members": members,
                "members_count": members_count,
            }
        )

    for r in roles_detail:
        summary_rows.append(
            {
                "project_id": r["project_id"],
                "project_number": r["project_number"],
                "role_name": r["role_name"],
                "title": r["title"],
                "role_type": r["role_type"],
                "stage": r["stage"],
                "members_count": r["members_count"],
                "permissions_count": r["permissions_count"]
                if r["permissions_count"] is not None
                else "N/A",
            }
        )

    summary_rows.sort(
        key=lambda x: (role_type_sort_key(x["role_type"]), x["role_name"])
    )
    roles_detail.sort(
        key=lambda x: (role_type_sort_key(x["role_type"]), x["role_name"])
    )

    return {
        "project_id": project_id_real,
        "project_number": project_number,
        "summary_rows": summary_rows,
        "roles_detail": roles_detail,
    }


# ---------------------------------------------------------------------------
# Formato de tablas y escritura de archivos
# ---------------------------------------------------------------------------

def format_summary_table(summary_rows):
    headers = [
        "Role",
        "Title",
        "Type",
        "Stage",
        "Members",
        "Permissions",
    ]
    rows = []
    for r in summary_rows:
        rows.append(
            [
                r["role_name"],
                r["title"],
                r["role_type"],
                r["stage"] or "",
                r["members_count"],
                r["permissions_count"],
            ]
        )

    return tabulate(rows, headers=headers, tablefmt="github")


def write_summary_csv(summary_rows, filepath):
    fieldnames = [
        "project_id",
        "project_number",
        "role_name",
        "title",
        "role_type",
        "stage",
        "members_count",
        "permissions_count",
        "generated_at",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)


def write_permissions_csv(roles_detail, filepath, generated_at: str):
    fieldnames = [
        "project_id",
        "project_number",
        "role_name",
        "title",
        "role_type",
        "permission",
        "generated_at",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in roles_detail:
            perms = r.get("permissions", []) or []
            if not perms:
                writer.writerow(
                    {
                        "project_id": r["project_id"],
                        "project_number": r["project_number"],
                        "role_name": r["role_name"],
                        "title": r["title"],
                        "role_type": r["role_type"],
                        "permission": "",
                        "generated_at": generated_at,
                    }
                )
            else:
                for p in perms:
                    writer.writerow(
                        {
                            "project_id": r["project_id"],
                            "project_number": r["project_number"],
                            "role_name": r["role_name"],
                            "title": r["title"],
                            "role_type": r["role_type"],
                            "permission": p,
                            "generated_at": generated_at,
                        }
                    )


def write_json(full_report, filepath, generated_at: str):
    data = {
        "generated_at": generated_at,
        "project_id": full_report["project_id"],
        "project_number": full_report["project_number"],
        "roles": full_report["roles_detail"],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_log_file(log_path: str):
    """Escribe todos los mensajes de LOG_MESSAGES al archivo .log."""
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("LOG de ejecución - gcp_iam_roles_report.py\n")
        f.write(f"Generado: {datetime.now(timezone.utc).isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        for msg in LOG_MESSAGES:
            # Asegurar salto de línea
            if not msg.endswith("\n"):
                f.write(msg + "\n")
            else:
                f.write(msg)


# ---------------------------------------------------------------------------
# Resumen final
# ---------------------------------------------------------------------------

def compute_and_print_summary(full_report):
    summary_rows = full_report["summary_rows"]
    roles_detail = full_report["roles_detail"]

    total_roles = len(summary_rows)
    c_by_type = Counter(r["role_type"] for r in summary_rows)

    roles_with_perms = sum(
        1
        for r in roles_detail
        if r.get("permissions_count") not in (None, 0)
    )
    roles_without_perms = total_roles - roles_with_perms

    total_memberships = sum(r["members_count"] for r in roles_detail)

    # Contar miembros únicos
    unique_members = set()
    for r in roles_detail:
        unique_members.update(r["members"])

    print("=" * 80)
    print("RESUMEN GLOBAL DEL REPORTE")
    print("=" * 80)
    print(f"Proyecto ID:      {full_report['project_id']}")
    print(f"Proyecto Número:  {full_report['project_number']}")
    print()
    print(f"- Roles totales en IAM Policy: {total_roles}")
    print("  - Por tipo:")
    for t in ["basic", "predefined", "custom-project", "custom-org", "unknown"]:
        print(f"    * {t:14s}: {c_by_type.get(t, 0)}")
    print()
    print(f"- Roles con permisos visibles:     {roles_with_perms}")
    print(f"- Roles sin detalle de permisos:   {roles_without_perms}")
    print(f"- Total de asignaciones (role-member): {total_memberships}")
    print(f"- Miembros únicos (identidades):   {len(unique_members)}")
    print("=" * 80)
    print()

    return {
        "total_roles": total_roles,
        "by_type": dict(c_by_type),
        "roles_with_perms": roles_with_perms,
        "roles_without_perms": roles_without_perms,
        "total_memberships": total_memberships,
        "unique_members": len(unique_members),
    }


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Genera un reporte de roles y permisos IAM asignados a un proyecto GCP "
            "(tabla resumen + CSV/JSON + LOG)."
        )
    )
    parser.add_argument(
        "--project-id",
        required=True,
        help="ID del proyecto GCP (por ejemplo: cpl-corp-cial-prod-17042024)",
    )
    parser.add_argument(
        "--output-dir",
        default="outcome",
        help="Directorio donde guardar el reporte (default: outcome)",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("🔍 GENERANDO REPORTE DE ROLES Y PERMISOS IAM DEL PROYECTO")
    print("=" * 80)
    print(f"Proyecto: {args.project_id}")
    print(f"Directorio de salida: {args.output_dir}")
    print()

    exit_code = 0

    try:
        try:
            google.auth.default()
        except DefaultCredentialsError as e:
            raise RuntimeError(
                f"No se encontraron Application Default Credentials (ADC): {e}\n"
                "Configura tus credenciales con 'gcloud auth application-default login' "
                "o usando la variable de entorno GOOGLE_APPLICATION_CREDENTIALS."
            )

        generated_at = datetime.now(timezone.utc).isoformat()

        full_report = build_roles_report(args.project_id)
        summary_rows = full_report["summary_rows"]

        log(f"[INFO] Proyecto real: {full_report['project_id']} "
            f"(número: {full_report['project_number']})")
        log(f"[INFO] Roles distintos encontrados en bindings de IAM: {len(summary_rows)}")
        print()

        for row in summary_rows:
            row["generated_at"] = generated_at

        summary_table = format_summary_table(summary_rows)

        print(summary_table)
        print()

        # Resumen global
        summary_stats = compute_and_print_summary(full_report)

        os.makedirs(args.output_dir, exist_ok=True)
        ts_for_filename = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"gcp_iam_roles_{full_report['project_id']}_{ts_for_filename}"

        txt_path = os.path.join(args.output_dir, base_name + ".txt")
        csv_summary_path = os.path.join(args.output_dir, base_name + "_summary.csv")
        csv_perms_path = os.path.join(args.output_dir, base_name + "_permissions.csv")
        json_path = os.path.join(args.output_dir, base_name + ".json")
        log_path = os.path.join(args.output_dir, base_name + ".log")

        # TXT resumen
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("REPORTE DE ROLES Y PERMISOS IAM DEL PROYECTO\n")
            f.write(f"Proyecto ID: {full_report['project_id']}\n")
            f.write(f"Proyecto Número: {full_report['project_number']}\n")
            f.write(f"Generado (UTC): {generated_at}\n")
            f.write("=" * 80 + "\n\n")
            f.write("TABLA RESUMEN DE ROLES\n")
            f.write(summary_table)
            f.write("\n\n")
            f.write("=" * 80 + "\n")
            f.write("RESUMEN GLOBAL\n")
            f.write("=" * 80 + "\n")
            f.write(f"- Roles totales: {summary_stats['total_roles']}\n")
            f.write("  - Por tipo:\n")
            for t in ["basic", "predefined", "custom-project", "custom-org", "unknown"]:
                f.write(f"    * {t:14s}: {summary_stats['by_type'].get(t, 0)}\n")
            f.write("\n")
            f.write(f"- Roles con permisos visibles:     {summary_stats['roles_with_perms']}\n")
            f.write(f"- Roles sin detalle de permisos:   {summary_stats['roles_without_perms']}\n")
            f.write(f"- Total de asignaciones (role-member): {summary_stats['total_memberships']}\n")
            f.write(f"- Miembros únicos (identidades):   {summary_stats['unique_members']}\n")

        # CSV/JSON
        write_summary_csv(summary_rows, csv_summary_path)
        write_permissions_csv(full_report["roles_detail"], csv_perms_path, generated_at)
        write_json(full_report, json_path, generated_at)

        # LOG
        write_log_file(log_path)

        print()
        print("=" * 80)
        print("✅ REPORTE GENERADO EXITOSAMENTE")
        print("=" * 80)
        print("📁 Archivos generados:")
        print(f"  - TXT resumen:      {txt_path}")
        print(f"  - CSV resumen:      {csv_summary_path}")
        print(f"  - CSV permisos:     {csv_perms_path}")
        print(f"  - JSON detallado:   {json_path}")
        print(f"  - LOG de warnings:  {log_path}")
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR GENERANDO EL REPORTE")
        print("=" * 80)
        print(f"{e}")
        print()
        import traceback
        traceback.print_exc()
        exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())