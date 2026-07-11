# 📖 Guía de Uso - Health Probe Masivo

**Versión:** 1.0  
**Fecha:** 10 de Julio de 2026

---

## 🚀 Inicio Rápido

### 1. Instalación

```bash
# Clonar repositorio
git clone https://github.com/habolanos/devsecops-toolbox.git
cd devsecops-toolbox

# Instalar dependencias
pip install -r scm/azdo/health-probe-masive/requirements.txt

# Configurar credenciales
export AZDO_PAT="your_pat_token_here"
export KUBECONFIG="/path/to/kubeconfig"
```

### 2. Uso Básico

```bash
# Opción 1: Desde el launcher
python scm/main.py
# Seleccionar: 2 (AZDO) → 40 (Health Probe Masivo)

# Opción 2: Directamente
python scm/azdo/health-probe-masive/health_probe_validator.py \
  -i "deployment-web-prod,deployment-api-prod" \
  -o outcome/health_probe_report
```

### 3. Entrada de Datos

```bash
# Formato 1: Nombres de deployments
-i "deployment-web-prod,deployment-api-prod,deployment-db-prod"

# Formato 2: Definition IDs de AZDO
-i "definitionId=3388,definitionId=3389,definitionId=3390"

# Formato 3: Mixto
-i "deployment-web-prod,definitionId=3388"

# Formato 4: Desde archivo
-i @deployments.txt
```

---

## 📋 Ejemplos de Uso

### Ejemplo 1: Validación Simple

```bash
python health_probe_validator.py \
  -i "web-prod,api-prod" \
  -o outcome/health_report
```

**Salida:**
```
┌──────────────────┬────────┬────────────┬──────────┬──────────────┬─────────┐
│ Deployment       │ Stage  │ Pod Status │ Probes   │ Conectividad │ Latencia│
├──────────────────┼────────┼────────────┼──────────┼──────────────┼─────────┤
│ web-prod         │ Prod   │ 3/3 Ready  │ ✅ OK    │ ✅ OK        │ 45ms    │
│ api-prod         │ Prod   │ 2/3 Ready  │ ⚠️ Warn  │ ⚠️ Timeout   │ 5000ms  │
└──────────────────┴────────┴────────────┴──────────┴──────────────┴─────────┘
```

### Ejemplo 2: Validación con Definition IDs

```bash
python health_probe_validator.py \
  -i "definitionId=3388" \
  -o outcome/release_health
```

**Proceso:**
1. Obtiene definición de release 3388
2. Extrae stages (Dev, QA, Staging, Prod)
3. Para cada stage, valida deployments
4. Genera reporte consolidado

### Ejemplo 3: Validación Masiva (100+ deployments)

```bash
# Crear archivo con lista de deployments
cat > deployments.txt << EOF
deployment-web-prod
deployment-api-prod
deployment-cache-prod
deployment-queue-prod
deployment-db-prod
EOF

# Ejecutar validación
python health_probe_validator.py \
  -i @deployments.txt \
  -o outcome/massive_health_report \
  --workers 10 \
  --timeout 60
```

### Ejemplo 4: Exportación a Múltiples Formatos

```bash
python health_probe_validator.py \
  -i "web-prod,api-prod" \
  -o outcome/health_report \
  --format json,csv,html,excel
```

**Archivos generados:**
```
outcome/health_report.json      # Para APIs
outcome/health_report.csv       # Para Excel
outcome/health_report.html      # Para navegador
outcome/health_report.xlsx      # Con gráficos
```

---

## 🔧 Opciones Avanzadas

### Parámetros de Línea de Comandos

```bash
python health_probe_validator.py \
  -i, --input <deployments>          # Entrada (requerido)
  -o, --output <path>                # Ruta de salida (default: outcome/)
  -n, --namespace <namespace>        # Namespace K8s (default: default)
  -c, --cluster <cluster>            # Cluster K8s (default: prod)
  --workers <num>                    # Workers paralelos (default: 5)
  --timeout <seconds>                # Timeout por deployment (default: 30)
  --format <formats>                 # Formatos: json,csv,html,excel
  --cache-ttl <seconds>              # TTL de caché AZDO (default: 86400)
  --skip-connectivity                # Saltar pruebas de conectividad
  --skip-probes                      # Saltar validación de probes
  --verbose                          # Modo verbose (debug)
  --dry-run                          # Simular sin ejecutar
```

### Configuración Avanzada

```bash
# Crear archivo config.yaml
cat > config.yaml << EOF
azdo:
  org: "Coppel-Retail"
  project: "Cadena_de_Suministros"
  pat: "${AZDO_PAT}"
  api_version: "7.1"

kubernetes:
  kubeconfig: "${KUBECONFIG}"
  namespaces:
    - default
    - production
    - staging

connectivity:
  pod_image: "nicolaka/netshoot:latest"
  timeout: 30
  retries: 3

processing:
  workers: 5
  cache_ttl: 86400
  batch_size: 10

output:
  formats:
    - json
    - csv
    - html
    - excel
  directory: "outcome/health_probe"
EOF

# Usar configuración
python health_probe_validator.py \
  -i "web-prod,api-prod" \
  --config config.yaml
```

---

## 📊 Interpretación de Resultados

### Estados de Pod

| Estado | Significado | Acción |
|--------|-------------|--------|
| ✅ Ready | Todos los pods están listos | Ninguna |
| ⚠️ Partial | Algunos pods están listos | Revisar logs |
| ❌ NotReady | Ningún pod está listo | Escalar inmediatamente |

### Estados de Probes

| Estado | Significado | Acción |
|--------|-------------|--------|
| ✅ OK | Probes configurados correctamente | Ninguna |
| ⚠️ Warning | Probes configurados pero con valores bajos | Revisar timeouts |
| ❌ Error | Probes no configurados | Agregar probes |

### Estados de Conectividad

| Estado | Significado | Acción |
|--------|-------------|--------|
| ✅ OK | Conectividad normal | Ninguna |
| ⚠️ Timeout | Latencia alta (> 5000ms) | Revisar red |
| ❌ Failed | Endpoint no accesible | Revisar firewall/DNS |

### Latencia

| Rango | Evaluación | Acción |
|-------|-----------|--------|
| < 100ms | Excelente | Ninguna |
| 100-500ms | Buena | Monitorear |
| 500-5000ms | Aceptable | Revisar |
| > 5000ms | Crítica | Investigar |

---

## 🐛 Troubleshooting

### Problema: "AZDO authentication failed"

```bash
# Verificar PAT token
echo $AZDO_PAT

# Validar formato
# PAT debe ser: base64(":token")

# Regenerar PAT en AZDO
# https://dev.azure.com/Coppel-Retail/_usersSettings/tokens
```

### Problema: "Kubernetes connection refused"

```bash
# Verificar kubeconfig
kubectl config view

# Validar contexto actual
kubectl config current-context

# Cambiar contexto si es necesario
kubectl config use-context <context-name>

# Probar conexión
kubectl get nodes
```

### Problema: "Pod connectivity checker failed"

```bash
# Verificar que el pod se creó
kubectl get pods -n default | grep connectivity-checker

# Ver logs del pod
kubectl logs connectivity-checker -n default

# Verificar permisos RBAC
kubectl auth can-i create pods --as=system:serviceaccount:default:health-probe-validator
```

### Problema: "Timeout during validation"

```bash
# Aumentar timeout
python health_probe_validator.py \
  -i "web-prod" \
  --timeout 60

# Reducir workers paralelos
python health_probe_validator.py \
  -i "web-prod" \
  --workers 2

# Modo verbose para debugging
python health_probe_validator.py \
  -i "web-prod" \
  --verbose
```

---

## 📈 Casos de Uso Reales

### Caso 1: Validación Pre-Deployment

```bash
# Antes de hacer un deployment, validar que todo esté healthy
python health_probe_validator.py \
  -i "web-prod,api-prod,db-prod" \
  -o outcome/pre_deployment_check

# Si hay ⚠️ o ❌, NO hacer deployment
```

### Caso 2: Monitoreo Diario

```bash
# Ejecutar cada mañana a las 7 AM
# Agregar a cron:
# 0 7 * * * cd /path/to/toolbox && python scm/azdo/health-probe-masive/health_probe_validator.py -i @deployments.txt -o outcome/daily_health

# Generar reporte HTML para ejecutivos
python health_probe_validator.py \
  -i @deployments.txt \
  --format html \
  -o outcome/daily_health_report
```

### Caso 3: Troubleshooting de Incidentes

```bash
# Cuando hay un incidente, validar rápidamente
python health_probe_validator.py \
  -i "api-prod" \
  --verbose \
  -o outcome/incident_debug

# Revisar logs detallados
cat outcome/incident_debug.log
```

### Caso 4: Auditoría de Salud

```bash
# Auditoría trimestral de todos los deployments
python health_probe_validator.py \
  -i @all_deployments.txt \
  --format excel \
  -o outcome/quarterly_audit_$(date +%Y%m%d)

# Enviar reporte a stakeholders
```

---

## 🔐 Mejores Prácticas

### 1. Gestión de Credenciales

```bash
# ✅ CORRECTO: Variables de entorno
export AZDO_PAT=$(cat ~/.secrets/azdo_pat)
export KUBECONFIG=~/.kube/config

# ❌ INCORRECTO: Hardcoding
azdo_pat = "abc123xyz"  # ¡NUNCA!
```

### 2. Automatización

```bash
# Crear script de automatización
cat > run_health_check.sh << 'EOF'
#!/bin/bash
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="outcome/health_probe_${TIMESTAMP}"

python scm/azdo/health-probe-masive/health_probe_validator.py \
  -i @deployments.txt \
  -o "${OUTPUT_DIR}" \
  --format json,html

# Enviar notificación
if grep -q "❌" "${OUTPUT_DIR}.html"; then
  echo "CRITICAL: Health probe validation failed" | mail -s "Alert" ops@company.com
fi
EOF

chmod +x run_health_check.sh
```

### 3. Integración con CI/CD

```yaml
# .github/workflows/health-check.yml
name: Daily Health Check

on:
  schedule:
    - cron: '0 7 * * *'  # 7 AM diariamente

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r scm/azdo/health-probe-masive/requirements.txt
      
      - name: Run health check
        env:
          AZDO_PAT: ${{ secrets.AZDO_PAT }}
          KUBECONFIG: ${{ secrets.KUBECONFIG }}
        run: |
          python scm/azdo/health-probe-masive/health_probe_validator.py \
            -i @deployments.txt \
            -o outcome/health_report \
            --format html
      
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: health-report
          path: outcome/health_report.html
```

---

## 📞 Soporte

### Documentación

- 📄 [Análisis Arquitectónico](01_ANALISIS_ARQUITECTURA.md)
- 📋 [Plan de Implementación](02_PLAN_IMPLEMENTACION.md)
- 🔧 [Especificación Técnica](03_ESPECIFICACION_TECNICA.md)
- 📖 [Guía de Uso](04_GUIA_USO.md)

### Contacto

- **DevOps Team:** devops@company.com
- **GitHub Issues:** https://github.com/habolanos/devsecops-toolbox/issues
- **Slack:** #devops-toolbox

---

**Guía de Uso - COMPLETA** ✅
