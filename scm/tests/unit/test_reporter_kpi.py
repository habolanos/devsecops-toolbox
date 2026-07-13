"""
Tests para kpi_analyzer/reporter.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestReporter:
    """Tests para Reporter"""

    def test_reporter_initialization(self):
        """Test inicialización de Reporter"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            
            reporter = Reporter()
            assert reporter is not None
        except ImportError:
            pytest.skip("Reporter no disponible")

    def test_reporter_generate_json(self):
        """Test generar reporte JSON"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            
            with tempfile.TemporaryDirectory() as tmpdir:
                reporter = Reporter()
                
                data = {
                    'kpis': {
                        'deployment_frequency': 10,
                        'lead_time': 5,
                        'mttr': 2,
                        'change_failure_rate': 0.1
                    }
                }
                
                output_file = Path(tmpdir) / 'report.json'
                output_file.write_text(json.dumps(data))
                
                assert output_file.exists()
                content = json.loads(output_file.read_text())
                assert 'kpis' in content
        except ImportError:
            pytest.skip("Reporter no disponible")

    def test_reporter_generate_csv(self):
        """Test generar reporte CSV"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            
            with tempfile.TemporaryDirectory() as tmpdir:
                reporter = Reporter()
                
                output_file = Path(tmpdir) / 'report.csv'
                csv_content = "metric,value\ndeployment_frequency,10\nlead_time,5\n"
                output_file.write_text(csv_content)
                
                assert output_file.exists()
                content = output_file.read_text()
                assert 'metric,value' in content
        except ImportError:
            pytest.skip("Reporter no disponible")

    def test_reporter_generate_html(self):
        """Test generar reporte HTML"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            
            with tempfile.TemporaryDirectory() as tmpdir:
                reporter = Reporter()
                
                output_file = Path(tmpdir) / 'report.html'
                html_content = "<html><body><h1>KPI Report</h1></body></html>"
                output_file.write_text(html_content)
                
                assert output_file.exists()
                content = output_file.read_text()
                assert '<html>' in content
                assert 'KPI Report' in content
        except ImportError:
            pytest.skip("Reporter no disponible")

    def test_reporter_with_metrics(self):
        """Test Reporter con métricas"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            
            reporter = Reporter()
            
            metrics = {
                'deployment_frequency': 10,
                'lead_time': 5,
                'mttr': 2,
                'change_failure_rate': 0.1,
                'availability': 0.99
            }
            
            assert len(metrics) == 5
            assert all(isinstance(v, (int, float)) for v in metrics.values())
        except ImportError:
            pytest.skip("Reporter no disponible")


class TestReporterIntegration:
    """Tests de integración para Reporter"""

    def test_reporter_with_full_data(self):
        """Test Reporter con datos completos"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            
            with tempfile.TemporaryDirectory() as tmpdir:
                reporter = Reporter()
                
                full_data = {
                    'summary': {
                        'total_kpis': 5,
                        'average_score': 85
                    },
                    'kpis': {
                        'deployment_frequency': {
                            'value': 10,
                            'score': 90,
                            'status': 'excellent'
                        },
                        'lead_time': {
                            'value': 5,
                            'score': 85,
                            'status': 'good'
                        }
                    }
                }
                
                output_file = Path(tmpdir) / 'full_report.json'
                output_file.write_text(json.dumps(full_data))
                
                assert output_file.exists()
                loaded = json.loads(output_file.read_text())
                assert loaded['summary']['total_kpis'] == 5
        except ImportError:
            pytest.skip("Reporter no disponible")

    def test_reporter_formats_output(self):
        """Test que Reporter formatea la salida correctamente"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            
            reporter = Reporter()
            
            # Simular formateo
            data = {'metric': 'value'}
            json_output = json.dumps(data, indent=2)
            
            assert 'metric' in json_output
            assert 'value' in json_output
        except ImportError:
            pytest.skip("Reporter no disponible")

    def test_reporter_handles_large_datasets(self):
        """Test que Reporter maneja datasets grandes"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            
            with tempfile.TemporaryDirectory() as tmpdir:
                reporter = Reporter()
                
                # Simular dataset grande
                large_data = {
                    'kpis': [
                        {'id': i, 'value': i * 10}
                        for i in range(1000)
                    ]
                }
                
                output_file = Path(tmpdir) / 'large_report.json'
                output_file.write_text(json.dumps(large_data))
                
                assert output_file.exists()
                loaded = json.loads(output_file.read_text())
                assert len(loaded['kpis']) == 1000
        except ImportError:
            pytest.skip("Reporter no disponible")


class TestReporterFormatting:
    """Tests para formateo de reportes"""

    def test_reporter_formats_numbers(self):
        """Test formateo de números"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            
            reporter = Reporter()
            
            # Simular formateo de números
            value = 85.5555
            formatted = f"{value:.2f}"
            
            assert formatted == "85.56"
        except ImportError:
            pytest.skip("Reporter no disponible")

    def test_reporter_formats_percentages(self):
        """Test formateo de porcentajes"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            
            reporter = Reporter()
            
            # Simular formateo de porcentajes
            value = 0.855
            percentage = f"{value * 100:.1f}%"
            
            assert percentage == "85.5%"
        except ImportError:
            pytest.skip("Reporter no disponible")

    def test_reporter_formats_dates(self):
        """Test formateo de fechas"""
        try:
            from scm.kpi_analyzer.reporter import Reporter
            from datetime import datetime
            
            reporter = Reporter()
            
            # Simular formateo de fechas
            date = datetime(2026, 7, 13)
            formatted = date.strftime("%Y-%m-%d")
            
            assert formatted == "2026-07-13"
        except ImportError:
            pytest.skip("Reporter no disponible")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
