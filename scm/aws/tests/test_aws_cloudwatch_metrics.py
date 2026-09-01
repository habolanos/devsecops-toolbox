"""
Tests unitarios para aws_cloudwatch_metrics.py
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from cloudwatch.aws_cloudwatch_metrics import (
    _format_percentage,
    _get_cloudwatch_client,
    _get_metric_statistics,
    get_ecs_fargate_usage_metrics,
    get_ecs_fargate_metrics_parallel,
)


class TestFormatPercentage:
    """Tests para _format_percentage."""

    @pytest.mark.unit
    def test_format_percentage_valid(self):
        assert _format_percentage(45.23) == "45.2%"

    @pytest.mark.unit
    def test_format_percentage_none(self):
        assert _format_percentage(None) == "N/A"

    @pytest.mark.unit
    def test_format_percentage_zero(self):
        assert _format_percentage(0.0) == "0.0%"


class TestGetCloudWatchClient:
    """Tests para _get_cloudwatch_client."""

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics.boto3.Session")
    def test_get_client_success(self, mock_session):
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client

        result = _get_cloudwatch_client(profile="test", region="us-east-1")

        assert result is mock_client
        mock_session.assert_called_once_with(profile_name="test")

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics.boto3.Session")
    def test_get_client_failure(self, mock_session):
        mock_session.side_effect = Exception("No credentials")

        result = _get_cloudwatch_client(profile="test", region="us-east-1")

        assert result is None


class TestGetMetricStatistics:
    """Tests para _get_metric_statistics."""

    @pytest.mark.unit
    def test_metric_success(self):
        cloudwatch = MagicMock()
        cloudwatch.get_metric_statistics.return_value = {
            "Datapoints": [
                {"Timestamp": MagicMock(), "Average": 42.5}
            ]
        }

        result = _get_metric_statistics(
            cloudwatch,
            "AWS/ECS",
            "CPUUtilization",
            [{"Name": "ClusterName", "Value": "prod"}],
            "Average"
        )

        assert result == 42.5

    @pytest.mark.unit
    def test_metric_no_datapoints(self):
        cloudwatch = MagicMock()
        cloudwatch.get_metric_statistics.return_value = {"Datapoints": []}

        result = _get_metric_statistics(
            cloudwatch,
            "AWS/ECS",
            "CPUUtilization",
            [{"Name": "ClusterName", "Value": "prod"}],
            "Average"
        )

        assert result is None

    @pytest.mark.unit
    def test_metric_cloudwatch_none(self):
        result = _get_metric_statistics(
            None,
            "AWS/ECS",
            "CPUUtilization",
            [{"Name": "ClusterName", "Value": "prod"}],
            "Average"
        )

        assert result is None


class TestEcsFargateUsageMetrics:
    """Tests para get_ecs_fargate_usage_metrics."""

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics._get_cloudwatch_client")
    @patch("cloudwatch.aws_cloudwatch_metrics._get_metric_statistics")
    def test_get_metrics_success(self, mock_get_stats, mock_get_client):
        cloudwatch = MagicMock()
        mock_get_client.return_value = cloudwatch
        mock_get_stats.side_effect = [10.0, 0.05, 45.0, 60.0, 1.0, 0.0]

        result = get_ecs_fargate_usage_metrics(
            cluster="prod",
            service_name="api",
            profile="test",
            region="us-east-1"
        )

        assert result["request_count"] == 10
        assert result["cpu_percent"] == 45.0
        assert result["memory_percent"] == 60.0
        assert result["status"] == "success"

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics._get_cloudwatch_client")
    def test_get_metrics_no_client(self, mock_get_client):
        mock_get_client.return_value = None

        result = get_ecs_fargate_usage_metrics(
            cluster="prod",
            service_name="api"
        )

        assert result["status"] == "unavailable"
        assert result["request_count"] is None


class TestEcsFargateMetricsParallel:
    """Tests para get_ecs_fargate_metrics_parallel."""

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics.get_ecs_fargate_usage_metrics")
    def test_parallel_empty(self, mock_get):
        result = get_ecs_fargate_metrics_parallel(
            cluster="prod",
            services=[]
        )

        assert result == {}

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics.get_ecs_fargate_usage_metrics")
    def test_parallel_services(self, mock_get):
        mock_get.return_value = {
            "request_count": 5,
            "cpu_percent": 30.0,
            "status": "success"
        }

        services = [{"name": "api"}, {"name": "worker"}]
        result = get_ecs_fargate_metrics_parallel(
            cluster="prod",
            services=services
        )

        assert "api" in result
        assert "worker" in result
        assert result["api"]["request_count"] == 5
