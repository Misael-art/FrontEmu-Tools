"""Widgets modernizados para a interface do FrontEmu-Tools.

Este módulo contém todos os widgets da interface seguindo as especificações
de UI/UX e Clean Architecture."""

from .system_info_widget import SystemInfoWidget
from .drive_selection_widget import DriveSelectionWidget
from .legacy_detection_widget import LegacyDetectionWidget
from .system_stats_widget import SystemStatsWidget

__all__ = [
    "SystemInfoWidget",
    "DriveSelectionWidget", 
    "LegacyDetectionWidget",
    "SystemStatsWidget"
]