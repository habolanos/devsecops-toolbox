# Extractor de Imágenes de Google Artifact Registry

Herramienta para extraer, filtrar y exportar información de imágenes Docker almacenadas en Google Artifact Registry.

## Descripción

Este conjunto de scripts permite:
- Listar todas las imágenes Docker de un repositorio en Artifact Registry
- Obtener versiones y tags de cada imagen
- Filtrar tags que sigan un patrón de versionado semántico
- Exportar los resultados a un archivo Excel formateado

## Requisitos Previos

### Google Cloud SDK
```bash
# Verificar instalación
gcloud --version

# Autenticarse
gcloud auth login

# Configurar proyecto (opcional)
gcloud config set project TU_PROYECTO
```

### Python 3 y dependencias

#### Opción 1: Instalar desde requirements.txt (recomendado)
```bash
pip3 install -r requirements.txt
```

#### Opción 2: Instalar manualmente
```bash
pip3 install pandas openpyxl
```

#### Opción 3: Usar gestor de paquetes del sistema
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3-pandas python3-openpyxl

# CentOS/RHEL
sudo yum install python3-pandas python3-openpyxl
```

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `extract-v2.sh` | Script principal que extrae información del registro |
| `tag_filter.py` | Filtra y formatea los resultados en Excel |
| `requirements.txt` | Dependencias de Python necesarias |

## Uso

### Paso 1: Instalar dependencias
```bash
pip3 install -r requirements.txt
```

### Paso 2: Dar permisos de ejecución
```bash
chmod +x extract-v2.sh
```

### Paso 3: Ejecutar el script

```bash
./extract-v2.sh [opciones]
```

**Opciones disponibles:**

| Opción | Alias | Descripción | Valor por defecto |
|--------|-------|-------------|-------------------|
| `--project` | `-p` | ID del proyecto en GCP | `cpl-xxxx-yyyy-zzzz-99999999` |
| `--repository` | `-r` | Nombre del repositorio | *Menú interactivo* |
| `--location` | `-l` | Región del repositorio | `us-central1` |
| `--all-csv-in-excel` | - | Generar un solo Excel con todos los CSVs | `false` |
| `--help` | `-h` | Mostrar ayuda | - |

### Modo interactivo (sin especificar repositorio)

Si no se especifica `--repository`, el script consultará todos los repositorios disponibles en el proyecto y mostrará un menú para seleccionar:

```
Configuración:
  PROJECT_ID: mi-proyecto-prod
  LOCATION:   us-central1

Obteniendo repositorios del proyecto...

Repositorios disponibles:
  0) TODOS los repositorios
  1) repo-backend
  2) repo-frontend
  3) repo-services

Seleccione una opción [0-3]: 
```

- **Opción 0**: Procesa todos los repositorios generando un archivo por cada uno
- **Opción 1-N**: Procesa solo el repositorio seleccionado

**Ejemplos:**
```bash
# Modo interactivo - usa valores por defecto y muestra menú de repositorios
./extract-v2.sh

# Especificar solo el proyecto
./extract-v2.sh --project mi-proyecto-prod

# Especificar proyecto y repositorio (sin menú)
./extract-v2.sh --project mi-proyecto-prod --repository docker-repo

# Usar alias cortos
./extract-v2.sh -p mi-proyecto-prod -r docker-repo -l us-east1

# El orden no importa
./extract-v2.sh -l us-east1 -r docker-repo -p mi-proyecto-prod

# Ver ayuda
./extract-v2.sh --help

# Generar un solo Excel con todos los CSVs
./extract-v2.sh --project mi-proyecto --all-csv-in-excel
```

### Paso 4: Revisar resultados
El script generará archivos en el directorio `outcome/`:
- `images_tags_<repositorio>_YYYY-MM-DD.csv` - Datos crudos por repositorio (siempre)
- `images_tags_<repositorio>_YYYY-MM-DD.xlsx` - Datos filtrados y formateados por repositorio (siempre)
- `consolidated_YYYY-MM-DD.xlsx` - Excel consolidado con todos los repositorios (con --all-csv-in-excel)

### Características adicionales

#### Barra de progreso
El script muestra barras de progreso en tiempo real durante el procesamiento:

**Progreso por repositorio:**
```
Procesando repositorio: backend-api
Encontrados 25 paquetes en backend-api
Paquetes backend-api: [====================] 85% (21/25)
```

**Barra de progreso principal de repositorios (efecto de renovación):**
Cuando se procesan múltiples repositorios, aparece una barra principal que se actualiza en tiempo real sin generar nuevas líneas:
```
Repositorios: [====================] 33% (1/3) - Procesando: backend-api
```

**Progreso cuando se procesan múltiples repositorios:**
```
Repositorios: [====================] 33% (1/3) - Procesando: backend-api

Procesando repositorio: backend-api
Encontrados 25 paquetes en backend-api
Paquetes backend-api: [====================] 100% (25/25)

=== Estadísticas del repositorio backend-api ===
Paquetes procesados: 25
Versiones procesadas: 142
Tags procesados: 67
Tiempo de procesamiento: 45s
Archivo generado: /path/to/outcome/images_tags_backend-api_2026-01-07.csv

Repositorios: [=========================] 66% (2/3) - Procesando: frontend-app

Procesando repositorio: frontend-app
Encontrados 20 paquetes en frontend-app
Paquetes frontend-app: [=========-] 40% (8/20)
```

#### Estadísticas de procesamiento
El script muestra estadísticas detalladas en dos niveles:

**Estadísticas por repositorio (después de procesar cada uno):**
```
=== Estadísticas del repositorio backend-api ===
Paquetes procesados: 25
Versiones procesadas: 142
Tags procesados: 67
Tiempo de procesamiento: 45s
Archivo generado: /path/to/outcome/images_tags_backend-api_2026-01-07.csv
```

**Estadísticas finales globales (al final del proceso):**
```
=== ESTADÍSTICAS FINALES ===
Total de repositorios procesados: 3
Total de paquetes procesados: 156
Total de versiones procesadas: 892
Total de tags procesados: 423
Tiempo total de procesamiento: 245s
Directorio de salida: /path/to/outcome
```

**Ejemplo completo de ejecución:**
```
$ ./extract-v2.sh --project mi-proyecto --all-csv-in-excel

Configuración:
  PROJECT_ID: mi-proyecto
  LOCATION:   us-central1

Obteniendo repositorios del proyecto...

Repositorios disponibles:
  0) TODOS los repositorios
  1) backend-api
  2) frontend-app
  3) data-processor

Seleccione una opción [0-3]: 0

Procesando todos los repositorios...

Repositorios: [====================] 33% (1/3) - Procesando: backend-api

Procesando repositorio: backend-api
Encontrados 25 paquetes en backend-api
Paquetes backend-api: [====================] 100% (25/25)

=== Estadísticas del repositorio backend-api ===
Paquetes procesados: 25
Versiones procesadas: 142
Tags procesados: 67
Tiempo de procesamiento: 45s
Archivo generado: /path/to/outcome/images_tags_backend-api_2026-01-07.csv

Repositorios: [=========================] 66% (2/3) - Procesando: frontend-app

Procesando repositorio: frontend-app
Encontrados 20 paquetes en frontend-app
Paquetes frontend-app: [====================] 100% (20/20)

=== Estadísticas del repositorio frontend-app ===
Paquetes procesados: 20
Versiones procesadas: 89
Tags procesados: 43
Tiempo de procesamiento: 38s
Archivo generado: /path/to/outcome/images_tags_frontend-app_2026-01-07.csv

Repositorios: [============================] 100% (3/3) - Procesando: data-processor

Procesando repositorio: data-processor
Encontrados 15 paquetes en data-processor
Paquetes data-processor: [====================] 100% (15/15)

=== Estadísticas del repositorio data-processor ===
Paquetes procesados: 15
Versiones procesadas: 67
Tags procesados: 31
Tiempo de procesamiento: 32s
Archivo generado: /path/to/outcome/images_tags_data-processor_2026-01-07.csv

Generando Excel consolidado con todos los CSVs...
CSV consolidado temporal: /path/to/outcome/consolidated_2026-01-07.csv
Excel consolidado generado: /path/to/outcome/consolidated_2026-01-07.xlsx

=== ESTADÍSTICAS FINALES ===
Total de repositorios procesados: 3
Total de paquetes procesados: 156
Total de versiones procesadas: 892
Total de tags procesados: 423
Tiempo total de procesamiento: 245s
Directorio de salida: /path/to/outcome

Proceso completado.
```

## Filtros Aplicados

El script `tag_filter.py` aplica los siguientes filtros:

| Filtro | Descripción | Ejemplo Válido |
|--------|-------------|----------------|
| Patrón de versión | `^\d+(\.\d+)*-[a-zA-Z]+$` | `1.0.0-release`, `2.1-beta` |
| Exclusión | Tags con `-master` | Se excluye `1.0.0-master` |

## Estructura del Excel de Salida

| Columna | Descripción |
|---------|-------------|
| `nombre_componente` | Nombre del paquete/imagen |
| `version` | SHA o identificador de versión |
| `tag` | Etiqueta asignada a la imagen |
| `fecha_creacion` | Fecha de creación (ordenado descendente) |

## Uso Avanzado: Construir URI de Imagen

Para hacer pull o push de una imagen específica, usa este formato:

```bash
IMAGE_URI="${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${PACKAGE}:${TAG}"

# Ejemplo concreto:
docker pull us-central1-docker.pkg.dev/mi-proyecto/mi-repo/mi-imagen:1.0.0-release
```

### Iterar sobre múltiples tags
```bash
for TAG in $TAGS; do
    IMAGE_URI="${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${PACKAGE}:${TAG}"
    echo "Procesando: $IMAGE_URI"
    # docker pull $IMAGE_URI
done
```

## Solución de Problemas

### Error de permisos en GCP
```bash
# Verificar acceso al repositorio
gcloud artifacts repositories describe $REPOSITORY \
    --project=$PROJECT_ID \
    --location=$LOCATION
```

### Error de Python
```bash
# Verificar dependencias
pip list | grep -E "pandas|openpyxl"
```

## Autor

**Harold Adrian**

---

## 📜 Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2026-01-12 | 1.1.0 | Actualización de documentación: añadida tabla de historial de cambios |
| 2025-01-07 | 1.0.0 | Versión inicial con extracción de imágenes, filtrado de tags y exportación a Excel |
