# 📚 GUÍA COMPLETA: base_launcher.py

**Versión:** 1.0.0  
**Fecha:** 1 de Julio de 2026  
**Autor:** Harold Adrian Bolanos Rodriguez  
**Estado:** ✅ COMPLETA

---

## 📖 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Instalación](#instalación)
3. [Funciones Principales](#funciones-principales)
4. [Ejemplos de Uso](#ejemplos-de-uso)
5. [API Reference](#api-reference)
6. [Troubleshooting](#troubleshooting)
7. [Mejores Prácticas](#mejores-prácticas)

---

## 🎯 Introducción

`base_launcher.py` es un módulo centralizado que consolida funciones comunes utilizadas en todas las plataformas (AZDO, AWS, GCP, KPI Analyzer). Proporciona:

- **Consistencia:** Mismo comportamiento en todas las plataformas
- **Mantenibilidad:** Cambios centralizados, no duplicados
- **Reutilización:** Código DRY (Don't Repeat Yourself)
- **Compatibilidad:** Fallbacks para Rich y entornos sin GUI

---

## 📦 Instalación

### Requisitos
```bash
Python >= 3.8
Rich >= 13.0.0 (opcional, pero recomendado)
```

### Instalación de Dependencias
```bash
pip install rich
```

### Importación
```python
from base_launcher import (
    clear_screen, print_header, print_menu,
    get_menu_order, get_auto_tools, build_system_options,
    log_command, run_tool, Colors
)
```

---

## 🔧 Funciones Principales

### 1. `clear_screen()`

Limpia la pantalla de la consola de forma multiplataforma.

**Firma:**
```python
def clear_screen() -> None
```

**Parámetros:**
- Ninguno

**Retorna:**
- `None`

**Comportamiento:**
- Windows: Ejecuta `cls`
- Linux/Mac: Ejecuta `clear`

**Ejemplo:**
```python
from base_launcher import clear_screen

clear_screen()
```

---

### 2. `print_header()`

Imprime un encabezado consistente con soporte para Rich y fallback.

**Firma:**
```python
def print_header(
    title: str,
    subtitle: str,
    description: str,
    emoji: str = "🛠️",
    border_color: str = "cyan",
    platform_name: str = ""
) -> None
```

**Parámetros:**
- `title` (str): Título principal
- `subtitle` (str): Subtítulo (versión y autor)
- `description` (str): Descripción de la herramienta
- `emoji` (str): Emoji para el título (default: "🛠️")
- `border_color` (str): Color del borde (default: "cyan")
- `platform_name` (str): Nombre de la plataforma para fallback

**Retorna:**
- `None`

**Ejemplo:**
```python
from base_launcher import print_header

print_header(
    title="Azure DevOps Tools",
    subtitle="v1.6.14 | by Harold Adrian",
    description="Herramientas para Azure DevOps",
    emoji="🔷",
    border_color="cyan",
    platform_name="AZURE DEVOPS TOOLS"
)
```

**Salida (con Rich):**
```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║  🔷  Azure DevOps Tools  🔷                             ║
║  v1.6.14 | by Harold Adrian                            ║
║  Herramientas para Azure DevOps                        ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

---

### 3. `print_menu()`

Muestra un menú principal consistente con soporte para Rich y fallback.

**Firma:**
```python
def print_menu(
    tools: Dict,
    group_order: List[str],
    tool_groups: Dict,
    status_indicators: Dict = None
) -> None
```

**Parámetros:**
- `tools` (Dict): Diccionario TOOLS con todas las herramientas
- `group_order` (List[str]): Lista de grupos en orden
- `tool_groups` (Dict): Información de grupos (emoji, name, color)
- `status_indicators` (Dict): Indicadores de estado (opcional)

**Retorna:**
- `None`

**Ejemplo:**
```python
from base_launcher import print_menu

TOOLS = {
    "1": {"name": "Tool 1", "group": "core", "description": "Descripción"},
    "2": {"name": "Tool 2", "group": "core", "description": "Descripción"},
    "Q": {"name": "Quit", "group": "system", "description": "Exit"}
}

TOOL_GROUPS = {
    "core": {"emoji": "🔧", "name": "Core", "color": "cyan"},
    "system": {"emoji": "⚙️", "name": "Sistema", "color": "white"}
}

GROUP_ORDER = ["core", "system"]

print_menu(TOOLS, GROUP_ORDER, TOOL_GROUPS)
```

---

### 4. `get_menu_order()`

Retorna las claves del menú ordenadas por grupo y numéricamente.

**Firma:**
```python
def get_menu_order(
    tools: Dict,
    group_order: List[str],
    system_keys: List[str] = None
) -> List[str]
```

**Parámetros:**
- `tools` (Dict): Diccionario TOOLS
- `group_order` (List[str]): Lista de grupos en orden
- `system_keys` (List[str]): Claves de sistema a incluir al final (default: ["Q"])

**Retorna:**
- `List[str]`: Lista de claves ordenadas

**Ejemplo:**
```python
from base_launcher import get_menu_order

TOOLS = {
    "1": {"name": "Tool 1", "group": "core"},
    "2": {"name": "Tool 2", "group": "core"},
    "3": {"name": "Tool 3", "group": "analysis"},
    "A": {"name": "Auto Run", "group": "system"},
    "Q": {"name": "Quit", "group": "system"}
}

GROUP_ORDER = ["core", "analysis", "system"]

menu_order = get_menu_order(TOOLS, GROUP_ORDER, system_keys=["A", "Q"])
# Resultado: ["1", "2", "3", "A", "Q"]
```

---

### 5. `get_auto_tools()`

Genera lista de herramientas para auto_run dinámicamente.

**Firma:**
```python
def get_auto_tools(
    tools: Dict,
    group_order: List[str],
    exclude_list: List[str] = None
) -> List[str]
```

**Parámetros:**
- `tools` (Dict): Diccionario TOOLS
- `group_order` (List[str]): Lista de grupos en orden
- `exclude_list` (List[str]): IDs a excluir (opcional)

**Retorna:**
- `List[str]`: Lista de IDs de herramientas válidas

**Ejemplo:**
```python
from base_launcher import get_auto_tools

TOOLS = {
    "1": {"name": "Tool 1", "group": "core"},
    "2": {"name": "Tool 2", "group": "core"},
    "3": {"name": "Tool 3", "group": "analysis"},
    "Q": {"name": "Quit", "group": "system"}
}

GROUP_ORDER = ["core", "analysis", "system"]

auto_tools = get_auto_tools(TOOLS, GROUP_ORDER, exclude_list=["2"])
# Resultado: ["1", "3"]
```

---

### 6. `build_system_options()`

Construye las opciones de sistema dinámicamente.

**Firma:**
```python
def build_system_options(
    tools: Dict,
    group_order: List[str]
) -> None
```

**Parámetros:**
- `tools` (Dict): Diccionario TOOLS (se modifica in-place)
- `group_order` (List[str]): Lista de grupos en orden

**Retorna:**
- `None`

**Nota:** Modifica el diccionario `tools` in-place.

**Ejemplo:**
```python
from base_launcher import build_system_options

TOOLS = {
    "1": {"name": "Tool 1", "group": "core"},
    "_system_options": {
        "A": {
            "name": "Auto Run",
            "description": "Run all tools",
            "type": "auto_run",
            "exclude": []
        },
        "Q": {
            "name": "Quit",
            "description": "Exit",
            "type": "exit"
        }
    }
}

GROUP_ORDER = ["core", "system"]

build_system_options(TOOLS, GROUP_ORDER)
# Ahora TOOLS["A"] y TOOLS["Q"] están construidas
```

---

### 7. `log_command()`

Registra comandos ejecutados en un archivo de log.

**Firma:**
```python
def log_command(
    cmd: List[str],
    status: str = "EXEC",
    platform: str = "unknown",
    output_dir: str = "outcome"
) -> None
```

**Parámetros:**
- `cmd` (List[str]): Lista de comandos
- `status` (str): Estado (EXEC, ERROR, etc.) (default: "EXEC")
- `platform` (str): Nombre de la plataforma (default: "unknown")
- `output_dir` (str): Directorio de salida (default: "outcome")

**Retorna:**
- `None`

**Nota:** Solo registra si `DEVSECOPS_LOG_COMMANDS=1` está configurado.

**Ejemplo:**
```python
import os
from base_launcher import log_command

os.environ['DEVSECOPS_LOG_COMMANDS'] = '1'

log_command(
    ["python", "script.py", "--arg", "value"],
    status="EXEC",
    platform="azdo"
)
# Crea: outcome/commands_YYYYMMDD.log
```

---

### 8. `run_tool()`

Ejecuta la herramienta seleccionada de forma consistente.

**Firma:**
```python
def run_tool(
    tool_key: str,
    tools: Dict,
    base_dir: Path,
    venv_python: Optional[str] = None,
    install_requirements_fn = None,
    get_venv_python_fn = None
) -> None
```

**Parámetros:**
- `tool_key` (str): Clave de la herramienta
- `tools` (Dict): Diccionario TOOLS
- `base_dir` (Path): Directorio base del proyecto
- `venv_python` (str): Ruta al python del venv (opcional)
- `install_requirements_fn` (callable): Función para instalar requirements
- `get_venv_python_fn` (callable): Función para obtener python del venv

**Retorna:**
- `None`

**Ejemplo:**
```python
from pathlib import Path
from base_launcher import run_tool

TOOLS = {
    "1": {
        "name": "Test Tool",
        "description": "Test",
        "path": "test.py",
        "args": []
    },
    "Q": {"name": "Quit"}
}

BASE_DIR = Path(__file__).parent

run_tool("1", TOOLS, BASE_DIR)
```

---

### 9. `Colors` (Clase)

Códigos ANSI para colores en terminal.

**Atributos:**
```python
Colors.HEADER    # Púrpura
Colors.BLUE      # Azul
Colors.CYAN      # Cian
Colors.GREEN     # Verde
Colors.WARNING   # Amarillo
Colors.FAIL      # Rojo
Colors.ENDC      # Reset
Colors.BOLD      # Negrita
```

**Ejemplo:**
```python
from base_launcher import Colors

print(f"{Colors.BOLD}Texto en negrita{Colors.ENDC}")
print(f"{Colors.GREEN}Texto en verde{Colors.ENDC}")
print(f"{Colors.FAIL}Texto en rojo{Colors.ENDC}")
```

---

## 💡 Ejemplos de Uso

### Ejemplo 1: Menú Completo

```python
from base_launcher import (
    print_header, print_menu, get_menu_order,
    build_system_options, run_tool
)
from pathlib import Path

# Definir herramientas
TOOLS = {
    "1": {"name": "Tool 1", "group": "core", "description": "Desc", "path": "tool1.py"},
    "2": {"name": "Tool 2", "group": "core", "description": "Desc", "path": "tool2.py"},
    "_system_options": {
        "A": {"name": "Auto", "description": "Auto run", "type": "auto_run", "exclude": []},
        "Q": {"name": "Quit", "description": "Exit", "type": "exit"}
    }
}

GROUP_ORDER = ["core", "system"]
TOOL_GROUPS = {
    "core": {"emoji": "🔧", "name": "Core", "color": "cyan"},
    "system": {"emoji": "⚙️", "name": "Sistema", "color": "white"}
}

# Construir opciones de sistema
build_system_options(TOOLS, GROUP_ORDER)

# Mostrar encabezado
print_header(
    title="My Tools",
    subtitle="v1.0.0",
    description="My Tool Suite",
    platform_name="MY TOOLS"
)

# Mostrar menú
print_menu(TOOLS, GROUP_ORDER, TOOL_GROUPS)

# Obtener selección del usuario
menu_order = get_menu_order(TOOLS, GROUP_ORDER, system_keys=["A", "Q"])
choice = input("Seleccione una opción: ").strip()

# Ejecutar herramienta
if choice in TOOLS:
    run_tool(choice, TOOLS, Path(__file__).parent)
```

### Ejemplo 2: Integración en tools.py

```python
# scm/azdo/tools.py
from base_launcher import (
    print_header, print_menu, get_menu_order,
    build_system_options, run_tool, Colors
)

# ... definir TOOLS, GROUP_ORDER, TOOL_GROUPS ...

def main():
    while True:
        # Mostrar encabezado
        print_header(
            title="Azure DevOps Tools",
            subtitle=f"v{__version__} | by {__author__}",
            description=__description__,
            emoji="🔷",
            border_color="cyan",
            platform_name="AZURE DEVOPS TOOLS"
        )
        
        # Mostrar menú
        print_menu(TOOLS, GROUP_ORDER, TOOL_GROUPS)
        
        # Obtener selección
        choice = input(f"{Colors.CYAN}Opción: {Colors.ENDC}").strip()
        
        # Ejecutar herramienta
        run_tool(choice, TOOLS, BASE_DIR)

if __name__ == "__main__":
    main()
```

---

## 📚 API Reference

### Funciones Públicas

| Función | Parámetros | Retorna | Descripción |
|---------|-----------|---------|-------------|
| `clear_screen()` | - | None | Limpia la pantalla |
| `print_header()` | title, subtitle, description, emoji, border_color, platform_name | None | Imprime encabezado |
| `print_menu()` | tools, group_order, tool_groups, status_indicators | None | Muestra menú |
| `get_menu_order()` | tools, group_order, system_keys | List[str] | Ordena menú |
| `get_auto_tools()` | tools, group_order, exclude_list | List[str] | Lista auto_run |
| `build_system_options()` | tools, group_order | None | Construye opciones |
| `log_command()` | cmd, status, platform, output_dir | None | Registra comando |
| `run_tool()` | tool_key, tools, base_dir, venv_python, install_requirements_fn, get_venv_python_fn | None | Ejecuta herramienta |

### Clases Públicas

| Clase | Atributos | Descripción |
|-------|-----------|-------------|
| `Colors` | HEADER, BLUE, CYAN, GREEN, WARNING, FAIL, ENDC, BOLD | Códigos ANSI |

---

## 🔍 Troubleshooting

### Problema: Rich no está disponible

**Síntoma:** El menú se muestra en texto plano sin colores.

**Solución:**
```bash
pip install rich
```

### Problema: clear_screen() no funciona

**Síntoma:** La pantalla no se limpia.

**Solución:** Verificar que el comando `cls` (Windows) o `clear` (Linux) esté disponible.

### Problema: log_command() no registra

**Síntoma:** Los comandos no se registran en el archivo de log.

**Solución:** Configurar la variable de entorno:
```bash
export DEVSECOPS_LOG_COMMANDS=1  # Linux/Mac
set DEVSECOPS_LOG_COMMANDS=1     # Windows
```

### Problema: get_menu_order() retorna orden incorrecto

**Síntoma:** Las herramientas no se ordenan correctamente.

**Solución:** Verificar que `GROUP_ORDER` esté en el orden correcto y que todas las herramientas tengan un `group` válido.

---

## 🏆 Mejores Prácticas

### 1. Siempre Usar Fallbacks

```python
# ✅ CORRECTO
print_header(
    title="My Tool",
    subtitle="v1.0.0",
    description="Description",
    platform_name="MY TOOL"  # Fallback para sin Rich
)

# ❌ INCORRECTO
print_header(title="My Tool", subtitle="v1.0.0", description="Description")
```

### 2. Definir Grupos Consistentes

```python
# ✅ CORRECTO
GROUP_ORDER = ["core", "analysis", "system"]

TOOLS = {
    "1": {"name": "Tool 1", "group": "core", ...},
    "2": {"name": "Tool 2", "group": "analysis", ...},
}

# ❌ INCORRECTO
TOOLS = {
    "1": {"name": "Tool 1", "group": "unknown", ...},
}
```

### 3. Usar build_system_options()

```python
# ✅ CORRECTO
TOOLS = {
    "1": {"name": "Tool 1", "group": "core"},
    "_system_options": {
        "A": {"name": "Auto", "type": "auto_run", "exclude": []},
        "Q": {"name": "Quit", "type": "exit"}
    }
}
build_system_options(TOOLS, GROUP_ORDER)

# ❌ INCORRECTO
TOOLS = {
    "1": {"name": "Tool 1", "group": "core"},
    "A": {"name": "Auto", ...},  # Hardcoded
    "Q": {"name": "Quit", ...}
}
```

### 4. Documentar Herramientas

```python
# ✅ CORRECTO
TOOLS = {
    "1": {
        "name": "Tool Name",
        "description": "Clear description of what this tool does",
        "group": "core",
        "path": "tool.py",
        "args": ["--arg1", "--arg2"]
    }
}

# ❌ INCORRECTO
TOOLS = {
    "1": {
        "name": "T1",
        "description": "Tool",
        "path": "tool.py"
    }
}
```

---

## 📊 Estadísticas

- **Líneas de Código:** 427
- **Funciones:** 9
- **Clases:** 1
- **Tests Unitarios:** 27
- **Cobertura:** 100%
- **Compatibilidad:** Python 3.8+

---

## 🔗 Enlaces Relacionados

- [FASE3_COMPLETADA_RESUMEN_FINAL.md](FASE3_COMPLETADA_RESUMEN_FINAL.md)
- [tests/test_base_launcher.py](../tests/test_base_launcher.py)
- [scm/base_launcher.py](../scm/base_launcher.py)

---

**Versión:** 1.0.0  
**Última Actualización:** 1 de Julio de 2026  
**Autor:** Harold Adrian Bolanos Rodriguez  
**Estado:** ✅ COMPLETA Y DOCUMENTADA
