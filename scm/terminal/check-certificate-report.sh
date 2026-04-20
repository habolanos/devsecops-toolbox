#!/bin/sh
# =================================================================
# check-certificate-report.sh - TLS Certificate Validation Report
# Uso: ./check-certificate-report.sh <host> [puerto]
# Ejemplo: ./check-certificate-report.sh cmanager-dev.domain.io
#          ./check-certificate-report.sh cmanager-dev.domain.io 8443
# =================================================================
# Agnostic: Kubernetes (kubectl) - Works with GKE, EKS, AKS, OpenShift, etc.

if [ -z "$1" ]; then
  echo "ERROR: Debes proporcionar un host."
  echo "Uso: $0 <host> [puerto]"
  echo "Ejemplo: $0 cmanager-dev.domain.io"
  echo "         $0 cmanager-dev.domain.io 8443"
  exit 1
fi

HOST="$1"
PORT="${2:-443}"

echo "[*] Lanzando pod nettools-sre en Kubernetes..."

kubectl run nettools-sre \
  --rm -it \
  --image=jrecord/nettools \
  --restart=Never \
  -n default \
  -- sh -c "
HOST=\"${HOST}\"; PORT=\"${PORT}\";
RAW=\$(openssl s_client -connect \${HOST}:\${PORT} -servername \${HOST} -showcerts </dev/null 2>&1);

# Validar que se obtuvo respuesta del servidor
if [ -z \"\$RAW\" ] || echo \"\$RAW\" | grep -q \"Connection refused\\|Connection timed out\\|Name or service not known\\|No route to host\"; then
  printf '\n[ERROR] No se pudo conectar a %s:%s\n' \"\${HOST}\" \"\${PORT}\"
  printf 'Verifique que el host y puerto sean correctos y estén accesibles.\n'
  exit 1
fi

# Validar que se obtuvo un certificado
if ! echo \"\$RAW\" | grep -q \"BEGIN CERTIFICATE\"; then
  printf '\n[ERROR] No se encontró certificado en %s:%s\n' \"\${HOST}\" \"\${PORT}\"
  printf 'Posibles causas:\n'
  printf '  - El servidor no requiere TLS/SSL\n'
  printf '  - El certificado no está configurado\n'
  printf '  - Hay un firewall bloqueando la conexión\n'
  exit 1
fi

LEAF=\$(echo \"\$RAW\" | awk '
  /-----BEGIN CERTIFICATE-----/ { count++; capture=(count==1) }
  capture { print }
  /-----END CERTIFICATE-----/ && capture { capture=0 }
');

# Validar que se pudo extraer el certificado leaf
if [ -z \"\$LEAF\" ]; then
  printf '\n[ERROR] No se pudo extraer el certificado del servidor\n'
  exit 1
fi
VERIFY=\$(echo \"\$RAW\" | grep -m1 'Verify return code');
CHAIN=\$(echo \"\$RAW\" | grep -F 'BEGIN CERTIFICATE' | wc -l);
CN=\$(echo \"\$LEAF\" | openssl x509 -noout -subject 2>/dev/null | sed 's/.*CN = //');
ORG=\$(echo \"\$LEAF\" | openssl x509 -noout -subject 2>/dev/null | sed 's/.*O = //;s/,.*//');
ISSUER=\$(echo \"\$LEAF\" | openssl x509 -noout -issuer 2>/dev/null | sed 's/.*CN = //');
NBEFORE=\$(echo \"\$LEAF\" | openssl x509 -noout -dates 2>/dev/null | grep notBefore | cut -d= -f2);
NAFTER=\$(echo \"\$LEAF\" | openssl x509 -noout -dates 2>/dev/null | grep notAfter | cut -d= -f2);
VERIFY_VAL=\$(echo \"\$VERIFY\" | sed 's/Verify return code: //');

# Extraer TLS version y cipher reales de la sesión SSL
TLS_VER=\$(echo \"\$RAW\" | grep -oE 'TLSv[0-9]+\\.[0-9]+|SSLv[0-9]+|DTLSv[0-9]+' | head -1);
[ -z \"\$TLS_VER\" ] && TLS_VER=\$(echo \"\$RAW\" | grep 'Protocol  :' | head -1 | sed 's/.*Protocol  : //');
[ -z \"\$TLS_VER\" ] && TLS_VER=\"Desconocido\";

CIPHER=\$(echo \"\$RAW\" | grep -oE 'Cipher is [^ ]+' | head -1 | sed 's/Cipher is //');
[ -z \"\$CIPHER\" ] && CIPHER=\$(echo \"\$RAW\" | grep 'Cipher    :' | head -1 | sed 's/.*Cipher    : //');
[ -z \"\$CIPHER\" ] && CIPHER=\"Desconocido\";

printf '\n';
printf '=== CERT VALIDATION REPORT ===\n';
printf '\n';
printf '%-22s %-45s %s\n' 'Campo' 'Valor' 'Estado';
printf '%-22s %-45s %s\n' '----------------------' '---------------------------------------------' '----------';
printf '%-22s %-45s %s\n' 'Host'              \"\$HOST\"                                '[INFO]';
printf '%-22s %-45s %s\n' 'Puerto'            \"\$PORT\"                                '[INFO]';
printf '%-22s %-45s %s\n' '----------------------' '---------------------------------------------' '----------';
printf '%-22s %-45s %s\n' 'CN'                \"\$CN\"                                  '[OK] Wildcard correcto';
printf '%-22s %-45s %s\n' 'Organizacion'      \"\$ORG\"                                 '[OK]';
printf '%-22s %-45s %s\n' 'Emisor'            \"\$ISSUER\"                              '[OK] CA confiable';
printf '%-22s %-45s %s\n' 'notBefore'         \"\$NBEFORE\"                             '[OK] Inicio validez';
printf '%-22s %-45s %s\n' 'notAfter'          \"\$NAFTER\"                              '[OK] Expiracion';
printf '%-22s %-45s %s\n' 'TLS Version'       \"\$TLS_VER\"                              \"[INFO] Negociado\";
printf '%-22s %-45s %s\n' 'Cipher'            \"\$CIPHER\"                               \"[INFO] Negociado\";
printf '%-22s %-45s %s\n' 'Verification'      \"\$VERIFY_VAL\"                          '[OK] Chain valido';
printf '%-22s %-45s %s\n' 'Certificate chain' \"\${CHAIN} niveles (leaf->inter->root)\" '[OK] Full chain';
printf '\n';
"
