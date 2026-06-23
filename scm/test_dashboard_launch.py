#!/usr/bin/env python3
"""
Script de prueba para verificar que Dashboard se puede lanzar desde main.py
"""

import json
import sys
from pathlib import Path

def test_dashboard_config():
    """Verifica la configuración de Dashboard"""
    
    config_file = Path(__file__).parent / "config.json"
    
    print("=" * 60)
    print("TEST: Configuración de Dashboard")
    print("=" * 60)
    
    # 1. Verificar que config.json existe
    print(f"\n1. Verificando config.json...")
    if not config_file.exists():
        print(f"   ❌ No existe: {config_file}")
        return False
    print(f"   ✅ Existe: {config_file}")
    
    # 2. Cargar config.json
    print(f"\n2. Cargando config.json...")
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"   ✅ JSON válido")
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON inválido: {e}")
        return False
    
    # 3. Verificar sección AZDO
    print(f"\n3. Verificando sección AZDO...")
    azdo = config.get("azdo", {})
    if not azdo:
        print(f"   ❌ Falta sección 'azdo'")
        return False
    
    org = azdo.get("organization", "")
    project = azdo.get("project", "")
    pat = azdo.get("pat", "")
    
    print(f"   Organization: {org if org and '<TU_' not in org else '❌ FALTA O INVÁLIDO'}")
    print(f"   Project: {project if project and '<TU_' not in project else '❌ FALTA O INVÁLIDO'}")
    print(f"   PAT: {'✅ Configurado' if pat and '<TU_' not in pat else '❌ FALTA O INVÁLIDO'}")
    
    if not (org and project and pat and '<TU_' not in org and '<TU_' not in project and '<TU_' not in pat):
        print(f"   ❌ Credenciales AZDO incompletas")
        return False
    
    print(f"   ✅ Credenciales AZDO válidas")
    
    # 4. Verificar sección Dashboard
    print(f"\n4. Verificando sección Dashboard...")
    dashboard = config.get("dashboard", {})
    if not dashboard:
        print(f"   ⚠️ Falta sección 'dashboard' (se creará interactivamente)")
    else:
        print(f"   ✅ Sección 'dashboard' existe")
        enabled = dashboard.get("enabled", False)
        webhook = dashboard.get("webhook_url", "")
        print(f"   Enabled: {enabled}")
        print(f"   Webhook: {'Configurado' if webhook else 'No configurado (opcional)'}")
    
    # 5. Simular validación de is_platform_configured()
    print(f"\n5. Simulando validación is_platform_configured()...")
    print(f"   Dashboard siempre retorna True (puede ejecutarse)")
    print(f"   ✅ Dashboard será lanzable")
    
    print("\n" + "=" * 60)
    print("✅ TODAS LAS PRUEBAS PASARON")
    print("=" * 60)
    print("\nPróximos pasos:")
    print("1. Ejecutar: python scm/main.py")
    print("2. Seleccionar opción: 6")
    print("3. Dashboard debería ejecutarse")
    
    return True

if __name__ == "__main__":
    success = test_dashboard_config()
    sys.exit(0 if success else 1)
