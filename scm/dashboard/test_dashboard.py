#!/usr/bin/env python3
"""
Script de prueba para validar la implementación del Dashboard Matutino
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def test_consolidator():
    """Prueba el consolidator"""
    print("\n" + "="*60)
    print("TEST 1: Dashboard Consolidator")
    print("="*60)
    
    try:
        from dashboard_consolidator import DashboardConsolidator
        
        # Crear consolidator
        consolidator = DashboardConsolidator(
            org="test-org",
            project="test-project",
            pat="test-pat",
            output_dir="outcome/dashboard"
        )
        
        # Ejecutar
        dashboard_data = consolidator.run()
        
        # Validar
        assert dashboard_data is not None, "dashboard_data es None"
        assert 'timestamp' in dashboard_data, "Falta timestamp"
        assert 'metrics' in dashboard_data, "Falta metrics"
        assert 'summary' in dashboard_data, "Falta summary"
        
        print("✅ Consolidator funcionando correctamente")
        print(f"   - Health Score: {dashboard_data['summary']['health_score']}/100")
        print(f"   - Code Coverage: {dashboard_data['summary']['code_coverage']}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en Consolidator: {str(e)}")
        return False


def test_generator():
    """Prueba el generator"""
    print("\n" + "="*60)
    print("TEST 2: Dashboard Generator")
    print("="*60)
    
    try:
        from dashboard_generator import DashboardGenerator
        
        # Crear generator
        generator = DashboardGenerator(
            input_file="outcome/dashboard/dashboard_data.json",
            output_file="outcome/dashboard/dashboard.html"
        )
        
        # Ejecutar
        result = generator.generate()
        
        # Validar
        assert result is True, "Generator retornó False"
        assert Path("outcome/dashboard/dashboard.html").exists(), "HTML no fue creado"
        
        # Validar contenido
        with open("outcome/dashboard/dashboard.html", 'r') as f:
            html_content = f.read()
        
        assert '<html' in html_content, "HTML inválido"
        assert 'Dashboard Matutino' in html_content, "Falta título"
        assert 'Health Score' in html_content, "Falta Health Score"
        
        print("✅ Generator funcionando correctamente")
        print(f"   - HTML generado: outcome/dashboard/dashboard.html")
        print(f"   - Tamaño: {len(html_content)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en Generator: {str(e)}")
        return False


def test_data_structure():
    """Prueba la estructura de datos"""
    print("\n" + "="*60)
    print("TEST 3: Estructura de Datos")
    print("="*60)
    
    try:
        # Leer dashboard_data.json
        with open("outcome/dashboard/dashboard_data.json", 'r') as f:
            data = json.load(f)
        
        # Validar estructura
        assert 'timestamp' in data, "Falta timestamp"
        assert 'status' in data, "Falta status"
        assert 'metrics' in data, "Falta metrics"
        assert 'alerts' in data, "Falta alerts"
        assert 'summary' in data, "Falta summary"
        
        # Validar métricas
        metrics = data['metrics']
        assert 'health_score' in metrics, "Falta health_score"
        assert 'code_coverage' in metrics, "Falta code_coverage"
        assert 'pr_metrics' in metrics, "Falta pr_metrics"
        
        # Validar health_score
        health = metrics['health_score']
        assert 'overall_score' in health, "Falta overall_score"
        assert 'deployment_frequency' in health, "Falta deployment_frequency"
        assert 'mttr_hours' in health, "Falta mttr_hours"
        
        # Validar code_coverage
        coverage = metrics['code_coverage']
        assert 'overall_coverage' in coverage, "Falta overall_coverage"
        assert 'line_coverage' in coverage, "Falta line_coverage"
        
        print("✅ Estructura de datos válida")
        print(f"   - Health Score: {health['overall_score']}/100")
        print(f"   - Code Coverage: {coverage['overall_coverage']}%")
        print(f"   - Deployment Frequency: {health['deployment_frequency']}/semana")
        print(f"   - MTTR: {health['mttr_hours']} horas")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en estructura de datos: {str(e)}")
        return False


def test_history_manager():
    """Prueba el gestor de histórico"""
    print("\n" + "="*60)
    print("TEST 4: History Manager")
    print("="*60)
    
    try:
        from dashboard_consolidator import HistoryManager
        
        # Crear history manager
        history_manager = HistoryManager()
        
        # Leer datos
        with open("outcome/dashboard/dashboard_data.json", 'r') as f:
            dashboard_data = json.load(f)
        
        # Guardar snapshot
        history_manager.save_daily_snapshot(dashboard_data)
        
        # Validar
        today = datetime.now().strftime('%Y-%m-%d')
        history_dir = Path("outcome/dashboard/history") / today
        
        assert history_dir.exists(), "Directorio de histórico no fue creado"
        
        # Validar archivos
        data_files = list(history_dir.glob("dashboard_data_*.json"))
        summary_files = list(history_dir.glob("metrics_summary_*.json"))
        
        assert len(data_files) > 0, "No se creó dashboard_data"
        assert len(summary_files) > 0, "No se creó metrics_summary"
        
        print("✅ History Manager funcionando correctamente")
        print(f"   - Directorio: {history_dir}")
        print(f"   - Archivos de datos: {len(data_files)}")
        print(f"   - Archivos de resumen: {len(summary_files)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en History Manager: {str(e)}")
        return False


def test_alerts():
    """Prueba la detección de alertas"""
    print("\n" + "="*60)
    print("TEST 5: Detección de Alertas")
    print("="*60)
    
    try:
        # Leer dashboard_data.json
        with open("outcome/dashboard/dashboard_data.json", 'r') as f:
            data = json.load(f)
        
        alerts = data.get('alerts', {})
        
        print("✅ Alertas evaluadas")
        print(f"   - Alertas críticas: {len(alerts.get('critical', []))}")
        print(f"   - Advertencias: {len(alerts.get('warning', []))}")
        print(f"   - Info: {len(alerts.get('info', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en detección de alertas: {str(e)}")
        return False


def main():
    """Ejecuta todas las pruebas"""
    print("\n" + "="*60)
    print("PRUEBAS DEL DASHBOARD MATUTINO DEVSECOPS")
    print("="*60)
    
    results = []
    
    # Ejecutar pruebas
    results.append(("Consolidator", test_consolidator()))
    results.append(("Generator", test_generator()))
    results.append(("Estructura de Datos", test_data_structure()))
    results.append(("History Manager", test_history_manager()))
    results.append(("Alertas", test_alerts()))
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE PRUEBAS")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} pruebas pasadas")
    
    if passed == total:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} prueba(s) fallaron")
        return 1


if __name__ == '__main__':
    sys.exit(main())
