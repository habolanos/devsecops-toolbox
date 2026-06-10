#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — KPI Analyzer Module
Tests para validar funcionalidad del analizador de KPIs

Version: 1.0.0
Author: Harold Adrian
"""

import pytest
import json
from pathlib import Path
import tempfile
import shutil
import sys

# Add scm to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scm.kpi_analyzer.benchmarks import (
    BenchmarkLevel,
    MaturityLevel,
    get_benchmark_level,
    get_benchmark_color,
    get_benchmark_emoji
)
from scm.kpi_analyzer.maturity_model import (
    evaluate_dimension,
    assess_maturity,
    get_level_name,
    get_level_color
)


class TestBenchmarks:
    """Tests para el módulo de benchmarks"""
    
    def test_benchmark_level_deployment_frequency(self):
        """Test benchmark level para deployment frequency"""
        # Elite: >= 1
        assert get_benchmark_level("ec_001", 1.5) == BenchmarkLevel.ELITE
        assert get_benchmark_level("ec_001", 1.0) == BenchmarkLevel.ELITE
        
        # High: 0.14-1
        assert get_benchmark_level("ec_001", 0.5) == BenchmarkLevel.HIGH
        
        # Medium: 0.03-0.14
        assert get_benchmark_level("ec_001", 0.1) == BenchmarkLevel.MEDIUM
        
        # Low: < 0.03
        assert get_benchmark_level("ec_001", 0.01) == BenchmarkLevel.LOW
    
    def test_benchmark_level_change_failure_rate(self):
        """Test benchmark level para change failure rate"""
        # Elite: < 5%
        assert get_benchmark_level("ec_002", 3.0) == BenchmarkLevel.ELITE
        
        # High: 5-15%
        assert get_benchmark_level("ec_002", 10.0) == BenchmarkLevel.HIGH
        
        # Medium: 15-30%
        assert get_benchmark_level("ec_002", 20.0) == BenchmarkLevel.MEDIUM
        
        # Low: > 30%
        assert get_benchmark_level("ec_002", 40.0) == BenchmarkLevel.LOW
    
    def test_benchmark_level_mttr(self):
        """Test benchmark level para MTTR"""
        # Elite: < 60 minutes
        assert get_benchmark_level("conf_001", 30.0) == BenchmarkLevel.ELITE
        
        # High: 60-240 minutes
        assert get_benchmark_level("conf_001", 120.0) == BenchmarkLevel.HIGH
        
        # Medium: 240-1440 minutes
        assert get_benchmark_level("conf_001", 600.0) == BenchmarkLevel.MEDIUM
        
        # Low: > 1440 minutes
        assert get_benchmark_level("conf_001", 2000.0) == BenchmarkLevel.LOW
    
    def test_benchmark_colors(self):
        """Test benchmark colors"""
        assert get_benchmark_color(BenchmarkLevel.ELITE) == "#2ecc71"
        assert get_benchmark_color(BenchmarkLevel.HIGH) == "#27ae60"
        assert get_benchmark_color(BenchmarkLevel.MEDIUM) == "#f39c12"
        assert get_benchmark_color(BenchmarkLevel.LOW) == "#e74c3c"
    
    def test_benchmark_emojis(self):
        """Test benchmark emojis"""
        assert get_benchmark_emoji(BenchmarkLevel.ELITE) == "💚"
        assert get_benchmark_emoji(BenchmarkLevel.HIGH) == "🟢"
        assert get_benchmark_emoji(BenchmarkLevel.MEDIUM) == "🟡"
        assert get_benchmark_emoji(BenchmarkLevel.LOW) == "🔴"


class TestMaturityModel:
    """Tests para el modelo de madurez"""
    
    def test_get_level_name(self):
        """Test nombres de niveles de madurez"""
        assert get_level_name(MaturityLevel.CAOTICO) == "Caótico"
        assert get_level_name(MaturityLevel.INICIAL) == "Inicial"
        assert get_level_name(MaturityLevel.GESTIONADO) == "Gestionado"
        assert get_level_name(MaturityLevel.DEFINIDO) == "Definido"
        assert get_level_name(MaturityLevel.CUANTIFICADO) == "Cuantificado"
        assert get_level_name(MaturityLevel.OPTIMIZADO) == "Optimizado"
    
    def test_get_level_color(self):
        """Test colores de niveles de madurez"""
        assert get_level_color(MaturityLevel.CAOTICO) == "#e74c3c"
        assert get_level_color(MaturityLevel.OPTIMIZADO) == "#2ecc71"
    
    def test_evaluate_dimension_caotico(self):
        """Test evaluación de dimensión en nivel caótico"""
        kpi_values = {
            "deployment_frequency": 0.01,
            "change_failure_rate": 60.0,
            "mttr": 20000.0
        }
        
        score = evaluate_dimension("entrega_continua", kpi_values, MaturityLevel.INICIAL)
        
        assert score.name == "entrega_continua"
        assert score.kpis_total > 0
        assert score.kpis_met <= score.kpis_total
    
    def test_evaluate_dimension_elite(self):
        """Test evaluación de dimensión en nivel elite"""
        kpi_values = {
            "deployment_frequency": 5.0,
            "change_failure_rate": 1.0,
            "lead_time_for_changes": 0.5,
            "deployment_success_rate": 99.0
        }
        
        score = evaluate_dimension("entrega_continua", kpi_values, MaturityLevel.OPTIMIZADO)
        
        assert score.name == "entrega_continua"
        assert score.score_percentage > 0.0
    
    def test_assess_maturity_low(self):
        """Test evaluación de madurez baja"""
        kpi_values = {
            "deployment_frequency": 0.01,
            "change_failure_rate": 50.0,
            "mttr": 15000.0,
            "availability": 90.0
        }
        
        assessment = assess_maturity(kpi_values)
        
        assert assessment is not None
        assert assessment.global_level in [MaturityLevel.CAOTICO, MaturityLevel.INICIAL]
        assert len(assessment.dimension_scores) > 0
        assert len(assessment.recommended_actions) > 0
    
    def test_assess_maturity_high(self):
        """Test evaluación de madurez alta"""
        kpi_values = {
            "deployment_frequency": 5.0,
            "change_failure_rate": 1.0,
            "lead_time_for_changes": 0.5,
            "deployment_success_rate": 99.0,
            "mttr": 10.0,
            "availability": 99.95,
            "mtbf": 200.0,
            "error_budget_remaining": 60.0,
            "mfa_coverage": 100.0,
            "secret_rotation_coverage": 100.0,
            "certificate_expiry_risk": 0.0,
            "iam_over_permissioning": 0.0,
            "monitoring_coverage": 98.0,
            "slo_compliance": 99.9,
            "policy_adherence": 98.0,
            "pipeline_drift_rate": 0.0,
            "resource_utilization": 80.0,
            "auto_scaling_effectiveness": 98.0
        }
        
        assessment = assess_maturity(kpi_values)
        
        assert assessment is not None
        assert assessment.global_level >= MaturityLevel.CUANTIFICADO
        assert assessment.global_score > 3.0
    
    def test_assess_maturity_empty_kpis(self):
        """Test evaluación con KPIs vacíos"""
        kpi_values = {}
        
        assessment = assess_maturity(kpi_values)
        
        assert assessment is not None
        assert assessment.global_level == MaturityLevel.CAOTICO
        assert assessment.global_score == 0.0


class TestKPIReporter:
    """Tests para el módulo de reportes"""
    
    @pytest.fixture
    def temp_dir(self):
        """Fixture para directorio temporal"""
        test_dir = Path(tempfile.mkdtemp())
        yield test_dir
        shutil.rmtree(test_dir)
    
    def test_export_json(self, temp_dir):
        """Test exportación a JSON"""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(temp_dir)
        
        test_data = {
            "metadata": {"generated_at": "2026-06-09T10:00:00Z"},
            "kpis": [
                {"id": "ec_001", "name": "Deployment Frequency", "value": 1.5}
            ]
        }
        
        filepath = reporter.export_json(test_data)
        
        assert filepath.exists()
        
        with open(filepath, 'r') as f:
            loaded_data = json.load(f)
        
        assert loaded_data["kpis"][0]["id"] == "ec_001"
    
    def test_export_csv(self, temp_dir):
        """Test exportación a CSV"""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(temp_dir)
        
        test_data = {
            "kpis": [
                {
                    "id": "ec_001",
                    "name": "Deployment Frequency",
                    "value": 1.5,
                    "unit": "deploys/día",
                    "benchmark_level": "elite"
                }
            ]
        }
        
        filepath = reporter.export_csv(test_data)
        
        assert filepath.exists()
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert "ec_001" in content
        assert "Deployment Frequency" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
