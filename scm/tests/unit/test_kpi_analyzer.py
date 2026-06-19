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
import csv
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


class TestBenchmarkConstants:
    """Tests para constantes en benchmarks.py"""
    
    @pytest.mark.unit
    def test_dora_benchmarks_has_deployment_frequency(self):
        """Test: DORA_BENCHMARKS contiene deployment_frequency."""
        from scm.kpi_analyzer.benchmarks import DORA_BENCHMARKS
        
        assert "deployment_frequency" in DORA_BENCHMARKS
        assert "elite" in DORA_BENCHMARKS["deployment_frequency"]
    
    @pytest.mark.unit
    def test_dora_benchmarks_has_change_failure_rate(self):
        """Test: DORA_BENCHMARKS contiene change_failure_rate."""
        from scm.kpi_analyzer.benchmarks import DORA_BENCHMARKS
        
        assert "change_failure_rate" in DORA_BENCHMARKS
        assert "high" in DORA_BENCHMARKS["change_failure_rate"]
    
    @pytest.mark.unit
    def test_dora_benchmarks_has_mttr(self):
        """Test: DORA_BENCHMARKS contiene mttr."""
        from scm.kpi_analyzer.benchmarks import DORA_BENCHMARKS
        
        assert "mttr" in DORA_BENCHMARKS
        assert "elite" in DORA_BENCHMARKS["mttr"]
    
    @pytest.mark.unit
    def test_benchmark_level_enum_values(self):
        """Test: BenchmarkLevel tiene valores válidos."""
        assert BenchmarkLevel.ELITE.value == "elite"
        assert BenchmarkLevel.HIGH.value == "high"
        assert BenchmarkLevel.MEDIUM.value == "medium"
        assert BenchmarkLevel.LOW.value == "low"


class TestBenchmarkHelperFunctions:
    """Tests para funciones helper de benchmarks"""
    
    def test_get_benchmark_color_elite(self):
        """Test color para nivel ELITE"""
        from scm.kpi_analyzer.benchmarks import get_benchmark_color
        assert get_benchmark_color(BenchmarkLevel.ELITE) == "#2ecc71"
    
    def test_get_benchmark_color_high(self):
        """Test color para nivel HIGH"""
        from scm.kpi_analyzer.benchmarks import get_benchmark_color
        assert get_benchmark_color(BenchmarkLevel.HIGH) == "#27ae60"
    
    def test_get_benchmark_color_medium(self):
        """Test color para nivel MEDIUM"""
        from scm.kpi_analyzer.benchmarks import get_benchmark_color
        assert get_benchmark_color(BenchmarkLevel.MEDIUM) == "#f39c12"
    
    def test_get_benchmark_color_low(self):
        """Test color para nivel LOW"""
        from scm.kpi_analyzer.benchmarks import get_benchmark_color
        assert get_benchmark_color(BenchmarkLevel.LOW) == "#e74c3c"
    
    def test_get_benchmark_emoji_elite(self):
        """Test emoji para nivel ELITE"""
        from scm.kpi_analyzer.benchmarks import get_benchmark_emoji
        assert get_benchmark_emoji(BenchmarkLevel.ELITE) == "💚"
    
    def test_get_benchmark_emoji_high(self):
        """Test emoji para nivel HIGH"""
        from scm.kpi_analyzer.benchmarks import get_benchmark_emoji
        assert get_benchmark_emoji(BenchmarkLevel.HIGH) == "🟢"
    
    def test_get_benchmark_emoji_medium(self):
        """Test emoji para nivel MEDIUM"""
        from scm.kpi_analyzer.benchmarks import get_benchmark_emoji
        assert get_benchmark_emoji(BenchmarkLevel.MEDIUM) == "🟡"
    
    def test_get_benchmark_emoji_low(self):
        """Test emoji para nivel LOW"""
        from scm.kpi_analyzer.benchmarks import get_benchmark_emoji
        assert get_benchmark_emoji(BenchmarkLevel.LOW) == "🔴"
    
    @pytest.mark.unit
    def test_get_benchmark_level_deployment_frequency_elite(self):
        """Test: get_benchmark_level para deployment_frequency ELITE."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_level
        
        result = get_benchmark_level("ec_001", 1.5)
        assert result == BenchmarkLevel.ELITE
    
    @pytest.mark.unit
    def test_get_benchmark_level_deployment_frequency_high(self):
        """Test: get_benchmark_level para deployment_frequency HIGH."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_level
        
        result = get_benchmark_level("ec_001", 0.2)
        assert result == BenchmarkLevel.HIGH
    
    @pytest.mark.unit
    def test_get_benchmark_level_deployment_frequency_medium(self):
        """Test: get_benchmark_level para deployment_frequency MEDIUM."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_level
        
        result = get_benchmark_level("ec_001", 0.05)
        assert result == BenchmarkLevel.MEDIUM
    
    @pytest.mark.unit
    def test_get_benchmark_level_deployment_frequency_low(self):
        """Test: get_benchmark_level para deployment_frequency LOW."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_level
        
        result = get_benchmark_level("ec_001", 0.001)
        assert result == BenchmarkLevel.LOW
    
    @pytest.mark.unit
    def test_get_benchmark_level_mttr_elite(self):
        """Test: get_benchmark_level para MTTR ELITE."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_level
        
        # MTTR: lower is better, elite <= 60 minutes
        result = get_benchmark_level("conf_001", 30.0)
        assert result == BenchmarkLevel.ELITE
    
    @pytest.mark.unit
    def test_get_benchmark_level_mttr_high(self):
        """Test: get_benchmark_level para MTTR HIGH."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_level
        
        # MTTR: lower is better, high <= 240 minutes
        result = get_benchmark_level("conf_001", 120.0)
        assert result == BenchmarkLevel.HIGH
    
    @pytest.mark.unit
    def test_get_benchmark_level_mttr_medium(self):
        """Test: get_benchmark_level para MTTR MEDIUM."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_level
        
        # MTTR: lower is better, medium <= 1440 minutes
        result = get_benchmark_level("conf_001", 600.0)
        assert result == BenchmarkLevel.MEDIUM
    
    @pytest.mark.unit
    def test_get_benchmark_color_high(self):
        """Test: get_benchmark_color para HIGH."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_color
        assert get_benchmark_color(BenchmarkLevel.HIGH) == "#27ae60"
    
    @pytest.mark.unit
    def test_get_benchmark_color_medium(self):
        """Test: get_benchmark_color para MEDIUM."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_color
        assert get_benchmark_color(BenchmarkLevel.MEDIUM) == "#f39c12"
    
    @pytest.mark.unit
    def test_get_benchmark_color_low(self):
        """Test: get_benchmark_color para LOW."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_color
        assert get_benchmark_color(BenchmarkLevel.LOW) == "#e74c3c"
    
    @pytest.mark.unit
    def test_get_benchmark_emoji_returns_string(self):
        """Test: get_benchmark_emoji retorna string."""
        from scm.kpi_analyzer.benchmarks import get_benchmark_emoji
        result = get_benchmark_emoji(BenchmarkLevel.ELITE)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_get_benchmark_level_unknown_kpi(self):
        """Test benchmark level para KPI desconocido"""
        assert get_benchmark_level("unknown_kpi", 50.0) == BenchmarkLevel.MEDIUM
    
    def test_get_benchmark_level_ec_002_elite(self):
        """Test change_failure_rate elite level"""
        assert get_benchmark_level("ec_002", 3.0) == BenchmarkLevel.ELITE
    
    def test_get_benchmark_level_ec_002_high(self):
        """Test change_failure_rate high level"""
        assert get_benchmark_level("ec_002", 10.0) == BenchmarkLevel.HIGH
    
    def test_get_benchmark_level_ec_002_medium(self):
        """Test change_failure_rate medium level"""
        assert get_benchmark_level("ec_002", 20.0) == BenchmarkLevel.MEDIUM
    
    def test_get_benchmark_level_ec_002_low(self):
        """Test change_failure_rate low level"""
        assert get_benchmark_level("ec_002", 40.0) == BenchmarkLevel.LOW
    
    def test_get_benchmark_level_conf_002_elite(self):
        """Test availability elite level"""
        assert get_benchmark_level("conf_002", 99.95) == BenchmarkLevel.ELITE
    
    def test_get_benchmark_level_conf_002_high(self):
        """Test availability high level"""
        assert get_benchmark_level("conf_002", 99.7) == BenchmarkLevel.HIGH
    
    def test_get_benchmark_level_seg_001_elite(self):
        """Test mfa_coverage elite level"""
        assert get_benchmark_level("seg_001", 100.0) == BenchmarkLevel.ELITE
    
    def test_get_benchmark_level_seg_002_elite(self):
        """Test certificate_expiry_risk elite level"""
        assert get_benchmark_level("seg_002", 0.0) == BenchmarkLevel.ELITE


class TestKPIReporter:
    """Tests para la clase KPIReporter."""
    
    @pytest.mark.unit
    def test_reporter_init(self, tmp_path):
        """Test: Inicializar KPIReporter."""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(output_dir=tmp_path)
        assert reporter.output_dir == tmp_path
        assert tmp_path.exists()
    
    @pytest.mark.unit
    def test_export_json_with_custom_filename(self, tmp_path):
        """Test: Exportar JSON con nombre personalizado."""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(output_dir=tmp_path)
        data = {
            "kpis": [
                {"id": "ec_001", "name": "Deployment Frequency", "value": 5.0}
            ]
        }
        
        filepath = reporter.export_json(data, filename="test_report.json")
        
        assert filepath.exists()
        assert filepath.name == "test_report.json"
        
        with open(filepath, 'r') as f:
            loaded = json.load(f)
        assert loaded["kpis"][0]["id"] == "ec_001"
    
    @pytest.mark.unit
    def test_export_json_auto_filename(self, tmp_path):
        """Test: Exportar JSON con nombre automático."""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(output_dir=tmp_path)
        data = {"kpis": []}
        
        filepath = reporter.export_json(data)
        
        assert filepath.exists()
        assert "kpi_report_" in filepath.name
        assert filepath.name.endswith(".json")
    
    @pytest.mark.unit
    def test_export_csv_with_kpis(self, tmp_path):
        """Test: Exportar CSV con KPIs."""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(output_dir=tmp_path)
        data = {
            "kpis": [
                {
                    "id": "ec_001",
                    "name": "Deployment Frequency",
                    "value": 5.0,
                    "unit": "deployments/day",
                    "benchmarks": {"elite": 10, "high": 5, "medium": 2, "low": 1},
                    "frameworks": ["DORA"],
                    "maturity_level_required": "CUANTIFICADO"
                }
            ]
        }
        
        filepath = reporter.export_csv(data, filename="test_report.csv")
        
        assert filepath.exists()
        assert filepath.name == "test_report.csv"
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 1
        assert rows[0]["ID"] == "ec_001"
        assert rows[0]["Name"] == "Deployment Frequency"
    
    @pytest.mark.unit
    def test_export_csv_empty_kpis(self, tmp_path):
        """Test: Exportar CSV sin KPIs."""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(output_dir=tmp_path)
        data = {"kpis": []}
        
        filepath = reporter.export_csv(data, filename="empty.csv")
        
        # Cuando no hay KPIs, retorna la ruta pero no crea el archivo
        assert filepath.name == "empty.csv"
        assert not filepath.exists()
    
    @pytest.mark.unit
    def test_export_html_simple(self, tmp_path):
        """Test: Exportar HTML simple."""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(output_dir=tmp_path)
        data = {
            "metadata": {
                "generated_at": "2024-01-01T00:00:00",
                "platform": "all",
                "analyzer_version": "1.0.0"
            },
            "dimensions": {
                "deployment": {
                    "kpis": [
                        {
                            "name": "Deployment Frequency",
                            "value": 5.0,
                            "unit": "deployments/day",
                            "benchmarks": {"elite": 10, "high": 5, "medium": 2, "low": 1}
                        }
                    ]
                }
            }
        }
        
        filepath = reporter.export_html_simple(data, filename="test_report.html")
        
        assert filepath.exists()
        assert filepath.name == "test_report.html"
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        assert "KPI Report" in content
        assert "Deployment Frequency" in content
        assert "5.00" in content
    
    @pytest.mark.unit
    def test_generate_simple_html_with_dimensions(self, tmp_path):
        """Test: Generar HTML con múltiples dimensiones."""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(output_dir=tmp_path)
        data = {
            "metadata": {
                "generated_at": "2024-01-01",
                "platform": "azdo",
                "analyzer_version": "1.0.0"
            },
            "dimensions": {
                "deployment": {
                    "kpis": [
                        {
                            "name": "Deployment Frequency",
                            "value": 5.0,
                            "unit": "deployments/day",
                            "benchmarks": {"elite": 10, "high": 5, "medium": 2, "low": 1}
                        }
                    ]
                },
                "reliability": {
                    "kpis": [
                        {
                            "name": "Change Failure Rate",
                            "value": 10.0,
                            "unit": "%",
                            "benchmarks": {"elite": 5, "high": 10, "medium": 20, "low": 30}
                        }
                    ]
                }
            }
        }
        
        html = reporter._generate_simple_html(data)
        
        assert "KPI Report" in html
        assert "Deployment" in html
        assert "Reliability" in html
        assert "Deployment Frequency" in html
        assert "Change Failure Rate" in html
    
    @pytest.mark.unit
    def test_save_to_cache(self, tmp_path):
        """Test: Guardar reporte en caché."""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(output_dir=tmp_path)
        data = {
            "kpis": [
                {"id": "ec_001", "name": "Deployment Frequency", "value": 5.0}
            ]
        }
        
        filepath = reporter.save_to_cache(data)
        
        assert filepath.exists()
        assert ".cache" in str(filepath)
        assert "kpi_history_" in filepath.name
        
        with open(filepath, 'r') as f:
            loaded = json.load(f)
        assert loaded["kpis"][0]["id"] == "ec_001"
    
    @pytest.mark.unit
    def test_export_json_with_special_characters(self, tmp_path):
        """Test: Exportar JSON con caracteres especiales."""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(output_dir=tmp_path)
        data = {
            "kpis": [
                {"id": "ec_001", "name": "Frecuencia de Despliegue Ñ", "value": 5.0}
            ]
        }
        
        filepath = reporter.export_json(data, filename="unicode_test.json")
        
        assert filepath.exists()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Ñ" in content
    
    @pytest.mark.unit
    def test_export_csv_with_missing_fields(self, tmp_path):
        """Test: Exportar CSV con campos faltantes."""
        from scm.kpi_analyzer.reporter import KPIReporter
        
        reporter = KPIReporter(output_dir=tmp_path)
        data = {
            "kpis": [
                {
                    "id": "ec_001",
                    "name": "Deployment Frequency",
                }
            ]
        }
        
        filepath = reporter.export_csv(data, filename="incomplete.csv")
        
        assert filepath.exists()
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) == 1
        assert rows[0]["ID"] == "ec_001"


class TestKPIAnalyzer:
    """Tests para la clase KPIAnalyzer."""
    
    @pytest.mark.unit
    def test_analyzer_init(self, tmp_path):
        """Test: Inicializar KPIAnalyzer."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        assert analyzer.schema is not None
        assert analyzer.output_dir is not None
        assert isinstance(analyzer.json_cache, dict)
    
    @pytest.mark.unit
    def test_discover_json_files_empty(self, tmp_path):
        """Test: Descubrir archivos JSON en directorio vacío."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        from unittest.mock import patch
        
        analyzer = KPIAnalyzer()
        
        with patch.object(analyzer, 'output_dir', tmp_path):
            files = analyzer.discover_json_files()
            assert isinstance(files, list)
            assert len(files) == 0
    
    @pytest.mark.unit
    def test_discover_json_files_with_platform_filter(self, tmp_path):
        """Test: Descubrir archivos JSON con filtro de plataforma."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        from unittest.mock import patch
        
        # Crear archivos de prueba
        (tmp_path / "gcp_scan_results.json").write_text("{}")
        (tmp_path / "azdo_scan_results.json").write_text("{}")
        
        analyzer = KPIAnalyzer()
        
        with patch.object(analyzer, 'output_dir', tmp_path):
            files = analyzer.discover_json_files(platform="gcp")
            assert len(files) > 0
            assert any("gcp" in f.name for f in files)
    
    @pytest.mark.unit
    def test_load_json_success(self, tmp_path):
        """Test: Cargar archivo JSON exitosamente."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        # Crear archivo JSON de prueba
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "number": 42}
        test_file.write_text(json.dumps(test_data))
        
        analyzer = KPIAnalyzer()
        result = analyzer.load_json(test_file)
        
        assert result == test_data
        assert str(test_file) in analyzer.json_cache
    
    @pytest.mark.unit
    def test_load_json_cache(self, tmp_path):
        """Test: Caché de archivos JSON."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        test_file = tmp_path / "test.json"
        test_data = {"key": "value"}
        test_file.write_text(json.dumps(test_data))
        
        analyzer = KPIAnalyzer()
        
        # Primera carga
        result1 = analyzer.load_json(test_file)
        
        # Modificar archivo
        test_file.write_text(json.dumps({"key": "modified"}))
        
        # Segunda carga debe venir del caché
        result2 = analyzer.load_json(test_file)
        
        assert result1 == result2
        assert result1["key"] == "value"
    
    @pytest.mark.unit
    def test_load_json_invalid_file(self, tmp_path):
        """Test: Cargar archivo JSON inválido."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json }")
        
        analyzer = KPIAnalyzer()
        result = analyzer.load_json(test_file)
        
        assert result is None
    
    @pytest.mark.unit
    def test_extract_field_simple(self):
        """Test: Extraer campo simple."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        data = {"name": "test", "value": 42}
        
        result = analyzer.extract_field(data, "name")
        assert result == "test"
    
    @pytest.mark.unit
    def test_extract_field_nested(self):
        """Test: Extraer campo anidado."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        data = {"user": {"name": "John", "age": 30}}
        
        result = analyzer.extract_field(data, "user.name")
        assert result == "John"
    
    @pytest.mark.unit
    def test_extract_field_array(self):
        """Test: Extraer campo de array."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        data = {
            "deployments": [
                {"id": 1, "status": "success"},
                {"id": 2, "status": "failed"}
            ]
        }
        
        result = analyzer.extract_field(data, "deployments[]")
        assert isinstance(result, list)
        assert len(result) == 2
    
    @pytest.mark.unit
    def test_extract_field_array_nested(self):
        """Test: Extraer campo anidado de array."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        data = {
            "deployments": [
                {"id": 1, "status": "success"},
                {"id": 2, "status": "failed"}
            ]
        }
        
        result = analyzer.extract_field(data, "deployments[].status")
        assert isinstance(result, list)
        assert "success" in result
        assert "failed" in result
    
    @pytest.mark.unit
    def test_extract_field_nonexistent(self):
        """Test: Extraer campo que no existe."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        data = {"name": "test"}
        
        result = analyzer.extract_field(data, "nonexistent")
        assert result is None
    
    @pytest.mark.unit
    def test_extract_field_deep_nested(self):
        """Test: Extraer campo profundamente anidado."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep"
                    }
                }
            }
        }
        
        result = analyzer.extract_field(data, "level1.level2.level3.value")
        assert result == "deep"
    
    @pytest.mark.unit
    def test_calculate_kpi_no_sources(self):
        """Test: Calcular KPI sin fuentes."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        from unittest.mock import patch
        
        analyzer = KPIAnalyzer()
        kpi_def = {
            "id": "ec_001",
            "sources": [],
            "formula": "count"
        }
        
        with patch.object(analyzer, 'discover_json_files', return_value=[]):
            result = analyzer.calculate_kpi(kpi_def)
            assert result is None
    
    @pytest.mark.unit
    def test_apply_formula_ec_001_no_deployments(self):
        """Test: Aplicar fórmula ec_001 sin deployments."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        source_data = []
        
        result = analyzer._apply_formula("count", source_data, "ec_001")
        assert result == 0.0
    
    @pytest.mark.unit
    def test_apply_formula_ec_002_no_deployments(self):
        """Test: Aplicar fórmula ec_002 sin deployments."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        source_data = []
        
        result = analyzer._apply_formula("failure_rate", source_data, "ec_002")
        assert result == 0.0
    
    @pytest.mark.unit
    def test_json_cache_multiple_files(self, tmp_path):
        """Test: Caché con múltiples archivos."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        file1 = tmp_path / "file1.json"
        file2 = tmp_path / "file2.json"
        
        file1.write_text(json.dumps({"id": 1}))
        file2.write_text(json.dumps({"id": 2}))
        
        analyzer = KPIAnalyzer()
        
        result1 = analyzer.load_json(file1)
        result2 = analyzer.load_json(file2)
        
        assert len(analyzer.json_cache) == 2
        assert result1["id"] == 1
        assert result2["id"] == 2
    
    @pytest.mark.unit
    def test_apply_formula_ec_001_with_deployments(self):
        """Test: Aplicar fórmula ec_001 con deployments."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        from datetime import datetime, timezone, timedelta
        
        analyzer = KPIAnalyzer()
        now = datetime.now(timezone.utc)
        recent_date = (now - timedelta(days=3)).isoformat()
        
        source_data = [
            {
                "field": "deployments",
                "value": [
                    {
                        "status": "success",
                        "environment": "prod",
                        "timestamp": recent_date
                    }
                ],
                "source": "test.json"
            }
        ]
        
        result = analyzer._apply_formula("count", source_data, "ec_001")
        assert result is not None
        assert isinstance(result, float)
    
    @pytest.mark.unit
    def test_apply_formula_ec_002_with_failures(self):
        """Test: Aplicar fórmula ec_002 con fallos."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        source_data = [
            {
                "field": "deployments",
                "value": [
                    {"status": "success"},
                    {"status": "failed"},
                    {"status": "success"}
                ],
                "source": "test.json"
            }
        ]
        
        result = analyzer._apply_formula("failure_rate", source_data, "ec_002")
        assert result is not None
        assert 0 <= result <= 100
    
    @pytest.mark.unit
    def test_apply_formula_unknown_kpi(self):
        """Test: Aplicar fórmula con KPI desconocido."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        source_data = [{"field": "test", "value": 42}]
        
        result = analyzer._apply_formula("unknown", source_data, "unknown_kpi")
        # Para KPIs desconocidos, retorna el promedio de valores
        assert result is not None
        assert isinstance(result, float)
    
    @pytest.mark.unit
    def test_extract_field_with_list_items(self):
        """Test: Extraer campo de items en lista."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        data = {
            "items": [
                {"status": "success", "id": 1},
                {"status": "failed", "id": 2},
                {"status": "success", "id": 3}
            ]
        }
        
        result = analyzer.extract_field(data, "items[].status")
        assert isinstance(result, list)
        assert len(result) == 3
        assert "success" in result
        assert "failed" in result
    
    @pytest.mark.unit
    def test_load_json_with_cache_key(self, tmp_path):
        """Test: load_json usa cache_key correctamente."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        test_file = tmp_path / "test.json"
        test_data = {"key": "value"}
        test_file.write_text(json.dumps(test_data))
        
        analyzer = KPIAnalyzer()
        
        # Primera carga
        result1 = analyzer.load_json(test_file)
        cache_key = str(test_file)
        
        # Verificar que está en caché
        assert cache_key in analyzer.json_cache
        assert analyzer.json_cache[cache_key] == test_data
    
    @pytest.mark.unit
    def test_discover_json_files_excludes_config(self, tmp_path):
        """Test: discover_json_files excluye archivos config."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        from unittest.mock import patch
        
        # Crear archivos de prueba
        (tmp_path / "gcp_scan.json").write_text("{}")
        (tmp_path / "config.json").write_text("{}")
        (tmp_path / "package.json").write_text("{}")
        
        analyzer = KPIAnalyzer()
        
        with patch.object(analyzer, 'output_dir', tmp_path):
            files = analyzer.discover_json_files()
            
            # No debe incluir config.json o package.json
            file_names = [f.name for f in files]
            assert "config.json" not in file_names
            assert "package.json" not in file_names
    
    @pytest.mark.unit
    def test_extract_field_returns_none_for_invalid_path(self):
        """Test: extract_field retorna None para path inválido."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        data = {"a": {"b": {"c": 1}}}
        
        result = analyzer.extract_field(data, "a.b.d.e.f")
        assert result is None
    
    @pytest.mark.unit
    def test_apply_formula_conf_001_mttr(self):
        """Test: Aplicar fórmula conf_001 (MTTR)."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        source_data = [
            {"field": "mttr", "value": 120},
            {"field": "mttr", "value": 180},
            {"field": "mttr", "value": 150}
        ]
        
        result = analyzer._apply_formula("avg", source_data, "conf_001")
        assert result is not None
        assert isinstance(result, float)
        assert result > 0
    
    @pytest.mark.unit
    def test_apply_formula_conf_002_availability(self):
        """Test: Aplicar fórmula conf_002 (Availability)."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        source_data = [
            {
                "field": "uptime",
                "value": [100, 99, 98, 100, 99]
            }
        ]
        
        result = analyzer._apply_formula("availability", source_data, "conf_002")
        assert result is not None
        assert isinstance(result, float)
    
    @pytest.mark.unit
    def test_apply_formula_seg_001_mfa(self):
        """Test: Aplicar fórmula seg_001 (MFA Coverage)."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        source_data = [
            {
                "field": "users",
                "value": [
                    {"mfa_enabled": True},
                    {"mfa_enabled": False},
                    {"mfa_enabled": True}
                ]
            }
        ]
        
        result = analyzer._apply_formula("mfa", source_data, "seg_001")
        assert result is not None
        assert isinstance(result, float)
    
    @pytest.mark.unit
    def test_apply_formula_obs_001_monitoring(self):
        """Test: Aplicar fórmula obs_001 (Monitoring Coverage)."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        source_data = [
            {
                "field": "services",
                "value": [
                    {"status": "healthy"},
                    {"status": "unhealthy"},
                    {"status": "running"}
                ]
            }
        ]
        
        result = analyzer._apply_formula("monitoring", source_data, "obs_001")
        assert result is not None
        assert isinstance(result, float)
    
    @pytest.mark.unit
    def test_apply_formula_cump_001_compliance(self):
        """Test: Aplicar fórmula cump_001 (Policy Adherence)."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        source_data = [
            {
                "field": "resources",
                "value": [
                    {"compliant": True},
                    {"compliant": False},
                    {"compliant": True}
                ]
            }
        ]
        
        result = analyzer._apply_formula("compliance", source_data, "cump_001")
        assert result is not None
        assert isinstance(result, float)
    
    @pytest.mark.unit
    def test_apply_formula_efic_001_utilization(self):
        """Test: Aplicar fórmula efic_001 (Resource Utilization)."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        source_data = [
            {
                "field": "resources",
                "value": [
                    {"used": 50, "allocated": 100},
                    {"used": 75, "allocated": 100}
                ]
            }
        ]
        
        result = analyzer._apply_formula("utilization", source_data, "efic_001")
        assert result is not None
        assert isinstance(result, float)
    
    @pytest.mark.unit
    def test_calculate_kpi_with_valid_definition(self, tmp_path):
        """Test: calculate_kpi con definición válida."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        
        analyzer = KPIAnalyzer()
        
        kpi_def = {
            "id": "ec_001",
            "name": "Deployment Frequency",
            "sources": [],
            "formula": "count"
        }
        
        result = analyzer.calculate_kpi(kpi_def)
        # Sin fuentes, debería retornar None
        assert result is None
    
    @pytest.mark.unit
    def test_discover_json_files_returns_list(self, tmp_path):
        """Test: discover_json_files retorna lista."""
        from scm.kpi_analyzer.analyzer import KPIAnalyzer
        from unittest.mock import patch
        
        # Crear archivos de prueba
        (tmp_path / "gcp_scan.json").write_text("{}")
        (tmp_path / "azdo_scan.json").write_text("{}")
        
        analyzer = KPIAnalyzer()
        
        with patch.object(analyzer, 'output_dir', tmp_path):
            files = analyzer.discover_json_files()
            
            assert isinstance(files, list)
            assert len(files) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
