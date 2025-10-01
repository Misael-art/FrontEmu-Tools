"""
Migration ViewModel

This module provides the migration viewmodel for the SD Emulation GUI application.
It manages the state for the migration component.
"""

from typing import Any

from PySide6.QtCore import QObject, Signal

# Import path management system
try:
    from ...meta.config.path_config import PathConfigManager
    from ...meta.config.path_resolver import PathResolver
except ImportError:
    from meta.config.path_config import PathConfigManager
    from meta.config.path_resolver import PathResolver
from ...services.migration_service import MigrationService


class MigrationViewModel(QObject):
    """View model for the migration component."""

    # Signals for UI updates
    migration_plan_updated = Signal(object)
    migration_results_updated = Signal(dict)
    fix_completed = Signal(dict)

    def __init__(
        self, migration_service: MigrationService, parent: QObject | None = None
    ):
        """Initialize the view model."""
        super().__init__(parent)
        self._migration_service = migration_service
        self._migration_plan: Any | None = None
        self._migration_results: dict[str, Any] | None = None

        # Initialize path management
        self.path_config_manager = PathConfigManager()
        self.path_resolver = PathResolver()

    @property
    def migration_plan(self) -> Any | None:
        """Get the current migration plan."""
        return self._migration_plan

    @migration_plan.setter
    def migration_plan(self, value: Any) -> None:
        """Set the migration plan."""
        self._migration_plan = value
        self.migration_plan_updated.emit(value)

    @property
    def migration_results(self) -> dict[str, Any] | None:
        """Get the current migration results."""
        return self._migration_results

    @migration_results.setter
    def migration_results(self, value: dict[str, Any]) -> None:
        """Set the migration results."""
        self._migration_results = value
        self.migration_results_updated.emit(value)

    def clear_results(self) -> None:
        """Clear migration results."""
        self._migration_plan = None
        self._migration_results = None
        self.migration_plan_updated.emit(None)
        self.migration_results_updated.emit({})

    def fix_symlinks(self, plan: Any | None = None) -> None:
        """Fix symlinks via service."""
        from datetime import datetime

        timestamp = datetime.now().isoformat()

        try:
            result = self._migration_service.fix_symlinks(plan)
            result["action"] = "fix_symlinks"
            result["timestamp"] = timestamp
            self.fix_completed.emit(result)
        except Exception as e:
            error_result = {
                "success": False,
                "action": "fix_symlinks",
                "timestamp": timestamp,
                "error": str(e),
                "messages": [f"Erro na correção de symlinks: {e}"],
            }
            self.fix_completed.emit(error_result)

    def fix_permissions(self, target_dir: str = None) -> None:
        """Fix permissions via service."""
        from datetime import datetime

        timestamp = datetime.now().isoformat()

        # Use dynamic path if not provided
        if target_dir is None:
            target_dir = self.path_resolver.resolve_path("emulation_root").resolved_path

        try:
            result = self._migration_service.fix_permissions(target_dir)
            result["action"] = "fix_permissions"
            result["timestamp"] = timestamp
            self.fix_completed.emit(result)
        except Exception as e:
            error_result = {
                "success": False,
                "action": "fix_permissions",
                "timestamp": timestamp,
                "error": str(e),
                "messages": [f"Erro na correção de permissões: {e}"],
            }
            self.fix_completed.emit(error_result)

    def fix_paths(self, base_path: str = None) -> None:
        """Fix paths via service."""
        from datetime import datetime

        timestamp = datetime.now().isoformat()

        # Use dynamic path if not provided
        if base_path is None:
            base_path = self.path_resolver.resolve_path("base_drive").resolved_path

        try:
            result = self._migration_service.fix_paths(base_path)
            result["action"] = "fix_paths"
            result["timestamp"] = timestamp
            self.fix_completed.emit(result)
        except Exception as e:
            error_result = {
                "success": False,
                "action": "fix_paths",
                "timestamp": timestamp,
                "error": str(e),
                "messages": [f"Erro na correção de caminhos: {e}"],
            }
            self.fix_completed.emit(error_result)
