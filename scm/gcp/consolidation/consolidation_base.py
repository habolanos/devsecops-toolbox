#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infrastructure Consolidation Base Module

Módulo base para consolidación de infraestructura GCP.

Autor: Harold Adrian
"""

import subprocess
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


def run_gcloud_command(command: str, debug: bool = False) -> Optional[List[Dict]]:
    """Ejecuta un comando gcloud."""
    try:
        if debug:
            print(f"[DEBUG] {command}")
        
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            return None
        
        if not result.stdout.strip():
            return []
        
        return json.loads(result.stdout)
    except:
        return None


class LoadBalancerExtractor:
    """Extrae datos de Load Balancers."""
    
    def __init__(self, project_id: str, debug: bool = False):
        self.project_id = project_id
        self.debug = debug
    
    def extract_all(self) -> Dict:
        """Extrae todos los datos de LB."""
        return {
            'forwarding_rules': self.get_forwarding_rules(),
            'backend_services': self.get_backend_services(),
            'url_maps': self.get_url_maps(),
            'health_checks': self.get_health_checks(),
            'ssl_certificates': self.get_ssl_certificates(),
            'security_policies': self.get_security_policies(),
            'network_endpoint_groups': self.get_negs()
        }
    
    def get_forwarding_rules(self) -> List[Dict]:
        """Obtiene forwarding rules."""
        cmd = f'gcloud compute forwarding-rules list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_backend_services(self) -> List[Dict]:
        """Obtiene backend services."""
        cmd = f'gcloud compute backend-services list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_url_maps(self) -> List[Dict]:
        """Obtiene URL maps."""
        cmd = f'gcloud compute url-maps list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_health_checks(self) -> List[Dict]:
        """Obtiene health checks."""
        cmd = f'gcloud compute health-checks list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_ssl_certificates(self) -> List[Dict]:
        """Obtiene SSL certificates."""
        cmd = f'gcloud compute ssl-certificates list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_security_policies(self) -> List[Dict]:
        """Obtiene security policies."""
        cmd = f'gcloud compute security-policies list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []
    
    def get_negs(self) -> List[Dict]:
        """Obtiene Network Endpoint Groups."""
        cmd = f'gcloud compute network-endpoint-groups list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []


class CloudRunExtractor:
    """Extrae datos de Cloud Run."""
    
    def __init__(self, project_id: str, debug: bool = False):
        self.project_id = project_id
        self.debug = debug
    
    def extract_all(self) -> Dict:
        """Extrae todos los datos de Cloud Run."""
        return {
            'services': self.get_services()
        }
    
    def get_services(self) -> List[Dict]:
        """Obtiene servicios Cloud Run."""
        cmd = f'gcloud run services list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []


class CloudFunctionsExtractor:
    """Extrae datos de Cloud Functions."""
    
    def __init__(self, project_id: str, debug: bool = False):
        self.project_id = project_id
        self.debug = debug
    
    def extract_all(self) -> Dict:
        """Extrae todos los datos de Cloud Functions."""
        return {
            'functions': self.get_functions()
        }
    
    def get_functions(self) -> List[Dict]:
        """Obtiene funciones Cloud Functions."""
        cmd = f'gcloud functions list --project={self.project_id} --format=json'
        return run_gcloud_command(cmd, self.debug) or []


class RelationshipMapper:
    """Mapea relaciones entre componentes."""
    
    def __init__(self, lb_data: Dict, cr_data: Dict, cf_data: Dict):
        self.lb_data = lb_data
        self.cr_data = cr_data
        self.cf_data = cf_data
    
    def map_all_relationships(self) -> Dict:
        """Mapea todas las relaciones."""
        return {
            'lb_to_cloud_run': self.map_lb_to_cloud_run(),
            'lb_to_cloud_functions': self.map_lb_to_cloud_functions(),
            'orphaned_cloud_run': self.find_orphaned_cloud_run(),
            'orphaned_cloud_functions': self.find_orphaned_cloud_functions()
        }
    
    def map_lb_to_cloud_run(self) -> List[Dict]:
        """Mapea Load Balancers a Cloud Run."""
        relationships = []
        
        backend_services = self.lb_data.get('backend_services', [])
        cr_services = {s.get('name'): s for s in self.cr_data.get('services', [])}
        
        for bs in backend_services:
            for backend in bs.get('backends', []):
                group_url = backend.get('group', '')
                
                # Buscar Cloud Run service en NEGs
                for neg in self.lb_data.get('network_endpoint_groups', []):
                    if 'cloudrun' in neg.get('name', '').lower():
                        for cr_name, cr_service in cr_services.items():
                            relationships.append({
                                'lb_name': self._extract_name(bs.get('name', '')),
                                'backend_service': bs.get('name'),
                                'cloud_run_service': cr_name,
                                'region': cr_service.get('location', 'N/A'),
                                'status': 'MAPPED'
                            })
        
        return relationships
    
    def map_lb_to_cloud_functions(self) -> List[Dict]:
        """Mapea Load Balancers a Cloud Functions."""
        relationships = []
        
        backend_services = self.lb_data.get('backend_services', [])
        cf_functions = {f.get('name'): f for f in self.cf_data.get('functions', [])}
        
        for bs in backend_services:
            for backend in bs.get('backends', []):
                group_url = backend.get('group', '')
                
                # Buscar Cloud Functions en NEGs
                for neg in self.lb_data.get('network_endpoint_groups', []):
                    if 'cloudfunctions' in neg.get('name', '').lower():
                        for cf_name, cf_func in cf_functions.items():
                            relationships.append({
                                'lb_name': self._extract_name(bs.get('name', '')),
                                'backend_service': bs.get('name'),
                                'cloud_function': cf_name,
                                'region': cf_func.get('serviceConfig', {}).get('region', 'N/A'),
                                'status': 'MAPPED'
                            })
        
        return relationships
    
    def find_orphaned_cloud_run(self) -> List[Dict]:
        """Encuentra Cloud Run sin LB."""
        mapped_services = {
            rel['cloud_run_service'] 
            for rel in self.map_lb_to_cloud_run()
        }
        
        return [
            s for s in self.cr_data.get('services', [])
            if s.get('name') not in mapped_services
        ]
    
    def find_orphaned_cloud_functions(self) -> List[Dict]:
        """Encuentra Cloud Functions sin LB."""
        mapped_functions = {
            rel['cloud_function'] 
            for rel in self.map_lb_to_cloud_functions()
        }
        
        return [
            f for f in self.cf_data.get('functions', [])
            if f.get('name') not in mapped_functions
        ]
    
    @staticmethod
    def _extract_name(full_name: str) -> str:
        """Extrae nombre de una URL."""
        return full_name.split('/')[-1] if full_name else 'N/A'
