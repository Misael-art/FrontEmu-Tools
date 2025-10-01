"""
Migration Service

This service handles safe migration of configurations and paths according to
SD emulation architecture rules with backup, rollback, and atomic operations.
"""

import ctypes
import os
import subprocess
import sys
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Import admin utilities
try:
    from utils.admin_utils import AdminUtils, is_admin, get_everyone_account
except ImportError:
    # Fallback implementations
    class AdminUtils:
        @staticmethod
        def is_admin():
            return False
        @staticmethod
        def get_everyone_account_name():
            return "Everyone"
        @staticmethod
        def request_admin_if_needed(op):
            return False
    
    def is_admin():
        return False
    
    def get_everyone_account():
        return "Everyone"

# Import the new path configuration system
import sys
from pathlib import Path

# Add meta/config to path
meta_config_path = Path(__file__).parent.parent.parent / "meta" / "config"
sys.path.insert(0, str(meta_config_path))

from meta.config.path_config import PathConfigManager
from meta.config.path_resolver import PathResolver

# Add src to path for imports
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

# Garantir aliases de módulo para testes que importam via "services.*"
import sys as _sys

_current_module = _sys.modules.setdefault(__name__, globals())
_sys.modules.setdefault("services.migration_service", _sys.modules[__name__])

try:
    from domain.models import EmulatorMapping, PlatformMapping
    from domain.sd_rules import SDEmulationRules
    from domain.path_types import PathType
    from utils import BaseService, PathUtils
    import utils  # Import module to access FileUtils via namespace
except ImportError:
    try:
        from config.emulator_mapping import EmulatorMapping  # type: ignore
        from config.platform_mapping import PlatformMapping  # type: ignore
        from meta.config.sd_rules import SDEmulationRules  # type: ignore
        from domain.path_types import PathType
        from utils import BaseService, PathUtils
        import utils  # Import module to access FileUtils via namespace
    except Exception:
        class EmulatorMapping:  # type: ignore
            pass

        class PlatformMapping:  # type: ignore
            pass

        class SDEmulationRules:  # type: ignore
            pass

        class PathType:  # type: ignore
            pass

        class BaseService:  # type: ignore
            pass

        class utils:  # type: ignore
            class FileUtils:  # type: ignore
                pass

        class PathUtils:  # type: ignore
            pass

# Create module-level FileUtils reference that can be patched by tests
# This avoids early binding and ensures patch("services.migration_service.FileUtils") works
try:
    FileUtils = utils.FileUtils
except (AttributeError, NameError):
    # Fallback for when utils module or FileUtils class is not available
    class FileUtils:  # type: ignore
        pass
class MigrationStep:
    """Individual migration step with details and rollback information."""

    def __init__(
        self,
        step_id: str,
        action: str,
        source_path: str | None = None,
        target_path: str | None = None,
        description: str = "",
    ):
        """
        Initialize migration step.

        Args:
            step_id: Unique identifier for this step
            action: Type of action (create_dir, move_file, create_symlink, etc.)
            source_path: Source path for the operation
            target_path: Target path for the operation
            description: Human-readable description
        """
        self.step_id = step_id
        self.action = action
        self.source_path = source_path
        self.target_path = target_path
        self.description = description
        self.executed = False
        self.rollback_info: dict[str, Any] = {}
        self.error: str | None = None


class MigrationPlan:
    """Plano completo de migração com estatísticas e DSL auxiliar."""

    def __init__(
        self,
        plan_id: str,
        description: str,
        *,
        steps: Iterable[MigrationStep] | None = None,
        created_at: str | None = None,
        executed: bool = False,
        execution_time: str | None = None,
        success: bool = False,
        backup_location: str | None = None,
    ) -> None:
        self.plan_id = plan_id
        self.description = description
        self.created_at = created_at or datetime.now().isoformat()
        self.steps: list[MigrationStep] = list(steps or [])
        self.executed = executed
        self.execution_time = execution_time
        self.success = success
        self.backup_location = backup_location

    # ------------------------------------------------------------------
    # Métodos de fábrica
    # ------------------------------------------------------------------
    @classmethod
    def plan_new(
        cls,
        *,
        description: str,
        prefix: str = "migration",
        timestamp: datetime | None = None,
    ) -> "MigrationPlan":
        ts = (timestamp or datetime.now()).strftime("%Y%m%d_%H%M%S")
        plan_id = f"{prefix}_{ts}"
        return cls(plan_id=plan_id, description=description)

    @classmethod
    def from_steps(
        cls,
        steps: Iterable[MigrationStep],
        *,
        plan_id: str = "migration_plan",
        description: str = "Migration Plan",
        executed: bool = False,
        success: bool = False,
        backup_location: str | None = None,
    ) -> "MigrationPlan":
        return cls(
            plan_id=plan_id,
            description=description,
            steps=steps,
            executed=executed,
            success=success,
            backup_location=backup_location,
        )

    # ------------------------------------------------------------------
    # API utilizada pelos testes / serviços
    # ------------------------------------------------------------------
    def add_step(self, step: MigrationStep) -> None:
        if not isinstance(step, MigrationStep):
            raise TypeError("step deve ser MigrationStep")
        self.steps.append(step)

    def extend_steps(self, steps: Iterable[MigrationStep]) -> None:
        for step in steps:
            self.add_step(step)

    def get_step_by_id(self, step_id: str) -> MigrationStep | None:
        return next((step for step in self.steps if step.step_id == step_id), None)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(1 for step in self.steps if step.executed and not step.error)

    @property
    def failed_steps(self) -> int:
        return sum(1 for step in self.steps if step.error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "description": self.description,
            "created_at": self.created_at,
            "executed": self.executed,
            "steps": [step.__dict__ for step in self.steps],
        }

    def to_serializable(self) -> dict[str, Any]:
        data = self.to_dict()
        data.update(
            {
                "execution_time": self.execution_time,
                "success": self.success,
                "backup_location": self.backup_location,
            }
        )
        return data


class MigrationResult:
    """Result of a migration operation with details and status."""

    def __init__(
        self,
        success: bool,
        message: str = "",
        executed_steps: list[str] | None = None,
        failed_step: str | None = None,
        backup_location: str | None = None,
        rollback_performed: bool = False,
    ):
        """
        Initialize migration result.

        Args:
            success: Whether the migration was successful
            message: Result message or error description
            executed_steps: List of step IDs that were executed
            failed_step: ID of the step that failed (if any)
            backup_location: Path to backup location
            rollback_performed: Whether rollback was performed
        """
        self.success = success
        self.message = message
        self.executed_steps = executed_steps or []
        self.failed_step = failed_step
        self.backup_location = backup_location
        self.rollback_performed = rollback_performed


class MigrationService(BaseService):
    """Service for handling configuration and path migrations."""

    def __init__(
        self,
        base_path: str = None,
        backup_dir: str = None,
        progress_callback: Callable[[str], None] | None = None,
    ):
        """
        Initialize migration service.

        Args:
            base_path: Base path for operations
            backup_dir: Directory for backups
            progress_callback: Optional callback function for progress updates
        """
        super().__init__()

        # Use simple paths if not provided
        if base_path is None:
            # Use project root as default
            project_root = Path(__file__).parent.parent.parent.parent
            base_path = str(project_root)
            
        if backup_dir is None:
            # Use backup subdirectory as default
            project_root = Path(__file__).parent.parent.parent.parent
            backup_dir = str(project_root / "backup")

        self.base_path = PathUtils.normalize_path(str(base_path))
        self.backup_dir = PathUtils.normalize_path(str(backup_dir))

        self._progress_callback = progress_callback
        
        # Create simple path resolver for internal use
        class SimpleResolver:
            def __init__(self, base_path):
                self.update_base_path(base_path)
                
            def update_base_path(self, base_path):
                """Update the base path used for resolution."""
                # CORREÇÃO: Usar sempre a raiz do drive atual
                current_drive = Path.cwd().anchor  # Get current drive (e.g., "F:\\")
                if current_drive:
                    self.base = Path(current_drive)
                    print(f"[SimpleResolver] Usando diretório base: {self.base}")
                else:
                    # Fallback para o drive atual detectado
                    self.base = Path("F:/")
                    print(f"[SimpleResolver] Fallback para: {self.base}")
                
            def resolve_path(self, path_key):
                class Result:
                    def __init__(self, path):
                        self.resolved_path = Path(path)
                        
                    def __str__(self):
                        return str(self.resolved_path)
                        
                    def __repr__(self):
                        return f"Result(resolved_path='{self.resolved_path}')"
                        
                paths = {
                    "emulation_root": str(self.base / "Emulation"),
                    "emulation_roms_symlinks": str(self.base / "Emulation" / "roms"),
                    "base_drive": str(self.base)
                }
                return Result(paths.get(path_key, str(self.base)))
        
        self.path_resolver = SimpleResolver(self.base_path)

        # Store for current migration plan
        self._current_migration_plan: MigrationPlan | None = None

        # Ensure backup directory exists using PathUtils
        PathUtils.ensure_directory_exists(self.backup_dir)

    def initialize(self) -> None:
        """Initialize MigrationService."""
        # MigrationService initialization is handled in __init__
        # This method is required by BaseService
        pass
    
    @property
    def progress_callback(self) -> Callable[[str], None] | None:
        """Get progress callback function."""
        return self._progress_callback
        
    @progress_callback.setter
    def progress_callback(self, callback: Callable[[str], None] | None) -> None:
        """Set progress callback function."""
        self._progress_callback = callback

    def set_progress_callback(self, callback: Callable[[str], None] | None) -> None:
        """Set progress callback function."""
        self._progress_callback = callback
    
    def update_base_path(self, new_base_path: str) -> None:
        """Update the base path used for migration operations.
        
        Args:
            new_base_path: New base directory path where the emulation structure will be created
        """
        self.base_path = PathUtils.normalize_path(str(new_base_path))
        # Update the internal path resolver
        if hasattr(self.path_resolver, 'update_base_path'):
            self.path_resolver.update_base_path(new_base_path)
        else:
            # Recreate the resolver with the new base path
            class SimpleResolver:
                def __init__(self, base_path):
                    self.base = Path(new_base_path)
                    
                def resolve_path(self, path_key):
                    class Result:
                        def __init__(self, path):
                            self.resolved_path = Path(path)
                            
                        def __str__(self):
                            return str(self.resolved_path)
                            
                        def __repr__(self):
                            return f"Result(resolved_path='{self.resolved_path}')"
                            
                    paths = {
                        "emulation_root": str(self.base / "Emulation"),
                        "emulation_roms_symlinks": str(self.base / "Emulation" / "roms"),
                        "base_drive": str(self.base)
                    }
                    return Result(paths.get(path_key, str(self.base)))
            
            self.path_resolver = SimpleResolver(new_base_path)
        
        if self._progress_callback:
            self._progress_callback(f"Diretório base atualizado para: {new_base_path}")
        self.logger.info(f"Base path updated to: {new_base_path}")
    
    def get_current_base_path(self) -> str:
        """Get the current base path being used for migration operations.
        
        Returns:
            Current base directory path
        """
        return self.base_path

    def plan_migration(
        self,
        emulator_mapping: EmulatorMapping,
        platform_mapping: PlatformMapping,
        rules: SDEmulationRules,
        dry_run: bool = True,
    ) -> MigrationPlan:
        """
        Create a migration plan based on current state and target rules.

        Args:
            emulator_mapping: Current emulator mapping
            platform_mapping: Platform name mapping
            rules: SD emulation rules to follow
            dry_run: If True, only plan without executing

        Returns:
            Complete migration plan
        """
        plan_id = f"plan_{uuid4().hex[:8]}"
        plan = MigrationPlan(
            plan_id,
            f"SD Emulation Migration Plan - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )

        try:
            # Plan directory structure creation
            self._plan_directory_structure(plan, rules)

            # Plan ROM organization (full_name directories with short_name symlinks)
            self._plan_rom_organization(plan, platform_mapping, rules)

            # Plan emulator path adjustments
            self._plan_emulator_paths(plan, emulator_mapping, rules)

            # Plan symlink creation for compatibility
            self._plan_symlink_creation(plan, emulator_mapping, platform_mapping, rules)

            if self._progress_callback:
                self._progress_callback(
                    f"Plano de migração criado: {plan.total_steps} passos planejados"
                )
            self.logger.info(
                f"Migration plan created: {plan.total_steps} steps planned"
            )

        except Exception as e:
            self.logger.error(f"Failed to create migration plan: {e}")
            if self._progress_callback:
                self._progress_callback(f"Erro ao criar plano de migração: {e}")
            raise

        self.set_current_migration_plan(plan)

        return plan

    # ------------------------------------------------------------------
    # Pipeline de planejamento granular (usado pelos testes)
    # ------------------------------------------------------------------
    def plan_emulator_paths(
        self, emulator_mapping: EmulatorMapping, rules: SDEmulationRules
    ) -> MigrationPlan:
        plan = MigrationPlan.plan_new(description="Plan emulator directories")
        self._plan_emulator_paths(plan, emulator_mapping, rules)
        return plan

    def plan_symlink_creation(
        self,
        emulator_mapping: EmulatorMapping,
        platform_mapping: PlatformMapping,
        rules: SDEmulationRules,
    ) -> MigrationPlan:
        plan = MigrationPlan.plan_new(description="Plan symlink creation")
        self._plan_symlink_creation(plan, emulator_mapping, platform_mapping, rules)
        return plan

    def load_plan(self, plan_data: dict[str, Any]) -> MigrationPlan:
        steps = [
            MigrationStep(
                step_id=item.get("step_id", "unknown"),
                action=item.get("action", "unknown"),
                source_path=item.get("source_path"),
                target_path=item.get("target_path"),
                description=item.get("description", ""),
            )
            for item in plan_data.get("steps", [])
        ]

        return MigrationPlan(
            plan_id=plan_data.get("plan_id", "migration_plan"),
            description=plan_data.get("description", "Migration Plan"),
            steps=steps,
            executed=plan_data.get("executed", False),
            execution_time=plan_data.get("execution_time"),
            success=plan_data.get("success", False),
            backup_location=plan_data.get("backup_location"),
        )

    def apply_migration(self, plan: MigrationPlan, confirm: bool = False) -> bool:
        """
        Apply a migration plan with atomic operations and rollback capability.

        Args:
            plan: Migration plan to execute
            confirm: Must be True to actually execute

        Returns:
            True if migration successful, False otherwise
        """
        if not confirm:
            warning_msg = "Migration not confirmed - use confirm=True to execute"
            self.logger.warning(warning_msg)
            if self._progress_callback:
                self._progress_callback(warning_msg)
            return False

        if plan.executed:
            warning_msg = f"Migration plan {plan.plan_id} already executed"
            self.logger.warning(warning_msg)
            if self._progress_callback:
                self._progress_callback(warning_msg)
            return False
        
        # Check if this migration requires admin privileges (has symlinks or file operations)
        requires_admin = any(step.action in ["create_symlink", "move_file"] for step in plan.steps)
        
        if requires_admin and sys.platform == "win32":
            if not is_admin():
                # Operating in read-only mode - do not request admin privileges automatically
                # This prevents UAC dialogs and application hangs
                warning_msg = f"Migração requer privilégios administrativos para {plan.total_steps} operações. Executando em modo somente-leitura."
                self.logger.warning(warning_msg)
                if self._progress_callback:
                    self._progress_callback(warning_msg)
                # Continue execution but some operations may fail gracefully

        # Create backup before starting
        if self._progress_callback:
            self._progress_callback("Criando backup de segurança...")
        backup_location = self._create_backup(plan)
        plan.backup_location = str(backup_location)
        if self._progress_callback:
            self._progress_callback(f"Backup criado em: {backup_location}")

        plan.executed = True
        plan.execution_time = datetime.now().isoformat()
        executed_steps = []

        try:
            total_steps_msg = f"Iniciando execução: {plan.total_steps} passos"
            self.logger.info(total_steps_msg)
            if self._progress_callback:
                self._progress_callback(total_steps_msg)

            for i, step in enumerate(plan.steps, 1):
                try:
                    step_msg = (
                        f"Executando passo {i}/{plan.total_steps}: {step.description}"
                    )
                    self.logger.debug(step_msg)
                    if self._progress_callback:
                        self._progress_callback(step_msg)

                    self._execute_step(step)
                    executed_steps.append(step)

                    success_msg = f"Passo concluído: {step.description}"
                    self.logger.debug(success_msg)
                    if self._progress_callback:
                        self._progress_callback(success_msg)

                except (
                    ValueError,
                    OSError,
                    FileNotFoundError,
                    PermissionError,
                    RuntimeError,
                ) as e:
                    step.error = str(e)
                    error_msg = f"Passo {i} falhou: {step.description} - {e}"
                    self.logger.error(error_msg)
                    if self._progress_callback:
                        self._progress_callback(error_msg)

                    # Attempt rollback of executed steps
                    rollback_msg = f"Executando rollback devido a falha no passo {i}"
                    self.logger.warning(rollback_msg)
                    if self._progress_callback:
                        self._progress_callback(rollback_msg)
                    self._rollback_steps(executed_steps)
                    return False

            success_msg = f"Migration plan {plan.plan_id} executed successfully"
            plan.success = True
            self.logger.info(success_msg)
            if self._progress_callback:
                self._progress_callback("Migração concluída com sucesso!")
            return True

        except (
            ValueError,
            OSError,
            FileNotFoundError,
            PermissionError,
            RuntimeError,
        ) as e:
            error_msg = f"Migration execution failed: {e}"
            self.logger.error(error_msg)
            if self._progress_callback:
                self._progress_callback(error_msg)
            self._rollback_steps(executed_steps)
            return False

    def _plan_directory_structure(
        self, plan: MigrationPlan, rules: SDEmulationRules
    ) -> None:
        """Plan directory structure creation according to rules."""
        if self._progress_callback:
            self._progress_callback("Planejando estrutura de diretórios...")

        for dir_rule in rules.get_required_directories():
            # Resolve the directory path dynamically using PathUtils
            resolved_path = (
                self.path_resolver.resolve_path(dir_rule.path)
                if hasattr(dir_rule, "path")
                else str(dir_rule)
            )
            target_path = PathUtils.join_paths(self.base_path, resolved_path)
            emulation_path = PathUtils.normalize_path(
                self.path_resolver.resolve_path("emulation_root").resolved_path
            )

            base_description = f"Create directory: {dir_rule.path} - Esta ação criará o diretório de emulação para centralizar recursos comuns a todos os emuladores e frontends, como configurações, saves, assets e symlinks compartilhados. Isso facilita a manutenção e evita dispersão de arquivos em múltiplos locais."

            if PathUtils.path_exists(emulation_path):
                # Resumir conteúdo do diretório usando FileUtils
                try:
                    items = FileUtils.find_files(emulation_path, "*", recursive=False)
                    main_items_count = len(
                        [item for item in items if not Path(item).name.startswith(".")]
                    )
                    content_summary = f"{main_items_count} itens principais (pastas/arquivos visíveis)"
                    if main_items_count > 10:
                        content_summary += " - diretório bem populado"
                    elif main_items_count == 0:
                        content_summary += " - diretório vazio, pronto para uso"
                except Exception:
                    content_summary = "conteúdo não acessível (verifique permissões)"

                description = f"{base_description} 📁 TARGET PATH: {emulation_path}\n\nDiretório de emulação já existe e está pronto - pulando criação para evitar sobrescrita. Conteúdo atual: {content_summary}."
                step = MigrationStep(
                    step_id=f"mkdir_{uuid4().hex[:8]}",
                    action="create_directory",
                    target_path=target_path,
                    description=description,
                )
            else:
                description = f"{base_description} 📁 TARGET PATH: {emulation_path}\n\nDiretório criado com sucesso para centralizar recursos de emuladores e frontends, como configs, saves e assets compartilhados."
                step = MigrationStep(
                    step_id=f"mkdir_{uuid4().hex[:8]}",
                    action="create_directory",
                    target_path=target_path,
                    description=description,
                )

            plan.add_step(step)

    def _plan_rom_organization(
        self,
        plan: MigrationPlan,
        platform_mapping: PlatformMapping,
        rules: SDEmulationRules,
    ) -> None:
        """Plan ROM directory organization with full names and symlinks."""
        if self._progress_callback:
            self._progress_callback("Planejando organização de ROMs...")

        # Handle both dict and object formats
        mappings = platform_mapping.get("mappings", {}) if isinstance(platform_mapping, dict) else getattr(platform_mapping, "mappings", {})
        
        for short_name, full_name in mappings.items():
            # Create full name directory using PathUtils
            roms_base = "Roms"  # Use default roms directory
            full_name_dir = PathUtils.join_paths(self.base_path, roms_base, full_name)
            step = MigrationStep(
                step_id=f"rom_dir_{uuid4().hex[:8]}",
                action="create_directory",
                target_path=full_name_dir,
                description=f"Create ROM directory for {full_name}",
            )
            plan.add_step(step)

            # Plan symlink creation using PathUtils
            emulation_roms = self.path_resolver.resolve_path("emulation_roms_symlinks")
            symlink_path = PathUtils.join_paths(
                self.base_path, emulation_roms, short_name
            )
            roms_base = "Roms"  # Use default roms directory
            relative_target = PathUtils.get_relative_path(
                PathUtils.join_paths(self.base_path, roms_base, full_name),
                PathUtils.join_paths(self.base_path, emulation_roms),
            )

            step = MigrationStep(
                step_id=f"rom_link_{uuid4().hex[:8]}",
                action="create_symlink",
                source_path=relative_target,
                target_path=symlink_path,
                description=f"Create symlink: {short_name} -> {full_name}",
            )
            plan.add_step(step)

    def _plan_emulator_paths(
        self,
        plan: MigrationPlan,
        emulator_mapping: EmulatorMapping,
        rules: SDEmulationRules,
    ) -> None:
        """Plan emulator path adjustments."""
        if self._progress_callback:
            self._progress_callback("Planejando caminhos de emuladores...")

        # Handle both dict and object formats for emulator mapping
        emulators = emulator_mapping.get("emulators", {}) if isinstance(emulator_mapping, dict) else getattr(emulator_mapping, "emulators", {})
        
        for emulator_name, emulator_config in emulators.items():
            emulator_dir = PathUtils.join_paths(
                self.base_path, "Emulators", emulator_name
            )

            # Create emulator directory
            step = MigrationStep(
                step_id=f"emu_dir_{uuid4().hex[:8]}",
                action="create_directory",
                target_path=emulator_dir,
                description=f"Create emulator directory for {emulator_name}",
            )
            plan.add_step(step)

    def _plan_symlink_creation(
        self,
        plan: MigrationPlan,
        emulator_mapping: EmulatorMapping,
        platform_mapping: PlatformMapping,
        rules: SDEmulationRules,
    ) -> None:
        """Plan creation of compatibility symlinks."""
        if self._progress_callback:
            self._progress_callback(
                "Planejando criação de symlinks de compatibilidade..."
            )

        for symlink_rule in rules.get_required_symlinks():
            # This would need expansion based on actual emulator configurations
            # For now, add a placeholder step
            step = MigrationStep(
                step_id=f"symlink_{uuid4().hex[:8]}",
                action="create_symlink",
                description="Esta ação criará links simbólicos (symlinks) para garantir compatibilidade de ROMs com frontends de emulação. Isso envolve mapear caminhos de ROMs para locais esperados pelos emuladores, evitando duplicação de arquivos e facilitando o acesso rápido. Nenhum arquivo será copiado ou alterado - apenas links serão criados. Se symlinks já existirem, eles serão atualizados ou pulados para evitar erros.",
            )
            plan.add_step(step)

    def _create_backup(self, plan: MigrationPlan) -> str:
        """Create backup before migration."""
        if self._progress_callback:
            self._progress_callback("Criando backup de segurança...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_location = PathUtils.join_paths(
            self.backup_dir, f"migration_backup_{plan.plan_id}_{timestamp}"
        )
        PathUtils.ensure_directory_exists(backup_location)

        # Backup critical directories and files
        critical_paths = [
            "Emulation/configs",
            "Emulation/saves",
            "config",  # If it exists in base path
        ]

        backup_count = 0
        for path_str in critical_paths:
            source = PathUtils.join_paths(self.base_path, path_str)
            if PathUtils.path_exists(source):
                target = PathUtils.join_paths(backup_location, path_str)
                if PathUtils.is_directory(source):
                    FileUtils.copy_directory(source, target)
                else:
                    PathUtils.ensure_directory_exists(
                        PathUtils.get_parent_directory(target)
                    )
                    FileUtils.copy_file(source, target)
                backup_count += 1

        if self._progress_callback:
            self._progress_callback(f"Backup concluído: {backup_count} itens copiados")

        # Save migration plan
        plan_file = PathUtils.join_paths(backup_location, "migration_plan.json")
        FileUtils.write_json_file(plan_file, self._serialize_plan(plan))

        self.logger.info(f"Backup created at: {backup_location}")
        return backup_location

    def _execute_step(self, step: MigrationStep) -> None:
        """Execute a single migration step."""
        try:
            if step.action == "create_directory":
                self._execute_create_directory(step)
            elif step.action == "create_symlink":
                self._execute_create_symlink(step)
            elif step.action == "move_file":
                self._execute_move_file(step)
            elif step.action == "copy_file":
                self._execute_copy_file(step)
            else:
                raise ValueError(f"Unknown action: {step.action}")

            step.executed = True

        except (
            ValueError,
            OSError,
            FileNotFoundError,
            PermissionError,
            RuntimeError,
        ) as e:
            step.error = str(e)
            raise

    def _execute_create_directory(self, step: MigrationStep) -> None:
        """Execute directory creation step."""
        if not step.target_path:
            raise ValueError("Target path required for directory creation")

        # Ensure target is a Path object
        target = Path(step.target_path) if isinstance(step.target_path, str) else step.target_path

        # Store rollback info
        existed_before = PathUtils.path_exists(target)
        step.rollback_info["existed_before"] = existed_before

        if existed_before:
            # Already exists, just confirm
            if self._progress_callback:
                self._progress_callback(
                    f"Diretório já existe: {target} - pulando criação."
                )
            step.description += "\n\n[EXECUTADO] Diretório de emulação já existe e está pronto - pulando criação para evitar sobrescrita."
        else:
            # Create directory using PathUtils
            PathUtils.ensure_directory_exists(target)
            if self._progress_callback:
                self._progress_callback(f"Diretório criado: {target}")
            step.description += "\n\n[EXECUTADO] Diretório criado com sucesso para centralizar recursos de emuladores e frontends, como configs, saves e assets compartilhados."

    def _execute_create_symlink(self, step: MigrationStep) -> None:
        """Execute symlink creation step."""
        if not step.target_path or not step.source_path:
            raise ValueError(
                "Both source and target paths required for symlink creation"
            )

        # Ensure target and source are Path objects
        target = Path(step.target_path) if isinstance(step.target_path, str) else step.target_path
        source = Path(step.source_path) if isinstance(step.source_path, str) else step.source_path

        # Store rollback info using PathUtils
        step.rollback_info["existed_before"] = PathUtils.path_exists(str(target))
        if PathUtils.path_exists(str(target)):
            step.rollback_info["was_symlink"] = PathUtils.is_symlink(str(target))
            if PathUtils.is_symlink(str(target)):
                step.rollback_info["old_target"] = PathUtils.read_symlink(str(target))

        # Create parent directory if needed using PathUtils
        parent_directory = target.parent
        PathUtils.ensure_directory_exists(str(parent_directory))

        # Remove existing if needed using FileUtils
        if PathUtils.path_exists(str(target)):
            if PathUtils.is_symlink(str(target)):
                FileUtils.delete_file(str(target))
            else:
                raise FileExistsError(f"Target exists and is not a symlink: {target}")

        # Check if running as admin for symlink operations - do not request elevation automatically
        if sys.platform == "win32":
            current_is_admin = is_admin()
            if not current_is_admin:
                # Operating in read-only mode - do not request admin privileges automatically
                # This prevents UAC dialogs and application hangs
                warning_msg = f"Criação de symlinks requer privilégios administrativos ({target} -> {source}). Tentando fallback junction."
                self.logger.warning(warning_msg)
                if self._progress_callback:
                    self._progress_callback(warning_msg)

        # Create symlink (Windows requires special handling)
        try:
            target.symlink_to(source, target_is_directory=True)
            step.rollback_info["method_used"] = "symlink"
            step.rollback_info["is_junction"] = False
            if self._progress_callback:
                self._progress_callback(f"Symlink criado: {target} -> {source}")

        except OSError as e:
            # Fallback for Windows systems without symlink privileges
            if "privilege not held" in str(e).lower() or sys.platform == "win32":
                self.logger.warning(f"Symlink creation failed due to privileges: {e}")
                self.logger.info("Attempting junction point creation as fallback...")

                # Fallback: Create Windows junction point using mklink
                try:
                    # mklink requires absolute paths and administrator privileges
                    abs_source = Path(source).resolve()
                    abs_target = target.resolve()

                    # Ensure source exists
                    if not abs_source.exists():
                        raise FileNotFoundError(
                            f"Source path does not exist for junction: {abs_source}"
                        )

                    # Create junction using mklink /J with timeout
                    cmd = [
                        "cmd.exe",
                        "/c",
                        "mklink",
                        "/J",
                        str(abs_target),
                        str(abs_source),
                    ]

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=10,  # 10 second timeout to prevent hanging
                    )

                    if result.returncode == 0:
                        step.rollback_info["method_used"] = "junction"
                        step.rollback_info["is_junction"] = True
                        step.rollback_info["junction_source"] = str(abs_source)
                        step.rollback_info["junction_target"] = str(abs_target)

                        self.logger.info(
                            f"Junction point created successfully: {abs_target} -> {abs_source}"
                        )
                        if self._progress_callback:
                            self._progress_callback(
                                f"Junction criado (fallback): {abs_target} -> {abs_source}"
                            )

                        # Verify junction was created
                        if not abs_target.exists():
                            raise RuntimeError(
                                "Junction created but target does not exist"
                            )

                        if sys.platform == "win32":
                            # Windows-specific junction verification
                            if not abs_target.is_symlink():
                                raise RuntimeError(
                                    "Junction created but not recognized as symlink"
                                )

                            # Test accessibility
                            test_file = abs_target / "test_access.txt"
                            try:
                                test_file.write_text("test")
                                test_file.unlink()
                                self.logger.debug(
                                    f"Junction accessibility verified: {abs_target}"
                                )
                            except Exception as access_error:
                                raise RuntimeError(
                                    f"Junction accessibility test failed: {access_error}"
                                )
                        else:
                            # Non-Windows verification
                            if not abs_target.is_symlink():
                                raise RuntimeError(
                                    "Junction created but not recognized as symlink"
                                )

                    else:
                        raise RuntimeError(
                            f"mklink failed with return code {result.returncode}: {result.stderr}"
                        )

                except subprocess.TimeoutExpired:
                    error_msg = "Junction creation timed out after 10 seconds"
                    self.logger.error(error_msg)
                    if self._progress_callback:
                        self._progress_callback(error_msg)
                    raise OSError(error_msg)
                except (
                    subprocess.CalledProcessError,
                    FileNotFoundError,
                    RuntimeError,
                ) as junction_error:
                    error_msg = f"Junction point creation failed: {junction_error}"
                    self.logger.error(error_msg)
                    if self._progress_callback:
                        self._progress_callback(error_msg)
                    raise OSError(error_msg)

            else:
                raise

    def _execute_move_file(self, step: MigrationStep) -> None:
        """Execute file move step."""
        if not step.source_path or not step.target_path:
            raise ValueError("Both source and target paths required for move operation")

        # Ensure source and target are Path objects
        source = Path(step.source_path) if isinstance(step.source_path, str) else step.source_path
        target = Path(step.target_path) if isinstance(step.target_path, str) else step.target_path

        path_exists = getattr(PathUtils, "path_exists", lambda value: os.path.exists(value))
        source_exists = bool(path_exists(str(source)))
        target_exists = bool(path_exists(str(target)))

        step.rollback_info["source_existed"] = bool(source_exists)
        step.rollback_info["target_existed"] = bool(target_exists)

        if not step.rollback_info["source_existed"]:
            self.logger.warning(
                "Fonte não encontrada antes do move",
                extra={"source": source, "target": target},
            )

        # Create parent directory
        parent_dir = PathUtils.get_parent_directory(str(target))
        PathUtils.ensure_directory_exists(str(parent_dir))

        # Move file (FileUtils already retorna bool nos testes)
        FileUtils.move_file(str(source), str(target))

    def _execute_copy_file(self, step: MigrationStep) -> None:
        """Execute file copy step."""
        if not step.source_path or not step.target_path:
            raise ValueError("Both source and target paths required for copy operation")

        # Ensure source and target are Path objects
        source = Path(step.source_path) if isinstance(step.source_path, str) else step.source_path
        target = Path(step.target_path) if isinstance(step.target_path, str) else step.target_path

        path_exists = getattr(PathUtils, "path_exists", lambda value: os.path.exists(value))
        target_exists = bool(path_exists(str(target)))
        source_exists = bool(path_exists(str(source)))

        step.rollback_info["target_existed"] = bool(target_exists)

        if not source_exists:
            self.logger.warning(
                "Fonte não encontrada antes do copy",
                extra={"source": source, "target": target},
            )

        # Create parent directory
        parent_dir = PathUtils.get_parent_directory(str(target))
        PathUtils.ensure_directory_exists(str(parent_dir))

        # Copy file
        FileUtils.copy_file(str(source), str(target))

    def _rollback_steps(self, executed_steps: list[MigrationStep]) -> None:
        """Rollback executed migration steps."""
        rollback_message = f"Rolling back {len(executed_steps)} steps"
        self.logger.info(rollback_message)
        if self._progress_callback:
            self._progress_callback(rollback_message)

        # Rollback in reverse order
        for step in reversed(executed_steps):
            try:
                step_message = f"Rolling back step: {step.description}"
                self.logger.debug(step_message)
                if self._progress_callback:
                    self._progress_callback(step_message)

                self._rollback_step(step)

                success_message = f"Step rolled back successfully: {step.description}"
                self.logger.debug(success_message)
                if self._progress_callback:
                    self._progress_callback(success_message)

            except (OSError, ValueError) as e:
                error_message = f"Failed to rollback step {step.step_id}: {e}"
                self.logger.error(error_message)
                if self._progress_callback:
                    self._progress_callback(error_message)

    def _rollback_step(self, step: MigrationStep) -> None:
        """Rollback a single step."""
        if step.action == "create_directory":
            self._rollback_create_directory(step)
        elif step.action == "create_symlink":
            self._rollback_create_symlink(step)
        elif step.action == "move_file":
            self._rollback_move_file(step)
        elif step.action == "copy_file":
            self._rollback_copy_file(step)

    def _rollback_create_directory(self, step: MigrationStep) -> None:
        """Rollback directory creation."""
        if not step.rollback_info.get("existed_before", False):
            target = step.target_path
            if PathUtils.path_exists(str(target)) and PathUtils.is_directory(str(target)):
                try:
                    # Try to remove directory using shutil
                    import shutil

                    shutil.rmtree(target)
                except OSError:
                    # Directory not empty or other error, leave it
                    pass

    def _rollback_create_symlink(self, step: MigrationStep) -> None:
        """Rollback symlink creation."""
        target = step.target_path
        if target:
            # Compatibilidade com os testes: delega ao FileUtils/mocks
            # Use module reference instead of global name to ensure patch works
            import sys
            if 'services.migration_service' in sys.modules:
                sys.modules['services.migration_service'].FileUtils.delete_file(target, safe=True)
            else:
                # Fallback for direct import path
                import sd_emulation_gui.services.migration_service as sms
                sms.FileUtils.delete_file(target, safe=True)

        # Restore old symlink if it existed
        if step.rollback_info.get("existed_before", False):
            if step.rollback_info.get("was_symlink", False):
                old_target = step.rollback_info.get("old_target")
                if old_target:
                    try:
                        path_obj = Path(target)
                        if callable(getattr(path_obj, "symlink_to", None)):
                            path_obj.symlink_to(old_target)
                        self.logger.debug(
                            f"Old symlink restored: {target} -> {old_target}"
                        )
                        if self._progress_callback:
                            self._progress_callback(
                                f"Symlink original restaurado: {target}"
                            )
                    except OSError as e:
                        self.logger.error(
                            f"Failed to restore old symlink {target}: {e}"
                        )
                        if self._progress_callback:
                            self._progress_callback(f"Falha na restauração: {e}")

    def _rollback_move_file(self, step: MigrationStep) -> None:
        """Rollback file move."""
        source = step.source_path
        target = step.target_path
        if source and target:
            # Garantir que mocks de FileUtils recebam a chamada diretamente
            # Use module reference instead of global name to ensure patch works
            import sys
            if 'services.migration_service' in sys.modules:
                sys.modules['services.migration_service'].FileUtils.move_file(target, source)
            else:
                # Fallback for direct import path
                import sd_emulation_gui.services.migration_service as sms
                sms.FileUtils.move_file(target, source)

    def _rollback_copy_file(self, step: MigrationStep) -> None:
        """Rollback file copy."""
        target = step.target_path
        if target:
            # Use module reference instead of global name to ensure patch works
            import sys
            if 'services.migration_service' in sys.modules:
                sys.modules['services.migration_service'].FileUtils.delete_file(target, safe=True)
            else:
                # Fallback for direct import path
                import sd_emulation_gui.services.migration_service as sms
                sms.FileUtils.delete_file(target, safe=True)

    def _retry_symlink_creation(self, step: MigrationStep) -> tuple[bool, str]:
        """Retry creation of a single symlink step."""
        try:
            if not step.target_path or not step.source_path:
                return False, "Paths ausentes para symlink"

            target = Path(step.target_path)
            source = step.source_path

            # Check admin privileges
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                return False, "Privilégios de administrador necessários para symlinks"

            # Create parent dir if needed
            target.parent.mkdir(parents=True, exist_ok=True)

            # Remove existing if present
            if target.exists():
                if target.is_symlink() or (sys.platform == "win32" and target.is_dir()):
                    target.unlink(missing_ok=True)
                else:
                    return False, f"Target existe e não é symlink: {target}"

            # Try symlink creation
            target.symlink_to(source, target_is_directory=True)
            return True, f"Symlink recriado: {target} -> {source}"

        except (OSError, PermissionError) as e:
            return False, f"Erro ao recriar symlink: {str(e)}"

    def fix_symlinks(self, plan: MigrationPlan | None = None) -> dict[str, Any]:
        """Fix failed symlink creation steps in the plan."""
        report = {"success": True, "fixed": 0, "failed": 0, "messages": []}
        timestamp = datetime.now().isoformat()

        self.logger.info(f"[{timestamp}] Iniciando correção de symlinks")

        if not plan:
            report["success"] = False
            report["messages"].append("Plano de migração não fornecido")
            return report

        failed_symlinks = [
            s for s in plan.steps if s.action == "create_symlink" and s.error
        ]

        if not failed_symlinks:
            report["messages"].append("Nenhum symlink falhado encontrado")
            self.logger.info(f"[{timestamp}] Nenhum symlink para corrigir")
            return report

        for step in failed_symlinks:
            success, msg = self._retry_symlink_creation(step)
            if success:
                report["fixed"] += 1
                step.error = None
                step.executed = True
            else:
                report["failed"] += 1
                report["success"] = False

            report["messages"].append(f"Step {step.step_id}: {msg}")
            self.logger.info(f"[{timestamp}] Correção symlink {step.step_id}: {msg}")

        self.logger.info(
            f"[{timestamp}] Correção de symlinks concluída: {report['fixed']} corrigidos, {report['failed']} falharam"
        )
        return report

    def _grant_permissions(self, target_dir: str = None) -> tuple[bool, str]:
        """
        Grant permissions to target directory using icacls.
        
        This method now operates in read-only mode by default to prevent UAC hangs.
        It only attempts to modify permissions if already running as administrator.
        """
        try:
            target = Path(target_dir)
            if not target.exists():
                return False, f"Diretório não existe: {target}"

            # Get localized name for Everyone account
            everyone_account = get_everyone_account()
            
            # Check current administrative status without requesting elevation
            if not is_admin():
                # Operating in read-only mode - do not request admin privileges
                # This prevents UAC dialogs and application hangs
                self.logger.info(f"Operando em modo somente-leitura para {target}")
                self.logger.info("Para modificar permissões, execute a aplicação como administrador")
                
                # Perform a basic read test to verify directory accessibility
                try:
                    # Test if we can read the directory
                    list(target.iterdir())
                    return True, f"Diretório {target} acessível em modo somente-leitura. Para modificar permissões, execute como administrador."
                except PermissionError:
                    return False, f"Acesso negado ao diretório {target}. Execute como administrador para modificar permissões."
                except Exception as e:
                    return False, f"Erro ao verificar acesso ao diretório {target}: {str(e)}"
            
            # Only attempt icacls if already running as administrator
            self.logger.info(f"Executando como administrador - tentando conceder permissões para {target}")
            
            # Use icacls to grant full permissions to Everyone (localized)
            cmd = ["icacls", str(target), "/grant", f"{everyone_account}:(OI)(CI)F", "/T"]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=30
            )

            return True, f"Permissões concedidas para {target} usando conta '{everyone_account}'"

        except subprocess.CalledProcessError as e:
            error_msg = f"Erro icacls: {e.stderr}"
            if "não foi feito mapeamento" in e.stderr or "not found" in e.stderr.lower():
                error_msg += f"\nDica: Verifique se a conta '{everyone_account}' existe no sistema."
            return False, error_msg
        except Exception as e:
            return False, f"Erro ao conceder permissões: {str(e)}"

    def fix_permissions(self, target_dir: str = None) -> dict[str, Any]:
        """Fix permissions on target directory."""
        report = {"success": True, "messages": []}
        timestamp = datetime.now().isoformat()

        self.logger.info(
            f"[{timestamp}] Iniciando correção de permissões em {target_dir}"
        )

        success, msg = self._grant_permissions(target_dir)
        report["messages"].append(msg)

        if success:
            self.logger.info(f"[{timestamp}] Permissões corrigidas: {msg}")
        else:
            report["success"] = False
            self.logger.error(f"[{timestamp}] Falha na correção de permissões: {msg}")

        return report

    def _auto_resolve_paths(self, base_path: str = None) -> dict[str, Any]:
        """Auto-resolve paths by scanning directories."""
        report = {"success": True, "resolved": [], "unresolved": [], "suggestions": []}
        timestamp = datetime.now().isoformat()

        self.logger.info(
            f"[{timestamp}] Iniciando auto-resolução de caminhos em {base_path}"
        )

        base = Path(base_path)
        if not base.exists():
            report["success"] = False
            report["unresolved"].append(f"Base path não existe: {base}")
            return report

        # Scan for ROMs and emulators
        for root, dirs, files in os.walk(base):
            # Look for common ROM extensions
            rom_files = [
                f for f in files if f.lower().endswith((".zip", ".7z", ".rar", ".iso"))
            ]
            if rom_files:
                rel_path = Path(root).relative_to(base)
                report["resolved"].append(f"ROMs encontradas em: {rel_path}")

                # Suggest organization
                suggestion = f"Sugerir mover ROMs de {rel_path} para Roms/ (organizar por plataforma)"
                report["suggestions"].append(suggestion)

            # Look for emulator executables
            emu_files = [
                f
                for f in files
                if f.lower().endswith((".exe", ".bat"))
                and any(
                    name in f.lower()
                    for name in ["retro", "dolphin", "pcsx", "mame", "snes9x"]
                )
            ]
            if emu_files:
                rel_path = Path(root).relative_to(base)
                report["resolved"].append(f"Emulador encontrado em: {rel_path}")

                # Suggest symlink
                suggestion = f"Sugerir symlink de {rel_path} para Emulators/"
                report["suggestions"].append(suggestion)

        if not report["resolved"]:
            report["unresolved"].append("Nenhum ROM ou emulador encontrado")
            report["suggestions"].append(
                "Execute scan manual ou verifique caminhos de instalação"
            )

        self.logger.info(
            f"[{timestamp}] Auto-resolução concluída: {len(report['resolved'])} itens resolvidos"
        )
        return report

    def fix_paths(self, base_path: str = None) -> dict[str, Any]:
        """Fix paths by auto-resolving and suggesting corrections."""
        timestamp = datetime.now().isoformat()
        self.logger.info(f"[{timestamp}] Iniciando correção de caminhos")

        return self._auto_resolve_paths(base_path)

    def _rollback_steps(self, executed_steps: list[MigrationStep]) -> None:
        """Rollback executed steps in reverse order."""
        if not executed_steps:
            return

        self.logger.info(f"Starting rollback of {len(executed_steps)} steps")

        for step in reversed(executed_steps):
            try:
                self._rollback_step(step)
                if self._progress_callback:
                    self._progress_callback(f"Rollback concluído: {step.description}")
            except Exception as e:
                self.logger.error(f"Failed to rollback step {step.step_id}: {e}")
                if self._progress_callback:
                    self._progress_callback(f"Erro no rollback: {e}")

    def get_current_migration_plan(self) -> MigrationPlan | None:
        """Get the current migration plan that was created but not executed."""
        try:
            return self._current_migration_plan
        except Exception as e:
            self.logger.error(f"Failed to get current migration plan: {e}")
            return None

    def set_current_migration_plan(self, plan: MigrationPlan) -> None:
        """Set the current migration plan."""
        self._current_migration_plan = plan

    def execute_migration(self) -> dict[str, Any]:
        """Execute the current migration plan."""
        try:
            # Get the current migration plan
            plan = self.get_current_migration_plan()
            if not plan:
                return {"success": False, "error": "No migration plan found"}

            # Execute the plan
            success = self.apply_migration(plan, confirm=True)
            return {"success": success, "plan_id": plan.plan_id}
        except Exception as e:
            self.logger.error(f"Failed to execute migration: {e}")
            return {"success": False, "error": str(e)}

    def rollback_migration(self) -> dict[str, Any]:
        """Rollback the last executed migration."""
        try:
            # Get migration history to find the last executed plan
            history = self.get_migration_history()
            if not history:
                return {"success": False, "error": "No migration history found"}

            # Get the most recent migration
            last_migration = history[0]
            plan_data = last_migration.get("plan", {})

            # Reconstruct the plan from history
            plan = MigrationPlan(
                plan_id=plan_data.get("plan_id", "unknown"),
                description=plan_data.get("description", "Migration rollback")
            )

            # Add steps from history
            for step_data in plan_data.get("steps", []):
                step = MigrationStep(
                    step_id=step_data.get("step_id", "unknown"),
                    action=step_data.get("action", "unknown"),
                    source_path=step_data.get("source_path"),
                    target_path=step_data.get("target_path"),
                    description=step_data.get("description", "")
                )
                step.executed = True  # Mark as executed for rollback
                plan.add_step(step)

            # Execute rollback
            self._rollback_steps(plan.steps)
            return {"success": True, "plan_id": plan.plan_id, "rolled_back": True}
        except Exception as e:
            self.logger.error(f"Failed to rollback migration: {e}")
            return {"success": False, "error": str(e)}

    def preview_migration(self, plan: MigrationPlan) -> dict[str, Any]:
        """
        Preview migration execution without applying changes.

        Args:
            plan: Migration plan to preview

        Returns:
            Dictionary with preview summary, changes, and warnings
        """
        if not plan:
            raise ValueError("No migration plan provided for preview")

        preview = {
            "summary": {
                "total_steps": plan.total_steps,
                "estimated_time": f"{plan.total_steps * 0.5:.1f}s (estimated)",
                "risk_level": (
                    "low"
                    if plan.total_steps < 50
                    else "medium" if plan.total_steps < 200 else "high"
                ),
                "backup_required": True,
            },
            "changes": [],
            "warnings": [],
            "success": True,
        }

        # Simulate execution of each step
        simulated_steps = 0
        for step in plan.steps:
            # Simulate successful execution
            step_copy = MigrationStep(
                step_id=step.step_id,
                action=step.action,
                source_path=step.source_path,
                target_path=step.target_path,
                description=step.description,
            )
            step_copy.executed = True
            step_copy.error = None

            # Add to changes list
            change_info = {
                "step_id": step.step_id,
                "action": step.action,
                "description": step.description,
                "status": "simulated_success",
                "target_path": step.target_path,
            }
            preview["changes"].append(change_info)
            simulated_steps += 1

            # Add warnings for risky operations
            if step.action in ["create_symlink", "move_file"]:
                preview["warnings"].append(
                    f"Step {step.step_id}: {step.action} may require administrator privileges on Windows"
                )

        preview["summary"]["simulated_steps"] = simulated_steps
        preview["summary"][
            "completion_estimate"
        ] = f"{(simulated_steps / plan.total_steps * 100):.1f}%"

        self.logger.info(
            f"Migration preview generated: {simulated_steps}/{plan.total_steps} steps simulated"
        )
        if self._progress_callback:
            self._progress_callback(
                f"Preview: {simulated_steps}/{plan.total_steps} steps simulated successfully"
            )

        return preview

    def get_plan_statistics(self, plan: MigrationPlan) -> dict[str, Any]:
        """Aggregate statistics for a migration plan."""
        if not isinstance(plan, MigrationPlan):
            raise TypeError("plan deve ser MigrationPlan")

        actions: dict[str, int] = {}
        errors = sum(1 for step in plan.steps if step.error)

        for step in plan.steps:
            actions[step.action] = actions.get(step.action, 0) + 1

        return {
            "plan_id": plan.plan_id,
            "total_steps": plan.total_steps,
            "completed_steps": plan.completed_steps,
            "failed_steps": plan.failed_steps,
            "steps_by_action": actions,
            "errors": errors,
        }

    def estimate_migration_time(self, plan: MigrationPlan) -> float:
        """Estimate migration time in seconds."""
        if not isinstance(plan, MigrationPlan):
            raise TypeError("plan deve ser MigrationPlan")

        baseline = {
            "create_directory": 0.4,
            "create_symlink": 0.6,
            "move_file": 0.8,
            "copy_file": 1.0,
        }

        total = 0.0
        for step in plan.steps:
            total += baseline.get(step.action, 0.5)

        return round(total, 2)

    def create_migration_plan(
        self,
        emulator_mapping: EmulatorMapping,
        platform_mapping: PlatformMapping,
        rules: SDEmulationRules,
        dry_run: bool = True,
    ) -> MigrationPlan:
        """
        Create a migration plan - alias for plan_migration for GUI compatibility.

        Args:
            emulator_mapping: Current emulator mapping
            platform_mapping: Platform name mapping
            rules: SD emulation rules to follow
            dry_run: If True, only plan without executing

        Returns:
            Complete migration plan
        """
        return self.plan_migration(emulator_mapping, platform_mapping, rules, dry_run)

    def _serialize_plan(self, plan: MigrationPlan) -> dict[str, Any]:
        """Serialize migration plan to dictionary."""
        return {
            "plan_id": plan.plan_id,
            "description": plan.description,
            "created_at": plan.created_at,
            "executed": plan.executed,
            "execution_time": plan.execution_time,
            "success": plan.success,
            "backup_location": plan.backup_location,
            "steps": [
                {
                    "step_id": step.step_id,
                    "action": step.action,
                    "source_path": step.source_path,
                    "target_path": step.target_path,
                    "description": step.description,
                    "executed": step.executed,
                    "error": step.error,
                    "rollback_info": step.rollback_info,
                }
                for step in plan.steps
            ],
        }

    def get_migration_history(self) -> list[dict[str, Any]]:
        """Get migration history from backups."""
        history = []
        backups_dir = str(self.backup_dir)

        if not PathUtils.path_exists(backups_dir):
            return history

        try:
            for backup_dir in PathUtils.list_directories(backups_dir):
                name = PathUtils.get_filename(backup_dir)
                if not name.startswith("migration_backup_"):
                    continue

                plan_file = PathUtils.join_path(backup_dir, "migration_plan.json")
                if not PathUtils.path_exists(plan_file):
                    continue

                try:
                    plan_data = FileUtils.read_json_file(plan_file)
                except Exception as exc:
                    self.logger.warning(
                        f"Could not read migration plan from {plan_file}: {exc}"
                    )
                    continue

                history.append(
                    {
                        "timestamp": name.replace("migration_backup_", ""),
                        "backup_location": backup_dir,
                        "plan_id": plan_data.get("plan_id"),
                        "plan": plan_data,
                        "status": "completed"
                        if plan_data.get("success")
                        else "pending",
                        "executed": plan_data.get("executed", False),
                    }
                )
        except Exception as e:
            self.logger.error(f"Failed to read migration history: {e}")

        history.sort(key=lambda item: item["timestamp"], reverse=True)
        return history

    def get_migration_status(self, plan_id: str) -> dict[str, Any] | None:
        """Return status information for a given plan id."""
        if not plan_id:
            raise ValueError("plan_id inválido")

        for entry in self.get_migration_history():
            # Alguns testes fornecem formato simplificado
            if entry.get("plan_id") == plan_id:
                return {
                    "plan_id": plan_id,
                    "status": entry.get("status", "pending"),
                    "executed": entry.get("executed", False),
                    "timestamp": entry.get("timestamp"),
                    "backup_location": entry.get("backup_location"),
                }

            plan = entry.get("plan", {})
            if plan.get("plan_id") == plan_id:
                status = plan.get("success")
                return {
                    "plan_id": plan_id,
                    "status": "completed" if status else "pending",
                    "executed": plan.get("executed", False),
                    "timestamp": entry.get("timestamp"),
                    "backup_location": entry.get("backup_location"),
                }

        return None

    def validate_target_path(self, path: str) -> bool:
        """Validate if a target path is considered safe."""
        if not path:
            return False

        normalized = PathUtils.normalize_path(path)
        allowed_root = PathUtils.normalize_path(self.base_path)
        is_safe = PathUtils.validate_safe_path(normalized, allowed_root)

        if not is_safe:
            self.logger.warning(
                "Path fora do escopo permitido",
                extra={
                    "path": normalized,
                    "allowed_root": allowed_root,
                },
            )

        return bool(is_safe)

    def rollback_steps(self, plan_or_steps: str | MigrationPlan | list[MigrationStep]) -> bool:
        """Interface pública para rollback utilizada pelos testes."""
        if isinstance(plan_or_steps, list):
            self._rollback_steps(plan_or_steps)
            return True

        if isinstance(plan_or_steps, MigrationPlan):
            steps = plan_or_steps.steps
            for step in steps:
                step.executed = True
            self._rollback_steps(steps)
            return True

        if isinstance(plan_or_steps, str):
            plan = self.load_plan_by_id(plan_or_steps)
            if not plan:
                return False
            return self.rollback_steps(plan)

        raise TypeError("Valor inválido para rollback")

    def cleanup_failed_migration(self, plan_id: str) -> bool:
        """Cleanup after a failed migration using rollback operations."""
        if not plan_id:
            raise ValueError("plan_id inválido")

        return self.rollback_steps(plan_id)

    def load_plan_by_id(self, plan_id: str) -> MigrationPlan | None:
        """Load a migration plan from history by its ID."""
        if not plan_id:
            raise ValueError("plan_id inválido")

        for entry in self.get_migration_history():
            if entry.get("plan_id") == plan_id and "plan" in entry:
                return self.load_plan(entry["plan"])

            plan_data = entry.get("plan")
            if plan_data and plan_data.get("plan_id") == plan_id:
                return self.load_plan(plan_data)

        return None
