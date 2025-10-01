"""
Main Window GUI

Janela principal modernizada para o SD Emulation GUI seguindo
as especificações de UI/UX e Clean Architecture.
"""

import sys
from typing import Optional, Dict, Any

try:
    from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QThread, Signal, QTimer
    from PySide6.QtGui import QAccessible, QColor, QFont, QIcon, QPalette, QShortcut, QPixmap
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
        QApplication,
        QStyleFactory
    )
    PYSIDE6_AVAILABLE = True
except ImportError as e:
    print(f"PySide6 não disponível: {e}. Instale com: pip install PySide6")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Importar componentes da aplicação
try:
    from ..infrastructure import get_container, DependencyContainer
    from ..app.logging_config import get_logger, operation_context
    
    # Importar widgets modernizados
    from ..gui.widgets.system_info_widget import SystemInfoWidget
    from ..gui.widgets.drive_selection_widget import DriveSelectionWidget
    from ..gui.widgets.legacy_detection_widget import LegacyDetectionWidget
    from ..gui.widgets.system_stats_widget import SystemStatsWidget
    
    # Importar casos de uso
    from ..domain.use_cases import (
        DetectDrivesUseCase,
        DetectEmulatorsUseCase,
        DetectLegacyInstallationsUseCase,
        MonitorSystemPerformanceUseCase,
        StartSystemSessionUseCase,
        EndSystemSessionUseCase
    )
    
except ImportError as e:
    print(f"Erro ao importar componentes: {e}")
    PYSIDE6_AVAILABLE = False


class ModernHelpDialog(QDialog):
    """Diálogo de ajuda modernizado com identidade visual."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajuda - FrontEmu Tools")
        self.setModal(True)
        self.resize(700, 500)
        
        # Aplicar estilo moderno
        self._apply_modern_style()
        self._setup_ui()

    def _apply_modern_style(self):
        """Aplica o estilo moderno com identidade visual."""
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                border: 2px solid #32CD32;
                border-radius: 12px;
            }
            QLabel {
                color: #2c3e50;
                font-weight: bold;
                font-size: 16px;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                line-height: 1.5;
            }
            QPushButton {
                background-color: #32CD32;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #28a428;
            }
            QPushButton:pressed {
                background-color: #228b22;
            }
        """)

    def _setup_ui(self):
        """Configura a interface do diálogo."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Título
        title_label = QLabel("🚀 FrontEmu Tools - Guia de Uso")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20px; color: #32CD32; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Conteúdo da ajuda
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        
        faq_content = """
<h2 style="color: #32CD32;">🎮 FrontEmu Tools v1.0</h2>

<h3 style="color: #2c3e50;">📋 Funcionalidades Principais</h3>
<ul>
<li><strong>Detecção Automática de Drives:</strong> Identifica automaticamente drives disponíveis para emulação</li>
<li><strong>Detecção de Sistemas Legacy:</strong> Encontra instalações antigas de emuladores</li>
<li><strong>Migração Inteligente:</strong> Migra configurações para estrutura SD otimizada</li>
<li><strong>Monitoramento em Tempo Real:</strong> Acompanha performance do sistema</li>
</ul>

<h3 style="color: #2c3e50;">🔧 Como Usar</h3>
<ol>
<li><strong>Info do Sistema:</strong> Visualize informações detalhadas do seu sistema</li>
<li><strong>Seleção de Drive:</strong> Escolha o drive para configuração de emulação</li>
<li><strong>Detecção Legacy:</strong> Identifique instalações existentes de emuladores</li>
<li><strong>Estatísticas:</strong> Monitore performance e uso de recursos</li>
</ol>

<h3 style="color: #2c3e50;">💡 Dicas</h3>
<ul>
<li>Execute como administrador para melhor detecção de drives</li>
<li>Mantenha backups antes de executar migrações</li>
<li>Monitore o uso de recursos durante operações intensivas</li>
<li>Use a detecção automática para configuração rápida</li>
</ul>

<h3 style="color: #2c3e50;">🆘 Suporte</h3>
<p>Para suporte técnico, consulte a documentação completa ou entre em contato com a equipe de desenvolvimento.</p>
        """
        
        help_text.setHtml(faq_content)
        layout.addWidget(help_text)

        # Botão OK
        ok_button = QPushButton("✅ Entendi")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)


class SystemWorker(QThread):
    """Worker thread para operações do sistema."""

    # Sinais
    finished = Signal(dict)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, container: DependencyContainer, operation: str, **kwargs):
        """Inicializa o worker do sistema."""
        super().__init__()
        self.container = container
        self.operation = operation
        self.kwargs = kwargs
        self.logger = get_logger(__name__)

    def run(self) -> None:
        """Executa operação em thread separada."""
        try:
            with operation_context(f"system_{self.operation}", self.logger):
                if self.operation == "detect_drives":
                    self._detect_drives()
                elif self.operation == "detect_emulators":
                    self._detect_emulators()
                elif self.operation == "detect_legacy":
                    self._detect_legacy_installations()
                elif self.operation == "monitor_performance":
                    self._monitor_performance()
                elif self.operation == "start_session":
                    self._start_session()
                elif self.operation == "end_session":
                    self._end_session()
                else:
                    self.error.emit(f"Operação desconhecida: {self.operation}")

        except Exception as e:
            self.logger.error(f"Erro no worker do sistema: {e}")
            self.error.emit(str(e))

    def _detect_drives(self):
        """Detecta drives disponíveis."""
        self.progress.emit("Detectando drives...")
        use_case = self.container.get_detect_drives_use_case()
        result = use_case.execute()
        
        if result.success:
            self.progress.emit("Detecção de drives concluída")
            self.finished.emit({
                "operation": "detect_drives",
                "drives": [drive.to_dict() for drive in result.data]
            })
        else:
            self.error.emit(result.error_message or "Erro na detecção de drives")

    def _detect_emulators(self):
        """Detecta emuladores instalados."""
        self.progress.emit("Detectando emuladores...")
        use_case = self.container.get_detect_emulators_use_case()
        result = use_case.execute()
        
        if result.success:
            self.progress.emit("Detecção de emuladores concluída")
            self.finished.emit({
                "operation": "detect_emulators",
                "emulators": [emulator.to_dict() for emulator in result.data]
            })
        else:
            self.error.emit(result.error_message or "Erro na detecção de emuladores")

    def _detect_legacy_installations(self):
        """Detecta instalações legacy."""
        self.progress.emit("Detectando instalações legacy...")
        use_case = self.container.get_detect_legacy_installations_use_case()
        result = use_case.execute()
        
        if result.success:
            self.progress.emit("Detecção de instalações legacy concluída")
            self.finished.emit({
                "operation": "detect_legacy",
                "installations": [install.to_dict() for install in result.data]
            })
        else:
            self.error.emit(result.error_message or "Erro na detecção de instalações legacy")

    def _monitor_performance(self):
        """Monitora performance do sistema."""
        self.progress.emit("Monitorando performance...")
        use_case = self.container.get_monitor_system_performance_use_case()
        result = use_case.execute()
        
        if result.success:
            self.progress.emit("Monitoramento de performance concluído")
            self.finished.emit({
                "operation": "monitor_performance",
                "metrics": result.data.to_dict() if result.data else {}
            })
        else:
            self.error.emit(result.error_message or "Erro no monitoramento de performance")

    def _start_session(self):
        """Inicia sessão do sistema."""
        self.progress.emit("Iniciando sessão...")
        use_case = self.container.get_start_system_session_use_case()
        result = use_case.execute()
        
        if result.success:
            self.progress.emit("Sessão iniciada")
            self.finished.emit({
                "operation": "start_session",
                "session": result.data.to_dict() if result.data else {}
            })
        else:
            self.error.emit(result.error_message or "Erro ao iniciar sessão")

    def _end_session(self):
        """Finaliza sessão do sistema."""
        self.progress.emit("Finalizando sessão...")
        use_case = self.container.get_end_system_session_use_case()
        session_id = self.kwargs.get('session_id')
        result = use_case.execute(session_id)
        
        if result.success:
            self.progress.emit("Sessão finalizada")
            self.finished.emit({
                "operation": "end_session",
                "session": result.data.to_dict() if result.data else {}
            })
        else:
            self.error.emit(result.error_message or "Erro ao finalizar sessão")


class MainWindow(QMainWindow):
    """Janela principal modernizada do FrontEmu Tools."""

    def __init__(self, container: Optional[DependencyContainer] = None):
        """Inicializa a janela principal."""
        super().__init__()
        
        # Container de dependências
        self.container = container or get_container()
        self.logger = get_logger(__name__)
        
        # Workers para operações assíncronas
        self.system_worker: Optional[SystemWorker] = None
        self.current_session_id: Optional[str] = None
        
        # Timer para atualizações automáticas
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_system_info)
        
        # Configurar interface
        self._setup_modern_ui()
        self._setup_modern_menu()
        self._setup_modern_style()
        self._connect_signals()
        self._start_application_session()
        
        self.logger.info("MainWindow modernizada inicializada com sucesso")

    def _setup_modern_ui(self) -> None:
        """Configura a interface moderna."""
        self.setWindowTitle("🚀 FrontEmu Tools v1.0")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header moderno
        self._create_modern_header(main_layout)

        # Área de conteúdo com tabs
        self._create_modern_content(main_layout)

        # Footer moderno
        self._create_modern_footer(main_layout)

    def _create_modern_header(self, layout: QVBoxLayout) -> None:
        """Cria header moderno."""
        header_frame = QFrame()
        header_frame.setFixedHeight(80)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #32CD32, stop:1 #28a428);
                border: none;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 16, 24, 16)

        # Logo e título
        title_label = QLabel("🚀 FrontEmu Tools")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        header_layout.addWidget(title_label)

        # Espaçador
        header_layout.addStretch()

        # Indicador de status
        self.status_indicator = QLabel("🟢 Sistema Ativo")
        self.status_indicator.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: 500;
                background-color: rgba(255, 255, 255, 0.2);
                padding: 8px 16px;
                border-radius: 20px;
            }
        """)
        header_layout.addWidget(self.status_indicator)

        layout.addWidget(header_frame)

    def _create_modern_content(self, layout: QVBoxLayout) -> None:
        """Cria área de conteúdo moderna."""
        # Container para o conteúdo
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: none;
            }
        """)
        
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(24, 24, 24, 24)

        # Tab widget moderno
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e9ecef;
                border-radius: 8px;
                background-color: white;
                margin-top: 8px;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #495057;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background-color: #32CD32;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e9ecef;
            }
        """)

        # Criar tabs modernos
        self._create_modern_tabs()
        
        content_layout.addWidget(self.tab_widget)
        layout.addWidget(content_frame)

    def _create_modern_tabs(self) -> None:
        """Cria tabs modernos."""
        # Tab de informações do sistema
        self.system_info_widget = SystemInfoWidget(self.container)
        self.tab_widget.addTab(self.system_info_widget, "📊 Info do Sistema")

        # Tab de seleção de drive
        self.drive_selection_widget = DriveSelectionWidget(self.container)
        self.tab_widget.addTab(self.drive_selection_widget, "💾 Seleção de Drive")

        # Tab de detecção legacy
        self.legacy_detection_widget = LegacyDetectionWidget(self.container)
        self.tab_widget.addTab(self.legacy_detection_widget, "🔍 Detecção Legacy")

        # Tab de estatísticas
        self.system_stats_widget = SystemStatsWidget(self.container)
        self.tab_widget.addTab(self.system_stats_widget, "📈 Estatísticas")

    def _create_modern_footer(self, layout: QVBoxLayout) -> None:
        """Cria footer moderno."""
        footer_frame = QFrame()
        footer_frame.setFixedHeight(40)
        footer_frame.setStyleSheet("""
            QFrame {
                background-color: #343a40;
                border: none;
            }
        """)
        
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(24, 8, 24, 8)

        # Status da aplicação
        self.app_status_label = QLabel("Pronto")
        self.app_status_label.setStyleSheet("""
            QLabel {
                color: #adb5bd;
                font-size: 12px;
            }
        """)
        footer_layout.addWidget(self.app_status_label)

        # Espaçador
        footer_layout.addStretch()

        # Versão
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 12px;
            }
        """)
        footer_layout.addWidget(version_label)

        layout.addWidget(footer_frame)

    def _setup_modern_style(self) -> None:
        """Configura estilo moderno da aplicação."""
        # Aplicar estilo global
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QScrollBar:vertical {
                background-color: #f8f9fa;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #32CD32;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #28a428;
            }
        """)

        # Configurar acessibilidade
        self._setup_accessibility()

    def _setup_accessibility(self) -> None:
        """Configura recursos de acessibilidade."""
        # Atalhos de teclado
        QShortcut("Ctrl+Q", self, self.close)
        QShortcut("Ctrl+H", self, self._show_help)
        QShortcut("F1", self, self._show_help)
        QShortcut("Ctrl+R", self, self._refresh_all_data)

        # Suporte a leitor de tela
        self.setAccessibleName("Janela Principal - FrontEmu Tools")
        self.setAccessibleDescription(
            "Aplicação principal para gerenciamento de emulação SD"
        )

        # Tornar widgets acessíveis
        self.tab_widget.setAccessibleName("Abas Principais")
        self.status_indicator.setAccessibleName("Indicador de Status")

    def _setup_modern_menu(self) -> None:
        """Configura menu moderno."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: white;
                color: #495057;
                border-bottom: 1px solid #e9ecef;
                padding: 4px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #32CD32;
                color: white;
            }
            QMenu {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 8px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #32CD32;
                color: white;
            }
        """)

        # Menu Sistema
        system_menu = menubar.addMenu("🔧 Sistema")
        
        refresh_action = system_menu.addAction("🔄 Atualizar Dados")
        refresh_action.setShortcut("Ctrl+R")
        refresh_action.triggered.connect(self._refresh_all_data)
        
        system_menu.addSeparator()
        
        exit_action = system_menu.addAction("🚪 Sair")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        # Menu Ferramentas
        tools_menu = menubar.addMenu("🛠️ Ferramentas")
        
        detect_drives_action = tools_menu.addAction("💾 Detectar Drives")
        detect_drives_action.triggered.connect(self._run_drive_detection)
        
        detect_legacy_action = tools_menu.addAction("🔍 Detectar Legacy")
        detect_legacy_action.triggered.connect(self._run_legacy_detection)
        
        monitor_action = tools_menu.addAction("📊 Monitorar Sistema")
        monitor_action.triggered.connect(self._run_system_monitoring)

        # Menu Ajuda
        help_menu = menubar.addMenu("❓ Ajuda")
        
        help_action = help_menu.addAction("📖 Guia de Uso")
        help_action.setShortcut("F1")
        help_action.triggered.connect(self._show_help)
        
        help_menu.addSeparator()
        
        about_action = help_menu.addAction("ℹ️ Sobre")
        about_action.triggered.connect(self._show_about)

    def _connect_signals(self) -> None:
        """Conecta sinais entre widgets."""
        # Conectar sinais dos widgets
        if hasattr(self.drive_selection_widget, 'drive_selected'):
            self.drive_selection_widget.drive_selected.connect(self._on_drive_selected)
        
        if hasattr(self.legacy_detection_widget, 'detection_completed'):
            self.legacy_detection_widget.detection_completed.connect(self._on_legacy_detection_completed)
        
        if hasattr(self.system_stats_widget, 'alert_generated'):
            self.system_stats_widget.alert_generated.connect(self._on_system_alert)

        # Conectar mudanças de tab
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _start_application_session(self) -> None:
        """Inicia sessão da aplicação."""
        try:
            self._run_system_operation("start_session")
            
            # Iniciar timer de atualização (a cada 30 segundos)
            self.update_timer.start(30000)
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar sessão: {e}")

    def _run_system_operation(self, operation: str, **kwargs) -> None:
        """Executa operação do sistema em thread separada."""
        if self.system_worker and self.system_worker.isRunning():
            return

        self.system_worker = SystemWorker(self.container, operation, **kwargs)
        self.system_worker.finished.connect(self._on_system_operation_finished)
        self.system_worker.error.connect(self._on_system_operation_error)
        self.system_worker.progress.connect(self._on_system_operation_progress)
        self.system_worker.start()

    def _run_drive_detection(self) -> None:
        """Executa detecção de drives."""
        self._run_system_operation("detect_drives")

    def _run_legacy_detection(self) -> None:
        """Executa detecção de instalações legacy."""
        self._run_system_operation("detect_legacy")

    def _run_system_monitoring(self) -> None:
        """Executa monitoramento do sistema."""
        self._run_system_operation("monitor_performance")

    def _refresh_all_data(self) -> None:
        """Atualiza todos os dados da interface."""
        self.app_status_label.setText("Atualizando dados...")
        
        # Atualizar widgets
        if hasattr(self.system_info_widget, 'refresh_data'):
            self.system_info_widget.refresh_data()
        
        if hasattr(self.drive_selection_widget, 'refresh_drives'):
            self.drive_selection_widget.refresh_drives()
        
        if hasattr(self.system_stats_widget, 'refresh_stats'):
            self.system_stats_widget.refresh_stats()
        
        self.app_status_label.setText("Dados atualizados")

    def _update_system_info(self) -> None:
        """Atualiza informações do sistema automaticamente."""
        if hasattr(self.system_stats_widget, 'update_metrics'):
            self.system_stats_widget.update_metrics()

    def _on_system_operation_finished(self, results: Dict[str, Any]) -> None:
        """Manipula conclusão de operação do sistema."""
        operation = results.get("operation", "unknown")
        
        if operation == "start_session":
            session_data = results.get("session", {})
            self.current_session_id = session_data.get("id")
            self.status_indicator.setText("🟢 Sessão Ativa")
            
        elif operation == "detect_drives":
            drives = results.get("drives", [])
            if hasattr(self.drive_selection_widget, 'update_drives'):
                self.drive_selection_widget.update_drives(drives)
            
        elif operation == "detect_legacy":
            installations = results.get("installations", [])
            if hasattr(self.legacy_detection_widget, 'update_installations'):
                self.legacy_detection_widget.update_installations(installations)
            
        elif operation == "monitor_performance":
            metrics = results.get("metrics", {})
            if hasattr(self.system_stats_widget, 'update_performance_metrics'):
                self.system_stats_widget.update_performance_metrics(metrics)

        self.app_status_label.setText(f"Operação '{operation}' concluída")

    def _on_system_operation_error(self, error: str) -> None:
        """Manipula erro em operação do sistema."""
        self.logger.error(f"Erro em operação do sistema: {error}")
        QMessageBox.warning(
            self, "Erro do Sistema", f"Erro durante operação: {error}"
        )
        self.app_status_label.setText("Erro na operação")
        self.status_indicator.setText("🔴 Erro no Sistema")

    def _on_system_operation_progress(self, message: str) -> None:
        """Manipula progresso de operação do sistema."""
        self.app_status_label.setText(message)

    def _on_drive_selected(self, drive_info: Dict[str, Any]) -> None:
        """Manipula seleção de drive."""
        drive_letter = drive_info.get("letter", "")
        self.app_status_label.setText(f"Drive selecionado: {drive_letter}")

    def _on_legacy_detection_completed(self, results: Dict[str, Any]) -> None:
        """Manipula conclusão de detecção legacy."""
        count = len(results.get("installations", []))
        self.app_status_label.setText(f"Detecção concluída: {count} instalações encontradas")

    def _on_system_alert(self, alert: Dict[str, Any]) -> None:
        """Manipula alerta do sistema."""
        severity = alert.get("severity", "info")
        message = alert.get("message", "Alerta do sistema")
        
        if severity == "critical":
            QMessageBox.critical(self, "Alerta Crítico", message)
        elif severity == "warning":
            QMessageBox.warning(self, "Aviso", message)
        else:
            QMessageBox.information(self, "Informação", message)

    def _on_tab_changed(self, index: int) -> None:
        """Manipula mudança de tab."""
        tab_text = self.tab_widget.tabText(index)
        self.app_status_label.setText(f"Visualizando: {tab_text}")

    def _show_help(self) -> None:
        """Exibe diálogo de ajuda."""
        help_dialog = ModernHelpDialog(self)
        help_dialog.exec()

    def _show_about(self) -> None:
        """Exibe diálogo sobre."""
        QMessageBox.about(
            self,
            "Sobre FrontEmu Tools",
            """
            <h2 style="color: #32CD32;">🚀 FrontEmu Tools v1.0</h2>
            
            <p><strong>Sistema avançado de gerenciamento de emulação SD</strong></p>
            
            <p>Desenvolvido com Clean Architecture e tecnologias modernas para 
            facilitar a configuração, migração e manutenção de sistemas de emulação.</p>
            
            <h3>Características:</h3>
            <ul>
            <li>✅ Detecção automática de drives e emuladores</li>
            <li>✅ Migração inteligente de configurações legacy</li>
            <li>✅ Monitoramento em tempo real</li>
            <li>✅ Interface moderna e acessível</li>
            </ul>
            
            <p><em>Desenvolvido com ❤️ para a comunidade de emulação</em></p>
            """
        )

    def closeEvent(self, event) -> None:
        """Manipula fechamento da aplicação."""
        try:
            # Finalizar sessão
            if self.current_session_id:
                self._run_system_operation("end_session", session_id=self.current_session_id)
            
            # Parar timer
            self.update_timer.stop()
            
            # Finalizar workers
            if self.system_worker and self.system_worker.isRunning():
                self.system_worker.terminate()
                self.system_worker.wait(3000)  # Aguardar até 3 segundos
            
            self.logger.info("Aplicação finalizada com sucesso")
            event.accept()
            
        except Exception as e:
            self.logger.error(f"Erro ao finalizar aplicação: {e}")
            event.accept()  # Aceitar mesmo com erro para não travar
