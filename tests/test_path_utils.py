"""Unit tests for path_utils module.

Tests all path manipulation and resolution functions to ensure proper
functionality across different platforms and scenarios.
"""

import tempfile
import unittest
from pathlib import Path

from utils.path_utils import PathUtils


class TestPathUtils(unittest.TestCase):
    """Test cases for PathUtils class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after each test method."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_normalize_path_basic(self):
        """Test basic path normalization."""
        # Test forward slashes
        result = PathUtils.normalize_path("path/to/file")
        self.assertEqual(result, "path/to/file")

        # Test backslashes
        result = PathUtils.normalize_path("path\\to\\file")
        self.assertEqual(result, "path/to/file")

        # Test mixed separators
        result = PathUtils.normalize_path("path\\to/file")
        self.assertEqual(result, "path/to/file")

    def test_normalize_path_edge_cases(self):
        """Test path normalization edge cases."""
        # Empty path
        result = PathUtils.normalize_path("")
        self.assertEqual(result, "")

        # None path
        result = PathUtils.normalize_path(None)
        self.assertEqual(result, "")

        # Double slashes
        result = PathUtils.normalize_path("path//to//file")
        self.assertEqual(result, "path/to/file")

        # Path object
        result = PathUtils.normalize_path(Path("path/to/file"))
        self.assertEqual(result, "path/to/file")

    def test_resolve_path_variables_basic(self):
        """Test basic path variable resolution."""
        variables = {"HOME": "/home/user", "PROJECT": "myproject"}

        path = "{HOME}/{PROJECT}/file.txt"
        result = PathUtils.resolve_path_variables(path, variables)
        self.assertEqual(result, "/home/user/myproject/file.txt")

    def test_resolve_path_variables_missing(self):
        """Test path variable resolution with missing variables."""
        variables = {"HOME": "/home/user"}

        path = "{HOME}/{MISSING}/file.txt"
        result = PathUtils.resolve_path_variables(path, variables)
        # Missing variable should remain unreplaced
        self.assertEqual(result, "/home/user/{MISSING}/file.txt")

    def test_resolve_path_variables_edge_cases(self):
        """Test path variable resolution edge cases."""
        variables = {"VAR": "value"}

        # Empty path
        result = PathUtils.resolve_path_variables("", variables)
        self.assertEqual(result, "")

        # No variables in path
        result = PathUtils.resolve_path_variables("simple/path", variables)
        self.assertEqual(result, "simple/path")

        # Empty variables dict
        result = PathUtils.resolve_path_variables("{VAR}/path", {})
        self.assertEqual(result, "{VAR}/path")

    def test_get_relative_path_basic(self):
        """Test basic relative path calculation."""
        # Create test directory structure
        base_dir = Path(self.temp_dir) / "base"
        target_dir = base_dir / "subdir" / "target"
        target_dir.mkdir(parents=True)

        target_file = target_dir / "file.txt"
        target_file.write_text("test")

        result = PathUtils.get_relative_path(target_file, base_dir)
        self.assertEqual(result, "subdir/target/file.txt")

    def test_get_relative_path_unrelated(self):
        """Test relative path calculation for unrelated paths."""
        # Create two separate directories
        dir1 = Path(self.temp_dir) / "dir1"
        dir2 = Path(self.temp_dir) / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        file1 = dir1 / "file.txt"
        file1.write_text("test")

        # Should return the original path when not relative
        result = PathUtils.get_relative_path(file1, dir2)
        self.assertTrue(str(file1) in result)

    def test_is_absolute_path_windows(self):
        """Test absolute path detection for Windows paths."""
        # Windows drive letters
        self.assertTrue(PathUtils.is_absolute_path("C:/path/to/file"))
        self.assertTrue(PathUtils.is_absolute_path("D:\\path\\to\\file"))
        self.assertTrue(PathUtils.is_absolute_path("c:/lowercase"))

        # Relative paths
        self.assertFalse(PathUtils.is_absolute_path("relative/path"))
        self.assertFalse(PathUtils.is_absolute_path("./relative"))
        self.assertFalse(PathUtils.is_absolute_path("../parent"))

    def test_is_absolute_path_unix(self):
        """Test absolute path detection for Unix paths."""
        # Unix absolute paths
        self.assertTrue(PathUtils.is_absolute_path("/path/to/file"))
        self.assertTrue(PathUtils.is_absolute_path("/"))

        # Relative paths
        self.assertFalse(PathUtils.is_absolute_path("relative/path"))
        self.assertFalse(PathUtils.is_absolute_path("./relative"))

    def test_is_absolute_path_edge_cases(self):
        """Test absolute path detection edge cases."""
        # Empty string
        self.assertFalse(PathUtils.is_absolute_path(""))

        # None
        self.assertFalse(PathUtils.is_absolute_path(None))

    def test_join_paths_basic(self):
        """Test basic path joining."""
        result = PathUtils.join_paths("base", "sub", "file.txt")
        self.assertEqual(result, "base/sub/file.txt")

    def test_join_paths_mixed_types(self):
        """Test path joining with mixed types."""
        result = PathUtils.join_paths(Path("base"), "sub", Path("file.txt"))
        self.assertEqual(result, "base/sub/file.txt")

    def test_join_paths_edge_cases(self):
        """Test path joining edge cases."""
        # No paths
        result = PathUtils.join_paths()
        self.assertEqual(result, "")

        # Empty paths
        result = PathUtils.join_paths("", "sub", "", "file.txt")
        self.assertEqual(result, "sub/file.txt")

        # All empty
        result = PathUtils.join_paths("", "", "")
        self.assertEqual(result, "")

    def test_ensure_directory_exists_create(self):
        """Test directory creation."""
        new_dir = Path(self.temp_dir) / "new_directory"

        self.assertFalse(new_dir.exists())

        result = PathUtils.ensure_directory_exists(new_dir)
        self.assertTrue(result)
        self.assertTrue(new_dir.exists())
        self.assertTrue(new_dir.is_dir())

    def test_ensure_directory_exists_nested(self):
        """Test nested directory creation."""
        nested_dir = Path(self.temp_dir) / "level1" / "level2" / "level3"

        result = PathUtils.ensure_directory_exists(nested_dir, create_parents=True)
        self.assertTrue(result)
        self.assertTrue(nested_dir.exists())

    def test_ensure_directory_exists_no_parents(self):
        """Test directory creation without parent creation."""
        nested_dir = Path(self.temp_dir) / "nonexistent" / "nested"

        result = PathUtils.ensure_directory_exists(nested_dir, create_parents=False)
        self.assertFalse(result)
        self.assertFalse(nested_dir.exists())

    def test_ensure_directory_exists_already_exists(self):
        """Test directory creation when directory already exists."""
        existing_dir = Path(self.temp_dir) / "existing"
        existing_dir.mkdir()

        result = PathUtils.ensure_directory_exists(existing_dir)
        self.assertTrue(result)
        self.assertTrue(existing_dir.exists())

    def test_get_safe_filename_basic(self):
        """Test basic safe filename generation."""
        # Valid filename
        result = PathUtils.get_safe_filename("valid_filename.txt")
        self.assertEqual(result, "valid_filename.txt")

        # Filename with invalid characters
        result = PathUtils.get_safe_filename('file<>:"/|?*.txt')
        self.assertEqual(result, "file_________.txt")

    def test_get_safe_filename_edge_cases(self):
        """Test safe filename generation edge cases."""
        # Empty filename
        result = PathUtils.get_safe_filename("")
        self.assertEqual(result, "unnamed")

        # Only invalid characters
        result = PathUtils.get_safe_filename('<>:"/|?*')
        self.assertEqual(result, "________")

        # Leading/trailing dots and spaces
        result = PathUtils.get_safe_filename("  ..filename..  ")
        self.assertEqual(result, "filename")

        # Custom replacement character
        result = PathUtils.get_safe_filename("file<>name", "-")
        self.assertEqual(result, "file--name")

    def test_get_path_depth_basic(self):
        """Test basic path depth calculation."""
        self.assertEqual(PathUtils.get_path_depth("file.txt"), 1)
        self.assertEqual(PathUtils.get_path_depth("dir/file.txt"), 2)
        self.assertEqual(PathUtils.get_path_depth("dir1/dir2/dir3/file.txt"), 4)

    def test_get_path_depth_edge_cases(self):
        """Test path depth calculation edge cases."""
        # Empty path
        self.assertEqual(PathUtils.get_path_depth(""), 0)

        # Root path
        self.assertEqual(PathUtils.get_path_depth("/"), 0)

        # Absolute path
        self.assertEqual(PathUtils.get_path_depth("/dir/file"), 2)

        # Path with trailing slash
        self.assertEqual(PathUtils.get_path_depth("dir/subdir/"), 2)

    def test_find_common_path_basic(self):
        """Test basic common path finding."""
        # Create test directory structure
        base_dir = Path(self.temp_dir)
        dir1 = base_dir / "common" / "path1"
        dir2 = base_dir / "common" / "path2"
        dir1.mkdir(parents=True)
        dir2.mkdir(parents=True)

        file1 = dir1 / "file1.txt"
        file2 = dir2 / "file2.txt"
        file1.write_text("test1")
        file2.write_text("test2")

        paths = [str(file1), str(file2)]
        common = PathUtils.find_common_path(paths)

        # Should find the common directory
        self.assertTrue("common" in common)

    def test_find_common_path_edge_cases(self):
        """Test common path finding edge cases."""
        # Empty list
        result = PathUtils.find_common_path([])
        self.assertEqual(result, "")

        # Single path
        single_path = str(Path(self.temp_dir) / "single" / "file.txt")
        result = PathUtils.find_common_path([single_path])
        self.assertTrue("single" in result)

    def test_expand_path_pattern_basic(self):
        """Test basic path pattern expansion."""
        # Create test files
        test_dir = Path(self.temp_dir) / "pattern_test"
        test_dir.mkdir()

        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")
        (test_dir / "other.log").write_text("log")

        # Expand pattern
        txt_files = PathUtils.expand_path_pattern("*.txt", test_dir)
        self.assertEqual(len(txt_files), 2)

        all_files = PathUtils.expand_path_pattern("*", test_dir)
        self.assertEqual(len(all_files), 3)

    def test_expand_path_pattern_non_existent(self):
        """Test path pattern expansion with non-existent directory."""
        non_existent = Path(self.temp_dir) / "non_existent"

        result = PathUtils.expand_path_pattern("*", non_existent)
        self.assertEqual(result, [])

    def test_get_path_info_file(self):
        """Test path info retrieval for files."""
        # Create test file
        test_file = Path(self.temp_dir) / "info_test.txt"
        test_content = "test content for info"
        test_file.write_text(test_content)

        info = PathUtils.get_path_info(test_file)

        self.assertTrue(info["exists"])
        self.assertTrue(info["is_file"])
        self.assertFalse(info["is_dir"])
        self.assertEqual(info["name"], "info_test.txt")
        self.assertEqual(info["stem"], "info_test")
        self.assertEqual(info["suffix"], ".txt")
        self.assertIn("size", info)
        self.assertIn("modified_time", info)

    def test_get_path_info_directory(self):
        """Test path info retrieval for directories."""
        # Create test directory
        test_dir = Path(self.temp_dir) / "info_dir"
        test_dir.mkdir()

        info = PathUtils.get_path_info(test_dir)

        self.assertTrue(info["exists"])
        self.assertFalse(info["is_file"])
        self.assertTrue(info["is_dir"])
        self.assertEqual(info["name"], "info_dir")
        self.assertEqual(info["stem"], "info_dir")
        self.assertEqual(info["suffix"], "")

    def test_get_path_info_non_existent(self):
        """Test path info retrieval for non-existent path."""
        non_existent = Path(self.temp_dir) / "non_existent.txt"

        info = PathUtils.get_path_info(non_existent)

        self.assertFalse(info["exists"])
        self.assertFalse(info["is_file"])
        self.assertFalse(info["is_dir"])
        self.assertEqual(info["name"], "non_existent.txt")
        self.assertNotIn("size", info)

    def test_validate_path_security_allowed(self):
        """Test path security validation for allowed paths."""
        # Create test structure
        allowed_base = Path(self.temp_dir) / "allowed"
        allowed_base.mkdir()

        test_file = allowed_base / "subdir" / "file.txt"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("test")

        is_valid, reason = PathUtils.validate_path_security(
            str(test_file), [str(allowed_base)]
        )

        self.assertTrue(is_valid)
        self.assertIn("within allowed", reason)

    def test_validate_path_security_forbidden(self):
        """Test path security validation for forbidden paths."""
        # Create test structure
        allowed_base = Path(self.temp_dir) / "allowed"
        forbidden_base = Path(self.temp_dir) / "forbidden"
        allowed_base.mkdir()
        forbidden_base.mkdir()

        forbidden_file = forbidden_base / "file.txt"
        forbidden_file.write_text("test")

        is_valid, reason = PathUtils.validate_path_security(
            str(forbidden_file), [str(allowed_base)]
        )

        self.assertFalse(is_valid)
        self.assertIn("outside allowed", reason)

    def test_validate_path_security_edge_cases(self):
        """Test path security validation edge cases."""
        # Empty path
        is_valid, reason = PathUtils.validate_path_security("", [self.temp_dir])
        self.assertFalse(is_valid)
        self.assertIn("Empty path", reason)

        # No restrictions
        is_valid, reason = PathUtils.validate_path_security("/any/path", [])
        self.assertTrue(is_valid)
        self.assertIn("No restrictions", reason)

    def test_create_backup_path_file(self):
        """Test backup path creation for files."""
        original = Path(self.temp_dir) / "document.txt"
        original.write_text("content")

        backup_path = PathUtils.create_backup_path(original)

        self.assertIn("document.backup_", backup_path)
        self.assertTrue(backup_path.endswith(".txt"))
        self.assertNotEqual(str(original), backup_path)

    def test_create_backup_path_directory(self):
        """Test backup path creation for directories."""
        original = Path(self.temp_dir) / "my_directory"
        original.mkdir()

        backup_path = PathUtils.create_backup_path(original)

        self.assertIn("my_directory.backup_", backup_path)
        self.assertNotEqual(str(original), backup_path)

    def test_create_backup_path_custom_suffix(self):
        """Test backup path creation with custom suffix."""
        original = Path(self.temp_dir) / "file.txt"
        original.write_text("content")

        backup_path = PathUtils.create_backup_path(original, ".old")

        self.assertIn("file.old_", backup_path)
        self.assertTrue(backup_path.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()