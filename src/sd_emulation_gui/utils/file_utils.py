"""
File Utilities Module

This module provides file system utilities for the SD Emulation GUI application.
"""

import json
import os
import glob
import fnmatch
from pathlib import Path
from typing import Any, Dict, Optional


class FileUtils:
    """File system utilities."""

    @staticmethod
    def read_file(path: str) -> str:
        """Read file content as string."""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def read_text_file(path: str) -> str:
        """Read text file content as string."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""

    @staticmethod
    def write_file(path: str, content: str) -> None:
        """Write content to file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    @staticmethod
    def read_json_file(path: str) -> Dict[str, Any]:
        """Read JSON file and return as dictionary."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def write_json_file(path: str, data: Dict[str, Any]) -> None:
        """Write dictionary to JSON file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def ensure_directory_exists(directory: str) -> bool:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def file_exists(path: str) -> bool:
        """Check if file exists."""
        return os.path.exists(path) and os.path.isfile(path)

    @staticmethod
    def directory_exists(path: str) -> bool:
        """Check if directory exists."""
        return os.path.exists(path) and os.path.isdir(path)

    @staticmethod
    def get_file_size(path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    @staticmethod
    def find_files(directory: str, pattern: str, recursive: bool = False, file_filter=None) -> list[str]:
        """Find files matching pattern."""
        if not os.path.exists(directory):
            return []

        if recursive:
            all_files = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if fnmatch.fnmatch(file, pattern):
                        if file_filter is None or file_filter(file):
                            all_files.append(os.path.join(root, file))
            return all_files
        else:
            search_pattern = os.path.join(directory, pattern)
            matches = glob.glob(search_pattern)
            if file_filter is None:
                return matches
            else:
                return [f for f in matches if file_filter(f)]

    @staticmethod
    def read_text(path: str | Path, *, encoding: str = "utf-8", errors: str = "strict", max_chars: int | None = None) -> str:
        content = FileUtils.read_text_file(str(path))
        if max_chars is not None:
            return content[:max_chars]
        return content

    @staticmethod
    def write_text(path: str | Path, content: str, *, encoding: str = "utf-8", errors: str = "strict") -> bool:
        try:
            FileUtils.write_file(str(path), content)
            return True
        except Exception:
            return False

    @staticmethod
    def delete_file(path: str | Path, safe: bool = True) -> bool:
        try:
            os.remove(path)
            return True
        except FileNotFoundError:
            return safe
        except Exception:
            return False

    @staticmethod
    def read_binary_file(path: str) -> bytes:
        with open(path, 'rb') as f:
            return f.read()

    @staticmethod
    def write_binary_file(path: str, data: bytes) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data)

    @staticmethod
    def get_file_modified_time(path: str) -> float:
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0.0

    @staticmethod
    def list_files(directory: str, pattern: str | None = None, recursive: bool = False) -> list[str]:
        if not os.path.isdir(directory):
            return []
        if pattern is None:
            return [os.path.join(directory, name) for name in os.listdir(directory)]
        if recursive:
            matches = glob.glob(os.path.join(directory, "**", pattern), recursive=True)
        else:
            matches = glob.glob(os.path.join(directory, pattern))
        return matches

    @staticmethod
    def copy_file(source: str, destination: str) -> bool:
        try:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(source, 'rb') as src, open(destination, 'wb') as dst:
                dst.write(src.read())
            return True
        except Exception:
            return False

    @staticmethod
    def move_file(source: str, destination: str) -> bool:
        try:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            os.replace(source, destination)
            return True
        except Exception:
            return False

    @staticmethod
    def copy_directory(source: str, destination: str) -> bool:
        try:
            import shutil

            shutil.copytree(source, destination, dirs_exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def safe_remove(path: str) -> bool:
        try:
            os.remove(path)
            return True
        except FileNotFoundError:
            return True
        except Exception:
            return False
