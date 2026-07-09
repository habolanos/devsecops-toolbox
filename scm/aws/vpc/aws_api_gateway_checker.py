#!/usr/bin/env python3
"""
AWS API Gateway Checker - Analiza API Gateways, stages, métodos y autorizaciones
Tool 24
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


class APIGatewayChecker:
    """Analizador de API Gateways"""
    
    def __init__(self, profile: str = None, region: str = 'us-east-1'):
        self.profile = profile
        self.region = region
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.client = self.session.client('apigateway', region_name=region)
    
    def get_apis(self) -> List[Dict[str, Any]]:
        """Obtiene todas las APIs"""
        try:
            response = self.client.get_rest_apis()
            return response.get('items', [])
        except ClientError as e:
            print(f"Error obteniendo APIs: {e}", file=sys.stderr)
            return []
    
    def analyze_api(self, api_id: str) -> Dict[str, Any]:
        """Analiza una API específica"""
        try:
            api = self.client.get_rest_api(restApiId=api_id)
            stages = self.client.get_stages(restApiId=api_id)
            resources = self.client.get_resources(restApiId=api_id)
            
            return {
                "api_id": api_id,
                "name": api.get('name'),
                "description": api.get('description'),
                "stages": [{"name": s['stageName'], "created_date": str(s.get('createdDate'))} 
                          for s in stages.get('item', [])],
                "resources": len(resources.get('items', [])),
                "endpoint_type": api.get('endpointConfiguration', {}).get('types', [])
            }
        except ClientError as e:
            print(f"Error analizando API {api_id}: {e}", file=sys.stderr)
            return {}
    
    def check_all(self) -> Dict[str, Any]:
        """Verifica todas las APIs"""
        apis = self.get_apis()
        result = {
            "region": self.region,
            "total_apis": len(apis),
            "apis": []
        }
        
        for api in apis:
            analysis = self.analyze_api(api['id'])
            if analysis:
                result["apis"].append(analysis)
        
        return result


def main():
    parser = argparse.ArgumentParser(description='Analiza API Gateways')
    parser.add_argument('--profile', help='AWS profile')
    parser.add_argument('--region', default='us-east-1', help='Región AWS')
    parser.add_argument('-o', '--output', choices=['json', 'csv'], help='Formato de salida')
    
    args = parser.parse_args()
    
    checker = APIGatewayChecker(profile=args.profile, region=args.region)
    result = checker.check_all()
    
    if args.output == 'json':
        output = json.dumps(result, indent=2, default=str)
        print(output)
        if EXPORT_MANAGER_AVAILABLE:
            manager = ExportManager()
            manager.export_json(result, 'api_gateway_analysis')
    else:
        print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
