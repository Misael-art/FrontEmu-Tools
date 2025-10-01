"""
Dashboard ViewModel

This module provides the dashboard viewmodel for the SD Emulation GUI application.
It manages the state for the dashboard component.
"""

from PySide6.QtCore import QObject, Signal

from domain.models import AppConfig


class DashboardViewModel(QObject):
    """View model for the dashboard component."""

    # Signals for UI updates
    config_updated = Signal(AppConfig)

    def __init__(self, parent: QObject | None = None):
        """Initialize the view model."""
        super().__init__(parent)
        self._config: AppConfig | None = None

    @property
    def config(self) -> AppConfig | None:
        """Get the current application configuration."""
        return self._config

    @config.setter
    def config(self, value: AppConfig) -> None:
        """Set the application configuration."""
        self._config = value
        self.config_updated.emit(value)
