# ============================================================
# SCRIPT DE RESTORE - Retorno desde Backup Versionado
# ============================================================
param (
    [Parameter(Mandatory=$true)]
    [string]$backupFile,       # Ruta completa al archivo JSON de backup

    [Parameter(Mandatory=$true)]
    [string]$restoreComment,   # Comentario obligatorio explicando el motivo del rollback

    [Parameter(Mandatory=$false)]
    [string]$pat = "TU_PAT_AQUI",

    [Parameter(Mandatory=$false)]
    [string]$backupPath = ".\backups"  # Carpeta donde están los backups
)

# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================
$organization = "Coppel-Retail"
$project      = "Cadena_de_Suministros"

$base64Token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$pat"))
$headers = @{
    Authorization  = "Basic $base64Token"
    "Content-Type" = "application/json"
    Accept         = "application/json"
}

$vsrmBase = "https://vsrm.dev.azure.com/$organization/$project/_apis/release"
$apiVer   = "api-version=7.0"

# ============================================================
# FASE 1: LECTURA - Cargar y validar el archivo de backup
# ============================================================
Write-Host ">>> [FASE 1] Cargando backup desde: $backupFile" -ForegroundColor Cyan

# Verificar que el archivo existe
if (-not (Test-Path -Path $backupFile)) {

    # Si no se pasó ruta completa, intentar buscar en la carpeta de backups
    Write-Host "    ⚠️  Archivo no encontrado en ruta directa. Buscando en $backupPath..." -ForegroundColor Yellow

    $found = Get-ChildItem -Path $backupPath -Filter "*$backupFile*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

    if ($found) {
        $backupFile = $found.FullName
        Write-Host "    ✅ Backup encontrado: $backupFile" -ForegroundColor Green
    } else {
        Write-Error ">>> ❌ No se encontró ningún backup con ese nombre o versión. Abortando."
        exit 1
    }
}

# Cargar el JSON
try {
    $backup = Get-Content -Path $backupFile -Raw | ConvertFrom-Json
    Write-Host "    ✅ Backup cargado correctamente." -ForegroundColor Green
} catch {
    Write-Error ">>> ❌ Error al leer el archivo de backup. Verifica que sea un JSON válido. Detalle: $($_.Exception.Message)"
    exit 1
}

# ============================================================
# FASE 2: VALIDACIÓN - Mostrar info del backup antes de restaurar
# ============================================================
Write-Host ">>> [FASE 2] Validando contenido del backup..." -ForegroundColor Cyan

$meta     = $backup.metadata
$snapshot = $backup.releaseSnapshot

Write-Host ""
Write-Host "    ╔══════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "    ║           INFORMACIÓN DEL BACKUP                ║" -ForegroundColor Magenta
Write-Host "    ╠══════════════════════════════════════════════════╣" -ForegroundColor Magenta
Write-Host "    ║  Versión Label  : $($meta.versionLabel)" -ForegroundColor White
Write-Host "    ║  Release Origen : #$($meta.sourceReleaseId)" -ForegroundColor White
Write-Host "    ║  Fecha Backup   : $($meta.backupDate)" -ForegroundColor White
Write-Host "    ║  Generado por   : $($meta.backedUpBy)" -ForegroundColor White
Write-Host "    ║  Pipeline       : $($snapshot.releaseDefinitionName)" -ForegroundColor White
Write-Host "    ║  Artefactos     : $($snapshot.artifacts.Count)" -ForegroundColor White
Write-Host "    ║  Comentario     : $($meta.comment)" -ForegroundColor White
Write-Host "    ╚══════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# Confirmación interactiva antes de proceder
$confirm = Read-Host "    ¿Confirmas el RESTORE desde este backup? (S/N)"
if ($confirm -notin @("S", "s", "Si", "si", "SI")) {
    Write-Host ">>> 🚫 Restore cancelado por el usuario." -ForegroundColor Yellow
    exit 0
}

# ============================================================
# FASE 3: CONSTRUIR PAYLOAD - Reconstruir desde el snapshot
# ============================================================
Write-Host ">>> [FASE 3] Construyendo payload de restore desde snapshot..." -ForegroundColor Cyan

# Mapear artefactos exactos del backup
$artifactPayload = @()
foreach ($artifact in $snapshot.artifacts) {
    $artifactPayload += @{
        alias             = $artifact.alias
        instanceReference = @{
            id   = $artifact.definitionReference.version.id
            name = $artifact.definitionReference.version.name
        }
    }
}

# Descripción con trazabilidad completa del rollback
$fullDescription = "🔄 RESTORE desde backup [$($meta.versionLabel)] - Release origen #$($meta.sourceReleaseId). Motivo: $restoreComment"

$restorePayload = @{
    definitionId       = $snapshot.releaseDefinitionId
    description        = $fullDescription
    artifacts          = $artifactPayload
    isDraft            = $false
    reason             = "manual"
    manualEnvironments = @()
}

Write-Host "    ✅ Payload construido. DefinitionId: $($snapshot.releaseDefinitionId)" -ForegroundColor Green
Write-Host "    🏷️  Artefactos mapeados: $($artifactPayload.Count)" -ForegroundColor Yellow

# ============================================================
# FASE 4: POST - Crear el Release de Restore
# ============================================================
Write-Host ">>> [FASE 4] Ejecutando POST para crear el release de restore..." -ForegroundColor Cyan

$body = $restorePayload | ConvertTo-Json -Depth 20 -Compress

try {
    $restoredRelease = Invoke-RestMethod `
        -Uri "$vsrmBase/releases?$apiVer" `
        -Method POST `
        -Headers $headers `
        -Body $body

    Write-Host ""
    Write-Host ">>> ✅ RESTORE EXITOSO!" -ForegroundColor Green
    Write-Host "    Nuevo Release ID  : $($restoredRelease.id)"
    Write-Host "    Nombre            : $($restoredRelease.name)"
    Write-Host "    Backup Origen     : $($meta.versionLabel)"
    Write-Host "    Release Origen    : #$($meta.sourceReleaseId)"
    Write-Host "    Motivo Restore    : $restoreComment"
    Write-Host "    URL               : https://dev.azure.com/$organization/$project/_releaseProgress?_a=release-pipeline-progress&releaseId=$($restoredRelease.id)"

} catch {
    Write-Host ">>> ❌ ERROR al crear el release de restore:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}