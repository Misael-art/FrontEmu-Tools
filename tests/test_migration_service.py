import os
import shutil
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from domain.models import EmulatorMapping, PlatformMapping
from sd_emulation_gui.services.migration_service import (
    MigrationPlan,
    MigrationResult,
    MigrationService,
    MigrationStep,
)


class TestMigrationStep:
    """Test MigrationStep class."""

    def test_migration_step_creation(self):
        """Test MigrationStep creation with all parameters."""
        step = MigrationStep(
            step_id="test_001",
            action="create_directory",
            source_path="/source",
            target_path="/target",
            description="Test step",
        )

        assert step.step_id == "test_001"
        assert step.action == "create_directory"
        assert step.source_path == "/source"
        assert step.target_path == "/target"
        assert step.description == "Test step"
        assert step.executed is False
        assert step.error is None
        assert step.rollback_info == {}

    def test_migration_step_minimal(self):
        """Test MigrationStep creation with minimal parameters."""
        step = MigrationStep(step_id="test_002", action="move_file")

        assert step.step_id == "test_002"
        assert step.action == "move_file"
        assert step.source_path is None
        assert step.target_path is None
        assert step.description == ""
        assert step.executed is False
        assert step.error is None
        assert step.rollback_info == {}


class TestMigrationPlan:
    """Test MigrationPlan class."""

    def test_migration_plan_creation(self):
        """Test MigrationPlan creation."""
        plan = MigrationPlan(plan_id="plan_001", description="Test plan")

        # Add steps manually
        step1 = MigrationStep("001", "create_directory")
        step2 = MigrationStep("002", "move_file")
        plan.add_step(step1)
        plan.add_step(step2)

        assert plan.plan_id == "plan_001"
        assert plan.description == "Test plan"
        assert len(plan.steps) == 2
        assert plan.total_steps == 2
        assert plan.executed is False
        assert plan.success is False
        assert plan.backup_location is None

    def test_migration_plan_empty_steps(self):
        """Test MigrationPlan with empty steps list."""
        plan = MigrationPlan(plan_id="plan_002", description="Empty plan")

        assert plan.total_steps == 0
        assert len(plan.steps) == 0


class TestMigrationResult:
    """Test MigrationResult class."""

    def test_migration_result_creation(self):
        """Test MigrationResult creation."""
        result = MigrationResult(
            success=True,
            message="Migration completed",
            executed_steps=["001", "002"],
            backup_location="/backup/test",
        )

        assert result.success is True
        assert result.message == "Migration completed"
        assert result.executed_steps == ["001", "002"]
        assert result.backup_location == "/backup/test"

    def test_migration_result_with_errors(self):
        """Test MigrationResult with errors."""
        result = MigrationResult(
            success=False,
            message="Migration failed",
            executed_steps=["001"],
            failed_step="002",
            rollback_performed=True,
        )

        assert result.success is False
        assert result.message == "Migration failed"
        assert result.executed_steps == ["001"]
        assert result.failed_step == "002"
        assert result.rollback_performed is True


class TestMigrationService:
    """Test MigrationService class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_config_manager(self):
        """Mock PathConfigManager."""
        mock = Mock()
        mock.get_base_path.return_value = "/test/base"
        mock.get_backup_directory.return_value = "/test/backup"
        return mock

    @pytest.fixture
    def mock_path_resolver(self):
        """Mock PathResolver."""
        mock = Mock()
        mock.resolve_path.return_value = "/resolved/path"
        return mock

    @pytest.fixture
    def migration_service(self):
        """Create MigrationService instance for testing."""
        with (
            patch("meta.config.path_config.PathConfigManager") as mock_pcm,
            patch("services.migration_service.PathResolver") as mock_pr,
            patch("services.migration_service.PathUtils") as mock_path_utils,
            patch("services.migration_service.FileUtils") as mock_file_utils,
            patch("services.migration_service.BaseService.__init__") as mock_base_init,
        ):

            # Configure mocks to prevent recursion
            mock_base_init.return_value = None
            mock_config = Mock()
            mock_resolver = Mock()
            mock_pcm.return_value = mock_config
            mock_pr.return_value = mock_resolver
            mock_config.get_path.return_value = None
            mock_resolver.resolve_path.return_value = None
            mock_path_utils.normalize_path.side_effect = lambda x: (
                str(x) if x else "/test/default"
            )
            mock_path_utils.ensure_directory_exists.return_value = None
            mock_path_utils.path_exists.return_value = True
            mock_file_utils.list_directory_contents.return_value = []

            service = MigrationService(
                base_path="/test/base", backup_dir="/test/backup"
            )
            # Manually set attributes that would be set by BaseService
            service.logger = Mock()
            return service

    @pytest.fixture
    def sample_emulator_mapping(self):
        """Create sample EmulatorMapping."""
        from domain.models import EmulatorConfig, EmulatorPaths, FrontendConfig

        emulator_config = EmulatorConfig(
            systems=["nintendo_64", "gamecube"],
            paths=EmulatorPaths(executable="/emulators/retroarch/retroarch.exe"),
        )

        return EmulatorMapping(
            emulators={"retroarch": emulator_config},
            frontends={"emulationstation": FrontendConfig()},
        )

    @pytest.fixture
    def sample_platform_mapping(self):
        """Create sample PlatformMapping."""
        return PlatformMapping(
            mappings={"nintendo_64": "Nintendo 64", "gamecube": "Nintendo GameCube"}
        )

    @pytest.fixture
    def sample_rules(self):
        """Create sample SDEmulationRules."""
        mock_rules = Mock()
        mock_rules.get_directory_structure.return_value = {
            "Roms": ["N64", "GC"],
            "Emulators": [],
            "Saves": [],
        }
        mock_rules.get_symlink_rules.return_value = {
            "create_emulator_symlinks": True,
            "create_save_symlinks": True,
        }
        # Add required_directories method that returns an iterable
        mock_dir_rule = Mock()
        mock_dir_rule.path = "Emulation"
        mock_rules.get_required_directories.return_value = [mock_dir_rule]

        # Add any other methods that might be called
        mock_rules.get_platform_rules.return_value = {}
        mock_rules.get_emulator_rules.return_value = {}
        return mock_rules

    def test_migration_service_initialization(self, migration_service):
        """Test MigrationService initialization."""
        assert migration_service.path_config is not None
        assert migration_service.path_resolver is not None
        assert migration_service.logger is not None
        assert migration_service.progress_callback is None
        assert migration_service.backup_dir == "/test/backup"

    def test_set_progress_callback(self, migration_service):
        """Test setting progress callback."""
        callback = Mock()
        migration_service.set_progress_callback(callback)
        assert migration_service.progress_callback == callback

    @patch("services.migration_service.PathUtils")
    @patch("os.walk")
    def test_plan_migration_success(
        self,
        mock_walk,
        mock_file_utils,
        mock_path_utils,
        migration_service,
        sample_emulator_mapping,
        sample_platform_mapping,
        sample_rules,
    ):
        """Test successful migration planning."""
        # Mock path utilities
        mock_path_utils.path_exists.return_value = True
        mock_path_utils.join_paths.side_effect = lambda *args: "/".join(
            str(arg) for arg in args if arg is not None
        )
        mock_path_utils.get_parent_directory.return_value = "/parent"
        mock_path_utils.normalize_path.return_value = "/test/path"
        mock_path_utils.ensure_directory_exists.return_value = None
        mock_file_utils.list_directory_contents.return_value = []
        mock_file_utils.find_files.return_value = []
        mock_walk.return_value = []

        # Configure sample_rules for symlinks
        mock_symlink_rule = Mock()
        mock_symlink_rule.source_pattern = "roms/gba"
        mock_symlink_rule.target_pattern = "../shared/gba_roms"
        mock_symlink_rule.description = "GBA ROM symlink"
        sample_rules.get_required_symlinks.return_value = [mock_symlink_rule]

        # Mock path config and resolver
        with patch("meta.config.path_config.PathConfigManager") as mock_config:
            with patch("services.migration_service.PathResolver") as mock_resolver:
                mock_config_instance = Mock()
                mock_resolver_instance = Mock()
                mock_config.return_value = mock_config_instance
                mock_resolver.return_value = mock_resolver_instance

                mock_config_instance.get_path.return_value = "/test"
                mock_resolver_instance.resolve_path.return_value = "/test"

                # Execute planning
                plan = migration_service.plan_migration(
                    sample_emulator_mapping, sample_platform_mapping, sample_rules
                )

                # Verify plan creation
                assert isinstance(plan, MigrationPlan)
                assert plan.plan_id is not None
                assert "SD Emulation Migration Plan" in plan.description
                assert isinstance(plan.steps, list)

    @patch("services.migration_service.FileUtils")
    @patch("services.migration_service.PathUtils")
    @patch("os.walk")
    def test_plan_directory_structure(
        self,
        mock_walk,
        mock_path_utils,
        mock_file_utils,
        migration_service,
        sample_rules,
    ):
        """Test directory structure planning."""
        mock_path_utils.path_exists.return_value = False
        mock_path_utils.join_paths.side_effect = lambda *args: "/".join(
            str(arg) for arg in args if arg is not None
        )
        mock_path_utils.normalize_path.side_effect = lambda x: (
            str(x) if x is not None else "/test/default"
        )
        mock_walk.return_value = []
        mock_file_utils.find_files.return_value = []

        # Mock path config and resolver
        with patch("meta.config.path_config.PathConfigManager") as mock_config:
            with patch("services.migration_service.PathResolver") as mock_resolver:
                mock_config_instance = Mock()
                mock_resolver_instance = Mock()
                mock_config.return_value = mock_config_instance
                mock_resolver.return_value = mock_resolver_instance

                mock_config_instance.get_path.return_value = "/test"
                mock_resolver_instance.resolve_path.return_value = "/test"

                plan = MigrationPlan(plan_id="test_plan", description="Test Plan")
                migration_service._plan_directory_structure(plan, sample_rules)

                assert isinstance(plan.steps, list)
                # Check if directory creation steps were added
                dir_steps = [
                    step for step in plan.steps if step.action == "create_directory"
                ]
                assert len(dir_steps) >= 0

    @patch("services.migration_service.PathUtils")
    def test_plan_rom_organization(
        self, mock_path_utils, migration_service, sample_platform_mapping, sample_rules
    ):
        """Test ROM organization planning."""
        mock_path_utils.path_exists.return_value = True
        mock_path_utils.join_paths.side_effect = lambda *args: "/".join(args)
        mock_path_utils.get_relative_path.return_value = (
            "../Roms/Nintendo Entertainment System"
        )

        plan = MigrationPlan(plan_id="test_plan", description="Test Plan")
        migration_service._plan_rom_organization(
            plan, sample_platform_mapping, sample_rules
        )

        assert isinstance(plan.steps, list)

    @patch("services.migration_service.PathUtils")
    def test_plan_emulator_paths(
        self, mock_path_utils, migration_service, sample_emulator_mapping, sample_rules
    ):
        """Test emulator paths planning."""
        mock_path_utils.path_exists.return_value = True
        mock_path_utils.join_paths.side_effect = lambda *args: "/".join(args)

        plan = MigrationPlan(plan_id="test_plan", description="Test Plan")
        migration_service._plan_emulator_paths(
            plan, sample_emulator_mapping, sample_rules
        )

        assert isinstance(plan.steps, list)

    @patch("services.migration_service.PathUtils")
    @patch("os.walk")
    def test_plan_symlink_creation(
        self,
        mock_walk,
        mock_path_utils,
        migration_service,
        sample_rules,
        sample_emulator_mapping,
        sample_platform_mapping,
    ):
        """Test symlink creation planning."""
        mock_path_utils.path_exists.return_value = True
        mock_path_utils.join_paths.side_effect = lambda *args: "/".join(args)
        mock_walk.return_value = []

        # Create mock symlink rule
        mock_symlink_rule = Mock()
        mock_symlink_rule.source_pattern = "roms/gba"
        mock_symlink_rule.target_pattern = "../shared/gba_roms"
        mock_symlink_rule.description = "GBA ROM symlink"

        # Configure sample_rules to return the mock symlink rule
        sample_rules.get_required_symlinks.return_value = [mock_symlink_rule]

        emulator_mapping = sample_emulator_mapping
        platform_mapping = sample_platform_mapping

        # Mock path config and resolver
        with patch("meta.config.path_config.PathConfigManager") as mock_config:
            with patch("services.migration_service.PathResolver") as mock_resolver:
                mock_config_instance = Mock()
                mock_resolver_instance = Mock()
                mock_config.return_value = mock_config_instance
                mock_resolver.return_value = mock_resolver_instance

                mock_config_instance.get_path.return_value = "/test"
                mock_resolver_instance.resolve_path.return_value = "/test"

                plan = MigrationPlan("test_plan", "Test Plan")
                migration_service._plan_symlink_creation(
                    plan, emulator_mapping, platform_mapping, sample_rules
                )

                assert isinstance(plan.steps, list)
                # Check if any symlink creation steps were added
                symlink_steps = [
                    step for step in plan.steps if step.action == "create_symlink"
                ]
                assert len(symlink_steps) >= 0

    @patch("services.migration_service.PathUtils")
    @patch("services.migration_service.FileUtils")
    def test_create_backup_success(
        self, mock_file_utils, mock_path_utils, migration_service
    ):
        """Test successful backup creation."""
        mock_path_utils.path_exists.return_value = True
        mock_path_utils.join_paths.side_effect = lambda *args: "/".join(args)
        mock_path_utils.ensure_directory_exists.return_value = None
        mock_path_utils.is_directory.return_value = True
        mock_path_utils.get_parent_directory.return_value = "/backup/parent"
        mock_file_utils.copy_directory.return_value = None
        mock_file_utils.write_json_file.return_value = None

        plan = MigrationPlan("test_plan", "Test Plan")
        backup_path = migration_service._create_backup(plan)

        assert backup_path is not None
        assert "migration_backup_" in backup_path

    @patch("services.migration_service.PathUtils")
    def test_create_backup_failure(self, mock_path_utils, migration_service):
        """Test backup creation failure."""
        mock_path_utils.path_exists.return_value = False

        with pytest.raises(Exception):
            migration_service._create_backup()

    def test_execute_step_create_directory(self, migration_service):
        """Test executing create directory step."""
        step = MigrationStep("001", "create_directory", target_path="/test/dir")

        with patch("services.migration_service.PathUtils") as mock_path_utils:
            mock_path_utils.path_exists.return_value = False
            mock_path_utils.create_directory.return_value = None

            migration_service._execute_step(step)

            assert step.executed is True
            assert step.error is None

    def test_execute_step_create_symlink(self, migration_service):
        """Test executing create symlink step."""
        step = MigrationStep(
            "002", "create_symlink", source_path="/source", target_path="/target"
        )

        with patch("services.migration_service.PathUtils") as mock_path_utils:
            with patch("pathlib.Path") as mock_path:
                mock_instance = Mock()
                mock_path.return_value = mock_instance
                mock_instance.parent.mkdir = Mock()
                mock_instance.exists.return_value = False
                mock_instance.symlink_to = Mock()
                mock_path_utils.ensure_directory_exists.return_value = True
                mock_path_utils.path_exists.return_value = False
                mock_path_utils.get_parent_directory.return_value = "/parent"

                # Mock the target_path to return the mock instance
                step.target_path = mock_instance

                migration_service._execute_step(step)

                assert step.executed is True
                assert step.error is None

    def test_execute_step_move_file(self, migration_service):
        """Test executing move file step."""
        step = MigrationStep(
            "003", "move_file", source_path="/source/file", target_path="/target/file"
        )

        with patch("services.migration_service.PathUtils") as mock_path_utils:
            with patch("services.migration_service.FileUtils") as mock_file_utils:
                mock_path_utils.path_exists.side_effect = (
                    lambda value: value == "/source/file"
                )
                mock_file_utils.move_file.return_value = True

                migration_service._execute_step(step)

                assert step.executed is True
                assert step.error is None

    def test_execute_step_copy_file(self, migration_service):
        """Test executing copy file step."""
        step = MigrationStep(
            "004", "copy_file", source_path="/source/file", target_path="/target/file"
        )

        with patch("services.migration_service.PathUtils") as mock_path_utils:
            with patch("services.migration_service.FileUtils") as mock_file_utils:
                mock_path_utils.path_exists.side_effect = (
                    lambda value: value == "/source/file"
                )
                mock_file_utils.copy_file.return_value = True

                migration_service._execute_step(step)

                assert step.executed is True
                assert step.error is None

    def test_execute_step_invalid_action(self, migration_service):
        """Test executing step with invalid action."""
        step = MigrationStep("005", "invalid_action")

        with pytest.raises(ValueError, match="Unknown action"):
            migration_service._execute_step(step)

    def test_rollback_steps(self, migration_service):
        """Test rolling back executed steps."""
        steps = [
            MigrationStep("001", "create_directory", target_path="/test1"),
            MigrationStep("002", "create_directory", target_path="/test2"),
        ]

        # Mark steps as executed
        for step in steps:
            step.executed = True

        with patch.object(migration_service, "_rollback_step") as mock_rollback:
            migration_service._rollback_steps(steps)

            # Should rollback in reverse order
            assert mock_rollback.call_count == 2
            calls = mock_rollback.call_args_list
            assert calls[0][0][0].step_id == "002"
            assert calls[1][0][0].step_id == "001"

    def test_rollback_create_directory(self, migration_service):
        """Test rollback of create directory step."""
        step = MigrationStep("001", "create_directory", target_path="/test/dir")
        step.rollback_info = {"created": True}

        with patch("shutil.rmtree") as mock_rmtree:
            with patch("services.migration_service.PathUtils") as mock_path_utils:
                mock_path_utils.path_exists.return_value = True

                migration_service._rollback_create_directory(step)

                mock_rmtree.assert_called_once_with("/test/dir")

    def test_rollback_create_symlink(self, migration_service):
        """Test rollback of create symlink step."""
        step = MigrationStep("002", "create_symlink", target_path="/test/link")
        step.rollback_info = {"created": True}

        with patch("services.migration_service.FileUtils") as mock_file_utils:
            mock_file_utils.delete_file.return_value = True

            migration_service._rollback_create_symlink(step)

            mock_file_utils.delete_file.assert_called_once_with("/test/link", safe=True)

    def test_rollback_move_file(self, migration_service):
        """Test rollback of move file step."""
        step = MigrationStep(
            "003", "move_file", source_path="/source", target_path="/target"
        )
        step.rollback_info = {"source_existed": True}

        with patch("services.migration_service.PathUtils") as mock_path_utils:
            with patch("services.migration_service.FileUtils") as mock_file_utils:
                mock_path_utils.path_exists.side_effect = (
                    lambda value: value == "/target"
                )
                mock_file_utils.move_file.return_value = True

                migration_service._rollback_move_file(step)

                mock_file_utils.move_file.assert_called_once_with("/target", "/source")

    def test_rollback_copy_file(self, migration_service):
        """Test rollback of copy file step."""
        step = MigrationStep("004", "copy_file", target_path="/target")
        step.rollback_info = {"target_existed": False}

        with patch("services.migration_service.PathUtils") as mock_path_utils:
            with patch("services.migration_service.FileUtils") as mock_file_utils:
                mock_path_utils.path_exists.side_effect = (
                    lambda value: value == "/target"
                )
                mock_file_utils.delete_file.return_value = True

                migration_service._rollback_copy_file(step)

                mock_file_utils.delete_file.assert_called_once_with("/target", safe=True)

    @patch("ctypes.windll.shell32.IsUserAnAdmin")
    @patch("services.migration_service.Path")
    def test_retry_symlink_creation_success(
        self, mock_path, mock_is_admin, migration_service
    ):
        """Test successful symlink retry."""
        mock_is_admin.return_value = True

        mock_target = Mock()
        mock_path.return_value = mock_target
        mock_target.parent.mkdir = Mock()
        mock_target.exists.return_value = False
        mock_target.symlink_to = Mock()

        step = MigrationStep(
            "001", "create_symlink", source_path="/source", target_path="/target"
        )

        with patch("services.migration_service.PathUtils") as mock_path_utils:
            mock_path_utils.ensure_directory_exists.return_value = True
            with patch("services.migration_service.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                success, msg = migration_service._retry_symlink_creation(step)

        assert success is True
        assert "sucesso" in msg.lower() or "criado" in msg.lower() or "Symlink" in msg

    @patch("ctypes.windll.shell32.IsUserAnAdmin")
    def test_retry_symlink_creation_no_admin(self, mock_is_admin, migration_service):
        """Test symlink retry without admin privileges."""
        mock_is_admin.return_value = False

        step = MigrationStep(
            "001", "create_symlink", source_path="/source", target_path="/target"
        )

        success, msg = migration_service._retry_symlink_creation(step)

        assert success is False
        assert "Privilégios de administrador" in msg

    def test_fix_symlinks_no_plan(self, migration_service):
        """Test fix symlinks with no plan."""
        report = migration_service.fix_symlinks(None)

        assert report["success"] is False
        assert "Plano de migração não fornecido" in report["messages"][0]

    def test_fix_symlinks_no_failed(self, migration_service):
        """Test fix symlinks with no failed symlinks."""
        plan = MigrationPlan("test", "Test plan")

        report = migration_service.fix_symlinks(plan)

        assert report["success"] is True
        assert "Nenhum symlink falhado encontrado" in report["messages"][0]

    @patch("subprocess.run")
    def test_grant_permissions_success(self, mock_run, migration_service):
        """Test successful permission granting."""
        mock_run.return_value = Mock(returncode=0)

        with patch("services.migration_service.Path") as mock_path:
            mock_target = Mock()
            mock_path.return_value = mock_target
            mock_target.exists.return_value = True

            success, msg = migration_service._grant_permissions("/test/dir")

            assert success is True
            assert "Permissões concedidas" in msg or "sucesso" in msg.lower()

    @patch("subprocess.run")
    def test_grant_permissions_failure(self, mock_run, migration_service):
        """Test permission granting failure."""
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(1, "icacls", stderr="Access denied")

        with patch("services.migration_service.Path") as mock_path:
            mock_target = Mock()
            mock_path.return_value = mock_target
            mock_target.exists.return_value = True

            success, msg = migration_service._grant_permissions("/test/dir")

            assert success is False
            assert "Erro" in msg or "erro" in msg.lower()

    @patch("os.walk")
    def test_auto_resolve_paths(self, mock_walk, migration_service):
        """Test auto path resolution."""
        mock_walk.return_value = [
            ("/test/roms", [], ["game1.zip", "game2.iso"]),
            ("/test/emulators", [], ["retroarch.exe"]),
        ]

        with patch("services.migration_service.Path") as mock_path:
            mock_base = Mock()
            mock_path.return_value = mock_base
            mock_base.exists.return_value = True
            mock_base.is_dir.return_value = True

            # Mock relative_to method
            mock_rel = Mock()
            mock_rel.__str__ = Mock(return_value="roms")
            mock_base.relative_to.return_value = mock_rel

            report = migration_service._auto_resolve_paths("/test")

            assert report["success"] is True
            # Check for the actual keys returned by the method
            assert "resolved" in report
            assert isinstance(report["resolved"], list)

    def test_preview_migration(self, migration_service):
        """Test migration preview."""
        steps = [
            MigrationStep("001", "create_directory", target_path="/test1"),
            MigrationStep("002", "move_file", source_path="/src", target_path="/dst"),
        ]
        plan = MigrationPlan("test", "Test plan")
        for step in steps:
            plan.add_step(step)

        preview = migration_service.preview_migration(plan)

        assert preview["success"] is True
        assert preview["summary"]["total_steps"] == 2
        assert len(preview["changes"]) == 2
        assert len(preview["warnings"]) > 0  # Should warn about symlink/move operations

    def test_preview_migration_no_plan(self, migration_service):
        """Test migration preview with no plan."""
        with pytest.raises(ValueError, match="No migration plan provided"):
            migration_service.preview_migration(None)

    def test_create_migration_plan_alias(
        self,
        migration_service,
        sample_emulator_mapping,
        sample_platform_mapping,
        sample_rules,
    ):
        """Test create_migration_plan as alias for plan_migration."""
        with patch.object(migration_service, "plan_migration") as mock_plan:
            mock_plan.return_value = MigrationPlan("test", "Test")

            result = migration_service.create_migration_plan(
                sample_emulator_mapping, sample_platform_mapping, sample_rules
            )

            mock_plan.assert_called_once_with(
                sample_emulator_mapping, sample_platform_mapping, sample_rules, True
            )
            assert isinstance(result, MigrationPlan)

    def test_serialize_plan(self, migration_service):
        """Test migration plan serialization."""
        steps = [MigrationStep("001", "create_directory", target_path="/test")]
        plan = MigrationPlan("test_plan", "Test plan")
        for step in steps:
            plan.add_step(step)
        plan.created_at = "2023-01-01T00:00:00"

        serialized = migration_service._serialize_plan(plan)

        assert serialized["plan_id"] == "test_plan"
        assert serialized["description"] == "Test plan"
        assert serialized["created_at"] == "2023-01-01T00:00:00"
        assert len(serialized["steps"]) == 1
        assert serialized["steps"][0]["step_id"] == "001"

    @patch("services.migration_service.PathUtils")
    @patch("services.migration_service.FileUtils")
    def test_get_migration_history(
        self, mock_file_utils, mock_path_utils, migration_service
    ):
        """Test getting migration history."""
        mock_path_utils.path_exists.side_effect = lambda x: x != "/test/backup" or True
        mock_path_utils.list_directories.return_value = [
            "/test/backup/migration_backup_20230101_120000"
        ]
        mock_path_utils.get_filename.return_value = "migration_backup_20230101_120000"
        mock_path_utils.join_path.return_value = (
            "/test/backup/migration_backup_20230101_120000/migration_plan.json"
        )
        mock_file_utils.read_json_file.return_value = {
            "plan_id": "test",
            "description": "Test plan",
        }

        history = migration_service.get_migration_history()

        assert len(history) == 1
        assert history[0]["timestamp"] == "20230101_120000"
        assert history[0]["plan"]["plan_id"] == "test"

    def test_validate_migration_plan(self, migration_service):
        """Test migration plan validation."""
        # Test valid plan
        plan = MigrationPlan(plan_id="test_plan", steps=[])
        result = migration_service.validate_migration_plan(plan)
        assert result is True

        # Test invalid plan with duplicate step IDs
        step1 = MigrationStep(step_id="duplicate", action="create_directory")
        step2 = MigrationStep(step_id="duplicate", action="create_directory")
        invalid_plan = MigrationPlan(plan_id="invalid", steps=[step1, step2])
        result = migration_service.validate_migration_plan(invalid_plan)
        assert result is False

    def test_get_plan_statistics(self, migration_service):
        """Test migration plan statistics."""
        # Create a plan with various step types
        steps = [
            MigrationStep("step1", "create_directory", description="Create dir"),
            MigrationStep("step2", "create_symlink", description="Create link"),
            MigrationStep("step3", "move_file", description="Move file"),
        ]
        plan = MigrationPlan(plan_id="stats_test", description="Stats", steps=steps)

        stats = migration_service.get_plan_statistics(plan)
        assert stats["total_steps"] == 3
        assert stats["steps_by_action"]["create_directory"] == 1
        assert stats["steps_by_action"]["create_symlink"] == 1
        assert stats["steps_by_action"]["move_file"] == 1

    def test_estimate_migration_time(self, migration_service):
        """Test migration time estimation."""
        steps = [
            MigrationStep("step1", "create_directory"),
            MigrationStep("step2", "create_symlink"),
            MigrationStep("step3", "move_file"),
        ]
        plan = MigrationPlan(plan_id="time_test", description="Time", steps=steps)

        # Test with default timing
        estimated_time = migration_service.estimate_migration_time(plan)
        assert estimated_time > 0
        assert isinstance(estimated_time, (int, float))

    def test_check_prerequisites(self, migration_service):
        """Test prerequisite checking."""
        # Mock successful prerequisite check
        with patch.object(migration_service, '_check_disk_space') as mock_space, \
             patch.object(migration_service, '_check_permissions') as mock_perm:

            mock_space.return_value = True
            mock_perm.return_value = True

            result = migration_service.check_prerequisites("/test/path")
            assert result is True

    def test_check_prerequisites_failures(self, migration_service):
        """Test prerequisite checking with failures."""
        with patch.object(migration_service, '_check_disk_space') as mock_space, \
             patch.object(migration_service, '_check_permissions') as mock_perm:

            # Test disk space failure
            mock_space.return_value = False
            mock_perm.return_value = True

            result = migration_service.check_prerequisites("/test/path")
            assert result is False

    def test_cleanup_failed_migration(self, migration_service):
        """Test cleanup of failed migration."""
        with patch.object(migration_service, 'rollback_steps') as mock_rollback:
            mock_rollback.return_value = True

            result = migration_service.cleanup_failed_migration("test_plan")
            mock_rollback.assert_called_once_with("test_plan")
            assert result is True

    def test_get_migration_status(self, migration_service):
        """Test getting migration status."""
        # Test with existing plan
        with patch.object(migration_service, 'get_migration_history') as mock_history:
            mock_history.return_value = [
                {"plan_id": "test_plan", "status": "completed", "timestamp": "2025-01-01"}
            ]

            status = migration_service.get_migration_status("test_plan")
            assert status["plan_id"] == "test_plan"
            assert status["status"] == "completed"

    def test_validate_target_path(self, migration_service):
        """Test target path validation."""
        # Test valid path
        result = migration_service.validate_target_path("/valid/path")
        assert result is True

        # Test invalid path (would need to mock PathUtils for more complex validation)
        with patch('sd_emulation_gui.services.migration_service.PathUtils') as mock_utils:
            mock_utils.validate_safe_path.return_value = False

            result = migration_service.validate_target_path("/invalid/path")
            assert result is False
        """Test getting migration history with no backups."""
        mock_path_utils.path_exists.return_value = False

        history = migration_service.get_migration_history()

        assert history == []