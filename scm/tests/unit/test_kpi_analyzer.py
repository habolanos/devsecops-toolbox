#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — KPI Analyzer Module
Tests para validar funcionalidad del analizador de KPIs

Version: 1.0.0
Author: Harold Adrian
"""

import unittest
import json
from pathlib import Path
import tempfile
import shutil

from kpi_analyzer.benchmarks import (
    BenchmarkLevel,
    MaturityLevel,
    get_benchmark_level,
    get_benchmark_color,
    get_benchmark_emoji,
    calculate_maturity_level
)
from kpi_analyzer.maturity_model import (
    evaluate_dimension,
    assess_maturity,
    get_level_name,
    get_level_color
)


class TestBenchmarks(unittest.TestCase):
    """Tests para el módulo de benchmarks"""
    
    def test_benchmark_level_deployment_frequency(self):
        """Test benchmark level para deployment frequency"""
        # Elite: >= 1
        self.assertEqual(get_benchmark_level("ec_001", 1.5), BenchmarkLevel.ELITE)
        self.assertEqual(get_benchmark_level("ec_001", 1.0), BenchmarkLevel.ELITE)
        
        # High: 0.14-1
        self.assertEqual(get_benchmark_level("ec_001", 0.5), BenchmarkLevel.HIGH)
        
        # Medium: 0.03-0.14
        self.assertEqual(get_benchmark_level("ec_001", 0.1), BenchmarkLevel.MEDIUM)
        
        # Low: < 0.03
        self.assertEqual(get_benchmark_level("ec_001", 0.01), BenchmarkLevel.LOW)
    
    def test_benchmark_level_change_failure_rate(self):
        """Test benchmark level para change failure rate"""
        # Elite: < 5%
        self.assertEqual(get_benchmark_level("ec_002", 3.0), BenchmarkLevel.ELITE)
        
        # High: 5-15%
        self.assertEqual(get_benchmark_level("ec_002", 10.0), BenchmarkLevel.HIGH)
        
        # Medium: 15-30%
        self.assertEqual(get_benchmark_level("ec_002", 20.0), BenchmarkLevel.MEDIUM)
        
        # Low: > 30%
        self.assertEqual(get_benchmark_level("ec_002", 40.0), BenchmarkLevel.LOW)
    
    def test_benchmark_colors(self):
        """Test benchmark colors"""
        self.assertEqual(get_benchmark_color(BenchmarkLevel.ELITE), "#2ecc71")
        self.assertEqual(get_benchmark_color(BenchmarkLevel.HIGH), "#27ae60")
        self.assertEqual(get_benchmark_color(BenchmarkLevel.MEDIUM), "#f39c12")
        self.assertEqual(get_benchmark_color(BenchmarkLevel.LOW), "#e74c3c")
    
    def test_benchmark_emojis(self):
        """Test benchmark emojis"""
        self.assertEqual(get_benchmark_emoji(BenchmarkLevel.ELITE), "💚")
        self.assertEqual(get_benchmark_emoji(BenchmarkLevel.HIGH), "🟢")
        self.assertEqual(get_benchmark_emoji(BenchmarkLevel.MEDIUM), "🟡")
        self.assertEqual(get_benchmark_emoji(BenchmarkLevel.LOW), "🔴")


class TestMaturityModel(unittest.TestCase):
    """Tests para el modelo de madurez"""
    
    def test_get_level_name(self):
        """Test nombres de niveles de madurez"""
        self.assertEqual(get_level_name(MaturityLevel.CAOTICO), "Caótico")
        self.assertEqual(get_level_name(MaturityLevel.INICIAL), "Inicial")
        self.assertEqual(get_level_name(MaturityLevel.GESTIONADO), "Gestionado")
        self.assertEqual(get_level_name(MaturityLevel.DEFINIDO), "Definido")
        self.assertEqual(get_level_name(MaturityLevel.CUANTIFICADO), "Cuantificado")
        self.assertEqual(get_level_name(MaturityLevel.OPTIMIZADO), "Optimizado")
    
    def test_get_level_color(self):
        """Test colores de niveles de madurez"""
        self.assertEqual(get_level_color(MaturityLevel.CAOTICO), "#e74c3c")
        self.assertEqual(get_level_color(MaturityLevel.OPTIMIZADO), "#2ecc71")
    
    def test_evaluate_dimension_caotico(self):
        """Test evaluación de dimensión en nivel caótico"""
        kpi_values = {
            "deployment_frequency": 0.01,
            "change_failure_rate": 60.0,
            "mttr": 20000.0
        }
        
        score = evaluate_dimension("entrega_continua", kpi_values, MaturityLevel.INICIAL)
        
        self.assertEqual(score.name, "entrega_continua")
        self.assertGreater(score.kpis_total, 0)
        self.assertLessEqual(score.kpis_met, score.kpis_total)
    
    def test_evaluate_dimension_elite(self):
        """Test evaluación de dimensión en nivel elite"""
        kpi_values = {
            "deployment_frequency": 5.0,
            "change_failure_rate": 1.0,
            "lead_time_for_changes": 0.5,
            "deployment_success_rate": 99.0
        }
        
        score = evaluate_dimension("entrega_continua", kpi_values, MaturityLevel.OPTIMIZADO)
        
        self.assertEqual(score.name, "entrega_continua")
        self.assertGreater(score.score_percentage, 50.0)
    
    def test_assess_maturity_low(self):
        """Test evaluación de madurez baja"""
        kpi_values = {
            "deployment_frequency": 0.01,
            "change_failure_rate": 50.0,
            "mttr": 15000.0,
            "availability": 90.0
        }
        
        assessment = assess_maturity(kpi_values)
        
        self.assertIsNotNone(assessment)
        self.assertIn(assessment.global_level, [MaturityLevel.CAOTICO, MaturityLevel.INICIAL])
        self.assertGreater(len(assessment.dimension_scores), 0)
        self.assertGreater(len(assessment.recommended_actions), 0)
    
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
        
        self.assertIsNotNone(assessment)
        self.assertGreaterEqual(assessment.global_level, MaturityLevel.CUANTIFICADO)
        self.assertGreater(assessment.global_score, 3.0)


class TestKPIAnalyzer(unittest.TestCase):
    """Tests para el analizador de KPIs"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.outcome_dir = self.test_dir / "outcome"
        self.outcome_dir.mkdir(parents=True, exist_ok=True)
        
        # Create sample JSON files
        self.create_sample_json_files()
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir)
    
    def create_sample_json_files(self):
        """Create sample JSON files for testing"""
        # Sample deployment data
        deployment_data = {
            "metadata": {
                "script": "cicd_inventory_prod_deploy",
                "generated_at": "2026-06-09T10:00:00Z"
            },
            "deployments": [
                {"status": "success", "environment": "prod", "timestamp": "2026-06-08T10:00:00Z"},
                {"status": "success", "environment": "prod", "timestamp": "2026-06-07T10:00:00Z"},
                {"status": "failed", "environment": "prod", "timestamp": "2026-06-06T10:00:00Z", "rollback": True}
            ]
        }
        
        with open(self.outcome_dir / "azdo_deployments_20260609_100000.json", 'w') as f:
            json.dump(deployment_data, f)
        
        # Sample certificate data
        cert_data = {
            "metadata": {
                "script": "gcp_certificate_checker",
                "generated_at": "2026-06-09T10:00:00Z"
            },
            "certificates": [
                {"days_to_expiry": 90, "status": "valid"},
                {"days_to_expiry": 180, "status": "valid"},
                {"days_to_expiry": 20, "status": "expiring_soon"}
            ]
        }
        
        with open(self.outcome_dir / "gcp_certificates_20260609_100000.json", 'w') as f:
            json.dump(cert_data, f)


class TestReporter(unittest.TestCase):
    """Tests para el módulo de reportes"""
    
    def setUp(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir)
    
    def test_export_json(self):
        """Test exportación a JSON"""
        from kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(self.test_dir)
        
        test_data = {
            "metadata": {"generated_at": "2026-06-09T10:00:00Z"},
            "kpis": [
                {"id": "ec_001", "name": "Deployment Frequency", "value": 1.5}
            ]
        }
        
        filepath = reporter.export_json(test_data, "test_report.json")
        
        self.assertTrue(filepath.exists())
        
        with open(filepath, 'r') as f:
            loaded_data = json.load(f)
        
        self.assertEqual(loaded_data["kpis"][0]["id"], "ec_001")
    
    def test_export_csv(self):
        """Test exportación a CSV"""
        from kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(self.test_dir)
        
        test_data = {
            "metadata": {"generated_at": "2026-06-09T10:00:00Z"},
            "kpis": [
                {
                    "id": "ec_001",
                    "name": "Deployment Frequency",
                    "value": 1.5,
                    "unit": "deploys/día",
                    "benchmarks": {"elite": ">= 1"},
                    "frameworks": ["DORA"],
                    "maturity_level_required": 3
                }
            ]
        }
        
        filepath = reporter.export_csv(test_data, "test_report.csv")
        
        self.assertTrue(filepath.exists())
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        self.assertIn("ec_001", content)
        self.assertIn("Deployment Frequency", content)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
