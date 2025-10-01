"""
Coverage ViewModel

This module provides the coverage viewmodel for the SD Emulation GUI application.
It manages the state for the coverage component.
"""

from typing import Any

from PySide6.QtCore import QObject, Signal


class CoverageViewModel(QObject):
    """View model for the coverage component."""

    # Signals for UI updates
    coverage_data_updated = Signal(dict)

    def __init__(self, parent: QObject | None = None):
        """Initialize the view model."""
        super().__init__(parent)
        self._coverage_data: dict[str, Any] | None = None

    @property
    def coverage_data(self) -> dict[str, Any] | None:
        """Get the current coverage data."""
        return self._coverage_data

    @coverage_data.setter
    def coverage_data(self, value: dict[str, Any]) -> None:
        """Set the coverage data."""
        self._coverage_data = value
        self.coverage_data_updated.emit(value)

    def clear_data(self) -> None:
        """Clear coverage data."""
        self._coverage_data = None
        self.coverage_data_updated.emit({})
