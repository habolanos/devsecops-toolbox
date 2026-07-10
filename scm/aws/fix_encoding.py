#!/usr/bin/env python3
"""
Script para arreglar encoding en archivos generados
"""

import os
import glob

def fix_file_encoding(filepath):
    """Arregla el encoding de un archivo"""
    try:
        # Intentar leer con diferentes encodings
        content = None
        for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except:
                continue
        
        if content is None:
            print(f"✗ No se pudo leer: {filepath}")
            return False
        
        # Verificar si ya tiene la declaración
        if content.startswith('# -*- coding:'):
            return False
        
        # Agregar declaración
        new_content = '# -*- coding: utf-8 -*-\n' + content
        
        # Escribir archivo con UTF-8
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"✗ Error procesando {filepath}: {e}")
        return False

def main():
    """Procesa todos los archivos AWS"""
    aws_dir = os.path.dirname(__file__)
    
    # Encontrar todos los archivos aws_*.py
    patterns = [
        os.path.join(aws_dir, '**', 'aws_*.py'),
        os.path.join(aws_dir, 'tests', '*.py')
    ]
    
    fixed = 0
    for pattern in patterns:
        for filepath in glob.glob(pattern, recursive=True):
            if fix_file_encoding(filepath):
                print(f"✓ Arreglado: {os.path.relpath(filepath, aws_dir)}")
                fixed += 1
    
    print(f"\n✓ Total arreglados: {fixed} archivos")

if __name__ == '__main__':
    main()
