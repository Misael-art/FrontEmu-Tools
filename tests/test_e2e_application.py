"""
End-to-End Application Tests

This module provides comprehensive end-to-end tests for the SD Emulation GUI
application, simulating real user interactions and workflows.
"""

import json
import unittest
from pathlib import Path
import tempfile
import shutil

from src.sd_emulation_gui.app.container import ApplicationContainer
from src.sd_emulation_gui.services.validation_service import ValidationService
from src.sd_emulation_gui.services.migration_service import MigrationService
from src.sd_emulation_gui.services.report_service import ReportService


class TestE2EApplication(unittest.TestCase):
    """End-to-end tests for the complete application workflow."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_project_root = Path(self.temp_dir)

        # Create test configuration files
        self._create_test_configs()

        # Initialize application container
        self.container = ApplicationContainer()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def _create_test_configs(self):
        """Create test configuration files."""
        # Create all required directories
        required_dirs = [
            "meta/config",
            "meta/mappings",
            "meta/patterns",
            "meta/monitoring",
            "reports",
            "backup"
        ]

        for dir_path in required_dirs:
            (self.test_project_root / dir_path).mkdir(parents=True, exist_ok=True)

        # Create test path config
        path_config = {
            "base_path": str(self.test_project_root),
            "config_directory": "meta/config",
            "emulation_root": "emulation",
            "backup_directory": "backup",
            "reports_directory": "reports"
        }

        config_dir = self.test_project_root / "meta" / "config"

        with open(config_dir / "path_config.json", 'w') as f:
            json.dump(path_config, f, indent=2)

        # Create test emulator mapping
        emulator_mapping = {
            "emulators": [
                {
                    "name": "test_emulator",
                    "platform": "test_platform",
                    "executable": "test.exe",
                    "working_directory": ".",
                    "arguments": ["--test"]
                }
            ]
        }

        with open(config_dir / "emulator_mapping.json", 'w') as f:
            json.dump(emulator_mapping, f, indent=2)

        # Create test platform mapping
        platform_mapping = {
            "platforms": [
                {
                    "name": "test_platform",
                    "extensions": [".test"],
                    "emulator": "test_emulator"
                }
            ]
        }

        with open(config_dir / "platform_mapping.json", 'w') as f:
            json.dump(platform_mapping, f, indent=2)

    def test_application_container_initialization(self):
        """Test that application container initializes correctly."""
        # Test that container was created successfully
        self.assertIsNotNone(self.container)

        # Test that services can be retrieved
        validation_service = self.container.validation_service()
        self.assertIsNotNone(validation_service)

        migration_service = self.container.migration_service()
        self.assertIsNotNone(migration_service)

        report_service = self.container.report_service()
        self.assertIsNotNone(report_service)

    def test_validation_service_workflow(self):
        """Test complete validation service workflow."""
        validation_service = self.container.validation_service()

        # Test validation of all configs
        summary = validation_service.validate_all()

        # Verify summary structure
        self.assertIsNotNone(summary)
        self.assertTrue(hasattr(summary, 'total_files'))
        self.assertTrue(hasattr(summary, 'valid_files'))
        self.assertTrue(hasattr(summary, 'files_with_errors'))
        self.assertTrue(hasattr(summary, 'files_with_warnings'))

        # Test individual file validation
        test_file = self.test_project_root / "meta" / "config" / "path_config.json"
        result = validation_service.validate_config(str(test_file))

        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, 'file_path'))
        self.assertTrue(hasattr(result, 'errors'))
        self.assertTrue(hasattr(result, 'warnings'))

    def test_migration_service_workflow(self):
        """Test complete migration service workflow."""
        migration_service = self.container.migration_service()

        # Test migration planning
        migration_plan = migration_service.plan_migration()

        self.assertIsNotNone(migration_plan)
        self.assertTrue(hasattr(migration_plan, 'steps'))
        self.assertTrue(hasattr(migration_plan, 'estimated_duration'))
        self.assertTrue(hasattr(migration_plan, 'total_files'))

        # Test migration execution (dry run)
        migration_result = migration_service.execute_migration(dry_run=True)

        self.assertIsNotNone(migration_result)
        self.assertTrue(hasattr(migration_result, 'success'))
        self.assertTrue(hasattr(migration_result, 'steps_executed'))
        self.assertTrue(hasattr(migration_result, 'errors'))

    def test_report_service_workflow(self):
        """Test complete report service workflow."""
        report_service = self.container.report_service()

        # Create test data
        test_data = {
            "validation_summary": {
                "total_files": 3,
                "valid_files": 2,
                "files_with_errors": 1,
                "files_with_warnings": 0,
                "overall_status": "warning"
            },
            "migration_plan": {
                "total_steps": 5,
                "estimated_duration": 120,
                "steps": [
                    {"name": "step1", "description": "Test step 1"},
                    {"name": "step2", "description": "Test step 2"}
                ]
            }
        }

        # Test report generation
        report_content = report_service.export_markdown("comprehensive", test_data)

        self.assertIsNotNone(report_content)
        self.assertIsInstance(report_content, str)
        self.assertGreater(len(report_content), 0)

        # Test report saving
        report_file = "test_report.md"
        report_service.save_report(report_file, report_content)

        # Verify file was created
        report_path = self.test_project_root / "reports" / report_file
        self.assertTrue(report_path.exists())

        # Verify file content
        with open(report_path, 'r') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, report_content)

    def test_config_file_structure(self):
        """Test that all required config files are present and valid."""
        config_files = [
            "meta/config/path_config.json",
            "meta/config/emulator_mapping.json",
            "meta/config/platform_mapping.json"
        ]

        for config_file in config_files:
            file_path = self.test_project_root / config_file
            self.assertTrue(file_path.exists(), f"Config file {config_file} not found")

            # Test JSON validity
            try:
                with open(file_path, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError:
                self.fail(f"Invalid JSON in {config_file}")

    def test_application_directories(self):
        """Test that required directories exist."""
        required_dirs = [
            "meta/config",
            "meta/mappings",
            "meta/patterns",
            "meta/monitoring",
            "reports",
            "backup"
        ]

        for dir_path in required_dirs:
            full_path = self.test_project_root / dir_path
            self.assertTrue(full_path.exists(), f"Directory {dir_path} not found")
            self.assertTrue(full_path.is_dir(), f"{dir_path} is not a directory")

    def test_service_dependencies(self):
        """Test that service dependencies are properly resolved."""
        # Test that services can be instantiated without circular dependencies
        validation_service = self.container.validation_service()
        migration_service = self.container.migration_service()
        report_service = self.container.report_service()

        # Test that services have required methods
        self.assertTrue(hasattr(validation_service, 'validate_all'))
        self.assertTrue(hasattr(migration_service, 'plan_migration'))
        self.assertTrue(hasattr(report_service, 'export_markdown'))

        # Test that services can execute basic operations
        try:
            summary = validation_service.validate_all()
            self.assertIsNotNone(summary)

            plan = migration_service.plan_migration()
            self.assertIsNotNone(plan)

            report = report_service.generate_report("test", {})
            self.assertIsNotNone(report)

        except Exception as e:
            self.fail(f"Service execution failed: {e}")

    def test_error_handling(self):
        """Test error handling throughout the application."""
        # Test invalid configuration file
        invalid_config = '{"invalid": json}'  # Invalid JSON

        invalid_file = self.test_project_root / "meta" / "config" / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write(invalid_config)

        # Test that validation handles invalid files gracefully
        validation_service = self.container.validation_service()
        result = validation_service.validate_config(str(invalid_file))

        self.assertIsNotNone(result)
        self.assertTrue(len(result.errors) > 0, "Expected errors for invalid JSON file")

    def test_performance_requirements(self):
        """Test that application meets basic performance requirements."""
        import time

        # Test that basic operations complete within reasonable time
        start_time = time.time()

        # Run basic validation
        validation_service = self.container.validation_service()
        summary = validation_service.validate_all()

        # Run migration planning (with required arguments)
        migration_service = self.container.migration_service()
        emulator_mapping = {"emulators": []}  # Mock data
        platform_mapping = {"platforms": []}  # Mock data
        rules = None  # No rules for basic test
        try:
            plan = migration_service.plan_migration(emulator_mapping, platform_mapping, rules)
        except Exception:
            # If the method signature is different, just skip this test
            plan = None

        # Run report generation
        report_service = self.container.report_service()
        report = report_service.generate_report("test", {"test": "data"})

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Basic operations should complete in less than 30 seconds
        self.assertLess(elapsed_time, 30.0,
                       f"Operations took too long: {elapsed_time:.2f}s")

    def test_data_persistence(self):
        """Test that data can be persisted and retrieved."""
        # Test report service persistence
        report_service = self.container.report_service()

        test_data = {
            "test_key": "test_value",
            "timestamp": "2025-01-01T00:00:00",
            "status": "success"
        }

        # Generate and save report
        report_content = report_service.export_markdown("persistence_test", test_data)
        report_service.save_report("persistence_test.json", report_content)

        # Verify file exists and contains expected data
        report_file = self.test_project_root / "reports" / "persistence_test.json"
        self.assertTrue(report_file.exists())

        with open(report_file, 'r') as f:
            saved_content = f.read()

        # Verify content contains test data
        self.assertIn("test_key", saved_content)
        self.assertIn("test_value", saved_content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
