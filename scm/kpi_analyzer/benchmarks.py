#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmarks Module — DevSecOps Toolbox KPI Analyzer
Tablas de referencia de industria basadas en DORA, SRE, ITIL 4, NIST CSF

Version: 1.0.0
Author: Harold Adrian
"""

from typing import Dict, Any, Tuple
from enum import Enum

class BenchmarkLevel(Enum):
    """Niveles de benchmark de industria"""
    ELITE = "elite"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class MaturityLevel(Enum):
    """Niveles de madurez DevSecOps"""
    CAOTICO = 0
    INICIAL = 1
    GESTIONADO = 2
    DEFINIDO = 3
    CUANTIFICADO = 4
    OPTIMIZADO = 5

# =============================================================================
# DORA METRICS BENCHMARKS (2024)
# =============================================================================

DORA_BENCHMARKS = {
    "deployment_frequency": {
        "elite": {"value": 1.0, "unit": "deploys/día", "description": "≥ 1 deploy/día"},
        "high": {"value": 0.14, "unit": "deploys/día", "description": "1/semana a 1/día"},
        "medium": {"value": 0.03, "unit": "deploys/día", "description": "1/mes a 1/semana"},
        "low": {"value": 0.0, "unit": "deploys/día", "description": "< 1/mes"},
    },
    "change_failure_rate": {
        "elite": {"value": 5.0, "unit": "%", "description": "< 5%"},
        "high": {"value": 15.0, "unit": "%", "description": "5-15%"},
        "medium": {"value": 30.0, "unit": "%", "description": "15-30%"},
        "low": {"value": 100.0, "unit": "%", "description": "> 30%"},
    },
    "lead_time_for_changes": {
        "elite": {"value": 24.0, "unit": "horas", "description": "< 1 día"},
        "high": {"value": 168.0, "unit": "horas", "description": "1-7 días"},
        "medium": {"value": 720.0, "unit": "horas", "description": "1-4 semanas"},
        "low": {"value": 99999.0, "unit": "horas", "description": "> 1 mes"},
    },
    "mttr": {
        "elite": {"value": 60.0, "unit": "minutos", "description": "< 1 hora"},
        "high": {"value": 1440.0, "unit": "minutos", "description": "1-24 horas"},
        "medium": {"value": 10080.0, "unit": "minutos", "description": "1-7 días"},
        "low": {"value": 999999.0, "unit": "minutos", "description": "> 7 días"},
    },
}

# =============================================================================
# SRE METRICS BENCHMARKS (Google SRE Book)
# =============================================================================

SRE_BENCHMARKS = {
    "availability": {
        "elite": {"value": 99.9, "unit": "%", "description": "4 nines (99.9%)"},
        "high": {"value": 99.5, "unit": "%", "description": "3 nines (99.5-99.9%)"},
        "medium": {"value": 99.0, "unit": "%", "description": "2 nines (99.0-99.5%)"},
        "low": {"value": 0.0, "unit": "%", "description": "< 99.0%"},
    },
    "error_budget_remaining": {
        "elite": {"value": 50.0, "unit": "%", "description": "> 50% restante"},
        "high": {"value": 25.0, "unit": "%", "description": "25-50% restante"},
        "medium": {"value": 10.0, "unit": "%", "description": "10-25% restante"},
        "low": {"value": 0.0, "unit": "%", "description": "< 10% restante"},
    },
    "slo_compliance": {
        "elite": {"value": 99.0, "unit": "%", "description": "> 99% SLOs cumplidos"},
        "high": {"value": 95.0, "unit": "%", "description": "95-99% SLOs cumplidos"},
        "medium": {"value": 90.0, "unit": "%", "description": "90-95% SLOs cumplidos"},
        "low": {"value": 0.0, "unit": "%", "description": "< 90% SLOs cumplidos"},
    },
    "resource_utilization": {
        "elite": {"value": (0.6, 0.8), "unit": "ratio", "description": "0.6-0.8 (optimal)"},
        "high": {"value": (0.5, 0.9), "unit": "ratio", "description": "0.5-0.9"},
        "medium": {"value": (0.4, 1.0), "unit": "ratio", "description": "0.4-1.0"},
        "low": {"value": (0.0, 1.5), "unit": "ratio", "description": "< 0.4 or > 1.0"},
    },
}

# =============================================================================
# SECURITY BENCHMARKS (NIST CSF, ISO 20000)
# =============================================================================

SECURITY_BENCHMARKS = {
    "mfa_coverage": {
        "elite": {"value": 100.0, "unit": "%", "description": "100% MFA"},
        "high": {"value": 90.0, "unit": "%", "description": "90-100% MFA"},
        "medium": {"value": 70.0, "unit": "%", "description": "70-90% MFA"},
        "low": {"value": 0.0, "unit": "%", "description": "< 70% MFA"},
    },
    "certificate_expiry_risk": {
        "elite": {"value": 0.0, "unit": "%", "description": "0% expirando < 30d"},
        "high": {"value": 5.0, "unit": "%", "description": "0-5% expirando"},
        "medium": {"value": 15.0, "unit": "%", "description": "5-15% expirando"},
        "low": {"value": 100.0, "unit": "%", "description": "> 15% expirando"},
    },
    "secret_rotation_coverage": {
        "elite": {"value": 100.0, "unit": "%", "description": "100% rotados < 90d"},
        "high": {"value": 80.0, "unit": "%", "description": "80-100% rotados"},
        "medium": {"value": 50.0, "unit": "%", "description": "50-80% rotados"},
        "low": {"value": 0.0, "unit": "%", "description": "< 50% rotados"},
    },
    "iam_over_permissioning": {
        "elite": {"value": 0.0, "unit": "%", "description": "0% wildcards"},
        "high": {"value": 5.0, "unit": "%", "description": "0-5% wildcards"},
        "medium": {"value": 15.0, "unit": "%", "description": "5-15% wildcards"},
        "low": {"value": 100.0, "unit": "%", "description": "> 15% wildcards"},
    },
    "vulnerability_remediation_time": {
        "elite": {"value": 7.0, "unit": "días", "description": "< 7 días (critical)"},
        "high": {"value": 30.0, "unit": "días", "description": "7-30 días"},
        "medium": {"value": 90.0, "unit": "días", "description": "30-90 días"},
        "low": {"value": 999.0, "unit": "días", "description": "> 90 días"},
    },
}

# =============================================================================
# COMPLIANCE BENCHMARKS (ITIL 4, ISO 20000)
# =============================================================================

COMPLIANCE_BENCHMARKS = {
    "policy_adherence": {
        "elite": {"value": 95.0, "unit": "%", "description": "> 95% compliant"},
        "high": {"value": 85.0, "unit": "%", "description": "85-95% compliant"},
        "medium": {"value": 70.0, "unit": "%", "description": "70-85% compliant"},
        "low": {"value": 0.0, "unit": "%", "description": "< 70% compliant"},
    },
    "pipeline_drift_rate": {
        "elite": {"value": 0.0, "unit": "%", "description": "0% drift"},
        "high": {"value": 5.0, "unit": "%", "description": "0-5% drift"},
        "medium": {"value": 15.0, "unit": "%", "description": "5-15% drift"},
        "low": {"value": 100.0, "unit": "%", "description": "> 15% drift"},
    },
}

# =============================================================================
# MATURITY LEVEL THRESHOLDS
# =============================================================================

MATURITY_THRESHOLDS = {
    MaturityLevel.CAOTICO: {
        "deployment_frequency": 0.0,  # < 1/mes
        "change_failure_rate": 100.0,  # Sin límite
        "mttr": 10080.0,  # > 7 días
        "availability": 0.0,  # < 95%
        "monitoring_coverage": 0.0,  # < 20%
    },
    MaturityLevel.INICIAL: {
        "deployment_frequency": 0.03,  # 1-2/mes
        "change_failure_rate": 50.0,  # 30-50%
        "mttr": 2880.0,  # 2-7 días
        "availability": 95.0,  # 95-98%
        "mfa_coverage": 0.0,  # < 50%
        "monitoring_coverage": 20.0,  # 20-40%
    },
    MaturityLevel.GESTIONADO: {
        "deployment_frequency": 0.14,  # 1/semana
        "change_failure_rate": 30.0,  # 15-30%
        "mttr": 1440.0,  # 1-2 días
        "availability": 98.0,  # 98-99%
        "mfa_coverage": 50.0,  # 50-80%
        "monitoring_coverage": 40.0,  # 40-60%
        "policy_adherence": 50.0,  # 50-70%
    },
    MaturityLevel.DEFINIDO: {
        "deployment_frequency": 1.0,  # 1/día
        "change_failure_rate": 15.0,  # 5-15%
        "mttr": 1440.0,  # < 24h
        "availability": 99.0,  # 99-99.5%
        "mfa_coverage": 90.0,  # > 90%
        "secret_rotation_coverage": 80.0,  # > 80%
        "monitoring_coverage": 60.0,  # 60-80%
        "slo_compliance": 95.0,  # > 95%
        "policy_adherence": 70.0,  # 70-90%
    },
    MaturityLevel.CUANTIFICADO: {
        "deployment_frequency": 2.0,  # > 1/día
        "change_failure_rate": 5.0,  # < 5%
        "mttr": 60.0,  # < 1h
        "availability": 99.5,  # 99.5-99.9%
        "mfa_coverage": 100.0,  # 100%
        "secret_rotation_coverage": 100.0,  # 100%
        "monitoring_coverage": 80.0,  # 80-95%
        "slo_compliance": 99.0,  # > 99%
        "policy_adherence": 90.0,  # > 90%
        "resource_utilization": 75.0,  # 75-85%
    },
    MaturityLevel.OPTIMIZADO: {
        "deployment_frequency": 5.0,  # Múltiples/día
        "change_failure_rate": 1.0,  # < 1%
        "mttr": 15.0,  # < 15min
        "availability": 99.9,  # > 99.9%
        "mfa_coverage": 100.0,  # 100%
        "secret_rotation_coverage": 100.0,  # 100%
        "monitoring_coverage": 95.0,  # > 95%
        "slo_compliance": 99.9,  # > 99.9%
        "policy_adherence": 95.0,  # > 95%
        "resource_utilization": 85.0,  # 85-95%
    },
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_benchmark_level(kpi_id: str, value: float) -> BenchmarkLevel:
    """
    Determina el nivel de benchmark para un KPI dado su valor.
    
    Args:
        kpi_id: ID del KPI (ej: 'ec_001')
        value: Valor actual del KPI
        
    Returns:
        BenchmarkLevel correspondiente
    """
    # Map KPI IDs to benchmark dictionaries
    kpi_to_benchmark = {
        "ec_001": DORA_BENCHMARKS["deployment_frequency"],
        "ec_002": DORA_BENCHMARKS["change_failure_rate"],
        "ec_003": DORA_BENCHMARKS["lead_time_for_changes"],
        "conf_001": DORA_BENCHMARKS["mttr"],
        "conf_002": SRE_BENCHMARKS["availability"],
        "conf_003": SRE_BENCHMARKS["error_budget_remaining"],
        "obs_002": SRE_BENCHMARKS["slo_compliance"],
        "obs_003": SRE_BENCHMARKS["resource_utilization"],
        "seg_001": SECURITY_BENCHMARKS["mfa_coverage"],
        "seg_002": SECURITY_BENCHMARKS["certificate_expiry_risk"],
        "seg_003": SECURITY_BENCHMARKS["secret_rotation_coverage"],
        "seg_004": SECURITY_BENCHMARKS["iam_over_permissioning"],
        "seg_005": SECURITY_BENCHMARKS["vulnerability_remediation_time"],
        "cump_001": COMPLIANCE_BENCHMARKS["policy_adherence"],
        "cump_002": COMPLIANCE_BENCHMARKS["pipeline_drift_rate"],
    }
    
    benchmark = kpi_to_benchmark.get(kpi_id)
    if not benchmark:
        return BenchmarkLevel.MEDIUM
    
    # Determine level based on value and benchmark thresholds
    # Logic depends on whether higher is better or lower is better
    if kpi_id in ["ec_001", "conf_002", "conf_003", "obs_002", "seg_001", "seg_003", "cump_001"]:
        # Higher is better
        if value >= benchmark["elite"]["value"]:
            return BenchmarkLevel.ELITE
        elif value >= benchmark["high"]["value"]:
            return BenchmarkLevel.HIGH
        elif value >= benchmark["medium"]["value"]:
            return BenchmarkLevel.MEDIUM
        else:
            return BenchmarkLevel.LOW
    else:
        # Lower is better
        if value <= benchmark["elite"]["value"]:
            return BenchmarkLevel.ELITE
        elif value <= benchmark["high"]["value"]:
            return BenchmarkLevel.HIGH
        elif value <= benchmark["medium"]["value"]:
            return BenchmarkLevel.MEDIUM
        else:
            return BenchmarkLevel.LOW


def calculate_maturity_level(kpi_scores: Dict[str, float]) -> Tuple[MaturityLevel, float]:
    """
    Calcula el nivel de madurez global basándose en los scores de KPIs.
    
    Args:
        kpi_scores: Diccionario con KPI IDs y sus valores
        
    Returns:
        Tupla (MaturityLevel, score_percentage)
    """
    # Simplified logic: count how many KPIs meet each maturity level threshold
    level_scores = {}
    
    for level in MaturityLevel:
        if level == MaturityLevel.CAOTICO:
            continue
        
        thresholds = MATURITY_THRESHOLDS[level]
        met_count = 0
        total_count = len(thresholds)
        
        for kpi_key, threshold in thresholds.items():
            # Map threshold keys to KPI IDs (simplified)
            if kpi_key == "deployment_frequency" and "ec_001" in kpi_scores:
                if kpi_scores["ec_001"] >= threshold:
                    met_count += 1
            elif kpi_key == "change_failure_rate" and "ec_002" in kpi_scores:
                if kpi_scores["ec_002"] <= threshold:
                    met_count += 1
            elif kpi_key == "mttr" and "conf_001" in kpi_scores:
                if kpi_scores["conf_001"] <= threshold:
                    met_count += 1
            elif kpi_key == "availability" and "conf_002" in kpi_scores:
                if kpi_scores["conf_002"] >= threshold:
                    met_count += 1
            # Add more mappings as needed
        
        level_scores[level] = met_count / total_count if total_count > 0 else 0.0
    
    # Determine highest level with >= 80% threshold met
    for level in reversed(list(MaturityLevel)):
        if level == MaturityLevel.CAOTICO:
            continue
        if level_scores.get(level, 0.0) >= 0.8:
            return level, level_scores[level] * 100
    
    return MaturityLevel.INICIAL, 0.0


def get_benchmark_color(level: BenchmarkLevel) -> str:
    """
    Retorna el color asociado a un nivel de benchmark.
    
    Args:
        level: Nivel de benchmark
        
    Returns:
        Código de color hexadecimal
    """
    colors = {
        BenchmarkLevel.ELITE: "#2ecc71",  # Verde brillante
        BenchmarkLevel.HIGH: "#27ae60",   # Verde
        BenchmarkLevel.MEDIUM: "#f39c12", # Naranja
        BenchmarkLevel.LOW: "#e74c3c",    # Rojo
    }
    return colors.get(level, "#95a5a6")  # Gris por defecto


def get_benchmark_emoji(level: BenchmarkLevel) -> str:
    """
    Retorna el emoji asociado a un nivel de benchmark.
    
    Args:
        level: Nivel de benchmark
        
    Returns:
        Emoji string
    """
    emojis = {
        BenchmarkLevel.ELITE: "💚",
        BenchmarkLevel.HIGH: "🟢",
        BenchmarkLevel.MEDIUM: "🟡",
        BenchmarkLevel.LOW: "🔴",
    }
    return emojis.get(level, "⚪")
