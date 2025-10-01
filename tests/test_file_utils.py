"""Unit tests for file_utils module.

Tests all file operations and utilities to ensure proper functionality
and error handling across different scenarios.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.file_utils import FileUtils


class TestFileUtils(unittest.TestCase):
    """Test cases for FileUtils class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test_file.txt"
        self.temp_json = Path(self.temp_dir) / "test_file.json"

    def tearDown(self):
        """Clean up after each test method."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_read_json_file_success(self):
        """Test successful JSON file reading."""
        test_data = {"key": "value", "number": 42}

        # Create test JSON file
        with open(self.temp_json, "w") as f:
            json.dump(test_data, f)

        result = FileUtils.read_json_file(self.temp_json)
        self.assertEqual(result, test_data)

    def test_read_json_file_not_found(self):
        """Test JSON file reading when file doesn't exist."""
        non_existent = Path(self.temp_dir) / "non_existent.json"

        # Test with default
        result = FileUtils.read_json_file(non_existent)
        self.assertEqual(result, {})

        # Test with custom default
        custom_default = {"default": True}
        result = FileUtils.read_json_file(non_existent, custom_default)
        self.assertEqual(result, custom_default)

    def test_read_json_file_invalid_json(self):
        """Test JSON file reading with invalid JSON content."""
        # Create file with invalid JSON
        with open(self.temp_json, "w") as f:
            f.write("invalid json content {")

        result = FileUtils.read_json_file(self.temp_json)
        self.assertEqual(result, {})

    def test_write_json_file_success(self):
        """Test successful JSON file writing."""
        test_data = {"key": "value", "list": [1, 2, 3]}

        result = FileUtils.write_json_file(self.temp_json, test_data)
        self.assertTrue(result)

        # Verify content
        with open(self.temp_json) as f:
            written_data = json.load(f)
        self.assertEqual(written_data, test_data)

    def test_write_json_file_create_directory(self):
        """Test JSON file writing with directory creation."""
        nested_path = Path(self.temp_dir) / "nested" / "dir" / "test.json"
        test_data = {"nested": True}

        result = FileUtils.write_json_file(nested_path, test_data)
        self.assertTrue(result)
        self.assertTrue(nested_path.exists())

    def test_read_text_file_success(self):
        """Test successful text file reading."""
        test_content = "Hello, World!\nLine 2"

        with open(self.temp_file, "w", encoding="utf-8") as f:
            f.write(test_content)

        result = FileUtils.read_text_file(self.temp_file)
        self.assertEqual(result, test_content)

    def test_read_text_file_not_found(self):
        """Test text file reading when file doesn't exist."""
        non_existent = Path(self.temp_dir) / "non_existent.txt"

        result = FileUtils.read_text_file(non_existent)
        self.assertEqual(result, "")

        # Test with custom default
        result = FileUtils.read_text_file(non_existent, default="custom default")
        self.assertEqual(result, "custom default")

    def test_write_text_file_success(self):
        """Test successful text file writing."""
        test_content = "Test content\nwith multiple lines"

        result = FileUtils.write_text_file(self.temp_file, test_content)
        self.assertTrue(result)

        # Verify content
        with open(self.temp_file, encoding="utf-8") as f:
            written_content = f.read()
        self.assertEqual(written_content, test_content)

    def test_copy_file_success(self):
        """Test successful file copying."""
        # Create source file
        source_content = "Source file content"
        with open(self.temp_file, "w") as f:
            f.write(source_content)

        destination = Path(self.temp_dir) / "copied_file.txt"

        result = FileUtils.copy_file(self.temp_file, destination)
        self.assertTrue(result)
        self.assertTrue(destination.exists())

        # Verify content
        with open(destination) as f:
            copied_content = f.read()
        self.assertEqual(copied_content, source_content)

    def test_copy_file_create_destination_dir(self):
        """Test file copying with destination directory creation."""
        # Create source file
        with open(self.temp_file, "w") as f:
            f.write("test")

        destination = Path(self.temp_dir) / "new_dir" / "copied_file.txt"

        result = FileUtils.copy_file(self.temp_file, destination)
        self.assertTrue(result)
        self.assertTrue(destination.exists())

    def test_move_file_success(self):
        """Test successful file moving."""
        # Create source file
        source_content = "Source file content"
        with open(self.temp_file, "w") as f:
            f.write(source_content)

        destination = Path(self.temp_dir) / "moved_file.txt"

        result = FileUtils.move_file(self.temp_file, destination)
        self.assertTrue(result)
        self.assertFalse(self.temp_file.exists())
        self.assertTrue(destination.exists())

        # Verify content
        with open(destination) as f:
            moved_content = f.read()
        self.assertEqual(moved_content, source_content)

    def test_delete_file_success(self):
        """Test successful file deletion."""
        # Create file to delete
        with open(self.temp_file, "w") as f:
            f.write("to be deleted")

        self.assertTrue(self.temp_file.exists())

        result = FileUtils.delete_file(self.temp_file)
        self.assertTrue(result)
        self.assertFalse(self.temp_file.exists())

    def test_delete_file_not_exists_safe(self):
        """Test file deletion when file doesn't exist (safe mode)."""
        non_existent = Path(self.temp_dir) / "non_existent.txt"

        result = FileUtils.delete_file(non_existent, safe=True)
        self.assertTrue(result)

    def test_delete_file_not_exists_unsafe(self):
        """Test file deletion when file doesn't exist (unsafe mode)."""
        non_existent = Path(self.temp_dir) / "non_existent.txt"

        result = FileUtils.delete_file(non_existent, safe=False)
        self.assertFalse(result)

    def test_create_backup_success(self):
        """Test successful backup creation."""
        # Create source file
        source_content = "Original content"
        with open(self.temp_file, "w") as f:
            f.write(source_content)

        backup_path = FileUtils.create_backup(self.temp_file)
        self.assertIsNotNone(backup_path)
        self.assertTrue(Path(backup_path).exists())

        # Verify backup content
        with open(backup_path) as f:
            backup_content = f.read()
        self.assertEqual(backup_content, source_content)

    def test_create_backup_custom_dir(self):
        """Test backup creation in custom directory."""
        # Create source file
        with open(self.temp_file, "w") as f:
            f.write("content")

        backup_dir = Path(self.temp_dir) / "backups"
        backup_path = FileUtils.create_backup(self.temp_file, backup_dir)

        self.assertIsNotNone(backup_path)
        self.assertTrue(Path(backup_path).exists())
        self.assertTrue(str(backup_path).startswith(str(backup_dir)))

    def test_create_backup_non_existent_file(self):
        """Test backup creation for non-existent file."""
        non_existent = Path(self.temp_dir) / "non_existent.txt"

        backup_path = FileUtils.create_backup(non_existent)
        self.assertIsNone(backup_path)

    def test_atomic_write_success(self):
        """Test successful atomic file writing."""
        test_content = "Atomic write test content"

        with FileUtils.atomic_write(self.temp_file) as f:
            f.write(test_content)

        self.assertTrue(self.temp_file.exists())

        # Verify content
        with open(self.temp_file) as f:
            written_content = f.read()
        self.assertEqual(written_content, test_content)

    def test_atomic_write_exception_cleanup(self):
        """Test atomic write cleanup on exception."""
        with self.assertRaises(ValueError):
            with FileUtils.atomic_write(self.temp_file) as f:
                f.write("partial content")
                raise ValueError("Test exception")

        # File should not exist after exception
        self.assertFalse(self.temp_file.exists())

    def test_get_file_size_success(self):
        """Test successful file size retrieval."""
        test_content = "Test content for size"
        with open(self.temp_file, "w") as f:
            f.write(test_content)

        size = FileUtils.get_file_size(self.temp_file)
        self.assertEqual(size, len(test_content.encode("utf-8")))

    def test_get_file_size_not_exists(self):
        """Test file size retrieval for non-existent file."""
        non_existent = Path(self.temp_dir) / "non_existent.txt"

        size = FileUtils.get_file_size(non_existent)
        self.assertIsNone(size)

    def test_get_file_modification_time_success(self):
        """Test successful modification time retrieval."""
        with open(self.temp_file, "w") as f:
            f.write("test")

        mtime = FileUtils.get_file_modification_time(self.temp_file)
        self.assertIsNotNone(mtime)
        self.assertIsInstance(mtime, float)

    def test_is_file_newer_comparison(self):
        """Test file age comparison."""
        # Create first file
        file1 = Path(self.temp_dir) / "file1.txt"
        with open(file1, "w") as f:
            f.write("first")

        # Wait a bit and create second file
        import time

        time.sleep(0.1)

        file2 = Path(self.temp_dir) / "file2.txt"
        with open(file2, "w") as f:
            f.write("second")

        # file2 should be newer than file1
        result = FileUtils.is_file_newer(file2, file1)
        self.assertTrue(result)

        # file1 should not be newer than file2
        result = FileUtils.is_file_newer(file1, file2)
        self.assertFalse(result)

    def test_find_files_basic(self):
        """Test basic file finding functionality."""
        # Create test files
        (Path(self.temp_dir) / "test1.txt").write_text("content1")
        (Path(self.temp_dir) / "test2.txt").write_text("content2")
        (Path(self.temp_dir) / "other.log").write_text("log content")

        # Find all txt files
        txt_files = FileUtils.find_files(self.temp_dir, "*.txt", recursive=False)
        self.assertEqual(len(txt_files), 2)

        # Find all files
        all_files = FileUtils.find_files(self.temp_dir, "*", recursive=False)
        self.assertEqual(len(all_files), 3)

    def test_find_files_recursive(self):
        """Test recursive file finding."""
        # Create nested structure
        subdir = Path(self.temp_dir) / "subdir"
        subdir.mkdir()

        (Path(self.temp_dir) / "root.txt").write_text("root")
        (subdir / "nested.txt").write_text("nested")

        # Find recursively
        txt_files = FileUtils.find_files(self.temp_dir, "*.txt", recursive=True)
        self.assertEqual(len(txt_files), 2)

        # Find non-recursively
        txt_files = FileUtils.find_files(self.temp_dir, "*.txt", recursive=False)
        self.assertEqual(len(txt_files), 1)

    def test_find_files_with_filter(self):
        """Test file finding with custom filter."""
        # Create test files with different sizes
        small_file = Path(self.temp_dir) / "small.txt"
        large_file = Path(self.temp_dir) / "large.txt"

        small_file.write_text("small")
        large_file.write_text("large content with more text")

        # Filter for files larger than 10 bytes
        def size_filter(path):
            return path.stat().st_size > 10

        large_files = FileUtils.find_files(
            self.temp_dir, "*.txt", recursive=False, file_filter=size_filter
        )
        self.assertEqual(len(large_files), 1)
        self.assertTrue("large.txt" in large_files[0])

    def test_find_files_non_existent_directory(self):
        """Test file finding in non-existent directory."""
        non_existent = Path(self.temp_dir) / "non_existent"

        files = FileUtils.find_files(non_existent, "*")
        self.assertEqual(files, [])

    @patch("os.chmod")
    def test_ensure_file_permissions_success(self, mock_chmod):
        """Test successful file permission setting."""
        # Create test file
        with open(self.temp_file, "w") as f:
            f.write("test")

        result = FileUtils.ensure_file_permissions(
            self.temp_file, readable=True, writable=True
        )
        self.assertTrue(result)

    def test_ensure_file_permissions_non_existent(self):
        """Test file permission setting for non-existent file."""
        non_existent = Path(self.temp_dir) / "non_existent.txt"

        result = FileUtils.ensure_file_permissions(non_existent)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()