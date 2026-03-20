# 🔐 GCP Service Account Checker

Herramienta SRE para listar, analizar y auditar Service Accounts en Google Cloud Platform.

## 📋 Tabla de Contenidos

- [Descripción](#descripción)
- [Características](#características)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Parámetros](#parámetros)
- [Salida](#salida)
- [Ejemplos](#ejemplos)
- [Alertas y Recomendaciones](#alertas-y-recomendaciones)
- [Troubleshooting](#troubleshooting)
- [Autor](#autor)
- [Historial de Cambios](#historial-de-cambios)

---

## 📖 Descripción

`gcp_service_account_checker.py` es una herramienta de línea de comandos que permite:

- Listar todas las Service Accounts de un proyecto GCP
- Verificar el estado (habilitada/deshabilitada) de cada SA
- Identificar keys de usuario y su antigüedad
- Analizar roles IAM asignados a cada SA
- Detectar posibles problemas de seguridad

---

## ✨ Características

| Característica | Descripción |
|---------------|-------------|
| **gcloud CLI** | Usa comandos gcloud (no requiere APIs de Python) |
| **Análisis de keys** | Detecta keys de usuario y calcula antigüedad |
| **Roles IAM** | Lista roles asignados a cada Service Account |
| **Alertas** | Identifica SAs con muchos roles o keys antiguas |
| **Exportación** | Soporta TXT, CSV y JSON |
| **Rich output** | Tablas formateadas con Rich (opcional) |

---

## 📦 Requisitos

### Obligatorios

- Python 3.8+
- Google Cloud SDK (`gcloud`) instalado y configurado
- Sesión activa de gcloud (`gcloud auth login`)
- Permisos en el proyecto:
  - `iam.serviceAccounts.list`
  - `iam.serviceAccountKeys.list`
  - `resourcemanager.projects.getIamPolicy`

### Opcionales

- `rich` - Para salida formateada con tablas y colores

```bash
pip install rich
```

---

## 🚀 Instalación

1. Clonar el repositorio o copiar el script
2. Instalar dependencias opcionales:

```bash
pip install rich
```

3. Verificar acceso a GCP:

```bash
gcloud auth login
gcloud config set project TU_PROYECTO
```

---

## 💻 Uso

### Uso básico (proyecto por defecto)

```bash
python gcp_service_account_checker.py
```

### Especificar proyecto

```bash
python gcp_service_account_checker.py --project mi-proyecto-gcp
```

### Con modo debug

```bash
python gcp_service_account_checker.py --project mi-proyecto-gcp --debug
```

### Exportar a JSON

```bash
python gcp_service_account_checker.py --output json
```

### Ver ayuda completa

```bash
python gcp_service_account_checker.py --help
```

---

## ⚙️ Parámetros

| Parámetro | Corto | Descripción | Default |
|-----------|-------|-------------|---------|
| `--project` | `-p` | ID del proyecto GCP | `cpl-xxxx-yyyy-zzzz-99999999` |
| `--output` | `-o` | Formato de exportación: `txt`, `csv`, `json` | `txt` |
| `--debug` | | Activa modo debug | `false` |
| `--no-keys` | | No consultar keys (más rápido) | `false` |
| `--help` | `-h` | Muestra esta documentación | |

---

## 📊 Salida

### Tabla de Service Accounts

```
┌──────────────────────────────────────────────────┬──────────────┬───────┬────────────┬───────┐
│ Email                                            │ Estado       │ Keys  │ Antigüedad │ Roles │
├──────────────────────────────────────────────────┼──────────────┼───────┼────────────┼───────┤
│ my-service@project.iam.gserviceaccount.com       │ 🟢 Activa    │ ⚠️ 2  │ 6mo        │ 5     │
│ compute@developer.gserviceaccount.com            │ 🟢 Activa    │ 0     │ N/A        │ 3     │
│ old-sa@project.iam.gserviceaccount.com           │ 🔴 Deshabili │ 0     │ N/A        │ 0     │
└──────────────────────────────────────────────────┴──────────────┴───────┴────────────┴───────┘
```

### Resumen

```
📊 Resumen de Service Accounts
┌─────────────────────────┬────────┐
│ Métrica                 │ Valor  │
├─────────────────────────┼────────┤
│ Total Service Accounts  │ 15     │
│ Activas                 │ 🟢 12  │
│ Deshabilitadas          │ 🔴 3   │
│ Con keys de usuario     │ 🔑 4   │
│ Total keys de usuario   │ 7      │
└─────────────────────────┴────────┘
```

---

## 📁 Archivos de Salida

Los reportes se guardan en `outcome/` con el formato:

- **TXT**: `sa_report_<project>_<timestamp>.txt`
- **CSV**: `sa_report_<project>_<timestamp>.csv`
- **JSON**: `sa_report_<project>_<timestamp>.json`

### Estructura JSON

```json
{
  "project_id": "mi-proyecto",
  "generated_at": "2026-02-20T12:30:00",
  "version": "1.0.0",
  "summary": {
    "total": 15,
    "active": 12,
    "disabled": 3,
    "with_user_keys": 4
  },
  "service_accounts": [
    {
      "email": "my-sa@project.iam.gserviceaccount.com",
      "name": "My Service Account",
      "disabled": false,
      "user_managed_keys": 2,
      "oldest_key_age": "6mo",
      "roles": ["roles/editor", "roles/storage.admin"],
      "roles_count": 2
    }
  ]
}
```

---

## ⚠️ Alertas y Recomendaciones

El script detecta automáticamente:

| Alerta | Descripción | Recomendación |
|--------|-------------|---------------|
| 🔑 Keys de usuario | SA tiene keys creadas manualmente | Considerar rotación o uso de Workload Identity |
| 📛 Muchos roles | SA tiene más de 10 roles | Revisar principio de mínimo privilegio |
| ⏰ Keys antiguas | Keys con más de 90 días | Rotar keys periódicamente |

### Buenas prácticas para Service Accounts

1. **Evitar keys de usuario**: Preferir Workload Identity para GKE
2. **Mínimo privilegio**: Asignar solo los roles necesarios
3. **Rotación de keys**: Si usas keys, rotarlas cada 90 días
4. **Deshabilitar SAs no usadas**: No eliminar, deshabilitar primero
5. **Nombres descriptivos**: Usar nombres que indiquen el propósito

---

## 🔧 Troubleshooting

### Error: "No hay sesión activa de gcloud"

```bash
gcloud auth login
```

### Error: "No tienes acceso al proyecto"

Verifica que tienes los permisos necesarios:

```bash
gcloud projects get-iam-policy PROYECTO_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:TU_EMAIL"
```

### Error: "Permission denied" al listar keys

Necesitas el permiso `iam.serviceAccountKeys.list`. Solicita el rol:

```bash
gcloud projects add-iam-policy-binding PROYECTO_ID \
  --member="user:TU_EMAIL" \
  --role="roles/iam.serviceAccountViewer"
```

### El script es lento

Usa `--no-keys` para omitir la consulta de keys de cada SA:

```bash
python gcp_service_account_checker.py --no-keys
```

---

## 🔗 Comandos gcloud relacionados

```bash
# Listar Service Accounts
gcloud iam service-accounts list --project=PROYECTO

# Ver keys de una SA
gcloud iam service-accounts keys list \
  --iam-account=EMAIL_SA

# Ver roles de una SA
gcloud projects get-iam-policy PROYECTO \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:EMAIL_SA" \
  --format="table(bindings.role)"

# Deshabilitar una SA
gcloud iam service-accounts disable EMAIL_SA

# Eliminar una key
gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=EMAIL_SA
```

---

## 👤 Autor

**Harold Adrian**

Desarrollado para auditoría y gestión de Service Accounts en GCP.

**Contacto**: DevSecOps Team

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-02-20 | 1.0.0 | Versión inicial con reporte JSON mejorado (timestamp, timezone, summary), análisis de keys y roles |
