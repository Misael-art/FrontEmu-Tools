"""
Validation Utilities Module

This module provides validation utilities for the SD Emulation GUI application.
"""

import json
import os
from typing import Any, Dict, List, NamedTuple
import re


class ValidationResult:
    """Rich validation result supporting GUI, tests and reporting."""

    def __init__(
        self,
        file_path: str | None = None,
        message: str = "",
        details: Dict[str, Any] | None = None,
        *,
        status: str = "valid",
        errors: List[str] | None = None,
        warnings: List[str] | None = None,
        info: List[str] | None = None,
        metrics: Dict[str, Any] | None = None,
        schema_valid: bool = True,
        schema_errors: List[str] | None = None,
        cross_reference_valid: bool = True,
        cross_reference_errors: List[str] | None = None,
        cross_reference_warnings: List[str] | None = None,
        validation_details: Dict[str, Any] | None = None,
        suggested_actions: List[str] | None = None,
        is_valid: bool | None = None,
    ) -> None:
        if isinstance(file_path, bool):
            status = "valid" if file_path else "error"
            file_path = None
        if isinstance(message, bool):
            status = "valid" if message else "error"
            message = ""
        if is_valid is not None:
            status = "valid" if is_valid else "error"
        self.file_path = file_path
        self.message = message
        self.details: Dict[str, Any] = details or {}
        self.status = status
        self.errors: List[str] = errors or []
        self.warnings: List[str] = warnings or []
        self.info: List[str] = info or []
        self.metrics: Dict[str, Any] = metrics or {}
        self.schema_valid = schema_valid
        self.schema_errors: List[str] = schema_errors or []
        self.cross_reference_valid = cross_reference_valid
        self.cross_reference_errors: List[str] = cross_reference_errors or []
        self.cross_reference_warnings: List[str] = cross_reference_warnings or []
        self.validation_details: Dict[str, Any] = validation_details or {}
        self.suggested_actions: List[str] = suggested_actions or []
        if "message" in self.details and not self.message:
            self.message = self.details.get("message", "")

    # Compatibility properties expected by tests
    @property
    def is_valid(self) -> bool:  # type: ignore[override]
        return self.status == "valid"
    
    @is_valid.setter
    def is_valid(self, value: bool) -> None:
        """Set validity by updating status."""
        if value:
            # Only set to valid if there are no errors
            if not self.errors:
                self.status = "valid"
            else:
                # Keep error status if there are errors
                self.status = "error"
        else:
            self.status = "error"

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def __str__(self) -> str:
        return f"ValidationResult(valid={self.is_valid}, message={self.message!r})"

    # --- mutation helpers -------------------------------------------------

    def add_error(self, error: str, *, schema: bool = False, cross_reference: bool = False) -> None:
        self.errors.append(error)
        if not self.message:
            self.message = error
        if schema:
            self.schema_valid = False
            self.schema_errors.append(error)
        if cross_reference:
            self.cross_reference_valid = False
            self.cross_reference_errors.append(error)
        self.status = "error"

    def add_warning(self, warning: str, *, cross_reference: bool = False) -> None:
        self.warnings.append(warning)
        if not self.message:
            self.message = warning
        if cross_reference:
            self.cross_reference_warnings.append(warning)
        if self.status == "valid":
            self.status = "warning"

    def add_info(self, info: str) -> None:
        self.info.append(info)
        if not self.message:
            self.message = info

    def add_metric(self, name: str, value: Any) -> None:
        self.metrics[name] = value

    def add_detail(self, key: str, value: Any) -> None:
        self.validation_details[key] = value

    def add_suggested_action(self, action: str) -> None:
        self.suggested_actions.append(action)

    # --- helpers ----------------------------------------------------------

    def set_schema_valid(self, valid: bool, *, errors: List[str] | None = None) -> None:
        self.schema_valid = valid
        if errors:
            self.schema_errors.extend(errors)
            if not valid:
                for err in errors:
                    if err not in self.errors:
                        self.errors.append(err)
                self.status = "error"

    def set_cross_reference_valid(self, valid: bool, *, errors: List[str] | None = None, warnings: List[str] | None = None) -> None:
        self.cross_reference_valid = valid
        if errors:
            self.cross_reference_errors.extend(errors)
            if not valid:
                for err in errors:
                    if err not in self.errors:
                        self.errors.append(err)
                self.status = "error"
        if warnings:
            self.cross_reference_warnings.extend(warnings)
            for warn in warnings:
                if warn not in self.warnings:
                    self.warnings.append(warn)
            if self.status == "valid":
                self.status = "warning"

    def has_warnings(self) -> bool:
        return bool(self.warnings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "metrics": self.metrics,
            "schema_valid": self.schema_valid,
            "schema_errors": self.schema_errors,
            "cross_reference_valid": self.cross_reference_valid,
            "cross_reference_errors": self.cross_reference_errors,
            "cross_reference_warnings": self.cross_reference_warnings,
            "validation_details": self.validation_details,
            "suggested_actions": self.suggested_actions,
        }


class ValidationUtils:
    """Validation utility functions."""

    # ------------------------------
    # File and directory checks
    # ------------------------------

    @staticmethod
    def validate_file_exists(path: str) -> ValidationResult:
        result = ValidationResult(path, message="File exists")
        if not path:
            return ValidationResult(None, message="Empty path", status="error")
        if not os.path.exists(path):
            return ValidationResult(path, message=f"File does not exist: {path}", status="error")
        if not os.path.isfile(path):
            return ValidationResult(path, message=f"Path is not a file: {path}", status="error")
        result.add_info(f"File exists: {path}")
        return result

    @staticmethod
    def validate_directory_exists(path: str) -> ValidationResult:
        if not path:
            return ValidationResult(None, message="Empty path", status="error")
        if not os.path.exists(path):
            return ValidationResult(path, message=f"Directory does not exist: {path}", status="error")
        if not os.path.isdir(path):
            return ValidationResult(path, message=f"Path is not a directory: {path}", status="error")
        result = ValidationResult(path, message=f"Directory exists: {path}")
        result.add_info(f"Directory exists: {path}")
        return result

    @staticmethod
    def validate_path(path: str) -> bool:
        return os.path.exists(path)

    @staticmethod
    def validate_path_length(path: str, max_length: int) -> ValidationResult:
        if not path:
            return ValidationResult(None, message="Empty path", status="error")
        length = len(path)
        if length > max_length:
            return ValidationResult(None, message=f"Path too long: {length} > {max_length}", status="error")
        result = ValidationResult(None, message="Path length is acceptable")
        result.add_metric("path_length", length)
        return result

    # ------------------------------
    # JSON validations
    # ------------------------------

    @staticmethod
    def validate_json_file(file_path: str) -> ValidationResult:
        result = ValidationResult(file_path, message=f"Validating JSON file: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json.load(f)
            success_msg = "valid JSON file"
            result.message = success_msg
            result.add_info(success_msg)
        except json.JSONDecodeError as e:
            result.message = f"Invalid JSON format: {e}"
            result.add_error(f"Invalid JSON format: {e}")
        except FileNotFoundError:
            result.message = f"File does not exist: {file_path}"
            result.add_error(f"File does not exist: {file_path}")
        except Exception as e:
            result.message = f"Error reading file: {e}"
            result.add_error(f"Error reading file: {e}")
        return result

    @staticmethod
    def _validate_with_pydantic(data: dict, schema_class: Any) -> ValidationResult:
        try:
            schema_class(**data)
            res = ValidationResult(None, message="Schema validation passed")
            res.add_info("Schema validation passed")
            return res
        except Exception as e:
            res = ValidationResult(None, message=f"Schema validation failed: {e}", status="error")
            res.add_error(f"Schema validation failed: {e}", schema=True)
            return res

    @staticmethod
    def validate_json_schema(data: dict, schema_class: Any) -> ValidationResult:
        return ValidationUtils._validate_with_pydantic(data, schema_class)

    @staticmethod
    def validate_json_syntax(json_str: str) -> ValidationResult:
        if not json_str:
            return ValidationResult(None, message="Empty JSON string", status="error")
        try:
            json.loads(json_str)
            result = ValidationResult(None, message="valid JSON")
            result.add_info("valid JSON")
            return result
        except json.JSONDecodeError as e:
            return ValidationResult(None, message=f"Invalid JSON syntax: {e}", status="error")

    # ------------------------------
    # Forbidden patterns / cross references
    # ------------------------------

    @staticmethod
    def validate_forbidden_patterns(path: str, patterns: List[str]) -> ValidationResult:
        if not patterns:
            return ValidationResult(path, message="No patterns to check")
        for pattern in patterns:
            if re.search(pattern, path):
                return ValidationResult(path, message=f"Forbidden pattern detected: {pattern}", status="error")
        res = ValidationResult(path, message="No forbidden patterns detected")
        res.add_info("No forbidden patterns detected")
        return res

    @staticmethod
    def validate_cross_references(config: Dict[str, Any]) -> ValidationResult:
        references = config.get("references")
        if not references:
            return ValidationResult(None, message="No cross-references to validate")
        fields = set(config.keys())
        invalid = [ref for ref in references.values() if ref not in fields]
        if invalid:
            res = ValidationResult(None, message=f"Invalid cross-reference: {', '.join(invalid)}", status="error")
            for ref in invalid:
                res.add_error(f"Invalid cross-reference: {ref}", cross_reference=True)
            return res
        result = ValidationResult(None, message="All cross-references are valid")
        result.add_info("All cross-references are valid")
        return result

    # ------------------------------
    # Aggregations / summaries
    # ------------------------------

    @staticmethod
    def combine_validation_results(results: List[ValidationResult]) -> ValidationResult:
        if not results:
            return ValidationResult(None, message="No validations to combine")
        combined = ValidationResult(None, message="All validations passed")
        combined.validation_details["individual_results"] = []
        combined.details["individual_results"] = combined.validation_details["individual_results"]
        failed = []
        for res in results:
            combined.validation_details["individual_results"].append(res.to_dict())
            if not res.is_valid:
                failed.append(res.message or res.file_path or "unknown")
        if failed:
            combined.status = "error"
            combined.message = f"{len(failed)} validation(s) failed"
            combined.validation_details["failed_validations"] = failed
            combined.details["failed_validations"] = failed
        else:
            combined.add_info("All validations passed")
        return combined

    @staticmethod
    def create_validation_summary(results: Dict[str, ValidationResult]) -> ValidationResult:
        total = len(results)
        passed = sum(1 for r in results.values() if r.is_valid)
        failed = total - passed
        summary = ValidationResult(None, message="Validation summary")
        summary.validation_details["total_validations"] = total
        summary.validation_details["passed_validations"] = passed
        summary.validation_details["failed_validations"] = failed
        summary.validation_details["failed_validation_names"] = [
            name for name, res in results.items() if not res.is_valid
        ]
        summary.details.update(summary.validation_details)
        if total == 0:
            summary.message = "No validations performed"
        elif failed == 0:
            summary.message = f"All {total} validations passed"
        else:
            summary.status = "error"
            summary.message = f"{failed} out of {total} validations failed"
        return summary

    @staticmethod
    def validate_required_keys(data: Dict[str, Any], required_keys: List[str]) -> List[str]:
        return [key for key in required_keys if key not in data]
