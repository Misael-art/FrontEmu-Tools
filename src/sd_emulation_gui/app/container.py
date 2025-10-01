"""
Application Container

This module provides dependency injection container for managing
service dependencies and application configuration.
"""

import sys
from functools import lru_cache
from pathlib import Path

# Add current directory to path for script execution
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Handle both module and script execution for imports_manager
try:
    # Try relative imports (when run as module)
    from .imports_manager import configure_imports, import_module_safe
except ImportError:
    try:
        # Fallback to absolute imports (when run as script)
        from imports_manager import configure_imports, import_module_safe
    except ImportError:
        # Final fallback - direct import
        import imports_manager
        configure_imports = imports_manager.configure_imports
        import_module_safe = imports_manager.import_module_safe

# Configure imports centrally
configure_imports()

# Import services directly with error handling
# First create fallback classes
class ConfigLoader:
    def __init__(self, base_path=None):
        self.base_path = base_path or str(Path(__file__).parent.parent.parent.parent / "config")
        
    def load_config(self, config_name: str) -> dict:
        """Load configuration file and return dict."""
        import json
        config_path = Path(self.base_path) / config_name
        
        # Return mock data for common configs if file doesn't exist
        if not config_path.exists():
            if "emulator_mapping" in config_name:
                return {
                    "version": "1.0.0",
                    "emulators": {
                        "retroarch": {
                            "systems": ["nes", "snes", "gb"],
                            "paths": {
                                "executable": "retroarch.exe",
                                "config": "retroarch.cfg"
                            }
                        }
                    }
                }
            elif "platform_mapping" in config_name:
                return {
                    "version": "1.0.0", 
                    "mappings": {
                        "nes": "Nintendo Entertainment System",
                        "snes": "Super Nintendo Entertainment System",
                        "gb": "Game Boy"
                    }
                }
            else:
                return {"version": "1.0.0", "data": {}}
        
        # Load actual config file if it exists
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ConfigLoader] Error loading {config_name}: {e}")
            return {"version": "1.0.0", "error": str(e)}
        
class FileSystemAdapter:
    def __init__(self, base_path=None):
        self.base_path = base_path

# Now try to import real service classes
try:
    # Import real services - use sys.path manipulation for reliability
    import sys
    from pathlib import Path
    
    # Ensure current project is in path
    current_dir = Path(__file__).parent.parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    # Try importing real services with specific error isolation
    try:
        from services.validation_service import ValidationService as RealValidationService
        ValidationService = RealValidationService
        print("[CONTAINER] ✅ ValidationService imported successfully")
    except Exception as e:
        print(f"[CONTAINER] ❌ ValidationService import failed: {e}")
        class ValidationService:
            def __init__(self, config_dir=None):
                self.config_dir = config_dir
                
    try:
        from services.coverage_service import CoverageService as RealCoverageService  
        CoverageService = RealCoverageService
        print("[CONTAINER] ✅ CoverageService imported successfully")
    except Exception as e:
        print(f"[CONTAINER] ❌ CoverageService import failed: {e}")
        class CoverageService:
            def __init__(self):
                pass
                
    try:
        from services.sd_emulation_service import SDEmulationService as RealSDEmulationService
        SDEmulationService = RealSDEmulationService  
        print("[CONTAINER] ✅ SDEmulationService imported successfully")
    except Exception as e:
        print(f"[CONTAINER] ❌ SDEmulationService import failed: {e}")
        class SDEmulationService:
            def __init__(self, architecture_doc_path=None):
                self.architecture_doc_path = architecture_doc_path
                
    try:
        from services.migration_service import MigrationService as RealMigrationService
        MigrationService = RealMigrationService
        print("[CONTAINER] ✅ MigrationService imported successfully")
    except Exception as e:
        print(f"[CONTAINER] ❌ MigrationService import failed: {e}")
        class MigrationService:
            def __init__(self, base_path=None, backup_dir=None):
                self.base_path = base_path
                self.backup_dir = backup_dir
                
    try:
        from services.report_service import ReportService as RealReportService
        ReportService = RealReportService
        print("[CONTAINER] ✅ ReportService imported successfully")
    except Exception as e:
        print(f"[CONTAINER] ❌ ReportService import failed: {e}")
        class ReportService:
            def __init__(self, reports_dir=None):
                self.reports_dir = reports_dir
    
    # Import new system services
    try:
        from services.system_info_service import SystemInfoService as RealSystemInfoService
        SystemInfoService = RealSystemInfoService
        print("[CONTAINER] ✅ SystemInfoService imported successfully")
    except Exception as e:
        print(f"[CONTAINER] ❌ SystemInfoService import failed: {e}")
        class SystemInfoService:
            def __init__(self, base_path=None):
                self.base_path = base_path
                
    try:
        from services.drive_manager_service import DriveManagerService as RealDriveManagerService
        DriveManagerService = RealDriveManagerService
        print("[CONTAINER] ✅ DriveManagerService imported successfully")
    except Exception as e:
        print(f"[CONTAINER] ❌ DriveManagerService import failed: {e}")
        class DriveManagerService:
            def __init__(self, base_path=None):
                self.base_path = base_path
                
    try:
        from services.legacy_detection_service import LegacyDetectionService as RealLegacyDetectionService
        LegacyDetectionService = RealLegacyDetectionService
        print("[CONTAINER] ✅ LegacyDetectionService imported successfully")
    except Exception as e:
        print(f"[CONTAINER] ❌ LegacyDetectionService import failed: {e}")
        class LegacyDetectionService:
            def __init__(self, base_path=None):
                self.base_path = base_path
                
    try:
        from services.system_stats_service import SystemStatsService as RealSystemStatsService
        SystemStatsService = RealSystemStatsService
        print("[CONTAINER] ✅ SystemStatsService imported successfully")
    except Exception as e:
        print(f"[CONTAINER] ❌ SystemStatsService import failed: {e}")
        class SystemStatsService:
            def __init__(self, base_path=None):
                self.base_path = base_path

except Exception as e:
    print(f"[CONTAINER] ❌ Critical import error: {e}")
    # Fallback classes are already defined above

# Simplified path management - use default paths
from pathlib import Path

class SimplePathResolver:
    """Simplified path resolver with default paths."""
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        
    def get_path(self, path_type: str) -> str:
        """Get path by type with sensible defaults."""
        paths = {
            "config_base_path": str(self.project_root / "config"),
            "base_drive": str(self.project_root),
            "backup_directory": str(self.project_root / "backup"),
            "reports_directory": str(self.project_root / "reports"),
            "architecture_doc_path": str(self.project_root / "sd-emulation.md")
        }
        return paths.get(path_type, str(self.project_root))
        
    def resolve_path(self, path_key: str):
        """Resolve path and return object with resolved_path attribute."""
        class ResolvedPath:
            def __init__(self, path: str):
                self.resolved_path = path
        
        # Map old path keys to new ones
        key_mapping = {
            "architecture_doc_path": "architecture_doc_path",
            "base_drive": "base_drive", 
            "base": "base_drive"
        }
        
        mapped_key = key_mapping.get(path_key, path_key)
        resolved = self.get_path(mapped_key)
        return ResolvedPath(resolved)


class ApplicationContainer:
    """Dependency injection container for the application."""

    def __init__(self):
        """Initialize the application container."""
        # Initialize simplified path resolver
        self._path_resolver = SimplePathResolver()

        # Get paths using simplified resolver
        self._config_base_path = self._path_resolver.get_path("config_base_path")
        self._fs_base_path = self._path_resolver.get_path("base_drive")
        self._backup_dir = self._path_resolver.get_path("backup_directory")
        self._reports_dir = self._path_resolver.get_path("reports_directory")
        self._architecture_doc_path = self._path_resolver.get_path("architecture_doc_path")
        
        print(f"[CONTAINER] Initialized with paths:")
        print(f"[CONTAINER]   config_base: {self._config_base_path}")
        print(f"[CONTAINER]   fs_base: {self._fs_base_path}")
        print(f"[CONTAINER]   backup: {self._backup_dir}")
        print(f"[CONTAINER]   reports: {self._reports_dir}")
        print(f"[CONTAINER]   arch_doc: {self._architecture_doc_path}")

    def wire(self) -> None:
        """Initialize and wire dependencies."""
        # Pre-create singletons to ensure proper initialization
        self.config_loader()
        self.fs_adapter()

        # Initialize existing services
        self.validation_service()
        self.coverage_service()
        self.sd_emulation_service()
        self.migration_service()
        self.report_service()
        
        # Initialize new system services
        self.system_info_service()
        self.drive_manager_service()
        self.legacy_detection_service()
        self.system_stats_service()

    # Adapters
    @lru_cache(maxsize=1)
    def config_loader(self) -> ConfigLoader:
        """Get configuration loader instance."""
        return ConfigLoader(base_path=self._config_base_path)

    @lru_cache(maxsize=1)
    def fs_adapter(self) -> FileSystemAdapter:
        """Get file system adapter instance."""
        return FileSystemAdapter(base_path=self._fs_base_path)

    # Services
    @lru_cache(maxsize=1)
    def validation_service(self) -> ValidationService:
        """Get validation service instance."""
        return ValidationService(config_dir=self._config_base_path)

    @lru_cache(maxsize=1)
    def coverage_service(self) -> CoverageService:
        """Get coverage service instance."""
        return CoverageService()

    @lru_cache(maxsize=1)
    def sd_emulation_service(self) -> SDEmulationService:
        """Get SD emulation service instance."""
        return SDEmulationService(architecture_doc_path=self._architecture_doc_path)

    @lru_cache(maxsize=1)
    def migration_service(self) -> MigrationService:
        """Get migration service instance."""
        return MigrationService(
            base_path=self._fs_base_path, backup_dir=self._backup_dir
        )

    @lru_cache(maxsize=1)
    def report_service(self) -> ReportService:
        """Get report service instance."""
        return ReportService(reports_dir=self._reports_dir)
    
    # New System Services
    @lru_cache(maxsize=1)
    def system_info_service(self) -> SystemInfoService:
        """Get system info service instance."""
        return SystemInfoService(base_path=self._fs_base_path)
    
    @lru_cache(maxsize=1)
    def drive_manager_service(self) -> DriveManagerService:
        """Get drive manager service instance."""
        return DriveManagerService(base_path=self._fs_base_path)
    
    @lru_cache(maxsize=1)
    def legacy_detection_service(self) -> LegacyDetectionService:
        """Get legacy detection service instance."""
        return LegacyDetectionService(base_path=self._fs_base_path)
    
    @lru_cache(maxsize=1)
    def system_stats_service(self) -> SystemStatsService:
        """Get system stats service instance."""
        return SystemStatsService(base_path=self._fs_base_path)

    # Configuration properties
    @property
    def config_base_path(self) -> str:
        """Get configuration base path."""
        return self._config_base_path

    @property
    def fs_base_path(self) -> str:
        """Get file system base path."""
        return self._fs_base_path

    @property
    def reports_dir(self) -> str:
        """Get reports directory."""
        return self._reports_dir

    @property
    def backup_dir(self) -> str:
        """Get backup directory."""
        return self._backup_dir

    @property
    def architecture_doc_path(self) -> str:
        """Get architecture document path."""
        return self._architecture_doc_path

    @property
    def path_resolver(self) -> SimplePathResolver:
        """Get path resolver instance."""
        return self._path_resolver
