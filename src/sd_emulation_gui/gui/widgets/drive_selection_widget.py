"""
Drive Selection Widget

Widget para seleção de drives alternativos, exibindo informações detalhadas
sobre drives disponíveis e permitindo configuração de preferências.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

try:
    from PySide6.QtCore import QTimer, Signal, QThread, Qt, QModelIndex
    from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QStandardItemModel, QStandardItem
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QGroupBox, QProgressBar, QGridLayout, QFrame, QScrollArea,
        QMessageBox, QSizePolicy, QSpacerItem, QComboBox, QTableView,
        QHeaderView, QCheckBox, QSpinBox, QLineEdit, QTextEdit,
        QTabWidget, QListWidget, QListWidgetItem, QAbstractItemView
    )
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback classes for non-GUI environments
    class QWidget:
        def __init__(self, parent=None): pass
    class Signal: pass
    class QThread: pass


class DriveInfoWorker(QThread):
    """Worker thread para coleta de informações de drives."""
    
    # Signals
    drives_updated = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self, container):
        """Inicializa o worker de informações de drives.
        
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
            
            # Obter serviço
            drive_manager_service = self.container.drive_manager_service()
            
            # Inicializar serviço se necessário
            if not hasattr(drive_manager_service, '_initialized'):
                drive_manager_service.initialize()
            
            # Coletar informações
            available_drives = drive_manager_service.get_available_drives()
            recommended_drives = drive_manager_service.get_recommended_drives()
            default_drive = drive_manager_service.get_default_drive_info()
            drive_stats = drive_manager_service.get_drive_statistics()
            
            # Combinar informações
            drives_info = {
                'available': available_drives,
                'recommended': recommended_drives,
                'default': default_drive,
                'statistics': drive_stats
            }
            
            self.drives_updated.emit(drives_info)
            
        except Exception as e:
            self.logger.error(f"Erro ao coletar informações de drives: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.running = False
    
    def stop(self):
        """Para a execução do worker."""
        self.running = False
        if self.isRunning():
            self.quit()
            self.wait(5000)  # Aguarda até 5 segundos


class DriveSelectionWidget(QWidget):
    """Widget para seleção de drives alternativos e configuração de preferências."""
    
    # Signals
    drive_selected = Signal(str)
    preferences_changed = Signal(dict)
    refresh_requested = Signal()
    
    def __init__(self, container, parent: QWidget = None):
        """Inicializa o widget de seleção de drives.
        
        Args:
            container: ApplicationContainer com os serviços
            parent: Widget pai (opcional)
        """
        super().__init__(parent)
        
        self.container = container
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Worker para coleta de informações
        self.drive_worker = None
        
        # Timer para atualização automática
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_drives)
        
        # Dados atuais
        self.current_drives = {}
        self.selected_drive = None
        
        # Configurar UI
        self._setup_ui()
        self._setup_connections()
        
        # Carregar informações iniciais
        self._refresh_drives()
        
        # Configurar atualização automática (a cada 60 segundos)
        self.refresh_timer.start(60000)
    
    def _setup_ui(self):
        """Configura a interface do usuário."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título e botão de atualização
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Seleção de Drives")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.setMaximumWidth(100)
        self.refresh_button.clicked.connect(self._refresh_drives)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Tabs para organizar conteúdo
        self.tab_widget = QTabWidget()
        
        # Tab 1: Drives Disponíveis
        self.drives_tab = self._create_drives_tab()
        self.tab_widget.addTab(self.drives_tab, "Drives Disponíveis")
        
        # Tab 2: Configurações
        self.settings_tab = self._create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "Configurações")
        
        # Tab 3: Estatísticas
        self.stats_tab = self._create_statistics_tab()
        self.tab_widget.addTab(self.stats_tab, "Estatísticas")
        
        layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_label = QLabel("Carregando drives...")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
    
    def _create_drives_tab(self) -> QWidget:
        """Cria a tab de drives disponíveis."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Drive padrão
        default_group = QGroupBox("Drive Padrão")
        default_layout = QGridLayout(default_group)
        
        self.default_drive_label = QLabel("Drive:")
        self.default_drive_value = QLabel("-")
        default_layout.addWidget(self.default_drive_label, 0, 0)
        default_layout.addWidget(self.default_drive_value, 0, 1)
        
        self.default_space_label = QLabel("Espaço Livre:")
        self.default_space_value = QLabel("-")
        default_layout.addWidget(self.default_space_label, 1, 0)
        default_layout.addWidget(self.default_space_value, 1, 1)
        
        self.default_type_label = QLabel("Tipo:")
        self.default_type_value = QLabel("-")
        default_layout.addWidget(self.default_type_label, 2, 0)
        default_layout.addWidget(self.default_type_value, 2, 1)
        
        default_layout.setColumnStretch(1, 1)
        layout.addWidget(default_group)
        
        # Lista de drives disponíveis
        available_group = QGroupBox("Drives Disponíveis")
        available_layout = QVBoxLayout(available_group)
        
        # Filtros
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Mostrar:"))
        
        self.show_all_checkbox = QCheckBox("Todos os drives")
        self.show_all_checkbox.setChecked(True)
        self.show_all_checkbox.toggled.connect(self._update_drive_filter)
        filter_layout.addWidget(self.show_all_checkbox)
        
        self.show_recommended_checkbox = QCheckBox("Apenas recomendados")
        self.show_recommended_checkbox.toggled.connect(self._update_drive_filter)
        filter_layout.addWidget(self.show_recommended_checkbox)
        
        filter_layout.addStretch()
        available_layout.addLayout(filter_layout)
        
        # Lista de drives
        self.drives_list = QListWidget()
        self.drives_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.drives_list.itemClicked.connect(self._on_drive_selected)
        available_layout.addWidget(self.drives_list)
        
        # Informações do drive selecionado
        selection_group = QGroupBox("Drive Selecionado")
        selection_layout = QGridLayout(selection_group)
        
        self.selected_drive_label = QLabel("Drive:")
        self.selected_drive_value = QLabel("Nenhum drive selecionado")
        selection_layout.addWidget(self.selected_drive_label, 0, 0)
        selection_layout.addWidget(self.selected_drive_value, 0, 1)
        
        self.selected_space_label = QLabel("Espaço Total:")
        self.selected_space_value = QLabel("-")
        selection_layout.addWidget(self.selected_space_label, 1, 0)
        selection_layout.addWidget(self.selected_space_value, 1, 1)
        
        self.selected_free_label = QLabel("Espaço Livre:")
        self.selected_free_value = QLabel("-")
        selection_layout.addWidget(self.selected_free_label, 2, 0)
        selection_layout.addWidget(self.selected_free_value, 2, 1)
        
        self.selected_score_label = QLabel("Pontuação:")
        self.selected_score_value = QLabel("-")
        selection_layout.addWidget(self.selected_score_label, 3, 0)
        selection_layout.addWidget(self.selected_score_value, 3, 1)
        
        # Botão para definir como preferido
        self.set_preferred_button = QPushButton("Definir como Preferido")
        self.set_preferred_button.setEnabled(False)
        self.set_preferred_button.clicked.connect(self._set_preferred_drive)
        selection_layout.addWidget(self.set_preferred_button, 4, 0, 1, 2)
        
        selection_layout.setColumnStretch(1, 1)
        available_layout.addWidget(selection_group)
        
        layout.addWidget(available_group)
        
        return widget
    
    def _create_settings_tab(self) -> QWidget:
        """Cria a tab de configurações."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Configurações de filtro
        filter_group = QGroupBox("Filtros de Drive")
        filter_layout = QGridLayout(filter_group)
        
        # Espaço mínimo
        filter_layout.addWidget(QLabel("Espaço Mínimo (GB):"), 0, 0)
        self.min_space_spinbox = QSpinBox()
        self.min_space_spinbox.setRange(1, 10000)
        self.min_space_spinbox.setValue(50)
        self.min_space_spinbox.setSuffix(" GB")
        filter_layout.addWidget(self.min_space_spinbox, 0, 1)
        
        # Tipos de drive excluídos
        filter_layout.addWidget(QLabel("Excluir Tipos:"), 1, 0)
        exclude_layout = QVBoxLayout()
        
        self.exclude_removable_checkbox = QCheckBox("Drives removíveis")
        self.exclude_removable_checkbox.setChecked(True)
        exclude_layout.addWidget(self.exclude_removable_checkbox)
        
        self.exclude_network_checkbox = QCheckBox("Drives de rede")
        self.exclude_network_checkbox.setChecked(True)
        exclude_layout.addWidget(self.exclude_network_checkbox)
        
        self.exclude_optical_checkbox = QCheckBox("Drives ópticos")
        self.exclude_optical_checkbox.setChecked(True)
        exclude_layout.addWidget(self.exclude_optical_checkbox)
        
        filter_layout.addLayout(exclude_layout, 1, 1)
        
        layout.addWidget(filter_group)
        
        # Configurações de preferência
        pref_group = QGroupBox("Preferências")
        pref_layout = QGridLayout(pref_group)
        
        # Drive preferido
        pref_layout.addWidget(QLabel("Drive Preferido:"), 0, 0)
        self.preferred_drive_combo = QComboBox()
        self.preferred_drive_combo.addItem("Automático")
        pref_layout.addWidget(self.preferred_drive_combo, 0, 1)
        
        # Estratégia de seleção
        pref_layout.addWidget(QLabel("Estratégia:"), 1, 0)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "Maior espaço livre",
            "Melhor pontuação",
            "Drive C: (padrão)",
            "Primeiro disponível"
        ])
        pref_layout.addWidget(self.strategy_combo, 1, 1)
        
        pref_layout.setColumnStretch(1, 1)
        layout.addWidget(pref_group)
        
        # Botões de ação
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.apply_settings_button = QPushButton("Aplicar Configurações")
        self.apply_settings_button.clicked.connect(self._apply_settings)
        buttons_layout.addWidget(self.apply_settings_button)
        
        self.reset_settings_button = QPushButton("Restaurar Padrões")
        self.reset_settings_button.clicked.connect(self._reset_settings)
        buttons_layout.addWidget(self.reset_settings_button)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
        
        return widget
    
    def _create_statistics_tab(self) -> QWidget:
        """Cria a tab de estatísticas."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Estatísticas gerais
        stats_group = QGroupBox("Estatísticas Gerais")
        stats_layout = QGridLayout(stats_group)
        
        self.total_drives_label = QLabel("Total de Drives:")
        self.total_drives_value = QLabel("-")
        stats_layout.addWidget(self.total_drives_label, 0, 0)
        stats_layout.addWidget(self.total_drives_value, 0, 1)
        
        self.available_drives_label = QLabel("Drives Disponíveis:")
        self.available_drives_value = QLabel("-")
        stats_layout.addWidget(self.available_drives_label, 1, 0)
        stats_layout.addWidget(self.available_drives_value, 1, 1)
        
        self.recommended_drives_label = QLabel("Drives Recomendados:")
        self.recommended_drives_value = QLabel("-")
        stats_layout.addWidget(self.recommended_drives_label, 2, 0)
        stats_layout.addWidget(self.recommended_drives_value, 2, 1)
        
        self.total_space_label = QLabel("Espaço Total:")
        self.total_space_value = QLabel("-")
        stats_layout.addWidget(self.total_space_label, 3, 0)
        stats_layout.addWidget(self.total_space_value, 3, 1)
        
        self.total_free_label = QLabel("Espaço Livre Total:")
        self.total_free_value = QLabel("-")
        stats_layout.addWidget(self.total_free_label, 4, 0)
        stats_layout.addWidget(self.total_free_value, 4, 1)
        
        stats_layout.setColumnStretch(1, 1)
        layout.addWidget(stats_group)
        
        # Resumo de tipos
        types_group = QGroupBox("Tipos de Drive")
        types_layout = QVBoxLayout(types_group)
        
        self.types_text = QTextEdit()
        self.types_text.setReadOnly(True)
        self.types_text.setMaximumHeight(150)
        types_layout.addWidget(self.types_text)
        
        layout.addWidget(types_group)
        
        layout.addStretch()
        
        return widget
    
    def _setup_connections(self):
        """Configura as conexões de sinais."""
        self.refresh_requested.connect(self._refresh_drives)
        
        # Conectar mudanças de configuração
        self.min_space_spinbox.valueChanged.connect(self._on_settings_changed)
        self.exclude_removable_checkbox.toggled.connect(self._on_settings_changed)
        self.exclude_network_checkbox.toggled.connect(self._on_settings_changed)
        self.exclude_optical_checkbox.toggled.connect(self._on_settings_changed)
        self.strategy_combo.currentTextChanged.connect(self._on_settings_changed)
    
    def _refresh_drives(self):
        """Atualiza as informações de drives."""
        try:
            # Parar worker anterior se estiver rodando
            if self.drive_worker and self.drive_worker.isRunning():
                self.drive_worker.stop()
            
            # Criar novo worker
            self.drive_worker = DriveInfoWorker(self.container)
            self.drive_worker.drives_updated.connect(self._on_drives_updated)
            self.drive_worker.error_occurred.connect(self._on_error_occurred)
            
            # Atualizar status
            self.status_label.setText("Atualizando drives...")
            self.refresh_button.setEnabled(False)
            
            # Iniciar coleta
            self.drive_worker.start()
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar atualização: {e}")
            self._on_error_occurred(str(e))
    
    def _on_drives_updated(self, drives_info: Dict[str, Any]):
        """Callback chamado quando as informações de drives são atualizadas.
        
        Args:
            drives_info: Dicionário com as informações de drives
        """
        try:
            self.current_drives = drives_info
            
            # Atualizar drive padrão
            default_drive = drives_info.get('default', {})
            if default_drive and isinstance(default_drive, dict):
                self._update_default_drive_info(default_drive)
            else:
                # Se default_drive não é um dicionário válido, usar valores padrão
                self._update_default_drive_info({
                    'drive': 'Desconhecido',
                    'type': 'Desconhecido',
                    'free_space': 0
                })
            
            # Atualizar lista de drives
            available_drives = drives_info.get('available', {})
            if isinstance(available_drives, dict):
                # Converter dicionário para lista
                drives_list = []
                for drive_letter, drive_info in available_drives.items():
                    drive_data = drive_info.copy() if isinstance(drive_info, dict) else {}
                    drive_data['drive'] = drive_letter
                    drives_list.append(drive_data)
                self._update_drives_list(drives_list)
            else:
                self._update_drives_list([])
            
            # Atualizar combo de drives preferidos
            if isinstance(available_drives, dict):
                drives_list = []
                for drive_letter, drive_info in available_drives.items():
                    drive_data = drive_info.copy() if isinstance(drive_info, dict) else {}
                    drive_data['drive'] = drive_letter
                    drives_list.append(drive_data)
                self._update_preferred_combo(drives_list)
            else:
                self._update_preferred_combo([])
            
            # Atualizar estatísticas
            statistics = drives_info.get('statistics', {})
            self._update_statistics(statistics)
            
            # Atualizar status
            drives_count = len(available_drives) if isinstance(available_drives, dict) else 0
            self.status_label.setText(f"Encontrados {drives_count} drives disponíveis")
            
        except Exception as e:
            self.logger.error(f"Erro ao processar informações de drives: {e}")
            self._on_error_occurred(str(e))
        finally:
            self.refresh_button.setEnabled(True)
    
    def _update_default_drive_info(self, default_drive: Dict[str, Any]):
        """Atualiza as informações do drive padrão.
        
        Args:
            default_drive: Dicionário com informações do drive padrão
        """
        self.default_drive_value.setText(default_drive.get('drive', 'Desconhecido'))
        self.default_type_value.setText(default_drive.get('type', 'Desconhecido'))
        
        # Formatar espaço livre
        free_bytes = default_drive.get('free_space', 0)
        if free_bytes > 0:
            free_gb = free_bytes / (1024**3)
            self.default_space_value.setText(f"{free_gb:.1f} GB")
        else:
            self.default_space_value.setText("Desconhecido")
    
    def _update_drives_list(self, drives: List[Dict[str, Any]]):
        """Atualiza a lista de drives disponíveis.
        
        Args:
            drives: Lista de drives disponíveis
        """
        self.drives_list.clear()
        
        for drive in drives:
            # Criar item da lista
            drive_letter = drive.get('drive', 'Desconhecido')
            drive_type = drive.get('type', 'Desconhecido')
            free_space = drive.get('free_space', 0)
            total_space = drive.get('total_space', 0)
            score = drive.get('suitability_score', 0)
            
            # Formatar espaços
            free_gb = free_space / (1024**3) if free_space > 0 else 0
            total_gb = total_space / (1024**3) if total_space > 0 else 0
            
            # Criar texto do item
            item_text = f"{drive_letter} - {drive_type} | {free_gb:.1f} GB livre de {total_gb:.1f} GB | Pontuação: {score:.1f}"
            
            # Criar item
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, drive)
            
            # Definir cor baseada na pontuação
            if score >= 8.0:
                item.setBackground(QColor(200, 255, 200))  # Verde claro
            elif score >= 6.0:
                item.setBackground(QColor(255, 255, 200))  # Amarelo claro
            elif score < 4.0:
                item.setBackground(QColor(255, 200, 200))  # Vermelho claro
            
            self.drives_list.addItem(item)
    
    def _update_preferred_combo(self, drives: List[Dict[str, Any]]):
        """Atualiza o combo de drives preferidos.
        
        Args:
            drives: Lista de drives disponíveis
        """
        current_text = self.preferred_drive_combo.currentText()
        
        self.preferred_drive_combo.clear()
        self.preferred_drive_combo.addItem("Automático")
        
        for drive in drives:
            drive_letter = drive.get('drive', 'Desconhecido')
            drive_type = drive.get('type', 'Desconhecido')
            self.preferred_drive_combo.addItem(f"{drive_letter} - {drive_type}")
        
        # Restaurar seleção anterior se possível
        index = self.preferred_drive_combo.findText(current_text)
        if index >= 0:
            self.preferred_drive_combo.setCurrentIndex(index)
    
    def _update_statistics(self, statistics: Dict[str, Any]):
        """Atualiza as estatísticas de drives.
        
        Args:
            statistics: Dicionário com estatísticas
        """
        # Estatísticas gerais
        self.total_drives_value.setText(str(statistics.get('total_drives', 0)))
        self.available_drives_value.setText(str(statistics.get('available_drives', 0)))
        self.recommended_drives_value.setText(str(statistics.get('recommended_drives', 0)))
        
        # Espaços totais
        total_space = statistics.get('total_space', 0)
        total_free = statistics.get('total_free_space', 0)
        
        if total_space > 0:
            total_gb = total_space / (1024**3)
            self.total_space_value.setText(f"{total_gb:.1f} GB")
        else:
            self.total_space_value.setText("Desconhecido")
        
        if total_free > 0:
            free_gb = total_free / (1024**3)
            self.total_free_value.setText(f"{free_gb:.1f} GB")
        else:
            self.total_free_value.setText("Desconhecido")
        
        # Tipos de drive
        drive_types = statistics.get('drive_types', {})
        if drive_types:
            types_text = "Distribuição por tipo:\n\n"
            for drive_type, count in drive_types.items():
                types_text += f"• {drive_type}: {count} drive(s)\n"
        else:
            types_text = "Nenhuma informação de tipos disponível."
        
        self.types_text.setPlainText(types_text)
    
    def _update_drive_filter(self):
        """Atualiza o filtro de exibição de drives."""
        # Implementar lógica de filtro se necessário
        pass
    
    def _on_drive_selected(self, item: QListWidgetItem):
        """Callback chamado quando um drive é selecionado.
        
        Args:
            item: Item selecionado na lista
        """
        drive_data = item.data(Qt.UserRole)
        if drive_data:
            self.selected_drive = drive_data
            self._update_selected_drive_info(drive_data)
            self.set_preferred_button.setEnabled(True)
            
            # Emitir sinal
            drive_letter = drive_data.get('drive', '')
            self.drive_selected.emit(drive_letter)
    
    def _update_selected_drive_info(self, drive_data: Dict[str, Any]):
        """Atualiza as informações do drive selecionado.
        
        Args:
            drive_data: Dados do drive selecionado
        """
        drive_letter = drive_data.get('drive', 'Desconhecido')
        total_space = drive_data.get('total_space', 0)
        free_space = drive_data.get('free_space', 0)
        score = drive_data.get('suitability_score', 0)
        
        self.selected_drive_value.setText(drive_letter)
        
        if total_space > 0:
            total_gb = total_space / (1024**3)
            self.selected_space_value.setText(f"{total_gb:.1f} GB")
        else:
            self.selected_space_value.setText("Desconhecido")
        
        if free_space > 0:
            free_gb = free_space / (1024**3)
            self.selected_free_value.setText(f"{free_gb:.1f} GB")
        else:
            self.selected_free_value.setText("Desconhecido")
        
        self.selected_score_value.setText(f"{score:.1f}/10")
    
    def _set_preferred_drive(self):
        """Define o drive selecionado como preferido."""
        if self.selected_drive:
            try:
                drive_letter = self.selected_drive.get('drive', '')
                
                # Atualizar combo
                combo_text = f"{drive_letter} - {self.selected_drive.get('type', 'Desconhecido')}"
                index = self.preferred_drive_combo.findText(combo_text)
                if index >= 0:
                    self.preferred_drive_combo.setCurrentIndex(index)
                
                # Aplicar configurações
                self._apply_settings()
                
                QMessageBox.information(
                    self,
                    "Drive Preferido",
                    f"Drive {drive_letter} definido como preferido."
                )
                
            except Exception as e:
                self.logger.error(f"Erro ao definir drive preferido: {e}")
                QMessageBox.warning(
                    self,
                    "Erro",
                    f"Erro ao definir drive preferido:\n{str(e)}"
                )
    
    def _apply_settings(self):
        """Aplica as configurações atuais."""
        try:
            settings = {
                'min_space_gb': self.min_space_spinbox.value(),
                'exclude_removable': self.exclude_removable_checkbox.isChecked(),
                'exclude_network': self.exclude_network_checkbox.isChecked(),
                'exclude_optical': self.exclude_optical_checkbox.isChecked(),
                'preferred_drive': self.preferred_drive_combo.currentText(),
                'selection_strategy': self.strategy_combo.currentText()
            }
            
            # Emitir sinal de mudança
            self.preferences_changed.emit(settings)
            
            # Atualizar drives com novas configurações
            self._refresh_drives()
            
            QMessageBox.information(
                self,
                "Configurações",
                "Configurações aplicadas com sucesso."
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao aplicar configurações: {e}")
            QMessageBox.warning(
                self,
                "Erro",
                f"Erro ao aplicar configurações:\n{str(e)}"
            )
    
    def _reset_settings(self):
        """Restaura as configurações padrão."""
        self.min_space_spinbox.setValue(50)
        self.exclude_removable_checkbox.setChecked(True)
        self.exclude_network_checkbox.setChecked(True)
        self.exclude_optical_checkbox.setChecked(True)
        self.preferred_drive_combo.setCurrentIndex(0)
        self.strategy_combo.setCurrentIndex(0)
        
        QMessageBox.information(
            self,
            "Configurações",
            "Configurações restauradas para os valores padrão."
        )
    
    def _on_settings_changed(self):
        """Callback chamado quando configurações são alteradas."""
        # Pode ser usado para validação em tempo real
        pass
    
    def _on_error_occurred(self, error_message: str):
        """Callback chamado quando ocorre um erro.
        
        Args:
            error_message: Mensagem de erro
        """
        self.logger.error(f"Erro no DriveSelectionWidget: {error_message}")
        
        # Atualizar status
        self.status_label.setText(f"Erro: {error_message}")
        self.refresh_button.setEnabled(True)
        
        # Mostrar mensagem de erro
        QMessageBox.warning(
            self,
            "Erro",
            f"Erro ao obter informações de drives:\n{error_message}"
        )
    
    def get_selected_drive(self) -> Optional[str]:
        """Retorna o drive atualmente selecionado.
        
        Returns:
            Letra do drive selecionado ou None
        """
        if self.selected_drive:
            return self.selected_drive.get('drive')
        return None
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Retorna as configurações atuais.
        
        Returns:
            Dicionário com as configurações atuais
        """
        return {
            'min_space_gb': self.min_space_spinbox.value(),
            'exclude_removable': self.exclude_removable_checkbox.isChecked(),
            'exclude_network': self.exclude_network_checkbox.isChecked(),
            'exclude_optical': self.exclude_optical_checkbox.isChecked(),
            'preferred_drive': self.preferred_drive_combo.currentText(),
            'selection_strategy': self.strategy_combo.currentText()
        }
    
    def closeEvent(self, event):
        """Evento chamado ao fechar o widget."""
        # Parar timer
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
        
        # Parar worker
        if self.drive_worker and self.drive_worker.isRunning():
            self.drive_worker.stop()
        
        super().closeEvent(event)