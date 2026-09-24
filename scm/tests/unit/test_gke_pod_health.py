#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests — Estado de salud GKE considerando pods not_running > running

Cubre:
- gcp_monitor.get_health_status: escalado a ADVERTENCIA cuando hay más pods
  no running que running, sin degradar CRÍTICO ni alterar SIN DATOS con pods sanos.
- generate_gcp_dashboard.compute_health_status: misma regla para el dashboard HTML.
- generate_gcp_dashboard._build_gke_row: integración de pods en la fila GKE.
"""

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT.parent))


def _import_module(module_path):
    """Importa módulos tolerando dependencias opcionales faltantes."""
    try:
        return importlib.import_module(module_path)
    except SystemExit:
        return None
    except Exception:
        pass
    try:
        parts = module_path.split('.')
        rel_path = Path(*parts[:-1]) / (parts[-1] + '.py')
        full_path = _PROJECT_ROOT / rel_path
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


gcp_monitor = _import_module("scm.gcp.monitoring.gcp_monitor")
dashboard = _import_module("scm.gcp.monitoring.generate_gcp_dashboard")

requires_monitor = pytest.mark.skipif(gcp_monitor is None, reason="gcp_monitor requiere dependencias")
requires_dashboard = pytest.mark.skipif(dashboard is None, reason="generate_gcp_dashboard requiere dependencias")


# ═══════════════════════════════════════════════════════════════════════════════
# gcp_monitor.get_health_status
# ═══════════════════════════════════════════════════════════════════════════════

@requires_monitor
class TestGetHealthStatusPods:
    def test_not_running_mayor_que_running_escala_a_advertencia(self):
        """Caso reportado: 104 running vs 123 not running con CPU/MEM bajos."""
        result = gcp_monitor.get_health_status(
            4.1, 34.1, pods_running=104, pods_not_running=123
        )
        assert result == '🟡 ADVERTENCIA'

    def test_not_running_menor_que_running_no_altera_ok(self):
        result = gcp_monitor.get_health_status(
            4.1, 34.1, pods_running=104, pods_not_running=2
        )
        assert result == '🟢 OK'

    def test_not_running_igual_a_running_no_altera_ok(self):
        result = gcp_monitor.get_health_status(
            10.0, 20.0, pods_running=50, pods_not_running=50
        )
        assert result == '🟢 OK'

    def test_pods_alert_no_degrada_critico(self):
        """Si CPU/MEM ya está crítico, se mantiene CRÍTICO (no baja a ADVERTENCIA)."""
        result = gcp_monitor.get_health_status(
            95.0, 10.0, pods_running=1, pods_not_running=99
        )
        assert result == '🔴 CRÍTICO'

    def test_sin_datos_metricas_con_pods_alert_da_advertencia(self):
        """Sin métricas CPU/MEM pero con pods fallando la mayoría → ADVERTENCIA."""
        result = gcp_monitor.get_health_status(
            None, None, pods_running=0, pods_not_running=5
        )
        assert result == '🟡 ADVERTENCIA'

    def test_sin_datos_metricas_sin_pods_alert_da_sin_datos(self):
        result = gcp_monitor.get_health_status(
            None, None, pods_running=10, pods_not_running=0
        )
        assert result == '⚪ SIN DATOS'

    def test_pods_na_se_ignoran(self):
        """Autopilot/kubectl fallido entrega 'N/A': no debe romper ni alertar."""
        result = gcp_monitor.get_health_status(
            10.0, 20.0, pods_running='N/A', pods_not_running='N/A'
        )
        assert result == '🟢 OK'

    def test_pods_none_se_ignoran(self):
        result = gcp_monitor.get_health_status(
            10.0, 20.0, pods_running=None, pods_not_running=None
        )
        assert result == '🟢 OK'

    def test_cero_pods_en_ambos_lados_no_alerta(self):
        result = gcp_monitor.get_health_status(
            10.0, 20.0, pods_running=0, pods_not_running=0
        )
        assert result == '🟢 OK'

    def test_sin_argumentos_pods_compatibilidad(self):
        """La firma vieja (sin pods) sigue comportándose igual."""
        assert gcp_monitor.get_health_status(50.0, 50.0) == '🟢 OK'
        assert gcp_monitor.get_health_status(80.0, 10.0) == '🟡 ADVERTENCIA'
        assert gcp_monitor.get_health_status(95.0, 10.0) == '🔴 CRÍTICO'
        assert gcp_monitor.get_health_status(None, None) == '⚪ SIN DATOS'


# ═══════════════════════════════════════════════════════════════════════════════
# generate_gcp_dashboard.compute_health_status
# ═══════════════════════════════════════════════════════════════════════════════

@requires_dashboard
class TestComputeHealthStatusPods:
    def test_not_running_mayor_que_running_da_advertencia(self):
        result = dashboard.compute_health_status(
            4.1, 34.1, pods_running=104, pods_not_running=123
        )
        assert result == 'ADVERTENCIA'

    def test_not_running_menor_que_running_da_ok(self):
        result = dashboard.compute_health_status(
            4.1, 34.1, pods_running=104, pods_not_running=2
        )
        assert result == 'OK'

    def test_pods_alert_no_degrada_critico(self):
        result = dashboard.compute_health_status(
            95.0, 10.0, pods_running=1, pods_not_running=99
        )
        assert result == 'CRÍTICO'

    def test_sin_datos_con_pods_alert_da_advertencia(self):
        result = dashboard.compute_health_status(
            None, None, pods_running=0, pods_not_running=5
        )
        assert result == 'ADVERTENCIA'

    def test_pods_na_no_rompen(self):
        result = dashboard.compute_health_status(
            10.0, 20.0, pods_running='N/A', pods_not_running='N/A'
        )
        assert result == 'OK'

    def test_compatibilidad_firma_antigua(self):
        assert dashboard.compute_health_status(50.0, 50.0) == 'OK'
        assert dashboard.compute_health_status(80.0, 10.0) == 'ADVERTENCIA'
        assert dashboard.compute_health_status(95.0, 10.0) == 'CRÍTICO'
        assert dashboard.compute_health_status(None, None) == 'SIN DATOS'


# ═══════════════════════════════════════════════════════════════════════════════
# generate_gcp_dashboard._build_gke_row (integración)
# ═══════════════════════════════════════════════════════════════════════════════

@requires_dashboard
class TestBuildGkeRowPods:
    def _cluster(self, running, not_running, cpu=4.1, mem=34.1):
        return {
            'name': 'gke-test',
            'location': 'us-central1',
            'status': 'RUNNING',
            'currentMasterVersion': '1.34.9-gke.1',
            'releaseChannel': {'channel': 'STABLE'},
            'usage_metrics': {
                'cpu_used_percent': cpu,
                'memory_used_percent': mem,
            },
            'pods_running': running,
            'pods_not_running': not_running,
        }

    def test_fila_con_mayoria_pods_fallando_es_advertencia(self):
        row = dashboard._build_gke_row('cpl-test-dev-01012024', self._cluster(104, 123))
        assert row['health'] == 'ADVERTENCIA'
        assert row['pods'] == 104
        assert row['not_running'] == 123

    def test_fila_con_pods_sanos_es_ok(self):
        row = dashboard._build_gke_row('cpl-test-dev-01012024', self._cluster(104, 2))
        assert row['health'] == 'OK'

    def test_fila_sin_pods_conserva_logica_cpu_mem(self):
        cluster = self._cluster(None, None)
        del cluster['pods_running']
        del cluster['pods_not_running']
        row = dashboard._build_gke_row('cpl-test-dev-01012024', cluster)
        assert row['health'] == 'OK'
