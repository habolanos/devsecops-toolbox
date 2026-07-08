#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para organizar archivos .md en carpetas temáticas
"""

import os
import shutil
from pathlib import Path

docs_dir = Path("docs")

# Definir mapeo de archivos a carpetas
file_mapping = {
    "architecture": [
        "DevSecOps_Maturity_Model.md",
        "KPIs_Frameworks_DevSecOps.md",
        "kpi_sources_inventory.md",
    ],
    "planning": [
        "Plan_Trabajo_Pipeline_Health.md",
        "Plan_Trabajo_Prod_Deploy.md",
    ],
    "analysis": [
        "VALIDACION_SYSTEM_OPTIONS.md",
    ],
    "sessions": [
        "RESUMEN_FINAL_SESION_INTENSIVA.md",
        "RESUMEN_SESION_COMPLETA.md",
        "SESION_COMPLETA_FASE2_FASE3.md",
        "SESION_FINAL_COMPLETA_FASE2_FASE3_FASE4.md",
    ],
    "corrections": [
        "CORRECCION_DUPLICADOS_TOOLS.md",
    ],
}

# Crear carpetas
for folder in file_mapping.keys():
    folder_path = docs_dir / folder
    folder_path.mkdir(exist_ok=True)
    print(f"✓ Carpeta creada: {folder}")

# Mover archivos
for folder, files in file_mapping.items():
    for file in files:
        src = docs_dir / file
        dst = docs_dir / folder / file
        
        if src.exists():
            shutil.move(str(src), str(dst))
            print(f"✓ Movido: {file} → {folder}/")
        else:
            print(f"✗ No encontrado: {file}")

print("\n✅ Organización completada")
