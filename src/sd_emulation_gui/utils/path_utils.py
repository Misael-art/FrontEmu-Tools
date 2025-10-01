"""
Path Utilities Module

This module provides path manipulation utilities for the SD Emulation GUI application.
"""

import os
import re
from pathlib import Path
from typing import Optional, Any, Dict


class PathUtils:
    """Path manipulation utilities."""

    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize a path keeping forward slashes for tests."""
        if path is None:
            return ""
        normalized = os.path.normpath(path)
        return normalized.replace("\\", "/") if normalized != "." else ""

    @staticmethod
    def ensure_directory_exists(directory: str, *, create_parents: bool = True) -> bool:
        try:
            Path(directory).mkdir(parents=create_parents, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def join_path(*args: str) -> str:
        return PathUtils.join_paths(*args)

    @staticmethod
    def join_paths(*args: str) -> str:
        if not args:
            return ""
        parts = [str(p) for p in args if str(p)]
        joined = os.path.join(*parts) if parts else ""
        return PathUtils.normalize_path(joined)

    @staticmethod
    def get_parent_directory(path: str) -> str:
        return PathUtils.normalize_path(str(Path(path).parent))

    @staticmethod
    def path_exists(path: str) -> bool:
        return os.path.exists(path)

    @staticmethod
    def get_relative_path(target: str | Path, base: str | Path) -> str:
        try:
            rel = Path(target).resolve().relative_to(Path(base).resolve())
            return PathUtils.normalize_path(str(rel))
        except Exception:
            return str(Path(target).resolve())

    @staticmethod
    def expand_path_pattern(pattern: str, directory: str) -> list[str]:
        if not os.path.exists(directory):
            return []
        matches = list(Path(directory).glob(pattern))
        return [PathUtils.normalize_path(str(match)) for match in matches]

    @staticmethod
    def find_common_path(paths: list[str]) -> str:
        if not paths:
            return ""
        try:
            common = os.path.commonpath(paths)
            return PathUtils.normalize_path(common)
        except Exception:
            return ""

    @staticmethod
    def get_path_depth(path: str) -> int:
        if not path:
            return 0
        normalized = PathUtils.normalize_path(path)
        return len([p for p in normalized.split("/") if p])

    @staticmethod
    def get_path_info(path: str | Path) -> dict[str, Any]:
        path_obj = Path(path)
        normalized = PathUtils.normalize_path(str(path_obj))
        exists = path_obj.exists()
        info = {
            "path": normalized,
            "name": path_obj.name,
            "stem": path_obj.stem,
            "suffix": path_obj.suffix,
            "exists": exists,
            "is_file": path_obj.is_file() if exists else False,
            "is_dir": path_obj.is_dir() if exists else False,
        }
        if info["is_file"]:
            stat = path_obj.stat()
            info["size"] = stat.st_size
            info["modified_time"] = stat.st_mtime
        return info

    @staticmethod
    def sanitize_input_path(path: str) -> str:
        if path is None or path == "":
            raise ValueError("Path cannot be empty")
        normalized = path.replace("\\", "/")
        forbidden = ["..", "/etc", "System32", "://"]
        if any(token in normalized for token in forbidden):
            raise ValueError("Dangerous path detected")
        cleaned = re.sub(r"[<>:\\|?*]", "", normalized)
        return PathUtils.normalize_path(cleaned.strip())

    @staticmethod
    def create_backup_path(path: str | Path, suffix: str = ".backup_") -> str:
        path_obj = Path(path)
        counter = 1
        while True:
            suffix_formatted = suffix
            if not suffix.endswith("_"):
                suffix_formatted = f"{suffix}_"
            candidate = path_obj.with_name(f"{path_obj.stem}{suffix_formatted}{counter}{path_obj.suffix}")
            if not candidate.exists():
                return PathUtils.normalize_path(str(candidate))
            counter += 1

    @staticmethod
    def get_safe_filename(name: str, replacement: str = "_") -> str:
        if name is None:
            raise ValueError("Filename cannot be empty")
        if name == "":
            return "unnamed"

        safe = re.sub(r"[<>:\\|?*\"/]", replacement, name)
        safe = safe.strip(" .")
        if not safe:
            return replacement * 8
        return safe

    @staticmethod
    def is_absolute_path(path: str | None) -> bool:
        if not path:
            return False
        return os.path.isabs(path)

    @staticmethod
    def resolve_path_variables(path: str, variables: Dict[str, str]) -> str:
        if not path:
            return ""
        resolved = path
        for key, value in variables.items():
            resolved = resolved.replace(f"{{{key}}}", value)
        return PathUtils.normalize_path(resolved)

    @staticmethod
    def expand_user_path(path: str) -> str:
        return PathUtils.normalize_path(os.path.expanduser(path))

    @staticmethod
    def expand_vars_path(path: str) -> str:
        return PathUtils.normalize_path(os.path.expandvars(path))

    @staticmethod
    def validate_path_security(path: str, allowed_roots: list[str]) -> tuple[bool, str]:
        if not path:
            return False, "Empty path"
        if not allowed_roots:
            return True, "No restrictions"
        normalized = PathUtils.normalize_path(Path(path).resolve())
        for root in allowed_roots:
            root_norm = PathUtils.normalize_path(Path(root).resolve())
            if normalized.startswith(root_norm):
                return True, "Path within allowed roots"
        return False, "Path outside allowed roots"

    @staticmethod
    def directory_exists(path: str) -> bool:
        return os.path.exists(path) and os.path.isdir(path)

    @staticmethod
    def is_directory(path: str | Path) -> bool:
        return os.path.isdir(path)

    @staticmethod
    def read_symlink(path: str | Path) -> str:
        return os.readlink(path)

    @staticmethod
    def list_directories(path: str) -> list[str]:
        if not os.path.isdir(path):
            return []
        return [os.path.join(path, entry) for entry in os.listdir(path)]

    @staticmethod
    def join_path(*args: str | Path) -> str:
        return PathUtils.normalize_path(os.path.join(*map(str, args)))

    @staticmethod
    def is_file(path: str | Path) -> bool:
        """Check if the given path is a file."""
        return os.path.isfile(path)

    @staticmethod
    def is_symlink(path: str | Path) -> bool:
        return os.path.islink(path)

    @staticmethod
    def file_exists(path: str) -> bool:
        return os.path.exists(path) and os.path.isfile(path)

    @staticmethod
    def validate_safe_path(path: str, base_path: str) -> bool:
        try:
            normalized_path = Path(path).resolve()
            normalized_base = Path(base_path).resolve()
            return str(normalized_path).startswith(str(normalized_base))
        except Exception:
            return False

    @staticmethod
    def get_filename(path: str | Path) -> str:
        return Path(path).name
