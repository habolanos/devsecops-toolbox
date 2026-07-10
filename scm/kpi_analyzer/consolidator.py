#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Consolidator
Consolida datos de múltiples fuentes (AZDO, GCP, AWS, KPI) en un único dashboard
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import Dict, Optional, Any

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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


class HistoryManager:
    """Gestiona histórico de métricas (90 días)"""
    
    def __init__(self, history_dir: Optional[str] = None):
        if history_dir is None:
            output_dir = get_output_dir("outcome/kpi_analyzer")
            self.history_dir = output_dir / "history"
        else:
            self.history_dir = Path(history_dir)
        
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = 90
    
    def save_daily_snapshot(self, data: Dict[str, Any]):
        """Guarda snapshot diario"""
        today = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        
        day_dir = self.history_dir / today
        day_dir.mkdir(parents=True, exist_ok=True)
        
        data_file = day_dir / f"consolidation_{timestamp}.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Snapshot guardado: {data_file}")
        return data_file
    
    def get_historical_data(self, days: int = 30) -> Dict[str, Any]:
        """Obtiene datos históricos de los últimos N días"""
        historical = {}
        
        for day_dir in sorted(self.history_dir.iterdir())[-days:]:
            if day_dir.is_dir():
                for json_file in day_dir.glob("consolidation_*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            historical[json_file.stem] = json.load(f)
                    except Exception as e:
                        logger.warning(f"Error leyendo {json_file}: {e}")
        
        return historical


class DataConsolidator:
    """Consolida datos de múltiples fuentes"""
    
    def __init__(self, org: Optional[str] = None, project: Optional[str] = None, 
                 pat: Optional[str] = None, output_dir: Optional[str] = None):
        self.org = org
        self.project = project
        self.pat = pat
        
        if output_dir is None:
            self.output_dir = get_output_dir("outcome/kpi_analyzer")
        else:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.history_manager = HistoryManager()
        logger.info(f"Consolidator inicializado")
        logger.info(f"Directorio de salida: {self.output_dir}")
    
    def consolidate_all(self) -> Dict[str, Any]:
        """Consolida todos los datos disponibles"""
        try:
            if RICH_AVAILABLE and console:
                console.print("[bold cyan]🔄 Consolidando datos de múltiples fuentes...[/bold cyan]")
            
            consolidated = {
                "timestamp": datetime.now().isoformat(),
                "organization": self.org,
                "project": self.project,
                "sources": {}
            }
            
            # Consolidar datos AZDO
            if self.org and self.project and self.pat:
                consolidated["sources"]["azdo"] = self._consolidate_azdo_data()
            
            # Consolidar datos KPI
            consolidated["sources"]["kpi"] = self._consolidate_kpi_data()
            
            # Consolidar datos de salud
            consolidated["sources"]["health"] = self._consolidate_health_data()
            
            # Guardar histórico
            self.history_manager.save_daily_snapshot(consolidated)
            
            # Guardar consolidación
            self._save_consolidated_data(consolidated)
            
            logger.info("✅ Consolidación completada")
            return consolidated
        except Exception as e:
            logger.error(f"❌ Error en consolidación: {e}")
            raise
    
    def _consolidate_azdo_data(self) -> Dict[str, Any]:
        """Consolida datos de AZDO"""
        try:
            azdo_data = {
                "organization": self.org,
                "project": self.project,
                "metrics": {}
            }
            
            # Buscar archivos JSON de AZDO
            azdo_dir = self.output_dir.parent.parent / "azdo" / "outcome"
            
            if azdo_dir.exists():
                for json_file in azdo_dir.glob("*.json"):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            azdo_data["metrics"][json_file.stem] = data
                    except Exception as e:
                        logger.warning(f"Error leyendo {json_file}: {e}")
            
            logger.info(f"Datos AZDO consolidados: {len(azdo_data['metrics'])} métricas")
            return azdo_data
        except Exception as e:
            logger.error(f"Error consolidando AZDO: {e}")
            return {}
    
    def _consolidate_kpi_data(self) -> Dict[str, Any]:
        """Consolida datos de KPI"""
        try:
            kpi_data = {
                "metrics": {}
            }
            
            # Buscar archivos JSON de KPI
            for json_file in self.output_dir.glob("*.json"):
                if json_file.name != "consolidated_data.json":
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            kpi_data["metrics"][json_file.stem] = data
                    except Exception as e:
                        logger.warning(f"Error leyendo {json_file}: {e}")
            
            logger.info(f"Datos KPI consolidados: {len(kpi_data['metrics'])} métricas")
            return kpi_data
        except Exception as e:
            logger.error(f"Error consolidando KPI: {e}")
            return {}
    
    def _consolidate_health_data(self) -> Dict[str, Any]:
        """Consolida datos de salud del sistema"""
        try:
            health_data = {
                "health_score": 0,
                "status": "unknown",
                "components": {}
            }
            
            # Buscar health_score_dora.json
            health_file = self.output_dir / "health_score_dora.json"
            if health_file.exists():
                try:
                    with open(health_file, 'r', encoding='utf-8') as f:
                        health_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Error leyendo health score: {e}")
            
            logger.info(f"Datos de salud consolidados")
            return health_data
        except Exception as e:
            logger.error(f"Error consolidando health data: {e}")
            return {}
    
    def _save_consolidated_data(self, data: Dict[str, Any]) -> bool:
        """Guarda datos consolidados"""
        try:
            filepath = self.output_dir / "consolidated_data.json"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Datos consolidados guardados: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error guardando datos consolidados: {e}")
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de consolidación"""
        try:
            filepath = self.output_dir / "consolidated_data.json"
            
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return {
                    "timestamp": data.get("timestamp"),
                    "organization": data.get("organization"),
                    "project": data.get("project"),
                    "sources": list(data.get("sources", {}).keys()),
                    "metrics_count": sum(
                        len(source.get("metrics", {})) 
                        for source in data.get("sources", {}).values()
                    )
                }
            
            return {}
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return {}


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Consolidator")
    parser.add_argument("--org", help="Organización AZDO")
    parser.add_argument("--project", help="Proyecto AZDO")
    parser.add_argument("--pat", help="Personal Access Token")
    parser.add_argument("--output", help="Directorio de salida")
    
    args = parser.parse_args()
    
    consolidator = DataConsolidator(
        org=args.org,
        project=args.project,
        pat=args.pat,
        output_dir=args.output
    )
    
    consolidated = consolidator.consolidate_all()
    summary = consolidator.get_summary()
    
    if RICH_AVAILABLE and console:
        console.print("[green]✅ Consolidación completada[/green]")
        console.print(f"[dim]Resumen: {summary}[/dim]")
    else:
        print("✅ Consolidación completada")
        print(f"Resumen: {summary}")


if __name__ == "__main__":
    main()
