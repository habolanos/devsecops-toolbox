#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Event Tracker (opción 41) multi-proyecto

Cubre:
- Registro del stem `event_tracker` en MULTI_PROJECT_PARAM_SCRIPTS del launcher
  y declaración de --multi-project en TOOLS["41"] (fix del crash "arguments
  are required" al correr sin args).
- _resolve_time_window: --hours N vs rango ISO y error cuando falta ambos.
- Reportes con columna Project (CSV/HTML/Markdown/JSON).
- main(): consolidación multi-proyecto, aislamiento de errores por proyecto
  y archivo de salida por defecto en el outcome resuelto.
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT.parent))


def _import_module(module_path, fallback_file=None):
    """Importa módulos tolerando dependencias opcionales faltantes."""
    try:
        return importlib.import_module(module_path)
    except SystemExit:
        return None
    except Exception:
        pass
    try:
        full_path = Path(fallback_file) if fallback_file else (
            _PROJECT_ROOT / Path(*module_path.split('.')[:-1]) / (module_path.split('.')[-1] + '.py'))
        if full_path.exists():
            spec = importlib.util.spec_from_file_location(module_path, full_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except SystemExit:
        return None
    except Exception:
        pass
    return None


event_tracker = _import_module(
    "scm.gcp.event_tracker",
    fallback_file=_PROJECT_ROOT / "gcp" / "event-tracker" / "event_tracker.py")


def _load_launcher():
    """Carga scm/gcp/tools.py como módulo aislado (mismo patrón que test_gcp_tools)."""
    spec = importlib.util.spec_from_file_location(
        "gcp_tools_launcher", _PROJECT_ROOT / "gcp" / "tools.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def launcher():
    return _load_launcher()


requires_tracker = pytest.mark.skipif(event_tracker is None, reason="event_tracker requiere dependencias")


# ═══════════════════════════════════════════════════════════════════════════════
# Launcher — coherencia de la opción 41
# ═══════════════════════════════════════════════════════════════════════════════

def test_tool_41_declares_multi_project(launcher):
    tool = launcher.TOOLS["41"]
    assert "--multi-project" in tool["args"]
    assert "--component-name" in tool["args"]
    assert "--hours" in tool["args"]
    assert "--output-format" in tool["args"]


def test_tool_41_stem_in_multi_project_param_scripts(launcher):
    assert "event_tracker" in launcher.MULTI_PROJECT_PARAM_SCRIPTS


# ═══════════════════════════════════════════════════════════════════════════════
# _resolve_time_window
# ═══════════════════════════════════════════════════════════════════════════════

@requires_tracker
def test_time_window_hours_generates_iso_range():
    parser = MagicMock()
    args = SimpleNamespace(hours=6, start_time=None, end_time=None)
    start, end = event_tracker._resolve_time_window(args, parser)
    assert start.endswith('Z') and 'T' in start
    assert end.endswith('Z') and 'T' in end
    assert start < end  # ISO strings comparables


@requires_tracker
def test_time_window_explicit_range():
    parser = MagicMock()
    args = SimpleNamespace(hours=None, start_time='2026-10-01T00:00:00Z',
                           end_time='2026-10-02T00:00:00Z')
    start, end = event_tracker._resolve_time_window(args, parser)
    assert (start, end) == ('2026-10-01T00:00:00Z', '2026-10-02T00:00:00Z')


@requires_tracker
def test_time_window_missing_everything_errors():
    parser = MagicMock()
    args = SimpleNamespace(hours=None, start_time=None, end_time=None)
    event_tracker._resolve_time_window(args, parser)
    parser.error.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# Reportes con columna Project
# ═══════════════════════════════════════════════════════════════════════════════

_REAL_TRACKER = event_tracker.EventTracker if event_tracker else None


def _bare_tracker(project_id='proj-1'):
    """EventTracker sin inicializar clientes GCP/K8s (clase real, no el mock)."""
    t = _REAL_TRACKER.__new__(_REAL_TRACKER)
    t.project_id = project_id
    t.events = []
    t.correlations = []
    return t


@requires_tracker
def test_normalize_events_adds_project():
    t = _bare_tracker('proj-1')
    normalized = t._normalize_events([
        {'timestamp': '2026-10-04T10:00:00Z', 'message': 'm', 'severity': 'INFO'}
    ])
    assert normalized[0]['project'] == 'proj-1'


@requires_tracker
def test_csv_report_includes_project_column():
    t = _bare_tracker('proj-1')
    events = t._normalize_events([
        {'timestamp': 't1', 'component_name': 'svc', 'severity': 'INFO', 'message': 'm'}
    ])
    csv_out = t._generate_csv_report(events)
    assert csv_out.splitlines()[0].startswith('project,')
    assert csv_out.splitlines()[1].startswith('proj-1,')


@requires_tracker
def test_html_report_includes_project():
    t = _bare_tracker('proj-1')
    events = t._normalize_events([
        {'timestamp': 't1', 'component_name': 'svc', 'severity': 'INFO', 'message': 'm'}
    ])
    html = t._generate_html_report(events)
    assert '<th>Project</th>' in html
    assert 'proj-1' in html


@requires_tracker
def test_markdown_report_includes_project():
    t = _bare_tracker('proj-1')
    events = t._normalize_events([
        {'timestamp': 't1', 'component_name': 'svc', 'severity': 'INFO', 'message': 'm'}
    ])
    md = t._generate_markdown_report(events)
    assert '| Project |' in md
    assert 'proj-1' in md


# ═══════════════════════════════════════════════════════════════════════════════
# main() — consolidación multi-proyecto y outcome por defecto
# ═══════════════════════════════════════════════════════════════════════════════

def _fake_tracker_for(project_id, events=None, fail=False):
    """Fábrica de EventTracker mock que devuelve eventos etiquetados."""
    tracker = MagicMock()
    tracker.project_id = project_id
    tracker.correlations = []
    if fail:
        tracker.search_component_events.side_effect = RuntimeError('sin acceso')
    else:
        tracker.search_component_events.return_value = [
            {'project': project_id, 'timestamp': '2026-10-04T10:00:00Z',
             'component_name': 'svc', 'event_type': 't', 'severity': 'INFO',
             'message': f'evt-{project_id}', 'source': 's', 'metadata': {}}
        ]
        # El formateo del reporte lo hace un tracker real sin clientes
        tracker.generate_report.side_effect = (
            lambda events, format, _p=project_id:
            _bare_tracker(_p).generate_report(events, format))
    return tracker


def _run_main(argv, trackers, tmp_path):
    """Ejecuta main() con trackers simulados y outcome en tmp_path."""
    created = []

    def _tracker_factory(project_id, credentials_file=None):
        t = trackers[project_id]
        created.append(project_id)
        return t

    with patch.object(event_tracker, 'EventTracker', side_effect=_tracker_factory), \
         patch.object(event_tracker, 'resolve_outcome_dir', return_value=tmp_path), \
         patch.object(sys, 'argv', argv):
        event_tracker.main()
    return created


@requires_tracker
def test_main_multi_project_consolidates_and_writes_file(tmp_path):
    trackers = {
        'p1': _fake_tracker_for('p1'),
        'p2': _fake_tracker_for('p2'),
    }
    argv = ['prog', '--component-name', 'svc', '--multi-project', 'p1,p2',
            '--hours', '2', '--output-format', 'json']
    created = _run_main(argv, trackers, tmp_path)

    assert created == ['p1', 'p2']
    files = list(tmp_path.glob('event_tracker_svc_*.json'))
    assert len(files) == 1
    import json as _json
    report = _json.loads(files[0].read_text(encoding='utf-8'))
    assert {e['project'] for e in report['events']} == {'p1', 'p2'}
    assert report['summary']['total_events'] == 2


@requires_tracker
def test_main_single_project_uses_project_id(tmp_path):
    trackers = {'p1': _fake_tracker_for('p1')}
    argv = ['prog', '--component-name', 'svc', '--project-id', 'p1',
            '--start-time', 'a', '--end-time', 'b', '--output-format', 'csv']
    created = _run_main(argv, trackers, tmp_path)

    assert created == ['p1']
    files = list(tmp_path.glob('event_tracker_svc_*.csv'))
    assert files and files[0].read_text().startswith('project,')


@requires_tracker
def test_main_one_failing_project_does_not_abort(tmp_path, capsys):
    trackers = {
        'p1': _fake_tracker_for('p1'),
        'bad': _fake_tracker_for('bad', fail=True),
    }
    argv = ['prog', '--component-name', 'svc', '--multi-project', 'p1,bad',
            '--hours', '1', '--output-format', 'json']
    _run_main(argv, trackers, tmp_path)

    out = capsys.readouterr().out
    assert 'proyecto(s) sin acceso' in out
    assert 'bad' in out
    files = list(tmp_path.glob('event_tracker_svc_*.json'))
    assert len(files) == 1


@requires_tracker
def test_main_requires_time_window(tmp_path):
    import argparse
    parser = argparse.ArgumentParser()
    trackers = {'p1': _fake_tracker_for('p1')}
    argv = ['prog', '--component-name', 'svc', '--project-id', 'p1']
    with patch.object(sys, 'argv', argv), \
         pytest.raises(SystemExit):
        event_tracker.main()
