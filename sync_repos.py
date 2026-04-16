#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sincronizador devsecops-toolbox ↔ devsecops-toolbox-azdo

Sincroniza el contenido de scm/ (y archivos raíz) entre los dos repositorios,
con soporte para modo simulación, logs, y commit automático.

Uso:
    python sync_repos.py                          # toolbox → azdo (default)
    python sync_repos.py --direction azdo-to-toolbox
    python sync_repos.py --what-if                # solo simular
    python sync_repos.py --no-commit              # copiar sin hacer commit
    python sync_repos.py --paths scm/gcp/inventory scm/gcp/tools.py  # solo rutas específicas
"""

import argparse
import filecmp
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
REPO_TOOLBOX = Path(r"c:\Users\harold.bolanos\repos-publics\devsecops-toolbox")
REPO_AZDO = Path(r"c:\Users\harold.bolanos\repos-publics\devsecops-toolbox-azdo")

# Directorios/archivos a excluir de la sincronización
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".vscode", ".idea", ".windsurf", "outcome", "cache", ".cache",
    "node_modules", ".tox", ".nox", "htmlcov",
}

EXCLUDE_FILES = {
    "*.pyc", "*.pyo", "*.pyd", "*.log", "*.zip", "*.gz",
    "*.tar", "*.xlsx", "*.docx", "*.pdf", "*.json",
    "*.config", "*.secret", "*.key", "*.origin.json",
}

# Rutas relativas a sincronizar por defecto (dentro del repo)
DEFAULT_SYNC_PATHS = [
    "scm/gcp",
    "scm/aws",
    "scm/azdo",
    "scm/__init__.py",
    "scm/main.py",
    "scm/README.md",
    "scm/config.json.template",
    "scm/ARCHITECTURE_ANALYSIS_PRO.md",
    "scm/tests",
    ".gitignore",
]

# Archivos raíz que también se sincronizan
ROOT_FILES = [
    ".gitignore",
]


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES
# ═══════════════════════════════════════════════════════════════════════════════

def should_exclude(name: str, is_dir: bool = False) -> bool:
    """Determina si un archivo/directorio debe excluirse."""
    if is_dir and name in EXCLUDE_DIRS:
        return True
    if not is_dir:
        for pattern in EXCLUDE_FILES:
            if pattern.startswith("*.") and name.endswith(pattern[1:]):
                return True
        if name in EXCLUDE_DIRS:
            return True
    return False


def sync_directory(src: Path, dst: Path, what_if: bool = False) -> dict:
    """
    Sincroniza un directorio recursivamente (estilo rsync).
    Retorna dict con stats: {copied, updated, deleted, skipped, errors}
    """
    stats = {"copied": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": 0}

    # Crear destino si no existe
    if not dst.exists():
        if not what_if:
            dst.mkdir(parents=True, exist_ok=True)
        print(f"  📁 + {dst.relative_to(dst.parents[2])}/")
        stats["copied"] += 1

    # Recorrer origen
    if src.exists():
        for item in sorted(src.iterdir()):
            if should_exclude(item.name, item.is_dir()):
                continue

            rel = item.relative_to(src)
            dst_item = dst / item.name

            if item.is_dir():
                sub_stats = sync_directory(item, dst_item, what_if)
                for k in stats:
                    stats[k] += sub_stats[k]
            else:
                # Verificar si necesita copiarse
                needs_copy = False
                if not dst_item.exists():
                    needs_copy = True
                    action = "+"
                elif not filecmp.cmp(item, dst_item, shallow=False):
                    needs_copy = True
                    action = "≠"
                else:
                    stats["skipped"] += 1
                    continue

                rel_path = dst_item.relative_to(dst.parents[2])
                print(f"  📄 {action} {rel_path}")

                if needs_copy:
                    if not what_if:
                        try:
                            shutil.copy2(item, dst_item)
                        except Exception as e:
                            print(f"  ❌ Error copiando {item}: {e}")
                            stats["errors"] += 1
                            continue
                    stats["updated" if action == "≠" else "copied"] += 1

    # Eliminar archivos en destino que ya no existen en origen
    if dst.exists():
        for item in sorted(dst.iterdir()):
            if should_exclude(item.name, item.is_dir()):
                continue
            src_item = src / item.name
            if not src_item.exists():
                rel_path = item.relative_to(item.parents[2])
                print(f"  🗑️  - {rel_path}")
                if not what_if:
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                    except Exception as e:
                        print(f"  ❌ Error eliminando {item}: {e}")
                        stats["errors"] += 1
                        continue
                stats["deleted"] += 1

    return stats


def sync_file(src: Path, dst: Path, what_if: bool = False) -> dict:
    """Sincroniza un archivo individual."""
    stats = {"copied": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": 0}

    if not src.exists():
        if dst.exists():
            print(f"  🗑️  - {dst}")
            if not what_if:
                dst.unlink()
            stats["deleted"] += 1
        return stats

    needs_copy = False
    if not dst.exists():
        needs_copy = True
        action = "+"
    elif not filecmp.cmp(src, dst, shallow=False):
        needs_copy = True
        action = "≠"
    else:
        stats["skipped"] += 1
        return stats

    print(f"  📄 {action} {dst}")
    if needs_copy and not what_if:
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            print(f"  ❌ Error copiando {src}: {e}")
            stats["errors"] += 1
            return stats
    stats["updated" if action == "≠" else "copied"] += 1
    return stats


def sync_path(rel_path: str, src_root: Path, dst_root: Path, what_if: bool = False) -> dict:
    """Sincroniza una ruta relativa (archivo o directorio)."""
    src = src_root / rel_path
    dst = dst_root / rel_path

    if not src.exists() and not dst.exists():
        print(f"  ⚠️  Ruta no encontrada en ningún repo: {rel_path}")
        return {"copied": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": 0}

    if src.is_dir() or (not src.exists() and dst.is_dir()):
        return sync_directory(src, dst, what_if)
    else:
        return sync_file(src, dst, what_if)


def git_add_commit_push(repo: Path, message: str, what_if: bool = False) -> bool:
    """Ejecuta git add, commit y push en el repositorio destino."""
    if what_if:
        print(f"\n  [SIM] git add -A && git commit -m '{message}' && git push")
        return True

    try:
        # git add -A
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=str(repo), capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ⚠️  git add: {result.stderr.strip()}")

        # Verificar si hay cambios para commitear
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(repo), capture_output=True, text=True
        )
        if result.returncode == 0:
            print("  ℹ️  No hay cambios para commitear")
            return True

        # git commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(repo), capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ❌ git commit falló: {result.stderr.strip()}")
            return False

        # git push
        result = subprocess.run(
            ["git", "push"],
            cwd=str(repo), capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ❌ git push falló: {result.stderr.strip()}")
            return False

        print(f"  ✅ Commit + push exitoso")
        return True

    except Exception as e:
        print(f"  ❌ Error en git: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Sincronizador devsecops-toolbox ↔ devsecops-toolbox-azdo"
    )
    parser.add_argument(
        "--direction", "-d",
        choices=["toolbox-to-azdo", "azdo-to-toolbox"],
        default="toolbox-to-azdo",
        help="Dirección de la sincronización (default: toolbox-to-azdo)",
    )
    parser.add_argument(
        "--what-if", "-n",
        action="store_true",
        help="Solo simular, no realizar cambios",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="No hacer git commit/push después de sincronizar",
    )
    parser.add_argument(
        "--paths", "-p",
        nargs="+",
        default=None,
        help="Rutas relativas específicas a sincronizar (default: todas)",
    )
    args = parser.parse_args()

    # Determinar origen y destino
    if args.direction == "toolbox-to-azdo":
        src_root = REPO_TOOLBOX
        dst_root = REPO_AZDO
        direction_label = "toolbox → azdo"
    else:
        src_root = REPO_AZDO
        dst_root = REPO_TOOLBOX
        direction_label = "azdo → toolbox"

    # Rutas a sincronizar
    sync_paths = args.paths if args.paths else DEFAULT_SYNC_PATHS

    # Header
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║          SINCRONIZADOR DevSecOps Toolbox ↔ AzDO                    ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print(f"  Dirección:  {direction_label}")
    print(f"  Origen:     {src_root}")
    print(f"  Destino:    {dst_root}")
    print(f"  Rutas:      {len(sync_paths)}")
    print(f"  Modo:       {'SIMULACIÓN' if args.what_if else 'EJECUCIÓN'}")
    print()

    # Validar que los repos existen
    if not src_root.exists():
        print(f"❌ Repositorio origen no encontrado: {src_root}")
        sys.exit(1)
    if not dst_root.exists():
        print(f"❌ Repositorio destino no encontrado: {dst_root}")
        sys.exit(1)

    # Sincronizar cada ruta
    total_stats = {"copied": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": 0}
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    for rel_path in sync_paths:
        print(f"\n📂 Sincronizando: {rel_path}")
        print("  " + "─" * 50)
        stats = sync_path(rel_path, src_root, dst_root, args.what_if)
        for k in total_stats:
            total_stats[k] += stats[k]

    # Resumen
    print()
    print("═" * 60)
    print("  RESUMEN DE SINCRONIZACIÓN")
    print("═" * 60)
    print(f"  Archivos nuevos:     {total_stats['copied']}")
    print(f"  Archivos actualizados: {total_stats['updated']}")
    print(f"  Archivos eliminados:  {total_stats['deleted']}")
    print(f"  Archivos sin cambios: {total_stats['skipped']}")
    print(f"  Errores:              {total_stats['errors']}")
    print()

    changes = total_stats["copied"] + total_stats["updated"] + total_stats["deleted"]
    if changes == 0:
        print("  ✅ Todo sincronizado, sin cambios necesarios")
        return

    # Commit y push
    if not args.no_commit and not args.what_if:
        commit_msg = f"sync: {direction_label} - {changes} cambios ({timestamp})"
        print(f"\n📦 Haciendo commit en destino...")
        git_add_commit_push(dst_root, commit_msg, args.what_if)

    # Guardar log
    log_dir = REPO_TOOLBOX / "outcome"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    if not args.what_if:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Sync: {direction_label}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Stats: {total_stats}\n")
        print(f"  📝 Log: {log_file}")

    print()


if __name__ == "__main__":
    main()
