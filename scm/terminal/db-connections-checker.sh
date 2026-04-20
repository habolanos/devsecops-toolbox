#!/usr/bin/env bash

# =============================================================================
# Script: db-connections-checker.sh
# Descripción: Valida conectividad a múltiples instancias PostgreSQL usando nc
# Uso: ./db-connections-checker.sh
# Requisitos: nc (netcat) instalado
# =============================================================================
# Agnostic: PostgreSQL connection checker using netcat

# Colores para la salida
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Timeout en segundos para cada intento de conexión
TIMEOUT=5

# Lista de conexiones (nombre y URL JDBC) - MODIFICAR SEGÚN NECESIDAD
declare -A DB_URLS=(
    ["example-db1"]="jdbc:postgresql://10.0.0.1:5432/database1?currentSchema=public"
    ["example-db2"]="jdbc:postgresql://10.0.0.2:5432/database2?currentSchema=public"
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
        return 0
    else
        echo -e "${RED}ERROR (no responde o timeout)${NC}"
        return 1
    fi
}

# ==================================================
# Inicio del script
# ==================================================

echo "============================================================="
echo "  Validación de conectividad a instancias PostgreSQL"
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
