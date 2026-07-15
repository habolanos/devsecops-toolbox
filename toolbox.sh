#!/bin/bash
# DevSecOps Toolbox - Wrapper para Linux/macOS
# Ejecuta el toolbox desde cualquier ubicación
#
# Uso: ./toolbox.sh [argumentos]

# Obtener directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verificar que el ejecutable existe
if [ ! -f "$SCRIPT_DIR/dist/toolbox" ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                      ERROR: Ejecutable no encontrado           ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "El archivo dist/toolbox no existe."
    echo ""
    echo "Opciones:"
    echo "  1. Compilar ejecutable:"
    echo "     python3 build_executables.py"
    echo ""
    echo "  2. Descargar ejecutable precompilado:"
    echo "     https://github.com/habolanos/devsecops-toolbox/releases"
    echo ""
    echo "  3. Usar Python directamente:"
    echo "     python3 scm/main.py"
    echo ""
    exit 1
fi

# Dar permisos de ejecución si es necesario
if [ ! -x "$SCRIPT_DIR/dist/toolbox" ]; then
    chmod +x "$SCRIPT_DIR/dist/toolbox"
fi

# Ejecutar el toolbox
"$SCRIPT_DIR/dist/toolbox" "$@"
