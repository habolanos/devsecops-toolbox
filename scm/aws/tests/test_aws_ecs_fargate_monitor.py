"""
Tests unitarios para aws_ecs_fargate_metrics_monitor.py
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from cloudwatch.aws_ecs_fargate_metrics_monitor import (
    get_ecs_services,
    get_service_info,
    print_table,
)


class TestGetEcsServices:
    """Tests para get_ecs_services."""

    @pytest.mark.unit
    @patch("cloudwatch.aws_ecs_fargate_metrics_monitor.boto3.Session")
    def test_list_services(self, mock_session):
        mock_client = MagicMock()
        mock_client.list_services.return_value = {
            "serviceArns": [
                "arn:aws:ecs:us-east-1:123456789:service/prod/api",
                "arn:aws:ecs:us-east-1:123456789:service/prod/worker"
            ]
        }
        mock_session.return_value.client.return_value = mock_client

        result = get_ecs_services("test", "us-east-1", "prod")

        assert len(result) == 2
        assert result[0]["name"] == "api"
        assert result[1]["name"] == "worker"

    @pytest.mark.unit
    @patch("cloudwatch.aws_ecs_fargate_metrics_monitor.boto3.Session")
    def test_list_services_error(self, mock_session):
        mock_client = MagicMock()
        mock_client.list_services.side_effect = Exception("No cluster")
        mock_session.return_value.client.return_value = mock_client

        result = get_ecs_services("test", "us-east-1", "prod")

        assert result == []


class TestGetServiceInfo:
    """Tests para get_service_info."""

    @pytest.mark.unit
    @patch("cloudwatch.aws_ecs_fargate_metrics_monitor.boto3.Session")
    def test_get_info_success(self, mock_session):
        mock_client = MagicMock()
        mock_client.describe_services.return_value = {
            "services": [
                {
                    "serviceName": "api",
                    "desiredCount": 2,
                    "runningCount": 2,
                    "pendingCount": 0,
                    "launchType": "FARGATE",
                    "status": "ACTIVE",
                    "taskDefinition": "arn:aws:ecs:us-east-1:123:task-definition/api:1",
                    "deploymentConfiguration": {}
                }
            ]
        }
        mock_session.return_value.client.return_value = mock_client

        result = get_service_info("test", "us-east-1", "prod", "api")

        assert result["name"] == "api"
        assert result["desired"] == 2
        assert result["running"] == 2
        assert result["launch_type"] == "FARGATE"

    @pytest.mark.unit
    @patch("cloudwatch.aws_ecs_fargate_metrics_monitor.boto3.Session")
    def test_get_info_error(self, mock_session):
        mock_client = MagicMock()
        mock_client.describe_services.side_effect = Exception("No service")
        mock_session.return_value.client.return_value = mock_client

        result = get_service_info("test", "us-east-1", "prod", "api")

        assert result["name"] == "api"


class TestPrintTable:
    """Tests para print_table."""

    @pytest.mark.unit
    def test_print_table_text(self, capsys):
        services_info = {
            "api": {"name": "api", "desired": 2, "running": 2, "pending": 0}
        }
        metrics = {
            "api": {
                "request_count": 10,
                "latency_p95_ms": 50.0,
                "cpu_percent": 45.0,
                "memory_percent": 60.0,
                "error_rate_percent": 0.5
            }
        }

        print_table("prod", "us-east-1", services_info, metrics)

        captured = capsys.readouterr()
        assert "api" in captured.out
        assert "45.0%" in captured.out
        assert "60.0%" in captured.out
