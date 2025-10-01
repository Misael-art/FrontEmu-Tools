"""Tests for ValidationService."""

from pathlib import Path
from unittest.mock import Mock, patch

from domain.models import AppConfig, EmulatorMapping
from sd_emulation_gui.services.validation_service import ValidationService, ValidationSummary
from utils.validation_utils import ValidationResult


class TestValidationSummary:
    """Test ValidationSummary class."""

    def test_init(self):
        """Test ValidationSummary initialization."""
        summary = ValidationSummary()

        assert summary.results == {}
        assert summary.total_files == 0
        assert summary.valid_files == 0
        assert summary.files_with_warnings == 0
        assert summary.files_with_errors == 0
        assert summary.overall_status == "valid"
        assert summary.coverage_percentage == 0.0
        assert summary.timestamp is not None

    def test_add_result_valid(self):
        """Test adding a valid result."""
        summary = ValidationSummary()
        result = ValidationResult("test.json")
        result.is_valid = True

        summary.add_result("test.json", result)

        assert summary.total_files == 1
        assert summary.valid_files == 1
        assert summary.files_with_warnings == 0
        assert summary.files_with_errors == 0
        assert summary.overall_status == "valid"
        assert summary.coverage_percentage == 100.0

    def test_add_result_with_warnings(self):
        """Test adding a result with warnings."""
        summary = ValidationSummary()
        result = ValidationResult("test.json")
        result.is_valid = True
        result.warnings = ["Warning message"]

        summary.add_result("test.json", result)

        assert summary.total_files == 1
        assert summary.valid_files == 0
        assert summary.files_with_warnings == 1
        assert summary.files_with_errors == 0
        assert summary.overall_status == "warning"
        assert summary.coverage_percentage == 0.0

    def test_add_result_with_errors(self):
        """Test adding a result with errors."""
        summary = ValidationSummary()
        result = ValidationResult("test.json")
        result.is_valid = False
        result.errors = ["Error message"]

        summary.add_result("test.json", result)

        assert summary.total_files == 1
        assert summary.valid_files == 0
        assert summary.files_with_warnings == 0
        assert summary.files_with_errors == 1
        assert summary.overall_status == "error"
        assert summary.coverage_percentage == 0.0

    def test_get_summary_stats(self):
        """Test getting summary statistics."""
        summary = ValidationSummary()
        result = ValidationResult("test.json")
        result.is_valid = True
        summary.add_result("test.json", result)

        stats = summary.get_summary_stats()

        assert stats["total_files"] == 1
        assert stats["valid_files"] == 1
        assert stats["files_with_warnings"] == 0
        assert stats["files_with_errors"] == 0
        assert stats["overall_status"] == "valid"
        assert stats["coverage_percentage"] == 100.0
        assert "timestamp" in stats

    def test_to_dict(self):
        """Test converting summary to dictionary."""
        summary = ValidationSummary()
        result = ValidationResult("test.json")
        result.is_valid = True
        result.add_info("Test info")
        summary.add_result("test.json", result)

        summary_dict = summary.to_dict()

        assert "summary" in summary_dict
        assert "results" in summary_dict
        assert "test.json" in summary_dict["results"]
        assert summary_dict["results"]["test.json"]["status"] == "valid"


class TestValidationService:
    """Test ValidationService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_dir = "/test/config"
        self.service = ValidationService(config_dir=self.config_dir)

    @patch("meta.config.path_config.PathConfigManager")
    @patch("services.validation_service.PathResolver")
    def test_init_with_config_dir(self, mock_resolver, mock_manager):
        """Test initialization with config directory."""
        service = ValidationService(config_dir="/test/config")

        assert service.base_path == "/test/config"
        assert len(service.config_files) == 6
        assert "config.json" in service.config_files

    @patch("meta.config.path_config.PathConfigManager")
    @patch("services.validation_service.PathResolver")
    @patch("services.validation_service.PathUtils")
    def test_init_with_base_path(self, mock_path_utils, mock_resolver, mock_manager):
        """Test initialization with base path."""
        mock_path_utils.normalize_path.return_value = "/normalized/path"

        service = ValidationService(base_path="/test/base")

        mock_path_utils.normalize_path.assert_called_with("/test/base")
        assert service.base_path == "/normalized/path"

    @patch("meta.config.path_config.PathConfigManager")
    @patch("services.validation_service.PathResolver")
    @patch("services.validation_service.PathUtils")
    def test_init_with_dynamic_path(self, mock_path_utils, mock_resolver, mock_manager):
        """Test initialization with dynamic path resolution."""
        mock_resolver_instance = Mock()
        mock_resolver.return_value = mock_resolver_instance
        mock_resolver_instance.resolve_path.return_value = "/dynamic/path"
        mock_path_utils.normalize_path.return_value = "/normalized/dynamic"

        service = ValidationService()

        mock_resolver_instance.resolve_path.assert_called_with("config_base_path")
        mock_path_utils.normalize_path.assert_called_with("/dynamic/path")

    @patch("services.validation_service.PathUtils")
    @patch("services.validation_service.ValidationUtils")
    @patch("services.validation_service.FileUtils")
    def test_validate_config_file_not_found(
        self, mock_file_utils, mock_validation_utils, mock_path_utils
    ):
        """Test validation when file is not found."""
        mock_path_utils.join_path.return_value = "/test/config/config.json"
        mock_path_utils.path_exists.return_value = False

        result = self.service.validate_config("config.json")

        assert not result.is_valid
        assert len(result.errors) == 1
        assert "não encontrado" in result.errors[0]

    @patch("services.validation_service.PathUtils")
    @patch("services.validation_service.ValidationUtils")
    @patch("services.validation_service.FileUtils")
    def test_validate_config_invalid_json(
        self, mock_file_utils, mock_validation_utils, mock_path_utils
    ):
        """Test validation with invalid JSON."""
        mock_path_utils.join_path.return_value = "/test/config/config.json"
        mock_path_utils.path_exists.return_value = True

        # Mock invalid JSON result
        invalid_json_result = ValidationResult("config.json")
        invalid_json_result.is_valid = False
        invalid_json_result.errors = ["Invalid JSON syntax"]
        mock_validation_utils.validate_json_file.return_value = invalid_json_result

        result = self.service.validate_config("config.json")

        assert not result.is_valid
        assert "Invalid JSON syntax" in result.errors

    @patch("services.validation_service.PathUtils")
    @patch("services.validation_service.ValidationUtils")
    @patch("services.validation_service.FileUtils")
    def test_validate_config_success(
        self, mock_file_utils, mock_validation_utils, mock_path_utils
    ):
        """Test successful configuration validation."""
        mock_path_utils.join_path.return_value = "/test/config/config.json"
        mock_path_utils.path_exists.return_value = True

        # Mock valid JSON result
        valid_json_result = ValidationResult("config.json")
        valid_json_result.is_valid = True
        valid_json_result.data = {"version": "1.0", "environment": "test", "paths": {}}
        mock_validation_utils.validate_json_file.return_value = valid_json_result

        # Mock file utilities
        mock_file_utils.get_file_size.return_value = 1024
        mock_file_utils.read_text_file.return_value = "line1\nline2\nline3"

        result = self.service.validate_config("config.json")

        assert result.is_valid
        assert result.metrics["file_size"] == 1024
        assert result.metrics["line_count"] == 3
        assert any("bem-sucedida" in info for info in result.info)

    @patch("services.validation_service.PathUtils")
    @patch("services.validation_service.ValidationUtils")
    @patch("services.validation_service.FileUtils")
    def test_validate_config_with_pydantic_model(
        self, mock_file_utils, mock_validation_utils, mock_path_utils
    ):
        """Test validation with Pydantic model validation."""
        mock_path_utils.join_path.return_value = "/test/config/config.json"
        mock_path_utils.path_exists.return_value = True

        # Mock valid JSON result
        valid_json_result = ValidationResult("config.json")
        valid_json_result.is_valid = True
        valid_json_result.data = {"version": "1.0", "environment": "test", "paths": {}}
        mock_validation_utils.validate_json_file.return_value = valid_json_result

        # Mock file utilities
        mock_file_utils.get_file_size.return_value = 1024
        mock_file_utils.read_text_file.return_value = "line1\nline2"

        with patch.object(self.service, "_get_model_for_file") as mock_get_model:
            mock_model = Mock()
            mock_get_model.return_value = mock_model

            result = self.service.validate_config("config.json")

            mock_model.assert_called_once_with(**valid_json_result.data)
            assert result.is_valid

    @patch("services.validation_service.PathUtils")
    @patch("services.validation_service.ValidationUtils")
    @patch("services.validation_service.FileUtils")
    def test_validate_config_missing_required_keys(
        self, mock_file_utils, mock_validation_utils, mock_path_utils
    ):
        """Test validation with missing required keys."""
        mock_path_utils.join_path.return_value = "/test/config/config.json"
        mock_path_utils.path_exists.return_value = True

        # Mock valid JSON result but missing required keys
        valid_json_result = ValidationResult("config.json")
        valid_json_result.is_valid = True
        valid_json_result.data = {"version": "1.0"}  # Missing 'environment' and 'paths'
        mock_validation_utils.validate_json_file.return_value = valid_json_result

        # Mock file utilities
        mock_file_utils.get_file_size.return_value = 1024
        mock_file_utils.read_text_file.return_value = "line1"

        result = self.service.validate_config("config.json")

        assert not result.is_valid
        assert any("Chaves obrigatórias ausentes" in error for error in result.errors)

    def test_validate_all(self):
        """Test validating all configuration files."""
        with (
            patch.object(self.service, "validate_config") as mock_validate_config,
            patch.object(
                self.service, "_validate_cross_references_with_utils"
            ) as mock_cross_ref,
        ):

            # Mock individual file validation results
            mock_result = ValidationResult("test.json")
            mock_result.is_valid = True
            mock_validate_config.return_value = mock_result

            # Mock cross-reference validation
            mock_cross_ref_result = ValidationResult("cross_references")
            mock_cross_ref_result.is_valid = True
            mock_cross_ref.return_value = mock_cross_ref_result

            summary = self.service.validate_all()

            assert mock_validate_config.call_count == len(self.service.config_files)
            mock_cross_ref.assert_called_once()
            assert (
                summary.total_files == len(self.service.config_files) + 1
            )  # +1 for cross_references

    def test_get_model_for_file(self):
        """Test getting Pydantic model for configuration files."""
        assert self.service._get_model_for_file("config.json") == AppConfig
        assert (
            self.service._get_model_for_file("emulator_mapping.json") == EmulatorMapping
        )
        assert self.service._get_model_for_file("unknown.json") is None

    def test_get_required_keys(self):
        """Test getting required keys for configuration files."""
        config_keys = self.service._get_required_keys("config.json")
        assert "version" in config_keys
        assert "environment" in config_keys
        assert "paths" in config_keys

        emulator_keys = self.service._get_required_keys("emulator_mapping.json")
        assert "emulators" in emulator_keys

        unknown_keys = self.service._get_required_keys("unknown.json")
        assert unknown_keys == []

    def test_validate_emulator_platform_consistency_missing_emulators(self):
        """Test emulator-platform consistency validation with missing emulators section."""
        emulator_config = {}  # Missing 'emulators' section
        platform_config = {"mappings": {}}
        result = ValidationResult("test")

        self.service._validate_emulator_platform_consistency(
            emulator_config, platform_config, result
        )

        assert len(result.errors) == 1
        assert "'emulators' ausente" in result.errors[0]

    def test_validate_emulator_platform_consistency_success(self):
        """Test successful emulator-platform consistency validation."""
        emulator_config = {
            "emulators": {
                "retroarch": {"supported_platforms": ["nes", "snes"]},
                "dolphin": {"supported_platforms": ["gamecube"]},
            }
        }
        platform_config = {
            "mappings": {
                "nes": {"emulator": "retroarch"},
                "snes": {"emulator": "retroarch"},
            }
        }
        result = ValidationResult("test")

        self.service._validate_emulator_platform_consistency(
            emulator_config, platform_config, result
        )

        assert len(result.errors) == 0

    def test_validate_emulator_platform_consistency_invalid_reference(self):
        """Test emulator-platform consistency with invalid emulator reference."""
        emulator_config = {"emulators": {"retroarch": {"supported_platforms": ["nes"]}}}
        platform_config = {
            "mappings": {
                "nes": {"emulator": "retroarch"},
                "snes": {"emulator": "nonexistent"},  # Invalid reference
            }
        }
        result = ValidationResult("test")

        self.service._validate_emulator_platform_consistency(
            emulator_config, platform_config, result
        )

        assert len(result.errors) == 1
        assert "referencia emulador inexistente" in result.errors[0]

    def test_validate_variant_platform_consistency_success(self):
        """Test successful variant-platform consistency validation."""
        platform_config = {"mappings": {"nes": {}, "snes": {}}}
        variant_config = {
            "variants": {
                "nes_pal": {"base_platform": "nes"},
                "snes_pal": {"base_platform": "snes"},
            }
        }
        result = ValidationResult("test")

        self.service._validate_variant_platform_consistency(
            platform_config, variant_config, result
        )

        assert len(result.errors) == 0

    def test_validate_variant_platform_consistency_invalid_reference(self):
        """Test variant-platform consistency with invalid platform reference."""
        platform_config = {"mappings": {"nes": {}}}
        variant_config = {
            "variants": {
                "nes_pal": {"base_platform": "nes"},
                "snes_pal": {"base_platform": "nonexistent"},  # Invalid reference
            }
        }
        result = ValidationResult("test")

        self.service._validate_variant_platform_consistency(
            platform_config, variant_config, result
        )

        assert len(result.errors) == 1
        assert "referencia plataforma base inexistente" in result.errors[0]

    def test_validate_frontend_paths_success(self):
        """Test successful frontend paths validation."""
        frontend_config = {
            "emulator_paths": {
                "retroarch": {"path": "/usr/bin/retroarch"},
                "dolphin": {"path": "/usr/bin/dolphin"},
            }
        }
        emulator_config = {
            "emulators": {
                "retroarch": {"path": "/usr/bin/retroarch"},
                "dolphin": {"path": "/usr/bin/dolphin"},
            }
        }
        result = ValidationResult("test")

        self.service._validate_frontend_paths(frontend_config, emulator_config, result)

        assert len(result.warnings) == 0

    def test_validate_frontend_paths_mismatch(self):
        """Test frontend paths validation with path mismatch."""
        frontend_config = {
            "emulator_paths": {"retroarch": {"path": "/wrong/path/retroarch"}}
        }
        emulator_config = {"emulators": {"retroarch": {"path": "/usr/bin/retroarch"}}}
        result = ValidationResult("test")

        self.service._validate_frontend_paths(frontend_config, emulator_config, result)

        assert len(result.warnings) == 1
        assert "não corresponde aos mapeamentos" in result.warnings[0]

    def test_check_for_duplicates_no_duplicates(self):
        """Test duplicate checking with no duplicates."""
        configs = {
            "platform_mapping.json": {"mappings": {"nes": {}, "snes": {}}},
            "variant_mapping.json": {"mappings": {"gameboy": {}, "gba": {}}},
        }
        result = ValidationResult("test")

        self.service._check_for_duplicates(configs, result)

        assert len(result.errors) == 0

    def test_check_for_duplicates_with_duplicates(self):
        """Test duplicate checking with duplicates found."""
        configs = {
            "platform_mapping.json": {"mappings": {"nes": {}, "snes": {}}},
            "variant_mapping.json": {"mappings": {"nes": {}, "gba": {}}},  # Duplicate
        }
        result = ValidationResult("test")

        self.service._check_for_duplicates(configs, result)

        assert len(result.errors) == 1
        assert "Plataformas duplicadas" in result.errors[0]
        assert "nes" in result.errors[0]

    def test_validate_completeness_missing_core_files(self):
        """Test completeness validation with missing core files."""
        configs = {
            "config.json": {"version": "1.0"}
            # Missing emulator_mapping.json and platform_mapping.json
        }
        result = ValidationResult("test")

        self.service._validate_completeness(configs, result)

        assert len(result.errors) >= 1
        assert any("essenciais ausentes" in error for error in result.errors)

    def test_validate_completeness_invalid_structure(self):
        """Test completeness validation with invalid structure."""
        configs = {
            "config.json": None,  # Invalid structure
            "emulator_mapping.json": {"version": "1.0"},
            "platform_mapping.json": {"version": "1.0"},
        }
        result = ValidationResult("test")

        self.service._validate_completeness(configs, result)

        assert len(result.errors) >= 1
        assert any("Estrutura inválida" in error for error in result.errors)

    def test_validate_completeness_missing_version(self):
        """Test completeness validation with missing version fields."""
        configs = {
            "config.json": {},  # Missing version
            "emulator_mapping.json": {"version": "1.0"},
            "platform_mapping.json": {"version": "1.0"},
        }
        result = ValidationResult("test")

        self.service._validate_completeness(configs, result)

        assert len(result.warnings) >= 1
        assert any("'version' ausente" in warning for warning in result.warnings)

    @patch("services.validation_service.PathUtils")
    @patch("services.validation_service.FileUtils")
    def test_validate_cross_references_no_configs(
        self, mock_file_utils, mock_path_utils
    ):
        """Test cross-reference validation with no configurations loaded."""
        mock_path_utils.join_path.return_value = "/test/config/config.json"
        mock_path_utils.path_exists.return_value = False

        result = self.service.validate_cross_references()

        assert not result.is_valid
        assert any(
            "Nenhuma configuração encontrada" in error for error in result.errors
        )

    @patch("services.validation_service.PathUtils")
    @patch("services.validation_service.FileUtils")
    def test_validate_cross_references_success(self, mock_file_utils, mock_path_utils):
        """Test successful cross-reference validation."""
        mock_path_utils.join_path.return_value = "/test/config/test.json"
        mock_path_utils.path_exists.return_value = True

        # Mock file loading
        mock_configs = {
            "emulator_mapping.json": {
                "emulators": {"retroarch": {"supported_platforms": ["nes"]}}
            },
            "platform_mapping.json": {"mappings": {"nes": {"emulator": "retroarch"}}},
        }

        def mock_read_json(path):
            filename = Path(path).name
            return mock_configs.get(filename, {})

        mock_file_utils.read_json_file.side_effect = mock_read_json

        result = self.service.validate_cross_references()

        assert result.cross_reference_valid
        assert any("bem-sucedida" in info for info in result.info)

    def test_get_cross_reference_rules(self):
        """Test getting cross-reference validation rules."""
        rules = self.service._get_cross_reference_rules()

        assert "emulator_platform_consistency" in rules
        assert "platform_variant_consistency" in rules
        assert "frontend_emulator_paths" in rules

        emulator_rule = rules["emulator_platform_consistency"]
        assert emulator_rule["source_file"] == "emulator_mapping.json"
        assert emulator_rule["target_file"] == "platform_mapping.json"

    @patch("services.validation_service.PathUtils")
    @patch("services.validation_service.ValidationUtils")
    def test_validate_cross_references_with_utils_success(
        self, mock_validation_utils, mock_path_utils
    ):
        """Test cross-reference validation using ValidationUtils."""
        mock_path_utils.join_path.return_value = "/test/config/test.json"
        mock_path_utils.path_exists.return_value = True

        # Mock ValidationUtils.validate_json_file
        valid_json_result = ValidationResult("test.json")
        valid_json_result.is_valid = True
        valid_json_result.data = {"test": "data"}
        mock_validation_utils.validate_json_file.return_value = valid_json_result

        # Mock ValidationUtils.validate_cross_references
        cross_ref_result = ValidationResult("cross_references")
        cross_ref_result.is_valid = True
        cross_ref_result.add_info("Cross-reference validation successful")
        mock_validation_utils.validate_cross_references.return_value = cross_ref_result

        result = self.service._validate_cross_references_with_utils()

        assert result.is_valid
        mock_validation_utils.validate_cross_references.assert_called_once()

    @patch("services.validation_service.PathUtils")
    @patch("services.validation_service.ValidationUtils")
    def test_validate_cross_references_with_utils_error(
        self, mock_validation_utils, mock_path_utils
    ):
        """Test cross-reference validation with ValidationUtils error."""
        mock_path_utils.join_path.side_effect = Exception("Test error")

        result = self.service._validate_cross_references_with_utils()

        assert not result.is_valid
        assert len(result.errors) == 1
        assert "Test error" in result.errors[0]