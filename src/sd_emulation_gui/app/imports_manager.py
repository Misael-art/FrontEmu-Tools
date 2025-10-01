"""
Import Manager for SD Emulation GUI

This module provides centralized import management and path configuration
to ensure consistent module resolution across the application.

Author: SD Emulation Team
"""

import sys
import os
from pathlib import Path
from typing import List, Optional

class ImportManager:
    """Centralized import and path management for SD Emulation GUI."""

    def __init__(self):
        """Initialize the import manager."""
        self._project_root: Optional[Path] = None
        self._src_path: Optional[Path] = None
        self._meta_config_path: Optional[Path] = None
        self._paths_added: List[str] = []

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        if self._project_root is None:
            # Find project root by looking for pyproject.toml or specific structure
            current_path = Path(__file__).resolve()

            # Try to find project root by looking for pyproject.toml
            for parent in [current_path] + list(current_path.parents):
                if (parent / "pyproject.toml").exists():
                    self._project_root = parent
                    break

            # Fallback: assume current file is in src/sd_emulation_gui/app/
            if self._project_root is None:
                self._project_root = current_path.parent.parent.parent

        return self._project_root

    @property
    def src_path(self) -> Path:
        """Get the src directory path."""
        if self._src_path is None:
            self._src_path = self.project_root / "src"
        return self._src_path

    @property
    def meta_config_path(self) -> Path:
        """Get the meta/config directory path."""
        if self._meta_config_path is None:
            self._meta_config_path = self.project_root / "meta" / "config"
        return self._meta_config_path

    def add_path(self, path: str) -> None:
        """Add a path to sys.path if not already present."""
        if path not in sys.path and path not in self._paths_added:
            sys.path.insert(0, path)
            self._paths_added.append(path)

    def configure_imports(self) -> None:
        """Configure all necessary paths for imports."""
        # Add src directory for main modules
        if self.src_path.exists():
            self.add_path(str(self.src_path))

        # Add meta/config directory for path configuration
        if self.meta_config_path.exists():
            self.add_path(str(self.meta_config_path))

        # Add project root for legacy compatibility
        self.add_path(str(self.project_root))

    def get_module_path(self, module_name: str) -> Optional[Path]:
        """Get the full path for a module."""
        # Try to find in src first
        src_module_path = self.src_path / "sd_emulation_gui" / module_name.replace(".", os.sep)
        if src_module_path.exists():
            return src_module_path

        # Try to find in meta/config
        meta_module_path = self.meta_config_path / module_name.replace(".", os.sep)
        if meta_module_path.exists():
            return meta_module_path

        # Try to find in project root
        root_module_path = self.project_root / module_name.replace(".", os.sep)
        if root_module_path.exists():
            return root_module_path

        return None

    def import_module_safe(self, module_name: str, fallback_class=None):
        """Safely import a module with fallback."""
        try:
            return __import__(module_name, fromlist=[''])
        except ImportError:
            if fallback_class:
                return fallback_class()
            raise

# Global instance
_import_manager = ImportManager()

def get_import_manager() -> ImportManager:
    """Get the global import manager instance."""
    return _import_manager

def configure_imports() -> None:
    """Configure imports for the application."""
    _import_manager.configure_imports()

def add_path(path: str) -> None:
    """Add a path to sys.path."""
    _import_manager.add_path(path)

def get_module_path(module_name: str) -> Optional[Path]:
    """Get the full path for a module."""
    return _import_manager.get_module_path(module_name)

def import_module_safe(module_name: str, fallback_class=None):
    """Safely import a module with fallback."""
    return _import_manager.import_module_safe(module_name, fallback_class)

def import_with_fallback(module_name: str, fallback_factory=None):
    """Import a module with proper fallback handling."""
    try:
        # Try direct import first
        return __import__(module_name, fromlist=[''])
    except ImportError:
        if fallback_factory:
            # Create a proper fallback instance
            service_name = module_name.split('.')[-1] if '.' in module_name else module_name
            return fallback_factory(service_name)
        raise

def get_required_modules():
    """Get list of required modules for the application."""
    return [
        'utils.base_service.BaseService',
        'utils.file_utils.FileUtils',
        'utils.path_utils.PathUtils',
        'utils.validation_utils.ValidationUtils',
        'domain.models.AppConfig',
        'domain.models.EmulatorMapping',
        'domain.models.PlatformMapping',
        'domain.sd_rules.SDEmulationRules',
        'domain.sd_rules.ComplianceReport',
        'adapters.config_loader.ConfigLoader',
        'adapters.fs_adapter.FileSystemAdapter',
        'services.validation_service.ValidationService',
        'services.migration_service.MigrationService',
        'services.report_service.ReportService',
        'services.sd_emulation_service.SDEmulationService',
        'services.coverage_service.CoverageService',
    ]

def validate_imports():
    """Validate that all required imports are working."""
    missing_imports = []

    for module_name in get_required_modules():
        try:
            __import__(module_name.replace('.', os.sep).replace('/', '.'))
        except ImportError:
            missing_imports.append(module_name)

    if missing_imports:
        print(f"⚠️ Missing imports detected: {missing_imports}")
        return False

    print("✅ All required imports are working")
    return True

# Auto-configure imports when module is loaded
configure_imports()
