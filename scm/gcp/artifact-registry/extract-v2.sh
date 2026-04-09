#!/bin/bash

# Obtener el directorio donde está el script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Valores por defecto
DEFAULT_PROJECT_ID="cpl-corp-cial-prod-17042024"
DEFAULT_LOCATION="us-central1"

# Inicializar variables
PROJECT_ID="$DEFAULT_PROJECT_ID"
LOCATION="$DEFAULT_LOCATION"
REPOSITORY=""
ALL_CSV_IN_EXCEL=false

# Crear directorio de salida
OUTCOME_DIR="$SCRIPT_DIR/outcome"
mkdir -p "$OUTCOME_DIR"

# Variables para estadísticas
TOTAL_PACKAGES=0
TOTAL_VERSIONS=0
TOTAL_TAGS=0
START_TIME=$(date +%s)

# Mostrar ayuda
show_help() {
    echo "Uso: $0 [opciones]"
    echo ""
    echo "Opciones:"
    echo "  --project, -p     ID del proyecto en GCP (default: $DEFAULT_PROJECT_ID)"
    echo "  --repository, -r  Nombre del repositorio (si no se especifica, muestra menú)"
    echo "  --location, -l    Región del repositorio (default: $DEFAULT_LOCATION)"
    echo "  --all-csv-in-excel Generar un solo Excel con todos los CSVs al final"
    echo "  --help, -h        Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0"
    echo "  $0 --project mi-proyecto"
    echo "  $0 --project mi-proyecto --repository mi-repo"
    echo "  $0 --project mi-proyecto --all-csv-in-excel"
    echo "  $0 -p mi-proyecto -r mi-repo -l us-east1 --all-csv-in-excel"
    exit 0
}

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --project|-p)
            PROJECT_ID="$2"
            shift 2
            ;;
        --repository|-r)
            REPOSITORY="$2"
            shift 2
            ;;
        --location|-l)
            LOCATION="$2"
            shift 2
            ;;
        --all-csv-in-excel)
            ALL_CSV_IN_EXCEL=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo "Opción desconocida: $1"
            echo "Use --help para ver las opciones disponibles"
            exit 1
            ;;
    esac
done

# Función para mostrar barra de progreso
show_progress() {
    local current=$1
    local total=$2
    local desc=$3
    
    # Validar que total no sea 0
    if [ "$total" -eq 0 ]; then
        return 1
    fi
    
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r%s: [" "$desc"
    printf "%*s" $filled | tr ' ' '='
    printf "%*s" $empty | tr ' ' '-'
    printf "] %d%% (%d/%d)" $percentage $current $total
}

# Función para mostrar barra de progreso de repositorios (con efecto de renovación)
show_repo_progress() {
    local current=$1
    local total=$2
    local repo_name=$3
    
    # Validar que total no sea 0
    if [ "$total" -eq 0 ]; then
        return 1
    fi
    
    local width=60
    local percentage=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    # Mover cursor a la línea de repositorios (línea 3 desde arriba)
    printf "\033[3A"
    
    # Limpiar línea completa y mostrar nueva barra
    printf "\r\033[KRepositorios: ["
    printf "%*s" $filled | tr ' ' '='
    printf "%*s" $empty | tr ' ' '-'
    printf "] %d%% (%d/%d) - Procesando: %s" $percentage $current $total "$repo_name"
    
    # Volver cursor al final del documento
    printf "\033[3B"
}

# Función para procesar un repositorio
process_repository() {
    local REPO=$1
    local OUTPUT_FILE="$OUTCOME_DIR/images_tags_${REPO}_$(date '+%Y-%m-%d').csv"
    local REPO_START_TIME=$(date +%s)
    local REPO_PACKAGES=0
    local REPO_VERSIONS=0
    local REPO_TAGS=0
    
    echo ""
    echo "Procesando repositorio: $REPO"
    echo "nombre_componente,version,tag,fecha_creacion" > $OUTPUT_FILE

    # Obtener todos los paquetes en el repositorio
    local PACKAGES=($(gcloud artifacts packages list \
        --project=$PROJECT_ID \
        --repository=$REPO \
        --location=$LOCATION \
        --format="value(name)" 2>/dev/null))
    
    local PACKAGE_COUNT=${#PACKAGES[@]}
    echo "Encontrados $PACKAGE_COUNT paquetes en $REPO"
    
    for i in "${!PACKAGES[@]}"; do
        local PACKAGE="${PACKAGES[$i]}"
        REPO_PACKAGES=$((REPO_PACKAGES + 1))
        TOTAL_PACKAGES=$((TOTAL_PACKAGES + 1))
        
        show_progress $((i + 1)) $PACKAGE_COUNT "Paquetes $REPO"
        
        # Obtener todas las versiones de este paquete
        local VERSIONS=$(gcloud artifacts versions list \
            --project=$PROJECT_ID \
            --repository=$REPO \
            --location=$LOCATION \
            --package=$PACKAGE \
            --format="csv(name,createTime)" 2>/dev/null)

        # Obtener todas las etiquetas para todos los paquetes
        local TAGS=$(gcloud artifacts tags list \
            --project=$PROJECT_ID \
            --repository=$REPO \
            --location=$LOCATION \
            --package=$PACKAGE \
            --format="csv(name,version)" 2>/dev/null)

        # Procesar cada versión
        echo "$VERSIONS" | while IFS=, read -r VERSION CREATION_DATE; do
            REPO_VERSIONS=$((REPO_VERSIONS + 1))
            TOTAL_VERSIONS=$((TOTAL_VERSIONS + 1))
            
            # Buscar las etiquetas correspondientes a la versión
            MATCHING_TAGS=$(echo "$TAGS" | grep ",$VERSION$" | cut -d, -f1)

            if [ -z "$MATCHING_TAGS" ]; then
                # Si no hay etiquetas, escribir la versión sin etiqueta
                echo "$PACKAGE,$VERSION,,${CREATION_DATE}" >> $OUTPUT_FILE
            else
                # Escribir las versiones con sus etiquetas
                for TAG in $MATCHING_TAGS; do
                    REPO_TAGS=$((REPO_TAGS + 1))
                    TOTAL_TAGS=$((TOTAL_TAGS + 1))
                    echo "$PACKAGE,$VERSION,$TAG,$CREATION_DATE}" >> $OUTPUT_FILE
                done
            fi
        done
    done
    echo ""
    
    # Estadísticas del repositorio
    local REPO_END_TIME=$(date +%s)
    local REPO_DURATION=$((REPO_END_TIME - REPO_START_TIME))
    
    echo "=== Estadísticas del repositorio $REPO ==="
    echo "Paquetes procesados: $REPO_PACKAGES"
    echo "Versiones procesadas: $REPO_VERSIONS"
    echo "Tags procesados: $REPO_TAGS"
    echo "Tiempo de procesamiento: ${REPO_DURATION}s"
    echo "Archivo generado: $OUTPUT_FILE"
    echo ""
    
    # Procesar con tag_filter.py
    python3 "$SCRIPT_DIR/tag_filter.py" $OUTPUT_FILE
}

# Función para generar un Excel con todos los CSVs
create_all_csv_excel() {
    local CONSOLIDATED_FILE="$OUTCOME_DIR/consolidated_$(date '+%Y-%m-%d').csv"
    local HEADER="nombre_componente,version,tag,fecha_creacion,repositorio"
    
    echo "Generando Excel consolidado con todos los CSVs..."
    echo "$HEADER" > "$CONSOLIDATED_FILE"
    
    for csv_file in "$OUTCOME_DIR"/images_tags_*.csv; do
        if [ -f "$csv_file" ] && [[ ! "$csv_file" =~ consolidated_ ]]; then
            local repo_name=$(basename "$csv_file" | sed 's/images_tags_//' | sed 's/_[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}\.csv$//')
            
            # Omitir la primera línea (header) y agregar el nombre del repositorio
            tail -n +2 "$csv_file" | while IFS= read -r line; do
                echo "$line,$repo_name" >> "$CONSOLIDATED_FILE"
            done
        fi
    done
    
    echo "CSV consolidado temporal: $CONSOLIDATED_FILE"
    
    # Generar Excel directamente desde el CSV consolidado
    python3 "$SCRIPT_DIR/tag_filter.py" "$CONSOLIDATED_FILE"
    
    # Eliminar el CSV temporal (solo dejar el Excel)
    rm "$CONSOLIDATED_FILE"
    
    echo "Excel consolidado generado: ${CONSOLIDATED_FILE%.csv}.xlsx"
}

echo "Configuración:"
echo "  PROJECT_ID: $PROJECT_ID"
echo "  LOCATION:   $LOCATION"
echo ""

# Si se pasa el repositorio como parámetro, usarlo directamente
if [ -n "$REPOSITORY" ]; then
    echo "Repositorio: $REPOSITORY"
    process_repository "$REPOSITORY"
else
    # Obtener lista de repositorios del proyecto
    echo "Obteniendo repositorios del proyecto..."
    REPOS=($(gcloud artifacts repositories list \
        --project=$PROJECT_ID \
        --location=$LOCATION \
        --format="value(name)" 2>/dev/null))

    if [ ${#REPOS[@]} -eq 0 ]; then
        echo "No se encontraron repositorios en el proyecto $PROJECT_ID"
        exit 1
    fi

    echo ""
    echo "Repositorios disponibles:"
    echo "  0) TODOS los repositorios"
    for i in "${!REPOS[@]}"; do
        echo "  $((i+1))) ${REPOS[$i]}"
    done
    echo ""

    read -p "Seleccione una opción [0-${#REPOS[@]}]: " SELECTION

    if [ "$SELECTION" -eq 0 ] 2>/dev/null; then
        # Procesar todos los repositorios
        echo "Procesando todos los repositorios..."
        echo ""
        echo ""
        echo ""
        
        REPO_COUNT=${#REPOS[@]}
        for i in "${!REPOS[@]}"; do
            REPO="${REPOS[$i]}"
            show_repo_progress $((i + 1)) $REPO_COUNT "$REPO"
            process_repository "$REPO"
        done
    elif [ "$SELECTION" -ge 1 ] && [ "$SELECTION" -le ${#REPOS[@]} ] 2>/dev/null; then
        # Procesar repositorio seleccionado
        SELECTED_REPO="${REPOS[$((SELECTION-1))]}"
        process_repository "$SELECTED_REPO"
    else
        echo "Opción inválida: $SELECTION"
        exit 1
    fi
fi

# Estadísticas finales y consolidación
END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

# Limpiar barra de progreso de repositorios
printf "\033[3A\r\033[K\033[3B"

echo ""
echo "=== ESTADÍSTICAS FINALES ==="
echo "Total de repositorios procesados: $([ "$REPOSITORY" ] && echo "1" || echo "${#REPOS[@]}")"
echo "Total de paquetes procesados: $TOTAL_PACKAGES"
echo "Total de versiones procesadas: $TOTAL_VERSIONS"
echo "Total de tags procesados: $TOTAL_TAGS"
echo "Tiempo total de procesamiento: ${TOTAL_DURATION}s"
echo "Directorio de salida: $OUTCOME_DIR"

# Si se solicitó --all-csv-in-excel, generar Excel consolidado
if [ "$ALL_CSV_IN_EXCEL" = true ]; then
    echo ""
    create_all_csv_excel
fi

echo ""
echo "Proceso completado."
