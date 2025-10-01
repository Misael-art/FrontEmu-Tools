"""
GUI Widgets Module

Este módulo contém todos os widgets personalizados da aplicação,
incluindo widgets para informações do sistema, seleção de drives,
detecção de instalações legadas e estatísticas do sistema.
"""

# Widgets existentes
try:
    from .base_path_selector import BasePathSelector
except ImportError:
    BasePathSelector = None

try:
    from .migration_config_widget import MigrationConfigWidget
except ImportError:
    MigrationConfigWidget = None

# Novos widgets do sistema
try:
    from .system_info_widget import SystemInfoWidget
except ImportError:
    SystemInfoWidget = None

try:
    from .drive_selection_widget import DriveSelectionWidget
except ImportError:
    DriveSelectionWidget = None

try:
    from .legacy_detection_widget import LegacyDetectionWidget
except ImportError:
    LegacyDetectionWidget = None

try:
    from .system_stats_widget import SystemStatsWidget
except ImportError:
    SystemStatsWidget = None

# Lista de widgets disponíveis
__all__ = [
    'BasePathSelector',
    'MigrationConfigWidget',
    'SystemInfoWidget',
    'DriveSelectionWidget', 
    'LegacyDetectionWidget',
    'SystemStatsWidget'
]

# Remover widgets None da lista de exportação
__all__ = [widget for widget in __all__ if globals().get(widget) is not None]