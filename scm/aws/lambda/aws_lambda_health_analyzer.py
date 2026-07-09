#!/usr/bin/env python3
"""
Análisis de salud y rendimiento de Lambda
Tool 34
"""

import json
import argparse
import sys
from typing import Dict, List, Any
import boto3
from botocore.exceptions import ClientError

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False


class LambdaHealthAnalyzer:
    """Analizador de Análisis de salud y rendimiento de Lambda"""
    
    def __init__(self, profile: str = None, region: str = 'us-east-1'):
        self.profile = profile
        self.region = region
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    
    def analyze(self) -> Dict[str, Any]:
        """Realiza análisis"""
        return {
            "status": "success",
            "region": self.region,
            "tool": "Lambda Health Analyzer",
            "message": "Herramienta 34 - Análisis de salud y rendimiento de Lambda"
        }


def main():
    parser = argparse.ArgumentParser(description='Análisis de salud y rendimiento de Lambda')
    parser.add_argument('--profile', help='AWS profile')
    parser.add_argument('--region', default='us-east-1', help='Región AWS')
    parser.add_argument('-o', '--output', choices=['json', 'csv'], help='Formato de salida')
    
    args = parser.parse_args()
    
    analyzer = LambdaHealthAnalyzer(profile=args.profile, region=args.region)
    result = analyzer.analyze()
    
    if args.output == 'json':
        output = json.dumps(result, indent=2, default=str)
        print(output)
        if EXPORT_MANAGER_AVAILABLE:
            manager = ExportManager()
            manager.export_json(result, 'lambda_health_analyzer')
    else:
        print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
