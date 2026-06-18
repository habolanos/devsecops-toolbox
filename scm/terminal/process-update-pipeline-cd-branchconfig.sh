# ============================================================
# CONFIGURACIÓN
# ============================================================
$organization = "Coppel-Retail"          # tu organización
$project      = "Cadena_de_Suministros"  # tu proyecto
$definitionId = 123                      # ID del release pipeline (lo ves en la URL)
$pat          = "TU_PAT_AQUI"            # Personal Access Token con scope Release (Read & Write)

# Endpoint de Release Management (vsrm, no dev.azure.com)
$uri = "https://vsrm.dev.azure.com/$organization/$project/_apis/release/definitions/$definitionId`?api-version=7.0"

# Auth: PAT en Base64
$base64Token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$pat"))
$headers = @{
    Authorization  = "Basic $base64Token"
    "Content-Type" = "application/json"
}

try {
    # ============================================================
    # 1. GET - Obtener definición actual
    # ============================================================
    Write-Host ">>> Obteniendo definición del release pipeline..." -ForegroundColor Cyan
    $def = Invoke-RestMethod -Uri $uri -Method GET -Headers $headers

    # ============================================================
    # 2. ACTUALIZAR VARIABLE branchConfig
    # ============================================================
    Write-Host ">>> Actualizando variable 'branchConfig'..." -ForegroundColor Cyan
    
    if ($def.variables.branchConfig) {
        $def.variables.branchConfig.value = "config-cadenaSuministro"
    } else {
        # Si no existe, la crea
        $def.variables | Add-Member -NotePropertyName "branchConfig" -NotePropertyValue @{
            value = "config-cadenaSuministro"
            allowOverride = $true
        }
    }
    Write-Host "    branchConfig = $($def.variables.branchConfig.value)" -ForegroundColor Green

    # ============================================================
    # 3. ACTUALIZAR TAREA 'get file k8-manifest'
    # ============================================================
    Write-Host ">>> Buscando tarea 'get file k8-manifest'..." -ForegroundColor Cyan

    $taskFound = $false
    foreach ($env in $def.environments) {
        foreach ($phase in $env.deployPhases) {
            foreach ($task in $phase.workflowTasks) {
                # Se identifica por el Display Name que se ve en la UI
                if ($task.displayName -eq "get file k8-manifest") {
                    $taskFound = $true
                    Write-Host "    Tarea encontrada en environment: $($env.name)" -ForegroundColor Yellow
                    
                    $oldScript = $task.inputs.script
                    $newScript = $oldScript -replace '\$\(path_pipelineConfig\)', '$(path_pipelineConfigYml)'
                    
                    $task.inputs.script = $newScript
                    
                    Write-Host "    Script actualizado:" -ForegroundColor Green
                    Write-Host "    ANT: $oldScript"
                    Write-Host "    NEW: $newScript"
                }
            }
        }
    }

    if (-not $taskFound) {
        throw "No se encontró la tarea con displayName 'get file k8-manifest'. Revisa el nombre en la UI."
    }

    # ============================================================
    # 4. PUT - Guardar cambios
    # ============================================================
    Write-Host ">>> Enviando definición actualizada..." -ForegroundColor Cyan
    
    $body = $def | ConvertTo-Json -Depth 100 -Compress
    
    $response = Invoke-RestMethod -Uri $uri -Method PUT -Headers $headers -Body $body
    
    Write-Host ">>> Pipeline actualizado exitosamente." -ForegroundColor Green
    Write-Host "    Revision: $($response.revision)"
    Write-Host "    URL: $($response._links.self.href)"
}
catch {
    Write-Host ">>> ERROR: $_" -ForegroundColor Red
    Write-Host $_.Exception.Response
}