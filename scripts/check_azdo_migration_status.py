#!/usr/bin/env python3
"""Script para verificar el estado de migración de herramientas AZDO."""

import os
import re
from pathlib import Path

def check_migration_status(filepath):
    """Verifica el estado de migración de una herramienta."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        has_import = 'from export_manager import ExportManager' in content
        has_export_results = 'def export_results(' in content
        
        if not has_export_results:
            return "NO_EXPORT_RESULTS"
        
        # Buscar si usa ExportManager en export_results
        export_pattern = r'def export_results\([^)]*\):[^}]*?(?=\ndef |\Z)'
        match = re.search(export_pattern, content, re.DOTALL)
        
        if match:
            export_func = match.group(0)
            uses_export_manager = 'manager = ExportManager' in export_func
            has_fallback = 'if not EXPORT_MANAGER_AVAILABLE:' in export_func
            
            if uses_export_manager and has_fallback:
                return "FULLY_MIGRATED"
            elif has_import and not uses_export_manager:
                return "IMPORT_ONLY"
            else:
                return "PARTIAL"
        
        return "UNKNOWN"
    except Exception as e:
        return f"ERROR: {e}"

# Encontrar todas las herramientas AZDO
azdo_dir = 'scm/azdo'
tools = []

for root, dirs, filenames in os.walk(azdo_dir):
    for filename in filenames:
        if filename.endswith('.py') and not filename.startswith('__'):
            filepath = os.path.join(root, filename)
            tools.append(filepath)

print("=" * 80)
print("ESTADO DE MIGRACIÓN - HERRAMIENTAS AZDO")
print("=" * 80)

status_counts = {
    "FULLY_MIGRATED": [],
    "PARTIAL": [],
    "IMPORT_ONLY": [],
    "NO_EXPORT_RESULTS": [],
    "UNKNOWN": [],
    "ERROR": []
}

for tool in sorted(tools):
    status = check_migration_status(tool)
    tool_name = os.path.basename(tool)
    
    if status.startswith("ERROR"):
        status_counts["ERROR"].append((tool_name, status))
    else:
        status_counts[status].append(tool_name)
    
    icon = "✅" if status == "FULLY_MIGRATED" else "⏳" if status == "PARTIAL" else "⚠️" if status == "IMPORT_ONLY" else "❌" if status == "NO_EXPORT_RESULTS" else "❓"
    print(f"{icon} {tool_name:50} {status}")

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"✅ Completamente migradas:     {len(status_counts['FULLY_MIGRATED'])}")
print(f"⏳ Parcialmente migradas:      {len(status_counts['PARTIAL'])}")
print(f"⚠️  Solo importes:             {len(status_counts['IMPORT_ONLY'])}")
print(f"❌ Sin export_results:         {len(status_counts['NO_EXPORT_RESULTS'])}")
print(f"❓ Desconocido:                {len(status_counts['UNKNOWN'])}")
print(f"🔴 Errores:                    {len(status_counts['ERROR'])}")

print("\n" + "=" * 80)
print("HERRAMIENTAS PENDIENTES DE MIGRACIÓN")
print("=" * 80)

pending = status_counts['PARTIAL'] + status_counts['IMPORT_ONLY']
if pending:
    for tool in sorted(pending):
        print(f"  - {tool}")
else:
    print("  ✅ Todas las herramientas AZDO están completamente migradas")

print("\n" + "=" * 80)
