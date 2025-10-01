"""
Validation ViewModel

This module provides the validation viewmodel for the SD Emulation GUI application.
It manages the state for the validation component.
"""

from PySide6.QtCore import QObject, Signal

from ...services.validation_service import ValidationSummary


class ValidationViewModel(QObject):
    """View model for the validation component."""

    # Signals for UI updates
    validation_results_updated = Signal(ValidationSummary)

    def __init__(self, parent: QObject | None = None):
        """Initialize the view model."""
        super().__init__(parent)
        self._validation_results: ValidationSummary | None = None

    @property
    def validation_results(self) -> ValidationSummary | None:
        """Get the current validation results."""
        return self._validation_results

    @validation_results.setter
    def validation_results(self, value: ValidationSummary) -> None:
        """Set the validation results."""
        self._validation_results = value
        self.validation_results_updated.emit(value)

    def clear_results(self) -> None:
        """Clear validation results."""
        self._validation_results = None
        self.validation_results_updated.emit(ValidationSummary())
