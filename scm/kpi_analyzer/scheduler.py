#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Scheduler
Planifica ejecución automática de análisis de KPI
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging
import schedule
import time

try:
    from rich.console import Console
    from rich.table import Table
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


class AutoScheduler:
    """Planifica ejecución automática de análisis"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, output_dir: Optional[str] = None):
        self.config = config or {}
        self.output_dir = Path(output_dir) if output_dir else get_output_dir("outcome/kpi_analyzer")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.jobs = []
        self.schedule_file = self.output_dir / "schedule.json"
        logger.info("Auto Scheduler inicializado")
    
    def schedule_daily(self, time_str: str = "09:00", job_name: str = "daily_analysis") -> bool:
        """Planifica ejecución diaria"""
        try:
            job = schedule.every().day.at(time_str).do(self._execute_job, job_name=job_name)
            self.jobs.append({
                "name": job_name,
                "frequency": "daily",
                "time": time_str,
                "next_run": str(job.next_run),
                "created_at": datetime.now().isoformat()
            })
            
            logger.info(f"✅ Job diario programado: {job_name} a las {time_str}")
            if RICH_AVAILABLE and console:
                console.print(f"[green]✅ Job diario programado: {job_name} a las {time_str}[/green]")
            
            self._save_schedule()
            return True
        except Exception as e:
            logger.error(f"Error programando job diario: {e}")
            return False
    
    def schedule_weekly(self, day: str = "monday", time_str: str = "09:00", 
                       job_name: str = "weekly_analysis") -> bool:
        """Planifica ejecución semanal"""
        try:
            days_map = {
                "monday": schedule.every().monday,
                "tuesday": schedule.every().tuesday,
                "wednesday": schedule.every().wednesday,
                "thursday": schedule.every().thursday,
                "friday": schedule.every().friday,
                "saturday": schedule.every().saturday,
                "sunday": schedule.every().sunday
            }
            
            day_scheduler = days_map.get(day.lower())
            if not day_scheduler:
                raise ValueError(f"Día inválido: {day}")
            
            job = day_scheduler.at(time_str).do(self._execute_job, job_name=job_name)
            self.jobs.append({
                "name": job_name,
                "frequency": "weekly",
                "day": day,
                "time": time_str,
                "next_run": str(job.next_run),
                "created_at": datetime.now().isoformat()
            })
            
            logger.info(f"✅ Job semanal programado: {job_name} cada {day} a las {time_str}")
            if RICH_AVAILABLE and console:
                console.print(f"[green]✅ Job semanal programado: {job_name} cada {day} a las {time_str}[/green]")
            
            self._save_schedule()
            return True
        except Exception as e:
            logger.error(f"Error programando job semanal: {e}")
            return False
    
    def schedule_hourly(self, job_name: str = "hourly_analysis") -> bool:
        """Planifica ejecución cada hora"""
        try:
            job = schedule.every().hour.do(self._execute_job, job_name=job_name)
            self.jobs.append({
                "name": job_name,
                "frequency": "hourly",
                "next_run": str(job.next_run),
                "created_at": datetime.now().isoformat()
            })
            
            logger.info(f"✅ Job horario programado: {job_name}")
            if RICH_AVAILABLE and console:
                console.print(f"[green]✅ Job horario programado: {job_name}[/green]")
            
            self._save_schedule()
            return True
        except Exception as e:
            logger.error(f"Error programando job horario: {e}")
            return False
    
    def schedule_on_demand(self, job_name: str = "on_demand_analysis") -> bool:
        """Registra ejecución bajo demanda"""
        try:
            self.jobs.append({
                "name": job_name,
                "frequency": "on_demand",
                "executed_at": datetime.now().isoformat()
            })
            
            logger.info(f"✅ Job bajo demanda registrado: {job_name}")
            self._save_schedule()
            return True
        except Exception as e:
            logger.error(f"Error registrando job bajo demanda: {e}")
            return False
    
    def run_pending(self):
        """Ejecuta jobs pendientes"""
        try:
            schedule.run_pending()
            logger.info("Jobs pendientes ejecutados")
        except Exception as e:
            logger.error(f"Error ejecutando jobs pendientes: {e}")
    
    def run_all(self):
        """Ejecuta todos los jobs"""
        try:
            schedule.run_all()
            logger.info("Todos los jobs ejecutados")
        except Exception as e:
            logger.error(f"Error ejecutando todos los jobs: {e}")
    
    def start_scheduler(self, blocking: bool = False):
        """Inicia el scheduler"""
        try:
            logger.info("Iniciando scheduler...")
            
            if blocking:
                while True:
                    self.run_pending()
                    time.sleep(60)
            else:
                logger.info("Scheduler iniciado en modo no-bloqueante")
        except KeyboardInterrupt:
            logger.info("Scheduler detenido")
        except Exception as e:
            logger.error(f"Error en scheduler: {e}")
    
    def get_schedule(self) -> list:
        """Obtiene lista de jobs programados"""
        return self.jobs
    
    def clear_schedule(self) -> bool:
        """Limpia todos los jobs"""
        try:
            schedule.clear()
            self.jobs = []
            self._save_schedule()
            logger.info("Schedule limpiado")
            return True
        except Exception as e:
            logger.error(f"Error limpiando schedule: {e}")
            return False
    
    def display_schedule(self):
        """Muestra schedule programado"""
        if RICH_AVAILABLE and console:
            table = Table(title="📅 Scheduled Jobs")
            table.add_column("Job Name", style="cyan")
            table.add_column("Frequency", style="magenta")
            table.add_column("Time/Day", style="yellow")
            table.add_column("Next Run", style="green")
            
            for job in self.jobs:
                table.add_row(
                    job.get("name", ""),
                    job.get("frequency", ""),
                    f"{job.get('day', '')} {job.get('time', '')}".strip(),
                    job.get("next_run", "")
                )
            
            console.print(table)
        else:
            print("\n📅 Scheduled Jobs")
            print("=" * 80)
            for job in self.jobs:
                print(f"\nJob: {job.get('name', '')}")
                print(f"  Frequency: {job.get('frequency', '')}")
                print(f"  Time/Day: {job.get('day', '')} {job.get('time', '')}".strip())
                print(f"  Next Run: {job.get('next_run', '')}")
    
    def _execute_job(self, job_name: str):
        """Ejecuta un job"""
        try:
            logger.info(f"Ejecutando job: {job_name}")
            
            # Aquí se ejecutaría el análisis real
            # Por ahora, solo registramos la ejecución
            execution_log = {
                "job_name": job_name,
                "executed_at": datetime.now().isoformat(),
                "status": "completed"
            }
            
            log_file = self.output_dir / f"execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(execution_log, f, indent=2)
            
            logger.info(f"✅ Job completado: {job_name}")
        except Exception as e:
            logger.error(f"Error ejecutando job: {e}")
    
    def _save_schedule(self):
        """Guarda schedule a archivo"""
        try:
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump(self.jobs, f, indent=2, ensure_ascii=False)
            logger.info(f"Schedule guardado: {self.schedule_file}")
        except Exception as e:
            logger.error(f"Error guardando schedule: {e}")


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto Scheduler")
    parser.add_argument("--action", choices=["schedule", "run", "list", "clear"], 
                       default="list", help="Acción a realizar")
    parser.add_argument("--frequency", choices=["daily", "weekly", "hourly", "on_demand"],
                       default="daily", help="Frecuencia de ejecución")
    parser.add_argument("--time", default="09:00", help="Hora de ejecución (HH:MM)")
    parser.add_argument("--day", default="monday", help="Día de la semana (para weekly)")
    parser.add_argument("--output", help="Directorio de salida")
    
    args = parser.parse_args()
    
    scheduler = AutoScheduler(output_dir=args.output)
    
    if args.action == "schedule":
        if args.frequency == "daily":
            scheduler.schedule_daily(time_str=args.time)
        elif args.frequency == "weekly":
            scheduler.schedule_weekly(day=args.day, time_str=args.time)
        elif args.frequency == "hourly":
            scheduler.schedule_hourly()
        elif args.frequency == "on_demand":
            scheduler.schedule_on_demand()
    
    elif args.action == "run":
        scheduler.run_all()
    
    elif args.action == "list":
        scheduler.display_schedule()
    
    elif args.action == "clear":
        scheduler.clear_schedule()


if __name__ == "__main__":
    main()
