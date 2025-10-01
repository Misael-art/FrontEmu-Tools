"""
System Info Widget

Widget para exibir informações do sistema, incluindo verificação de espaço em disco,
informações do drive padrão e métricas básicas do sistema.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

try:
    from PySide6.QtCore import QTimer, Signal, QThread, Qt
    from PySide6.QtGui import QFont, QPixmap, QPainter, QColor
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QGroupBox, QProgressBar, QGridLayout, QFrame, QScrollArea,
        QMessageBox, QSizePolicy, QSpacerItem
    )
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback classes for non-GUI environments
    class QWidget:
        def __init__(self, parent=None): pass
    class Signal: pass
    class QThread: pass


class SystemInfoWorker(QThread):
    """Worker thread para coleta de informações do sistema."""
    
    # Signals
    info_updated = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, container):
        """Inicializa o worker de informações do sistema.
        
        Args:
            container: ApplicationContainer com os serviços
        """
        super().__init__()
        self.container = container
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = False
    
    def run(self):
        """Executa a coleta de informações em background."""
        try:
            self.running = True
            
            # Obter serviços
            system_info_service = self.container.system_info_service()
            drive_manager_service = self.container.drive_manager_service()
            
            # Inicializar serviços se necessário
            if not hasattr(system_info_service, '_initialized'):
                system_info_service.initialize()
            
            if not hasattr(drive_manager_service, '_initialized'):
                drive_manager_service.initialize()
            
            # Coletar informações
            system_info = system_info_service.get_system_info()
            drive_info = drive_manager_service.get_default_drive_info()
            
            # Verificar espaço em disco do drive padrão
            default_drive = drive_manager_service.get_default_drive()
            if default_drive:
                disk_space = system_info_service.check_disk_space(f"{default_drive}\\", 1.0)
            else:
                disk_space = system_info_service.check_disk_space("C:\\", 1.0)
            
            # Combinar informações
            combined_info = {
                'system': system_info,
                'drive': drive_info,
                'disk_space': disk_space,
                'timestamp': system_info.get('timestamp')
            }
            
            self.info_updated.emit(combined_info)
            
        except Exception as e:
            self.logger.error(f"Erro ao coletar informações do sistema: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.running = False
    
    def stop(self):
        """Para a execução do worker."""
        self.running = False
        if self.isRunning():
            self.quit()
            self.wait(5000)  # Aguarda até 5 segundos


class SystemInfoWidget(QWidget):
    """Widget para exibir informações do sistema e verificação de espaço em disco."""
    
    # Signals
    refresh_requested = Signal()
    drive_changed = Signal(str)
    
    def __init__(self, container, parent: QWidget = None):
        """Inicializa o widget de informações do sistema.
        
        Args:
            container: ApplicationContainer com os serviços
            parent: Widget pai (opcional)
        """
        super().__init__(parent)
        
        self.container = container
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Worker para coleta de informações
        self.info_worker = None
        
        # Timer para atualização automática
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_info)
        
        # Dados atuais
        self.current_info = {}
        
        # Configurar UI
        self._setup_ui()
        self._setup_connections()
        
        # Carregar informações iniciais
        self._refresh_info()
        
        # Configurar atualização automática (a cada 30 segundos)
        self.refresh_timer.start(30000)
    
    def _setup_ui(self):
        """Configura a interface do usuário."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título e botão de atualização
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Informações do Sistema")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setMaximumWidth(100)
        self.refresh_button.clicked.connect(self._refresh_info)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Área de scroll para o conteúdo
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Widget de conteúdo
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # Seção de informações do sistema
        self.system_group = self._create_system_info_group()
        content_layout.addWidget(self.system_group)
        
        # Seção de informações do drive
        self.drive_group = self._create_drive_info_group()
        content_layout.addWidget(self.drive_group)
        
        # Seção de espaço em disco
        self.disk_space_group = self._create_disk_space_group()
        content_layout.addWidget(self.disk_space_group)
        
        # Seção de recomendações
        self.recommendations_group = self._create_recommendations_group()
        content_layout.addWidget(self.recommendations_group)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # Status bar
        self.status_label = QLabel("Carregando informações...")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
    
    def _create_system_info_group(self) -> QGroupBox:
        """Cria o grupo de informações do sistema."""
        group = QGroupBox("Sistema")
        layout = QGridLayout(group)
        
        # Labels para informações do sistema
        self.os_label = QLabel("Sistema Operacional:")
        self.os_value = QLabel("-")
        layout.addWidget(self.os_label, 0, 0)
        layout.addWidget(self.os_value, 0, 1)
        
        self.arch_label = QLabel("Arquitetura:")
        self.arch_value = QLabel("-")
        layout.addWidget(self.arch_label, 1, 0)
        layout.addWidget(self.arch_value, 1, 1)
        
        self.cpu_label = QLabel("Processador:")
        self.cpu_value = QLabel("-")
        layout.addWidget(self.cpu_label, 2, 0)
        layout.addWidget(self.cpu_value, 2, 1)
        
        self.memory_label = QLabel("Memória Total:")
        self.memory_value = QLabel("-")
        layout.addWidget(self.memory_label, 3, 0)
        layout.addWidget(self.memory_value, 3, 1)
        
        self.user_label = QLabel("Usuário:")
        self.user_value = QLabel("-")
        layout.addWidget(self.user_label, 4, 0)
        layout.addWidget(self.user_value, 4, 1)
        
        # Configurar expansão das colunas
        layout.setColumnStretch(1, 1)
        
        return group
    
    def _create_drive_info_group(self) -> QGroupBox:
        """Cria o grupo de informações do drive."""
        group = QGroupBox("Drive Padrão")
        layout = QGridLayout(group)
        
        # Labels para informações do drive
        self.drive_letter_label = QLabel("Drive:")
        self.drive_letter_value = QLabel("-")
        layout.addWidget(self.drive_letter_label, 0, 0)
        layout.addWidget(self.drive_letter_value, 0, 1)
        
        self.drive_type_label = QLabel("Tipo:")
        self.drive_type_value = QLabel("-")
        layout.addWidget(self.drive_type_label, 1, 0)
        layout.addWidget(self.drive_type_value, 1, 1)
        
        self.file_system_label = QLabel("Sistema de Arquivos:")
        self.file_system_value = QLabel("-")
        layout.addWidget(self.file_system_label, 2, 0)
        layout.addWidget(self.file_system_value, 2, 1)
        
        self.drive_label_label = QLabel("Rótulo:")
        self.drive_label_value = QLabel("-")
        layout.addWidget(self.drive_label_label, 3, 0)
        layout.addWidget(self.drive_label_value, 3, 1)
        
        # Configurar expansão das colunas
        layout.setColumnStretch(1, 1)
        
        return group
    
    def _create_disk_space_group(self) -> QGroupBox:
        """Cria o grupo de informações de espaço em disco."""
        group = QGroupBox("Espaço em Disco")
        layout = QVBoxLayout(group)
        
        # Grid para informações numéricas
        info_layout = QGridLayout()
        
        self.total_space_label = QLabel("Espaço Total:")
        self.total_space_value = QLabel("-")
        info_layout.addWidget(self.total_space_label, 0, 0)
        info_layout.addWidget(self.total_space_value, 0, 1)
        
        self.used_space_label = QLabel("Espaço Usado:")
        self.used_space_value = QLabel("-")
        info_layout.addWidget(self.used_space_label, 1, 0)
        info_layout.addWidget(self.used_space_value, 1, 1)
        
        self.free_space_label = QLabel("Espaço Livre:")
        self.free_space_value = QLabel("-")
        info_layout.addWidget(self.free_space_label, 2, 0)
        info_layout.addWidget(self.free_space_value, 2, 1)
        
        # Configurar expansão das colunas
        info_layout.setColumnStretch(1, 1)
        layout.addLayout(info_layout)
        
        # Barra de progresso para uso do disco
        usage_layout = QHBoxLayout()
        usage_layout.addWidget(QLabel("Uso:"))
        
        self.disk_usage_bar = QProgressBar()
        self.disk_usage_bar.setRange(0, 100)
        self.disk_usage_bar.setValue(0)
        self.disk_usage_bar.setTextVisible(True)
        usage_layout.addWidget(self.disk_usage_bar)
        
        layout.addLayout(usage_layout)
        
        return group
    
    def _create_recommendations_group(self) -> QGroupBox:
        """Cria o grupo de recomendações."""
        group = QGroupBox("Recomendações")
        layout = QVBoxLayout(group)
        
        self.recommendations_label = QLabel("Nenhuma recomendação disponível.")
        self.recommendations_label.setWordWrap(True)
        self.recommendations_label.setStyleSheet("color: #666;")
        layout.addWidget(self.recommendations_label)
        
        return group
    
    def _setup_connections(self):
        """Configura as conexões de sinais."""
        self.refresh_requested.connect(self._refresh_info)
    
    def _refresh_info(self):
        """Atualiza as informações do sistema."""
        try:
            # Parar worker anterior se estiver rodando
            if self.info_worker and self.info_worker.isRunning():
                self.info_worker.stop()
            
            # Criar novo worker
            self.info_worker = SystemInfoWorker(self.container)
            self.info_worker.info_updated.connect(self._on_info_updated)
            self.info_worker.error_occurred.connect(self._on_error_occurred)
            
            # Atualizar status
            self.status_label.setText("Atualizando informações...")
            self.refresh_button.setEnabled(False)
            
            # Iniciar coleta
            self.info_worker.start()
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar atualização: {e}")
            self._on_error_occurred(str(e))
    
    def _on_info_updated(self, info: Dict[str, Any]):
        """Callback chamado quando as informações são atualizadas.
        
        Args:
            info: Dicionário com as informações coletadas
        """
        try:
            self.current_info = info
            
            # Atualizar informações do sistema
            system_info = info.get('system', {})
            self._update_system_info(system_info)
            
            # Atualizar informações do drive
            drive_info = info.get('drive', {})
            self._update_drive_info(drive_info)
            
            # Atualizar informações de espaço em disco
            disk_space = info.get('disk_space', {})
            self._update_disk_space_info(disk_space)
            
            # Atualizar recomendações
            self._update_recommendations(disk_space)
            
            # Atualizar status
            timestamp = info.get('timestamp', 'Desconhecido')
            self.status_label.setText(f"Última atualização: {timestamp}")
            
        except Exception as e:
            self.logger.error(f"Erro ao processar informações: {e}")
            self._on_error_occurred(str(e))
        finally:
            self.refresh_button.setEnabled(True)
    
    def _update_system_info(self, system_info: Dict[str, Any]):
        """Atualiza as informações do sistema na UI.
        
        Args:
            system_info: Dicionário com informações do sistema
        """
        self.os_value.setText(system_info.get('os', 'Desconhecido'))
        self.arch_value.setText(system_info.get('architecture', 'Desconhecido'))
        self.cpu_value.setText(system_info.get('processor', 'Desconhecido'))
        
        # Formatar memória
        memory_gb = system_info.get('memory_gb', 0)
        if memory_gb > 0:
            self.memory_value.setText(f"{memory_gb:.1f} GB")
        else:
            self.memory_value.setText("Desconhecido")
        
        self.user_value.setText(system_info.get('username', 'Desconhecido'))
    
    def _update_drive_info(self, drive_info: Dict[str, Any]):
        """Atualiza as informações do drive na UI.
        
        Args:
            drive_info: Dicionário com informações do drive
        """
        self.drive_letter_value.setText(drive_info.get('drive', 'Desconhecido'))
        self.drive_type_value.setText(drive_info.get('type', 'Desconhecido'))
        self.file_system_value.setText(drive_info.get('file_system', 'Desconhecido'))
        self.drive_label_value.setText(drive_info.get('label', 'Sem rótulo'))
    
    def _update_disk_space_info(self, disk_space: Dict[str, Any]):
        """Atualiza as informações de espaço em disco na UI.
        
        Args:
            disk_space: Dicionário com informações de espaço em disco
        """
        # Obter valores em bytes
        total_bytes = disk_space.get('total_space', 0)
        used_bytes = disk_space.get('used_space', 0)
        free_bytes = disk_space.get('free_space', 0)
        
        # Converter para GB
        total_gb = total_bytes / (1024**3) if total_bytes > 0 else 0
        used_gb = used_bytes / (1024**3) if used_bytes > 0 else 0
        free_gb = free_bytes / (1024**3) if free_bytes > 0 else 0
        
        # Atualizar labels
        self.total_space_value.setText(f"{total_gb:.1f} GB")
        self.used_space_value.setText(f"{used_gb:.1f} GB")
        self.free_space_value.setText(f"{free_gb:.1f} GB")
        
        # Calcular e atualizar barra de progresso
        if total_bytes > 0:
            usage_percent = (used_bytes / total_bytes) * 100
            self.disk_usage_bar.setValue(int(usage_percent))
            
            # Definir cor da barra baseada no uso
            if usage_percent > 90:
                self.disk_usage_bar.setStyleSheet("QProgressBar::chunk { background-color: #dc3545; }")
            elif usage_percent > 80:
                self.disk_usage_bar.setStyleSheet("QProgressBar::chunk { background-color: #ffc107; }")
            else:
                self.disk_usage_bar.setStyleSheet("QProgressBar::chunk { background-color: #28a745; }")
        else:
            self.disk_usage_bar.setValue(0)
            self.disk_usage_bar.setStyleSheet("")
    
    def _update_recommendations(self, disk_space: Dict[str, Any]):
        """Atualiza as recomendações baseadas no espaço em disco.
        
        Args:
            disk_space: Dicionário com informações de espaço em disco
        """
        recommendations = disk_space.get('recommendations', [])
        
        if recommendations:
            # Combinar recomendações em texto
            rec_text = "\n".join([f"• {rec}" for rec in recommendations])
            self.recommendations_label.setText(rec_text)
            self.recommendations_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        else:
            # Verificar se há espaço suficiente
            free_bytes = disk_space.get('free_space', 0)
            free_gb = free_bytes / (1024**3) if free_bytes > 0 else 0
            
            if free_gb > 50:
                self.recommendations_label.setText("✓ Espaço em disco suficiente para operações.")
                self.recommendations_label.setStyleSheet("color: #28a745;")
            elif free_gb > 20:
                self.recommendations_label.setText("⚠ Espaço em disco adequado, mas monitore o uso.")
                self.recommendations_label.setStyleSheet("color: #ffc107;")
            else:
                self.recommendations_label.setText("⚠ Pouco espaço em disco disponível.")
                self.recommendations_label.setStyleSheet("color: #dc3545;")
    
    def _on_error_occurred(self, error_message: str):
        """Callback chamado quando ocorre um erro.
        
        Args:
            error_message: Mensagem de erro
        """
        self.logger.error(f"Erro no SystemInfoWidget: {error_message}")
        
        # Atualizar status
        self.status_label.setText(f"Erro: {error_message}")
        self.refresh_button.setEnabled(True)
        
        # Mostrar mensagem de erro
        QMessageBox.warning(
            self,
            "Erro",
            f"Erro ao obter informações do sistema:\n{error_message}"
        )
    
    def get_current_info(self) -> Dict[str, Any]:
        """Retorna as informações atuais do sistema.
        
        Returns:
            Dicionário com as informações atuais
        """
        return self.current_info.copy()
    
    def closeEvent(self, event):
        """Evento chamado ao fechar o widget."""
        # Parar timer
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        
        # Parar worker
        if self.info_worker and self.info_worker.isRunning():
            self.info_worker.stop()
        
        super().closeEvent(event)