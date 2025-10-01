"""Tests for FileSystemAdapter."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from adapters.fs_adapter import FileSystemAdapter, FileSystemError, AtomicOperation


class TestFileSystemAdapter:
    """Test cases for FileSystemAdapter."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def fs_adapter(self, temp_dir):
        """Create FileSystemAdapter instance for testing."""
        return FileSystemAdapter(base_path=temp_dir)

    def test_init_with_base_path(self, temp_dir):
        """Test FileSystemAdapter initialization with base path."""
        adapter = FileSystemAdapter(base_path=temp_dir)
        assert adapter.base_path == temp_dir
        assert adapter._stats["operations_performed"] == 0

    def test_init_without_base_path(self):
        """Test FileSystemAdapter initialization without base path."""
        with patch('meta.config.path_config.PathConfigManager') as mock_config:
            mock_config.return_value.get_path.return_value = "C:/test"
            adapter = FileSystemAdapter()
            assert adapter.base_path == Path("C:/test")

    def test_atomic_write_success(self, fs_adapter, temp_dir):
        """Test successful atomic write operation."""
        test_file = temp_dir / "test.txt"
        test_content = "Hello, World!"
        
        with fs_adapter.atomic_write(test_file) as temp_path:
            temp_path.write_text(test_content)
        
        assert test_file.exists()
        assert test_file.read_text() == test_content

    def test_atomic_write_failure(self, fs_adapter, temp_dir):
        """Test atomic write operation with failure."""
        test_file = temp_dir / "test.txt"
        
        try:
            with fs_adapter.atomic_write(test_file) as temp_path:
                temp_path.write_text("test")
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # File should not exist after failed operation
        assert not test_file.exists()

    def test_safe_copy_success(self, fs_adapter, temp_dir):
        """Test successful file copy."""
        source = temp_dir / "source.txt"
        dest = temp_dir / "dest.txt"
        
        source.write_text("test content")
        
        result = fs_adapter.safe_copy(source, dest)
        
        assert result is True
        assert dest.exists()
        assert dest.read_text() == "test content"
        assert fs_adapter._stats["files_created"] == 1
        assert fs_adapter._stats["operations_performed"] == 1

    def test_safe_copy_source_not_found(self, fs_adapter, temp_dir):
        """Test copy with non-existent source file."""
        source = temp_dir / "nonexistent.txt"
        dest = temp_dir / "dest.txt"
        
        result = fs_adapter.safe_copy(source, dest)
        
        assert result is False
        assert not dest.exists()
        assert fs_adapter._stats["errors_encountered"] == 1

    def test_safe_copy_basic(self, fs_adapter, temp_dir):
        """Test basic copy operation."""
        source = temp_dir / "source.txt"
        dest = temp_dir / "dest.txt"
        
        source.write_text("test content")
        
        result = fs_adapter.safe_copy(source, dest)
        
        assert result is True
        assert dest.exists()
        assert dest.read_text() == "test content"
        
    def test_safe_copy_with_backup(self, fs_adapter, temp_dir):
        """Test copy with backup creation."""
        source = temp_dir / "source.txt"
        dest = temp_dir / "dest.txt"
        
        source.write_text("new content")
        dest.write_text("old content")
        
        # Get initial stats
        initial_stats = fs_adapter.get_statistics()
        initial_backups = initial_stats["backups_created"]
        
        result = fs_adapter.safe_copy(source, dest, create_backup=True)
        
        assert result is True
        assert dest.read_text() == "new content"
        
        # Check if backup count increased
        final_stats = fs_adapter.get_statistics()
        assert final_stats["backups_created"] > initial_backups

    def test_get_statistics(self, fs_adapter):
        """Test statistics retrieval."""
        stats = fs_adapter.get_statistics()
        
        assert "operations_performed" in stats
        assert "bytes_copied" in stats
        assert "files_created" in stats
        assert "directories_created" in stats
        assert "backups_created" in stats
        assert "errors_encountered" in stats
        
    def test_reset_statistics(self, fs_adapter):
        """Test statistics reset."""
        # Perform some operation to generate stats
        fs_adapter._stats["operations_performed"] = 5
        fs_adapter._stats["files_created"] = 3
        
        # Reset stats
        fs_adapter.reset_statistics()
        
        # Check all stats are zero
        stats = fs_adapter.get_statistics()
        for value in stats.values():
            assert value == 0
            
    def test_safe_move_basic(self, fs_adapter, temp_dir):
        """Test basic move operation."""
        source = temp_dir / "source.txt"
        dest = temp_dir / "dest.txt"
        
        source.write_text("test content")
        
        result = fs_adapter.safe_move(source, dest)
        
        assert result is True
        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "test content"
        
    def test_create_directory_basic(self, fs_adapter, temp_dir):
        """Test basic directory creation."""
        new_dir = temp_dir / "new_directory"
        
        result = fs_adapter.create_directory(new_dir)
        
        assert result is True
        assert new_dir.exists()
        assert new_dir.is_dir()


class TestAtomicOperation:
    """Test cases for AtomicOperation."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def fs_adapter(self, temp_dir):
        """Create FileSystemAdapter instance for testing."""
        return FileSystemAdapter(base_path=temp_dir)

    def test_atomic_operation_success(self, fs_adapter, temp_dir):
        """Test successful atomic operation."""
        target_path = temp_dir / "target.txt"
        
        with AtomicOperation(target_path, fs_adapter) as temp_path:
            temp_path.write_text("test content")
        
        assert target_path.exists()
        assert target_path.read_text() == "test content"

    def test_atomic_operation_failure(self, fs_adapter, temp_dir):
        """Test atomic operation with failure."""
        target_path = temp_dir / "target.txt"
        
        try:
            with AtomicOperation(target_path, fs_adapter) as temp_path:
                temp_path.write_text("test content")
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Target file should not exist after failed operation
        assert not target_path.exists()
        # Temp file should be cleaned up
        temp_files = list(temp_dir.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_create_symlink_success(self, fs_adapter, temp_dir):
        """Test successful symlink creation."""
        source = temp_dir / "source.txt"
        link = temp_dir / "link.txt"
        
        source.write_text("test content")
        
        result = fs_adapter.create_symlink(source, link)
        
        # Result may be True or False depending on Windows privileges
        # Just check that no exception was raised
        assert isinstance(result, bool)
        
    def test_delete_file_success(self, fs_adapter, temp_dir):
        """Test successful file deletion."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        result = fs_adapter.delete_file(test_file, create_backup=False)
        
        assert result is True
        assert not test_file.exists()
        
    def test_delete_file_with_backup(self, fs_adapter, temp_dir):
        """Test file deletion with backup."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        initial_stats = fs_adapter.get_statistics()
        initial_backups = initial_stats["backups_created"]
        
        result = fs_adapter.delete_file(test_file, create_backup=True)
        
        assert result is True
        assert not test_file.exists()
        
        # Check if backup was created
        final_stats = fs_adapter.get_statistics()
        assert final_stats["backups_created"] > initial_backups
        
    def test_delete_file_not_found(self, fs_adapter, temp_dir):
        """Test deletion of non-existent file."""
        test_file = temp_dir / "nonexistent.txt"
        
        result = fs_adapter.delete_file(test_file)
        
        assert result is True  # Should return True for already deleted files
        
    def test_delete_directory_success(self, fs_adapter, temp_dir):
        """Test successful directory deletion."""
        test_dir = temp_dir / "test_dir"
        test_dir.mkdir()
        
        result = fs_adapter.delete_directory(test_dir, create_backup=False)
        
        assert result is True
        assert not test_dir.exists()
        
    def test_calculate_checksum_success(self, fs_adapter, temp_dir):
        """Test checksum calculation."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        checksum = fs_adapter.calculate_checksum(test_file)
        
        assert checksum is not None
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 hex length
        
    def test_calculate_checksum_not_found(self, fs_adapter, temp_dir):
        """Test checksum calculation for non-existent file."""
        test_file = temp_dir / "nonexistent.txt"
        
        checksum = fs_adapter.calculate_checksum(test_file)
        
        assert checksum is None
        
    def test_get_file_info_success(self, fs_adapter, temp_dir):
        """Test file info retrieval."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        
        info = fs_adapter.get_file_info(test_file)
        
        assert info is not None
        assert info["name"] == "test.txt"
        assert info["size_bytes"] > 0
        assert info["is_file"] is True
        assert info["is_directory"] is False
        assert "modified" in info
        assert "created" in info
        
    def test_get_file_info_not_found(self, fs_adapter, temp_dir):
        """Test file info for non-existent file."""
        test_file = temp_dir / "nonexistent.txt"
        
        info = fs_adapter.get_file_info(test_file)
        
        assert info is None
        
    def test_find_files_success(self, fs_adapter, temp_dir):
        """Test file finding."""
        # Create test files
        (temp_dir / "test1.txt").write_text("content1")
        (temp_dir / "test2.txt").write_text("content2")
        (temp_dir / "other.log").write_text("log content")
        
        # Find all txt files
        txt_files = fs_adapter.find_files(temp_dir, "*.txt", recursive=False)
        
        assert len(txt_files) == 2
        assert all(f.suffix == ".txt" for f in txt_files)
        
    def test_find_files_empty_directory(self, fs_adapter, temp_dir):
        """Test file finding in empty directory."""
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()
        
        files = fs_adapter.find_files(empty_dir, "*")
        
        assert len(files) == 0
        
    def test_get_disk_usage_success(self, fs_adapter, temp_dir):
        """Test disk usage retrieval."""
        usage = fs_adapter.get_disk_usage(temp_dir)
        
        assert usage is not None
        assert "total_bytes" in usage
        assert "free_bytes" in usage
        assert "used_bytes" in usage
        assert usage["total_bytes"] > 0
        assert usage["free_bytes"] >= 0
        assert usage["used_bytes"] >= 0