#Requires -Version 5.1
<#
.SYNOPSIS
    Genera un ZIP distribuible del proyecto devsecops-toolbox.

.DESCRIPTION
    Empaqueta todos los archivos del toolbox respetando las exclusiones del .gitignore:
    sin .git, venv, __pycache__, config.json (secretos), outcome/, tests/, archivos temporales, etc.
    El ZIP resultante se genera en la carpeta outcome/ con timestamp.

.PARAMETER OutputDir
    Carpeta de salida. Default: <directorio_del_script>\outcome

.PARAMETER ZipPrefix
    Prefijo del nombre del archivo ZIP. Default: devsecops-toolbox_dist

.PARAMETER ShowExcluded
    Muestra la lista detallada de archivos excluidos al finalizar.

.PARAMETER GitHubPublish
    Switch para activar la publicacion del release en GitHub.

.PARAMETER GitHubToken
    Personal Access Token con scope 'repo'. Si no se indica, se lee de la
    variable de entorno GITHUB_TOKEN.

.PARAMETER ReleaseTag
    Tag de la version a crear (ej: v1.3.1). Obligatorio con -GitHubPublish.

.PARAMETER ReleaseTitle
    Titulo del release. Default: mismo valor que -ReleaseTag.

.PARAMETER ReleaseNotes
    Descripcion del release en texto plano o Markdown.

.PARAMETER Draft
    Crear el release como borrador (no visible publicamente).

.PARAMETER Prerelease
    Marcar el release como pre-release.

.EXAMPLE
    .\make_dist.ps1

.EXAMPLE
    .\make_dist.ps1 -OutputDir "C:\entregas" -ShowExcluded

.EXAMPLE
    .\make_dist.ps1 -GitHubPublish -ReleaseTag "v1.3.1" -GitHubToken "ghp_xxx"

.EXAMPLE
    .\make_dist.ps1 -GitHubPublish -ReleaseTag "v1.4.0" -ReleaseTitle "Release 1.4.0" -ReleaseNotes "Cambios: ..."

.NOTES
    Autor  : Harold Adrian
    Salida : outcome\devsecops-toolbox_dist_<YYYYMMDD_HHMMSS>.zip
    GitHub : requiere PAT con scope 'Contents: Read and Write' o 'repo'
    ENCODING: ASCII-only source (PowerShell 5.1 ANSI compat)
#>

[CmdletBinding()]
param(
    [string]$OutputDir    = "$PSScriptRoot\outcome",
    [string]$ZipPrefix    = "devsecops-toolbox_dist",
    [switch]$ShowExcluded,
    [switch]$GitHubPublish,
    [string]$GitHubToken   = "",
    [string]$ReleaseTag    = "",
    [string]$ReleaseTitle  = "",
    [string]$ReleaseNotes  = "",
    [switch]$Draft,
    [switch]$Prerelease
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ===============================================================================
# CONFIGURACIoN DE EXCLUSIONES
# ===============================================================================

# Carpetas: si algun segmento del path relativo coincide, se excluye el archivo
$ExcludedDirs = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
)
@(
    '.git', '.github', '.windsurf',
    '.venv', 'venv', 'env',
    '__pycache__',
    'outcome',
    'cache', '.cache',
    '.vscode', '.docker', '.config', '.npm', '.kube', '.ssh',
    '.local', '.rustup', '.gemini',
    'tests', 'scm/tests', '__tests__', '__tests__e2e'
) | ForEach-Object { [void]$ExcludedDirs.Add($_) }

# Nombres de archivo exactos excluidos
$ExcludedFileNames = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
)
@(
    'config.json',                   # Secretos - distribuir solo config.json.template
    'make_dist.ps1',                 # Script de empaquetado - no incluir en el distribuible
    '.gitignore', '.gitconfig',
    '.bash_history', '.bash_logout', '.bashrc', '.profile',
    '.env', 'taged.cache', '.lesshst', '.viminfo'
) | ForEach-Object { [void]$ExcludedFileNames.Add($_) }

# Extensiones excluidas
$ExcludedExtensions = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase
)
@(
    '.pyc', '.pyd', '.pyo',
    '.zip', '.gz', '.tar',
    '.xlsx', '.xls', '.docx',
    '.log'
) | ForEach-Object { [void]$ExcludedExtensions.Add($_) }

# Patrones wildcard de nombre de archivo
$ExcludedNamePatterns = @(
    '*.origin.json',
    '*.tar.gz', '*.tar.bz2', '*.tar.xz', '*.tar.lz', '*.tar.lzma', '*.tar.lz4'
)

# ===============================================================================
# FUNCION: Detectar repositorio GitHub desde git remote
# ===============================================================================
function Get-GitHubRepo {
    try {
        $remoteUrl = & git remote get-url origin 2>$null
    } catch {
        return $null
    }
    if (-not $remoteUrl) { return $null }

    if ($remoteUrl -match "https://github\.com/([^/]+)/([^/]+?)(\.git)?$") {
        return @{ Owner = $Matches[1]; Repo = $Matches[2] }
    }
    if ($remoteUrl -match "git@github\.com:([^/]+)/([^/]+?)(\.git)?$") {
        return @{ Owner = $Matches[1]; Repo = $Matches[2] }
    }
    return $null
}

# ===============================================================================
# FUNCIoN DE FILTRO
# ===============================================================================
function Test-IsExcluded {
    param([System.IO.FileInfo]$File)

    $relPath = $File.FullName.Substring($SourceRoot.Length + 1)
    $parts   = $relPath.Split([char[]](47, 92))

    # Verificar segmentos de directorio (todos menos el ultimo que es el archivo)
    for ($i = 0; $i -lt ($parts.Length - 1); $i++) {
        if ($ExcludedDirs.Contains($parts[$i])) { return $true }
    }

    # Nombre exacto
    if ($ExcludedFileNames.Contains($File.Name)) { return $true }

    # Extension
    if ($ExcludedExtensions.Contains($File.Extension)) { return $true }

    # Patrones wildcard
    foreach ($pattern in $ExcludedNamePatterns) {
        if ($File.Name -like $pattern) { return $true }
    }

    return $false
}

# ===============================================================================
# INICIO
# ===============================================================================
$SourceRoot = $PSScriptRoot
$Timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$ZipName    = "${ZipPrefix}_${Timestamp}.zip"
$ZipPath    = Join-Path $OutputDir $ZipName

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  DevSecOps Toolbox - Generador de Distribucion ZIP  " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Origen : $SourceRoot" -ForegroundColor Gray
Write-Host "  Destino: $ZipPath"    -ForegroundColor Gray
Write-Host ""

# -- Crear carpeta outcome si no existe ---------------------------------------
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
    Write-Host "  [DIR] Carpeta creada: $OutputDir" -ForegroundColor DarkGray
}

# -- Recolectar y clasificar archivos -----------------------------------------
Write-Host "  >> Escaneando archivos..." -NoNewline -ForegroundColor Yellow

$AllFiles = Get-ChildItem -Path $SourceRoot -Recurse -File

$Included = [System.Collections.Generic.List[System.IO.FileInfo]]::new()
$Excluded = [System.Collections.Generic.List[string]]::new()

foreach ($file in $AllFiles) {
    if (Test-IsExcluded $file) {
        $Excluded.Add($file.FullName.Substring($SourceRoot.Length + 1))
    } else {
        $Included.Add($file)
    }
}

Write-Host " OK" -ForegroundColor Green
Write-Host ""
Write-Host ("  [OK]   Incluidos : {0,4} archivo(s)" -f $Included.Count) -ForegroundColor White
Write-Host ("  [SKIP] Excluidos : {0,4} archivo(s)" -f $Excluded.Count) -ForegroundColor DarkGray
Write-Host ""

if ($Included.Count -eq 0) {
    Write-Host "  [!!] Sin archivos a empaquetar. Verificar ruta origen." -ForegroundColor Red
    exit 1
}

# -- Crear ZIP -----------------------------------------------------------------
Add-Type -Assembly System.IO.Compression
Add-Type -Assembly System.IO.Compression.FileSystem

Write-Host "  >> Comprimiendo..." -NoNewline -ForegroundColor Yellow

$zip = [System.IO.Compression.ZipFile]::Open(
    $ZipPath,
    [System.IO.Compression.ZipArchiveMode]::Create
)
try {
    foreach ($file in $Included) {
        $entryName = $file.FullName.Substring($SourceRoot.Length + 1).Replace([char]92, '/')
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $zip,
            $file.FullName,
            $entryName,
            [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }
} finally {
    $zip.Dispose()
}

Write-Host " Listo" -ForegroundColor Green

# -- Resumen -------------------------------------------------------------------
$zipInfo   = Get-Item $ZipPath
$zipSizeMB = [math]::Round($zipInfo.Length / 1MB, 3)
$zipSizeKB = [math]::Round($zipInfo.Length / 1KB, 1)
$sizeStr   = if ($zipSizeMB -ge 1) { "$zipSizeMB MB" } else { "$zipSizeKB KB" }

Write-Host ""
Write-Host "  ------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ("  ZIP      : {0}" -f $ZipName)             -ForegroundColor Cyan
Write-Host ("  Tamano   : {0}" -f $sizeStr)             -ForegroundColor White
Write-Host ("  Archivos : {0}" -f $Included.Count)      -ForegroundColor White
Write-Host ("  Generado : {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -ForegroundColor White
Write-Host "  ------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# -- Desglose por subcarpeta ---------------------------------------------------
Write-Host "  Contenido del ZIP:" -ForegroundColor Cyan
Write-Host ""

$bslash      = [char]92
$groupCounts = @{}
foreach ($file in $Included) {
    $rel   = $file.FullName.Substring($SourceRoot.Length + 1)
    $parts = $rel.Split([char[]](47, 92))
    $key   = "raiz"
    if ($parts.Length -ge 3) {
        $key = $parts[0] + $bslash + $parts[1]
    } elseif ($parts.Length -ge 2) {
        $key = $parts[0]
    }
    if ($groupCounts.ContainsKey($key)) {
        $groupCounts[$key]++
    } else {
        $groupCounts[$key] = 1
    }
}

foreach ($key in ($groupCounts.Keys | Sort-Object)) {
    Write-Host ("     {0,-35} {1,3} archivo(s)" -f $key, $groupCounts[$key]) -ForegroundColor Gray
}

Write-Host ""

# -- Archivos excluidos (opcional) --------------------------------------------
if ($ShowExcluded -and $Excluded.Count -gt 0) {
    Write-Host "  [SKIP] Archivos excluidos:" -ForegroundColor DarkGray
    foreach ($f in $Excluded | Sort-Object) {
        Write-Host ("     - {0}" -f $f) -ForegroundColor DarkGray
    }
    Write-Host ""
}

Write-Host "  [OK] Distribucion generada exitosamente:" -ForegroundColor Green
Write-Host "     $ZipPath"                             -ForegroundColor Yellow
Write-Host ""

# -- GitHub Release -----------------------------------------------------------
if ($GitHubPublish) {

    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "  GitHub Release Publisher                            " -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host ""

    # Validar token
    $ghToken = $GitHubToken
    if (-not $ghToken) { $ghToken = $env:GITHUB_TOKEN }
    if (-not $ghToken) {
        Write-Host "  [!!] Token requerido: usa -GitHubToken o define la var GITHUB_TOKEN." -ForegroundColor Red
        exit 1
    }

    # Validar tag
    if (-not $ReleaseTag) {
        Write-Host "  [!!] -ReleaseTag es obligatorio (ej: v1.3.1)." -ForegroundColor Red
        exit 1
    }

    # Detectar repo
    $ghRepo = Get-GitHubRepo
    if (-not $ghRepo) {
        Write-Host "  [!!] No se pudo detectar el repositorio desde git remote." -ForegroundColor Red
        Write-Host "       Verifica que el origen sea github.com." -ForegroundColor DarkGray
        exit 1
    }

    $owner  = $ghRepo.Owner
    $repo   = $ghRepo.Repo
    $title  = if ($ReleaseTitle) { $ReleaseTitle } else { $ReleaseTag }

    Write-Host "  Repositorio : $owner/$repo" -ForegroundColor Gray
    Write-Host "  Tag         : $ReleaseTag"  -ForegroundColor Gray
    Write-Host "  Titulo      : $title"       -ForegroundColor Gray
    if ($Draft)      { Write-Host "  Modo        : DRAFT"      -ForegroundColor Yellow }
    if ($Prerelease) { Write-Host "  Modo        : PRE-RELEASE" -ForegroundColor Yellow }
    Write-Host ""

    $ghHeaders = @{
        Authorization          = "Bearer $ghToken"
        Accept                 = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
    }

    # Crear release
    Write-Host "  >> Creando release $ReleaseTag ..." -NoNewline -ForegroundColor Yellow

    $releasePayload = @{
        tag_name   = $ReleaseTag
        name       = $title
        body       = $ReleaseNotes
        draft      = [bool]$Draft
        prerelease = [bool]$Prerelease
    } | ConvertTo-Json -Compress

    try {
        $release = Invoke-RestMethod `
            -Uri "https://api.github.com/repos/$owner/$repo/releases" `
            -Method POST `
            -Headers $ghHeaders `
            -Body $releasePayload `
            -ContentType "application/json"
        Write-Host " OK" -ForegroundColor Green
        Write-Host "  [OK] Release : $($release.html_url)" -ForegroundColor Green
    } catch {
        Write-Host " ERROR" -ForegroundColor Red
        Write-Host "  [!!] $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }

    # Subir ZIP como asset
    Write-Host "  >> Subiendo asset ($ZipName) ..." -NoNewline -ForegroundColor Yellow

    $uploadUri = "https://uploads.github.com/repos/$owner/$repo/releases/$($release.id)/assets?name=$ZipName"

    try {
        $fileBytes = [System.IO.File]::ReadAllBytes($ZipPath)
        $asset = Invoke-RestMethod `
            -Uri $uploadUri `
            -Method POST `
            -Headers $ghHeaders `
            -Body $fileBytes `
            -ContentType "application/zip"
        Write-Host " OK" -ForegroundColor Green
        Write-Host "  [OK] Asset   : $($asset.browser_download_url)" -ForegroundColor Green
    } catch {
        Write-Host " ERROR" -ForegroundColor Red
        Write-Host "  [!!] $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }

    Write-Host ""
    Write-Host "  [OK] Release publicado exitosamente en GitHub." -ForegroundColor Green
    Write-Host "     URL  : $($release.html_url)" -ForegroundColor Yellow
    Write-Host ""
}
