"""
Drive Selection Widget

Widget modernizado para seleção e gerenciamento de drives
seguindo as especificações de UI/UX e Clean Architecture.
"""

from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QPushButton, QProgressBar,
    QGroupBox, QListWidget, QListWidgetItem, QComboBox,
    QCheckBox, QSpinBox, QLineEdit, QTextEdit, QMessageBox
)
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QIcon

from ...infrastructure import DependencyContainer
from ...domain.entities import DriveInfo, DriveType
from ...app.logging_config import get_logger


class DriveDetectionWorker(QThread):
    """Worker thread para detecção de drives."""
    
    drives_detected = Signal(list)
    detection_finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, container: DependencyContainer):
        super().__init__()
        self.container = container
        self.logger = get_logger(__name__)

    def run(self):
        """Executa detecção de drives em thread separada."""
        try:
            # Obter use case de detecção de drives
            detect_drives_use_case = self.container.get_detect_drives_use_case()
            
            # Executar detecção
            result = detect_drives_use_case.execute()
            
            if result.success:
                self.drives_detected.emit(result.data)
            else:
                self.error_occurred.emit(result.error_message)
                
        except Exception as e:
            self.logger.error(f"Erro na detecção de drives: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.detection_finished.emit()


class DriveCard(QFrame):
    """Card moderno para exibir informações de um drive."""

    drive_selected = Signal(object)  # DriveInfo
    drive_configured = Signal(object, dict)  # DriveInfo, config

    def __init__(self, drive_info: DriveInfo, parent=None):
        """Inicializa o card do drive."""
        super().__init__(parent)
        self.drive_info = drive_info
        self.is_selected = False
        
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """Configura a interface do card."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header com ícone e informações básicas
        self._create_header(layout)
        
        # Informações detalhadas
        self._create_details(layout)
        
        # Configurações (inicialmente ocultas)
        self._create_configuration_section(layout)
        
        # Botões de ação
        self._create_action_buttons(layout)

    def _create_header(self, layout: QVBoxLayout):
        """Cria o header do card."""
        header_layout = QHBoxLayout()
        
        # Ícone do drive
        icon_label = QLabel(self._get_drive_icon())
        icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_label)
        
        # Informações principais
        info_layout = QVBoxLayout()
        
        # Nome/letra do drive
        self.drive_label = QLabel(f"Drive {self.drive_info.letter}")
        self.drive_label.setStyleSheet("""
            QLabel {
                color: #212529;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        info_layout.addWidget(self.drive_label)
        
        # Tipo e tamanho
        details = f"{self.drive_info.drive_type.value} • {self._format_size(self.drive_info.total_space)}"
        details_label = QLabel(details)
        details_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 12px;
            }
        """)
        info_layout.addWidget(details_label)
        
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        
        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-size: 16px;
            }
        """)
        header_layout.addWidget(self.status_indicator)
        
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
            f"📁 Rótulo: {self.drive_info.label or 'Sem rótulo'}",
            f"💾 Sistema: {self.drive_info.file_system}",
            f"📊 Usado: {self._format_size(self.drive_info.used_space)} / {self._format_size(self.drive_info.total_space)}",
            f"🆓 Livre: {self._format_size(self.drive_info.free_space)}"
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
        
        # Barra de progresso do uso
        self.usage_bar = QProgressBar()
        usage_percent = (self.drive_info.used_space / self.drive_info.total_space) * 100
        self.usage_bar.setValue(int(usage_percent))
        self.usage_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #32CD32;
                border-radius: 3px;
            }
        """)
        details_layout.addWidget(self.usage_bar)
        
        layout.addWidget(details_frame)

    def _create_configuration_section(self, layout: QVBoxLayout):
        """Cria seção de configuração."""
        self.config_frame = QFrame()
        self.config_frame.setVisible(False)
        self.config_frame.setStyleSheet("""
            QFrame {
                background-color: #e3f2fd;
                border: 1px solid #32CD32;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        config_layout = QVBoxLayout(self.config_frame)
        config_layout.setContentsMargins(12, 12, 12, 12)
        config_layout.setSpacing(8)
        
        # Título da configuração
        config_title = QLabel("⚙️ Configurações de Emulação")
        config_title.setStyleSheet("""
            QLabel {
                color: #32CD32;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 8px;
            }
        """)
        config_layout.addWidget(config_title)
        
        # Opções de configuração
        options_layout = QGridLayout()
        
        # Tamanho do cache
        cache_label = QLabel("Cache (MB):")
        self.cache_spinbox = QSpinBox()
        self.cache_spinbox.setRange(64, 2048)
        self.cache_spinbox.setValue(512)
        self.cache_spinbox.setSuffix(" MB")
        options_layout.addWidget(cache_label, 0, 0)
        options_layout.addWidget(self.cache_spinbox, 0, 1)
        
        # Modo de emulação
        mode_label = QLabel("Modo:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Padrão", "Performance", "Compatibilidade"])
        options_layout.addWidget(mode_label, 1, 0)
        options_layout.addWidget(self.mode_combo, 1, 1)
        
        # Opções avançadas
        self.advanced_checkbox = QCheckBox("Habilitar opções avançadas")
        options_layout.addWidget(self.advanced_checkbox, 2, 0, 1, 2)
        
        config_layout.addLayout(options_layout)
        layout.addWidget(self.config_frame)

    def _create_action_buttons(self, layout: QVBoxLayout):
        """Cria botões de ação."""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        # Botão de seleção
        self.select_button = QPushButton("Selecionar")
        self.select_button.setStyleSheet("""
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
        self.select_button.clicked.connect(self._on_select_clicked)
        buttons_layout.addWidget(self.select_button)
        
        # Botão de configuração
        self.config_button = QPushButton("⚙️")
        self.config_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.config_button.clicked.connect(self._toggle_configuration)
        buttons_layout.addWidget(self.config_button)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

    def _get_drive_icon(self) -> str:
        """Retorna ícone apropriado para o tipo de drive."""
        icons = {
            DriveType.HDD: "💿",
            DriveType.SSD: "💾",
            DriveType.USB: "🔌",
            DriveType.OPTICAL: "📀",
            DriveType.NETWORK: "🌐",
            DriveType.UNKNOWN: "❓"
        }
        return icons.get(self.drive_info.drive_type, "💿")

    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes para formato legível."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def _on_select_clicked(self):
        """Manipula clique no botão de seleção."""
        self.set_selected(not self.is_selected)
        self.drive_selected.emit(self.drive_info)

    def _toggle_configuration(self):
        """Alterna visibilidade da seção de configuração."""
        self.config_frame.setVisible(not self.config_frame.isVisible())

    def set_selected(self, selected: bool):
        """Define estado de seleção do card."""
        self.is_selected = selected
        
        if selected:
            self.select_button.setText("✓ Selecionado")
            self.select_button.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: 500;
                }
            """)
            self._apply_selected_style()
        else:
            self.select_button.setText("Selecionar")
            self.select_button.setStyleSheet("""
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
            """)
            self._apply_default_style()

    def _apply_selected_style(self):
        """Aplica estilo de card selecionado."""
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #32CD32;
                border-radius: 12px;
                margin: 4px;
            }
        """)

    def _apply_default_style(self):
        """Aplica estilo padrão do card."""
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

    def _apply_style(self):
        """Aplica estilo inicial ao card."""
        self._apply_default_style()

    def get_configuration(self) -> Dict[str, Any]:
        """Retorna configuração atual do drive."""
        return {
            "cache_size": self.cache_spinbox.value(),
            "mode": self.mode_combo.currentText(),
            "advanced_options": self.advanced_checkbox.isChecked()
        }


class DriveSelectionWidget(QWidget):
    """Widget modernizado para seleção de drives."""

    # Sinais
    drive_selected = Signal(object)  # DriveInfo
    drives_refreshed = Signal(list)  # List[DriveInfo]
    selection_changed = Signal(list)  # List[DriveInfo]

    def __init__(self, container: DependencyContainer, parent=None):
        """Inicializa o widget de seleção de drives."""
        super().__init__(parent)
        
        self.container = container
        self.logger = get_logger(__name__)
        
        # Estado
        self.drive_cards: List[DriveCard] = []
        self.selected_drives: List[DriveInfo] = []
        self.detection_worker: Optional[DriveDetectionWorker] = None
        
        # Timer para auto-refresh
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._auto_refresh)
        
        self._setup_ui()
        self._apply_modern_style()
        self._load_initial_drives()
        
        # Iniciar auto-refresh (a cada 30 segundos)
        self.refresh_timer.start(30000)

    def _setup_ui(self):
        """Configura a interface do widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        self._create_header(layout)

        # Área de filtros e controles
        self._create_controls(layout)

        # Área de scroll para os cards de drives
        self._create_drives_area(layout)

        # Footer com informações de seleção
        self._create_footer(layout)

    def _create_header(self, layout: QVBoxLayout):
        """Cria o header do widget."""
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
        title_label = QLabel("💿 Seleção de Drives")
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

        # Botão de atualização
        self.refresh_button = QPushButton("🔄 Detectar Drives")
        self.refresh_button.setStyleSheet("""
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
        self.refresh_button.clicked.connect(self.refresh_drives)
        header_layout.addWidget(self.refresh_button)

        layout.addWidget(header_frame)

    def _create_controls(self, layout: QVBoxLayout):
        """Cria área de controles e filtros."""
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(16, 12, 16, 12)

        # Filtro por tipo
        type_label = QLabel("Filtrar por tipo:")
        type_label.setStyleSheet("color: #495057; font-weight: 500;")
        controls_layout.addWidget(type_label)

        self.type_filter = QComboBox()
        self.type_filter.addItems(["Todos", "HDD", "SSD", "USB", "Óptico", "Rede"])
        self.type_filter.currentTextChanged.connect(self._apply_filters)
        controls_layout.addWidget(self.type_filter)

        controls_layout.addStretch()

        # Indicador de status
        self.status_label = QLabel("Pronto")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-weight: 500;
                padding: 4px 8px;
                background-color: #d4edda;
                border-radius: 4px;
            }
        """)
        controls_layout.addWidget(self.status_label)

        layout.addWidget(controls_frame)

    def _create_drives_area(self, layout: QVBoxLayout):
        """Cria área de exibição dos drives."""
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Widget de conteúdo
        self.drives_widget = QWidget()
        self.drives_layout = QVBoxLayout(self.drives_widget)
        self.drives_layout.setSpacing(12)
        self.drives_layout.setContentsMargins(0, 0, 0, 0)
        
        # Mensagem quando não há drives
        self.no_drives_label = QLabel("🔍 Nenhum drive detectado")
        self.no_drives_label.setAlignment(Qt.AlignCenter)
        self.no_drives_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 16px;
                padding: 40px;
                background-color: #f8f9fa;
                border: 2px dashed #dee2e6;
                border-radius: 12px;
            }
        """)
        self.drives_layout.addWidget(self.no_drives_label)
        
        scroll_area.setWidget(self.drives_widget)
        layout.addWidget(scroll_area)

    def _create_footer(self, layout: QVBoxLayout):
        """Cria footer com informações de seleção."""
        self.footer_frame = QFrame()
        self.footer_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        footer_layout = QHBoxLayout(self.footer_frame)
        footer_layout.setContentsMargins(16, 12, 16, 12)

        # Informações de seleção
        self.selection_info = QLabel("Nenhum drive selecionado")
        self.selection_info.setStyleSheet("""
            QLabel {
                color: #495057;
                font-weight: 500;
            }
        """)
        footer_layout.addWidget(self.selection_info)

        footer_layout.addStretch()

        # Botão de ação
        self.action_button = QPushButton("Configurar Selecionados")
        self.action_button.setEnabled(False)
        self.action_button.setStyleSheet("""
            QPushButton {
                background-color: #32CD32;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover:enabled {
                background-color: #28a428;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.action_button.clicked.connect(self._configure_selected_drives)
        footer_layout.addWidget(self.action_button)

        layout.addWidget(self.footer_frame)

    def _apply_modern_style(self):
        """Aplica estilo moderno ao widget."""
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
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

    def _load_initial_drives(self):
        """Carrega drives iniciais."""
        self.refresh_drives()

    def refresh_drives(self):
        """Atualiza lista de drives."""
        if self.detection_worker and self.detection_worker.isRunning():
            return

        self.refresh_button.setText("🔄 Detectando...")
        self.refresh_button.setEnabled(False)
        self.status_label.setText("Detectando drives...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #ffc107;
                font-weight: 500;
                padding: 4px 8px;
                background-color: #fff3cd;
                border-radius: 4px;
            }
        """)

        # Iniciar detecção em thread separada
        self.detection_worker = DriveDetectionWorker(self.container)
        self.detection_worker.drives_detected.connect(self._on_drives_detected)
        self.detection_worker.error_occurred.connect(self._on_detection_error)
        self.detection_worker.detection_finished.connect(self._on_detection_finished)
        self.detection_worker.start()

    def _on_drives_detected(self, drives: List[DriveInfo]):
        """Manipula drives detectados."""
        self._clear_drive_cards()
        
        if not drives:
            self.no_drives_label.setVisible(True)
            self.status_label.setText("Nenhum drive encontrado")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #dc3545;
                    font-weight: 500;
                    padding: 4px 8px;
                    background-color: #f8d7da;
                    border-radius: 4px;
                }
            """)
            return

        self.no_drives_label.setVisible(False)
        
        # Criar cards para cada drive
        for drive in drives:
            card = DriveCard(drive)
            card.drive_selected.connect(self._on_drive_card_selected)
            self.drive_cards.append(card)
            self.drives_layout.addWidget(card)

        self.drives_layout.addStretch()
        self._apply_filters()
        
        # Emitir sinal
        self.drives_refreshed.emit(drives)

    def _on_detection_error(self, error_message: str):
        """Manipula erro na detecção."""
        self.logger.error(f"Erro na detecção de drives: {error_message}")
        self.status_label.setText(f"Erro: {error_message}")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #dc3545;
                font-weight: 500;
                padding: 4px 8px;
                background-color: #f8d7da;
                border-radius: 4px;
            }
        """)

    def _on_detection_finished(self):
        """Manipula fim da detecção."""
        self.refresh_button.setText("🔄 Detectar Drives")
        self.refresh_button.setEnabled(True)
        
        if self.status_label.text().startswith("Detectando"):
            self.status_label.setText("Pronto")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #28a745;
                    font-weight: 500;
                    padding: 4px 8px;
                    background-color: #d4edda;
                    border-radius: 4px;
                }
            """)

    def _on_drive_card_selected(self, drive_info: DriveInfo):
        """Manipula seleção de card de drive."""
        if drive_info in self.selected_drives:
            self.selected_drives.remove(drive_info)
        else:
            self.selected_drives.append(drive_info)
        
        self._update_selection_info()
        self.drive_selected.emit(drive_info)
        self.selection_changed.emit(self.selected_drives)

    def _apply_filters(self):
        """Aplica filtros aos cards de drives."""
        filter_type = self.type_filter.currentText()
        
        for card in self.drive_cards:
            should_show = True
            
            if filter_type != "Todos":
                drive_type_map = {
                    "HDD": DriveType.HDD,
                    "SSD": DriveType.SSD,
                    "USB": DriveType.USB,
                    "Óptico": DriveType.OPTICAL,
                    "Rede": DriveType.NETWORK
                }
                
                if filter_type in drive_type_map:
                    should_show = card.drive_info.drive_type == drive_type_map[filter_type]
            
            card.setVisible(should_show)

    def _update_selection_info(self):
        """Atualiza informações de seleção."""
        count = len(self.selected_drives)
        
        if count == 0:
            self.selection_info.setText("Nenhum drive selecionado")
            self.action_button.setEnabled(False)
        elif count == 1:
            drive = self.selected_drives[0]
            self.selection_info.setText(f"1 drive selecionado: {drive.letter}")
            self.action_button.setEnabled(True)
        else:
            drives_text = ", ".join([d.letter for d in self.selected_drives])
            self.selection_info.setText(f"{count} drives selecionados: {drives_text}")
            self.action_button.setEnabled(True)

    def _configure_selected_drives(self):
        """Configura drives selecionados."""
        if not self.selected_drives:
            return

        # Aqui seria implementada a lógica de configuração
        # Por enquanto, apenas mostra uma mensagem
        QMessageBox.information(
            self,
            "Configuração",
            f"Configurando {len(self.selected_drives)} drive(s) selecionado(s)..."
        )

    def _clear_drive_cards(self):
        """Remove todos os cards de drives."""
        for card in self.drive_cards:
            card.setParent(None)
            card.deleteLater()
        
        self.drive_cards.clear()
        self.selected_drives.clear()
        self._update_selection_info()

    def _auto_refresh(self):
        """Auto-refresh periódico."""
        # Apenas refresh se não estiver detectando
        if not (self.detection_worker and self.detection_worker.isRunning()):
            self.refresh_drives()

    def get_selected_drives(self) -> List[DriveInfo]:
        """Retorna drives selecionados."""
        return self.selected_drives.copy()

    def closeEvent(self, event):
        """Manipula fechamento do widget."""
        self.refresh_timer.stop()
        if self.detection_worker and self.detection_worker.isRunning():
            self.detection_worker.quit()
            self.detection_worker.wait()
        super().closeEvent(event)