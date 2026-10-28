# Permission & Access Auditor — Azure DevOps

Auditoría de **solo lectura** de permisos efectivos en una organización/proyecto
de Azure DevOps, sobre los recursos de seguridad de la plataforma:

- **CD — Release Pipelines** (namespace *ReleaseManagement*)
- **CI — Build Pipelines** (namespace *Build*)
- **Repositorios Git** (namespace *Git Repositories*)
- **Permisos de nivel Proyecto** (namespace *Project*)

## Motivación

Caso real: un usuario que **cambió de rol** sigue pudiendo modificar pipelines
CD aunque ya no pertenece al proyecto. El permiso le puede llegar por:

- Membresía residual en un grupo con permisos (proyecto, colección o AAD).
- Una **ACE directa** sobre el ACL del pipeline o del proyecto.
- Herencia de un grupo de nivel organización/colección.

La herramienta **explica de dónde viene cada permiso efectivo** (grupo
heredante o ACE directa) y compara contra la lista de usuarios que SÍ deberían
tener acceso.

## Documentos

| Archivo | Contenido |
|---|---|
| [01_ANALISIS.md](01_ANALISIS.md) | Problema, caso real, modelo de seguridad de AzDO (identidades, grupos, ACLs, herencia, tokens) |
| [02_APIS.md](02_APIS.md) | Catálogo de endpoints (Graph + Security), namespaces, formatos de token, scopes de PAT |
| [03_PLAN_IMPLEMENTACION.md](03_PLAN_IMPLEMENTACION.md) | Diseño del script, fases, salidas, flags, criterios de aceptación |

## Uso rápido

```bash
# Auditoría masiva (todas las vistas) + exports JSON/HTML/Excel
python scm/azdo/azdo_permission_audit.py --pat <PAT> \
    --org https://dev.azure.com/<ORG> --project <PROJECT>

# Deep dive de un usuario (cadena de herencia + origen por recurso)
python scm/azdo/azdo_permission_audit.py --pat <PAT> \
    --org ... --project ... --user usuario@dominio.com

# Comparar permisos de dos usuarios
python scm/azdo/azdo_permission_audit.py --pat <PAT> \
    --org ... --project ... --compare a@dominio.com,b@dominio.com

# Marcar accesos no esperados
python scm/azdo/azdo_permission_audit.py --pat <PAT> \
    --org ... --project ... --expected-users expected.csv
```

Opción **49** en `python scm/azdo/tools.py` (grupo 🛡️ Seguridad).

## Historial de cambios

| Fecha | Versión | Cambio |
|---|---|---|
| 2026-10-27 | 1.9.30 | Diseño inicial del auditor de permisos (megaplan aprobado): auditoría masiva con vistas por usuario y por recurso, `--user` deep dive, `--compare`, `--expected-users`, solo lectura |
