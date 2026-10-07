#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cert Manager Tools — Submenú de operación de certificados TLS

Launcher interactivo para los scripts de `operation_update_certs_on_gke_gcp/`:

- Alcance Kubernetes/GKE: respaldo y preparación de renovación de Secrets
  `kubernetes.io/tls`, y validación del certificado publicado por un endpoint.
- Alcance GCP: inventario de certificados SSL de Compute Engine y cartas
  para el equipo Multicloud.

Los scripts requieren un entorno POSIX (`bash`, finales LF) y kubectl/gcloud
autenticados. Los artefactos generados (backups, YAML, evidencia HTML) se
crean en este mismo directorio.

Uso:
    python tools.py
"""

import os
import sys
import json
import shutil
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-INSTALACIÓN DE RICH
# ═══════════════════════════════════════════════════════════════════════════════
def _ensure_rich():
    """Verifica si rich está instalado; si no, lo instala automáticamente."""
    try:
        import rich  # noqa: F401
        return True
    except ImportError:
        pass

    print("📦 Instalando rich para interfaz moderna...")
    pip_args = [sys.executable, "-m", "pip", "install", "-q", "rich"]

    try:
        subprocess.check_call(pip_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Dependencias instaladas correctamente.\n")
        return True
    except subprocess.CalledProcessError:
        print("⚠️  No se pudo instalar rich. Se usará interfaz básica.\n")
        return False

RICH_AVAILABLE = _ensure_rich()

if RICH_AVAILABLE:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.box import ROUNDED, DOUBLE_EDGE
    from rich.align import Align
    from rich.prompt import Prompt

try:
    from utils import get_output_dir
except ImportError:
    def get_output_dir(default="."):
        env = os.getenv("DEVSECOPS_OUTPUT_DIR")
        p = Path(env) if env else Path(default)
        p.mkdir(parents=True, exist_ok=True)
        return p

# ═══════════════════════════════════════════════════════════════════════════════
# METADATA
# ═══════════════════════════════════════════════════════════════════════════════
__version__ = "1.8.32"
__author__ = "Harold Adrian"
__description__ = "Cert Manager Tools - Operación de certificados TLS en GKE y GCP"

console = Console() if RICH_AVAILABLE else None
BASE_DIR = Path(__file__).parent.absolute()
SCM_ROOT = BASE_DIR.parent.parent  # Raíz de scm/
CONFIG_FILE = SCM_ROOT / "config.json"
DEFAULT_BASE_CERT = "cer-io-2027.yml"


def resolve_outcome_dir() -> str:
    """Resuelve el outcome global: DEVSECOPS_OUTPUT_DIR > config.json > scm/outcome."""
    env = os.getenv("DEVSECOPS_OUTPUT_DIR")
    if env:
        return env
    try:
        if CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            out = (cfg.get("global") or {}).get("output_dir") or "outcome"
            p = Path(out)
            return str(p if p.is_absolute() else (SCM_ROOT / p).resolve())
    except Exception:
        pass
    return str((SCM_ROOT / "outcome").resolve())

# ═══════════════════════════════════════════════════════════════════════════════
# COLORES FALLBACK
# ═══════════════════════════════════════════════════════════════════════════════
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ═══════════════════════════════════════════════════════════════════════════════
# OPERACIONES DISPONIBLES
# ═══════════════════════════════════════════════════════════════════════════════
OPERATIONS = {
    "1": {
        "name": "Backup y renovación de Secrets TLS",
        "scope": "K8s/GKE",
        "description": "Respalda Secrets kubernetes.io/tls del clúster activo, genera el YAML de actualización y la evidencia HTML (no aplica cambios)",
        "path": "cert_backup_and_renew_tls_certs.sh",
        "status": "ready"
    },
    "2": {
        "name": "Validar certificado TLS de un endpoint",
        "scope": "K8s/GKE",
        "description": "Valida el certificado publicado, la cadena de confianza y la negociación TLS desde un pod temporal (jrecord/nettools)",
        "path": "cert_check-certificate-report.sh",
        "status": "ready"
    },
    "3": {
        "name": "Inventario de certificados SSL de GCP",
        "scope": "GCP",
        "description": "Lista ssl-certificates del proyecto (global/regional), vigencia, estado y target proxies que los usan; genera cartas para Multicloud",
        "path": "cert_report_ssl_certs_gcp_components.sh",
        "status": "ready"
    },
    "4": {
        "name": "Verificar prerrequisitos",
        "scope": "CHECK",
        "description": "Comprueba bash, kubectl (contexto y permisos) y gcloud (sesión y proyecto) según el README",
        "path": None,
        "status": "ready",
        "action": "prereqs"
    },
    "Q": {
        "name": "Volver",
        "scope": "",
        "description": "Regresar al menú anterior",
        "path": None,
        "status": "exit"
    }
}


def print_menu_rich():
    """Muestra el menú con Rich."""
    console.print()

    header = Panel(
        Align.center(Text("🔐 CERT MANAGER TOOLS", style="bold cyan")),
        box=DOUBLE_EDGE,
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(header)

    console.print(Panel(
        "[dim]Operación de certificados TLS — Secrets K8s/GKE y SSL Certificates de GCP[/dim]",
        box=ROUNDED,
        border_style="dim"
    ))
    console.print()

    table = Table(
        box=ROUNDED,
        header_style="bold cyan",
        border_style="cyan",
        title="[bold]Operaciones Disponibles[/bold]",
        title_style="cyan"
    )

    table.add_column("#", justify="center", width=4)
    table.add_column("Alcance", justify="center", width=9)
    table.add_column("Operación", style="white", min_width=30)
    table.add_column("Descripción", style="dim", min_width=50)

    for key, op in OPERATIONS.items():
        name_style = "bold white" if key != "Q" else "bold yellow"
        scope = op.get("scope", "")
        scope_fmt = {
            "K8s/GKE": f"[magenta]{scope}[/magenta]",
            "GCP": f"[blue]{scope}[/blue]",
            "CHECK": f"[green]{scope}[/green]",
        }.get(scope, scope)

        table.add_row(
            f"[cyan]{key}[/cyan]",
            scope_fmt,
            f"[{name_style}]{op['name']}[/{name_style}]",
            op.get("description", "")
        )

    console.print(table)
    console.print()


def print_menu_fallback():
    """Muestra el menú sin Rich."""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'🔐  CERT MANAGER TOOLS':^60}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print()

    for key, op in OPERATIONS.items():
        color = Colors.WARNING if key == "Q" else Colors.BLUE
        scope = op.get("scope", "")
        print(f"  {color}[{key}]{Colors.ENDC} {Colors.BOLD}{op['name']}{Colors.ENDC} [{scope}]")
        print(f"      {op.get('description', '')}")
    print()


def check_shell_compatibility() -> bool:
    """Verifica que exista un entorno POSIX para ejecutar scripts shell."""
    if platform.system() != "Windows":
        return True

    bash_path = shutil.which("bash")
    if bash_path:
        print(f"\n{Colors.WARNING}⚠️  Windows detectado — se usará bash de: {bash_path}{Colors.ENDC}")
        print(f"{Colors.WARNING}   (Los scripts requieren finales de línea LF y entorno POSIX){Colors.ENDC}")
        return True

    print(f"\n{Colors.FAIL}{'='*60}{Colors.ENDC}")
    print(f"{Colors.FAIL}  ⚠️  PLATAFORMA WINDOWS SIN BASH{Colors.ENDC}")
    print(f"{Colors.FAIL}{'='*60}{Colors.ENDC}")
    print(f"\n{Colors.WARNING}Los scripts .sh requieren Linux, WSL o Git Bash.{Colors.ENDC}")
    print(f"{Colors.CYAN}Opción recomendada: ejecutar desde WSL.{Colors.ENDC}")
    input(f"\n{Colors.FAIL}Presione Enter para continuar...{Colors.ENDC}")
    return False


def _prompt(msg: str, default: str = "") -> str:
    """Prompt unificado Rich/fallback."""
    if RICH_AVAILABLE and console:
        return Prompt.ask(msg, default=default).strip() if default else Prompt.ask(msg).strip()
    suffix = f" [{default}]" if default else ""
    return input(f"{Colors.BOLD}{msg}{suffix}: {Colors.ENDC}").strip()


def run_script_file(op: Dict, extra_args: List[str], capture: bool = False) -> Tuple[int, str]:
    """Ejecuta un script shell del directorio con cwd=BASE_DIR."""
    script_path = BASE_DIR / op["path"]
    if not script_path.exists():
        print(f"{Colors.FAIL}Error: no se encontró {script_path}{Colors.ENDC}")
        return 1, ""

    cmd = ["bash", str(script_path)] + extra_args
    print(f"\n{Colors.CYAN}Ejecutando: {' '.join(cmd)}{Colors.ENDC}\n")

    env = os.environ.copy()
    env.setdefault("DEVSECOPS_OUTPUT_DIR", resolve_outcome_dir())

    try:
        if capture:
            result = subprocess.run(cmd, cwd=str(BASE_DIR), env=env,
                                    capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            return result.returncode, result.stdout or ""
        result = subprocess.run(cmd, cwd=str(BASE_DIR), env=env)
        return result.returncode, ""
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.FAIL}Error al ejecutar el script: {e}{Colors.ENDC}")
        return e.returncode or 1, ""
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida.{Colors.ENDC}")
        return 130, ""
    except FileNotFoundError:
        print(f"\n{Colors.FAIL}No se encontró 'bash' en el PATH.{Colors.ENDC}")
        return 127, ""


def op_backup_and_renew():
    """Opción 1: respaldo + YAML de renovación de Secrets TLS."""
    default = DEFAULT_BASE_CERT if (BASE_DIR / DEFAULT_BASE_CERT).exists() else ""
    base_file = _prompt(
        f"Archivo base (Secret YAML con tls.crt/tls.key)", default or "cer-io-2027.yml"
    )
    if not base_file:
        base_file = default or "cer-io-2027.yml"

    if not (BASE_DIR / base_file).exists():
        print(f"{Colors.FAIL}No se encontró {base_file} en {BASE_DIR}{Colors.ENDC}")
        print(f"{Colors.WARNING}Coloca el YAML base en esta carpeta o indica otro nombre.{Colors.ENDC}")
        return

    print(f"{Colors.CYAN}Clúster activo:{Colors.ENDC}")
    subprocess.run(["kubectl", "config", "current-context"], check=False)

    confirm = _prompt("¿Continuar con el respaldo y generación del YAML? (s/n)", "n").lower()
    if confirm != "s":
        print(f"{Colors.WARNING}Operación cancelada.{Colors.ENDC}")
        return

    code, _ = run_script_file(OPERATIONS["1"], [f"--base-cert-file={base_file}"])
    if code == 0:
        print(f"\n{Colors.GREEN}✅ Respaldo completado. Artefactos en "
              f"{resolve_outcome_dir()}/certs-<cluster>-<ts>/ "
              f"(tls-backups/, update-certs-*.yaml, evidencia-*.html).{Colors.ENDC}")
        print(f"{Colors.WARNING}Recuerda: revisar el YAML antes de aplicar con "
              f"'kubectl apply -f <outcome>/certs-*/update-certs-*.yaml'{Colors.ENDC}")
    else:
        print(f"\n{Colors.FAIL}El script terminó con código {code}.{Colors.ENDC}")


def op_check_endpoint():
    """Opción 2: validación del certificado TLS publicado por un endpoint."""
    host = _prompt("Host a validar (ej: wms-dev.coppel.io)")
    if not host:
        print(f"{Colors.FAIL}Se requiere el host.{Colors.ENDC}")
        return

    port = _prompt("Puerto", "443") or "443"
    code, _ = run_script_file(OPERATIONS["2"], [host, port])
    if code != 0:
        print(f"\n{Colors.WARNING}El reporte terminó con código {code} — revisa los "
              f"bloques [WARN]/[ERROR] de la salida.{Colors.ENDC}")


def op_gcp_inventory():
    """Opción 3: inventario de ssl-certificates de un proyecto GCP."""
    project = _prompt("PROJECT_ID de GCP (ej: cpl-cs-wms-dev-30112023)")
    if not project:
        print(f"{Colors.FAIL}Se requiere el PROJECT_ID.{Colors.ENDC}")
        return

    todos = _prompt("¿Generar cartas para TODOS los certificados? (s/n)", "n").lower()
    export = _prompt("¿Exportar el reporte a outcome/? (s/n)", "n").lower()

    args = [project] + (["--todos"] if todos == "s" else [])

    if export == "s":
        code, stdout = run_script_file(OPERATIONS["3"], args, capture=True)
        if stdout:
            out_dir = get_output_dir("outcome")
            from datetime import datetime
            out_file = out_dir / f"reporte-certs-{project}-{datetime.now():%Y%m%d_%H%M%S}.txt"
            out_file.write_text(stdout, encoding="utf-8")
            print(f"\n{Colors.GREEN}📄 Reporte exportado: {out_file}{Colors.ENDC}")
    else:
        code, _ = run_script_file(OPERATIONS["3"], args)

    if code != 0:
        print(f"\n{Colors.FAIL}El script terminó con código {code}.{Colors.ENDC}")


def _check_cmd(cmd: List[str], label: str) -> Tuple[str, str, str]:
    """Ejecuta un comando de verificación y retorna (label, estado, detalle)."""
    if not shutil.which(cmd[0]):
        return label, "NO DISPONIBLE", f"'{cmd[0]}' no está en el PATH"
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        out = (result.stdout or result.stderr).strip()
        if result.returncode == 0:
            return label, "OK", out.splitlines()[0] if out else "OK"
        return label, "ERROR", out.splitlines()[0] if out else f"exit {result.returncode}"
    except subprocess.TimeoutExpired:
        return label, "TIMEOUT", ">30s sin respuesta"
    except Exception as e:
        return label, "ERROR", str(e)


def op_check_prereqs():
    """Opción 4: verificación de prerrequisitos del README."""
    checks = [
        (["bash", "--version"], "bash (entorno POSIX)"),
        (["kubectl", "config", "current-context"], "kubectl contexto activo"),
        (["kubectl", "auth", "can-i", "list", "secrets", "--all-namespaces"], "kubectl list secrets"),
        (["kubectl", "auth", "can-i", "create", "pods", "-n", "default"], "kubectl create pods (default)"),
        (["openssl", "version"], "openssl"),
        (["jq", "--version"], "jq"),
        (["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"], "gcloud sesión activa"),
        (["gcloud", "config", "get-value", "project"], "gcloud proyecto"),
    ]

    rows = [_check_cmd(cmd, label) for cmd, label in checks]

    if RICH_AVAILABLE and console:
        table = Table(box=ROUNDED, header_style="bold cyan", border_style="cyan",
                      title="[bold]Prerrequisitos[/bold]", title_style="cyan")
        table.add_column("Verificación", style="white", min_width=28)
        table.add_column("Estado", justify="center", width=14)
        table.add_column("Detalle", style="dim", min_width=40)
        for label, status, detail in rows:
            style = {"OK": "green", "NO DISPONIBLE": "yellow"}.get(status, "red")
            table.add_row(label, f"[{style}]{status}[/{style}]", detail[:80])
        console.print(table)
    else:
        for label, status, detail in rows:
            print(f"  [{status:>12}] {label}: {detail[:80]}")

    failed = [r for r in rows if r[1] not in ("OK",)]
    if failed:
        print(f"\n{Colors.WARNING}⚠️  {len(failed)} verificación(es) requieren atención.{Colors.ENDC}")
    else:
        print(f"\n{Colors.GREEN}✅ Todos los prerrequisitos están listos.{Colors.ENDC}")


def run_operation(choice: str):
    """Despacha la operación seleccionada."""
    if choice not in OPERATIONS:
        print(f"{Colors.FAIL}Opción no válida.{Colors.ENDC}")
        return

    op = OPERATIONS[choice]
    if choice == "Q":
        return

    print(f"\n{Colors.HEADER}=== {op['name']} ==={Colors.ENDC}")
    print(f"{op['description']}\n")

    if op.get("action") == "prereqs":
        op_check_prereqs()
    elif choice == "1":
        if check_shell_compatibility():
            op_backup_and_renew()
    elif choice == "2":
        if check_shell_compatibility():
            op_check_endpoint()
    elif choice == "3":
        if check_shell_compatibility():
            op_gcp_inventory()

    input(f"\n{Colors.CYAN}Presione Enter para continuar...{Colors.ENDC}")


def main():
    """Bucle principal del submenú."""
    while True:
        if RICH_AVAILABLE and console:
            print_menu_rich()
        else:
            print_menu_fallback()

        try:
            if RICH_AVAILABLE and console:
                choice = Prompt.ask("[bold cyan]Seleccione una opción[/]", default="Q").strip().upper()
            else:
                choice = input(f"{Colors.BOLD}Seleccione una opción: {Colors.ENDC}").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Colors.GREEN}Saliendo...{Colors.ENDC}")
            break

        if choice == "Q":
            print(f"\n{Colors.GREEN}Volviendo...{Colors.ENDC}")
            break

        run_operation(choice)


if __name__ == "__main__":
    main()
