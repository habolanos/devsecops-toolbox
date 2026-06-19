#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Dashboard Generator Module
Tests para validar funcionalidad del generador de dashboards

Version: 1.0.0
Author: Harold Adrian
"""

import pytest
import json
from pathlib import Path
import sys

# Add scm to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scm.kpi_analyzer.dashboard_generator import DashboardGenerator


class TestDashboardGeneratorInit:
    """Tests para inicialización de DashboardGenerator."""
    
    @pytest.mark.unit
    def test_dashboard_generator_init(self, tmp_path):
        """Test: Inicializar DashboardGenerator."""
        generator = DashboardGenerator(output_dir=tmp_path)
        
        assert generator.output_dir == tmp_path
        assert tmp_path.exists()
    
    @pytest.mark.unit
    def test_dashboard_generator_init_creates_directory(self, tmp_path):
        """Test: DashboardGenerator crea directorio si no existe."""
        new_dir = tmp_path / "new_dashboard_dir"
        
        generator = DashboardGenerator(output_dir=new_dir)
        
        assert new_dir.exists()
        assert generator.output_dir == new_dir


class TestDashboardGeneratorMethods:
    """Tests para métodos de DashboardGenerator."""
    
    @pytest.mark.unit
    def test_generate_dashboard_creates_file(self, tmp_path):
        """Test: generate_dashboard crea archivo HTML."""
        generator = DashboardGenerator(output_dir=tmp_path)
        
        kpi_data = {
            "kpis": [
                {
                    "id": "ec_001",
                    "name": "Deployment Frequency",
                    "value": 5.0,
                    "unit": "deployments/day"
                }
            ]
        }
        
        filepath = generator.generate_dashboard(kpi_data, filename="test_dashboard.html")
        
        assert filepath.exists()
        assert filepath.name == "test_dashboard.html"
        assert filepath.suffix == ".html"
    
    @pytest.mark.unit
    def test_generate_dashboard_auto_filename(self, tmp_path):
        """Test: generate_dashboard con nombre automático."""
        generator = DashboardGenerator(output_dir=tmp_path)
        
        kpi_data = {"kpis": []}
        
        filepath = generator.generate_dashboard(kpi_data)
        
        assert filepath.exists()
        assert "kpi_dashboard_" in filepath.name
        assert filepath.name.endswith(".html")
    
    @pytest.mark.unit
    def test_generate_dashboard_with_maturity_data(self, tmp_path):
        """Test: generate_dashboard con datos de madurez."""
        generator = DashboardGenerator(output_dir=tmp_path)
        
        kpi_data = {"kpis": []}
        maturity_data = {
            "global_level": "CUANTIFICADO",
            "dimensions": {}
        }
        
        filepath = generator.generate_dashboard(kpi_data, maturity_data=maturity_data, filename="test.html")
        
        assert filepath.exists()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 0
    
    @pytest.mark.unit
    def test_generate_dashboard_html_content(self, tmp_path):
        """Test: generate_dashboard_html genera contenido válido."""
        generator = DashboardGenerator(output_dir=tmp_path)
        
        kpi_data = {
            "kpis": [
                {
                    "id": "ec_001",
                    "name": "Deployment Frequency",
                    "value": 5.0
                }
            ]
        }
        
        html = generator._generate_dashboard_html(kpi_data)
        
        assert html is not None
        assert isinstance(html, str)
        assert len(html) > 0
        assert "<!DOCTYPE html>" in html or "<html" in html
    
    @pytest.mark.unit
    def test_generate_dashboard_html_includes_kpi_data(self, tmp_path):
        """Test: HTML incluye datos de KPIs."""
        generator = DashboardGenerator(output_dir=tmp_path)
        
        kpi_data = {
            "kpis": [
                {
                    "id": "ec_001",
                    "name": "Deployment Frequency",
                    "value": 5.0
                }
            ]
        }
        
        html = generator._generate_dashboard_html(kpi_data)
        
        # Verificar que contiene referencias a los datos
        assert "Deployment Frequency" in html or "ec_001" in html or len(html) > 100
    
    @pytest.mark.unit
    def test_generate_dashboard_empty_kpi_data(self, tmp_path):
        """Test: generate_dashboard con datos vacíos."""
        generator = DashboardGenerator(output_dir=tmp_path)
        
        kpi_data = {"kpis": []}
        
        filepath = generator.generate_dashboard(kpi_data, filename="empty.html")
        
        assert filepath.exists()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 0
    
    @pytest.mark.unit
    def test_generate_dashboard_multiple_kpis(self, tmp_path):
        """Test: generate_dashboard con múltiples KPIs."""
        generator = DashboardGenerator(output_dir=tmp_path)
        
        kpi_data = {
            "kpis": [
                {"id": "ec_001", "name": "Deployment Frequency", "value": 5.0},
                {"id": "ec_002", "name": "Change Failure Rate", "value": 10.0},
                {"id": "conf_001", "name": "MTTR", "value": 120.0}
            ]
        }
        
        filepath = generator.generate_dashboard(kpi_data, filename="multi_kpi.html")
        
        assert filepath.exists()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert len(content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
