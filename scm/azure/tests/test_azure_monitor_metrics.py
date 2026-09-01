"""
Tests unitarios para azure_monitor_metrics.py y azure_container_apps_metrics_monitor.py
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from monitoring.azure_monitor_metrics import (
    _format_percentage,
    get_container_app_usage_metrics,
    get_container_app_metrics_parallel,
)

# container-apps tiene guión, no es importable como paquete: agregamos el dir
sys.path.insert(0, str(Path(__file__).parent.parent / "container-apps"))
import azure_container_apps_metrics_monitor as apps_monitor

from azure_container_apps_metrics_monitor import (
    _is_tty,
    get_container_apps,
    print_table,
)


class TestFormatPercentage:
    """Tests para _format_percentage."""

    @pytest.mark.unit
    def test_format_percentage_valid(self):
        assert _format_percentage(45.23) == "45.2%"

    @pytest.mark.unit
    def test_format_percentage_none(self):
        assert _format_percentage(None) == "N/A"


class TestIsTty:
    """Tests para _is_tty."""

    @pytest.mark.unit
    @patch("azure_container_apps_metrics_monitor.sys.stdout")
    def test_is_tty_true(self, mock_stdout):
        mock_stdout.isatty.return_value = True
        assert _is_tty() is True

    @pytest.mark.unit
    @patch("azure_container_apps_metrics_monitor.sys.stdout")
    def test_is_tty_false(self, mock_stdout):
        mock_stdout.isatty.return_value = False
        assert _is_tty() is False


class TestGetContainerAppUsageMetrics:
    """Tests para get_container_app_usage_metrics."""

    @pytest.mark.unit
    @patch("monitoring.azure_monitor_metrics._get_metrics_client")
    @patch("monitoring.azure_monitor_metrics._query_metric")
    def test_get_metrics_success(self, mock_query, mock_client):
        mock_client.return_value = MagicMock()
        mock_query.side_effect = [10.0, 50.0, 45.0, 60.0, 1.0]

        result = get_container_app_usage_metrics("/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.App/containerApps/app")

        assert result["request_count"] == 10
        assert result["latency_p95_ms"] == 50.0
        assert result["cpu_percent"] == 45.0
        assert result["memory_percent"] == 60.0
        assert result["status"] == "success"

    @pytest.mark.unit
    @patch("monitoring.azure_monitor_metrics._get_metrics_client")
    def test_get_metrics_unavailable(self, mock_client):
        mock_client.return_value = None

        result = get_container_app_usage_metrics("/subscriptions/xxx/resourceGroups/rg/providers/Microsoft.App/containerApps/app")

        assert result["status"] == "unavailable"


class TestGetContainerAppMetricsParallel:
    """Tests para get_container_app_metrics_parallel."""

    @pytest.mark.unit
    @patch("monitoring.azure_monitor_metrics.get_container_app_usage_metrics")
    def test_parallel_apps(self, mock_get):
        mock_get.return_value = {
            "request_count": 5,
            "cpu_percent": 30.0,
            "status": "success"
        }

        apps = [{"name": "app1", "resource_id": "/id/1"}, {"name": "app2", "resource_id": "/id/2"}]
        result = get_container_app_metrics_parallel(apps)

        assert "app1" in result
        assert "app2" in result
        assert result["app1"]["request_count"] == 5

    @pytest.mark.unit
    def test_parallel_empty(self):
        assert get_container_app_metrics_parallel([]) == {}


class TestGetContainerApps:
    """Tests para get_container_apps."""

    @pytest.mark.unit
    @patch("azure_container_apps_metrics_monitor.AZURE_AVAILABLE", False)
    def test_get_container_apps_no_azure(self):
        result = get_container_apps("sub-123")
        assert result == []


class TestPrintTable:
    """Tests para print_table."""

    @pytest.mark.unit
    def test_print_table_text(self, capsys):
        apps_info = {
            "app1": {"name": "app1", "resource_group": "rg", "location": "eastus"}
        }
        metrics = {
            "app1": {
                "request_count": 10,
                "cpu_percent": 45.0,
                "memory_percent": 60.0,
                "status": "success"
            }
        }

        with patch("azure_container_apps_metrics_monitor.RICH_AVAILABLE", False):
            print_table(apps_info, metrics)

        captured = capsys.readouterr()
        assert "app1" in captured.out
        assert "45.0" in captured.out or "45" in captured.out
