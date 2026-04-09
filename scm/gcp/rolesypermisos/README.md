# gcp_iam_roles_report

Script en Python para generar un **reporte detallado de roles y permisos IAM** asignados a un proyecto de Google Cloud Platform (GCP).

Permite responder preguntas como:

- ¿Qué roles están asignados en este proyecto?
- ¿Cuántos miembros tiene cada rol?
- ¿Qué permisos incluye cada rol?
- ¿Cuántos roles son básicos, predefinidos o custom (proyecto / organización)?
- ¿Qué advertencias se produjeron al generar el reporte (por ejemplo, falta de permisos para ver roles de organización)?

---

## Características

- Lee la **IAM Policy del proyecto** (bindings de `role` ↔ `members`).
- Obtiene el detalle de cada rol desde la API IAM:
  - Título (`title`)
  - Descripción (`description`)
  - Permisos incluidos (`includedPermissions`)
  - Estado (`stage`)
- Clasifica los roles por tipo:
  - `basic` → `roles/owner`, `roles/editor`, `roles/viewer`
  - `predefined` → `roles/...`
  - `custom-project` → `projects/{PROJECT_ID}/roles/...`
  - `custom-org` → `organizations/{ORG_ID}/roles/...`
  - `unknown`
- Genera múltiples salidas:
  - **Tabla en consola** con el resumen de roles
  - **Resumen global** con métricas:
    - Cantidad total de roles
    - Conteo por tipo de rol
    - Roles con y sin detalle de permisos
    - Total de asignaciones `role-member`
    - Número de identidades únicas (miembros)
  - **Archivos** (por defecto en `outcome/`):
    - `.txt` → resumen + tabla + métricas globales
    - `_summary.csv` → una fila por rol
    - `_permissions.csv` → una fila por (rol, permiso)
    - `.json` → detalle completo (roles, permisos, miembros)
    - `.log` → todos los warnings y mensajes relevantes

---

## Estructura del proyecto

- `gcp_iam_roles_report.py` → Script principal.
- `requirements.txt` → Dependencias de Python.

Contenido sugerido de `requirements.txt`:

```text
google-api-python-client>=2.130.0
google-auth>=2.35.0
google-auth-httplib2>=0.2.0
tabulate>=0.9.0
```

---

## Requisitos previos

1. **Python 3.8+**  
   Verifica tu versión:

   ```bash
   python3 --version
   ```

2. **Google Cloud SDK (`gcloud`)** instalado y autenticado.

3. Permisos mínimos recomendados en el proyecto objetivo:

   - `resourcemanager.projects.get`
   - `resourcemanager.projects.getIamPolicy`
   - `iam.roles.get` (para ver el detalle de los roles, incluidos los permisos)

   En la práctica, un rol como:

   - `roles/viewer` + `roles/iam.securityReviewer`  

   suele ser suficiente para la mayoría de los casos de lectura.

---

## Instalación

1. Clona o copia el script y el `requirements.txt` en un directorio, por ejemplo:

   ```bash
   mkdir gcp-iam-report
   cd gcp-iam-report
   # Copia aquí gcp_iam_roles_report.py y requirements.txt
   ```

2. (Opcional, recomendado) Crea un entorno virtual:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instala las dependencias:

   ```bash
   pip3 install -r requirements.txt
   ```

   > Si tu sistema es tipo Debian/Ubuntu y hay conflictos con paquetes del sistema:
   >
   > ```bash
   > pip3 install -r requirements.txt --break-system-packages
   > ```

---

## Autenticación (ADC)

El script utiliza **Application Default Credentials (ADC)**.

1. Inicia sesión con:

   ```bash
   gcloud auth application-default login
   ```

2. (Recomendado) Asegura que el **quota project** sea el proyecto donde vas a consultar IAM:

   ```bash
   gcloud auth application-default set-quota-project TU_PROYECTO_ID
   ```

   Ejemplo:

   ```bash
   gcloud auth application-default set-quota-project cpl-corp-cial-prod-17042024
   ```

3. Verifica que no tengas variables de entorno conflictivas:

   ```bash
   echo "$GOOGLE_APPLICATION_CREDENTIALS"
   echo "$CLOUDSDK_CONFIG"
   ```

   Si apuntan a otro contexto/proyecto y no lo deseas, elimínalas del entorno.

---

## Uso

### Parámetros

- `--project-id` (**obligatorio**)  
  ID del proyecto GCP a analizar.  
  Ejemplo: `cpl-corp-cial-prod-17042024`

- `--output-dir` (**opcional**, default: `outcome`)  
  Directorio donde se guardarán los archivos de salida.

### Comandos de ejemplo

#### 1. Uso básico (salida en `outcome/`)

```bash
python3 gcp_iam_roles_report.py \
  --project-id cpl-corp-cial-prod-17042024
```

Esto generará los archivos bajo el directorio `outcome/`.  
Si la carpeta no existe, el script la crea automáticamente.

#### 2. Usando un directorio personalizado

```bash
python3 gcp_iam_roles_report.py \
  --project-id cpl-corp-cial-prod-17042024 \
  --output-dir reports
```

Las salidas se generarán ahora en `reports/`.

#### 3. Ver ayuda

```bash
python3 gcp_iam_roles_report.py --help
```

---

## Archivos generados

Para un proyecto `cpl-corp-cial-prod-17042024` ejecutado en `2025-01-15 10:30:45`, se generarán nombres similares a:

- `gcp_iam_roles_cpl-corp-cial-prod-17042024_20250115_103045.txt`
- `gcp_iam_roles_cpl-corp-cial-prod-17042024_20250115_103045_summary.csv`
- `gcp_iam_roles_cpl-corp-cial-prod-17042024_20250115_103045_permissions.csv`
- `gcp_iam_roles_cpl-corp-cial-prod-17042024_20250115_103045.json`
- `gcp_iam_roles_cpl-corp-cial-prod-17042024_20250115_103045.log`

### 1. Archivo `.txt` (resumen)

Incluye:

- Metadatos:
  - Project ID
  - Project Number
  - Fecha/hora de generación (UTC)
- Tabla resumen de roles (en formato tipo Markdown)
- Resumen global de métricas:
  - Cantidad total de roles
  - Conteo por tipo (`basic`, `predefined`, `custom-project`, `custom-org`, `unknown`)
  - Roles con/sin permisos visibles
  - Total de asignaciones `role-member`
  - Número de miembros únicos

Ejemplo parcial de tabla:

```text
| Role                                     | Title                     | Type           | Stage   |   Members |   Permissions |
|------------------------------------------|---------------------------|----------------|---------|-----------|---------------|
| roles/owner                              | Owner                     | basic          | GA      |         2 |           249 |
| roles/editor                             | Editor                    | basic          | GA      |         0 |           213 |
| roles/viewer                             | Viewer                    | basic          | GA      |         5 |           113 |
| roles/iam.securityReviewer               | Security Reviewer         | predefined     | GA      |         1 |            72 |
| projects/mi-proyecto/roles/customAuditor | Custom Auditor            | custom-project | GA      |         3 |            10 |
```

### 2. `_summary.csv`

Una fila por rol, con columnas principales:

- `project_id`
- `project_number`
- `role_name`
- `title`
- `role_type`
- `stage`
- `members_count`
- `permissions_count`
- `generated_at`

Útil para cargar en Excel o una herramienta BI.

### 3. `_permissions.csv`

Una fila por (rol, permiso). Campos:

- `project_id`
- `project_number`
- `role_name`
- `title`
- `role_type`
- `permission`
- `generated_at`

Ejemplo:

```text
project_id,project_number,role_name,title,role_type,permission,generated_at
cpl-corp-cial-prod-17042024,123456789012,roles/viewer,Viewer,basic,compute.instances.get,2025-01-15T10:30:45+00:00
cpl-corp-cial-prod-17042024,123456789012,roles/viewer,Viewer,basic,resourcemanager.projects.get,2025-01-15T10:30:45+00:00
...
```

### 4. `.json` (detalle completo)

Estructura principal:

```json
{
  "generated_at": "2025-01-15T10:30:45+00:00",
  "project_id": "cpl-corp-cial-prod-17042024",
  "project_number": "123456789012",
  "roles": [
    {
      "project_id": "cpl-corp-cial-prod-17042024",
      "project_number": "123456789012",
      "role_name": "roles/viewer",
      "role_type": "basic",
      "title": "Viewer",
      "description": "...",
      "stage": "GA",
      "permissions": [
        "resourcemanager.projects.get",
        "compute.instances.get",
        "..."
      ],
      "permissions_count": 113,
      "members": [
        "user:alguien@example.com",
        "group:gcp-admins@example.com"
      ],
      "members_count": 2
    }
  ]
}
```

### 5. `.log` (warnings y mensajes)

Incluye:

- Fecha/hora de generación
- Mensajes `[INFO]`, `[WARN]`, `[AVISO]`, por ejemplo:
  - Cuando no se puede ver un rol de organización por falta de `iam.roles.get`.
  - Cuando el formato de rol es desconocido.
  - Información resumida del proyecto y conteo de roles.

Ejemplo de contenido parcial:

```text
LOG de ejecución - gcp_iam_roles_report.py
Generado: 2025-01-15T10:30:45+00:00
================================================================================

[INFO] Encontrados 18 roles distintos en el IAM Policy del proyecto.
[AVISO] No tienes permiso 'iam.roles.get' sobre roles de ORGANIZACIÓN.
        Esos roles aparecerán en el reporte pero SIN detalle de permisos.
        Para ver permisos de roles org-level, pide el rol
        'roles/iam.securityReviewer' o similar a nivel de organización.
[WARN] Sin permisos para rol: organizations/123456789012/roles/customOrgRole
[INFO] Proyecto real: cpl-corp-cial-prod-17042024 (número: 123456789012)
[INFO] Roles distintos encontrados en bindings de IAM: 18
```

---

## Notas y limitaciones

- Si no tienes `iam.roles.get` sobre ciertos roles (por ejemplo, roles de organización), esos roles:
  - Aparecerán en el resumen (se verán en la IAM Policy).
  - **No tendrán detalle de permisos** (`permissions_count` será `N/A`).
  - Se registrará un aviso en el `.log`.

- El script **no hace cambios** en la IAM Policy, solo lectura.

- La clasificación de roles (`basic`, `predefined`, `custom-project`, `custom-org`, `unknown`) se basa únicamente en el patrón del nombre del rol.

---

## Troubleshooting

### 1. Error de credenciales (ADC)

**Mensaje típico:**

> No se encontraron Application Default Credentials (ADC)

Solución:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project TU_PROYECTO_ID
```

### 2. Error `403 PERMISSION_DENIED` en IAM/Resource Manager

Revisa que tu identidad (cuenta de usuario o service account) tenga, al menos:

- `resourcemanager.projects.get`
- `resourcemanager.projects.getIamPolicy`
- `iam.roles.get` (para detalle de permisos)

### 3. No veo algunos permisos en roles de organización

Es probable que falte `iam.roles.get` a nivel de organización.  
Pide a tu equipo de seguridad/infra un rol como:

- `roles/iam.securityReviewer` (a nivel organización).

Mientras tanto, el script:

- Listará el rol en el resumen.
- No mostrará sus permisos (`permissions_count = N/A`).
- Guardará un aviso en el `.log`.

### 4. El directorio de salida no aparece

- Asegúrate de revisar la ruta correcta:
  - Por defecto: `outcome/`
  - O la que pasaste con `--output-dir`.
- El script crea el directorio si no existe, siempre que el usuario tenga permisos de escritura en el filesystem local.

---

## Sugerencias de uso

- **Auditorías periódicas**  
  Programar el script (por ejemplo con cron o un pipeline CI/CD) para generar un snapshot diario/semanal de roles y compararlos en el tiempo.

- **Integración con SIEM / GRC**  
  Cargar el `_summary.csv` y `_permissions.csv` en tu herramienta de análisis para hacer correlaciones de permisos y accesos.

- **Revisión manual de seguridad**  
  Usar el `.txt` y `.json` como input en sesiones de revisión de seguridad con tu equipo de Cloud/Security.

---

Si necesitas extender el script (por ejemplo, filtrar por tipos de miembros, exportar también solo grupos, o generar un reporte diferenciado por tipo de identidad –users, groups, serviceAccounts–), se puede añadir sin problema sobre esta base.

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-01-12 | 1.1.0 | Actualización de documentación: añadida tabla de historial de cambios |
| 2025-01-15 | 1.0.0 | Versión inicial con reporte de roles IAM, permisos y métricas globales |

---

## Autor

**Harold Adrian**