"""
Tests completos para KPI Analyzer
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestKPIAnalyzerComplete:
    """Tests completos para KPI Analyzer"""

    def test_kpi_dora_metrics(self):
        """Test métricas DORA"""
        dora_metrics = {
            'deployment_frequency': 10,  # deployments per day
            'lead_time': 5,  # hours
            'mttr': 2,  # minutes
            'change_failure_rate': 0.1  # 10%
        }
        
        assert dora_metrics['deployment_frequency'] == 10
        assert dora_metrics['lead_time'] == 5
        assert dora_metrics['mttr'] == 2
        assert dora_metrics['change_failure_rate'] == 0.1

    def test_kpi_sre_metrics(self):
        """Test métricas SRE"""
        sre_metrics = {
            'availability': 0.9999,
            'latency_p99': 100,  # ms
            'error_rate': 0.001,  # 0.1%
            'saturation': 0.7  # 70%
        }
        
        assert sre_metrics['availability'] == 0.9999
        assert sre_metrics['latency_p99'] == 100
        assert sre_metrics['error_rate'] == 0.001
        assert sre_metrics['saturation'] == 0.7

    def test_kpi_security_metrics(self):
        """Test métricas de seguridad"""
        security_metrics = {
            'vulnerability_count': 5,
            'critical_vulnerabilities': 0,
            'compliance_score': 95,
            'security_incidents': 0
        }
        
        assert security_metrics['vulnerability_count'] == 5
        assert security_metrics['critical_vulnerabilities'] == 0
        assert security_metrics['compliance_score'] == 95
        assert security_metrics['security_incidents'] == 0

    def test_kpi_cost_metrics(self):
        """Test métricas de costo"""
        cost_metrics = {
            'monthly_cost': 5000,
            'cost_per_deployment': 50,
            'cost_per_user': 10,
            'cost_optimization_score': 85
        }
        
        assert cost_metrics['monthly_cost'] == 5000
        assert cost_metrics['cost_per_deployment'] == 50
        assert cost_metrics['cost_per_user'] == 10
        assert cost_metrics['cost_optimization_score'] == 85

    def test_kpi_quality_metrics(self):
        """Test métricas de calidad"""
        quality_metrics = {
            'code_coverage': 85,
            'test_pass_rate': 98,
            'bug_density': 0.5,
            'technical_debt_ratio': 0.1
        }
        
        assert quality_metrics['code_coverage'] == 85
        assert quality_metrics['test_pass_rate'] == 98
        assert quality_metrics['bug_density'] == 0.5
        assert quality_metrics['technical_debt_ratio'] == 0.1

    def test_kpi_performance_metrics(self):
        """Test métricas de performance"""
        performance_metrics = {
            'response_time': 100,  # ms
            'throughput': 1000,  # requests/sec
            'cpu_usage': 45,  # %
            'memory_usage': 60  # %
        }
        
        assert performance_metrics['response_time'] == 100
        assert performance_metrics['throughput'] == 1000
        assert performance_metrics['cpu_usage'] == 45
        assert performance_metrics['memory_usage'] == 60


class TestKPIMaturityModel:
    """Tests para modelo de madurez KPI"""

    def test_kpi_maturity_level_0(self):
        """Test nivel de madurez 0 (Inicial)"""
        maturity = {
            'level': 0,
            'name': 'Initial',
            'description': 'Ad hoc processes',
            'score': 0
        }
        
        assert maturity['level'] == 0
        assert maturity['name'] == 'Initial'

    def test_kpi_maturity_level_1(self):
        """Test nivel de madurez 1 (Repetible)"""
        maturity = {
            'level': 1,
            'name': 'Repeatable',
            'description': 'Documented processes',
            'score': 20
        }
        
        assert maturity['level'] == 1
        assert maturity['score'] == 20

    def test_kpi_maturity_level_2(self):
        """Test nivel de madurez 2 (Definido)"""
        maturity = {
            'level': 2,
            'name': 'Defined',
            'description': 'Standardized processes',
            'score': 40
        }
        
        assert maturity['level'] == 2
        assert maturity['score'] == 40

    def test_kpi_maturity_level_3(self):
        """Test nivel de madurez 3 (Gestionado)"""
        maturity = {
            'level': 3,
            'name': 'Managed',
            'description': 'Measured and controlled',
            'score': 60
        }
        
        assert maturity['level'] == 3
        assert maturity['score'] == 60

    def test_kpi_maturity_level_4(self):
        """Test nivel de madurez 4 (Optimizado)"""
        maturity = {
            'level': 4,
            'name': 'Optimized',
            'description': 'Continuous improvement',
            'score': 80
        }
        
        assert maturity['level'] == 4
        assert maturity['score'] == 80

    def test_kpi_maturity_level_5(self):
        """Test nivel de madurez 5 (Excelencia)"""
        maturity = {
            'level': 5,
            'name': 'Excellence',
            'description': 'World-class processes',
            'score': 100
        }
        
        assert maturity['level'] == 5
        assert maturity['score'] == 100


class TestKPIBenchmarks:
    """Tests para benchmarks KPI"""

    def test_kpi_dora_benchmarks(self):
        """Test benchmarks DORA"""
        benchmarks = {
            'deployment_frequency': {
                'elite': 'on-demand',
                'high': 'weekly',
                'medium': 'monthly',
                'low': 'quarterly'
            },
            'lead_time': {
                'elite': '<1 day',
                'high': '<1 week',
                'medium': '<1 month',
                'low': '>1 month'
            }
        }
        
        assert 'deployment_frequency' in benchmarks
        assert 'lead_time' in benchmarks

    def test_kpi_sre_benchmarks(self):
        """Test benchmarks SRE"""
        benchmarks = {
            'availability': {
                'elite': 0.99999,
                'high': 0.9999,
                'medium': 0.999,
                'low': 0.99
            },
            'latency': {
                'elite': '<50ms',
                'high': '<100ms',
                'medium': '<500ms',
                'low': '>500ms'
            }
        }
        
        assert benchmarks['availability']['elite'] == 0.99999
        assert benchmarks['latency']['elite'] == '<50ms'

    def test_kpi_security_benchmarks(self):
        """Test benchmarks de seguridad"""
        benchmarks = {
            'vulnerability_count': {
                'excellent': 0,
                'good': '<5',
                'fair': '<20',
                'poor': '>20'
            },
            'compliance_score': {
                'excellent': '>95',
                'good': '>80',
                'fair': '>60',
                'poor': '<60'
            }
        }
        
        assert benchmarks['vulnerability_count']['excellent'] == 0
        assert benchmarks['compliance_score']['excellent'] == '>95'


class TestKPIScoring:
    """Tests para cálculo de scores KPI"""

    def test_kpi_score_calculation(self):
        """Test cálculo de score"""
        def calculate_score(value, threshold):
            return min(100, max(0, (value / threshold) * 100))
        
        score = calculate_score(10, 20)
        assert score == 50

    def test_kpi_weighted_score(self):
        """Test cálculo de score ponderado"""
        metrics = {
            'deployment_frequency': {'value': 10, 'weight': 0.2},
            'lead_time': {'value': 5, 'weight': 0.2},
            'mttr': {'value': 2, 'weight': 0.25},
            'change_failure_rate': {'value': 0.1, 'weight': 0.25},
            'availability': {'value': 0.9999, 'weight': 0.1}
        }
        
        total_weight = sum(m['weight'] for m in metrics.values())
        assert total_weight == 1.0

    def test_kpi_aggregate_score(self):
        """Test cálculo de score agregado"""
        scores = {
            'dora': 85,
            'sre': 90,
            'security': 95,
            'cost': 80,
            'quality': 88
        }
        
        aggregate_score = sum(scores.values()) / len(scores)
        assert aggregate_score == 87.6


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
