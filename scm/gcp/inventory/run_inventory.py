#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Inventario GKE + Cloud SQL - Launcher

Ejecuta el pipeline completo de inventario:
  1. generar-inventario-csv.py  → genera CSVs por proyecto (Rich UI)
  2. generar-inventario-csv-combinar-a-excel.py → consolida en Excel

Uso:
    python run_inventory.py [--skip-csv]
"""

import subprocess
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.box import HEAVY
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

SCRIPT_DIR = Path(__file__).parent.resolve()


def run_step_rich(console: Console, desc: str, cmd: list, cwd: str) -> bool:
    with console.status(f"[bold cyan]⏳ {desc}[/bold cyan]", spinner="dots"):
        result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        console.print(f"[red]❌ Error en: {desc} (código {result.returncode})[/red]")
        return False
    console.print(f"[green]✅ {desc} completado.[/green]")
    return True


def run_step_fallback(desc: str, cmd: list, cwd: str) -> bool:
    print(f"\n{'='*60}")
    print(f"  {desc}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\n❌ Error en: {desc} (código {result.returncode})")
        return False
    print(f"✅ {desc} completado.")
    return True


def main():
    skip_csv = "--skip-csv" in sys.argv

    if RICH_AVAILABLE:
        console = Console()
        console.print(Panel(
            Text.assemble(
                ("📋 Inventario GKE + Cloud SQL\n\n", "bold white"),
                ("Pipeline completo de inventario:\n", "dim"),
                ("  1. CSVs por proyecto (Rich UI)\n", "cyan"),
                ("  2. Consolidación en Excel\n", "cyan"),
            ),
            border_style="cyan", box=HEAVY, padding=(1, 2), expand=False,
        ))
    else:
        print("📋 Inventario GKE + Cloud SQL - Launcher")

    if not skip_csv:
        csv_script = SCRIPT_DIR / "generar-inventario-csv.py"
        if not csv_script.exists():
            # Fallback al script bash si existe
            bash_script = SCRIPT_DIR / "generar-inventario-csv.sh"
            if bash_script.exists():
                csv_script = bash_script
                cmd = ["bash", str(csv_script)]
            else:
                print(f"❌ No se encontró: generar-inventario-csv.py ni .sh")
                sys.exit(1)
        else:
            cmd = [sys.executable, str(csv_script)]
            # Pasar argumentos extra (excepto --skip-csv)
            extra_args = [a for a in sys.argv[1:] if a != "--skip-csv"]
            cmd.extend(extra_args)

        if RICH_AVAILABLE:
            if not run_step_rich(console, "Paso 1/2 – Generando CSVs de inventario", cmd, str(SCRIPT_DIR)):
                sys.exit(1)
        else:
            if not run_step_fallback("Paso 1/2 – Generando CSVs de inventario", cmd, str(SCRIPT_DIR)):
                sys.exit(1)

    excel_script = SCRIPT_DIR / "generar-inventario-csv-combinar-a-excel.py"
    if not excel_script.exists():
        print(f"❌ No se encontró: {excel_script}")
        sys.exit(1)

    if RICH_AVAILABLE:
        if not run_step_rich(console, "Paso 2/2 – Consolidando CSVs en Excel",
                             [sys.executable, str(excel_script)], str(SCRIPT_DIR)):
            sys.exit(1)
        console.print()
        console.print(Panel(
            "[bold green]✅ Inventario completado exitosamente[/bold green]",
            border_style="green", box=HEAVY, padding=(1, 2), expand=False,
        ))
    else:
        if not run_step_fallback("Paso 2/2 – Consolidando CSVs en Excel",
                                 [sys.executable, str(excel_script)], str(SCRIPT_DIR)):
            sys.exit(1)
        print(f"\n{'='*60}")
        print("  ✅ Inventario completado exitosamente")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
