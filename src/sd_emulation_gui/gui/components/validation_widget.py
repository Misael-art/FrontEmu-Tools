"""
Validation Widget Component

This module provides the validation widget for the SD Emulation GUI application.
It displays configuration file validation results and detailed error information.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.validation_service import ValidationSummary


class ValidationWidget(QWidget):
    """Validation widget showing configuration file validation results."""

    # Signals
    validate_requested = Signal()
    clear_requested = Signal()
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Initialize validation widget."""
        super().__init__(parent)
        self._validation_results: ValidationSummary | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Controls
        controls_layout = QHBoxLayout()

        run_validation_btn = QPushButton("Run Validation")
        run_validation_btn.clicked.connect(self.validate_requested.emit)
        controls_layout.addWidget(run_validation_btn)

        clear_btn = QPushButton("Clear Results")
        clear_btn.clicked.connect(self.clear_requested.emit)
        controls_layout.addWidget(clear_btn)

        export_btn = QPushButton("Export Report")
        export_btn.clicked.connect(self.export_requested.emit)
        controls_layout.addWidget(export_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Summary section
        summary_group = QGroupBox("Validation Summary")
        summary_layout = QHBoxLayout(summary_group)

        self._summary_label = QLabel(
            "Click 'Run Validation' to check configuration files..."
        )
        self._summary_label.setWordWrap(True)
        summary_layout.addWidget(self._summary_label)

        layout.addWidget(summary_group)

        # Main content area with splitter
        main_splitter = QSplitter(Qt.Horizontal)

        # Left panel: File tree
        files_group = QGroupBox("Configuration Files")
        files_layout = QVBoxLayout(files_group)

        self._files_tree = QTreeWidget()
        self._files_tree.setHeaderLabel("Files")
        self._files_tree.setRootIsDecorated(True)
        self._files_tree.itemClicked.connect(self._on_item_clicked)
        files_layout.addWidget(self._files_tree)

        main_splitter.addWidget(files_group)

        # Right panel: Details
        details_group = QGroupBox("File Details")
        details_layout = QVBoxLayout(details_group)

        self._details_text = QTextEdit()
        self._details_text.setReadOnly(True)
        self._details_text.setPlainText(
            "Select a file from the tree to view detailed validation results..."
        )
        details_layout.addWidget(self._details_text)

        main_splitter.addWidget(details_group)

        # Set splitter proportions
        main_splitter.setSizes([300, 500])
        layout.addWidget(main_splitter)

    def _connect_signals(self) -> None:
        """Connect UI signals."""
        pass

    def set_validation_results(self, results: ValidationSummary) -> None:
        """Set validation results and update display."""
        self._validation_results = results
        self._update_display()

    def clear_results(self) -> None:
        """Clear validation results."""
        self._validation_results = None
        self._summary_label.setText(
            "Click 'Run Validation' to check configuration files..."
        )
        self._files_tree.clear()
        self._details_text.setPlainText(
            "Select a file from the tree to view detailed validation results..."
        )

    def update_results(self, results: dict) -> None:
        """Update validation widget with new results."""
        self._validation_results = results
        self._update_display()

    def _update_display(self) -> None:
        """Update display with validation results."""
        if not self._validation_results:
            return

        # Handle both ValidationSummary object and dict format
        if isinstance(self._validation_results, dict):
            # Dict format from worker thread
            results = self._validation_results
            summary_data = results.get("summary", {})
            results_data = results.get("results", {})

            # Extract values with fallbacks
            overall_status = summary_data.get("overall_status", "UNKNOWN")
            total_files = summary_data.get("total_files", 0)
            valid_files = summary_data.get("valid_files", 0)
            files_with_warnings = summary_data.get("files_with_warnings", 0)
            files_with_errors = summary_data.get("files_with_errors", 0)
            coverage_percentage = summary_data.get("coverage_percentage", 0.0)
        else:
            # Object format (direct ValidationSummary)
            overall_status = getattr(self._validation_results, "overall_status", "UNKNOWN")
            total_files = getattr(self._validation_results, "total_files", 0)
            valid_files = getattr(self._validation_results, "valid_files", 0)
            files_with_warnings = getattr(self._validation_results, "files_with_warnings", 0)
            files_with_errors = getattr(self._validation_results, "files_with_errors", 0)
            coverage_percentage = getattr(self._validation_results, "coverage_percentage", 0.0)
            results_data = getattr(self._validation_results, "results", {})

        # Update summary
        status = overall_status.upper()
        status_color = (
            "green" if status == "VALID" else "orange" if status == "WARNING" else "red"
        )

        summary_text = (
            f"<b>Status:</b> <span style='color: {status_color}'>{status}</span> | "
            f"<b>Files:</b> {total_files} total, "
            f"{valid_files} valid, "
            f"{files_with_warnings} warnings, "
            f"{files_with_errors} errors | "
            f"<b>Coverage:</b> {coverage_percentage:.1f}%"
        )
        self._summary_label.setText(summary_text)
        self._summary_label.setTextFormat(Qt.RichText)

        # Populate file tree
        self._files_tree.clear()
        root_item = QTreeWidgetItem(self._files_tree)
        root_item.setText(0, "Configuration Files")
        root_item.setExpanded(True)

        # Sort files by status (errors first, then warnings, then success/valid)
        files_by_status = {"ERROR": [], "WARNING": [], "SUCCESS": [], "VALID": []}
        for filename, result in results_data.items():
            if isinstance(result, dict):
                status = result.get("status", "UNKNOWN").upper()
                errors = result.get("errors", [])
                warnings = result.get("warnings", [])
                info = result.get("info", [])
            else:
                status = getattr(result, "status", "UNKNOWN").upper()
                errors = getattr(result, "errors", [])
                warnings = getattr(result, "warnings", [])
                info = getattr(result, "info", [])

            # Map different status values to standard categories
            if status in ["ERROR", "FAILED"]:
                mapped_status = "ERROR"
            elif status in ["WARNING", "WARN"]:
                mapped_status = "WARNING"
            elif status in ["SUCCESS", "VALID", "OK"]:
                mapped_status = "SUCCESS"
            else:
                mapped_status = "VALID"  # fallback for unknown status

            files_by_status[mapped_status].append((filename, result))

        for status in ["ERROR", "WARNING", "SUCCESS", "VALID"]:
            if files_by_status[status]:
                status_item = QTreeWidgetItem(root_item)
                status_emoji = (
                    "❌" if status == "ERROR"
                    else "⚠️" if status == "WARNING"
                    else "✅" if status in ["SUCCESS", "VALID"]
                    else "✅"
                )
                status_item.setText(
                    0, f"{status_emoji} {status} ({len(files_by_status[status])})"
                )
                status_item.setData(
                    0, Qt.UserRole, {"type": "status", "status": status}
                )
                status_item.setExpanded(True)

                for filename, result in sorted(files_by_status[status]):
                    file_item = QTreeWidgetItem(status_item)
                    file_item.setText(0, filename)
                    file_item.setData(
                        0,
                        Qt.UserRole,
                        {"type": "file", "filename": filename, "result": result},
                    )

                    # Set color based on status
                    if status == "ERROR":
                        file_item.setForeground(0, QColor("red"))
                    elif status == "WARNING":
                        file_item.setForeground(0, QColor("orange"))
                    else:
                        file_item.setForeground(0, QColor("green"))

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle tree item click."""
        item_data = item.data(0, Qt.UserRole)

        if not item_data or item_data.get("type") != "file":
            return

        filename = item_data["filename"]
        result = item_data["result"]

        # Build detailed view
        details = []
        details.append(f"File: {filename}")

        # Get status and details based on result type
        if isinstance(result, dict):
            status = result.get("status", "UNKNOWN").upper()
            errors = result.get("errors", [])
            warnings = result.get("warnings", [])
            info = result.get("info", [])
        else:
            status = getattr(result, "status", "UNKNOWN").upper()
            errors = getattr(result, "errors", [])
            warnings = getattr(result, "warnings", [])
            info = getattr(result, "info", [])

        details.append(f"Status: {status}")
        details.append("=" * 50)
        details.append("")

        if errors:
            details.append("🔴 ERRORS:")
            for i, error in enumerate(errors, 1):
                details.append(f"  {i}. {error}")
            details.append("")

        if warnings:
            details.append("🟡 WARNINGS:")
            for i, warning in enumerate(warnings, 1):
                details.append(f"  {i}. {warning}")
            details.append("")

        if info:
            details.append("ℹ️ INFORMATION:")
            for i, info_item in enumerate(info, 1):
                details.append(f"  {i}. {info_item}")
            details.append("")

        if not errors and not warnings and not info:
            details.append("✅ This file passed all validation checks successfully!")

        self._details_text.setPlainText("\n".join(details))

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Signals are already connected in _setup_ui with direct emit calls
        pass
