"""
Migration Widget Component

This module provides the migration widget for the SD Emulation GUI application.
It allows planning, previewing, and executing configuration migrations.
"""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class MigrationWidget(QWidget):
    """Migration widget for planning and executing configuration migrations."""

    # Signals
    plan_requested = Signal()
    preview_requested = Signal()
    execute_requested = Signal()
    rollback_requested = Signal()
    clear_requested = Signal()
    fix_symlink_requested = Signal()
    fix_permissions_requested = Signal()
    fix_paths_requested = Signal()
    progress_updated = Signal(str)  # Signal for progress updates

    def __init__(self, parent: QWidget | None = None):
        """Initialize migration widget."""
        super().__init__(parent)
        self._migration_plan: Any | None = None
        self._migration_results: dict[str, Any] | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Controls section
        controls_group = QGroupBox("Migration Operations")
        controls_layout = QHBoxLayout(controls_group)

        plan_migration_btn = QPushButton("Plan Migration")
        plan_migration_btn.clicked.connect(self.plan_requested.emit)
        controls_layout.addWidget(plan_migration_btn)

        preview_btn = QPushButton("Preview Changes")
        preview_btn.clicked.connect(self.preview_requested.emit)
        controls_layout.addWidget(preview_btn)

        execute_btn = QPushButton("Execute Migration")
        execute_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; }"
        )
        execute_btn.clicked.connect(self._on_execute_clicked)
        controls_layout.addWidget(execute_btn)

        rollback_btn = QPushButton("Rollback")
        rollback_btn.setStyleSheet(
            "QPushButton { background-color: #f44336; color: white; }"
        )
        rollback_btn.clicked.connect(self._on_rollback_clicked)
        controls_layout.addWidget(rollback_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_requested.emit)
        controls_layout.addWidget(clear_btn)

        controls_layout.addStretch()
        layout.addWidget(controls_group)

        # Migration status section
        status_group = QGroupBox("Migration Status")
        status_layout = QHBoxLayout(status_group)

        self._status_label = QLabel(
            "Click 'Plan Migration' to create a migration plan..."
        )
        self._status_label.setWordWrap(True)
        status_layout.addWidget(self._status_label)

        layout.addWidget(status_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)  # Hidden by default
        progress_layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setWordWrap(True)
        self._progress_label.setVisible(False)  # Hidden by default
        progress_layout.addWidget(self._progress_label)

        layout.addWidget(progress_group)

        # Fix Errors section
        fix_group = QGroupBox("Fix Errors")
        fix_layout = QHBoxLayout(fix_group)

        retry_symlink_btn = QPushButton("Retry Symlink Creation")
        retry_symlink_btn.clicked.connect(self.fix_symlink_requested.emit)
        fix_layout.addWidget(retry_symlink_btn)

        grant_permissions_btn = QPushButton("Grant Permissions")
        grant_permissions_btn.clicked.connect(self.fix_permissions_requested.emit)
        fix_layout.addWidget(grant_permissions_btn)

        auto_resolve_btn = QPushButton("Auto-Resolve Paths")
        auto_resolve_btn.clicked.connect(self.fix_paths_requested.emit)
        fix_layout.addWidget(auto_resolve_btn)

        fix_layout.addStretch()
        layout.addWidget(fix_group)

        # Main content area with splitter
        main_splitter = QSplitter(Qt.Horizontal)

        # Left panel: Migration plan tree
        plan_group = QGroupBox("Migration Plan")
        plan_layout = QVBoxLayout(plan_group)

        self._plan_tree = QTreeWidget()
        self._plan_tree.setHeaderLabel("Operations")
        self._plan_tree.setRootIsDecorated(True)
        self._plan_tree.itemClicked.connect(self._on_item_clicked)
        plan_layout.addWidget(self._plan_tree)

        # Wizard para orientação passo a passo
        self._wizard_stack = QStackedWidget()
        self._wizard_stack.setCurrentIndex(0)

        # Página 1: Revise tree
        page1 = QWidget()
        page1_layout = QVBoxLayout(page1)
        page1_layout.addWidget(
            QLabel(
                "Página 1: Revise os 183 steps na tree à esquerda (agrupado por ação, detalhes em clique)."
            )
        )
        self._wizard_stack.addWidget(page1)

        # Página 2: Preview mudanças
        page2 = QWidget()
        page2_layout = QVBoxLayout(page2)
        page2_layout.addWidget(
            QLabel(
                "Página 2: Preview mudanças com summary, mudanças e warnings sem brancos."
            )
        )
        self._wizard_stack.addWidget(page2)

        # Página 3: Execute migração
        page3 = QWidget()
        page3_layout = QVBoxLayout(page3)
        page3_layout.addWidget(
            QLabel("Página 3: Execute migração ou use Fix Errors se necessário.")
        )
        self._wizard_stack.addWidget(page3)

        # Botões de navegação do wizard
        wizard_nav_layout = QHBoxLayout()
        self._prev_btn = QPushButton("Anterior")
        self._next_btn = QPushButton("Próximo")
        self._finish_btn = QPushButton("Finalizar")
        wizard_nav_layout.addWidget(self._prev_btn)
        wizard_nav_layout.addWidget(self._next_btn)
        wizard_nav_layout.addWidget(self._finish_btn)
        wizard_nav_layout.addStretch()

        # Conectar navegação
        self._next_btn.clicked.connect(self._next_wizard_page)
        self._prev_btn.clicked.connect(self._prev_wizard_page)
        self._finish_btn.clicked.connect(self._finish_wizard)

        # Mensagens de ajuda contextual
        self._help_label = QLabel(
            "O que fazer agora? 1. Revise os 183 steps na tree à esquerda (agrupado por ação, detalhes em clique). 2. Clique em 'Preview' para ver mudanças simuladas. 3. Se tudo estiver OK, inicie a migração com 'Run Migration'. Dúvidas? Verifique logs em sd-emulation-gui/logs/sd_emulation_gui.log ou feche instâncias antigas nos terminais 1-7 para um teste limpo."
        )
        self._help_label.setWordWrap(True)
        self._help_label.setStyleSheet("color: blue; font-style: italic;")

        # Layout principal do wizard
        wizard_layout = QVBoxLayout()
        wizard_layout.addWidget(self._wizard_stack)
        wizard_layout.addLayout(wizard_nav_layout)
        wizard_layout.addWidget(self._help_label)
        plan_layout.addLayout(wizard_layout)

        main_splitter.addWidget(plan_group)

        # Right panel: Operation details
        details_group = QGroupBox("Operation Details")
        details_layout = QVBoxLayout(details_group)

        self._details_text = QTextEdit()
        self._details_text.setReadOnly(True)
        self._details_text.setPlainText(
            "Select an operation from the migration plan to view details..."
        )
        details_layout.addWidget(self._details_text)

        main_splitter.addWidget(details_group)

        # Set splitter proportions
        main_splitter.setSizes([400, 400])
        layout.addWidget(main_splitter)

    def _connect_signals(self) -> None:
        """Connect UI signals."""
        pass

    def _on_execute_clicked(self) -> None:
        """Handle execute button click."""
        if not self._migration_plan:
            QMessageBox.warning(
                self, "No Plan", "Please create a migration plan first."
            )
            return

        reply = QMessageBox.question(
            self,
            "Execute Migration",
            "This will execute the migration plan and make changes to your configuration files.\n\n"
            "A backup will be created automatically. Do you want to proceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.execute_requested.emit()

    def _on_rollback_clicked(self) -> None:
        """Handle rollback button click."""
        reply = QMessageBox.question(
            self,
            "Rollback Migration",
            "This will rollback the last migration and restore from backup.\n\n"
            "Do you want to proceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.rollback_requested.emit()

    def set_migration_plan(self, plan: Any) -> None:
        """Set migration plan and update display."""
        self._migration_plan = plan
        self._update_plan_display()

    def set_migration_results(self, results: dict[str, Any]) -> None:
        """Set migration results and update display."""
        self._migration_results = results
        self._update_results_display()

    def clear_results(self) -> None:
        """Clear migration results."""
        self._migration_plan = None
        self._migration_results = None
        self._status_label.setText(
            "Click 'Plan Migration' to create a migration plan..."
        )
        self._plan_tree.clear()
        self._details_text.setPlainText(
            "Select an operation from the migration plan to view details..."
        )

    def _update_plan_display(self) -> None:
        """Update display with migration plan."""
        if not self._migration_plan:
            return

        plan = self._migration_plan

        # Update status
        if hasattr(plan, "steps") and plan.steps:
            step_count = len(plan.steps)
            self._status_label.setText(
                f"<b>Migration Plan Created</b> | "
                f"Steps: {step_count} | "
                f"Status: Ready for preview/execution"
            )

            # Populate tree with plan steps
            self._populate_migration_tree(plan)
        else:
            self._status_label.setText("<b>Migration Plan:</b> No steps required")

        self._status_label.setTextFormat(Qt.RichText)

    def _update_results_display(self) -> None:
        """Update display with migration results."""
        if not self._migration_results:
            return

        results = self._migration_results
        operation = results.get("operation", "unknown")

        if operation == "preview":
            preview = results.get("preview")
            self._show_migration_preview(preview)
        elif operation == "execute":
            result = results.get("result")
            if result and hasattr(result, "success") and result.success:
                self._status_label.setText(
                    f"<b>Migration Executed Successfully</b> | "
                    f"Backup ID: {getattr(result, 'backup_id', 'N/A')}"
                )
            else:
                self._status_label.setText(
                    "<b>Migration Failed</b> | " "Check details for error information"
                )
        elif operation == "rollback":
            result = results.get("result")
            if result and hasattr(result, "success") and result.success:
                self._status_label.setText("<b>Migration Rolled Back Successfully</b>")
            else:
                self._status_label.setText(
                    "<b>Rollback Failed</b> | Check details for error information"
                )

        self._status_label.setTextFormat(Qt.RichText)

    def _populate_migration_tree(self, plan) -> None:
        """Populate migration tree with plan steps."""
        self._plan_tree.clear()

        if not plan or not hasattr(plan, "steps") or not plan.steps:
            root_item = QTreeWidgetItem(self._plan_tree)
            root_item.setText(0, "No migration steps needed")
            return

        root_item = QTreeWidgetItem(self._plan_tree)
        root_item.setText(0, f"Migration Plan ({len(plan.steps)} steps)")
        root_item.setExpanded(True)

        # Group steps by action type
        steps_by_action = {}
        for step in plan.steps:
            action_type = step.action
            if action_type not in steps_by_action:
                steps_by_action[action_type] = []
            steps_by_action[action_type].append(step)

        for action_type, steps in steps_by_action.items():
            type_item = QTreeWidgetItem(root_item)
            type_item.setText(0, f"{action_type.upper()} ({len(steps)} steps)")
            type_item.setExpanded(True)

            for step in steps:
                step_item = QTreeWidgetItem(type_item)
                step_item.setText(
                    0,
                    (
                        step.description[:80] + "..."
                        if len(step.description) > 80
                        else step.description
                    ),
                )
                step_item.setData(0, Qt.UserRole, {"type": "step", "step": step})

    def _show_migration_preview(self, preview) -> None:
        """Show migration preview in details pane."""
        if not preview:
            self._details_text.setPlainText("No preview data available.")
            return

        details = []
        details.append("MIGRATION PREVIEW")
        details.append("=" * 50)
        details.append("")

        # Summary
        if "summary" in preview:
            summary = preview["summary"]
            details.append("SUMMARY:")
            details.append(f"  Total Steps: {summary.get('total_steps', 'N/A')}")
            details.append(f"  Estimated Time: {summary.get('estimated_time', 'N/A')}")
            details.append(f"  Risk Level: {summary.get('risk_level', 'N/A')}")
            details.append(
                f"  Backup Required: {'Yes' if summary.get('backup_required', False) else 'No'}"
            )
            if "simulated_steps" in summary:
                details.append(f"  Simulated Steps: {summary['simulated_steps']}")
                details.append(
                    f"  Completion Estimate: {summary.get('completion_estimate', 'N/A')}"
                )
            details.append("")

        # Changes
        if "changes" in preview and preview["changes"]:
            details.append("PLANNED CHANGES:")
            for change in preview["changes"]:
                action = change.get("action", "Unknown")
                description = change.get("description", "")
                target = change.get("target_path", "N/A")
                status = change.get("status", "simulated")
                details.append(f"  {action.upper()}: {description}")
                if target != "N/A":
                    details.append(f"    Target: {target}")
                details.append(f"    Status: {status}")
                details.append("")
            details.append("")

        # Warnings
        if "warnings" in preview and preview["warnings"]:
            details.append("⚠️ WARNINGS:")
            for warning in preview["warnings"]:
                details.append(f"  • {warning}")
            details.append("")

        self._details_text.setPlainText("\n".join(details))

    def _next_wizard_page(self) -> None:
        """Navigate to next wizard page."""
        current_index = self._wizard_stack.currentIndex()
        if current_index < self._wizard_stack.count() - 1:
            self._wizard_stack.setCurrentIndex(current_index + 1)
            self._update_wizard_navigation()

    def _prev_wizard_page(self) -> None:
        """Navigate to previous wizard page."""
        current_index = self._wizard_stack.currentIndex()
        if current_index > 0:
            self._wizard_stack.setCurrentIndex(current_index - 1)
            self._update_wizard_navigation()

    def _finish_wizard(self) -> None:
        """Finish wizard and reset to first page."""
        self._wizard_stack.setCurrentIndex(0)
        self._update_wizard_navigation()

    def _update_wizard_navigation(self) -> None:
        """Update wizard navigation buttons."""
        current_index = self._wizard_stack.currentIndex()
        total_pages = self._wizard_stack.count()

        self._prev_btn.setEnabled(current_index > 0)
        self._next_btn.setEnabled(current_index < total_pages - 1)
        self._finish_btn.setEnabled(current_index == total_pages - 1)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle tree item click."""
        item_data = item.data(0, Qt.UserRole)

        if not item_data or item_data.get("type") != "step":
            return

        step = item_data["step"]

        # Build detailed view
        details = []
        details.append(f"Step ID: {step.step_id}")
        details.append(f"Action: {step.action.upper()}")
        details.append(f"Status: {'Executed' if step.executed else 'Pending'}")
        if step.error:
            details.append(f"Error: {step.error}")
        details.append("=" * 50)
        details.append("")

        details.append("DESCRIPTION:")
        details.append(step.description)
        details.append("")

        if step.source_path:
            details.append(f"📁 SOURCE PATH: {step.source_path}")

        if step.target_path:
            details.append(f"📁 TARGET PATH: {step.target_path}")

        if step.rollback_info:
            details.append("🔄 ROLLBACK INFO:")
            for key, value in step.rollback_info.items():
                details.append(f"  {key}: {value}")

        self._details_text.setPlainText("\n".join(details))

    def _connect_signals(self) -> None:
        """Connect signals to slots."""
        # Signals are already connected in _setup_ui with direct emit calls
        pass

    def update_results(self, results: dict) -> None:
        """Update migration widget with new results."""
        self._migration_results = results
        self._update_results_display()

    def show_progress(self, message: str = "") -> None:
        """
        Show progress bar and optional message.
        
        Args:
            message: Optional progress message to display
        """
        self._progress_bar.setVisible(True)
        if message:
            self._progress_label.setText(message)
            self._progress_label.setVisible(True)
        else:
            self._progress_label.setVisible(False)

    def hide_progress(self) -> None:
        """Hide progress bar and message."""
        self._progress_bar.setVisible(False)
        self._progress_label.setVisible(False)

    def update_progress(self, message: str) -> None:
        """
        Update progress message and emit signal.
        
        Args:
            message: Progress message to display and emit
        """
        self._progress_label.setText(message)
        if not self._progress_label.isVisible():
            self._progress_label.setVisible(True)
        
        # Emit signal for external listeners
        self.progress_updated.emit(message)

    def set_progress_value(self, value: int, maximum: int = 100) -> None:
        """
        Set progress bar value and maximum.
        
        Args:
            value: Current progress value
            maximum: Maximum progress value
        """
        self._progress_bar.setMaximum(maximum)
        self._progress_bar.setValue(value)
        
        # Show progress bar if not visible
        if not self._progress_bar.isVisible():
            self._progress_bar.setVisible(True)
