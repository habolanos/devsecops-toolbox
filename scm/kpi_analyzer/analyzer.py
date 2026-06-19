#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KPI Analyzer Engine — DevSecOps Toolbox
Motor de análisis de KPIs desde salidas JSON

Version: 1.0.0
Author: Harold Adrian
"""

import json
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    from utils import get_output_dir
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    def get_output_dir(default="."):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = _Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p


class KPIAnalyzer:
    """Motor de análisis de KPIs"""
    
    def __init__(self, schema_path: Optional[Path] = None):
        """
        Inicializa el analizador de KPIs.
        
        Args:
            schema_path: Ruta al archivo kpi_schema.yaml
        """
        if schema_path is None:
            schema_path = Path(__file__).parent / "kpi_schema.yaml"
        
        if YAML_AVAILABLE:
            with open(schema_path, 'r', encoding='utf-8') as f:
                self.schema = yaml.safe_load(f)
        else:
            # Fallback: use empty schema if yaml is not available
            self.schema = {}
        
        self.output_dir = get_output_dir("outcome")
        self.json_cache = {}
    
    def discover_json_files(self, platform: Optional[str] = None) -> List[Path]:
        """
        Descubre archivos JSON en el directorio de salida.
        
        Args:
            platform: Filtrar por plataforma (gcp, azdo, aws, terminal)
            
        Returns:
            Lista de rutas a archivos JSON
        """
        patterns = []
        if platform:
            patterns.append(f"{platform}_*.json")
        else:
            patterns.extend(["gcp_*.json", "azdo_*.json", "aws_*.json", "*.json"])
        
        json_files = []
        for pattern in patterns:
            json_files.extend(self.output_dir.glob(pattern))
        
        # Filter out config files
        exclude_patterns = ['config', 'webhook', 'settings', 'package', 'tsconfig', 'eslint']
        json_files = [f for f in json_files if not any(ex in f.name.lower() for ex in exclude_patterns)]
        
        return sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def load_json(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """
        Carga un archivo JSON con caché.
        
        Args:
            filepath: Ruta al archivo JSON
            
        Returns:
            Contenido del JSON o None si falla
        """
        cache_key = str(filepath)
        if cache_key in self.json_cache:
            return self.json_cache[cache_key]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.json_cache[cache_key] = data
                return data
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return None
    
    def extract_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        Extrae un campo de un JSON usando notación de punto.
        
        Args:
            data: Diccionario JSON
            field_path: Ruta del campo (ej: "deployments[].status")
            
        Returns:
            Valor del campo o None
        """
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if '[]' in part:
                # Array field
                key = part.replace('[]', '')
                if isinstance(current, dict) and key in current:
                    current = current[key]
                    if not isinstance(current, list):
                        return None
                else:
                    return None
            else:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif isinstance(current, list):
                    # Apply to all items in list
                    results = []
                    for item in current:
                        if isinstance(item, dict) and part in item:
                            results.append(item[part])
                    current = results if results else None
                else:
                    return None
        
        return current
    
    def calculate_kpi(self, kpi_def: Dict[str, Any]) -> Optional[float]:
        """
        Calcula el valor de un KPI basándose en su definición.
        
        Args:
            kpi_def: Definición del KPI desde el schema
            
        Returns:
            Valor calculado del KPI o None
        """
        kpi_id = kpi_def.get('id')
        sources = kpi_def.get('sources', [])
        formula = kpi_def.get('formula', '')
        
        # Collect data from sources
        source_data = []
        for source in sources:
            script_name = source.get('script', '')
            fields = source.get('fields', [])
            
            # Find matching JSON files
            json_files = self.discover_json_files()
            matching_files = [f for f in json_files if script_name.split('/')[-1].replace('.py', '') in f.name]
            
            if not matching_files:
                continue
            
            # Use most recent file
            latest_file = matching_files[0]
            data = self.load_json(latest_file)
            if not data:
                continue
            
            # Extract fields
            for field_path in fields:
                value = self.extract_field(data, field_path)
                if value is not None:
                    source_data.append({'field': field_path, 'value': value, 'source': latest_file.name})
        
        if not source_data:
            return None
        
        # Apply formula (simplified implementation)
        return self._apply_formula(formula, source_data, kpi_id)
    
    def _apply_formula(self, formula: str, source_data: List[Dict], kpi_id: str) -> Optional[float]:
        """
        Aplica la fórmula del KPI a los datos recolectados.
        
        Args:
            formula: Fórmula del KPI
            source_data: Datos de fuentes
            kpi_id: ID del KPI
            
        Returns:
            Valor calculado
        """
        # Simplified formula application - in production, use a proper expression parser
        
        # Deployment Frequency (ec_001)
        if kpi_id == "ec_001":
            # count(deployments where status='success' and environment='prod' in last 7 days) / 7
            deployments = []
            for item in source_data:
                if isinstance(item['value'], list):
                    deployments.extend(item['value'])
            
            if not deployments:
                return 0.0
            
            # Filter successful prod deployments in last 7 days
            now = datetime.now()
            seven_days_ago = now - timedelta(days=7)
            success_count = 0
            
            for dep in deployments:
                if isinstance(dep, dict):
                    status = dep.get('status', '')
                    env = dep.get('environment', '')
                    timestamp_str = dep.get('timestamp', '')
                    
                    if status == 'success' and 'prod' in env.lower():
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            if timestamp >= seven_days_ago:
                                success_count += 1
                        except:
                            pass
            
            return success_count / 7.0
        
        # Change Failure Rate (ec_002)
        elif kpi_id == "ec_002":
            # count(deployments where status='failed' or rollback=true) / count(total_deployments) * 100
            deployments = []
            for item in source_data:
                if isinstance(item['value'], list):
                    deployments.extend(item['value'])
            
            if not deployments:
                return 0.0
            
            failed_count = sum(1 for d in deployments if isinstance(d, dict) and 
                             (d.get('status') == 'failed' or d.get('rollback') == True))
            
            return (failed_count / len(deployments) * 100) if deployments else 0.0
        
        # MTTR (conf_001)
        elif kpi_id == "conf_001":
            # avg(time_resolved - time_detected)
            mttr_values = []
            for item in source_data:
                value = item['value']
                if isinstance(value, (int, float)):
                    mttr_values.append(value)
                elif isinstance(value, list):
                    mttr_values.extend([v for v in value if isinstance(v, (int, float))])
            
            return sum(mttr_values) / len(mttr_values) if mttr_values else 0.0
        
        # Availability (conf_002)
        elif kpi_id == "conf_002":
            # sum(uptime_minutes) / sum(total_minutes) * 100
            healthy_count = 0
            total_count = 0
            
            for item in source_data:
                value = item['value']
                if isinstance(value, list):
                    for v in value:
                        if isinstance(v, (int, float)):
                            total_count += 1
                            if v > 0:
                                healthy_count += 1
            
            return (healthy_count / total_count * 100) if total_count > 0 else 0.0
        
        # MFA Coverage (seg_001)
        elif kpi_id == "seg_001":
            # count(users where mfa_enabled=true) / count(total_users) * 100
            users = []
            for item in source_data:
                if isinstance(item['value'], list):
                    users.extend(item['value'])
            
            if not users:
                return 0.0
            
            mfa_enabled_count = sum(1 for u in users if isinstance(u, dict) and u.get('mfa_enabled') == True)
            
            return (mfa_enabled_count / len(users) * 100) if users else 0.0
        
        # Certificate Expiry Risk (seg_002)
        elif kpi_id == "seg_002":
            # count(certs where days_to_expiry < 30) / count(total_certs) * 100
            certs = []
            for item in source_data:
                if isinstance(item['value'], list):
                    certs.extend(item['value'])
            
            if not certs:
                return 0.0
            
            expiring_count = sum(1 for c in certs if isinstance(c, (int, float)) and c < 30)
            
            return (expiring_count / len(certs) * 100) if certs else 0.0
        
        # Monitoring Coverage (obs_001)
        elif kpi_id == "obs_001":
            # count(services where monitoring_enabled=true) / count(total_services) * 100
            services = []
            for item in source_data:
                if isinstance(item['value'], list):
                    services.extend(item['value'])
            
            if not services:
                return 0.0
            
            monitored_count = sum(1 for s in services if isinstance(s, dict) and s.get('status') in ['healthy', 'running', 'active'])
            
            return (monitored_count / len(services) * 100) if services else 0.0
        
        # Policy Adherence (cump_001)
        elif kpi_id == "cump_001":
            # count(resources where compliant=true) / count(total_resources) * 100
            resources = []
            for item in source_data:
                if isinstance(item['value'], list):
                    resources.extend(item['value'])
            
            if not resources:
                return 0.0
            
            compliant_count = sum(1 for r in resources if isinstance(r, dict) and r.get('compliant') == True)
            
            return (compliant_count / len(resources) * 100) if resources else 0.0
        
        # Resource Utilization (efic_001)
        elif kpi_id == "efic_001":
            # avg(used / allocated) * 100
            utilization_values = []
            for item in source_data:
                value = item['value']
                if isinstance(value, (int, float)):
                    utilization_values.append(value)
                elif isinstance(value, list):
                    utilization_values.extend([v for v in value if isinstance(v, (int, float))])
            
            return sum(utilization_values) / len(utilization_values) if utilization_values else 0.0
        
        # Default: try to extract numeric values and average
        numeric_values = []
        for item in source_data:
            value = item['value']
            if isinstance(value, (int, float)):
                numeric_values.append(value)
            elif isinstance(value, list):
                numeric_values.extend([v for v in value if isinstance(v, (int, float))])
        
        return sum(numeric_values) / len(numeric_values) if numeric_values else 0.0
    
    def analyze_all_kpis(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """
        Analiza todos los KPIs definidos en el schema.
        
        Args:
            platform: Filtrar por plataforma
            
        Returns:
            Diccionario con resultados de KPIs
        """
        results = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "platform": platform or "all",
                "analyzer_version": "1.0.0"
            },
            "dimensions": {},
            "kpis": []
        }
        
        for dimension_name, dimension_data in self.schema.items():
            if dimension_name in ['metadata', 'version']:
                continue
            
            dimension_results = {
                "name": dimension_name,
                "weight": dimension_data.get('weight', 0.0),
                "kpis": []
            }
            
            for kpi_def in dimension_data.get('kpis', []):
                kpi_value = self.calculate_kpi(kpi_def)
                
                kpi_result = {
                    "id": kpi_def.get('id'),
                    "name": kpi_def.get('name'),
                    "value": kpi_value,
                    "unit": kpi_def.get('unit'),
                    "benchmarks": kpi_def.get('benchmarks', {}),
                    "frameworks": kpi_def.get('frameworks', []),
                    "maturity_level_required": kpi_def.get('maturity_level_required', 0)
                }
                
                dimension_results["kpis"].append(kpi_result)
                results["kpis"].append(kpi_result)
            
            results["dimensions"][dimension_name] = dimension_results
        
        return results
