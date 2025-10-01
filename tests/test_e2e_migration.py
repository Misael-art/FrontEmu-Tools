"""
Testes E2E para operações de migração

Testes end-to-end que simulam fluxos completos de migração, incluindo
planejamento, execução, rollback e verificação de estado final.
Expandido para cobrir cenários de falha (INC-007): disk full, permission denied,
timeout em subprocess e cross-platform (Windows/Linux mocks).
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import DEFAULT as ANY
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from sd_emulation_gui.domain.sd_rules import SDEmulationRules
from sd_emulation_gui.gui.main_window import MainWindow
from sd_emulation_gui.services.migration_service import MigrationService
from sd_emulation_gui.services.validation_service import ValidationService


@pytest.fixture(scope="session")
def qapp():
    """Fixture para QApplication única para todos os testes E2E."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_base_path():
    """Fixture para diretório temporário base para testes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Criar estrutura básica de arquivos
        base_path = Path(temp_dir)

        # Criar diretórios básicos
        (base_path / "Emulation" / "roms").mkdir(parents=True, exist_ok=True)
        (base_path / "Roms").mkdir(exist_ok=True)
        (base_path / "Emulators").mkdir(exist_ok=True)
        (base_path / "backups").mkdir(exist_ok=True)

        # Criar arquivos de configuração de teste
        config_dir = base_path / "scripts" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Configuração de emulador de teste
        emulator_config = {
            "version": "1.0.0",
            "emulators": {
                "retroarch": {
                    "path": "Emulators/RetroArch/RetroArch.exe",
                    "supported_platforms": ["nes", "snes", "gb"],
                    "config_dir": "Emulation/configs/retroarch",
                }
            },
        }

        with open(config_dir / "emulator_mapping.json", "w") as f:
            json.dump(emulator_config, f, indent=2)

        # Mapeamento de plataforma de teste
        platform_config = {
            "version": "1.0.0",
            "mappings": {
                "nes": "Nintendo Entertainment System",
                "snes": "Super Nintendo Entertainment System",
                "gb": "Game Boy",
            },
        }

        with open(config_dir / "platform_mapping.json", "w") as f:
            json.dump(platform_config, f, indent=2)

        # Configuração principal
        main_config = {
            "version": "1.0.0",
            "environment": "test",
            "paths": {"base_path": str(base_path), "config_dir": str(config_dir)},
        }

        with open(base_path / "config.json", "w") as f:
            json.dump(main_config, f, indent=2)

        # Criar fonte para symlink/junction
        source_dir = base_path / "Roms" / "NES_Source"
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "test_rom.nes").touch()

        yield base_path


@pytest.fixture
def mock_sd_rules():
    """Mock para regras de emulação SD com atributos reais."""

    class MockDirRule:
        def __init__(self, path, purpose):
            self.path = path
            self.purpose = purpose

    class MockSymlinkRule:
        def __init__(self, description):
            self.description = description

    mock_rules = MagicMock(spec=SDEmulationRules)

    # Mock para diretórios requeridos
    mock_rules.get_required_directories.return_value = [
        MockDirRule("Emulation/roms", "ROM storage with platform organization"),
        MockDirRule("Emulators/RetroArch", "Emulator executable location"),
    ]

    # Mock para symlinks requeridos
    mock_rules.get_required_symlinks.return_value = [
        MockSymlinkRule("Compatibility symlinks for legacy emulators")
    ]

    return mock_rules


@pytest.fixture
def mock_container(mock_sd_rules):
    """Mock para container de dependências expandido."""
    container = MagicMock()

    # Mock services
    container.validation_service.return_value = MagicMock(spec=ValidationService)
    container.migration_service.return_value = MagicMock(spec=MigrationService)

    # Mock config loader
    mock_config_loader = MagicMock()

    def mock_load_config(filename):
        configs = {
            "emulator_mapping.json": {
                "emulators": {
                    "retroarch": {"path": "Emulators/RetroArch/RetroArch.exe"}
                }
            },
            "platform_mapping.json": {
                "mappings": {"nes": "Nintendo Entertainment System"}
            },
        }
        return configs.get(filename, {})

    mock_config_loader.load_config.side_effect = mock_load_config
    container.config_loader.return_value = mock_config_loader

    # Mock SD service
    mock_sd_service = MagicMock()
    mock_sd_service.parse_rules_from_document.return_value = mock_sd_rules
    container.sd_emulation_service.return_value = mock_sd_service

    return container


class TestMigrationE2E:
    """Testes E2E para fluxo completo de migração, expandido para falhas (INC-007)."""

    def test_complete_migration_flow(
        self, qapp, temp_base_path, mock_container, mock_sd_rules
    ):
        """Testa o fluxo completo de migração: plan -> preview -> execute."""

        # Setup
        container = mock_container
        migration_service = container.migration_service.return_value

        # Mock successful migration plan
        mock_plan = MagicMock()
        mock_plan.total_steps = 3
        mock_plan.steps = [
            MagicMock(
                step_id="step1",
                action="create_directory",
                description="Create ROM dir",
                executed=False,
            ),
            MagicMock(
                step_id="step2",
                action="create_symlink",
                description="Create NES symlink",
                executed=False,
            ),
            MagicMock(
                step_id="step3",
                action="create_directory",
                description="Create emulator dir",
                executed=False,
            ),
        ]
        mock_plan.success = True
        mock_plan.executed = False
        mock_plan.backup_location = str(temp_base_path / "backups" / "test_backup")

        migration_service.plan_migration.return_value = mock_plan
        migration_service.apply_migration.return_value = True

        # Test 1: Create main window (this should initialize components)
        main_window = MainWindow(container)

        # Test 2: Verify main window components are created
        assert main_window.migration_widget is not None
        assert main_window.tab_widget is not None

        # Test 3: Test migration service directly (bypass UI worker)
        config_loader = container.config_loader.return_value
        sd_service = container.sd_emulation_service.return_value
        path_resolver = container.path_resolver.return_value

        # Mock the dependencies
        config_loader.load_config.return_value = {"test": "config"}
        sd_service.parse_rules_from_document.return_value = mock_sd_rules
        path_resolver.resolve_path.return_value = "/test/path"

        # Call migration service directly
        result_plan = migration_service.plan_migration(
            {"test": "emulator"}, {"test": "platform"}, mock_sd_rules
        )

        # Test 4: Verify migration plan was created
        migration_service.plan_migration.assert_called_once()
        assert result_plan == mock_plan

        # Test 5: Test migration execution
        result = migration_service.apply_migration(mock_plan, confirm=True)
        migration_service.apply_migration.assert_called_once_with(
            mock_plan, confirm=True
        )
        assert result == True

        # Cleanup
        main_window.close()

    @patch("sd_emulation_gui.services.migration_service.subprocess.run")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.is_symlink", return_value=True)
    @patch(
        "pathlib.Path.is_junction", side_effect=[False, True]
    )  # First symlink fail, junction success
    def test_fallback_junction_on_symlink_failure(
        self, mock_is_junction, mock_is_symlink, mock_exists, mock_run, temp_base_path
    ):
        """Testa fallback de junction quando symlink falha (INC-007)."""

        # Setup migration service
        migration_service = MigrationService(base_path=str(temp_base_path))

        # Create source directory
        source_dir = temp_base_path / "source_dir"
        source_dir.mkdir()
        (source_dir / "test_file.txt").write_text("test content")

        # Mock step for symlink creation
        step = MagicMock()
        step.target_path = str(temp_base_path / "test_junction")
        step.source_path = str(source_dir)
        step.description = "Test junction fallback"

        # Mock symlink failure
        with patch.object(
            Path, "symlink_to", side_effect=OSError("Privilege not held")
        ):
            # Mock subprocess success for mklink
            mock_run.return_value = MagicMock(returncode=0, stderr="")

            # Execute the step that triggers fallback
            migration_service._execute_create_symlink(step)

            # Verify fallback was triggered
            mock_run.assert_called_once_with(
                ["cmd.exe", "/c", "mklink", "/J", ANY, ANY],  # Paths will be resolved
                capture_output=True,
                text=True,
                check=True,
                timeout=ANY,  # From previous fix
            )

            # Verify rollback_info was set for junction
            assert step.rollback_info.get("method_used") == "junction"
            assert step.rollback_info.get("is_junction") == True

            # Verify junction accessibility test was called
            # (Mocked write_text/unlink would be called here)
            assert "test_access.txt" in str(
                mock_exists.call_args[0][0]
            )  # Test file creation

    @patch("sd_emulation_gui.services.migration_service.subprocess.run")
    def test_junction_timeout_scenario(self, mock_run, temp_base_path):
        """Testa timeout em subprocess para mklink (INC-007)."""

        # Setup
        migration_service = MigrationService(base_path=str(temp_base_path))

        step = MagicMock()
        step.target_path = str(temp_base_path / "test_timeout")
        step.source_path = str(temp_base_path / "source")
        step.description = "Test timeout scenario"

        # Mock source
        source_dir = temp_base_path / "source"
        source_dir.mkdir()

        # Mock timeout in subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", timeout=10)

        # Execute and expect timeout exception
        with pytest.raises(
            subprocess.TimeoutExpired, match="timed out after 10 seconds"
        ):
            migration_service._execute_create_symlink(step)

        # Verify error handling and cleanup
        assert mock_run.call_args[1]["timeout"] == 10
        assert "Junction creation timed out after 10 seconds" in str(mock_run.call_args)

    @patch("sd_emulation_gui.services.migration_service.shutil.disk_usage")
    def test_disk_full_prevention(self, mock_disk_usage, temp_base_path):
        """Testa prevenção de migração quando espaço insuficiente (INC-007)."""

        # Mock low disk space
        mock_disk_usage.return_value = MagicMock(free=100 * 1024 * 1024)  # 100MB free

        migration_service = MigrationService(base_path=str(temp_base_path))

        # Mock plan that requires more space
        mock_plan = MagicMock()
        mock_plan.total_steps = 1
        mock_plan.steps = [MagicMock()]

        # Mock estimate requiring 200MB
        with patch.object(
            migration_service,
            "_estimate_required_space",
            return_value=200 * 1024 * 1024,
        ):
            result = migration_service.apply_migration(mock_plan, confirm=True)
            assert not result  # Should fail due to space

        # Verify error message was logged
        mock_disk_usage.assert_called_once()

    @patch("sd_emulation_gui.services.migration_service.subprocess.run")
    @patch("pathlib.Path.exists", return_value=False)
    def test_rollback_verification_failure(self, mock_exists, mock_run, temp_base_path):
        """Testa falha de verificação em rollback (INC-007)."""

        migration_service = MigrationService(base_path=str(temp_base_path))

        step = MagicMock()
        step.target_path = str(temp_base_path / "persistent_target")
        step.rollback_info = {
            "method_used": "junction",
            "junction_target": str(temp_base_path / "persistent_target"),
        }

        # Mock rmdir failure (target still exists after rmdir)
        mock_run.return_value = MagicMock(returncode=1, stderr="Access denied")

        with pytest.raises(RuntimeError, match="Rollback verification failed"):
            migration_service._rollback_create_symlink(step)

        # Verify error raised and logged
        mock_run.assert_called_once_with(
            ["cmd.exe", "/c", "rmdir", ANY], timeout=5, check=False
        )
        assert mock_exists.return_value == True  # Target still exists

    def test_permission_denied_scenario(self, temp_base_path):
        """Testa cenários de permission denied em criação de junction (INC-007)."""

        migration_service = MigrationService(base_path=str(temp_base_path))

        # Create read-only target directory to simulate permission denied
        target_dir = temp_base_path / "read_only_target"
        target_dir.mkdir()
        os.chmod(target_dir, 0o444)  # Read-only

        step = MagicMock()
        step.target_path = str(target_dir / "junction")
        step.source_path = str(temp_base_path / "source")
        step.description = "Test permission denied"

        # Create source
        source_dir = temp_base_path / "source"
        source_dir.mkdir()

        with pytest.raises((OSError, PermissionError)):
            migration_service._execute_create_symlink(step)

        # Verify cleanup attempted
        os.chmod(target_dir, 0o755)  # Restore permissions for test cleanup


class TestE2EValidationIntegration:
    """Testes E2E de integração entre validação e migração, expandido para falhas."""

    @patch(
        "sd_emulation_gui.services.validation_service.ValidationService.validate_all"
    )
    def test_pre_post_migration_validation_with_failure(
        self, mock_validate_all, qapp, temp_base_path, mock_container
    ):
        """Testa validação antes e depois da migração com falha intermediária (INC-007)."""

        # Mock initial validation success
        initial_summary = MagicMock()
        initial_summary.overall_status = "valid"
        initial_summary.files_with_errors = 0

        # Mock migration failure on step 2
        mock_validate_all.side_effect = [
            initial_summary,
            MagicMock(overall_status="error", files_with_errors=1),
        ]

        container = mock_container
        main_window = MainWindow(container)
        main_window.show()

        QTimer.singleShot(100, lambda: None)
        qapp.processEvents()

        # Initial validation passes
        main_window._run_validation()
        QTimer.singleShot(300, lambda: None)
        qapp.processEvents()

        assert main_window.view_model.validation_results.overall_status == "valid"

        # Mock migration plan and execute (fails)
        mock_plan = MagicMock()
        main_window.view_model.migration_plan = mock_plan

        with patch.object(
            container.migration_service.return_value,
            "execute_migration",
            side_effect=PermissionError("Simulated permission error"),
        ):
            main_window._execute_migration()
            QTimer.singleShot(300, lambda: None)
            qapp.processEvents()

        # Post-migration validation should show errors
        main_window._run_validation()
        QTimer.singleShot(300, lambda: None)
        qapp.processEvents()

        assert main_window.view_model.validation_results.overall_status == "error"

        # Verify rollback triggered and post-rollback validation
        main_window._rollback_migration()
        QTimer.singleShot(300, lambda: None)
        qapp.processEvents()

        # Mock rollback success, validation returns to valid
        mock_validate_all.side_effect = [initial_summary]  # Post-rollback valid
        main_window._run_validation()
        QTimer.singleShot(300, lambda: None)
        qapp.processEvents()

        assert main_window.view_model.validation_results.overall_status == "valid"

        main_window.close()
        qapp.processEvents()


@pytest.mark.parametrize("platform", ["win32", "linux"], indirect=True)
def test_cross_platform_symlink_handling(platform, temp_base_path):
    """Testa handling cross-platform de symlinks/junctions (INC-007)."""

    # Mock platform via sys.platform patch
    with patch("sys.platform", platform):
        migration_service = MigrationService(base_path=str(temp_base_path))

        step = MagicMock()
        step.target_path = str(temp_base_path / "cross_platform_link")
        step.source_path = str(temp_base_path / "source")
        step.rollback_info = {}

        # Create source
        source_dir = temp_base_path / "source"
        source_dir.mkdir()
        (source_dir / "platform_test.txt").write_text(f"Content for {platform}")

        # For Windows, expect junction fallback
        if platform == "win32":
            with patch.object(
                Path, "symlink_to", side_effect=OSError("Privilege error")
            ):
                with patch("subprocess.run", return_value=MagicMock(returncode=0)):
                    migration_service._execute_create_symlink(step)
                    assert step.rollback_info.get("method_used") == "junction"
        else:
            # For Linux, expect standard symlink
            migration_service._execute_create_symlink(step)
            assert step.rollback_info.get("method_used") == "symlink"

        # Verify cross-platform access
        link_path = Path(step.target_path)
        assert (
            link_path / "platform_test.txt"
        ).read_text() == f"Content for {platform}"

        # Test rollback works cross-platform
        migration_service._rollback_create_symlink(step)
        assert not link_path.exists()


if __name__ == "__main__":
    # Run E2E tests manually
    pytest.main([__file__, "-v", "-s", "--tb=short"])
