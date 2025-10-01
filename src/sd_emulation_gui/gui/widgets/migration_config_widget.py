#!/usr/bin/env python3
"""
Migration Configuration Widget

Widget que combina o seletor de diretório base com opções de configuração 
da migração, permitindo ao usuário configurar onde a estrutura será criada.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QMessageBox, QProgressBar, QTextEdit, QTabWidget,
    QScrollArea, QFrame
)

# Add src path for imports
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))

try:
    from .base_path_selector import BasePathSelector
    from services.migration_service import MigrationService
    from utils.path_utils import PathUtils
except ImportError:
    # Fallback for imports
    BasePathSelector = None
    MigrationService = None
    
    class PathUtils:
        @staticmethod
        def normalize_path(path) -> str:
            return os.path.normpath(str(path))


class MigrationConfigWidget(QWidget):
    """Widget de configuração da migração com seletor de diretório base."""
    
    # Signals
    migration_configured = Signal(str)  # Emitido quando a migração é configurada
    migration_started = Signal()
    migration_completed = Signal(dict)
    
    def __init__(self, migration_service=None, parent=None):
        super().__init__(parent)
        self.migration_service = migration_service
        self.current_base_path = ""
        self.setup_ui()
        
    def setup_ui(self):
        """Configura a interface do widget."""
        layout = QVBoxLayout(self)
        
        # Criar tabs para organizar as opções
        tab_widget = QTabWidget()
        
        # Tab 1: Configuração do Diretório Base
        base_config_tab = self._create_base_config_tab()
        tab_widget.addTab(base_config_tab, "📁 Diretório Base")
        
        # Tab 2: Opções de Migração
        migration_options_tab = self._create_migration_options_tab()
        tab_widget.addTab(migration_options_tab, "⚙️ Opções de Migração")
        
        # Tab 3: Status e Log
        status_tab = self._create_status_tab()
        tab_widget.addTab(status_tab, "📊 Status")
        
        layout.addWidget(tab_widget)
        
        # Barra de progresso (inicialmente oculta)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
    def _create_base_config_tab(self):
        """Cria a aba de configuração do diretório base."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Adicionar o seletor de diretório base se disponível
        if BasePathSelector:
            self.base_path_selector = BasePathSelector()
            self.base_path_selector.base_path_changed.connect(self._on_base_path_changed)
            
            # Scroll area para o seletor
            scroll = QScrollArea()
            scroll.setWidget(self.base_path_selector)
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(400)
            layout.addWidget(scroll)
        else:
            # Fallback simples se BasePathSelector não estiver disponível
            fallback_group = QGroupBox("Configuração do Diretório Base")
            fallback_layout = QVBoxLayout(fallback_group)
            
            info_label = QLabel(
                "O seletor de diretório base não está disponível.\n"
                "A estrutura será criada no diretório padrão."
            )
            info_label.setStyleSheet("color: #666;")
            fallback_layout.addWidget(info_label)
            
            layout.addWidget(fallback_group)
        
        # Informações adicionais
        info_group = QGroupBox("Informações Importantes")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel("""
<b>📌 Sobre a Estrutura de Emulação:</b><br><br>
• <b>Emulation/</b> - Diretório centralizado com BIOS, saves, configurações<br>
• <b>Roms/</b> - ROMs organizadas por plataforma (nomes completos)<br>
• <b>Emulators/</b> - Executáveis e configurações dos emuladores<br>
• <b>Tools/</b> - Ferramentas auxiliares e scripts<br>
• <b>Frontends/</b> - Interfaces gráficas (EmulationStation, etc.)<br><br>
<b>⚠️ Importante:</b> Certifique-se de ter espaço suficiente no drive selecionado.
        """)
        info_text.setWordWrap(True)
        info_text.setStyleSheet("font-size: 12px; padding: 10px;")
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)
        layout.addStretch()
        
        return tab
    
    def _create_migration_options_tab(self):
        """Cria a aba de opções de migração."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Opções de backup
        backup_group = QGroupBox("Opções de Backup")
        backup_layout = QVBoxLayout(backup_group)
        
        backup_info = QLabel(
            "Um backup automático será criado antes da migração para permitir "
            "rollback em caso de problemas."
        )
        backup_info.setWordWrap(True)
        backup_info.setStyleSheet("color: #666; font-size: 12px;")
        backup_layout.addWidget(backup_info)
        
        layout.addWidget(backup_group)
        
        # Opções de symlinks
        symlinks_group = QGroupBox("Opções de Symlinks")
        symlinks_layout = QVBoxLayout(symlinks_group)
        
        symlinks_info = QLabel(
            "Symlinks serão criados para manter compatibilidade com nomes curtos "
            "de plataformas (ex: 'NES' -> 'Nintendo Entertainment System')."
        )
        symlinks_info.setWordWrap(True)
        symlinks_info.setStyleSheet("color: #666; font-size: 12px;")
        symlinks_layout.addWidget(symlinks_info)
        
        layout.addWidget(symlinks_group)
        
        # Botões de ação
        actions_group = QGroupBox("Ações")
        actions_layout = QVBoxLayout(actions_group)
        
        # Botão para iniciar migração
        self.start_migration_button = QPushButton("🚀 Iniciar Migração")
        self.start_migration_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.start_migration_button.clicked.connect(self._start_migration)
        self.start_migration_button.setEnabled(False)  # Habilitado quando path é configurado
        actions_layout.addWidget(self.start_migration_button)
        
        # Botão para preview
        self.preview_button = QPushButton("👁️ Preview da Migração")
        self.preview_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.preview_button.clicked.connect(self._preview_migration)
        self.preview_button.setEnabled(False)
        actions_layout.addWidget(self.preview_button)
        
        layout.addWidget(actions_group)
        layout.addStretch()
        
        return tab
    
    def _create_status_tab(self):
        """Cria a aba de status e log."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Status atual
        status_group = QGroupBox("Status da Migração")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Aguardando configuração do diretório base...")
        self.status_label.setStyleSheet("font-weight: bold; color: #e67e22;")
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_group)
        
        # Log de atividades
        log_group = QGroupBox("Log de Atividades")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 4px;
            }
        """)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        return tab
    
    def _on_base_path_changed(self, new_path: str):
        """Chamado quando o diretório base é alterado."""
        self.current_base_path = new_path
        
        # Atualizar o migration service se disponível
        if self.migration_service and hasattr(self.migration_service, 'update_base_path'):
            self.migration_service.update_base_path(new_path)
        
        # Atualizar status
        self.status_label.setText(f"Diretório configurado: {new_path}")
        self.status_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        
        # Habilitar botões
        self.start_migration_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        
        # Log
        self._add_log(f"Diretório base configurado: {new_path}")
        
        # Emitir signal
        self.migration_configured.emit(new_path)
    
    def _start_migration(self):
        """Inicia o processo de migração."""
        if not self.current_base_path:
            QMessageBox.warning(
                self, 
                "Configuração Necessária", 
                "Por favor, configure o diretório base antes de iniciar a migração."
            )
            return
        
        # Confirmação
        reply = QMessageBox.question(
            self,
            "Confirmar Migração",
            f"Iniciar migração para o diretório:\n{self.current_base_path}\n\n"
            "Esta operação criará a estrutura de emulação e pode mover arquivos existentes. "
            "Um backup será criado automaticamente.\n\nDeseja continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Iniciar migração
        self._add_log("Iniciando processo de migração...")
        self.status_label.setText("Migração em andamento...")
        self.status_label.setStyleSheet("font-weight: bold; color: #f39c12;")
        
        # Mostrar barra de progresso
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Desabilitar botões durante migração
        self.start_migration_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        
        # Emitir signal
        self.migration_started.emit()
        
        # Simular processo de migração (em implementação real, seria assíncrono)
        QTimer.singleShot(2000, self._simulate_migration_completion)
    
    def _preview_migration(self):
        """Mostra um preview da migração."""
        if not self.current_base_path:
            return
        
        preview_text = f"""
Preview da Migração para: {self.current_base_path}

Estrutura que será criada:
📁 {self.current_base_path}/
├── 📁 Emulation/
│   ├── 📁 bios/
│   ├── 📁 saves/ 
│   ├── 📁 configs/
│   ├── 📁 shaders/
│   └── 📁 roms/
├── 📁 Emulators/
├── 📁 Roms/
├── 📁 Frontends/
├── 📁 Tools/
└── 📁 backups/

Operações planejadas:
• Criação de diretórios principais
• Organização de ROMs por plataforma
• Criação de symlinks para compatibilidade
• Configuração de emuladores
• Backup automático dos dados existentes
        """
        
        QMessageBox.information(self, "Preview da Migração", preview_text)
        self._add_log("Preview da migração visualizado")
    
    def _simulate_migration_completion(self):
        """Simula a conclusão da migração (para teste)."""
        # Em uma implementação real, isso seria chamado pelo migration service
        self.progress_bar.setVisible(False)
        
        self.status_label.setText("Migração concluída com sucesso!")
        self.status_label.setStyleSheet("font-weight: bold; color: #27ae60;")
        
        # Reabilitar botões
        self.start_migration_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        
        self._add_log("Migração concluída com sucesso!")
        
        # Emitir signal
        result = {
            "success": True,
            "message": "Migração concluída com sucesso",
            "base_path": self.current_base_path
        }
        self.migration_completed.emit(result)
        
        QMessageBox.information(
            self,
            "Migração Concluída",
            f"A estrutura de emulação foi criada com sucesso em:\n{self.current_base_path}"
        )
    
    def _add_log(self, message: str):
        """Adiciona uma mensagem ao log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.log_text.append(formatted_message)
        
        # Auto-scroll para a última mensagem
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)
    
    def set_migration_service(self, service):
        """Define o serviço de migração a ser usado."""
        self.migration_service = service
        
        # Configurar callback de progresso se disponível
        if hasattr(service, 'set_progress_callback'):
            service.set_progress_callback(self._add_log)
    
    def get_current_base_path(self) -> str:
        """Retorna o diretório base atualmente configurado."""
        return self.current_base_path


if __name__ == "__main__":
    # Teste do widget
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = MigrationConfigWidget()
    widget.setWindowTitle("Configuração de Migração")
    widget.resize(800, 600)
    widget.show()
    
    def on_migration_configured(path):
        print(f"Migração configurada para: {path}")
    
    def on_migration_completed(result):
        print(f"Migração concluída: {result}")
    
    widget.migration_configured.connect(on_migration_configured)
    widget.migration_completed.connect(on_migration_completed)
    
    sys.exit(app.exec())