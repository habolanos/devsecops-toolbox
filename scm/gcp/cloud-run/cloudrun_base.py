#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloud Run Base Module

Módulo base para todas las herramientas Cloud Run.
Proporciona funcionalidad común y reutilizable.

Autor: Harold Adrian
"""

import subprocess
import json
import os
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

try:
    from rich.console import Console
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

try:
    from utils import get_output_dir
except ImportError:
    def get_output_dir(default="."):
        env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = Path(env)
            p.mkdir(parents=True, exist_ok=True)
            return p
        p = Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p


class CloudRunBase:
    """Clase base para herramientas Cloud Run"""
    
    def __init__(self, project: str, region: str = "all", debug: bool = False, tz: str = "America/Mazatlan"):
        self.project = project
        self.region = region
        self.debug = debug
        self.tz = tz
        self.console = Console() if RICH_AVAILABLE else None
        self.gcp_client = None
    
    def run_gcloud_command(self, command: str) -> Optional[List[Dict]]:
        """
        Ejecuta comando gcloud y retorna JSON.
        
        Args:
            command: Comando gcloud a ejecutar
        
        Returns:
            Lista de diccionarios con resultado o None
        """
        full_command = f"{command} --project={self.project} --format=json"
        
        if self.debug and RICH_AVAILABLE:
            self.console.print(f"[dim]DEBUG: {full_command}[/dim]")
        
        try:
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                if self.debug:
                    error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                    if RICH_AVAILABLE:
                        self.console.print(f"[red]Error: {error_msg}[/red]")
                    else:
                        print(f"Error: {error_msg}")
                return []
            
            if result.stdout.strip():
                return json.loads(result.stdout)
            return []
        
        except subprocess.TimeoutExpired:
            if RICH_AVAILABLE:
                self.console.print(f"[yellow]Timeout ejecutando: {command}[/yellow]")
            return []
        except json.JSONDecodeError:
            if self.debug:
                if RICH_AVAILABLE:
                    self.console.print(f"[yellow]No JSON output para: {command}[/yellow]")
            return []
        except Exception as e:
            if self.debug:
                if RICH_AVAILABLE:
                    self.console.print(f"[red]Exception: {e}[/red]")
                else:
                    print(f"Exception: {e}")
            return []
    
    def validate_connection(self) -> bool:
        """Valida conexión a GCP"""
        if RICH_AVAILABLE:
            with self.console.status("[bold blue]Validando conexión a GCP...[/bold blue]"):
                result = self.run_gcloud_command("gcloud run services list")
                return result is not None
        else:
            result = self.run_gcloud_command("gcloud run services list")
            return result is not None
    
    def export_results(self, data: Dict, format: str = "json", filename_prefix: str = "cloudrun_export") -> str:
        """
        Exporta resultados usando ExportManager.
        
        Args:
            data: Datos a exportar
            format: Formato (json, csv, excel)
            filename_prefix: Prefijo del archivo
        
        Returns:
            Ruta del archivo exportado
        """
        if EXPORT_MANAGER_AVAILABLE:
            try:
                exporter = ExportManager(
                    tool_name=self.__class__.__name__,
                    version="1.0.0"
                )
                
                if format == "json":
                    return exporter.to_json(data)
                elif format == "csv":
                    return exporter.to_csv(data)
                elif format == "excel":
                    return exporter.to_excel(data)
            except Exception as e:
                if self.debug:
                    if RICH_AVAILABLE:
                        self.console.print(f"[yellow]ExportManager error: {e}[/yellow]")
                return self._export_fallback(data, format, filename_prefix)
        
        return self._export_fallback(data, format, filename_prefix)
    
    def _export_fallback(self, data: Dict, format: str, filename_prefix: str) -> str:
        """Fallback si ExportManager no está disponible"""
        import csv
        
        output_dir = Path(str(get_output_dir("outcome")))
        output_dir.mkdir(exist_ok=True)
        
        try:
            local_tz = ZoneInfo(self.tz)
        except Exception:
            local_tz = timezone.utc
        
        timestamp = datetime.now(local_tz).strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            filename = output_dir / f"{filename_prefix}_{self.project}_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        
        elif format == "csv":
            filename = output_dir / f"{filename_prefix}_{self.project}_{timestamp}.csv"
            if isinstance(data, list) and len(data) > 0:
                headers = list(data[0].keys())
                with open(filename, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(data)
            else:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("No data to export")
        
        elif format == "excel":
            try:
                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment
                
                filename = output_dir / f"{filename_prefix}_{self.project}_{timestamp}.xlsx"
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Data"
                
                if isinstance(data, list) and len(data) > 0:
                    headers = list(data[0].keys())
                    ws.append(headers)
                    for row in data:
                        ws.append([row.get(h, "") for h in headers])
                
                wb.save(filename)
            except ImportError:
                filename = output_dir / f"{filename_prefix}_{self.project}_{timestamp}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
        
        return str(filename)
    
    def print_header(self, title: str, subtitle: str = "", description: str = ""):
        """Imprime encabezado formateado"""
        if RICH_AVAILABLE:
            header_text = f"[bold cyan]{title}[/bold cyan]"
            if subtitle:
                header_text += f"\n[dim]{subtitle}[/dim]"
            if description:
                header_text += f"\n[yellow]{description}[/yellow]"
            
            self.console.print(Panel.fit(
                header_text,
                border_style="cyan"
            ))
        else:
            print(f"\n{'='*60}")
            print(f"{title}")
            if subtitle:
                print(f"{subtitle}")
            if description:
                print(f"{description}")
            print(f"{'='*60}\n")
    
    def print_success(self, message: str):
        """Imprime mensaje de éxito"""
        if RICH_AVAILABLE:
            self.console.print(f"[green]✅ {message}[/green]")
        else:
            print(f"✓ {message}")
    
    def print_error(self, message: str):
        """Imprime mensaje de error"""
        if RICH_AVAILABLE:
            self.console.print(f"[red]❌ {message}[/red]")
        else:
            print(f"✗ {message}")
    
    def print_warning(self, message: str):
        """Imprime mensaje de advertencia"""
        if RICH_AVAILABLE:
            self.console.print(f"[yellow]⚠️  {message}[/yellow]")
        else:
            print(f"! {message}")
    
    def print_info(self, message: str):
        """Imprime mensaje de información"""
        if RICH_AVAILABLE:
            self.console.print(f"[blue]ℹ️  {message}[/blue]")
        else:
            print(f"i {message}")
