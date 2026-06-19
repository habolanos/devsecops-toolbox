# ============================================================
# PARÁMETROS DE ENTRADA
# ============================================================
param (
    [Parameter(Mandatory=$false)]
    [int]$sourceReleaseId = 987,

    [Parameter(Mandatory=$false)]
    [string]$pat = "TU_PAT_AQUI",

    [Parameter(Mandatory=$true)]
    [string]$releaseComment,  # Comentario obligatorio para el nuevo release

    [Parameter(Mandatory=$false)]
    [string]$backupPath = ".\backups"  # Carpeta donde se guardarán los backups
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

# Crear carpeta de backups si no existe
if (-not (Test-Path -Path $backupPath)) {
    New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
    Write-Host ">>> Carpeta de backups creada: $backupPath" -ForegroundColor DarkGray
}

# ============================================================
# FASE 1: GET - Consultar info del Release Origen
# ============================================================
Write-Host ">>> [FASE 1] Obteniendo info del Release fuente #$sourceReleaseId..." -ForegroundColor Cyan

try {
    $sourceRelease = Invoke-RestMethod -Uri "$vsrmBase/releases/$sourceReleaseId`?$apiVer" -Method GET -Headers $headers
    Write-Host "    ✅ Release encontrado: $($sourceRelease.name)" -ForegroundColor Green
} catch {
    Write-Error ">>> ❌ No se pudo obtener el release origen. Verifica ID o permisos. Detalle: $($_.Exception.Message)"
    exit 1
}

# ============================================================
# FASE 2: BACKUP - Guardar snapshot versionado del release
# ============================================================
Write-Host ">>> [FASE 2] Generando backup versionado del release origen..." -ForegroundColor Cyan

# Número de versión: combinamos ReleaseID + Timestamp (formato ordenable)
$timestamp     = Get-Date -Format "yyyyMMdd_HHmmss"
$versionLabel  = "REL_$sourceReleaseId`_$timestamp"
$backupFile    = Join-Path $backupPath "release_backup_$versionLabel.json"

# Extraemos los datos críticos para poder "retornar" o auditar
$backupData = @{
    metadata = @{
        versionLabel    = $versionLabel
        sourceReleaseId = $sourceReleaseId
        backupDate      = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        backedUpBy      = $env:USERNAME
        comment         = $releaseComment
    }
    releaseSnapshot = @{
        releaseDefinitionId   = $sourceRelease.releaseDefinition.id
        releaseDefinitionName = $sourceRelease.releaseDefinition.name
        originalDescription   = $sourceRelease.description
        originalStatus        = $sourceRelease.status
        createdOn             = $sourceRelease.createdOn
        modifiedOn            = $sourceRelease.modifiedOn
        createdBy             = $sourceRelease.createdBy.displayName
        artifacts             = $sourceRelease.artifacts
        variables             = $sourceRelease.variables
        environments          = $sourceRelease.environments | Select-Object id, name, status, variables
    }
}

# Guardamos el backup en disco
$backupData | ConvertTo-Json -Depth 20 | Out-File -FilePath $backupFile -Encoding utf8

Write-Host "    ✅ Backup guardado: $backupFile" -ForegroundColor Green
Write-Host "    🏷️  Versión: $versionLabel" -ForegroundColor Yellow

# ============================================================
# FASE 3: Construir Payload con el nuevo comentario
# ============================================================
Write-Host ">>> [FASE 3] Mapeando artefactos y comentario para el nuevo release..." -ForegroundColor Cyan

# Extraemos los artefactos exactos que se usaron en el release anterior
$artifactPayload = @()
foreach ($artifact in $sourceRelease.artifacts) {
    $artifactPayload += @{
        alias             = $artifact.alias
        instanceReference = @{
            id   = $artifact.definitionReference.version.id
            name = $artifact.definitionReference.version.name
        }
    }
}

# Construimos la descripción final combinando el ID de origen, versión de backup y tu comentario
$fullDescription = "Re-release desde #$sourceReleaseId [Backup: $versionLabel]. Motivo: $releaseComment"

$newReleasePayload = @{
    definitionId       = $sourceRelease.releaseDefinition.id
    description        = $fullDescription
    artifacts          = $artifactPayload
    isDraft            = $false
    reason             = "manual"
    manualEnvironments = @() # Se disparan los stages automáticos por defecto
}

# ============================================================
# FASE 4: POST - Crear nuevo Release (Fresh Start)
# ============================================================
Write-Host ">>> [FASE 4] Ejecutando POST para crear el release con datos frescos..." -ForegroundColor Cyan

$body = $newReleasePayload | ConvertTo-Json -Depth 20 -Compress

try {
    $newRelease = Invoke-RestMethod `
        -Uri "$vsrmBase/releases?$apiVer" `
        -Method POST `
        -Headers $headers `
        -Body $body

    Write-Host ">>> ✅ ÉXITO: Nuevo Release creado!" -ForegroundColor Green
    Write-Host "    ID         : $($newRelease.id)"
    Write-Host "    Nombre     : $($newRelease.name)"
    Write-Host "    Comentario : $releaseComment"
    Write-Host "    Backup Ref : $versionLabel"
    Write-Host "    Pipeline   : $($newRelease.releaseDefinition.name)"
    Write-Host "    URL        : https://dev.azure.com/$organization/$project/_releaseProgress?_a=release-pipeline-progress&releaseId=$($newRelease.id)"
} catch {
    Write-Host ">>> ❌ ERROR al crear el release:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    
    # Si falla la creación, dejamos el backup igual para diagnóstico
    Write-Host ">>> 💾 El backup del release origen está disponible en: $backupFile" -ForegroundColor Yellow
    exit 1
}