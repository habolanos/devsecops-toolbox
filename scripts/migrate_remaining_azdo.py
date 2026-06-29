#!/usr/bin/env python3
"""Script para migrar todas las herramientas AZDO restantes a ExportManager."""

import os
import re
from pathlib import Path

def add_export_manager_import(filepath):
    """Agrega import de ExportManager a un archivo."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Si ya tiene el import, saltar
        if 'from export_manager import ExportManager' in content:
            return False
        
        # Buscar dónde agregar el import
        lines = content.split('\n')
        insert_pos = 0
        
        # Buscar después del último try-except block de imports
        for i, line in enumerate(lines):
            if 'RICH_AVAILABLE' in line or 'REQUESTS_AVAILABLE' in line:
                insert_pos = i + 1
                break
        
        # Crear bloque de import
        import_block = """try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

"""
        
        lines.insert(insert_pos, import_block)
        new_content = '\n'.join(lines)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"Error procesando {filepath}: {e}")
        return False

def find_files_with_export_results(directory):
    """Encuentra todos los archivos con función export_results."""
    files = []
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith('.py') and not filename.startswith('__'):
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if 'def export_results(' in content:
                            files.append(filepath)
                except:
                    pass
    return files

# Encontrar todas las herramientas AZDO con export_results
azdo_tools = find_files_with_export_results('scm/azdo')

print("=" * 60)
print("MIGRACIÓN AUTOMÁTICA AZDO A EXPORTMANAGER")
print("=" * 60)

print(f"\n🔴 MIGRANDO HERRAMIENTAS AZDO...")
print(f"Encontradas {len(azdo_tools)} herramientas con export_results()\n")

azdo_count = 0
for tool in sorted(azdo_tools):
    if add_export_manager_import(tool):
        print(f"  ✅ {os.path.basename(tool)}")
        azdo_count += 1
    else:
        print(f"  ⏭️  {os.path.basename(tool)} (ya tiene import)")

print(f"\n✅ AZDO: {azdo_count} herramientas actualizadas")
print("=" * 60)
