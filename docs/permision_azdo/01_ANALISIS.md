# 01 — Análisis del problema y modelo de seguridad de Azure DevOps

## El caso real

Un usuario que **cambió de rol** (dejó de pertenecer al equipo/proyecto) sigue
pudiendo **editar pipelines CD** en Azure DevOps. No debería: ya no es miembro
del proyecto. Pero el permiso persiste.

## ¿Por qué puede pasar?

En Azure DevOps el acceso efectivo a un recurso es la **unión** de permisos que
llegan por varias vías:

```
permiso_efectivo(usuario, recurso) =
      ACEs directas del usuario sobre ese recurso/token
    ∪ ACEs de los grupos a los que pertenece (transitivamente)
    ∪ permisos heredados del token padre (proyecto → pipeline → stage)
    − deny bits (la negación siempre gana)
```

Vías típicas de "permiso fantasma":

1. **Membresía residual en un grupo** — el usuario sigue en un grupo de AzDO
   (o anidado en un grupo de colección/AAD) que tiene permisos sobre el
   pipeline. Sacarlo "del proyecto" a nivel funcional no lo saca del grupo.
2. **ACE directa** — alguien le otorgó permiso directamente sobre un pipeline
   o sobre el proyecto (sin pasar por un grupo). Queda huérfana al cambiar de rol.
3. **Herencia de nivel superior** — el permiso viene del ACL del proyecto
   (`token = projectId`) y baja por `recurse` a cada pipeline: el usuario
   hereda "Edit release definition" de `Contributors`/`Release Administrators`
   o de un grupo custom con permiso de proyecto.
4. **Grupo anidado en colección** — un grupo del proyecto es miembro de un
   grupo de *Project Collection* (o viceversa) y la cadena de membresía no es
   obvia.

## Modelo de seguridad de AzDO (resumen operativo)

### Identidades y descriptores

- Todo sujeto de seguridad es un **descriptor** (Graph descriptor):
  usuarios `aad.*`, grupos `vssgp.*`, service principals.
- Los **grupos** existen a nivel organización (Project Collection) y a nivel
  proyecto (`scopeDescriptor` del proyecto).
- Las **membresías** son transitivas (un grupo puede ser miembro de otro) —
  `graph/memberships/{desc}?direction=up|down&depth=n`.

### ACLs, ACEs y tokens

- Cada recurso securizable vive en un **security namespace**
  (ReleaseManagement, Build, Git Repositories, Project, …).
- Un **token** identifica el recurso dentro del namespace
  (ej. `{projectId}/{releaseDefinitionId}`).
- Un **ACL** agrupa ACEs por token; cada **ACE** = descriptor + bits
  `allow`/`deny`. Con `includeExtendedInfo=true` vienen también
  `effectiveAllow/effectiveDeny` e `inheritedAllow/inheritedDeny` →
  distingue **directo vs heredado**.
- **Deny precede allow**; un permiso "Not set" hereda.

### Acciones (bits) relevantes por namespace

| Namespace | Acciones sensibles (muestra) |
|---|---|
| ReleaseManagement | EditReleaseDefinition, DeleteReleaseDefinition, ManageReleases, EditReleaseEnvironment, AdministerReleasePermissions, ManageDeployments |
| Build | EditBuildDefinition, DeleteBuildDefinition, QueueBuilds, EditBuildQuality, AdministerBuildPermissions |
| Git Repositories | Contribute, ForcePush, PolicyExempt, EditPolicies, ManagePermissions, DeleteRepository |
| Project | EditProjectLevelInformation, DeleteTeamProject, RenameTeamProject, ManageProjectProperties |

## Lo que debe explicar la herramienta

Para responder *"¿por qué este usuario aún edita CDs?"* cada permiso efectivo
debe llevar **trazabilidad de origen**:

| Permiso | Origen |
|---|---|
| EditReleaseDefinition sobre CD-1403 | `heredado del grupo "X Team"` (el usuario es miembro) |
| ManageReleases sobre CD-1403 | `ACE directa` (el descriptor del usuario está en el ACL) |
| ViewProjectInformation proyecto | `heredado de "Project Valid Users"` |

Y la operación contraria: *"¿quién puede tocar ESTE pipeline?"* — vista por
recurso que lista los usuarios con acceso efectivo y su vía de acceso.
