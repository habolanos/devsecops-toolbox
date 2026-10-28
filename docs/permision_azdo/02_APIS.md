# 02 — Catálogo de APIs, namespaces y tokens

## Hosts

| Host | Base | Uso |
|---|---|---|
| Core | `https://dev.azure.com/{org}` | projects, securitynamespaces, accesscontrollists, permissions, git repos, build definitions |
| VSRM | `https://vsrm.dev.azure.com/{org}` | release definitions (CD) |
| Graph | `https://vssps.dev.azure.com/{org}` | users, groups, memberships, descriptors |

Helper `vssps(org)`: `dev.azure.com` → `vssps.dev.azure.com` (igual que `vsrm()`).

## Graph API (`api-version=7.1-preview.1`)

| Endpoint | Descripción |
|---|---|
| `GET _apis/graph/descriptors/{projectId}` | Resuelve el **scope descriptor** del proyecto (`{value: "scp.*"}`) — filtra grupos/usuarios del proyecto |
| `GET _apis/graph/groups?scopeDescriptor={desc}` | Grupos del proyecto (paginado por `continuationToken` en query) |
| `GET _apis/graph/users?scopeDescriptor={desc}` | Usuarios con acceso al proyecto |
| `GET _apis/graph/memberships/{subjectDescriptor}?direction=up&depth={n}` | Grupos a los que pertenece el sujeto (transitivo con `depth`) |
| `GET _apis/graph/memberships/{subjectDescriptor}?direction=down&depth={n}` | Miembros de un grupo |
| `GET _apis/graph/subjectdescriptors?subjectDescriptors={d1,d2}` | Traduce descriptor de identidad (de una ACE) → descriptor de sujeto (usuario/grupo Graph) |

Respuestas `value[]`; usuarios traen `descriptor`, `displayName`, `mailAddress`,
`originId`. Grupos: `descriptor`, `displayName`, `principalName`.

## Security API (`api-version=7.1`)

| Endpoint | Descripción |
|---|---|
| `GET _apis/securitynamespaces` | Todos los namespaces: `namespaceId`, `name`, `actions[]` (bit → nombre de permiso). **Resolver por `name`, no por GUID quemado** |
| `GET _apis/accesscontrollists/{nsId}?token={t}&includeExtendedInfo=true&recurse=true` | ACLs del token raíz + hijos (cada pipeline/repo) en una llamada. `acesDictionary[descriptor] = {allow, deny, extendedInfo:{effectiveAllow, effectiveDeny, inheritedAllow, inheritedDeny}}` |
| `GET _apis/permissions/{nsId}/{bits}?descriptor={identityDesc}&token={token}` | Evaluación efectiva puntual de un descriptor sobre un token (para `--user` / `--compare` o verificación) |

## Namespaces y tokens

| Recurso | Nombre del namespace | ID (fallback) | Token raíz proyecto | Token por recurso |
|---|---|---|---|---|
| CD Release pipelines | `ReleaseManagement` | `c788c23e-1b46-4162-8f76-99428ed13bce` | `{projectId}` | `{projectId}/{definitionId}` (o `{projectId}/{folderPath}/{definitionId}`) |
| CI Build pipelines | `Build` | `33344d9c-fc72-4d6f-bf44-14e94696ab48` | `{projectId}` | `{projectId}/{definitionId}` |
| Repos Git | `Git Repositories` | `2e9eb7ed-3c0a-47d4-87c1-0ffdd275fd87` | `repoV2/{projectId}` | `repoV2/{projectId}/{repoId}` |
| Proyecto | `Project` | `52d39943-cb85-4d7f-8fa8-c6baac873819` | `$PROJECT:vstfs:///Classification/TeamProject/{projectId}` | mismo |

> **Nota de robustez**: no depender del formato exacto del token hijo —
> `recurse=true` devuelve los tokens reales tal como los genera el servidor;
> el token solo se parsea para extraer el último ID (definitionId/repoId).

## Datos de soporte (nombres amigables)

| Endpoint | Mapa |
|---|---|
| `GET {org}/{project}/_apis/projects/{project}` | `projectId` |
| `GET {vsrm}/{project}/_apis/release/definitions` | `id → nombre CD` |
| `GET {org}/{project}/_apis/build/definitions` | `id → nombre CI` |
| `GET {org}/{project}/_apis/git/repositories` | `id → nombre repo` |

## Scopes de PAT requeridos (todo solo-lectura)

| Scope | Para |
|---|---|
| Graph — Read | usuarios, grupos, membresías, descriptores |
| Security — Read | namespaces, ACLs, evaluación de permisos |
| Identity — Read | resolución de identidades |
| Release — Read | nombres de release definitions |
| Build — Read | nombres de build definitions |
| Code — Read | nombres de repositorios |

Un PAT **Full access** cubre todo; uno de scope custom debe incluir los 6.

## Flujo de evaluación efectiva (algoritmo)

```
1. groups_of(user)   = memberships(direction=up, transitivo)
2. aces(token)       = ACLs del namespace (recurse desde raíz)
3. efectivo(user, token) =
       ∪ ace.allow/effectiveAllow donde descriptor==user
       ∪ ace.allow donde descriptor ∈ groups_of(user)
       − ace.deny / effectiveDeny (precede allow)
4. origen(bit)       = 'directa' | 'grupo:<nombre>'
```
