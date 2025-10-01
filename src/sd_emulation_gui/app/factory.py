"""
Factory Module

This module provides factory classes for creating fallback objects
when imports are not available. This replaces the scattered try/except
ImportError blocks throughout the codebase.
"""

from typing import Any, Dict, List, Optional, Type


class FallbackFactory:
    """Factory for creating fallback objects when imports fail."""

    @staticmethod
    def create_service_fallback(service_name: str) -> Any:
        """Create a fallback service object."""
        class FallbackService:
            def __init__(self, name: str = service_name):
                self.service_name = name
                self.logger = None

            def __getattr__(self, name: str) -> Any:
                """Return None for any attribute access."""
                return None

            def __call__(self, *args, **kwargs) -> Any:
                """Return None when called."""
                return None

        return FallbackService(service_name)

    @staticmethod
    def create_model_fallback(model_name: str) -> Any:
        """Create a fallback model/dataclass."""
        class FallbackModel:
            def __init__(self, name: str = model_name, **kwargs):
                self.model_name = name
                for key, value in kwargs.items():
                    setattr(self, key, value)

            def __getattr__(self, name: str) -> Any:
                """Return None for any attribute access."""
                return None

            def __repr__(self) -> str:
                return f"FallbackModel({self.model_name})"

        return FallbackModel

    @staticmethod
    def create_utils_fallback(util_name: str) -> Any:
        """Create a fallback utilities object."""
        class FallbackUtils:
            def __init__(self, name: str = util_name):
                self.util_name = name

            @staticmethod
            def normalize_path(path: str) -> str:
                import os
                return os.path.normpath(path)

            @staticmethod
            def ensure_directory_exists(directory: str) -> None:
                import os
                os.makedirs(directory, exist_ok=True)

            @staticmethod
            def sanitize_input_path(path: str) -> str:
                return path

            @staticmethod
            def validate_safe_path(path: str, base_path: str) -> bool:
                return True

            @staticmethod
            def read_file(path: str) -> str:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception:
                    return ""

            @staticmethod
            def write_file(path: str, content: str) -> None:
                import os
                os.makedirs(os.path.dirname(path), exist_ok=True)
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(content)
                except Exception:
                    pass

        return FallbackUtils(util_name)

    @staticmethod
    def create_validation_result(file_path: str) -> Any:
        """Create a fallback validation result."""
        class FallbackValidationResult:
            def __init__(self, path: str):
                self.file_path = path
                self.status = "valid"
                self.errors: List[str] = []
                self.warnings: List[str] = []
                self.info: List[str] = []
                self.metrics: Dict[str, Any] = {}

            def add_error(self, error: str) -> None:
                self.errors.append(error)
                self.status = "error"

            def add_warning(self, warning: str) -> None:
                self.warnings.append(warning)

            def add_info(self, info: str) -> None:
                self.info.append(info)

            def is_valid(self) -> bool:
                return self.status == "valid"

            def has_warnings(self) -> bool:
                return len(self.warnings) > 0

        return FallbackValidationResult(file_path)

    @staticmethod
    def create_report_service() -> Any:
        """Create a fallback report service."""
        class FallbackReportService:
            def __init__(self, reports_dir: str = "reports"):
                self.reports_dir = reports_dir
                import os
                os.makedirs(reports_dir, exist_ok=True)

            def generate_report(self, report_type: str, data: Any) -> str:
                return f"Fallback report for {report_type}"

            def save_report(self, filename: str, content: str) -> None:
                import os
                with open(os.path.join(self.reports_dir, filename), 'w') as f:
                    f.write(content)

        return FallbackReportService()

    @staticmethod
    def get_fallback_for_module(module_name: str) -> Any:
        """Get appropriate fallback based on module name."""
        if module_name.startswith('services.'):
            return FallbackFactory.create_service_fallback(module_name.split('.')[-1])
        elif module_name.startswith('domain.'):
            return FallbackFactory.create_model_fallback(module_name.split('.')[-1])
        elif module_name.startswith('utils.'):
            return FallbackFactory.create_utils_fallback(module_name.split('.')[-1])
        elif module_name.startswith('adapters.'):
            return FallbackFactory.create_service_fallback(module_name.split('.')[-1])
        else:
            return FallbackFactory.create_service_fallback(module_name)
