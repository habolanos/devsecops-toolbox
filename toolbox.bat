@echo off
REM DevSecOps Toolbox - Wrapper para Windows
REM Ejecuta el toolbox desde cualquier ubicacion
REM
REM Uso: toolbox.bat [argumentos]

setlocal enabledelayedexpansion

REM Obtener directorio del script
set SCRIPT_DIR=%~dp0

REM Verificar que el ejecutable existe
if not exist "%SCRIPT_DIR%dist\toolbox.exe" (
    echo.
    echo ╔════════════════════════════════════════════════════════════════╗
    echo ║                      ERROR: Ejecutable no encontrado           ║
    echo ╚════════════════════════════════════════════════════════════════╝
    echo.
    echo El archivo dist\toolbox.exe no existe.
    echo.
    echo Opciones:
    echo   1. Compilar ejecutable:
    echo      python build_executables.py
    echo.
    echo   2. Descargar ejecutable precompilado:
    echo      https://github.com/habolanos/devsecops-toolbox/releases
    echo.
    echo   3. Usar Python directamente:
    echo      python scm\main.py
    echo.
    pause
    exit /b 1
)

REM Ejecutar el toolbox
"%SCRIPT_DIR%dist\toolbox.exe" %*

endlocal
