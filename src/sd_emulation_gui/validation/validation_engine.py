"""Validation Engine

Centralized validation system to reduce code duplication
and provide consistent validation across all modules.
"""

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from typing import Any

from interfaces.data_interfaces import OperationData
from interfaces.service_interfaces import ValidationResult
from utils.path_utils import PathUtils


class ValidationRule(ABC):
    """Base class for validation rules."""

    def __init__(self, rule_id: str, description: str, severity: str = "error"):
        self.rule_id = rule_id
        self.description = description
        self.severity = severity

    @abstractmethod
    def validate(self, target: Any, context: dict[str, Any] = None) -> ValidationResult:
        """Validate the target against this rule."""
        pass

    def create_result(
        self,
        is_valid: bool,
        message: str,
        target_path: str = "",
        details: dict[str, Any] = None,
        suggested_fix: str = None,
    ) -> ValidationResult:
        """Create a validation result."""
        return ValidationResult(
            is_valid=is_valid,
            message=message,
            rule_id=self.rule_id,
            target_path=target_path,
            severity=self.severity,
            details=details or {},
            suggested_fix=suggested_fix,
            validation_timestamp=datetime.now().isoformat(),
        )


class PathValidationRule(ValidationRule):
    """Validation rule for file system paths."""

    def __init__(
        self,
        must_exist: bool = True,
        must_be_absolute: bool = True,
        must_be_directory: bool = False,
        must_be_file: bool = False,
        allowed_extensions: list[str] = None,
    ):
        super().__init__("path_validation", "Validate file system paths")
        self.must_exist = must_exist
        self.must_be_absolute = must_be_absolute
        self.must_be_directory = must_be_directory
        self.must_be_file = must_be_file
        self.allowed_extensions = allowed_extensions or []

    def validate(self, target: str, context: dict[str, Any] = None) -> ValidationResult:
        """Validate a file system path."""
        if not isinstance(target, str):
            return self.create_result(
                False,
                f"Path must be a string, got {type(target).__name__}",
                str(target),
                {"actual_type": type(target).__name__},
                "Provide a valid string path",
            )

        if not target.strip():
            return self.create_result(
                False, "Path cannot be empty", target, {}, "Provide a non-empty path"
            )

        errors = []

        # Check if absolute
        if self.must_be_absolute and not PathUtils.is_absolute(target):
            errors.append("Path must be absolute")

        # Check if exists
        if self.must_exist and not PathUtils.path_exists(target):
            errors.append("Path does not exist")

        # Check if directory
        if (
            self.must_be_directory
            and PathUtils.path_exists(target)
            and not PathUtils.is_directory(target)
        ):
            errors.append("Path must be a directory")

        # Check if file
        if (
            self.must_be_file
            and PathUtils.path_exists(target)
            and PathUtils.is_directory(target)
        ):
            errors.append("Path must be a file")

        # Check file extension
        if (
            self.allowed_extensions
            and PathUtils.path_exists(target)
            and not PathUtils.is_directory(target)
        ):
            file_ext = PathUtils.get_file_extension(target).lower()
            if file_ext not in [ext.lower() for ext in self.allowed_extensions]:
                errors.append(
                    f"File extension '{file_ext}' not allowed. Allowed: {self.allowed_extensions}"
                )

        is_valid = len(errors) == 0
        message = (
            "Path validation passed"
            if is_valid
            else f"Path validation failed: {'; '.join(errors)}"
        )

        return self.create_result(
            is_valid,
            message,
            target,
            {
                "errors": errors,
                "path_info": {
                    "exists": PathUtils.path_exists(target),
                    "is_absolute": PathUtils.is_absolute(target),
                    "is_directory": (
                        PathUtils.is_directory(target)
                        if PathUtils.path_exists(target)
                        else None
                    ),
                    "extension": (
                        PathUtils.get_file_extension(target)
                        if PathUtils.path_exists(target)
                        else None
                    ),
                },
            },
            "Fix path issues: " + "; ".join(errors) if errors else None,
        )


class ConfigurationValidationRule(ValidationRule):
    """Validation rule for configuration parameters."""

    def __init__(
        self,
        required_fields: list[str],
        field_types: dict[str, type] = None,
        field_validators: dict[str, Callable] = None,
    ):
        super().__init__(
            "configuration_validation", "Validate configuration parameters"
        )
        self.required_fields = required_fields
        self.field_types = field_types or {}
        self.field_validators = field_validators or {}

    def validate(
        self, target: dict[str, Any], context: dict[str, Any] = None
    ) -> ValidationResult:
        """Validate configuration dictionary."""
        if not isinstance(target, dict):
            return self.create_result(
                False,
                f"Configuration must be a dictionary, got {type(target).__name__}",
                "configuration",
                {"actual_type": type(target).__name__},
                "Provide a valid configuration dictionary",
            )

        errors = []

        # Check required fields
        for field in self.required_fields:
            if field not in target or target[field] is None:
                errors.append(f"Required field '{field}' is missing or None")

        # Check field types
        for field, expected_type in self.field_types.items():
            if field in target and target[field] is not None:
                if not isinstance(target[field], expected_type):
                    errors.append(
                        f"Field '{field}' must be of type {expected_type.__name__}, got {type(target[field]).__name__}"
                    )

        # Run custom validators
        for field, validator in self.field_validators.items():
            if field in target:
                try:
                    if not validator(target[field]):
                        errors.append(f"Field '{field}' failed custom validation")
                except Exception as e:
                    errors.append(f"Field '{field}' validation error: {str(e)}")

        is_valid = len(errors) == 0
        message = (
            "Configuration validation passed"
            if is_valid
            else f"Configuration validation failed: {'; '.join(errors)}"
        )

        return self.create_result(
            is_valid,
            message,
            "configuration",
            {
                "errors": errors,
                "provided_fields": list(target.keys()),
                "required_fields": self.required_fields,
                "missing_fields": [
                    f
                    for f in self.required_fields
                    if f not in target or target[f] is None
                ],
            },
            "Fix configuration issues: " + "; ".join(errors) if errors else None,
        )


class OperationDataValidationRule(ValidationRule):
    """Validation rule for operation data structures."""

    def __init__(self):
        super().__init__(
            "operation_data_validation", "Validate operation data structure"
        )
        self.required_fields = [
            "operation_id",
            "operation_type",
            "service_name",
            "status",
        ]
        self.valid_statuses = ["pending", "running", "completed", "failed", "cancelled"]

    def validate(
        self, target: OperationData, context: dict[str, Any] = None
    ) -> ValidationResult:
        """Validate operation data structure."""
        if not isinstance(target, dict):
            return self.create_result(
                False,
                f"Operation data must be a dictionary, got {type(target).__name__}",
                "operation_data",
                {"actual_type": type(target).__name__},
                "Provide a valid operation data dictionary",
            )

        errors = []

        # Check required fields
        for field in self.required_fields:
            if field not in target or not target[field]:
                errors.append(f"Required field '{field}' is missing or empty")

        # Validate status
        if "status" in target and target["status"] not in self.valid_statuses:
            errors.append(
                f"Invalid status '{target['status']}'. Must be one of: {self.valid_statuses}"
            )

        # Validate progress percent
        if "progress_percent" in target:
            progress = target["progress_percent"]
            if not isinstance(progress, (int, float)) or progress < 0 or progress > 100:
                errors.append("Progress percent must be a number between 0 and 100")

        # Validate operation_id format
        if "operation_id" in target:
            op_id = target["operation_id"]
            if not isinstance(op_id, str) or len(op_id) < 1:
                errors.append("Operation ID must be a non-empty string")

        # Validate timestamps
        timestamp_fields = ["created_at", "started_at", "completed_at"]
        for field in timestamp_fields:
            if field in target and target[field]:
                try:
                    datetime.fromisoformat(target[field].replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"Field '{field}' must be a valid ISO timestamp")

        is_valid = len(errors) == 0
        message = (
            "Operation data validation passed"
            if is_valid
            else f"Operation data validation failed: {'; '.join(errors)}"
        )

        return self.create_result(
            is_valid,
            message,
            "operation_data",
            {
                "errors": errors,
                "operation_data": target,
                "provided_fields": list(target.keys()),
                "required_fields": self.required_fields,
            },
            "Fix operation data issues: " + "; ".join(errors) if errors else None,
        )


class RegexValidationRule(ValidationRule):
    """Validation rule using regular expressions."""

    def __init__(
        self,
        pattern: str,
        rule_id: str,
        description: str,
        case_sensitive: bool = True,
        must_match: bool = True,
    ):
        super().__init__(rule_id, description)
        flags = 0 if case_sensitive else re.IGNORECASE
        self.pattern = re.compile(pattern, flags)
        self.pattern_str = pattern
        self.must_match = must_match

    def validate(self, target: str, context: dict[str, Any] = None) -> ValidationResult:
        """Validate string against regex pattern."""
        if not isinstance(target, str):
            return self.create_result(
                False,
                f"Target must be a string, got {type(target).__name__}",
                str(target),
                {"actual_type": type(target).__name__},
                "Provide a valid string",
            )

        matches = bool(self.pattern.search(target))
        is_valid = matches if self.must_match else not matches

        if is_valid:
            message = f"String matches pattern '{self.pattern_str}'"
        else:
            if self.must_match:
                message = f"String does not match required pattern '{self.pattern_str}'"
            else:
                message = f"String matches forbidden pattern '{self.pattern_str}'"

        return self.create_result(
            is_valid,
            message,
            target,
            {
                "pattern": self.pattern_str,
                "matches": matches,
                "must_match": self.must_match,
            },
            f"Ensure string {'matches' if self.must_match else 'does not match'} pattern '{self.pattern_str}'",
        )


class ValidationEngine:
    """Central validation engine that manages and executes validation rules."""

    def __init__(self):
        self.rules: dict[str, ValidationRule] = {}
        self.rule_groups: dict[str, list[str]] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        """Register default validation rules."""
        # Path validation rules
        self.register_rule(
            PathValidationRule(must_exist=True, must_be_absolute=True),
            "path_exists_absolute",
        )
        self.register_rule(
            PathValidationRule(must_exist=False, must_be_absolute=True), "path_absolute"
        )
        self.register_rule(
            PathValidationRule(must_exist=True, must_be_directory=True),
            "directory_exists",
        )
        self.register_rule(
            PathValidationRule(must_exist=True, must_be_file=True), "file_exists"
        )

        # Configuration validation
        self.register_rule(
            ConfigurationValidationRule(["service_name", "log_level"]),
            "basic_service_config",
        )

        # Operation data validation
        self.register_rule(OperationDataValidationRule(), "operation_data")

        # Common regex patterns
        self.register_rule(
            RegexValidationRule(
                r"^[a-zA-Z0-9_-]+$", "alphanumeric_id", "Alphanumeric ID validation"
            ),
            "alphanumeric_id",
        )
        self.register_rule(
            RegexValidationRule(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "email",
                "Email validation",
            ),
            "email",
        )
        self.register_rule(
            RegexValidationRule(
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
                "iso_timestamp",
                "ISO timestamp validation",
            ),
            "iso_timestamp",
        )

        # Create rule groups
        self.create_rule_group(
            "path_validation",
            [
                "path_exists_absolute",
                "path_absolute",
                "directory_exists",
                "file_exists",
            ],
        )
        self.create_rule_group(
            "data_validation", ["operation_data", "basic_service_config"]
        )
        self.create_rule_group(
            "format_validation", ["alphanumeric_id", "email", "iso_timestamp"]
        )

    def register_rule(self, rule: ValidationRule, rule_name: str):
        """Register a validation rule."""
        self.rules[rule_name] = rule

    def create_rule_group(self, group_name: str, rule_names: list[str]):
        """Create a group of validation rules."""
        self.rule_groups[group_name] = rule_names

    def validate_single(
        self, rule_name: str, target: Any, context: dict[str, Any] = None
    ) -> ValidationResult:
        """Validate target against a single rule."""
        if rule_name not in self.rules:
            return ValidationResult(
                is_valid=False,
                message=f"Unknown validation rule: {rule_name}",
                rule_id="unknown_rule",
                target_path=str(target),
                severity="error",
                details={"rule_name": rule_name},
                suggested_fix=f"Use a valid rule name. Available: {list(self.rules.keys())}",
                validation_timestamp=datetime.now().isoformat(),
            )

        rule = self.rules[rule_name]
        return rule.validate(target, context)

    def validate_group(
        self, group_name: str, target: Any, context: dict[str, Any] = None
    ) -> list[ValidationResult]:
        """Validate target against a group of rules."""
        if group_name not in self.rule_groups:
            return [
                ValidationResult(
                    is_valid=False,
                    message=f"Unknown validation group: {group_name}",
                    rule_id="unknown_group",
                    target_path=str(target),
                    severity="error",
                    details={"group_name": group_name},
                    suggested_fix=f"Use a valid group name. Available: {list(self.rule_groups.keys())}",
                    validation_timestamp=datetime.now().isoformat(),
                )
            ]

        results = []
        for rule_name in self.rule_groups[group_name]:
            result = self.validate_single(rule_name, target, context)
            results.append(result)

        return results

    def validate_multiple(
        self, rule_names: list[str], target: Any, context: dict[str, Any] = None
    ) -> list[ValidationResult]:
        """Validate target against multiple rules."""
        results = []
        for rule_name in rule_names:
            result = self.validate_single(rule_name, target, context)
            results.append(result)

        return results

    def validate_path(
        self,
        path: str,
        must_exist: bool = True,
        must_be_absolute: bool = True,
        must_be_directory: bool = False,
        must_be_file: bool = False,
        allowed_extensions: list[str] = None,
    ) -> ValidationResult:
        """Convenience method for path validation."""
        rule = PathValidationRule(
            must_exist=must_exist,
            must_be_absolute=must_be_absolute,
            must_be_directory=must_be_directory,
            must_be_file=must_be_file,
            allowed_extensions=allowed_extensions,
        )
        return rule.validate(path)

    def validate_config(
        self,
        config: dict[str, Any],
        required_fields: list[str],
        field_types: dict[str, type] = None,
        field_validators: dict[str, Callable] = None,
    ) -> ValidationResult:
        """Convenience method for configuration validation."""
        rule = ConfigurationValidationRule(
            required_fields=required_fields,
            field_types=field_types,
            field_validators=field_validators,
        )
        return rule.validate(config)

    def validate_operation_data(
        self, operation_data: OperationData
    ) -> ValidationResult:
        """Convenience method for operation data validation."""
        return self.validate_single("operation_data", operation_data)

    def validate_regex(
        self, text: str, pattern: str, must_match: bool = True
    ) -> ValidationResult:
        """Convenience method for regex validation."""
        rule = RegexValidationRule(
            pattern, "custom_regex", "Custom regex validation", must_match=must_match
        )
        return rule.validate(text)

    def get_validation_summary(self, results: list[ValidationResult]) -> dict[str, Any]:
        """Get summary of validation results."""
        total = len(results)
        passed = sum(1 for r in results if r.is_valid)
        failed = total - passed

        errors = [r for r in results if not r.is_valid and r.severity == "error"]
        warnings = [r for r in results if not r.is_valid and r.severity == "warning"]

        return {
            "total_validations": total,
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "all_passed": failed == 0,
            "has_errors": len(errors) > 0,
            "has_warnings": len(warnings) > 0,
            "failed_rules": [r.rule_id for r in results if not r.is_valid],
        }

    def get_available_rules(self) -> dict[str, str]:
        """Get list of available validation rules."""
        return {name: rule.description for name, rule in self.rules.items()}

    def get_available_groups(self) -> dict[str, list[str]]:
        """Get list of available rule groups."""
        return self.rule_groups.copy()


# Global validation engine instance
validation_engine = ValidationEngine()


# Convenience functions for common validations


def validate_path(path: str, **kwargs) -> ValidationResult:
    """Validate a file system path."""
    return validation_engine.validate_path(path, **kwargs)


def validate_config(
    config: dict[str, Any], required_fields: list[str], **kwargs
) -> ValidationResult:
    """Validate a configuration dictionary."""
    return validation_engine.validate_config(config, required_fields, **kwargs)


def validate_operation_data(operation_data: OperationData) -> ValidationResult:
    """Validate operation data structure."""
    return validation_engine.validate_operation_data(operation_data)


def validate_regex(
    text: str, pattern: str, must_match: bool = True
) -> ValidationResult:
    """Validate text against regex pattern."""
    return validation_engine.validate_regex(text, pattern, must_match)


def validate_multiple(
    targets: list[tuple], rule_names: list[str]
) -> list[ValidationResult]:
    """Validate multiple targets against specified rules."""
    results = []
    for target, context in targets:
        for rule_name in rule_names:
            result = validation_engine.validate_single(rule_name, target, context)
            results.append(result)
    return results