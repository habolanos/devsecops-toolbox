# 📋 Guía de Migración a ExportManager

**Versión:** 1.0  
**Fecha:** 29 de Junio de 2026  
**Objetivo:** Migrar 76 herramientas a usar el módulo centralizado `export_manager.py`

---

## 📊 Resumen

```
Herramientas a migrar: 76
├─ AZDO:     27
├─ AWS:      19
├─ GCP:      22
└─ Terminal:  6 (scripts shell - no aplica)

Cambios por herramienta:
├─ Reemplazar import de funciones locales
├─ Reemplazar función export_results()
├─ Actualizar llamadas a export_results()
└─ Agregar tests
```

---

## 🔄 Patrón de Migración

### ANTES (Hardcodeado)

```python
def export_results(rows: List[Dict], output_format: str, tz_name: str) -> Optional[str]:
    outcome_dir = str(get_output_dir("outcome"))
    os.makedirs(outcome_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if output_format == "json":
        filepath = os.path.join(outcome_dir, f"tool_name_{ts}.json")
        payload = {
            "metadata": {
                "tool": "tool_name",
                "version": __version__,
                "generated_at": datetime.now(ZoneInfo(tz_name)).isoformat(),
            },
            "total": len(rows),
            "data": rows,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return filepath
    
    # ... más código para CSV y Excel ...
```

### DESPUÉS (Usando ExportManager)

```python
from export_manager import ExportManager

def export_results(rows: List[Dict], output_format: str, tz_name: str) -> Optional[str]:
    manager = ExportManager("tool_name", __version__)
    
    metadata = {
        # Metadatos adicionales específicos de la herramienta
    }
    
    summary = {
        "total": len(rows),
        # Resumen adicional específico
    }
    
    if output_format == "json":
        return manager.export_json(rows, metadata, summary, timezone=tz_name)
    elif output_format == "csv":
        return manager.export_csv(rows)
    elif output_format == "excel":
        return manager.export_excel(rows, sheet_name="Data", metadata=metadata, summary=summary)
    
    return None
```

---

## 📝 Pasos de Migración

### 1. Agregar Import

```python
from export_manager import ExportManager
```

### 2. Reemplazar Función

Reemplazar la función `export_results()` completa con la versión simplificada.

### 3. Actualizar Llamadas

```python
# ANTES
filepath = export_results(rows, args.output, tz_name)

# DESPUÉS
filepath = export_results(rows, args.output, tz_name)
# (La función sigue siendo la misma, solo internamente usa ExportManager)
```

### 4. Agregar Tests

Crear tests para validar que la exportación funciona correctamente.

---

## 🎯 Ejemplo Completo: azdo_pr_master_checker.py

### Paso 1: Agregar Import

```python
from export_manager import ExportManager
```

### Paso 2: Reemplazar Función

```python
def export_results(rows: List[Dict], output_format: str, script_dir: str, stage_name: str, tz_name: str) -> Optional[str]:
    manager = ExportManager("azdo_pr_master_checker", __version__)
    
    metadata = {
        "stage_searched": stage_name,
    }
    
    summary = {
        "total": len(rows),
    }
    
    if output_format == "json":
        return manager.export_json(rows, metadata, summary, timezone=tz_name)
    elif output_format == "csv":
        return manager.export_csv(rows)
    elif output_format == "excel":
        return manager.export_excel(rows, sheet_name="PRs", metadata=metadata, summary=summary)
    
    return None
```

### Paso 3: Validar Llamadas

```python
# En main()
filepath = export_results(rows, args.output, script_dir, args.stage_name, tz_name)
if filepath:
    print(f"✅ Exportado: {filepath}")
```

---

## 📋 Checklist de Migración

### AZDO (27 herramientas)

- [ ] 1. azdo_pr_master_checker.py
- [ ] 2. azdo_branch_policy_checker.py
- [ ] 3. azdo_release_cd_health.py
- [ ] 4. azdo_pipeline_drift.py
- [ ] 5. azdo_release_deep_dive.py
- [ ] 6. azdo_task_validator.py
- [ ] 7. azdo_pipeline_logs_scanner.py
- [ ] 8. azdo_repo_vulnerabilities_scanner.py
- [ ] 9. azdo_cicd_inventory_ci_detailed.py
- [ ] 10. azdo_gke_pipelines_inventory.py
- [ ] 11. azdo_pending_approvals.py
- [ ] 12. azdo_branches_created.py
- [ ] 13. azdo_release_explorer_rich.py
- [ ] 14. azdo_pr_pipeline_analyzer.py
- [ ] 15. azdo_branch_lock_checker.py
- [ ] 16. azdo_cicd_inventory_cd_detailed.py
- [ ] 17. azdo_pipeline_health_score.py
- [ ] 18. azdo_update_pipeline_cd_branchconfig.py
- [ ] 19. azdo_rollback_pipeline.py
- [ ] 20. azdo_pipeline_updater.py
- [ ] 21. azdo_release_updater.py
- [ ] 22. azdo_pipeline_validator.py
- [ ] 23. azdo_release_validator.py
- [ ] 24. azdo_policy_enforcer.py
- [ ] 25. azdo_compliance_checker.py
- [ ] 26. azdo_security_scanner.py
- [ ] 27. azdo_audit_logger.py

### GCP (22 herramientas)

- [ ] 1. gcp_monitoring_checker.py
- [ ] 2. gcp_iam_auditor.py
- [ ] 3. gcp_security_scanner.py
- [ ] 4. gcp_database_checker.py
- [ ] 5. gcp_network_analyzer.py
- [ ] 6. gcp_kubernetes_auditor.py
- [ ] 7. gcp_artifact_scanner.py
- [ ] 8. gcp_inventory_generator.py
- [ ] 9. gcp_reports_viewer.py
- [ ] 10-22. (Más herramientas GCP)

### AWS (19 herramientas)

- [ ] 1. aws_monitoring_checker.py
- [ ] 2. aws_iam_auditor.py
- [ ] 3. aws_security_scanner.py
- [ ] 4. aws_database_checker.py
- [ ] 5. aws_network_analyzer.py
- [ ] 6. aws_kubernetes_auditor.py
- [ ] 7. aws_artifact_scanner.py
- [ ] 8. aws_inventory_generator.py
- [ ] 9. aws_reports_viewer.py
- [ ] 10-19. (Más herramientas AWS)

---

## 🧪 Testing

### Test Básico

```python
import pytest
from export_manager import ExportManager

def test_export_json():
    manager = ExportManager("test_tool", "1.0.0")
    data = [{"id": 1, "name": "Test"}]
    
    filepath = manager.export_json(data)
    assert filepath is not None
    assert filepath.endswith(".json")
    
    # Validar contenido
    import json
    with open(filepath) as f:
        payload = json.load(f)
    
    assert "metadata" in payload
    assert "data" in payload
    assert len(payload["data"]) == 1
```

---

## 📊 Beneficios

```
Antes:
├─ 76 × 50 líneas = 3,800 líneas de código duplicado
├─ 76 puntos de cambio para actualizaciones
├─ Inconsistencias entre herramientas
└─ Difícil de mantener

Después:
├─ 1 módulo centralizado (392 líneas)
├─ 1 punto de cambio para actualizaciones
├─ Consistencia 100%
└─ Fácil de mantener y extender
```

---

## 🔗 Referencias

- `scm/export_manager.py` - Módulo centralizado
- `GUIA_ESTANDARIZACION_JSON.md` - Guía de estandarización
- `PLAN_IMPLEMENTACION_ESTANDARIZACION.md` - Plan detallado

---

**Estado:** En Progreso  
**Próximo Paso:** Migrar herramientas AZDO (Semana 1)
