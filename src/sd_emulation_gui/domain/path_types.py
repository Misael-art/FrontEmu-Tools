"""Path types and enumerations for SD emulation system."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class PathType(Enum):
    """Enumeration of different path types in the SD emulation system."""

    # Base paths
    BASE_DRIVE = "base_drive"
    BASE = "base"
    CONFIG = "config"
    CONFIG_DIRECTORY = "config_directory"
    CONFIG_FILE = "config_file"

    # Emulation roots and related directories
    EMULATION_ROOT = "emulation_root"
    EMULATION = "emulation"
    EMULATORS = "emulators"
    ROMS = "roms"
    FRONTENDS = "frontends"
    TOOLS = "tools"

    # ROM paths
    ROM_DIRECTORY = "rom_directory"
    ROM_SUBDIRECTORY = "rom_subdirectory"

    # Save paths
    SAVE_DIRECTORY = "save_directory"
    SAVE_SUBDIRECTORY = "save_subdirectory"

    # Emulator paths
    EMULATOR_EXECUTABLE = "emulator_executable"
    EMULATOR_CONFIG = "emulator_config"

    # Backup and temporary paths
    BACKUP_DIRECTORY = "backup_directory"
    TEMP_DIRECTORY = "temp_directory"

    # Asset paths
    ASSET_DIRECTORY = "asset_directory"
    THUMBNAIL_DIRECTORY = "thumbnail_directory"

    # Log paths
    LOG_DIRECTORY = "log_directory"
    LOG_FILE = "log_file"

    # Symlink paths
    SYMLINK_SOURCE = "symlink_source"
    SYMLINK_TARGET = "symlink_target"


@dataclass
class PathDefinition:
    """Definition of a path with its properties and constraints."""

    path_type: PathType
    description: str
    required: bool = True
    create_if_missing: bool = True
    permissions: str = "755"
    metadata: dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class PathCategory(Enum):
    """Categories for grouping related path types."""

    SYSTEM = "system"
    EMULATION = "emulation"
    USER_DATA = "user_data"
    CONFIGURATION = "configuration"
    TEMPORARY = "temporary"
    ASSETS = "assets"
    LOGS = "logs"


# Path type to category mapping
PATH_CATEGORIES = {
    PathType.BASE_DRIVE: PathCategory.SYSTEM,
    PathType.BASE: PathCategory.SYSTEM,
    PathType.CONFIG: PathCategory.CONFIGURATION,
    PathType.EMULATION_ROOT: PathCategory.EMULATION,
    PathType.EMULATION: PathCategory.EMULATION,
    PathType.EMULATORS: PathCategory.EMULATION,
    PathType.ROMS: PathCategory.USER_DATA,
    PathType.FRONTENDS: PathCategory.EMULATION,
    PathType.TOOLS: PathCategory.SYSTEM,
    PathType.ROM_DIRECTORY: PathCategory.USER_DATA,
    PathType.ROM_SUBDIRECTORY: PathCategory.USER_DATA,
    PathType.SAVE_DIRECTORY: PathCategory.USER_DATA,
    PathType.SAVE_SUBDIRECTORY: PathCategory.USER_DATA,
    PathType.CONFIG_DIRECTORY: PathCategory.CONFIGURATION,
    PathType.CONFIG_FILE: PathCategory.CONFIGURATION,
    PathType.EMULATOR_EXECUTABLE: PathCategory.EMULATION,
    PathType.EMULATOR_CONFIG: PathCategory.CONFIGURATION,
    PathType.BACKUP_DIRECTORY: PathCategory.TEMPORARY,
    PathType.TEMP_DIRECTORY: PathCategory.TEMPORARY,
    PathType.ASSET_DIRECTORY: PathCategory.ASSETS,
    PathType.THUMBNAIL_DIRECTORY: PathCategory.ASSETS,
    PathType.LOG_DIRECTORY: PathCategory.LOGS,
    PathType.LOG_FILE: PathCategory.LOGS,
    PathType.SYMLINK_SOURCE: PathCategory.SYSTEM,
    PathType.SYMLINK_TARGET: PathCategory.SYSTEM,
}


def get_path_category(path_type: PathType) -> PathCategory:
    """Get the category for a given path type."""
    return PATH_CATEGORIES.get(path_type, PathCategory.SYSTEM)


def get_paths_by_category(category: PathCategory) -> list[PathType]:
    """Get all path types in a given category."""
    return [path_type for path_type, cat in PATH_CATEGORIES.items() if cat == category]