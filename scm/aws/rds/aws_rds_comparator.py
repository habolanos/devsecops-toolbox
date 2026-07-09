#!/usr/bin/env python3
"""
AWS RDS Comparator - Compara instancias RDS entre regiones o cuentas
Tool 23
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


class RDSComparator:
    """Comparador de instancias RDS"""
    
    def __init__(self, profile: str = None):
        self.profile = profile
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        
    def get_instances(self, region: str) -> List[Dict[str, Any]]:
        """Obtiene instancias RDS de una región"""
        try:
            client = self.session.client('rds', region_name=region)
            response = client.describe_db_instances()
            return response.get('DBInstances', [])
        except ClientError as e:
            print(f"Error obteniendo instancias RDS en {region}: {e}", file=sys.stderr)
            return []
    
    def compare_instances(self, region1: str, region2: str, instance_name: str = None) -> Dict[str, Any]:
        """Compara instancias RDS entre dos regiones"""
        instances1 = self.get_instances(region1)
        instances2 = self.get_instances(region2)
        
        result = {
            "region1": region1,
            "region2": region2,
            "comparison": {
                "only_in_region1": [],
                "only_in_region2": [],
                "in_both": [],
                "differences": []
            }
        }
        
        names1 = {inst['DBInstanceIdentifier']: inst for inst in instances1}
        names2 = {inst['DBInstanceIdentifier']: inst for inst in instances2}
        
        # Instancias solo en región 1
        for name in names1:
            if name not in names2:
                result["comparison"]["only_in_region1"].append({
                    "name": name,
                    "engine": names1[name].get('Engine'),
                    "instance_class": names1[name].get('DBInstanceClass')
                })
        
        # Instancias solo en región 2
        for name in names2:
            if name not in names1:
                result["comparison"]["only_in_region2"].append({
                    "name": name,
                    "engine": names2[name].get('Engine'),
                    "instance_class": names2[name].get('DBInstanceClass')
                })
        
        # Instancias en ambas regiones
        for name in names1:
            if name in names2:
                inst1 = names1[name]
                inst2 = names2[name]
                
                differences = {}
                for key in ['Engine', 'DBInstanceClass', 'AllocatedStorage', 'MultiAZ']:
                    val1 = inst1.get(key)
                    val2 = inst2.get(key)
                    if val1 != val2:
                        differences[key] = {"region1": val1, "region2": val2}
                
                if differences:
                    result["comparison"]["differences"].append({
                        "name": name,
                        "differences": differences
                    })
                else:
                    result["comparison"]["in_both"].append(name)
        
        return result


def main():
    parser = argparse.ArgumentParser(description='Compara instancias RDS entre regiones')
    parser.add_argument('--profile', help='AWS profile')
    parser.add_argument('--region1', default='us-east-1', help='Primera región')
    parser.add_argument('--region2', default='us-west-2', help='Segunda región')
    parser.add_argument('--instance', help='Nombre específico de instancia')
    parser.add_argument('-o', '--output', choices=['json', 'csv'], help='Formato de salida')
    
    args = parser.parse_args()
    
    comparator = RDSComparator(profile=args.profile)
    result = comparator.compare_instances(args.region1, args.region2, args.instance)
    
    if args.output == 'json':
        output = json.dumps(result, indent=2, default=str)
        print(output)
        if EXPORT_MANAGER_AVAILABLE:
            manager = ExportManager()
            manager.export_json(result, 'rds_comparison')
    else:
        print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
