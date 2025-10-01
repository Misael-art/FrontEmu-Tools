"""Tests for config.config_manager module."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from meta.config.config_manager import (
    ConfigFormat,
    ConfigManager,
    ConfigMetadata,
    ConfigScope,
    EnumValidator,
    EnvConfigLoader,
    IniConfigLoader,
    JsonConfigLoader,
    PatternValidator,
    RangeValidator,
    TypeValidator,
    YamlConfigLoader,
)


class TestConfigFormat(unittest.TestCase):
    """Test ConfigFormat enum."""

    def test_config_format_values(self):
        """Test ConfigFormat enum values."""
        self.assertEqual(ConfigFormat.JSON.value, "json")
        self.assertEqual(ConfigFormat.YAML.value, "yaml")
        self.assertEqual(ConfigFormat.INI.value, "ini")
        self.assertEqual(ConfigFormat.ENV.value, "env")


class TestConfigScope(unittest.TestCase):
    """Test ConfigScope enum."""

    def test_config_scope_values(self):
        """Test ConfigScope enum values."""
        self.assertEqual(ConfigScope.GLOBAL.value, "global")
        self.assertEqual(ConfigScope.PROJECT.value, "project")
        self.assertEqual(ConfigScope.USER.value, "user")
        self.assertEqual(ConfigScope.SESSION.value, "session")


class TestConfigMetadata(unittest.TestCase):
    """Test ConfigMetadata class."""

    def test_metadata_creation(self):
        """Test creating configuration metadata."""
        metadata = ConfigMetadata(
            key="test_config",
            scope=ConfigScope.PROJECT,
            format=ConfigFormat.JSON,
            source_file="/path/to/config.json",
        )

        self.assertEqual(metadata.key, "test_config")
        self.assertEqual(metadata.scope, ConfigScope.PROJECT)
        self.assertEqual(metadata.format, ConfigFormat.JSON)
        self.assertEqual(metadata.source_file, "/path/to/config.json")
        self.assertIsNone(metadata.validation_schema)
        self.assertIsNone(metadata.created_at)
        self.assertIsNone(metadata.modified_at)


class TestValidators(unittest.TestCase):
    """Test configuration validators."""

    def test_type_validator_valid(self):
        """Test TypeValidator with valid type."""
        validator = TypeValidator()
        schema = {"type": "str"}

        self.assertTrue(validator.validate("test_key", "string_value", schema))
        self.assertTrue(validator.validate("test_key", 123, {"type": "int"}))
        self.assertTrue(validator.validate("test_key", 3.14, {"type": "float"}))
        self.assertTrue(validator.validate("test_key", True, {"type": "bool"}))

    def test_type_validator_invalid(self):
        """Test TypeValidator with invalid type."""
        validator = TypeValidator()
        schema = {"type": "str"}

        self.assertFalse(validator.validate("test_key", 123, schema))
        self.assertIn("Expected type str", validator.get_error_message())

    def test_range_validator_valid(self):
        """Test RangeValidator with valid range."""
        validator = RangeValidator()
        schema = {"min": 0, "max": 100}

        self.assertTrue(validator.validate("test_key", 50, schema))
        self.assertTrue(validator.validate("test_key", 0, schema))
        self.assertTrue(validator.validate("test_key", 100, schema))

    def test_range_validator_invalid(self):
        """Test RangeValidator with invalid range."""
        validator = RangeValidator()
        schema = {"min": 0, "max": 100}

        self.assertFalse(validator.validate("test_key", -1, schema))
        self.assertFalse(validator.validate("test_key", 101, schema))

    def test_enum_validator_valid(self):
        """Test EnumValidator with valid values."""
        validator = EnumValidator()
        schema = {"enum": ["option1", "option2", "option3"]}

        self.assertTrue(validator.validate("test_key", "option1", schema))
        self.assertTrue(validator.validate("test_key", "option2", schema))

    def test_enum_validator_invalid(self):
        """Test EnumValidator with invalid values."""
        validator = EnumValidator()
        schema = {"enum": ["option1", "option2", "option3"]}

        self.assertFalse(validator.validate("test_key", "invalid_option", schema))

    def test_pattern_validator_valid(self):
        """Test PatternValidator with valid pattern."""
        validator = PatternValidator()
        schema = {"pattern": r"^[a-zA-Z0-9_]+$"}

        self.assertTrue(validator.validate("test_key", "valid_name123", schema))
        self.assertTrue(validator.validate("test_key", "VALID_NAME", schema))

    def test_pattern_validator_invalid(self):
        """Test PatternValidator with invalid pattern."""
        validator = PatternValidator()
        schema = {"pattern": r"^[a-zA-Z0-9_]+$"}

        self.assertFalse(validator.validate("test_key", "invalid-name!", schema))


class TestJsonConfigLoader(unittest.TestCase):
    """Test JsonConfigLoader class."""

    def setUp(self):
        """Set up test fixtures."""
        self.loader = JsonConfigLoader()

    @patch("utils.path_utils.PathUtils.path_exists")
    @patch("utils.file_utils.FileUtils.read_file")
    def test_load_valid_json(self, mock_read, mock_exists):
        """Test loading valid JSON configuration."""
        mock_exists.return_value = True
        mock_read.return_value = '{"key": "value", "number": 42}'

        result = self.loader.load("/test/config.json")

        self.assertEqual(result, {"key": "value", "number": 42})

    @patch("utils.path_utils.PathUtils.path_exists")
    def test_load_nonexistent_file(self, mock_exists):
        """Test loading non-existent file."""
        mock_exists.return_value = False

        result = self.loader.load("/nonexistent/config.json")

        self.assertEqual(result, {})

    @patch("utils.path_utils.PathUtils.path_exists")
    @patch("utils.file_utils.FileUtils.read_file")
    def test_load_invalid_json(self, mock_read, mock_exists):
        """Test loading invalid JSON."""
        mock_exists.return_value = True
        mock_read.return_value = "{invalid json}"

        with self.assertRaises(ValueError) as context:
            self.loader.load("/test/invalid.json")

        self.assertIn("Failed to load JSON config", str(context.exception))

    @patch("utils.file_utils.FileUtils.write_file")
    def test_save_json(self, mock_write):
        """Test saving JSON configuration."""
        config = {"key": "value", "number": 42}

        self.loader.save("/test/config.json", config)

        mock_write.assert_called_once()
        args = mock_write.call_args[0]
        self.assertEqual(args[0], "/test/config.json")
        # Verify JSON content
        saved_data = json.loads(args[1])
        self.assertEqual(saved_data, config)

    def test_get_format(self):
        """Test getting loader format."""
        self.assertEqual(self.loader.get_format(), ConfigFormat.JSON)


class TestYamlConfigLoader(unittest.TestCase):
    """Test YamlConfigLoader class."""

    def setUp(self):
        """Set up test fixtures."""
        self.loader = YamlConfigLoader()

    @patch("utils.path_utils.PathUtils.path_exists")
    @patch("utils.file_utils.FileUtils.read_file")
    @patch("yaml.safe_load")
    def test_load_valid_yaml(self, mock_yaml_load, mock_read, mock_exists):
        """Test loading valid YAML configuration."""
        mock_exists.return_value = True
        mock_read.return_value = "key: value\nnumber: 42"
        mock_yaml_load.return_value = {"key": "value", "number": 42}

        result = self.loader.load("/test/config.yaml")

        self.assertEqual(result, {"key": "value", "number": 42})

    @patch("utils.file_utils.FileUtils.write_file")
    @patch("yaml.dump")
    def test_save_yaml(self, mock_yaml_dump, mock_write):
        """Test saving YAML configuration."""
        config = {"key": "value", "number": 42}
        mock_yaml_dump.return_value = "key: value\nnumber: 42\n"

        self.loader.save("/test/config.yaml", config)

        mock_write.assert_called_once_with(
            "/test/config.yaml", "key: value\nnumber: 42\n"
        )

    def test_get_format(self):
        """Test getting loader format."""
        self.assertEqual(self.loader.get_format(), ConfigFormat.YAML)


class TestIniConfigLoader(unittest.TestCase):
    """Test IniConfigLoader class."""

    def setUp(self):
        """Set up test fixtures."""
        self.loader = IniConfigLoader()

    def test_get_format(self):
        """Test getting loader format."""
        self.assertEqual(self.loader.get_format(), ConfigFormat.INI)


class TestEnvConfigLoader(unittest.TestCase):
    """Test EnvConfigLoader class."""

    def setUp(self):
        """Set up test fixtures."""
        self.loader = EnvConfigLoader()

    @patch("utils.path_utils.PathUtils.path_exists")
    @patch("utils.file_utils.FileUtils.read_file")
    def test_load_valid_env(self, mock_read, mock_exists):
        """Test loading valid ENV configuration."""
        mock_exists.return_value = True
        mock_read.return_value = (
            'KEY1=value1\nKEY2=value2\n# Comment\nKEY3="quoted value"'
        )

        result = self.loader.load("/test/.env")

        expected = {"KEY1": "value1", "KEY2": "value2", "KEY3": "quoted value"}
        self.assertEqual(result, expected)

    @patch("utils.file_utils.FileUtils.write_file")
    def test_save_env(self, mock_write):
        """Test saving ENV configuration."""
        config = {"KEY1": "value1", "KEY2": "value with spaces", "KEY3": "simple"}

        self.loader.save("/test/.env", config)

        mock_write.assert_called_once()
        args = mock_write.call_args[0]
        content = args[1]

        self.assertIn("KEY1=value1", content)
        self.assertIn('KEY2="value with spaces"', content)
        self.assertIn("KEY3=simple", content)

    def test_get_format(self):
        """Test getting loader format."""
        self.assertEqual(self.loader.get_format(), ConfigFormat.ENV)


class TestConfigManager(unittest.TestCase):
    """Test ConfigManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        with (
            patch(
                "utils.path_utils.PathUtils.normalize_path",
                return_value=Path(self.temp_dir),
            ),
            patch("utils.file_utils.FileUtils.ensure_directory_exists"),
            patch("utils.path_utils.PathUtils.path_exists", return_value=True),
            patch("utils.file_utils.FileUtils.list_files", return_value=[]),
        ):

            self.config_manager = ConfigManager(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_creates_config_dir(self):
        """Test that initialization creates config directory."""
        with patch("utils.file_utils.FileUtils.ensure_directory_exists") as mock_ensure:
            with patch("utils.path_utils.PathUtils.path_exists", return_value=False):
                ConfigManager("/new/config/dir")
                mock_ensure.assert_called_once()

    def test_get_default_value(self):
        """Test getting default configuration value."""
        result = self.config_manager.get("nonexistent_key", default="default_value")
        self.assertEqual(result, "default_value")

    def test_set_and_get_value(self):
        """Test setting and getting configuration value."""
        with patch.object(self.config_manager, "save_scope"):
            self.config_manager.set("test_key", "test_value")
            result = self.config_manager.get("test_key")
            self.assertEqual(result, "test_value")

    def test_set_nested_value(self):
        """Test setting nested configuration value."""
        with patch.object(self.config_manager, "save_scope"):
            self.config_manager.set("section.subsection.key", "nested_value")
            result = self.config_manager.get("section.subsection.key")
            self.assertEqual(result, "nested_value")

    def test_get_nested_value(self):
        """Test getting nested configuration value."""
        # Manually set nested structure
        scope_key = ConfigScope.PROJECT.value
        self.config_manager._configs[scope_key] = {
            "section": {"subsection": {"key": "nested_value"}}
        }

        result = self.config_manager.get("section.subsection.key")
        self.assertEqual(result, "nested_value")

    def test_delete_value(self):
        """Test deleting configuration value."""
        with patch.object(self.config_manager, "save_scope"):
            # Set a value first
            self.config_manager.set("test_key", "test_value", save_immediately=False)

            # Delete the value
            result = self.config_manager.delete("test_key")
            self.assertTrue(result)

            # Verify it's gone
            value = self.config_manager.get("test_key", default="not_found")
            self.assertEqual(value, "not_found")

    def test_delete_nonexistent_value(self):
        """Test deleting non-existent configuration value."""
        result = self.config_manager.delete("nonexistent_key")
        self.assertFalse(result)

    @patch("utils.file_utils.FileUtils.get_file_modified_time")
    def test_load_config_file(self, mock_get_time):
        """Test loading configuration file."""
        mock_get_time.return_value = 1234567890

        # Mock loader
        mock_loader = Mock()
        mock_loader.load.return_value = {"key": "value"}
        self.config_manager._loaders[ConfigFormat.JSON] = mock_loader

        self.config_manager._load_config_file(
            "/test/config.json", ConfigScope.PROJECT, ConfigFormat.JSON
        )

        # Verify config was loaded
        scope_key = ConfigScope.PROJECT.value
        self.assertIn(scope_key, self.config_manager._configs)
        self.assertEqual(self.config_manager._configs[scope_key], {"key": "value"})

    def test_save_scope(self):
        """Test saving configuration scope."""
        # Set up test data
        scope_key = ConfigScope.PROJECT.value
        self.config_manager._configs[scope_key] = {"key": "value"}
        self.config_manager._metadata[scope_key] = ConfigMetadata(
            key=scope_key,
            scope=ConfigScope.PROJECT,
            format=ConfigFormat.JSON,
            source_file="/test/config.json",
        )

        # Mock loader
        mock_loader = Mock()
        self.config_manager._loaders[ConfigFormat.JSON] = mock_loader

        self.config_manager.save_scope(ConfigScope.PROJECT)

        mock_loader.save.assert_called_once_with("/test/config.json", {"key": "value"})

    def test_save_all(self):
        """Test saving all configurations."""
        with patch.object(self.config_manager, "save_scope") as mock_save:
            # Set up test data
            scope_key = ConfigScope.PROJECT.value
            self.config_manager._configs[scope_key] = {"key": "value"}
            self.config_manager._metadata[scope_key] = ConfigMetadata(
                key=scope_key, scope=ConfigScope.PROJECT, format=ConfigFormat.JSON
            )

            self.config_manager.save_all()

            mock_save.assert_called_once_with(ConfigScope.PROJECT)

    def test_reload_scope(self):
        """Test reloading configuration scope."""
        with patch.object(self.config_manager, "_load_config_file") as mock_load:
            # Set up metadata
            scope_key = ConfigScope.PROJECT.value
            self.config_manager._metadata[scope_key] = ConfigMetadata(
                key=scope_key,
                scope=ConfigScope.PROJECT,
                format=ConfigFormat.JSON,
                source_file="/test/config.json",
            )

            with patch("utils.path_utils.PathUtils.path_exists", return_value=True):
                self.config_manager.reload_scope(ConfigScope.PROJECT)

                mock_load.assert_called_once_with(
                    "/test/config.json", ConfigScope.PROJECT, ConfigFormat.JSON
                )

    def test_validation_on_set(self):
        """Test validation when setting values."""
        # Mock validator that always fails
        mock_validator = Mock()
        mock_validator.validate.return_value = False
        mock_validator.get_error_message.return_value = "Validation failed"

        self.config_manager._validators = [mock_validator]

        with self.assertRaises(ValueError) as context:
            self.config_manager.set("test_key", "invalid_value")

        self.assertIn("Configuration validation failed", str(context.exception))

    def test_thread_safety(self):
        """Test thread safety of configuration operations."""
        results = []

        def set_config(key, value):
            with patch.object(self.config_manager, "save_scope"):
                self.config_manager.set(key, value, save_immediately=False)
                results.append(self.config_manager.get(key))

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=set_config, args=(f"key_{i}", f"value_{i}")
            )
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all values were set correctly
        self.assertEqual(len(results), 10)
        for i, result in enumerate(results):
            self.assertEqual(result, f"value_{i}")


if __name__ == "__main__":
    unittest.main()