#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador de registro de herramientas AWS en tools.py
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# Obtener directorio actual
BASE_DIR = Path(__file__).parent.absolute()

# Leer tools.py
tools_py_path = BASE_DIR / "tools.py"
with open(tools_py_path, 'r', encoding='utf-8') as f:
    tools_content = f.read()

# Extraer todas las rutas de herramientas del diccionario TOOLS
pattern = r'"path":\s*"([^"]+)"'
registered_paths = set(re.findall(pattern, tools_content))

# Obtener todas las herramientas del filesystem
aws_tools = set()
for root, dirs, files in os.walk(BASE_DIR):
    # Excluir directorios especiales
    dirs[:] = [d for d in dirs if d not in ['__pycache__', '.venv', 'tests', 'outcome']]
    
    for file in files:
        if file.startswith('aws_') and file.endswith('.py'):
            rel_path = os.path.relpath(os.path.join(root, file), BASE_DIR)
            # Normalizar path (convertir backslash a forward slash)
            rel_path = rel_path.replace('\\', '/')
            aws_tools.add(rel_path)

# Comparar
registered_tools = {p for p in registered_paths if p.startswith('aws_') or '/' in p}
unregistered = aws_tools - registered_tools
all_registered = aws_tools - unregistered

print("=" * 80)
print("VALIDACIÓN DE REGISTRO DE HERRAMIENTAS AWS")
print("=" * 80)
print()

print(f"📊 ESTADÍSTICAS:")
print(f"  • Herramientas en filesystem: {len(aws_tools)}")
print(f"  • Herramientas registradas: {len(all_registered)}")
print(f"  • Herramientas NO registradas: {len(unregistered)}")
print(f"  • Cobertura: {len(all_registered) / len(aws_tools) * 100:.1f}%")
print()

if unregistered:
    print("⚠️  HERRAMIENTAS NO REGISTRADAS EN tools.py:")
    print("-" * 80)
    for tool in sorted(unregistered):
        print(f"  ❌ {tool}")
    print()
else:
    print("✅ TODAS LAS HERRAMIENTAS ESTÁN REGISTRADAS EN tools.py")
    print()

print("✅ HERRAMIENTAS REGISTRADAS:")
print("-" * 80)
for tool in sorted(all_registered):
    print(f"  ✓ {tool}")
print()

# Crear tabla de resumen por categoría
print("📋 RESUMEN POR CATEGORÍA:")
print("-" * 80)

categories = defaultdict(list)
for tool in sorted(aws_tools):
    # Extraer categoría del path (primer directorio)
    parts = tool.split('/')
    if len(parts) > 1:
        category = parts[0]
    else:
        category = 'root'
    
    status = '✅' if tool in all_registered else '❌'
    categories[category].append((tool, status))

for category in sorted(categories.keys()):
    tools_in_cat = categories[category]
    registered_count = sum(1 for _, status in tools_in_cat if status == '✅')
    total_count = len(tools_in_cat)
    
    print(f"\n{category.upper()} ({registered_count}/{total_count}):")
    for tool, status in tools_in_cat:
        tool_name = tool.split('/')[-1]
        print(f"  {status} {tool_name}")

print()
print("=" * 80)

# Retornar código de salida
exit(0 if not unregistered else 1)
