#!/usr/bin/env python3
"""
Script para compilar ejecutables de DevSecOps Toolbox para Windows y Linux.
Genera: toolbox.exe (Windows) y toolbox (Linux)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """Verifica si PyInstaller está instalado."""
    try:
        import PyInstaller
        print("✅ PyInstaller encontrado")
        return True
    except ImportError:
        print("❌ PyInstaller no está instalado")
        print("Instalando: pip install pyinstaller")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        return True

def build_executable():
    """Compila el ejecutable usando PyInstaller."""
    
    # Detectar sistema operativo
    is_windows = sys.platform == "win32"
    is_linux = sys.platform.startswith("linux")
    
    if not (is_windows or is_linux):
        print(f"❌ Sistema operativo no soportado: {sys.platform}")
        return False
    
    # Rutas
    project_root = Path(__file__).parent
    main_py = project_root / "scm" / "main.py"
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    
    if not main_py.exists():
        print(f"❌ No se encontró: {main_py}")
        return False
    
    print(f"📦 Compilando ejecutable para {sys.platform}...")
    print(f"   Origen: {main_py}")
    print(f"   Destino: {dist_dir}")
    
    # Limpiar directorios anteriores
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    # Comando PyInstaller
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--name", "toolbox",
        "--distpath", str(dist_dir),
        "--buildpath", str(build_dir),
        "--specpath", str(project_root),
        "--add-data", f"{project_root / 'scm'}:scm",
        "--hidden-import=rich",
        "--hidden-import=pyyaml",
        "--hidden-import=google.cloud",
        "--hidden-import=azure",
        "--hidden-import=boto3",
        str(main_py)
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Compilación exitosa")
        
        # Mostrar ubicación del ejecutable
        if is_windows:
            exe_path = dist_dir / "toolbox.exe"
            if exe_path.exists():
                print(f"✅ Ejecutable creado: {exe_path}")
                print(f"   Tamaño: {exe_path.stat().st_size / (1024*1024):.2f} MB")
        else:
            exe_path = dist_dir / "toolbox"
            if exe_path.exists():
                print(f"✅ Ejecutable creado: {exe_path}")
                print(f"   Tamaño: {exe_path.stat().st_size / (1024*1024):.2f} MB")
                # Hacer ejecutable en Linux
                os.chmod(exe_path, 0o755)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error durante compilación:")
        print(e.stdout)
        print(e.stderr)
        return False

def create_wrapper_scripts():
    """Crea scripts wrapper para facilitar el uso."""
    
    project_root = Path(__file__).parent
    
    # Script para Windows (batch)
    batch_script = project_root / "toolbox.bat"
    batch_content = """@echo off
REM DevSecOps Toolbox - Wrapper para Windows
REM Ejecuta el toolbox desde cualquier ubicación

setlocal enabledelayedexpansion

REM Obtener directorio del script
set SCRIPT_DIR=%~dp0

REM Ejecutar el toolbox
"%SCRIPT_DIR%dist\\toolbox.exe" %*

endlocal
"""
    
    with open(batch_script, "w") as f:
        f.write(batch_content)
    print(f"✅ Script wrapper creado: {batch_script}")
    
    # Script para Linux (bash)
    bash_script = project_root / "toolbox"
    bash_content = """#!/bin/bash
# DevSecOps Toolbox - Wrapper para Linux
# Ejecuta el toolbox desde cualquier ubicación

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ejecutar el toolbox
"$SCRIPT_DIR/dist/toolbox" "$@"
"""
    
    with open(bash_script, "w") as f:
        f.write(bash_content)
    os.chmod(bash_script, 0o755)
    print(f"✅ Script wrapper creado: {bash_script}")

def main():
    """Función principal."""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║         DevSecOps Toolbox - Compilador de Ejecutables         ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    
    # Verificar PyInstaller
    if not check_pyinstaller():
        return False
    
    print()
    
    # Compilar ejecutable
    if not build_executable():
        return False
    
    print()
    
    # Crear scripts wrapper
    create_wrapper_scripts()
    
    print()
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║                    ✅ COMPILACIÓN COMPLETADA                   ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    print("📦 Ejecutables generados:")
    print("   Windows: dist/toolbox.exe")
    print("   Linux:   dist/toolbox")
    print()
    print("🚀 Uso:")
    print("   Windows: toolbox.bat")
    print("   Linux:   ./toolbox")
    print()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
