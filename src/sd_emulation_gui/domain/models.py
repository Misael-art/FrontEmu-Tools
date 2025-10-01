"""
Domain models for SD Emulation GUI application.

This module contains Pydantic models that define the structure and validation
rules for all configuration files used in the emulation system.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class BasePaths(BaseModel):
    """Base directory paths for the emulation system."""

    drive_root: str = Field(description="Root drive path (dynamically resolved)")
    emulation_root: str = Field(description="Root emulation directory path")
    roms_root: str = Field(description="Root ROMs directory path")
    emulators_root: str = Field(description="Root emulators directory path")
    storage_media_root: str = Field(description="Downloaded media storage path")
    media_root: str = Field(description="Media assets directory path")
    emulation_roms_root: str = Field(description="Emulation ROMs symbolic links path")
    frontends_root: str = Field(description="Frontends directory path")

    @field_validator("*")
    @classmethod
    def normalize_path(cls, v: str) -> str:
        """Normalize path separators for Windows compatibility."""
        if v:
            return str(Path(v).as_posix())
        return v


class DirectoryNames(BaseModel):
    """Standard directory names used throughout the system."""

    emulators_dir_name: str = Field(default="Emulators")
    frontends_dir_name: str = Field(default="Frontends")
    roms_dir_name: str = Field(default="Roms")
    emulation_dir_name: str = Field(default="Emulation")
    storage_dir_name: str = Field(default="storage")
    downloaded_media_name: str = Field(default="downloaded_media")
    media_dir_name: str = Field(default="media")


class ConfigFiles(BaseModel):
    """Configuration file references."""

    platform_list_file: str = Field(description="Platform name mappings file")
    emulator_mapping_file: str = Field(description="Emulator configurations file")
    variant_mapping_file: str = Field(description="ROM variant mappings file")
    frontend_config_file: str = Field(description="Frontend configurations file")


class SystemSettings(BaseModel):
    """System-wide configuration settings."""

    convert_to_snake_case: bool = Field(default=True)
    require_admin_privileges: bool = Field(default=True)
    enable_dry_run_by_default: bool = Field(default=False)
    log_level: str = Field(
        default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )


class BlockerIssue(BaseModel):
    """Represents a blocking issue that needs resolution."""

    id: int = Field(gt=0, description="Unique identifier for the blocker")
    description: str = Field(
        min_length=1, description="Description of the blocking issue"
    )
    severity: str = Field(pattern=r"^(baixa|média|alta|crítica|resolvida)$")


class ActionPlan(BaseModel):
    """Represents an action item in the project plan."""

    action: str = Field(min_length=1, description="Action description")
    impact: int = Field(ge=1, le=10, description="Impact score (1-10)")
    feasibility: int = Field(ge=1, le=10, description="Feasibility score (1-10)")
    deadline: str = Field(description="Expected completion deadline")


class Metrics(BaseModel):
    """Project quality metrics."""

    code: int = Field(ge=0, le=100, description="Code quality score")
    docs: int = Field(ge=0, le=100, description="Documentation quality score")
    gui: int = Field(default=100, ge=0, le=100, description="GUI quality score")


class Functionalities(BaseModel):
    """System functionality tracking."""

    total: int = Field(ge=0, description="Total number of functionalities")
    implemented: int = Field(ge=0, description="Number of implemented functionalities")
    details: list[str] = Field(
        default_factory=list, description="Detailed functionality descriptions"
    )

    @model_validator(mode="after")
    def validate_implementation_count(self) -> "Functionalities":
        """Ensure implemented count does not exceed total."""
        if self.implemented > self.total:
            raise ValueError("Implemented functionalities cannot exceed total")
        return self


class Diagnostic(BaseModel):
    """System diagnostic information."""

    document_discrepancies: str = Field(description="Documentation inconsistencies")
    ci: str = Field(description="CI/CD status and notes", alias="CI")


class AppConfig(BaseModel):
    """Main application configuration model."""

    base_paths: BasePaths
    directory_names: DirectoryNames = Field(default_factory=DirectoryNames)
    config_files: ConfigFiles
    system_settings: SystemSettings = Field(default_factory=SystemSettings)
    project: str = Field(description="Project name")
    status: str = Field(description="Project status")
    score: int = Field(ge=0, le=100, description="Overall project score")
    metrics: Metrics
    blockers: list[BlockerIssue] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    functionalities: Functionalities
    diagnostic: Diagnostic
    action_plan: list[ActionPlan] = Field(alias="actionPlan", default_factory=list)
    final_observations: str = Field(alias="finalObservations")


class EmulatorPaths(BaseModel):
    """File and directory paths for an emulator."""

    config: str | None = Field(None, description="Configuration file path")
    executable: str | None = Field(None, description="Executable path")
    cores: str | None = Field(None, description="Cores directory (RetroArch)")
    bios: str | None = Field(None, description="BIOS directory path")
    saves: str | None = Field(None, description="Save files directory path")
    roms: str | None = Field(None, description="ROMs directory path")
    shaders: str | None = Field(None, description="Shaders directory path")
    hdpacks: str | None = Field(None, description="HD texture packs path")
    recordings: str | None = Field(None, description="Recordings directory path")
    screenshots: str | None = Field(None, description="Screenshots directory path")
    storage: str | None = Field(None, description="Storage directory path")
    downloaded_media: str | None = Field(None, description="Downloaded media path")

    @field_validator("*")
    @classmethod
    def normalize_emulator_path(cls, v: str | None) -> str | None:
        """Normalize emulator paths for consistency."""
        if v:
            return str(Path(v).as_posix())
        return v


class EmulatorConfig(BaseModel):
    """Configuration for a single emulator."""

    systems: list[str] = Field(description="Supported system identifiers")
    paths: EmulatorPaths = Field(description="File and directory paths")
    components: list[str] = Field(
        default_factory=list, description="Emulator components"
    )

    @field_validator("systems")
    @classmethod
    def validate_systems_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure systems list is not empty."""
        if not v:
            raise ValueError("Emulator must support at least one system")
        return v


class FrontendPaths(BaseModel):
    """Paths configuration for a frontend."""

    roms: str | None = Field(None, description="ROMs directory path")
    emulators: str | None = Field(None, description="Emulators directory path")
    media: str | None = Field(None, description="Media assets directory path")
    screenshots: str | None = Field(None, description="Screenshots directory path")
    saves: str | None = Field(None, description="Save files directory path")
    bios: str | None = Field(None, description="BIOS directory path")
    emulator_path: str | None = Field(None, description="Emulator executable path")
    rom_path: str | None = Field(None, description="ROM files path")

    @field_validator("*")
    @classmethod
    def normalize_frontend_path(cls, v: str | None) -> str | None:
        """Normalize frontend paths for consistency."""
        if v:
            return str(Path(v).as_posix())
        return v


class FrontendConfig(BaseModel):
    """Configuration for a frontend application."""

    config: str | None = Field(None, description="Configuration file path")
    paths: FrontendPaths | None = Field(None, description="Directory paths")


class EmulatorMapping(BaseModel):
    """Complete emulator and frontend mapping configuration."""

    emulators: dict[str, EmulatorConfig] = Field(description="Emulator configurations")
    frontends: dict[str, FrontendConfig] = Field(description="Frontend configurations")

    @field_validator("emulators")
    @classmethod
    def validate_emulators_not_empty(
        cls, v: dict[str, EmulatorConfig]
    ) -> dict[str, EmulatorConfig]:
        """Ensure at least one emulator is configured."""
        if not v:
            raise ValueError("At least one emulator must be configured")
        return v


class PlatformMapping(BaseModel):
    """Mapping of short platform names to full display names."""

    mappings: dict[str, str] = Field(description="Platform name mappings")

    def __init__(self, **data: Any):
        """Initialize platform mapping from flat dictionary or nested format."""
        # Handle different input formats
        if "mappings" not in data and data:
            # Handle flat dictionary input (e.g., {"nintendo_ds": "Nintendo DS", ...})
            super().__init__(mappings=data)
        elif data and isinstance(list(data.keys())[0], str) and all(isinstance(v, str) for v in data.values()):
            # Already in correct format
            super().__init__(mappings=data)
        else:
            # Use provided data as-is
            super().__init__(**data)

    def get_full_name(self, short_name: str) -> str | None:
        """Get full platform name from short name."""
        return self.mappings.get(short_name)

    def get_short_name(self, full_name: str) -> str | None:
        """Get short platform name from full name."""
        for short, full in self.mappings.items():
            if full == full_name:
                return short
        return None


class VariantMapping(BaseModel):
    """ROM variant mappings for different platforms."""

    variants: dict[str, dict[str, str]] = Field(description="Platform variant mappings")

    def __init__(self, **data: Any):
        """Initialize variant mapping from nested dictionary."""
        if "variants" not in data and data:
            # Handle direct platform dictionary input
            super().__init__(variants=data)
        else:
            super().__init__(**data)

    def get_variant_name(self, platform: str, variant_key: str) -> str | None:
        """Get variant display name for a platform."""
        return self.variants.get(platform, {}).get(variant_key)


class GlobalPaths(BaseModel):
    """Global path configurations for frontends."""

    roms_base_path: str = Field(description="Base path for ROM files")
    media_base_path: str = Field(description="Base path for media assets")
    frontend_base_path: str = Field(description="Base path for frontend installations")
    mapping_files: dict[str, str] = Field(description="Configuration file mappings")

    @field_validator("roms_base_path", "media_base_path", "frontend_base_path")
    @classmethod
    def normalize_global_path(cls, v: str) -> str:
        """Normalize global paths for consistency."""
        return str(Path(v).as_posix())


class FrontendGlobalConfig(BaseModel):
    """Global frontend configuration."""

    emulationstation_de: dict[str, str] | None = Field(
        None, alias="EmulationStation-DE"
    )
    retroarch: dict[str, str] | None = Field(None, alias="RetroArch")
    global_paths: GlobalPaths


class FrontendEmulatorPath(BaseModel):
    """Frontend-specific emulator path configuration."""

    path_suffix: str = Field(description="Path suffix for this frontend")
    link_name_pattern: str = Field(description="Pattern for symbolic link names")


class FrontendEmulatorPaths(BaseModel):
    """Complete frontend emulator paths configuration."""

    paths: dict[str, FrontendEmulatorPath] = Field(
        description="Frontend path configurations"
    )

    def __init__(self, **data: Any):
        """Initialize from flat dictionary structure."""
        if "paths" not in data and data:
            # Convert flat structure to nested
            paths = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    paths[key] = FrontendEmulatorPath(**value)
            super().__init__(paths=paths)
        else:
            super().__init__(**data)


class SystemRequirements(BaseModel):
    """System requirements configuration."""

    minimum_windows_version: str = Field(description="Minimum Windows version")
    minimum_powershell_version: int = Field(
        ge=1, description="Minimum PowerShell version"
    )
    minimum_free_space_gb: int = Field(ge=0, description="Minimum free space in GB")
    required_powershell_scripts: list[str] = Field(
        description="Required PowerShell scripts"
    )


class LoggingConfig(BaseModel):
    """Logging system configuration."""

    enabled: bool = Field(default=True)
    level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    max_log_files: int = Field(default=10, ge=1)
    max_report_files: int = Field(default=5, ge=1)
    max_days_retention: int = Field(default=7, ge=1)
    auto_rotation: bool = Field(default=True)
    log_format: str = Field(default="[%timestamp%] [%level%] %message%")


class BackupConfig(BaseModel):
    """Backup system configuration."""

    enabled: bool = Field(default=True)
    auto_backup_before_operations: bool = Field(default=True)
    max_backup_files: int = Field(default=5, ge=1)
    compression_enabled: bool = Field(default=True)
    backup_critical_files: list[str] = Field(default_factory=list)


class OperationsConfig(BaseModel):
    """Operations configuration settings."""

    timeout_seconds: int = Field(default=300, ge=1)
    retry_attempts: int = Field(default=3, ge=1)
    retry_delay_seconds: int = Field(default=5, ge=1)
    enable_rollback: bool = Field(default=True)
    require_confirmation_for_critical: bool = Field(default=True)


class MonitoringConfig(BaseModel):
    """System monitoring configuration."""

    enabled: bool = Field(default=True)
    check_interval_minutes: int = Field(default=30, ge=1)
    alert_on_errors: bool = Field(default=True)
    performance_tracking: bool = Field(default=True)
    disk_space_warning_threshold_gb: int = Field(default=10, ge=1)


class SecurityConfig(BaseModel):
    """Security configuration settings."""

    execution_policy: str = Field(default="Bypass")
    validate_script_integrity: bool = Field(default=True)
    require_admin_privileges: bool = Field(default=False)
    log_security_events: bool = Field(default=True)


class UIConfig(BaseModel):
    """User interface configuration."""

    show_enterprise_header: bool = Field(default=True)
    use_colors: bool = Field(default=True)
    show_progress_indicators: bool = Field(default=True)
    auto_pause_after_operations: bool = Field(default=True)
    menu_timeout_seconds: int = Field(default=0, ge=0)


class AdvancedConfig(BaseModel):
    """Advanced system configuration options."""

    enable_experimental_features: bool = Field(default=False)
    parallel_operations: bool = Field(default=False)
    cache_validation_results: bool = Field(default=True)
    optimize_for_ssd: bool = Field(default=True)
    enable_telemetry: bool = Field(default=False)


class StatusCodes(BaseModel):
    """System status code definitions."""

    success: int = Field(default=0)
    warning: int = Field(default=1)
    error: int = Field(default=2)
    critical: int = Field(default=3)


class FilePatterns(BaseModel):
    """File pattern definitions for log rotation and cleanup."""

    log_rotation: dict[str, str] = Field(description="Log rotation patterns")


class Metadata(BaseModel):
    """Configuration metadata."""

    name: str | None = Field(None, description="Configuration name")
    version: str | None = Field(None, description="Configuration version")
    environment: str | None = Field(None, description="Environment type")
    status: str | None = Field(None, description="Configuration status")
    score: int | None = Field(None, ge=0, le=100, description="Quality score")
    created_date: str | None = Field(None, description="Creation date")
    last_modified: str | None = Field(None, description="Last modification date")
    config_version: str | None = Field(None, description="Configuration version")
    author: str | None = Field(None, description="Configuration author")
    description: str | None = Field(None, description="Configuration description")
    documentation_url: str | None = Field(None, description="Documentation URL")


class ConsolidatedConfig(BaseModel):
    """Complete consolidated configuration model."""

    metadata: Metadata | None = Field(None, description="Configuration metadata")
    paths: dict[str, Any] | None = Field(None, description="Path configurations")
    system: dict[str, Any] | None = Field(None, description="System configurations")
    config_files: ConfigFiles | None = Field(
        None, description="Configuration file references"
    )
    logging: LoggingConfig | None = Field(None, description="Logging configuration")
    backup: BackupConfig | None = Field(None, description="Backup configuration")
    operations: OperationsConfig | None = Field(
        None, description="Operations configuration"
    )
    monitoring: MonitoringConfig | None = Field(
        None, description="Monitoring configuration"
    )
    ui: UIConfig | None = Field(None, description="UI configuration")
    advanced: AdvancedConfig | None = Field(None, description="Advanced configuration")
    status_codes: StatusCodes | None = Field(
        None, description="Status code definitions"
    )
    file_patterns: FilePatterns | None = Field(
        None, description="File pattern definitions"
    )
    metrics: Metrics | None = Field(None, description="Quality metrics")
    blockers: list[BlockerIssue] | None = Field(None, description="Blocking issues")
    opportunities: list[str] | None = Field(
        None, description="Improvement opportunities"
    )
    functionalities: Functionalities | None = Field(
        None, description="Functionality tracking"
    )
    diagnostic: Diagnostic | None = Field(None, description="Diagnostic information")
    action_plan: list[ActionPlan] | None = Field(None, description="Action plan items")
    final_observations: str | None = Field(None, description="Final observations")


class EnterpriseConfig(BaseModel):
    """Enterprise-specific configuration model."""

    system: dict[str, Any] = Field(description="System information")
    requirements: SystemRequirements = Field(description="System requirements")
    directories: dict[str, str] = Field(description="Directory configurations")
    logging: LoggingConfig = Field(description="Logging configuration")
    backup: BackupConfig = Field(description="Backup configuration")
    operations: OperationsConfig = Field(description="Operations configuration")
    monitoring: MonitoringConfig = Field(description="Monitoring configuration")
    security: SecurityConfig = Field(description="Security configuration")
    ui: UIConfig = Field(description="UI configuration")
    advanced: AdvancedConfig = Field(description="Advanced configuration")
    status_codes: StatusCodes = Field(description="Status code definitions")
    file_patterns: FilePatterns = Field(description="File pattern definitions")
    metadata: Metadata = Field(description="Configuration metadata")