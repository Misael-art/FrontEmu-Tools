from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from meta.config.emulator_mapping import EmulatorConfig, EmulatorMapping


@pytest.fixture
def mock_loader():
    loader = Mock()
    return loader


@pytest.fixture
def mock_resolver():
    resolver = Mock()
    return resolver


class TestEmulatorMapping:
    def setup_method(self):
        self.emulator_mapping = EmulatorMapping()

    @pytest.mark.parametrize(
        "emu_path, emulator_dir",
        [
            ("/custom/emu", "/default/dir"),
            (None, "/project/emu"),
            (r"C:\Emus", r"D:\Emulators"),
        ],
    )
    @patch("config.emulator_mapping.os.getenv")
    @patch("config.emulator_mapping.get_path_resolver")
    @patch("adapters.config_loader.ConfigLoader")
    def test_load_default_mappings_dynamic(
        self, mock_loader_cls, mock_get_resolver, mock_getenv, emu_path, emulator_dir
    ):
        # Setup mocks
        mock_loader = Mock()
        mock_loader_cls.return_value = mock_loader
        mock_resolver = Mock()
        mock_get_resolver.return_value = mock_resolver
        mock_getenv.return_value = emu_path

        mock_resolver.resolve_path.return_value.resolved_path = Path(emulator_dir)

        # Mock raw config from JSON
        raw_configs = {
            "default_sd": {
                "name": "Default SD Emulator",
                "executable": "sd_emulator.exe",
                "supported_extensions": [".img", ".iso", ".bin"],
                "command_template": "{executable} --mount {file_path}",
            },
            "advanced_sd": {
                "name": "Advanced SD Emulator",
                "executable": "advanced_sd.exe",
                "supported_extensions": [".img", ".iso", ".bin", ".raw"],
                "command_template": "{executable} -f {file_path} -m {mount_point}",
            },
        }
        json_path = Path("sd-emulation-gui/config/sd_emulator_mapping.json")
        mock_loader._load_raw_config.return_value = raw_configs

        # Expected base
        expected_base = Path(emu_path) if emu_path else Path(emulator_dir)

        # Create instance to trigger load
        mapping = EmulatorMapping()

        # Assertions
        assert len(mapping._emulators) == 2
        default_config = mapping._emulators["default_sd"]
        assert default_config.name == "Default SD Emulator"
        assert str(default_config.executable_path) == str(
            expected_base / "sd_emulator.exe"
        )
        assert default_config.supported_extensions == [".img", ".iso", ".bin"]
        assert default_config.command_template == "{executable} --mount {file_path}"

        advanced_config = mapping._emulators["advanced_sd"]
        assert str(advanced_config.executable_path) == str(
            expected_base / "advanced_sd.exe"
        )

        # Extension mapping
        assert ".img" in mapping._extension_mapping
        assert mapping._extension_mapping[".img"] == "default_sd"
        assert ".raw" in mapping._extension_mapping
        assert mapping._extension_mapping[".raw"] == "advanced_sd"

        # Mocks called
        mock_loader._load_raw_config.assert_called_once_with(json_path)
        mock_getenv.assert_called_once_with("EMU_PATH", str(Path(emulator_dir)))
        mock_resolver.resolve_path.assert_called_once_with("emulator_dir")

    @pytest.mark.parametrize("emulator_id", ["default_sd", "advanced_sd"])
    def test_get_emulator(self, emulator_id):
        config = self.emulator_mapping.get_emulator(emulator_id)
        assert isinstance(config, EmulatorConfig)
        assert config.name in ["Default SD Emulator", "Advanced SD Emulator"]

    @pytest.mark.parametrize(
        "extension, expected_id",
        [
            (".img", "default_sd"),
            (".iso", "default_sd"),
            (".bin", "default_sd"),
            (".raw", "advanced_sd"),
            (".unknown", None),
        ],
    )
    def test_get_emulator_for_extension(self, extension, expected_id):
        config = self.emulator_mapping.get_emulator_for_extension(extension)
        if expected_id:
            assert config.name in ["Default SD Emulator", "Advanced SD Emulator"]
        else:
            assert config is None

    @pytest.mark.parametrize(
        "emulator_id, path_exists, expected",
        [
            ("default_sd", True, True),
            ("default_sd", False, False),
            ("unknown", None, False),
        ],
    )
    @patch("pathlib.Path.exists")
    def test_validate_emulator_path(
        self, mock_exists, emulator_id, path_exists, expected
    ):
        if path_exists is not None:
            mock_exists.return_value = path_exists
        result = self.emulator_mapping.validate_emulator_path(emulator_id)
        assert result == expected
        if path_exists is not None:
            mock_exists.assert_called_once()

    def test_load_default_mappings_fallback(self):
        with patch("adapters.config_loader.ConfigLoader") as mock_loader_cls:
            mock_loader = Mock()
            mock_loader_cls.return_value = mock_loader
            mock_loader._load_raw_config.side_effect = RuntimeError("Load failed")

            # Expect RuntimeError raised
            with pytest.raises(RuntimeError):
                mapping = EmulatorMapping()
                mapping._load_default_mappings()  # This will be called in init, but test direct
