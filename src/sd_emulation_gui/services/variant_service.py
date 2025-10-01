"""
Variant Service - Intelligent ROM Folder Organization

This service handles automatic detection, creation, and validation of
variant folder structures with integrated symlinks and media management.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Import path management system
try:
    from meta.config.path_config import PathConfigManager
    from meta.config.path_resolver import PathResolver
except ImportError:
    # Fallback imports
    class PathConfigManager:
        pass
    class PathResolver:
        pass


@dataclass
class SymlinkOperation:
    """Represents a symlinking operation for a variant."""

    variant_type: str
    platform_name: str
    main_platform_dir: str
    target_variant_folder: str
    main_media_dir: str
    status: str = "pending"  # pending, detected, created, failed


@dataclass
class PlatformVariantAnalysis:
    """Analysis result for a specific platform's variant structure."""

    platform_name: str
    platform_dir: Path
    variant_ops: list[SymlinkOperation] = field(default_factory=list)
    main_media_dir: str | None = None


@dataclass
class MigrationOperation:
    """Represents a single migration operation."""

    id: str
    operation_type: str
    description: str
    source_path: str | None = None
    target_path: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class MigrationPlan:
    """Complete migration plan with operations."""

    plan_id: str
    description: str
    operations: list[MigrationOperation] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result of executing a migration plan."""

    success: bool = False
    executed_operations: int = 0
    failed_operations: int = 0
    errors: list[str] = field(default_factory=list)


class VariantService:
    """Service for managing ROM variant organization and symlinks."""

    @staticmethod
    def _coerce_path_result(value: Any) -> Path:
        if hasattr(value, "resolved_path") and value.resolved_path:
            return Path(value.resolved_path)
        return Path(value)

    def __init__(
        self,
        base_path: str | None = None,
        *,
        path_config_manager: PathConfigManager | None = None,
        path_resolver: PathResolver | None = None,
    ):
        """
        Initialize variant service.

        Args:
            base_path: Base SD card path (optional, uses dynamic path if not provided)
        """
        self.path_config_manager = path_config_manager or PathConfigManager()
        self.path_resolver = path_resolver or PathResolver()

        resolver = self.path_resolver

        base_drive_resolution = resolver.resolve_path("base_drive")
        config_resolution = resolver.resolve_path("config_base_path")

        if base_path is None:
            if base_drive_resolution is not None:
                base_path = self._coerce_path_result(base_drive_resolution)
            else:
                base_path = self._coerce_path_result(
                    getattr(self.path_config_manager, "get_base_path", lambda: Path.cwd())()
                )

        self._config_base_path = self._coerce_path_result(config_resolution)

        self.base_path = Path(base_path)
        self.roms_path = self.base_path / "Roms"
        self.emulation_path = self.base_path / "Emulation"
        self.media_path = self.emulation_path / "downloaded_media"

        self.logger = logging.getLogger(__name__)

        # Ensure required directories exist
        self.roms_path.mkdir(exist_ok=True)
        self.media_path.mkdir(exist_ok=True)

        # Load variant mapping
        self.variant_mapping = self._load_variant_mapping()

    def _load_variant_mapping(self) -> dict[str, dict[str, str]]:
        """Load variant mapping configuration."""
        config_base = self._config_base_path
        mapping_file = Path(config_base) / "variant_mapping.json"

        try:
            with open(mapping_file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"variant_mapping.json not found: {mapping_file}")
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load variant mapping: {e}")
            return {}

    def analyze_variant_structure(self) -> list[PlatformVariantAnalysis]:
        """
        Analyze existing ROM folder structure and identify variant opportunities.

        Returns:
            List of variant analysis results
        """
        analyses = []

        if not self.roms_path.exists():
            self.logger.warning("ROMs path does not exist")
            return analyses

        # Analyze each platform folder
        for platform_dir in self.roms_path.iterdir():
            if not platform_dir.is_dir():
                continue

            platform_name = platform_dir.name
            analysis = self._analyze_platform_variants(platform_name, platform_dir)
            if analysis.variant_ops:
                analyses.append(analysis)

        return analyses

    def _analyze_platform_variants(
        self, platform_name: str, platform_dir: Path
    ) -> PlatformVariantAnalysis:
        """Analyze a single platform for variant opportunities."""
        analysis = PlatformVariantAnalysis(platform_name, platform_dir)
        analysis.main_media_dir = self._get_platform_media_dir(platform_name)

        # Look for existing variant folders or files that suggest variants
        existing_folders = [
            item.name for item in platform_dir.iterdir() if item.is_dir()
        ]

        # Check for variant indicators
        variant_indicators = self._detect_variant_indicators(
            platform_name, existing_folders
        )

        for indicator in variant_indicators:
            variant_folder = self._find_actual_variant_folder(platform_name, indicator)
            if variant_folder:
                op = SymlinkOperation(
                    variant_type=indicator,
                    platform_name=platform_name,
                    main_platform_dir=platform_name,
                    target_variant_folder=variant_folder,
                    main_media_dir=analysis.main_media_dir,
                    status="detected",
                )
                analysis.variant_ops.append(op)

        # Also check for folders that might be variants themselves
        for folder in existing_folders:
            if folder != "media":  # Skip media folder
                variant_type = self._detect_if_variant_folder(platform_name, folder)
                if variant_type:
                    existing_variant_folder = self._find_actual_variant_folder(
                        platform_name, variant_type
                    )
                    if not existing_variant_folder:
                        # Create operation to organize this as variant
                        op = SymlinkOperation(
                            variant_type=variant_type,
                            platform_name=platform_name,
                            main_platform_dir=platform_name,
                            target_variant_folder=folder,
                            main_media_dir=analysis.main_media_dir,
                            status="needs_organization",
                        )
                        analysis.variant_ops.append(op)

        return analysis

    def _detect_variant_indicators(
        self, platform_name: str, existing_folders: list[str]
    ) -> set[str]:
        """Detect variant indicators in existing folder structure."""
        indicators = set()

        # Check if there are variant-specific folders (regional, hacks, etc.)
        variant_indicators = [
            "Brazil Games Translated",
            "Hacks",
            "HD",
            "Homebrew",
            "Tech Demo",
            "Unlicensed",
            "Prototype",
            "Japanese",
        ]

        for indicator in variant_indicators:
            # Look for corresponding folders
            if indicator in existing_folders:
                indicators.add(indicator)

        return indicators

    def _find_actual_variant_folder(
        self, platform_name: str, variant_type: str
    ) -> str | None:
        """Find the actual variant folder name for a given variant type."""
        if platform_name not in self.variant_mapping:
            return None

        platform_variants = self.variant_mapping[platform_name]

        for key, value in platform_variants.items():
            if key == variant_type or value == variant_type:
                return value

        return None

    def _detect_if_variant_folder(
        self, platform_name: str, folder_name: str
    ) -> str | None:
        """Check if a folder name indicates a variant and return the variant type."""
        if platform_name not in self.variant_mapping:
            return None

        platform_variants = self.variant_mapping[platform_name]

        # Check if folder name matches any variant pattern
        for variant_type, folder_pattern in platform_variants.items():
            if folder_pattern in folder_name or variant_type in folder_name:
                return variant_type

        return None

    def _get_platform_media_dir(self, platform_name: str) -> str:
        """Get the media directory short name for a platform."""
        # Map common platforms to their short names
        media_short_names = {
            "Nintendo 3DS": "n3ds",
            "Nintendo Entertainment System": "nes",
            "Super Nintendo Entertainment System": "snes",
            "Nintendo Game Boy Advance": "gba",
            "Nintendo 64": "n64",
        }

        return media_short_names.get(
            platform_name, platform_name.lower().replace(" ", "").replace("-", "")
        )

    def plan_variant_symlinks(
        self, analyses: list[PlatformVariantAnalysis]
    ) -> MigrationPlan:
        """
        Create a migration plan for implementing variant symlinks.

        Args:
            analyses: List of platform analyses

        Returns:
            Migration plan with operations
        """
        import uuid

        plan_id = str(uuid.uuid4())[:8]
        plan = MigrationPlan(
            plan_id=plan_id,
            description="ROM Variant Structure Organization",
            operations=[],
        )

        for analysis in analyses:
            for op in analysis.variant_ops:
                plan.operations.append(
                    MigrationOperation(
                        id=str(uuid.uuid4())[:8],
                        operation_type="create_variant_symlink",
                        description=f"Create {op.variant_type} symlink for {op.platform_name}",
                        source_path=op.target_variant_folder,
                        target_path=op.variant_type,
                        metadata={
                            "platform": op.platform_name,
                            "variant_type": op.variant_type,
                            "media_link": op.main_media_dir,
                        },
                    )
                )

                # Add media symlink operation
                plan.operations.append(
                    MigrationOperation(
                        id=str(uuid.uuid4())[:8],
                        operation_type="create_media_symlink",
                        description=f"Link {op.variant_type} media to main platform media",
                        source_path=f"../Emulation/downloaded_media/{op.main_media_dir}",
                        target_path=f"{op.variant_type}/media",
                        metadata={
                            "platform": op.platform_name,
                            "variant_type": op.variant_type,
                        },
                    )
                )

        return plan

    def execute_variant_plan(self, plan: MigrationPlan) -> ExecutionResult:
        """Execute a migration plan for variant symlinks."""
        result = ExecutionResult()

        try:
            for operation in plan.operations:
                try:
                    if operation.operation_type == "create_variant_symlink":
                        self._execute_variant_symlink(operation)
                    elif operation.operation_type == "create_media_symlink":
                        self._execute_media_symlink(operation)
                    else:
                        raise ValueError(
                            f"Unknown operation type: {operation.operation_type}"
                        )

                    result.executed_operations += 1

                except Exception as e:
                    result.failed_operations += 1
                    result.errors.append(f"Operation {operation.id} failed: {str(e)}")
                    self.logger.error(
                        f"Failed to execute operation {operation.id}: {e}"
                    )

            result.success = result.failed_operations == 0

        except Exception as e:
            result.success = False
            result.errors.append(f"Execution failed: {str(e)}")
            self.logger.error(f"Variant plan execution failed: {e}")

        return result

    def _execute_variant_symlink(self, operation: MigrationOperation) -> None:
        """Execute a variant symlink operation."""
        if not operation.target_path:
            raise ValueError("Target path required for variant symlink")

        if not operation.source_path:
            raise ValueError("Source path required for variant symlink")

        platform_name = operation.metadata.get("platform", "")
        variant_type = operation.metadata.get("variant_type", "")

        # Construct paths
        platform_dir = self.roms_path / platform_name
        symlink_target = platform_dir / operation.target_path

        # Remove existing symlink if it exists
        if symlink_target.exists():
            if symlink_target.is_symlink():
                symlink_target.unlink()
            else:
                raise FileExistsError(
                    f"Cannot create symlink: {symlink_target} exists and is not a symlink"
                )

        # Create the symlink
        try:
            symlink_target.parent.mkdir(parents=True, exist_ok=True)
            symlink_target.symlink_to(operation.source_path, target_is_directory=True)
            self.logger.info(
                f"Created variant symlink: {symlink_target} -> {operation.source_path}"
            )
        except OSError as e:
            raise FileExistsError(
                f"Failed to create symlink: Administrator privileges required for: {e}"
            )

    def _execute_media_symlink(self, operation: MigrationOperation) -> None:
        """Execute a media symlink operation."""
        if not operation.target_path:
            raise ValueError("Target path required for media symlink")

        if not operation.source_path:
            raise ValueError("Source path required for media symlink")

        platform_name = operation.metadata.get("platform", "")
        variant_type = operation.metadata.get("variant_type", "")

        # Construct paths
        platform_dir = self.roms_path / platform_name
        variant_dir = platform_dir / variant_type
        media_dir = variant_dir / "media"

        # Remove existing media symlink if it exists
        if media_dir.exists():
            if media_dir.is_symlink():
                media_dir.unlink()
            else:
                self.logger.warning(
                    f"Media directory exists and is not a symlink: {media_dir}"
                )

        # Create the media symlink
        try:
            media_dir.parent.mkdir(parents=True, exist_ok=True)
            media_dir.symlink_to(operation.source_path, target_is_directory=True)
            self.logger.info(
                f"Created media symlink: {media_dir} -> {operation.source_path}"
            )
        except OSError as e:
            if "privilege not held" in str(e).lower():
                raise FileExistsError(
                    "Failed to create media symlink: Administrator privileges required"
                )
            else:
                raise FileExistsError(f"Failed to create media symlink: {e}")
