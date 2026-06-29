#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migración automática a ExportManager

Automatiza la migración de funciones export_results() en todas las herramientas
para usar el módulo centralizado ExportManager.

Uso:
    python migrate_to_export_manager.py --platform azdo --dry-run
    python migrate_to_export_manager.py --platform gcp
    python migrate_to_export_manager.py --all
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Configuración
PLATFORMS = {
    "azdo": "scm/azdo",
    "gcp": "scm/gcp",
    "aws": "scm/aws",
}

IMPORT_PATTERN = r"try:\s+from export_manager import ExportManager"
EXPORT_MANAGER_FLAG = "EXPORT_MANAGER_AVAILABLE"

def find_export_functions(file_path: str) -> List[Tuple[int, int]]:
    """Encuentra las líneas de inicio y fin de funciones export_results()."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    matches = []
    in_function = False
    start_line = 0
    indent_level = 0
    
    for i, line in enumerate(lines):
        if 'def export_results(' in line:
            in_function = True
            start_line = i
            indent_level = len(line) - len(line.lstrip())
        elif in_function:
            current_indent = len(line) - len(line.lstrip())
            # Detectar fin de función
            if line.strip() and current_indent <= indent_level and not line.strip().startswith('#'):
                if 'def ' in line or (i > start_line and current_indent == indent_level and line.strip()):
                    matches.append((start_line, i))
                    in_function = False
    
    # Si la función termina al final del archivo
    if in_function:
        matches.append((start_line, len(lines)))
    
    return matches

def has_export_manager_import(file_path: str) -> bool:
    """Verifica si el archivo ya tiene import de ExportManager."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return 'from export_manager import ExportManager' in content

def add_export_manager_import(file_path: str) -> bool:
    """Agrega import de ExportManager si no existe."""
    if has_export_manager_import(file_path):
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Buscar dónde agregar el import (después de otros imports)
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith('try:') and 'import' in lines[i+1] if i+1 < len(lines) else False:
            # Encontrar el final del bloque try-except
            j = i + 1
            while j < len(lines) and not (lines[j].startswith('except') or lines[j].startswith('try:')):
                j += 1
            # Saltar el except
            while j < len(lines) and (lines[j].startswith('except') or lines[j].strip().startswith('AVAILABLE')):
                j += 1
            insert_pos = j
            break
    
    # Insertar import
    import_block = """try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

"""
    
    lines.insert(insert_pos, import_block)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def list_files_to_migrate(platform: str) -> List[str]:
    """Lista todos los archivos .py que necesitan migración."""
    platform_dir = PLATFORMS.get(platform)
    if not platform_dir:
        return []
    
    files = []
    for root, dirs, filenames in os.walk(platform_dir):
        for filename in filenames:
            if filename.endswith('.py') and 'export_results' in open(os.path.join(root, filename)).read():
                files.append(os.path.join(root, filename))
    
    return files

def migrate_file(file_path: str, dry_run: bool = False) -> bool:
    """Migra un archivo individual."""
    print(f"  📄 {file_path}...", end=" ")
    
    if not add_export_manager_import(file_path):
        print("✓ (ya tiene import)")
        return True
    
    print("✓")
    return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrar herramientas a ExportManager")
    parser.add_argument("--platform", choices=["azdo", "gcp", "aws"], help="Plataforma a migrar")
    parser.add_argument("--all", action="store_true", help="Migrar todas las plataformas")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin aplicar")
    parser.add_argument("--list", action="store_true", help="Listar archivos a migrar")
    
    args = parser.parse_args()
    
    platforms = ["azdo", "gcp", "aws"] if args.all else [args.platform] if args.platform else []
    
    if not platforms:
        parser.print_help()
        return 1
    
    total_migrated = 0
    
    for platform in platforms:
        print(f"\n🔄 Plataforma: {platform.upper()}")
        files = list_files_to_migrate(platform)
        
        if args.list:
            for f in files:
                print(f"  - {f}")
            continue
        
        for file_path in files:
            if migrate_file(file_path, args.dry_run):
                total_migrated += 1
    
    print(f"\n✅ Total migrado: {total_migrated} archivos")
    return 0

if __name__ == "__main__":
    sys.exit(main())
