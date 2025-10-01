"""
Configuration Validation Service

This service handles validation of configuration files and cross-reference
checking to ensure data consistency across all configuration components.
"""

from datetime import datetime
from typing import Any

# Import centralized systems
from sd_emulation_gui.app.imports_manager import configure_imports, import_with_fallback
from sd_emulation_gui.app.factory import FallbackFactory

# Configure imports centrally
configure_imports()

# Import with proper fallbacks
PathConfigManager = import_with_fallback(
    'path_config.PathConfigManager',
    FallbackFactory.create_service_fallback
)

PathResolver = import_with_fallback(
    'path_resolver.PathResolver',
    FallbackFactory.create_service_fallback
)
from sd_emulation_gui.domain.models import (
    AppConfig,
    ConsolidatedConfig,
    EmulatorMapping,
    EnterpriseConfig,
    FrontendEmulatorPaths,
    FrontendGlobalConfig,
    PlatformMapping,
    VariantMapping,
)
# Import utilities with simple fallbacks
try:
    from sd_emulation_gui.utils.base_service import BaseService
except ImportError:
    class BaseService:
        def __init__(self):
            pass

try:
    from sd_emulation_gui.utils.file_utils import FileUtils
except ImportError:
    class FileUtils:
        @staticmethod
        def read_file(path: str) -> str:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return ""

try:
    from sd_emulation_gui.utils.path_utils import PathUtils
except ImportError:
    import os
    class PathUtils:
        @staticmethod
        def normalize_path(path: str) -> str:
            return os.path.normpath(path)

try:
    from sd_emulation_gui.utils.validation_utils import ValidationResult, ValidationUtils
except ImportError:
    class ValidationResult:
        def __init__(self, file_path: str):
            self.file_path = file_path
            self.errors = []
            self.warnings = []
            self.info = []

    class ValidationUtils:
        @staticmethod
        def validate_path(path: str) -> bool:
            import os
            return os.path.exists(path)

# ValidationResult is now imported from utils


class ValidationSummary:
    """Summary of all validation results.

    Aggregates results from multiple file validations and provides overall metrics.
    """

    def __init__(self):
        """Initialize validation summary."""
        self.results: dict[str, ValidationResult] = {}
        self.timestamp = datetime.now().isoformat()
        self.total_files = 0
        self.valid_files = 0
        self.files_with_warnings = 0
        self.files_with_errors = 0
        self.overall_status = "valid"
        self.coverage_percentage = 0.0

    def add_result(self, file_path: str, result: ValidationResult) -> None:
        """Add a validation result to the summary.

        Args:
            file_path: Path of the validated file
            result: Validation result object
        """
        self.results[file_path] = result
        self.total_files += 1

        if result.is_valid and not result.warnings:
            self.valid_files += 1
        elif result.warnings:
            self.files_with_warnings += 1
        else:
            self.files_with_errors += 1

        # Update overall status
        if self.files_with_errors > 0:
            self.overall_status = "error"
        elif self.files_with_warnings > 0:
            self.overall_status = "warning"

        # Calculate coverage percentage
        if self.total_files > 0:
            self.coverage_percentage = (self.valid_files / self.total_files) * 100

    def get_summary_stats(self) -> dict[str, Any]:
        """Get summary statistics.

        Returns:
            Dictionary with validation metrics
        """
        return {
            "total_files": self.total_files,
            "valid_files": self.valid_files,
            "files_with_warnings": self.files_with_warnings,
            "files_with_errors": self.files_with_errors,
            "overall_status": self.overall_status,
            "coverage_percentage": round(self.coverage_percentage, 2),
            "timestamp": self.timestamp,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert validation summary to dictionary format for reporting."""
        return {
            "summary": self.get_summary_stats(),
            "results": {
                file_path: {
                    "status": result.status,
                    "schema_valid": result.schema_valid,
                    "cross_reference_valid": result.cross_reference_valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "info": result.info,
                    "metrics": result.metrics,
                }
                for file_path, result in self.results.items()
            },
        }


class ValidationService(BaseService):
    """Service for validating configuration files and cross-references."""

    def __init__(self, config_dir: str = None, base_path: str = None):
        """Initialize validation service.

        Args:
            config_dir: Directory containing configuration files (takes precedence over base_path)
            base_path: Base directory for configuration files (optional, uses dynamic path if not provided)
        """
        super().__init__()
        # Initialize path management
        self.path_config_manager = PathConfigManager()
        self.path_resolver = PathResolver()

        if config_dir:
            self.base_path = PathUtils.normalize_path(config_dir)
        elif base_path:
            self.base_path = PathUtils.normalize_path(base_path)
        else:
            # Use dynamic path resolution
            resolved_path = self.path_resolver.resolve_path("config_base_path").resolved_path
            self.base_path = PathUtils.normalize_path(resolved_path)
        self.config_files = [
            "config.json",
            "emulator_mapping.json",
            "platform_mapping.json",
            "variant_mapping.json",
            "frontend_config.json",
            "enterprise_config.json",
        ]

    def initialize(self) -> None:
        """Initialize ValidationService.

        This method is required by BaseService and performs any additional
        initialization needed after the constructor.
        """
        # ValidationService initialization is handled in __init__
        # This method is required by BaseService
        pass

    def validate_config(self, file_path: str) -> ValidationResult:
        """Validate a single configuration file.

        Args:
            file_path: Path to the configuration file

        Returns:
            ValidationResult containing validation outcome
        """
        result = ValidationResult(file_path)

        try:
            # Check if file exists using PathUtils
            full_path = PathUtils.join_path(self.base_path, file_path)
            if not PathUtils.path_exists(full_path):
                result.add_error(f"Arquivo de configuração não encontrado: {file_path}")
                return result

            # Validate JSON format using ValidationUtils
            json_result = ValidationUtils.validate_json_file(full_path)
            if not json_result.is_valid:
                result.errors.extend(json_result.errors)
                result.warnings.extend(json_result.warnings)
                result.is_valid = False
                return result

            # Read JSON data directly
            try:
                config_data = FileUtils.read_json_file(full_path)
            except Exception as e:
                result.add_error(f"Erro ao ler dados JSON: {e}")
                result.is_valid = False
                return result

            # Get file metrics using FileUtils
            file_size = FileUtils.get_file_size(full_path)
            file_content = FileUtils.read_text_file(full_path)
            line_count = len(file_content.splitlines())
            result.add_metric("file_size", file_size)
            result.add_metric("line_count", line_count)

            # Validate with Pydantic model if available
            model_class = self._get_model_for_file(file_path)
            if model_class:
                try:
                    model_class(**config_data)
                    result.add_info(
                        f"Validação de schema bem-sucedida para {file_path}"
                    )
                except Exception as e:
                    result.add_error(f"Erro de validação de schema: {e}")
                    result.schema_valid = False

            # Check required keys
            required_keys = self._get_required_keys(file_path)
            missing_keys = [key for key in required_keys if key not in config_data]
            if missing_keys:
                result.add_error(
                    f"Chaves obrigatórias ausentes: {', '.join(missing_keys)}"
                )

            if result.is_valid:
                result.add_info(f"Validação bem-sucedida para {file_path}")

            return result

        except Exception as e:
            result.add_error(f"Erro inesperado na validação: {e}")
            self.logger.error(f"Erro na validação de {file_path}: {e}")
            return result

    def validate_all(self) -> ValidationSummary:
        """Validate all configuration files.

        Returns:
            ValidationSummary containing results for all files
        """
        summary = ValidationSummary()

        # Validate individual files
        for config_file in self.config_files:
            result = self.validate_config(config_file)
            summary.add_result(config_file, result)

        # Perform cross-reference validation using ValidationUtils
        cross_ref_result = self._validate_cross_references_with_utils()
        summary.add_result("cross_references", cross_ref_result)

        return summary

    def _validate_cross_references_with_utils(self) -> ValidationResult:
        """Validate cross-references between configuration files using ValidationUtils.

        Returns:
            ValidationResult containing cross-reference validation outcome
        """
        result = ValidationResult("cross_references")

        try:
            # Load all configuration files
            configs = {}
            for config_file in self.config_files:
                full_path = PathUtils.join_path(self.base_path, config_file)
                if PathUtils.path_exists(full_path):
                    try:
                        config_data = FileUtils.read_json_file(full_path)
                        configs[config_file] = config_data
                    except Exception as e:
                        result.add_warning(
                            f"Erro ao carregar {config_file} para validação de cross-references: {e}"
                        )

            # Perform basic cross-reference validation
            self._validate_cross_references_basic(configs, result)

            return result

        except Exception as e:
            result.add_error(f"Erro na validação de cross-references: {e}")
            self.logger.error(f"Erro na validação cross-reference: {e}")
            return result

    def _get_cross_reference_rules(self) -> dict[str, Any]:
        """Get cross-reference validation rules.

        Returns:
            Dictionary containing validation rules for cross-references
        """
        return {
            "emulator_platform_consistency": {
                "source_file": "emulator_mapping.json",
                "target_file": "platform_mapping.json",
                "source_key": "emulators",
                "target_key": "mappings",
                "reference_field": "emulator",
            },
            "platform_variant_consistency": {
                "source_file": "platform_mapping.json",
                "target_file": "variant_mapping.json",
                "source_key": "mappings",
                "target_key": "variants",
                "reference_field": "base_platform",
            },
            "frontend_emulator_paths": {
                "source_file": "emulator_mapping.json",
                "target_file": "frontend_config.json",
                "source_key": "emulators",
                "target_key": "emulator_paths",
                "reference_field": "path",
            },
        }

    def _validate_cross_references_basic(
        self, configs: dict[str, dict], result: ValidationResult
    ) -> None:
        """Perform basic cross-reference validation between configurations."""
        # Check if emulator_mapping and platform_mapping exist
        if "emulator_mapping.json" in configs and "platform_mapping.json" in configs:
            emulator_data = configs["emulator_mapping.json"]
            platform_data = configs["platform_mapping.json"]

            # Check emulator-platform consistency
            emulators = emulator_data.get("emulators", {})
            platforms = platform_data

            for emulator_name, emulator_info in emulators.items():
                supported_platforms = emulator_info.get("systems", [])
                for platform in supported_platforms:
                    if platform not in platforms:
                        result.add_warning(
                            f"Emulador '{emulator_name}' suporta plataforma inexistente: '{platform}'"
                        )

            for platform_name, platform_full_name in platforms.items():
                found_emulator = False
                for emulator_info in emulators.values():
                    if platform_name in emulator_info.get("systems", []):
                        found_emulator = True
                        break

                if not found_emulator:
                    result.add_warning(
                        f"Plataforma '{platform_full_name}' ({platform_name}) não tem emulador compatível"
                    )

            if not result.warnings:
                result.add_info("Validação de cross-references básica bem-sucedida")

    def validate_cross_references(self) -> ValidationResult:
        """Validate cross-references between configuration files.

        Checks consistency between emulator mappings, platform mappings,
        variant mappings, and frontend configurations.

        Returns:
            ValidationResult with cross-reference validation issues
        """
        result = ValidationResult("cross_references")

        try:
            # Load all configurations using FileUtils
            configs = {}
            for config_file in self.config_files:
                full_path = PathUtils.join_path(self.base_path, config_file)
                if PathUtils.path_exists(full_path):
                    try:
                        config_data = FileUtils.read_json_file(full_path)
                        configs[config_file] = config_data
                    except Exception as e:
                        result.add_warning(f"Erro ao carregar {config_file}: {e}")
                else:
                    result.add_warning(
                        f"Arquivo ausente para validação cross-reference: {config_file}"
                    )

            if not configs:
                result.add_error(
                    "Nenhuma configuração encontrada para validação cross-reference"
                )
                return result

            # Validate emulator-platform consistency
            if (
                "emulator_mapping.json" in configs
                and "platform_mapping.json" in configs
            ):
                self._validate_emulator_platform_consistency(
                    configs["emulator_mapping.json"],
                    configs["platform_mapping.json"],
                    result,
                )

            # Validate variant-platform consistency
            if "platform_mapping.json" in configs and "variant_mapping.json" in configs:
                self._validate_variant_platform_consistency(
                    configs["platform_mapping.json"],
                    configs["variant_mapping.json"],
                    result,
                )

            # Validate frontend paths against actual mappings
            if all(
                key in configs
                for key in ["frontend_config.json", "emulator_mapping.json"]
            ):
                self._validate_frontend_paths(
                    configs["frontend_config.json"],
                    configs["emulator_mapping.json"],
                    result,
                )

            # Check for duplicate mappings
            self._check_for_duplicates(configs, result)

            # Validate configuration completeness
            self._validate_completeness(configs, result)

            if result.errors:
                result.cross_reference_valid = False
                result.add_error(
                    f"Encontrados {len(result.errors)} problemas de cross-reference"
                )
            else:
                result.add_info("Validação de cross-references bem-sucedida")

            return result

        except Exception as e:
            result.add_error(f"Erro na validação de cross-references: {e}")
            self.logger.error(f"Erro na validação cross-reference: {e}")
            return result

    def _get_model_for_file(self, file_path: str) -> type | None:
        """Get the appropriate Pydantic model for a configuration file.

        Args:
            file_path: Configuration file path

        Returns:
            Corresponding Pydantic model or None if not found
        """
        model_map = {
            "config.json": AppConfig,
            "emulator_mapping.json": EmulatorMapping,
            "platform_mapping.json": PlatformMapping,
            "variant_mapping.json": VariantMapping,
            "frontend_config.json": FrontendGlobalConfig,
            "enterprise_config.json": EnterpriseConfig,
            "frontend_emulator_paths.json": FrontendEmulatorPaths,
            "consolidated_config.json": ConsolidatedConfig,
        }
        return model_map.get(file_path)

    def _get_required_keys(self, file_path: str) -> list[str]:
        """Get required keys for a specific configuration file.

        Args:
            file_path: Configuration file path

        Returns:
            List of required configuration keys
        """
        required_keys_map = {
            "config.json": ["version", "environment", "paths"],
            "emulator_mapping.json": ["emulators"],
            "platform_mapping.json": ["mappings"],
            "variant_mapping.json": ["variants"],
            "frontend_config.json": ["theme", "features"],
            "enterprise_config.json": ["organization", "deployment"],
        }
        return required_keys_map.get(file_path, [])

    def _validate_emulator_platform_consistency(
        self, emulator_config: dict, platform_config: dict, result: ValidationResult
    ) -> None:
        """Validate consistency between emulator and platform configurations.

        Args:
            emulator_config: Emulator mapping configuration
            platform_config: Platform mapping configuration
            result: Validation result to populate
        """
        if "emulators" not in emulator_config:
            result.add_error("Seção 'emulators' ausente na configuração de emuladores")
            return

        emulator_names = set()
        for emu_name, emu_data in emulator_config["emulators"].items():
            emulator_names.add(emu_name)
            # Check if emulator supports required platforms
            supported_platforms = emu_data.get("supported_platforms", [])
            if not supported_platforms:
                result.add_warning(
                    f"Emulador '{emu_name}' sem plataformas suportadas definidas"
                )

        # Check platform references to emulators
        if "mappings" in platform_config:
            for platform_name, platform_data in platform_config["mappings"].items():
                emulator_ref = platform_data.get("emulator")
                if emulator_ref and emulator_ref not in emulator_names:
                    result.add_error(
                        f"Plataforma '{platform_name}' referencia emulador inexistente: '{emulator_ref}'"
                    )

    def _validate_variant_platform_consistency(
        self, platform_config: dict, variant_config: dict, result: ValidationResult
    ) -> None:
        """Validate consistency between platform and variant configurations.

        Args:
            platform_config: Platform mapping configuration
            variant_config: Variant mapping configuration
            result: Validation result to populate
        """
        platform_names = set()

        if "mappings" in platform_config:
            for platform_name in platform_config["mappings"]:
                platform_names.add(platform_name)

        if "variants" not in variant_config:
            result.add_warning("Seção 'variants' ausente na configuração de variantes")
            return

        for variant_name, variant_data in variant_config["variants"].items():
            base_platform = variant_data.get("base_platform")
            if base_platform and base_platform not in platform_names:
                result.add_error(
                    f"Variante '{variant_name}' referencia plataforma base inexistente: '{base_platform}'"
                )

    def _validate_frontend_paths(
        self, frontend_config: dict, emulator_config: dict, result: ValidationResult
    ) -> None:
        """Validate frontend configuration paths against emulator mappings.

        Args:
            frontend_config: Frontend configuration
            emulator_config: Emulator mapping configuration
            result: Validation result to populate
        """
        emulator_paths = set()
        if "emulators" in emulator_config:
            for emu_data in emulator_config["emulators"].values():
                emu_path = emu_data.get("path")
                if emu_path:
                    emulator_paths.add(emu_path)

        # Check frontend emulator paths
        frontend_paths = frontend_config.get("emulator_paths", {})
        for emu_name, path_config in frontend_paths.items():
            configured_path = path_config.get("path")
            if configured_path and configured_path not in emulator_paths:
                result.add_warning(
                    f"Caminho de emulador no frontend '{emu_name}' não corresponde aos mapeamentos: {configured_path}"
                )

    def _check_for_duplicates(
        self, configs: dict[str, dict], result: ValidationResult
    ) -> None:
        """Check for duplicate entries across configuration files.

        Args:
            configs: Loaded configuration files
            result: Validation result to populate
        """
        # Check for duplicate platform names across mappings
        all_platforms = set()
        duplicate_platforms = set()

        platform_files = ["platform_mapping.json", "variant_mapping.json"]
        for file_name in platform_files:
            if file_name in configs:
                config = configs[file_name]
                if "mappings" in config:
                    for platform_name in config["mappings"]:
                        if platform_name in all_platforms:
                            duplicate_platforms.add(platform_name)
                        else:
                            all_platforms.add(platform_name)

        if duplicate_platforms:
            result.add_error(
                f"Plataformas duplicadas encontradas: {', '.join(duplicate_platforms)}"
            )

    def _validate_completeness(
        self, configs: dict[str, dict], result: ValidationResult
    ) -> None:
        """Validate overall configuration completeness.

        Args:
            configs: Loaded configuration files
            result: Validation result to populate
        """
        # Check if core configuration files exist
        core_files = ["config.json", "emulator_mapping.json", "platform_mapping.json"]
        missing_core = [f for f in core_files if f not in configs]

        if missing_core:
            result.add_error(
                f"Arquivos de configuração essenciais ausentes: {', '.join(missing_core)}"
            )

        # Check if configurations have minimum required structure
        for file_name, config in configs.items():
            if not config or not isinstance(config, dict):
                result.add_error(f"Estrutura inválida no arquivo {file_name}")
                continue

            # Check for version field in configs that should have it
            if file_name in [
                "config.json",
                "emulator_mapping.json",
                "platform_mapping.json",
            ]:
                if "version" not in config:
                    result.add_warning(f"Campo 'version' ausente em {file_name}")
