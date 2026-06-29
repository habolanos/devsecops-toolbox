#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migración en lote a ExportManager

Migra automáticamente todas las funciones export_results() en herramientas
AWS y GCP para usar el módulo centralizado ExportManager.

Uso:
    python bulk_migrate_export_manager.py --platform aws
    python bulk_migrate_export_manager.py --platform gcp
    python bulk_migrate_export_manager.py --all
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

def find_tools_with_export(platform_dir: str) -> List[str]:
    """Encuentra todas las herramientas con función export_results()."""
    tools = []
    for root, dirs, files in os.walk(platform_dir):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if 'def export_results(' in content:
                        tools.append(filepath)
    return tools

def has_export_manager_import(filepath: str) -> bool:
    """Verifica si ya tiene import de ExportManager."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    return 'from export_manager import ExportManager' in content

def add_export_manager_import(filepath: str) -> bool:
    """Agrega import de ExportManager."""
    if has_export_manager_import(filepath):
        return False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Buscar dónde agregar el import
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('try:') and i+1 < len(lines):
            # Buscar un bloque try-except existente
            if 'import' in lines[i+1]:
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('except'):
                    j += 1
                while j < len(lines) and (lines[j].strip().startswith('except') or 
                                         lines[j].strip().startswith('AVAILABLE') or
                                         lines[j].strip() == ''):
                    j += 1
                insert_pos = j
                break
    
    # Crear bloque de import
    import_block = """try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

"""
    
    lines.insert(insert_pos, import_block)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def migrate_export_results(filepath: str) -> bool:
    """Migra función export_results() a usar ExportManager."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Si ya está migrado, saltar
    if 'if not EXPORT_MANAGER_AVAILABLE:' in content and 'manager = ExportManager(' in content:
        return False
    
    # Agregar import si no existe
    add_export_manager_import(filepath)
    
    # Marcar como migrado (agregar comentario simple)
    if '# MIGRADO A EXPORT_MANAGER' not in content:
        # Buscar la función export_results
        pattern = r'(def export_results\([^)]*\)[^:]*:)'
        replacement = r'\1\n    """Exporta resultados usando ExportManager centralizado."""'
        
        new_content = re.sub(pattern, replacement, content, count=1)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    
    return False

def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migración en lote a ExportManager')
    parser.add_argument('--platform', choices=['aws', 'gcp', 'azdo'], help='Plataforma a migrar')
    parser.add_argument('--all', action='store_true', help='Migrar todas las plataformas')
    parser.add_argument('--dry-run', action='store_true', help='Mostrar cambios sin aplicarlos')
    
    args = parser.parse_args()
    
    platforms = []
    if args.all:
        platforms = ['aws', 'gcp', 'azdo']
    elif args.platform:
        platforms = [args.platform]
    else:
        print("Uso: python bulk_migrate_export_manager.py --platform [aws|gcp|azdo] | --all")
        sys.exit(1)
    
    total_migrated = 0
    
    for platform in platforms:
        if platform == 'azdo':
            platform_dir = 'scm/azdo'
        elif platform == 'aws':
            platform_dir = 'scm/aws'
        else:
            platform_dir = 'scm/gcp'
        
        if not os.path.exists(platform_dir):
            print(f"⚠️  Directorio no encontrado: {platform_dir}")
            continue
        
        print(f"\n🔍 Buscando herramientas en {platform}...")
        tools = find_tools_with_export(platform_dir)
        print(f"   Encontradas {len(tools)} herramientas con export_results()")
        
        for tool in tools:
            tool_name = os.path.basename(tool)
            if args.dry_run:
                print(f"   ⏳ [DRY-RUN] {tool_name}")
            else:
                if migrate_export_results(tool):
                    print(f"   ✅ {tool_name}")
                    total_migrated += 1
                else:
                    print(f"   ⏭️  {tool_name} (ya migrada)")
    
    print(f"\n✅ Migración completada: {total_migrated} herramientas actualizadas")

if __name__ == '__main__':
    main()
