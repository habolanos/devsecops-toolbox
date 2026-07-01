#!/usr/bin/env python3
"""
Script para encontrar todas las herramientas que NO tienen función export_results()
"""

import os
import re
from pathlib import Path

def has_export_results(filepath):
    """Verifica si un archivo tiene función export_results()"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return 'def export_results(' in content
    except:
        return False

def find_tool_files(base_dir):
    """Encuentra todos los archivos de herramientas"""
    tools = []
    
    for root, dirs, files in os.walk(base_dir):
        # Excluir directorios específicos
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'outcome']]
        
        for file in files:
            if file.endswith('.py') and file != 'tools.py' and file != '__init__.py':
                # Excluir archivos que no son herramientas
                if not any(x in file for x in ['test_', 'conftest', 'setup.py']):
                    filepath = os.path.join(root, file)
                    tools.append(filepath)
    
    return sorted(tools)

# Directorios a buscar
base_dirs = [
    'scm/azdo',
    'scm/aws',
    'scm/gcp',
]

print("=" * 80)
print("BÚSQUEDA DE HERRAMIENTAS SIN export_results()")
print("=" * 80)

all_without_export = []
all_with_export = []

for base_dir in base_dirs:
    if not os.path.exists(base_dir):
        continue
    
    tools = find_tool_files(base_dir)
    
    print(f"\n📁 {base_dir.upper()}")
    print("-" * 80)
    
    without_export = []
    with_export = []
    
    for tool in tools:
        rel_path = tool.replace('\\', '/')
        tool_name = os.path.basename(tool)
        
        if has_export_results(tool):
            with_export.append(rel_path)
            print(f"  ✅ {tool_name}")
        else:
            without_export.append(rel_path)
            print(f"  ❌ {tool_name}")
    
    all_without_export.extend(without_export)
    all_with_export.extend(with_export)
    
    print(f"\n  Resumen: {len(with_export)} con export_results(), {len(without_export)} sin export_results()")

print("\n" + "=" * 80)
print("RESUMEN GENERAL")
print("=" * 80)
print(f"\n✅ Herramientas CON export_results():    {len(all_with_export)}")
print(f"❌ Herramientas SIN export_results():    {len(all_without_export)}")
print(f"📊 TOTAL:                                {len(all_with_export) + len(all_without_export)}")

print("\n" + "=" * 80)
print("HERRAMIENTAS SIN export_results() - LISTA COMPLETA")
print("=" * 80)

for tool in all_without_export:
    print(f"  {tool}")

# Generar lista Python para scripts
print("\n" + "=" * 80)
print("LISTA PYTHON PARA SCRIPTS")
print("=" * 80)
print("\ntools_without_export = [")
for tool in all_without_export:
    print(f"    '{tool}',")
print("]")
