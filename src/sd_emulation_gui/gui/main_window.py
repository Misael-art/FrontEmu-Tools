"""
Main Window GUI

This module provides the main window for the SD Emulation GUI application.
"""

import sys

try:
    from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QThread, Signal
    from PySide6.QtGui import QAccessible, QColor, QFont, QIcon, QPalette, QShortcut
    from PySide6.QtWidgets import (
        QDialog,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMenuBar,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSplitter,
        QStatusBar,
        QTabWidget,
        QTextEdit,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as e:
    # Graceful fallback if PySide6 not available
    print(f"PySide6 not available: {e}. Please install with: pip install PySide6")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Import with fallbacks for GUI components
try:
    from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QThread, Signal
    from PySide6.QtGui import QAccessible, QColor, QFont, QIcon, QPalette, QShortcut
    from PySide6.QtWidgets import (
        QDialog,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMenuBar,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSplitter,
        QStatusBar,
        QTabWidget,
        QTextEdit,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False

if PYSIDE6_AVAILABLE:
    # Import app components
    try:
        from sd_emulation_gui.app.container import ApplicationContainer
        from sd_emulation_gui.app.logging_config import get_logger, operation_context
        from sd_emulation_gui.gui.components.compliance_widget import ComplianceWidget
        from sd_emulation_gui.gui.components.coverage_widget import CoverageWidget
        from sd_emulation_gui.gui.components.dashboard_widget import DashboardWidget
        from sd_emulation_gui.gui.components.loader import LoaderWidget
        from sd_emulation_gui.gui.components.migration_widget import MigrationWidget
        from sd_emulation_gui.gui.components.navbar import Navbar
        from sd_emulation_gui.gui.components.validation_widget import ValidationWidget
        # Import new system widgets
        from sd_emulation_gui.gui.widgets.system_info_widget import SystemInfoWidget
        from sd_emulation_gui.gui.widgets.drive_selection_widget import DriveSelectionWidget
        from sd_emulation_gui.gui.widgets.legacy_detection_widget import LegacyDetectionWidget
        from sd_emulation_gui.gui.widgets.system_stats_widget import SystemStatsWidget
    except ImportError:
        # Fallback for GUI-less execution
        PYSIDE6_AVAILABLE = False


class HelpDialog(QDialog):
    """Diálogo de ajuda com FAQ."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajuda - SD Emulation GUI")
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        text = QTextEdit()
        text.setReadOnly(True)
        faq = """
FAQ - SD Emulation GUI

Como testar sem afetar setups existentes?
Feche terminais antigos (1-7) e use novo para execução do .bat.

Como ver logs?
Abra sd-emulation-gui/logs/sd_emulation_gui.log para erros/warnings.

Contexto de execução:
Rode start_sd_emulation_gui.bat no diretório base do projeto para iniciar com validação (7 arquivos), coverage (52.9%), compliance e planejamento de migração (183 steps).
"""
        text.setPlainText(faq)
        layout.addWidget(text)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)


# Import viewmodels
from sd_emulation_gui.gui.viewmodels.main_window_viewmodel import MainWindowViewModel


class ValidationWorker(QThread):
    """Worker thread for validation operations."""

    # Signals
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, container: ApplicationContainer):
        """Initialize validation worker."""
        super().__init__()
        self.container = container
        self.logger = get_logger(__name__)

    def run(self) -> None:
        """Run validation in background thread."""
        try:
            with operation_context("validation_worker", self.logger):
                self.progress.emit("Starting validation...")

                validation_service = self.container.validation_service()
                summary = validation_service.validate_all()

                self.progress.emit("Validation completed")
                # Use the to_dict method of ValidationSummary for consistent format
                self.finished.emit(summary.to_dict())

        except Exception as e:
            self.logger.error(f"Validation worker error: {e}")
            self.error.emit(str(e))


class ComplianceWorker(QThread):
    """Worker thread for compliance operations."""

    # Signals
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, container: ApplicationContainer):
        """Initialize compliance worker."""
        super().__init__()
        self.container = container
        self.logger = get_logger(__name__)

    def run(self) -> None:
        """Run compliance check in background thread."""
        try:
            with operation_context("compliance_worker", self.logger):
                self.progress.emit("Starting compliance check...")

                sd_service = self.container.sd_emulation_service()

                self.progress.emit("Parsing SD emulation rules...")
                # Parse rules from the architecture document
                # Get dynamic path for architecture document
                path_resolver = self.container.path_resolver
                architecture_doc_path = path_resolver.resolve_path(
                    "architecture_doc_path"
                ).resolved_path
                rules = sd_service.parse_rules_from_document(architecture_doc_path)

                self.progress.emit("Checking compliance...")
                # Check compliance against the current system
                # Use dynamic path resolution instead of hardcoded path
                path_resolver = self.container.path_resolver
                base_path = path_resolver.resolve_path("base_drive").resolved_path
                compliance_report = sd_service.check_compliance(str(base_path), rules)

                self.progress.emit("Compliance check completed")
                # Convert ComplianceReport to dict using Pydantic's model_dump method
                self.finished.emit({
                    "report": compliance_report.model_dump() if hasattr(compliance_report, 'model_dump') else compliance_report.dict(),
                    "rules": rules
                })

        except Exception as e:
            self.logger.error(f"Compliance worker error: {e}")
            self.error.emit(str(e))


class MigrationWorker(QThread):
    """Worker thread for migration operations."""

    # Signals
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, container: ApplicationContainer, operation: str, **kwargs):
        """Initialize migration worker."""
        super().__init__()
        self.container = container
        self.operation = operation
        self.kwargs = kwargs
        self.logger = get_logger(__name__)

    def _progress_callback(self, message: str) -> None:
        """Callback function to emit progress signals for migration service."""
        self.progress.emit(message)

    def run(self) -> None:
        """Run migration operation in background thread."""
        try:
            with operation_context(f"migration_{self.operation}", self.logger):
                migration_service = self.container.migration_service()

                # Set progress callback for migration service
                original_callback = migration_service.progress_callback
                migration_service.progress_callback = self._progress_callback

                try:
                    if self.operation == "plan":
                        self.progress.emit("Creating migration plan...")
                        # Load necessary configurations for migration planning
                        config_loader = self.container.config_loader()
                        sd_service = self.container.sd_emulation_service()

                        emulator_mapping = config_loader.load_config(
                            "emulator_mapping.json"
                        )
                        platform_mapping = config_loader.load_config(
                            "platform_mapping.json"
                        )
                        # Get dynamic path for architecture document
                        path_resolver = self.container.path_resolver
                        architecture_doc_path = path_resolver.resolve_path(
                            "architecture_doc_path"
                        ).resolved_path
                        rules = sd_service.parse_rules_from_document(
                            architecture_doc_path
                        )

                        plan = migration_service.plan_migration(
                            emulator_mapping, platform_mapping, rules
                        )
                        # Store the plan in the service for later use
                        migration_service.set_current_migration_plan(plan)
                        self.progress.emit("Migration plan created")
                        self.finished.emit({"operation": "plan", "plan": plan})
                    elif self.operation == "preview":
                        self.progress.emit("Generating migration preview...")
                        # Get current migration plan for preview
                        current_plan = migration_service.get_current_migration_plan()
                        if not current_plan:
                            self.error.emit("No migration plan found for preview")
                            return
                        
                        preview = migration_service.preview_migration(current_plan)
                        self.progress.emit("Migration preview generated")
                        self.finished.emit({"operation": "preview", "preview": preview})
                    elif self.operation == "execute":
                        self.progress.emit("Executing migration...")
                        # Execute the migration plan
                        result = migration_service.execute_migration()
                        self.progress.emit("Migration executed")
                        self.finished.emit({"operation": "execute", "result": result})
                    elif self.operation == "rollback":
                        self.progress.emit("Rolling back migration...")
                        # Rollback the migration
                        result = migration_service.rollback_migration()
                        self.progress.emit("Migration rolled back")
                        self.finished.emit({"operation": "rollback", "result": result})
                    else:
                        self.progress.emit("Unknown operation")
                        self.finished.emit({"status": "unknown"})
                except Exception as e:
                    self.logger.error(f"Erro na migração: {e}")
                    self.error.emit(str(e))
                finally:
                    if original_callback is not None:
                        migration_service.progress_callback = original_callback
                    self.progress.emit("Migration operation completed")
        except Exception as e:
            self.logger.error(f"Erro na migração principal: {e}")
            self.error.emit(str(e))
        finally:
            self.finished.emit({"status": "completed"})


class MainWindow(QMainWindow):
    """Classe principal da janela GUI para SD Emulation."""
    """Main window for SD Emulation GUI application."""

    def __init__(self, container: ApplicationContainer):
        """Initialize main window."""
        super().__init__()
        self.container = container
        self.logger = get_logger(__name__)

        # Initialize workers
        self.validation_worker = None
        self.compliance_worker = None
        self.migration_worker = None

        # Initialize viewmodel
        self.viewmodel = MainWindowViewModel(self)

        # Initialize UI
        self._setup_ui()
        self._setup_menu()
        self._connect_signals()

        self.logger.info("MainWindow initialized successfully")

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("SD Emulation GUI")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Navbar
        self.navbar = Navbar()
        layout.addWidget(self.navbar)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create and add tabs
        self._create_dashboard_tab()
        self._create_validation_tab()
        self._create_coverage_tab()
        self._create_compliance_tab()
        self._create_migration_tab()
        # Add new system tabs
        self._create_system_info_tab()
        self._create_drive_selection_tab()
        self._create_legacy_detection_tab()
        self._create_system_stats_tab()

        # Loader
        self.loader = LoaderWidget()
        layout.addWidget(self.loader)

        # Create status bar
        self.statusBar().showMessage("Pronto")

    def _setup_accessibility(self):
        """Setup accessibility features."""
        # WCAG AA contrast palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(255, 255, 255))
        palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(0, 123, 255))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)

        # Keyboard shortcuts
        QShortcut("Ctrl+Q", self, self.close)
        QShortcut("Ctrl+H", self, self._show_help)

        # Screen reader support
        self.setAccessibleName("Main Window - SD Emulation GUI")
        self.setAccessibleDescription(
            "Main application window for SD Emulation configuration management"
        )

        # Make widgets accessible
        self.tab_widget.setAccessibleName("Main Tab Widget")
        self.statusBar().setAccessibleName("Status Bar")
        self.navbar.setAccessibleName("Navigation Bar")
        self.loader.setAccessibleName("Loading Indicator")

    def _setup_menu(self) -> None:
        """Set up the menu bar."""
        menubar = self.menuBar()

        # Help menu
        help_menu = menubar.addMenu("Ajuda")

        # Help action
        help_action = help_menu.addAction("FAQ")
        help_action.triggered.connect(self._show_help)

        # About action
        about_action = help_menu.addAction("Sobre")
        about_action.triggered.connect(self._show_about)

    def _create_dashboard_tab(self) -> None:
        """Create dashboard tab."""
        self.dashboard_widget = DashboardWidget()
        self.tab_widget.addTab(self.dashboard_widget, "Dashboard")

    def _create_validation_tab(self) -> None:
        """Create validation tab."""
        self.validation_widget = ValidationWidget()
        self.tab_widget.addTab(self.validation_widget, "Validação")

    def _create_coverage_tab(self) -> None:
        """Create coverage tab."""
        self.coverage_widget = CoverageWidget()
        self.tab_widget.addTab(self.coverage_widget, "Cobertura")

    def _create_compliance_tab(self) -> None:
        """Create compliance tab."""
        self.compliance_widget = ComplianceWidget()
        self.tab_widget.addTab(self.compliance_widget, "Conformidade")

    def _create_migration_tab(self) -> None:
        """Create migration tab."""
        self.migration_widget = MigrationWidget()
        self.tab_widget.addTab(self.migration_widget, "Migração")
    
    def _create_system_info_tab(self) -> None:
        """Create system info tab."""
        self.system_info_widget = SystemInfoWidget(self.container)
        self.tab_widget.addTab(self.system_info_widget, "Info do Sistema")
    
    def _create_drive_selection_tab(self) -> None:
        """Create drive selection tab."""
        self.drive_selection_widget = DriveSelectionWidget(self.container)
        self.tab_widget.addTab(self.drive_selection_widget, "Seleção de Drive")
    
    def _create_legacy_detection_tab(self) -> None:
        """Create legacy detection tab."""
        self.legacy_detection_widget = LegacyDetectionWidget(self.container)
        self.tab_widget.addTab(self.legacy_detection_widget, "Detecção Legacy")
    
    def _create_system_stats_tab(self) -> None:
        """Create system stats tab."""
        self.system_stats_widget = SystemStatsWidget(self.container)
        self.tab_widget.addTab(self.system_stats_widget, "Estatísticas")

    def _connect_signals(self) -> None:
        """Connect signals between widgets and workers."""
        # Dashboard signals
        self.dashboard_widget.validate_requested.connect(self._run_validation)
        self.dashboard_widget.coverage_requested.connect(self._run_coverage)
        self.dashboard_widget.compliance_requested.connect(self._run_compliance)
        self.dashboard_widget.migration_requested.connect(self._run_migration)

        # Validation widget signals
        self.validation_widget.validate_requested.connect(self._run_validation)
        self.validation_widget.export_requested.connect(self._export_validation_report)

        # Coverage widget signals
        self.coverage_widget.analyze_requested.connect(self._run_coverage)

        # Compliance widget signals
        self.compliance_widget.check_requested.connect(self._run_compliance)
        self.compliance_widget.export_requested.connect(self._export_compliance_report)

        # Migration widget signals
        self.migration_widget.plan_requested.connect(self._run_migration)
        self.migration_widget.preview_requested.connect(self._run_migration_preview)
        self.migration_widget.execute_requested.connect(self._run_migration_execute)
        self.migration_widget.rollback_requested.connect(self._run_migration_rollback)
        self.migration_widget.clear_requested.connect(self._clear_migration_results)
        self.migration_widget.fix_symlink_requested.connect(self._fix_symlinks)
        self.migration_widget.fix_permissions_requested.connect(self._fix_permissions)
        self.migration_widget.fix_paths_requested.connect(self._fix_paths)
        # Connect progress signal to show/hide progress bar
        self.migration_widget.progress_updated.connect(self._on_migration_widget_progress)

    def _run_validation(self) -> None:
        """Run validation in background thread."""
        if self.validation_worker and self.validation_worker.isRunning():
            return

        self.validation_worker = ValidationWorker(self.container)
        self.validation_worker.finished.connect(self._on_validation_finished)
        self.validation_worker.error.connect(self._on_validation_error)
        self.validation_worker.progress.connect(self._on_validation_progress)
        self.validation_worker.start()

        self.statusBar().showMessage("Executando validação...")

    def _run_coverage(self) -> None:
        """Run coverage analysis."""
        try:
            coverage_service = self.container.coverage_service()
            coverage_data = coverage_service.analyze_coverage()
            self.coverage_widget.update_coverage_data(coverage_data)
            self.statusBar().showMessage("Análise de cobertura concluída")
        except Exception as e:
            self.logger.error(f"Coverage analysis error: {e}")
            QMessageBox.warning(self, "Erro", f"Erro na análise de cobertura: {e}")

    def _run_compliance(self) -> None:
        """Run compliance check in background thread."""
        if self.compliance_worker and self.compliance_worker.isRunning():
            return

        self.compliance_worker = ComplianceWorker(self.container)
        self.compliance_worker.finished.connect(self._on_compliance_finished)
        self.compliance_worker.error.connect(self._on_compliance_error)
        self.compliance_worker.progress.connect(self._on_compliance_progress)
        self.compliance_worker.start()

        self.statusBar().showMessage("Verificando conformidade...")

    def _run_migration(self) -> None:
        """Run migration planning in background thread."""
        if self.migration_worker and self.migration_worker.isRunning():
            return

        # Show progress bar
        self.migration_widget.show_progress()
        
        self.migration_worker = MigrationWorker(self.container, "plan")
        self.migration_worker.finished.connect(self._on_migration_finished)
        self.migration_worker.error.connect(self._on_migration_error)
        self.migration_worker.progress.connect(self._on_migration_progress)
        self.migration_worker.start()

        self.statusBar().showMessage("Criando plano de migração...")

    def _run_migration_execute(self) -> None:
        """Run migration execution in background thread."""
        if self.migration_worker and self.migration_worker.isRunning():
            return

        # Show progress bar
        self.migration_widget.show_progress()

        self.migration_worker = MigrationWorker(self.container, "execute")
        self.migration_worker.finished.connect(self._on_migration_finished)
        self.migration_worker.error.connect(self._on_migration_error)
        self.migration_worker.progress.connect(self._on_migration_progress)
        self.migration_worker.start()

        self.statusBar().showMessage("Executando migração...")

    def _run_migration_rollback(self) -> None:
        """Run migration rollback in background thread."""
        if self.migration_worker and self.migration_worker.isRunning():
            return

        # Show progress bar
        self.migration_widget.show_progress()

        self.migration_worker = MigrationWorker(self.container, "rollback")
        self.migration_worker.finished.connect(self._on_migration_finished)
        self.migration_worker.error.connect(self._on_migration_error)
        self.migration_worker.progress.connect(self._on_migration_progress)
        self.migration_worker.start()

        self.statusBar().showMessage("Executando rollback...")

    def _run_migration_preview(self) -> None:
        """Run migration preview in background thread."""
        if self.migration_worker and self.migration_worker.isRunning():
            return

        # Show progress bar
        self.migration_widget.show_progress()

        self.migration_worker = MigrationWorker(self.container, "preview")
        self.migration_worker.finished.connect(self._on_migration_finished)
        self.migration_worker.error.connect(self._on_migration_error)
        self.migration_worker.progress.connect(self._on_migration_progress)
        self.migration_worker.start()

        self.statusBar().showMessage("Gerando preview da migração...")

    def _clear_migration_results(self) -> None:
        """Clear migration results from the widget."""
        self.migration_widget.clear_results()
        self.statusBar().showMessage("Resultados da migração limpos")

    def _fix_symlinks(self) -> None:
        """Fix symlink creation issues."""
        try:
            migration_service = self.container.migration_service()
            current_plan = migration_service.get_current_migration_plan()
            
            if not current_plan:
                QMessageBox.information(
                    self, "No Plan", "Nenhum plano de migração encontrado. Crie um plano primeiro."
                )
                return
            
            result = migration_service.fix_symlinks(current_plan)
            
            if result.get("success", False):
                message = f"Symlinks corrigidos: {result.get('fixed', 0)} de {result.get('fixed', 0) + result.get('failed', 0)}"
                QMessageBox.information(self, "Sucesso", message)
            else:
                message = f"Erro na correção de symlinks: {result.get('messages', ['Erro desconhecido'])[0]}"
                QMessageBox.warning(self, "Erro", message)
                
            self.statusBar().showMessage(f"Correção de symlinks concluída: {result.get('fixed', 0)} corrigidos")
            
        except Exception as e:
            self.logger.error(f"Error fixing symlinks: {e}")
            QMessageBox.warning(self, "Erro", f"Erro na correção de symlinks: {e}")
            self.statusBar().showMessage("Erro na correção de symlinks")

    def _fix_permissions(self) -> None:
        """Fix permission issues."""
        try:
            migration_service = self.container.migration_service()
            path_resolver = self.container.path_resolver
            emulation_root = path_resolver.resolve_path("emulation_root").resolved_path
            
            result = migration_service.fix_permissions(emulation_root)
            
            if result.get("success", False):
                message = "\n".join(result.get("messages", ["Permissões corrigidas com sucesso"]))
                QMessageBox.information(self, "Sucesso", message)
            else:
                message = "\n".join(result.get("messages", ["Erro desconhecido"]))
                QMessageBox.warning(self, "Erro", message)
                
            self.statusBar().showMessage("Correção de permissões concluída")
            
        except Exception as e:
            self.logger.error(f"Error fixing permissions: {e}")
            QMessageBox.warning(self, "Erro", f"Erro na correção de permissões: {e}")
            self.statusBar().showMessage("Erro na correção de permissões")

    def _fix_paths(self) -> None:
        """Fix path resolution issues."""
        try:
            migration_service = self.container.migration_service()
            path_resolver = self.container.path_resolver
            base_path = path_resolver.resolve_path("base_drive").resolved_path
            
            result = migration_service.fix_paths(base_path)
            
            if result.get("success", False):
                resolved = result.get("resolved", [])
                suggestions = result.get("suggestions", [])
                
                message = f"Auto-resolução concluída:\n\n"
                message += f"Itens encontrados: {len(resolved)}\n"
                if resolved:
                    message += "\n".join(resolved[:5])  # Show first 5 results
                    if len(resolved) > 5:
                        message += f"\n... e mais {len(resolved) - 5} itens"
                
                if suggestions:
                    message += f"\n\nSugestões ({len(suggestions)}):\n"
                    message += "\n".join(suggestions[:3])  # Show first 3 suggestions
                    if len(suggestions) > 3:
                        message += f"\n... e mais {len(suggestions) - 3} sugestões"
                
                QMessageBox.information(self, "Auto-resolução de Caminhos", message)
            else:
                unresolved = result.get("unresolved", [])
                message = f"Problemas encontrados:\n\n"
                message += "\n".join(unresolved)
                QMessageBox.warning(self, "Problemas na Resolução", message)
                
            self.statusBar().showMessage(f"Auto-resolução concluída: {len(result.get('resolved', []))} itens encontrados")
            
        except Exception as e:
            self.logger.error(f"Error fixing paths: {e}")
            QMessageBox.warning(self, "Erro", f"Erro na correção de caminhos: {e}")
            self.statusBar().showMessage("Erro na correção de caminhos")

    def _export_validation_report(self) -> None:
        """Export validation results to file."""
        try:
            # Get validation results from the widget
            validation_results = getattr(self.validation_widget, '_validation_results', None)
            if not validation_results:
                QMessageBox.information(
                    self, "No Results", "No validation results to export. Please run validation first."
                )
                return

            # Create export service
            export_service = self.container.report_service()

            # Export to file
            export_path = export_service.export_validation_report(validation_results)
            QMessageBox.information(
                self, "Export Complete", f"Validation report exported to:\n{export_path}"
            )
            self.statusBar().showMessage(f"Validation report exported: {export_path}")
        except Exception as e:
            self.logger.error(f"Failed to export validation report: {e}")
            QMessageBox.warning(
                self, "Export Error", f"Failed to export validation report: {e}"
            )
            self.statusBar().showMessage("Erro na exportação do relatório de validação")

    def _export_compliance_report(self) -> None:
        """Export compliance results to file."""
        try:
            # Get compliance results from the widget
            compliance_results = getattr(self.compliance_widget, '_compliance_results', None)
            if not compliance_results:
                QMessageBox.information(
                    self, "No Results", "No compliance results to export. Please run compliance check first."
                )
                return

            # Create export service
            export_service = self.container.report_service()

            # Export to file
            export_path = export_service.export_compliance_report(compliance_results)
            QMessageBox.information(
                self, "Export Complete", f"Compliance report exported to:\n{export_path}"
            )
            self.statusBar().showMessage(f"Compliance report exported: {export_path}")
        except Exception as e:
            self.logger.error(f"Failed to export compliance report: {e}")
            QMessageBox.warning(
                self, "Export Error", f"Failed to export compliance report: {e}"
            )
            self.statusBar().showMessage("Erro na exportação do relatório de conformidade")

    def _on_validation_finished(self, results: dict) -> None:
        """Handle validation completion."""
        self.validation_widget.update_results(results)
        self.statusBar().showMessage("Validação concluída")

    def _on_validation_error(self, error: str) -> None:
        """Handle validation error."""
        self.logger.error(f"Validation error: {error}")
        QMessageBox.warning(
            self, "Erro de Validação", f"Erro durante validação: {error}"
        )
        self.statusBar().showMessage("Erro na validação")

    def _on_validation_progress(self, message: str) -> None:
        """Handle validation progress."""
        self.statusBar().showMessage(message)

    def _on_compliance_finished(self, results: dict) -> None:
        """Handle compliance check completion."""
        self.compliance_widget.update_results(results)
        self.statusBar().showMessage("Verificação de conformidade concluída")

    def _on_compliance_error(self, error: str) -> None:
        """Handle compliance check error."""
        self.logger.error(f"Compliance error: {error}")
        QMessageBox.warning(
            self, "Erro de Conformidade", f"Erro durante verificação: {error}"
        )
        self.statusBar().showMessage("Erro na verificação de conformidade")

    def _on_compliance_progress(self, message: str) -> None:
        """Handle compliance check progress."""
        self.statusBar().showMessage(message)

    def _on_migration_finished(self, results: dict) -> None:
        """Handle migration operation completion."""
        # Hide progress bar
        self.migration_widget.hide_progress()
        
        operation = results.get("operation", "unknown")
        
        if operation == "plan" and "plan" in results:
            # Handle migration plan creation
            self.migration_widget.set_migration_plan(results["plan"])
            self.statusBar().showMessage("Plano de migração criado")
        elif operation == "preview" and "preview" in results:
            # Handle migration preview
            self.migration_widget.set_migration_results(results)
            self.statusBar().showMessage("Preview de migração gerado")
        elif operation in ["execute", "rollback"]:
            # Handle execution/rollback results
            self.migration_widget.set_migration_results(results)
            if operation == "execute":
                self.statusBar().showMessage("Migração executada")
            else:
                self.statusBar().showMessage("Rollback executado")
        else:
            # Fallback for legacy format
            self.migration_widget.update_results(results)
            self.statusBar().showMessage("Operação de migração concluída")

    def _on_migration_error(self, error: str) -> None:
        """Handle migration planning error."""
        # Hide progress bar
        self.migration_widget.hide_progress()
        
        self.logger.error(f"Migration error: {error}")
        QMessageBox.warning(
            self, "Erro de Migração", f"Erro durante planejamento: {error}"
        )
        self.statusBar().showMessage("Erro na migração")

    def _on_migration_progress(self, message: str) -> None:
        """Handle migration planning progress."""
        self.statusBar().showMessage(message)
        # Update migration widget progress
        if hasattr(self, 'migration_widget'):
            self.migration_widget.update_progress(message)

    def _on_migration_widget_progress(self, message: str) -> None:
        """Handle progress updates from migration widget."""
        self.statusBar().showMessage(message)

    def _show_help(self) -> None:
        """Show help dialog."""
        help_dialog = HelpDialog(self)
        help_dialog.exec()

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "Sobre SD Emulation GUI",
            "SD Emulation GUI v1.0\n\n"
            "Sistema de gerenciamento e validação de emulação SD.\n\n"
            "Desenvolvido para facilitar a configuração e manutenção "
            "de sistemas de emulação.",
        )
