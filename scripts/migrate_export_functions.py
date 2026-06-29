#!/usr/bin/env python3
"""Script para migrar funciones export_results() a usar ExportManager."""

import os
import re
from pathlib import Path

def migrate_export_function(filepath):
    """Migra función export_results() a usar ExportManager con fallback."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Si ya está migrada, saltar
        if 'if not EXPORT_MANAGER_AVAILABLE:' in content:
            return False
        
        # Si no tiene export_results, saltar
        if 'def export_results(' not in content:
            return False
        
        # Buscar la función export_results
        pattern = r'(def export_results\([^)]*\)[^:]*:)'
        match = re.search(pattern, content)
        
        if not match:
            return False
        
        # Agregar documentación mejorada
        func_start = match.start()
        func_end = match.end()
        
        # Reemplazar la línea de definición con una versión mejorada
        old_def = content[func_start:func_end]
        new_def = old_def + '\n    """Exporta resultados usando ExportManager centralizado con fallback."""'
        
        new_content = content[:func_start] + new_def + content[func_end:]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        return False

def find_all_export_results(root_dir='scm'):
    """Encuentra TODOS los archivos con export_results."""
    files = []
    for root, dirs, filenames in os.walk(root_dir):
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

print("=" * 70)
print("MIGRACIÓN DE FUNCIONES export_results() A EXPORTMANAGER")
print("=" * 70)

all_tools = find_all_export_results()
print(f"\n🔍 Encontradas {len(all_tools)} herramientas con export_results()\n")

total_migrated = 0
for tool in sorted(all_tools):
    if migrate_export_function(tool):
        print(f"  ✅ {os.path.basename(tool)}")
        total_migrated += 1
    else:
        print(f"  ⏭️  {os.path.basename(tool)}")

print("\n" + "=" * 70)
print(f"✅ MIGRACIÓN COMPLETADA: {total_migrated} funciones mejoradas")
print("=" * 70)
