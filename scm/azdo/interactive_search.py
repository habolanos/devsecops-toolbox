#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Búsqueda Interactiva en Vivo para Azure DevOps Tools

Proporciona una interfaz de búsqueda con captura de teclas en tiempo real,
permitiendo filtrado visual mientras el usuario escribe.

Características:
- Búsqueda en vivo (se actualiza con cada tecla)
- Fuzzy matching en ID, nombre, descripción y grupo
- Navegación con flechas arriba/abajo
- Selección rápida por número
- Compatible con Windows, Linux y macOS
"""

import sys
import os
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.box import ROUNDED
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

# ═══════════════════════════════════════════════════════════════════════════════
# DETECCIÓN DE PLATAFORMA Y CAPTURA DE TECLAS
# ═══════════════════════════════════════════════════════════════════════════════

def get_char_windows() -> Optional[str]:
    """Captura una tecla en Windows usando msvcrt."""
    try:
        import msvcrt
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch == b'\x00' or ch == b'\xe0':  # Teclas especiales
                msvcrt.getch()  # Consumir siguiente byte
                return None
            return ch.decode('utf-8', errors='ignore')
    except Exception:
        pass
    return None


def get_char_unix() -> Optional[str]:
    """Captura una tecla en Unix/Linux/macOS usando termios."""
    try:
        import termios
        import tty
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            return ch if ch else None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        pass
    return None


def get_single_char() -> Optional[str]:
    """Captura una tecla según la plataforma."""
    if sys.platform == "win32":
        return get_char_windows()
    else:
        return get_char_unix()


# ═══════════════════════════════════════════════════════════════════════════════
# BÚSQUEDA Y FILTRADO
# ═══════════════════════════════════════════════════════════════════════════════

def fuzzy_match(query: str, text: str) -> float:
    """
    Calcula similitud fuzzy entre query y text.
    Retorna valor entre 0 y 1 (1 = coincidencia perfecta).
    """
    if not query:
        return 1.0
    
    query = query.lower()
    text = text.lower()
    
    # Coincidencia exacta
    if query in text:
        return 1.0
    
    # Coincidencia al inicio
    if text.startswith(query):
        return 0.9
    
    # Fuzzy matching
    matcher = SequenceMatcher(None, query, text)
    return matcher.ratio()


def search_tools(tools: Dict, query: str, tool_groups: Dict) -> List[Tuple[str, Dict, float]]:
    """
    Filtra herramientas por query.
    Busca en: ID, nombre, descripción, grupo.
    Retorna lista de (key, tool, score) ordenada por relevancia.
    """
    if not query:
        # Si no hay query, retornar todas las herramientas
        return [(k, v, 1.0) for k, v in tools.items()]
    
    results = []
    query_lower = query.lower()
    
    for key, tool in tools.items():
        # Obtener información de la herramienta
        name = tool.get("name", "").lower()
        desc = tool.get("description", "").lower()
        group_key = tool.get("group", "system")
        group_name = tool_groups.get(group_key, {}).get("name", "").lower()
        
        # Calcular puntuaciones
        scores = [
            fuzzy_match(query_lower, key.lower()) * 2.0,  # ID: peso 2x
            fuzzy_match(query_lower, name) * 1.5,          # Nombre: peso 1.5x
            fuzzy_match(query_lower, desc) * 1.0,          # Descripción: peso 1x
            fuzzy_match(query_lower, group_name) * 1.2,    # Grupo: peso 1.2x
        ]
        
        max_score = max(scores)
        
        # Solo incluir si hay alguna coincidencia
        if max_score > 0.3:
            results.append((key, tool, max_score))
    
    # Ordenar por puntuación descendente
    results.sort(key=lambda x: x[2], reverse=True)
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def clear_screen():
    """Limpia la pantalla."""
    os.system('cls' if sys.platform == 'win32' else 'clear')


def print_search_interface(query: str, results: List[Tuple[str, Dict, float]], 
                          tool_groups: Dict, selected_idx: int = 0):
    """Imprime la interfaz de búsqueda con resultados."""
    
    if RICH_AVAILABLE and console:
        # Usar Rich para mejor visualización
        console.clear()
        
        # Panel de búsqueda
        search_text = Text(f"🔍 Búsqueda: {query}", style="bold cyan")
        console.print(Panel(
            search_text,
            title="[bold white]BÚSQUEDA EN VIVO[/bold white]",
            border_style="cyan",
            box=ROUNDED,
        ))
        
        # Tabla de resultados
        if results:
            table = Table(
                title=f"[bold white]Coincidencias: {len(results)}/{len(results) + 100}[/bold white]",
                title_style="bold white",
                box=ROUNDED,
                header_style="bold cyan",
                border_style="blue",
                show_lines=False,
            )
            
            table.add_column("#", justify="center", style="bold white", width=4)
            table.add_column("Grupo", justify="left", width=20)
            table.add_column("Herramienta", justify="left", style="white", min_width=26)
            table.add_column("Descripción", justify="left", style="dim", min_width=40)
            
            for idx, (key, tool, score) in enumerate(results):
                group_key = tool.get("group", "system")
                group_info = tool_groups.get(group_key, tool_groups.get("system", {}))
                group_text = f"{group_info.get('emoji', '🔧')} {group_info.get('name', '')}"
                
                # Destacar fila seleccionada
                if idx == selected_idx:
                    key_style = "bold yellow"
                    group_style = "bold yellow"
                    name_style = "bold yellow"
                    desc_style = "bold yellow"
                else:
                    key_style = "bold cyan"
                    group_style = group_info.get('color', 'white')
                    name_style = "white"
                    desc_style = "dim"
                
                table.add_row(
                    f"[{key_style}]{key}[/{key_style}]",
                    f"[{group_style}]{group_text}[/{group_style}]",
                    f"[{name_style}]{tool.get('name', '')}[/{name_style}]",
                    f"[{desc_style}]{tool.get('description', '')[:40]}...[/{desc_style}]",
                )
            
            console.print(table)
        else:
            console.print("[bold red]❌ No se encontraron resultados[/bold red]")
        
        # Instrucciones
        console.print()
        console.print(Panel(
            "[dim]"
            "⬆️  ⬇️  Navegar  │  "
            "ENTER Seleccionar  │  "
            "BACKSPACE Borrar  │  "
            "ESC Cancelar"
            "[/dim]",
            border_style="dim",
        ))
    else:
        # Fallback sin Rich
        clear_screen()
        print(f"\n{'='*70}")
        print(f"{'🔍 BÚSQUEDA EN VIVO':^70}")
        print(f"{'='*70}\n")
        print(f"Búsqueda: {query}")
        print(f"Coincidencias: {len(results)}\n")
        
        if results:
            for idx, (key, tool, score) in enumerate(results):
                prefix = ">>> " if idx == selected_idx else "    "
                print(f"{prefix}[{key}] {tool.get('name', '')}")
                print(f"     {tool.get('description', '')[:60]}...\n")
        else:
            print("❌ No se encontraron resultados\n")
        
        print(f"{'='*70}")
        print("⬆️  ⬇️  Navegar  │  ENTER Seleccionar  │  ESC Cancelar")
        print(f"{'='*70}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# INTERFAZ INTERACTIVA
# ═══════════════════════════════════════════════════════════════════════════════

def interactive_search(tools: Dict, tool_groups: Dict) -> Optional[str]:
    """
    Interfaz interactiva de búsqueda en vivo.
    Retorna el ID de la herramienta seleccionada o None si se cancela.
    """
    query = ""
    selected_idx = 0
    results = list(tools.items())
    
    # Mostrar interfaz inicial
    print_search_interface(query, [(k, v, 1.0) for k, v in results], tool_groups, selected_idx)
    
    while True:
        try:
            # Capturar tecla
            ch = get_single_char()
            
            if ch is None:
                continue
            
            # Tecla ESC (27 en ASCII)
            if ord(ch) == 27:
                return None
            
            # Tecla ENTER
            elif ord(ch) == 13:
                if results:
                    filtered = search_tools(tools, query, tool_groups)
                    if filtered and selected_idx < len(filtered):
                        return filtered[selected_idx][0]
                return None
            
            # Tecla BACKSPACE
            elif ord(ch) == 8 or ord(ch) == 127:
                query = query[:-1]
            
            # Tecla ARRIBA
            elif ord(ch) == 27:  # Secuencia de escape
                # Leer siguiente carácter para flechas
                ch2 = get_single_char()
                if ch2 and ord(ch2) == 91:  # [
                    ch3 = get_single_char()
                    if ch3 and ord(ch3) == 65:  # A = arriba
                        selected_idx = max(0, selected_idx - 1)
                    elif ch3 and ord(ch3) == 66:  # B = abajo
                        filtered = search_tools(tools, query, tool_groups)
                        selected_idx = min(len(filtered) - 1, selected_idx + 1)
            
            # Caracteres normales
            elif ch.isprintable():
                query += ch
                selected_idx = 0  # Reset selección al escribir
            
            # Actualizar resultados y pantalla
            filtered = search_tools(tools, query, tool_groups)
            print_search_interface(query, filtered, tool_groups, selected_idx)
        
        except KeyboardInterrupt:
            return None
        except Exception:
            continue


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PÚBLICA
# ═══════════════════════════════════════════════════════════════════════════════

def search_and_select(tools: Dict, tool_groups: Dict) -> Optional[str]:
    """
    Inicia la búsqueda interactiva.
    Retorna el ID de la herramienta seleccionada o None.
    """
    return interactive_search(tools, tool_groups)
