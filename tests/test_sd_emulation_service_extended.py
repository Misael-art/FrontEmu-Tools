"""Extended tests for SDEmulationService.

This module provides comprehensive test coverage for SDEmulationService,
focusing on document parsing, rule extraction, and compliance checking.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from domain.sd_rules import (
    ComplianceLevel,
    DirectoryStructureRule,
    PathValidationRule,
    PlatformRule,
    PortabilityRule,
    SDEmulationRules,
    StorageRule,
    SymlinkRule,
    OperationRule,
)
from sd_emulation_gui.services.sd_emulation_service import SDEmulationService


class TestSDEmulationServiceDocumentParsing(unittest.TestCase):
    """Test document parsing functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = SDEmulationService()
        self.temp_dir = tempfile.mkdtemp()
        self.test_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_rules_from_document_file_not_found(self):
        """Test parsing when document file doesn't exist."""
        with self.assertRaises(FileNotFoundError) as context:
            self.service.parse_rules_from_document("nonexistent.md")
        
        self.assertIn("Architecture document not found", str(context.exception))

    @patch("builtins.open", mock_open(read_data="# Test Document\n\nSome content"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_parse_rules_from_document_success(self, mock_exists):
        """Test successful document parsing."""
        result = self.service.parse_rules_from_document("test.md")
        
        self.assertIsInstance(result, SDEmulationRules)
        self.assertEqual(result.version, "1.0.0")
        self.assertIn("SD Emulation Architecture Rules", result.description)

    @patch("builtins.open", side_effect=PermissionError("Access denied"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_parse_rules_from_document_read_error(self, mock_exists, mock_open):
        """Test parsing when file can't be read."""
        with self.assertRaises(ValueError) as context:
            self.service.parse_rules_from_document("test.md")
        
        self.assertIn("Failed to read architecture document", str(context.exception))

    def test_extract_platform_rules_with_table(self):
        """Test platform rule extraction from table content."""
        content = """
        || Short_Name | Full_Name | Extensions |
        || nes | Nintendo Entertainment System | .nes, .fds |
        || snes | Super Nintendo | .smc, .sfc |
        || gb | Game Boy | .gb, .gbc |
        
        * End of table
        """
        
        rules = self.service._extract_platform_rules(content)
        self.assertEqual(len(rules), 3)
        
        # Check first rule (nes)
        nes_rule = rules[0]
        self.assertEqual(nes_rule.short_name, "nes")
        self.assertEqual(nes_rule.full_name, "Nintendo Entertainment System")
        # Extensions come from the common_extensions dict, not from the table
        self.assertIn(".nes", nes_rule.supported_extensions)
        
        # Check second rule (snes)
        snes_rule = rules[1]
        self.assertEqual(snes_rule.short_name, "snes")
        self.assertEqual(snes_rule.full_name, "Super Nintendo")
        
        # Check third rule (gb)
        gb_rule = rules[2]
        self.assertEqual(gb_rule.short_name, "gb")
        self.assertEqual(gb_rule.full_name, "Game Boy")

    def test_extract_platform_rules_no_table(self):
        """Test platform rule extraction when no table is found."""
        content = "# Document without platform table\n\nSome other content."
        
        rules = self.service._extract_platform_rules(content)
        
        self.assertEqual(len(rules), 0)

    def test_extract_extensions_for_platform(self):
        """Test extension extraction for known platforms."""
        # Test known platform
        extensions = self.service._extract_extensions_for_platform("", "psx")
        self.assertIn(".iso", extensions)
        self.assertIn(".cue", extensions)
        
        # Test unknown platform
        extensions = self.service._extract_extensions_for_platform("", "unknown")
        self.assertEqual(extensions, [".zip", ".7z"])

    def test_extract_deduplication_rules(self):
        """Test deduplication rule extraction."""
        content = "This document mentions deduplicação and redundancy_cleanup."
        
        rules = self.service._extract_deduplication_rules(content)
        
        self.assertEqual(len(rules), 2)
        self.assertTrue(all(rule.hash_based for rule in rules))
        self.assertTrue(all(rule.backup_duplicates for rule in rules))

    def test_extract_path_validation_rules(self):
        """Test path validation rule extraction."""
        content = "Warning: avoid C:/ and %APPDATA% and %USERPROFILE% paths."
        
        rule = self.service._extract_path_validation_rules(content)
        
        self.assertIn("C:/", rule.forbidden_patterns)
        self.assertIn("%APPDATA%", rule.forbidden_patterns)
        self.assertIn("%USERPROFILE%", rule.forbidden_patterns)
        self.assertEqual(rule.max_path_length, 260)
        self.assertFalse(rule.case_sensitive)

    def test_extract_backup_rules(self):
        """Test backup rule extraction."""
        content = "Setup backup for your saves and configs."
        
        rules = self.service._extract_backup_rules(content)
        
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertTrue(rule.compression_enabled)
        self.assertEqual(rule.retention_days, 30)
        self.assertEqual(rule.max_backup_size_gb, 10)

    def test_extract_storage_rules(self):
        """Test storage rule extraction."""
        content = "Ensure you have at least 50GB of free space."
        
        rule = self.service._extract_storage_rules(content)
        
        self.assertEqual(rule.minimum_free_space_gb, 50)
        self.assertEqual(rule.warning_threshold_gb, 10)
        self.assertEqual(rule.critical_threshold_gb, 5)
        self.assertTrue(rule.enable_deduplication)

    def test_extract_operation_rules(self):
        """Test operation rule extraction."""
        content = "Standard operation rules apply."
        
        rule = self.service._extract_operation_rules(content)
        
        self.assertTrue(rule.require_dry_run_first)
        self.assertTrue(rule.require_confirmation)
        self.assertTrue(rule.enable_rollback)
        self.assertEqual(rule.max_parallel_operations, 4)
        self.assertEqual(rule.operation_timeout_seconds, 300)
        self.assertTrue(rule.log_all_operations)


class TestSDEmulationServiceCompliance(unittest.TestCase):
    """Test compliance checking functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = SDEmulationService()
        self.temp_dir = tempfile.mkdtemp()
        self.test_path = Path(self.temp_dir)
        
        # Create sample rules
        self.sample_rules = SDEmulationRules(
            description="Test SD Emulation Rules",
            directory_structure=[
                DirectoryStructureRule(
                    path="Emulation", purpose="Core emulation", required=True
                ),
                DirectoryStructureRule(
                    path="Roms", purpose="ROM storage", required=True
                ),
            ],
            symlink_rules=[
                SymlinkRule(
                    source_pattern="Emulation/roms/nes",
                    target_pattern="../../Roms/Nintendo Entertainment System",
                    description="NES ROM symlink",
                )
            ],
            platform_rules=[],
            deduplication_rules=[],
            path_validation=PathValidationRule(
                forbidden_patterns=["C:/", "%APPDATA%"],
                required_patterns=[]
            ),
            backup_rules=[],
            portability_rules=PortabilityRule(),
            storage_rules=StorageRule(
                minimum_free_space_gb=20,
                warning_threshold_gb=10,
                critical_threshold_gb=5,
            ),
            operation_rules=OperationRule(),
        )

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_check_compliance_no_rules(self):
        """Test compliance check when no rules are available."""
        # Create a service with a non-existent document path to avoid file loading
        service = SDEmulationService(architecture_doc_path="/non/existent/path.md")
        service._rules = None
        
        # Mock get_rules to return None instead of trying to load from file
        with patch.object(service, 'get_rules', return_value=None):
            with self.assertRaises(ValueError) as context:
                service.check_compliance(str(self.test_path))
        
        self.assertIn("No rules available", str(context.exception))

    def test_check_directory_structure_compliant(self):
        """Test directory structure compliance when directories exist."""
        # Create required directories
        (self.test_path / "Emulation").mkdir()
        (self.test_path / "Roms").mkdir()
        
        checks = self.service._check_directory_structure(self.test_path, self.sample_rules)
        
        self.assertEqual(len(checks), 2)
        for check in checks:
            self.assertEqual(check.level, ComplianceLevel.COMPLIANT)
            self.assertIn("exists", check.message)

    def test_check_directory_structure_missing(self):
        """Test directory structure compliance when directories are missing."""
        checks = self.service._check_directory_structure(self.test_path, self.sample_rules)
        
        self.assertEqual(len(checks), 2)
        for check in checks:
            self.assertEqual(check.level, ComplianceLevel.NON_COMPLIANT)
            self.assertIn("missing", check.message)
            self.assertIsNotNone(check.suggested_action)

    def test_check_symlink_compliance(self):
        """Test symlink compliance checking."""
        checks = self.service._check_symlink_compliance(self.test_path, self.sample_rules)
        
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].level, ComplianceLevel.WARNING)
        self.assertIn("Manual verification", checks[0].message)

    @patch("shutil.disk_usage")
    def test_check_storage_compliance_sufficient(self, mock_disk_usage):
        """Test storage compliance when space is sufficient."""
        # Mock 30GB free space
        mock_disk_usage.return_value = (100 * 1024**3, 70 * 1024**3, 30 * 1024**3)
        
        checks = self.service._check_storage_compliance(self.test_path, self.sample_rules)
        
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].level, ComplianceLevel.COMPLIANT)
        self.assertIn("Sufficient free space", checks[0].message)

    @patch("shutil.disk_usage")
    def test_check_storage_compliance_warning(self, mock_disk_usage):
        """Test storage compliance when space is low but not critical."""
        # Mock 8GB free space (below minimum but above critical)
        mock_disk_usage.return_value = (100 * 1024**3, 92 * 1024**3, 8 * 1024**3)
        
        checks = self.service._check_storage_compliance(self.test_path, self.sample_rules)
        
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].level, ComplianceLevel.WARNING)
        self.assertIn("Low disk space", checks[0].message)

    @patch("shutil.disk_usage")
    def test_check_storage_compliance_critical(self, mock_disk_usage):
        """Test storage compliance when space is critically low."""
        # Mock 3GB free space (below critical threshold)
        mock_disk_usage.return_value = (100 * 1024**3, 97 * 1024**3, 3 * 1024**3)
        
        checks = self.service._check_storage_compliance(self.test_path, self.sample_rules)
        
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].level, ComplianceLevel.NON_COMPLIANT)
        self.assertIn("Critical disk space", checks[0].message)

    @patch("shutil.disk_usage", side_effect=OSError("Disk error"))
    def test_check_storage_compliance_error(self, mock_disk_usage):
        """Test storage compliance when disk check fails."""
        checks = self.service._check_storage_compliance(self.test_path, self.sample_rules)
        
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].level, ComplianceLevel.UNKNOWN)
        self.assertIn("Failed to check disk space", checks[0].message)

    def test_generate_recommendations(self):
        """Test recommendation generation based on compliance checks."""
        from domain.sd_rules import ComplianceCheck
        
        checks = [
            ComplianceCheck(
                rule_name="directory_structure_missing",
                level=ComplianceLevel.NON_COMPLIANT,
                message="Missing directory",
            ),
            ComplianceCheck(
                rule_name="storage_space_warning",
                level=ComplianceLevel.WARNING,
                message="Low space",
            ),
            ComplianceCheck(
                rule_name="path_validation_compliant",
                level=ComplianceLevel.COMPLIANT,
                message="Path OK",
            ),
        ]
        
        recommendations = self.service._generate_recommendations(checks)
        
        self.assertGreater(len(recommendations), 0)
        self.assertTrue(any("critical compliance issues" in rec for rec in recommendations))
        self.assertTrue(any("warning issues" in rec for rec in recommendations))
        self.assertTrue(any("missing required directories" in rec for rec in recommendations))

    def test_plan_sd_alignment(self):
        """Test SD alignment planning."""
        # Mock compliance report
        with patch.object(self.service, 'check_compliance') as mock_check:
            from domain.sd_rules import ComplianceReport, ComplianceCheck
            
            mock_report = ComplianceReport(
                timestamp="2024-01-01T00:00:00",
                rules_version="1.0.0",
                total_checks=2,
                compliant_checks=0,
                warning_checks=1,
                non_compliant_checks=1,
                checks=[
                    ComplianceCheck(
                        rule_name="directory_missing",
                        level=ComplianceLevel.NON_COMPLIANT,
                        message="Missing directory",
                        suggested_action="Create directory: /test/path",
                    ),
                    ComplianceCheck(
                        rule_name="storage_warning",
                        level=ComplianceLevel.WARNING,
                        message="Low space",
                        suggested_action="Free up disk space",
                    ),
                ],
                summary={},
                recommendations=[],
            )
            mock_check.return_value = mock_report
            
            plan = self.service.plan_sd_alignment(str(self.test_path), self.sample_rules)
            
            self.assertIn("critical_actions", plan)
            self.assertIn("recommended_actions", plan)
            self.assertIn("optional_improvements", plan)
            
            self.assertIn("Create directory: /test/path", plan["critical_actions"])
            self.assertIn("Free up disk space", plan["recommended_actions"])
            self.assertGreater(len(plan["optional_improvements"]), 0)


class TestSDEmulationServiceIntegration(unittest.TestCase):
    """Integration tests for SDEmulationService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = SDEmulationService()
        self.temp_dir = tempfile.mkdtemp()
        self.test_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_rules_lazy_loading(self):
        """Test that rules are loaded lazily when first accessed."""
        # Initially no rules loaded
        self.assertIsNone(self.service._rules)
        
        # Mock the document parsing
        with patch.object(self.service, 'parse_rules_from_document') as mock_parse:
            mock_rules = SDEmulationRules(
                description="Test Lazy Loading Rules",
                directory_structure=[],
                symlink_rules=[],
                platform_rules=[],
                deduplication_rules=[],
                path_validation=PathValidationRule(
                    forbidden_patterns=[],
                    required_patterns=[]
                ),
                backup_rules=[],
                portability_rules=PortabilityRule(),
                storage_rules=StorageRule(),
                operation_rules=OperationRule(),
            )
            mock_parse.return_value = mock_rules
            
            # First call should trigger parsing
            rules = self.service.get_rules()
            
            self.assertEqual(rules, mock_rules)
            self.assertEqual(self.service._rules, mock_rules)
            mock_parse.assert_called_once()
            
            # Second call should use cached rules
            rules2 = self.service.get_rules()
            
            self.assertEqual(rules2, mock_rules)
            # parse_rules_from_document should still only be called once
            mock_parse.assert_called_once()

    @patch("shutil.disk_usage")
    def test_full_compliance_check_integration(self, mock_disk_usage):
        """Test full compliance check integration."""
        # Mock sufficient disk space
        mock_disk_usage.return_value = (100 * 1024**3, 50 * 1024**3, 50 * 1024**3)
        
        # Create some directories
        (self.test_path / "Emulation").mkdir()
        
        # Mock rules
        rules = SDEmulationRules(
            description="Test Integration Rules",
            directory_structure=[
                DirectoryStructureRule(
                    path="Emulation", purpose="Core", required=True
                ),
                DirectoryStructureRule(
                    path="Roms", purpose="Storage", required=True
                ),
            ],
            symlink_rules=[],
            platform_rules=[],
            deduplication_rules=[],
            path_validation=PathValidationRule(
                forbidden_patterns=[],
                required_patterns=[]
            ),
            backup_rules=[],
            portability_rules=PortabilityRule(),
            storage_rules=StorageRule(minimum_free_space_gb=20),
            operation_rules=OperationRule(),
        )
        
        report = self.service.check_compliance(str(self.test_path), rules)
        
        self.assertIsNotNone(report)
        self.assertGreater(report.total_checks, 0)
        self.assertIsInstance(report.timestamp, str)
        self.assertEqual(report.rules_version, rules.version)
        
        # Should have both compliant and non-compliant checks
        self.assertGreater(report.compliant_checks, 0)  # Storage and existing directory
        self.assertGreater(report.non_compliant_checks, 0)  # Missing Roms directory


if __name__ == "__main__":
    unittest.main()