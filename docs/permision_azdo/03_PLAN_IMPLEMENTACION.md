# 03 — Plan de implementación

## Script

`scm/azdo/azdo_permission_audit.py` — opción **49** del launcher azdo
(grupo `security` 🛡️), nombre **"Permission & Access Auditor"**, `__version__ = "1.0.0"`.
Solo lectura (auditoría y reporte; la remediación es manual en el portal).

### Flags

```
--pat --org --project            (requeridos)
--user <email|displayName|desc>  deep dive de 1 usuario
--compare <a,b>        diff de permisos efectivos entre 2 usuarios
--expected-users <file|csv-list> lista de emails permitidos → ⚠️ NO ESPERADO
--namespaces release,build,git,project   (default: todos)
--definition-id / --repo         acotar a un pipeline/repo puntual
--threads N (default 10)  --debug   --output csv|excel
```

### Fases (con progress Rich / fallback plano)

1. **Contexto**: `projectId` → scope descriptor → grupos + usuarios del
   proyecto (Graph paginado).
2. **Membresías** (paralelo `--threads`): `direction=up` por usuario →
   grupos transitivos; `direction=down` por grupo → miembros. Cadena de
   herencia.
3. **ACLs** (paralelo por namespace): `accesscontrollists` con token raíz +
   `recurse=true&includeExtendedInfo=true`.
4. **Identidades**: `subjectdescriptors` → usuario (nombre/email) o grupo;
   los no resueltos se clasifican `service/other`.
5. **Matriz efectiva usuario×recurso** con trazabilidad de origen.
6. **Anomalías** vs `--expected-users` + permisos sensibles resaltados.

### Salidas

1. Resumen (usuarios, grupos, recursos, flags).
2. **Vista por usuario**: `USUARIO | EMAIL | GRUPOS | CD | CI | REPO | PROYECTO | PERMISOS CLAVE | ¿ESPERADO?`
3. **Vista por recurso**: `RECURSO | USUARIOS CON ACCESO | PERMISO MÁXIMO | VÍA | ALERTAS`
4. `--user`: cadena de herencia + tabla recurso×permiso×origen (bit a bit).
5. `--compare A B`: diff (solo-A / solo-B / común) + origen de la diferencia.
6. Tabla de anomalías + tabla informativa de grupos.
7. `write_default_reports` → JSON + HTML + Excel en `outcome/` con rutas al final.

## Archivos

| Archivo | Cambio |
|---|---|
| `scm/azdo/azdo_permission_audit.py` | NUEVO |
| `scm/azdo/tools.py` | opción `"49"` en TOOLS |
| `scm/tests/unit/test_azdo_permission_audit.py` | NUEVO |
| `docs/permision_azdo/` | estos docs |
| `scm/azdo/README.md` | sección + historial |
| `README.version.md` + `VERSION` | patch |

## Tests unitarios

- Decodificación de bits → nombres por namespace.
- Resolución de identidades (user/group/service).
- Matriz efectiva: herencia de grupo, deny precede, origen trazado.
- `--expected-users` (case-insensitive), `--user`, `--compare`.
- Vista por recurso. Paginación Graph. Dual-path Rich/plain.

## Criterios de aceptación

1. `--user <email>` muestra cadena de herencia + permisos por recurso con origen.
2. Masivo produce ambas vistas + flags de esperados.
3. `--compare A B` explica el origen de cada diferencia.
4. El caso real queda respondido (por qué el ex-rol sigue editando CDs).
5. JSON+HTML+Excel en `outcome/` con rutas al final; tests verdes.
