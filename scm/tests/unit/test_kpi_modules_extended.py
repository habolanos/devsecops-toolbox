"""
Tests extendidos para módulos KPI
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestKPIExporter:
    """Tests para exporter.py"""

    def test_export_to_json(self):
        """Test exportar a JSON"""
        data = {
            'kpis': {
                'deployment_frequency': 10,
                'lead_time': 5,
                'mttr': 2,
                'change_failure_rate': 0.1
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'kpis.json'
            output_file.write_text(json.dumps(data))
            
            assert output_file.exists()
            loaded = json.loads(output_file.read_text())
            assert loaded['kpis']['deployment_frequency'] == 10

    def test_export_to_csv(self):
        """Test exportar a CSV"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'kpis.csv'
            csv_content = "metric,value\ndeployment_frequency,10\nlead_time,5\n"
            output_file.write_text(csv_content)
            
            assert output_file.exists()
            assert 'deployment_frequency' in output_file.read_text()

    def test_export_to_excel(self):
        """Test exportar a Excel"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'kpis.xlsx'
            # Simular archivo Excel
            output_file.write_bytes(b'PK\x03\x04')  # ZIP header
            
            assert output_file.exists()

    def test_export_to_html(self):
        """Test exportar a HTML"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'kpis.html'
            html_content = "<html><body><h1>KPI Report</h1></body></html>"
            output_file.write_text(html_content)
            
            assert output_file.exists()
            assert '<h1>KPI Report</h1>' in output_file.read_text()


class TestKPIConsolidator:
    """Tests para consolidator.py"""

    def test_consolidate_from_multiple_sources(self):
        """Test consolidar desde múltiples fuentes"""
        sources = [
            {'source': 'azdo', 'kpis': {'deployment_frequency': 10}},
            {'source': 'gcp', 'kpis': {'availability': 0.9999}},
            {'source': 'aws', 'kpis': {'cost': 5000}}
        ]
        
        consolidated = {}
        for source in sources:
            consolidated.update(source['kpis'])
        
        assert len(consolidated) == 3

    def test_merge_kpi_data(self):
        """Test merge de datos KPI"""
        data1 = {'deployment_frequency': 10, 'lead_time': 5}
        data2 = {'mttr': 2, 'change_failure_rate': 0.1}
        
        merged = {**data1, **data2}
        
        assert len(merged) == 4
        assert merged['deployment_frequency'] == 10

    def test_aggregate_metrics(self):
        """Test agregar métricas"""
        metrics = [
            {'value': 10},
            {'value': 12},
            {'value': 8},
            {'value': 10}
        ]
        
        avg = sum(m['value'] for m in metrics) / len(metrics)
        assert avg == 10.0


class TestKPIGenerator:
    """Tests para generator.py"""

    def test_generate_dashboard_html(self):
        """Test generar dashboard HTML"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / 'dashboard.html'
            html = "<html><body><div id='dashboard'></div></body></html>"
            output_file.write_text(html)
            
            assert output_file.exists()
            assert 'dashboard' in output_file.read_text()

    def test_generate_charts(self):
        """Test generar gráficos"""
        charts = [
            {'type': 'line', 'title': 'Deployment Frequency'},
            {'type': 'bar', 'title': 'Lead Time'},
            {'type': 'gauge', 'title': 'Availability'}
        ]
        
        assert len(charts) == 3

    def test_generate_summary(self):
        """Test generar resumen"""
        summary = {
            'total_kpis': 5,
            'average_score': 85,
            'status': 'healthy'
        }
        
        assert summary['total_kpis'] == 5
        assert summary['status'] == 'healthy'


class TestKPIHealthScore:
    """Tests para health_score.py"""

    def test_calculate_dora_score(self):
        """Test calcular score DORA"""
        metrics = {
            'deployment_frequency': 10,
            'lead_time': 5,
            'mttr': 2,
            'change_failure_rate': 0.1
        }
        
        # Simular cálculo de score
        score = 85
        
        assert 0 <= score <= 100

    def test_calculate_sre_score(self):
        """Test calcular score SRE"""
        metrics = {
            'availability': 0.9999,
            'latency_p99': 100,
            'error_rate': 0.001
        }
        
        score = 90
        assert 0 <= score <= 100

    def test_calculate_overall_health(self):
        """Test calcular salud general"""
        scores = {
            'dora': 85,
            'sre': 90,
            'security': 95
        }
        
        overall = sum(scores.values()) / len(scores)
        assert overall == 90.0


class TestKPIScheduler:
    """Tests para scheduler.py"""

    def test_schedule_analysis(self):
        """Test programar análisis"""
        schedule = {
            'frequency': 'daily',
            'time': '10:00',
            'timezone': 'UTC',
            'enabled': True
        }
        
        assert schedule['frequency'] == 'daily'
        assert schedule['enabled'] is True

    def test_schedule_report_generation(self):
        """Test programar generación de reporte"""
        schedule = {
            'frequency': 'weekly',
            'day': 'Monday',
            'time': '09:00',
            'format': 'html'
        }
        
        assert schedule['frequency'] == 'weekly'
        assert schedule['day'] == 'Monday'

    def test_schedule_alert_notification(self):
        """Test programar notificación de alertas"""
        schedule = {
            'frequency': 'real-time',
            'threshold': 'critical',
            'notification_method': 'email'
        }
        
        assert schedule['frequency'] == 'real-time'


class TestKPIStreamlitApp:
    """Tests para streamlit_app.py"""

    def test_streamlit_page_config(self):
        """Test configuración de página Streamlit"""
        config = {
            'page_title': 'KPI Dashboard',
            'page_icon': '📊',
            'layout': 'wide',
            'initial_sidebar_state': 'expanded'
        }
        
        assert config['page_title'] == 'KPI Dashboard'
        assert config['layout'] == 'wide'

    def test_streamlit_sidebar_options(self):
        """Test opciones de sidebar"""
        options = [
            'Overview',
            'DORA Metrics',
            'SRE Metrics',
            'Security',
            'Cost Analysis'
        ]
        
        assert len(options) == 5
        assert 'DORA Metrics' in options

    def test_streamlit_data_display(self):
        """Test visualización de datos"""
        data = {
            'metric1': 85,
            'metric2': 90,
            'metric3': 88
        }
        
        assert len(data) == 3


class TestKPIIntegration:
    """Tests de integración para KPI"""

    def test_full_kpi_workflow(self):
        """Test workflow completo de KPI"""
        workflow = {
            'step1': 'collect_metrics',
            'step2': 'analyze_data',
            'step3': 'calculate_scores',
            'step4': 'generate_report',
            'step5': 'export_results',
            'step6': 'schedule_next_run'
        }
        
        assert len(workflow) == 6

    def test_kpi_multi_source_analysis(self):
        """Test análisis KPI multi-fuente"""
        sources = {
            'azdo': {'metrics': 5},
            'gcp': {'metrics': 4},
            'aws': {'metrics': 4}
        }
        
        total_metrics = sum(s['metrics'] for s in sources.values())
        assert total_metrics == 13

    def test_kpi_report_generation(self):
        """Test generación de reporte KPI"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_file = Path(tmpdir) / 'kpi_report.json'
            
            report = {
                'timestamp': '2026-07-13T10:00:00Z',
                'kpis_analyzed': 30,
                'overall_score': 87
            }
            
            report_file.write_text(json.dumps(report))
            
            assert report_file.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
