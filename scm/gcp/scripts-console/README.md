# Scripts de Consola para Operaciones GCP

Este directorio agrupa utilidades ligeras (shell) que se ejecutan directamente desde la consola para obtener información rápida de los clústeres GKE y validar conectividad.

## 📋 Herramientas Disponibles

| Script | Descripción | Dependencias |
|--------|-------------|--------------|
| `deployments_last_news_list.sh` | Lista los deployments más recientes (ordenados por fecha de creación) y convierte la hora a America/Mazatlan. | `kubectl`, `date`, `sort`, `head`
| `deployments_last_update_list.sh` | Muestra los deployments según el rollout más reciente (ReplicaSet actual) con timestamps locales. | `kubectl`, `date`, `sort`
| `deployments_recent_events_list.sh` | Obtiene los eventos más recientes relacionados con Deployments, coloreando por tipo (Normal/Warning). | `kubectl`, `date`, `sort`, `head`
| `db_connections_checker.sh` | Valida conectividad TCP contra múltiples instancias PostgreSQL mediante `nc`. | `nc`, `date`
| `ip_addresses_checker.sh` | Versión shell legacy para calcular la utilización de IPs en pods y servicios GKE (reemplazada por el checker Python). | `gcloud`, `kubectl`, `jq`, `awk`

## 📄 Detalle por Script

### 1. deployments_last_news_list.sh
- **Uso:** `./deployments_last_news_list.sh`
- **Descripción:**
  - Consulta todos los deployments (`kubectl get deployments --all-namespaces`).
  - Ordena por `creationTimestamp` y muestra los 15 más recientes.
  - Convierte la hora UTC a `America/Mazatlan` para facilitar la lectura local.
- **Salida:** columna con namespace, nombre, hora local y réplicas deseadas.

### 2. deployments_last_update_list.sh
- **Uso:** `./deployments_last_update_list.sh [topN] [namespace]`
  - `topN`: cantidad de resultados (default 10).
  - `namespace`: filtra un namespace específico (opcional).
- **Descripción:**
  - Recorre deployments y obtiene la `deployment.kubernetes.io/revision` actual.
  - Busca el ReplicaSet asociado a esa revisión y utiliza su `creationTimestamp` (≈ último rollout exitoso).
  - Convierte la fecha a Mazatlán y muestra namespace, deployment, timestamp, revisión, réplicas y nombre del ReplicaSet.
- **Notas:** muestra `N/A` cuando no existe ReplicaSet asociado.

### 3. deployments_recent_events_list.sh
- **Uso:** `./deployments_recent_events_list.sh [eventos] [namespace]`
  - `eventos`: cantidad de eventos a listar (default 20).
  - `namespace`: restringe la búsqueda.
- **Descripción:**
  - Ejecuta `kubectl get events` filtrando por `Deployment` y ordenando por timestamp.
  - Convierte la hora a Mazatlán e imprime namespace, deployment, hora, tipo (coloreado), razón y mensaje.
  - Colores: Verde (Normal), Amarillo (Warning), Rojo (otros).

### 4. db_connections_checker.sh
- **Uso:** `./db_connections_checker.sh`
- **Descripción:**
  - Contiene un mapa `DB_URLS` con endpoints PostgreSQL (`jdbc:postgresql://host:puerto/...`).
  - Extrae IP:puerto con `sed` y ejecuta `nc -z -w TIMEOUT` para validar la conexión.
  - Tiempo de espera por host configurable (`TIMEOUT=5`).
  - Imprime resultado por endpoint con códigos de color.
- **Requisitos:** utilidad `nc` instalada en el host que ejecuta el script.

### 5. ip_addresses_checker.sh (Legacy)
- **Uso:** `./ip_addresses_checker.sh`
- **Descripción:**
  - Recupera rangos CIDR para pods y servicios (`gcloud container clusters describe`).
  - Cuenta IPs activas usando `kubectl` (`pods` y `svc`).
  - Calcula porcentajes con `awk` y genera alertas.
- **Nota:** Este script fue reemplazado por `vpc-networks/gcp_ip_addresses_checker.py`, pero se conserva para referencia rápida desde la consola.

## 📦 Requisitos Generales
- `kubectl` autenticado contra el clúster objetivo.
- Acceso a `gcloud` (solo para `ip_addresses_checker.sh`).
- Herramientas GNU básicas: `awk`, `sed`, `sort`, `head`, `date`.
- Para scripts de timezone: compatibilidad con `TZ` (GNU date).
- Para validación de bases de datos: `nc` (netcat).

## 📁 Carpetas de Salida
Estos scripts imprimen en consola y no generan archivos. Cualquier output adicional debe almacenarse en `outcome/` (regla global del repositorio).

## 🕒 Historial

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-03-09 | 1.0.0 | Documentación inicial de los scripts de consola y clasificación por categorías |
