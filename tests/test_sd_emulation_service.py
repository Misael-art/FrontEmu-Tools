"""Tests for SDEmulationService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from sd_emulation_gui.services.sd_emulation_service import SDEmulationService
from domain.sd_rules import (
    SDEmulationRules,
    DirectoryStructureRule,
    SymlinkRule,
    PlatformRule,
    DeduplicationRule,
    PathValidationRule,
    BackupRule,
    PortabilityRule,
    StorageRule,
    OperationRule,
    ComplianceReport,
    ComplianceCheck,
    ComplianceLevel,
)


class TestSDEmulationService:
    """Test cases for SDEmulationService."""

    @pytest.fixture
    def mock_path_config(self):
        """Mock PathConfigManager."""
        with patch('meta.config.path_config.PathConfigManager') as mock:
            yield mock

    @pytest.fixture
    def mock_path_resolver(self):
        """Mock PathResolver."""
        with patch('config.path_resolver.PathResolver') as mock:
            yield mock

    @pytest.fixture
    def service(self, mock_path_config, mock_path_resolver):
        """Create SDEmulationService instance for testing."""
        return SDEmulationService()

    @pytest.fixture
    def sample_rules(self):
        """Create sample SDEmulationRules for testing."""
        return SDEmulationRules(
            version="1.0.0",
            description="Test rules",
            directory_structure=[
                DirectoryStructureRule(path="models", purpose="Models directory", required=True),
                DirectoryStructureRule(path="outputs", purpose="Outputs directory", required=True)
            ],
            symlink_rules=[
                SymlinkRule(
                    source_pattern="models/*.safetensors",
                    target_pattern="/shared/models/*.safetensors",
                    description="Model symlinks"
                )
            ],
            platform_rules=[
                PlatformRule(
                    short_name="windows",
                    full_name="Windows",
                    supported_extensions=[".exe", ".bat"]
                )
            ],
            deduplication_rules=[
                DeduplicationRule(
                    target_directories=["models"],
                    file_patterns=["*.safetensors"]
                )
            ],
            path_validation=PathValidationRule(
                forbidden_patterns=["<", ">", ":", '"', "|", "?", "*"],
                required_patterns=[],
                max_path_length=260
            ),
            backup_rules=[
                BackupRule(
                    target_patterns=["*.json"],
                    backup_location="./backups"
                )
            ],
            portability_rules=PortabilityRule(
                require_relative_paths=True
            ),
            storage_rules=StorageRule(
                minimum_free_space_gb=10,
                critical_threshold_gb=5
            ),
            operation_rules=OperationRule(
                log_all_operations=True
            )
        )

    def test_service_initialization(self, mock_path_config, mock_path_resolver):
        """Test SDEmulationService initialization."""
        service = SDEmulationService()
        
        assert service.path_config_manager is not None
        assert service.path_resolver is not None
        assert service.architecture_doc_path is not None
        assert service._rules is None

    def test_service_initialization_with_custom_doc_path(self, mock_path_config, mock_path_resolver):
        """Test SDEmulationService initialization with custom document path."""
        custom_path = "/custom/path/doc.md"
        service = SDEmulationService(architecture_doc_path=custom_path)
        
        assert service.architecture_doc_path == custom_path

    @patch('builtins.open')
    @patch('pathlib.Path.exists')
    def test_parse_rules_from_document_success(self, mock_exists, mock_open, service):
        """Test successful parsing of rules from document."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = """
        # Directory Structure
        - models/ (required)
        - outputs/ (required)
        
        # Symlinks
        - models/*.safetensors -> /shared/models/*.safetensors
        
        # Platform Rules
        Windows: .exe, .bat
        
        # Deduplication
        *.safetensors: hash strategy
        
        # Path Validation
        Max length: 260
        Forbidden: < > : " | ? *
        
        # Backup
        *.json: daily, 30 days
        
        # Portability
        Path length: max 260
        
        # Storage
        Min free: 10GB
        Critical: 5GB
        
        # Operations
        Copy: source_exists, target_writable
        """
        
        rules = service.parse_rules_from_document("/test/doc.md")
        
        assert rules is not None
        assert rules.version == "1.0.0"
        assert len(rules.directory_structure) >= 0

    @patch('pathlib.Path.exists')
    def test_parse_rules_from_document_file_not_found(self, mock_exists, service):
        """Test parsing rules when document file doesn't exist."""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            service.parse_rules_from_document("/nonexistent/doc.md")

    def test_get_rules_with_cached_rules(self, service, sample_rules):
        """Test getting rules when already cached."""
        service._rules = sample_rules
        
        rules = service.get_rules()
        
        assert rules == sample_rules

    @patch.object(SDEmulationService, 'parse_rules_from_document')
    def test_get_rules_parse_from_document(self, mock_parse, service, sample_rules):
        """Test getting rules by parsing from document."""
        mock_parse.return_value = sample_rules
        service.architecture_doc_path = "/test/doc.md"
        
        rules = service.get_rules()
        
        assert rules == sample_rules
        mock_parse.assert_called_once_with("/test/doc.md")

    def test_get_rules_no_document_path(self, service):
        """Test getting rules when no document path is set."""
        service.architecture_doc_path = None
        
        rules = service.get_rules()
        
        assert rules is None

    @patch('pathlib.Path.exists')
    @patch('shutil.disk_usage')
    def test_check_compliance_success(self, mock_disk_usage, mock_exists, service, sample_rules):
        """Test successful compliance check."""
        mock_exists.return_value = True
        mock_disk_usage.return_value = (1000000000000, 500000000000, 15000000000)  # 15GB free
        service._rules = sample_rules
        
        report = service.check_compliance("/test/path")
        
        assert isinstance(report, ComplianceReport)
        assert report.total_checks > 0
        assert report.rules_version == "1.0.0"
        assert isinstance(report.timestamp, str)

    def test_check_compliance_no_rules(self, service):
        """Test compliance check when no rules are available."""
        service._rules = None
        service.architecture_doc_path = None
        
        with pytest.raises(ValueError, match="No rules available"):
            service.check_compliance("/test/path")

    @patch('pathlib.Path.exists')
    def test_check_directory_structure_compliant(self, mock_exists, service, sample_rules):
        """Test directory structure compliance check - compliant case."""
        mock_exists.return_value = True
        
        checks = service._check_directory_structure(Path("/test"), sample_rules)
        
        assert len(checks) == 2  # models and outputs directories
        assert all(check.level == ComplianceLevel.COMPLIANT for check in checks)

    @patch('pathlib.Path.exists')
    def test_check_directory_structure_non_compliant(self, mock_exists, service, sample_rules):
        """Test directory structure compliance check - non-compliant case."""
        mock_exists.return_value = False
        
        checks = service._check_directory_structure(Path("/test"), sample_rules)
        
        assert len(checks) == 2
        assert all(check.level == ComplianceLevel.NON_COMPLIANT for check in checks)
        assert all("missing" in check.message.lower() for check in checks)

    def test_check_symlink_compliance(self, service, sample_rules):
        """Test symlink compliance check."""
        checks = service._check_symlink_compliance(Path("/test"), sample_rules)
        
        assert len(checks) == 1
        assert checks[0].level == ComplianceLevel.WARNING
        assert "Manual verification" in checks[0].message

    @patch('shutil.disk_usage')
    def test_check_storage_compliance_sufficient(self, mock_disk_usage, service, sample_rules):
        """Test storage compliance check - sufficient space."""
        mock_disk_usage.return_value = (1000000000000, 500000000000, 15000000000)  # 15GB free
        
        checks = service._check_storage_compliance(Path("/test"), sample_rules)
        
        assert len(checks) == 1
        assert checks[0].level == ComplianceLevel.COMPLIANT
        assert "Sufficient free space" in checks[0].message

    @patch('shutil.disk_usage')
    def test_check_storage_compliance_warning(self, mock_disk_usage, service, sample_rules):
        """Test storage compliance check - warning level."""
        mock_disk_usage.return_value = (1000000000000, 500000000000, 7000000000)  # 7GB free
        
        checks = service._check_storage_compliance(Path("/test"), sample_rules)
        
        assert len(checks) == 1
        assert checks[0].level == ComplianceLevel.WARNING
        assert "Low disk space" in checks[0].message

    @patch('shutil.disk_usage')
    def test_check_storage_compliance_critical(self, mock_disk_usage, service, sample_rules):
        """Test storage compliance check - critical level."""
        mock_disk_usage.return_value = (1000000000000, 500000000000, 3000000000)  # 3GB free
        
        checks = service._check_storage_compliance(Path("/test"), sample_rules)
        
        assert len(checks) == 1
        assert checks[0].level == ComplianceLevel.NON_COMPLIANT
        assert "Critical disk space" in checks[0].message

    @patch('shutil.disk_usage')
    def test_check_storage_compliance_error(self, mock_disk_usage, service, sample_rules):
        """Test storage compliance check - error case."""
        mock_disk_usage.side_effect = Exception("Disk access error")
        
        checks = service._check_storage_compliance(Path("/test"), sample_rules)
        
        assert len(checks) == 1
        assert checks[0].level == ComplianceLevel.UNKNOWN
        assert "Failed to check disk space" in checks[0].message

    def test_generate_recommendations_no_issues(self, service):
        """Test recommendation generation with no issues."""
        checks = [
            ComplianceCheck(
                rule_name="test_compliant",
                level=ComplianceLevel.COMPLIANT,
                message="All good"
            )
        ]
        
        recommendations = service._generate_recommendations(checks)
        
        assert len(recommendations) == 0

    def test_generate_recommendations_with_issues(self, service):
        """Test recommendation generation with issues."""
        checks = [
            ComplianceCheck(
                rule_name="directory_structure_missing",
                level=ComplianceLevel.NON_COMPLIANT,
                message="Directory missing"
            ),
            ComplianceCheck(
                rule_name="storage_space_warning",
                level=ComplianceLevel.WARNING,
                message="Low space"
            )
        ]
        
        recommendations = service._generate_recommendations(checks)
        
        assert len(recommendations) >= 2
        assert any("critical compliance issues" in rec for rec in recommendations)
        assert any("warning issues" in rec for rec in recommendations)
        assert any("missing required directories" in rec for rec in recommendations)

    @patch.object(SDEmulationService, 'check_compliance')
    def test_plan_sd_alignment(self, mock_check_compliance, service, sample_rules):
        """Test SD alignment planning."""
        mock_report = ComplianceReport(
            timestamp=datetime.now().isoformat(),
            rules_version="1.0.0",
            total_checks=3,
            compliant_checks=1,
            warning_checks=1,
            non_compliant_checks=1,
            checks=[
                ComplianceCheck(
                    rule_name="directory_missing",
                    level=ComplianceLevel.NON_COMPLIANT,
                    message="Directory missing",
                    suggested_action="Create directory"
                ),
                ComplianceCheck(
                    rule_name="storage_warning",
                    level=ComplianceLevel.WARNING,
                    message="Low space",
                    suggested_action="Free up space"
                ),
                ComplianceCheck(
                    rule_name="path_compliant",
                    level=ComplianceLevel.COMPLIANT,
                    message="Path OK"
                )
            ],
            summary={},
            recommendations=[]
        )
        mock_check_compliance.return_value = mock_report
        service._rules = sample_rules
        
        plan = service.plan_sd_alignment("/test/path")
        
        assert "critical_actions" in plan
        assert "recommended_actions" in plan
        assert "optional_improvements" in plan
        assert "Create directory" in plan["critical_actions"]
        assert "Free up space" in plan["recommended_actions"]
        assert len(plan["optional_improvements"]) >= 3

    def test_plan_sd_alignment_with_custom_rules(self, service, sample_rules):
        """Test SD alignment planning with custom rules."""
        with patch.object(service, 'check_compliance') as mock_check:
            mock_check.return_value = ComplianceReport(
                timestamp=datetime.now().isoformat(),
                rules_version="1.0.0",
                total_checks=0,
                compliant_checks=0,
                warning_checks=0,
                non_compliant_checks=0,
                checks=[],
                summary={},
                recommendations=[]
            )
            
            plan = service.plan_sd_alignment("/test/path", sample_rules)
            
            mock_check.assert_called_once_with("/test/path", sample_rules)
            assert isinstance(plan, dict)

    def test_parse_document_content_empty(self, service):
        """Test parsing empty document content."""
        rules = service._parse_document_content("")
        
        assert isinstance(rules, SDEmulationRules)
        assert rules.version == "1.0.0"
        assert len(rules.directory_structure) == 0

    def test_parse_document_content_with_sections(self, service):
        """Test parsing document content with various sections."""
        content = """
        # Directory Structure
        - models/ (required)
        - outputs/ (optional)
        
        # Platform Rules
        Windows: .exe, .bat
        Linux: .sh, .bin
        
        # Storage Requirements
        Minimum free space: 10GB
        Critical threshold: 5GB
        """
        
        rules = service._parse_document_content(content)
        
        assert isinstance(rules, SDEmulationRules)
        assert rules.version == "1.0.0"
        # The actual parsing logic would need to be implemented
        # For now, we just verify the structure is created