#!/usr/bin/env pwsh
# ═══════════════════════════════════════════════════════════════════════════════
# Script de Sincronización GCP
# Sincroniza cambios entre devsecops-toolbox-azdo\gcp y devsecops-toolbox\scm\gcp
# ═══════════════════════════════════════════════════════════════════════════════

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("azdo-to-toolbox", "toolbox-to-azdo")]
    [string]$Direction = "azdo-to-toolbox",
    
    [Parameter(Mandatory=$false)]
    [switch]$WhatIf = $false
)

$ErrorActionPreference = "Stop"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
$repoAzdo = "c:\Users\harold.bolanos\repos-publics\devsecops-toolbox-azdo"
$repoToolbox = "c:\Users\harold.bolanos\repos-publics\devsecops-toolbox"
$sourceGcp = "$repoAzdo\gcp"
$targetGcp = "$repoToolbox\scm\gcp"
$logDir = "$repoToolbox\outcome"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# Crear directorio de logs si no existe
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES
# ═══════════════════════════════════════════════════════════════════════════════
function Show-Header {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║          SINCRONIZACIÓN GCP - DevSecOps Toolbox                     ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Show-Config {
    param([string]$Direction)
    
    if ($Direction -eq "azdo-to-toolbox") {
        $source = $sourceGcp
        $target = $targetGcp
    } else {
        $source = $targetGcp
        $target = $sourceGcp
    }
    
    Write-Host "📋 Configuración:" -ForegroundColor Yellow
    Write-Host "   Dirección: $Direction" -ForegroundColor White
    Write-Host "   Origen:    $source" -ForegroundColor Gray
    Write-Host "   Destino:   $target" -ForegroundColor Gray
    Write-Host ""
}

function Invoke-Sync {
    param(
        [string]$Source,
        [string]$Target,
        [string]$LogFile,
        [switch]$WhatIf
    )
    
    # Opciones de Robocopy
    $roboOptions = @(
        "/MIR"                    # Mirror - sincroniza exactamente
        "/XD", ".venv", "__pycache__", ".git"  # Excluir directorios
        "/XF", "*.pyc"            # Excluir archivos
        "/FFT"                    # Tiempos de archivo FAT
        "/Z"                      # Modo reiniciable
        "/W:5"                    # Espera entre reintentos
        "/R:3"                    # Número de reintentos
        "/NDL"                    # No listar directorios
        "/NFL"                    # No listar archivos
        "/NP"                     # No mostrar progreso
        "/TEE"                    # Mostrar en consola y log
        "/LOG:$LogFile"          # Archivo de log
    )
    
    if ($WhatIf) {
        Write-Host "🔍 MODO SIMULACIÓN - No se realizarán cambios" -ForegroundColor Magenta
        $roboOptions += "/L"  # List only - simulación
    }
    
    Write-Host "🚀 Iniciando sincronización..." -ForegroundColor Green
    Write-Host ""
    
    $exitCode = (Start-Process -FilePath "robocopy" -ArgumentList @($Source, $Target) + $roboOptions -Wait -PassThru).ExitCode
    
    # Interpretar código de salida de Robocopy
    switch ($exitCode) {
        0 { Write-Host "✅ Éxito: No se realizaron cambios" -ForegroundColor Green }
        1 { Write-Host "✅ Éxito: Se copiaron archivos" -ForegroundColor Green }
        2 { Write-Host "✅ Éxito: Se encontraron diferencias en archivos extras" -ForegroundColor Green }
        3 { Write-Host "✅ Éxito: Se copiaron archivos y hubo extras" -ForegroundColor Green }
        4 { Write-Host "⚠️  Advertencia: Errores de coincidencia" -ForegroundColor Yellow }
        5 { Write-Host "⚠️  Advertencia: Errores de copia" -ForegroundColor Yellow }
        6 { Write-Host "⚠️  Advertencia: Errores de coincidencia y extras" -ForegroundColor Yellow }
        7 { Write-Host "⚠️  Advertencia: Errores de copia y extras" -ForegroundColor Yellow }
        8 { Write-Host "❌ Error grave: No se pudo copiar" -ForegroundColor Red }
        default { Write-Host "❌ Error desconocido: Código $exitCode" -ForegroundColor Red }
    }
    
    return $exitCode
}

function Show-DiffSummary {
    param([string]$LogFile)
    
    if (Test-Path $LogFile) {
        Write-Host ""
        Write-Host "📊 Resumen del log:" -ForegroundColor Cyan
        $logContent = Get-Content $LogFile -Tail 20
        $logContent | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# EJECUCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════
Show-Header
Show-Config -Direction $Direction

# Determinar origen y destino según dirección
if ($Direction -eq "azdo-to-toolbox") {
    $source = $sourceGcp
    $target = $targetGcp
    $logFile = "$logDir\sync_azdo_to_toolbox_$timestamp.log"
} else {
    $source = $targetGcp
    $target = $sourceGcp
    $logFile = "$logDir\sync_toolbox_to_azdo_$timestamp.log"
}

# Validar existencia de directorios
if (-not (Test-Path $source)) {
    Write-Error "❌ Directorio origen no existe: $source"
    exit 1
}

# Crear directorio destino si no existe
if (-not (Test-Path $target)) {
    Write-Host "📁 Creando directorio destino: $target" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $target -Force | Out-Null
}

# Ejecutar sincronización
$exitCode = Invoke-Sync -Source $source -Target $target -LogFile $logFile -WhatIf:$WhatIf

# Mostrar resumen
Show-DiffSummary -LogFile $logFile

Write-Host ""
Write-Host "📝 Log guardado en: $logFile" -ForegroundColor Cyan
Write-Host ""

# Retornar código de salida
exit $exitCode
