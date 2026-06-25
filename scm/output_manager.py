#!/usr/bin/env python3
"""
Output Manager - Módulo centralizado para gestionar ubicaciones de salida

Proporciona funciones consistentes para determinar y crear directorios de salida
respetando DEVSECOPS_OUTPUT_DIR y manteniendo estructura consistente.
"""

import os
from pathlib import Path
from typing import Optional

__version__ = "1.0.0"


class OutputManager:
    """Gestor centralizado de ubicaciones de salida."""
    
    # Estructura de directorios estándar
    STRUCTURE = {
        "root": "outcome",
        "platforms": {
            "azdo": "outcome/azdo",
            "gcp": "outcome/gcp",
            "aws": "outcome/aws",
            "terminal": "outcome/terminal",
            "dashboard": "outcome/dashboard",
        },
        "dashboard_history": "outcome/dashboard/history",
    }
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Inicializa el gestor de ubicaciones.
        
        Args:
            base_dir: Directorio base (si None, usa DEVSECOPS_OUTPUT_DIR o default)
        """
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            env_dir = os.getenv("DEVSECOPS_OUTPUT_DIR")
            if env_dir:
                self.base_dir = Path(env_dir)
            else:
                self.base_dir = Path("outcome")
        
        # Crear directorio base si no existe
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def get_output_dir(self, subdir: str = "") -> Path:
        """
        Obtiene el directorio de salida.
        
        Args:
            subdir: Subdirectorio adicional (ej: "azdo", "gcp", "dashboard")
            
        Returns:
            Path del directorio de salida
        """
        if subdir:
            output_path = self.base_dir / subdir
        else:
            output_path = self.base_dir
        
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    
    def get_platform_dir(self, platform: str) -> Path:
        """
        Obtiene el directorio de una plataforma.
        
        Args:
            platform: Nombre de la plataforma (azdo, gcp, aws, terminal)
            
        Returns:
            Path del directorio de la plataforma
        """
        platform = platform.lower()
        if platform not in self.STRUCTURE["platforms"]:
            raise ValueError(f"Plataforma no válida: {platform}")
        
        subdir = self.STRUCTURE["platforms"][platform]
        return self.get_output_dir(subdir)
    
    def get_dashboard_dir(self) -> Path:
        """
        Obtiene el directorio del dashboard.
        
        Returns:
            Path del directorio del dashboard
        """
        return self.get_output_dir(self.STRUCTURE["platforms"]["dashboard"])
    
    def get_dashboard_history_dir(self) -> Path:
        """
        Obtiene el directorio de histórico del dashboard.
        
        Returns:
            Path del directorio de histórico
        """
        return self.get_output_dir(self.STRUCTURE["dashboard_history"])
    
    def get_dashboard_history_date_dir(self, date_str: str = None) -> Path:
        """
        Obtiene el directorio de histórico por fecha.
        
        Args:
            date_str: Fecha en formato YYYY-MM-DD (si None, usa hoy)
            
        Returns:
            Path del directorio de histórico por fecha
        """
        if date_str is None:
            from datetime import date
            date_str = date.today().isoformat()
        
        history_dir = self.get_dashboard_history_dir()
        date_dir = history_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir
    
    def list_structure(self) -> dict:
        """
        Lista la estructura de directorios.
        
        Returns:
            Diccionario con la estructura
        """
        return {
            "base_dir": str(self.base_dir),
            "env_var": os.getenv("DEVSECOPS_OUTPUT_DIR"),
            "structure": self.STRUCTURE,
        }


# Instancia global
_global_manager = None


def get_global_manager(base_dir: Optional[str] = None) -> OutputManager:
    """
    Obtiene la instancia global del OutputManager.
    
    Args:
        base_dir: Directorio base (si None, usa DEVSECOPS_OUTPUT_DIR o default)
        
    Returns:
        Instancia de OutputManager
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = OutputManager(base_dir)
    return _global_manager


def get_output_dir(subdir: str = "") -> Path:
    """
    Función simplificada para obtener directorio de salida.
    
    Args:
        subdir: Subdirectorio adicional
        
    Returns:
        Path del directorio de salida
    """
    manager = get_global_manager()
    return manager.get_output_dir(subdir)


def get_platform_dir(platform: str) -> Path:
    """
    Función simplificada para obtener directorio de plataforma.
    
    Args:
        platform: Nombre de la plataforma (azdo, gcp, aws, terminal)
        
    Returns:
        Path del directorio de la plataforma
    """
    manager = get_global_manager()
    return manager.get_platform_dir(platform)


def get_dashboard_dir() -> Path:
    """
    Función simplificada para obtener directorio del dashboard.
    
    Returns:
        Path del directorio del dashboard
    """
    manager = get_global_manager()
    return manager.get_dashboard_dir()


def get_dashboard_history_dir() -> Path:
    """
    Función simplificada para obtener directorio de histórico del dashboard.
    
    Returns:
        Path del directorio de histórico
    """
    manager = get_global_manager()
    return manager.get_dashboard_history_dir()


def get_dashboard_history_date_dir(date_str: str = None) -> Path:
    """
    Función simplificada para obtener directorio de histórico por fecha.
    
    Args:
        date_str: Fecha en formato YYYY-MM-DD
        
    Returns:
        Path del directorio de histórico por fecha
    """
    manager = get_global_manager()
    return manager.get_dashboard_history_date_dir(date_str)


if __name__ == "__main__":
    # Ejemplo de uso
    print("=== Output Manager ===\n")
    
    manager = OutputManager()
    
    print("Estructura de directorios:")
    print(f"Base: {manager.base_dir}")
    print(f"DEVSECOPS_OUTPUT_DIR: {os.getenv('DEVSECOPS_OUTPUT_DIR', 'No configurado')}\n")
    
    print("Directorios disponibles:")
    print(f"Root: {manager.get_output_dir()}")
    print(f"AZDO: {manager.get_platform_dir('azdo')}")
    print(f"GCP: {manager.get_platform_dir('gcp')}")
    print(f"AWS: {manager.get_platform_dir('aws')}")
    print(f"Terminal: {manager.get_platform_dir('terminal')}")
    print(f"Dashboard: {manager.get_dashboard_dir()}")
    print(f"Dashboard History: {manager.get_dashboard_history_dir()}")
    print(f"Dashboard History (Hoy): {manager.get_dashboard_history_date_dir()}\n")
    
    print("Estructura completa:")
    import json
    print(json.dumps(manager.list_structure(), indent=2, default=str))
