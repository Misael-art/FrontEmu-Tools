"""
Dashboard Widget Component

This module provides the main dashboard widget for the SD Emulation GUI application.
It displays key metrics and quick actions for the user.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from domain.models import AppConfig


class DashboardWidget(QWidget):
    """Dashboard widget showing project overview and quick actions."""

    # Signals
    validate_requested = Signal()
    coverage_requested = Signal()
    compliance_requested = Signal()
    migration_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Initialize dashboard widget."""
        super().__init__(parent)
        self._config: AppConfig | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("SD Emulation Configuration Manager")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Metrics grid
        metrics_group = QGroupBox("Project Overview")
        metrics_layout = QGridLayout(metrics_group)
        metrics_layout.setSpacing(10)

        # Project status
        self._status_label = QLabel("Status: Loading...")
        self._status_label.setStyleSheet("font-weight: bold;")
        metrics_layout.addWidget(self._status_label, 0, 0)

        # Score
        self._score_label = QLabel("Score: --")
        metrics_layout.addWidget(self._score_label, 0, 1)

        # Functionalities
        self._functionalities_label = QLabel("Functionalities: --/--")
        metrics_layout.addWidget(self._functionalities_label, 1, 0)

        # Blockers
        self._blockers_label = QLabel("Blockers: --")
        metrics_layout.addWidget(self._blockers_label, 1, 1)

        layout.addWidget(metrics_group)

        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)

        validate_btn = QPushButton("Run Validation")
        validate_btn.setToolTip(
            "Validate all configuration files for errors and warnings.\n"
            "This will check JSON schemas, cross-references, and data integrity.\n"
            "Shortcut: Ctrl+V"
        )
        validate_btn.clicked.connect(self.validate_requested.emit)
        actions_layout.addWidget(validate_btn)

        coverage_btn = QPushButton("Analyze Coverage")
        coverage_btn.setToolTip(
            "Analyze platform and emulator coverage across your configuration.\n"
            "Identifies gaps and provides recommendations for improvement.\n"
            "Shortcut: Ctrl+C"
        )
        coverage_btn.clicked.connect(self.coverage_requested.emit)
        actions_layout.addWidget(coverage_btn)

        compliance_btn = QPushButton("Check Compliance")
        compliance_btn.setToolTip(
            "Verify compliance with SD emulation architecture rules.\n"
            "Ensures your setup follows best practices and standards.\n"
            "Shortcut: Ctrl+O"
        )
        compliance_btn.clicked.connect(self.compliance_requested.emit)
        actions_layout.addWidget(compliance_btn)

        migration_btn = QPushButton("Plan Migration")
        migration_btn.setToolTip(
            "Plan and execute safe migrations between configurations.\n"
            "Includes backup, rollback capabilities, and step-by-step guidance.\n"
            "Shortcut: Ctrl+M"
        )
        migration_btn.clicked.connect(self.migration_requested.emit)
        actions_layout.addWidget(migration_btn)

        actions_layout.addStretch()
        layout.addWidget(actions_group)

        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()

        # Description
        desc_label = QLabel(
            "This application helps you validate, analyze, and manage your SD card emulation configuration.\\n"
            "Use the tabs above to access different features:\\n\\n"
            "• Validation: Check configuration files for errors\\n"
            "• Coverage: Analyze platform and emulator coverage\\n"
            "• Compliance: Verify SD emulation architecture compliance\\n"
            "• Migration: Plan and execute safe configuration changes\\n\\n"
            "<b>Keyboard Shortcuts:</b>\\n"
            "• Ctrl+V: Run Validation\\n"
            "• Ctrl+C: Analyze Coverage\\n"
            "• Ctrl+O: Check Compliance\\n"
            "• Ctrl+M: Plan Migration"
            "• Migration: Plan and execute configuration migrations"
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        layout.addStretch()

    def _setup_keyboard_shortcuts(self) -> None:
        """Set up keyboard shortcuts for quick access to features."""
        # These shortcuts will be connected to the main window's methods
        # since we don't have direct access to the main window from here
        pass

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Signals are already connected in _setup_ui with direct emit calls
        pass

    def set_config(self, config: AppConfig) -> None:
        """Set application configuration and update display."""
        self._config = config
        self._update_display()

    def _update_display(self) -> None:
        """Update display with current configuration."""
        if not self._config:
            return

        # Update status
        status = self._config.status
        status_color = "green" if status == "production-ready" else "orange"
        self._status_label.setText(
            f"Status: <span style='color: {status_color}'>{status}</span>"
        )
        self._status_label.setTextFormat(Qt.RichText)

        # Update score
        self._score_label.setText(f"Score: {self._config.score}/100")

        # Update functionalities
        funcs = self._config.functionalities
        self._functionalities_label.setText(
            f"Functionalities: {funcs.implemented}/{funcs.total}"
        )

        # Update blockers
        blockers_count = len(self._config.blockers)
        critical_count = len(
            [b for b in self._config.blockers if b.severity in ["crítica", "alta"]]
        )
        self._blockers_label.setText(
            f"Blockers: {blockers_count} ({critical_count} critical)"
        )

        # Update blocker colors
        if critical_count > 0:
            self._blockers_label.setStyleSheet("color: red; font-weight: bold;")
        elif blockers_count > 0:
            self._blockers_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self._blockers_label.setStyleSheet("color: green; font-weight: bold;")
