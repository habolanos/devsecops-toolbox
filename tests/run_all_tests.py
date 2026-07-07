#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Testing Completo

Ejecuta todos los tests para Tools 35, 36, 37 con reporte detallado.

Uso:
    python tests/run_all_tests.py
    python tests/run_all_tests.py --verbose
    python tests/run_all_tests.py --coverage

Autor: Harold Adrian
"""

import sys
import unittest
import argparse
from pathlib import Path
from io import StringIO
import time

# Agregar rutas
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))


def run_tests(verbose=False, coverage=False):
    """Ejecuta todos los tests."""
    
    print("=" * 80)
    print("🧪 TESTING SUITE - Tools 35, 36, 37")
    print("=" * 80)
    print()
    
    # Importar test modules
    try:
        from test_cloud_functions_analyzer import (
            TestCloudFunctionsBase,
            TestCloudFunctionsMetrics,
            TestCloudFunctionsIntegration
        )
        print("✓ Módulo test_cloud_functions_analyzer importado")
    except Exception as e:
        print(f"✗ Error importando test_cloud_functions_analyzer: {e}")
        return False
    
    try:
        from test_infrastructure_consolidator import (
            TestLoadBalancerExtractor,
            TestCloudRunExtractor,
            TestCloudFunctionsExtractor,
            TestRelationshipMapper,
            TestConsolidationIntegration,
            TestConsolidationMetrics
        )
        print("✓ Módulo test_infrastructure_consolidator importado")
    except Exception as e:
        print(f"✗ Error importando test_infrastructure_consolidator: {e}")
        return False
    
    print()
    print("=" * 80)
    print("📋 EJECUTANDO TESTS")
    print("=" * 80)
    print()
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar tests de Cloud Functions Analyzer
    print("📦 Tool 35: Cloud Functions Analyzer")
    suite.addTests(loader.loadTestsFromTestCase(TestCloudFunctionsBase))
    suite.addTests(loader.loadTestsFromTestCase(TestCloudFunctionsMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestCloudFunctionsIntegration))
    print(f"   ├─ TestCloudFunctionsBase")
    print(f"   ├─ TestCloudFunctionsMetrics")
    print(f"   └─ TestCloudFunctionsIntegration")
    
    # Agregar tests de Infrastructure Consolidator
    print()
    print("📦 Tool 36: Infrastructure Consolidator")
    suite.addTests(loader.loadTestsFromTestCase(TestLoadBalancerExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestCloudRunExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestCloudFunctionsExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestRelationshipMapper))
    suite.addTests(loader.loadTestsFromTestCase(TestConsolidationIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestConsolidationMetrics))
    print(f"   ├─ TestLoadBalancerExtractor")
    print(f"   ├─ TestCloudRunExtractor")
    print(f"   ├─ TestCloudFunctionsExtractor")
    print(f"   ├─ TestRelationshipMapper")
    print(f"   ├─ TestConsolidationIntegration")
    print(f"   └─ TestConsolidationMetrics")
    
    print()
    print("=" * 80)
    print("🏃 RESULTADOS")
    print("=" * 80)
    print()
    
    # Ejecutar tests
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
    
    start_time = time.time()
    result = runner.run(suite)
    elapsed_time = time.time() - start_time
    
    # Resumen
    print()
    print("=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    print()
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = total_tests - failures - errors - skipped
    
    print(f"Total de Tests:        {total_tests}")
    print(f"✓ Pasados:             {passed}")
    print(f"✗ Fallidos:            {failures}")
    print(f"⚠ Errores:             {errors}")
    print(f"⊘ Saltados:            {skipped}")
    print()
    print(f"Tiempo de Ejecución:   {elapsed_time:.2f}s")
    print()
    
    # Tasa de éxito
    if total_tests > 0:
        success_rate = (passed / total_tests) * 100
        print(f"Tasa de Éxito:         {success_rate:.1f}%")
    
    print()
    
    # Detalles de fallos
    if failures > 0:
        print("=" * 80)
        print("❌ FALLOS")
        print("=" * 80)
        for test, traceback in result.failures:
            print()
            print(f"Test: {test}")
            print("-" * 80)
            print(traceback)
    
    # Detalles de errores
    if errors > 0:
        print()
        print("=" * 80)
        print("⚠️  ERRORES")
        print("=" * 80)
        for test, traceback in result.errors:
            print()
            print(f"Test: {test}")
            print("-" * 80)
            print(traceback)
    
    # Resultado final
    print()
    print("=" * 80)
    if result.wasSuccessful():
        print("✅ TODOS LOS TESTS PASARON")
        print("=" * 80)
        return True
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("=" * 80)
        return False


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Testing Suite para Tools 35, 36, 37",
        add_help=True
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Modo verbose (más detalles)"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generar reporte de cobertura"
    )
    
    args = parser.parse_args()
    
    success = run_tests(verbose=args.verbose, coverage=args.coverage)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
