#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KPI Analyzer Package — DevSecOps Toolbox
Análisis de KPIs desde salidas JSON con modelo de madurez DevSecOps

Version: 1.0.0
Author: Harold Adrian
"""

__version__ = "1.0.0"
__author__ = "Harold Adrian"

from .analyzer import KPIAnalyzer
from .reporter import KPIReporter
from .maturity_model import (
    MaturityLevel,
    DimensionScore,
    MaturityAssessment,
    assess_maturity,
    get_level_name,
    get_level_color,
)
from .benchmarks import (
    BenchmarkLevel,
    get_benchmark_level,
    get_benchmark_color,
    get_benchmark_emoji,
)

__all__ = [
    "KPIAnalyzer",
    "KPIReporter",
    "MaturityLevel",
    "DimensionScore",
    "MaturityAssessment",
    "assess_maturity",
    "get_level_name",
    "get_level_color",
    "BenchmarkLevel",
    "get_benchmark_level",
    "get_benchmark_color",
    "get_benchmark_emoji",
]
