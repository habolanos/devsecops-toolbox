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

import importlib.util
import runpy
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



try:
    from export_manager import ExportManager
    EXPORT_MANAGER_AVAILABLE = True
except ImportError:
    EXPORT_MANAGER_AVAILABLE = False

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

    # ── Paso 1: Generar CSVs ──────────────────────────────────────────────
    if not skip_csv:
        csv_py = SCRIPT_DIR / "generar-inventario-csv.py"
        csv_sh = SCRIPT_DIR / "generar-inventario-csv.sh"

        if csv_py.exists():
            # Cargar módulo por ruta de archivo (mismo proceso → Rich funciona)
            csv_args = [a for a in sys.argv[1:] if a != "--skip-csv"]
            saved_argv = sys.argv
            sys.argv = [str(csv_py)] + csv_args
            try:
                spec = importlib.util.spec_from_file_location("generar_inventario_csv", str(csv_py))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.main()
            except SystemExit as e:
                if e.code and e.code != 0:
                    sys.argv = saved_argv
                    sys.exit(e.code)
            except Exception as e:
                sys.argv = saved_argv
                if RICH_AVAILABLE:
                    console.print(f"[red]❌ Error en CSVs: {e}[/red]")
                else:
                    print(f"❌ Error en CSVs: {e}")
                sys.exit(1)
            finally:
                sys.argv = saved_argv
        elif csv_sh.exists():
            # Fallback a bash
            cmd = ["bash", str(csv_sh)]
            extra_args = [a for a in sys.argv[1:] if a != "--skip-csv"]
            cmd.extend(extra_args)
            result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
            if result.returncode != 0:
                print(f"❌ Error en bash script (código {result.returncode})")
                sys.exit(1)
        else:
            print("❌ No se encontró: generar-inventario-csv.py ni .sh")
            sys.exit(1)

    # ── Paso 2: Consolidar Excel ───────────────────────────────────────────
    excel_script = SCRIPT_DIR / "generar-inventario-csv-combinar-a-excel.py"
    if not excel_script.exists():
        print(f"❌ No se encontró: {excel_script}")
        sys.exit(1)

    if RICH_AVAILABLE:
        with console.status("[bold cyan]⏳ Paso 2/2 – Consolidando CSVs en Excel[/bold cyan]", spinner="dots"):
            result = subprocess.run(
                [sys.executable, str(excel_script)],
                cwd=str(SCRIPT_DIR),
            )
        if result.returncode != 0:
            console.print(f"[red]❌ Error consolidando Excel (código {result.returncode})[/red]")
            sys.exit(1)
        console.print()
        console.print(Panel(
            "[bold green]✅ Inventario completado exitosamente[/bold green]",
            border_style="green", box=HEAVY, padding=(1, 2), expand=False,
        ))
    else:
        print(f"\n{'='*60}")
        print("  Paso 2/2 – Consolidando CSVs en Excel")
        print(f"{'='*60}")
        result = subprocess.run(
            [sys.executable, str(excel_script)],
            cwd=str(SCRIPT_DIR),
        )
        if result.returncode != 0:
            print(f"❌ Error consolidando Excel (código {result.returncode})")
            sys.exit(1)
        print(f"\n{'='*60}")
        print("  ✅ Inventario completado exitosamente")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def export_results(data, output_format: str = "json", output_dir: str = "outcome"):
    """Exporta resultados usando ExportManager centralizado con fallback."""
    
    from pathlib import Path
    import json
    import csv
    from datetime import datetime
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not EXPORT_MANAGER_AVAILABLE:
        # Fallback a exportación manual
        if output_format == "json":
            filepath = output_path / f"run_inventory_{ts}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.now().isoformat(), "data": data}, f, indent=2, default=str)
        elif output_format == "csv":
            filepath = output_path / f"run_inventory_{ts}.csv"
            if isinstance(data, list) and data and isinstance(data[0], dict):
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            return None
        
        print(f"✅ Resultados exportados a: {filepath}")
        return str(filepath)
    
    # Usar ExportManager
    manager = ExportManager("run_inventory", "1.0.0")
    
    summary = {"total_items": len(data) if isinstance(data, list) else 1}
    
    if output_format == "json":
        return manager.export_json(data if isinstance(data, list) else [data], summary=summary)
    elif output_format == "csv":
        return manager.export_csv(data if isinstance(data, list) else [data])
    elif output_format == "excel":
        return manager.export_excel(data if isinstance(data, list) else [data], sheet_name="Results", summary=summary)
    
    return None
