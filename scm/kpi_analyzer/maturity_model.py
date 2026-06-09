#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maturity Model Module — DevSecOps Toolbox KPI Analyzer
Implementación del modelo de madurez DevSecOps de 6 niveles

Version: 1.0.0
Author: Harold Adrian
"""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import IntEnum

class MaturityLevel(IntEnum):
    """Niveles de madurez DevSecOps (0-5)"""
    CAOTICO = 0
    INICIAL = 1
    GESTIONADO = 2
    DEFINIDO = 3
    CUANTIFICADO = 4
    OPTIMIZADO = 5

@dataclass
class DimensionScore:
    """Score de una dimensión específica"""
    name: str
    weight: float
    current_level: MaturityLevel
    score_percentage: float
    kpis_met: int
    kpis_total: int
    blocking_kpis: List[str]

@dataclass
class MaturityAssessment:
    """Evaluación completa de madurez"""
    global_level: MaturityLevel
    global_score: float
    dimension_scores: Dict[str, DimensionScore]
    next_level: MaturityLevel
    gap_to_next: float
    recommended_actions: List[Dict[str, Any]]

# Pesos de dimensiones
DIMENSION_WEIGHTS = {
    "entrega_continua": 0.20,
    "confiabilidad": 0.20,
    "seguridad": 0.20,
    "observabilidad": 0.15,
    "cumplimiento": 0.15,
    "eficiencia_operativa": 0.10,
}

# Criterios por nivel y dimensión
MATURITY_CRITERIA = {
    MaturityLevel.INICIAL: {
        "entrega_continua": {
            "deployment_frequency": 0.03,  # 1-2/mes
            "change_failure_rate": 50.0,
        },
        "confiabilidad": {
            "mttr": 10080.0,  # 2-7 días en minutos
            "availability": 95.0,
        },
        "seguridad": {
            "mfa_coverage": 30.0,
        },
        "observabilidad": {
            "monitoring_coverage": 20.0,
        },
        "cumplimiento": {
            "policy_adherence": 30.0,
        },
        "eficiencia_operativa": {
            "resource_utilization": 30.0,
        },
    },
    MaturityLevel.GESTIONADO: {
        "entrega_continua": {
            "deployment_frequency": 0.14,  # 1/semana
            "change_failure_rate": 30.0,
            "deployment_success_rate": 70.0,
        },
        "confiabilidad": {
            "mttr": 2880.0,  # 1-2 días
            "availability": 98.0,
            "mtbf": 30.0,
        },
        "seguridad": {
            "mfa_coverage": 50.0,
            "certificate_expiry_risk": 20.0,
        },
        "observabilidad": {
            "monitoring_coverage": 40.0,
        },
        "cumplimiento": {
            "policy_adherence": 50.0,
            "approval_workflow_coverage": 80.0,
        },
        "eficiencia_operativa": {
            "resource_utilization": 40.0,
        },
    },
    MaturityLevel.DEFINIDO: {
        "entrega_continua": {
            "deployment_frequency": 1.0,  # 1/día
            "change_failure_rate": 15.0,
            "lead_time_for_changes": 168.0,  # < 1 semana
            "deployment_success_rate": 85.0,
        },
        "confiabilidad": {
            "mttr": 1440.0,  # < 24h
            "availability": 99.0,
            "mtbf": 60.0,
        },
        "seguridad": {
            "mfa_coverage": 90.0,
            "secret_rotation_coverage": 80.0,
            "certificate_expiry_risk": 10.0,
            "iam_over_permissioning": 10.0,
        },
        "observabilidad": {
            "monitoring_coverage": 60.0,
            "slo_compliance": 95.0,
        },
        "cumplimiento": {
            "policy_adherence": 70.0,
            "pipeline_drift_rate": 10.0,
        },
        "eficiencia_operativa": {
            "resource_utilization": 60.0,
        },
    },
    MaturityLevel.CUANTIFICADO: {
        "entrega_continua": {
            "deployment_frequency": 2.0,  # > 1/día
            "change_failure_rate": 5.0,
            "lead_time_for_changes": 24.0,  # < 1 día
            "deployment_success_rate": 95.0,
        },
        "confiabilidad": {
            "mttr": 60.0,  # < 1h
            "availability": 99.5,
            "mtbf": 90.0,
            "error_budget_remaining": 25.0,
        },
        "seguridad": {
            "mfa_coverage": 100.0,
            "secret_rotation_coverage": 100.0,
            "certificate_expiry_risk": 5.0,
            "iam_over_permissioning": 5.0,
            "vulnerability_remediation_time": 30.0,
        },
        "observabilidad": {
            "monitoring_coverage": 80.0,
            "slo_compliance": 99.0,
            "resource_utilization_efficiency": 0.6,
        },
        "cumplimiento": {
            "policy_adherence": 90.0,
            "pipeline_drift_rate": 5.0,
        },
        "eficiencia_operativa": {
            "resource_utilization": 75.0,
            "auto_scaling_effectiveness": 80.0,
        },
    },
    MaturityLevel.OPTIMIZADO: {
        "entrega_continua": {
            "deployment_frequency": 5.0,  # Múltiples/día
            "change_failure_rate": 1.0,
            "lead_time_for_changes": 1.0,  # < 1h
            "deployment_success_rate": 99.0,
        },
        "confiabilidad": {
            "mttr": 15.0,  # < 15min
            "availability": 99.9,
            "mtbf": 180.0,
            "error_budget_remaining": 50.0,
        },
        "seguridad": {
            "mfa_coverage": 100.0,
            "secret_rotation_coverage": 100.0,
            "certificate_expiry_risk": 0.0,
            "iam_over_permissioning": 0.0,
            "vulnerability_remediation_time": 7.0,
        },
        "observabilidad": {
            "monitoring_coverage": 95.0,
            "slo_compliance": 99.9,
            "resource_utilization_efficiency": 0.7,
        },
        "cumplimiento": {
            "policy_adherence": 95.0,
            "pipeline_drift_rate": 0.0,
        },
        "eficiencia_operativa": {
            "resource_utilization": 85.0,
            "auto_scaling_effectiveness": 95.0,
        },
    },
}

# Acciones recomendadas por nivel
RECOMMENDED_ACTIONS = {
    (MaturityLevel.CAOTICO, MaturityLevel.INICIAL): [
        {"action": "Implementar CI básico (build automatizado)", "impact": "high", "effort": "medium"},
        {"action": "Documentar procesos críticos", "impact": "medium", "effort": "low"},
        {"action": "Configurar monitoreo básico (logs, uptime)", "impact": "high", "effort": "medium"},
        {"action": "Definir políticas de seguridad", "impact": "high", "effort": "low"},
        {"action": "Establecer versionado de código", "impact": "high", "effort": "low"},
    ],
    (MaturityLevel.INICIAL, MaturityLevel.GESTIONADO): [
        {"action": "Automatizar deployments completos (CI + CD)", "impact": "high", "effort": "high"},
        {"action": "Implementar rollback automatizado", "impact": "high", "effort": "medium"},
        {"action": "Aumentar cobertura de tests > 50%", "impact": "high", "effort": "high"},
        {"action": "Monitorear servicios críticos", "impact": "high", "effort": "medium"},
        {"action": "Aplicar políticas de seguridad (branch policies)", "impact": "medium", "effort": "medium"},
        {"action": "Implementar IaC básico (Terraform/CloudFormation)", "impact": "high", "effort": "high"},
    ],
    (MaturityLevel.GESTIONADO, MaturityLevel.DEFINIDO): [
        {"action": "Aumentar deployment frequency > 1/día", "impact": "high", "effort": "medium"},
        {"action": "Definir SLIs/SLOs para servicios críticos", "impact": "high", "effort": "medium"},
        {"action": "Implementar security scanning automatizado (SAST/DAST)", "impact": "high", "effort": "high"},
        {"action": "Automatizar secret rotation", "impact": "high", "effort": "medium"},
        {"action": "Implementar observabilidad distribuida (tracing)", "impact": "high", "effort": "high"},
        {"action": "Establecer error budget tracking", "impact": "medium", "effort": "medium"},
    ],
    (MaturityLevel.DEFINIDO, MaturityLevel.CUANTIFICADO): [
        {"action": "Habilitar deployment on-demand (múltiples/día)", "impact": "high", "effort": "medium"},
        {"action": "Implementar error budgets con políticas de freeze", "impact": "high", "effort": "high"},
        {"action": "Desarrollar auto-healing para incidentes comunes", "impact": "high", "effort": "high"},
        {"action": "Iniciar chaos engineering (GameDays)", "impact": "medium", "effort": "high"},
        {"action": "Implementar predictive analytics (anomaly detection)", "impact": "medium", "effort": "high"},
        {"action": "Desplegar canary deployments / blue-green", "impact": "high", "effort": "medium"},
    ],
    (MaturityLevel.CUANTIFICADO, MaturityLevel.OPTIMIZADO): [
        {"action": "Implementar AIOps / ML-driven operations", "impact": "high", "effort": "high"},
        {"action": "Completar arquitectura zero-trust", "impact": "high", "effort": "high"},
        {"action": "Automatizar chaos engineering continuo", "impact": "medium", "effort": "high"},
        {"action": "Desarrollar self-service platform", "impact": "high", "effort": "high"},
        {"action": "Establecer cultura FinOps (cost as code)", "impact": "medium", "effort": "medium"},
        {"action": "Optimizar developer experience", "impact": "high", "effort": "medium"},
    ],
}


def evaluate_dimension(dimension_name: str, kpi_values: Dict[str, float], target_level: MaturityLevel) -> DimensionScore:
    """
    Evalúa una dimensión específica contra un nivel de madurez objetivo.
    
    Args:
        dimension_name: Nombre de la dimensión
        kpi_values: Valores actuales de KPIs
        target_level: Nivel de madurez objetivo
        
    Returns:
        DimensionScore con la evaluación
    """
    if target_level == MaturityLevel.CAOTICO:
        return DimensionScore(
            name=dimension_name,
            weight=DIMENSION_WEIGHTS.get(dimension_name, 0.0),
            current_level=MaturityLevel.CAOTICO,
            score_percentage=0.0,
            kpis_met=0,
            kpis_total=0,
            blocking_kpis=[]
        )
    
    criteria = MATURITY_CRITERIA.get(target_level, {}).get(dimension_name, {})
    if not criteria:
        return DimensionScore(
            name=dimension_name,
            weight=DIMENSION_WEIGHTS.get(dimension_name, 0.0),
            current_level=MaturityLevel.CAOTICO,
            score_percentage=0.0,
            kpis_met=0,
            kpis_total=len(criteria),
            blocking_kpis=list(criteria.keys())
        )
    
    kpis_met = 0
    kpis_total = len(criteria)
    blocking_kpis = []
    
    for kpi_key, threshold in criteria.items():
        actual_value = kpi_values.get(kpi_key, 0.0)
        
        # Determine if KPI is met based on whether higher or lower is better
        if kpi_key in ["deployment_frequency", "availability", "mfa_coverage", "secret_rotation_coverage",
                       "monitoring_coverage", "slo_compliance", "policy_adherence", "deployment_success_rate",
                       "approval_workflow_coverage", "resource_utilization", "auto_scaling_effectiveness",
                       "error_budget_remaining", "mtbf", "resource_utilization_efficiency"]:
            # Higher is better
            if actual_value >= threshold:
                kpis_met += 1
            else:
                blocking_kpis.append(kpi_key)
        else:
            # Lower is better
            if actual_value <= threshold:
                kpis_met += 1
            else:
                blocking_kpis.append(kpi_key)
    
    score_percentage = (kpis_met / kpis_total * 100) if kpis_total > 0 else 0.0
    
    # Determine current level (highest level with >= 80% criteria met)
    current_level = MaturityLevel.CAOTICO
    for level in reversed(list(MaturityLevel)):
        if level == MaturityLevel.CAOTICO:
            continue
        level_criteria = MATURITY_CRITERIA.get(level, {}).get(dimension_name, {})
        if not level_criteria:
            continue
        
        level_met = 0
        for kpi_key, threshold in level_criteria.items():
            actual_value = kpi_values.get(kpi_key, 0.0)
            if kpi_key in ["deployment_frequency", "availability", "mfa_coverage", "secret_rotation_coverage",
                           "monitoring_coverage", "slo_compliance", "policy_adherence", "deployment_success_rate",
                           "approval_workflow_coverage", "resource_utilization", "auto_scaling_effectiveness",
                           "error_budget_remaining", "mtbf", "resource_utilization_efficiency"]:
                if actual_value >= threshold:
                    level_met += 1
            else:
                if actual_value <= threshold:
                    level_met += 1
        
        if level_met / len(level_criteria) >= 0.8:
            current_level = level
            break
    
    return DimensionScore(
        name=dimension_name,
        weight=DIMENSION_WEIGHTS.get(dimension_name, 0.0),
        current_level=current_level,
        score_percentage=score_percentage,
        kpis_met=kpis_met,
        kpis_total=kpis_total,
        blocking_kpis=blocking_kpis
    )


def assess_maturity(kpi_values: Dict[str, float]) -> MaturityAssessment:
    """
    Evalúa el nivel de madurez global basándose en los valores de KPIs.
    
    Args:
        kpi_values: Diccionario con valores de KPIs
        
    Returns:
        MaturityAssessment con evaluación completa
    """
    # Evaluate each dimension
    dimension_scores = {}
    for dimension_name in DIMENSION_WEIGHTS.keys():
        # Try each level from highest to lowest
        for level in reversed(list(MaturityLevel)):
            if level == MaturityLevel.CAOTICO:
                continue
            score = evaluate_dimension(dimension_name, kpi_values, level)
            if score.score_percentage >= 80.0:
                dimension_scores[dimension_name] = score
                break
        else:
            # No level met, assign CAOTICO
            dimension_scores[dimension_name] = DimensionScore(
                name=dimension_name,
                weight=DIMENSION_WEIGHTS[dimension_name],
                current_level=MaturityLevel.CAOTICO,
                score_percentage=0.0,
                kpis_met=0,
                kpis_total=0,
                blocking_kpis=[]
            )
    
    # Calculate global level (weighted average)
    weighted_sum = sum(score.current_level * score.weight for score in dimension_scores.values())
    global_score = weighted_sum / sum(DIMENSION_WEIGHTS.values()) if DIMENSION_WEIGHTS else 0.0
    global_level = MaturityLevel(int(round(global_score)))
    
    # Determine next level and gap
    next_level = MaturityLevel(min(global_level + 1, MaturityLevel.OPTIMIZADO))
    gap_to_next = (next_level - global_score) * 100 / 5  # Percentage gap
    
    # Get recommended actions
    action_key = (global_level, next_level)
    recommended_actions = RECOMMENDED_ACTIONS.get(action_key, [])
    
    return MaturityAssessment(
        global_level=global_level,
        global_score=global_score,
        dimension_scores=dimension_scores,
        next_level=next_level,
        gap_to_next=gap_to_next,
        recommended_actions=recommended_actions
    )


def get_level_name(level: MaturityLevel) -> str:
    """Retorna el nombre en español del nivel de madurez"""
    names = {
        MaturityLevel.CAOTICO: "Caótico",
        MaturityLevel.INICIAL: "Inicial",
        MaturityLevel.GESTIONADO: "Gestionado",
        MaturityLevel.DEFINIDO: "Definido",
        MaturityLevel.CUANTIFICADO: "Cuantificado",
        MaturityLevel.OPTIMIZADO: "Optimizado",
    }
    return names.get(level, "Desconocido")


def get_level_color(level: MaturityLevel) -> str:
    """Retorna el color asociado al nivel de madurez"""
    colors = {
        MaturityLevel.CAOTICO: "#e74c3c",      # Rojo
        MaturityLevel.INICIAL: "#e67e22",      # Naranja oscuro
        MaturityLevel.GESTIONADO: "#f39c12",   # Naranja
        MaturityLevel.DEFINIDO: "#f1c40f",     # Amarillo
        MaturityLevel.CUANTIFICADO: "#27ae60", # Verde
        MaturityLevel.OPTIMIZADO: "#2ecc71",   # Verde brillante
    }
    return colors.get(level, "#95a5a6")
