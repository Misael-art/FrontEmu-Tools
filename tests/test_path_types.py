"""Tests for PathTypes module."""

import pytest

from domain.path_types import (
    PathType,
    PathDefinition,
    PathCategory,
    PATH_CATEGORIES,
    get_path_category,
    get_paths_by_category,
)


class TestPathType:
    """Test cases for PathType enum."""

    def test_path_type_values(self):
        """Test that PathType enum has expected values."""
        assert PathType.BASE_DRIVE.value == "base_drive"
        assert PathType.EMULATION_ROOT.value == "emulation_root"
        assert PathType.ROM_DIRECTORY.value == "rom_directory"
        assert PathType.CONFIG_FILE.value == "config_file"
        assert PathType.LOG_FILE.value == "log_file"

    def test_path_type_enumeration(self):
        """Test that all expected path types are present."""
        expected_types = {
            "BASE_DRIVE",
            "EMULATION_ROOT",
            "ROM_DIRECTORY",
            "ROM_SUBDIRECTORY",
            "SAVE_DIRECTORY",
            "SAVE_SUBDIRECTORY",
            "CONFIG_DIRECTORY",
            "CONFIG_FILE",
            "EMULATOR_EXECUTABLE",
            "EMULATOR_CONFIG",
            "BACKUP_DIRECTORY",
            "TEMP_DIRECTORY",
            "ASSET_DIRECTORY",
            "THUMBNAIL_DIRECTORY",
            "LOG_DIRECTORY",
            "LOG_FILE",
            "SYMLINK_SOURCE",
            "SYMLINK_TARGET",
        }
        
        actual_types = {path_type.name for path_type in PathType}
        assert actual_types == expected_types


class TestPathDefinition:
    """Test cases for PathDefinition dataclass."""

    def test_path_definition_creation(self):
        """Test creating a PathDefinition instance."""
        path_def = PathDefinition(
            path_type=PathType.ROM_DIRECTORY,
            description="ROM storage directory",
            required=True,
            create_if_missing=True,
            permissions="755"
        )
        
        assert path_def.path_type == PathType.ROM_DIRECTORY
        assert path_def.description == "ROM storage directory"
        assert path_def.required is True
        assert path_def.create_if_missing is True
        assert path_def.permissions == "755"
        assert path_def.metadata == {}

    def test_path_definition_defaults(self):
        """Test PathDefinition with default values."""
        path_def = PathDefinition(
            path_type=PathType.CONFIG_FILE,
            description="Configuration file"
        )
        
        assert path_def.required is True
        assert path_def.create_if_missing is True
        assert path_def.permissions == "755"
        assert path_def.metadata == {}

    def test_path_definition_with_metadata(self):
        """Test PathDefinition with custom metadata."""
        metadata = {"owner": "user", "group": "admin"}
        path_def = PathDefinition(
            path_type=PathType.LOG_DIRECTORY,
            description="Log directory",
            metadata=metadata
        )
        
        assert path_def.metadata == metadata

    def test_path_definition_post_init(self):
        """Test that __post_init__ initializes metadata when None."""
        path_def = PathDefinition(
            path_type=PathType.TEMP_DIRECTORY,
            description="Temporary directory",
            metadata=None
        )
        
        assert path_def.metadata == {}


class TestPathCategory:
    """Test cases for PathCategory enum."""

    def test_path_category_values(self):
        """Test that PathCategory enum has expected values."""
        assert PathCategory.SYSTEM.value == "system"
        assert PathCategory.EMULATION.value == "emulation"
        assert PathCategory.USER_DATA.value == "user_data"
        assert PathCategory.CONFIGURATION.value == "configuration"
        assert PathCategory.TEMPORARY.value == "temporary"
        assert PathCategory.ASSETS.value == "assets"
        assert PathCategory.LOGS.value == "logs"

    def test_path_category_enumeration(self):
        """Test that all expected categories are present."""
        expected_categories = {
            "SYSTEM",
            "EMULATION",
            "USER_DATA",
            "CONFIGURATION",
            "TEMPORARY",
            "ASSETS",
            "LOGS",
        }
        
        actual_categories = {category.name for category in PathCategory}
        assert actual_categories == expected_categories


class TestPathCategoriesMapping:
    """Test cases for PATH_CATEGORIES mapping."""

    def test_path_categories_completeness(self):
        """Test that all PathType values are mapped to categories."""
        all_path_types = set(PathType)
        mapped_path_types = set(PATH_CATEGORIES.keys())
        
        assert all_path_types == mapped_path_types

    def test_specific_path_mappings(self):
        """Test specific path type to category mappings."""
        assert PATH_CATEGORIES[PathType.BASE_DRIVE] == PathCategory.SYSTEM
        assert PATH_CATEGORIES[PathType.ROM_DIRECTORY] == PathCategory.USER_DATA
        assert PATH_CATEGORIES[PathType.CONFIG_FILE] == PathCategory.CONFIGURATION
        assert PATH_CATEGORIES[PathType.LOG_FILE] == PathCategory.LOGS
        assert PATH_CATEGORIES[PathType.TEMP_DIRECTORY] == PathCategory.TEMPORARY
        assert PATH_CATEGORIES[PathType.ASSET_DIRECTORY] == PathCategory.ASSETS
        assert PATH_CATEGORIES[PathType.EMULATOR_EXECUTABLE] == PathCategory.EMULATION


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_get_path_category(self):
        """Test get_path_category function."""
        assert get_path_category(PathType.ROM_DIRECTORY) == PathCategory.USER_DATA
        assert get_path_category(PathType.CONFIG_FILE) == PathCategory.CONFIGURATION
        assert get_path_category(PathType.LOG_DIRECTORY) == PathCategory.LOGS

    def test_get_path_category_unknown(self):
        """Test get_path_category with unknown path type."""
        # Create a mock PathType that's not in the mapping
        class MockPathType:
            pass
        
        mock_path = MockPathType()
        result = get_path_category(mock_path)
        assert result == PathCategory.SYSTEM  # Default fallback

    def test_get_paths_by_category(self):
        """Test get_paths_by_category function."""
        user_data_paths = get_paths_by_category(PathCategory.USER_DATA)
        expected_user_data = [
            PathType.ROM_DIRECTORY,
            PathType.ROM_SUBDIRECTORY,
            PathType.SAVE_DIRECTORY,
            PathType.SAVE_SUBDIRECTORY,
        ]
        
        assert set(user_data_paths) == set(expected_user_data)

    def test_get_paths_by_category_system(self):
        """Test get_paths_by_category for system category."""
        system_paths = get_paths_by_category(PathCategory.SYSTEM)
        expected_system = [
            PathType.BASE_DRIVE,
            PathType.SYMLINK_SOURCE,
            PathType.SYMLINK_TARGET,
        ]
        
        assert set(system_paths) == set(expected_system)

    def test_get_paths_by_category_empty(self):
        """Test get_paths_by_category with category that has no paths."""
        # Create a mock category that doesn't exist in mapping
        class MockCategory:
            pass
        
        mock_category = MockCategory()
        result = get_paths_by_category(mock_category)
        assert result == []

    def test_all_categories_have_paths(self):
        """Test that all categories have at least one path type."""
        for category in PathCategory:
            paths = get_paths_by_category(category)
            assert len(paths) > 0, f"Category {category} has no associated paths"