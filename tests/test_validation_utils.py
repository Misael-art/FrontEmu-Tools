"""Unit tests for validation_utils module.

Tests all validation functions to ensure proper validation of files,
directories, JSON schemas, and configuration integrity.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from utils.validation_utils import ValidationResult, ValidationUtils


class TestValidationResult(unittest.TestCase):
    """Test cases for ValidationResult class."""

    def test_validation_result_creation(self):
        """Test ValidationResult object creation."""
        result = ValidationResult(
            is_valid=True, message="Test passed", details={"key": "value"}
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.message, "Test passed")
        self.assertEqual(result.details, {"key": "value"})

    def test_validation_result_defaults(self):
        """Test ValidationResult with default values."""
        result = ValidationResult(is_valid=False, message="Test failed")

        self.assertFalse(result.is_valid)
        self.assertEqual(result.message, "Test failed")
        self.assertEqual(result.details, {})

    def test_validation_result_string_representation(self):
        """Test ValidationResult string representation."""
        result = ValidationResult(is_valid=True, message="Success")
        str_repr = str(result)

        self.assertIn("True", str_repr)
        self.assertIn("Success", str_repr)


class TestValidationUtils(unittest.TestCase):
    """Test cases for ValidationUtils class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after each test method."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_validate_file_exists_valid(self):
        """Test file existence validation for existing file."""
        # Create test file
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_file.write_text("test content")

        result = ValidationUtils.validate_file_exists(str(test_file))

        self.assertTrue(result.is_valid)
        self.assertIn("exists", result.message)

    def test_validate_file_exists_missing(self):
        """Test file existence validation for missing file."""
        missing_file = Path(self.temp_dir) / "missing_file.txt"

        result = ValidationUtils.validate_file_exists(str(missing_file))

        self.assertFalse(result.is_valid)
        self.assertIn("does not exist", result.message)

    def test_validate_file_exists_is_directory(self):
        """Test file existence validation when path is directory."""
        test_dir = Path(self.temp_dir) / "test_directory"
        test_dir.mkdir()

        result = ValidationUtils.validate_file_exists(str(test_dir))

        self.assertFalse(result.is_valid)
        self.assertIn("is not a file", result.message)

    def test_validate_file_exists_empty_path(self):
        """Test file existence validation with empty path."""
        result = ValidationUtils.validate_file_exists("")

        self.assertFalse(result.is_valid)
        self.assertIn("Empty path", result.message)

    def test_validate_directory_exists_valid(self):
        """Test directory existence validation for existing directory."""
        test_dir = Path(self.temp_dir) / "test_directory"
        test_dir.mkdir()

        result = ValidationUtils.validate_directory_exists(str(test_dir))

        self.assertTrue(result.is_valid)
        self.assertIn("exists", result.message)

    def test_validate_directory_exists_missing(self):
        """Test directory existence validation for missing directory."""
        missing_dir = Path(self.temp_dir) / "missing_directory"

        result = ValidationUtils.validate_directory_exists(str(missing_dir))

        self.assertFalse(result.is_valid)
        self.assertIn("does not exist", result.message)

    def test_validate_directory_exists_is_file(self):
        """Test directory existence validation when path is file."""
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_file.write_text("content")

        result = ValidationUtils.validate_directory_exists(str(test_file))

        self.assertFalse(result.is_valid)
        self.assertIn("is not a directory", result.message)

    def test_validate_json_syntax_valid(self):
        """Test JSON syntax validation for valid JSON."""
        valid_json = '{"key": "value", "number": 42, "array": [1, 2, 3]}'

        result = ValidationUtils.validate_json_syntax(valid_json)

        self.assertTrue(result.is_valid)
        self.assertIn("valid JSON", result.message)

    def test_validate_json_syntax_invalid(self):
        """Test JSON syntax validation for invalid JSON."""
        invalid_json = '{"key": "value", "missing_quote: 42}'

        result = ValidationUtils.validate_json_syntax(invalid_json)

        self.assertFalse(result.is_valid)
        self.assertIn("Invalid JSON", result.message)

    def test_validate_json_syntax_empty(self):
        """Test JSON syntax validation for empty string."""
        result = ValidationUtils.validate_json_syntax("")

        self.assertFalse(result.is_valid)
        self.assertIn("Empty JSON", result.message)

    def test_validate_json_file_valid(self):
        """Test JSON file validation for valid JSON file."""
        # Create valid JSON file
        json_file = Path(self.temp_dir) / "valid.json"
        json_data = {"key": "value", "number": 42}
        json_file.write_text(json.dumps(json_data, indent=2))

        result = ValidationUtils.validate_json_file(str(json_file))

        self.assertTrue(result.is_valid)
        self.assertIn("valid JSON file", result.message)

    def test_validate_json_file_invalid_syntax(self):
        """Test JSON file validation for file with invalid JSON syntax."""
        # Create invalid JSON file
        json_file = Path(self.temp_dir) / "invalid.json"
        json_file.write_text('{"key": "value", "missing_quote: 42}')

        result = ValidationUtils.validate_json_file(str(json_file))

        self.assertFalse(result.is_valid)
        self.assertIn("Invalid JSON", result.message)

    def test_validate_json_file_missing(self):
        """Test JSON file validation for missing file."""
        missing_file = Path(self.temp_dir) / "missing.json"

        result = ValidationUtils.validate_json_file(str(missing_file))

        self.assertFalse(result.is_valid)
        self.assertIn("does not exist", result.message)

    @patch("utils.validation_utils.ValidationUtils._validate_with_pydantic")
    def test_validate_json_schema_valid(self, mock_pydantic):
        """Test JSON schema validation with valid data."""
        mock_pydantic.return_value = ValidationResult(
            is_valid=True, message="Schema validation passed"
        )

        json_data = {"name": "test", "age": 25}
        schema_class = MagicMock()

        result = ValidationUtils.validate_json_schema(json_data, schema_class)

        self.assertTrue(result.is_valid)
        mock_pydantic.assert_called_once_with(json_data, schema_class)

    @patch("utils.validation_utils.ValidationUtils._validate_with_pydantic")
    def test_validate_json_schema_invalid(self, mock_pydantic):
        """Test JSON schema validation with invalid data."""
        mock_pydantic.return_value = ValidationResult(
            is_valid=False,
            message="Schema validation failed",
            details={"errors": ["Missing required field"]},
        )

        json_data = {"name": "test"}  # Missing age field
        schema_class = MagicMock()

        result = ValidationUtils.validate_json_schema(json_data, schema_class)

        self.assertFalse(result.is_valid)
        self.assertIn("Schema validation failed", result.message)

    def test_validate_forbidden_patterns_clean(self):
        """Test forbidden pattern validation for clean path."""
        clean_path = "normal/path/to/file.txt"
        forbidden_patterns = [r"\.\.[\\//]", r"[<>:'|?*]"]

        result = ValidationUtils.validate_forbidden_patterns(
            clean_path, forbidden_patterns
        )

        self.assertTrue(result.is_valid)
        self.assertIn("No forbidden patterns", result.message)

    def test_validate_forbidden_patterns_violation(self):
        """Test forbidden pattern validation with pattern violation."""
        malicious_path = "../../../etc/passwd"
        forbidden_patterns = [r"\.\.[\\/]"]

        result = ValidationUtils.validate_forbidden_patterns(
            malicious_path, forbidden_patterns
        )

        self.assertFalse(result.is_valid)
        self.assertIn("Forbidden pattern", result.message)

    def test_validate_forbidden_patterns_multiple_violations(self):
        """Test forbidden pattern validation with multiple violations."""
        bad_path = "../bad<file>name.txt"
        forbidden_patterns = [r"\.\.[\\//]", r"[<>:'|?*]"]

        result = ValidationUtils.validate_forbidden_patterns(
            bad_path, forbidden_patterns
        )

        self.assertFalse(result.is_valid)
        self.assertIn("Forbidden pattern", result.message)

    def test_validate_forbidden_patterns_empty_patterns(self):
        """Test forbidden pattern validation with empty pattern list."""
        any_path = "any/path/here"

        result = ValidationUtils.validate_forbidden_patterns(any_path, [])

        self.assertTrue(result.is_valid)
        self.assertIn("No patterns to check", result.message)

    def test_validate_path_length_valid(self):
        """Test path length validation for valid length."""
        normal_path = "normal/path/to/file.txt"

        result = ValidationUtils.validate_path_length(normal_path, max_length=100)

        self.assertTrue(result.is_valid)
        self.assertIn("Path length is acceptable", result.message)

    def test_validate_path_length_too_long(self):
        """Test path length validation for path that's too long."""
        long_path = "very/" * 50 + "long/path.txt"  # Create very long path

        result = ValidationUtils.validate_path_length(long_path, max_length=50)

        self.assertFalse(result.is_valid)
        self.assertIn("Path too long", result.message)
        self.assertIn(str(len(long_path)), result.message)

    def test_validate_path_length_empty(self):
        """Test path length validation for empty path."""
        result = ValidationUtils.validate_path_length("", max_length=100)

        self.assertFalse(result.is_valid)
        self.assertIn("Empty path", result.message)

    def test_validate_cross_references_valid(self):
        """Test cross-reference validation for valid references."""
        config = {
            "source_path": "/path/to/source",
            "target_path": "/path/to/target",
            "references": {"ref1": "source_path", "ref2": "target_path"},
        }

        result = ValidationUtils.validate_cross_references(config)

        self.assertTrue(result.is_valid)
        self.assertIn("All cross-references are valid", result.message)

    def test_validate_cross_references_invalid(self):
        """Test cross-reference validation for invalid references."""
        config = {
            "source_path": "/path/to/source",
            "references": {
                "ref1": "source_path",
                "ref2": "nonexistent_key",  # Invalid reference
            },
        }

        result = ValidationUtils.validate_cross_references(config)

        self.assertFalse(result.is_valid)
        self.assertIn("Invalid cross-reference", result.message)
        self.assertIn("nonexistent_key", result.message)

    def test_validate_cross_references_no_references(self):
        """Test cross-reference validation with no references section."""
        config = {"source_path": "/path/to/source", "target_path": "/path/to/target"}

        result = ValidationUtils.validate_cross_references(config)

        self.assertTrue(result.is_valid)
        self.assertIn("No cross-references to validate", result.message)

    def test_validate_cross_references_empty_references(self):
        """Test cross-reference validation with empty references."""
        config = {"source_path": "/path/to/source", "references": {}}

        result = ValidationUtils.validate_cross_references(config)

        self.assertTrue(result.is_valid)
        self.assertIn("No cross-references to validate", result.message)

    def test_combine_validation_results_all_valid(self):
        """Test combining validation results when all are valid."""
        results = [
            ValidationResult(True, "Test 1 passed"),
            ValidationResult(True, "Test 2 passed"),
            ValidationResult(True, "Test 3 passed"),
        ]

        combined = ValidationUtils.combine_validation_results(results)

        self.assertTrue(combined.is_valid)
        self.assertIn("All validations passed", combined.message)
        self.assertEqual(len(combined.details["individual_results"]), 3)

    def test_combine_validation_results_some_invalid(self):
        """Test combining validation results when some are invalid."""
        results = [
            ValidationResult(True, "Test 1 passed"),
            ValidationResult(False, "Test 2 failed"),
            ValidationResult(True, "Test 3 passed"),
        ]

        combined = ValidationUtils.combine_validation_results(results)

        self.assertFalse(combined.is_valid)
        self.assertIn("1 validation(s) failed", combined.message)
        self.assertEqual(len(combined.details["failed_validations"]), 1)

    def test_combine_validation_results_empty(self):
        """Test combining empty validation results list."""
        combined = ValidationUtils.combine_validation_results([])

        self.assertTrue(combined.is_valid)
        self.assertIn("No validations to combine", combined.message)

    def test_create_validation_summary_all_passed(self):
        """Test creating validation summary when all tests pass."""
        results = {
            "file_check": ValidationResult(True, "File exists"),
            "json_check": ValidationResult(True, "Valid JSON"),
            "schema_check": ValidationResult(True, "Schema valid"),
        }

        summary = ValidationUtils.create_validation_summary(results)

        self.assertTrue(summary.is_valid)
        self.assertIn("All 3 validations passed", summary.message)
        self.assertEqual(summary.details["total_validations"], 3)
        self.assertEqual(summary.details["passed_validations"], 3)
        self.assertEqual(summary.details["failed_validations"], 0)

    def test_create_validation_summary_some_failed(self):
        """Test creating validation summary when some tests fail."""
        results = {
            "file_check": ValidationResult(True, "File exists"),
            "json_check": ValidationResult(False, "Invalid JSON"),
            "schema_check": ValidationResult(False, "Schema invalid"),
        }

        summary = ValidationUtils.create_validation_summary(results)

        self.assertFalse(summary.is_valid)
        self.assertIn("2 out of 3 validations failed", summary.message)
        self.assertEqual(summary.details["total_validations"], 3)
        self.assertEqual(summary.details["passed_validations"], 1)
        self.assertEqual(summary.details["failed_validations"], 2)
        self.assertIn("failed_validation_names", summary.details)
        self.assertEqual(len(summary.details["failed_validation_names"]), 2)

    def test_create_validation_summary_empty(self):
        """Test creating validation summary with empty results."""
        summary = ValidationUtils.create_validation_summary({})

        self.assertTrue(summary.is_valid)
        self.assertIn("No validations performed", summary.message)
        self.assertEqual(summary.details["total_validations"], 0)

    def test_pydantic_validation_mock(self):
        """Test the private Pydantic validation method with mock."""
        # This tests the structure of the method without actual Pydantic dependency
        test_data = {"name": "test", "age": 25}

        # Mock schema class
        mock_schema = MagicMock()
        mock_instance = MagicMock()
        mock_schema.return_value = mock_instance

        with patch("pydantic.BaseModel", mock_schema):
            try:
                result = ValidationUtils._validate_with_pydantic(test_data, mock_schema)
                # If Pydantic is available, should return ValidationResult
                self.assertIsInstance(result, ValidationResult)
            except ImportError:
                # If Pydantic is not available, should handle gracefully
                result = ValidationUtils._validate_with_pydantic(test_data, mock_schema)
                self.assertFalse(result.is_valid)
                self.assertIn("Pydantic not available", result.message)


if __name__ == "__main__":
    unittest.main()
