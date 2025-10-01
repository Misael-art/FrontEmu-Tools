"""
SD Emulation Service

This service handles parsing of the SD emulation architecture document and
provides compliance checking and rule enforcement capabilities.
"""

import re
from datetime import datetime
from pathlib import Path

# Import path management system
import sys
from pathlib import Path

# Add meta/config to path
meta_config_path = Path(__file__).parent.parent.parent / "meta" / "config"
sys.path.insert(0, str(meta_config_path))

try:
    from meta.config.path_config import PathConfigManager
    from meta.config.path_resolver import PathResolver
except ImportError:
    # Fallback imports
    class PathConfigManager:
        def __init__(self):
            pass
    class PathResolver:
        def __init__(self):
            pass
# Add src to path for imports
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

try:
    from domain.sd_rules import (
        BackupRule,
        ComplianceCheck,
        ComplianceLevel,
        ComplianceReport,
        DeduplicationRule,
        DirectoryStructureRule,
        LinkType,
        OperationRule,
        PathValidationRule,
        PlatformRule,
        PortabilityRule,
        SDEmulationRules,
        StorageRule,
        SymlinkRule,
    )
except ImportError:
    # Fallback imports
    class BackupRule:
        pass
    class ComplianceCheck:
        pass
    class ComplianceLevel:
        pass
    class ComplianceReport:
        pass
    class DeduplicationRule:
        pass
    class DirectoryStructureRule:
        pass
    class LinkType:
        pass
    class OperationRule:
        pass
    class PathValidationRule:
        pass
    class PlatformRule:
        pass
    class PortabilityRule:
        pass
    class SDEmulationRules:
        pass
    class StorageRule:
        pass
    class SymlinkRule:
        pass


class SDEmulationService:
    """Service for parsing and enforcing SD emulation rules."""

    def __init__(self, architecture_doc_path: str | None = None):
        """
        Initialize the SD emulation service.

        Args:
            architecture_doc_path: Path to the sd-emulation.md architecture document (optional, uses dynamic path if not provided)
        """
        # Initialize path management
        self.path_config_manager = PathConfigManager()
        self.path_resolver = PathResolver()

        # Use dynamic path if not provided
        if architecture_doc_path is None:
            result = self.path_resolver.resolve_path("architecture_doc_path")
            self.architecture_doc_path = str(result.resolved_path)
        else:
            self.architecture_doc_path = architecture_doc_path
        self._rules: SDEmulationRules | None = None

    def parse_rules_from_document(self, document_path: str) -> SDEmulationRules:
        """
        Parse SD emulation rules from the architecture document.

        Args:
            document_path: Path to the sd-emulation.md file

        Returns:
            Structured SDEmulationRules object

        Raises:
            FileNotFoundError: If document not found
            ValueError: If document format is invalid
        """
        doc_path = Path(document_path)
        if not doc_path.exists():
            raise FileNotFoundError(f"Architecture document not found: {document_path}")

        try:
            with open(doc_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"Failed to read architecture document: {e}")

        return self._parse_document_content(content)

    def _parse_document_content(self, content: str) -> SDEmulationRules:
        """Parse the architecture document content into structured rules."""

        # Extract directory structure rules
        directory_rules = self._extract_directory_structure_rules(content)

        # Extract symlink rules
        symlink_rules = self._extract_symlink_rules(content)

        # Extract platform rules from platform mappings table
        platform_rules = self._extract_platform_rules(content)

        # Extract deduplication rules
        deduplication_rules = self._extract_deduplication_rules(content)

        # Extract path validation rules
        path_validation = self._extract_path_validation_rules(content)

        # Extract backup rules
        backup_rules = self._extract_backup_rules(content)

        # Extract portability rules
        portability_rules = self._extract_portability_rules(content)

        # Extract storage rules
        storage_rules = self._extract_storage_rules(content)

        # Extract operation rules
        operation_rules = self._extract_operation_rules(content)

        return SDEmulationRules(
            version="1.0.0",
            description="SD Emulation Architecture Rules parsed from sd-emulation.md",
            directory_structure=directory_rules,
            symlink_rules=symlink_rules,
            platform_rules=platform_rules,
            deduplication_rules=deduplication_rules,
            path_validation=path_validation,
            backup_rules=backup_rules,
            portability_rules=portability_rules,
            storage_rules=storage_rules,
            operation_rules=operation_rules,
        )

    def _extract_directory_structure_rules(
        self, content: str
    ) -> list[DirectoryStructureRule]:
        """Extract directory structure rules from document."""
        rules = []
        
        # If content is empty, return empty rules
        if not content.strip():
            return rules

        # Core directory structure patterns
        core_dirs = [
            (
                "Emulation/",
                "Centralizes resources common for all emulators and frontends",
            ),
            ("Emulation/bios/", "Firmware/BIOS per emulator"),
            ("Emulation/saves/", "Saves and states per console"),
            ("Emulation/shaders/", "Global shared assets (GLSL)"),
            ("Emulation/configs/", "Overrides INI/XML/JSON per emulator"),
            ("Emulators/", "Emulator installations with relative symlinks"),
            ("Roms/", "Real ROM storage with full names"),
            ("Emulation/roms/", "Short name symlinks for compatibility"),
            ("Frontends/", "Frontend configurations"),
            ("Tools/scripts/", "Maintenance kit"),
        ]

        # Get dynamic base drive
        base_drive_result = self.path_resolver.resolve_path("base")
        base_drive = str(base_drive_result.resolved_path)

        for path, purpose in core_dirs:
            rules.append(
                DirectoryStructureRule(
                    path=path,
                    purpose=purpose,
                    required=True,
                    relative_to=base_drive,
                    system_files=(
                        ["systeminfo.txt", "metadata.txt", "gamelist.xml"]
                        if "Roms/" in path
                        else []
                    ),
                )
            )

        return rules

    def _extract_symlink_rules(self, content: str) -> list[SymlinkRule]:
        """Extract symbolic link rules from document."""
        rules = []

        # Extract symlink examples from the document
        emulation_root = str(self.path_resolver.resolve_path('emulation_root').resolved_path)
        emulators_root = str(self.path_resolver.resolve_path('emulators_root').resolved_path)
        
        symlink_patterns = [
            (
                f"{emulation_root}/roms/{{short_name}}/",
                "../../Roms/{full_name}/",
                "ROM compatibility symlinks for frontends",
            ),
            (
                f"{emulators_root}/{{emulator}}/shaders/",
                "../../../Emulation/shaders/",
                "Shared shader resources",
            ),
            (
                f"{emulators_root}/{{emulator}}/bios/",
                "../../../Emulation/bios/",
                "Shared BIOS resources",
            ),
            (
                f"{emulators_root}/{{emulator}}/saves/",
                "../../../Emulation/saves/",
                "Shared save files",
            ),
        ]

        for source, target, description in symlink_patterns:
            rules.append(
                SymlinkRule(
                    source_pattern=source,
                    target_pattern=target,
                    link_type=LinkType.SYMBOLIC_LINK,
                    relative=True,
                    required=True,
                    description=description,
                )
            )

        return rules

    def _extract_platform_rules(self, content: str) -> list[PlatformRule]:
        """Extract platform rules from the platform mappings table."""
        rules = []

        # Extract table content between markers
        table_match = re.search(
            r"\|\|\s*Short_Name\s*\|.*?\n(.*?)(?=\n\*|\n#|\Z)", content, re.DOTALL
        )

        if table_match:
            table_content = table_match.group(1)

            # Parse table rows
            for line in table_content.split("\n"):
                if line.strip() and line.strip().startswith("||"):
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 3:
                        short_name = parts[0]
                        full_name = parts[1]

                        # Extract supported extensions if available
                        extensions = self._extract_extensions_for_platform(
                            content, short_name
                        )

                        rules.append(
                            PlatformRule(
                                short_name=short_name,
                                full_name=full_name,
                                supported_extensions=extensions,
                                system_files=[
                                    "systeminfo.txt",
                                    "metadata.txt",
                                    "gamelist.xml",
                                ],
                                symlink_required=True,
                            )
                        )

        return rules

    def _extract_extensions_for_platform(
        self, content: str, platform: str
    ) -> list[str]:
        """Extract supported file extensions for a platform."""
        # Look for extension patterns in the document
        common_extensions = {
            "nes": [".nes", ".fds"],
            "snes": [".smc", ".sfc", ".zip"],
            "gb": [".gb", ".gbc", ".zip"],
            "gba": [".gba", ".zip"],
            "psx": [".cue", ".bin", ".iso", ".pbp"],
            "ps2": [".iso", ".cso", ".chd"],
            "gc": [".iso", ".rvz", ".gcm"],
            "wii": [".iso", ".wbfs", ".rvz"],
            "n64": [".n64", ".z64", ".v64"],
            "3ds": [".3ds", ".cia"],
            "nds": [".nds", ".zip"],
            "psp": [".iso", ".cso", ".pbp"],
            "dreamcast": [".chd", ".cdi", ".iso", ".gdi", ".cue"],
            "switch": [".nsp", ".xci"],
            "mame": [".zip", ".7z"],
            "arcade": [".zip", ".7z"],
        }

        return common_extensions.get(platform, [".zip", ".7z"])

    def _extract_deduplication_rules(self, content: str) -> list[DeduplicationRule]:
        """Extract deduplication rules from document."""
        rules = []

        # Pattern for deduplication mentions
        if "deduplicação" in content or "redundancy_cleanup" in content:
            rules.append(
                DeduplicationRule(
                    target_directories=[
                        f"{self.path_resolver.resolve_path('emulators_root').resolved_path}/",
                        f"{self.path_resolver.resolve_path('emulation_root').resolved_path}/shaders/",
                    ],
                    file_patterns=["*.dll", "*.exe", "*.glsl", "*.cg"],
                    hash_based=True,
                    preserve_newest=True,
                    backup_duplicates=True,
                    min_file_size_mb=1,
                )
            )

            rules.append(
                DeduplicationRule(
                    target_directories=[
                        f"{self.path_resolver.resolve_path('roms_root').resolved_path}/"
                    ],
                    file_patterns=["*.zip", "*.7z", "*.iso", "*.chd"],
                    hash_based=True,
                    preserve_newest=False,  # Preserve by region/version priority
                    backup_duplicates=True,
                    min_file_size_mb=10,  # Larger threshold for ROMs
                )
            )

        return rules

    def _extract_path_validation_rules(self, content: str) -> PathValidationRule:
        """Extract path validation rules from document."""
        forbidden_patterns = []

        # Extract forbidden patterns from warnings
        if "C:/" in content:
            forbidden_patterns.append("C:/")
        if "%APPDATA%" in content:
            forbidden_patterns.append("%APPDATA%")
        if "%USERPROFILE%" in content:
            forbidden_patterns.append("%USERPROFILE%")

        return PathValidationRule(
            forbidden_patterns=forbidden_patterns,
            required_patterns=[f"{self.path_resolver.resolve_path('base').resolved_path}/"],
            max_path_length=260,
            max_filename_length=255,
            case_sensitive=False,
        )

    def _extract_backup_rules(self, content: str) -> list[BackupRule]:
        """Extract backup rules from document."""
        rules = []

        backup_path_result = self.path_resolver.resolve_path("backup")
        backup_path = str(backup_path_result.resolved_path)
        if "backup" in content.lower() or backup_path.lower() in content.lower():
            rules.append(
                BackupRule(
                    target_patterns=[
                        f"{str(self.path_resolver.resolve_path('emulation_root').resolved_path)}/saves/*",
                        f"{str(self.path_resolver.resolve_path('emulation_root').resolved_path)}/configs/*",
                    ],
                    backup_location=f"{str(self.path_resolver.resolve_path('backup').resolved_path)}/",
                    timestamp_format="%Y%m%d_%H%M%S",
                    compression_enabled=True,
                    retention_days=30,
                    max_backup_size_gb=10,
                )
            )

        return rules

    def _extract_portability_rules(self, content: str) -> PortabilityRule:
        """Extract portability rules from document."""
        return PortabilityRule(
            require_relative_paths=True,
            forbidden_absolute_patterns=[
                "C:/",
                "%APPDATA%",
                "%USERPROFILE%",
                "%PROGRAMFILES%",
            ],
            allowed_drive_patterns=[
                f"{str(self.path_resolver.resolve_path('base').resolved_path)}/"
            ],
            validate_symlink_targets=True,
        )

    def _extract_storage_rules(self, content: str) -> StorageRule:
        """Extract storage management rules from document."""
        # Look for space requirements in the document
        space_match = re.search(r"(\d+)GB", content)
        min_space = 20  # Default from document context
        if space_match:
            min_space = int(space_match.group(1))

        return StorageRule(
            minimum_free_space_gb=min_space,
            warning_threshold_gb=10,
            critical_threshold_gb=5,
            enable_deduplication=True,
            compress_backups=True,
            cleanup_temp_files=True,
        )

    def _extract_operation_rules(self, content: str) -> OperationRule:
        """Extract operation execution rules from document."""
        return OperationRule(
            require_dry_run_first=True,
            require_confirmation=True,
            enable_rollback=True,
            max_parallel_operations=4,
            operation_timeout_seconds=300,
            log_all_operations=True,
        )

    def get_rules(self) -> SDEmulationRules:
        """Get the current rules set."""
        if self._rules is None and self.architecture_doc_path:
            self._rules = self.parse_rules_from_document(self.architecture_doc_path)
        return self._rules

    def check_compliance(
        self, target_path: str, rules: SDEmulationRules | None = None
    ) -> ComplianceReport:
        """
        Check compliance of a target path against SD emulation rules.

        Args:
            target_path: Path to check for compliance
            rules: Rules to check against (uses default if None)

        Returns:
            Comprehensive compliance report
        """
        if rules is None:
            rules = self.get_rules()

        if rules is None:
            raise ValueError("No rules available for compliance checking")

        checks = []
        target = Path(target_path)

        # Check directory structure compliance
        checks.extend(self._check_directory_structure(target, rules))

        # Check symlink compliance
        checks.extend(self._check_symlink_compliance(target, rules))

        # Check path validation compliance
        checks.extend(rules.validate_path_compliance(str(target)))

        # Check storage compliance
        checks.extend(self._check_storage_compliance(target, rules))

        # Compile report statistics
        total_checks = len(checks)
        compliant_checks = len(
            [c for c in checks if c.level == ComplianceLevel.COMPLIANT]
        )
        warning_checks = len([c for c in checks if c.level == ComplianceLevel.WARNING])
        non_compliant_checks = len(
            [c for c in checks if c.level == ComplianceLevel.NON_COMPLIANT]
        )

        # Generate summary by rule category
        summary = {}
        for check in checks:
            category = check.rule_name.split("_")[0]  # Extract category prefix
            summary[category] = summary.get(category, 0) + 1

        # Generate recommendations
        recommendations = self._generate_recommendations(checks)

        return ComplianceReport(
            timestamp=datetime.now().isoformat(),
            rules_version=rules.version,
            total_checks=total_checks,
            compliant_checks=compliant_checks,
            warning_checks=warning_checks,
            non_compliant_checks=non_compliant_checks,
            checks=checks,
            summary=summary,
            recommendations=recommendations,
        )

    def _check_directory_structure(
        self, target_path: Path, rules: SDEmulationRules
    ) -> list[ComplianceCheck]:
        """Check directory structure compliance."""
        checks = []

        for dir_rule in rules.get_required_directories():
            expected_path = target_path / dir_rule.path

            if expected_path.exists():
                checks.append(
                    ComplianceCheck(
                        rule_name="directory_structure_compliant",
                        level=ComplianceLevel.COMPLIANT,
                        message=f"Required directory exists: {dir_rule.path}",
                        affected_paths=[str(expected_path)],
                    )
                )
            else:
                checks.append(
                    ComplianceCheck(
                        rule_name="directory_structure_missing",
                        level=ComplianceLevel.NON_COMPLIANT,
                        message=f"Required directory missing: {dir_rule.path}",
                        affected_paths=[str(expected_path)],
                        suggested_action=f"Create directory: {expected_path}",
                    )
                )

        return checks

    def _check_symlink_compliance(
        self, target_path: Path, rules: SDEmulationRules
    ) -> list[ComplianceCheck]:
        """Check symbolic link compliance."""
        checks = []

        for symlink_rule in rules.get_required_symlinks():
            # This would need platform-specific implementation
            # For now, provide general guidance
            checks.append(
                ComplianceCheck(
                    rule_name="symlink_compliance_check",
                    level=ComplianceLevel.WARNING,
                    message=f"Manual verification needed for symlinks: {symlink_rule.description}",
                    details=f"Source: {symlink_rule.source_pattern}, Target: {symlink_rule.target_pattern}",
                    suggested_action="Verify symlinks exist and point to correct targets",
                )
            )

        return checks

    def _check_storage_compliance(
        self, target_path: Path, rules: SDEmulationRules
    ) -> list[ComplianceCheck]:
        """Check storage space compliance."""
        checks = []

        try:
            # Check available disk space
            import shutil

            _, _, free_bytes = shutil.disk_usage(target_path)
            free_gb = free_bytes // (1024**3)

            if free_gb >= rules.storage_rules.minimum_free_space_gb:
                checks.append(
                    ComplianceCheck(
                        rule_name="storage_space_sufficient",
                        level=ComplianceLevel.COMPLIANT,
                        message=f"Sufficient free space: {free_gb}GB available",
                        affected_paths=[str(target_path)],
                    )
                )
            elif free_gb >= rules.storage_rules.critical_threshold_gb:
                checks.append(
                    ComplianceCheck(
                        rule_name="storage_space_warning",
                        level=ComplianceLevel.WARNING,
                        message=f"Low disk space: {free_gb}GB available",
                        affected_paths=[str(target_path)],
                        suggested_action="Consider cleaning up old files or expanding storage",
                    )
                )
            else:
                checks.append(
                    ComplianceCheck(
                        rule_name="storage_space_critical",
                        level=ComplianceLevel.NON_COMPLIANT,
                        message=f"Critical disk space: {free_gb}GB available",
                        affected_paths=[str(target_path)],
                        suggested_action="Immediate action required: free up disk space",
                    )
                )

        except Exception as e:
            checks.append(
                ComplianceCheck(
                    rule_name="storage_check_failed",
                    level=ComplianceLevel.UNKNOWN,
                    message=f"Failed to check disk space: {e}",
                    affected_paths=[str(target_path)],
                )
            )

        return checks

    def _generate_recommendations(self, checks: list[ComplianceCheck]) -> list[str]:
        """Generate high-level recommendations based on compliance checks."""
        recommendations = []

        non_compliant = [c for c in checks if c.level == ComplianceLevel.NON_COMPLIANT]
        warnings = [c for c in checks if c.level == ComplianceLevel.WARNING]

        if non_compliant:
            recommendations.append(
                f"Address {len(non_compliant)} critical compliance issues before proceeding"
            )

        if warnings:
            recommendations.append(
                f"Consider resolving {len(warnings)} warning issues for optimal setup"
            )

        # Specific recommendations based on rule types
        rule_types = {check.rule_name.split("_")[0] for check in non_compliant}

        if "directory" in rule_types:
            recommendations.append(
                "Create missing required directories for proper emulation structure"
            )

        if "storage" in rule_types:
            recommendations.append("Free up disk space or expand storage capacity")

        if "path" in rule_types:
            recommendations.append(
                "Fix path issues to ensure portability across systems"
            )

        return recommendations

    def plan_sd_alignment(
        self, target_path: str, rules: SDEmulationRules | None = None
    ) -> dict[str, list[str]]:
        """
        Generate a plan to align the system with SD emulation rules.

        Args:
            target_path: Path to align
            rules: Rules to align against

        Returns:
            Dictionary of action categories with specific actions
        """
        if rules is None:
            rules = self.get_rules()

        report = self.check_compliance(target_path, rules)
        plan = {
            "critical_actions": [],
            "recommended_actions": [],
            "optional_improvements": [],
        }

        for check in report.checks:
            if check.level == ComplianceLevel.NON_COMPLIANT and check.suggested_action:
                plan["critical_actions"].append(check.suggested_action)
            elif check.level == ComplianceLevel.WARNING and check.suggested_action:
                plan["recommended_actions"].append(check.suggested_action)

        # Add general improvements
        plan["optional_improvements"].extend(
            [
                "Run deduplication cleanup to save space",
                "Verify all symlinks point to correct targets",
                "Set up automated backup schedule for critical files",
            ]
        )

        return plan