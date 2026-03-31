# 🛡️ DevSecOps Toolbox - Análisis Arquitectónico Pro

**Fecha:** 2026-03-31  
**Versión Analizada:** 1.0.0 - 1.1.0  
**Autor del Análisis:** Cascade AI Architect  

---

## 📊 Resumen Ejecutivo

El **DevSecOps Toolbox** es una suite CLI modular para Azure DevOps y GCP con ~10+ herramientas especializadas. La arquitectura actual es funcional pero presenta oportunidades significativas de mejora en **modularización**, **seguridad**, **testing** y **mantenibilidad**.

### Puntuación General

| Categoría | Puntuación | Estado |
|-----------|------------|--------|
| Arquitectura | 6.5/10 | 🟡 Mejorable |
| Seguridad | 5.5/10 | 🟠 Requiere atención |
| Código DRY | 5/10 | 🟠 Duplicación significativa |
| Testing | 3/10 | 🔴 Crítico |
| UX/CLI | 8/10 | 🟢 Bueno |
| Documentación | 7.5/10 | 🟢 Bueno |

---

## 🔴 CRÍTICO (Prioridad 1)

### 1.1 Credenciales Hardcodeadas
**Archivos afectados:** `scan_azure_devops_repos.py`, `azdo_vulnerabilities_checker.py`

```python
# ❌ PROBLEMA ACTUAL
AZDO_ORG = "Coppel-Retail"
AZDO_PROJECT = "Cadena_de_Suministros"
AZDO_PAT = os.getenv("AZDO_PAT")  # Solo PAT usa env var
```

**Riesgo:** Exposición de información organizacional, dificulta reutilización.

**✅ SOLUCIÓN:**
```python
# config.py centralizado
from pydantic_settings import BaseSettings

class AzDoSettings(BaseSettings):
    org: str = "https://dev.azure.com/MyOrg"
    project: str = "MyProject"
    pat: str  # Requerido desde env
    
    class Config:
        env_prefix = "AZDO_"
        env_file = ".env"

settings = AzDoSettings()
```

---

### 1.2 Sin Validación de Inputs
**Archivos afectados:** Todos los scripts que reciben argumentos

```python
# ❌ PROBLEMA: Sin sanitización de inputs
def get_file_content(session, org, project, repo_id, path, branch):
    url = f".../{repo_id}/items?path={path}..."  # Path injection posible
```

**✅ SOLUCIÓN:**
```python
from urllib.parse import quote

def sanitize_path(path: str) -> str:
    """Sanitiza path para evitar injection."""
    # Remover caracteres peligrosos
    dangerous = ['..', '\\', '\0', '\n', '\r']
    for char in dangerous:
        path = path.replace(char, '')
    return quote(path, safe='/')
```

---

### 1.3 Ausencia Total de Tests
**Estado actual:** 0 tests unitarios, 0 tests de integración

**Impacto:**
- Regresiones silenciosas
- Refactoring riesgoso
- Baja confianza en releases

**✅ SOLUCIÓN:**
```
tests/
├── conftest.py              # Fixtures compartidos
├── unit/
│   ├── test_api_helpers.py
│   ├── test_parsers.py
│   └── test_validators.py
├── integration/
│   └── test_azdo_api.py
└── mocks/
    └── responses/           # Mock JSON responses
```

---

## 🟠 ALTO (Prioridad 2)

### 2.1 Código Duplicado Masivo (~60%)

**Funciones duplicadas entre scripts:**

| Función | Archivos donde aparece |
|---------|----------------------|
| `get_headers()` | 5 archivos |
| `api_get()` | 4 archivos |
| `make_headers()` | 3 archivos |
| `normalize_version()` | 2 archivos |
| `clear_screen()` | 3 archivos |
| `Colors` class | 3 archivos |

**✅ SOLUCIÓN: Crear módulo común**

```python
# lib/azdo_client.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

@dataclass
class AzDoConfig:
    org_url: str
    project: str
    pat: str
    api_version: str = "7.1"
    timeout: int = 30
    max_retries: int = 3

class AzDoClient:
    """Cliente unificado para Azure DevOps API."""
    
    def __init__(self, config: AzDoConfig):
        self.config = config
        self.session = self._build_session()
    
    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers.update(self._make_headers())
        return session
    
    def _make_headers(self) -> Dict[str, str]:
        import base64
        token = base64.b64encode(f":{self.config.pat}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Any]:
        url = f"{self.config.org_url}/{self.config.project}/_apis/{endpoint}"
        params = params or {}
        params["api-version"] = self.config.api_version
        
        try:
            resp = self.session.get(url, params=params, timeout=self.config.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"API Error: {e}")
            return None
```

---

### 2.2 Sin Logging Estructurado

**Estado actual:** `print()` statements dispersos

```python
# ❌ PROBLEMA
print(f"  Error consultando rama {branch}: {e}")
print(f"Repositorio: {repo_name}")
```

**✅ SOLUCIÓN:**
```python
# lib/logging_config.py
import logging
import sys
from rich.logging import RichHandler

def setup_logging(level: str = "INFO", json_output: bool = False):
    """Configura logging con Rich o JSON."""
    
    if json_output:
        import json_log_formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(json_log_formatter.JSONFormatter())
    else:
        handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_path=False,
        )
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=[handler],
        format="%(message)s",
    )
    
    return logging.getLogger("devsecops")

# Uso en scripts
logger = setup_logging()
logger.info("Procesando repositorio", extra={"repo": repo_name})
logger.error("Error en API", exc_info=True)
```

---

### 2.3 Manejo de Errores Inconsistente

```python
# ❌ PROBLEMA: Mezcla de estrategias
except Exception as e:
    print(f"Error: {e}")        # A veces print
    return None                  # A veces return None
    continue                     # A veces continue
```

**✅ SOLUCIÓN: Error handling centralizado**
```python
# lib/errors.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ErrorCode(Enum):
    API_ERROR = "API_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"

@dataclass
class ToolError(Exception):
    code: ErrorCode
    message: str
    context: Optional[dict] = None
    
    def __str__(self):
        return f"[{self.code.value}] {self.message}"

def handle_api_error(response: requests.Response) -> None:
    """Convierte HTTP errors a ToolError."""
    if response.status_code == 401:
        raise ToolError(ErrorCode.AUTH_ERROR, "PAT inválido o expirado")
    elif response.status_code == 404:
        raise ToolError(ErrorCode.NOT_FOUND, "Recurso no encontrado")
    elif response.status_code == 429:
        raise ToolError(ErrorCode.RATE_LIMITED, "Rate limit excedido")
    elif response.status_code >= 400:
        raise ToolError(ErrorCode.API_ERROR, f"HTTP {response.status_code}")
```

---

### 2.4 Requirements.txt Incompleto

**Estado actual:**
```
requests>=2.31.0
rich>=13.7.0
pandas>=2.1.0
openpyxl>=3.1.2
matplotlib>=3.8.0
```

**Problemas:**
- Sin version pinning exacto (reproducibilidad)
- Faltan dependencias de desarrollo
- Sin separación dev/prod

**✅ SOLUCIÓN: pyproject.toml moderno**
```toml
[project]
name = "devsecops-toolbox"
version = "1.1.0"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31.0,<3.0",
    "rich>=13.7.0,<14.0",
    "pandas>=2.1.0,<3.0",
    "openpyxl>=3.1.2,<4.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    "mypy>=1.5.0",
    "ruff>=0.1.0",
    "pre-commit>=3.4.0",
]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.10"
strict = true
```

---

## 🟡 MEDIO (Prioridad 3)

### 3.1 Sin Type Hints Consistentes

```python
# ❌ Inconsistente
def get_repositories(session, org, project):  # Sin hints
    
def branch_exists(session: requests.Session, org: str, ...) -> bool:  # Con hints
```

**✅ SOLUCIÓN: Tipado completo + mypy**
```python
from typing import TypedDict, List, Optional

class Repository(TypedDict):
    id: str
    name: str
    webUrl: str
    defaultBranch: Optional[str]

def get_repositories(
    client: AzDoClient,
    project: str,
) -> List[Repository]:
    """Obtiene todos los repositorios del proyecto."""
    ...
```

---

### 3.2 CLI No Estandarizado

**Estado actual:** `argparse` manual en cada script

**✅ SOLUCIÓN: Click/Typer unificado**
```python
# cli/main.py
import typer
from rich.console import Console

app = typer.Typer(
    name="devsecops",
    help="DevSecOps Toolbox CLI",
    add_completion=True,
)
console = Console()

@app.command()
def pr_checker(
    org: str = typer.Option(..., "--org", "-o", envvar="AZDO_ORG"),
    project: str = typer.Option(..., "--project", "-p", envvar="AZDO_PROJECT"),
    pat: str = typer.Option(..., "--pat", envvar="AZDO_PAT", hide_input=True),
    output: str = typer.Option("table", "--output", "-f", help="Output format"),
):
    """Analiza PRs hacia master con pipeline CD."""
    ...

@app.command()
def policy_checker(...):
    """Audita políticas de rama."""
    ...

if __name__ == "__main__":
    app()
```

---

### 3.3 Sin Caching de Respuestas API

**Problema:** Llamadas repetidas a la misma API

**✅ SOLUCIÓN:**
```python
from functools import lru_cache
from cachetools import TTLCache
import hashlib

# Cache en memoria con TTL
api_cache = TTLCache(maxsize=1000, ttl=300)  # 5 min

def cached_api_get(client: AzDoClient, endpoint: str) -> Optional[dict]:
    cache_key = hashlib.md5(f"{client.config.org_url}{endpoint}".encode()).hexdigest()
    
    if cache_key in api_cache:
        return api_cache[cache_key]
    
    result = client.get(endpoint)
    if result:
        api_cache[cache_key] = result
    
    return result
```

---

### 3.4 Exportación de Reportes Limitada

**Estado actual:** CSV, JSON, Excel básico

**✅ MEJORAS:**
```python
# lib/exporters.py
from abc import ABC, abstractmethod
from pathlib import Path

class ReportExporter(ABC):
    @abstractmethod
    def export(self, data: pd.DataFrame, path: Path) -> None:
        pass

class ExcelExporter(ReportExporter):
    def export(self, data: pd.DataFrame, path: Path) -> None:
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            data.to_excel(writer, sheet_name='Results', index=False)
            
            # Auto-ajustar columnas
            worksheet = writer.sheets['Results']
            for column in worksheet.columns:
                max_length = max(len(str(cell.value or '')) for cell in column)
                worksheet.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)
            
            # Formato condicional para status
            from openpyxl.formatting.rule import ColorScaleRule
            # ... aplicar estilos

class HTMLExporter(ReportExporter):
    """Exporta a HTML interactivo con DataTables."""
    ...
```

---

## 🟢 BAJO (Prioridad 4)

### 4.1 Sin Progress Bars Consistentes

```python
# ✅ Ya existe parcialmente con Rich, estandarizar:
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

def with_progress(items, description="Processing"):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task(description, total=len(items))
        for item in items:
            yield item
            progress.advance(task)
```

---

### 4.2 Sin Métricas de Ejecución

**✅ SOLUCIÓN:**
```python
# lib/metrics.py
import time
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class ExecutionMetrics:
    tool_name: str
    start_time: float = field(default_factory=time.time)
    api_calls: int = 0
    errors: int = 0
    items_processed: int = 0
    
    def record_api_call(self):
        self.api_calls += 1
    
    def record_error(self):
        self.errors += 1
    
    def summary(self) -> Dict:
        return {
            "tool": self.tool_name,
            "duration_seconds": time.time() - self.start_time,
            "api_calls": self.api_calls,
            "errors": self.errors,
            "items_processed": self.items_processed,
        }
```

---

## 📁 Estructura Propuesta

```
devsecops-toolbox/
├── pyproject.toml           # Configuración moderna
├── README.md
├── .env.example             # Template de variables
├── .pre-commit-config.yaml  # Hooks de calidad
│
├── src/
│   └── devsecops/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py      # Entry point Typer
│       │   └── commands/
│       │       ├── azdo.py
│       │       └── gcp.py
│       │
│       ├── lib/
│       │   ├── __init__.py
│       │   ├── azdo_client.py
│       │   ├── gcp_client.py
│       │   ├── config.py
│       │   ├── errors.py
│       │   ├── logging.py
│       │   ├── exporters.py
│       │   └── validators.py
│       │
│       └── tools/
│           ├── azdo/
│           │   ├── pr_checker.py
│           │   ├── policy_checker.py
│           │   └── drift_analyzer.py
│           └── gcp/
│               └── ...
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
│
└── docs/
    ├── architecture.md
    └── api-reference.md
```

---

## 🚀 Roadmap de Implementación

### Fase 1: Fundamentos (1-2 semanas)
1. ✅ Crear `pyproject.toml` moderno
2. ✅ Extraer código común a `lib/`
3. ✅ Implementar `AzDoClient` unificado
4. ✅ Agregar logging estructurado
5. ✅ Configurar pre-commit hooks

### Fase 2: Calidad (1-2 semanas)
1. ⬜ Agregar type hints completos
2. ⬜ Implementar tests unitarios (>80% coverage)
3. ⬜ Configurar CI/CD (GitHub Actions)
4. ⬜ Agregar mypy strict mode

### Fase 3: Features (2-3 semanas)
1. ⬜ Migrar a Typer CLI
2. ⬜ Implementar caching de API
3. ⬜ Agregar exportación HTML
4. ⬜ Métricas de ejecución
5. ⬜ Modo watch para cambios

### Fase 4: Enterprise (Opcional)
1. ⬜ Plugin system para extensiones
2. ⬜ Dashboard web (FastAPI + HTMX)
3. ⬜ Integración con Slack/Teams
4. ⬜ Scheduling con APScheduler

---

## 📊 Matriz de Prioridad vs Esfuerzo

```
                    ESFUERZO
                Bajo    Medio    Alto
         ┌────────┬────────┬────────┐
    Alto │ 1.1    │ 2.1    │ 1.3    │
         │ 1.2    │ 2.2    │        │
IMPACTO  ├────────┼────────┼────────┤
   Medio │ 2.4    │ 2.3    │ 3.2    │
         │ 3.1    │ 3.3    │        │
         ├────────┼────────┼────────┤
    Bajo │ 4.1    │ 3.4    │ 4.2    │
         │        │        │        │
         └────────┴────────┴────────┘

Leyenda:
1.x = Crítico (rojo)
2.x = Alto (naranja)  
3.x = Medio (amarillo)
4.x = Bajo (verde)
```

---

## ✅ Quick Wins (Implementar Hoy)

1. **Mover credenciales a `.env`** - 10 min
2. **Crear `lib/azdo_client.py`** - 30 min
3. **Agregar `requirements-dev.txt`** - 5 min
4. **Configurar `.pre-commit-config.yaml`** - 10 min

---

## 📝 Conclusión

El DevSecOps Toolbox tiene una base sólida con excelente UX (Rich) y funcionalidad. Las mejoras principales se centran en:

1. **Eliminar duplicación** → Crear módulo común
2. **Mejorar seguridad** → Externalizar config, validar inputs
3. **Agregar tests** → Habilitar refactoring seguro
4. **Estandarizar CLI** → Migrar a Typer

**Esfuerzo estimado total:** 4-6 semanas para implementación completa.

---

*Generado por Cascade AI Architect - 2026-03-31*
