"""Tests for VariantService."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sd_emulation_gui.services.variant_service import (
    ExecutionResult,
    MigrationOperation,
    MigrationPlan,
    PlatformVariantAnalysis,
    SymlinkOperation,
    VariantService,
)


class TestVariantService:
    """Test cases for VariantService."""

    @pytest.fixture
    def mock_path_resolver(self):
        """Mock path resolver."""
        mock = Mock()
        mock.resolve_path.return_value = "/test/path"
        return mock

    @pytest.fixture
    def mock_path_config_manager(self):
        """Mock path config manager."""
        return Mock()

    @pytest.fixture
    def temp_variant_mapping(self, tmp_path):
        """Create temporary variant mapping file."""
        mapping = {
            "Nintendo Entertainment System": {
                "Hacks": "Hacks",
                "Homebrew": "Homebrew",
                "Japanese": "Japanese",
            },
            "Super Nintendo Entertainment System": {
                "HD": "HD",
                "Brazil Games Translated": "Brazil Games Translated",
            },
        }
        mapping_file = tmp_path / "variant_mapping.json"
        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f)
        return mapping_file, mapping

    @pytest.fixture
    def variant_service(
        self,
        tmp_path,
        mock_path_resolver,
        mock_path_config_manager,
        temp_variant_mapping,
    ):
        """Create VariantService instance with mocked dependencies."""
        mapping_file, mapping = temp_variant_mapping

        with (
            patch(
                "services.variant_service.PathResolver", return_value=mock_path_resolver
            ),
            patch(
                "meta.config.path_config.PathConfigManager",
                return_value=mock_path_config_manager,
            ),
            patch.object(Path, "mkdir"),
            patch("builtins.open", create=True) as mock_open,
        ):

            mock_open.return_value.__enter__.return_value.read.return_value = (
                json.dumps(mapping)
            )

            service = VariantService(
                str(tmp_path),
                path_resolver=mock_path_resolver,
                path_config_manager=mock_path_config_manager,
            )

            service.variant_mapping = mapping
            return service

    def test_init_with_base_path(
        self, tmp_path, mock_path_resolver, mock_path_config_manager
    ):
        """Test VariantService initialization with base path."""
        with patch.object(Path, "mkdir"):

            service = VariantService(
                str(tmp_path),
                path_resolver=mock_path_resolver,
                path_config_manager=mock_path_config_manager,
            )

            assert service.base_path == tmp_path
            assert service.roms_path == tmp_path / "Roms"
            assert service.emulation_path == tmp_path / "Emulation"
            assert service.media_path == tmp_path / "Emulation" / "downloaded_media"

    def test_init_without_base_path(self, mock_path_resolver, mock_path_config_manager):
        """Test VariantService initialization without base path (uses dynamic path)."""
        mock_path_resolver.resolve_path.side_effect = lambda x: (
            "/dynamic/path" if x == "base_drive" else "/config/path"
        )

        with patch.object(Path, "mkdir"):

            service = VariantService(
                path_resolver=mock_path_resolver,
                path_config_manager=mock_path_config_manager,
            )

            # Should be called twice: once for base_drive, once for config_base_path
            assert mock_path_resolver.resolve_path.call_count == 2
            mock_path_resolver.resolve_path.assert_any_call("base_drive")
            mock_path_resolver.resolve_path.assert_any_call("config_base_path")
            assert Path(str(service.base_path)) == Path("/dynamic/path")

    def test_load_variant_mapping_success(
        self,
        tmp_path,
        mock_path_resolver,
        mock_path_config_manager,
        temp_variant_mapping,
    ):
        """Test successful loading of variant mapping."""
        mapping_file, expected_mapping = temp_variant_mapping
        def resolve_side_effect(key):
            if key == "config_base_path":
                return str(mapping_file.parent)
            if key == "base_drive":
                return str(tmp_path)
            return str(mapping_file.parent)

        mock_path_resolver.resolve_path.side_effect = resolve_side_effect

        with patch.object(Path, "mkdir"), patch("builtins.open", create=True) as mock_open:

            mock_open.return_value.__enter__.return_value.read.return_value = (
                json.dumps(expected_mapping)
            )

            service = VariantService(
                str(tmp_path),
                path_resolver=mock_path_resolver,
                path_config_manager=mock_path_config_manager,
            )

        assert service.variant_mapping == expected_mapping

    def test_load_variant_mapping_file_not_found(
        self, tmp_path, mock_path_resolver, mock_path_config_manager
    ):
        """Test variant mapping loading when file doesn't exist."""
        mock_path_resolver.resolve_path.return_value = str(tmp_path)

        with patch.object(Path, "mkdir"):

            service = VariantService(
                str(tmp_path),
                path_resolver=mock_path_resolver,
                path_config_manager=mock_path_config_manager,
            )

        assert service.variant_mapping == {}

    def test_analyze_variant_structure_no_roms_path(self, variant_service):
        """Test analyze_variant_structure when ROMs path doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            result = variant_service.analyze_variant_structure()
            assert result == []

    def test_analyze_variant_structure_with_platforms(self, variant_service, tmp_path):
        """Test analyze_variant_structure with platform directories."""
        # Create mock platform directories
        roms_path = tmp_path / "Roms"
        roms_path.mkdir()
        nes_dir = roms_path / "Nintendo Entertainment System"
        nes_dir.mkdir()
        hacks_dir = nes_dir / "Hacks"
        hacks_dir.mkdir()

        variant_service.roms_path = roms_path

        with patch.object(
            variant_service, "_analyze_platform_variants"
        ) as mock_analyze:
            mock_analysis = PlatformVariantAnalysis(
                platform_name="Nintendo Entertainment System",
                platform_dir=nes_dir,
                variant_ops=[
                    SymlinkOperation(
                        variant_type="Hacks",
                        platform_name="Nintendo Entertainment System",
                        main_platform_dir="Nintendo Entertainment System",
                        target_variant_folder="Hacks",
                        main_media_dir="nes",
                    )
                ],
            )
            mock_analyze.return_value = mock_analysis

            result = variant_service.analyze_variant_structure()

            assert len(result) == 1
            assert result[0].platform_name == "Nintendo Entertainment System"
            mock_analyze.assert_called_once_with(
                "Nintendo Entertainment System", nes_dir
            )

    def test_detect_variant_indicators(self, variant_service):
        """Test detection of variant indicators in folder structure."""
        existing_folders = ["Hacks", "Homebrew", "Regular Games", "media"]

        indicators = variant_service._detect_variant_indicators(
            "Nintendo Entertainment System", existing_folders
        )

        assert "Hacks" in indicators
        assert "Homebrew" in indicators
        assert "Regular Games" not in indicators
        assert "media" not in indicators

    def test_find_actual_variant_folder(self, variant_service):
        """Test finding actual variant folder name."""
        # Test existing platform and variant
        result = variant_service._find_actual_variant_folder(
            "Nintendo Entertainment System", "Hacks"
        )
        assert result == "Hacks"

        # Test non-existing platform
        result = variant_service._find_actual_variant_folder(
            "Unknown Platform", "Hacks"
        )
        assert result is None

        # Test non-existing variant
        result = variant_service._find_actual_variant_folder(
            "Nintendo Entertainment System", "Unknown Variant"
        )
        assert result is None

    def test_detect_if_variant_folder(self, variant_service):
        """Test detection if a folder is a variant folder."""
        # Test existing variant folder
        result = variant_service._detect_if_variant_folder(
            "Nintendo Entertainment System", "Hacks"
        )
        assert result == "Hacks"

        # Test non-variant folder
        result = variant_service._detect_if_variant_folder(
            "Nintendo Entertainment System", "Regular Games"
        )
        assert result is None

        # Test unknown platform
        result = variant_service._detect_if_variant_folder("Unknown Platform", "Hacks")
        assert result is None

    def test_get_platform_media_dir(self, variant_service):
        """Test getting platform media directory short name."""
        # Test known platforms
        assert (
            variant_service._get_platform_media_dir("Nintendo Entertainment System")
            == "nes"
        )
        assert variant_service._get_platform_media_dir("Nintendo 3DS") == "n3ds"
        assert (
            variant_service._get_platform_media_dir(
                "Super Nintendo Entertainment System"
            )
            == "snes"
        )

        # Test unknown platform
        result = variant_service._get_platform_media_dir("Unknown Platform")
        assert result == "unknownplatform"

    def test_plan_variant_symlinks(self, variant_service):
        """Test creating migration plan for variant symlinks."""
        # Create test analysis
        analysis = PlatformVariantAnalysis(
            platform_name="Nintendo Entertainment System",
            platform_dir=Path("/test/nes"),
            variant_ops=[
                SymlinkOperation(
                    variant_type="Hacks",
                    platform_name="Nintendo Entertainment System",
                    main_platform_dir="Nintendo Entertainment System",
                    target_variant_folder="Hacks",
                    main_media_dir="nes",
                )
            ],
            main_media_dir="nes",
        )

        plan = variant_service.plan_variant_symlinks([analysis])

        assert isinstance(plan, MigrationPlan)
        assert (
            len(plan.operations) == 2
        )  # One for variant symlink, one for media symlink
        assert plan.operations[0].operation_type == "create_variant_symlink"
        assert plan.operations[1].operation_type == "create_media_symlink"

    def test_execute_variant_plan_success(self, variant_service):
        """Test successful execution of variant plan."""
        # Create test plan
        plan = MigrationPlan(
            plan_id="test",
            description="Test plan",
            operations=[
                MigrationOperation(
                    id="op1",
                    operation_type="create_variant_symlink",
                    description="Test variant symlink",
                    source_path="source",
                    target_path="target",
                    metadata={"platform": "NES", "variant_type": "Hacks"},
                )
            ],
        )

        with patch.object(variant_service, "_execute_variant_symlink") as mock_execute:
            result = variant_service.execute_variant_plan(plan)

            assert result.success is True
            assert result.executed_operations == 1
            assert result.failed_operations == 0
            mock_execute.assert_called_once()

    def test_execute_variant_plan_failure(self, variant_service):
        """Test execution of variant plan with failures."""
        # Create test plan
        plan = MigrationPlan(
            plan_id="test",
            description="Test plan",
            operations=[
                MigrationOperation(
                    id="op1",
                    operation_type="create_variant_symlink",
                    description="Test variant symlink",
                    source_path="source",
                    target_path="target",
                    metadata={"platform": "NES", "variant_type": "Hacks"},
                )
            ],
        )

        with patch.object(
            variant_service,
            "_execute_variant_symlink",
            side_effect=Exception("Test error"),
        ):
            result = variant_service.execute_variant_plan(plan)

            assert result.success is False
            assert result.executed_operations == 0
            assert result.failed_operations == 1
            assert len(result.errors) == 1
            assert "Test error" in result.errors[0]

    def test_execute_variant_symlink_success(self, variant_service, tmp_path):
        """Test successful execution of variant symlink operation."""
        # Setup paths
        variant_service.roms_path = tmp_path / "Roms"
        platform_dir = variant_service.roms_path / "NES"
        platform_dir.mkdir(parents=True)
        source_dir = platform_dir / "source"
        source_dir.mkdir()

        operation = MigrationOperation(
            id="op1",
            operation_type="create_variant_symlink",
            description="Test",
            source_path="source",
            target_path="target",
            metadata={"platform": "NES", "variant_type": "Hacks"},
        )

        with patch.object(Path, "symlink_to") as mock_symlink:
            variant_service._execute_variant_symlink(operation)
            mock_symlink.assert_called_once_with("source", target_is_directory=True)

    def test_execute_variant_symlink_missing_paths(self, variant_service):
        """Test variant symlink execution with missing paths."""
        # Test missing target path
        operation = MigrationOperation(
            id="op1",
            operation_type="create_variant_symlink",
            description="Test",
            source_path="source",
            target_path=None,
            metadata={"platform": "NES", "variant_type": "Hacks"},
        )

        with pytest.raises(ValueError, match="Target path required"):
            variant_service._execute_variant_symlink(operation)

        # Test missing source path
        operation.target_path = "target"
        operation.source_path = None

        with pytest.raises(ValueError, match="Source path required"):
            variant_service._execute_variant_symlink(operation)

    def test_execute_media_symlink_success(self, variant_service, tmp_path):
        """Test successful execution of media symlink operation."""
        # Setup paths
        variant_service.roms_path = tmp_path / "Roms"
        platform_dir = variant_service.roms_path / "NES"
        variant_dir = platform_dir / "Hacks"
        variant_dir.mkdir(parents=True)

        operation = MigrationOperation(
            id="op1",
            operation_type="create_media_symlink",
            description="Test",
            source_path="../media/nes",
            target_path="media",
            metadata={"platform": "NES", "variant_type": "Hacks"},
        )

        with patch.object(Path, "symlink_to") as mock_symlink:
            variant_service._execute_media_symlink(operation)
            mock_symlink.assert_called_once_with(
                "../media/nes", target_is_directory=True
            )

    def test_execute_media_symlink_missing_paths(self, variant_service):
        """Test media symlink execution with missing paths."""
        # Test missing target path
        operation = MigrationOperation(
            id="op1",
            operation_type="create_media_symlink",
            description="Test",
            source_path="source",
            target_path=None,
            metadata={"platform": "NES", "variant_type": "Hacks"},
        )

        with pytest.raises(ValueError, match="Target path required"):
            variant_service._execute_media_symlink(operation)

        # Test missing source path
        operation.target_path = "target"
        operation.source_path = None

        with pytest.raises(ValueError, match="Source path required"):
            variant_service._execute_media_symlink(operation)

    def test_symlink_operation_dataclass(self):
        """Test SymlinkOperation dataclass."""
        op = SymlinkOperation(
            variant_type="Hacks",
            platform_name="NES",
            main_platform_dir="NES",
            target_variant_folder="Hacks",
            main_media_dir="nes",
        )

        assert op.variant_type == "Hacks"
        assert op.platform_name == "NES"
        assert op.status == "pending"  # Default value

    def test_platform_variant_analysis_dataclass(self):
        """Test PlatformVariantAnalysis dataclass."""
        analysis = PlatformVariantAnalysis(
            platform_name="NES", platform_dir=Path("/test")
        )

        assert analysis.platform_name == "NES"
        assert analysis.platform_dir == Path("/test")
        assert analysis.variant_ops == []  # Default value
        assert analysis.main_media_dir is None  # Default value

    def test_migration_operation_dataclass(self):
        """Test MigrationOperation dataclass."""
        op = MigrationOperation(
            id="test", operation_type="create_symlink", description="Test operation"
        )

        assert op.id == "test"
        assert op.operation_type == "create_symlink"
        assert op.description == "Test operation"
        assert op.source_path is None  # Default value
        assert op.target_path is None  # Default value
        assert op.metadata == {}  # Default value

    def test_migration_plan_dataclass(self):
        """Test MigrationPlan dataclass."""
        plan = MigrationPlan(plan_id="test", description="Test plan")

        assert plan.plan_id == "test"
        assert plan.description == "Test plan"
        assert plan.operations == []  # Default value

    def test_execution_result_dataclass(self):
        """Test ExecutionResult dataclass."""
        result = ExecutionResult()

        assert result.success is False  # Default value
        assert result.executed_operations == 0  # Default value
        assert result.failed_operations == 0  # Default value
        assert result.errors == []  # Default value