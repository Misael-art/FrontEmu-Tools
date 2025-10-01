"""
System Info Widget

Widget modernizado para exibir informações detalhadas do sistema
seguindo as especificações de UI/UX e Clean Architecture.
"""

from typing import Optional, Dict, Any
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QPushButton, QProgressBar,
    QGroupBox, QTextEdit
)
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor

from ...infrastructure import DependencyContainer
from ...app.logging_config import get_logger


class InfoCard(QFrame):
    """Card moderno para exibir informações do sistema."""

    def __init__(self, title: str, value: str, icon: str = "📊", parent=None):
        """Inicializa o card de informação."""
        super().__init__(parent)
        self.title = title
        self.value = value
        self.icon = icon
        
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """Configura a interface do card."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Header com ícone e título
        header_layout = QHBoxLayout()
        
        # Ícone
        icon_label = QLabel(self.icon)
        icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)
        
        # Título
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                color: #495057;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        # Valor
        self.value_label = QLabel(self.value)
        self.value_label.setStyleSheet("""
            QLabel {
                color: #32CD32;
                font-size: 20px;
                font-weight: bold;
                margin-top: 4px;
            }
        """)
        layout.addWidget(self.value_label)

    def _apply_style(self):
        """Aplica estilo moderno ao card."""
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

    def update_value(self, new_value: str):
        """Atualiza o valor do card."""
        self.value = new_value
        self.value_label.setText(new_value)


class SystemInfoWidget(QWidget):
    """Widget modernizado para informações do sistema."""

    # Sinais
    refresh_requested = Signal()
    info_updated = Signal(dict)

    def __init__(self, container: DependencyContainer, parent=None):
        """Inicializa o widget de informações do sistema."""
        super().__init__(parent)
        
        self.container = container
        self.logger = get_logger(__name__)
        
        # Timer para atualizações automáticas
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._auto_refresh)
        
        # Dados do sistema
        self.system_data: Dict[str, Any] = {}
        
        # Cards de informação
        self.info_cards: Dict[str, InfoCard] = {}
        
        self._setup_ui()
        self._apply_modern_style()
        self._load_initial_data()
        
        # Iniciar atualizações automáticas (a cada 10 segundos)
        self.update_timer.start(10000)

    def _setup_ui(self):
        """Configura a interface do widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        self._create_header(layout)

        # Área de scroll para os cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Widget de conteúdo
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(20)

        # Seções de informações
        self._create_system_overview_section()
        self._create_hardware_section()
        self._create_performance_section()
        self._create_storage_section()

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

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
        title_label = QLabel("📊 Informações do Sistema")
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
        self.refresh_button = QPushButton("🔄 Atualizar")
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
        self.refresh_button.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_button)

        layout.addWidget(header_frame)

    def _create_system_overview_section(self):
        """Cria seção de visão geral do sistema."""
        section = self._create_section("🖥️ Visão Geral do Sistema")
        
        cards_layout = QGridLayout()
        cards_layout.setSpacing(12)

        # Cards de informações básicas
        self.info_cards["os"] = InfoCard("Sistema Operacional", "Carregando...", "🖥️")
        self.info_cards["hostname"] = InfoCard("Nome do Computador", "Carregando...", "🏷️")
        self.info_cards["uptime"] = InfoCard("Tempo Ligado", "Carregando...", "⏰")
        self.info_cards["user"] = InfoCard("Usuário Atual", "Carregando...", "👤")

        cards_layout.addWidget(self.info_cards["os"], 0, 0)
        cards_layout.addWidget(self.info_cards["hostname"], 0, 1)
        cards_layout.addWidget(self.info_cards["uptime"], 1, 0)
        cards_layout.addWidget(self.info_cards["user"], 1, 1)

        section.layout().addLayout(cards_layout)
        self.content_layout.addWidget(section)

    def _create_hardware_section(self):
        """Cria seção de hardware."""
        section = self._create_section("⚙️ Hardware")
        
        cards_layout = QGridLayout()
        cards_layout.setSpacing(12)

        # Cards de hardware
        self.info_cards["cpu"] = InfoCard("Processador", "Carregando...", "🔧")
        self.info_cards["memory"] = InfoCard("Memória RAM", "Carregando...", "💾")
        self.info_cards["gpu"] = InfoCard("Placa de Vídeo", "Carregando...", "🎮")
        self.info_cards["architecture"] = InfoCard("Arquitetura", "Carregando...", "🏗️")

        cards_layout.addWidget(self.info_cards["cpu"], 0, 0)
        cards_layout.addWidget(self.info_cards["memory"], 0, 1)
        cards_layout.addWidget(self.info_cards["gpu"], 1, 0)
        cards_layout.addWidget(self.info_cards["architecture"], 1, 1)

        section.layout().addLayout(cards_layout)
        self.content_layout.addWidget(section)

    def _create_performance_section(self):
        """Cria seção de performance."""
        section = self._create_section("📈 Performance Atual")
        
        cards_layout = QGridLayout()
        cards_layout.setSpacing(12)

        # Cards de performance
        self.info_cards["cpu_usage"] = InfoCard("Uso da CPU", "Carregando...", "📊")
        self.info_cards["memory_usage"] = InfoCard("Uso da RAM", "Carregando...", "📈")
        self.info_cards["disk_usage"] = InfoCard("Uso do Disco", "Carregando...", "💿")
        self.info_cards["network"] = InfoCard("Rede", "Carregando...", "🌐")

        cards_layout.addWidget(self.info_cards["cpu_usage"], 0, 0)
        cards_layout.addWidget(self.info_cards["memory_usage"], 0, 1)
        cards_layout.addWidget(self.info_cards["disk_usage"], 1, 0)
        cards_layout.addWidget(self.info_cards["network"], 1, 1)

        section.layout().addLayout(cards_layout)
        self.content_layout.addWidget(section)

    def _create_storage_section(self):
        """Cria seção de armazenamento."""
        section = self._create_section("💾 Armazenamento")
        
        # Área de texto para informações detalhadas de drives
        self.storage_text = QTextEdit()
        self.storage_text.setReadOnly(True)
        self.storage_text.setMaximumHeight(200)
        self.storage_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        
        section.layout().addWidget(self.storage_text)
        self.content_layout.addWidget(section)

    def _create_section(self, title: str) -> QGroupBox:
        """Cria uma seção com título."""
        section = QGroupBox(title)
        section.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #495057;
                border: 2px solid #e9ecef;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px 0 8px;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(12)
        
        return section

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

    def _load_initial_data(self):
        """Carrega dados iniciais do sistema."""
        try:
            # Obter serviços do container
            file_system_service = self.container.get_file_system_service()
            system_monitoring_service = self.container.get_system_monitoring_service()
            
            # Coletar informações básicas do sistema
            self._update_system_overview()
            self._update_hardware_info()
            self._update_performance_info()
            self._update_storage_info()
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar dados iniciais: {e}")

    def _update_system_overview(self):
        """Atualiza informações de visão geral."""
        try:
            import platform
            import getpass
            import datetime
            import psutil

            # Sistema operacional
            os_info = f"{platform.system()} {platform.release()}"
            self.info_cards["os"].update_value(os_info)

            # Nome do computador
            hostname = platform.node()
            self.info_cards["hostname"].update_value(hostname)

            # Tempo ligado
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.datetime.now() - boot_time
            uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
            self.info_cards["uptime"].update_value(uptime_str)

            # Usuário atual
            user = getpass.getuser()
            self.info_cards["user"].update_value(user)

        except Exception as e:
            self.logger.error(f"Erro ao atualizar visão geral: {e}")

    def _update_hardware_info(self):
        """Atualiza informações de hardware."""
        try:
            import platform
            import psutil

            # CPU
            cpu_info = platform.processor() or "Processador não identificado"
            if len(cpu_info) > 50:
                cpu_info = cpu_info[:47] + "..."
            self.info_cards["cpu"].update_value(cpu_info)

            # Memória
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            self.info_cards["memory"].update_value(f"{memory_gb:.1f} GB")

            # Arquitetura
            arch = platform.architecture()[0]
            self.info_cards["architecture"].update_value(arch)

            # GPU (informação básica)
            self.info_cards["gpu"].update_value("Detectando...")

        except Exception as e:
            self.logger.error(f"Erro ao atualizar hardware: {e}")

    def _update_performance_info(self):
        """Atualiza informações de performance."""
        try:
            import psutil

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.info_cards["cpu_usage"].update_value(f"{cpu_percent:.1f}%")

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.info_cards["memory_usage"].update_value(f"{memory_percent:.1f}%")

            # Disk usage (drive C:)
            try:
                disk = psutil.disk_usage('C:')
                disk_percent = (disk.used / disk.total) * 100
                self.info_cards["disk_usage"].update_value(f"{disk_percent:.1f}%")
            except:
                self.info_cards["disk_usage"].update_value("N/A")

            # Network (basic status)
            net_io = psutil.net_io_counters()
            if net_io:
                self.info_cards["network"].update_value("Ativo")
            else:
                self.info_cards["network"].update_value("Inativo")

        except Exception as e:
            self.logger.error(f"Erro ao atualizar performance: {e}")

    def _update_storage_info(self):
        """Atualiza informações de armazenamento."""
        try:
            import psutil

            storage_info = []
            storage_info.append("=== DRIVES DETECTADOS ===\n")

            # Listar todos os drives
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    total_gb = usage.total / (1024**3)
                    used_gb = usage.used / (1024**3)
                    free_gb = usage.free / (1024**3)
                    percent = (usage.used / usage.total) * 100

                    storage_info.append(f"Drive: {partition.device}")
                    storage_info.append(f"  Tipo: {partition.fstype}")
                    storage_info.append(f"  Total: {total_gb:.1f} GB")
                    storage_info.append(f"  Usado: {used_gb:.1f} GB ({percent:.1f}%)")
                    storage_info.append(f"  Livre: {free_gb:.1f} GB")
                    storage_info.append("")

                except PermissionError:
                    storage_info.append(f"Drive: {partition.device}")
                    storage_info.append("  Status: Acesso negado")
                    storage_info.append("")

            self.storage_text.setPlainText("\n".join(storage_info))

        except Exception as e:
            self.logger.error(f"Erro ao atualizar armazenamento: {e}")
            self.storage_text.setPlainText(f"Erro ao carregar informações de armazenamento: {e}")

    def _auto_refresh(self):
        """Atualização automática dos dados."""
        self._update_performance_info()

    def refresh_data(self):
        """Atualiza todos os dados do sistema."""
        try:
            self.refresh_button.setText("🔄 Atualizando...")
            self.refresh_button.setEnabled(False)
            
            self._update_system_overview()
            self._update_hardware_info()
            self._update_performance_info()
            self._update_storage_info()
            
            # Emitir sinal de atualização
            self.info_updated.emit(self.system_data)
            self.refresh_requested.emit()
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar dados: {e}")
        finally:
            self.refresh_button.setText("🔄 Atualizar")
            self.refresh_button.setEnabled(True)

    def get_system_data(self) -> Dict[str, Any]:
        """Retorna dados atuais do sistema."""
        return self.system_data.copy()

    def closeEvent(self, event):
        """Manipula fechamento do widget."""
        self.update_timer.stop()
        super().closeEvent(event)