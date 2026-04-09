# GCP Load Balancer Checker

Herramienta SRE para monitorear y analizar Load Balancers en Google Cloud Platform.

## 📋 Contenido

| Archivo | Descripción |
|---------|-------------|
| `gcp_load_balancer_checker.py` | Checker de Load Balancers GCP |
| `outcome/` | Directorio de salida para exportaciones |
| `README.md` | Documentación |

---

## 🎯 Características

- **Validación de conexión GCP** al inicio
- **Ejecución paralela** para mejor rendimiento
- **Múltiples vistas** para filtrar información
- **Exportación** a JSON y CSV
- **Timezone configurable**
- **Security Policies (Cloud Armor)** - Equivalente a WAF de Akamai
- **CDN Configuration** - Visualización de configuración CDN por backend
- **Comparación entre proyectos** - Compara configuraciones de seguridad entre dos proyectos

### Componentes Analizados

| Componente | Descripción |
|------------|-------------|
| **Forwarding Rules** | Reglas de reenvío globales y regionales |
| **Backend Services** | Servicios backend globales y regionales |
| **URL Maps** | Mapeos de URL para HTTP(S) LB |
| **Target Proxies** | HTTP, HTTPS, TCP y SSL proxies |
| **Health Checks** | Verificaciones de salud |
| **SSL Certificates** | Certificados SSL (managed y self-managed) |
| **SSL Policies** | Políticas de SSL |
| **Target Pools** | Pools para Network Load Balancers |
| **Backend Buckets** | Buckets de Cloud Storage como backend |
| **Security Policies** | Cloud Armor (WAF/DDoS) - Equivalente a Akamai WAF |
| **CDN Config** | Configuración de Cloud CDN por backend service |

---

## 🚀 Uso

### Requisitos

```bash
pip install rich
```

### Comandos Básicos

```bash
# Ver todos los load balancers
python gcp_load_balancer_checker.py --project mi-proyecto

# Ver solo forwarding rules
python gcp_load_balancer_checker.py --project mi-proyecto --view forwarding

# Ver solo backend services
python gcp_load_balancer_checker.py --project mi-proyecto --view backends

# Ver solo health checks
python gcp_load_balancer_checker.py --project mi-proyecto --view healthchecks

# Ver solo certificados SSL
python gcp_load_balancer_checker.py --project mi-proyecto --view ssl

# Ver Security Policies (Cloud Armor)
python gcp_load_balancer_checker.py --project mi-proyecto --view security

# Ver configuración CDN
python gcp_load_balancer_checker.py --project mi-proyecto --view cdn

# Comparar con otro proyecto
python gcp_load_balancer_checker.py --project proyecto-prod --compare proyecto-dev

# Exportar a JSON
python gcp_load_balancer_checker.py --project mi-proyecto --output json

# Exportar a CSV
python gcp_load_balancer_checker.py --project mi-proyecto --output csv

# Modo debug
python gcp_load_balancer_checker.py --project mi-proyecto --debug
```

---

## 📊 Parámetros

| Parámetro | Requerido | Descripción |
|-----------|-----------|-------------|
| `--project, -p` | ❌ | ID del proyecto GCP (Default: cpl-corp-cial-prod-17042024) |
| `--view, -v` | ❌ | Vista: `all`, `forwarding`, `backends`, `urlmaps`, `healthchecks`, `ssl`, `security`, `cdn` |
| `--output, -o` | ❌ | Exportar: `json` o `csv` |
| `--debug` | ❌ | Muestra comandos gcloud ejecutados |
| `--parallel` | ❌ | Ejecución paralela (default: activado) |
| `--no-parallel` | ❌ | Desactiva ejecución paralela |
| `--max-workers` | ❌ | Workers para paralelismo (default: 6) |
| `--timezone, -tz` | ❌ | Timezone (default: America/Mazatlan) |
| `--compare, -c` | ❌ | Compara con otro proyecto GCP (ej: `--compare proyecto-dev`) |
| `--help, -h` | ❌ | Muestra ayuda |

---

## 📈 Salida de Ejemplo

### Tabla Resumen

```
┌────────────────────────────────────────────────────────────┐
│                 📊 Resumen de Load Balancers               │
├────────────────────────────────────────────────────────────┤
│ Componente                        │ Global │ Regional │ Total │
├────────────────────────────────────────────────────────────┤
│ Forwarding Rules                  │     5  │       3  │     8 │
│ Backend Services                  │     4  │       2  │     6 │
│ URL Maps                          │     3  │       -  │     3 │
│ Target Proxies (HTTP/HTTPS/TCP)   │     6  │       -  │     6 │
│ Health Checks                     │     5  │       -  │     5 │
│ SSL Certificates                  │     4  │       -  │     4 │
│ Target Pools (Network LB)         │     -  │       2  │     2 │
└────────────────────────────────────────────────────────────┘
```

### Forwarding Rules

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          🔀 Forwarding Rules                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Nombre          │ Tipo     │ Scope    │ IP Address    │ Protocolo │ Puertos  │
├──────────────────────────────────────────────────────────────────────────────┤
│ web-frontend    │ HTTP(S)  │ Global   │ 34.120.x.x    │ TCP       │ 443      │
│ api-gateway     │ HTTP(S)  │ Global   │ 34.120.x.y    │ TCP       │ 80,443   │
│ internal-svc    │ Internal │ Regional │ 10.0.1.5      │ TCP       │ 8080     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Permisos IAM Requeridos

```yaml
roles/compute.viewer:
  - compute.forwardingRules.list
  - compute.backendServices.list
  - compute.urlMaps.list
  - compute.targetHttpProxies.list
  - compute.targetHttpsProxies.list
  - compute.healthChecks.list
  - compute.sslCertificates.list
  - compute.targetPools.list
```

O el rol predefinido: `roles/compute.networkViewer`

---

## 🏗️ Arquitectura de Load Balancers en GCP

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUJO DE TRÁFICO                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Internet                                                                    │
│     │                                                                        │
│     ▼                                                                        │
│  ┌─────────────────┐                                                         │
│  │ Forwarding Rule │  ◄── IP Externa + Puerto                                │
│  │ (Global/Regional)│                                                        │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │  Target Proxy   │  ◄── HTTP, HTTPS, TCP, SSL                              │
│  │                 │                                                         │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │    URL Map      │  ◄── Routing basado en host/path                        │
│  │  (solo HTTP/S)  │                                                         │
│  └────────┬────────┘                                                         │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐     ┌──────────────────┐                                │
│  │ Backend Service │────▶│   Health Check   │                                │
│  │                 │     │                  │                                │
│  └────────┬────────┘     └──────────────────┘                                │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │    Backends     │  ◄── Instance Groups, NEGs, Cloud Run, GKE              │
│  │                 │                                                         │
│  └─────────────────┘                                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Exportación

### JSON

Exporta todos los datos en formato JSON estructurado:

```bash
python gcp_load_balancer_checker.py --project mi-proyecto -o json
```

Archivo generado: `outcome/lb_checker_mi-proyecto_20260219_084500.json`

### CSV

Exporta las forwarding rules como tabla CSV:

```bash
python gcp_load_balancer_checker.py --project mi-proyecto -o csv
```

Archivo generado: `outcome/lb_checker_mi-proyecto_20260219_084500.csv`

---

## 🔧 Troubleshooting

### Error: No hay sesión activa de gcloud

```bash
gcloud auth login
gcloud config set project TU_PROYECTO
```

### Error: Permission denied

Verifica que tengas el rol `roles/compute.viewer` o `roles/compute.networkViewer` en el proyecto.

### Error: rich no instalado

```bash
pip install rich
```

---

## �️ Cloud Armor vs Akamai

**Akamai NO es un servicio nativo de GCP**. En GCP, los equivalentes nativos son:

| Akamai Feature | Equivalente GCP | Vista en este script |
|----------------|-----------------|----------------------|
| CDN | **Cloud CDN** | `--view cdn` |
| WAF/DDoS | **Cloud Armor** | `--view security` |
| Edge Security | **Security Policies** | `--view security` |

### Comparación de Proyectos

El modo `--compare` permite identificar diferencias de configuración entre proyectos:

```bash
# Comparar producción con desarrollo
python gcp_load_balancer_checker.py -p proyecto-prod --compare proyecto-dev
```

Muestra:
- Security Policies en cada proyecto
- Backends con CDN habilitado
- Backends con Cloud Armor
- Backends con IAP (Identity-Aware Proxy)
- Diferencias en reglas de seguridad

---

## �📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-03-25 | 1.1.0 | Security Policies (Cloud Armor), CDN Config, Comparación entre proyectos |
| 2026-02-19 | 1.0.0 | Versión inicial con soporte completo para Load Balancers |

---

## Autor

**Harold Adrian**
