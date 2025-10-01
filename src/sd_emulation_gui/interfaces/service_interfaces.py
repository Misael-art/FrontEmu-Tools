"""Service Interfaces

Defines clear interfaces between modules using TypedDict protocols
to improve communication and reduce coupling between services.
"""

from enum import Enum
from typing import Any, TypedDict


class OperationStatus(Enum):
    """Status of operations across services."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OperationResult(TypedDict):
    """Standard operation result interface."""

    success: bool
    message: str
    data: dict[str, Any] | None
    errors: list[str]
    warnings: list[str]


class PathInfo(TypedDict):
    """Path information interface."""

    path: str
    exists: bool
    is_directory: bool
    is_symlink: bool
    size_bytes: int | None
    modified_time: str | None


class MigrationStepInfo(TypedDict):
    """Migration step information interface."""

    step_id: str
    operation_type: str
    source_path: str
    target_path: str
    status: str
    rollback_info: dict[str, Any] | None
    error_message: str | None


class MigrationPlanInfo(TypedDict):
    """Migration plan interface."""

    plan_id: str
    description: str
    steps: list[MigrationStepInfo]
    estimated_duration: int
    requires_backup: bool
    dry_run_completed: bool


class VariantInfo(TypedDict):
    """Variant information interface."""

    platform: str
    variant_name: str
    source_path: str
    target_path: str
    symlink_type: str
    is_media_variant: bool


class VariantPlanInfo(TypedDict):
    """Variant plan interface."""

    platform: str
    variants: list[VariantInfo]
    media_symlinks: list[dict[str, str]]
    total_operations: int


class ComplianceCheckInfo(TypedDict):
    """Compliance check result interface."""

    rule_name: str
    level: str
    message: str
    affected_paths: list[str]
    suggested_action: str | None


class ComplianceReportInfo(TypedDict):
    """Compliance report interface."""

    timestamp: str
    rules_version: str
    total_checks: int
    compliant_checks: int
    warning_checks: int
    non_compliant_checks: int
    checks: list[ComplianceCheckInfo]
    summary: dict[str, int]
    recommendations: list[str]


class ServiceConfigInfo(TypedDict):
    """Service configuration interface."""

    service_name: str
    version: str
    enabled: bool
    config_path: str
    dependencies: list[str]
    settings: dict[str, Any]


class FileOperationInfo(TypedDict):
    """File operation interface."""

    operation_id: str
    operation_type: str  # copy, move, delete, create_symlink
    source_path: str
    target_path: str | None
    status: str
    progress_percent: int
    bytes_processed: int
    total_bytes: int
    error_message: str | None


class BackupInfo(TypedDict):
    """Backup information interface."""

    backup_id: str
    source_paths: list[str]
    backup_path: str
    timestamp: str
    compression_enabled: bool
    size_bytes: int
    status: str


class SystemInfo(TypedDict):
    """System information interface."""

    platform: str
    architecture: str
    free_space_bytes: int
    total_space_bytes: int
    memory_available_mb: int
    cpu_cores: int


class ValidationResult(TypedDict):
    """Validation result interface."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    suggestions: list[str]


class ProgressInfo(TypedDict):
    """Progress tracking interface."""

    current_step: int
    total_steps: int
    current_operation: str
    progress_percent: int
    estimated_time_remaining: int | None
    status: str


# Service Interface Protocols


class IMigrationService(TypedDict):
    """Migration service interface."""

    def plan_migration(
        self, source_path: str, target_path: str
    ) -> MigrationPlanInfo: ...
    def execute_migration(self, plan: MigrationPlanInfo) -> OperationResult: ...
    def rollback_migration(self, plan: MigrationPlanInfo) -> OperationResult: ...
    def get_migration_status(self, plan_id: str) -> ProgressInfo: ...


class IVariantService(TypedDict):
    """Variant service interface."""

    def analyze_variants(self, platform: str, roms_path: str) -> list[VariantInfo]: ...
    def plan_variant_symlinks(self, platform: str) -> VariantPlanInfo: ...
    def execute_variant_plan(self, plan: VariantPlanInfo) -> OperationResult: ...
    def get_variant_status(self, platform: str) -> ProgressInfo: ...


class ISDEmulationService(TypedDict):
    """SD Emulation service interface."""

    def check_compliance(self, target_path: str) -> ComplianceReportInfo: ...
    def parse_rules_from_document(self, document_path: str) -> dict[str, Any]: ...
    def get_rules(self) -> dict[str, Any]: ...


class IPathService(TypedDict):
    """Path service interface."""

    def normalize_path(self, path: str) -> str: ...
    def join_paths(self, *paths: str) -> str: ...
    def get_path_info(self, path: str) -> PathInfo: ...
    def validate_path(self, path: str) -> ValidationResult: ...


class IFileService(TypedDict):
    """File service interface."""

    def copy_file(self, source: str, target: str) -> OperationResult: ...
    def move_file(self, source: str, target: str) -> OperationResult: ...
    def delete_file(self, path: str) -> OperationResult: ...
    def create_symlink(self, source: str, target: str) -> OperationResult: ...
    def get_file_info(self, path: str) -> PathInfo: ...


class IBackupService(TypedDict):
    """Backup service interface."""

    def create_backup(self, paths: list[str], backup_path: str) -> BackupInfo: ...
    def restore_backup(self, backup_id: str) -> OperationResult: ...
    def list_backups(self) -> list[BackupInfo]: ...
    def delete_backup(self, backup_id: str) -> OperationResult: ...


class ISystemService(TypedDict):
    """System service interface."""

    def get_system_info(self) -> SystemInfo: ...
    def check_permissions(self, path: str) -> ValidationResult: ...
    def get_free_space(self, path: str) -> int: ...


# Event interfaces for inter-service communication


class ServiceEvent(TypedDict):
    """Service event interface."""

    event_id: str
    event_type: str
    source_service: str
    timestamp: str
    data: dict[str, Any]
    priority: str


class EventHandler(TypedDict):
    """Event handler interface."""

    def handle_event(self, event: ServiceEvent) -> OperationResult: ...
    def subscribe_to_events(self, event_types: list[str]) -> bool: ...
    def unsubscribe_from_events(self, event_types: list[str]) -> bool: ...


# Configuration interfaces


class ServiceConfiguration(TypedDict):
    """Service configuration interface."""

    service_configs: dict[str, ServiceConfigInfo]
    global_settings: dict[str, Any]
    logging_config: dict[str, Any]
    performance_settings: dict[str, Any]


class ConfigurationManager(TypedDict):
    """Configuration manager interface."""

    def load_configuration(self, config_path: str) -> ServiceConfiguration: ...
    def save_configuration(
        self, config: ServiceConfiguration, config_path: str
    ) -> OperationResult: ...
    def validate_configuration(
        self, config: ServiceConfiguration
    ) -> ValidationResult: ...
    def get_service_config(self, service_name: str) -> ServiceConfigInfo: ...