"""
GCP Event Tracker - Rastreo de eventos y caídas de servicio

Módulo para rastrear eventos, caídas de servicio e interrupciones en componentes
Cloud Run y Kubernetes en Google Cloud Platform.

Características:
- Búsqueda multi-fuente (Cloud Logging, Monitoring, Audit Logs, Kubernetes Events)
- Normalización y deduplicación de eventos
- Correlación automática de eventos relacionados
- Análisis de causa raíz
- Reportería en JSON, CSV, HTML, Markdown

Uso:
    from event_tracker import EventTracker
    
    tracker = EventTracker(project_id="my-project")
    events = tracker.search_component_events(
        component_name="my-service",
        start_time="2026-07-13T00:00:00Z",
        end_time="2026-07-14T00:00:00Z"
    )
    report = tracker.generate_report(events, format="html")
"""

__version__ = "1.0.0"
__author__ = "DevSecOps Team"
__description__ = "GCP Event Tracker - Rastreo de eventos y caídas de servicio"

from .event_tracker import EventTracker

__all__ = ['EventTracker']
