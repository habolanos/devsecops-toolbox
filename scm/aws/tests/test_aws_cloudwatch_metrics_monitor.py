"""
Tests unitarios para aws_cloudwatch_metrics_monitor.py
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from cloudwatch.aws_cloudwatch_metrics_monitor import (
    CloudWatchMetricsMonitor,
    _is_tty,
)


class TestIsTty:
    """Tests para _is_tty."""

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics_monitor.sys.stdout")
    def test_is_tty_true(self, mock_stdout):
        mock_stdout.isatty.return_value = True
        assert _is_tty() is True

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics_monitor.sys.stdout")
    def test_is_tty_false(self, mock_stdout):
        mock_stdout.isatty.return_value = False
        assert _is_tty() is False


class TestCloudWatchMetricsMonitor:
    """Tests para CloudWatchMetricsMonitor."""

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics_monitor.boto3.Session")
    def test_initialization(self, mock_session):
        CloudWatchMetricsMonitor(profile="test", region="us-east-1")
        mock_session.assert_called_once_with(profile_name="test")

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics_monitor.boto3.Session")
    def test_get_all_metrics(self, mock_session):
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {"InstanceId": "i-123", "State": {"Name": "running"}, "InstanceType": "t2.micro", "LaunchTime": MagicMock()}
                    ]
                }
            ]
        }
        rds = MagicMock()
        rds.describe_db_instances.return_value = {"DBInstances": []}
        eks = MagicMock()
        eks.list_clusters.return_value = {"clusters": []}
        lambda_client = MagicMock()
        lambda_client.list_functions.return_value = {"Functions": []}

        session = MagicMock()
        session.client.side_effect = [None, ec2, rds, eks, lambda_client]
        mock_session.return_value = session

        monitor = CloudWatchMetricsMonitor(profile="test", region="us-east-1")
        metrics = monitor.get_all_metrics()

        assert metrics["ec2"]["total_instances"] == 1
        assert metrics["ec2"]["running"] == 1

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics_monitor.boto3.Session")
    def test_generate_consolidated_report(self, mock_session):
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [
                {"Instances": [
                    {"State": {"Name": "running"}},
                    {"State": {"Name": "stopped"}}
                ]}
            ]
        }
        rds = MagicMock()
        rds.describe_db_instances.return_value = {"DBInstances": [{}, {}]}
        eks = MagicMock()
        eks.list_clusters.return_value = {"clusters": ["c1"]}
        lambda_client = MagicMock()
        lambda_client.list_functions.return_value = {"Functions": [{}]}

        session = MagicMock()
        # __init__ consumes 5 clients (cloudwatch, ec2, rds, eks, lambda)
        # generate_consolidated_report consumes 4 more (ec2, rds, eks, lambda)
        session.client.side_effect = [None, None, None, None, None, ec2, rds, eks, lambda_client]
        mock_session.return_value = session

        monitor = CloudWatchMetricsMonitor(profile="test", region="us-east-1")
        report = monitor.generate_consolidated_report(regions=["us-east-1"])

        assert len(report["regions"]) == 1
        assert report["regions"][0]["ec2_total"] == 2
        assert report["regions"][0]["ec2_running"] == 1
        assert report["totals"]["rds_total"] == 2
        assert report["totals"]["eks_total"] == 1
        assert report["totals"]["lambda_total"] == 1

    @pytest.mark.unit
    @patch("cloudwatch.aws_cloudwatch_metrics_monitor.boto3.Session")
    def test_print_consolidated_table_text(self, mock_session, capsys):
        session = MagicMock()
        session.client.return_value = None
        mock_session.return_value = session

        monitor = CloudWatchMetricsMonitor(profile="test", region="us-east-1")
        report = {
            "profile": "test",
            "regions": [
                {"region": "us-east-1", "ec2_total": 2, "ec2_running": 1, "rds_total": 1, "eks_total": 1, "lambda_total": 1}
            ],
            "totals": {"ec2_total": 2, "ec2_running": 1, "rds_total": 1, "eks_total": 1, "lambda_total": 1},
            "skipped_regions": []
        }

        with patch("cloudwatch.aws_cloudwatch_metrics_monitor.RICH_AVAILABLE", False):
            monitor.print_consolidated_table(report)

        captured = capsys.readouterr()
        assert "us-east-1" in captured.out
