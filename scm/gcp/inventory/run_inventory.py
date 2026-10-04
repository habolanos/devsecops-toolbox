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
import os
import runpy
import subprocess
import sys
from pathlib import Path

# --- Config global: DEVSECOPS_* env > scm/config.json > scm/outcome ---
try:
    from utils import resolve_outcome_dir, log_command
except ImportError:
    import os as _os
    import json as _json
    from pathlib import Path as _Path
    from datetime import datetime as _dt

    _SCM_ROOT = _Path(__file__).resolve().parents[2]  # inventory -> gcp -> scm

    def resolve_outcome_dir(default="outcome"):
        env = _os.getenv("DEVSECOPS_OUTPUT_DIR")
        if env:
            p = _Path(env)
        else:
            try:
                cfg_file = _SCM_ROOT / "config.json"
                cfg = _json.loads(cfg_file.read_text(encoding="utf-8")) \
                    if cfg_file.exists() else {}
                out = (cfg.get("global") or {}).get("output_dir") or default
            except Exception:
                out = default
            p = _Path(out)
            if not p.is_absolute():
                p = _SCM_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p.resolve()

    def log_command(cmd, status="EXEC", platform_name="GCP"):
        if _os.getenv("DEVSECOPS_LOG_COMMANDS") != "1":
            return
        log_dir = resolve_outcome_dir()
        ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        today = _dt.now().strftime("%Y%m%d")
        cmd_str = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
        try:
            with open(log_dir / f"commands_{today}.log", "a", encoding="utf-8") as f:
                f.write(f"[{ts}] [{platform_name}] [{status}] {cmd_str}\n")
        except OSError:
            pass
# ----------------------------------------------------------------------

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

def ensure_output_env() -> Path:
    """Resuelve el outcome global y lo fija en DEVSECOPS_OUTPUT_DIR si falta.

    Garantiza que el generador CSV (mismo proceso) y el consolidador Excel
    (subproceso) resuelvan exactamente el mismo directorio.
    """
    out_dir = resolve_outcome_dir()
    os.environ.setdefault("DEVSECOPS_OUTPUT_DIR", str(out_dir))
    return out_dir


def main():
    skip_csv = "--skip-csv" in sys.argv

    out_dir = ensure_output_env()

    if RICH_AVAILABLE:
        console = Console()
        console.print(Panel(
            Text.assemble(
                ("📋 Inventario GKE + Cloud SQL\n\n", "bold white"),
                ("Pipeline completo de inventario:\n", "dim"),
                ("  1. CSVs por proyecto (Rich UI)\n", "cyan"),
                ("  2. Consolidación en Excel\n", "cyan"),
                ("  Output: ", "dim"),
                (f"{out_dir}\n", "green"),
            ),
            border_style="cyan", box=HEAVY, padding=(1, 2), expand=False,
        ))
    else:
        print("📋 Inventario GKE + Cloud SQL - Launcher")
        print(f"  Output: {out_dir}")

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

    excel_cmd = [sys.executable, str(excel_script)]
    log_command(excel_cmd)

    if RICH_AVAILABLE:
        # Capturar salida del consolidador para que no se interponga con el
        # spinner en vivo; se imprime al terminar.
        with console.status("[bold cyan]⏳ Paso 2/2 – Consolidando CSVs en Excel[/bold cyan]", spinner="dots"):
            result = subprocess.run(
                excel_cmd,
                cwd=str(SCRIPT_DIR),
                capture_output=True, text=True,
            )
        if result.stdout:
            console.print(result.stdout.rstrip())
        if result.returncode != 0:
            if result.stderr:
                console.print(f"[dim]{result.stderr.rstrip()}[/dim]")
            log_command(excel_cmd, "ERROR")
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
            excel_cmd,
            cwd=str(SCRIPT_DIR),
        )
        if result.returncode != 0:
            log_command(excel_cmd, "ERROR")
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
