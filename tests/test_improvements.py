"""Tests for Security and Performance Improvements

Comprehensive tests for the enhanced security features, caching system,
and GUI improvements implemented in the SD Emulation GUI.
"""

import json
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PySide6.QtWidgets import QApplication

# Import components to test
from utils.path_utils import PathUtils
from cache.cache_manager import cache_manager
from gui.components.dashboard_widget import DashboardWidget
from gui.components.setup_wizard import SetupWizard
from adapters.config_loader import ConfigLoader, ConfigurationError


class TestPathUtilsSecurity:
    """Test security enhancements in PathUtils."""

    def test_sanitize_input_path_valid(self):
        """Test sanitization of valid paths."""
        safe_path = PathUtils.sanitize_input_path("valid/path/file.json")
        assert safe_path == "valid/path/file.json"

    def test_sanitize_input_path_dangerous_chars(self):
        """Test rejection of paths with dangerous characters."""
        dangerous_paths = [
            "path/with/..",
            "/absolute/path",
            "path/with/<script>",
            "path/with/|command",
            "path/with/\x00null"
        ]

        for path in dangerous_paths:
            with pytest.raises(ValueError):
                PathUtils.sanitize_input_path(path)

    def test_validate_safe_path_within_base(self):
        """Test safe path validation within base directory."""
        base_path = "/safe/base"
        safe_path = "/safe/base/subdir/file.json"

        is_safe = PathUtils.validate_safe_path(safe_path, base_path)
        assert is_safe is True

    def test_validate_safe_path_outside_base(self):
        """Test rejection of paths outside base directory."""
        base_path = "/safe/base"
        unsafe_path = "/safe/other/file.json"

        is_safe = PathUtils.validate_safe_path(unsafe_path, base_path)
        assert is_safe is False

    def test_normalize_path_security(self):
        """Test security validation in path normalization."""
        # Should reject paths with dangerous patterns
        with pytest.raises(ValueError):
            PathUtils.normalize_path("../../../etc/passwd")

        # Should accept safe paths
        safe_normalized = PathUtils.normalize_path("safe/path/file.json")
        assert safe_normalized == "safe/path/file.json"


class TestCacheManager:
    """Test enhanced cache manager functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = cache_manager

    def teardown_method(self):
        """Clean up test environment."""
        self.cache_manager.clear("all")

    def test_cache_basic_operations(self):
        """Test basic cache operations."""
        key = "test_key"
        data = {"test": "data"}

        # Test set and get
        self.cache_manager.set(key, data, "memory")
        cached_data = self.cache_manager.get(key, "memory")

        assert cached_data == data

    def test_cache_ttl_expiration(self):
        """Test cache TTL functionality."""
        key = "ttl_test"
        data = {"test": "data"}

        # Set with short TTL
        self.cache_manager.set(key, data, "memory", ttl=1)

        # Should be available immediately
        assert self.cache_manager.get(key, "memory") == data

        # Should expire after TTL
        time.sleep(1.1)
        assert self.cache_manager.get(key, "memory") is None

    def test_cache_statistics(self):
        """Test cache statistics."""
        stats = self.cache_manager.get_global_stats()

        assert "memory_cache" in stats
        assert "persistent_cache" in stats
        assert "file_cache" in stats
        assert "path_cache" in stats

    def test_cache_invalidation_pattern(self):
        """Test cache invalidation by pattern."""
        # Set multiple cache entries
        self.cache_manager.set("config:app:settings", {"app": "settings"}, "memory")
        self.cache_manager.set("config:db:connection", {"db": "connection"}, "memory")
        self.cache_manager.set("user:profile:123", {"user": "profile"}, "memory")

        # Invalidate config entries
        invalidated = self.cache_manager.invalidate_pattern("config:")
        assert invalidated == 2

        # Check that config entries are gone
        assert self.cache_manager.get("config:app:settings", "memory") is None
        assert self.cache_manager.get("config:db:connection", "memory") is None

        # User entry should remain
        assert self.cache_manager.get("user:profile:123", "memory") == {"user": "profile"}


class TestConfigLoaderSecurity:
    """Test security enhancements in ConfigLoader."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.loader = ConfigLoader(self.temp_dir)

    def test_load_config_path_validation(self):
        """Test path validation in config loading."""
        # Create a valid config file
        config_data = {"test": "configuration"}
        config_file = Path(self.temp_dir) / "valid_config.json"

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # Should load valid config
        loaded = self.loader.load_config("valid_config.json")
        assert loaded == config_data

    def test_load_config_path_traversal_protection(self):
        """Test protection against path traversal attacks."""
        # Attempt to load file outside base directory should fail
        with pytest.raises(ConfigurationError):
            self.loader.load_config("../../../etc/passwd")

    def test_load_config_large_file_protection(self):
        """Test protection against oversized configuration files."""
        # Create a file larger than 10MB limit
        large_file = Path(self.temp_dir) / "large_config.json"
        with open(large_file, 'w') as f:
            f.write("x" * (11 * 1024 * 1024))  # 11MB

        with pytest.raises(ConfigurationError):
            self.loader.load_config("large_config.json")

    def test_cache_integration(self):
        """Test cache integration in config loading."""
        config_data = {"cached": "configuration"}
        config_file = Path(self.temp_dir) / "cached_config.json"

        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        # First load should hit disk
        start_time = time.time()
        loaded1 = self.loader.load_config("cached_config.json")
        first_load_time = time.time() - start_time

        # Second load should use cache
        start_time = time.time()
        loaded2 = self.loader.load_config("cached_config.json")
        second_load_time = time.time() - start_time

        assert loaded1 == loaded2 == config_data
        assert second_load_time < first_load_time  # Cache should be faster


class TestDashboardWidget:
    """Test dashboard widget improvements."""

    def setup_method(self):
        """Setup test environment."""
        self.app = QApplication.instance() or QApplication([])
        self.widget = DashboardWidget()

    def teardown_method(self):
        """Clean up test environment."""
        if self.widget:
            self.widget.deleteLater()

    def test_tooltips_exist(self):
        """Test that tooltips are properly set on buttons."""
        # Get buttons from widget
        buttons = self.widget.findChildren(type(self.widget.validate_btn))

        for button in buttons:
            assert button.toolTip() is not None
            assert len(button.toolTip()) > 0

    def test_keyboard_shortcuts_setup(self):
        """Test that keyboard shortcuts setup method exists."""
        assert hasattr(self.widget, '_setup_keyboard_shortcuts')
        self.widget._setup_keyboard_shortcuts()  # Should not raise

    def test_config_display(self):
        """Test configuration display functionality."""
        from domain.models import AppConfig

        config = AppConfig(
            application_name="Test App",
            version="1.0.0",
            environment="test"
        )

        self.widget.set_config(config)
        # Widget should handle config without errors

    def test_signals_connected(self):
        """Test that signals are properly connected."""
        # This would require mocking the signal connections
        # For now, just verify the method exists
        assert hasattr(self.widget, '_connect_signals')
        self.widget._connect_signals()  # Should not raise


class TestSetupWizard:
    """Test setup wizard functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.app = QApplication.instance() or QApplication([])
        self.wizard = SetupWizard()

    def teardown_method(self):
        """Clean up test environment."""
        if self.wizard:
            self.wizard.deleteLater()

    def test_wizard_initialization(self):
        """Test wizard initialization."""
        assert self.wizard.windowTitle() == "SD Emulation GUI - Setup Wizard"
        assert self.wizard.currentId() == 0  # Should start at first page

    def test_wizard_pages_created(self):
        """Test that all wizard pages are created."""
        # Should have 6 pages (indices 0-5)
        assert self.wizard.page(0) is not None
        assert self.wizard.page(1) is not None
        assert self.wizard.page(2) is not None
        assert self.wizard.page(3) is not None
        assert self.wizard.page(4) is not None
        assert self.wizard.page(5) is not None

    def test_path_validation(self):
        """Test path validation in wizard."""
        # Navigate to path configuration page
        self.wizard.setCurrentId(1)

        # Test valid path
        self.wizard.base_path_edit.setText("/valid/path")
        assert self.wizard.validateCurrentPage() is True

        # Test empty path
        self.wizard.base_path_edit.setText("")
        assert self.wizard.validateCurrentPage() is False

    def test_emulator_validation(self):
        """Test emulator selection validation."""
        # Navigate to emulator selection page
        self.wizard.setCurrentId(2)

        # Test no selection
        assert self.wizard.validateCurrentPage() is False

        # Test valid selection
        if "RetroArch" in self.wizard.emulator_checkboxes:
            self.wizard.emulator_checkboxes["RetroArch"].setChecked(True)
            assert self.wizard.validateCurrentPage() is True

    def test_frontend_validation(self):
        """Test frontend configuration validation."""
        # Navigate to frontend configuration page
        self.wizard.setCurrentId(3)

        # Test custom frontend without name
        self.wizard.frontend_radios["Custom"].setChecked(True)
        assert self.wizard.validateCurrentPage() is False

        # Test custom frontend with name
        self.wizard.custom_frontend_edit.setText("Custom Frontend")
        assert self.wizard.validateCurrentPage() is True

    def test_configuration_collection(self):
        """Test configuration data collection."""
        # Set up some configuration data
        self.wizard.base_path_edit.setText("/test/path")
        self.wizard.emulators_edit.setText("Emulators")
        self.wizard.roms_edit.setText("ROMs")

        # Select an emulator
        if "Dolphin" in self.wizard.emulator_checkboxes:
            self.wizard.emulator_checkboxes["Dolphin"].setChecked(True)

        # Select frontend
        self.wizard.frontend_radios["None"].setChecked(True)

        # Collect configuration
        self.wizard._collect_configuration()

        # Verify collected data
        assert self.wizard.config_data["base_path"] == "/test/path"
        assert self.wizard.config_data["emulators_dir"] == "Emulators"
        assert self.wizard.config_data["roms_dir"] == "ROMs"
        assert "Dolphin" in self.wizard.config_data["emulators"]
        assert self.wizard.config_data["frontend"] == "None"


class TestPerformanceImprovements:
    """Test performance improvements."""

    def test_cache_performance_gain(self):
        """Test that caching provides performance benefits."""
        # This would require more complex performance testing
        # For now, just test that cache operations are fast
        import time

        data = {"large": "configuration", "with": "lots", "of": "nested", "data": list(range(100))}

        start_time = time.time()
        for i in range(100):
            cache_manager.set(f"perf_test_{i}", data, "memory", ttl=60)

        set_time = time.time() - start_time

        start_time = time.time()
        for i in range(100):
            cache_manager.get(f"perf_test_{i}", "memory")

        get_time = time.time() - start_time

        # Basic sanity checks - operations should be fast
        assert set_time < 1.0  # Should complete in less than 1 second
        assert get_time < 1.0  # Should complete in less than 1 second

    def test_memory_cache_efficiency(self):
        """Test memory cache efficiency."""
        # Test with small cache size to trigger evictions
        small_cache = cache_manager.memory_cache
        original_max_size = small_cache.max_size
        small_cache.max_size = 10

        try:
            # Fill cache
            for i in range(15):
                small_cache.set(f"test_{i}", f"data_{i}")

            # Check that cache size is managed
            assert small_cache.get_stats()["size"] <= 10

        finally:
            # Restore original size
            small_cache.max_size = original_max_size

    def test_file_operation_caching(self):
        """Test file operation caching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"

            # Write file
            test_file.write_text("test content")

            # Test path existence caching
            exists1 = cache_manager.cache_path_exists(str(test_file))
            exists2 = cache_manager.cache_path_exists(str(test_file))

            assert exists1 is True
            assert exists2 is True

            # Test file content caching
            content1 = cache_manager.cache_file_content(str(test_file))
            content2 = cache_manager.cache_file_content(str(test_file))

            assert content1 == "test content"
            assert content2 == "test content"


class TestErrorHandling:
    """Test error handling improvements."""

    def test_path_utils_error_handling(self):
        """Test error handling in PathUtils."""
        # Test invalid path handling
        with pytest.raises(ValueError):
            PathUtils.sanitize_input_path("")

        with pytest.raises(ValueError):
            PathUtils.sanitize_input_path(None)

        # Test dangerous path detection
        dangerous_paths = [
            "/etc/passwd",
            "C:\\Windows\\System32\\config",
            "../../../secret.txt"
        ]

        for path in dangerous_paths:
            with pytest.raises(ValueError):
                PathUtils.sanitize_input_path(path)

    def test_config_loader_error_handling(self):
        """Test error handling in ConfigLoader."""
        with tempfile.TemporaryDirectory() as temp_dir:
            loader = ConfigLoader(temp_dir)

            # Test non-existent file
            with pytest.raises(ConfigurationError):
                loader.load_config("nonexistent.json")

            # Test invalid JSON
            invalid_json_file = Path(temp_dir) / "invalid.json"
            invalid_json_file.write_text("{ invalid json }")

            with pytest.raises(ConfigurationError):
                loader.load_config("invalid.json")

    def test_cache_error_recovery(self):
        """Test cache error recovery."""
        # Test with corrupted cache files
        with tempfile.TemporaryDirectory() as temp_dir:
            corrupted_file = Path(temp_dir) / "corrupted.json"
            corrupted_file.write_text("{ invalid json content }")

            # Should handle error gracefully and return None
            result = cache_manager.get("corrupted_key", "file")
            assert result is None

    def test_gui_error_handling(self):
        """Test error handling in GUI components."""
        app = QApplication.instance() or QApplication([])

        try:
            # Test dashboard with invalid config
            widget = DashboardWidget()

            # Should handle None config gracefully
            widget.set_config(None)

            # Should handle empty config gracefully
            from domain.models import AppConfig
            empty_config = AppConfig()
            widget.set_config(empty_config)

            widget.deleteLater()

        finally:
            if app:
                app.quit()


# Integration tests

class TestIntegration:
    """Integration tests for all improvements."""

    def test_end_to_end_security(self):
        """Test end-to-end security features."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test secure path handling
            safe_path = PathUtils.sanitize_input_path("safe/path")
            assert safe_path == "safe/path"

            # Test unsafe path rejection
            with pytest.raises(ValueError):
                PathUtils.sanitize_input_path("../../../unsafe")

    def test_end_to_end_performance(self):
        """Test end-to-end performance improvements."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test data
            test_data = {"performance": "test", "data": list(range(1000))}

            # Test caching performance
            start_time = time.time()
            for i in range(50):
                cache_manager.set(f"perf_integration_{i}", test_data, "memory", ttl=300)
            set_time = time.time() - start_time

            start_time = time.time()
            for i in range(50):
                cache_manager.get(f"perf_integration_{i}", "memory")
            get_time = time.time() - start_time

            # Should be reasonably fast
            assert set_time < 2.0
            assert get_time < 1.0

    def test_end_to_end_gui_improvements(self):
        """Test end-to-end GUI improvements."""
        app = QApplication.instance() or QApplication([])

        try:
            # Test dashboard widget
            dashboard = DashboardWidget()
            assert dashboard is not None

            # Test setup wizard
            wizard = SetupWizard()
            assert wizard is not None
            assert wizard.currentId() == 0

            # Test wizard navigation
            wizard.setCurrentId(1)  # Path configuration page
            assert wizard.currentId() == 1

            wizard.deleteLater()
            dashboard.deleteLater()

        finally:
            if app:
                app.quit()


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
