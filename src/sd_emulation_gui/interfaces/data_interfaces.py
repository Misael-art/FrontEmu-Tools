"""Data Interfaces

Defines clear data interfaces and contracts between modules
using TypedDict for type safety and consistency.
"""

from typing import Any, Literal, TypedDict

# Core Data Types


class BaseEntity(TypedDict):
    """Base entity interface with common fields."""

    id: str
    created_at: str
    updated_at: str
    version: str


class PathData(TypedDict):
    """Path data interface."""

    path: str
    normalized_path: str
    is_absolute: bool
    exists: bool
    is_directory: bool
    is_file: bool
    is_symlink: bool
    parent_directory: str
    filename: str
    extension: str


class FileMetadata(TypedDict):
    """File metadata interface."""

    path: str
    size_bytes: int
    created_time: str
    modified_time: str
    accessed_time: str
    permissions: str
    owner: str
    mime_type: str | None
    checksum_md5: str | None
    checksum_sha256: str | None


class DirectoryData(TypedDict):
    """Directory data interface."""

    path: str
    total_files: int
    total_directories: int
    total_size_bytes: int
    file_list: list[str]
    directory_list: list[str]
    last_scan_time: str


# Migration Data Interfaces


class MigrationStepData(TypedDict):
    """Migration step data interface."""

    step_id: str
    step_type: Literal[
        "create_directory", "create_symlink", "move_file", "copy_file", "delete_file"
    ]
    source_path: str
    target_path: str
    parameters: dict[str, Any]
    dependencies: list[str]
    rollback_data: dict[str, Any] | None
    execution_order: int
    estimated_duration_seconds: int


class MigrationPlanData(TypedDict):
    """Migration plan data interface."""

    plan_id: str
    name: str
    description: str
    source_root: str
    target_root: str
    steps: list[MigrationStepData]
    total_steps: int
    estimated_total_duration: int
    requires_admin_privileges: bool
    backup_required: bool
    dry_run_completed: bool
    validation_passed: bool
    created_by: str
    created_at: str


class MigrationExecutionData(TypedDict):
    """Migration execution data interface."""

    execution_id: str
    plan_id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    current_step: int
    total_steps: int
    progress_percent: float
    started_at: str
    completed_at: str | None
    error_message: str | None
    rollback_available: bool
    execution_log: list[str]


# Variant Data Interfaces


class VariantData(TypedDict):
    """Variant data interface."""

    platform: str
    variant_name: str
    full_name: str
    source_directory: str
    target_symlink: str
    variant_type: Literal["region", "version", "language", "special"]
    priority: int
    file_count: int
    total_size_bytes: int
    indicators: list[str]
    metadata: dict[str, Any]


class PlatformData(TypedDict):
    """Platform data interface."""

    platform_id: str
    short_name: str
    full_name: str
    supported_extensions: list[str]
    emulator_paths: list[str]
    rom_directories: list[str]
    media_directories: list[str]
    system_files: list[str]
    variant_patterns: list[str]
    symlink_required: bool


class MediaData(TypedDict):
    """Media data interface."""

    media_type: Literal["artwork", "screenshot", "video", "manual", "music"]
    source_path: str
    target_path: str
    platform: str
    game_name: str
    file_format: str
    resolution: str | None
    size_bytes: int


# Compliance Data Interfaces


class RuleData(TypedDict):
    """Rule data interface."""

    rule_id: str
    rule_type: str
    name: str
    description: str
    severity: Literal["info", "warning", "error", "critical"]
    enabled: bool
    parameters: dict[str, Any]
    validation_function: str


class ComplianceCheckData(TypedDict):
    """Compliance check data interface."""

    check_id: str
    rule_id: str
    target_path: str
    status: Literal["compliant", "warning", "non_compliant", "error"]
    message: str
    details: str | None
    affected_paths: list[str]
    suggested_actions: list[str]
    check_timestamp: str
    execution_time_ms: int


class ComplianceReportData(TypedDict):
    """Compliance report data interface."""

    report_id: str
    target_path: str
    rules_version: str
    scan_timestamp: str
    total_checks: int
    compliant_count: int
    warning_count: int
    non_compliant_count: int
    error_count: int
    checks: list[ComplianceCheckData]
    summary_by_category: dict[str, int]
    overall_score: float
    recommendations: list[str]


# Configuration Data Interfaces


class PathConfigData(TypedDict):
    """Path configuration data interface."""

    config_name: str
    base_drive: str
    emulation_root: str
    emulators_root: str
    roms_root: str
    frontends_root: str
    tools_root: str
    backup_directory: str
    temp_directory: str
    config_directory: str
    custom_paths: dict[str, str]


class ServiceConfigData(TypedDict):
    """Service configuration data interface."""

    service_name: str
    version: str
    enabled: bool
    auto_start: bool
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    max_parallel_operations: int
    timeout_seconds: int
    retry_attempts: int
    settings: dict[str, Any]


class GlobalConfigData(TypedDict):
    """Global configuration data interface."""

    application_version: str
    config_version: str
    path_config: PathConfigData
    service_configs: dict[str, ServiceConfigData]
    logging_config: dict[str, Any]
    performance_settings: dict[str, Any]
    feature_flags: dict[str, bool]
    user_preferences: dict[str, Any]


# Operation Data Interfaces


class OperationData(TypedDict):
    """Operation data interface."""

    operation_id: str
    operation_type: str
    service_name: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    progress_percent: float
    started_at: str
    completed_at: str | None
    parameters: dict[str, Any]
    result_data: dict[str, Any] | None
    error_message: str | None
    warnings: list[str]


class BatchOperationData(TypedDict):
    """Batch operation data interface."""

    batch_id: str
    name: str
    description: str
    operations: list[OperationData]
    total_operations: int
    completed_operations: int
    failed_operations: int
    overall_status: str
    started_at: str
    estimated_completion: str | None
    can_rollback: bool


# Backup Data Interfaces


class BackupData(TypedDict):
    """Backup data interface."""

    backup_id: str
    name: str
    description: str
    source_paths: list[str]
    backup_path: str
    backup_type: Literal["full", "incremental", "differential"]
    compression_type: Literal["zip", "7z", "tar.gz"] | None
    created_at: str
    size_bytes: int
    file_count: int
    checksum: str
    retention_days: int
    tags: list[str]


class RestorePointData(TypedDict):
    """Restore point data interface."""

    restore_point_id: str
    name: str
    description: str
    created_at: str
    operation_id: str
    affected_paths: list[str]
    backup_data: BackupData
    can_restore: bool
    restore_instructions: list[str]


# Event Data Interfaces


class EventData(TypedDict):
    """Event data interface."""

    event_id: str
    event_type: str
    source_service: str
    target_service: str | None
    timestamp: str
    priority: Literal["low", "normal", "high", "critical"]
    data: dict[str, Any]
    correlation_id: str | None
    user_id: str | None


class LogEntryData(TypedDict):
    """Log entry data interface."""

    log_id: str
    timestamp: str
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    service_name: str
    operation_id: str | None
    message: str
    details: dict[str, Any] | None
    exception_info: str | None
    user_id: str | None


# Validation Data Interfaces


class ValidationRuleData(TypedDict):
    """Validation rule data interface."""

    rule_id: str
    name: str
    description: str
    rule_type: Literal["path", "file", "directory", "symlink", "permission", "space"]
    validation_function: str
    parameters: dict[str, Any]
    error_message_template: str
    severity: Literal["info", "warning", "error", "critical"]


class ValidationResultData(TypedDict):
    """Validation result data interface."""

    validation_id: str
    rule_id: str
    target_path: str
    is_valid: bool
    severity: str
    message: str
    details: dict[str, Any] | None
    suggested_fix: str | None
    validation_timestamp: str


# Statistics Data Interfaces


class PerformanceMetrics(TypedDict):
    """Performance metrics interface."""

    operation_type: str
    execution_time_ms: int
    memory_usage_mb: float
    cpu_usage_percent: float
    disk_io_bytes: int
    network_io_bytes: int
    timestamp: str


class UsageStatistics(TypedDict):
    """Usage statistics interface."""

    feature_name: str
    usage_count: int
    last_used: str
    average_execution_time: float
    success_rate: float
    error_count: int
    user_rating: float | None
