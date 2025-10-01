"""
Configuration Loader Adapter

This adapter handles safe loading of configuration files with caching,
validation, and error handling capabilities.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

# Import path management system
import sys
from pathlib import Path

# Add meta/config to path
import sys
from pathlib import Path
meta_config_path = Path(__file__).parent.parent.parent / "meta" / "config"
sys.path.insert(0, str(meta_config_path))

from meta.config.path_config import PathConfigManager
from meta.config.path_resolver import PathResolver
from cache.cache_manager import cache_manager
from utils.path_utils import PathUtils

T = TypeVar("T", bound=BaseModel)


class ConfigCache:
    """Thread-safe configuration cache with expiration."""

    def __init__(self, default_ttl_seconds: int = 300):
        """
        Initialize configuration cache.

        Args:
            default_ttl_seconds: Default time-to-live for cached items
        """
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl_seconds

    def get(self, key: str) -> Any | None:
        """
        Get cached configuration.

        Args:
            key: Cache key

        Returns:
            Cached configuration or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check expiration
            if datetime.now().timestamp() > entry["expires_at"]:
                del self._cache[key]
                return None

            return entry["data"]

    def set(self, key: str, data: Any, ttl: int | None = None) -> None:
        """
        Set cached configuration.

        Args:
            key: Cache key
            data: Configuration data
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl or self.default_ttl
        expires_at = datetime.now().timestamp() + ttl

        with self._lock:
            self._cache[key] = {
                "data": data,
                "expires_at": expires_at,
                "cached_at": datetime.now().timestamp(),
            }

    def invalidate(self, key: str) -> None:
        """
        Invalidate cached configuration.

        Args:
            key: Cache key to invalidate
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        """Clear all cached configurations."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            now = datetime.now().timestamp()
            active_entries = 0
            expired_entries = 0

            for entry in self._cache.values():
                if now <= entry["expires_at"]:
                    active_entries += 1
                else:
                    expired_entries += 1

            return {
                "total_entries": len(self._cache),
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "cache_hit_ratio": getattr(self, "_hit_ratio", 0.0),
            }


class ConfigurationError(Exception):
    """Configuration loading error."""

    pass


class ConfigLoader:
    """Configuration loader with caching and validation."""

    def __init__(self, base_path: str | Path | None = None):
        """
        Initialize configuration loader.

        Args:
            base_path: Base path for configuration files (optional, uses dynamic path if not provided)
        """
        # Initialize path management
        self.path_config_manager = PathConfigManager()
        self.path_resolver = PathResolver()

        # Use dynamic path if not provided
        if base_path is None:
            self.base_path = Path(self.path_resolver.resolve_path("config_base_path").resolved_path)
        else:
            self.base_path = Path(base_path)
        self.cache = ConfigCache()
        self.logger = logging.getLogger(__name__)

        # Configuration type mappings
        self._config_types: dict[str, type[BaseModel]] = {
            "config.json": AppConfig,
            "consolidated_config.json": ConsolidatedConfig,
            "emulator_mapping.json": EmulatorMapping,
            "enterprise_config.json": EnterpriseConfig,
            "frontend_config.json": FrontendGlobalConfig,
            "frontend_emulator_paths.json": FrontendEmulatorPaths,
            "platform_mapping.json": PlatformMapping,
            "variant_mapping.json": VariantMapping,
        }

    def load_config(
        self,
        filename: str,
        model_class: type[T] | None = None,
        use_cache: bool = True,
        validate_schema: bool = True,
    ) -> T:
        """
        Load configuration file with validation, caching, and security checks.

        Args:
            filename: Configuration filename
            model_class: Pydantic model class for validation
            use_cache: Whether to use cached version if available
            validate_schema: Whether to validate against Pydantic schema

        Returns:
            Loaded and validated configuration

        Raises:
            ConfigurationError: If loading or validation fails
        """
        try:
            # Security validation of filename
            safe_filename = PathUtils.sanitize_input_path(filename)
            file_path = self.base_path / safe_filename

            # Validate that the file path is safe
            if not PathUtils.validate_safe_path(file_path, self.base_path):
                raise ConfigurationError(f"Unsafe file path: {file_path}")

            cache_key = f"config:{safe_filename}"

            # Check cache first with enhanced cache manager
            if use_cache:
                cached_config = cache_manager.get(cache_key, "file")
                if cached_config is not None:
                    self.logger.debug(f"Using cached configuration: {filename}")
                    return cached_config

            # Load raw data with security validation
            raw_data = self._load_raw_config_secure(file_path)

            # Determine model class
            if model_class is None:
                model_class = self._config_types.get(filename)
                if model_class is None:
                    raise ConfigurationError(f"No model class defined for {filename}")

            # Validate and create model instance
            if validate_schema and filename != "platform_mapping.json":
                config_instance = self._validate_and_create(
                    raw_data, model_class, filename
                )
            else:
                # For platform_mapping.json, try validation but fallback to raw data
                try:
                    config_instance = self._validate_and_create(
                        raw_data, model_class, filename
                    )
                except Exception:
                    # Fallback to raw data if validation fails
                    config_instance = raw_data

            # Cache the result with enhanced cache manager
            if use_cache:
                cache_manager.set(cache_key, config_instance, "file", ttl=300)  # 5 minutes TTL

            self.logger.info(f"Loaded configuration: {filename}")
            return config_instance

        except Exception as e:
            error_msg = f"Failed to load configuration {filename}: {e}"
            self.logger.error(error_msg, exc_info=True)
            raise ConfigurationError(error_msg) from e

    def _load_raw_config_secure(self, file_path: Path) -> Any:
        """
        Load raw configuration data with security validation.

        Args:
            file_path: Path to configuration file

        Returns:
            Raw configuration data

        Raises:
            ConfigurationError: If file cannot be loaded safely
        """
        try:
            # Validate file path exists and is readable
            if not file_path.exists():
                raise ConfigurationError(f"Configuration file not found: {file_path}")

            if not file_path.is_file():
                raise ConfigurationError(f"Path is not a file: {file_path}")

            # Check file permissions and size
            file_stat = file_path.stat()
            if file_stat.st_size > 10 * 1024 * 1024:  # 10MB limit
                raise ConfigurationError(f"Configuration file too large: {file_path}")

            # Use cache manager for file content loading
            file_content = cache_manager.cache_file_content(str(file_path), ttl=300)

            if file_content is None:
                raise ConfigurationError(f"Could not read configuration file: {file_path}")

            # Parse JSON with security considerations
            try:
                return json.loads(file_content)
            except json.JSONDecodeError as e:
                raise ConfigurationError(f"Invalid JSON in configuration file {file_path}: {e}")

        except (OSError, PermissionError) as e:
            raise ConfigurationError(f"Cannot access configuration file {file_path}: {e}")

    def load_all_configs(self, use_cache: bool = True) -> dict[str, BaseModel]:
        """
        Load all known configuration files.

        Args:
            use_cache: Whether to use cached versions if available

        Returns:
            Dictionary mapping filenames to configuration instances
        """
        configs = {}
        errors = {}

        for filename, model_class in self._config_types.items():
            try:
                configs[filename] = self.load_config(filename, model_class, use_cache)
            except ConfigurationError as e:
                errors[filename] = str(e)
                self.logger.warning(f"Failed to load {filename}: {e}")

        if errors:
            self.logger.warning(
                f"Failed to load {len(errors)} configuration files: {list(errors.keys())}"
            )

        return configs

    def reload_config(self, filename: str, model_class: type[T] | None = None) -> T:
        """
        Force reload configuration, bypassing cache.

        Args:
            filename: Configuration filename
            model_class: Pydantic model class for validation

        Returns:
            Freshly loaded configuration
        """
        # Invalidate cache
        file_path = self.base_path / filename
        self.cache.invalidate(str(file_path))

        # Load fresh configuration
        return self.load_config(filename, model_class, use_cache=False)

    def save_config(
        self,
        filename: str,
        config: BaseModel,
        backup: bool = True,
        validate: bool = True,
    ) -> None:
        """
        Save configuration to file with optional backup.

        Args:
            filename: Configuration filename
            config: Configuration instance to save
            backup: Whether to create backup before saving
            validate: Whether to validate before saving

        Raises:
            ConfigurationError: If saving fails
        """
        file_path = self.base_path / filename

        try:
            # Validate if requested
            if validate:
                # Re-validate the configuration
                if hasattr(config, "model_validate"):
                    config.model_validate(config.model_dump())

            # Create backup if requested
            if backup and file_path.exists():
                self._create_backup(file_path)

            # Prepare data for saving
            if isinstance(config, BaseModel):
                data = config.model_dump(exclude_none=True, by_alias=True)
            else:
                data = config

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first (atomic operation)
            temp_file = file_path.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Move to final location
            temp_file.replace(file_path)

            # Invalidate cache
            self.cache.invalidate(str(file_path))

            self.logger.info(f"Saved configuration: {filename}")

        except Exception as e:
            error_msg = f"Failed to save configuration {filename}: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg) from e

    def _load_raw_config(self, file_path: Path) -> dict[str, Any]:
        """Load raw configuration data from file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError(
                    f"Configuration must be a JSON object, got {type(data)}"
                )

            return data

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to read configuration file: {e}")

    def _validate_and_create(
        self, data: dict[str, Any], model_class: type[T], filename: str
    ) -> T:
        """Validate data against model and create instance."""
        try:
            return model_class(**data)
        except ValidationError as e:
            # Create detailed error message
            error_details = []
            for error in e.errors():
                location = " -> ".join(str(loc) for loc in error["loc"])
                error_details.append(f"{location}: {error['msg']}")

            raise ConfigurationError(
                f"Validation failed for {filename}: {'; '.join(error_details)}"
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create {model_class.__name__} from {filename}: {e}"
            )

    def _create_backup(self, file_path: Path) -> Path:
        """Create backup of configuration file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".{timestamp}.bak")

        try:
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            import shutil

            shutil.copy2(file_path, backup_path)

            self.logger.debug(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.warning(f"Failed to create backup for {file_path}: {e}")
            raise

    def list_config_files(self) -> list[dict[str, Any]]:
        """
        List all configuration files with metadata.

        Returns:
            List of configuration file information
        """
        files = []

        try:
            for filename in self._config_types.keys():
                file_path = self.base_path / filename

                file_info = {
                    "filename": filename,
                    "path": str(file_path),
                    "exists": file_path.exists(),
                    "model_class": self._config_types[filename].__name__,
                    "size": 0,
                    "modified": None,
                    "cached": self.cache.get(str(file_path)) is not None,
                }

                if file_path.exists():
                    stat = file_path.stat()
                    file_info.update(
                        {
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                        }
                    )

                files.append(file_info)

        except Exception as e:
            self.logger.error(f"Failed to list configuration files: {e}")

        return files

    def validate_config_file(self, filename: str) -> dict[str, Any]:
        """
        Validate a configuration file without loading it into cache.

        Args:
            filename: Configuration filename to validate

        Returns:
            Validation result dictionary
        """
        result = {
            "filename": filename,
            "valid": False,
            "errors": [],
            "warnings": [],
            "model_class": None,
        }

        try:
            file_path = self.base_path / filename
            model_class = self._config_types.get(filename)

            if model_class is None:
                result["errors"].append(f"No model class defined for {filename}")
                return result

            result["model_class"] = model_class.__name__

            if not file_path.exists():
                result["errors"].append(f"File not found: {file_path}")
                return result

            # Load and validate
            raw_data = self._load_raw_config(file_path)
            validated_config = self._validate_and_create(
                raw_data, model_class, filename
            )

            result["valid"] = True
            result["warnings"].append("Configuration is valid")

            # Add some basic metrics
            if hasattr(validated_config, "model_dump"):
                data = validated_config.model_dump()
                if isinstance(data, dict):
                    result["field_count"] = len(data)

        except ConfigurationError as e:
            result["errors"].append(str(e))
        except Exception as e:
            result["errors"].append(f"Unexpected error: {e}")

        return result

    def get_cache_stats(self) -> dict[str, Any]:
        """Get configuration cache statistics."""
        return self.cache.get_stats()

    def clear_cache(self) -> None:
        """Clear configuration cache."""
        self.cache.clear()
        self.logger.info("Configuration cache cleared")