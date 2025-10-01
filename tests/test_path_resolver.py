"""Tests for config.path_resolver module."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from config.path_resolver import (
    PathResolutionResult,
    PathResolutionStrategy,
    PathResolver,
    convert_hardcoded_path,
    get_path_resolver,
    resolve_path,
)
from domain.path_types import PathType


class TestPathResolutionResult(unittest.TestCase):
    """Test PathResolutionResult class."""

    def test_valid_result_creation(self):
        """Test creating a valid resolution result."""
        path = Path("/test/path")
        result = PathResolutionResult(
            original_path="test",
            resolved_path=path,
            is_valid=True,
            strategy_used=PathResolutionStrategy.STRICT,
        )

        self.assertEqual(result.original_path, "test")
        self.assertEqual(result.resolved_path, path)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.strategy_used, PathResolutionStrategy.STRICT)
        self.assertIsNone(result.error_message)

    def test_invalid_result_creation(self):
        """Test creating an invalid resolution result."""
        result = PathResolutionResult(
            original_path="invalid",
            resolved_path=None,
            is_valid=False,
            error_message="Path not found",
        )

        self.assertEqual(result.original_path, "invalid")
        self.assertIsNone(result.resolved_path)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_message, "Path not found")


class TestPathResolver(unittest.TestCase):
    """Test PathResolver class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config_manager = Mock()
        self.mock_logger = Mock()

        # Mock platform detection
        with patch("platform.system", return_value="Windows"):
            self.resolver = PathResolver(config_manager=self.mock_config_manager)

        # Replace logger with mock
        self.resolver.logger = self.mock_logger

    def test_init_windows_platform(self):
        """Test initialization on Windows platform."""
        with patch("platform.system", return_value="Windows"):
            resolver = PathResolver()
            self.assertTrue(resolver.is_windows)

    def test_init_unix_platform(self):
        """Test initialization on Unix platform."""
        with patch("platform.system", return_value="Linux"):
            resolver = PathResolver()
            self.assertFalse(resolver.is_windows)

    def test_resolve_path_strict_strategy(self):
        """Test path resolution with strict strategy."""
        test_path = "/test/path"
        expected_path = Path("/resolved/path")

        with patch.object(self.resolver, "_resolve_strict", return_value=expected_path):
            result = self.resolver.resolve_path(
                test_path, PathResolutionStrategy.STRICT
            )

            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_path, expected_path)
            self.assertEqual(result.strategy_used, PathResolutionStrategy.STRICT)

    def test_resolve_path_flexible_strategy(self):
        """Test path resolution with flexible strategy."""
        test_path = "/test/path"
        expected_path = Path("/resolved/path")

        with patch.object(
            self.resolver, "_resolve_flexible", return_value=expected_path
        ):
            result = self.resolver.resolve_path(
                test_path, PathResolutionStrategy.FLEXIBLE
            )

            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_path, expected_path)
            self.assertEqual(result.strategy_used, PathResolutionStrategy.FLEXIBLE)

    def test_resolve_path_fallback_strategy(self):
        """Test path resolution with fallback strategy."""
        test_path = "/test/path"
        expected_path = Path("/resolved/path")

        with patch.object(
            self.resolver, "_resolve_with_fallback", return_value=expected_path
        ):
            result = self.resolver.resolve_path(
                test_path, PathResolutionStrategy.FALLBACK
            )

            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_path, expected_path)
            self.assertEqual(result.strategy_used, PathResolutionStrategy.FALLBACK)

    def test_resolve_path_auto_strategy_success(self):
        """Test path resolution with auto strategy - successful resolution."""
        test_path = "/test/path"
        expected_path = Path("/resolved/path")

        with patch.object(self.resolver, "_resolve_strict", return_value=expected_path):
            result = self.resolver.resolve_path(test_path, PathResolutionStrategy.AUTO)

            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_path, expected_path)
            self.assertEqual(result.strategy_used, PathResolutionStrategy.STRICT)

    def test_resolve_path_auto_strategy_fallback(self):
        """Test path resolution with auto strategy - falls back to flexible."""
        test_path = "/test/path"
        expected_path = Path("/resolved/path")

        with (
            patch.object(self.resolver, "_resolve_strict", return_value=None),
            patch.object(
                self.resolver, "_resolve_flexible", return_value=expected_path
            ),
        ):

            result = self.resolver.resolve_path(test_path, PathResolutionStrategy.AUTO)

            self.assertTrue(result.is_valid)
            self.assertEqual(result.resolved_path, expected_path)
            self.assertEqual(result.strategy_used, PathResolutionStrategy.FLEXIBLE)

    def test_resolve_path_failure(self):
        """Test path resolution failure."""
        test_path = "/invalid/path"

        with (
            patch.object(self.resolver, "_resolve_strict", return_value=None),
            patch.object(self.resolver, "_resolve_flexible", return_value=None),
            patch.object(self.resolver, "_resolve_with_fallback", return_value=None),
        ):

            result = self.resolver.resolve_path(test_path, PathResolutionStrategy.AUTO)

            self.assertFalse(result.is_valid)
            self.assertIsNone(result.resolved_path)
            self.assertIn("Failed to resolve path", result.error_message)

    @patch("utils.path_utils.PathUtils.normalize_path")
    def test_resolve_strict_existing_path(self, mock_normalize):
        """Test strict resolution with existing path."""
        test_path = "/existing/path"
        normalized_path = Path("/normalized/path")
        mock_normalize.return_value = normalized_path

        with patch.object(normalized_path, "exists", return_value=True):
            result = self.resolver._resolve_strict(test_path)

            self.assertEqual(result, normalized_path)
            mock_normalize.assert_called_once_with(test_path)

    @patch("utils.path_utils.PathUtils.normalize_path")
    def test_resolve_strict_nonexistent_path(self, mock_normalize):
        """Test strict resolution with non-existent path."""
        test_path = "/nonexistent/path"
        normalized_path = Path("/normalized/path")
        mock_normalize.return_value = normalized_path

        with patch.object(normalized_path, "exists", return_value=False):
            result = self.resolver._resolve_strict(test_path)

            self.assertIsNone(result)

    def test_resolve_by_mapping_exact_match(self):
        """Test resolution by mapping with exact match."""
        test_path = "mapped_path"
        expected_path = Path("/resolved/mapped/path")

        self.resolver.path_mappings = {"mapped_path": PathType.EMULATION}
        self.mock_config_manager.get_path.return_value = expected_path

        result = self.resolver._resolve_by_mapping(test_path)

        self.assertEqual(result, expected_path)
        self.mock_config_manager.get_path.assert_called_once_with(PathType.EMULATION)

    def test_resolve_by_mapping_case_insensitive(self):
        """Test resolution by mapping with case-insensitive match."""
        test_path = "MAPPED_PATH"
        expected_path = Path("/resolved/mapped/path")

        self.resolver.path_mappings = {"mapped_path": PathType.EMULATION}
        self.mock_config_manager.get_path.return_value = expected_path

        result = self.resolver._resolve_by_mapping(test_path)

        self.assertEqual(result, expected_path)

    def test_resolve_by_mapping_no_match(self):
        """Test resolution by mapping with no match."""
        test_path = "unmapped_path"

        self.resolver.path_mappings = {"other_path": PathType.EMULATION}

        result = self.resolver._resolve_by_mapping(test_path)

        self.assertIsNone(result)

    def test_resolve_by_pattern_windows(self):
        """Test pattern resolution on Windows."""
        self.resolver.is_windows = True
        test_path = "F:\\Emulation\\SubPath"
        expected_base = Path("/emulation/base")
        expected_result = expected_base / "SubPath"

        self.mock_config_manager.get_path.return_value = expected_base

        result = self.resolver._resolve_by_pattern(test_path)

        self.assertEqual(result, expected_result)
        self.mock_config_manager.get_path.assert_called_once_with(PathType.EMULATION)

    def test_resolve_by_pattern_unix(self):
        """Test pattern resolution on Unix."""
        self.resolver.is_windows = False
        test_path = "/emulation/subpath"
        expected_base = Path("/emulation/base")
        expected_result = expected_base / "subpath"

        self.mock_config_manager.get_path.return_value = expected_base

        result = self.resolver._resolve_by_pattern(test_path)

        self.assertEqual(result, expected_result)

    def test_resolve_multiple_paths(self):
        """Test resolving multiple paths at once."""
        paths = ["/path1", "/path2", "/path3"]

        with patch.object(self.resolver, "resolve_path") as mock_resolve:
            mock_resolve.side_effect = [
                PathResolutionResult("/path1", Path("/resolved1"), True),
                PathResolutionResult("/path2", Path("/resolved2"), True),
                PathResolutionResult("/path3", None, False, error_message="Failed"),
            ]

            results = self.resolver.resolve_multiple_paths(paths)

            self.assertEqual(len(results), 3)
            self.assertTrue(results[0].is_valid)
            self.assertTrue(results[1].is_valid)
            self.assertFalse(results[2].is_valid)

    def test_get_alternative_paths(self):
        """Test getting alternative paths."""
        original_path = "/test/file.txt"

        # Mock path type iteration
        mock_paths = {
            PathType.EMULATION: Path("/emulation"),
            PathType.TOOLS: Path("/tools"),
            PathType.BASE: Path("/base"),
        }

        def mock_get_path(path_type):
            path = mock_paths.get(path_type, Path("/default"))
            path.exists = Mock(return_value=True)
            return path

        self.mock_config_manager.get_path.side_effect = mock_get_path

        alternatives = self.resolver.get_alternative_paths(original_path)

    @patch("utils.file_utils.FileUtils.read_text")
    @patch("utils.path_utils.PathUtils.file_exists")
    @patch("utils.path_utils.PathUtils.directory_exists")
    def test_validate_path_accessibility_file(
        self, mock_dir_exists, mock_file_exists, mock_read
    ):
        """Test path accessibility validation for files."""
        test_path = "/test/file.txt"

        mock_file_exists.return_value = True
        mock_dir_exists.return_value = False
        mock_read.return_value = "test content"

        with patch(
            "utils.path_utils.PathUtils.normalize_path", return_value=Path(test_path)
        ):
            is_accessible, message = self.resolver.validate_path_accessibility(
                test_path
            )

            self.assertTrue(is_accessible)
            self.assertEqual(message, "Path is accessible")

    @patch("utils.file_utils.FileUtils.write_text")
    @patch("utils.file_utils.FileUtils.delete_file")
    @patch("utils.path_utils.PathUtils.file_exists")
    @patch("utils.path_utils.PathUtils.directory_exists")
    def test_validate_path_accessibility_directory(
        self, mock_dir_exists, mock_file_exists, mock_delete, mock_write
    ):
        """Test path accessibility validation for directories."""
        test_path = "/test/directory"

        mock_file_exists.return_value = False
        mock_dir_exists.return_value = True

        with patch(
            "utils.path_utils.PathUtils.normalize_path", return_value=Path(test_path)
        ):
            is_accessible, message = self.resolver.validate_path_accessibility(
                test_path
            )

            self.assertTrue(is_accessible)
            self.assertEqual(message, "Path is accessible")

    def test_convert_hardcoded_path_success(self):
        """Test converting hardcoded path successfully."""
        hardcoded_path = "F:\\Hardcoded\\Path"
        resolved_path = Path("/resolved/path")

        with patch.object(self.resolver, "resolve_path") as mock_resolve:
            mock_resolve.return_value = PathResolutionResult(
                hardcoded_path, resolved_path, True
            )

            result = self.resolver.convert_hardcoded_path(hardcoded_path)

            self.assertEqual(result, str(resolved_path))

    def test_convert_hardcoded_path_failure(self):
        """Test converting hardcoded path with failure."""
        hardcoded_path = "F:\\Invalid\\Path"

        with patch.object(self.resolver, "resolve_path") as mock_resolve:
            mock_resolve.return_value = PathResolutionResult(
                hardcoded_path, None, False, error_message="Failed"
            )

            result = self.resolver.convert_hardcoded_path(hardcoded_path)

            self.assertEqual(result, hardcoded_path)
            self.mock_logger.warning.assert_called_once()

    @patch("utils.file_utils.FileUtils.get_file_size")
    @patch("utils.path_utils.PathUtils.file_exists")
    @patch("utils.path_utils.PathUtils.directory_exists")
    def test_get_path_info(self, mock_dir_exists, mock_file_exists, mock_get_size):
        """Test getting comprehensive path information."""
        test_path = "/test/file.txt"
        path_obj = Path(test_path)

        mock_file_exists.return_value = True
        mock_dir_exists.return_value = False
        mock_get_size.return_value = 1024

        with (
            patch("utils.path_utils.PathUtils.normalize_path", return_value=path_obj),
            patch.object(
                self.resolver,
                "validate_path_accessibility",
                return_value=(True, "Accessible"),
            ),
        ):

            info = self.resolver.get_path_info(test_path)

            self.assertEqual(info["original"], test_path)
            self.assertTrue(info["exists"])
            self.assertTrue(info["is_file"])
            self.assertFalse(info["is_dir"])
            self.assertTrue(info["accessible"])
            self.assertEqual(info["size_bytes"], 1024)


class TestGlobalFunctions(unittest.TestCase):
    """Test global convenience functions."""

    @patch("config.path_resolver.PathResolver")
    def test_get_path_resolver_singleton(self, mock_resolver_class):
        """Test that get_path_resolver returns singleton instance."""
        # Clear global instance
        import config.path_resolver

        config.path_resolver._path_resolver = None

        mock_instance = Mock()
        mock_resolver_class.return_value = mock_instance

        # First call should create instance
        resolver1 = get_path_resolver()
        self.assertEqual(resolver1, mock_instance)

        # Second call should return same instance
        resolver2 = get_path_resolver()
        self.assertEqual(resolver2, mock_instance)

        # Should only create instance once
        mock_resolver_class.assert_called_once()

    @patch("config.path_resolver.get_path_resolver")
    def test_resolve_path_convenience(self, mock_get_resolver):
        """Test resolve_path convenience function."""
        mock_resolver = Mock()
        mock_get_resolver.return_value = mock_resolver

        test_path = "/test/path"
        expected_result = PathResolutionResult(test_path, Path("/resolved"), True)
        mock_resolver.resolve_path.return_value = expected_result

        result = resolve_path(test_path)

        self.assertEqual(result, expected_result)
        mock_resolver.resolve_path.assert_called_once_with(
            test_path, PathResolutionStrategy.AUTO
        )

    @patch("config.path_resolver.get_path_resolver")
    def test_convert_hardcoded_path_convenience(self, mock_get_resolver):
        """Test convert_hardcoded_path convenience function."""
        mock_resolver = Mock()
        mock_get_resolver.return_value = mock_resolver

        hardcoded_path = "F:\\Hardcoded"
        expected_result = "/resolved/path"
        mock_resolver.convert_hardcoded_path.return_value = expected_result

        result = convert_hardcoded_path(hardcoded_path)

        self.assertEqual(result, expected_result)
        mock_resolver.convert_hardcoded_path.assert_called_once_with(hardcoded_path)


if __name__ == "__main__":
    unittest.main()