"""
Legacy Detection Widget

Widget para detecção e tratamento de instalações legadas do EmuDeck e EmulationStationDE,
fornecendo interface para visualização, análise e limpeza de instalações antigas.
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional

try:
    from PySide6.QtCore import QTimer, Signal, QThread, Qt, QModelIndex
    from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QStandardItemModel, QStandardItem
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QGroupBox, QProgressBar, QGridLayout, QFrame, QScrollArea,
        QMessageBox, QSizePolicy, QSpacerItem, QComboBox, QTableView,
        QHeaderView, QCheckBox, QSpinBox, QLineEdit, QTextEdit,
        QTabWidget, QListWidget, QListWidgetItem, QAbstractItemView,
        QTreeWidget, QTreeWidgetItem, QSplitter, QDialog, QDialogButtonBox
    )
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    # Fallback classes for non-GUI environments
    class QWidget:
        def __init__(self, parent=None): pass
    class Signal: pass
    class QThread: pass


class LegacyDetectionWorker(QThread):
    """Worker thread para detecção de instalações legadas."""
    
    # Signals
    detection_completed = Signal(dict)
    detection_progress = Signal(str, int)
    error_occurred = Signal(str)
    
    def __init__(self, container, target_drive=None):
        """Inicializa o worker de detecção legada.
        
        Args:
            container: ApplicationContainer com os serviços
            target_drive: Drive específico para verificar (opcional)
        """
        super().__init__()
        self.container = container
        self.target_drive = target_drive
        self.logger = logging.getLogger(self.__class__.__name__)
        self.running = False
    
    def run(self):
        """Executa a detecção de instalações legadas."""
        try:
            self.running = True
            
            # Obter serviço
            legacy_service = self.container.legacy_detection_service()
            
            # Verificar e inicializar serviço se necessário
            try:
                # Verificar se o serviço tem os atributos necessários
                if not hasattr(legacy_service, 'drive_manager') or not hasattr(legacy_service, 'validation_service'):
                    self.logger.info("Inicializando LegacyDetectionService...")
                    legacy_service.initialize()
                
                # Verificar se os métodos necessários existem
                if not hasattr(legacy_service, 'scan_for_legacy_installations'):
                    raise AttributeError("LegacyDetectionService não possui método scan_for_legacy_installations")
                    
            except Exception as init_error:
                self.logger.error(f"Erro ao inicializar LegacyDetectionService: {init_error}")
                self.error_occurred.emit(f"Falha na inicialização do serviço: {init_error}")
                return
            
            # Verificar drives disponíveis (nova API robusta)
            self.detection_progress.emit("Verificando drives disponíveis...", 10)
            available_drives = legacy_service._verify_available_drives()
            if not available_drives:
                raise Exception("Nenhum drive disponível para detecção")
            
            # Executar scan completo de instalações legadas
            self.detection_progress.emit("Executando scan de instalações legadas...", 30)
            all_installations_dict = legacy_service.scan_for_legacy_installations()
            
            # Separar por tipo para compatibilidade com a UI
            emudeck_installations = []
            esde_installations = []
            
            for key, installation in all_installations_dict.items():
                if key == 'emudeck' or 'emudeck' in installation.name.lower():
                    emudeck_installations.append(installation)
                elif key == 'es-de' or 'emulationstation' in installation.name.lower():
                    esde_installations.append(installation)
                else:
                    # Outras instalações (dependências, runtimes, etc.)
                    emudeck_installations.append(installation)  # Agrupar com EmuDeck por enquanto
            
            # Calcular tamanhos e gerar recomendações
            self.detection_progress.emit("Analisando instalações encontradas...", 80)
            
            all_installations = emudeck_installations + esde_installations
            total_size = 0
            cleanup_recommendations = []
            
            for installation in all_installations:
                # O tamanho já está calculado no objeto installation
                if hasattr(installation, 'size_bytes'):
                    installation.total_size = installation.size_bytes
                    total_size += installation.size_bytes
                else:
                    installation.total_size = 0
            
            # Gerar recomendações usando o método correto
            cleanup_recommendations = legacy_service.get_cleanup_recommendations()
            
            self.detection_progress.emit("Detecção concluída!", 100)
            
            # Combinar resultados
            results = {
                'emudeck_installations': emudeck_installations,
                'esde_installations': esde_installations,
                'total_installations': len(all_installations),
                'total_size': total_size,
                'cleanup_recommendations': cleanup_recommendations,
                'target_drive': self.target_drive or 'C:'
            }
            
            self.detection_completed.emit(results)
            
        except Exception as e:
            self.logger.error(f"Erro na detecção legada: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.running = False
    
    def stop(self):
        """Para a execução do worker."""
        self.running = False
        if self.isRunning():
            self.quit()
            self.wait(5000)  # Aguarda até 5 segundos


class CleanupDialog(QDialog):
    """Dialog para confirmação de limpeza de instalações legadas."""
    
    def __init__(self, installations: List[Any], parent=None):
        """Inicializa o dialog de limpeza.
        
        Args:
            installations: Lista de instalações para limpeza
            parent: Widget pai
        """
        super().__init__(parent)
        self.installations = installations
        self.selected_installations = []
        
        self.setWindowTitle("Confirmar Limpeza")
        self.setModal(True)
        self.resize(600, 400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura a interface do dialog."""
        layout = QVBoxLayout(self)
        
        # Título
        title_label = QLabel("Selecione as instalações para remover:")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Lista de instalações
        self.installations_tree = QTreeWidget()
        self.installations_tree.setHeaderLabels(["Instalação", "Tipo", "Versão", "Tamanho", "Caminho"])
        self.installations_tree.setRootIsDecorated(True)
        
        for installation in self.installations:
            item = QTreeWidgetItem()
            item.setText(0, installation.name)
            item.setText(1, installation.type)
            item.setText(2, installation.version or "Desconhecida")
            
            # Formatar tamanho
            size_mb = getattr(installation, 'total_size', 0) / (1024 * 1024)
            item.setText(3, f"{size_mb:.1f} MB")
            
            item.setText(4, installation.path)
            item.setCheckState(0, Qt.Unchecked)
            item.setData(0, Qt.UserRole, installation)
            
            self.installations_tree.addTopLevelItem(item)
        
        layout.addWidget(self.installations_tree)
        
        # Aviso
        warning_label = QLabel("⚠️ ATENÇÃO: Esta operação não pode ser desfeita. Certifique-se de fazer backup dos dados importantes.")
        warning_label.setStyleSheet("color: #dc3545; font-weight: bold; padding: 10px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px;")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        # Botões
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accepted)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Conectar mudanças de seleção
        self.installations_tree.itemChanged.connect(self._on_item_changed)
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Callback chamado quando um item é alterado."""
        if column == 0:  # Coluna de checkbox
            installation = item.data(0, Qt.UserRole)
            if item.checkState(0) == Qt.Checked:
                if installation not in self.selected_installations:
                    self.selected_installations.append(installation)
            else:
                if installation in self.selected_installations:
                    self.selected_installations.remove(installation)
    
    def _on_accepted(self):
        """Callback chamado quando OK é clicado."""
        if not self.selected_installations:
            QMessageBox.warning(
                self,
                "Nenhuma Seleção",
                "Selecione pelo menos uma instalação para remover."
            )
            return
        
        # Confirmar novamente
        total_size = sum(getattr(inst, 'total_size', 0) for inst in self.selected_installations)
        size_mb = total_size / (1024 * 1024)
        
        reply = QMessageBox.question(
            self,
            "Confirmar Remoção",
            f"Tem certeza que deseja remover {len(self.selected_installations)} instalação(ões)?\n"
            f"Tamanho total: {size_mb:.1f} MB\n\n"
            f"Esta operação não pode ser desfeita!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.accept()
    
    def get_selected_installations(self) -> List[Any]:
        """Retorna as instalações selecionadas para remoção."""
        return self.selected_installations.copy()


class LegacyDetectionWidget(QWidget):
    """Widget para detecção e tratamento de instalações legadas."""
    
    # Signals
    detection_started = Signal()
    detection_completed = Signal(dict)
    cleanup_requested = Signal(list)
    
    def __init__(self, container, parent: QWidget = None):
        """Inicializa o widget de detecção legada.
        
        Args:
            container: ApplicationContainer com os serviços
            parent: Widget pai (opcional)
        """
        super().__init__(parent)
        
        self.container = container
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Worker para detecção
        self.detection_worker = None
        
        # Dados atuais
        self.current_results = {}
        self.emudeck_installations = []
        self.esde_installations = []
        
        # Configurar UI
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Configura a interface do usuário."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Título e controles
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Detecção de Instalações Legadas")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Seleção de drive
        header_layout.addWidget(QLabel("Drive:"))
        self.drive_combo = QComboBox()
        self.drive_combo.addItem("C: (Padrão)")
        self.drive_combo.setMinimumWidth(120)
        header_layout.addWidget(self.drive_combo)
        
        # Botão de detecção
        self.detect_button = QPushButton("Iniciar Detecção")
        self.detect_button.clicked.connect(self._start_detection)
        header_layout.addWidget(self.detect_button)
        
        layout.addLayout(header_layout)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel("Clique em 'Iniciar Detecção' para procurar instalações legadas.")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Splitter para dividir conteúdo
        splitter = QSplitter(Qt.Horizontal)
        
        # Painel esquerdo - Resumo
        summary_widget = self._create_summary_panel()
        splitter.addWidget(summary_widget)
        
        # Painel direito - Detalhes
        details_widget = self._create_details_panel()
        splitter.addWidget(details_widget)
        
        # Configurar proporções do splitter
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        # Botões de ação
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.cleanup_button = QPushButton("Limpar Instalações")
        self.cleanup_button.setEnabled(False)
        self.cleanup_button.clicked.connect(self._start_cleanup)
        actions_layout.addWidget(self.cleanup_button)
        
        self.export_button = QPushButton("Exportar Relatório")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_report)
        actions_layout.addWidget(self.export_button)
        
        layout.addLayout(actions_layout)
    
    def _create_summary_panel(self) -> QWidget:
        """Cria o painel de resumo."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Resumo geral
        summary_group = QGroupBox("Resumo da Detecção")
        summary_layout = QGridLayout(summary_group)
        
        self.total_installations_label = QLabel("Total de Instalações:")
        self.total_installations_value = QLabel("0")
        summary_layout.addWidget(self.total_installations_label, 0, 0)
        summary_layout.addWidget(self.total_installations_value, 0, 1)
        
        self.emudeck_count_label = QLabel("EmuDeck:")
        self.emudeck_count_value = QLabel("0")
        summary_layout.addWidget(self.emudeck_count_label, 1, 0)
        summary_layout.addWidget(self.emudeck_count_value, 1, 1)
        
        self.esde_count_label = QLabel("EmulationStationDE:")
        self.esde_count_value = QLabel("0")
        summary_layout.addWidget(self.esde_count_label, 2, 0)
        summary_layout.addWidget(self.esde_count_value, 2, 1)
        
        self.total_size_label = QLabel("Tamanho Total:")
        self.total_size_value = QLabel("0 MB")
        summary_layout.addWidget(self.total_size_label, 3, 0)
        summary_layout.addWidget(self.total_size_value, 3, 1)
        
        summary_layout.setColumnStretch(1, 1)
        layout.addWidget(summary_group)
        
        # Recomendações
        recommendations_group = QGroupBox("Recomendações")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        self.recommendations_text.setMaximumHeight(200)
        self.recommendations_text.setPlainText("Nenhuma recomendação disponível.")
        recommendations_layout.addWidget(self.recommendations_text)
        
        layout.addWidget(recommendations_group)
        
        layout.addStretch()
        
        return widget
    
    def _create_details_panel(self) -> QWidget:
        """Cria o painel de detalhes."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tabs para diferentes tipos
        self.details_tabs = QTabWidget()
        
        # Tab EmuDeck
        self.emudeck_tab = self._create_installations_tab("EmuDeck")
        self.details_tabs.addTab(self.emudeck_tab, "EmuDeck")
        
        # Tab EmulationStationDE
        self.esde_tab = self._create_installations_tab("EmulationStationDE")
        self.details_tabs.addTab(self.esde_tab, "EmulationStationDE")
        
        layout.addWidget(self.details_tabs)
        
        return widget
    
    def _create_installations_tab(self, installation_type: str) -> QWidget:
        """Cria uma tab para um tipo específico de instalação.
        
        Args:
            installation_type: Tipo de instalação (EmuDeck ou EmulationStationDE)
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tree widget para mostrar instalações
        tree = QTreeWidget()
        tree.setHeaderLabels(["Nome", "Versão", "Caminho", "Tamanho", "Componentes"])
        tree.setRootIsDecorated(True)
        tree.setAlternatingRowColors(True)
        
        # Configurar colunas
        header = tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        layout.addWidget(tree)
        
        # Armazenar referência da tree
        if installation_type == "EmuDeck":
            self.emudeck_tree = tree
        else:
            self.esde_tree = tree
        
        return widget
    
    def _setup_connections(self):
        """Configura as conexões de sinais."""
        pass
    
    def _start_detection(self):
        """Inicia a detecção de instalações legadas."""
        try:
            # Parar worker anterior se estiver rodando
            if self.detection_worker and self.detection_worker.isRunning():
                self.detection_worker.stop()
            
            # Obter drive selecionado
            drive_text = self.drive_combo.currentText()
            target_drive = drive_text.split(':')[0] + ':' if ':' in drive_text else None
            
            # Criar novo worker
            self.detection_worker = LegacyDetectionWorker(self.container, target_drive)
            self.detection_worker.detection_completed.connect(self._on_detection_completed)
            self.detection_worker.detection_progress.connect(self._on_detection_progress)
            self.detection_worker.error_occurred.connect(self._on_error_occurred)
            
            # Atualizar UI
            self.detect_button.setEnabled(False)
            self.cleanup_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Iniciando detecção...")
            
            # Limpar resultados anteriores
            self._clear_results()
            
            # Emitir sinal
            self.detection_started.emit()
            
            # Iniciar detecção
            self.detection_worker.start()
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar detecção: {e}")
            self._on_error_occurred(str(e))
    
    def _on_detection_progress(self, message: str, progress: int):
        """Callback chamado durante o progresso da detecção.
        
        Args:
            message: Mensagem de status
            progress: Progresso (0-100)
        """
        self.status_label.setText(message)
        self.progress_bar.setValue(progress)
    
    def _on_detection_completed(self, results: Dict[str, Any]):
        """Callback chamado quando a detecção é concluída.
        
        Args:
            results: Resultados da detecção
        """
        try:
            self.current_results = results
            
            # Extrair dados
            self.emudeck_installations = results.get('emudeck_installations', [])
            self.esde_installations = results.get('esde_installations', [])
            
            # Atualizar resumo
            self._update_summary(results)
            
            # Atualizar detalhes
            self._update_installations_tree(self.emudeck_tree, self.emudeck_installations)
            self._update_installations_tree(self.esde_tree, self.esde_installations)
            
            # Atualizar recomendações
            self._update_recommendations(results.get('cleanup_recommendations', []))
            
            # Atualizar UI
            total_installations = results.get('total_installations', 0)
            self.cleanup_button.setEnabled(total_installations > 0)
            self.export_button.setEnabled(total_installations > 0)
            
            # Emitir sinal
            self.detection_completed.emit(results)
            
            # Atualizar status
            if total_installations > 0:
                self.status_label.setText(f"Detecção concluída. Encontradas {total_installations} instalação(ões) legada(s).")
            else:
                self.status_label.setText("Detecção concluída. Nenhuma instalação legada encontrada.")
            
        except Exception as e:
            self.logger.error(f"Erro ao processar resultados: {e}")
            self._on_error_occurred(str(e))
        finally:
            self.detect_button.setEnabled(True)
            self.progress_bar.setVisible(False)
    
    def _update_summary(self, results: Dict[str, Any]):
        """Atualiza o resumo da detecção.
        
        Args:
            results: Resultados da detecção
        """
        total_installations = results.get('total_installations', 0)
        emudeck_count = len(results.get('emudeck_installations', []))
        esde_count = len(results.get('esde_installations', []))
        total_size = results.get('total_size', 0)
        
        self.total_installations_value.setText(str(total_installations))
        self.emudeck_count_value.setText(str(emudeck_count))
        self.esde_count_value.setText(str(esde_count))
        
        # Formatar tamanho
        if total_size > 0:
            size_mb = total_size / (1024 * 1024)
            if size_mb > 1024:
                size_gb = size_mb / 1024
                self.total_size_value.setText(f"{size_gb:.1f} GB")
            else:
                self.total_size_value.setText(f"{size_mb:.1f} MB")
        else:
            self.total_size_value.setText("0 MB")
    
    def _update_installations_tree(self, tree: QTreeWidget, installations: List[Any]):
        """Atualiza a árvore de instalações.
        
        Args:
            tree: Widget de árvore
            installations: Lista de instalações
        """
        tree.clear()
        
        for installation in installations:
            # Item principal
            item = QTreeWidgetItem()
            item.setText(0, installation.name)
            item.setText(1, installation.version or "Desconhecida")
            item.setText(2, installation.path)
            
            # Formatar tamanho
            size = getattr(installation, 'total_size', 0)
            if size > 0:
                size_mb = size / (1024 * 1024)
                if size_mb > 1024:
                    size_gb = size_mb / 1024
                    item.setText(3, f"{size_gb:.1f} GB")
                else:
                    item.setText(3, f"{size_mb:.1f} MB")
            else:
                item.setText(3, "Desconhecido")
            
            # Contar componentes
            components_count = len(installation.executables) + len(installation.config_files) + len(installation.data_directories)
            item.setText(4, str(components_count))
            
            # Adicionar componentes como filhos
            if installation.executables:
                exec_item = QTreeWidgetItem(item)
                exec_item.setText(0, "Executáveis")
                exec_item.setText(4, str(len(installation.executables)))
                
                for exe in installation.executables:
                    exe_item = QTreeWidgetItem(exec_item)
                    # Verificar se exe é um dicionário ou string
                    if isinstance(exe, dict):
                        # Se for dicionário, usar .get() normalmente
                        exe_item.setText(0, exe.get('name', 'Desconhecido'))
                        exe_item.setText(2, exe.get('path', ''))
                    elif isinstance(exe, str):
                        # Se for string (caminho), extrair nome do arquivo
                        exe_name = os.path.basename(exe) if exe else 'Desconhecido'
                        exe_item.setText(0, exe_name)
                        exe_item.setText(2, exe)
                    else:
                        # Fallback para outros tipos
                        exe_item.setText(0, str(exe) if exe else 'Desconhecido')
                        exe_item.setText(2, '')
            
            if installation.config_files:
                config_item = QTreeWidgetItem(item)
                config_item.setText(0, "Arquivos de Configuração")
                config_item.setText(4, str(len(installation.config_files)))
                
                for config in installation.config_files:
                    config_child = QTreeWidgetItem(config_item)
                    # Verificar se config é um dicionário ou string
                    if isinstance(config, dict):
                        # Se for dicionário, usar .get() normalmente
                        config_child.setText(0, config.get('name', 'Desconhecido'))
                        config_child.setText(2, config.get('path', ''))
                    elif isinstance(config, str):
                        # Se for string (caminho), extrair nome do arquivo
                        config_name = os.path.basename(config) if config else 'Desconhecido'
                        config_child.setText(0, config_name)
                        config_child.setText(2, config)
                    else:
                        # Fallback para outros tipos
                        config_child.setText(0, str(config) if config else 'Desconhecido')
                        config_child.setText(2, '')
            
            if installation.data_directories:
                data_item = QTreeWidgetItem(item)
                data_item.setText(0, "Diretórios de Dados")
                data_item.setText(4, str(len(installation.data_directories)))
                
                for data_dir in installation.data_directories:
                    data_child = QTreeWidgetItem(data_item)
                    # Verificar se data_dir é um dicionário ou string
                    if isinstance(data_dir, dict):
                        # Se for dicionário, usar .get() normalmente
                        data_child.setText(0, data_dir.get('name', 'Desconhecido'))
                        data_child.setText(2, data_dir.get('path', ''))
                    elif isinstance(data_dir, str):
                        # Se for string (caminho), extrair nome do diretório
                        dir_name = os.path.basename(data_dir.rstrip(os.sep)) if data_dir else 'Desconhecido'
                        data_child.setText(0, dir_name)
                        data_child.setText(2, data_dir)
                    else:
                        # Fallback para outros tipos
                        data_child.setText(0, str(data_dir) if data_dir else 'Desconhecido')
                        data_child.setText(2, '')
            
            tree.addTopLevelItem(item)
            item.setExpanded(True)
    
    def _update_recommendations(self, recommendations: List[str]):
        """Atualiza as recomendações.
        
        Args:
            recommendations: Lista de recomendações
        """
        if recommendations:
            text = "Recomendações de limpeza:\n\n"
            for i, rec in enumerate(recommendations, 1):
                text += f"{i}. {rec}\n"
        else:
            text = "Nenhuma recomendação de limpeza disponível."
        
        self.recommendations_text.setPlainText(text)
    
    def _start_cleanup(self):
        """Inicia o processo de limpeza."""
        try:
            # Combinar todas as instalações
            all_installations = self.emudeck_installations + self.esde_installations
            
            if not all_installations:
                QMessageBox.information(
                    self,
                    "Nenhuma Instalação",
                    "Nenhuma instalação legada encontrada para limpeza."
                )
                return
            
            # Mostrar dialog de confirmação
            dialog = CleanupDialog(all_installations, self)
            if dialog.exec() == QDialog.Accepted:
                selected_installations = dialog.get_selected_installations()
                
                if selected_installations:
                    # Emitir sinal para limpeza
                    self.cleanup_requested.emit(selected_installations)
                    
                    QMessageBox.information(
                        self,
                        "Limpeza Iniciada",
                        f"Limpeza de {len(selected_installations)} instalação(ões) iniciada.\n"
                        f"Verifique o log para acompanhar o progresso."
                    )
        
        except Exception as e:
            self.logger.error(f"Erro ao iniciar limpeza: {e}")
            QMessageBox.warning(
                self,
                "Erro",
                f"Erro ao iniciar limpeza:\n{str(e)}"
            )
    
    def _export_report(self):
        """Exporta um relatório da detecção."""
        try:
            if not self.current_results:
                QMessageBox.information(
                    self,
                    "Nenhum Resultado",
                    "Execute a detecção primeiro para gerar um relatório."
                )
                return
            
            # Gerar relatório em texto
            report = self._generate_text_report()
            
            # Salvar em arquivo (implementação simplificada)
            from PySide6.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Relatório",
                "relatorio_deteccao_legada.txt",
                "Arquivos de Texto (*.txt);;Todos os Arquivos (*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                QMessageBox.information(
                    self,
                    "Relatório Exportado",
                    f"Relatório salvo em:\n{file_path}"
                )
        
        except Exception as e:
            self.logger.error(f"Erro ao exportar relatório: {e}")
            QMessageBox.warning(
                self,
                "Erro",
                f"Erro ao exportar relatório:\n{str(e)}"
            )
    
    def _generate_text_report(self) -> str:
        """Gera um relatório em texto dos resultados.
        
        Returns:
            String com o relatório
        """
        report = "RELATÓRIO DE DETECÇÃO DE INSTALAÇÕES LEGADAS\n"
        report += "=" * 50 + "\n\n"
        
        # Resumo
        report += "RESUMO:\n"
        report += f"- Total de instalações: {self.current_results.get('total_installations', 0)}\n"
        report += f"- EmuDeck: {len(self.emudeck_installations)}\n"
        report += f"- EmulationStationDE: {len(self.esde_installations)}\n"
        
        total_size = self.current_results.get('total_size', 0)
        if total_size > 0:
            size_mb = total_size / (1024 * 1024)
            report += f"- Tamanho total: {size_mb:.1f} MB\n"
        
        report += f"- Drive verificado: {self.current_results.get('target_drive', 'Desconhecido')}\n\n"
        
        # Detalhes das instalações
        if self.emudeck_installations:
            report += "INSTALAÇÕES EMUDECK:\n"
            for installation in self.emudeck_installations:
                report += f"- {installation.name}\n"
                report += f"  Versão: {installation.version or 'Desconhecida'}\n"
                report += f"  Caminho: {installation.path}\n"
                
                size = getattr(installation, 'total_size', 0)
                if size > 0:
                    size_mb = size / (1024 * 1024)
                    report += f"  Tamanho: {size_mb:.1f} MB\n"
                
                report += "\n"
        
        if self.esde_installations:
            report += "INSTALAÇÕES EMULATIONSTATIONDE:\n"
            for installation in self.esde_installations:
                report += f"- {installation.name}\n"
                report += f"  Versão: {installation.version or 'Desconhecida'}\n"
                report += f"  Caminho: {installation.path}\n"
                
                size = getattr(installation, 'total_size', 0)
                if size > 0:
                    size_mb = size / (1024 * 1024)
                    report += f"  Tamanho: {size_mb:.1f} MB\n"
                
                report += "\n"
        
        # Recomendações
        recommendations = self.current_results.get('cleanup_recommendations', [])
        if recommendations:
            report += "RECOMENDAÇÕES:\n"
            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec}\n"
        
        return report
    
    def _clear_results(self):
        """Limpa os resultados anteriores."""
        self.current_results = {}
        self.emudeck_installations = []
        self.esde_installations = []
        
        # Limpar UI
        self.total_installations_value.setText("0")
        self.emudeck_count_value.setText("0")
        self.esde_count_value.setText("0")
        self.total_size_value.setText("0 MB")
        
        self.emudeck_tree.clear()
        self.esde_tree.clear()
        
        self.recommendations_text.setPlainText("Nenhuma recomendação disponível.")
    
    def _on_error_occurred(self, error_message: str):
        """Callback chamado quando ocorre um erro.
        
        Args:
            error_message: Mensagem de erro
        """
        self.logger.error(f"Erro no LegacyDetectionWidget: {error_message}")
        
        # Atualizar UI
        self.detect_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Erro: {error_message}")
        
        # Mostrar mensagem de erro
        QMessageBox.warning(
            self,
            "Erro",
            f"Erro na detecção de instalações legadas:\n{error_message}"
        )
    
    def get_current_results(self) -> Dict[str, Any]:
        """Retorna os resultados atuais da detecção.
        
        Returns:
            Dicionário com os resultados atuais
        """
        return self.current_results.copy()
    
    def closeEvent(self, event):
        """Evento chamado ao fechar o widget."""
        # Parar worker
        if self.detection_worker and self.detection_worker.isRunning():
            self.detection_worker.stop()
        
        super().closeEvent(event)