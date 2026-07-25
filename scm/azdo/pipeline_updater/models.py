"""
Modelos de datos para Pipeline Updater
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class SearchRule:
    """Regla de búsqueda en pipelines"""
    stages: List[str] = field(default_factory=list)
    tasks: List[Dict] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    artifacts: List[Dict] = field(default_factory=list)
    exact_match: bool = False  # Validar que pipeline tenga EXACTAMENTE los stages especificados


@dataclass
class UpdateRule:
    """Regla de actualización en pipelines"""
    tasks: List[Dict] = field(default_factory=list)
    variables: List[Dict] = field(default_factory=list)
    stages: List[Dict] = field(default_factory=list)


@dataclass
class TemplateMetadata:
    """Metadata de template"""
    name: str
    version: str
    description: Optional[str] = None
    comment: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class IgnoreVariableGroups:
    """Configuracion de variable groups a remover por scope"""
    global_ids: List[int] = field(default_factory=list)
    environment_ids: List[int] = field(default_factory=list)
    all_ids: List[int] = field(default_factory=list)

    def has_any(self) -> bool:
        return bool(self.global_ids or self.environment_ids or self.all_ids)

    def ids_for_global(self) -> List[int]:
        return list(set(self.global_ids + self.all_ids))

    def ids_for_environments(self) -> List[int]:
        return list(set(self.environment_ids + self.all_ids))


@dataclass
class TemplateOptions:
    """Opciones de ejecucion del template"""
    dry_run: bool = False
    rollback_on_error: bool = True
    ignore_variable_groups: IgnoreVariableGroups = field(default_factory=IgnoreVariableGroups)


@dataclass
class UpdateResult:
    """Resultado de actualización de un pipeline"""
    definition_id: int
    success: bool
    snapshot_id: str
    matches_found: int
    changes_applied: int
    changes: List[Dict] = field(default_factory=list)
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ExecutionSummary:
    """Resumen de ejecución"""
    total_pipelines: int
    successful: int
    failed: int
    total_matches: int
    total_changes: int
    total_duration: float
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    errors: List[Dict] = field(default_factory=list)


@dataclass
class Match:
    """Coincidencia encontrada en búsqueda"""
    type: str  # 'stage', 'task', 'variable', 'artifact'
    name: str
    location: str  # Ubicación en el pipeline
    object: Dict = field(default_factory=dict)
    stage_name: Optional[str] = None
