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

# Timeout en segundos para cada intento de conexión (puede sobrescribirse via TERMINAL_TIMEOUT)
TIMEOUT=${TERMINAL_TIMEOUT:-5}

# =============================================================================
# CONFIGURACIÓN DE CONEXIONES - ORDEN DE PRIORIDAD:
# 1. Parámetros CLI: --name y --url (si se pasan)
# 2. Variables de entorno: TERMINAL_DB_NAME + TERMINAL_DB_URL
# 3. JSON desde config: TERMINAL_DB_CONFIG (connections[] o single)
# 4. Modo interactivo (si no hay nada configurado)
# =============================================================================

declare -A DB_URLS

# Función para parsear JSON simple (solo para nuestro formato)
parse_db_config() {
    local json="$1"
    # Extraer conexiones del array "connections" (formato simple)
    # Esto es un parser básico para bash - no soporta JSON complejo
    echo "$json" | grep -o '"name"[^,}]*' | sed 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' > /tmp/db_names.txt 2>/dev/null
    echo "$json" | grep -o '"url"[^,}]*' | sed 's/.*"url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' > /tmp/db_urls.txt 2>/dev/null
    
    # Leer y combinar
    local i=0
    while read -r name && read -r url <&3; do
        [[ -n "$name" && -n "$url" ]] && DB_URLS["$name"]="$url"
        ((i++))
    done < /tmp/db_names.txt 3< /tmp/db_urls.txt 2>/dev/null
    
    rm -f /tmp/db_names.txt /tmp/db_urls.txt 2>/dev/null
}

# PRIORIDAD 1: Parámetros CLI
if [[ -n "$1" && -n "$2" ]]; then
    # Modo CLI: ./script.sh "nombre" "url"
    DB_URLS=(
        ["$1"]="$2"
    )
    echo "Usando conexión desde parámetros CLI: $1"

# PRIORIDAD 2: Variables de entorno simples
elif [[ -n "$TERMINAL_DB_NAME" && -n "$TERMINAL_DB_URL" ]]; then
    DB_URLS=(
        ["$TERMINAL_DB_NAME"]="$TERMINAL_DB_URL"
    )
    echo "Usando conexión desde variables de entorno: $TERMINAL_DB_NAME"

# PRIORIDAD 3: JSON desde config.json
elif [[ -n "$TERMINAL_DB_CONFIG" ]]; then
    # Intentar extraer del JSON
    parse_db_config "$TERMINAL_DB_CONFIG"
    if [[ ${#DB_URLS[@]} -eq 0 ]]; then
        # Si no se pudo parsear el array, intentar con "single"
        SINGLE_NAME=$(echo "$TERMINAL_DB_CONFIG" | grep -o '"single"[^}]*' | grep -o '"name"[^,]*' | sed 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
        SINGLE_URL=$(echo "$TERMINAL_DB_CONFIG" | grep -o '"single"[^}]*' | grep -o '"url"[^,]*' | sed 's/.*"url"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
        if [[ -n "$SINGLE_NAME" && -n "$SINGLE_URL" ]]; then
            DB_URLS=(
                ["$SINGLE_NAME"]="$SINGLE_URL"
            )
        fi
    fi
    echo "Usando ${#DB_URLS[@]} conexión(es) desde config.json"

# PRIORIDAD 4: Modo interactivo
else
    echo "No se encontró configuración. Modo interactivo:"
    echo ""
    read -rp "Nombre de la conexión: " conn_name
    read -rp "URL JDBC (ej: jdbc:postgresql://host:5432/db): " conn_url
    if [[ -n "$conn_name" && -n "$conn_url" ]]; then
        DB_URLS=(
            ["$conn_name"]="$conn_url"
        )
    else
        echo "Error: Se requiere nombre y URL de conexión"
        exit 1
    fi
fi

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
