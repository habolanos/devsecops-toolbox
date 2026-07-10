#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo Centralizado de Búsqueda Interactiva

Proporciona una interfaz de búsqueda unificada para todas las plataformas:
- AZDO (herramientas)
- GCP (herramientas)
- AWS (herramientas)
- Terminal (scripts)
- KPI Analyzer (herramientas)
- Main (plataformas)

Características:
- Búsqueda fuzzy en vivo
- Captura de teclas multiplataforma (Windows/Linux/macOS)
- Visualización con Rich
- Navegación interactiva
- Compatible con todas las plataformas
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
            # Teclas especiales en Windows (flechas, Fn, etc.)
            # Estos códigos requieren consumir un byte adicional
            if ch == b'\x00' or ch == b'\xe0':
                # Consumir el siguiente byte de la secuencia
                next_ch = msvcrt.getch()
                # Retornar ESC + siguiente byte para procesamiento
                # Esto permite manejar secuencias de flechas
                return ch.decode('utf-8', errors='ignore') + next_ch.decode('utf-8', errors='ignore')
            # ESC es una tecla simple (0x1b = 27 en ASCII)
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
    
    Prioriza:
    1. Coincidencia exacta (1.0)
    2. Coincidencia al inicio (0.95)
    3. Coincidencia de palabra completa (0.85)
    4. Fuzzy matching (ratio)
    """
    if not query:
        return 1.0
    
    query = query.lower()
    text = text.lower()
    
    # Coincidencia exacta
    if query == text:
        return 1.0
    
    # Coincidencia exacta como substring
    if query in text:
        return 0.95
    
    # Coincidencia al inicio
    if text.startswith(query):
        return 0.90
    
    # Coincidencia de palabra completa (separada por espacios)
    words = text.split()
    for word in words:
        if word.startswith(query):
            return 0.85
    
    # Fuzzy matching con SequenceMatcher
    matcher = SequenceMatcher(None, query, text)
    ratio = matcher.ratio()
    
    # Solo retornar si hay al menos 50% de similitud
    return ratio if ratio >= 0.5 else 0.0


def search_items(items: Dict, query: str, search_fields: Dict = None) -> List[Tuple[str, Dict, float]]:
    """
    Filtra items por query.
    
    Args:
        items: Diccionario de items (ej: TOOLS, SCRIPTS, PLATFORMS)
        query: Texto a buscar
        search_fields: Diccionario con campos a buscar y pesos
                      ej: {"name": 2.0, "description": 1.0, "group": 1.2}
    
    Returns:
        Lista de (key, item, score) ordenada por relevancia
    """
    if not query:
        return [(k, v, 1.0) for k, v in items.items()]
    
    if search_fields is None:
        search_fields = {"name": 2.0, "description": 1.0}
    
    results = []
    query_lower = query.lower()
    
    for key, item in items.items():
        scores = []
        
        # Calcular puntuaciones para cada campo
        for field, weight in search_fields.items():
            field_value = item.get(field, "")
            if isinstance(field_value, str):
                score = fuzzy_match(query_lower, field_value) * weight
                scores.append(score)
        
        if scores:
            max_score = max(scores)
            
            # Solo incluir si hay alguna coincidencia significativa
            # Threshold: 0.5 (50% de similitud mínima)
            if max_score > 0.5:
                results.append((key, item, max_score))
    
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
                          columns: List[str] = None, selected_idx: int = 0):
    """
    Imprime la interfaz de búsqueda con resultados.
    
    Args:
        query: Texto de búsqueda
        results: Lista de (key, item, score)
        columns: Columnas a mostrar (ej: ["#", "Grupo", "Herramienta", "Descripción"])
        selected_idx: Índice seleccionado
    """
    if columns is None:
        columns = ["#", "Nombre", "Descripción"]
    
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
                title=f"[bold white]Coincidencias: {len(results)}[/bold white]",
                title_style="bold white",
                box=ROUNDED,
                header_style="bold cyan",
                border_style="blue",
                show_lines=False,
                expand=True,
            )
            
            # Agregar columnas
            for col in columns:
                if col == "#":
                    table.add_column(col, justify="center", style="bold white", width=4)
                else:
                    table.add_column(col, justify="left", style="white")
            
            # Agregar filas
            for idx, (key, item, score) in enumerate(results):
                # Destacar fila seleccionada
                if idx == selected_idx:
                    key_style = "bold yellow"
                    row_style = "bold yellow"
                else:
                    key_style = "bold cyan"
                    row_style = "white"
                
                # Construir fila según columnas
                row = []
                for col in columns:
                    if col == "#":
                        row.append(f"[{key_style}]{key}[/{key_style}]")
                    elif col == "Nombre":
                        row.append(f"[{row_style}]{item.get('name', '')}[/{row_style}]")
                    elif col == "Descripción":
                        row.append(f"[dim]{item.get('description', '')}[/dim]")
                    elif col == "Grupo":
                        row.append(f"[{row_style}]{item.get('group', '')}[/{row_style}]")
                    else:
                        row.append(f"[{row_style}]{item.get(col.lower(), '')}[/{row_style}]")
                
                table.add_row(*row)
            
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
            for idx, (key, item, score) in enumerate(results):
                prefix = ">>> " if idx == selected_idx else "    "
                print(f"{prefix}[{key}] {item.get('name', '')}")
                print(f"     {item.get('description', '')[:60]}...\n")
        else:
            print("❌ No se encontraron resultados\n")
        
        print(f"{'='*70}")
        print("⬆️  ⬇️  Navegar  │  ENTER Seleccionar  │  ESC Cancelar")
        print(f"{'='*70}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# INTERFAZ INTERACTIVA
# ═══════════════════════════════════════════════════════════════════════════════

def interactive_search(items: Dict, search_fields: Dict = None, columns: List[str] = None) -> Optional[str]:
    """
    Interfaz interactiva de búsqueda en vivo.
    
    Args:
        items: Diccionario de items a buscar
        search_fields: Campos a buscar y pesos
        columns: Columnas a mostrar
    
    Returns:
        El ID del item seleccionado o None si se cancela
    """
    query = ""
    selected_idx = 0
    
    # Mostrar interfaz inicial
    filtered = search_items(items, query, search_fields)
    print_search_interface(query, filtered, columns, selected_idx)
    
    while True:
        try:
            # Capturar tecla
            ch = get_single_char()
            
            if ch is None:
                continue
            
            # Tecla ESC (27 en ASCII = '\x1b')
            if ch == '\x1b' or (len(ch) > 0 and ord(ch[0]) == 27):
                # ESC simple - cancelar búsqueda
                if len(ch) == 1:
                    return None
                # Secuencia de escape (Windows: \x00 o \xe0 + código)
                elif len(ch) > 1:
                    # En Windows, las flechas vienen como \x00 + código o \xe0 + código
                    second_byte = ord(ch[1]) if len(ch) > 1 else 0
                    # Códigos de flechas en Windows:
                    # 72 = arriba, 80 = abajo, 75 = izquierda, 77 = derecha
                    if second_byte == 72:  # Flecha arriba
                        selected_idx = max(0, selected_idx - 1)
                        filtered = search_items(items, query, search_fields)
                        print_search_interface(query, filtered, columns, selected_idx)
                    elif second_byte == 80:  # Flecha abajo
                        filtered = search_items(items, query, search_fields)
                        selected_idx = min(len(filtered) - 1, selected_idx + 1)
                        print_search_interface(query, filtered, columns, selected_idx)
            
            # Tecla ENTER
            elif ord(ch[0]) == 13:
                filtered = search_items(items, query, search_fields)
                if filtered and selected_idx < len(filtered):
                    return filtered[selected_idx][0]
                return None
            
            # Tecla BACKSPACE
            elif ord(ch[0]) == 8 or ord(ch[0]) == 127:
                query = query[:-1]
                selected_idx = 0  # Reset selección al borrar
                # Actualizar resultados y pantalla
                filtered = search_items(items, query, search_fields)
                print_search_interface(query, filtered, columns, selected_idx)
            
            # Caracteres normales (letras, números, espacios, etc.)
            elif ch[0].isprintable():
                query += ch[0]
                selected_idx = 0  # Reset selección al escribir
                # Actualizar resultados y pantalla
                filtered = search_items(items, query, search_fields)
                print_search_interface(query, filtered, columns, selected_idx)
        
        except KeyboardInterrupt:
            return None
        except Exception:
            continue


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES PÚBLICAS
# ═══════════════════════════════════════════════════════════════════════════════

def search_and_select_tools(tools: Dict, tool_groups: Dict = None) -> Optional[str]:
    """
    Búsqueda interactiva de herramientas.
    
    Args:
        tools: Diccionario de herramientas (TOOLS)
        tool_groups: Diccionario de grupos (TOOL_GROUPS)
    
    Returns:
        ID de la herramienta seleccionada o None
    """
    search_fields = {
        "name": 2.0,
        "description": 1.0,
        "group": 1.2
    }
    
    columns = ["#", "Grupo", "Herramienta", "Descripción"]
    
    return interactive_search(tools, search_fields, columns)


def search_and_select_platforms(platforms: Dict) -> Optional[str]:
    """
    Búsqueda interactiva de plataformas.
    
    Args:
        platforms: Diccionario de plataformas (PLATFORMS)
    
    Returns:
        ID de la plataforma seleccionada o None
    """
    search_fields = {
        "name": 2.0,
        "description": 1.0,
        "short": 1.5
    }
    
    columns = ["#", "Plataforma", "Descripción"]
    
    return interactive_search(platforms, search_fields, columns)


def search_and_select_scripts(scripts: Dict) -> Optional[str]:
    """
    Búsqueda interactiva de scripts.
    
    Args:
        scripts: Diccionario de scripts (SCRIPTS)
    
    Returns:
        ID del script seleccionado o None
    """
    search_fields = {
        "name": 2.0,
        "description": 1.0
    }
    
    columns = ["#", "Script", "Descripción"]
    
    return interactive_search(scripts, search_fields, columns)
