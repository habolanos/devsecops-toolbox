#!/usr/bin/env python3
"""Script para migrar TODAS las herramientas a ExportManager."""

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
            if 'AVAILABLE' in line and 'except' in lines[i-1] if i > 0 else False:
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
        return False

def find_all_export_results(root_dir='scm'):
    """Encuentra TODOS los archivos con export_results en el proyecto."""
    files = {}
    for platform in ['azdo', 'aws', 'gcp', 'terminal', 'kpi_analyzer']:
        platform_dir = os.path.join(root_dir, platform)
        if not os.path.exists(platform_dir):
            continue
        
        platform_files = []
        for root, dirs, filenames in os.walk(platform_dir):
            for filename in filenames:
                if filename.endswith('.py') and not filename.startswith('__'):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if 'def export_results(' in content:
                                platform_files.append(filepath)
                    except:
                        pass
        
        if platform_files:
            files[platform] = platform_files
    
    return files

print("=" * 70)
print("MIGRACIÓN COMPLETA A EXPORTMANAGER - TODAS LAS PLATAFORMAS")
print("=" * 70)

all_tools = find_all_export_results()
total_migrated = 0

for platform, tools in sorted(all_tools.items()):
    print(f"\n{'🔴' if platform == 'azdo' else '🔵' if platform == 'aws' else '🟢'} {platform.upper()} ({len(tools)} herramientas)")
    
    platform_count = 0
    for tool in sorted(tools):
        if add_export_manager_import(tool):
            print(f"  ✅ {os.path.basename(tool)}")
            platform_count += 1
            total_migrated += 1
        else:
            print(f"  ⏭️  {os.path.basename(tool)}")
    
    print(f"  → {platform_count} actualizadas")

print("\n" + "=" * 70)
print(f"✅ MIGRACIÓN COMPLETADA: {total_migrated} herramientas actualizadas")
print("=" * 70)
