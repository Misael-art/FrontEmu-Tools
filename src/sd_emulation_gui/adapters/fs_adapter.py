"""
File System Adapter

This adapter provides safe file system operations with atomic operations,
backup capabilities, and proper error handling for Windows environments.
"""

import hashlib
import logging
import os
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

# Import the new path configuration system
try:
    from meta.config.path_config import PathConfigManager
    from path_resolver import PathResolver
except ImportError:
    # Fallback imports
    class PathConfigManager:
        def __init__(self):
            pass
    class PathResolver:
        def __init__(self):
            pass


class FileSystemError(Exception):
    """File system operation error."""

    pass


class AtomicOperation:
    """Context manager for atomic file operations."""

    def __init__(self, target_path: Path, fs_adapter: "FileSystemAdapter"):
        """
        Initialize atomic operation.

        Args:
            target_path: Target file path
            fs_adapter: FileSystemAdapter instance
        """
        self.target_path = target_path
        self.fs_adapter = fs_adapter
        self.temp_path: Path | None = None
        self.backup_path: Path | None = None

    def __enter__(self) -> Path:
        """Enter atomic operation context."""
        # Create temporary file in same directory as target
        self.temp_path = self.target_path.with_suffix(".tmp")
        return self.temp_path

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit atomic operation context."""
        if exc_type is None:
            # Success - move temp file to target
            if self.temp_path and self.temp_path.exists():
                try:
                    self.temp_path.replace(self.target_path)
                except Exception as e:
                    self.fs_adapter.logger.error(
                        f"Failed to complete atomic operation: {e}"
                    )
                    # Clean up temp file
                    if self.temp_path.exists():
                        self.temp_path.unlink()
                    raise
        else:
            # Error occurred - clean up temp file
            if self.temp_path and self.temp_path.exists():
                try:
                    self.temp_path.unlink()
                except Exception:
                    pass  # Best effort cleanup


class FileSystemAdapter:
    """Safe file system operations adapter."""

    def __init__(self, base_path: str | Path = None):
        """
        Initialize file system adapter.

        Args:
            base_path: Base path for operations (optional, uses dynamic config if not provided)
        """
        # Initialize path configuration system
        self.path_config = PathConfigManager()
        self.path_resolver = PathResolver()

        # Use dynamic path if not provided
        if base_path is None:
            base_path = self.path_config.get_path(
                "base_drive"
            ) or self.path_resolver.resolve_path("base_drive").resolved_path

        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)
        self._lock = Lock()

        # Statistics
        self._stats = {
            "operations_performed": 0,
            "bytes_copied": 0,
            "files_created": 0,
            "directories_created": 0,
            "backups_created": 0,
            "errors_encountered": 0,
        }

    @contextmanager
    def atomic_write(self, file_path: str | Path):
        """
        Context manager for atomic file writing.

        Args:
            file_path: Path to file to write atomically

        Yields:
            Temporary file path for writing
        """
        path = Path(file_path)
        self._ensure_parent_exists(path)

        with AtomicOperation(path, self) as temp_path:
            yield temp_path

    def safe_copy(
        self,
        source: str | Path,
        destination: str | Path,
        create_backup: bool = False,
        preserve_metadata: bool = True,
    ) -> bool:
        """
        Safely copy file with optional backup.

        Args:
            source: Source file path
            destination: Destination file path
            create_backup: Whether to backup destination if it exists
            preserve_metadata: Whether to preserve file metadata

        Returns:
            True if successful, False otherwise
        """
        source_path = Path(source)
        dest_path = Path(destination)

        try:
            with self._lock:
                self._stats["operations_performed"] += 1

            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")

            if not source_path.is_file():
                raise ValueError(f"Source must be a file: {source_path}")

            # Create backup if requested and destination exists
            if create_backup and dest_path.exists():
                backup_path = self._create_backup(dest_path)
                self.logger.debug(f"Created backup: {backup_path}")

            # Ensure destination directory exists
            self._ensure_parent_exists(dest_path)

            # Copy file
            if preserve_metadata:
                shutil.copy2(source_path, dest_path)
            else:
                shutil.copy(source_path, dest_path)

            # Update statistics
            with self._lock:
                self._stats["bytes_copied"] += source_path.stat().st_size
                self._stats["files_created"] += 1

            self.logger.debug(f"Copied file: {source_path} -> {dest_path}")
            return True

        except Exception as e:
            with self._lock:
                self._stats["errors_encountered"] += 1
            self.logger.error(f"Failed to copy file {source_path} -> {dest_path}: {e}")
            return False

    def safe_move(
        self, source: str | Path, destination: str | Path, create_backup: bool = False
    ) -> bool:
        """
        Safely move file with optional backup.

        Args:
            source: Source file path
            destination: Destination file path
            create_backup: Whether to backup destination if it exists

        Returns:
            True if successful, False otherwise
        """
        source_path = Path(source)
        dest_path = Path(destination)

        try:
            with self._lock:
                self._stats["operations_performed"] += 1

            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")

            # Create backup if requested and destination exists
            if create_backup and dest_path.exists():
                backup_path = self._create_backup(dest_path)
                self.logger.debug(f"Created backup: {backup_path}")

            # Ensure destination directory exists
            self._ensure_parent_exists(dest_path)

            # Move file
            shutil.move(str(source_path), str(dest_path))

            with self._lock:
                self._stats["files_created"] += 1

            self.logger.debug(f"Moved file: {source_path} -> {dest_path}")
            return True

        except Exception as e:
            with self._lock:
                self._stats["errors_encountered"] += 1
            self.logger.error(f"Failed to move file {source_path} -> {dest_path}: {e}")
            return False

    def create_directory(
        self, directory_path: str | Path, create_parents: bool = True
    ) -> bool:
        """
        Safely create directory.

        Args:
            directory_path: Directory path to create
            create_parents: Whether to create parent directories

        Returns:
            True if successful, False otherwise
        """
        dir_path = Path(directory_path)

        try:
            with self._lock:
                self._stats["operations_performed"] += 1

            dir_path.mkdir(parents=create_parents, exist_ok=True)

            with self._lock:
                self._stats["directories_created"] += 1

            self.logger.debug(f"Created directory: {dir_path}")
            return True

        except Exception as e:
            with self._lock:
                self._stats["errors_encountered"] += 1
            self.logger.error(f"Failed to create directory {dir_path}: {e}")
            return False

    def create_symlink(
        self,
        source: str | Path,
        link_path: str | Path,
        target_is_directory: bool = False,
    ) -> bool:
        """
        Safely create symbolic link.

        Args:
            source: Source path (target of the symlink)
            link_path: Path where symlink will be created
            target_is_directory: Whether target is a directory

        Returns:
            True if successful, False otherwise
        """
        source_path = Path(source)
        link_path_obj = Path(link_path)

        try:
            with self._lock:
                self._stats["operations_performed"] += 1

            # Ensure parent directory exists
            self._ensure_parent_exists(link_path_obj)

            # Remove existing link if it exists
            if link_path_obj.exists() or link_path_obj.is_symlink():
                link_path_obj.unlink()

            # Create symlink (Windows-specific handling)
            try:
                link_path_obj.symlink_to(
                    source_path, target_is_directory=target_is_directory
                )
                self.logger.debug(f"Created symlink: {link_path_obj} -> {source_path}")
                return True

            except OSError as e:
                if "privilege not held" in str(e).lower():
                    # Try junction point for directories on Windows
                    if target_is_directory:
                        return self._create_junction(source_path, link_path_obj)
                    else:
                        self.logger.error(
                            f"Symlink creation failed (insufficient privileges): {e}"
                        )
                        return False
                else:
                    raise

        except Exception as e:
            with self._lock:
                self._stats["errors_encountered"] += 1
            self.logger.error(
                f"Failed to create symlink {link_path_obj} -> {source_path}: {e}"
            )
            return False

    def _create_junction(self, source: Path, link_path: Path) -> bool:
        """Create junction point on Windows (fallback for symlinks)."""
        try:
            import subprocess

            # Use mklink command to create junction
            cmd = ["mklink", "/J", str(link_path), str(source)]
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.debug(f"Created junction: {link_path} -> {source}")
                return True
            else:
                self.logger.error(f"Junction creation failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to create junction: {e}")
            return False

    def delete_file(self, file_path: str | Path, create_backup: bool = True) -> bool:
        """
        Safely delete file with optional backup.

        Args:
            file_path: File path to delete
            create_backup: Whether to create backup before deletion

        Returns:
            True if successful, False otherwise
        """
        path = Path(file_path)

        try:
            with self._lock:
                self._stats["operations_performed"] += 1

            if not path.exists():
                self.logger.warning(f"File not found for deletion: {path}")
                return True  # Already deleted

            # Create backup if requested
            if create_backup:
                backup_path = self._create_backup(path)
                self.logger.debug(f"Created backup before deletion: {backup_path}")

            # Delete file
            path.unlink()

            self.logger.debug(f"Deleted file: {path}")
            return True

        except Exception as e:
            with self._lock:
                self._stats["errors_encountered"] += 1
            self.logger.error(f"Failed to delete file {path}: {e}")
            return False

    def delete_directory(
        self,
        directory_path: str | Path,
        recursive: bool = False,
        create_backup: bool = True,
    ) -> bool:
        """
        Safely delete directory with optional backup.

        Args:
            directory_path: Directory path to delete
            recursive: Whether to delete recursively
            create_backup: Whether to create backup before deletion

        Returns:
            True if successful, False otherwise
        """
        dir_path = Path(directory_path)

        try:
            with self._lock:
                self._stats["operations_performed"] += 1

            if not dir_path.exists():
                self.logger.warning(f"Directory not found for deletion: {dir_path}")
                return True  # Already deleted

            # Create backup if requested
            if create_backup and dir_path.is_dir():
                backup_path = self._create_directory_backup(dir_path)
                self.logger.debug(f"Created backup before deletion: {backup_path}")

            # Delete directory
            if recursive:
                shutil.rmtree(dir_path)
            else:
                dir_path.rmdir()  # Only works if empty

            self.logger.debug(f"Deleted directory: {dir_path}")
            return True

        except Exception as e:
            with self._lock:
                self._stats["errors_encountered"] += 1
            self.logger.error(f"Failed to delete directory {dir_path}: {e}")
            return False

    def calculate_checksum(
        self, file_path: str | Path, algorithm: str = "sha256"
    ) -> str | None:
        """
        Calculate file checksum.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm to use

        Returns:
            Hexadecimal checksum string or None if error
        """
        path = Path(file_path)

        try:
            if not path.exists() or not path.is_file():
                return None

            hash_obj = hashlib.new(algorithm)

            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()

        except Exception as e:
            self.logger.error(f"Failed to calculate checksum for {path}: {e}")
            return None

    def get_file_info(self, file_path: str | Path) -> dict[str, Any] | None:
        """
        Get comprehensive file information.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file information or None if error
        """
        path = Path(file_path)

        try:
            if not path.exists():
                return None

            stat = path.stat()

            info = {
                "path": str(path.absolute()),
                "name": path.name,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "is_file": path.is_file(),
                "is_directory": path.is_dir(),
                "is_symlink": path.is_symlink(),
                "readable": path.stat().st_mode & 0o400 != 0,
                "writable": path.stat().st_mode & 0o200 != 0,
                "executable": path.stat().st_mode & 0o100 != 0,
            }

            # Add checksum for files
            if (
                path.is_file() and stat.st_size < 100 * 1024 * 1024
            ):  # Only for files < 100MB
                info["sha256"] = self.calculate_checksum(path)

            # Add symlink target if applicable
            if path.is_symlink():
                try:
                    info["symlink_target"] = str(path.readlink())
                except Exception:
                    info["symlink_target"] = None

            return info

        except Exception as e:
            self.logger.error(f"Failed to get file info for {path}: {e}")
            return None

    def find_files(
        self,
        directory: str | Path,
        pattern: str = "*",
        recursive: bool = True,
        include_dirs: bool = False,
    ) -> list[Path]:
        """
        Find files matching pattern.

        Args:
            directory: Directory to search
            pattern: Glob pattern to match
            recursive: Whether to search recursively
            include_dirs: Whether to include directories in results

        Returns:
            List of matching file paths
        """
        dir_path = Path(directory)

        try:
            if not dir_path.exists() or not dir_path.is_dir():
                return []

            if recursive:
                matches = list(dir_path.rglob(pattern))
            else:
                matches = list(dir_path.glob(pattern))

            # Filter based on include_dirs
            if not include_dirs:
                matches = [p for p in matches if p.is_file()]

            return sorted(matches)

        except Exception as e:
            self.logger.error(
                f"Failed to find files in {dir_path} with pattern '{pattern}': {e}"
            )
            return []

    def get_disk_usage(self, path: str | Path) -> dict[str, int] | None:
        """
        Get disk usage information.

        Args:
            path: Path to check disk usage for

        Returns:
            Dictionary with usage information or None if error
        """
        try:
            usage = shutil.disk_usage(path)

            return {
                "total_bytes": usage.total,
                "used_bytes": usage.total - usage.free,
                "free_bytes": usage.free,
                "total_gb": usage.total // (1024**3),
                "used_gb": (usage.total - usage.free) // (1024**3),
                "free_gb": usage.free // (1024**3),
                "usage_percentage": (
                    ((usage.total - usage.free) / usage.total) * 100
                    if usage.total > 0
                    else 0
                ),
            }

        except Exception as e:
            self.logger.error(f"Failed to get disk usage for {path}: {e}")
            return None

    def _ensure_parent_exists(self, file_path: Path) -> None:
        """Ensure parent directory exists."""
        parent = file_path.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                self._stats["directories_created"] += 1

    def _create_backup(self, file_path: Path) -> Path:
        """Create backup of file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".{timestamp}.bak")

        # Ensure unique backup name
        counter = 1
        while backup_path.exists():
            backup_path = file_path.with_suffix(f".{timestamp}_{counter}.bak")
            counter += 1

        shutil.copy2(file_path, backup_path)

        with self._lock:
            self._stats["backups_created"] += 1

        return backup_path

    def _create_directory_backup(self, dir_path: Path) -> Path:
        """Create backup of directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = dir_path.with_suffix(f"_backup_{timestamp}")

        # Ensure unique backup name
        counter = 1
        while backup_path.exists():
            backup_path = dir_path.with_suffix(f"_backup_{timestamp}_{counter}")
            counter += 1

        shutil.copytree(dir_path, backup_path)

        with self._lock:
            self._stats["backups_created"] += 1

        return backup_path

    def get_statistics(self) -> dict[str, Any]:
        """Get adapter operation statistics."""
        with self._lock:
            return dict(self._stats)

    def reset_statistics(self) -> None:
        """Reset operation statistics."""
        with self._lock:
            for key in self._stats:
                self._stats[key] = 0