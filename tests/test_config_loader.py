"""Tests for ConfigLoader adapter."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel, ValidationError

from adapters.config_loader import ConfigCache, ConfigLoader, ConfigurationError
from domain.models import AppConfig


class TestModel(BaseModel):
    """Test model for configuration testing."""
    name: str
    value: int
    enabled: bool = True


class TestConfigCache:
    """Test cases for ConfigCache."""

    def test_cache_init(self):
        """Test cache initialization."""
        cache = ConfigCache()
        assert cache.default_ttl == 300
        
        cache_custom = ConfigCache(default_ttl_seconds=600)
        assert cache_custom.default_ttl == 600

    def test_cache_set_get(self):
        """Test basic cache set and get operations."""
        cache = ConfigCache()
        test_data = {"key": "value"}
        
        # Test set and get
        cache.set("test_key", test_data)
        result = cache.get("test_key")
        assert result == test_data
        
        # Test non-existent key
        assert cache.get("non_existent") is None

    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        import time
        cache = ConfigCache()
        test_data = {"key": "value"}
        
        # Set with very short TTL
        cache.set("test_key", test_data, ttl=1)
        
        # Should still be available immediately
        result = cache.get("test_key")
        assert result == test_data
        
        # Wait for expiration and check again
        time.sleep(1.1)
        result = cache.get("test_key")
        assert result is None

    def test_cache_invalidate(self):
        """Test cache invalidation."""
        cache = ConfigCache()
        test_data = {"key": "value"}
        
        cache.set("test_key", test_data)
        assert cache.get("test_key") == test_data
        
        cache.invalidate("test_key")
        assert cache.get("test_key") is None

    def test_cache_clear(self):
        """Test cache clear functionality."""
        cache = ConfigCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_stats(self):
        """Test cache statistics."""
        import time
        cache = ConfigCache()
        
        # Empty cache
        stats = cache.get_stats()
        assert stats["total_entries"] == 0
        assert stats["active_entries"] == 0
        
        # Add some entries
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=1)  # Will expire
        
        # Check immediately - both should be active
        stats = cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        
        # Wait for expiration
        time.sleep(1.1)
        stats = cache.get_stats()
        assert stats["total_entries"] == 2
        assert stats["expired_entries"] == 1


class TestConfigLoader:
    """Test cases for ConfigLoader."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary directory for config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_config_data(self):
        """Sample configuration data."""
        return {
            "name": "test_config",
            "value": 42,
            "enabled": True
        }

    @pytest.fixture
    def config_loader(self, temp_config_dir):
        """Create ConfigLoader instance with temporary directory."""
        with patch('adapters.config_loader.PathResolver') as mock_resolver:
            mock_resolver.return_value.resolve_path.return_value = str(temp_config_dir)
            loader = ConfigLoader(base_path=temp_config_dir)
            loader._config_types["test_config.json"] = TestModel
            return loader

    def test_config_loader_init(self, temp_config_dir):
        """Test ConfigLoader initialization."""
        loader = ConfigLoader(base_path=temp_config_dir)
        assert loader.base_path == temp_config_dir
        assert isinstance(loader.cache, ConfigCache)
        assert "config.json" in loader._config_types

    def test_config_loader_init_no_base_path(self):
        """Test ConfigLoader initialization without base path."""
        with patch('adapters.config_loader.PathResolver') as mock_resolver:
            mock_resolver.return_value.resolve_path.return_value = "\\test\\path"
            loader = ConfigLoader()
            assert str(loader.base_path) == "\\test\\path"

    def test_load_config_success(self, config_loader, temp_config_dir, sample_config_data):
        """Test successful configuration loading."""
        # Create test config file
        config_file = temp_config_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(sample_config_data, f)
        
        # Load configuration
        config = config_loader.load_config("test_config.json", TestModel)
        
        assert isinstance(config, TestModel)
        assert config.name == "test_config"
        assert config.value == 42
        assert config.enabled is True

    def test_load_config_file_not_found(self, config_loader):
        """Test loading non-existent configuration file."""
        with pytest.raises(ConfigurationError, match="Failed to load configuration"):
            config_loader.load_config("non_existent.json", TestModel)

    def test_load_config_invalid_json(self, config_loader, temp_config_dir):
        """Test loading configuration with invalid JSON."""
        # Create invalid JSON file
        config_file = temp_config_dir / "invalid.json"
        with open(config_file, 'w') as f:
            f.write("{ invalid json }")
        
        config_loader._config_types["invalid.json"] = TestModel
        
        with pytest.raises(ConfigurationError, match="Failed to load configuration"):
            config_loader.load_config("invalid.json", TestModel)

    def test_load_config_validation_error(self, config_loader, temp_config_dir):
        """Test loading configuration with validation errors."""
        # Create config with missing required field
        invalid_data = {"value": 42}  # Missing 'name' field
        config_file = temp_config_dir / "invalid_config.json"
        with open(config_file, 'w') as f:
            json.dump(invalid_data, f)
        
        config_loader._config_types["invalid_config.json"] = TestModel
        
        with pytest.raises(ConfigurationError, match="Failed to load configuration"):
            config_loader.load_config("invalid_config.json", TestModel)

    def test_load_config_with_cache(self, config_loader, temp_config_dir, sample_config_data):
        """Test configuration loading with caching."""
        # Create test config file
        config_file = temp_config_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(sample_config_data, f)
        
        # Load configuration twice
        config1 = config_loader.load_config("test_config.json", TestModel, use_cache=True)
        config2 = config_loader.load_config("test_config.json", TestModel, use_cache=True)
        
        # Should be the same cached instance
        assert config1 is config2

    def test_load_config_without_cache(self, config_loader, temp_config_dir, sample_config_data):
        """Test configuration loading without caching."""
        # Create test config file
        config_file = temp_config_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(sample_config_data, f)
        
        # Load configuration twice without cache
        config1 = config_loader.load_config("test_config.json", TestModel, use_cache=False)
        config2 = config_loader.load_config("test_config.json", TestModel, use_cache=False)
        
        # Should be different instances
        assert config1 is not config2
        assert config1.name == config2.name  # But same data

    def test_load_config_auto_model_detection(self, config_loader, temp_config_dir):
        """Test automatic model detection based on filename."""
        config_data = {
            "project": "test-project",
            "status": "active",
            "score": 85,
            "base_paths": {
                "drive_root": "C:",
                "emulation_root": "C:/Emulation",
                "roms_root": "C:/Roms",
                "emulators_root": "C:/Emulators",
                "storage_media_root": "C:/Storage",
                "media_root": "C:/Media",
                "emulation_roms_root": "C:/EmulationRoms",
                "frontends_root": "C:/Frontends"
            },
            "config_files": {
                "platform_list_file": "platforms.json",
                "emulator_mapping_file": "emulators.json",
                "variant_mapping_file": "variants.json",
                "frontend_config_file": "frontends.json"
            },
            "metrics": {
                "code": 80,
                "docs": 70
            },
            "functionalities": {
                "total": 10,
                "implemented": 8
            },
            "diagnostic": {
                "document_discrepancies": "None",
                "CI": "Active"
            },
            "finalObservations": "Test observations"
        }
        
        # Use a known config filename that maps to AppConfig
        config_file = temp_config_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)
        
        # Should auto-detect as AppConfig based on filename
        result = config_loader.load_config("config.json")
        assert result is not None
        assert result.project == "test-project"

    def test_reload_config(self, config_loader, temp_config_dir, sample_config_data):
        """Test configuration reloading."""
        # Create test config file
        config_file = temp_config_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(sample_config_data, f)
        
        # Load and cache
        config1 = config_loader.load_config("test_config.json", TestModel)
        
        # Modify file
        modified_data = sample_config_data.copy()
        modified_data["value"] = 100
        with open(config_file, 'w') as f:
            json.dump(modified_data, f)
        
        # Reload should get fresh data
        config2 = config_loader.reload_config("test_config.json", TestModel)
        assert config2.value == 100
        assert config1.value == 42  # Original cached version unchanged

    def test_save_config(self, config_loader, temp_config_dir):
        """Test configuration saving."""
        test_config = TestModel(name="saved_config", value=123)
        
        # Save configuration
        config_loader.save_config("saved_config.json", test_config)
        
        # Verify file was created
        config_file = temp_config_dir / "saved_config.json"
        assert config_file.exists()
        
        # Verify content
        with open(config_file) as f:
            data = json.load(f)
        
        assert data["name"] == "saved_config"
        assert data["value"] == 123
        assert data["enabled"] is True

    def test_save_config_with_backup(self, config_loader, temp_config_dir):
        """Test configuration saving with backup."""
        # Create existing file
        config_file = temp_config_dir / "existing_config.json"
        original_data = {"name": "original", "value": 1}
        with open(config_file, 'w') as f:
            json.dump(original_data, f)
        
        # Save new configuration with backup
        new_config = TestModel(name="updated", value=2)
        config_loader.save_config("existing_config.json", new_config, backup=True)
        
        # Check backup was created
        backup_files = list(temp_config_dir.glob("existing_config.*.bak"))
        assert len(backup_files) == 1
        
        # Verify backup content
        with open(backup_files[0]) as f:
            backup_data = json.load(f)
        assert backup_data == original_data

    def test_list_config_files(self, config_loader, temp_config_dir):
        """Test listing configuration files."""
        # Create some config files
        config_data = {"name": "test", "value": 1}
        
        for filename in ["config.json", "platform_mapping.json"]:
            config_file = temp_config_dir / filename
            with open(config_file, 'w') as f:
                json.dump(config_data, f)
        
        # List files
        files = config_loader.list_config_files()
        
        # Should include all known config types
        assert len(files) == len(config_loader._config_types)
        
        # Check specific files
        config_file_info = next(f for f in files if f["filename"] == "config.json")
        assert config_file_info["exists"] is True
        assert config_file_info["size"] > 0
        assert config_file_info["model_class"] == "AppConfig"

    def test_validate_config_file(self, config_loader, temp_config_dir, sample_config_data):
        """Test configuration file validation."""
        # Create valid config file
        config_file = temp_config_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(sample_config_data, f)
        
        # Validate
        result = config_loader.validate_config_file("test_config.json")
        
        assert result["valid"] is True
        assert result["filename"] == "test_config.json"
        assert result["model_class"] == "TestModel"
        assert len(result["errors"]) == 0

    def test_validate_config_file_invalid(self, config_loader, temp_config_dir):
        """Test validation of invalid configuration file."""
        # Create invalid config file
        invalid_data = {"value": "not_an_int"}  # Wrong type
        config_file = temp_config_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(invalid_data, f)
        
        # Validate
        result = config_loader.validate_config_file("test_config.json")
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_get_cache_stats(self, config_loader):
        """Test getting cache statistics."""
        stats = config_loader.get_cache_stats()
        
        assert "total_entries" in stats
        assert "active_entries" in stats
        assert isinstance(stats["total_entries"], int)

    def test_clear_cache(self, config_loader, temp_config_dir, sample_config_data):
        """Test clearing configuration cache."""
        # Create and load config to populate cache
        config_file = temp_config_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(sample_config_data, f)
        
        config_loader.load_config("test_config.json", TestModel)
        
        # Clear cache
        config_loader.clear_cache()
        
        # Verify cache is empty
        stats = config_loader.get_cache_stats()
        assert stats["total_entries"] == 0

    def test_load_all_configs(self, config_loader, temp_config_dir):
        """Test loading all configurations from directory."""
        # Create a config file with complete AppConfig structure using a known filename
        config_data = {
            "base_paths": {
                "drive_root": "C:",
                "emulation_root": "C:/Emulation",
                "roms_root": "C:/Roms",
                "emulators_root": "C:/Emulators",
                "storage_media_root": "C:/Storage",
                "media_root": "C:/Media",
                "emulation_roms_root": "C:/EmulationRoms",
                "frontends_root": "C:/Frontends"
            },
            "config_files": {
                "platform_list_file": "platforms.json",
                "emulator_mapping_file": "emulators.json",
                "variant_mapping_file": "variants.json",
                "frontend_config_file": "frontends.json"
            },
            "project": "test-project",
            "status": "active",
            "score": 85,
            "metrics": {"code": 80, "docs": 70},
            "functionalities": {"total": 10, "implemented": 8},
            "diagnostic": {"document_discrepancies": "None", "CI": "Active"},
            "finalObservations": "Test observations"
        }
        
        # Create config.json which is a known config type
        config_file = temp_config_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)
        
        all_configs = config_loader.load_all_configs()
        # Should have at least the config.json we created
        assert len(all_configs) >= 1
        # Check if our config was loaded
        assert "config.json" in all_configs
        assert all_configs["config.json"].project == "test-project"

    def test_save_config_without_backup(self, config_loader, temp_config_dir):
        """Test configuration saving without backup."""
        test_config = TestModel(name="no_backup_config", value=456)
        
        # Save configuration without backup
        config_loader.save_config("no_backup_config.json", test_config, backup=False)
        
        # Verify file was created
        config_file = temp_config_dir / "no_backup_config.json"
        assert config_file.exists()
        
        # Verify content
        with open(config_file) as f:
            data = json.load(f)
        
        assert data["name"] == "no_backup_config"
        assert data["value"] == 456

    def test_save_config_validation_disabled(self, config_loader, temp_config_dir):
        """Test configuration saving with validation disabled."""
        test_config = TestModel(name="no_validation", value=789)
        
        # Save configuration without validation
        config_loader.save_config("no_validation.json", test_config, validate=False)
        
        # Verify file was created
        config_file = temp_config_dir / "no_validation.json"
        assert config_file.exists()

    def test_load_config_without_schema_validation(self, config_loader, temp_config_dir, sample_config_data):
        """Test loading configuration without schema validation."""
        # Create test config file
        config_file = temp_config_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(sample_config_data, f)
        
        # Load configuration without validation
        config = config_loader.load_config("test_config.json", TestModel, validate_schema=False)
        
        # Should return raw data
        assert config == sample_config_data

    def test_validate_config_file_not_found(self, config_loader, temp_config_dir):
        """Test validation of non-existent configuration file."""
        # First register a model class for the file
        config_loader._config_types["non_existent.json"] = TestModel
        
        result = config_loader.validate_config_file("non_existent.json")
        
        assert result["valid"] is False
        assert "File not found" in result["errors"][0]

    def test_validate_config_file_no_model_class(self, config_loader):
        """Test validation of file with no defined model class."""
        result = config_loader.validate_config_file("unknown_config.json")
        
        assert result["valid"] is False
        assert "No model class defined" in result["errors"][0]

    def test_load_raw_config_non_dict(self, config_loader, temp_config_dir):
        """Test loading configuration that is not a JSON object."""
        # Create config file with array instead of object
        config_file = temp_config_dir / "array_config.json"
        with open(config_file, 'w') as f:
            json.dump(["not", "an", "object"], f)
        
        config_loader._config_types["array_config.json"] = TestModel
        
        with pytest.raises(ConfigurationError, match="Failed to load configuration"):
            config_loader.load_config("array_config.json", TestModel)

    def test_create_backup_failure(self, config_loader, temp_config_dir):
        """Test backup creation failure handling."""
        # Create existing file
        config_file = temp_config_dir / "backup_test.json"
        with open(config_file, 'w') as f:
            json.dump({"test": "data"}, f)
        
        # Mock shutil.copy2 to raise an exception
        with patch('shutil.copy2', side_effect=OSError("Permission denied")):
            test_config = TestModel(name="backup_fail", value=999)
            
            with pytest.raises(ConfigurationError, match="Failed to save configuration"):
                config_loader.save_config("backup_test.json", test_config, backup=True)