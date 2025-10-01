"""
Coverage Widget Component

This module provides the coverage widget for the SD Emulation GUI application.
It displays platform and emulator coverage analysis.
"""

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CoverageWidget(QWidget):
    """Coverage widget showing platform and emulator coverage analysis."""

    # Signals
    analyze_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Initialize coverage widget."""
        super().__init__(parent)
        self._coverage_data: dict[str, Any] | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Controls
        controls_layout = QHBoxLayout()

        analyze_btn = QPushButton("Analyze Coverage")
        analyze_btn.clicked.connect(self.analyze_requested.emit)
        controls_layout.addWidget(analyze_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Results display
        self._results_text = QTextEdit()
        self._results_text.setReadOnly(True)
        self._results_text.setPlainText(
            "Click 'Analyze Coverage' to view platform and emulator coverage..."
        )
        layout.addWidget(self._results_text)

    def _connect_signals(self) -> None:
        """Connect UI signals."""
        pass

    def set_coverage_data(self, data: dict[str, Any]) -> None:
        """Set coverage data and update display."""
        self._coverage_data = data
        self._update_display()

    def clear_data(self) -> None:
        """Clear coverage data."""
        self._coverage_data = None
        self._results_text.setPlainText(
            "Click 'Analyze Coverage' to view platform and emulator coverage..."
        )

    def update_coverage_data(self, data: dict) -> None:
        """Update coverage widget with new data."""
        self._coverage_data = data
        self._update_display()

    def _update_display(self) -> None:
        """Update display with coverage data."""
        if not self._coverage_data:
            return

        data = self._coverage_data
        overview = data.get("overview", {})

        # Build results text
        output = []
        output.append("=== COVERAGE ANALYSIS ===")
        output.append(f"Total platforms: {overview.get('total_platforms', 0)}")
        output.append(f"Covered platforms: {overview.get('covered_platforms', 0)}")
        output.append(
            f"Coverage percentage: {overview.get('coverage_percentage', 0):.1f}%"
        )
        output.append(f"Total emulators: {overview.get('total_emulators', 0)}")
        output.append(
            f"Configured emulators: {overview.get('configured_emulators', 0)}"
        )
        output.append(
            f"Configuration percentage: {overview.get('configuration_percentage', 0):.1f}%"
        )

        # Show some platform details
        platform_details = data.get("platform_details", {})
        covered_platforms = platform_details.get("covered", [])
        if covered_platforms:
            output.append("=== COVERED PLATFORMS (first 10) ===")
            for platform in covered_platforms[:10]:
                emulators = ", ".join(platform.get("emulators", []))
                output.append(
                    f"✅ {platform.get('full_name', '')} ({platform.get('short_name', '')})"
                )
                output.append(f"   Emulators: {emulators}")

        # Show gaps
        gaps = data.get("gaps_and_recommendations", {}).get("coverage_gaps", [])
        if gaps:
            output.append("=== COVERAGE GAPS (first 10) ===")
            for gap in gaps[:10]:
                output.append(f"❌ {gap}")

        self._results_text.setPlainText("\n".join(output))

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Signals are already connected in _setup_ui with direct emit calls
        pass
