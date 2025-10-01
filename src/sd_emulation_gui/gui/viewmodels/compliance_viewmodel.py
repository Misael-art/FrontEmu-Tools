"""
Compliance ViewModel

This module provides the compliance viewmodel for the SD Emulation GUI application.
It manages the state for the compliance component.
"""

from PySide6.QtCore import QObject, Signal

from domain.sd_rules import ComplianceReport


class ComplianceViewModel(QObject):
    """View model for the compliance component."""

    # Signals for UI updates
    compliance_results_updated = Signal(ComplianceReport)

    def __init__(self, parent: QObject | None = None):
        """Initialize the view model."""
        super().__init__(parent)
        self._compliance_results: ComplianceReport | None = None

    @property
    def compliance_results(self) -> ComplianceReport | None:
        """Get the current compliance results."""
        return self._compliance_results

    @compliance_results.setter
    def compliance_results(self, value: ComplianceReport) -> None:
        """Set the compliance results."""
        self._compliance_results = value
        self.compliance_results_updated.emit(value)

    def clear_results(self) -> None:
        """Clear compliance results."""
        # Create an empty compliance report
        from domain.sd_rules import ComplianceReport

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
