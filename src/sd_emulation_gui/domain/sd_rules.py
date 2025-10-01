"""
SD Emulation Rules domain models.

This module contains domain models that represent the business rules and 
compliance requirements extracted from the SD emulation architecture document.
"""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class LinkType(Enum):
    """Types of symbolic links supported."""

    SYMBOLIC_LINK = "symbolic_link"
    JUNCTION = "junction"
    HARD_LINK = "hard_link"


class ComplianceLevel(Enum):
    """Compliance levels for SD emulation rules."""

    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


class DirectoryStructureRule(BaseModel):
    """Rules for directory structure organization."""

    path: str = Field(description="Directory path pattern")
    purpose: str = Field(description="Purpose of this directory")
    required: bool = Field(
        default=True, description="Whether this directory is required"
    )
    relative_to: str | None = Field(None, description="Base path this is relative to")
    allowed_extensions: list[str] = Field(
        default_factory=list, description="Allowed file extensions"
    )
    system_files: list[str] = Field(
        default_factory=list, description="System files to preserve"
    )

    @field_validator("path")
    @classmethod
    def normalize_directory_path(cls, v: str) -> str:
        """Normalize directory path for consistency."""
        return str(Path(v).as_posix())


class SymlinkRule(BaseModel):
    """Rules for symbolic link creation and management."""

    source_pattern: str = Field(description="Source path pattern")
    target_pattern: str = Field(description="Target path pattern")
    link_type: LinkType = Field(default=LinkType.SYMBOLIC_LINK)
    relative: bool = Field(default=True, description="Whether links should be relative")
    required: bool = Field(default=True, description="Whether this symlink is required")
    description: str = Field(description="Description of the symlink purpose")

    @field_validator("source_pattern", "target_pattern")
    @classmethod
    def normalize_symlink_paths(cls, v: str) -> str:
        """Normalize symlink paths for consistency."""
        return str(Path(v).as_posix())


class DeduplicationRule(BaseModel):
    """Rules for file and directory deduplication."""

    target_directories: list[str] = Field(description="Directories to deduplicate")
    file_patterns: list[str] = Field(description="File patterns to deduplicate")
    hash_based: bool = Field(default=True, description="Use hash-based deduplication")
    preserve_newest: bool = Field(default=True, description="Preserve newest files")
    backup_duplicates: bool = Field(
        default=True, description="Backup duplicates before removal"
    )
    min_file_size_mb: int = Field(
        default=1, ge=0, description="Minimum file size to deduplicate (MB)"
    )


class PathValidationRule(BaseModel):
    """Rules for path validation and restrictions."""

    forbidden_patterns: list[str] = Field(description="Forbidden path patterns")
    required_patterns: list[str] = Field(description="Required path patterns")
    max_path_length: int = Field(default=260, ge=1, description="Maximum path length")
    max_filename_length: int = Field(
        default=255, ge=1, description="Maximum filename length"
    )
    case_sensitive: bool = Field(
        default=False, description="Whether paths are case sensitive"
    )


class BackupRule(BaseModel):
    """Rules for backup operations."""

    target_patterns: list[str] = Field(description="Patterns for files/dirs to backup")
    backup_location: str = Field(description="Backup directory pattern")
    timestamp_format: str = Field(
        default="%Y%m%d_%H%M%S", description="Timestamp format"
    )
    compression_enabled: bool = Field(
        default=True, description="Enable backup compression"
    )
    retention_days: int = Field(
        default=30, ge=1, description="Backup retention in days"
    )
    max_backup_size_gb: int = Field(
        default=50, ge=1, description="Maximum backup size (GB)"
    )


class PortabilityRule(BaseModel):
    """Rules for ensuring portability across systems."""

    require_relative_paths: bool = Field(
        default=True, description="Require relative paths"
    )
    forbidden_absolute_patterns: list[str] = Field(
        default_factory=lambda: ["%APPDATA%", "%USERPROFILE%"],
        description="Forbidden absolute path patterns",
    )
    allowed_drive_patterns: list[str] = Field(
        default_factory=lambda: [None],  # Dynamically resolved
        description="Allowed drive patterns",
    )
    validate_symlink_targets: bool = Field(
        default=True, description="Validate symlink targets exist"
    )


class PlatformRule(BaseModel):
    """Rules for platform-specific configurations."""

    short_name: str = Field(description="Platform short name")
    full_name: str = Field(description="Platform full display name")
    supported_extensions: list[str] = Field(description="Supported ROM file extensions")
    system_files: list[str] = Field(
        default_factory=lambda: ["systeminfo.txt", "metadata.txt", "gamelist.xml"],
        description="Platform system files to preserve",
    )
    emulators: list[str] = Field(
        default_factory=list, description="Supported emulators"
    )
    symlink_required: bool = Field(
        default=True, description="Whether symlink is required"
    )


class StorageRule(BaseModel):
    """Rules for storage management and space optimization."""

    minimum_free_space_gb: int = Field(
        default=20, ge=1, description="Minimum free space (GB)"
    )
    warning_threshold_gb: int = Field(
        default=10, ge=1, description="Warning threshold (GB)"
    )
    critical_threshold_gb: int = Field(
        default=5, ge=1, description="Critical threshold (GB)"
    )
    enable_deduplication: bool = Field(
        default=True, description="Enable automatic deduplication"
    )
    compress_backups: bool = Field(default=True, description="Compress backup files")
    cleanup_temp_files: bool = Field(
        default=True, description="Clean up temporary files"
    )


class OperationRule(BaseModel):
    """Rules for operation execution and safety."""

    require_dry_run_first: bool = Field(
        default=True, description="Require dry run before execution"
    )
    require_confirmation: bool = Field(
        default=True, description="Require user confirmation"
    )
    enable_rollback: bool = Field(default=True, description="Enable operation rollback")
    max_parallel_operations: int = Field(
        default=4, ge=1, le=16, description="Maximum parallel operations"
    )
    operation_timeout_seconds: int = Field(
        default=300, ge=30, description="Operation timeout"
    )
    log_all_operations: bool = Field(default=True, description="Log all operations")


class ComplianceCheck(BaseModel):
    """Individual compliance check result."""

    rule_name: str = Field(description="Name of the compliance rule")
    level: ComplianceLevel = Field(description="Compliance level")
    message: str = Field(description="Compliance check message")
    details: str | None = Field(None, description="Additional details")
    suggested_action: str | None = Field(
        None, description="Suggested remediation action"
    )
    affected_paths: list[str] = Field(
        default_factory=list, description="Affected file/directory paths"
    )


class SDEmulationRules(BaseModel):
    """Complete set of SD emulation rules and compliance requirements."""

    version: str = Field(default="1.0.0", description="Rules version")
    description: str = Field(description="Rules description")

    # Core structural rules
    directory_structure: list[DirectoryStructureRule] = Field(
        description="Directory structure rules"
    )
    symlink_rules: list[SymlinkRule] = Field(description="Symbolic link rules")
    platform_rules: list[PlatformRule] = Field(description="Platform-specific rules")

    # Operation and safety rules
    deduplication_rules: list[DeduplicationRule] = Field(
        description="Deduplication rules"
    )
    path_validation: PathValidationRule = Field(description="Path validation rules")
    backup_rules: list[BackupRule] = Field(description="Backup operation rules")
    portability_rules: PortabilityRule = Field(description="Portability requirements")
    storage_rules: StorageRule = Field(description="Storage management rules")
    operation_rules: OperationRule = Field(description="Operation execution rules")

    def get_platform_rule(self, platform_short_name: str) -> PlatformRule | None:
        """Get platform rule by short name."""
        for rule in self.platform_rules:
            if rule.short_name == platform_short_name:
                return rule
        return None

    def get_required_directories(self) -> list[DirectoryStructureRule]:
        """Get all required directory rules."""
        return [rule for rule in self.directory_structure if rule.required]

    def get_required_symlinks(self) -> list[SymlinkRule]:
        """Get all required symlink rules."""
        return [rule for rule in self.symlink_rules if rule.required]

    def validate_path_compliance(self, path: str) -> list[ComplianceCheck]:
        """Validate path against all applicable rules."""
        checks = []

        # Check forbidden patterns
        for pattern in self.path_validation.forbidden_patterns:
            if pattern.lower() in path.lower():
                checks.append(
                    ComplianceCheck(
                        rule_name="forbidden_path_pattern",
                        level=ComplianceLevel.NON_COMPLIANT,
                        message=f"Path contains forbidden pattern: {pattern}",
                        affected_paths=[path],
                        suggested_action=f"Remove or replace forbidden pattern: {pattern}",
                    )
                )

        # Check portability rules
        if self.portability_rules.require_relative_paths:
            for forbidden in self.portability_rules.forbidden_absolute_patterns:
                if path.startswith(forbidden):
                    checks.append(
                        ComplianceCheck(
                            rule_name="absolute_path_forbidden",
                            level=ComplianceLevel.NON_COMPLIANT,
                            message=f"Absolute path not allowed: {forbidden}",
                            affected_paths=[path],
                            suggested_action="Convert to relative path",
                        )
                    )

        # Check path length limits
        if len(path) > self.path_validation.max_path_length:
            checks.append(
                ComplianceCheck(
                    rule_name="path_too_long",
                    level=ComplianceLevel.NON_COMPLIANT,
                    message=f"Path exceeds maximum length ({self.path_validation.max_path_length})",
                    affected_paths=[path],
                    suggested_action="Shorten path or use shorter directory names",
                )
            )

        return checks

    def get_all_compliance_rules(self) -> list[str]:
        """Get list of all compliance rule names."""
        return [
            "directory_structure",
            "symlink_compliance",
            "platform_configuration",
            "deduplication_efficiency",
            "path_validation",
            "backup_integrity",
            "portability_requirements",
            "storage_optimization",
            "operation_safety",
        ]


class ComplianceReport(BaseModel):
    """Complete compliance assessment report."""

    timestamp: str = Field(description="Report generation timestamp")
    rules_version: str = Field(description="Rules version used for assessment")
    total_checks: int = Field(ge=0, description="Total number of checks performed")
    compliant_checks: int = Field(ge=0, description="Number of compliant checks")
    warning_checks: int = Field(ge=0, description="Number of warning checks")
    non_compliant_checks: int = Field(
        ge=0, description="Number of non-compliant checks"
    )

    checks: list[ComplianceCheck] = Field(
        description="Individual compliance check results"
    )
    summary: dict[str, int] = Field(description="Summary statistics by rule category")
    recommendations: list[str] = Field(description="High-level recommendations")

    @property
    def compliance_percentage(self) -> float:
        """Calculate overall compliance percentage."""
        if self.total_checks == 0:
            return 0.0
        return (self.compliant_checks / self.total_checks) * 100.0

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical compliance issues."""
        return self.non_compliant_checks > 0

    def get_checks_by_level(self, level: ComplianceLevel) -> list[ComplianceCheck]:
        """Get compliance checks filtered by level."""
        return [check for check in self.checks if check.level == level]

    def get_affected_paths(self) -> set[str]:
        """Get all unique paths affected by compliance issues."""
        paths = set()
        for check in self.checks:
            paths.update(check.affected_paths)
        return paths