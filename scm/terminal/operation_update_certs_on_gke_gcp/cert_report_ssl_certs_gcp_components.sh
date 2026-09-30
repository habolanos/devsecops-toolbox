#!/bin/sh
#===============================================================================
#  report_ssl_certs_gcp.sh   (POSIX sh: dash, busybox, bash, etc.)
#
#  Dado un PROJECT_ID de GCP, consulta todos los certificados SSL del
#  proyecto (globales y regionales), detecta su expiracion y que target
#  proxy los esta usando, y genera en terminal:
#
#   1. Tabla resumen de todos los certificados
#   2. Carta para el equipo Multicloud por cada certificado VENCIDO o
#      POR VENCER (<= UMBRAL dias). Con --todos emite la carta de todos.
#      Cada carta incluye titulo y disclaimer de no traducir literalmente.
#
#  Uso:
#     sh report_ssl_certs_gcp.sh <PROJECT_ID>            # cartas vencidos y por vencer
#     sh report_ssl_certs_gcp.sh <PROJECT_ID> --todos    # cartas de todos
#     sh report_ssl_certs_gcp.sh <PROJECT_ID> > carta.txt
#
#  Requiere: gcloud (autenticado), jq, GNU date
#===============================================================================
set -eu

PROJECT="${1:-}"
MODO="${2:-}"
UMBRAL=30   # dias restantes para considerar "POR VENCER" y emitir carta

if [ -z "$PROJECT" ]; then
  echo "Uso: $0 <PROJECT_ID> [--todos]"
  exit 1
fi

for cmd in gcloud jq; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Falta el comando requerido: $cmd"; exit 1; }
done
date -d @0 >/dev/null 2>&1 || { echo "Se requiere GNU date (Linux)."; exit 1; }

ROJO='\033[0;31m'; AMAR='\033[0;33m'; VERDE='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
NOW=$(date +%s)
HORA=$(date +%-H)
if [ "$HORA" -lt 12 ]; then
  SALUDO="Buenos Dias"
elif [ "$HORA" -lt 18 ]; then
  SALUDO="Buenas Tardes"
else
  SALUDO="Buenas Noches"
fi

PROXIES_TSV=$(mktemp); ROWS=$(mktemp); LETTERS=$(mktemp); CERTS_FILE=$(mktemp)
trap 'rm -f "$PROXIES_TSV" "$ROWS" "$LETTERS" "$CERTS_FILE"' EXIT

#-----------------------------------------------------------------------------
# 1. Inventario de target proxies (para saber donde esta en uso cada certificado)
#-----------------------------------------------------------------------------
printf '%b\n' "${CYAN}Consultando target proxies del proyecto ${PROJECT}...${NC}" >&2

# Target HTTPS proxies regionales (ILB / Cloud Run detras de LB regional)
gcloud compute target-https-proxies list --project="$PROJECT" \
  --format='value(name,region,sslCertificates)' 2>/dev/null |
  awk -F'\t' '{ c=""; for(i=3;i<=NF;i++){ s=$i; gsub(/;/," ",s);
               m=split(s,u," "); for(j=1;j<=m;j++){ if(u[j]!=""){ n=split(u[j],q,"/"); c=c q[n] " " } } }
               print $1 "\t" (($2=="")?"GLOBAL":$2) "\t" c }' >> "$PROXIES_TSV" || true

# Target HTTPS proxies globales
gcloud compute target-https-proxies list --global --project="$PROJECT" \
  --format='value(name,sslCertificates)' 2>/dev/null |
  awk -F'\t' '{ c=""; for(i=2;i<=NF;i++){ s=$i; gsub(/;/," ",s);
               m=split(s,u," "); for(j=1;j<=m;j++){ if(u[j]!=""){ n=split(u[j],q,"/"); c=c q[n] " " } } }
               print $1 "\tGLOBAL\t" c }' >> "$PROXIES_TSV" || true

# Target SSL proxies (globales, p.ej. balanceadores externos TCP/SSL)
gcloud compute target-ssl-proxies list --project="$PROJECT" \
  --format='value(name,sslCertificates)' 2>/dev/null |
  awk -F'\t' '{ c=""; for(i=2;i<=NF;i++){ s=$i; gsub(/;/," ",s);
               m=split(s,u," "); for(j=1;j<=m;j++){ if(u[j]!=""){ n=split(u[j],q,"/"); c=c q[n] " " } } }
               print $1 "\tGLOBAL\t" c }' >> "$PROXIES_TSV" || true

sort -u -o "$PROXIES_TSV" "$PROXIES_TSV" 2>/dev/null || true

#-----------------------------------------------------------------------------
# 2. Listar y describir cada certificado SSL del proyecto
#-----------------------------------------------------------------------------
printf '%b\n' "${CYAN}Consultando certificados SSL del proyecto ${PROJECT}...${NC}" >&2

gcloud compute ssl-certificates list --project="$PROJECT" \
  --format='json(name,region)' |
  jq -r '.[] | "\(.name)|\(.region // "GLOBAL")"' > "$CERTS_FILE" || true

if [ ! -s "$CERTS_FILE" ]; then
  echo "No se encontraron certificados SSL en el proyecto ${PROJECT} (o sin permisos)."
  exit 0
fi

while IFS= read -r entry; do
  name="${entry%%|*}"
  region="${entry#*|}"
  if [ "$region" != "GLOBAL" ]; then
    region="${region##*/}"
  fi

  if [ "$region" = "GLOBAL" ]; then
    detail=$(gcloud compute ssl-certificates describe "$name" --project="$PROJECT" --format=json 2>/dev/null) || detail=""
  else
    detail=$(gcloud compute ssl-certificates describe "$name" --region="$region" --project="$PROJECT" --format=json 2>/dev/null) || detail=""
  fi

  if [ -z "$detail" ]; then
    printf "%-64s | %-16s | %-13s | %-29s | %5s | %-10s | %s\n" \
      "$name" "$region" "-" "-" "-" "ERROR" "-" >> "$ROWS"
    continue
  fi

  ctype=$(printf '%s' "$detail" | jq -r '.type // "SELF_MANAGED"')
  created=$(printf '%s' "$detail" | jq -r '.creationTimestamp // ""')
  expire=$(printf '%s' "$detail" | jq -r '.expireTime // ""')
  mstatus=$(printf '%s' "$detail" | jq -r '.managed.status // ""')

  # Que proxy usa este certificado?
  usado_por=$(awk -F'\t' -v cert="$name" '$3 ~ ("(^| )" cert "( |$)") { print $1 }' "$PROXIES_TSV" | sort -u | paste -sd',' -)

  # Expiracion
  if [ -n "$expire" ]; then
    exp_ts=$(date -d "$expire" +%s 2>/dev/null || echo 0)
    dias=$(( (exp_ts - NOW) / 86400 ))
    if [ "$dias" -lt 0 ]; then
      estado="VENCIDO"
    elif [ "$dias" -le "$UMBRAL" ]; then
      estado="POR VENCER"
    else
      estado="VIGENTE"
    fi
  else
    dias="-"; estado="SIN FECHA"
  fi

  printf "%-64s | %-16s | %-13s | %-29s | %5s | %-10s | %s\n" \
    "$name" "$region" "$ctype" "${expire:--}" "$dias" "$estado" "${usado_por:-(sin uso)}" >> "$ROWS"

  #---------------------------------------------------------------------------
  # 3. Carta para el equipo Multicloud (titulo + disclaimer + cuerpo)
  #    Se emite para: VENCIDO, POR VENCER (<= UMBRAL dias) o --todos
  #---------------------------------------------------------------------------
  generar=0
  if [ "$MODO" = "--todos" ]; then
    generar=1
  elif [ "$estado" = "VENCIDO" ] || [ "$estado" = "POR VENCER" ]; then
    generar=1
  fi

  if [ "$generar" -eq 1 ]; then
    if [ -n "$usado_por" ]; then
      if [ "$estado" = "VENCIDO" ]; then
        titulo="Solicitud de actualización de certificado vencido en proyecto: ${PROJECT} / Certificado ${name}"
        asunto="Se solicita de su apoyo para actualizar el siguiente certificado vencido y que esta en uso en el proyecto de GCP: ${PROJECT}."
      elif [ "$estado" = "POR VENCER" ]; then
        titulo="Solicitud de renovación de certificado próximo a vencer en proyecto: ${PROJECT} / Certificado ${name}"
        asunto="Se solicita de su apoyo para renovar el siguiente certificado proximo a vencer (quedan ${dias} dias) y que esta en uso en el proyecto de GCP: ${PROJECT}."
      else
        titulo="Informativo de certificado en uso en proyecto: ${PROJECT} / Certificado ${name}"
        asunto="Informativo: el siguiente certificado se encuentra en uso en el proyecto de GCP: ${PROJECT}."
      fi
      despedida="En caso de que generen un nuevo certificado con otro nombre, favor de eliminar el anterior para que quede SIN USO y EXPIRADO."
    else
      if [ "$estado" = "VENCIDO" ]; then
        titulo="Solicitud de eliminación de certificado sin uso y expirado en proyecto: ${PROJECT} / Certificado ${name}"
        asunto="Se solicita de su apoyo para eliminar el siguiente certificado SIN USO y EXPIRADO del proyecto de GCP: ${PROJECT}."
      else
        titulo="Solicitud de eliminación de certificado sin uso en proyecto: ${PROJECT} / Certificado ${name}"
        asunto="Se solicita de su apoyo para eliminar el siguiente certificado SIN USO del proyecto de GCP: ${PROJECT}."
      fi
      despedida="Favor de eliminar el certificado para no dejar recursos SIN USO y EXPIRADOS en el proyecto."
    fi

    {
      echo "${titulo}"
      echo "========================================================================"
      echo
      echo "${SALUDO} Equipo Multicloud"
      echo
      echo "${asunto}"
      echo
      echo "NAME: ${name}"
      echo "TYPE: ${ctype}"
      echo "CREATION_TIMESTAMP: ${created}"
      echo "EXPIRE_TIME: ${expire}"
      echo "REGION: ${region}"
      echo "MANAGED_STATUS: ${mstatus}"
      echo
      echo "USADO POR: ${usado_por:-(sin uso)}"
      echo "SSL_CERTIFICATES: ${name}"
      echo
      echo "${despedida}"
      echo
      echo "Muchas gracias"
      echo
      echo "⚠️ Disclaimer: Do not perform a literal translation from Spanish to English."
      echo "------------------------------------------------------------------------"
      echo
    } >> "$LETTERS"
  fi
done < "$CERTS_FILE"

#-----------------------------------------------------------------------------
# 4. Salida: tabla resumen + cartas (contadores calculados sin grep -c)
#-----------------------------------------------------------------------------
VENCIDOS=0; POR_VENCER=0; VIGENTES=0; SIN_USO=0
while IFS= read -r row; do
  case "$row" in
    *"| VENCIDO "*)   VENCIDOS=$((VENCIDOS+1)) ;;
    *"| POR VENCER"*) POR_VENCER=$((POR_VENCER+1)) ;;
    *"| VIGENTE "*)   VIGENTES=$((VIGENTES+1)) ;;
  esac
  case "$row" in *"(sin uso)"*) SIN_USO=$((SIN_USO+1)) ;; esac
done < "$ROWS"
TOTAL=$(wc -l < "$ROWS" | tr -d ' ')
CARTAS=$(awk '/^={10}/{n++} END{print n+0}' "$LETTERS")

COLS="%-64s | %-16s | %-13s | %-29s | %5s | %-10s | %s"
header=$(printf "$COLS" "NAME" "REGION" "TYPE" "EXPIRE_TIME" "DIAS" "ESTADO" "USADO POR")
max_width=${#header}
while IFS= read -r row; do
  [ "${#row}" -gt "$max_width" ] && max_width=${#row}
done < "$ROWS"
sep=$(printf '%*s' "$max_width" '' | tr ' ' '-')

echo
printf '%b\n' "${CYAN}Certificados SSL del proyecto: ${PROJECT}${NC}"
printf '%s\n' "$header"
printf '%s\n' "$sep"
if [ -s "$ROWS" ]; then
  while IFS= read -r row; do
    case "$row" in
      *"VENCIDO"*|*"SIN FECHA"*|*"ERROR"*)    printf '%b\n' "${ROJO}${row}${NC}" ;;
      *"POR VENCER"*)                         printf '%b\n' "${AMAR}${row}${NC}" ;;
      *)                                      printf '%b\n' "${VERDE}${row}${NC}" ;;
    esac
  done < "$ROWS"
fi
printf '%s\n' "$sep"
printf '%b\n' "${CYAN}Total: ${TOTAL}${NC} | ${ROJO}Vencidos: ${VENCIDOS}${NC} | ${AMAR}Por vencer (<=${UMBRAL}d): ${POR_VENCER}${NC} | ${VERDE}Vigentes: ${VIGENTES}${NC} | Sin uso: ${SIN_USO}${NC}"

if [ "$CARTAS" -gt 0 ]; then
  echo
  printf '%b\n' "${CYAN}Carta(s) para el equipo Multicloud (${CARTAS}) - copia el bloque correspondiente:${NC}"
  echo
  cat "$LETTERS"
else
  echo
  echo "No se generaron cartas (no hay certificados vencidos ni por vencer en <= ${UMBRAL} dias)."
fi