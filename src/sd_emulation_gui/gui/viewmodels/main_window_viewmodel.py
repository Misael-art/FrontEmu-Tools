"""
Main Window ViewModel

This module provides the main window viewmodel for the SD Emulation GUI application.
It manages the overall application state and coordinates between components.
"""

from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from sd_emulation_gui.domain.models import AppConfig
from ...domain.sd_rules import ComplianceReport
from ...services.validation_service import ValidationSummary


class MainWindowViewModel(QObject):
    """ViewModel para a janela principal, gerenciando estado e lógica."""
    """View model for the main window."""

    # Signals for UI updates
    config_loaded = Signal(AppConfig)
    validation_results_updated = Signal(ValidationSummary)
    coverage_data_updated = Signal(dict)
    compliance_results_updated = Signal(ComplianceReport)
    migration_plan_updated = Signal(object)
    migration_results_updated = Signal(dict)
    status_message_updated = Signal(str)

    def __init__(self, parent: QObject | None = None):
        """Initialize the view model."""
        super().__init__(parent)
        self._config: AppConfig | None = None
        self._validation_results: ValidationSummary | None = None
        self._coverage_data: dict[str, Any] | None = None
        self._compliance_results: ComplianceReport | None = None
        self._migration_plan: Any | None = None
        self._migration_results: dict[str, Any] | None = None

    @property
    def config(self) -> AppConfig | None:
        """Get the current application configuration."""
        return self._config

    @config.setter
    def config(self, value: AppConfig) -> None:
        """Set the application configuration."""
        self._config = value
        self.config_loaded.emit(value)

    @property
    def validation_results(self) -> ValidationSummary | None:
        """Get the current validation results."""
        return self._validation_results

    @validation_results.setter
    def validation_results(self, value: ValidationSummary) -> None:
        """Set the validation results."""
        self._validation_results = value
        self.validation_results_updated.emit(value)

    @property
    def coverage_data(self) -> dict[str, Any] | None:
        """Get the current coverage data."""
        return self._coverage_data

    @coverage_data.setter
    def coverage_data(self, value: dict[str, Any]) -> None:
        """Set the coverage data."""
        self._coverage_data = value
        self.coverage_data_updated.emit(value)

    @property
    def compliance_results(self) -> ComplianceReport | None:
        """Get the current compliance results."""
        return self._compliance_results

    @compliance_results.setter
    def compliance_results(self, value: ComplianceReport) -> None:
        """Set the compliance results."""
        self._compliance_results = value
        self.compliance_results_updated.emit(value)

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

    @Slot(str)
    def update_status_message(self, message: str) -> None:
        """Update the status message."""
        self.status_message_updated.emit(message)

    def clear_validation_results(self) -> None:
        """Clear validation results."""
        self._validation_results = None
        self.validation_results_updated.emit(ValidationSummary())

    def clear_compliance_results(self) -> None:
        """Clear compliance results."""
        # Create an empty compliance report
        from ...domain.sd_rules import ComplianceReport

        empty_report = ComplianceReport(
            timestamp="",
            rules_version="",
            total_checks=0,
            compliant_checks=0,
            warning_checks=0,
            non_compliant_checks=0,
            checks=[],
            summary={},
            recommendations=[],
        )
        self._compliance_results = empty_report
        self.compliance_results_updated.emit(empty_report)

    def clear_migration_results(self) -> None:
        """Clear migration results."""
        self._migration_plan = None
        self._migration_results = None
        self.migration_plan_updated.emit(None)
        self.migration_results_updated.emit({})
