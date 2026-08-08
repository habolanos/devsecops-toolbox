"""
DevSecOps Toolbox - Setup Wizard Unit Tests

Cobertura:
- ConfigValidator: placeholders, secciones requeridas, campos minimos
- WizardStep: metodos base (ask, confirm, show_header)
- PrecheckStep: deteccion de CLIs
- AzdoStep: validacion de org, project, pat
- GcpStep: validacion de project_id
- GlobalStep: validacion de output_dir
- SetupWizard: should_run, _load_template, _clean_metadata, _save_config
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, patch as mock_patch

from setup.validators.config_validator import ConfigValidator
from setup.steps.base_step import WizardStep
from setup.steps.precheck_step import PrecheckStep
from setup.steps.azdo_step import AzdoStep
from setup.steps.gcp_step import GcpStep
from setup.steps.azure_step import AzureStep
from setup.steps.aws_step import AwsStep
from setup.steps.dashboard_step import DashboardStep
from setup.steps.global_step import GlobalStep
from setup.wizard import SetupWizard


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfigValidator(unittest.TestCase):

    def test_valid_config_no_errors(self):
        config = {
            "azdo": {"organization_url": "https://dev.azure.com/myorg", "project": "myproject", "pat": "abc123"},
            "gcp": {"project_id": "my-project-123"},
            "global": {"output_dir": "outcome"},
        }
        errors = ConfigValidator.validate(config)
        self.assertEqual(errors, [])

    def test_placeholder_detection(self):
        config = {
            "azdo": {"organization_url": "https://dev.azure.com/<TU_ORG>", "project": "proj", "pat": "pat123"},
            "gcp": {"project_id": "my-project"},
            "global": {"output_dir": "outcome"},
        }
        errors = ConfigValidator.validate(config)
        self.assertTrue(any("placeholder" in e.lower() for e in errors))

    def test_missing_required_section(self):
        config = {
            "gcp": {"project_id": "my-project"},
            "global": {"output_dir": "outcome"},
        }
        errors = ConfigValidator.validate(config)
        self.assertTrue(any("azdo" in e for e in errors))

    def test_missing_required_field(self):
        config = {
            "azdo": {"organization_url": "https://dev.azure.com/org", "project": "proj"},
            "gcp": {"project_id": "my-project"},
            "global": {"output_dir": "outcome"},
        }
        errors = ConfigValidator.validate(config)
        self.assertTrue(any("pat" in e for e in errors))

    def test_empty_field(self):
        config = {
            "azdo": {"organization_url": "https://dev.azure.com/org", "project": "proj", "pat": ""},
            "gcp": {"project_id": "my-project"},
            "global": {"output_dir": "outcome"},
        }
        errors = ConfigValidator.validate(config)
        self.assertTrue(any("pat" in e for e in errors))

    def test_has_placeholders_true(self):
        config = {"azdo": {"pat": "<TU_PAT_TOKEN>"}}
        self.assertTrue(ConfigValidator.has_placeholders(config))

    def test_has_placeholders_false(self):
        config = {"azdo": {"pat": "real_token_123"}}
        self.assertFalse(ConfigValidator.has_placeholders(config))

    def test_has_placeholders_empty(self):
        config = {}
        self.assertFalse(ConfigValidator.has_placeholders(config))

    def test_multiple_placeholders(self):
        config = {
            "azdo": {"organization_url": "<TU_ORG>", "pat": "<TU_PAT>"},
            "gcp": {"project_id": "<TU_PROJECT>"},
            "global": {"output_dir": "outcome"},
        }
        errors = ConfigValidator.validate(config)
        self.assertTrue(len(errors) >= 1)


# ═══════════════════════════════════════════════════════════════════════════════
# AZDO STEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAzdoStep(unittest.TestCase):

    def setUp(self):
        self.console = MagicMock()
        self.template = {
            "azdo": {
                "organization_url": "https://dev.azure.com/<TU_ORG>",
                "organization": "<TU_ORG>",
                "project": "<TU_PROYECTO>",
                "pat": "<TU_PAT_TOKEN>",
                "enabled": True,
                "defaults": {"timezone": "America/Mazatlan", "threads": 8},
            }
        }

    def test_extract_org_name_from_url(self):
        self.assertEqual(AzdoStep._extract_org_name("https://dev.azure.com/myorg"), "myorg")
        self.assertEqual(AzdoStep._extract_org_name("https://dev.azure.com/myorg/"), "myorg")
        self.assertEqual(AzdoStep._extract_org_name(""), "")

    def test_validate_valid_values(self):
        step = AzdoStep(self.console, self.template)
        values = {
            "organization_url": "https://dev.azure.com/myorg",
            "project": "myproject",
            "pat": "abc123",
        }
        errors = step.validate(values)
        self.assertEqual(errors, [])

    def test_validate_missing_pat(self):
        step = AzdoStep(self.console, self.template)
        values = {
            "organization_url": "https://dev.azure.com/myorg",
            "project": "myproject",
            "pat": "",
        }
        errors = step.validate(values)
        self.assertTrue(any("PAT" in e for e in errors))

    def test_validate_placeholder_pat(self):
        step = AzdoStep(self.console, self.template)
        values = {
            "organization_url": "https://dev.azure.com/myorg",
            "project": "myproject",
            "pat": "<TU_PAT_TOKEN>",
        }
        errors = step.validate(values)
        self.assertTrue(any("PAT" in e for e in errors))

    def test_validate_invalid_url(self):
        step = AzdoStep(self.console, self.template)
        values = {
            "organization_url": "https://github.com/myorg",
            "project": "myproject",
            "pat": "abc123",
        }
        errors = step.validate(values)
        self.assertTrue(any("dev.azure.com" in e for e in errors))

    def test_validate_missing_project(self):
        step = AzdoStep(self.console, self.template)
        values = {
            "organization_url": "https://dev.azure.com/myorg",
            "project": "",
            "pat": "abc123",
        }
        errors = step.validate(values)
        self.assertTrue(any("Project" in e for e in errors))

    def test_run_returns_hydrated_values(self):
        step = AzdoStep(self.console, self.template)
        step.ask = MagicMock(side_effect=[
            "https://dev.azure.com/myorg",
            "myproject",
            "mypat123"
        ])
        result = step.run()
        self.assertEqual(result["organization_url"], "https://dev.azure.com/myorg")
        self.assertEqual(result["organization"], "myorg")
        self.assertEqual(result["project"], "myproject")
        self.assertEqual(result["pat"], "mypat123")
        self.assertTrue(result["enabled"])

    def test_run_preserves_template_defaults(self):
        step = AzdoStep(self.console, self.template)
        step.ask = MagicMock(side_effect=[
            "https://dev.azure.com/myorg",
            "myproject",
            "mypat123"
        ])
        result = step.run()
        self.assertIn("defaults", result)
        self.assertEqual(result["defaults"]["timezone"], "America/Mazatlan")


# ═══════════════════════════════════════════════════════════════════════════════
# GCP STEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGcpStep(unittest.TestCase):

    def setUp(self):
        self.console = MagicMock()
        self.template = {
            "gcp": {
                "project_id": "<TU_PROJECT_ID>",
                "region": "us-central1",
                "enabled": True,
                "credentials": {"type": "adc"},
            }
        }

    def test_validate_valid(self):
        step = GcpStep(self.console, self.template)
        errors = step.validate({"project_id": "my-project-123", "region": "us-central1"})
        self.assertEqual(errors, [])

    def test_validate_missing_project_id(self):
        step = GcpStep(self.console, self.template)
        errors = step.validate({"project_id": "", "region": "us-central1"})
        self.assertTrue(any("Project ID" in e for e in errors))

    def test_validate_placeholder_project_id(self):
        step = GcpStep(self.console, self.template)
        errors = step.validate({"project_id": "<TU_PROJECT_ID>", "region": "us-central1"})
        self.assertTrue(any("Project ID" in e for e in errors))

    def test_run_with_session(self):
        template = dict(self.template)
        template["_precheck"] = {"gcloud": {"installed": True, "session": True, "detail": "user@example.com"}}
        step = GcpStep(self.console, template)
        step._get_gcloud_project = MagicMock(return_value="auto-project-123")
        step.ask = MagicMock(side_effect=["auto-project-123", "us-central1"])
        result = step.run()
        self.assertEqual(result["project_id"], "auto-project-123")
        self.assertTrue(result["enabled"])

    def test_run_without_session(self):
        template = dict(self.template)
        template["_precheck"] = {"gcloud": {"installed": False, "session": False, "detail": "N/A"}}
        step = GcpStep(self.console, template)
        step.ask = MagicMock(side_effect=["my-manual-project", "us-central1"])
        result = step.run()
        self.assertEqual(result["project_id"], "my-manual-project")

    def test_run_preserves_credentials(self):
        step = GcpStep(self.console, self.template)
        step.ask = MagicMock(side_effect=["my-project", "us-central1"])
        result = step.run()
        self.assertIn("credentials", result)
        self.assertEqual(result["credentials"]["type"], "adc")


# ═══════════════════════════════════════════════════════════════════════════════
# AZURE STEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAzureStep(unittest.TestCase):

    def setUp(self):
        self.console = MagicMock()
        self.template = {"azure": {"subscription_id": "<TU_SUB>", "tenant_id": "<TU_TENANT>", "region": "eastus"}}

    def test_validate_valid(self):
        step = AzureStep(self.console, self.template)
        errors = step.validate({"subscription_id": "abc-123", "tenant_id": "def-456", "region": "eastus"})
        self.assertEqual(errors, [])

    def test_validate_missing_subscription(self):
        step = AzureStep(self.console, self.template)
        errors = step.validate({"subscription_id": "", "tenant_id": "def-456", "region": "eastus"})
        self.assertTrue(any("Subscription" in e for e in errors))

    def test_is_optional(self):
        step = AzureStep(self.console, self.template)
        self.assertTrue(step.optional)


# ═══════════════════════════════════════════════════════════════════════════════
# AWS STEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAwsStep(unittest.TestCase):

    def setUp(self):
        self.console = MagicMock()
        self.template = {"aws": {"profile": "default", "region": "us-east-1"}}

    def test_validate_valid(self):
        step = AwsStep(self.console, self.template)
        errors = step.validate({"profile": "default", "region": "us-east-1"})
        self.assertEqual(errors, [])

    def test_validate_missing_profile(self):
        step = AwsStep(self.console, self.template)
        errors = step.validate({"profile": "", "region": "us-east-1"})
        self.assertTrue(any("Profile" in e for e in errors))

    def test_is_optional(self):
        step = AwsStep(self.console, self.template)
        self.assertTrue(step.optional)


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD STEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardStep(unittest.TestCase):

    def setUp(self):
        self.console = MagicMock()
        self.template = {"dashboard": {"webhook_url": "<TU_WEBHOOK>", "enabled": True}}

    def test_validate_always_passes(self):
        step = DashboardStep(self.console, self.template)
        errors = step.validate({})
        self.assertEqual(errors, [])

    def test_is_optional(self):
        step = DashboardStep(self.console, self.template)
        self.assertTrue(step.optional)

    def test_run_with_webhook(self):
        step = DashboardStep(self.console, self.template)
        step.ask = MagicMock(return_value="https://webhook.example.com/123")
        result = step.run()
        self.assertEqual(result["webhook_url"], "https://webhook.example.com/123")

    def test_run_skip_webhook(self):
        step = DashboardStep(self.console, self.template)
        step.ask = MagicMock(return_value="")
        result = step.run()
        self.assertNotEqual(result.get("webhook_url"), "<TU_WEBHOOK>")


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL STEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGlobalStep(unittest.TestCase):

    def setUp(self):
        self.console = MagicMock()
        self.template = {"global": {"output_dir": "outcome", "debug": False, "log_level": "INFO"}}

    def test_validate_valid(self):
        step = GlobalStep(self.console, self.template)
        errors = step.validate({"output_dir": "outcome"})
        self.assertEqual(errors, [])

    def test_validate_missing_output_dir(self):
        step = GlobalStep(self.console, self.template)
        errors = step.validate({"output_dir": ""})
        self.assertTrue(any("directorio" in e.lower() or "output" in e.lower() for e in errors))

    def test_run_returns_values(self):
        step = GlobalStep(self.console, self.template)
        step.ask = MagicMock(return_value="outcome")
        step.confirm = MagicMock(side_effect=[False, False])
        result = step.run()
        self.assertEqual(result["output_dir"], "outcome")
        self.assertFalse(result["debug"])

    def test_run_debug_enabled(self):
        step = GlobalStep(self.console, self.template)
        step.ask = MagicMock(return_value="outcome")
        step.confirm = MagicMock(side_effect=[True, False])
        result = step.run()
        self.assertTrue(result["debug"])
        self.assertEqual(result["log_level"], "DEBUG")


# ═══════════════════════════════════════════════════════════════════════════════
# PRECHECK STEP TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPrecheckStep(unittest.TestCase):

    def setUp(self):
        self.console = MagicMock()
        self.template = {}

    def test_validate_always_empty(self):
        step = PrecheckStep(self.console, self.template)
        errors = step.validate({"gcloud": {"installed": False}})
        self.assertEqual(errors, [])

    def test_is_not_optional(self):
        step = PrecheckStep(self.console, self.template)
        self.assertFalse(step.optional)

    @patch('setup.steps.precheck_step.shutil.which')
    def test_is_installed_true(self, mock_which):
        mock_which.return_value = "/usr/bin/gcloud"
        step = PrecheckStep(self.console, self.template)
        self.assertTrue(step._is_installed("gcloud"))

    @patch('setup.steps.precheck_step.shutil.which')
    def test_is_installed_false(self, mock_which):
        mock_which.return_value = None
        step = PrecheckStep(self.console, self.template)
        self.assertFalse(step._is_installed("gcloud"))

    @patch('setup.steps.precheck_step.subprocess.run')
    def test_check_session_active(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="user@example.com")
        step = PrecheckStep(self.console, self.template)
        session, detail = step._check_session(["gcloud", "auth", "list"])
        self.assertTrue(session)
        self.assertEqual(detail, "user@example.com")

    @patch('setup.steps.precheck_step.subprocess.run')
    def test_check_session_inactive(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        step = PrecheckStep(self.console, self.template)
        session, detail = step._check_session(["gcloud", "auth", "list"])
        self.assertFalse(session)

    @patch('setup.steps.precheck_step.subprocess.run')
    def test_check_session_timeout(self, mock_run):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="gcloud", timeout=15)
        step = PrecheckStep(self.console, self.template)
        session, detail = step._check_session(["gcloud", "auth", "list"])
        self.assertFalse(session)
        self.assertEqual(detail, "Timeout")


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP WIZARD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSetupWizard(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = Path(self.tmpdir) / "config.json"
        self.template_path = Path(self.tmpdir) / "config.json.template"
        self.template_data = {
            "_info": "Template",
            "_version": "1.0.0",
            "azdo": {
                "_info": "AZDO config",
                "organization_url": "https://dev.azure.com/<TU_ORG>",
                "organization": "<TU_ORG>",
                "project": "<TU_PROYECTO>",
                "pat": "<TU_PAT_TOKEN>",
                "enabled": True,
                "defaults": {"timezone": "America/Mazatlan"},
            },
            "gcp": {
                "_info": "GCP config",
                "project_id": "<TU_PROJECT_ID>",
                "region": "us-central1",
                "enabled": True,
            },
            "global": {
                "_info": "Global",
                "output_dir": "outcome",
                "debug": False,
            },
        }
        with open(self.template_path, "w", encoding="utf-8") as f:
            json.dump(self.template_data, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_should_run_no_config(self):
        wizard = SetupWizard(self.config_path, self.template_path, console=MagicMock())
        self.assertTrue(wizard.should_run())

    def test_should_run_with_placeholders(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.template_data, f)
        wizard = SetupWizard(self.config_path, self.template_path, console=MagicMock())
        self.assertTrue(wizard.should_run())

    def test_should_not_run_complete_config(self):
        complete = {
            "azdo": {"organization_url": "https://dev.azure.com/org", "project": "proj", "pat": "real_pat"},
            "gcp": {"project_id": "real-project"},
            "global": {"output_dir": "outcome"},
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(complete, f)
        wizard = SetupWizard(self.config_path, self.template_path, console=MagicMock())
        self.assertFalse(wizard.should_run())

    def test_should_not_run_with_optional_placeholders(self):
        """Config con placeholders solo en secciones opcionales (azure, aws) no dispara wizard."""
        config_with_optional_placeholders = {
            "azdo": {"organization_url": "https://dev.azure.com/org", "project": "proj", "pat": "real_pat"},
            "gcp": {"project_id": "real-project"},
            "global": {"output_dir": "outcome"},
            "azure": {"subscription_id": "<TU_SUB>", "tenant_id": "<TU_TENANT>"},
            "aws": {"profile": "<TU_PROFILE>"},
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config_with_optional_placeholders, f)
        wizard = SetupWizard(self.config_path, self.template_path, console=MagicMock())
        self.assertFalse(wizard.should_run())

    def test_should_run_invalid_json(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write("invalid json {{{")
        wizard = SetupWizard(self.config_path, self.template_path, console=MagicMock())
        self.assertTrue(wizard.should_run())

    def test_load_template(self):
        wizard = SetupWizard(self.config_path, self.template_path, console=MagicMock())
        self.assertEqual(wizard.template["_version"], "1.0.0")
        self.assertIn("azdo", wizard.template)

    def test_load_template_missing_file(self):
        wizard = SetupWizard(self.config_path, Path("/nonexistent/template.json"), console=MagicMock())
        self.assertEqual(wizard.template, {})

    def test_clean_metadata_removes_info_keys(self):
        wizard = SetupWizard(self.config_path, self.template_path, console=MagicMock())
        config = {
            "_info": "test",
            "_version": "1.0",
            "azdo": {"_info": "azdo info", "pat": "123", "nested": {"_info": "nested"}},
            "gcp": {"project_id": "proj"},
        }
        wizard._clean_metadata(config)
        self.assertNotIn("_info", config)
        self.assertNotIn("_version", config)
        self.assertNotIn("_info", config["azdo"])
        self.assertNotIn("_info", config["azdo"]["nested"])

    def test_save_config(self):
        wizard = SetupWizard(self.config_path, self.template_path, console=MagicMock())
        config = {"azdo": {"pat": "test123"}, "global": {"output_dir": "outcome"}}
        wizard._save_config(config)
        self.assertTrue(self.config_path.exists())
        with open(self.config_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["azdo"]["pat"], "test123")

    def test_step_classes_contains_required(self):
        step_sections = [cls.section for cls in SetupWizard.STEP_CLASSES]
        self.assertIn("_precheck", step_sections)
        self.assertIn("azdo", step_sections)
        self.assertIn("gcp", step_sections)
        self.assertIn("global", step_sections)

    def test_step_classes_order_precheck_first(self):
        self.assertEqual(SetupWizard.STEP_CLASSES[0].section, "_precheck")

    def test_run_section_azdo(self):
        wizard = SetupWizard(self.config_path, self.template_path, console=MagicMock())
        wizard._save_config(dict(self.template_data))
        with patch.object(AzdoStep, 'run', return_value={"organization_url": "https://dev.azure.com/neworg", "pat": "newpat", "project": "newproj", "enabled": True}):
            with patch.object(AzdoStep, 'validate', return_value=[]):
                wizard.run_section("azdo")
        with open(self.config_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["azdo"]["pat"], "newpat")


# ═══════════════════════════════════════════════════════════════════════════════
# WIZARD STEP BASE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestWizardStepBase(unittest.TestCase):
    """Test the WizardStep abstract class methods."""

    def test_cannot_instantiate_abstract(self):
        with self.assertRaises(TypeError):
            WizardStep(MagicMock(), {})

    def test_ask_skip_optional_false(self):
        class DummyStep(WizardStep):
            name = "DUMMY"
            title = "Dummy"
            section = "dummy"
            optional = False

            def run(self):
                return {}

            def validate(self, values):
                return []

        step = DummyStep(MagicMock(), {})
        self.assertFalse(step.ask_skip())

    def test_ask_skip_optional_true_user_skips(self):
        class DummyStep(WizardStep):
            name = "DUMMY"
            title = "Dummy"
            section = "dummy"
            optional = True

            def run(self):
                return {}

            def validate(self, values):
                return []

        step = DummyStep(MagicMock(), {})
        step.confirm = MagicMock(return_value=False)
        self.assertTrue(step.ask_skip())

    def test_ask_skip_optional_true_user_configures(self):
        class DummyStep(WizardStep):
            name = "DUMMY"
            title = "Dummy"
            section = "dummy"
            optional = True

            def run(self):
                return {}

            def validate(self, values):
                return []

        step = DummyStep(MagicMock(), {})
        step.confirm = MagicMock(return_value=True)
        self.assertFalse(step.ask_skip())

    def test_run_with_validation_retries(self):
        class DummyStep(WizardStep):
            name = "DUMMY"
            title = "Dummy"
            section = "dummy"
            optional = False
            call_count = 0

            def run(self):
                self.call_count += 1
                return {"value": f"attempt_{self.call_count}"}

            def validate(self, values):
                if values.get("value") == "attempt_1":
                    return ["error on first try"]
                return []

        step = DummyStep(MagicMock(), {})
        step.confirm = MagicMock(return_value=True)
        result = step.run_with_validation()
        self.assertEqual(result["value"], "attempt_2")

    def test_run_with_validation_no_retry(self):
        class DummyStep(WizardStep):
            name = "DUMMY"
            title = "Dummy"
            section = "dummy"
            optional = False

            def run(self):
                return {"value": "ok"}

            def validate(self, values):
                return []

        step = DummyStep(MagicMock(), {})
        result = step.run_with_validation()
        self.assertEqual(result["value"], "ok")


if __name__ == "__main__":
    unittest.main()
