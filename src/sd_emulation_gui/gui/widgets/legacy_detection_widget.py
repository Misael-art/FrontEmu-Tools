"""
Legacy Detection Widget

Widget modernizado para detecção e migração de instalações legacy
seguindo as especificações de UI/UX e Clean Architecture.
"""

from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QPushButton, QProgressBar,
    QGroupBox, QListWidget, QListWidgetItem, QComboBox,
    QCheckBox, QSpinBox, QLineEdit, QTextEdit, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QSplitter
)
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QIcon

from ...infrastructure import DependencyContainer
from ...domain.entities import LegacyInstallation, MigrationTask, MigrationStatus
from ...app.logging_config import get_logger


class LegacyDetectionWorker(QThread):
    """Worker thread para detecção de instalações legacy."""
    
    installations_detected = Signal(list)
    detection_progress = Signal(int, str)
    detection_finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, container: DependencyContainer):
        super().__init__()
        self.container = container
        self.logger = get_logger(__name__)

    def run(self):
        """Executa detecção de instalações legacy."""
        try:
            # Obter use case de detecção
            detect_legacy_use_case = self.container.get_detect_legacy_installations_use_case()
            
            # Simular progresso de detecção
            self.detection_progress.emit(10, "Iniciando varredura...")
            self.msleep(500)
            
            self.detection_progress.emit(30, "Verificando drives...")
            self.msleep(1000)
            
            self.detection_progress.emit(60, "Analisando diretórios...")
            self.msleep(1500)
            
            self.detection_progress.emit(90, "Finalizando...")
            
            # Executar detecção
            result = detect_legacy_use_case.execute()
            
            if result.success:
                self.installations_detected.emit(result.data)
                self.detection_progress.emit(100, "Concluído")
            else:
                self.error_occurred.emit(result.error_message)
                
        except Exception as e:
            self.logger.error(f"Erro na detecção legacy: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.detection_finished.emit()


class MigrationWorker(QThread):
    """Worker thread para execução de migração."""
    
    migration_progress = Signal(int, str)
    migration_finished = Signal(bool, str)
    error_occurred = Signal(str)

    def __init__(self, container: DependencyContainer, migration_task: MigrationTask):
        super().__init__()
        self.container = container
        self.migration_task = migration_task
        self.logger = get_logger(__name__)

    def run(self):
        """Executa migração."""
        try:
            # Obter use case de migração
            execute_migration_use_case = self.container.get_execute_migration_use_case()
            
            # Simular progresso de migração
            steps = [
                (10, "Preparando migração..."),
                (25, "Criando backup..."),
                (40, "Copiando arquivos..."),
                (60, "Configurando emulador..."),
                (80, "Validando instalação..."),
                (95, "Finalizando..."),
                (100, "Migração concluída")
            ]
            
            for progress, message in steps:
                self.migration_progress.emit(progress, message)
                self.msleep(1000)  # Simular tempo de processamento
            
            # Executar migração real
            result = execute_migration_use_case.execute(self.migration_task.id)
            
            if result.success:
                self.migration_finished.emit(True, "Migração concluída com sucesso")
            else:
                self.migration_finished.emit(False, result.error_message)
                
        except Exception as e:
            self.logger.error(f"Erro na migração: {e}")
            self.error_occurred.emit(str(e))


class LegacyInstallationCard(QFrame):
    """Card para exibir informações de uma instalação legacy."""

    migration_requested = Signal(object)  # LegacyInstallation
    details_requested = Signal(object)  # LegacyInstallation

    def __init__(self, installation: LegacyInstallation, parent=None):
        """Inicializa o card da instalação legacy."""
        super().__init__(parent)
        self.installation = installation
        
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """Configura a interface do card."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        self._create_header(layout)
        
        # Detalhes
        self._create_details(layout)
        
        # Botões de ação
        self._create_action_buttons(layout)

    def _create_header(self, layout: QVBoxLayout):
        """Cria header do card."""
        header_layout = QHBoxLayout()
        
        # Ícone do emulador
        icon_label = QLabel(self._get_emulator_icon())
        icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_label)
        
        # Informações principais
        info_layout = QVBoxLayout()
        
        # Nome do emulador
        name_label = QLabel(self.installation.emulator_name)
        name_label.setStyleSheet("""
            QLabel {
                color: #212529;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        info_layout.addWidget(name_label)
        
        # Versão e plataforma
        version_text = f"v{self.installation.version} • {self.installation.platform.value}"
        version_label = QLabel(version_text)
        version_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 12px;
            }
        """)
        info_layout.addWidget(version_label)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        # Status
        status_color = self._get_status_color()
        status_label = QLabel("●")
        status_label.setStyleSheet(f"""
            QLabel {{
                color: {status_color};
                font-size: 16px;
            }}
        """)
        header_layout.addWidget(status_label)
        
        layout.addLayout(header_layout)

    def _create_details(self, layout: QVBoxLayout):
        """Cria seção de detalhes."""
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(12, 8, 12, 8)
        details_layout.setSpacing(4)
        
        # Informações detalhadas
        details_info = [
            f"📁 Caminho: {self.installation.installation_path}",
            f"📊 Tamanho: {self._format_size(self.installation.size_bytes)}",
            f"📅 Instalado: {self.installation.install_date.strftime('%d/%m/%Y')}",
            f"🎮 ROMs: {len(self.installation.rom_paths)} encontradas"
        ]
        
        for info in details_info:
            label = QLabel(info)
            label.setStyleSheet("""
                QLabel {
                    color: #495057;
                    font-size: 11px;
                    padding: 2px 0;
                }
            """)
            details_layout.addWidget(label)
        
        layout.addWidget(details_frame)

    def _create_action_buttons(self, layout: QVBoxLayout):
        """Cria botões de ação."""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        # Botão de migração
        self.migrate_button = QPushButton("🚀 Migrar")
        self.migrate_button.setStyleSheet("""
            QPushButton {
                background-color: #32CD32;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #28a428;
            }
            QPushButton:pressed {
                background-color: #1e7e1e;
            }
        """)
        self.migrate_button.clicked.connect(self._on_migrate_clicked)
        buttons_layout.addWidget(self.migrate_button)
        
        # Botão de detalhes
        details_button = QPushButton("📋 Detalhes")
        details_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        details_button.clicked.connect(self._on_details_clicked)
        buttons_layout.addWidget(details_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

    def _get_emulator_icon(self) -> str:
        """Retorna ícone do emulador."""
        icons = {
            "RetroArch": "🎮",
            "PCSX2": "🎯",
            "Dolphin": "🐬",
            "PPSSPP": "📱",
            "ePSXe": "💿",
            "Project64": "🎲",
            "MAME": "🕹️"
        }
        return icons.get(self.installation.emulator_name, "🎮")

    def _get_status_color(self) -> str:
        """Retorna cor do status."""
        if self.installation.is_compatible:
            return "#28a745"  # Verde
        else:
            return "#ffc107"  # Amarelo

    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def _on_migrate_clicked(self):
        """Manipula clique no botão de migração."""
        self.migration_requested.emit(self.installation)

    def _on_details_clicked(self):
        """Manipula clique no botão de detalhes."""
        self.details_requested.emit(self.installation)

    def _apply_style(self):
        """Aplica estilo ao card."""
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 12px;
                margin: 4px;
            }
            QFrame:hover {
                border-color: #32CD32;
                box-shadow: 0 4px 12px rgba(50, 205, 50, 0.15);
            }
        """)


class LegacyDetectionWidget(QWidget):
    """Widget modernizado para detecção de instalações legacy."""

    # Sinais
    installation_detected = Signal(object)  # LegacyInstallation
    migration_started = Signal(object)  # MigrationTask
    migration_completed = Signal(object, bool)  # MigrationTask, success

    def __init__(self, container: DependencyContainer, parent=None):
        """Inicializa o widget de detecção legacy."""
        super().__init__(parent)
        
        self.container = container
        self.logger = get_logger(__name__)
        
        # Estado
        self.installation_cards: List[LegacyInstallationCard] = []
        self.current_migrations: Dict[str, MigrationWorker] = {}
        self.detection_worker: Optional[LegacyDetectionWorker] = None
        
        self._setup_ui()
        self._apply_modern_style()

    def _setup_ui(self):
        """Configura a interface do widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        self._create_header(layout)

        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        
        # Lado esquerdo - Lista de instalações
        self._create_installations_panel(splitter)
        
        # Lado direito - Progresso e logs
        self._create_progress_panel(splitter)
        
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)

    def _create_header(self, layout: QVBoxLayout):
        """Cria header do widget."""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #32CD32, stop:1 #28a428);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 16, 20, 16)

        # Título
        title_label = QLabel("🔍 Detecção de Instalações Legacy")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title_label)

        # Espaçador
        header_layout.addStretch()

        # Botão de detecção
        self.detect_button = QPushButton("🔍 Detectar Instalações")
        self.detect_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.detect_button.clicked.connect(self.start_detection)
        header_layout.addWidget(self.detect_button)

        layout.addWidget(header_frame)

    def _create_installations_panel(self, splitter: QSplitter):
        """Cria painel de instalações."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(12)

        # Título do painel
        title_label = QLabel("📦 Instalações Encontradas")
        title_label.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(title_label)

        # Área de scroll para instalações
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.installations_widget = QWidget()
        self.installations_layout = QVBoxLayout(self.installations_widget)
        self.installations_layout.setSpacing(12)
        self.installations_layout.setContentsMargins(0, 0, 0, 0)
        
        # Mensagem inicial
        self.no_installations_label = QLabel("🔍 Clique em 'Detectar Instalações' para começar")
        self.no_installations_label.setAlignment(Qt.AlignCenter)
        self.no_installations_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 14px;
                padding: 40px;
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 12px;
            }
        """)
        self.installations_layout.addWidget(self.no_installations_label)
        
        scroll_area.setWidget(self.installations_widget)
        layout.addWidget(scroll_area)
        
        splitter.addWidget(panel)

    def _create_progress_panel(self, splitter: QSplitter):
        """Cria painel de progresso."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(12)

        # Título do painel
        title_label = QLabel("📊 Progresso e Logs")
        title_label.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(title_label)

        # Seção de detecção
        detection_group = QGroupBox("Detecção")
        detection_layout = QVBoxLayout(detection_group)
        
        self.detection_progress = QProgressBar()
        self.detection_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #32CD32;
                border-radius: 3px;
            }
        """)
        detection_layout.addWidget(self.detection_progress)
        
        self.detection_status = QLabel("Pronto para detectar")
        self.detection_status.setStyleSheet("color: #6c757d; font-size: 12px;")
        detection_layout.addWidget(self.detection_status)
        
        layout.addWidget(detection_group)

        # Seção de migração
        migration_group = QGroupBox("Migração Ativa")
        migration_layout = QVBoxLayout(migration_group)
        
        self.migration_progress = QProgressBar()
        self.migration_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 3px;
            }
        """)
        migration_layout.addWidget(self.migration_progress)
        
        self.migration_status = QLabel("Nenhuma migração ativa")
        self.migration_status.setStyleSheet("color: #6c757d; font-size: 12px;")
        migration_layout.addWidget(self.migration_status)
        
        layout.addWidget(migration_group)

        # Log de atividades
        log_group = QGroupBox("Log de Atividades")
        log_layout = QVBoxLayout(log_group)
        
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMaximumHeight(200)
        self.activity_log.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        log_layout.addWidget(self.activity_log)
        
        # Botão para limpar log
        clear_log_button = QPushButton("🗑️ Limpar Log")
        clear_log_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        clear_log_button.clicked.connect(self.activity_log.clear)
        log_layout.addWidget(clear_log_button)
        
        layout.addWidget(log_group)
        
        splitter.addWidget(panel)

    def _apply_modern_style(self):
        """Aplica estilo moderno ao widget."""
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                color: #495057;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px 0 6px;
                background-color: #f8f9fa;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
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

    def start_detection(self):
        """Inicia detecção de instalações legacy."""
        if self.detection_worker and self.detection_worker.isRunning():
            return

        self.detect_button.setText("🔍 Detectando...")
        self.detect_button.setEnabled(False)
        self.detection_progress.setValue(0)
        self.detection_status.setText("Iniciando detecção...")
        
        self._log_activity("🔍 Iniciando detecção de instalações legacy...")

        # Limpar instalações anteriores
        self._clear_installation_cards()

        # Iniciar detecção
        self.detection_worker = LegacyDetectionWorker(self.container)
        self.detection_worker.installations_detected.connect(self._on_installations_detected)
        self.detection_worker.detection_progress.connect(self._on_detection_progress)
        self.detection_worker.error_occurred.connect(self._on_detection_error)
        self.detection_worker.detection_finished.connect(self._on_detection_finished)
        self.detection_worker.start()

    def _on_installations_detected(self, installations: List[LegacyInstallation]):
        """Manipula instalações detectadas."""
        self._log_activity(f"✅ Detectadas {len(installations)} instalações legacy")
        
        if not installations:
            self.no_installations_label.setText("❌ Nenhuma instalação legacy encontrada")
            self.no_installations_label.setVisible(True)
            return

        self.no_installations_label.setVisible(False)
        
        # Criar cards para cada instalação
        for installation in installations:
            card = LegacyInstallationCard(installation)
            card.migration_requested.connect(self._start_migration)
            card.details_requested.connect(self._show_installation_details)
            self.installation_cards.append(card)
            self.installations_layout.addWidget(card)

        self.installations_layout.addStretch()

    def _on_detection_progress(self, progress: int, message: str):
        """Atualiza progresso da detecção."""
        self.detection_progress.setValue(progress)
        self.detection_status.setText(message)

    def _on_detection_error(self, error_message: str):
        """Manipula erro na detecção."""
        self.logger.error(f"Erro na detecção: {error_message}")
        self._log_activity(f"❌ Erro na detecção: {error_message}")
        self.detection_status.setText(f"Erro: {error_message}")

    def _on_detection_finished(self):
        """Manipula fim da detecção."""
        self.detect_button.setText("🔍 Detectar Instalações")
        self.detect_button.setEnabled(True)
        self.detection_status.setText("Detecção concluída")
        self._log_activity("✅ Detecção concluída")

    def _start_migration(self, installation: LegacyInstallation):
        """Inicia migração de uma instalação."""
        try:
            # Criar tarefa de migração
            create_migration_use_case = self.container.get_create_migration_task_use_case()
            result = create_migration_use_case.execute(
                installation.id,
                f"Migração de {installation.emulator_name}",
                {"preserve_saves": True, "backup_original": True}
            )
            
            if not result.success:
                QMessageBox.warning(self, "Erro", f"Erro ao criar tarefa de migração: {result.error_message}")
                return
            
            migration_task = result.data
            
            # Confirmar migração
            reply = QMessageBox.question(
                self,
                "Confirmar Migração",
                f"Deseja migrar a instalação '{installation.emulator_name}'?\n\n"
                f"Origem: {installation.installation_path}\n"
                f"Tamanho: {self._format_size(installation.size_bytes)}\n\n"
                "Esta operação pode levar alguns minutos.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Iniciar migração
            self._log_activity(f"🚀 Iniciando migração: {installation.emulator_name}")
            
            migration_worker = MigrationWorker(self.container, migration_task)
            migration_worker.migration_progress.connect(self._on_migration_progress)
            migration_worker.migration_finished.connect(self._on_migration_finished)
            migration_worker.error_occurred.connect(self._on_migration_error)
            
            self.current_migrations[migration_task.id] = migration_worker
            migration_worker.start()
            
            # Emitir sinal
            self.migration_started.emit(migration_task)
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar migração: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar migração: {e}")

    def _on_migration_progress(self, progress: int, message: str):
        """Atualiza progresso da migração."""
        self.migration_progress.setValue(progress)
        self.migration_status.setText(message)

    def _on_migration_finished(self, success: bool, message: str):
        """Manipula fim da migração."""
        if success:
            self._log_activity(f"✅ Migração concluída: {message}")
            QMessageBox.information(self, "Sucesso", message)
        else:
            self._log_activity(f"❌ Migração falhou: {message}")
            QMessageBox.warning(self, "Erro", f"Migração falhou: {message}")
        
        self.migration_progress.setValue(0)
        self.migration_status.setText("Nenhuma migração ativa")

    def _on_migration_error(self, error_message: str):
        """Manipula erro na migração."""
        self.logger.error(f"Erro na migração: {error_message}")
        self._log_activity(f"❌ Erro na migração: {error_message}")
        QMessageBox.critical(self, "Erro", f"Erro na migração: {error_message}")

    def _show_installation_details(self, installation: LegacyInstallation):
        """Mostra detalhes de uma instalação."""
        details = f"""
Detalhes da Instalação Legacy

Emulador: {installation.emulator_name}
Versão: {installation.version}
Plataforma: {installation.platform.value}
Caminho: {installation.installation_path}
Tamanho: {self._format_size(installation.size_bytes)}
Data de Instalação: {installation.install_date.strftime('%d/%m/%Y %H:%M')}
Compatível: {'Sim' if installation.is_compatible else 'Não'}

ROMs Encontradas: {len(installation.rom_paths)}
{chr(10).join(installation.rom_paths[:5])}
{'...' if len(installation.rom_paths) > 5 else ''}

Configurações:
{chr(10).join([f"- {k}: {v}" for k, v in installation.config_files.items()])}
        """
        
        QMessageBox.information(self, "Detalhes da Instalação", details)

    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def _log_activity(self, message: str):
        """Adiciona mensagem ao log de atividades."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(f"[{timestamp}] {message}")

    def _clear_installation_cards(self):
        """Remove todos os cards de instalações."""
        for card in self.installation_cards:
            card.setParent(None)
            card.deleteLater()
        
        self.installation_cards.clear()

    def closeEvent(self, event):
        """Manipula fechamento do widget."""
        # Parar workers ativos
        if self.detection_worker and self.detection_worker.isRunning():
            self.detection_worker.quit()
            self.detection_worker.wait()
        
        for worker in self.current_migrations.values():
            if worker.isRunning():
                worker.quit()
                worker.wait()
        
        super().closeEvent(event)