#!/usr/bin/env bash

# =============================================================================
# Script: check_bodegamuebles_connections.sh
# Descripción: Valida conectividad a múltiples instancias PostgreSQL usando nc
# Autor: Adaptado para tu lista de conexiones
# Fecha: Febrero 2026
# Requisitos: nc (netcat) instalado
# =============================================================================

# Colores para la salida
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Timeout en segundos para cada intento de conexión
TIMEOUT=5

# Lista de conexiones (nombre y URL JDBC)
declare -A DB_URLS=(
    ["bodegamuebles30001"]="jdbc:postgresql://10.30.232.68:5432/bodegamuebles.30001?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30002"]="jdbc:postgresql://10.30.225.4:5432/bodegamuebles.30002?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30003"]="jdbc:postgresql://10.30.227.4:5432/bodegamuebles.30003?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30004"]="jdbc:postgresql://10.30.232.196:5432/bodegamuebles.30004?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30006"]="jdbc:postgresql://10.30.233.68:5432/bodegamuebles.30006?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30007"]="jdbc:postgresql://10.30.226.132:5432/bodegamuebles.30007?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30008"]="jdbc:postgresql://10.30.224.4:5432/bodegamuebles.30008?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30009"]="jdbc:postgresql://10.30.225.132:5432/bodegamuebles.30009?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30010"]="jdbc:postgresql://10.30.234.68:5432/bodegamuebles.30010?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30011"]="jdbc:postgresql://10.30.224.196:5432/bodegamuebles.30011?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30013"]="jdbc:postgresql://10.30.225.69:5432/bodegamuebles.30013?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30014"]="jdbc:postgresql://10.30.224.68:5432/bodegamuebles.30014?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30015"]="jdbc:postgresql://10.30.224.132:5432/bodegamuebles.30015?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30016"]="jdbc:postgresql://10.30.225.196:5432/bodegamuebles.30016?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30017"]="jdbc:postgresql://10.30.228.4:5432/bodegamuebles.30017?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30018"]="jdbc:postgresql://10.30.227.132:5432/bodegamuebles.30018?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30019"]="jdbc:postgresql://10.30.228.132:5432/bodegamuebles.30019?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30020"]="jdbc:postgresql://10.30.233.196:5432/bodegamuebles.30020?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30021"]="jdbc:postgresql://10.30.192.137:5432/bodegamuebles.30021?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30022"]="jdbc:postgresql://10.30.226.4:5432/bodegamuebles.30022?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30023"]="jdbc:postgresql://10.30.239.195:5432/bodegamuebles.30023?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30024"]="jdbc:postgresql://10.30.234.196:5432/bodegamuebles.30024?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30025"]="jdbc:postgresql://10.30.229.14:5432/bodegamuebles.30025?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30026"]="jdbc:postgresql://10.30.229.78:5432/bodegamuebles.30026?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30027"]="jdbc:postgresql://10.30.192.14:5432/bodegamuebles.30027?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30028"]="jdbc:postgresql://10.30.193.14:5432/bodegamuebles.30028?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30030"]="jdbc:postgresql://10.30.192.131:5432/bodegamuebles.30030?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30031"]="jdbc:postgresql://10.30.238.68:5432/bodegamuebles.30031?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30081"]="jdbc:postgresql://10.30.239.5:5432/bodegamuebles.30081?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30082"]="jdbc:postgresql://10.30.239.69:5432/bodegamuebles.30082?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30084"]="jdbc:postgresql://10.30.229.133:5432/bodegamuebles.30084?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30085"]="jdbc:postgresql://10.30.239.133:5432/bodegamuebles.30085?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
    ["bodegamuebles30086"]="jdbc:postgresql://10.30.229.197:5432/bodegamuebles.30086?currentSchema=public&ApplicationName=tms-sys-bodegamuebles&socketTimeout=180"
)

# Función para extraer IP y puerto de la URL JDBC
extract_ip_port() {
    local url="$1"
    # Extrae la parte después de // y antes del / o ?
    local host_port=$(echo "$url" | sed -E 's#^jdbc:postgresql://([^/]+).*#\1#')
    echo "$host_port"
}

# Función para validar conexión
check_connection() {
    local name="$1"
    local url="$2"
    local ip_port
    ip_port=$(extract_ip_port "$url")

    if [[ -z "$ip_port" ]]; then
        echo -e "${RED}ERROR${NC}  | $name | No se pudo extraer IP:puerto de la URL"
        return 1
    fi

    local ip="${ip_port%%:*}"
    local port="${ip_port##*:}"

    echo -n "Validando $name ($ip:$port) ... "

    # -z = modo zero-I/O (solo chequea si está abierto)
    # -w $TIMEOUT = timeout en segundos
    if nc -z -w "$TIMEOUT" "$ip" "$port" 2>/dev/null; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}ERROR (no responde o timeout)${NC}"
    fi
}

# ==================================================
# Inicio del script
# ==================================================

echo "============================================================="
echo "  Validación de conectividad a instancias bodegamuebles"
echo "  Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Timeout por conexión: ${TIMEOUT} segundos"
echo "============================================================="
echo ""

# Contadores
total=${#DB_URLS[@]}
success=0
failed=0

for name in "${!DB_URLS[@]}"; do
    if check_connection "$name" "${DB_URLS[$name]}"; then
        ((success++))
    else
        ((failed++))
    fi
done

echo ""
echo "============================================================="
echo "Resumen:"
echo "  Total conexiones verificadas: $total"
echo -e "  ${GREEN}Éxitos:${NC} $success"
echo -e "  ${RED}Fallos:${NC} $failed"
echo "============================================================="

if (( failed > 0 )); then
    echo -e "${YELLOW}¡Atención! Hay ${failed} conexiones que no responden.${NC}"
    echo "Revisa red, firewalls, estado de las instancias o DNS."
fi