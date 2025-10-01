"""
Compliance Widget Component

This module provides the compliance widget for the SD Emulation GUI application.
It displays SD emulation architecture compliance results.
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

from domain.sd_rules import ComplianceReport


class ComplianceWidget(QWidget):
    """Compliance widget showing SD emulation architecture compliance results."""

    # Signals
    check_requested = Signal()
    clear_requested = Signal()
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Initialize compliance widget."""
        super().__init__(parent)
        self._compliance_results: ComplianceReport | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Controls
        controls_layout = QHBoxLayout()

        check_compliance_btn = QPushButton("Check Compliance")
        check_compliance_btn.clicked.connect(self.check_requested.emit)
        controls_layout.addWidget(check_compliance_btn)

        clear_btn = QPushButton("Clear Results")
        clear_btn.clicked.connect(self.clear_requested.emit)
        controls_layout.addWidget(clear_btn)

        export_btn = QPushButton("Export Report")
        export_btn.clicked.connect(self.export_requested.emit)
        controls_layout.addWidget(export_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Summary section
        summary_group = QGroupBox("Compliance Summary")
        summary_layout = QHBoxLayout(summary_group)

        self._summary_label = QLabel(
            "Click 'Check Compliance' to verify SD emulation architecture compliance..."
        )
        self._summary_label.setWordWrap(True)
        summary_layout.addWidget(self._summary_label)

        layout.addWidget(summary_group)

        # Main content area with splitter
        main_splitter = QSplitter(Qt.Horizontal)

        # Left panel: Rules tree
        rules_group = QGroupBox("Compliance Rules")
        rules_layout = QVBoxLayout(rules_group)

        self._rules_tree = QTreeWidget()
        self._rules_tree.setHeaderLabel("Rules")
        self._rules_tree.setRootIsDecorated(True)
        self._rules_tree.itemClicked.connect(self._on_item_clicked)
        rules_layout.addWidget(self._rules_tree)

        main_splitter.addWidget(rules_group)

        # Right panel: Details
        details_group = QGroupBox("Rule Details")
        details_layout = QVBoxLayout(details_group)

        self._details_text = QTextEdit()
        self._details_text.setReadOnly(True)
        self._details_text.setPlainText(
            "Select a rule from the tree to view detailed compliance information..."
        )
        details_layout.addWidget(self._details_text)

        main_splitter.addWidget(details_group)

        # Set splitter proportions
        main_splitter.setSizes([350, 450])
        layout.addWidget(main_splitter)

    def _connect_signals(self) -> None:
        """Connect UI signals."""
        pass

    def set_compliance_results(self, results: ComplianceReport) -> None:
        """Set compliance results and update display."""
        self._compliance_results = results
        self._update_display()

    def clear_results(self) -> None:
        """Clear compliance results."""
        self._compliance_results = None
        self._summary_label.setText(
            "Click 'Check Compliance' to verify SD emulation architecture compliance..."
        )
        self._rules_tree.clear()
        self._details_text.setPlainText(
            "Select a rule from the tree to view detailed compliance information..."
        )

    def update_results(self, results: dict) -> None:
        """Update compliance widget with new results."""
        self._compliance_results = results
        self._update_display()

    def _update_display(self) -> None:
        """Update display with compliance results."""
        if not self._compliance_results:
            return

        # Handle both direct ComplianceReport object and dict format
        if isinstance(self._compliance_results, dict):
            # Extract report from the results dict structure
            report_data = self._compliance_results.get("report", {})
        else:
            # If it's a ComplianceReport object, use it directly
            report_data = self._compliance_results

        # Update summary
        if isinstance(report_data, dict):
            # Dict format (from worker thread)
            compliance_percentage = report_data.get("compliance_percentage", 0)
            has_critical_issues = report_data.get("has_critical_issues", False)
            total_checks = report_data.get("total_checks", 0)
            compliant_checks = report_data.get("compliant_checks", 0)
            warning_checks = report_data.get("warning_checks", 0)
            non_compliant_checks = report_data.get("non_compliant_checks", 0)
            checks = report_data.get("checks", [])
        else:
            # Object format (direct ComplianceReport)
            compliance_percentage = getattr(report_data, "compliance_percentage", 0)
            has_critical_issues = getattr(report_data, "has_critical_issues", False)
            total_checks = getattr(report_data, "total_checks", 0)
            compliant_checks = getattr(report_data, "compliant_checks", 0)
            warning_checks = getattr(report_data, "warning_checks", 0)
            non_compliant_checks = getattr(report_data, "non_compliant_checks", 0)
            checks = getattr(report_data, "checks", [])

        status_color = (
            "green"
            if compliance_percentage >= 80
            else "orange" if compliance_percentage >= 60 else "red"
        )

        # Get critical issues status
        critical_status = "Yes" if has_critical_issues else "No"

        summary_text = (
            f"<b>Compliance:</b> <span style='color: {status_color}'>{compliance_percentage:.1f}%</span> | "
            f"<b>Checks:</b> {total_checks} total, "
            f"{compliant_checks} compliant, "
            f"{warning_checks} warnings, "
            f"{non_compliant_checks} non-compliant | "
            f"<b>Critical Issues:</b> {critical_status}"
        )
        self._summary_label.setText(summary_text)
        self._summary_label.setTextFormat(Qt.RichText)

        # Populate rules tree
        self._rules_tree.clear()
        root_item = QTreeWidgetItem(self._rules_tree)
        root_item.setText(0, "SD Emulation Rules")
        root_item.setExpanded(True)

        # Group rules by level (compliance status)
        rules_by_level = {"non_compliant": [], "warning": [], "compliant": []}
        for rule_check in checks:
            if isinstance(rule_check, dict):
                level = rule_check.get("level", "compliant")
            else:
                level = getattr(rule_check, "level", "compliant")
            if level in rules_by_level:
                rules_by_level[level].append(rule_check)

        for level in ["non_compliant", "warning", "compliant"]:
            if rules_by_level[level]:
                status_item = QTreeWidgetItem(root_item)
                status_emoji = (
                    "❌"
                    if level == "non_compliant"
                    else "⚠️" if level == "warning" else "✅"
                )
                status_name = (
                    "Non-Compliant" if level == "non_compliant" else level.title()
                )
                status_item.setText(
                    0, f"{status_emoji} {status_name} ({len(rules_by_level[level])})"
                )
                status_item.setData(0, Qt.UserRole, {"type": "status", "level": level})
                status_item.setExpanded(True)

                for rule_check in sorted(
                    rules_by_level[level],
                    key=lambda x: x.get("rule_name", "unknown"),
                ):
                    rule_item = QTreeWidgetItem(status_item)
                    rule_name = rule_check.get("rule_name", "Unknown Rule")
                    message = rule_check.get("message", "No message")
                    display_text = (
                        f"{rule_name}: {message[:60]}..."
                        if len(message) > 60
                        else f"{rule_name}: {message}"
                    )
                    rule_item.setText(0, display_text)
                    rule_item.setData(
                        0, Qt.UserRole, {"type": "rule", "rule_check": rule_check}
                    )

                    # Set color based on level
                    if level == "non_compliant":
                        rule_item.setForeground(0, QColor("red"))
                    elif level == "warning":
                        rule_item.setForeground(0, QColor("orange"))
                    else:
                        rule_item.setForeground(0, QColor("green"))

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle tree item click."""
        item_data = item.data(0, Qt.UserRole)

        if not item_data or item_data.get("type") != "rule":
            return

        rule_check = item_data["rule_check"]

        # Build detailed view
        details = []
        rule_name = rule_check.get("rule_name", "Unknown Rule")
        level_value = rule_check.get("level", "compliant")
        message = rule_check.get("message", "No message")

        details.append(f"Rule Name: {rule_name}")
        details.append(f"Compliance Level: {level_value.upper()}")
        details.append("=" * 60)
        details.append("")

        # Main message
        level_emoji = (
            "❌"
            if level_value == "non_compliant"
            else "⚠️" if level_value == "warning" else "✅"
        )
        details.append(f"{level_emoji} MESSAGE:")
        details.append(message)
        details.append("")

        # Additional details if available
        if rule_check.get("details"):
            details.append("📄 DETAILS:")
            details.append(rule_check["details"])
            details.append("")

        # Suggested action if available
        if rule_check.get("suggested_action"):
            details.append("💡 SUGGESTED ACTION:")
            details.append(rule_check.suggested_action)
            details.append("")

        # Affected paths if available
        affected_paths = rule_check.get("affected_paths", [])
        if affected_paths:
            details.append("📋 AFFECTED PATHS:")
            for path in affected_paths:
                details.append(f"  • {path}")
            details.append("")

        self._details_text.setPlainText("\n".join(details))

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Signals are already connected in _setup_ui with direct emit calls
        pass
