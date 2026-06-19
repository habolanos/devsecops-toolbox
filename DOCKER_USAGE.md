# 🐳 Docker Usage Guide - DevSecOps Toolbox

Guía completa para usar el DevSecOps Toolbox con Docker y Docker Compose.

---

## 📋 Tabla de Contenidos

- [Requisitos Previos](#requisitos-previos)
- [Servicios Disponibles](#servicios-disponibles)
- [Configuración](#configuración)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Requisitos Previos

- Docker 20.10+
- Docker Compose 2.0+
- Credenciales configuradas localmente:
  - Azure: `~/.azure/`
  - AWS: `~/.aws/`
  - GCP: `~/.config/gcloud/`
  - Kubernetes: `~/.kube/`

---

## 🎯 Servicios Disponibles

| Servicio | Descripción | Profile | Comando |
|----------|-------------|---------|---------|
| **toolbox** | Contenedor interactivo general | default | `docker-compose up -d toolbox` |
| **toolbox-dev** | Desarrollo con código fuente montado | dev | `docker-compose --profile dev up toolbox-dev` |
| **toolbox-cmd** | Ejecutar comandos específicos | cmd | `docker-compose run --rm toolbox-cmd <comando>` |
| **toolbox-azdo** | Azure DevOps Tools | azdo | `docker-compose --profile azdo up toolbox-azdo` |
| **toolbox-gcp** | GCP Tools | gcp | `docker-compose --profile gcp up toolbox-gcp` |
| **toolbox-aws** | AWS Tools | aws | `docker-compose --profile aws up toolbox-aws` |

---

## ⚙️ Configuración

### 1. Crear `config.json`

```bash
cp scm/config.json.template scm/config.json
```

Editar `scm/config.json`:

```json
{
  "azdo": {
    "organization": "YourOrg",
    "project": "YourProject",
    "pat": "YOUR_AZURE_DEVOPS_PAT"
  },
  "gcp": {
    "project_id": "your-gcp-project",
    "region": "us-central1"
  },
  "aws": {
    "region": "us-east-1"
  }
}
```

### 2. Variables de Entorno (Opcional)

Crear `.env` en la raíz del proyecto:

```bash
# Azure
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
AZURE_SUBSCRIPTION_ID=your-subscription-id

# AWS
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=us-east-1

# GCP
GCP_PROJECT_ID=your-project-id
```

---

## 🚀 Ejemplos de Uso

### **Opción 1: Contenedor Interactivo General**

```bash
# Iniciar contenedor
docker-compose up -d toolbox

# Conectarse al contenedor
docker exec -it devsecops-toolbox /bin/bash

# Dentro del contenedor
cd /app/scm
python main.py
```

### **Opción 2: Azure DevOps Tools (Directo)**

```bash
# Ejecutar Azure DevOps Tools directamente
docker-compose --profile azdo up toolbox-azdo

# Esto ejecuta automáticamente: python scm/azdo/tools.py
# Verás el menú interactivo con las 22 herramientas de Azure DevOps
```

### **Opción 3: GCP Tools (Directo)**

```bash
# Ejecutar GCP Tools directamente
docker-compose --profile gcp up toolbox-gcp

# Esto ejecuta automáticamente: python scm/gcp/tools.py
# Verás el menú interactivo con las 25 herramientas de GCP
```

### **Opción 4: AWS Tools (Directo)**

```bash
# Ejecutar AWS Tools directamente
docker-compose --profile aws up toolbox-aws

# Esto ejecuta automáticamente: python scm/aws/tools.py
# Verás el menú interactivo con las 19 herramientas de AWS
```

### **Opción 5: Ejecutar Comandos Específicos**

```bash
# Verificar versiones de CLIs
docker-compose run --rm toolbox-cmd az version
docker-compose run --rm toolbox-cmd aws --version
docker-compose run --rm toolbox-cmd gcloud version

# Ejecutar script específico
docker-compose run --rm toolbox-cmd python /app/scm/azdo/tools.py

# Ejecutar con argumentos
docker-compose run --rm toolbox-cmd python /app/scm/azdo/rollback-pipeline.py --list-backups
```

### **Opción 6: Modo Desarrollo**

```bash
# Iniciar en modo desarrollo (código fuente montado)
docker-compose --profile dev up -d toolbox-dev

# Conectarse
docker exec -it devsecops-toolbox-dev /bin/bash

# Los cambios en el código local se reflejan inmediatamente
```

---

## 📊 Ejemplos Prácticos

### **Pipeline Updater (Azure DevOps)**

```bash
# Opción A: Modo interactivo
docker-compose --profile azdo up toolbox-azdo
# Seleccionar opción 21: Pipeline Updater

# Opción B: Comando directo
docker-compose run --rm toolbox-cmd \
  python /app/scm/azdo/update-pipeline-cd-branchconfig.py --interactive
```

### **Pipeline Rollback (Azure DevOps)**

```bash
# Listar backups disponibles
docker-compose run --rm toolbox-cmd \
  python /app/scm/azdo/rollback-pipeline.py --list-backups

# Rollback híbrido
docker-compose run --rm toolbox-cmd \
  python /app/scm/azdo/rollback-pipeline.py \
  --backup-file outcome/backups/pipeline_2758_backup_20260618_154530.json \
  --hybrid \
  --pat YOUR_PAT
```

### **GCP Inventory**

```bash
# Ejecutar inventario GKE + Cloud SQL
docker-compose --profile gcp up toolbox-gcp
# Seleccionar opción 22: Inventario GKE+Cloud SQL
```

---

## 🔍 Verificación de Instalación

```bash
# Construir imagen
docker-compose build

# Verificar herramientas instaladas
docker-compose run --rm toolbox-cmd bash -c "
  echo '=== Azure CLI ===' && az version && \
  echo '=== AWS CLI ===' && aws --version && \
  echo '=== GCloud ===' && gcloud version && \
  echo '=== Kubectl ===' && kubectl version --client && \
  echo '=== Helm ===' && helm version && \
  echo '=== Terraform ===' && terraform version
"
```

---

## 🛠️ Troubleshooting

### **Error: No se encuentra config.json**

```bash
# Crear config.json desde template
cp scm/config.json.template scm/config.json
# Editar con tus credenciales
```

### **Error: Permisos en outcome/**

```bash
# Crear directorio outcome si no existe
mkdir -p outcome/backups

# Dar permisos
chmod -R 777 outcome/
```

### **Error: Credenciales no encontradas**

```bash
# Verificar que las credenciales existen localmente
ls -la ~/.azure
ls -la ~/.aws
ls -la ~/.config/gcloud
ls -la ~/.kube

# Si no existen, configurarlas primero:
az login
aws configure
gcloud auth login
```

### **Reconstruir imagen con cambios**

```bash
# Reconstruir sin caché
docker-compose build --no-cache

# Reconstruir y reiniciar
docker-compose down
docker-compose build
docker-compose up -d toolbox
```

### **Ver logs de un servicio**

```bash
# Ver logs del servicio principal
docker-compose logs -f toolbox

# Ver logs de Azure DevOps Tools
docker-compose --profile azdo logs -f toolbox-azdo
```

---

## 📦 Volúmenes Persistentes

Los siguientes directorios se montan desde el host:

| Host | Contenedor | Descripción |
|------|------------|-------------|
| `./outcome` | `/home/devsecops/outcome` | Salidas de scripts (backups, reportes, etc.) |
| `./workspace` | `/home/devsecops/workspace` | Espacio de trabajo temporal |
| `./scm/config.json` | `/app/scm/config.json` | Configuración centralizada |
| `~/.azure` | `/home/devsecops/.azure` | Credenciales Azure (read-only) |
| `~/.aws` | `/home/devsecops/.aws` | Credenciales AWS (read-only) |
| `~/.config/gcloud` | `/home/devsecops/.config/gcloud` | Credenciales GCP (read-only) |
| `~/.kube` | `/home/devsecops/.kube` | Configuración Kubernetes (read-only) |

---

## 🎯 Mejores Prácticas

1. **Usar profiles para servicios específicos**
   ```bash
   docker-compose --profile azdo up toolbox-azdo
   ```

2. **Limpiar contenedores regularmente**
   ```bash
   docker-compose down
   docker system prune -f
   ```

3. **Actualizar imagen periódicamente**
   ```bash
   docker-compose pull
   docker-compose build --no-cache
   ```

4. **Verificar salud del contenedor**
   ```bash
   docker ps
   docker inspect devsecops-toolbox
   ```

---

## 📚 Recursos Adicionales

- [Dockerfile](./Dockerfile)
- [docker-compose.yml](./docker-compose.yml)
- [README.md](./README.md)
- [README.version.md](./README.version.md)

---

**Versión**: 1.6.10  
**Última actualización**: 2026-06-18
