# GCP Cloud Run Checker

Herramienta SRE para monitorear y analizar servicios Cloud Run en Google Cloud Platform.

## 📋 Contenido

| Archivo | Descripción |
|---------|-------------|
| `gcp_cloudrun_checker.py` | Checker de Cloud Run Services |
| `outcome/` | Directorio de salida para exportaciones |
| `README.md` | Documentación |

---

## 🎯 Características

- **Validación de conexión GCP** al inicio
- **Ejecución paralela** para mejor rendimiento
- **Múltiples vistas** para filtrar información
- **Exportación** a JSON y CSV
- **Timezone configurable**
- **Análisis de seguridad** (IAM, ingress, VPC)
- **Comparación entre proyectos**

### Componentes Analizados

| Componente | Descripción |
|------------|-------------|
| **Services** | Servicios Cloud Run desplegados |
| **Revisions** | Versiones de cada servicio |
| **Jobs** | Cloud Run Jobs (batch processing) |
| **IAM Policies** | Políticas de acceso (público vs autenticado) |
| **VPC Connectors** | Conectores a redes VPC |
| **Domain Mappings** | Dominios personalizados |
| **Ingress Settings** | Configuración de ingreso (all, internal, internal-and-cloud-load-balancing) |

---

## 🚀 Uso

### Requisitos

```bash
pip install rich
```

### Comandos Básicos

```bash
# Ver todos los servicios Cloud Run
python gcp_cloudrun_checker.py --project mi-proyecto

# Ver solo servicios
python gcp_cloudrun_checker.py --project mi-proyecto --view services

# Ver revisiones
python gcp_cloudrun_checker.py --project mi-proyecto --view revisions

# Ver configuración de seguridad (IAM, ingress, VPC)
python gcp_cloudrun_checker.py --project mi-proyecto --view security

# Ver Cloud Run Jobs
python gcp_cloudrun_checker.py --project mi-proyecto --view jobs

# Ver networking (URLs, dominios, VPC)
python gcp_cloudrun_checker.py --project mi-proyecto --view networking

# Filtrar por región
python gcp_cloudrun_checker.py --project mi-proyecto --region us-central1

# Comparar con otro proyecto
python gcp_cloudrun_checker.py --project proyecto-prod --compare proyecto-dev

# Exportar a JSON
python gcp_cloudrun_checker.py --project mi-proyecto --output json

# Exportar a CSV
python gcp_cloudrun_checker.py --project mi-proyecto --output csv

# Modo debug
python gcp_cloudrun_checker.py --project mi-proyecto --debug
```

---

## 📊 Parámetros

| Parámetro | Requerido | Descripción |
|-----------|-----------|-------------|
| `--project, -p` | ✅ | ID del proyecto GCP |
| `--region, -r` | ❌ | Región específica o 'all' (default: all) |
| `--view, -v` | ❌ | Vista: `all`, `services`, `revisions`, `security`, `jobs`, `networking` |
| `--compare, -c` | ❌ | Compara con otro proyecto GCP |
| `--output, -o` | ❌ | Exportar: `json` o `csv` |
| `--debug` | ❌ | Muestra comandos gcloud ejecutados |
| `--parallel` | ❌ | Ejecución paralela (default: activado) |
| `--no-parallel` | ❌ | Desactiva ejecución paralela |
| `--max-workers` | ❌ | Workers para paralelismo (default: 6) |
| `--timezone, -tz` | ❌ | Timezone (default: America/Mazatlan) |
| `--help, -h` | ❌ | Muestra ayuda |

---

## 📈 Salida de Ejemplo

### Tabla de Servicios

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                              🚀 Cloud Run Services                                        │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Servicio       │ Región      │ URL                          │ CPU │ Memoria │ Min/Max   │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ api-gateway    │ us-central1 │ https://api-gateway-xxx.run  │ 1   │ 512Mi   │ 1/10      │
│ web-frontend   │ us-central1 │ https://web-frontend-xxx.run │ 2   │ 1Gi     │ 0/100     │
│ worker-service │ us-east1    │ https://worker-xxx.run       │ 1   │ 256Mi   │ 0/5       │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### Tabla de Seguridad

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                              🔐 Security Configuration                                    │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Servicio       │ Región      │ Acceso       │ Ingress  │ VPC Connector │ Service Account │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ api-gateway    │ us-central1 │ 🔒 Autenticado│ internal │ vpc-connector │ api-sa@...      │
│ web-frontend   │ us-central1 │ 🌐 PÚBLICO    │ all      │ None          │ default         │
│ worker-service │ us-east1    │ 🔒 Autenticado│ internal │ vpc-connector │ worker-sa@...   │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Permisos IAM Requeridos

```yaml
roles/run.viewer:
  - run.services.list
  - run.services.get
  - run.revisions.list
  - run.jobs.list
  - run.jobs.get

roles/iam.securityReviewer:
  - run.services.getIamPolicy
```

O el rol predefinido: `roles/run.admin` (con más permisos de los necesarios)

---

## 🛡️ Análisis de Seguridad

El checker analiza los siguientes aspectos de seguridad:

| Aspecto | Descripción | Recomendación |
|---------|-------------|---------------|
| **Acceso Público** | Servicios con `allUsers` o `allAuthenticatedUsers` | Evitar a menos que sea necesario |
| **Ingress** | `all`, `internal`, `internal-and-cloud-load-balancing` | Usar `internal` cuando sea posible |
| **VPC Connector** | Conexión a redes privadas | Recomendado para servicios internos |
| **Service Account** | Identidad del servicio | Usar SA dedicada, no default |
| **Binary Authorization** | Verificación de imágenes | Activar en producción |

---

## 🔄 Comparación entre Proyectos

El modo `--compare` permite identificar diferencias entre entornos:

```bash
python gcp_cloudrun_checker.py -p proyecto-prod --compare proyecto-dev
```

Muestra:
- Total de servicios en cada proyecto
- Servicios únicos de cada proyecto
- Servicios compartidos
- Diferencias en configuración

---

## 📁 Exportación

### JSON

Exporta todos los datos en formato JSON estructurado:

```bash
python gcp_cloudrun_checker.py --project mi-proyecto -o json
```

Archivo generado: `outcome/cloudrun_checker_mi-proyecto_20260325_143000.json`

### CSV

Exporta los servicios como tabla CSV:

```bash
python gcp_cloudrun_checker.py --project mi-proyecto -o csv
```

Archivo generado: `outcome/cloudrun_checker_mi-proyecto_20260325_143000.csv`

---

## 🔧 Troubleshooting

### Error: No hay sesión activa de gcloud

```bash
gcloud auth login
gcloud config set project TU_PROYECTO
```

### Error: Permission denied

Verifica que tengas el rol `roles/run.viewer` en el proyecto.

### Error: rich no instalado

```bash
pip install rich
```

### No se muestran servicios

Verifica que:
1. El proyecto tenga servicios Cloud Run desplegados
2. La región especificada sea correcta
3. Tengas permisos de lectura

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-03-25 | 1.0.0 | Versión inicial con soporte completo para Cloud Run |

---

## Autor

**Harold Adrian**
