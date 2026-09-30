#!/bin/sh
# =================================================================
# check-certificate-report.sh - TLS Certificate Validation Report
# Uso: ./check-certificate-report.sh <host> [puerto]
# Ejemplo: ./check-certificate-report.sh cmanager-dev.coppel.io
#          ./check-certificate-report.sh cmanager-dev.coppel.io 443
# =================================================================

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "ERROR: Debes proporcionar un host y, opcionalmente, un puerto." >&2
  echo "Uso: $0 <host> [puerto]" >&2
  echo "Ejemplo: $0 cmanager-dev.coppel.io" >&2
  echo "         $0 cmanager-dev.coppel.io 443" >&2
  exit 1
fi

HOST="$1"
PORT="${2:-443}"

case "$HOST" in
  ""|*[!A-Za-z0-9._-]*)
    echo "ERROR: Host no valido: $HOST" >&2
    exit 1
    ;;
esac

case "$PORT" in
  ""|*[!0-9]*)
    echo "ERROR: El puerto debe ser numerico." >&2
    exit 1
    ;;
esac

if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
  echo "ERROR: El puerto debe estar entre 1 y 65535." >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl no esta instalado o no esta disponible en PATH." >&2
  exit 1
fi

POD_NAME="nettools-sre-$(date +%s)-$$"
echo "[*] Lanzando pod $POD_NAME en GKE..."

kubectl run "$POD_NAME" \
  --rm -i \
  --image=jrecord/nettools \
  --restart=Never \
  --pod-running-timeout=60s \
  -n default \
  -- sh -c "
HOST=\"\$1\"; PORT=\"\$2\";
RAW=\$(openssl s_client -connect \"\${HOST}:\${PORT}\" -servername \"\$HOST\" -verify_hostname \"\$HOST\" -showcerts </dev/null 2>&1);
OPENSSL_STATUS=\$?;
LEAF=\$(printf '%s\n' \"\$RAW\" | awk '
  /-----BEGIN CERTIFICATE-----/ { count++; capture=(count==1) }
  capture { print }
  /-----END CERTIFICATE-----/ && capture { capture=0 }
');

if [ -z \"\$LEAF\" ]; then
  printf '%s\n' \"\$RAW\" >&2
  echo 'ERROR: El servidor no entrego un certificado TLS.' >&2
  exit 2
fi

VERIFY_VAL=\$(printf '%s\n' \"\$RAW\" | sed -n 's/.*Verify return code: //p' | head -n 1);
[ -n \"\$VERIFY_VAL\" ] || VERIFY_VAL='No disponible';
CHAIN=\$(printf '%s\n' \"\$RAW\" | grep -cF 'BEGIN CERTIFICATE');
SUBJECT=\$(printf '%s\n' \"\$LEAF\" | openssl x509 -noout -subject 2>/dev/null);
CN=\$(printf '%s\n' \"\$SUBJECT\" | sed 's/.*CN = //;s/,.*//');
ORG=\$(printf '%s\n' \"\$SUBJECT\" | sed 's/.*O = //;s/,.*//');
ISSUER=\$(printf '%s\n' \"\$LEAF\" | openssl x509 -noout -issuer 2>/dev/null | sed 's/.*CN = //;s/,.*//');
NBEFORE=\$(printf '%s\n' \"\$LEAF\" | openssl x509 -noout -startdate 2>/dev/null | cut -d= -f2-);
NAFTER=\$(printf '%s\n' \"\$LEAF\" | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2-);
SERIAL=\$(printf '%s\n' \"\$LEAF\" | openssl x509 -noout -serial 2>/dev/null | cut -d= -f2-);
FINGERPRINT=\$(printf '%s\n' \"\$LEAF\" | openssl x509 -noout -fingerprint -sha256 2>/dev/null | cut -d= -f2-);
TLS_VERSION=\$(printf '%s\n' \"\$RAW\" | sed -n 's/^New, \([^,]*\), Cipher is .*/\1/p; s/^ *Protocol *: *//p' | head -n 1);
CIPHER=\$(printf '%s\n' \"\$RAW\" | sed -n 's/^New, [^,]*, Cipher is //p; s/^ *Cipher *: *//p' | head -n 1);
[ -n \"\$TLS_VERSION\" ] || TLS_VERSION='No disponible';
[ -n \"\$CIPHER\" ] || CIPHER='No disponible';

RESULT=0;
case \"\$VERIFY_VAL\" in
  '0 (ok)') VERIFY_STATUS='[OK] Host y cadena validos' ;;
  '20 ('*|'21 ('*) VERIFY_STATUS='[ERROR] Cadena incompleta o no confiable'; RESULT=1 ;;
  '62 ('*) VERIFY_STATUS='[ERROR] Hostname no coincide'; RESULT=1 ;;
  '10 ('*) VERIFY_STATUS='[ERROR] Certificado vencido'; RESULT=1 ;;
  *) VERIFY_STATUS='[ERROR] Validacion fallida'; RESULT=1 ;;
esac

if [ \"\$CHAIN\" -gt 1 ]; then
  CHAIN_STATUS='[INFO] Leaf e intermedios recibidos';
else
  CHAIN_STATUS='[WARN] Solo se recibio el certificado leaf';
fi

if [ \"\$OPENSSL_STATUS\" -ne 0 ]; then
  CONNECTION_STATUS='[WARN] OpenSSL termino con error';
else
  CONNECTION_STATUS='[OK] Handshake completado';
fi

EXPIRY_TS=\$(date -d \"\$NAFTER\" +%s 2>/dev/null || printf '');
NOW_TS=\$(date +%s);
if [ -n \"\$EXPIRY_TS\" ]; then
  EXPIRY_SECONDS=\$((EXPIRY_TS - NOW_TS));
  if [ \"\$EXPIRY_SECONDS\" -ge 0 ]; then
    EXPIRY_DAYS=\$((EXPIRY_SECONDS / 86400));
    if printf '%s\n' \"\$LEAF\" | openssl x509 -checkend 2592000 -noout >/dev/null 2>&1; then
      EXPIRY_STATUS=\"[OK] Vence en \${EXPIRY_DAYS} dias\";
    else
      EXPIRY_STATUS=\"[WARN] Vence en \${EXPIRY_DAYS} dias\";
    fi
  else
    EXPIRY_DAYS=\$(((-EXPIRY_SECONDS + 86399) / 86400));
    EXPIRY_STATUS=\"[ERROR] Vencido hace \${EXPIRY_DAYS} dias\";
    RESULT=1;
  fi
else
  EXPIRY_STATUS='[WARN] No fue posible calcular los dias';
fi

case \"\$TLS_VERSION\" in
  TLSv1.3) TLS_STATUS='[OK] Version segura' ;;
  TLSv1.2) TLS_STATUS='[OK] Version aceptable' ;;
  *) TLS_STATUS='[WARN] Version antigua o desconocida' ;;
esac

printf '\n';
printf '=== CERT VALIDATION REPORT ===\n';
printf 'Fecha de ejecucion: %s\n' \"\$(date '+%Y-%m-%d %H:%M:%S %Z')\";
printf '\n';
printf '%-22s %-45s %s\n' 'Campo' 'Valor' 'Estado';
printf '%-22s %-45s %s\n' '----------------------' '---------------------------------------------' '------------------------------';
printf '%-22s %-45s %s\n' 'Host'              \"\$HOST\"                    '[INFO]';
printf '%-22s %-45s %s\n' 'Puerto'            \"\$PORT\"                    '[INFO]';
printf '%-22s %-45s %s\n' '----------------------' '---------------------------------------------' '------------------------------';
printf '%-22s %-45s %s\n' 'CN'                \"\$CN\"                      \"\$VERIFY_STATUS\";
printf '%-22s %-45s %s\n' 'Organizacion'      \"\$ORG\"                     '[INFO]';
printf '%-22s %-45s %s\n' 'Emisor'            \"\$ISSUER\"                  '[INFO]';
printf '%-22s %-45s %s\n' 'notBefore'         \"\$NBEFORE\"                 '[INFO] Inicio de validez';
printf '%-22s %-45s %s\n' 'notAfter'          \"\$NAFTER\"                  \"\$EXPIRY_STATUS\";
printf '%-22s %-45s %s\n' 'Serial'            \"\$SERIAL\"                  '[INFO]';
printf '%-22s %-45s %s\n' 'SHA256 Fingerprint' \"\$FINGERPRINT\"             '[INFO]';
printf '%-22s %-45s %s\n' 'TLS Version'       \"\$TLS_VERSION\"             \"\$TLS_STATUS\";
printf '%-22s %-45s %s\n' 'Cipher'            \"\$CIPHER\"                  '[INFO] Negociado';
printf '%-22s %-45s %s\n' 'Connection'        \"exit=\$OPENSSL_STATUS\"      \"\$CONNECTION_STATUS\";
printf '%-22s %-45s %s\n' 'Verification'      \"\$VERIFY_VAL\"              \"\$VERIFY_STATUS\";
printf '%-22s %-45s %s\n' 'Certificates sent' \"\$CHAIN\"                   \"\$CHAIN_STATUS\";
printf '\n';
exit \"\$RESULT\";
" sh "$HOST" "$PORT"
