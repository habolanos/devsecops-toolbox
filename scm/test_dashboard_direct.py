#!/usr/bin/env python3
"""
Script para probar Dashboard directamente sin launcher
"""

import subprocess
import sys
from pathlib import Path

def test_dashboard():
    """Prueba ejecutar Dashboard directamente"""
    
    print("=" * 60)
    print("TEST: Ejecutar Dashboard Directamente")
    print("=" * 60)
    
    # Parámetros
    org = "Coppel-Retail"
    project = "Cadena_de_Suministros"
    pat = "test_pat_token"  # Token de prueba
    
    # Ruta del consolidator
    consolidator = Path(__file__).parent / "dashboard" / "dashboard_consolidator.py"
    
    if not consolidator.exists():
        print(f"❌ No existe: {consolidator}")
        return False
    
    print(f"\n1. Ejecutando Dashboard Consolidator...")
    print(f"   Ruta: {consolidator}")
    print(f"   Org: {org}")
    print(f"   Project: {project}")
    
    # Ejecutar
    cmd = [sys.executable, str(consolidator), "--org", org, "--project", project, "--pat", pat]
    
    print(f"\n2. Comando: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=False, capture_output=False)
        print(f"\n3. Código de retorno: {result.returncode}")
        
        if result.returncode == 0:
            print("   ✅ Dashboard ejecutado exitosamente")
        else:
            print(f"   ⚠️ Dashboard retornó código: {result.returncode}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_dashboard()
    sys.exit(0 if success else 1)
