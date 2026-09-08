# 🔧 DEPURACIÓN Y MEJORAS: Recomendaciones para v1.7.1+

**Fecha:** 8 de Septiembre de 2026  
**Versión:** 1.0  
**Estado:** 📋 RECOMENDACIONES PARA IMPLEMENTACIÓN  
**Basado en:** Análisis de v1.6.14 (2 Julio 2026)

---

## 🎯 RESUMEN EJECUTIVO

Se han identificado **8 áreas de mejora** y **5 bugs potenciales** en la arquitectura actual. Este documento proporciona recomendaciones específicas para depuración y mejoras en futuras versiones.

---

## 🐛 BUGS POTENCIALES IDENTIFICADOS

### 1. ⚠️ SearchHistory - Archivo de Historial No Sincronizado

**Ubicación:** `scm/search_module_advanced.py:36-80`

**Problema:**
```python
def _load_from_file(self) -> None:
    """Carga el historial desde archivo."""
    try:
        history_file = Path.home() / ".devsecops_search_history"
        if history_file.exists():
            with open(history_file, 'r') as f:
                self.history = [line.strip() for line in f.readlines()][:self.max_items]
    except Exception:
        pass  # ❌ Silencia errores
```

**Impacto:** 
- Errores de lectura/escritura se silencian
- Historial puede no persistir correctamente
- Difícil de debuggear

**Recomendación:**
```python
def _load_from_file(self) -> None:
    """Carga el historial desde archivo."""
    try:
        history_file = Path.home() / ".devsecops_search_history"
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                self.history = [line.strip() for line in f.readlines()][:self.max_items]
    except FileNotFoundError:
        pass  # Archivo no existe, es normal
    except PermissionError:
        print("⚠️  No hay permisos para leer historial")
    except Exception as e:
        print(f"⚠️  Error al cargar historial: {e}")
```

---

### 2. ⚠️ ExportManager - Directorio No Validado

**Ubicación:** `scm/export_manager.py:41-52`

**Problema:**
```python
def __init__(self, tool_name: str, tool_version: str = "1.0.0"):
    self.tool_name = tool_name
    self.tool_version = tool_version
    self.output_dir = get_output_dir("outcome")  # ❌ No valida si es escribible
    self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
```

**Impacto:**
- Si el directorio no es escribible, falla silenciosamente
- No hay validación de permisos
- Archivos pueden no guardarse

**Recomendación:**
```python
def __init__(self, tool_name: str, tool_version: str = "1.0.0"):
    self.tool_name = tool_name
    self.tool_version = tool_version
    self.output_dir = get_output_dir("outcome")
    
    # Validar que el directorio es escribible
    try:
        test_file = self.output_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
    except (PermissionError, OSError) as e:
        raise RuntimeError(f"No se puede escribir en {self.output_dir}: {e}")
    
    self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
```

---

### 3. ⚠️ FuzzyMatch - Algoritmo No Optimizado

**Ubicación:** `scm/search_module.py:95-135`

**Problema:**
```python
def fuzzy_match(query: str, text: str) -> float:
    # ... código ...
    matcher = SequenceMatcher(None, query, text)
    ratio = matcher.ratio()
    return ratio if ratio >= 0.5 else 0.0  # ❌ Threshold fijo
```

**Impacto:**
- Threshold de 0.5 es arbitrario
- Puede no funcionar bien con queries cortas
- No hay configurabilidad

**Recomendación:**
```python
def fuzzy_match(query: str, text: str, min_threshold: float = 0.5) -> float:
    """
    Calcula similitud fuzzy entre query y text.
    
    Args:
        query: Texto a buscar
        text: Texto donde buscar
        min_threshold: Umbral mínimo de similitud (0-1)
    
    Returns:
        Valor entre 0 y 1 (1 = coincidencia perfecta)
    """
    if not query:
        return 1.0
    
    query = query.lower().strip()
    text = text.lower().strip()
    
    # Coincidencia exacta
    if query == text:
        return 1.0
    
    # Coincidencia exacta como substring
    if query in text:
        return 0.95
    
    # Coincidencia al inicio
    if text.startswith(query):
        return 0.90
    
    # Coincidencia de palabra completa
    words = text.split()
    for word in words:
        if word.startswith(query):
            return 0.85
    
    # Fuzzy matching con SequenceMatcher
    matcher = SequenceMatcher(None, query, text)
    ratio = matcher.ratio()
    
    # Aplicar threshold configurable
    return ratio if ratio >= min_threshold else 0.0
```

---

### 4. ⚠️ RunTool - Manejo de Errores Incompleto

**Ubicación:** `scm/base_launcher.py:325-428`

**Problema:**
```python
def run_tool(tool_key: str, tools: Dict, base_dir: Path, ...):
    # ... código ...
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al ejecutar la herramienta: {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida por el usuario.{Colors.ENDC}")
    # ❌ No maneja TimeoutExpired, FileNotFoundError, etc.
```

**Impacto:**
- Errores de timeout no se capturan
- Script no encontrado no se reporta bien
- Errores de permisos se silencian

**Recomendación:**
```python
def run_tool(tool_key: str, tools: Dict, base_dir: Path, ...):
    # ... código ...
    try:
        subprocess.run(cmd, check=True, timeout=3600)  # 1 hora timeout
    except subprocess.TimeoutExpired:
        print(f"{Colors.FAIL}Error: La herramienta tardó demasiado (timeout).{Colors.ENDC}")
    except FileNotFoundError:
        print(f"{Colors.FAIL}Error: No se encontró el script {script_path}{Colors.ENDC}")
    except PermissionError:
        print(f"{Colors.FAIL}Error: Permisos insuficientes para ejecutar {script_path}{Colors.ENDC}")
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error al ejecutar la herramienta (código {e.returncode}): {e}{Colors.ENDC}")
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Ejecución interrumpida por el usuario.{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Error inesperado: {e}{Colors.ENDC}")
```

---

### 5. ⚠️ PrintMenu - Ancho de Columnas No Adaptativo

**Ubicación:** `scm/base_launcher.py:231-276`

**Problema:**
```python
def _print_menu_rich(tools: Dict, group_order: List[str], tool_groups: Dict):
    table = Table(...)
    table.add_column("#", justify="center", style="bold white", width=4)
    table.add_column("Grupo", justify="left", width=18)  # ❌ Ancho fijo
    table.add_column("Herramienta", justify="left", style="white")
    table.add_column("Descripción", justify="left", style="dim", min_width=40)
```

**Impacto:**
- Nombres largos se cortan
- En terminales pequeñas se ve mal
- No se adapta al tamaño de pantalla

**Recomendación:**
```python
def _print_menu_rich(tools: Dict, group_order: List[str], tool_groups: Dict):
    # Obtener ancho de terminal
    import shutil
    terminal_width = shutil.get_terminal_size((80, 20)).columns
    
    # Calcular anchos adaptativos
    col_width = max(4, terminal_width // 4)
    
    table = Table(...)
    table.add_column("#", justify="center", style="bold white", width=4)
    table.add_column("Grupo", justify="left", width=min(18, col_width))
    table.add_column("Herramienta", justify="left", style="white", width=min(30, col_width))
    table.add_column("Descripción", justify="left", style="dim", min_width=20)
```

---

## 📈 MEJORAS RECOMENDADAS

### 1. 🚀 Agregar Logging Centralizado

**Ubicación:** Crear `scm/logger.py`

**Propósito:** Centralizar logging en todas las herramientas

**Implementación:**
```python
import logging
from pathlib import Path

class DevSecOpsLogger:
    """Logger centralizado para DevSecOps Toolbox."""
    
    def __init__(self, name: str, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Handler para archivo
        log_dir = Path("outcome/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_dir / f"{name}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, msg): self.logger.debug(msg)
    def info(self, msg): self.logger.info(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def critical(self, msg): self.logger.critical(msg)

# Uso
logger = DevSecOpsLogger("mi_herramienta")
logger.info("Iniciando herramienta")
```

---

### 2. 🔐 Agregar Validación de Configuración

**Ubicación:** Crear `scm/config_validator.py`

**Propósito:** Validar config.json antes de usar

**Implementación:**
```python
import json
from pathlib import Path
from typing import Dict, Optional

class ConfigValidator:
    """Valida la configuración de DevSecOps Toolbox."""
    
    REQUIRED_FIELDS = {
        "gcp": ["project_id"],
        "azure": ["subscription_id"],
        "aws": ["profile"],
        "azdo": ["pat", "organization_url"]
    }
    
    @staticmethod
    def validate(config_path: Path) -> Dict:
        """Valida config.json."""
        if not config_path.exists():
            raise FileNotFoundError(f"Config no encontrada: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Config JSON inválida: {e}")
        
        # Validar campos requeridos por plataforma
        for platform, required_fields in ConfigValidator.REQUIRED_FIELDS.items():
            if platform in config:
                for field in required_fields:
                    if field not in config[platform]:
                        raise ValueError(f"Campo requerido faltante: {platform}.{field}")
        
        return config
    
    @staticmethod
    def validate_platform(config: Dict, platform: str) -> bool:
        """Valida si una plataforma está configurada."""
        if platform not in config:
            return False
        
        required = ConfigValidator.REQUIRED_FIELDS.get(platform, [])
        return all(field in config[platform] for field in required)
```

---

### 3. 📊 Agregar Métricas de Rendimiento

**Ubicación:** Crear `scm/metrics.py`

**Propósito:** Rastrear rendimiento de herramientas

**Implementación:**
```python
import time
from typing import Callable, Any
from functools import wraps

class PerformanceMetrics:
    """Rastrear métricas de rendimiento."""
    
    def __init__(self):
        self.metrics = {}
    
    def track(self, name: str):
        """Decorador para rastrear tiempo de ejecución."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed = time.time() - start_time
                    if name not in self.metrics:
                        self.metrics[name] = []
                    self.metrics[name].append(elapsed)
            return wrapper
        return decorator
    
    def get_stats(self, name: str) -> Dict:
        """Obtener estadísticas de una métrica."""
        if name not in self.metrics:
            return {}
        
        times = self.metrics[name]
        return {
            "count": len(times),
            "total": sum(times),
            "average": sum(times) / len(times),
            "min": min(times),
            "max": max(times)
        }

# Uso
metrics = PerformanceMetrics()

@metrics.track("mi_herramienta")
def mi_herramienta():
    time.sleep(1)

mi_herramienta()
print(metrics.get_stats("mi_herramienta"))
# {'count': 1, 'total': 1.0, 'average': 1.0, 'min': 1.0, 'max': 1.0}
```

---

### 4. 🧪 Agregar Modo de Prueba

**Ubicación:** Crear `scm/test_mode.py`

**Propósito:** Ejecutar herramientas en modo de prueba

**Implementación:**
```python
import os
from typing import Optional

class TestMode:
    """Gestiona modo de prueba."""
    
    ENABLED = os.getenv("DEVSECOPS_TEST_MODE", "0") == "1"
    
    @staticmethod
    def enable():
        """Habilitar modo de prueba."""
        os.environ["DEVSECOPS_TEST_MODE"] = "1"
        TestMode.ENABLED = True
    
    @staticmethod
    def disable():
        """Deshabilitar modo de prueba."""
        os.environ["DEVSECOPS_TEST_MODE"] = "0"
        TestMode.ENABLED = False
    
    @staticmethod
    def is_enabled() -> bool:
        """Verificar si está habilitado."""
        return TestMode.ENABLED
    
    @staticmethod
    def mock_api_call(endpoint: str, **kwargs) -> dict:
        """Mock de llamada API en modo prueba."""
        if not TestMode.is_enabled():
            raise RuntimeError("Solo disponible en modo prueba")
        
        # Retornar datos de prueba
        return {
            "status": "success",
            "data": [],
            "message": "Mock data (test mode)"
        }

# Uso
TestMode.enable()
if TestMode.is_enabled():
    result = TestMode.mock_api_call("/api/endpoint")
```

---

### 5. 📝 Agregar Auditoría Completa

**Ubicación:** Crear `scm/audit.py`

**Propósito:** Rastrear todas las acciones

**Implementación:**
```python
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class AuditLog:
    """Registra auditoría de acciones."""
    
    def __init__(self, log_dir: str = "outcome/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_action(self, action: str, user: str, details: Dict[str, Any]):
        """Registra una acción."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user": user,
            "details": details
        }
        
        log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    
    def get_logs(self, action: str = None, user: str = None) -> list:
        """Obtener logs filtrados."""
        logs = []
        
        for log_file in self.log_dir.glob("audit_*.jsonl"):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    
                    if action and entry['action'] != action:
                        continue
                    if user and entry['user'] != user:
                        continue
                    
                    logs.append(entry)
        
        return logs

# Uso
audit = AuditLog()
audit.log_action(
    action="tool_executed",
    user="harold.bolanos",
    details={"tool": "pr_master_checker", "status": "success"}
)
```

---

## 🎯 PRIORIDADES DE IMPLEMENTACIÓN

### Crítica (v1.7.1)
1. ✅ Fix SearchHistory - Manejo de errores
2. ✅ Fix ExportManager - Validación de directorio
3. ✅ Fix RunTool - Manejo de errores completo

### Alta (v1.7.2)
1. ⏳ Agregar Logging Centralizado
2. ⏳ Agregar Validación de Configuración
3. ⏳ Fix FuzzyMatch - Algoritmo optimizado

### Media (v1.8.0)
1. ⏳ Agregar Métricas de Rendimiento
2. ⏳ Agregar Modo de Prueba
3. ⏳ Agregar Auditoría Completa

---

## 📊 MATRIZ DE IMPACTO

| Mejora | Impacto | Esfuerzo | Prioridad |
|--------|---------|----------|-----------|
| Fix SearchHistory | Alto | Bajo | 🔴 Crítica |
| Fix ExportManager | Alto | Bajo | 🔴 Crítica |
| Fix RunTool | Alto | Medio | 🔴 Crítica |
| Logging Centralizado | Medio | Medio | 🟠 Alta |
| Validación Config | Medio | Bajo | 🟠 Alta |
| FuzzyMatch Optimizado | Bajo | Bajo | 🟠 Alta |
| Métricas Rendimiento | Bajo | Medio | 🟡 Media |
| Modo Prueba | Bajo | Medio | 🟡 Media |
| Auditoría Completa | Medio | Alto | 🟡 Media |

---

## ✅ CHECKLIST DE DEPURACIÓN

### Antes de v1.7.1
- [ ] Revisar SearchHistory para manejo de errores
- [ ] Revisar ExportManager para validación de directorio
- [ ] Revisar RunTool para manejo de excepciones
- [ ] Ejecutar todos los tests
- [ ] Validar en Windows, Linux, macOS

### Antes de v1.8.0
- [ ] Implementar Logging Centralizado
- [ ] Implementar Validación de Configuración
- [ ] Implementar Métricas de Rendimiento
- [ ] Agregar 20+ tests nuevos
- [ ] Actualizar documentación

---

## 📞 REFERENCIAS

### Código Actual
- `scm/base_launcher.py` - 428 líneas
- `scm/export_manager.py` - 392 líneas
- `scm/search_module.py` - 446 líneas
- `scm/search_module_advanced.py` - 479 líneas

### Documentación Relacionada
- `docs/refactor_arquitectura/ANALISIS_IMPLEMENTACION_ACTUAL_v1.7.0.md`
- `docs/refactor_arquitectura/GUIA_BASE_LAUNCHER.md`
- `docs/refactor_arquitectura/GUIA_BUSQUEDA_INTERACTIVA.md`

---

## 📝 CONCLUSIÓN

El proyecto tiene una **arquitectura sólida** pero necesita **mejoras en manejo de errores** y **funcionalidades adicionales** para ser más robusto.

**Recomendación:** Implementar los 3 fixes críticos en v1.7.1 (estimado 4-6 horas) antes de agregar nuevas características.

---

**Documento:** DEPURACION_Y_MEJORAS_v1.7.0.md  
**Fecha:** 8 de Septiembre de 2026  
**Versión:** 1.0  
**Estado:** ✅ COMPLETO

