#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP Service Accounts Multi-Project Reporter
Extrae, analiza y reporta service accounts de múltiples proyectos GCP

Uso:
    python gcp_sa_multi_project_reporter.py --projects=p1,p2,p3 --mode=all --output=json
    python gcp_sa_multi_project_reporter.py  # Usa config.json
"""

import argparse
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

# Agregar parent directory al path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from sa_config_loader import ConfigLoader
from sa_extractors import ServiceAccountExtractor
from sa_analyzers import RolesAndPermissionsAnalyzer, SecurityAnalyzer
from sa_report_generators import (
    JSONReportGenerator, CSVReportGenerator, ExcelReportGenerator, HTMLReportGenerator
)


class MultiProjectOrchestrator:
    """Orquesta extracción y análisis de múltiples proyectos."""
    
    def __init__(self, projects: List[str], config: Dict, debug: bool = False):
        self.projects = projects
        self.config = config
        self.debug = debug
        self.max_workers = config.get('parallel_workers', 5)
    
    def extract_all(self) -> Dict:
        """Extrae datos de todos los proyectos en paralelo."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._extract_project, proj): proj
                for proj in self.projects
            }
            
            for future in as_completed(futures):
                project = futures[future]
                try:
                    results[project] = future.result()
                    if self.debug:
                        print(f"✅ Proyecto extraído: {project}")
                except Exception as e:
                    results[project] = {'error': str(e)}
                    if self.debug:
                        print(f"❌ Error en {project}: {e}")
        
        return results
    
    def _extract_project(self, project_id: str) -> Dict:
        """Extrae datos de un proyecto específico."""
        extractor = ServiceAccountExtractor(project_id, self.debug)
        data = extractor.extract_all()
        
        # Analizar roles
        roles_analyzer = RolesAndPermissionsAnalyzer(self.debug)
        iam_bindings = data.get('iam_bindings', [])
        
        for sa in data.get('service_accounts', []):
            sa['roles_analysis'] = roles_analyzer.analyze_roles(sa['email'], iam_bindings)
            
            # Analizar seguridad
            security_analyzer = SecurityAnalyzer(self.debug)
            sa['security'] = security_analyzer.analyze(sa)
        
        return data
    
    def consolidate(self, data: Dict) -> Dict:
        """Consolida datos de múltiples proyectos."""
        return {
            'summary': self._generate_summary(data),
            'by_project': data,
            'cross_project_analysis': self._cross_project_analysis(data)
        }
    
    def _generate_summary(self, data: Dict) -> Dict:
        """Genera resumen general."""
        total_sa = sum(len(proj.get('service_accounts', []))
                      for proj in data.values() if isinstance(proj, dict))
        total_roles = sum(len(sa.get('roles_analysis', {}).get('iam_bindings', []))
                         for proj in data.values() if isinstance(proj, dict)
                         for sa in proj.get('service_accounts', []))
        
        return {
            'total_projects': len(data),
            'total_service_accounts': total_sa,
            'total_roles': total_roles,
            'generated_at': __import__('datetime').datetime.now().isoformat()
        }
    
    def _cross_project_analysis(self, data: Dict) -> Dict:
        """Análisis cruzado entre proyectos."""
        high_risk_sas = []
        
        for proj_name, proj_data in data.items():
            if isinstance(proj_data, dict) and 'error' not in proj_data:
                for sa in proj_data.get('service_accounts', []):
                    if sa.get('security', {}).get('risk_level') in ['HIGH', 'CRITICAL']:
                        high_risk_sas.append({
                            'project': proj_name,
                            'service_account': sa.get('email'),
                            'risk_level': sa.get('security', {}).get('risk_level')
                        })
        
        return {
            'high_risk_service_accounts': high_risk_sas,
            'projects_with_issues': len([p for p in data.values() 
                                        if isinstance(p, dict) and 'error' not in p])
        }


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='GCP Service Accounts Multi-Project Reporter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Usar configuración desde config.json
  python gcp_sa_multi_project_reporter.py
  
  # Override de proyectos
  python gcp_sa_multi_project_reporter.py --projects=p1,p2,p3
  
  # Modo seguridad con salida Excel
  python gcp_sa_multi_project_reporter.py --mode=security --output=excel
  
  # Debug mode
  python gcp_sa_multi_project_reporter.py --debug
        """
    )
    
    parser.add_argument('--projects', 
                       help='Proyectos a analizar (separados por coma)')
    parser.add_argument('--mode', 
                       choices=['all', 'security', 'compliance', 'usage'],
                       default='all',
                       help='Modo de reporte (default: all)')
    parser.add_argument('-o', '--output', 
                       choices=['json', 'csv', 'excel', 'html'],
                       default='json',
                       help='Formato de salida (default: json)')
    parser.add_argument('--config', 
                       default='config.json',
                       help='Ruta a config.json (default: config.json)')
    parser.add_argument('--output-dir', 
                       default='outcome',
                       help='Directorio de salida (default: outcome)')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='Modo debug')
    
    args = parser.parse_args()
    
    # Cargar configuración
    config_loader = ConfigLoader(args.config, args.debug)
    
    # Validar configuración
    is_valid, errors = config_loader.validate()
    if not is_valid and not args.projects:
        print("❌ Errores de configuración:")
        for error in errors:
            print(f"   - {error}")
        print("\n💡 Solución: Especifica --projects o configura config.json")
        sys.exit(1)
    
    # Obtener proyectos
    projects = args.projects.split(',') if args.projects else config_loader.get_projects()
    
    if not projects:
        print("❌ No hay proyectos para analizar")
        sys.exit(1)
    
    # Obtener configuración
    defaults = config_loader.get_defaults()
    
    print(f"🚀 Iniciando análisis de {len(projects)} proyecto(s)...")
    print(f"   Proyectos: {', '.join(projects)}")
    print(f"   Modo: {args.mode}")
    print(f"   Salida: {args.output}")
    
    # Extraer datos
    orchestrator = MultiProjectOrchestrator(projects, defaults, args.debug)
    extracted_data = orchestrator.extract_all()
    
    # Consolidar datos
    consolidated_data = orchestrator.consolidate(extracted_data)
    
    # Generar reporte
    print(f"\n📊 Generando reporte {args.output}...")
    
    generators = {
        'json': JSONReportGenerator,
        'csv': CSVReportGenerator,
        'excel': ExcelReportGenerator,
        'html': HTMLReportGenerator
    }
    
    generator_class = generators.get(args.output, JSONReportGenerator)
    generator = generator_class(args.output_dir, args.debug)
    report_path = generator.generate(consolidated_data)
    
    if report_path:
        print(f"✅ Reporte generado: {report_path}")
        print(f"\n📈 Resumen:")
        summary = consolidated_data.get('summary', {})
        print(f"   - Proyectos: {summary.get('total_projects', 0)}")
        print(f"   - Service Accounts: {summary.get('total_service_accounts', 0)}")
        print(f"   - Roles: {summary.get('total_roles', 0)}")
    else:
        print("❌ Error generando reporte")
        sys.exit(1)


if __name__ == '__main__':
    main()
