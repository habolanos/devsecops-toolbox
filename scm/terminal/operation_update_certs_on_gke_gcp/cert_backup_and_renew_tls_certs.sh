#!/bin/sh
#===============================================================================
#  backup_and_renew_tls_certs.sh
#
#  1. Recorre todos los namespaces y detecta secrets tipo kubernetes.io/tls
#  2. Genera un backup YAML de cada secret en <OUTCOME>/certs-<CLUSTER>-<FECHA_HORA>/tls-backups/
#  3. Muestra un resumen en tabla (namespace, secret, expiración, días, estado)
#  4. Genera update-certs-<CLUSTER>-<FECHA_HORA>.yaml por cada ejecución,
#     usando como base el certificado nuevo de BASE_CERT_FILE (cer-io-2027.yml)
#  5. Genera evidencia-certs-<CLUSTER>-<FECHA_HORA>.html con la salida completa
#
#  Todos los artefactos quedan en un solo folder por ejecución:
#     <OUTCOME>/certs-<CLUSTER>-<FECHA_HORA>/
#       ├── tls-backups/                        (backups YAML por secret)
#       ├── update-certs-<CLUSTER>-<TS>.yaml    (manifiesto para kubectl apply)
#       └── evidencia-certs-<CLUSTER>-<TS>.html (evidencia HTML)
#
#  Resolución de <OUTCOME>:
#     1. Variable de entorno DEVSECOPS_OUTPUT_DIR (inyectada por el launcher)
#     2. scm/config.json -> global.output_dir (relativo a scm/ si no es absoluto)
#     3. <scm>/outcome por defecto
#
#  Uso: ./backup_and_renew_tls_certs.sh [--base-cert-file=<archivo.yml>]
#  Aplicar al final:   kubectl apply -f <OUTCOME>/certs-*/update-certs-*.yaml
#===============================================================================
set -eu

# ------------------------- Configuración --------------------------------------
FECHA_HORA=$(date +%Y%m%d-%H%M%S)
BASE_CERT_FILE="cer-io-2027.yml"          # Secret TLS con el certificado nuevo
DIAS_UMBRAL=0                             # 0 = incluir TODOS los certs TLS
                                          # N = solo los que expiran en <= N días
EXCLUDE_NS=""                             # Ej: "kube-system gmp-system"

ROJO='\033[0;31m'; AMAR='\033[0;33m'; VERDE='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

usage() {
  echo "Uso: $0 [--base-cert-file=<archivo.yml>]"
  echo "     $0 [--base-cert-file <archivo.yml>]"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-cert-file=*)
      BASE_CERT_FILE="${1#*=}"
      [ -n "$BASE_CERT_FILE" ] || { echo "❌ --base-cert-file requiere un valor." >&2; usage >&2; exit 1; }
      ;;
    --base-cert-file)
      [ "$#" -ge 2 ] && [ -n "$2" ] || { echo "❌ --base-cert-file requiere un valor." >&2; usage >&2; exit 1; }
      BASE_CERT_FILE="$2"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "❌ Parámetro no reconocido: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

# ------------------------- Validaciones ---------------------------------------
for cmd in kubectl jq openssl base64 mkfifo tee; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "❌ Falta el comando requerido: $cmd" >&2; exit 1
  fi
done
if ! date -d @0 >/dev/null 2>&1; then
  echo "❌ Se requiere GNU date (Linux)." >&2; exit 1
fi
if [ ! -f "$BASE_CERT_FILE" ]; then
  echo "❌ No existe el archivo base: $BASE_CERT_FILE" >&2; exit 1
fi
if ! CLUSTER_NAME=$(kubectl config view --minify -o jsonpath='{.clusters[0].name}') || [ -z "$CLUSTER_NAME" ]; then
  echo "❌ No fue posible determinar el clúster del contexto actual." >&2; exit 1
fi
CLUSTER_SAFE=$(printf '%s' "$CLUSTER_NAME" | tr -c 'A-Za-z0-9._-' '_')

# ------------------------- Directorio de salida --------------------------------
# Un solo folder por ejecución dentro del outcome global:
#   DEVSECOPS_OUTPUT_DIR > scm/config.json (global.output_dir) > <scm>/outcome
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SCM_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." 2>/dev/null && pwd || printf '%s' "$SCRIPT_DIR")

if [ -n "${DEVSECOPS_OUTPUT_DIR:-}" ]; then
  OUTCOME_BASE="$DEVSECOPS_OUTPUT_DIR"
elif [ -f "$SCM_ROOT/config.json" ]; then
  OUTCOME_BASE=$(jq -r '.global.output_dir // "outcome"' "$SCM_ROOT/config.json" 2>/dev/null)
  [ -n "$OUTCOME_BASE" ] && [ "$OUTCOME_BASE" != "null" ] || OUTCOME_BASE="outcome"
  case "$OUTCOME_BASE" in
    /*|[A-Za-z]:*) ;;                                   # ruta absoluta
    *) OUTCOME_BASE="$SCM_ROOT/$OUTCOME_BASE" ;;        # relativa a scm/
  esac
else
  OUTCOME_BASE="$SCM_ROOT/outcome"
fi

RUN_ID="${CLUSTER_SAFE}-${FECHA_HORA}"
RUN_OUTCOME="${OUTCOME_BASE}/certs-${RUN_ID}"
SUFFIX=0
while [ -e "$RUN_OUTCOME" ]; do
  SUFFIX=$((SUFFIX + 1))
  RUN_ID="${CLUSTER_SAFE}-${FECHA_HORA}-${SUFFIX}"
  RUN_OUTCOME="${OUTCOME_BASE}/certs-${RUN_ID}"
done
mkdir -p "$RUN_OUTCOME"
BACKUP_DIR="${RUN_OUTCOME}/tls-backups"
UPDATE_FILE="${RUN_OUTCOME}/update-certs-${RUN_ID}.yaml"
HTML_FILE="${RUN_OUTCOME}/evidencia-certs-${RUN_ID}.html"
SESSION_LOG=$(mktemp)
LOG_DIR=$(mktemp -d)
LOG_PIPE="${LOG_DIR}/output.pipe"
mkfifo "$LOG_PIPE"
ROWS=""
exec 3>&1 4>&2
tee "$SESSION_LOG" < "$LOG_PIPE" >&3 &
TEE_PID=$!
exec > "$LOG_PIPE" 2>&1

append_html_content() {
  awk '
    function html(value, result, i, char) {
      result = ""
      for (i = 1; i <= length(value); i++) {
        char = substr(value, i, 1)
        if (char == "&") result = result "&amp;"
        else if (char == "<") result = result "&lt;"
        else if (char == ">") result = result "&gt;"
        else result = result char
      }
      return result
    }
    function summarize(value) {
      if (length(value) > 40) return substr(value, 1, 20) "*********" substr(value, length(value) - 19)
      return value
    }
    function redact_json(line, key, secret,    marker, position, prefix, rest, closing, value, replacement) {
      marker = "\"" key "\":\""
      position = index(line, marker)
      if (!position) return line
      prefix = substr(line, 1, position + length(marker) - 1)
      rest = substr(line, position + length(marker))
      closing = index(rest, "\"")
      if (!closing) return line
      value = substr(rest, 1, closing - 1)
      replacement = secret ? "[REDACTADO]" : summarize(value)
      return prefix replacement substr(rest, closing)
    }
    /^[[:space:]]*tls\.crt:/ {
      separator = index($0, ":")
      prefix = substr($0, 1, separator)
      value = substr($0, separator + 1)
      gsub(/[[:space:]]/, "", value)
      $0 = prefix " " summarize(value)
    }
    /^[[:space:]]*tls\.key:/ { sub(/:.*/, ": [REDACTADO]") }
    {
      $0 = redact_json($0, "tls.crt", 0)
      $0 = redact_json($0, "tls.key", 1)
      gsub(/\033\[[0-9;]*m/, "")
      print html($0)
    }
  ' "$1" >> "$HTML_FILE"
}

generate_html() {
  backups=0
  cat > "$HTML_FILE" <<EOF
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Evidencia TLS - ${RUN_ID}</title>
<style>
body{font-family:Arial,sans-serif;background:#f4f6f8;color:#1f2937;margin:0;padding:24px}main{max-width:1400px;margin:auto}h1{margin-top:0}.meta{display:grid;grid-template-columns:max-content 1fr;gap:8px 16px;margin-bottom:20px}.panel{background:#fff;border-radius:10px;padding:20px;margin:18px 0;box-shadow:0 2px 10px #0002}.panel h2{margin-top:0}.file{color:#1d4ed8;margin:18px 0 8px}pre{background:#111827;color:#e5e7eb;padding:18px;border-radius:8px;overflow:auto;white-space:pre-wrap;word-break:break-word;line-height:1.4}</style>
</head>
<body><main>
<h1>Evidencia de respaldo y renovación TLS</h1>
<div class="meta"><strong>Clúster:</strong><span>${CLUSTER_SAFE}</span><strong>Ejecución:</strong><span>${FECHA_HORA}</span></div>
<section class="panel"><h2>Salida de terminal</h2><pre>
EOF
  append_html_content "$SESSION_LOG"
  printf '</pre></section>\n<section class="panel"><h2>Contenido de backups</h2>\n' >> "$HTML_FILE"
  for backup_file in "$BACKUP_DIR"/*.yaml; do
    [ -f "$backup_file" ] || continue
    backups=$((backups + 1))
    printf '<h3 class="file">%s</h3><pre>\n' "$(basename "$backup_file")" >> "$HTML_FILE"
    append_html_content "$backup_file"
    printf '</pre>\n' >> "$HTML_FILE"
  done
  [ "$backups" -gt 0 ] || printf '<p>No se generaron backups.</p>\n' >> "$HTML_FILE"
  printf '</section>\n<section class="panel"><h2>Archivo de actualización</h2>\n' >> "$HTML_FILE"
  if [ -s "$UPDATE_FILE" ]; then
    printf '<h3 class="file">%s</h3><pre>\n' "$(basename "$UPDATE_FILE")" >> "$HTML_FILE"
    append_html_content "$UPDATE_FILE"
    printf '</pre>\n' >> "$HTML_FILE"
  else
    printf '<p>No se generó contenido para actualización.</p>\n' >> "$HTML_FILE"
  fi
  printf '</section>\n</main></body>\n</html>\n' >> "$HTML_FILE"
}

on_exit() {
  EXIT_STATUS=$?
  trap - 0
  set +e
  exec 1>&3 2>&4
  wait "$TEE_PID"
  generate_html
  [ -n "$ROWS" ] && rm -f "$ROWS"
  rm -f "$SESSION_LOG" "$LOG_PIPE"
  rmdir "$LOG_DIR" 2>/dev/null || true
  printf 'Evidencia HTML generada: %s\n' "$HTML_FILE"
  exit "$EXIT_STATUS"
}
trap on_exit 0

# ------------------------- Certificado nuevo (base) ----------------------------
# Extrae el valor (base64) de un campo del bloque data: del Secret base
extract_data_field() {
  awk -v campo="$1" '
    $1 == campo { encontrado=1; sub(/^[^:]*:[[:space:]]*/, ""); valor=$0; next }
    encontrado && /^  [^[:space:]][^:]*:/ { encontrado=0 }
    encontrado { gsub(/^[[:space:]]+/, ""); valor = valor $0 }
    END { gsub(/[[:space:]]/, "", valor); print valor }
  ' "$BASE_CERT_FILE"
}

NEW_CRT=$(extract_data_field "tls.crt:")
NEW_KEY=$(extract_data_field "tls.key:")
if [ -z "$NEW_CRT" ] || [ -z "$NEW_KEY" ]; then
  echo "❌ No se pudo extraer tls.crt/tls.key de $BASE_CERT_FILE" >&2; exit 1
fi

NEW_EXPIRA=$(printf '%s' "$NEW_CRT" | base64 -d 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2-) || NEW_EXPIRA=""
CERT_PUB=$(printf '%s' "$NEW_CRT" | base64 -d 2>/dev/null | openssl x509 -noout -modulus 2>/dev/null) || CERT_PUB=""
KEY_PUB=$(printf '%s' "$NEW_KEY" | base64 -d 2>/dev/null | openssl rsa -noout -modulus 2>/dev/null) || KEY_PUB=""
if [ -z "$NEW_EXPIRA" ]; then
  echo "❌ tls.crt de $BASE_CERT_FILE no es un certificado X.509 válido." >&2; exit 1
fi
if [ -z "$CERT_PUB" ]; then
  echo "❌ No se pudo obtener la clave pública de tls.crt en $BASE_CERT_FILE." >&2; exit 1
fi
if [ -z "$KEY_PUB" ]; then
  echo "❌ tls.key de $BASE_CERT_FILE no es una llave privada RSA válida." >&2; exit 1
fi
if [ "$CERT_PUB" != "$KEY_PUB" ]; then
  echo "❌ tls.crt y tls.key de $BASE_CERT_FILE no corresponden entre sí." >&2; exit 1
fi
printf '%b\n' "${CYAN}🌐 Clúster activo     : ${CLUSTER_NAME}"
printf '%b\n' "🔑 Certificado base   : ${BASE_CERT_FILE}"
printf '%b\n' "📅 Nueva expiración   : ${NEW_EXPIRA:-desconocida}"
printf '%b\n' "🧾 Archivo de salida  : ${UPDATE_FILE}"
printf '%b\n' "📄 Evidencia HTML     : ${HTML_FILE}"
printf '%b\n' "📁 Carpeta de salida  : ${RUN_OUTCOME}${NC}"
echo ""

# ------------------------- Escaneo del clúster ---------------------------------
mkdir -p "$BACKUP_DIR"
: > "$UPDATE_FILE"
ROWS=$(mktemp)
TOTAL=0; VIGENTES=0; POR_VENCER=0; EXPIRADOS=0; INVALIDOS=0; DOCS=0
NS_REVISADOS=0; NS_ERRORES=0; BACKUP_ERRORES=0

printf '%b\n' "${CYAN}🔎 Escaneando secrets TLS en el clúster...${NC}"

if ! NAMESPACES=$(kubectl get ns -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'); then
  echo "❌ No fue posible listar los namespaces del clúster." >&2
  exit 1
fi

while IFS= read -r ns; do
  [ -z "$ns" ] && continue
  case " ${EXCLUDE_NS} " in
    *" ${ns} "*) continue ;;
  esac
  NS_REVISADOS=$((NS_REVISADOS + 1))

  if ! secrets_json=$(kubectl get secrets -n "$ns" -o json); then
    printf '%b\n' "${AMAR}⚠️  No fue posible listar los secrets del namespace ${ns}.${NC}" >&2
    NS_ERRORES=$((NS_ERRORES + 1))
    continue
  fi
  if ! secrets=$(printf '%s' "$secrets_json" | jq -r '.items[] | select(.type=="kubernetes.io/tls") | .metadata.name'); then
    printf '%b\n' "${AMAR}⚠️  Respuesta inválida al procesar el namespace ${ns}.${NC}" >&2
    NS_ERRORES=$((NS_ERRORES + 1))
    continue
  fi
  if [ -z "$secrets" ]; then continue; fi

  printf '%b\n' "🔹 Namespace: ${ns}"

  while read -r secret; do
    if [ -z "$secret" ]; then continue; fi
    TOTAL=$((TOTAL + 1))

    # 1) Backup completo del secret
    backup_file="${BACKUP_DIR}/backup-${FECHA_HORA}_${ns}_${secret}.yaml"
    if ! kubectl get secret "$secret" -n "$ns" -o yaml > "$backup_file"; then
      printf "%-38s | %-28s | %-27s | %6s | %-10s | %s\n" "$ns" "$secret" "-" "-" "ERROR" "-" >> "$ROWS"
      BACKUP_ERRORES=$((BACKUP_ERRORES + 1))
      continue
    fi

    # 2) Expiración del certificado
    cert=$(kubectl get secret "$secret" -n "$ns" -o json 2>/dev/null | \
           jq -r '.data["tls.crt"] // empty' | base64 -d 2>/dev/null) || cert=""
    if [ -z "$cert" ]; then
      printf "%-38s | %-28s | %-27s | %6s | %-10s | %s\n" "$ns" "$secret" "-" "-" "INVÁLIDO" "$(basename "$backup_file")" >> "$ROWS"
      INVALIDOS=$((INVALIDOS + 1))
      continue
    fi

    expira=$(printf '%s' "$cert" | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2-) || expira=""
    if [ -z "$expira" ] || ! expira_ts=$(date -d "$expira" +%s 2>/dev/null); then
      printf "%-38s | %-28s | %-27s | %6s | %-10s | %s\n" "$ns" "$secret" "-" "-" "INVÁLIDO" "$(basename "$backup_file")" >> "$ROWS"
      INVALIDOS=$((INVALIDOS + 1))
      continue
    fi
    dias=$(( (expira_ts - $(date +%s)) / 86400 ))

    if [ "$dias" -lt 0 ]; then
      estado="EXPIRADO";   EXPIRADOS=$((EXPIRADOS + 1))
    elif [ "$dias" -le 30 ]; then
      estado="POR VENCER"; POR_VENCER=$((POR_VENCER + 1))
    else
      estado="VIGENTE";    VIGENTES=$((VIGENTES + 1))
    fi

    printf "%-38s | %-28s | %-27s | %6s | %-10s | %s\n" \
      "$ns" "$secret" "$expira" "$dias" "$estado" "$(basename "$backup_file")" >> "$ROWS"

    # 3) Documento para el archivo de actualización
    if [ "$DIAS_UMBRAL" -eq 0 ] || [ "$dias" -le "$DIAS_UMBRAL" ]; then
      if [ "$DOCS" -gt 0 ]; then echo "---" >> "$UPDATE_FILE"; fi
      cat >> "$UPDATE_FILE" <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${secret}
  namespace: ${ns}
type: kubernetes.io/tls
data:
  tls.crt: ${NEW_CRT}
  tls.key: ${NEW_KEY}
EOF
      DOCS=$((DOCS + 1))
    fi
  done <<EOF_SECRETS
$secrets
EOF_SECRETS
done <<EOF_NAMESPACES
$NAMESPACES
EOF_NAMESPACES

# ------------------------- Tabla resumen ---------------------------------------
header=$(printf "%-38s | %-28s | %-27s | %6s | %-10s | %s" \
  "NAMESPACE" "SECRET" "EXPIRA" "DIAS" "ESTADO" "BACKUP")
sep=$(printf '%*s' "${#header}" '' | tr ' ' '-')

echo ""
printf '%b\n' "${CYAN}${header}${NC}"
echo "${sep}"

if [ -s "$ROWS" ]; then
  while IFS= read -r row; do
    case "$row" in
      *"EXPIRADO"*) printf '%b\n' "${ROJO}${row}${NC}" ;;
      *"POR VENCER"*|*"INVÁLIDO"*|*"ERROR"*) printf '%b\n' "${AMAR}${row}${NC}" ;;
      *)            printf '%b\n' "${VERDE}${row}${NC}" ;;
    esac
  done < "$ROWS"
else
  echo "No se encontraron secrets tipo TLS en ningún namespace."
fi

# ------------------------- Resumen final ---------------------------------------
echo "${sep}"
printf '%b\n' "${CYAN}🌐 Namespaces revisados   : ${NS_REVISADOS}${NC}"
printf '%b\n' "${AMAR}⚠️  Namespaces con error   : ${NS_ERRORES}${NC}"
printf '%b\n' "${CYAN}📊 Secretos TLS analizados : ${TOTAL}${NC}"
printf '%b\n' "${VERDE}✅ Vigentes               : ${VIGENTES}${NC}"
printf '%b\n' "${AMAR}⚠️  Por vencer (≤30 días)  : ${POR_VENCER}${NC}"
printf '%b\n' "${ROJO}❌ Expirados              : ${EXPIRADOS}${NC}"
printf '%b\n' "${AMAR}❓ Inválidos              : ${INVALIDOS}${NC}"
printf '%b\n' "${AMAR}⚠️  Backups con error      : ${BACKUP_ERRORES}${NC}"
printf '%b\n' "${CYAN}📦 Backups generados en   : ${BACKUP_DIR}/${NC}"

if [ "$DOCS" -gt 0 ]; then
  if ! kubectl apply --dry-run=client --validate=false -f "$UPDATE_FILE" >/dev/null; then
    echo "❌ El archivo generado no superó la validación de kubectl: $UPDATE_FILE" >&2
    exit 1
  fi
  printf '%b\n' "${CYAN}🧾 Archivo de actualización: ${UPDATE_FILE} (${DOCS} documento(s))${NC}"
  printf '%b\n' "${CYAN}   👉 Revisa el contenido y aplica con: kubectl apply -f ${UPDATE_FILE}${NC}"
else
  echo "🧾 El archivo de actualización quedó vacío (DIAS_UMBRAL=${DIAS_UMBRAL})."
fi

if [ "$NS_ERRORES" -gt 0 ] || [ "$BACKUP_ERRORES" -gt 0 ]; then
  echo "❌ El recorrido no fue completo; revisa los errores anteriores." >&2
  exit 1
fi